from pymongo import MongoClient, GEOSPHERE, ASCENDING
from config_vars import MONGO_URI, DB_NAME


def setup():
    """
    Inicializa la base de datos FleetDAO.
    Crea las colecciones con sus índices.
    Seguro para correr múltiples veces — no rompe datos existentes.
    """
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    # Colección: telemetry
    telemetry = db["telemetry"]
    
    # Índice compuesto único para evitar duplicación de eventos de telemetría
    telemetry.create_index(
        [("truck_id", ASCENDING), ("timestamp", ASCENDING)],
        unique=True
    )
    print("--OK-- Colección telemetry — índice compuesto único (truck_id, timestamp) creado")
    
    # Índice geoespacial 2dsphere para permitir operaciones $near y $geoWithin
    telemetry.create_index([("location", GEOSPHERE)])
    print("--OK-- Colección telemetry — índice geoespacial (location: 2dsphere) creado")

    client.close()
    print(f"\n--OK-- Base de datos '{DB_NAME}' lista.")


if __name__ == "__main__":
    setup()
