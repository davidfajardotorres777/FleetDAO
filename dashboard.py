import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from dao import FleetDAO

st.set_page_config(page_title="FleetDAO Dashboard", layout="wide")

st.title("🚚 FleetDAO - Panel de Control & Telemetría")

@st.cache_resource
def get_dao():
    return FleetDAO()

dao = get_dao()

# Resumen Ejecutivo en la parte superior
summary = dao.get_fleet_summary()
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Camiones Registrados", summary.get("total_trucks", 0))
kpi2.metric("Choferes Activos", summary.get("total_drivers", 0))
kpi3.metric("Rutas Asignadas", summary.get("total_routes", 0))
kpi4.metric("Alertas Detectadas", summary.get("alerts", {}).get("total_alerts", 0), delta_color="inverse")

st.markdown("---")

# Obtener camiones
trucks = dao.get_trucks()
if not trucks:
    st.warning("No hay camiones en la base de datos. Ejecuta `seed.py` primero.")
else:
    truck_ids = [str(t["_id"]) for t in trucks]
    selected_truck = st.sidebar.selectbox("Selecciona un camión", truck_ids)
    
    # Obtener telemetria
    telemetry = dao.get_telemetry(selected_truck)
    
    if not telemetry:
        st.info("No hay telemetría registrada para este camión.")
    else:
        df = pd.DataFrame(telemetry)
        
        if 'location' in df.columns:
            df['lon'] = df['location'].apply(lambda x: x['coordinates'][0] if isinstance(x, dict) and 'coordinates' in x else None)
            df['lat'] = df['location'].apply(lambda x: x['coordinates'][1] if isinstance(x, dict) and 'coordinates' in x else None)
        
        df['speed_kmh'] = pd.to_numeric(df.get('speed_kmh', 0), errors='coerce').fillna(0)
        df['engine_temp_c'] = pd.to_numeric(df.get('engine_temp_c', 0), errors='coerce').fillna(0)
        df['fuel_level_pct'] = pd.to_numeric(df.get('fuel_level_pct', 0), errors='coerce').fillna(0)

        # Estadísticas rápidas del vehículo seleccionado
        st.subheader(f"Estadísticas del Camión {selected_truck}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Velocidad Promedio", f"{df['speed_kmh'].mean():.1f} km/h")
        col2.metric("Temp Máxima Motor", f"{df['engine_temp_c'].max():.1f} °C")
        col3.metric("Combustible Restante", f"{df['fuel_level_pct'].iloc[-1]:.1f} %")
        
        # Mapa interactivo Folium
        st.subheader("Ruta en Tiempo Real")
        
        valid_coords = df.dropna(subset=['lat', 'lon'])
        if not valid_coords.empty:
            start_lat = valid_coords['lat'].iloc[0]
            start_lon = valid_coords['lon'].iloc[0]
            
            m = folium.Map(location=[start_lat, start_lon], zoom_start=7)
            route_coords = list(zip(valid_coords['lat'], valid_coords['lon']))
            
            folium.PolyLine(route_coords, color="blue", weight=3, opacity=0.8).add_to(m)
            
            # Marcador posición final
            last_speed = valid_coords['speed_kmh'].iloc[-1]
            folium.Marker(
                location=route_coords[-1],
                popup=f"Última posición<br>Velocidad: {last_speed} km/h",
                icon=folium.Icon(color="red", icon="truck", prefix="fa")
            ).add_to(m)
            
            st_folium(m, width=1200, height=450)
        else:
            st.warning("No hay coordenadas GPS válidas para mostrar en el mapa.")
        
        # Gráficos de Comportamiento
        st.subheader("Gráficos de Comportamiento")
        st.line_chart(df.set_index('timestamp')[['speed_kmh', 'engine_temp_c']])
