import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import numpy as np
from calendar import monthrange

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Reporte TI 2025", layout="wide")

# --- ESTILOS CSS ---
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
    </style>
""", unsafe_allow_html=True)

# --- CARGA DE DATOS ---
@st.cache_data
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
            st.error(f"Error al leer el archivo: {e}")
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

# --- LÓGICAS DE NEGOCIO ---
def calcular_estatus_solucion(row, fecha_limite):
    dias = row['DIAS'] if pd.notnull(row['DIAS']) else 0
    txt = str(row['RANGO']).lower()
    
    if dias > 7 and (pd.isna(row['FIN']) or row['FIN'] > fecha_limite):
        return "Acumulado"
    
    if dias > 7 and any(x in txt for x in ['fuera', 'asap', 'programado']):
        return "Fuera"
        
    return "Dentro"

def calcular_detalle_solucion(row):
    padre = row['Estatus_Solucion']
    if padre == 'Fuera':
        txt = str(row['RANGO']).lower()
        if 'program' in txt: return 'Programado'
        if 'asap' in txt: return 'Asap'
        return 'Fuera '
    return np.nan 

def calcular_contacto(dias):
    return "Fuera" if (pd.notnull(dias) and dias > 3) else "A tiempo"

# --- FUNCIONES DE ESTILO CON OPACIDAD ---

def hex_to_rgba(hex_code, opacity=0.4):
    """Convierte HEX a RGBA con opacidad ajustada"""
    hex_code = hex_code.lstrip('#')
    r = int(hex_code[0:2], 16)
    g = int(hex_code[2:4], 16)
    b = int(hex_code[4:6], 16)
    return f'rgba({r}, {g}, {b}, {opacity})'

def estilo_generacion(row):
    val = str(row['Generacion_Excel'])
    color_hex = ''
    
    if 'A tiempo' in val: color_hex = '#4472C4' # Azul
    elif 'Mismo día' in val or 'Mismo dia' in val: color_hex = '#ED7D31' # Naranja
    elif 'Fuera' in val: color_hex = '#FFC000' # Amarillo
    elif 'Programado' in val: color_hex = '#A5A5A5' # Gris
    
    if color_hex:
        # Usamos texto negro para que se lea bien sobre el fondo transparente
        rgba = hex_to_rgba(color_hex, 0.4) 
        return [f'background-color: {rgba}; color: black'] * len(row)
    return [''] * len(row)

def estilo_solucion(row):
    estatus = row['Estatus_Solucion']
    detalle = str(row['Detalle_Solucion'])
    color_hex = ''
    
    if estatus == 'Dentro': color_hex = '#4472C4' # Azul
    elif estatus == 'Acumulado': color_hex = '#FFC000' # Amarillo
    elif estatus == 'Fuera':
        if 'Asap' in detalle: color_hex = '#A5A5A5' # Gris
        elif 'Programado' in detalle: color_hex = '#70AD47' # Verde
        else: color_hex = '#ED7D31' # Naranja
            
    if color_hex:
        rgba = hex_to_rgba(color_hex, 0.4) # 40% opacidad
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

# --- APP ---
df = load_data()

if df is not None:
    st.sidebar.title("Menú Principal")
    if st.sidebar.button("🔄 Recargar Excel"):
        load_data.clear()
        st.rerun()

    st.sidebar.markdown("---")
    pagina = st.sidebar.radio("Selecciona:", ["1. Generación", "2. Solución", "3. Contacto", "4. Resumen Anual"])
    st.sidebar.markdown("---")
    
    # Filtros Globales
    selected_year = 2025
    datos_2025 = df[(df['INICIO'].dt.year == 2025) | (df['FIN'].dt.year == 2025)]
    
    if datos_2025.empty:
        st.sidebar.error("No se encontraron registros en 2025.")
        st.stop()
    
    # Selectores de Mes (Páginas 1, 2, 3)
    if pagina != "4. Resumen Anual":
        st.sidebar.selectbox("Año", [2025], disabled=True)
        
        meses_actividad = set()
        meses_actividad.update(df.loc[df['INICIO'].dt.year == 2025, 'INICIO'].dt.month.dropna().unique())
        meses_actividad.update(df.loc[df['FIN'].dt.year == 2025, 'FIN'].dt.month.dropna().unique())
        
        meses_map = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio',
                     7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
        
        lista_meses_nums = sorted(list(meses_actividad))
        meses_disp = [meses_map[m] for m in lista_meses_nums if m in meses_map]
        
        if not meses_disp:
            st.warning("Sin datos de actividad en 2025.")
            st.stop()

        selected_month_name = st.sidebar.selectbox("Mes", meses_disp)
        selected_month_num = [k for k,v in meses_map.items() if v==selected_month_name][0]

        cond_abierto = (df['INICIO'].dt.year == selected_year) & (df['INICIO'].dt.month == selected_month_num)
        cond_cerrado = (df['FIN'].dt.year == selected_year) & (df['FIN'].dt.month == selected_month_num)
        df_f = df[cond_abierto | cond_cerrado].copy()
        
        ultimo = monthrange(selected_year, selected_month_num)[1]
        limite = pd.Timestamp(selected_year, selected_month_num, ultimo, 23, 59, 59)

        # Cálculos KPI Mes
        df_f['Estatus_Solucion'] = df_f.apply(lambda x: calcular_estatus_solucion(x, limite), axis=1)
        df_f['Detalle_Solucion'] = df_f.apply(calcular_detalle_solucion, axis=1)
        
        if 'DIAS PRIMER CONTACTO' in df_f.columns:
            df_f['Estatus_Contacto'] = df_f['DIAS PRIMER CONTACTO'].apply(calcular_contacto)
            
        st.title(f"📊 {pagina}")
        st.caption(f"Datos de {selected_month_name} {selected_year}")

    else:
        st.title("📈 Resumen Anual 2025")
        st.caption("Evolución de eficiencia y métricas globales del año")

    # ---------------------------------------------------------
    # 1. GENERACIÓN
    # ---------------------------------------------------------
    if pagina == "1. Generación":
        col_kpi = 'Generacion_Excel'
        if col_kpi in df_f.columns and not df_f[col_kpi].isnull().all():
            d = df_f[col_kpi].value_counts().reset_index()
            d.columns=['E','C']
            color_gen = {
                'A tiempo': '#4472C4', 'Mismo día': '#ED7D31',
                'Fuera': '#FFC000', 'Programados': '#A5A5A5'
            }
            fig = px.pie(d, values='C', names='E', color='E', 
                         color_discrete_map=color_gen, hole=0.5)
            fig.update_layout(height=600, font=dict(size=20))
            fig.update_traces(
                textposition='inside', textinfo='percent+label', 
                marker=dict(line=dict(color='#ffffff', width=2))
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # --- TABLA DESPLEGABLE CON OPACIDAD ---
            with st.expander("Ver Detalle de Tickets"): 
                cols = ['N° TICKET', 'USUARIO', 'INICIO', col_kpi]
                df_show = df_f[[c for c in cols if c in df_f.columns]]
                st.dataframe(df_show.style.apply(estilo_generacion, axis=1))
        else:
            st.warning("No se encontró columna de Generación.")

    # ---------------------------------------------------------
    # 2. SOLUCIÓN
    # ---------------------------------------------------------
    elif pagina == "2. Solución":
        if not df_f.empty:
            conteo_padres = df_f['Estatus_Solucion'].value_counts()
            df_fuera = df_f[df_f['Estatus_Solucion'] == 'Fuera']
            conteo_hijos = df_fuera['Detalle_Solucion'].value_counts()

            # Colores Sólidos para el Gráfico
            C_DENTRO = '#4472C4'; C_ACUMULADO = '#FFC000'; C_FUERA_PADRE = '#ED7D31' 
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

            # --- TABLA DESPLEGABLE CON OPACIDAD ---
            with st.expander("Ver Detalle de Tickets"):
                cols = ['N° TICKET', 'USUARIO', 'INICIO', 'FIN', 'DIAS', 'RANGO', 'Estatus_Solucion', 'Detalle_Solucion']
                df_show = df_f[[c for c in cols if c in df_f.columns]]
                st.dataframe(df_show.style.apply(estilo_solucion, axis=1))

    # ---------------------------------------------------------
    # 3. CONTACTO
    # ---------------------------------------------------------
    elif pagina == "3. Contacto":
        if 'Estatus_Contacto' in df_f.columns:
            d = df_f['Estatus_Contacto'].value_counts().reset_index()
            d.columns=['E','C']
            color_con = {'A tiempo':'#4472C4', 'Fuera':'#ed7d31'}
            fig = px.pie(d, values='C', names='E', color='E', 
                         color_discrete_map=color_con, hole=0.5)
            fig.update_layout(height=600, font=dict(size=20))
            fig.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#ffffff', width=2)))
            st.plotly_chart(fig, use_container_width=True)
            
            # --- TABLA DESPLEGABLE CON OPACIDAD ---
            with st.expander("Ver Detalle de Tickets"):
                cols = ['N° TICKET', 'USUARIO', 'INICIO', 'DIAS PRIMER CONTACTO', 'Estatus_Contacto']
                df_show = df_f[[c for c in cols if c in df_f.columns]]
                st.dataframe(df_show.style.apply(estilo_contacto, axis=1))

    # ---------------------------------------------------------
    # 4. RESUMEN ANUAL
    # ---------------------------------------------------------
    elif pagina == "4. Resumen Anual":
        df_anual = df[df['FIN'].dt.year == 2025].copy()
        
        if not df_anual.empty:
            total_anual = len(df_anual)
            tiempo_anual = len(df_anual[df_anual['DIAS'] <= 7])
            eff_anual = (tiempo_anual / total_anual * 100) if total_anual > 0 else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Tickets 2025", total_anual)
            c2.metric("Promedio Eficiencia Anual", f"{eff_anual:.1f}%")
            
            st.markdown("---")
            st.markdown("### 📈 Tendencia: Tickets Cerrados en Tiempo (<= 7 días)")
            
            df_anual['Cumple'] = df_anual['DIAS'].apply(lambda x: 1 if x <= 7 else 0)
            tendencia = df_anual.groupby(df_anual['FIN'].dt.month)['Cumple'].mean() * 100
            tendencia = tendencia.reset_index()
            tendencia.columns = ['MesNum', 'Eficiencia']
            
            meses_map_graf = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio',
                              7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
            
            tendencia['Mes'] = tendencia['MesNum'].apply(lambda x: meses_map_graf.get(x, str(x)))
            tendencia = tendencia.sort_values('MesNum')

            fig_line = px.line(tendencia, x='Mes', y='Eficiencia', markers=True, text='Eficiencia')
            fig_line.update_traces(
                line_color='#4472C4', line_width=4, marker_size=12,
                texttemplate='%{y:.1f}%', textposition='top center'
            )
            fig_line.update_layout(
                yaxis_title="% Eficiencia Solución", xaxis_title=None,
                yaxis_range=[0, 115], font=dict(size=16), height=450, hovermode="x unified"
            )
            st.plotly_chart(fig_line, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 📞 Tendencia: Primer Contacto a Tiempo (<= 3 días)")
            
            if 'DIAS PRIMER CONTACTO' in df_anual.columns:
                df_anual['Contacto_Ok'] = df_anual['DIAS PRIMER CONTACTO'].apply(
                    lambda x: 1 if (pd.notnull(x) and x <= 3) else 0
                )
                tend_con = df_anual.groupby(df_anual['FIN'].dt.month)['Contacto_Ok'].mean() * 100
                tend_con = tend_con.reset_index()
                tend_con.columns = ['MesNum', 'Eficiencia_Contacto']
                tend_con['Mes'] = tend_con['MesNum'].apply(lambda x: meses_map_graf.get(x, str(x)))
                tend_con = tend_con.sort_values('MesNum')

                fig_line_con = px.line(tend_con, x='Mes', y='Eficiencia_Contacto', markers=True, text='Eficiencia_Contacto')
                fig_line_con.update_traces(
                    line_color='#00C853', line_width=4, marker_size=12,
                    texttemplate='%{y:.1f}%', textposition='top center'
                )
                fig_line_con.update_layout(
                    yaxis_title="% Eficiencia Contacto", xaxis_title=None,
                    yaxis_range=[0, 115], font=dict(size=16), height=450, hovermode="x unified"
                )
                st.plotly_chart(fig_line_con, use_container_width=True)
            
            with st.expander("Ver Datos Anuales"):
                cols = ['N° TICKET', 'USUARIO', 'INICIO', 'FIN', 'DIAS', 'RANGO']
                st.dataframe(df_anual[[c for c in cols if c in df_anual.columns]])
        else:
            st.info("No hay tickets cerrados en 2025.")

else:
    st.error("No se encontró 'Tickets año.xlsx'")