import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from dao import FleetDAO

# Configuración de página
st.set_page_config(
    page_title="FleetDAO - Control de Flota & Telemetría",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# DAO
@st.cache_resource
def get_dao():
    return FleetDAO()

dao = get_dao()

# Encabezado Principal
st.title("🚚 FleetDAO - Panel de Control & Telemetría IoT")
st.caption("Sistema de gestión de flotas con DAO dinámico sobre MongoDB")

# KPI Summary Cards
summary = dao.get_fleet_summary()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Camiones Registrados", summary.get("total_trucks", 0))
c2.metric("Choferes Activos", summary.get("total_drivers", 0))
c3.metric("Rutas Asignadas", summary.get("total_routes", 0))
c4.metric("Alertas Detectadas", summary.get("alerts", {}).get("total_alerts", 0), delta_color="inverse")

st.markdown("---")

# PESTAÑAS DEL DASHBOARD
tab_monitoring, tab_alerts, tab_variables = st.tabs([
    "🚚 Monitoreo & Mapa GPS", 
    "🚨 Centro de Alertas", 
    "🛠️ Gestor Dinámico de Variables (DAO)"
])

# -----------------------------------------------------------------------------
# PESTAÑA 1: MONITOREO & MAPA GPS
# -----------------------------------------------------------------------------
with tab_monitoring:
    trucks = dao.get_trucks()
    if not trucks:
        st.warning("No hay camiones registrados en MongoDB. Ejecuta `seed.py` para cargar datos de prueba.")
    else:
        # Selector de camión en la barra lateral o superior
        truck_options = {f"{t.get('brand', 'Camión')} ({t.get('patente', t.get('_id'))})": str(t['_id']) for t in trucks}
        selected_label = st.selectbox("Selecciona un vehículo para inspeccionar su telemetría:", list(truck_options.keys()))
        selected_truck_id = truck_options[selected_label]

        telemetry = dao.get_telemetry(selected_truck_id)
        if not telemetry:
            st.info("No se registraron lecturas de telemetría para este vehículo.")
        else:
            df = pd.DataFrame(telemetry)
            df['speed_kmh'] = pd.to_numeric(df.get('speed_kmh', 0), errors='coerce').fillna(0)
            df['engine_temp_c'] = pd.to_numeric(df.get('engine_temp_c', 0), errors='coerce').fillna(0)
            df['fuel_level_pct'] = pd.to_numeric(df.get('fuel_level_pct', 0), errors='coerce').fillna(0)

            if 'location' in df.columns:
                df['lon'] = df['location'].apply(lambda x: x['coordinates'][0] if isinstance(x, dict) and 'coordinates' in x else None)
                df['lat'] = df['location'].apply(lambda x: x['coordinates'][1] if isinstance(x, dict) and 'coordinates' in x else None)

            # Métricas rápidas del camión seleccionado
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Velocidad Promedio", f"{df['speed_kmh'].mean():.1f} km/h")
            m2.metric("Velocidad Máxima", f"{df['speed_kmh'].max():.1f} km/h")
            m3.metric("Temp Máxima Motor", f"{df['engine_temp_c'].max():.1f} °C")
            m4.metric("Combustible Actual", f"{df['fuel_level_pct'].iloc[-1]:.1f} %")

            # Mapa Folium
            st.subheader("Ruta en Tiempo Real (GPS)")
            valid_coords = df.dropna(subset=['lat', 'lon'])
            if not valid_coords.empty:
                start_lat, start_lon = valid_coords['lat'].iloc[0], valid_coords['lon'].iloc[0]
                m = folium.Map(location=[start_lat, start_lon], zoom_start=7)
                route = list(zip(valid_coords['lat'], valid_coords['lon']))

                folium.PolyLine(route, color="blue", weight=3.5, opacity=0.85).add_to(m)

                # Inicio y Fin
                folium.Marker(route[0], popup="Inicio del viaje", icon=folium.Icon(color="green", icon="play")).add_to(m)
                folium.Marker(
                    route[-1], 
                    popup=f"Posición Actual<br>Velocidad: {valid_coords['speed_kmh'].iloc[-1]} km/h", 
                    icon=folium.Icon(color="red", icon="truck", prefix="fa")
                ).add_to(m)

                st_folium(m, width=1200, height=420)

            # Gráficos de Línea de Velocidad y Temperatura
            st.subheader("Historial de Velocidad y Temperatura del Motor")
            if 'timestamp' in df.columns:
                chart_df = df.set_index('timestamp')[['speed_kmh', 'engine_temp_c']]
                st.line_chart(chart_df)

# -----------------------------------------------------------------------------
# PESTAÑA 2: CENTRO DE ALERTAS
# -----------------------------------------------------------------------------
with tab_alerts:
    st.subheader("🚨 Diagnósticos y Anomalías Detectadas en Vivo")
    alerts = dao.get_recent_alerts(limit=25)
    if not alerts:
        st.success("✔ Toda la flota opera normalmente. No se detectaron anomalías.")
    else:
        df_alerts = pd.DataFrame(alerts)
        st.dataframe(df_alerts[['_id', 'truck_id', 'timestamp', 'speed_kmh', 'engine_temp_c', 'fuel_level_pct']], use_container_width=True)

# -----------------------------------------------------------------------------
# PESTAÑA 3: GESTOR DINÁMICO DE VARIABLES (DEMO DEL DAO)
# -----------------------------------------------------------------------------
with tab_variables:
    st.subheader("🛠️ Gestor de Variables Dinámicas del DAO (Demostración)")
    st.info("Agrega o modifica cualquier variable personalizada en MongoDB en tiempo real sin alterar el esquema.")

    trucks = dao.get_trucks()
    if trucks:
        truck_dict = {f"{t.get('brand', 'Camión')} ({t.get('_id')})": str(t['_id']) for t in trucks}
        sel_name = st.selectbox("Selecciona un camión para administrar sus variables:", list(truck_dict.keys()), key="var_truck_sel")
        target_id = truck_dict[sel_name]

        current_truck = dao.get_truck_by_id(target_id)
        st.markdown("**Documento actual en MongoDB:**")
        st.json(current_truck)

        st.markdown("---")
        st.markdown("#### ➕ Agregar o Modificar Variable Personalizada")
        col_name, col_val = st.columns(2)
        var_name = col_name.text_input("Nombre de la Variable (ej: seguro_vencimiento, gps_id, chofer_asignado):")
        var_val = col_val.text_input("Valor de la Variable (ej: 2027-12-31, GPS-9988-X, Carlos Pérez):")

        if st.button("Guardar Variable en MongoDB"):
            if var_name and var_val:
                dao.add_variable_to_truck(target_id, var_name, var_val)
                st.success(f"✔ Variable `{var_name}` = `{var_val}` guardada correctamente en MongoDB!")
                st.rerun()
            else:
                st.error("Por favor completa el nombre y el valor de la variable.")

        st.markdown("---")
        st.markdown("#### ❌ Eliminar Variable Personalizada")
        del_name = st.text_input("Nombre de la Variable a Eliminar:")
        if st.button("Eliminar Variable de MongoDB"):
            if del_name:
                dao.delete_variable_from_truck(target_id, del_name)
                st.success(f"✔ Variable `{del_name}` eliminada de MongoDB!")
                st.rerun()
