
import time
import logging

from app import cliente
from reservas_temporales import liberar_reservas_vencidas

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

base_datos = cliente["game_shop"]
juegos = base_datos["videojuegos"]
reservas = base_datos["reservas"]


def limpiar():
    cantidad = liberar_reservas_vencidas(
        juegos,
        reservas
    )

    if cantidad:
        logging.info(
            "Reservas vencidas liberadas: %s",
            cantidad
        )


if __name__ == "__main__":
    logging.info(
        "Servicio de limpieza de reservas iniciado."
    )

    while True:
        try:
            limpiar()
        except Exception:
            logging.exception(
                "Error al liberar reservas vencidas."
            )

        time.sleep(5)
