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

# --- CONFIGURACIÓN DE ENLACES DE LÍNEAS DE TIEMPO ---
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
    [data-testid="stMetricValue"] { font-size: 26px; }
    .timeline-link {
        font-size: 16px; font-weight: bold; color: #4472C4 !important; text-decoration: none;
        padding: 10px 20px; border: 2px solid #4472C4; border-radius: 8px; display: inline-block;
        margin-top: 15px; transition: all 0.3s ease; text-align: center;
    }
    .timeline-link:hover { background-color: #4472C4; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE LÓGICA ---
def contar_dias_habiles(inicio, fin):
    try:
        if pd.isna(inicio) or pd.isna(fin): return 0
        start = np.datetime64(inicio, 'D'); end = np.datetime64(fin, 'D')
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

# --- FUNCIONES DE ESTILO (OPACIDAD 0.3) ---
def hex_to_rgba(hex_code, opacity=0.3):
    hex_code = hex_code.lstrip('#')
    r, g, b = int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)
    return f'rgba({r}, {g}, {b}, {opacity})'

def estilo_generacion(row):
    val = str(row['Generacion_Excel'])
    color_hex = '#4472C4' if 'A tiempo' in val else ('#ED7D31' if 'Mismo' in val else ('#FFC000' if 'Fuera' in val else '#A5A5A5'))
    return [f'background-color: {hex_to_rgba(color_hex)}; color: black'] * len(row)

def estilo_solucion(row):
    estatus, detalle = row['Estatus_Solucion'], str(row['Detalle_Solucion'])
    color_hex = '#4472C4' if estatus == 'Dentro' else ('#FFC000' if estatus == 'Acumulado' else ('#ED7D31' if 'Asap' in detalle else ('#70AD47' if 'Programado' in detalle else '#ED7D31')))
    return [f'background-color: {hex_to_rgba(color_hex)}; color: black'] * len(row)

def estilo_contacto(row):
    color_hex = '#4472C4' if row['Estatus_Contacto'] == 'A tiempo' else '#ED7D31'
    return [f'background-color: {hex_to_rgba(color_hex)}; color: black'] * len(row)

def estilo_escalados_suave(row):
    color_hex = '#DC3545' if row['dias_transcurridos'] > 7 else '#28A745'
    return [f'background-color: {hex_to_rgba(color_hex)}; color: black'] * len(row)

# --- CARGA DE DATOS ---
@st.cache_data(ttl=300) 
def load_data():
    for f in ["Tickets año.xlsx", "Tickets año.xls", "Tickets año.csv"]:
        if os.path.exists(f):
            df = pd.read_excel(f) if 'xls' in f else pd.read_csv(f)
            df.columns = df.columns.str.strip()
            for c in ['INICIO', 'FIN', 'CORREO']:
                if c in df.columns: df[c] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')
            if 'INICIO' in df.columns and 'FIN' in df.columns:
                df['DIAS'] = df.apply(lambda x: contar_dias_habiles(x['INICIO'], x['FIN']) if pd.notnull(x['FIN']) else np.nan, axis=1)
            col_gen_real = next((col for col in df.columns if "GENERACI" in col.upper()), 'Generacion_Excel')
            df.rename(columns={col_gen_real: 'Generacion_Excel'}, inplace=True)
            return df
    return None

@st.cache_data(ttl=300)
def load_escalados():
    if os.path.exists("Datos escalados.xlsx"):
        df = pd.read_excel("Datos escalados.xlsx")
        df.columns = [str(c).strip() for c in df.columns]
        col_ini = next((c for c in df.columns if c.lower() == 'inicio'), None)
        if col_ini:
            df[col_ini] = pd.to_datetime(df[col_ini], dayfirst=True, errors='coerce')
            df['dias_transcurridos'] = df[col_ini].apply(lambda x: contar_dias_habiles(x, pd.Timestamp.now()))
        return df
    return None

# --- SIDEBAR ---
st.sidebar.title("Menú Principal")
pagina = st.sidebar.radio("Selecciona:", ["1. Generación", "2. Solución", "3. Contacto", "4. Resumen Anual", "5. Escalados"])
selected_year = st.sidebar.selectbox("Año", [2025, 2026], index=1)

df = load_data()

if df is not None:
    ahora = pd.Timestamp.now()
    meses_map = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
    
    if pagina in ["1. Generación", "2. Solución", "3. Contacto"]:
        limite_mes = ahora.month if selected_year == ahora.year else 13
        meses_disp_nums = [m for m in range(1, limite_mes)]
        
        if not meses_disp_nums:
            st.info(f"Sin meses cerrados para {selected_year}.")
        else:
            meses_disp_names = [meses_map[m] for m in meses_disp_nums]
            selected_month_name = st.sidebar.selectbox("Mes", meses_disp_names, index=len(meses_disp_names)-1)
            selected_month_num = next(k for k,v in meses_map.items() if v==selected_month_name)
            
            inicio_mes = pd.Timestamp(selected_year, selected_month_num, 1)
            fin_mes = pd.Timestamp(selected_year, selected_month_num, monthrange(selected_year, selected_month_num)[1], 23, 59, 59)
            
            df_f = df[(df['INICIO'] <= fin_mes) & ((df['FIN'].isnull()) | (df['FIN'] >= inicio_mes))].copy()
            df_f['Estatus_Solucion'] = df_f.apply(lambda x: calcular_estatus_solucion(x, fin_mes, inicio_mes), axis=1)
            df_f = df_f[df_f['Estatus_Solucion'] != 'IGNORAR']
            df_f['Detalle_Solucion'] = df_f.apply(calcular_detalle_solucion, axis=1)
            if 'DIAS PRIMER CONTACTO' in df_f.columns:
                df_f['Estatus_Contacto'] = df_f['DIAS PRIMER CONTACTO'].apply(calcular_contacto)

            st.title(f"📊 {pagina} - {selected_month_name} {selected_year}")

            if pagina == "1. Generación":
                d = df_f['Generacion_Excel'].value_counts().reset_index()
                fig = px.pie(d, values='count', names='Generacion_Excel', hole=0.5, color='Generacion_Excel', 
                             color_discrete_map={'A tiempo': '#4472C4', 'Mismo día': '#ED7D31', 'Fuera': '#FFC000'})
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("Ver Detalle"): st.dataframe(df_f.style.apply(estilo_generacion, axis=1), use_container_width=True)

            elif pagina == "2. Solución":
                conteo = df_f['Estatus_Solucion'].value_counts()
                ids, labels, parents, values, colors = [], [], [], [], []
                # MAPA DE COLORES ORIGINAL
                c_map = {'Dentro': '#4472C4', 'Acumulado': '#FFC000', 'Fuera': '#ED7D31', 'Asap': '#ED7D31', 'Programado': '#70AD47'}

                for n in ['Dentro', 'Acumulado', 'Fuera']:
                    if n in conteo:
                        ids.append(n); labels.append(n); parents.append(""); values.append(conteo[n]); colors.append(c_map[n])
                
                df_fuera = df_f[df_f['Estatus_Solucion'] == 'Fuera']
                for subtipo, cant in df_fuera['Detalle_Solucion'].value_counts().items():
                    ids.append(f"F_{subtipo}"); labels.append(subtipo); parents.append("Fuera"); values.append(cant)
                    colors.append(c_map['Programado'] if 'Programado' in str(subtipo) else c_map['Asap'])
                
                fig = go.Figure(go.Sunburst(ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
                    marker=dict(colors=colors, line=dict(color='#ffffff', width=2)), leaf=dict(opacity=1),
                    textinfo="label+value+percent entry"))
                # AUMENTO DE TAMAÑO Y AJUSTE DE MÁRGENES
                fig.update_layout(height=850, margin=dict(t=10, l=10, r=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("Ver Detalle"): st.dataframe(df_f.style.apply(estilo_solucion, axis=1), use_container_width=True)

            elif pagina == "3. Contacto":
                if 'Estatus_Contacto' in df_f.columns:
                    d = df_f['Estatus_Contacto'].value_counts().reset_index()
                    fig = px.pie(d, values='count', names='Estatus_Contacto', hole=0.5, color='Estatus_Contacto',
                                 color_discrete_map={'A tiempo':'#4472C4', 'Fuera':'#ED7D31'})
                    st.plotly_chart(fig, use_container_width=True)
                    with st.expander("Ver Detalle"): st.dataframe(df_f.style.apply(estilo_contacto, axis=1), use_container_width=True)

            # Botón Lucid
            link = LINKS_TIMELINE.get((selected_year, selected_month_num))
            if link:
                st.markdown(f'<a href="{link}" target="_blank" class="timeline-link">🔗 Ver Línea de Tiempo - {selected_month_name}</a>', unsafe_allow_html=True)

    elif pagina == "5. Escalados":
        st.title("🚀 Reporte de Tickets Escalados (Histórico)")
        df_esc = load_escalados()
        if df_esc is not None:
            col_mot = next((c for c in df_esc.columns if c.lower() == 'motivo'), 'Motivo')
            categorias = df_esc[col_mot].unique()
            color_map = {cat: px.colors.qualitative.Prism[i % 11] for i, cat in enumerate(categorias)}
            c1, c2 = st.columns(2)
            with c1:
                df_f_esc = df_esc[df_esc['dias_transcurridos'] > 7]
                if not df_f_esc.empty:
                    fig1 = px.pie(df_f_esc, names=col_mot, hole=0.4, title="Fuera de Tiempo (> 7 días)", color=col_mot, color_discrete_map=color_map)
                    st.plotly_chart(fig1, use_container_width=True)
            with c2:
                df_d_esc = df_esc[df_esc['dias_transcurridos'] <= 7]
                if not df_d_esc.empty:
                    fig2 = px.pie(df_d_esc, names=col_mot, hole=0.4, title="En Tiempo (≤ 7 días)", color=col_mot, color_discrete_map=color_map)
                    st.plotly_chart(fig2, use_container_width=True)
            st.markdown("---")
            st.dataframe(df_esc.sort_values(by='dias_transcurridos', ascending=False).style.apply(estilo_escalados_suave, axis=1), use_container_width=True)

    elif pagina == "4. Resumen Anual":
        st.title(f"📈 Resumen Anual {selected_year}")
        df_anual = df[df['FIN'].dt.year == selected_year].copy()
        if not df_anual.empty:
            total = len(df_anual); tiempo = len(df_anual[df_anual['DIAS'] <= 7])
            st.metric("Eficiencia Anual", f"{(tiempo/total*100):.1f}%")
            df_anual['Cumple'] = df_anual['DIAS'].apply(lambda x: 1 if x <= 7 else 0)
            tendencia = df_anual.groupby(df_anual['FIN'].dt.month)['Cumple'].mean() * 100
            fig_line = px.line(x=[meses_map[m] for m in tendencia.index if m in meses_map], y=tendencia.values, markers=True)
            st.plotly_chart(fig_line, use_container_width=True)
else:
    st.error("Archivo 'Tickets año.xlsx' no encontrado.")
