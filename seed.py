import random
from datetime import datetime, timedelta
from dao import FleetDAO

def seed_database():
    dao = FleetDAO()
    
    # Camiones iniciales
    if len(dao.get_trucks()) == 0:
        print("Cargando datos iniciales de la flota...")
        t1 = dao.add_truck(brand="Volvo", capacity_tons=25.5, patente="AA-123-ZZ")
        t2 = dao.add_truck(brand="Mercedes-Benz", capacity_tons=30.0, patente="AB-456-YY")
        t3 = dao.add_truck(brand="Scania", capacity_tons=18.0, patente="AC-789-XX")

        d1 = dao.add_driver(name="Juan Pérez", license_level="A", phone="+54911223344")
        d2 = dao.add_driver(name="María González", license_level="B", phone="+54911556677")

        dao.add_route(origin="Buenos Aires", destination="Córdoba", truck_id=t1, driver_id=d1)
        dao.add_route(origin="Rosario", destination="Mendoza", truck_id=t2, driver_id=d2)
    
    trucks = dao.get_trucks()
    if not trucks:
        return
        
    truck_id = str(trucks[0]["_id"])
    print(f"Generando telemetría de simulación para el camión {truck_id}...")
    
    dao._telemetry.delete_many({"truck_id": truck_id})
    base_time = datetime(2026, 7, 19, 8, 0, 0)
    
    start_lon, start_lat = -58.3816, -34.6037
    end_lon, end_lat = -64.1835, -31.4201
    
    for i in range(60):
        t_time = base_time + timedelta(minutes=i)
        pct = i / 59.0
        lon = round(start_lon + (end_lon - start_lon) * pct + random.uniform(-0.005, 0.005), 5)
        lat = round(start_lat + (end_lat - start_lat) * pct + random.uniform(-0.005, 0.005), 5)
        
        speed = 115.0 if (20 < i < 28) else round(random.uniform(60, 90), 2)
        temp = 102.0 if (35 < i < 42) else round(random.uniform(75, 88), 2)
        fuel = round(max(10.0, 100.0 - (i * 0.5)), 2)
        
        dao.add_telemetry(
            truck_id=truck_id,
            timestamp=t_time,
            speed_kmh=speed,
            engine_rpm=int(1200 + speed * 10),
            engine_temp_c=temp,
            fuel_level_pct=fuel,
            lon=lon,
            lat=lat
        )
            
    print("¡Base de datos poblada exitosamente!")
    dao.close()

if __name__ == "__main__":
    seed_database()
