import os
from datetime import datetime
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, url_for, abort, jsonify
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
mongo_uri = os.environ.get('MONGO_URI')
if not mongo_uri:
    if os.environ.get('RENDER'):
        raise RuntimeError('Configura MONGO_URI en Render.')
    mongo_uri = 'mongodb://127.0.0.1:27017/'
cliente = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
juegos = cliente['game_shop']['videojuegos']
CATEGORIAS = ['Acción','Aventura','Terror','Carreras','Deportes','Estrategia','RPG','Simulación','Multijugador','Otros']

def validar_imagen(url):
    if not url: return ''
    p = urlparse(url)
    if p.scheme not in ('https', 'http') or not p.netloc:
        abort(400, description='La imagen debe ser una URL http o https válida.')
    return url

def leer_datos(origen):
    nombre = str(origen.get('nombre','')).strip()
    categoria = str(origen.get('categoria','')).strip()
    descripcion = str(origen.get('descripcion','')).strip()
    desarrollador = str(origen.get('desarrollador','')).strip()
    imagen = str(origen.get('imagen','')).strip()
    banner = str(origen.get('banner','')).strip()
    try:
        precio = float(origen.get('precio', 0))
        stock = int(origen.get('stock', 0))
    except (TypeError, ValueError):
        abort(400, description='Precio y stock deben ser números válidos.')
    if not nombre or not categoria:
        abort(400, description='Completa nombre y categoría.')
    if len(nombre)>100 or len(categoria)>40 or len(descripcion)>2000 or len(desarrollador)>100:
        abort(400, description='Uno de los campos supera el máximo permitido.')
    if precio<0 or stock<0 or precio>1000000 or stock>1000000:
        abort(400, description='Precio y stock deben ser valores válidos no negativos.')
    if len(imagen)>1000 or len(banner)>1000:
        abort(400, description='La URL de imagen es demasiado larga.')
    return dict(nombre=nombre,categoria=categoria,descripcion=descripcion,desarrollador=desarrollador,
                precio=precio,stock=stock,imagen=validar_imagen(imagen),banner=validar_imagen(banner))

def buscar_juego(id):
    if not ObjectId.is_valid(id): abort(404, description='ID inválido.')
    juego = juegos.find_one({'_id':ObjectId(id)})
    if not juego: abort(404, description='Videojuego no encontrado.')
    return juego

def serializar(j):
    return {'id':str(j['_id']),**{k:j.get(k, '' if k not in ('precio','stock') else 0) for k in
        ('nombre','categoria','descripcion','desarrollador','precio','stock','imagen','banner')}}

@app.route('/')
def inicio():
    q = request.args.get('q','').strip()
    categoria = request.args.get('categoria','').strip()
    filtro = {}
    if q: filtro['nombre']={'$regex':__import__('re').escape(q),'$options':'i'}
    if categoria: filtro['categoria']=categoria
    lista = list(juegos.find(filtro).sort('nombre',1))
    return render_template('index.html', juegos=lista, categorias=CATEGORIAS, q=q, categoria=categoria)

@app.route('/juego/<id>')
def detalle(id):
    return render_template('detalle.html', juego=buscar_juego(id))

@app.route('/registrar')
def registrar():
    return render_template('registrar.html', categorias=CATEGORIAS)

@app.route('/agregar',methods=['POST'])
def agregar():
    juegos.insert_one(leer_datos(request.form))
    return redirect(url_for('inicio'))

@app.route('/lista')
def lista():
    lista_juegos=list(juegos.find().sort('nombre',1))
    return render_template('lista.html',juegos=lista_juegos)

@app.route('/editar/<id>',methods=['GET','POST'])
def editar(id):
    juego=buscar_juego(id)
    if request.method=='POST':
        juegos.update_one({'_id':juego['_id']},{'$set':leer_datos(request.form)})
        return redirect(url_for('detalle',id=id))
    return render_template('editar.html',juego=juego,categorias=CATEGORIAS)

@app.route('/eliminar/<id>',methods=['POST'])
def eliminar(id):
    juego=buscar_juego(id)
    juegos.delete_one({'_id':juego['_id']})
    return redirect(url_for('lista'))

@app.route('/ayuda')
def ayuda():
    return render_template('ayuda.html',fecha=datetime.now().strftime('%d/%m/%Y'))

@app.route('/api/videojuegos',methods=['GET','POST'])
def api_videojuegos():
    if request.method=='GET':
        return jsonify([serializar(j) for j in juegos.find().sort('nombre',1)])
    datos=request.get_json(silent=True)
    if not isinstance(datos,dict): return jsonify(error='Envía un objeto JSON.'),400
    doc=leer_datos(datos)
    result=juegos.insert_one(doc)
    doc['_id']=result.inserted_id
    return jsonify(mensaje='Videojuego registrado correctamente',videojuego=serializar(doc)),201

@app.route('/api/videojuegos/<id>',methods=['GET','PUT','DELETE'])
def api_videojuego(id):
    juego=buscar_juego(id)
    if request.method=='GET': return jsonify(serializar(juego))
    if request.method=='DELETE':
        juegos.delete_one({'_id':juego['_id']})
        return jsonify(mensaje='Videojuego eliminado correctamente')
    datos=request.get_json(silent=True)
    if not isinstance(datos,dict): return jsonify(error='Envía un objeto JSON.'),400
    nuevo=leer_datos(datos)
    juegos.update_one({'_id':juego['_id']},{'$set':nuevo})
    nuevo['_id']=juego['_id']
    return jsonify(mensaje='Videojuego actualizado correctamente',videojuego=serializar(nuevo))

@app.errorhandler(PyMongoError)
def error_mongo(error):
    app.logger.error('Error al consultar MongoDB: %s',type(error).__name__)
    if request.path.startswith('/api/'):
        return jsonify(error='No fue posible conectar con MongoDB.'),503
    return render_template('error.html',mensaje='No fue posible conectar con MongoDB.'),503

@app.errorhandler(HTTPException)
def error_http(error):
    if request.path.startswith('/api/'):
        return jsonify(error=error.description),error.code
    return render_template('error.html',mensaje=error.description),error.code

if __name__=='__main__':
    app.run(host='127.0.0.1',port=5000,debug=False)
