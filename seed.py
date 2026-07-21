import random
from datetime import datetime, timedelta
from pymongo.errors import DuplicateKeyError

from dao import FleetDAO
from db_models.trucks import Truck
from db_models.drivers import Driver
from db_models.routes import Route
from db_models.telemetry import Telemetry

def seed_database():
    print("Iniciando carga de datos de prueba...\n")
    dao = FleetDAO()
    
    # Me fijo si ya hay datos cargados
    if len(dao.get_trucks()) > 0:
        print("La base de datos ya tiene camiones cargados, limpiando para cargar nuevos datos...")
        dao._db["trucks"].delete_many({})
        dao._db["drivers"].delete_many({})
        dao._db["routes"].delete_many({})
        dao._db["telemetry"].delete_many({})
        print("  ✓ Datos anteriores limpiados.\n")

    print("Insertando camiones...")
    t1_id = dao.add_truck(Truck(brand="Volvo", capacity_tons=25.5))
    print(f"  ✓ Camión: Volvo (Capacidad: 25.5t)")
    t2_id = dao.add_truck(Truck(brand="Mercedes-Benz", capacity_tons=30.0))
    print(f"  ✓ Camión: Mercedes-Benz (Capacidad: 30.0t)")
    t3_id = dao.add_truck(Truck(brand="Scania", capacity_tons=18.0))
    print(f"  ✓ Camión: Scania (Capacidad: 18.0t)\n")

    print("Insertando choferes...")
    d1_id = dao.add_driver(Driver(name="Juan Perez", license_level="A"))
    print(f"  ✓ Chofer: Juan Perez (Licencia A)")
    d2_id = dao.add_driver(Driver(name="Maria Gonzalez", license_level="B"))
    print(f"  ✓ Chofer: Maria Gonzalez (Licencia B)\n")

    print("Insertando rutas...")
    dao.add_route(Route(origin="Buenos Aires", destination="Cordoba", truck_id=t1_id, driver_id=d1_id))
    print("  ✓ Ruta: Buenos Aires -> Cordoba (Asignada a Juan Perez en Volvo)")
    dao.add_route(Route(origin="Rosario", destination="Mendoza", truck_id=t2_id, driver_id=d2_id))
    print("  ✓ Ruta: Rosario -> Mendoza (Asignada a Maria Gonzalez en Mercedes-Benz)\n")
    
    trucks = dao.get_trucks()
    if not trucks:
        print("Error: No se encontraron camiones!")
        return
        
    t1_id = str(trucks[0]["_id"])
    print(f"Simulando telemetría para el camión {t1_id}...")
    
    base_time = datetime(2026, 7, 19, 8, 0, 0)
    current_speed = 0
    current_fuel = 100.0
    current_temp = 70.0
    
    # Coordenadas: Buenos Aires a Cordoba
    start_lon, start_lat = -58.3816, -34.6037
    end_lon, end_lat = -64.1835, -31.4201
    
    total_steps = 120
    
    for i in range(total_steps): # Simulamos 2 horas de viaje, guardando datos cada minuto
        current_time = base_time + timedelta(minutes=i)
        
        # Calculo el avance del camion en el mapa
        progress = i / float(total_steps - 1)
        current_lon = start_lon + (end_lon - start_lon) * progress
        current_lat = start_lat + (end_lat - start_lat) * progress
        
        # Le meto ruido al GPS para que no sea una linea recta aburrida
        current_lon += random.uniform(-0.01, 0.01)
        current_lat += random.uniform(-0.01, 0.01)
        
        # Acelera y frena el camion
        if i < 10:
            current_speed += random.uniform(5, 10)
        elif i > 110:
            current_speed -= random.uniform(5, 10)
        else:
            current_speed += random.uniform(-3, 3)
            
        current_speed = max(0, min(100, current_speed))
        
        # Hacemos que pise el acelerador a fondo a la mitad del viaje para que salte una alerta
        if 55 < i < 65:
            current_speed = 115.0 # Exceso de velocidad
            
        # Suben las revoluciones y la temperatura si va mas rapido
        if current_speed == 0:
            current_rpm = 800
            current_temp = max(70, current_temp - 0.5)
        else:
            current_rpm = int(1000 + (current_speed * 15) + random.uniform(-100, 100))
            current_temp = min(95, current_temp + random.uniform(-0.2, 0.5))
            
        # Hacemos que se le caliente el motor mas adelante
        if 75 < i < 85:
            current_temp = 105.0 # Motor recalentado
            
        # Va gastando combustible de a poco
        current_fuel -= random.uniform(0.05, 0.15)
        
        telemetry = Telemetry(
            truck_id=t1_id,
            timestamp=current_time,
            speed_kmh=round(current_speed, 2),
            engine_rpm=current_rpm,
            engine_temp_c=round(current_temp, 2),
            fuel_level_pct=round(current_fuel, 2),
            lon=round(current_lon, 5),
            lat=round(current_lat, 5)
        )
        
        try:
            dao.add_telemetry(telemetry)
        except DuplicateKeyError:
            pass
            
    print(f"  ✓ {total_steps} eventos de telemetría insertados.\n")
    print("✓ Seed completado.")
    dao.close()

if __name__ == "__main__":
    seed_database()
