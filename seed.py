import random
from datetime import datetime, timedelta
from pymongo.errors import DuplicateKeyError

from dao import FleetDAO
from db_models.trucks import Truck
from db_models.drivers import Driver
from db_models.routes import Route
from db_models.telemetry import Telemetry

def seed_database():
    dao = FleetDAO()
    
    # Check if already seeded
    if len(dao.get_trucks()) > 0:
        print("La base de datos ya tiene camiones cargados, actualizando los datos de prueba...")
    else:
        print("Agregando camiones...")
        t1_id = dao.add_truck(Truck(brand="Volvo", capacity_tons=25.5))
        t2_id = dao.add_truck(Truck(brand="Mercedes-Benz", capacity_tons=30.0))
        t3_id = dao.add_truck(Truck(brand="Scania", capacity_tons=18.0))

        print("Agregando choferes...")
        d1_id = dao.add_driver(Driver(name="Juan Perez", license_level="A"))
        d2_id = dao.add_driver(Driver(name="Maria Gonzalez", license_level="B"))

        print("Agregando rutas...")
        dao.add_route(Route(origin="Buenos Aires", destination="Cordoba", truck_id=t1_id, driver_id=d1_id))
        dao.add_route(Route(origin="Rosario", destination="Mendoza", truck_id=t2_id, driver_id=d2_id))
    
    trucks = dao.get_trucks()
    if not trucks:
        print("No trucks found!")
        return
        
    t1_id = str(trucks[0]["_id"])
    print(f"Armando el viaje de prueba para el camion {t1_id}...")
    
    # Borro lo viejo por si corro el script dos veces
    dao._telemetry.delete_many({})
    
    base_time = datetime(2026, 7, 19, 8, 0, 0)
    current_speed = 0
    current_fuel = 100.0
    current_temp = 70.0
    
    # GPS: Buenos Aires (-58.3816, -34.6037) to Cordoba (-64.1835, -31.4201)
    start_lon, start_lat = -58.3816, -34.6037
    end_lon, end_lat = -64.1835, -31.4201
    
    total_steps = 120
    
    for i in range(total_steps): # 2 hours of data, every minute
        current_time = base_time + timedelta(minutes=i)
        
        # Interpolate GPS
        progress = i / float(total_steps - 1)
        current_lon = start_lon + (end_lon - start_lon) * progress
        current_lat = start_lat + (end_lat - start_lat) * progress
        
        # Add some noise to GPS (wobble)
        current_lon += random.uniform(-0.01, 0.01)
        current_lat += random.uniform(-0.01, 0.01)
        
        # Simulate speed
        if i < 10:
            current_speed += random.uniform(5, 10)
        elif i > 110:
            current_speed -= random.uniform(5, 10)
        else:
            current_speed += random.uniform(-3, 3)
            
        current_speed = max(0, min(100, current_speed))
        
        # Over-speed event simulation around step 60
        if 55 < i < 65:
            current_speed = 115.0 # Speeding!
            
        # Simulate engine RPM and Temp based on speed
        if current_speed == 0:
            current_rpm = 800
            current_temp = max(70, current_temp - 0.5)
        else:
            current_rpm = int(1000 + (current_speed * 15) + random.uniform(-100, 100))
            current_temp = min(95, current_temp + random.uniform(-0.2, 0.5))
            
        # Hot engine event around step 80
        if 75 < i < 85:
            current_temp = 105.0 # Overheating!
            
        # Simulate fuel consumption
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
            
    print("Viaje guardado en la bd con exito!")
    dao.close()

if __name__ == "__main__":
    seed_database()
