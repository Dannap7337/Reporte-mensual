import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import numpy as np
from calendar import monthrange

st.set_page_config(page_title="Reporte TI", layout="wide")

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
    div.stButton > button:first-child {
        background-color: #28a745;
        color: white;
        border: none;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #218838;
        color: white;
        border: none;
    }
    [data-testid="stMetricValue"] {
        font-size: 26px;
    }
    .timeline-link {
        font-size: 16px;
        font-weight: bold;
        color: #4472C4 !important;
        text-decoration: none;
        padding: 8px 15px;
        border: 2px solid #4472C4;
        border-radius: 8px;
        display: inline-block;
        margin-top: 15px;
        transition: all 0.3s ease;
    }
    .timeline-link:hover {
        background-color: #4472C4;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE LÓGICA ---

def calcular_estatus_solucion(row, fecha_limite, fecha_inicio_mes):
    inicio = row['INICIO']
    fin = row['FIN']
    dias_totales_excel = row['DIAS'] if pd.notnull(row['DIAS']) else 0
    txt = str(row['RANGO']).lower()
    
    sigue_abierto_al_corte = pd.isna(fin) or (fin > fecha_limite)
    if sigue_abierto_al_corte:
        if pd.notnull(inicio):
            dias_al_momento = (fecha_limite - inicio).days
            if dias_al_momento <= 7:
                return "Dentro"
            elif inicio >= fecha_inicio_mes:
                return "Acumulado"
        return "IGNORAR"

    if dias_totales_excel <= 7:
        return "Dentro"
    
    return "Fuera"

def calcular_detalle_solucion(row):
    padre = row['Estatus_Solucion']
    if padre == 'Fuera':
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
    r = int(hex_code[0:2], 16)
    g = int(hex_code[2:4], 16)
    b = int(hex_code[4:6], 16)
    return f'rgba({r}, {g}, {b}, {opacity})'

def estilo_generacion(row):
    val = str(row['Generacion_Excel'])
    color_hex = ''
    if 'A tiempo' in val: color_hex = '#4472C4'
    elif 'Mismo día' in val or 'Mismo dia' in val: color_hex = '#ED7D31'
    elif 'Fuera' in val: color_hex = '#FFC000'
    elif 'Programado' in val: color_hex = '#A5A5A5'
    
    if color_hex:
        rgba = hex_to_rgba(color_hex, 0.4)
        return [f'background-color: {rgba}; color: black'] * len(row)
    return [''] * len(row)

def estilo_solucion(row):
    estatus = row['Estatus_Solucion']
    detalle = str(row['Detalle_Solucion'])
    color_hex = ''
    if estatus == 'Dentro': color_hex = '#4472C4'
    elif estatus == 'Acumulado': color_hex = '#FFC000'
    elif estatus == 'Fuera':
        if 'Asap' in detalle: color_hex = '#A5A5A5'
        elif 'Programado' in detalle: color_hex = '#70AD47'
        else: color_hex = '#ED7D31'
            
    if color_hex:
        rgba = hex_to_rgba(color_hex, 0.4)
        return [f'background-color: {rgba}; color: black'] * len(row)
    return [''] * len(row)

def estilo_contacto(row):
    val = row['Estatus_Contacto']
    color_hex = ''
    if val == 'A tiempo': color_hex = '#4472C4'
    elif val == 'Fuera': color_hex = '#ED7D31'
    if color_hex:
        rgba = hex_to_rgba(color_hex, 0.4)
        return [f'background-color: {rgba}; color: black'] * len(row)
    return [''] * len(row)

# --- CARGA DE DATOS ---
@st.cache_data(ttl=300) 
def load_data():
    posibles = ["Tickets año.xlsx", "Tickets año.xls", "Tickets año.csv"]
    archivo_encontrado = None
    for f in posibles:
        if os.path.exists(f):
            archivo_encontrado = f
            break
            
    if archivo_encontrado:
        try: 
            df = pd.read_excel(archivo_encontrado) if 'xls' in archivo_encontrado else pd.read_csv(archivo_encontrado)
            df.columns = df.columns.str.strip()
            for c in ['INICIO', 'FIN', 'CORREO']:
                if c in df.columns: 
                    df[c] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')
            
            col_gen_real = next((col for col in df.columns if "GENERACI" in col.upper() and "TICKET" in col.upper()), None)
            if col_gen_real:
                df.rename(columns={col_gen_real: 'Generacion_Excel'}, inplace=True)
            else:
                df['Generacion_Excel'] = "No encontrado"
            return df
        except: return None
    return None

@st.cache_data
def get_data_mensual(df, year, month_num):
    inicio_mes = pd.Timestamp(year, month_num, 1)
    ultimo_dia = monthrange(year, month_num)[1]
    fin_mes = pd.Timestamp(year, month_num, ultimo_dia, 23, 59, 59)

    cond_inicio = df['INICIO'] <= fin_mes
    cond_fin = (df['FIN'].isnull()) | (df['FIN'] >= inicio_mes)
    df_f = df[cond_inicio & cond_fin].copy()
    
    df_f['Estatus_Solucion'] = df_f.apply(lambda x: calcular_estatus_solucion(x, fin_mes, inicio_mes), axis=1)
    df_f = df_f[df_f['Estatus_Solucion'] != 'IGNORAR']
    df_f['Detalle_Solucion'] = df_f.apply(calcular_detalle_solucion, axis=1)
    
    if 'DIAS PRIMER CONTACTO' in df_f.columns:
        df_f['Estatus_Contacto'] = df_f['DIAS PRIMER CONTACTO'].apply(calcular_contacto)
        
    return df_f, inicio_mes, fin_mes

# --- APP ---
df = load_data()

if df is not None:
    st.sidebar.title("Menú Principal")
    pagina = st.sidebar.radio("Selecciona:", ["1. Generación", "2. Solución", "3. Contacto", "4. Resumen Anual"])
    
    all_years = [2025, 2026]
    selected_year = st.sidebar.selectbox("Año", all_years, index=len(all_years)-1)

    # --- LÓGICA DE FILTRADO POR MESES CONCLUIDOS ---
    ahora = pd.Timestamp.now()
    mes_actual = ahora.month
    anio_actual = ahora.year

    meses_map = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio',
                 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
    
    start_year = pd.Timestamp(selected_year, 1, 1)
    end_year = pd.Timestamp(selected_year, 12, 31, 23, 59, 59)
    df_y = df[(df['INICIO'] <= end_year) & ((df['FIN'].isnull()) | (df['FIN'] >= start_year))]
    meses_con_datos = set(df_y['INICIO'].dt.month.dropna().unique())

    lista_meses_nums = []
    for m in sorted(list(meses_con_datos)):
        if selected_year < anio_actual:
            lista_meses_nums.append(int(m))
        elif selected_year == anio_actual and m < mes_actual:
            lista_meses_nums.append(int(m))

    meses_disp = [meses_map[m] for m in lista_meses_nums if m in meses_map]

    if pagina != "4. Resumen Anual":
        if not meses_disp:
            st.title("Reporte TI")
            st.info(f"Aún no hay meses cerrados para mostrar en el año {selected_year}.")
        else:
            selected_month_name = st.sidebar.selectbox("Mes", meses_disp, index=len(meses_disp)-1)
            selected_month_num = [k for k,v in meses_map.items() if v==selected_month_name][0]

            df_f, inicio_mes, fin_mes = get_data_mensual(df, selected_year, selected_month_num)

            st.title(f"📊 {pagina}")
            st.caption(f"Datos de {selected_month_name} {selected_year}")

            # --- PÁGINA 1: GENERACIÓN ---
            if pagina == "1. Generación":
                col_kpi = 'Generacion_Excel'
                if col_kpi in df_f.columns and not df_f[col_kpi].isnull().all():
                    d = df_f[col_kpi].value_counts().reset_index()
                    d.columns=['E','C']
                    color_gen = {'A tiempo': '#4472C4', 'Mismo día': '#ED7D31', 'Fuera': '#FFC000', 'Programados': '#A5A5A5'}
                    fig = px.pie(d, values='C', names='E', color='E', color_discrete_map=color_gen, hole=0.5)
                    fig.update_layout(height=600, font=dict(size=20))
                    fig.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#ffffff', width=2)))
                    st.plotly_chart(fig, use_container_width=True)
                    with st.expander("Ver Detalle de Tickets"):
                        st.dataframe(df_f[['N° TICKET', 'USUARIO', 'INICIO', col_kpi]].style.apply(estilo_generacion, axis=1))

            # --- PÁGINA 2: SOLUCIÓN (RESTAURADA AL 100% ESTÉTICA) ---
            elif pagina == "2. Solución":
                if not df_f.empty:
                    conteo_padres = df_f['Estatus_Solucion'].value_counts()
                    df_fuera = df_f[df_f['Estatus_Solucion'] == 'Fuera']
                    conteo_hijos = df_fuera['Detalle_Solucion'].value_counts()
                    
                    ids, labels, parents, values, colors = [], [], [], [], []
                    if 'Dentro' in conteo_padres:
                        ids.append("Dentro"); labels.append("Dentro"); parents.append(""); values.append(conteo_padres['Dentro']); colors.append('#4472C4')
                    if 'Acumulado' in conteo_padres:
                        ids.append("Acumulado"); labels.append("Acumulado"); parents.append(""); values.append(conteo_padres['Acumulado']); colors.append('#FFC000')

                    if not df_fuera.empty:
                        ids.append("Fuera"); labels.append("Fuera"); parents.append(""); values.append(len(df_fuera)); colors.append('#ED7D31')
                        for subtipo, cant in conteo_hijos.items():
                            ids.append(f"Fuera - {subtipo}"); labels.append(subtipo); parents.append("Fuera"); values.append(cant)
                            c = '#A5A5A5' if 'Asap' in str(subtipo) else ('#70AD47' if 'Programado' in str(subtipo) else '#ED7D31')
                            colors.append(c)

                    # SUNBURST CONFIGURACIÓN ORIGINAL
                    fig = go.Figure(go.Sunburst(
                        ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
                        marker=dict(colors=colors, line=dict(color='#ffffff', width=2)),
                        textinfo="label+value+percent root", insidetextorientation='auto'
                    ))
                    # LÍNEA CRUCIAL PARA COLORES VIBRANTES (No opacos)
                    fig.update_traces(leaf=dict(opacity=1), opacity=1)
                    # TAMAÑO ORIGINAL
                    fig.update_layout(height=850, margin=dict(t=10, l=10, r=10, b=10), font=dict(size=18, family="Arial"))
                    st.plotly_chart(fig, use_container_width=True)

                    st.markdown("---")
                    st.subheader(f"⚠️ Top 5 Tickets cerrados con mayor demora ({selected_month_name})")
                    if 'DIAS' in df_f.columns:
                        mask_cerrados = (df_f['FIN'].dt.month == selected_month_num) & (df_f['FIN'].dt.year == selected_year)
                        df_peores = df_f[mask_cerrados & df_f['DIAS'].notnull()].sort_values(by='DIAS', ascending=False).head(5)
                        if not df_peores.empty:
                            st.table(df_peores[['N° TICKET', 'USUARIO', 'INICIO', 'FIN', 'DIAS', 'Detalle_Solucion']].style.format({"DIAS": "{:.0f}", "FIN": "{:%d-%m-%Y}"}))
                            enlace = LINKS_TIMELINE.get((selected_year, selected_month_num))
                            if enlace: st.markdown(f'<a href="{enlace}" class="timeline-link" target="_blank">📅 Ver Línea de Tiempo: TOP 5 tickets</a>', unsafe_allow_html=True)
                    
                    with st.expander("Ver Detalle de Tickets"):
                        st.dataframe(df_f[['N° TICKET', 'USUARIO', 'INICIO', 'FIN', 'DIAS', 'RANGO', 'Estatus_Solucion', 'Detalle_Solucion']].style.apply(estilo_solucion, axis=1))

            # --- PÁGINA 3: CONTACTO ---
            elif pagina == "3. Contacto":
                if selected_year == 2025 and selected_month_num < 5:
                    st.warning("KPI implementado a partir de Mayo 2025.")
                elif 'Estatus_Contacto' in df_f.columns:
                    d = df_f['Estatus_Contacto'].value_counts().reset_index()
                    d.columns=['E','C']
                    fig = px.pie(d, values='C', names='E', color='E', color_discrete_map={'A tiempo':'#4472C4', 'Fuera':'#ed7d31'}, hole=0.5)
                    fig.update_layout(height=600, font=dict(size=20))
                    fig.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#ffffff', width=2)))
                    st.plotly_chart(fig, use_container_width=True)
                    with st.expander("Ver Detalle de Tickets"):
                        st.dataframe(df_f[['N° TICKET', 'USUARIO', 'INICIO', 'DIAS PRIMER CONTACTO', 'Estatus_Contacto']].style.apply(estilo_contacto, axis=1))

    # --- PÁGINA 4: RESUMEN ANUAL ---
    else:
        st.title(f"📈 Resumen Anual {selected_year}")
        df_anual = df[df['FIN'].dt.year == selected_year].copy()
        if not df_anual.empty:
            c1, c2, c3 = st.columns(3)
            total_anual = len(df_anual)
            tiempo_anual = len(df_anual[df_anual['DIAS'] <= 7])
            eff_anual = (tiempo_anual / total_anual * 100) if total_anual > 0 else 0
            c1.metric(f"Total Tickets {selected_year}", total_anual)
            c2.metric("Promedio Eficiencia Anual", f"{eff_anual:.1f}%")

            st.markdown("---")
            st.markdown("### 📈 Tendencia: Tickets Cerrados en Tiempo (7 días)")
            df_anual['Cumple'] = df_anual['DIAS'].apply(lambda x: 1 if x <= 7 else 0)
            tendencia = df_anual.groupby(df_anual['FIN'].dt.month)['Cumple'].mean() * 100
            if selected_year == anio_actual:
                tendencia = tendencia[tendencia.index < mes_actual]

            fig_line = px.line(x=[meses_map[m] for m in tendencia.index], y=tendencia.values, markers=True, text=[f"{v:.1f}%" for v in tendencia.values])
            fig_line.update_traces(line_color='#4472C4', line_width=4, marker_size=12, textposition='top center')
            fig_line.update_layout(yaxis_title="% Eficiencia Solución", xaxis_title=None, yaxis_range=[0, 115], font=dict(size=16), height=450)
            st.plotly_chart(fig_line, use_container_width=True)
else:
    st.error("No se encontró 'Tickets año.xlsx'")
