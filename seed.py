import random
from datetime import datetime, timedelta
from pymongo.errors import DuplicateKeyError

from dao import FleetDAO
from db_models.trucks import Truck
from db_models.drivers import Driver
from db_models.routes import Route
from db_models.telemetry import Telemetry
from db_models.geofence import Geofence

def seed_database():
    print("Iniciando carga completa de datos de prueba para la flota...\n")
    dao = FleetDAO()
    
    # Limpiar colecciones anteriores para garantizar datos limpios
    print("Limpiando colecciones anteriores en MongoDB...")
    dao._db["trucks"].delete_many({})
    dao._db["drivers"].delete_many({})
    dao._db["routes"].delete_many({})
    dao._db["telemetry"].delete_many({})
    dao._db["geofences"].delete_many({})
    print("  --OK-- Base de datos limpiada exitosamente.\n")

    # 1. Insertar Camiones
    print("Insertando camiones...")
    truck_data = [
        {"brand": "Volvo FH16", "capacity_tons": 25.5},
        {"brand": "Mercedes-Benz Actros", "capacity_tons": 30.0},
        {"brand": "Scania R450", "capacity_tons": 18.0},
        {"brand": "Iveco Stralis", "capacity_tons": 22.0},
        {"brand": "Ford Cargo 1723", "capacity_tons": 17.5},
        {"brand": "MAN TGX 26.480", "capacity_tons": 28.0},
        {"brand": "Renault T High", "capacity_tons": 24.0},
        {"brand": "Volkswagen Constellation", "capacity_tons": 19.0}
    ]
    truck_ids = []
    for t in truck_data:
        t_id = dao.add_truck(Truck(brand=t["brand"], capacity_tons=t["capacity_tons"]))
        truck_ids.append(t_id)
        print(f"  --OK-- Camión: {t['brand']} (Capacidad: {t['capacity_tons']}t)")

    print()

    # 2. Insertar Choferes
    print("Insertando choferes...")
    driver_data = [
        {"name": "Juan Perez", "license_level": "A"},
        {"name": "Maria Gonzalez", "license_level": "B"},
        {"name": "Carlos Rodriguez", "license_level": "A"},
        {"name": "Ana Martinez", "license_level": "B"},
        {"name": "Roberto Fernandez", "license_level": "A"},
        {"name": "Laura Benitez", "license_level": "B"},
        {"name": "Diego Gomez", "license_level": "A"},
        {"name": "Sofia Lopez", "license_level": "B"}
    ]
    driver_ids = []
    for d in driver_data:
        d_id = dao.add_driver(Driver(name=d["name"], license_level=d["license_level"]))
        driver_ids.append(d_id)
        print(f"  --OK-- Chofer: {d['name']} (Licencia {d['license_level']})")

    print()

    # 3. Insertar Rutas Logísticas
    print("Insertando rutas logísticas...")
    route_configs = [
        {"origin": "Buenos Aires", "destination": "Cordoba", "start": (-58.3816, -34.6037), "end": (-64.1835, -31.4201)},
        {"origin": "Rosario", "destination": "Mendoza", "start": (-60.6393, -32.9468), "end": (-68.8272, -32.8895)},
        {"origin": "Cordoba", "destination": "Tucuman", "start": (-64.1835, -31.4201), "end": (-65.2226, -26.8241)},
        {"origin": "Mendoza", "destination": "La Rioja (Chilecito)", "start": (-68.8272, -32.8895), "end": (-67.4988, -29.1633)},
        {"origin": "Salta", "destination": "Jujuy", "start": (-65.4117, -24.7859), "end": (-65.2971, -24.1858)},
        {"origin": "Buenos Aires", "destination": "Mar del Plata", "start": (-58.3816, -34.6037), "end": (-57.5575, -38.0055)},
        {"origin": "Neuquen", "destination": "Bariloche", "start": (-68.0591, -38.9516), "end": (-71.3082, -41.1335)},
        {"origin": "Santa Fe", "destination": "Corrientes", "start": (-60.7012, -31.6333), "end": (-58.8341, -27.4806)}
    ]

    for idx, cfg in enumerate(route_configs):
        dao.add_route(Route(
            origin=cfg["origin"],
            destination=cfg["destination"],
            truck_id=truck_ids[idx],
            driver_id=driver_ids[idx]
        ))
        print(f"  --OK-- Ruta: {cfg['origin']} -> {cfg['destination']} (Asignada a {driver_data[idx]['name']})")

    print()

    # 4. Insertar Geocercas (Polígonos de autorización en GeoJSON)
    print("Insertando geocercas espaciales...")
    geofence_data = [
        {
            "name": "Geocerca Zona Centro (BA - Cba)",
            "truck_id": truck_ids[0],
            "polygon": [
                [-58.0, -34.0], [-58.0, -35.5], [-65.0, -32.5], [-65.0, -30.5], [-58.0, -34.0]
            ]
        },
        {
            "name": "Geocerca Zona Cuyo (Mendoza - La Rioja)",
            "truck_id": truck_ids[3],
            "polygon": [
                [-69.5, -33.5], [-66.5, -33.5], [-66.5, -28.5], [-69.5, -28.5], [-69.5, -33.5]
            ]
        },
        {
            "name": "Geocerca Zona Norte (Tucumán - Salta)",
            "truck_id": truck_ids[4],
            "polygon": [
                [-66.5, -27.5], [-64.0, -27.5], [-64.0, -23.5], [-66.5, -23.5], [-66.5, -27.5]
            ]
        },
        {
            "name": "Geocerca Zona Patagonia (Neuquén - Bariloche)",
            "truck_id": truck_ids[6],
            "polygon": [
                [-72.0, -42.0], [-67.5, -42.0], [-67.5, -38.0], [-72.0, -38.0], [-72.0, -42.0]
            ]
        }
    ]

    for gf in geofence_data:
        dao.add_geofence(Geofence(name=gf["name"], truck_id=gf["truck_id"], polygon=gf["polygon"]))
        print(f"  --OK-- Geocerca espacial creada: {gf['name']}")

    print()

    # 5. Generar Telemetría para TODOS los 8 camiones
    print("Generando series temporales de telemetría para TODOS los camiones de la flota...")
    base_time = datetime.utcnow() - timedelta(hours=3)
    total_steps = 100

    for idx, t_id in enumerate(truck_ids):
        route_cfg = route_configs[idx]
        start_lon, start_lat = route_cfg["start"]
        end_lon, end_lat = route_cfg["end"]

        current_speed = 0.0
        current_fuel = round(random.uniform(70.0, 98.0), 2)
        current_temp = round(random.uniform(72.0, 80.0), 2)

        # Hacer que algunos camiones tengan picos de aceleración / calentamiento para probar ML
        overheat_start = 45 if idx % 2 == 0 else 999
        overheat_end = 60 if idx % 2 == 0 else 999

        for step in range(total_steps):
            current_time = base_time + timedelta(minutes=step)
            progress = step / float(total_steps - 1)

            # Coordenadas progresivas sobre la ruta con variación GPS realista
            current_lon = start_lon + (end_lon - start_lon) * progress + random.uniform(-0.005, 0.005)
            current_lat = start_lat + (end_lat - start_lat) * progress + random.uniform(-0.005, 0.005)

            # Velocidad y aceleración
            if step < 5:
                current_speed += random.uniform(8.0, 15.0)
            elif step > 90:
                current_speed -= random.uniform(5.0, 10.0)
            else:
                current_speed += random.uniform(-4.0, 4.0)

            current_speed = max(0.0, min(110.0, current_speed))

            # Tramo con exceso de velocidad si aplica
            if overheat_start <= step <= overheat_end:
                current_speed = random.uniform(112.0, 125.0)
                current_temp = min(115.0, current_temp + random.uniform(1.0, 2.5))
            else:
                if current_speed > 0:
                    current_temp = max(75.0, min(95.0, current_temp + random.uniform(-0.3, 0.6)))
                else:
                    current_temp = max(70.0, current_temp - 0.5)

            current_rpm = int(900 + (current_speed * 18) + random.uniform(-80, 80)) if current_speed > 0 else 800
            current_fuel = max(5.0, current_fuel - random.uniform(0.04, 0.12))

            telemetry = Telemetry(
                truck_id=t_id,
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

        print(f"  --OK-- Camión [{truck_data[idx]['brand']}] -> {total_steps} lecturas de telemetría inyectadas.")

    print("\n--OK-- ¡Poblado completo de la flota realizado con éxito!")
    dao.close()

if __name__ == "__main__":
    seed_database()
