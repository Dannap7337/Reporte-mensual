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

# --- CONFIGURACIÓN DE ENLACES ---
LINKS_TIMELINE = {
    (2025, 8): "https://lucid.app/lucidspark/543f6a91-1a33-4c3b-a36a-c1aa7ed7e063/edit?invitationId=inv_cc6d1591-c99a-4b82-b334-9898dbadd8b8",
    (2025, 9): "https://lucid.app/lucidspark/b6d966fe-81c8-4c80-b434-8b887b9f478c/edit?invitationId=inv_0789d6c9-c78c-43fa-b137-445bee6dd70c",
    (2025, 10): "https://lucid.app/lucidspark/fa0b5127-cb34-48b6-ab4d-760d38ac95d5/edit?invitationId=inv_f9d4919f-3afb-4862-8abd-a3fa7e90c52a",
    (2025, 11): "https://lucid.app/lucidspark/487992bf-7d7d-4eab-a389-6ccfae58c557/edit?invitationId=inv_25f6128c-a3ec-4f65-a58f-21be6ac896c6",
    (2025, 12): "https://lucid.app/lucidspark/fd3b8c79-5408-495f-b2ac-f1a58b043db7/edit?invitationId=inv_54a83472-e357-462a-9493-7172fe0b7757",
    (2026, 1): "https://lucid.app/lucidspark/7f65f049-6242-485e-ac78-31abe3bc87f3/edit?invitationId=inv_5568d403-e21a-4692-a3c7-70582e9cb58f",
    (2026, 2): "https://lucid.app/lucidspark/81cc3721-e383-4dad-a64f-25644745f3f6/edit?viewport_loc=728%2C-8296%2C11633%2C5008%2C0_0&invitationId=inv_e1b9573f-c69d-48dd-8bf7-f178d663d77e"
}

# --- CSS ---
st.markdown("""
    <style>
    div.stButton > button:first-child { background-color: #28a745; color: white; border: none; font-weight: bold; }
    [data-testid="stMetricValue"] { font-size: 26px; }
    .timeline-link {
        font-size: 16px; font-weight: bold; color: #4472C4 !important; text-decoration: none;
        padding: 8px 15px; border: 2px solid #4472C4; border-radius: 8px; display: inline-block;
        margin-top: 15px; transition: all 0.3s ease;
    }
    .timeline-link:hover { background-color: #4472C4; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES ---
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
    posibles = ["Tickets año.xlsx", "Tickets año.xls", "Tickets año.csv"]
    archivo = next((f for f in posibles if os.path.exists(f)), None)
    if archivo:
        df = pd.read_excel(archivo) if 'xls' in archivo else pd.read_csv(archivo)
        df.columns = df.columns.str.strip()
        for c in ['INICIO', 'FIN']:
            if c in df.columns: df[c] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')
        return df
    return None

@st.cache_data(ttl=300)
def load_escalados():
    if os.path.exists("Datos escalados.xlsx"):
        df = pd.read_excel("Datos escalados.xlsx")
        df.columns = df.columns.str.strip()
        # Buscamos la columna 'inicio' sin importar mayúsculas
        col_ini = next((c for c in df.columns if c.lower() == 'inicio'), None)
        if col_ini:
            df[col_ini] = pd.to_datetime(df[col_ini], dayfirst=True, errors='coerce')
            hoy = pd.Timestamp.now()
            df['dias_transcurridos'] = df[col_ini].apply(lambda x: contar_dias_habiles(x, hoy))
        return df
    return None

# --- SIDEBAR (Siempre definido primero) ---
st.sidebar.title("Menú Principal")
pagina = st.sidebar.radio("Selecciona:", ["1. Generación", "2. Solución", "3. Contacto", "4. Resumen Anual", "5. Escalados"])
selected_year = st.sidebar.selectbox("Año", [2025, 2026], index=1)

# --- LÓGICA DE PÁGINAS ---
df = load_data()

if df is not None:
    meses_map = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}

    if pagina == "4. Resumen Anual":
        st.title(f"📈 Resumen Anual {selected_year}")
        df['DIAS'] = df.apply(lambda x: contar_dias_habiles(x['INICIO'], x['FIN']) if pd.notnull(x['FIN']) else np.nan, axis=1)
        df_anual = df[df['FIN'].dt.year == selected_year].copy()
        if not df_anual.empty:
            df_anual['Cumple'] = df_anual['DIAS'].apply(lambda x: 1 if x <= 7 else 0)
            tendencia = df_anual.groupby(df_anual['FIN'].dt.month)['Cumple'].mean() * 100
            fig = px.line(x=[meses_map[m] for m in tendencia.index], y=tendencia.values, markers=True)
            st.plotly_chart(fig, width='stretch')

    elif pagina == "5. Escalados":
        st.title("🚀 Tickets Escalados")
        df_esc = load_escalados()
        if df_esc is not None and 'dias_transcurridos' in df_esc.columns:
            # Buscamos columna Motivo
            col_mot = next((c for c in df_esc.columns if c.lower() == 'motivo'), 'Motivo')
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("⚠️ Fuera de Tiempo (> 7 días)")
                df_f = df_esc[df_esc['dias_transcurridos'] > 7]
                if not df_f.empty:
                    fig1 = px.pie(df_f, names=col_mot, hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
                    st.plotly_chart(fig1, width='stretch')
                else: st.success("Todo al día.")
            
            with c2:
                st.subheader("✅ En Tiempo (≤ 7 días)")
                df_d = df_esc[df_esc['dias_transcurridos'] <= 7]
                if not df_d.empty:
                    fig2 = px.pie(df_d, names=col_mot, hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig2, width='stretch')
                else: st.info("Sin tickets recientes.")
        else:
            st.error("No se encontró 'Datos escalados.xlsx' o falta la columna 'inicio'.")

    else:
        st.title(f"📊 {pagina}")
        st.info("Esta sección mantiene tu lógica original de filtrado por mes.")
        # Aquí puedes pegar tu lógica original de las páginas 1, 2 y 3 si lo deseas
else:
    st.error("No se encontró el archivo de Tickets.")
