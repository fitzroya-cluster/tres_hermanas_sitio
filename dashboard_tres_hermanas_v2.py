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

# Configurar la página
st.set_page_config(page_title="Visualizador de datos estación Tres Hermanas", layout="wide", initial_sidebar_state="expanded")

# Inyectar CSS para fijar el ancho máximo de algunos contenedores (opcional)
st.markdown("""
    <style>
    .fixed-figure {
        max-width: 600px;
        margin: auto;
    }
    </style>
    """, unsafe_allow_html=True)

# Función para cargar datos
@st.cache_data
def load_data():
    data = pd.read_csv("base_de_datos_3_hermanas.csv.gz", compression="gzip", parse_dates=["TIMESTAMP"])
    data.set_index("TIMESTAMP", inplace=True)
    return data

data = load_data()

# Filtros en la barra lateral
st.sidebar.title("📊 Selección de Variables")
variables_disponibles = {
    "Temperatura (°C)": "AirTC_Avg",
    "Humedad (%)": "RH_Avg",
    "Velocidad del Viento (m/s)": "WS_ms_Avg",
    "Dirección del Viento (°)": "WindDir_Avg",
    "Presión Atmosférica (hPa)": "BP_mbar_Avg",
    "Radiación Solar (W/m²)": "incomingSW_Avg",
    "Radiación de onda corta saliente (W/m²)": "outgoingSW_Avg",
    "Radiación de onda larga entrante (W/m²)": "incomingLW_Avg",
    "Albedo (%)": "albedo_Avg",
    "Precipitación (mm)": "Rain_mm_Tot",
    "Punto de Rocío (°C)": "PtoRocio_Avg",
    "Temperatura del Suelo a 50 cm (°C)": "T107_50cm_Avg",
    "Temperatura del Suelo a 10 cm (°C)": "T107_10cm_Avg",
    "Humedad del Suelo (%)": "SoilMoisture_Avg",
    "Rosa de los Vientos": "Wind_Rose"
}
default_vars = ["Temperatura (°C)", "Radiación Solar (W/m²)", "Rosa de los Vientos"]
variables_seleccionadas = st.sidebar.multiselect(
    "Selecciona las variables a visualizar:",
    list(variables_disponibles.keys()),
    default=default_vars
)

if not variables_seleccionadas:
    st.warning("Por favor, selecciona al menos una variable para visualizar.")
    st.stop()

# Encabezados principales
st.title("Fundación Mar Adentro")
st.header("Bosque Pehuén")
st.subheader("📊 Visualización de Variables Meteorológicas estación Tres Hermanas")

# Slider para rango de fechas
st.subheader("📅 Selección de Rango Temporal")
min_date = data.index.min().date()
max_date = data.index.max().date()
start_date, end_date = st.slider(
    "Selecciona el rango de fechas:",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)
filtered_data = data.loc[str(start_date):str(end_date)]

# Resolución temporal en la barra lateral
st.sidebar.title("⏳ Selección de Resolución Temporal")
resoluciones = {
    "Cada 15 minutos": "15min",
    "Diaria": "D",
    "Mensual": "ME",
    "Estacional (3 meses)": "Q"
}
resolucion_seleccionada = st.sidebar.radio(
    "Selecciona la resolución temporal:",
    list(resoluciones.keys()),
    index=1
)

# Mapa de ubicación en la barra lateral
st.sidebar.title("🌍 Ubicación de la estación")
with st.sidebar:
    mapa = folium.Map(location=[-39.4167, -71.75], zoom_start=6)
    folium.Marker(
        [-39.4167, -71.75],
        popup="Estación Tres Hermanas",
        tooltip="Estación Meteorológica"
    ).add_to(mapa)
    st_folium(mapa, width=300, height=350)

# Función para reagrupar los datos usando MetPy para calcular u y v,
# luego promediar y recalcular la dirección del viento a partir de ellos.
def resample_data(df, resolution):
    df_copy = df.copy()
    # Calcular u y v usando MetPy (convención: u = -ws*sin(wd), v = -ws*cos(wd))
    ws = df_copy["WS_ms_Avg"].values * units("m/s")
    wd = df_copy["WindDir_Avg"].values * units.deg
    u, v = mpcalc.wind_components(ws, wd)
    df_copy["Wind_u"] = u.magnitude
    df_copy["Wind_v"] = v.magnitude

    # Obtener la frecuencia correcta a partir del diccionario
    freq = resoluciones[resolution]
    aggregated = df_copy.resample(freq).mean()

    # Recalcular la dirección del viento a partir del promedio de u y v
    u_avg = aggregated["Wind_u"].values * units("m/s")
    v_avg = aggregated["Wind_v"].values * units("m/s")
    wd_new = mpcalc.wind_direction(u_avg, v_avg)
    aggregated["WindDir_Avg"] = wd_new.magnitude
    # Calcular la velocidad resultante (promedio vectorial)
    aggregated["WS_calc"] = np.sqrt(aggregated["Wind_u"]**2 + aggregated["Wind_v"]**2)
    return aggregated

filtered_data = resample_data(filtered_data, resolucion_seleccionada)

# Gráfico interactivo de las series de tiempo para las demás variables (excepto la rosa de los vientos)
variables_a_graficar = [var for var in variables_seleccionadas if var != "Rosa de los Vientos"]
if variables_a_graficar:
    ts_fig = make_subplots(
        rows=len(variables_a_graficar),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=variables_a_graficar
    )
    for i, var in enumerate(variables_a_graficar):
        ts_fig.add_trace(
            go.Scatter(
                x=filtered_data.index,
                y=filtered_data[variables_disponibles[var]],
                mode='lines',
                name=var,
                showlegend=False
            ),
            row=i+1,
            col=1
        )
    # Ajustar los títulos de cada subgráfico
    for annotation in ts_fig['layout']['annotations']:
        annotation['font'] = dict(size=20, color='black')
    ts_fig.update_layout(
        height=300 * len(variables_a_graficar),
        template="plotly_white",
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True)
    )
    st.plotly_chart(ts_fig, use_container_width=True)

# Mostrar la rosa de los vientos y las estadísticas juntas debajo de las series de tiempo
col1, col2 = st.columns(2)

with col1:
    st.subheader("Rosa de los Vientos")
    def create_wind_rose_windrose(df, figsize=(6,6)):
        # Filtrar los datos necesarios
        df_plot = df.dropna(subset=["WindDir_Avg", "WS_calc"]).copy()
        wd = df_plot["WindDir_Avg"].values
        ws = df_plot["WS_calc"].values

        fig = plt.figure(figsize=figsize, constrained_layout=True)
        ax = WindroseAxes.from_ax(fig=fig)
        ax.bar(wd, ws, normed=True, opening=0.8, edgecolor='white', cmap=plt.cm.jet)
        ax.set_legend(title="Velocidad (m/s)", fontsize=12, title_fontsize=14)
        # Quitamos el título interno para mostrarlo como Streamlit
        return fig

    windrose_fig = create_wind_rose_windrose(filtered_data, figsize=(6,6))
    buf = io.BytesIO()
    windrose_fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    st.image(buf, width=600)

with col2:
    st.subheader("Estadísticas Descriptivas")
    st.dataframe(filtered_data.describe().T)
