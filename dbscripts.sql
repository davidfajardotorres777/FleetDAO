-- Esquema Relacional de FleetDAO
-- Lo hice para cumplir con los requisitos de la guia, 
-- aunque el backend posta lo pase a MongoDB para que ande rapido el IoT

CREATE TABLE Trucks (
    truck_id VARCHAR(50) PRIMARY KEY,
    brand VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    year INT NOT NULL,
    capacity_tons DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Drivers (
    driver_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    license_level VARCHAR(10) NOT NULL,
    license_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Routes (
    route_id VARCHAR(50) PRIMARY KEY,
    truck_id VARCHAR(50) NOT NULL,
    driver_id VARCHAR(50) NOT NULL,
    origin VARCHAR(100) NOT NULL,
    destination VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (truck_id) REFERENCES Trucks(truck_id),
    FOREIGN KEY (driver_id) REFERENCES Drivers(driver_id)
);

CREATE TABLE Telemetry (
    id SERIAL PRIMARY KEY,
    truck_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    speed_kmh DECIMAL(5, 2) NOT NULL,
    engine_rpm INT NOT NULL,
    engine_temp_c DECIMAL(5, 2) NOT NULL,
    fuel_level_pct DECIMAL(5, 2) NOT NULL,
    lon DECIMAL(10, 7),
    lat DECIMAL(10, 7),
    FOREIGN KEY (truck_id) REFERENCES Trucks(truck_id)
);

-- Indice para que no se dupliquen las lecturas si se manda dos veces el mismo timestamp
CREATE UNIQUE INDEX idx_telemetry_truck_time ON Telemetry(truck_id, timestamp);
