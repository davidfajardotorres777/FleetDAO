import pytest
from dao import FleetDAO
from db_models.trucks import Truck
from db_models.drivers import Driver

@pytest.fixture
def dao():
    # Conectamos a BD
    d = FleetDAO()
    # Limpiar estado previo
    d._trucks.delete_many({"brand": "TestPytest"})
    d._drivers.delete_many({"name": "DriverPytest"})
    yield d
    # Limpiar despues
    d._trucks.delete_many({"brand": "TestPytest"})
    d._drivers.delete_many({"name": "DriverPytest"})
    d.close()

def test_truck_crud(dao):
    truck = Truck(brand="TestPytest", capacity_tons=15.0)
    truck_id = dao.add_truck(truck)
    assert truck_id is not None
    
    trucks = dao.get_trucks(brand="TestPytest")
    assert len(trucks) > 0
    assert trucks[0]["brand"] == "TestPytest"

def test_driver_crud(dao):
    driver = Driver(name="DriverPytest", license_level="A")
    driver_id = dao.add_driver(driver)
    assert driver_id is not None
    
    drivers = dao.get_drivers(name="DriverPytest")
    assert len(drivers) > 0
    assert drivers[0]["name"] == "DriverPytest"
