import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import numpy as np
from calendar import monthrange

st.set_page_config(page_title="Reporte TI", layout="wide")

# --- CONFIGURACIÓN DE FERIADOS ---
FERIADOS = [
    '2025-01-01', '2025-02-03', '2025-03-17', '2025-05-01', '2025-09-16', 
    '2025-11-17', '2025-12-25', '2026-01-01', '2026-02-02', '2026-03-16'
]
feriados_np = np.array(FERIADOS, dtype='datetime64[D]')

# --- CSS ---
st.markdown("""
    <style>
    div.stButton > button:first-child { background-color: #28a745; color: white; border: none; font-weight: bold; }
    [data-testid="stMetricValue"] { font-size: 26px; }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE LÓGICA ---
def contar_dias_habiles(inicio, fin):
    try:
        if pd.isna(inicio) or pd.isna(fin): return 0
        start = np.datetime64(inicio, 'D')
        end = np.datetime64(fin, 'D')
        if start > end: return 0
        return int(np.busday_count(start, end, holidays=feriados_np))
    except: return 0

# --- CARGA DE DATOS ---
@st.cache_data(ttl=300)
def load_data():
    for f in ["Tickets año.xlsx", "Tickets año.xls", "Tickets año.csv"]:
        if os.path.exists(f):
            df = pd.read_excel(f) if 'xls' in f else pd.read_csv(f)
            df.columns = df.columns.str.strip()
            for c in ['INICIO', 'FIN']:
                if c in df.columns: df[c] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')
            return df
    return None

@st.cache_data(ttl=300)
def load_escalados():
    if os.path.exists("Datos escalados.xlsx"):
        try:
            df = pd.read_excel("Datos escalados.xlsx")
            df.columns = df.columns.str.strip()
            if 'inicio' in df.columns:
                df['inicio'] = pd.to_datetime(df['inicio'], dayfirst=True, errors='coerce')
                hoy = pd.Timestamp.now()
                df['dias_transcurridos'] = df['inicio'].apply(lambda x: contar_dias_habiles(x, hoy))
            return df
        except: return None
    return None

# --- SIDEBAR (Siempre se ejecuta primero para evitar NameError) ---
st.sidebar.title("Menú Principal")
pagina = st.sidebar.radio("Selecciona:", ["1. Generación", "2. Solución", "3. Contacto", "4. Resumen Anual"])
selected_year = st.sidebar.selectbox("Año", [2025, 2026], index=1)

# --- PROCESAMIENTO ---
df = load_data()
df_esc = load_escalados()

if df is not None:
    # Lógica de fechas
    ahora = pd.Timestamp.now()
    meses_map = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}

    if pagina == "4. Resumen Anual":
        st.title(f"📈 Resumen Anual {selected_year}")
        
        # Filtrar datos del año para eficiencia
        df['DIAS'] = df.apply(lambda x: contar_dias_habiles(x['INICIO'], x['FIN']) if pd.notnull(x['FIN']) else np.nan, axis=1)
        df_anual = df[df['FIN'].dt.year == selected_year].copy()
        
        if not df_anual.empty:
            df_anual['Cumple'] = df_anual['DIAS'].apply(lambda x: 1 if x <= 7 else 0)
            tendencia = df_anual.groupby(df_anual['FIN'].dt.month)['Cumple'].mean() * 100
            
            fig_line = px.line(x=[meses_map[m] for m in tendencia.index], y=tendencia.values, markers=True, title="Eficiencia Mensual")
            st.plotly_chart(fig_line, use_container_width=True)
        
        # --- SECCIÓN ESCALADOS ---
        st.markdown("---")
        st.header("🚀 Tickets Escalados (Datos Actuales)")
        
        if df_esc is not None:
            col1, col2 = st.columns(2)
            
            # Gráfico 1: > 7 días
            df_fuera = df_esc[df_esc['dias_transcurridos'] > 7]
            with col1:
                st.subheader("⚠️ Más de 7 días hábiles")
                if not df_fuera.empty:
                    fig1 = px.pie(df_fuera, names='Motivo', hole=0.4, 
                                 color_discrete_sequence=px.colors.qualitative.Reds_r)
                    st.plotly_chart(fig1, use_container_width=True)
                else:
                    st.info("No hay tickets escalados con más de 7 días.")

            # Gráfico 2: <= 7 días
            df_dentro = df_esc[df_esc['dias_transcurridos'] <= 7]
            with col2:
                st.subheader("✅ 7 días hábiles o menos")
                if not df_dentro.empty:
                    fig2 = px.pie(df_dentro, names='Motivo', hole=0.4,
                                 color_discrete_sequence=px.colors.qualitative.Blues_r)
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("No hay tickets escalados recientes.")
            
            with st.expander("Ver lista de tickets escalados"):
                st.table(df_esc[['Ticket', 'Usuario', 'Motivo', 'inicio', 'dias_transcurridos']])
        else:
            st.warning("No se pudo cargar 'Datos escalados.xlsx'. Verifica que el archivo exista.")

    else:
        st.title(f"📊 {pagina}")
        st.info("Selecciona 'Resumen Anual' para ver los nuevos gráficos de escalados.")
        # Aquí iría el resto de tu código para las páginas 1, 2 y 3...

else:
    st.error("Error: No se encontró el archivo principal 'Tickets año.xlsx'.")
