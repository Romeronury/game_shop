# Game Shop 2.0
Tienda de videojuegos con Flask, MongoDB Atlas, catálogo de portadas, ficha individual, inventario CRUD y API REST.

## Ejecutar localmente
1. Crea un entorno virtual e instala `pip install -r requirements.txt`.
2. Configura la variable de entorno `MONGO_URI` con tu conexión privada a MongoDB Atlas o inicia MongoDB local.
3. Ejecuta `python app.py` y abre http://127.0.0.1:5000.

## Render
Root Directory: carpeta que contiene `app.py` y `requirements.txt`.
Build Command: `pip install -r requirements.txt`
Start Command: `gunicorn app:app`
Environment: `MONGO_URI` (cadena privada de MongoDB Atlas).

## API
GET/POST `/api/videojuegos`
GET/PUT/DELETE `/api/videojuegos/<id>`

Ejemplo POST (Body → raw → JSON):
```json
{
  "nombre":"Minecraft",
  "categoria":"Aventura",
  "precio":599,
  "stock":12,
  "descripcion":"Juego de construcción y exploración.",
  "desarrollador":"Mojang Studios",
  "imagen":"",
  "banner":""
}
```
Las imágenes deben ser enlaces públicos directos. No se incluyen portadas con derechos de terceros.

**Nota:** esta versión usa base `game_shop` y colección `videojuegos`, distintas de la antigua base `escuela_practica` / `alumnos`. No migra registros antiguos.

**Aviso:** proyecto educativo; los botones de compra/descarga reales no están implementados. El catálogo es de demostración. Para una tienda real hacen falta autenticación, autorización, pagos y gestión de derechos de imágenes.
