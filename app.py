import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import numpy as np
from calendar import monthrange

st.set_page_config(page_title="Reporte TI", layout="wide")

# --- CONFIGURACIÓN DE ENLACES (NUEVO) ---
# Agrega aquí tus enlaces. El formato es: (AÑO, MES): "URL"
LINKS_TIMELINE = {
    (2025, 8): "https://tu-enlace-agosto.com",
    (2025, 9): "https://tu-enlace-septiembre.com",
    (2025, 10): "https://tu-enlace-octubre.com",
    (2025, 11): "https://tu-enlace-noviembre.com",
    (2025, 12): "https://tu-enlace-diciembre.com",
    (2026, 1): "https://tu-enlace-enero-2026.com",
    (2026, 2): "https://tu-enlace-febrero-2026.com",
    # Agrega más meses aquí...
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
    
    # 1. ¿Estaba abierto al cierre del mes?
    sigue_abierto_al_corte = pd.isna(fin) or (fin > fecha_limite)

    if sigue_abierto_al_corte:
        if pd.notnull(inicio):
            dias_al_momento = (fecha_limite - inicio).days
        else:
            dias_al_momento = 0
        
        if dias_al_momento > 7:
            if pd.notnull(inicio) and (inicio >= fecha_inicio_mes):
                return "Acumulado"
            else:
                return "IGNORAR" 
        else:
            return "Dentro"

    else:
        # TICKET CERRADO EN EL MES
        es_fuera_rango = any(x in txt for x in ['fuera', 'asap', 'programado'])
        if dias_totales_excel > 7 or es_fuera_rango:
            return "Fuera"
        else:
            return "Dentro"

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

# --- CARGA DE DATOS (CACHÉ NIVEL 1: Lectura) ---
@st.cache_data(ttl=300) 
def load_data():
    df = None
    posibles = ["Tickets año.xlsx", "Tickets año.xls", "Tickets año.csv"]
    archivo_encontrado = None
    
    for f in posibles:
        if os.path.exists(f):
            archivo_encontrado = f
            break
            
    if archivo_encontrado:
        try: 
            df = pd.read_excel(archivo_encontrado) if 'xls' in archivo_encontrado else pd.read_csv(archivo_encontrado)
        except Exception as e:
            return None
    else:
        return None
    
    if df is not None:
        df.columns = df.columns.str.strip()
        for c in ['INICIO', 'FIN', 'CORREO']:
            if c in df.columns: 
                df[c] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')
        
        col_gen_real = None
        for col in df.columns:
            if "GENERACI" in col.upper() and "TICKET" in col.upper():
                col_gen_real = col
                break
        
        if col_gen_real:
            df.rename(columns={col_gen_real: 'Generacion_Excel'}, inplace=True)
        else:
            df['Generacion_Excel'] = "No encontrado"

    return df

# --- PROCESAMIENTO MENSUAL (CACHÉ NIVEL 2: Cálculos Pesados) ---
@st.cache_data
def get_data_mensual(df, year, month_num):
    inicio_mes = pd.Timestamp(year, month_num, 1)
    ultimo_dia = monthrange(year, month_num)[1]
    fin_mes = pd.Timestamp(year, month_num, ultimo_dia, 23, 59, 59)

    # Filtro fechas
    cond_inicio = df['INICIO'] <= fin_mes
    cond_fin = (df['FIN'].isnull()) | (df['FIN'] >= inicio_mes)
    
    df_f = df[cond_inicio & cond_fin].copy()
    
    # Cálculo pesado
    df_f['Estatus_Solucion'] = df_f.apply(lambda x: calcular_estatus_solucion(x, fin_mes, inicio_mes), axis=1)
    
    # Filtrar IGNORAR
    df_f = df_f[df_f['Estatus_Solucion'] != 'IGNORAR']
    
    # Cálculos secundarios
    df_f['Detalle_Solucion'] = df_f.apply(calcular_detalle_solucion, axis=1)
    
    if 'DIAS PRIMER CONTACTO' in df_f.columns:
        df_f['Estatus_Contacto'] = df_f['DIAS PRIMER CONTACTO'].apply(calcular_contacto)
        
    return df_f, inicio_mes, fin_mes

# --- APP ---
df = load_data()

if df is not None:
    st.sidebar.title("Menú Principal")
    
    st.sidebar.markdown("---")
    pagina = st.sidebar.radio("Selecciona:", ["1. Generación", "2. Solución", "3. Contacto", "4. Resumen Anual"])
    st.sidebar.markdown("---")
    
    all_years = [2025, 2026]
    selected_year = st.sidebar.selectbox("Año", all_years, index=len(all_years)-1)

    # Lógica de Fechas Global
    start_year = pd.Timestamp(selected_year, 1, 1)
    end_year = pd.Timestamp(selected_year, 12, 31, 23, 59, 59)
    
    # Determinar meses activos
    cond_activos = (
        (df['INICIO'] <= end_year) & 
        ((df['FIN'].isnull()) | (df['FIN'] >= start_year))
    )
    df_year_activity = df[cond_activos]
    meses_actividad = set()
    meses_actividad.update(df_year_activity.loc[df_year_activity['INICIO'].dt.year == selected_year, 'INICIO'].dt.month.dropna().unique())
    meses_actividad.update(df_year_activity.loc[df_year_activity['FIN'].dt.year == selected_year, 'FIN'].dt.month.dropna().unique())
    if not df_year_activity.loc[df_year_activity['INICIO'] < start_year].empty:
            meses_actividad.add(1)

    meses_map = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio',
                    7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
    
    lista_meses_nums = sorted([int(m) for m in meses_actividad if pd.notnull(m)])
    meses_disp = [meses_map[m] for m in lista_meses_nums if m in meses_map]
    if not meses_disp: meses_disp = ["Enero"] 

    if pagina != "4. Resumen Anual":
        selected_month_name = st.sidebar.selectbox("Mes", meses_disp, index=len(meses_disp)-1)
        selected_month_num = [k for k,v in meses_map.items() if v==selected_month_name][0]

        df_f, inicio_mes, fin_mes = get_data_mensual(df, selected_year, selected_month_num)

        st.title(f"📊 {pagina}")
        st.caption(f"Datos de {selected_month_name} {selected_year}")

    else:
        st.title(f"📈 Resumen Anual {selected_year}")
        st.caption("Evolución de eficiencia y métricas globales")

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
                cols = ['N° TICKET', 'USUARIO', 'INICIO', col_kpi]
                df_show = df_f[[c for c in cols if c in df_f.columns]]
                st.dataframe(df_show.style.apply(estilo_generacion, axis=1))
        else:
            st.warning("No se encontró columna de Generación.")

    # --- PÁGINA 2: SOLUCIÓN ---
    elif pagina == "2. Solución":
        if not df_f.empty:
            conteo_padres = df_f['Estatus_Solucion'].value_counts()
            df_fuera = df_f[df_f['Estatus_Solucion'] == 'Fuera']
            conteo_hijos = df_fuera['Detalle_Solucion'].value_counts()
            
            C_DENTRO = '#4472C4'
            C_ACUMULADO = '#FFC000' 
            C_FUERA_PADRE = '#ED7D31' 
            C_FUERA_REAL = '#ED7D31'; C_ASAP = '#A5A5A5'; C_PROG = '#70AD47'        
            
            ids, labels, parents, values, colors = [], [], [], [], []

            if 'Dentro' in conteo_padres:
                ids.append("Dentro"); labels.append("Dentro"); parents.append(""); values.append(conteo_padres['Dentro']); colors.append(C_DENTRO)
            if 'Acumulado' in conteo_padres:
                ids.append("Acumulado"); labels.append("Acumulado"); parents.append(""); values.append(conteo_padres['Acumulado']); colors.append(C_ACUMULADO)

            total_fuera = conteo_hijos.sum()
            if total_fuera > 0:
                ids.append("Fuera"); labels.append("Fuera"); parents.append(""); values.append(total_fuera); colors.append(C_FUERA_PADRE)
                for subtipo, cantidad in conteo_hijos.items():
                    ids.append(f"Fuera - {subtipo}"); labels.append(subtipo); parents.append("Fuera"); values.append(cantidad)
                    if 'Asap' in str(subtipo): c = C_ASAP
                    elif 'Programado' in str(subtipo): c = C_PROG
                    else: c = C_FUERA_REAL
                    colors.append(c)

            if len(ids) > 0:
                fig = go.Figure(go.Sunburst(
                    ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
                    marker=dict(colors=colors, line=dict(color='#ffffff', width=2)),
                    textinfo="label+value+percent root", insidetextorientation='auto'
                ))
                fig.update_traces(leaf=dict(opacity=1), opacity=1)
                fig.update_layout(height=850, margin=dict(t=10, l=10, r=10, b=10), font=dict(size=18, family="Arial"))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos.")
            
            # --- SECCIÓN: 5 PEORES TICKETS ---
            if selected_month_num >= 1: 
                st.markdown("---")
                st.subheader(f"⚠️ Top 5 Tickets cerrados con mayor demora ({selected_month_name})")
                
                if 'DIAS' in df_f.columns:
                    mask_cerrados = (df_f['FIN'].dt.month == selected_month_num) & (df_f['FIN'].dt.year == selected_year)
                    df_peores = df_f[mask_cerrados & df_f['DIAS'].notnull()].sort_values(by='DIAS', ascending=False).head(5)
                    
                    if not df_peores.empty:
                        cols_peores = ['N° TICKET', 'USUARIO', 'INICIO', 'FIN', 'DIAS', 'Detalle_Solucion']
                        cols_mostrar = [c for c in cols_peores if c in df_peores.columns]
                        st.table(df_peores[cols_mostrar].style.format({"DIAS": "{:.0f}", "FIN": "{:%d-%m-%Y}"}))

                        if (selected_year == 2025 and selected_month_num >= 8) or (selected_year > 2025):
                            enlace_actual = LINKS_TIMELINE.get((selected_year, selected_month_num))
                            
                            if enlace_actual:
                                st.markdown(
                                    f'<a href="{enlace_actual}" class="timeline-link" target="_blank">📅 Ver Línea de Tiempo: TOP 5 tickets</a>', 
                                    unsafe_allow_html=True
                                )
                            else:
                                st.caption("🚫 No hay enlace configurado para este mes aún.")

                    else:
                        st.info(f"No hay tickets cerrados en {selected_month_name} con información de días.")
                else:
                    st.warning("La columna 'DIAS' no existe en el archivo.")

            with st.expander("Ver Detalle de Tickets"):
                cols = ['N° TICKET', 'USUARIO', 'INICIO', 'FIN', 'DIAS', 'RANGO', 'Estatus_Solucion', 'Detalle_Solucion']
                df_show = df_f[[c for c in cols if c in df_f.columns]]
                st.dataframe(df_show.style.apply(estilo_solucion, axis=1))

    # --- PÁGINA 3: CONTACTO ---
    elif pagina == "3. Contacto":
        if selected_year == 2025 and selected_month_num < 5:
            st.warning(f"⚠️ **Información no disponible.**")
            st.info(f"El KPI de 'Primer Contacto' se implementó a partir de **Mayo de 2025**.")
        else:
            if 'Estatus_Contacto' in df_f.columns:
                d = df_f['Estatus_Contacto'].value_counts().reset_index()
                d.columns=['E','C']
                color_con = {'A tiempo':'#4472C4', 'Fuera':'#ed7d31'}
                fig = px.pie(d, values='C', names='E', color='E', 
                             color_discrete_map=color_con, hole=0.5)
                fig.update_layout(height=600, font=dict(size=20))
                fig.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#ffffff', width=2)))
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("Ver Detalle de Tickets"):
                    cols = ['N° TICKET', 'USUARIO', 'INICIO', 'DIAS PRIMER CONTACTO', 'Estatus_Contacto']
                    df_show = df_f[[c for c in cols if c in df_f.columns]]
                    st.dataframe(df_show.style.apply(estilo_contacto, axis=1))
            else:
                 st.info("No hay datos de contacto para este mes.")

    # --- PÁGINA 4: RESUMEN ANUAL ---
    elif pagina == "4. Resumen Anual":
        df_anual = df[df['FIN'].dt.year == selected_year].copy()
        
        if not df_anual.empty:
            total_anual = len(df_anual)
            tiempo_anual = len(df_anual[df_anual['DIAS'] <= 7])
            eff_anual = (tiempo_anual / total_anual * 100) if total_anual > 0 else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Total Tickets {selected_year}", total_anual)
            c2.metric("Promedio Eficiencia Anual", f"{eff_anual:.1f}%")
            
            st.markdown("---")
            st.markdown("### 📈 Tendencia: Tickets Cerrados en Tiempo (7 días)")
            
            df_anual['Cumple'] = df_anual['DIAS'].apply(lambda x: 1 if x <= 7 else 0)
            tendencia = df_anual.groupby(df_anual['FIN'].dt.month)['Cumple'].mean() * 100
            tendencia = tendencia.reset_index()
            tendencia.columns = ['MesNum', 'Eficiencia']
            
            meses_map_graf = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio',
                              7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
            
            tendencia['Mes'] = tendencia['MesNum'].apply(lambda x: meses_map_graf.get(x, str(x)))
            tendencia = tendencia.sort_values('MesNum')

            fig_line = px.line(tendencia, x='Mes', y='Eficiencia', markers=True, text='Eficiencia')
            fig_line.update_traces(line_color='#4472C4', line_width=4, marker_size=12, texttemplate='%{y:.1f}%', textposition='top center')
            fig_line.update_layout(yaxis_title="% Eficiencia Solución", xaxis_title=None, yaxis_range=[0, 115], font=dict(size=16), height=450, hovermode="x unified")
            st.plotly_chart(fig_line, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 📞 Tendencia: Primer Contacto a Tiempo (3 días)")
            st.caption("Nota: KPI implementado a partir de Mayo 2025.")
            
            if 'DIAS PRIMER CONTACTO' in df_anual.columns:
                df_anual['Contacto_Ok'] = df_anual['DIAS PRIMER CONTACTO'].apply(lambda x: 1 if (pd.notnull(x) and x <= 3) else 0)
                tend_con = df_anual.groupby(df_anual['FIN'].dt.month)['Contacto_Ok'].mean() * 100
                tend_con = tend_con.reset_index()
                tend_con.columns = ['MesNum', 'Eficiencia_Contacto']
                
                # Filtrar meses anteriores a mayo SOLO si estamos en 2025
                if selected_year == 2025:
                    tend_con = tend_con[tend_con['MesNum'] >= 5]
                    
                tend_con['Mes'] = tend_con['MesNum'].apply(lambda x: meses_map_graf.get(x, str(x)))
                tend_con = tend_con.sort_values('MesNum')
                
                if not tend_con.empty:
                    fig_line_con = px.line(tend_con, x='Mes', y='Eficiencia_Contacto', markers=True, text='Eficiencia_Contacto')
                    fig_line_con.update_traces(line_color='#00C853', line_width=4, marker_size=12, texttemplate='%{y:.1f}%', textposition='top center')
                    fig_line_con.update_layout(yaxis_title="% Eficiencia Contacto", xaxis_title=None, yaxis_range=[0, 115], font=dict(size=16), height=450, hovermode="x unified")
                    st.plotly_chart(fig_line_con, use_container_width=True)
                else:
                    st.info("No hay datos suficientes para generar la tendencia.")
            
            with st.expander("Ver Datos Anuales"):
                cols = ['N° TICKET', 'USUARIO', 'INICIO', 'FIN', 'DIAS', 'RANGO']
                st.dataframe(df_anual[[c for c in cols if c in df_anual.columns]])
        else:
            st.info(f"No hay tickets cerrados en {selected_year}.")

else:
    st.error("No se encontró 'Tickets año.xlsx'")
