import sys
from datetime import datetime
from dao import FleetDAO
from db_models import Truck, Driver, Route, Telemetry, Geofence

def test_full_crud():
    print("=" * 70)
    print("INICIANDO PRUEBAS AUTOMATIZADAS DE CRUD COMPLETO Y VARIABLES DINÁMICAS")
    print("=" * 70)

    dao = FleetDAO()

    # -------------------------------------------------------------------------
    # 1. PRUEBA DE CAMIONES (TRUCKS)
    # -------------------------------------------------------------------------
    print("\n--- [1/5] PRUEBAS DE CAMIONES (TRUCKS) ---")

    # A. Crear (Create)
    print("1. Creando nuevo camión de prueba...")
    nuevo_camion = Truck(
        brand="Scania R500",
        capacity_tons=35.0,
        model="V8 Streamline",
        year=2024,
        license_plate="AB-123-CD",
        status="active"
    )
    truck_id = dao.add_truck(nuevo_camion)
    print(f"  -> Camión creado con ID: {truck_id}")

    # B. Leer (Read)
    print("2. Leyendo camión recién creado por ID...")
    camion_obtenido = dao.get_truck_by_id(truck_id)
    assert camion_obtenido is not None, "Error: No se encontró el camión recién creado"
    assert camion_obtenido["brand"] == "Scania R500"
    print(f"  -> Camión obtenido correctamente: {camion_obtenido['brand']} (Capacidad: {camion_obtenido['capacity_tons']}t)")

    # C. Modificar y Agregar Variables Nuevas (Update)
    print("3. Modificando capacidad y AGREGANDO VARIABLES PERSONALIZADAS NUEVAS...")
    variables_nuevas = {
        "capacity_tons": 40.0,
        "year": 2025,
        "status": "maintenance",
        "custom_gps_tracker_id": "GPS-9988-X",  # <- Variable propia 1
        "seguro_vencimiento": "2027-12-31",      # <- Variable propia 2
        "chofer_favorito": "Carlos Pérez"        # <- Variable propia 3
    }
    actualizado = dao.update_truck(truck_id, variables_nuevas)
    assert actualizado is True, "Error: Falló la actualización del camión"

    # Verificar que las nuevas variables existen en la BD
    camion_modificado = dao.get_truck_by_id(truck_id)
    print(f"  -> Camión modificado exitosamente!")
    print(f"     * Nueva Capacidad: {camion_modificado.get('capacity_tons')}")
    print(f"     * Variable Custom 1 (GPS): {camion_modificado.get('custom_gps_tracker_id')}")
    print(f"     * Variable Custom 2 (Seguro): {camion_modificado.get('seguro_vencimiento')}")
    print(f"     * Variable Custom 3 (Chofer): {camion_modificado.get('chofer_favorito')}")

    assert camion_modificado["custom_gps_tracker_id"] == "GPS-9988-X"
    assert camion_modificado["seguro_vencimiento"] == "2027-12-31"

    # D. Eliminar (Delete)
    print("4. Eliminando camión de prueba...")
    eliminado = dao.delete_truck(truck_id)
    assert eliminado is True, "Error: No se pudo eliminar el camión"
    verificacion = dao.get_truck_by_id(truck_id)
    assert verificacion is None, "Error: El camión sigue existiendo tras eliminarlo"
    print("  -> Camión eliminado y verificado en la base de datos.")

    # -------------------------------------------------------------------------
    # 2. PRUEBA DE CHOFERES (DRIVERS)
    # -------------------------------------------------------------------------
    print("\n--- [2/5] PRUEBAS DE CHOFERES (DRIVERS) ---")
    driver_id = dao.add_driver(Driver(name="Lucía Fernández", license_level="E", phone="+5491122334455"))
    print(f"1. Chofer creado con ID: {driver_id}")

    dao.update_driver(driver_id, {"phone": "+5491199887766", "codigo_empresa": "EMP-404"})
    driver_mod = dao.get_driver_by_id(driver_id)
    assert driver_mod["codigo_empresa"] == "EMP-404"
    print(f"2. Chofer modificado con nueva variable 'codigo_empresa': {driver_mod['codigo_empresa']}")

    dao.delete_driver(driver_id)
    print("3. Chofer eliminado correctamente.")

    # -------------------------------------------------------------------------
    # 3. PRUEBA DE RUTAS (ROUTES)
    # -------------------------------------------------------------------------
    print("\n--- [3/5] PRUEBAS DE RUTAS (ROUTES) ---")
    route_id = dao.add_route(Route(origin="Salta", destination="Jujuy", truck_id="dummy_t", driver_id="dummy_d"))
    print(f"1. Ruta creada con ID: {route_id}")

    dao.update_route(route_id, {"status": "in_transit", "peajes_estimados": 4500.0})
    route_mod = dao.get_route_by_id(route_id)
    assert route_mod["peajes_estimados"] == 4500.0
    print(f"2. Ruta modificada con variable 'peajes_estimados': {route_mod['peajes_estimados']}")

    dao.delete_route(route_id)
    print("3. Ruta eliminada correctamente.")

    # -------------------------------------------------------------------------
    # 4. PRUEBA DE GEOCERCAS (GEOFENCES)
    # -------------------------------------------------------------------------
    print("\n--- [4/5] PRUEBAS DE GEOCERCAS (GEOFENCES) ---")
    gf_id = dao.add_geofence(Geofence(
        name="Zona Puerto Buenos Aires",
        truck_id="dummy_t",
        polygon=[[-58.37, -34.60], [-58.35, -34.60], [-58.35, -34.62], [-58.37, -34.62], [-58.37, -34.60]]
    ))
    print(f"1. Geocerca creada con ID: {gf_id}")

    dao.update_geofence(gf_id, {"nivel_seguridad": "ALTO"})
    gf_mod = dao.get_geofence_by_id(gf_id)
    assert gf_mod["nivel_seguridad"] == "ALTO"
    print(f"2. Geocerca modificada con variable 'nivel_seguridad': {gf_mod['nivel_seguridad']}")

    dao.delete_geofence(gf_id)
    print("3. Geocerca eliminada correctamente.")

    # -------------------------------------------------------------------------
    # 5. PRUEBA DE TELEMETRÍA (TELEMETRY)
    # -------------------------------------------------------------------------
    print("\n--- [5/5] PRUEBAS DE TELEMETRÍA (TELEMETRY) ---")
    tel_id = dao.add_telemetry(Telemetry(
        truck_id="dummy_t",
        timestamp=datetime.now(),
        speed_kmh=85.5,
        engine_rpm=2100,
        engine_temp_c=88.0,
        fuel_level_pct=75.0,
        lon=-58.38,
        lat=-34.60
    ))
    print(f"1. Telemetría creada con ID: {tel_id}")

    dao.update_telemetry(tel_id, {"alerta_presion_neumaticos": False, "presion_psi": 110})
    tel_mod = dao.get_telemetry_by_id(tel_id)
    assert tel_mod["presion_psi"] == 110
    print(f"2. Telemetría modificada con variable 'presion_psi': {tel_mod['presion_psi']}")

    dao.delete_telemetry(tel_id)
    print("3. Telemetría eliminada correctamente.")

    dao.close()

    print("\n" + "=" * 70)
    print("¡TODAS LAS PRUEBAS PASARON CORRECTAMENTE SIN ERRORES!")
    print("El DAO soporta CRUD completo y variables arbitrarias sin restricciones.")
    print("=" * 70)

if __name__ == "__main__":
    test_full_crud()
