import subprocess
import time
import os
import logging
from dao import FleetDAO
from config_vars import MONGO_URI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BackupService")

def run_backup():
    logger.info("Iniciando proceso de backup automático de MongoDB...")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_filename = f"fleet_db_backup_{timestamp}.archive"
    dao = None

    try:
        # Volcado a un archivo local
        logger.info("Ejecutando mongodump...")
        cmd = ["mongodump", "--uri", MONGO_URI, "--archive=" + backup_filename]
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Dump generado correctamente: {backup_filename}")

        # Subir a MinIO a través del DAO
        with open(backup_filename, "rb") as f:
            file_data = f.read()

        dao = FleetDAO()
        url = dao.upload_file(
            bucket_name="backups",
            object_name=backup_filename,
            file_data=file_data
        )
        logger.info(f"Backup subido a MinIO (Storage). URL de descarga generada.")
        logger.info("Proceso de backup finalizado correctamente.")

    except FileNotFoundError:
        logger.error("No se encontró 'mongodump' en el sistema local. Instale MongoDB Database Tools.")
    except Exception as e:
        logger.error(f"Error grave en el backup: {e}")
    finally:
        # Limpiar archivo temporal, exista o no, haya fallado o no el proceso
        if os.path.exists(backup_filename):
            os.remove(backup_filename)
        # Cerrar la conexión del DAO para no dejarla abierta en cada corrida
        if dao is not None:
            dao.close()

if __name__ == "__main__":
    run_backup()
