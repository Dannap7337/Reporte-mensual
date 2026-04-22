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
    div.stButton > button:hover { background-color: #218838; color: white; border: none; }
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

def calcular_estatus_solucion(row, fecha_limite, fecha_inicio_mes):
    inicio, fin = row['INICIO'], row['FIN']
    sigue_abierto_al_corte = pd.isna(fin) or (fin > fecha_limite)
    if sigue_abierto_al_corte:
        if pd.notnull(inicio):
            dias_al_momento = contar_dias_habiles(inicio, fecha_limite)
            if dias_al_momento <= 7: return "Dentro"
            elif inicio >= fecha_inicio_mes: return "Acumulado"
        return "IGNORAR"
    dias_reales = row['DIAS'] if pd.notnull(row['DIAS']) else 0
    return "Dentro" if dias_reales <= 7 else "Fuera"

def calcular_detalle_solucion(row):
    if row['Estatus_Solucion'] == 'Fuera':
        gen_val = str(row['Generacion_Excel']).strip().lower()
        if 'mismo' in gen_val: return 'Asap'
        txt = str(row['RANGO']).lower()
        if 'program' in txt: return 'Programado'
        if 'asap' in txt: return 'Asap'
        return 'Fuera.'
    return np.nan 

def calcular_contacto(dias):
    return "Fuera" if (pd.notnull(dias) and dias > 3) else "A tiempo"

# --- FUNCIONES DE ESTILO (100% SÓLIDOS) ---
def hex_to_rgba(hex_code, opacity=1.0):
    hex_code = hex_code.lstrip('#')
    r, g, b = int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)
    return f'rgba({r}, {g}, {b}, {opacity})'

def estilo_generacion(row):
    val = str(row['Generacion_Excel'])
    color_hex = '#4472C4' if 'A tiempo' in val else ('#ED7D31' if 'Mismo' in val else ('#FFC000' if 'Fuera' in val else '#A5A5A5'))
    return [f'background-color: {color_hex}; color: white; font-weight: bold'] * len(row)

def estilo_solucion(row):
    estatus, detalle = row['Estatus_Solucion'], str(row['Detalle_Solucion'])
    color_hex = '#4472C4' if estatus == 'Dentro' else ('#FFC000' if estatus == 'Acumulado' else ('#A5A5A5' if 'Asap' in detalle else ('#70AD47' if 'Programado' in detalle else '#ED7D31')))
    return [f'background-color: {color_hex}; color: white; font-weight: bold'] * len(row)

def estilo_contacto(row):
    color_hex = '#4472C4' if row['Estatus_Contacto'] == 'A tiempo' else '#ED7D31'
    return [f'background-color: {color_hex}; color: white; font-weight: bold'] * len(row)

# --- CARGA DE DATOS ---
@st.cache_data(ttl=300) 
def load_data():
    posibles = ["Tickets año.xlsx", "Tickets año.xls", "Tickets año.csv"]
    archivo_encontrado = next((f for f in posibles if os.path.exists(f)), None)
    if archivo_encontrado:
        try: 
            df = pd.read_excel(archivo_encontrado) if 'xls' in archivo_encontrado else pd.read_csv(archivo_encontrado)
            df.columns = df.columns.str.strip()
            for c in ['INICIO', 'FIN', 'CORREO']:
                if c in df.columns: df[c] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')
            if 'INICIO' in df.columns and 'FIN' in df.columns:
                df['DIAS'] = df.apply(lambda x: contar_dias_habiles(x['INICIO'], x['FIN']) if pd.notnull(x['FIN']) else np.nan, axis=1)
            col_gen_real = next((col for col in df.columns if "GENERACI" in col.upper() and "TICKET" in col.upper()), None)
            df.rename(columns={col_gen_real: 'Generacion_Excel'} if col_gen_real else {}, inplace=True)
            if 'Generacion_Excel' not in df.columns: df['Generacion_Excel'] = "No encontrado"
            return df
        except: return None
    return None

@st.cache_data(ttl=300)
def load_escalados():
    if os.path.exists("Datos escalados.xlsx"):
        try:
            df = pd.read_excel("Datos escalados.xlsx")
            df.columns = [str(c).strip() for c in df.columns]
            col_ini = next((c for c in df.columns if c.lower() == 'inicio'), None)
            if col_ini:
                df[col_ini] = pd.to_datetime(df[col_ini], dayfirst=True, errors='coerce')
                hoy = pd.Timestamp.now()
                df['dias_transcurridos'] = df[col_ini].apply(lambda x: contar_dias_habiles(x, hoy))
            return df
        except: return None
    return None

@st.cache_data
def get_data_mensual(df, year, month_num):
    inicio_mes = pd.Timestamp(year, month_num, 1)
    fin_mes = pd.Timestamp(year, month_num, monthrange(year, month_num)[1], 23, 59, 59)
    df_f = df[(df['INICIO'] <= fin_mes) & ((df['FIN'].isnull()) | (df['FIN'] >= inicio_mes))].copy()
    df_f['Estatus_Solucion'] = df_f.apply(lambda x: calcular_estatus_solucion(x, fin_mes, inicio_mes), axis=1)
    df_f = df_f[df_f['Estatus_Solucion'] != 'IGNORAR']
    df_f['Detalle_Solucion'] = df_f.apply(calcular_detalle_solucion, axis=1)
    if 'DIAS PRIMER CONTACTO' in df_f.columns:
        df_f['Estatus_Contacto'] = df_f['DIAS PRIMER CONTACTO'].apply(calcular_contacto)
    return df_f, inicio_mes, fin_mes

# --- SIDEBAR ---
st.sidebar.title("Menú Principal")
pagina = st.sidebar.radio("Selecciona:", ["1. Generación", "2. Solución", "3. Contacto", "4. Resumen Anual", "5. Escalados"])
all_years = [2025, 2026]
selected_year = st.sidebar.selectbox("Año", all_years, index=len(all_years)-1)

# --- APP ---
df = load_data()

if df is not None:
    ahora = pd.Timestamp.now()
    meses_map = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}

    if pagina in ["1. Generación", "2. Solución", "3. Contacto"]:
        # (Lógica de selección de mes omitida por brevedad, mantenida igual que tu original)
        df_y = df[df['INICIO'].dt.year == selected_year]
        meses_con_datos = sorted(df_y['INICIO'].dt.month.dropna().unique())
        meses_disp = [meses_map[m] for m in meses_con_datos]

        if not meses_disp:
            st.info(f"Sin datos en {selected_year}.")
        else:
            selected_month_name = st.sidebar.selectbox("Mes", meses_disp, index=len(meses_disp)-1)
            selected_month_num = next(k for k,v in meses_map.items() if v==selected_month_name)
            df_f, _, _ = get_data_mensual(df, selected_year, selected_month_num)

            st.title(f"📊 {pagina}")

            if pagina == "2. Solución":
                conteo_padres = df_f['Estatus_Solucion'].value_counts()
                df_fuera = df_f[df_f['Estatus_Solucion'] == 'Fuera']
                ids, labels, parents, values, colors = [], [], [], [], []
                
                # Definición de colores sólidos para el gráfico
                c_dentro, c_acumulado, c_fuera = '#4472C4', '#FFC000', '#ED7D31'
                c_asap, c_prog = '#A5A5A5', '#70AD47'

                if 'Dentro' in conteo_padres:
                    ids.append("Dentro"); labels.append("Dentro"); parents.append(""); values.append(conteo_padres['Dentro']); colors.append(c_dentro)
                if 'Acumulado' in conteo_padres:
                    ids.append("Acumulado"); labels.append("Acumulado"); parents.append(""); values.append(conteo_padres['Acumulado']); colors.append(c_acumulado)
                if not df_fuera.empty:
                    ids.append("Fuera"); labels.append("Fuera"); parents.append(""); values.append(len(df_fuera)); colors.append(c_fuera)
                    for subtipo, cant in df_fuera['Detalle_Solucion'].value_counts().items():
                        ids.append(f"Fuera - {subtipo}"); labels.append(subtipo); parents.append("Fuera"); values.append(cant)
                        colors.append(c_asap if 'Asap' in str(subtipo) else (c_prog if 'Programado' in str(subtipo) else c_fuera))
                
                fig = go.Figure(go.Sunburst(
                    ids=ids, labels=labels, parents=parents, values=values,
                    branchvalues="total",
                    marker=dict(colors=colors, line=dict(color='#ffffff', width=2)),
                    leaf=dict(opacity=1), # ESTO QUITA LO OPACO DEL EXTERIOR
                    textinfo="label+value+percent root"
                ))
                fig.update_layout(height=800, font=dict(size=18), margin=dict(t=0, l=0, r=0, b=0))
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("Ver Detalle"): 
                    st.dataframe(df_f[['N° TICKET', 'USUARIO', 'INICIO', 'FIN', 'DIAS', 'RANGO', 'Estatus_Solucion', 'Detalle_Solucion']].style.apply(estilo_solucion, axis=1), use_container_width=True)

            elif pagina == "1. Generación":
                d = df_f['Generacion_Excel'].value_counts().reset_index()
                d.columns=['E','C']
                fig = px.pie(d, values='C', names='E', hole=0.5, color='E', color_discrete_map={'A tiempo': '#4472C4', 'Mismo día': '#ED7D31', 'Fuera': '#FFC000', 'Programados': '#A5A5A5'})
                fig.update_traces(opacity=1)
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("Ver Detalle"): st.dataframe(df_f[['N° TICKET', 'USUARIO', 'INICIO', 'Generacion_Excel']].style.apply(estilo_generacion, axis=1), use_container_width=True)

            elif pagina == "3. Contacto":
                d = df_f['Estatus_Contacto'].value_counts().reset_index()
                d.columns=['E','C']
                fig = px.pie(d, values='C', names='E', hole=0.5, color='E', color_discrete_map={'A tiempo':'#4472C4', 'Fuera':'#ed7d31'})
                fig.update_traces(opacity=1)
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("Ver Detalle"): st.dataframe(df_f[['N° TICKET', 'USUARIO', 'INICIO', 'DIAS PRIMER CONTACTO', 'Estatus_Contacto']].style.apply(estilo_contacto, axis=1), use_container_width=True)

    elif pagina == "5. Escalados":
        st.title("🚀 Reporte de Tickets Escalados (Histórico Total)")
        df_esc = load_escalados()
        if df_esc is not None:
            col_mot = next((c for c in df_esc.columns if c.lower() == 'motivo'), 'Motivo')
            c1, c2 = st.columns(2)
            # (Gráficos de escalados mantenidos con opacidad 1)
            df_f = df_esc[df_esc['dias_transcurridos'] > 7]
            df_d = df_esc[df_esc['dias_transcurridos'] <= 7]
            
            with c1:
                if not df_f.empty:
                    fig1 = px.pie(df_f, names=col_mot, hole=0.4, color_discrete_sequence=px.colors.qualitative.Set1)
                    fig1.update_traces(opacity=1)
                    st.plotly_chart(fig1, use_container_width=True)
            with c2:
                if not df_d.empty:
                    fig2 = px.pie(df_d, names=col_mot, hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig2.update_traces(opacity=1)
                    st.plotly_chart(fig2, use_container_width=True)
            
            st.markdown("---")
            df_esc_sort = df_esc.sort_values(by='dias_transcurridos', ascending=False)
            st.dataframe(df_esc_sort, use_container_width=True)

else:
    st.error("No se encontró 'Tickets año.xlsx'")
