import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import requests
from dao import FleetDAO

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="FleetDAO Dashboard", layout="wide")

st.title("🚚 FleetDAO - Panel de Control de Flotas")

@st.cache_resource
def get_dao():
    return FleetDAO()

dao = get_dao()

# Obtener camiones de MongoDB
trucks = dao.get_trucks()
if not trucks:
    st.warning("No hay camiones en la base de datos. Ejecuta seed.py primero.")
else:
    # Mapeo de nombres legibles para el selector
    truck_options = {"🌐 Flota Completa (Todos los Camiones)": "ALL"}
    truck_map = {}
    for t in trucks:
        t_id = str(t["_id"])
        label = f"🚚 {t.get('brand', 'Camión')} ({t.get('capacity_tons', '?')}t) - ID: ...{t_id[-4:]}"
        truck_options[label] = t_id
        truck_map[t_id] = t.get("brand", "Camión")

    selected_label = st.sidebar.selectbox("Selecciona un Vehículo o Vista", list(truck_options.keys()))
    selected_truck_id = truck_options[selected_label]

    if selected_truck_id == "ALL":
        # --- VISTA FLOTA COMPLETA ---
        st.subheader("📊 Resumen de Toda la Flota")
        
        all_telemetry = []
        for t_id in truck_map.keys():
            t_data = dao.get_telemetry(t_id)
            if t_data:
                for record in t_data:
                    record['truck_brand'] = truck_map[t_id]
                all_telemetry.extend(t_data)

        if not all_telemetry:
            st.info("No hay telemetría disponible en la base de datos.")
        else:
            df_all = pd.DataFrame(all_telemetry)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Camiones Activos", len(trucks))
            col2.metric("Lecturas Registradas", len(df_all))
            col3.metric("Velocidad Promedio Flota", f"{df_all['speed_kmh'].mean():.1f} km/h")
            col4.metric("Temp Máxima Flota", f"{df_all['engine_temp_c'].max():.1f} °C")

            st.subheader("🗺️ Mapa Global de la Flota y Geocercas")
            
            # Centro del mapa en Argentina
            m = folium.Map(location=[-33.0, -64.0], zoom_start=5)

            # Dibujar geocercas
            geofences = dao.get_geofences()
            for gf in geofences:
                try:
                    coords = gf['geometry']['coordinates'][0]
                    folium_coords = [[lat, lon] for lon, lat in coords]
                    folium.Polygon(
                        locations=folium_coords,
                        color='green',
                        fill=True,
                        fill_color='lightgreen',
                        fill_opacity=0.25,
                        popup=gf.get('name', 'Geocerca Autorizada')
                    ).add_to(m)
                except Exception:
                    pass

            # Dibujar cada camión en el mapa con diferente color
            colors = ["blue", "red", "purple", "orange", "darkred", "green", "cadetblue", "darkpurple"]
            for idx, (t_id, t_brand) in enumerate(truck_map.items()):
                t_telemetry = [r for r in all_telemetry if r['truck_id'] == t_id]
                if t_telemetry:
                    df_t = pd.DataFrame(t_telemetry)
                    if 'location' in df_t.columns:
                        df_t['lon'] = df_t['location'].apply(lambda x: x['coordinates'][0] if isinstance(x, dict) else None)
                        df_t['lat'] = df_t['location'].apply(lambda x: x['coordinates'][1] if isinstance(x, dict) else None)
                        df_gps = df_t.dropna(subset=['lat', 'lon'])
                        
                        if not df_gps.empty:
                            route_coords = list(zip(df_gps['lat'], df_gps['lon']))
                            color = colors[idx % len(colors)]
                            folium.PolyLine(route_coords, color=color, weight=3, opacity=0.7, tooltip=t_brand).add_to(m)
                            
                            last = df_gps.iloc[-1]
                            folium.Marker(
                                location=[last['lat'], last['lon']],
                                popup=f"<b>{t_brand}</b><br>Velocidad: {last['speed_kmh']} km/h<br>Temp: {last['engine_temp_c']} °C",
                                icon=folium.Icon(color=color, icon="truck", prefix='fa')
                            ).add_to(m)

            st_folium(m, width=1200, height=550)

    else:
        # --- VISTA DE UN CAMIÓN ESPECÍFICO ---
        telemetry = dao.get_telemetry(selected_truck_id)
        
        if not telemetry:
            st.info("No hay telemetría registrada para este camión.")
        else:
            df = pd.DataFrame(telemetry)
            
            if 'location' in df.columns:
                df['lon'] = df['location'].apply(lambda x: x['coordinates'][0] if isinstance(x, dict) else None)
                df['lat'] = df['location'].apply(lambda x: x['coordinates'][1] if isinstance(x, dict) else None)
            else:
                df['lon'] = None
                df['lat'] = None
            
            st.subheader(f"📊 Estadísticas de Telemetría — {truck_map.get(selected_truck_id, 'Camión')}")
            col1, col2, col3 = st.columns(3)
            col1.metric("Velocidad Promedio", f"{df['speed_kmh'].mean():.1f} km/h")
            col2.metric("Temp Máxima Motor", f"{df['engine_temp_c'].max():.1f} °C")
            col3.metric("Combustible Restante", f"{df['fuel_level_pct'].iloc[-1]:.1f} %")
            
            st.subheader("🤖 Predicción de Temperatura del Motor (Machine Learning)")
            last_telemetry = df.iloc[-1]
            try:
                res = requests.post(
                    f"{API_URL}/api/predict_temp", 
                    params={"speed_kmh": last_telemetry['speed_kmh'], "engine_rpm": int(last_telemetry['engine_rpm'])}
                )
                if res.status_code == 200:
                    data = res.json()
                    col_pred1, col_pred2 = st.columns(2)
                    col_pred1.metric("Temp Estimada por IA", f"{data['predicted_temp_c']:.1f} °C")
                    if data['alerta_recalentamiento']:
                        col_pred2.error("⚠️ ALERTA CRÍTICA: El motor podría estar por sobrecalentarse.")
                    else:
                        col_pred2.success("✅ Temperatura en niveles normales de operación.")
                else:
                    st.warning("Servicio predictivo no disponible.")
            except Exception:
                st.error("El backend API no está corriendo en el puerto 8000.")
            
            st.subheader("🗺️ Ruta del Vehículo y Geocercas")

            df_con_gps = df.dropna(subset=['lat', 'lon'])
            if df_con_gps.empty:
                st.info("Este camión todavía no tiene lecturas con coordenadas GPS.")
            else:
                start_lat = df_con_gps['lat'].iloc[0]
                start_lon = df_con_gps['lon'].iloc[0]

                m = folium.Map(location=[start_lat, start_lon], zoom_start=7)

                # Dibujar geocercas
                geofences = dao.get_geofences()
                for gf in geofences:
                    try:
                        coords = gf['geometry']['coordinates'][0]
                        folium_coords = [[lat, lon] for lon, lat in coords]
                        folium.Polygon(
                            locations=folium_coords,
                            color='green',
                            fill=True,
                            fill_color='lightgreen',
                            fill_opacity=0.3,
                            popup=gf.get('name', 'Geocerca Autorizada')
                        ).add_to(m)
                    except Exception:
                        pass

                # Dibujar ruta
                route_coords = list(zip(df_con_gps['lat'], df_con_gps['lon']))
                if route_coords:
                    folium.PolyLine(route_coords, color="blue", weight=4, opacity=0.85).add_to(m)

                    # Marcador actual
                    last_row = df_con_gps.iloc[-1]
                    folium.Marker(
                        location=[last_row['lat'], last_row['lon']],
                        popup=f"Última posición<br>Velocidad: {last_row['speed_kmh']} km/h<br>Temp: {last_row['engine_temp_c']} °C",
                        icon=folium.Icon(color="red", icon="truck", prefix='fa')
                    ).add_to(m)

                st_folium(m, width=1200, height=500)

            # Gráficos
            st.subheader("📉 Gráficos de Comportamiento Temporal")
            st.line_chart(df.set_index('timestamp')[['speed_kmh', 'engine_temp_c']])
