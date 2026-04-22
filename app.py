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

# --- FUNCIONES DE ESTILO (COLORES SÓLIDOS 1.0) ---
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

def estilo_escalados_vivos(row):
    color = '#DC3545' if row['dias_transcurridos'] > 7 else '#28A745'
    return [f'background-color: {color}; color: white; font-weight: bold'] * len(row)

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

# --- SIDEBAR ---
st.sidebar.title("Menú Principal")
pagina = st.sidebar.radio("Selecciona:", ["1. Generación", "2. Solución", "3. Contacto", "4. Resumen Anual", "5. Escalados"])
selected_year = st.sidebar.selectbox("Año", [2025, 2026], index=1)

df = load_data()

if df is not None:
    ahora = pd.Timestamp.now()
    # Lógica de meses cerrados (Hoy es Abril 2026, mostrar hasta Marzo)
    meses_map = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
    
    if pagina in ["1. Generación", "2. Solución", "3. Contacto"]:
        if selected_year == ahora.year:
            meses_validos = list(range(1, ahora.month)) # 1 a 3 si es Abril
        elif selected_year < ahora.year:
            meses_validos = list(range(1, 13))
        else:
            meses_validos = []

        if not meses_validos:
            st.info(f"Sin meses cerrados para {selected_year}.")
        else:
            meses_disp = [meses_map[m] for m in meses_validos]
            selected_month_name = st.sidebar.selectbox("Mes", meses_disp, index=len(meses_disp)-1)
            selected_month_num = next(k for k,v in meses_map.items() if v==selected_month_name)
            
            inicio_mes = pd.Timestamp(selected_year, selected_month_num, 1)
            fin_mes = pd.Timestamp(selected_year, selected_month_num, monthrange(selected_year, selected_month_num)[1], 23, 59, 59)
            
            df_f = df[(df['INICIO'] <= fin_mes) & ((df['FIN'].isnull()) | (df['FIN'] >= inicio_mes))].copy()
            df_f['Estatus_Solucion'] = df_f.apply(lambda x: calcular_estatus_solucion(x, fin_mes, inicio_mes), axis=1)
            df_f = df_f[df_f['Estatus_Solucion'] != 'IGNORAR']
            df_f['Detalle_Solucion'] = df_f.apply(calcular_detalle_solucion, axis=1)
            if 'DIAS PRIMER CONTACTO' in df_f.columns:
                df_f['Estatus_Contacto'] = df_f['DIAS PRIMER CONTACTO'].apply(calcular_contacto)

            st.title(f"📊 {pagina} - {selected_month_name}")

            if pagina == "1. Generación":
                d = df_f['Generacion_Excel'].value_counts().reset_index()
                d.columns=['E','C']
                fig = px.pie(d, values='C', names='E', hole=0.5, color='E', color_discrete_map={'A tiempo': '#4472C4', 'Mismo día': '#ED7D31', 'Fuera': '#FFC000', 'Programados': '#A5A5A5'})
                fig.update_traces(opacity=1)
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("Ver Detalle"): st.dataframe(df_f.style.apply(estilo_generacion, axis=1), use_container_width=True)

            elif pagina == "2. Solución":
                conteo_padres = df_f['Estatus_Solucion'].value_counts()
                df_fuera = df_f[df_f['Estatus_Solucion'] == 'Fuera']
                ids, labels, parents, values, colors = [], [], [], [], []
                
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
                
                fig = go.Figure(go.Sunburst(ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
                    marker=dict(colors=colors, line=dict(color='#ffffff', width=2)), leaf=dict(opacity=1)))
                fig.update_layout(height=700)
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("Ver Detalle"): st.dataframe(df_f.style.apply(estilo_solucion, axis=1), use_container_width=True)

            elif pagina == "3. Contacto":
                if 'Estatus_Contacto' in df_f.columns:
                    d = df_f['Estatus_Contacto'].value_counts().reset_index()
                    d.columns=['E','C']
                    fig = px.pie(d, values='C', names='E', hole=0.5, color='E', color_discrete_map={'A tiempo':'#4472C4', 'Fuera':'#ed7d31'})
                    fig.update_traces(opacity=1)
                    st.plotly_chart(fig, use_container_width=True)
                    with st.expander("Ver Detalle"): st.dataframe(df_f.style.apply(estilo_contacto, axis=1), use_container_width=True)

    elif pagina == "5. Escalados":
        st.title("🚀 Reporte de Tickets Escalados (Histórico Total)")
        df_esc = load_escalados()
        if df_esc is not None:
            col_mot = next((c for c in df_esc.columns if c.lower() == 'motivo'), 'Motivo')
            
            # Mapa de colores consistente para los dos gráficos de Escalados
            categorias = df_esc[col_mot].unique()
            color_map = {cat: px.colors.qualitative.Prism[i % len(px.colors.qualitative.Prism)] for i, cat in enumerate(categorias)}

            df_f_esc = df_esc[df_esc['dias_transcurridos'] > 7]
            df_d_esc = df_esc[df_esc['dias_transcurridos'] <= 7]

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("⚠️ Fuera de Tiempo (> 7 días)")
                if not df_f_esc.empty:
                    fig1 = px.pie(df_f_esc, names=col_mot, hole=0.4, color=col_mot, color_discrete_map=color_map)
                    fig1.update_traces(opacity=1)
                    st.plotly_chart(fig1, use_container_width=True)
                else: st.success("Sin tickets pendientes fuera de tiempo.")

            with c2:
                st.subheader("✅ En Tiempo (≤ 7 días)")
                if not df_d_esc.empty:
                    fig2 = px.pie(df_d_esc, names=col_mot, hole=0.4, color=col_mot, color_discrete_map=color_map)
                    fig2.update_traces(opacity=1)
                    st.plotly_chart(fig2, use_container_width=True)
                else: st.info("Sin tickets recientes.")
            
            st.markdown("---")
            st.subheader("📋 Detalle de Tickets Escalados")
            df_esc_sort = df_esc.sort_values(by='dias_transcurridos', ascending=False)
            st.dataframe(df_esc_sort.style.apply(estilo_escalados_vivos, axis=1), use_container_width=True)

    elif pagina == "4. Resumen Anual":
        st.title(f"📈 Resumen Anual {selected_year}")
        df_anual = df[df['FIN'].dt.year == selected_year].copy()
        if not df_anual.empty:
            total = len(df_anual)
            tiempo = len(df_anual[df_anual['DIAS'] <= 7])
            c1, c2 = st.columns(2)
            c1.metric(f"Total Tickets {selected_year}", total)
            c2.metric("Eficiencia Anual", f"{(tiempo/total*100):.1f}%")
            
            df_anual['Cumple'] = df_anual['DIAS'].apply(lambda x: 1 if x <= 7 else 0)
            tendencia = df_anual.groupby(df_anual['FIN'].dt.month)['Cumple'].mean() * 100
            fig_line = px.line(x=[meses_map[m] for m in tendencia.index], y=tendencia.values, markers=True)
            st.plotly_chart(fig_line, use_container_width=True)
else:
    st.error("No se encontró 'Tickets año.xlsx'")
