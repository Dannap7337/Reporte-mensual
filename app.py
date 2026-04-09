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
            # Normalizar nombres de columnas: quitar espacios y pasar a MAYÚSCULAS para comparar mejor
            df.columns = df.columns.str.strip()
            
            # Buscar la columna de fecha sin importar si es 'inicio', 'Inicio' o 'INICIO'
            col_fecha = next((c for c in df.columns if c.upper() == 'INICIO'), None)
            
            if col_fecha:
                df[col_fecha] = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
                hoy = pd.Timestamp.now()
                # Creamos la columna asegurándonos de que exista
                df['dias_transcurridos'] = df[col_fecha].apply(lambda x: contar_dias_habiles(x, hoy))
            else:
                # Si no encuentra la columna, creamos la de días en 0 para evitar que el app explote
                df['dias_transcurridos'] = 0
                st.sidebar.error("⚠️ No se encontró la columna 'inicio' en el Excel de Escalados.")
            return df
        except Exception as e:
            st.sidebar.error(f"Error cargando escalados: {e}")
            return None
    return None

# --- SIDEBAR ---
st.sidebar.title("Menú Principal")
pagina = st.sidebar.radio("Selecciona:", ["1. Generación", "2. Solución", "3. Contacto", "4. Resumen Anual"])
selected_year = st.sidebar.selectbox("Año", [2025, 2026], index=1)

# --- PROCESAMIENTO ---
df = load_data()
df_esc = load_escalados()

if df is not None:
    meses_map = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}

    if pagina == "4. Resumen Anual":
        st.title(f"📈 Resumen Anual {selected_year}")
        
        # Lógica de eficiencia anual
        df['DIAS'] = df.apply(lambda x: contar_dias_habiles(x['INICIO'], x['FIN']) if pd.notnull(x['FIN']) else np.nan, axis=1)
        df_anual = df[df['FIN'].dt.year == selected_year].copy()
        
        if not df_anual.empty:
            df_anual['Cumple'] = df_anual['DIAS'].apply(lambda x: 1 if x <= 7 else 0)
            tendencia = df_anual.groupby(df_anual['FIN'].dt.month)['Cumple'].mean() * 100
            
            fig_line = px.line(x=[meses_map[m] for m in tendencia.index], y=tendencia.values, markers=True, title="Eficiencia Mensual")
            # Actualizado: width='stretch' reemplaza use_container_width=True
            st.plotly_chart(fig_line, width='stretch')
        
        # --- SECCIÓN ESCALADOS ---
        st.markdown("---")
        st.header("🚀 Tickets Escalados (Estatus Actual)")
        
        if df_esc is not None and 'dias_transcurridos' in df_esc.columns:
            col1, col2 = st.columns(2)
            
            # Gráfico 1: > 7 días
            df_fuera = df_esc[df_esc['dias_transcurridos'] > 7]
            with col1:
                st.subheader("⚠️ Más de 7 días hábiles")
                if not df_fuera.empty:
                    # Buscamos la columna de Motivo ignorando mayúsculas
                    col_motivo = next((c for c in df_esc.columns if c.upper() == 'MOTIVO'), 'Motivo')
                    fig1 = px.pie(df_fuera, names=col_motivo, hole=0.4, 
                                 color_discrete_sequence=px.colors.qualitative.Reds_r)
                    st.plotly_chart(fig1, width='stretch')
                else:
                    st.info("No hay tickets escalados con más de 7 días.")

            # Gráfico 2: <= 7 días
            df_dentro = df_esc[df_esc['dias_transcurridos'] <= 7]
            with col2:
                st.subheader("✅ 7 días hábiles o menos")
                if not df_dentro.empty:
                    col_motivo = next((c for c in df_esc.columns if c.upper() == 'MOTIVO'), 'Motivo')
                    fig2 = px.pie(df_dentro, names=col_motivo, hole=0.4,
                                 color_discrete_sequence=px.colors.qualitative.Blues_r)
                    st.plotly_chart(fig2, width='stretch')
                else:
                    st.info("No hay tickets escalados recientes.")
        else:
            st.warning("No hay datos de escalados disponibles.")

    else:
        st.title(f"📊 {pagina}")
        st.info("La sección de escalados se encuentra en '4. Resumen Anual'.")

else:
    st.error("No se encontró el archivo principal de tickets.")
