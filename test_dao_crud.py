from datetime import datetime
from dao import FleetDAO

def test_full_crud():
    print("=" * 60)
    print("EJECUTANDO PRUEBAS COMPLETA DEL DAO (STANDALONE)")
    print("=" * 60)

    with FleetDAO() as dao:
        # 1. Trucks CRUD & Variables Dinámicas
        print("1. Probando Camiones (Trucks) & Variables Dinámicas...")
        t_id = dao.add_truck(brand="Scania R500", capacity_tons=35.0, patente="AB-123-CD")
        assert dao.get_truck_by_id(t_id)["brand"] == "Scania R500"
        
        dao.add_variable_to_truck(t_id, "gps_id", "GPS-9988-X")
        dao.update_truck(t_id, capacity_tons=40.0, chofer_favorito="Carlos Pérez")
        
        truck = dao.get_truck_by_id(t_id)
        assert truck["gps_id"] == "GPS-9988-X"
        assert truck["chofer_favorito"] == "Carlos Pérez"
        assert dao.delete_truck(t_id) is True

        # 2. Drivers CRUD
        print("2. Probando Choferes (Drivers)...")
        d_id = dao.add_driver(name="Lucía Fernández", license_level="E")
        assert dao.update_driver(d_id, codigo="EMP-404") is True
        assert dao.delete_driver(d_id) is True

        # 3. Routes CRUD
        print("3. Probando Rutas (Routes)...")
        r_id = dao.add_route(origin="Salta", destination="Jujuy")
        assert dao.update_route(r_id, status="en_transito") is True
        assert dao.delete_route(r_id) is True

        # 4. Geofences CRUD
        print("4. Probando Geocercas (Geofences)...")
        g_id = dao.add_geofence(name="Puerto BA", polygon=[[-58.37, -34.60], [-58.35, -34.60], [-58.35, -34.62], [-58.37, -34.60]])
        assert dao.update_geofence(g_id, nivel="ALTO") is True
        assert dao.delete_geofence(g_id) is True

        # 5. Telemetry CRUD
        print("5. Probando Telemetría (Telemetry)...")
        tel_id = dao.add_telemetry(truck_id="t_test", speed_kmh=85.5, engine_temp_c=88.0, lon=-58.38, lat=-34.60)
        assert dao.update_telemetry(tel_id, presion_psi=110) is True
        assert dao.delete_telemetry(tel_id) is True

        # 6. Analytics & Alerts
        print("6. Probando Analítica y Búsqueda...")
        summary = dao.get_fleet_summary()
        assert "total_trucks" in summary
        alerts = dao.get_recent_alerts(limit=5)
        assert isinstance(alerts, list)

    print("=" * 60)
    print("¡TODAS LAS PRUEBAS COMPLETADAS CON 100% DE ÉXITO!")
    print("=" * 60)

if __name__ == "__main__":
    test_full_crud()
