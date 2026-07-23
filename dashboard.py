import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import requests
from dao import FleetDAO

API_URL = os.getenv("API_URL", "http://localhost:8000")

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
        else:
            df['lon'] = None
            df['lat'] = None
        
        # Estadisticas rapidas
        st.subheader("Estadísticas de Telemetría")
        col1, col2, col3 = st.columns(3)
        col1.metric("Velocidad Promedio", f"{df['speed_kmh'].mean():.1f} km/h")
        col2.metric("Temp Máxima Motor", f"{df['engine_temp_c'].max():.1f} °C")
        col3.metric("Combustible Restante", f"{df['fuel_level_pct'].iloc[-1]:.1f} %")
        
        st.subheader("Predicción de Temperatura del Motor")
        last_telemetry = df.iloc[-1]
        try:
            res = requests.post(
                f"{API_URL}/api/predict_temp", 
                params={"speed_kmh": last_telemetry['speed_kmh'], "engine_rpm": int(last_telemetry['engine_rpm'])}
            )
            if res.status_code == 200:
                data = res.json()
                col_pred1, col_pred2 = st.columns(2)
                col_pred1.metric("Temp Estimada (IA)", f"{data['predicted_temp_c']:.1f} °C")
                if data['alerta_recalentamiento']:
                    col_pred2.error("⚠️ CUIDADO: El motor podría estar por sobrecalentarse.")
                else:
                    col_pred2.success("✅ Temperatura en niveles normales.")
            else:
                st.warning("Servicio predictivo no disponible.")
        except Exception as e:
            st.error(f"El backend API no está corriendo. Inicie uvicorn o use docker-compose.")
        
        st.subheader("Ruta del Vehículo y Geocercas")

        df_con_gps = df.dropna(subset=['lat', 'lon'])
        if df_con_gps.empty:
            st.info("Este camión todavía no tiene lecturas con coordenadas GPS.")
        else:
            start_lat = df_con_gps['lat'].iloc[0]
            start_lon = df_con_gps['lon'].iloc[0]

            m = folium.Map(location=[start_lat, start_lon], zoom_start=7)

            # Dibujar geocercas (Polígonos de autorización)
            geofences = dao.get_geofences()
            for gf in geofences:
                try:
                    coords = gf['geometry']['coordinates'][0] # Primer anillo del polígono
                    # Folium usa [lat, lon], GeoJSON usa [lon, lat]
                    folium_coords = [[lat, lon] for lon, lat in coords]
                    folium.Polygon(
                        locations=folium_coords,
                        color='green',
                        fill=True,
                        fill_color='lightgreen',
                        fill_opacity=0.3,
                        popup=gf.get('name', 'Geocerca Autorizada')
                    ).add_to(m)
                except Exception as e:
                    pass

            # Dibujar ruta
            route_coords = list(zip(df_con_gps['lat'], df_con_gps['lon']))
            if route_coords:
                folium.PolyLine(route_coords, color="blue", weight=3, opacity=0.8).add_to(m)

                # Marcador actual
                folium.Marker(
                    location=route_coords[-1],
                    popup=f"Última posición\\nVelocidad: {df['speed_kmh'].iloc[-1]} km/h",
                    icon=folium.Icon(color="red", icon="truck", prefix='fa')
                ).add_to(m)

            st_folium(m, width=1200, height=500)

        # Graficos
        st.subheader("Gráficos de Comportamiento")
        st.line_chart(df.set_index('timestamp')[['speed_kmh', 'engine_temp_c']])
