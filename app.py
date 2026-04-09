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
    div.stButton > button:hover { background-color: #218838; color: white; border: none; }
    [data-testid="stMetricValue"] { font-size: 26px; }
    .timeline-link {
        font-size: 16px; font-weight: bold; color: #4472C4 !important; text-decoration: none;
        padding: 8px 15px; border: 2px solid #4472C4; border-radius: 8px; display: inline-block;
        margin-top: 15px; transition: all 0.3s ease;
    }
    .timeline-link:hover { background-color: #4472C4; color: white !important; }
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

# --- FUNCIONES DE ESTILO ---
def hex_to_rgba(hex_code, opacity=0.4):
    hex_code = hex_code.lstrip('#')
    r, g, b = int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)
    return f'rgba({r}, {g}, {b}, {opacity})'

def estilo_generacion(row):
    val = str(row['Generacion_Excel'])
    color_hex = '#4472C4' if 'A tiempo' in val else ('#ED7D31' if 'Mismo' in val else ('#FFC000' if 'Fuera' in val else '#A5A5A5'))
    return [f'background-color: {hex_to_rgba(color_hex, 0.4)}; color: black'] * len(row)

def estilo_solucion(row):
    estatus, detalle = row['Estatus_Solucion'], str(row['Detalle_Solucion'])
    color_hex = '#4472C4' if estatus == 'Dentro' else ('#FFC000' if estatus == 'Acumulado' else ('#A5A5A5' if 'Asap' in detalle else ('#70AD47' if 'Programado' in detalle else '#ED7D31')))
    return [f'background-color: {hex_to_rgba(color_hex, 0.4)}; color: black'] * len(row)

def estilo_contacto(row):
    color_hex = '#4472C4' if row['Estatus_Contacto'] == 'A tiempo' else '#ED7D31'
    return [f'background-color: {hex_to_rgba(color_hex, 0.4)}; color: black'] * len(row)

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

# --- SIDEBAR (SIEMPRE PRIMERO) ---
st.sidebar.title("Menú Principal")
pagina = st.sidebar.radio("Selecciona:", ["1. Generación", "2. Solución", "3. Contacto", "4. Resumen Anual", "5. Escalados"])
all_years = [2025, 2026]
selected_year = st.sidebar.selectbox("Año", all_years, index=len(all_years)-1)

# --- APP ---
df = load_data()

if df is not None:
    ahora = pd.Timestamp.now()
    mes_actual, anio_actual = ahora.month, ahora.year
    meses_map = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}

    # PÁGINAS MENSUALES (1, 2, 3)
    if pagina in ["1. Generación", "2. Solución", "3. Contacto"]:
        start_year, end_year = pd.Timestamp(selected_year, 1, 1), pd.Timestamp(selected_year, 12, 31, 23, 59, 59)
        df_y = df[(df['INICIO'] <= end_year) & ((df['FIN'].isnull()) | (df['FIN'] >= start_year))]
        meses_con_datos = sorted(df_y['INICIO'].dt.month.dropna().unique())
        lista_meses_nums = [int(m) for m in meses_con_datos if (selected_year < anio_actual) or (selected_year == anio_actual and m < mes_actual)]
        meses_disp = [meses_map[m] for m in lista_meses_nums if m in meses_map]

        if not meses_disp:
            st.info(f"Sin meses cerrados en {selected_year}.")
        else:
            selected_month_name = st.sidebar.selectbox("Mes", meses_disp, index=len(meses_disp)-1)
            selected_month_num = next(k for k,v in meses_map.items() if v==selected_month_name)
            df_f, _, _ = get_data_mensual(df, selected_year, selected_month_num)

            st.title(f"📊 {pagina}")
            st.caption(f"Datos de {selected_month_name} {selected_year}")

            if pagina == "1. Generación":
                d = df_f['Generacion_Excel'].value_counts().reset_index()
                d.columns=['E','C']
                fig = px.pie(d, values='C', names='E', hole=0.5, color='E', color_discrete_map={'A tiempo': '#4472C4', 'Mismo día': '#ED7D31', 'Fuera': '#FFC000', 'Programados': '#A5A5A5'})
                fig.update_layout(height=600, font=dict(size=20))
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("Ver Detalle"): st.dataframe(df_f[['N° TICKET', 'USUARIO', 'INICIO', 'Generacion_Excel']].style.apply(estilo_generacion, axis=1))

            elif pagina == "2. Solución":
                conteo_padres = df_f['Estatus_Solucion'].value_counts()
                df_fuera = df_f[df_f['Estatus_Solucion'] == 'Fuera']
                ids, labels, parents, values, colors = [], [], [], [], []
                if 'Dentro' in conteo_padres:
                    ids.append("Dentro"); labels.append("Dentro"); parents.append(""); values.append(conteo_padres['Dentro']); colors.append('#4472C4')
                if 'Acumulado' in conteo_padres:
                    ids.append("Acumulado"); labels.append("Acumulado"); parents.append(""); values.append(conteo_padres['Acumulado']); colors.append('#FFC000')
                if not df_fuera.empty:
                    ids.append("Fuera"); labels.append("Fuera"); parents.append(""); values.append(len(df_fuera)); colors.append('#ED7D31')
                    for subtipo, cant in df_fuera['Detalle_Solucion'].value_counts().items():
                        ids.append(f"Fuera - {subtipo}"); labels.append(subtipo); parents.append("Fuera"); values.append(cant)
                        colors.append('#A5A5A5' if 'Asap' in str(subtipo) else ('#70AD47' if 'Programado' in str(subtipo) else '#ED7D31'))
                
                fig = go.Figure(go.Sunburst(ids=ids, labels=labels, parents=parents, values=values, branchvalues="total", marker=dict(colors=colors, line=dict(color='#ffffff', width=2)), textinfo="label+value+percent root"))
                fig.update_layout(height=800, font=dict(size=18))
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("Ver Detalle"): st.dataframe(df_f[['N° TICKET', 'USUARIO', 'INICIO', 'FIN', 'DIAS', 'RANGO', 'Estatus_Solucion', 'Detalle_Solucion']].style.apply(estilo_solucion, axis=1))

            elif pagina == "3. Contacto":
                if 'Estatus_Contacto' in df_f.columns:
                    d = df_f['Estatus_Contacto'].value_counts().reset_index()
                    d.columns=['E','C']
                    fig = px.pie(d, values='C', names='E', hole=0.5, color='E', color_discrete_map={'A tiempo':'#4472C4', 'Fuera':'#ed7d31'})
                    fig.update_layout(height=600, font=dict(size=20))
                    st.plotly_chart(fig, use_container_width=True)
                    with st.expander("Ver Detalle"): st.dataframe(df_f[['N° TICKET', 'USUARIO', 'INICIO', 'DIAS PRIMER CONTACTO', 'Estatus_Contacto']].style.apply(estilo_contacto, axis=1))

    # PÁGINA 4: RESUMEN ANUAL
    elif pagina == "4. Resumen Anual":
        st.title(f"📈 Resumen Anual {selected_year}")
        df_anual = df[df['FIN'].dt.year == selected_year].copy()
        if not df_anual.empty:
            total, tiempo = len(df_anual), len(df_anual[df_anual['DIAS'] <= 7])
            c1, c2 = st.columns(2)
            c1.metric(f"Total Tickets {selected_year}", total)
            c2.metric("Promedio Eficiencia Anual", f"{(tiempo/total*100):.1f}%")
            st.markdown("### 📈 Tendencia: Tickets Cerrados en Tiempo (7 días hábiles)")
            df_anual['Cumple'] = df_anual['DIAS'].apply(lambda x: 1 if x <= 7 else 0)
            tendencia = df_anual.groupby(df_anual['FIN'].dt.month)['Cumple'].mean() * 100
            fig_line = px.line(x=[meses_map[m] for m in tendencia.index], y=tendencia.values, markers=True)
            st.plotly_chart(fig_line, use_container_width=True)

    # PÁGINA 5: ESCALADOS (ACTUALIZADA: HISTÓRICO COMPLETO + TABLA)
    elif pagina == "5. Escalados":
        st.title("🚀 Reporte de Tickets Escalados (Histórico)")
        df_esc = load_escalados()
        
        if df_esc is not None and 'dias_transcurridos' in df_esc.columns:
            # Identificar columna motivo
            col_mot = next((c for c in df_esc.columns if c.lower() == 'motivo'), 'Motivo')
            
            # --- SECCIÓN GRÁFICOS ---
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("⚠️ Fuera de Tiempo (> 7 días)")
                df_f = df_esc[df_esc['dias_transcurridos'] > 7]
                if not df_f.empty:
                    fig1 = px.pie(df_f, names=col_mot, hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
                    st.plotly_chart(fig1, use_container_width=True)
                else: st.success("Sin tickets pendientes mayores a 7 días.")

            with c2:
                st.subheader("✅ En Tiempo (≤ 7 días)")
                df_d = df_esc[df_esc['dias_transcurridos'] <= 7]
                if not df_d.empty:
                    fig2 = px.pie(df_d, names=col_mot, hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig2, use_container_width=True)
                else: st.info("Sin tickets escalados recientes.")
            
            # --- SECCIÓN TABLA DETALLE ---
            st.markdown("---")
            st.subheader("📋 Detalle de Tickets Escalados")
            
            # Estilo para la tabla de escalados
            def estilo_fila_escalados(row):
                color = '#f8d7da' if row['dias_transcurridos'] > 7 else '#d4edda'
                return [f'background-color: {color}; color: black'] * len(row)
            
            # Ordenar para que los más antiguos/urgentes salgan arriba
            df_esc_sort = df_esc.sort_values(by='dias_transcurridos', ascending=False)
            
            st.dataframe(
                df_esc_sort.style.apply(estilo_fila_escalados, axis=1),
                use_container_width=True
            )
        else:
            st.error("No se encontró 'Datos escalados.xlsx' o falta la columna 'inicio'.")
else:
    st.error("No se encontró 'Tickets año.xlsx'")
