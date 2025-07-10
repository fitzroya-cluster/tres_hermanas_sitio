# dashboard_final_corregido_v2.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from plotly.subplots import make_subplots
import numpy as np
import metpy.calc as mpcalc
from metpy.units import units
import matplotlib.pyplot as plt
from windrose import WindroseAxes
import io
import os
import base64

# --- CONFIGURACIÓN DE PÁGINA Y FUNCIONES AUXILIARES ---
st.set_page_config(page_title="Visualizador de datos: Estación Tres Hermanas", layout="wide", initial_sidebar_state="expanded")

@st.cache_data
def get_image_as_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None

@st.cache_data
def load_data():
    try:
        data = pd.read_csv("base_de_datos_3_hermanas.csv.gz", compression="gzip", parse_dates=["TIMESTAMP"])
        data.set_index("TIMESTAMP", inplace=True)
        return data
    except FileNotFoundError:
        st.error("Error: El archivo 'base_de_datos_3_hermanas.csv.gz' no se encontró.")
        return None

# --- CARGA Y PREPARACIÓN DE DATOS ---
data = load_data()
if data is None: st.stop()

if 'DT_Avg' in data.columns:
    data['SnowDepth_calc_cm'] = data['DT_Avg'].max() - data['DT_Avg']
    data['SnowDepth_calc_cm'] = data['SnowDepth_calc_cm'].clip(lower=0)
    snow_depth_available = True
else: snow_depth_available = False

if 'WS_ms_Avg' in data.columns:
    data['WS_kmh_Avg'] = data['WS_ms_Avg'] * 3.6
    wind_speed_available = True
else: wind_speed_available = False

# --- DICCIONARIOS DE CONFIGURACIÓN ---
variables_disponibles = {
    "Temperatura (°C)": "AirTC_Avg", "Humedad (%)": "RH_Avg",
    "Velocidad del viento (km/h)": "WS_kmh_Avg", "Dirección del viento (°)": "WindDir_Avg",
    "Presión atmosférica (hPa)": "BP_mbar_Avg", "Radiación solar (W/m²)": "incomingSW_Avg",
    "Albedo (%)": "albedo_Avg", "Precipitación (mm)": "Rain_mm_Tot",
    "Punto de rocío (°C)": "PtoRocio_Avg", "Temperatura del suelo a 50 cm (°C)": "T107_50cm_Avg",
    "Temperatura del suelo a 10 cm (°C)": "T107_10cm_Avg", "Profundidad de nieve (cm)": "SnowDepth_calc_cm",
    "Rosa de los vientos": "Wind_Rose"
}

# --- DEFINICIÓN DE FUNCIONES ---
def resample_data(df, freq):
    df_copy = df.copy()
    if "WS_ms_Avg" in df_copy.columns and "WindDir_Avg" in df_copy.columns:
        ws, wd = df_copy["WS_ms_Avg"].values * units("m/s"), df_copy["WindDir_Avg"].values * units.deg
        u, v = mpcalc.wind_components(ws, wd)
        df_copy["Wind_u"], df_copy["Wind_v"] = u.magnitude, v.magnitude

    agg_rules = {col: 'mean' for col in df_copy.columns if col not in ['Wind_u', 'Wind_v']}
    if 'Rain_mm_Tot' in df_copy.columns: agg_rules['Rain_mm_Tot'] = 'sum'
    if 'Wind_u' in df_copy.columns: agg_rules['Wind_u'] = 'mean'
    if 'Wind_v' in df_copy.columns: agg_rules['Wind_v'] = 'mean'
    
    aggregated = df_copy.resample(freq).agg(agg_rules).dropna(how='all')

    if "Wind_u" in aggregated.columns and "Wind_v" in aggregated.columns:
        u_avg, v_avg = aggregated["Wind_u"].values * units("m/s"), aggregated["Wind_v"].values * units("m/s")
        aggregated["WindDir_Avg"] = mpcalc.wind_direction(u_avg, v_avg).magnitude
        ws_ms_avg = mpcalc.wind_speed(u_avg, v_avg).magnitude
        aggregated["WS_ms_Avg"] = ws_ms_avg
        aggregated["WS_kmh_Avg"] = ws_ms_avg * 3.6
    return aggregated

def create_wind_rose(df):
    df_plot = df.dropna(subset=["WindDir_Avg", "WS_kmh_Avg"]).copy()
    if df_plot.empty or len(df_plot) < 2: return None
    wind_speed_bins = np.arange(0, 31, 3) 
    fig = plt.figure(figsize=(8, 8))
    ax = WindroseAxes.from_ax(fig=fig)
    ax.bar(df_plot["WindDir_Avg"], df_plot["WS_kmh_Avg"], bins=wind_speed_bins, normed=True, opening=0.8, edgecolor='white', cmap=plt.cm.jet)
    ax.set_legend(title="Velocidad (km/h)")
    ax.set_title("Frecuencia de viento por dirección (%)", pad=25)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()

def display_stats(df, header, variables_a_graficar):
    st.subheader(header)
    cols_to_describe = [variables_disponibles[v] for v in variables_a_graficar if v in variables_disponibles and variables_disponibles[v] in df.columns]
    if cols_to_describe:
        stats_df = df[cols_to_describe].describe().T
        columnas_traducidas = {'count': 'N° de Registros', 'mean': 'Promedio', 'std': 'Desv. Estándar', 'min': 'Mínimo', '25%': 'P. 25', '50%': 'Mediana', '75%': 'P. 75', 'max': 'Máximo'}
        stats_df = stats_df.rename(columns=columnas_traducidas)
        nombres_de_filas = {v: k for k, v in variables_disponibles.items()}
        stats_df = stats_df.rename(index=nombres_de_filas)
        st.dataframe(stats_df.style.format("{:.2f}"))
    else: st.info("No hay variables seleccionadas para mostrar estadísticas.")

# --- BANNER SUPERIOR ---
col_logo, col_link = st.columns([1, 3])
with col_logo:
    logo_base64 = get_image_as_base64("logo_fma.png")
    if logo_base64: st.markdown(f'<a href="https://www.fundacionmaradentro.cl/" target="_blank"><img src="data:image/png;base64,{logo_base64}" width="200"></a>', unsafe_allow_html=True)
st.markdown("---")

# --- BARRA LATERAL ---
st.sidebar.title("📊 Selección de variables")
default_vars = ["Temperatura (°C)", "Radiación solar (W/m²)"]
variables_seleccionadas = [var for var in variables_disponibles if st.sidebar.checkbox(var, value=(var in default_vars))]

st.sidebar.markdown("---")
modo_comparacion = st.sidebar.checkbox("Activar modo de comparación")
st.sidebar.markdown("---")

st.sidebar.title("⏳ Selección de resolución temporal")
resoluciones = {
    "Cada 15 minutos": "15min",
    "Diaria": "D",
    "Mensual": "ME",
    "Estacional (3 meses)": "Q"
}
resolucion_seleccionada_label = st.sidebar.radio("Resolución:", list(resoluciones.keys()), index=1, label_visibility="collapsed")
resolucion_seleccionada_freq = resoluciones[resolucion_seleccionada_label]

st.sidebar.title("🌍 Ubicación")
with st.sidebar:
    mapa = folium.Map(location=[-39.4167, -71.75], zoom_start=6)
    folium.CircleMarker(location=[-39.4167, -71.75], radius=8, color='crimson', fill=True, popup="Estación Tres Hermanas").add_to(mapa)
    st_folium(mapa, width=300, height=300)

# --- PÁGINA PRINCIPAL ---
st.title("Visualizador de datos: Estación Meteorológica Tres Hermanas")
st.header("Bosque Pehuén")
st.caption("Un proyecto de Fundación Mar Adentro")

min_date, max_date = data.index.min().date(), data.index.max().date()
variables_a_graficar = [v for v in variables_seleccionadas if v != "Rosa de los vientos"]

if modo_comparacion:
    st.subheader("Selección de Períodos a Comparar")
    st.markdown("**Período 1 (Referencia)**")
    c1a, c1b = st.columns(2)
    start_date1 = c1a.date_input("Desde", min_date, min_value=min_date, max_value=max_date, key="d1_start")
    end_date1 = c1b.date_input("Hasta", max_date, min_value=start_date1, max_value=max_date, key="d1_end")
    
    st.markdown("**Período 2 (Comparación)**")
    c2a, c2b = st.columns(2)
    start_date2 = c2a.date_input("Desde", min_date, min_value=min_date, max_value=max_date, key="d2_start")
    end_date2 = c2b.date_input("Hasta", max_date, min_value=start_date2, max_value=max_date, key="d2_end")

    df1 = data.loc[str(start_date1):str(end_date1)]
    df2 = data.loc[str(start_date2):str(end_date2)]
    
    df1_resampled = resample_data(df1, resolucion_seleccionada_freq)
    df2_resampled = resample_data(df2, resolucion_seleccionada_freq)
    
    st.markdown("---")
    st.header(f"Comparación de Variables (Resolución: {resolucion_seleccionada_label})")
    
    for var in variables_a_graficar:
        col_name = variables_disponibles.get(var)
        if not col_name: continue
        fig = make_subplots(rows=2, cols=1, subplot_titles=[f"{var} - Período 1", f"{var} - Período 2"])
        if col_name in df1_resampled.columns: fig.add_trace(go.Scatter(x=df1_resampled.index, y=df1_resampled[col_name], name='P. 1'), row=1, col=1)
        if col_name in df2_resampled.columns: fig.add_trace(go.Scatter(x=df2_resampled.index, y=df2_resampled[col_name], name='P. 2'), row=2, col=1)
        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    b_col1, b_col2 = st.columns(2)
    if "Rosa de los vientos" in variables_seleccionadas:
        with b_col1:
            st.subheader("Rosa de vientos - Período 1")
            img1 = create_wind_rose(df1_resampled)
            if img1: st.image(img1) 
            else: st.info("No hay datos de viento para este período.")
            
            st.subheader("Rosa de vientos - Período 2")
            img2 = create_wind_rose(df2_resampled)
            if img2: st.image(img2)
            else: st.info("No hay datos de viento para este período.")
    with b_col2:
        display_stats(df1_resampled, "Estadísticas - Período 1", variables_a_graficar)
        st.markdown("---")
        display_stats(df2_resampled, "Estadísticas - Período 2", variables_a_graficar)

else: # MODO NORMAL
    st.subheader("Selección por fechas")
    c1, c2 = st.columns(2)
    start_date = c1.date_input("Desde", min_date, min_value=min_date, max_value=max_date)
    end_date = c2.date_input("Hasta", max_date, min_value=start_date, max_value=max_date)
    
    df_normal = data.loc[str(start_date):str(end_date)]
    df_normal_resampled = resample_data(df_normal, resolucion_seleccionada_freq)

    if variables_a_graficar:
        fig = make_subplots(rows=len(variables_a_graficar), cols=1, subplot_titles=variables_a_graficar)
        for i, var in enumerate(variables_a_graficar):
            col_name = variables_disponibles.get(var)
            if not col_name: continue
            if col_name in df_normal_resampled.columns: fig.add_trace(go.Scatter(x=df_normal_resampled.index, y=df_normal_resampled[col_name], name=var), row=i+1, col=1)
        fig.update_layout(height=300*len(variables_a_graficar), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    b_col1, b_col2 = st.columns(2)
    if "Rosa de los vientos" in variables_seleccionadas:
        with b_col1:
            st.subheader("Rosa de vientos")
            img = create_wind_rose(df_normal_resampled)
            if img: st.image(img)
            else: st.info("No hay datos de viento para este período.")
    with b_col2:
        display_stats(df_normal_resampled, "Estadísticas descriptivas", variables_a_graficar)

st.markdown("---")
st.info("Este dashboard fue desarrollado para el monitoreo y la divulgación de los datos de la estación meteorológica en el Bosque Pehuén.")
