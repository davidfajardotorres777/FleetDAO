import nbformat as nbf

nb = nbf.v4.new_notebook()

nb['cells'] = [
    nbf.v4.new_markdown_cell("""# FleetDAO — Notebook de Consultas y Operaciones DAO
### Proyecto Integrador · Bases de Datos II (2026)
**Autor:** Alesandro David Fajardo Torres

Este cuaderno demuestra el funcionamiento integral del **Patrón Data Access Object (DAO)** mediante la clase `FleetDAO`, la cual abstrae y centraliza las consultas a **MongoDB**, **Redis** y **MinIO**.

---
## 1. Conexión e Inicialización de la Capa DAO"""),
    
    nbf.v4.new_code_cell("""import pandas as pd
import matplotlib.pyplot as plt
from dao import FleetDAO

# Instanciación de la capa DAO
dao = FleetDAO()
print("✅ Conexión exitosa a MongoDB, Redis y MinIO a través de FleetDAO.")"""),

    nbf.v4.new_markdown_cell("""---
## 2. Gestión de Entidades Maestras (Trucks & Drivers)
Consultamos los camiones y choferes almacenados en la base de datos y los estructuramos en DataFrames de Pandas."""),

    nbf.v4.new_code_cell("""# 2.1 Obtención de Camiones
trucks = dao.get_trucks()
df_trucks = pd.DataFrame(trucks)

if not df_trucks.empty:
    df_trucks['_id'] = df_trucks['_id'].astype(str)
    print(f"Total camiones registrados: {len(df_trucks)}")
    display(df_trucks[['_id', 'brand', 'capacity_tons']])
else:
    print("No hay camiones en la base de datos.")"""),

    nbf.v4.new_code_cell("""# 2.2 Visualización: Capacidad de Carga por Marca
if not df_trucks.empty:
    plt.figure(figsize=(10, 4))
    plt.bar(df_trucks['brand'], df_trucks['capacity_tons'], color='#3498db', edgecolor='black')
    plt.title('Capacidad de Carga por Vehículo (Toneladas)')
    plt.xlabel('Marca y Modelo')
    plt.ylabel('Capacidad (t)')
    plt.xticks(rotation=30, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.show()"""),

    nbf.v4.new_code_cell("""# 2.3 Obtención de Conductores y Niveles de Licencia
drivers = dao.get_drivers()
df_drivers = pd.DataFrame(drivers)

if not df_drivers.empty:
    df_drivers['_id'] = df_drivers['_id'].astype(str)
    display(df_drivers[['_id', 'name', 'license_level']])
    
    # Gráfico de distribución de licencias
    plt.figure(figsize=(5, 4))
    df_drivers['license_level'].value_counts().plot(
        kind='pie', autopct='%1.1f%%', startangle=90,
        colors=['#2ecc71', '#e74c3c', '#f1c40f']
    )
    plt.title('Distribución por Tipo de Licencia')
    plt.ylabel('')
    plt.show()"""),

    nbf.v4.new_markdown_cell("""---
## 3. Consultas de Rutas Logísticas
Analizamos las asignaciones de rutas entre orígenes, destinos, camiones y choferes."""),

    nbf.v4.new_code_cell("""routes = dao.get_routes()
df_routes = pd.DataFrame(routes)

if not df_routes.empty:
    df_routes['_id'] = df_routes['_id'].astype(str)
    print(f"Total rutas logísticas activas: {len(df_routes)}")
    display(df_routes[['_id', 'origin', 'destination', 'truck_id', 'driver_id']])
else:
    print("No hay rutas registradas.")"""),

    nbf.v4.new_markdown_cell("""---
## 4. Agregaciones de Telemetría (Aggregation Pipelines en MongoDB)
Usamos el método `get_truck_statistics()` del DAO que ejecuta un pipeline `$group` en MongoDB."""),

    nbf.v4.new_code_cell("""if not df_trucks.empty:
    first_truck_id = df_trucks.iloc[0]['_id']
    first_truck_name = df_trucks.iloc[0]['brand']
    
    stats = dao.get_truck_statistics(first_truck_id)
    print(f"📊 Estadísticas calculadas en MongoDB para {first_truck_name} (ID: {first_truck_id}):")
    print(f"  • Total lecturas de telemetría: {stats.get('total_lecturas')}")
    print(f"  • Velocidad Promedio: {stats.get('velocidad_promedio', 0):.2f} km/h")
    print(f"  • Temperatura Máxima del Motor: {stats.get('temp_maxima', 0):.2f} °C")
    print(f"  • Combustible Promedio: {stats.get('combustible_promedio', 0):.2f} %")"""),

    nbf.v4.new_markdown_cell("""---
## 5. Consultas Geoespaciales (Índices `2dsphere` y Geocercas)
Consultamos las geocercas registradas y ejecutamos búsquedas por proximidad ($near)."""),

    nbf.v4.new_code_cell("""geofences = dao.get_geofences()
print(f"🗺️ Total geocercas espaciales encontradas: {len(geofences)}")
for gf in geofences:
    print(f"  • Geocerca: '{gf.get('name')}' (Camión ID: {gf.get('truck_id')})")"""),

    nbf.v4.new_markdown_cell("""---
## 6. Demostración de Caché en Tiempo Real (Redis)
Consultamos la última posición en caché O(1) utilizando Redis mediante `get_latest_telemetry_cache()`."""),

    nbf.v4.new_code_cell("""if not df_trucks.empty:
    cache_data = dao.get_latest_telemetry_cache(truck_id=first_truck_id)
    if cache_data:
        print(f"⚡ Lectura desde Redis en O(1) para camión {first_truck_id}:")
        print(cache_data)
    else:
        print(f"No hay caché en Redis para el camión {first_truck_id} (ejecute simulator.py si desea ver lecturas en vivo).")"""),

    nbf.v4.new_markdown_cell("""---
## 7. Cierre de Conexiones
Liberamos los recursos de conexión con MongoDB y Redis."""),

    nbf.v4.new_code_cell("""dao.close()
print("🔒 Conexiones cerradas de manera segura.")""")
]

with open('dao_consultas.ipynb', 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print("Notebook dao_consultas.ipynb actualizado exitosamente.")
