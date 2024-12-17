import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configurar la página
st.set_page_config(page_title="Estación Tres Hermanas", layout="wide")

# CSS avanzado para la estética
st.markdown(
    """
    <style>
    body, .stApp {
        background-color: #f8f9fa;
        font-family: 'Montserrat', sans-serif;
        color: #333333;
    }
    .main-title {
        font-size: 3rem;
        font-weight: bold;
        color: #1F4E79;
        text-align: center;
        padding: 1.5rem 0;
        background: linear-gradient(to right, #e3f2fd, #ffffff);
        border-radius: 12px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    .filter-box, .chart-card {
        background-color: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
    }
    .section-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1F4E79;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Encabezado principal
st.markdown('<div class="main-title">Estación Tres Hermanas</div>', unsafe_allow_html=True)

# Cargar datos
@st.cache_data
def load_data():
    data = pd.read_csv("base_de_datos_3_hermanas.csv.gz", compression="gzip", parse_dates=["TIMESTAMP"])
    data.set_index("TIMESTAMP", inplace=True)
    return data

data = load_data()

# Filtros
st.markdown('<div class="filter-box">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
start_date = col1.date_input("Fecha de inicio", value=data.index.min())
end_date = col2.date_input("Fecha de término", value=data.index.max())
st.markdown('</div>', unsafe_allow_html=True)
filtered_data = data.loc[start_date:end_date].copy()

# Clasificar estaciones correctamente
def assign_season(date):
    if date.month == 12:
        return f"{date.year + 1}-Verano"
    elif date.month in [1, 2]:
        return f"{date.year}-Verano"
    elif date.month in [3, 4, 5]:
        return f"{date.year}-Otoño"
    elif date.month in [6, 7, 8]:
        return f"{date.year}-Invierno"
    else:
        return f"{date.year}-Primavera"

filtered_data["Season_Year"] = filtered_data.index.map(assign_season)

# Agrupaciones
agg_functions = {
    "Rain_mm_Tot": "sum",
    "AirTC_Avg": "mean", "RH_Avg": "mean", "BP_mbar_Avg": "mean", "PTemp_C_Avg": "mean",
    "PtoRocio_Avg": "mean", "WS_ms_Avg": "mean", "incomingSW_Avg": "mean",
    "outgoingSW_Avg": "mean", "incomingLW_Avg": "mean", "outgoingLW_Avg": "mean",
    "albedo_Avg": "mean"
}
daily_data = filtered_data.resample("D").agg(agg_functions)
monthly_data = filtered_data.resample("ME").agg(agg_functions)
seasonal_data = filtered_data.groupby("Season_Year").agg(agg_functions).reset_index()

# Función para crear gráficos dinámicos
def create_dynamic_graph(resolution, variable, y_title):
    fig = go.Figure()

    if resolution == "Cada 15 minutos":
        fig.add_trace(go.Scatter(x=filtered_data.index, y=filtered_data[variable],
                                 mode='lines', name="Datos Crudos (15 min)",
                                 line=dict(color="#1f77b4", width=1)))

    elif resolution == "Diaria":
        fig.add_trace(go.Scatter(x=daily_data.index, y=daily_data[variable],
                                 mode='lines+markers', name="Promedio Diario",
                                 line=dict(color="#ff5733", width=2)))

    elif resolution == "Mensual":
        fig.add_trace(go.Scatter(x=monthly_data.index, y=monthly_data[variable],
                                 mode='lines+markers', name="Promedio Mensual",
                                 line=dict(color="#2ca02c", width=2)))

    elif resolution == "Estacional":
        fig.add_trace(go.Bar(x=seasonal_data["Season_Year"], y=seasonal_data[variable],
                             name="Promedio Estacional", marker_color="#f39c12"))

    # Configurar el layout
    fig.update_layout(
        title=f"{resolution} - {y_title}",
        xaxis_title="Fecha",
        yaxis_title=y_title,
        font=dict(size=14, color="black"),
        xaxis=dict(tickfont=dict(size=12, color="black")),
        yaxis=dict(tickfont=dict(size=12, color="black")),
        legend=dict(font=dict(size=12, color="black")),
        plot_bgcolor="white",
        paper_bgcolor="white"
    )
    return fig

# Selector de variable y resolución temporal
st.markdown('<div class="chart-card">', unsafe_allow_html=True)
variables = {
    "Precipitación Total (mm)": "Rain_mm_Tot",
    "Temperatura Promedio (°C)": "AirTC_Avg",
    "Humedad Relativa Promedio (%)": "RH_Avg",
    "Presión Barométrica (mbar)": "BP_mbar_Avg",
    "Temperatura Sensor (°C)": "PTemp_C_Avg",
    "Punto de Rocío (°C)": "PtoRocio_Avg",
    "Velocidad del Viento (m/s)": "WS_ms_Avg",
    "Radiación SW Entrante (W/m²)": "incomingSW_Avg",
    "Radiación SW Saliente (W/m²)": "outgoingSW_Avg",
    "Radiación LW Entrante (W/m²)": "incomingLW_Avg",
    "Radiación LW Saliente (W/m²)": "outgoingLW_Avg",
    "Albedo Promedio": "albedo_Avg"
}
selected_var = st.selectbox("Selecciona una variable:", list(variables.keys()))
resolution = st.selectbox("Selecciona la resolución temporal:", ["Cada 15 minutos", "Diaria", "Mensual", "Estacional"])

# Mostrar el gráfico
fig = create_dynamic_graph(resolution, variables[selected_var], selected_var)
st.plotly_chart(fig, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# Botón de descarga
st.subheader("Descargar Datos")
csv = filtered_data.to_csv()
st.download_button(
    label="Descargar datos filtrados en CSV",
    data=csv,
    file_name="datos_filtrados_tres_hermanas.csv",
    mime="text/csv"
)
