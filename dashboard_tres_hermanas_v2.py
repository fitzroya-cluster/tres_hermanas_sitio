import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configurar la página
st.set_page_config(page_title="Visualizador de datos estación Tres Hermanas", layout="wide")

# CSS avanzado para el diseño Oscuro Futurista
st.markdown(
    """
    <style>
    body, .stApp {
        background-color: #1C1C1C;
        font-family: 'Montserrat', sans-serif;
        color: #F0F0F0;
    }
    .main-title {
        font-size: 3.5rem;
        font-weight: bold;
        text-align: center;
        color: white;
        padding: 1rem 0;
    }
    .filter-box, .chart-card {
        background-color: #292929;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
        margin-bottom: 2rem;
        border: 1px solid #3C3C3C;
    }
    .section-title {
        font-size: 1.8rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #00E5FF;
    }
    .stButton>button {
        background-color: #76FF03;
        color: black;
        border-radius: 12px;
        padding: 0.5rem 1rem;
        font-size: 1rem;
        font-weight: bold;
        border: none;
    }
    .stButton>button:hover {
        background-color: #64DD17;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Encabezado principal
st.markdown('<div class="main-title">📊 Visualizador de datos estación Tres Hermanas</div>', unsafe_allow_html=True)

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
agg_functions = {col: "mean" for col in data.columns if col != "Rain_mm_Tot"}
agg_functions["Rain_mm_Tot"] = "sum"

daily_data = filtered_data.resample("D").agg(agg_functions)
monthly_data = filtered_data.resample("ME").agg(agg_functions)
seasonal_data = filtered_data.groupby("Season_Year").agg(agg_functions).reset_index()

# Función para crear gráficos dinámicos
def create_dynamic_graph(resolution, variable, y_title):
    if resolution == "Cada 15 minutos":
        df = filtered_data
    elif resolution == "Diaria":
        df = daily_data
    elif resolution == "Mensual":
        df = monthly_data
    elif resolution == "Estacional":
        df = seasonal_data
        df.set_index("Season_Year", inplace=True)

    fig = go.Figure()

    if resolution == "Estacional":
        fig.add_trace(go.Bar(x=df.index, y=df[variable],
                             name=y_title, marker_color="#FF6F61"))
    else:
        fig.add_trace(go.Scatter(x=df.index, y=df[variable],
                                 mode='lines', name=y_title,
                                 line=dict(color="#FF6F61", width=2)))

    fig.update_layout(
        title=f"{resolution} - {y_title}",
        xaxis_title="Fecha",
        yaxis_title=y_title,
        font=dict(family="Montserrat", size=14, color="white"),
        xaxis=dict(tickfont=dict(size=12, color="white")),
        yaxis=dict(tickfont=dict(size=12, color="white")),
        legend=dict(font=dict(size=12, color="white")),
        plot_bgcolor="#292929",
        paper_bgcolor="#292929"
    )
    return fig

# Función para crear gráfico combinado "Combinada"
def create_puelche_graph(resolution):
    if resolution == "Cada 15 minutos":
        df = filtered_data
    elif resolution == "Diaria":
        df = daily_data
    elif resolution == "Mensual":
        df = monthly_data
    elif resolution == "Estacional":
        df = seasonal_data
        df.set_index("Season_Year", inplace=True)

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=("Temperatura (°C)", "Humedad (%)", "Velocidad del Viento (m/s)", "Dirección del Viento (°)")
    )

    # Subgráficos
    if resolution == "Estacional":
        fig.add_trace(go.Bar(x=df.index, y=df["AirTC_Avg"],
                             name="Temperatura", marker_color="#FF6F61"),
                      row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df["RH_Avg"],
                             name="Humedad", marker_color="#4FC3F7"),
                      row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df["WS_ms_Avg"],
                             name="Velocidad del Viento", marker_color="#81C784"),
                      row=3, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df["WindDir_Avg"],
                             name="Dirección del Viento", marker_color="#388E3C"),
                      row=4, col=1)
    else:
        fig.add_trace(go.Scatter(x=df.index, y=df["AirTC_Avg"],
                                 mode='lines', name="Temperatura",
                                 line=dict(color="#FF6F61", width=2)),
                      row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["RH_Avg"],
                                 mode='lines', name="Humedad",
                                 line=dict(color="#4FC3F7", width=2)),
                      row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["WS_ms_Avg"],
                                 mode='lines', name="Velocidad del Viento",
                                 line=dict(color="#81C784", width=2)),
                      row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["WindDir_Avg"],
                                 mode='lines', name="Dirección del Viento",
                                 line=dict(color="#388E3C", width=2)),
                      row=4, col=1)

    # Configuración
    fig.update_layout(
        height=900,
        title=f"Combinada - Comparación de Variables Clave ({resolution})",
        font=dict(family="Montserrat", size=14, color="white"),
        xaxis=dict(tickfont=dict(size=12, color="white")),
        yaxis=dict(tickfont=dict(size=12, color="white")),
        legend=dict(font=dict(size=12, color="white")),
        plot_bgcolor="#292929",
        paper_bgcolor="#292929",
        showlegend=True
    )

    return fig

# Selector de variable y resolución temporal
st.markdown('<div class="chart-card">', unsafe_allow_html=True)
variables = {"Combinada: Temperatura, Humedad y Viento": None}
variables.update({col: col for col in data.columns})
selected_var = st.selectbox("Selecciona una variable:", list(variables.keys()))
resolution = st.selectbox("Selecciona la resolución temporal:", ["Cada 15 minutos", "Diaria", "Mensual", "Estacional"])

# Mostrar el gráfico
if selected_var == "Combinada: Temperatura, Humedad y Viento":
    fig = create_puelche_graph(resolution)
else:
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
