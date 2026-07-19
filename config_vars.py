import os
from dotenv import load_dotenv

# Cargo las variables de entorno desde el .env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "fleet_db")
