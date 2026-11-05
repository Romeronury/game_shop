
"""Reservas temporales del carrito de Game Shop 2.0."""

from datetime import datetime, timedelta, timezone
from bson import ObjectId
from pymongo import ReturnDocument

RESERVA_SEGUNDOS = 60


def ahora():
    return datetime.now(timezone.utc)


class SinExistencias(Exception):
    pass


def liberar_reservas_vencidas(juegos, reservas):
    """Devuelve el inventario de las reservas vencidas."""

    vencidas = reservas.find(
        {
            "estado": "reservada",
            "vence_en": {"$lte": ahora()}
        },
        {"_id": 1}
    )

    ids = [reserva["_id"] for reserva in vencidas]
    liberadas = 0

    for reserva_id in ids:

        def operacion(sesion):
            fecha = ahora()

            reserva = reservas.find_one_and_update(
                {
                    "_id": reserva_id,
                    "estado": "reservada",
                    "vence_en": {"$lte": fecha}
                },
                {
                    "$set": {
                        "estado": "vencida",
                        "finalizado_en": fecha
                    }
                },
                return_document=ReturnDocument.AFTER,
                session=sesion
            )

            if reserva is None:
                return False

            for item in reserva["items"]:
                resultado = juegos.update_one(
                    {"_id": item["juego_id"]},
                    {
                        "$inc": {
                            "stock": item["cantidad"]
                        }
                    },
                    session=sesion
                )

                if resultado.matched_count != 1:
                    raise RuntimeError(
                        "No se pudo devolver el inventario."
                    )

            return True

        with juegos.database.client.start_session() as sesion:
            if sesion.with_transaction(operacion):
                liberadas += 1

    return liberadas


def reservar_carrito(juegos, reservas, usuario_id, carrito):
    """Reserva todos los productos o ninguno."""

    if not carrito:
        return None, "Tu carrito está vacío."

    try:
        usuario = ObjectId(usuario_id)

        items = [
            (ObjectId(juego_id), int(cantidad))
            for juego_id, cantidad in carrito.items()
        ]

        if any(cantidad < 1 or cantidad > 100
               for _, cantidad in items):
            raise ValueError()

    except (TypeError, ValueError):
        return None, "El carrito contiene datos inválidos."

    reserva_id = ObjectId()

    def operacion(sesion):
        fecha = ahora()

        existente = reservas.find_one(
            {
                "usuario_id": usuario,
                "estado": "reservada",
                "vence_en": {"$gt": fecha}
            },
            session=sesion
        )

        if existente:
            return None, "Ya tienes una reserva activa."

        productos = []

        for juego_id, cantidad in items:
            juego = juegos.find_one_and_update(
                {
                    "_id": juego_id,
                    "stock": {"$gte": cantidad}
                },
                {
                    "$inc": {"stock": -cantidad}
                },
                return_document=ReturnDocument.AFTER,
                session=sesion
            )

            if juego is None:
                raise SinExistencias(
                    "No hay existencias suficientes "
                    "para completar el carrito."
                )

            productos.append({
                "juego_id": juego_id,
                "nombre": juego["nombre"],
                "cantidad": cantidad,
                "precio": float(juego["precio"])
            })

        total = round(
            sum(
                item["cantidad"] * item["precio"]
                for item in productos
            ),
            2
        )

        reservas.insert_one(
            {
                "_id": reserva_id,
                "usuario_id": usuario,
                "items": productos,
                "total": total,
                "estado": "reservada",
                "creado_en": fecha,
                "vence_en": fecha + timedelta(
                    seconds=RESERVA_SEGUNDOS
                )
            },
            session=sesion
        )

        return str(reserva_id), None

    try:
        with juegos.database.client.start_session() as sesion:
            return sesion.with_transaction(operacion)

    except SinExistencias as error:
        return None, str(error)


def cancelar_carrito(
    juegos, reservas, usuario_id, reserva_id
):
    """Cancela una reserva vigente y devuelve el stock."""

    try:
        usuario = ObjectId(usuario_id)
        identificador = ObjectId(reserva_id)

    except (TypeError, ValueError):
        return False

    def operacion(sesion):
        fecha = ahora()

        reserva = reservas.find_one_and_update(
            {
                "_id": identificador,
                "usuario_id": usuario,
                "estado": "reservada",
                "vence_en": {"$gt": fecha}
            },
            {
                "$set": {
                    "estado": "cancelada",
                    "finalizado_en": fecha
                }
            },
            return_document=ReturnDocument.AFTER,
            session=sesion
        )

        if reserva is None:
            return False

        for item in reserva["items"]:
            resultado = juegos.update_one(
                {"_id": item["juego_id"]},
                {
                    "$inc": {
                        "stock": item["cantidad"]
                    }
                },
                session=sesion
            )

            if resultado.matched_count != 1:
                raise RuntimeError(
                    "No se pudo devolver el inventario."
                )

        return True

    with juegos.database.client.start_session() as sesion:
        return sesion.with_transaction(operacion)


def confirmar_carrito(
    juegos, reservas, pedidos, usuario_id, reserva_id
):
    """Confirma la reserva y registra una compra simulada."""

    try:
        usuario = ObjectId(usuario_id)
        identificador = ObjectId(reserva_id)

    except (TypeError, ValueError):
        return False

    pedido_id = ObjectId()

    def operacion(sesion):
        fecha = ahora()

        reserva = reservas.find_one_and_update(
            {
                "_id": identificador,
                "usuario_id": usuario,
                "estado": "reservada",
                "vence_en": {"$gt": fecha}
            },
            {
                "$set": {
                    "estado": "confirmada",
                    "finalizado_en": fecha
                }
            },
            return_document=ReturnDocument.AFTER,
            session=sesion
        )

        if reserva is None:
            return False

        items = [
            {
                "id": str(item["juego_id"]),
                "nombre": item["nombre"],
                "cantidad": item["cantidad"],
                "precio": item["precio"]
            }
            for item in reserva["items"]
        ]

        pedidos.insert_one(
            {
                "_id": pedido_id,
                "reserva_id": identificador,
                "usuario_id": usuario,
                "items": items,
                "total": reserva["total"],
                "fecha": fecha,
                "estado": "Simulada"
            },
            session=sesion
        )

        return True

    with juegos.database.client.start_session() as sesion:
        return sesion.with_transaction(operacion)
