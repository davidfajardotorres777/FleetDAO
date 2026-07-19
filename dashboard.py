import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from dao import FleetDAO

st.set_page_config(page_title="FleetDAO Dashboard", layout="wide")

st.title("🚚 FleetDAO - Panel de Control")

@st.cache_resource
def get_dao():
    return FleetDAO()

dao = get_dao()

# Obtener camiones
trucks = dao.get_trucks()
if not trucks:
    st.warning("No hay camiones en la base de datos. Ejecuta seed.py primero.")
else:
    truck_ids = [str(t["_id"]) for t in trucks]
    selected_truck = st.sidebar.selectbox("Selecciona un camión", truck_ids)
    
    # Obtener telemetria
    telemetry = dao.get_telemetry(selected_truck)
    
    if not telemetry:
        st.info("No hay telemetría para este camión.")
    else:
        df = pd.DataFrame(telemetry)
        
        if 'location' in df.columns:
            df['lon'] = df['location'].apply(lambda x: x['coordinates'][0] if isinstance(x, dict) else None)
            df['lat'] = df['location'].apply(lambda x: x['coordinates'][1] if isinstance(x, dict) else None)
        
        # Estadisticas rapidas
        st.subheader("Estadísticas de Telemetría")
        col1, col2, col3 = st.columns(3)
        col1.metric("Velocidad Promedio", f"{df['speed_kmh'].mean():.1f} km/h")
        col2.metric("Temp Máxima Motor", f"{df['engine_temp_c'].max():.1f} °C")
        col3.metric("Combustible Restante", f"{df['fuel_level_pct'].iloc[-1]:.1f} %")
        
        # Mapa
        st.subheader("Ruta del Vehículo")
        
        start_lat = df['lat'].iloc[0]
        start_lon = df['lon'].iloc[0]
        
        m = folium.Map(location=[start_lat, start_lon], zoom_start=7)
        
        # Dibujar ruta
        route_coords = list(zip(df['lat'].dropna(), df['lon'].dropna()))
        if route_coords:
            folium.PolyLine(route_coords, color="blue", weight=2.5, opacity=1).add_to(m)
            
            # Marcador actual
            folium.Marker(
                location=route_coords[-1],
                popup=f"Última posición\\nVelocidad: {df['speed_kmh'].iloc[-1]} km/h",
                icon=folium.Icon(color="red", icon="info-sign")
            ).add_to(m)
        
        st_folium(m, width=1200, height=500)
        
        # Graficos
        st.subheader("Gráficos de Comportamiento")
        st.line_chart(df.set_index('timestamp')[['speed_kmh', 'engine_temp_c']])
