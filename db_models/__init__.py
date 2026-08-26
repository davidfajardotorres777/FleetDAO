from .trucks import Truck, TruckUpdate
from .drivers import Driver, DriverUpdate
from .routes import Route, RouteUpdate
from .telemetry import Telemetry, TelemetryUpdate
from .geofence import Geofence, GeofenceUpdate
from .dao import FleetDAO

__all__ = [
    "FleetDAO",
    "Truck", "TruckUpdate",
    "Driver", "DriverUpdate",
    "Route", "RouteUpdate",
    "Telemetry", "TelemetryUpdate",
    "Geofence", "GeofenceUpdate",
]
