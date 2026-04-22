import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import numpy as np
from calendar import monthrange
import unicodedata

st.set_page_config(page_title="Reporte TI", layout="wide")

# --- CONFIGURACIÓN DE FERIADOS ---
FERIADOS = [
    '2025-01-01', '2025-02-03', '2025-03-17', '2025-05-01', '2025-09-16', 
    '2025-11-17', '2025-12-25', '2026-01-01', '2026-02-02', '2026-03-16'
]
feriados_np = np.array(FERIADOS, dtype='datetime64[D]')

# --- ENLACES DE LÍNEAS DE TIEMPO ---
LINKS_TIMELINE = {
    (2025, 8): "https://lucid.app/lucidspark/543f6a91-1a33-4c3b-a36a-c1aa7ed7e063/edit?invitationId=inv_cc6d1591-c99a-4b82-b334-9898dbadd8b8",
    (2025, 9): "https://lucid.app/lucidspark/b6d966fe-81c8-4c80-b434-8b887b9f478c/edit?invitationId=inv_0789d6c9-c78c-43fa-b137-445bee6dd70c",
    (2025, 10): "https://lucid.app/lucidspark/fa0b5127-cb34-48b6-ab4d-760d38ac95d5/edit?invitationId=inv_f9d4919f-3afb-4862-8abd-a3fa7e90c52a",
    (2025, 11): "https://lucid.app/lucidspark/487992bf-7d7d-4eab-a389-6ccfae58c557/edit?invitationId=inv_25f6128c-a3ec-4f65-a58f-21be6ac896c6",
    (2025, 12): "https://lucid.app/lucidspark/fd3b8c79-5408-495f-b2ac-f1a58b043db7/edit?invitationId=inv_54a83472-e357-462a-9493-7172fe0b7757",
    (2026, 1): "https://lucid.app/lucidspark/7f65f049-6242-485e-ac78-31abe3bc87f3/edit?invitationId=inv_5568d403-e21a-4692-a3c7-70582e9cb58f",
    (2026, 2): "https://lucid.app/lucidspark/81cc3721-e383-4dad-a64f-25644745f3f6/edit?viewport_loc=728%2C-8296%2C11633%2C5008%2C0_0&invitationId=inv_e1b9573f-c69d-48dd-8bf7-f178d663d77e"
}

# --- FUNCIONES AUXILIARES ---
def limpiar_texto(texto):
    if pd.isna(texto): return ""
    texto = str(texto).lower().strip()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto

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
    return "Dentro" if (row['DIAS'] if pd.notnull(row['DIAS']) else 0) <= 7 else "Fuera"

def calcular_detalle_solucion(row):
    if 'Estatus_Solucion' in row and row['Estatus_Solucion'] == 'Fuera':
        gen_val = limpiar_texto(row.get('Generacion_Excel', ''))
        if 'mismo' in gen_val: return 'Asap'
        txt = limpiar_texto(row.get('RANGO', ''))
        if 'program' in txt: return 'Programado'
        return 'Asap'
    return np.nan 

# --- ESTILOS (OPACIDAD 0.3) ---
def hex_to_rgba(hex_code, opacity=0.3):
    hex_code = hex_code.lstrip('#')
    r, g, b = int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)
    return f'rgba({r}, {g}, {b}, {opacity})'

def estilo_generacion(row):
    val = limpiar_texto(row.get('Generacion_Excel', ''))
    if 'tiempo' in val: color = '#4472C4' 
    elif 'mismo' in val: color = '#A5A5A5' 
    else: color = '#ED7D31' 
    return [f'background-color: {hex_to_rgba(color)}; color: black'] * len(row)

def estilo_solucion(row):
    est = row.get('Estatus_Solucion', 'Fuera')
    det = str(row.get('Detalle_Solucion', '')).lower()
    color = '#4472C4' if est == 'Dentro' else ('#FFC000' if est == 'Acumulado' else ('#70AD47' if 'programado' in det else '#ED7D31'))
    return [f'background-color: {hex_to_rgba(color)}; color: black'] * len(row)

def estilo_contacto(row):
    color = '#4472C4' if row.get('Estatus_Contacto', '') == 'A tiempo' else '#ED7D31'
    return [f'background-color: {hex_to_rgba(color)}; color: black'] * len(row)

# --- CARGA DE DATOS ---
@st.cache_data(ttl=300) 
def load_data():
    for f in ["Tickets año.xlsx", "Tickets año.xls", "Tickets año.csv"]:
        if os.path.exists(f):
            df = pd.read_excel(f) if 'xls' in f else pd.read_csv(f)
            df.columns = df.columns.str.strip()
            for c in ['INICIO', 'FIN', 'CORREO']:
                if c in df.columns: df[c] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')
            df['DIAS'] = df.apply(lambda x: contar_dias_habiles(x['INICIO'], x['FIN']) if pd.notnull(x['FIN']) else np.nan, axis=1)
            col_gen = next((col for col in df.columns if "GENERACI" in col.upper()), 'Generacion_Excel')
            df.rename(columns={col_gen: 'Generacion_Excel'}, inplace=True)
            return df
    return None

@st.cache_data(ttl=300)
def load_escalados():
    if os.path.exists("Datos escalados.xlsx"):
        df = pd.read_excel("Datos escalados.xlsx")
        df.columns = df.columns.str.strip()
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
        limite = ahora.month if selected_year == ahora.year else 13
        meses_disp = [meses_map[m] for m in range(1, limite)]
        
        if meses_disp:
            sel_mes_nom = st.sidebar.selectbox("Mes", meses_disp, index=len(meses_disp)-1)
            sel_mes_num = next(k for k,v in meses_map.items() if v==sel_mes_nom)
            
            ini_m = pd.Timestamp(selected_year, sel_mes_num, 1)
            fin_m = pd.Timestamp(selected_year, sel_mes_num, monthrange(selected_year, sel_mes_num)[1], 23, 59)
            df_f = df[(df['INICIO'] <= fin_m) & ((df['FIN'].isnull()) | (df['FIN'] >= ini_m))].copy()
            df_f['Generacion_Excel_Clean'] = df_f['Generacion_Excel'].apply(limpiar_texto)
            df_f['Estatus_Solucion'] = df_f.apply(lambda x: calcular_estatus_solucion(x, fin_m, ini_m), axis=1)
            df_f = df_f[df_f['Estatus_Solucion'] != 'IGNORAR']
            df_f['Detalle_Solucion'] = df_f.apply(calcular_detalle_solucion, axis=1)
            if 'DIAS PRIMER CONTACTO' in df_f.columns:
                df_f['Estatus_Contacto'] = df_f['DIAS PRIMER CONTACTO'].apply(lambda x: "Fuera" if x > 3 else "A tiempo")

            st.title(f"📊 {pagina} - {sel_mes_nom} {selected_year}")

            if pagina == "1. Generación":
                d = df_f['Generacion_Excel_Clean'].value_counts().reset_index()
                name_map = {'a tiempo': 'A tiempo', 'mismo dia': 'Mismo día', 'programados': 'Programados'}
                d['Etiqueta'] = d['Generacion_Excel_Clean'].map(lambda x: name_map.get(x, 'Programados'))
                fig = px.pie(d, values='count', names='Etiqueta', hole=0.5, color='Etiqueta',
                             color_discrete_map={'A tiempo': '#4472C4', 'Mismo día': '#A5A5A5', 'Programados': '#ED7D31'})
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("Ver Detalle de Tabla"):
                    st.dataframe(df_f.style.apply(estilo_generacion, axis=1), use_container_width=True)

            elif pagina == "2. Solución":
                ids, labels, parents, values, colors = [], [], [], [], []
                c_sol = {'Dentro': '#4472C4', 'Acumulado': '#FFC000', 'Fuera': '#ED7D31', 'Asap': '#ED7D31', 'Programado': '#70AD47'}
                counts = df_f['Estatus_Solucion'].value_counts()
                for n in ['Dentro', 'Acumulado', 'Fuera']:
                    if n in counts:
                        ids.append(n); labels.append(n); parents.append(""); values.append(counts[n]); colors.append(c_sol[n])
                df_fuera = df_f[df_f['Estatus_Solucion'] == 'Fuera']
                for subtipo, cant in df_fuera['Detalle_Solucion'].value_counts().items():
                    ids.append(f"F_{subtipo}"); labels.append(subtipo); parents.append("Fuera"); values.append(cant)
                    colors.append(c_sol['Programado'] if 'programado' in str(subtipo).lower() else c_sol['Asap'])
                fig = go.Figure(go.Sunburst(ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
                    marker=dict(colors=colors, line=dict(color='#ffffff', width=2)), leaf=dict(opacity=1), textinfo="label+value+percent entry"))
                fig.update_layout(height=850)
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("Ver Detalle de Tabla"):
                    st.dataframe(df_f.style.apply(estilo_solucion, axis=1), use_container_width=True)

            elif pagina == "3. Contacto":
                if 'Estatus_Contacto' in df_f.columns:
                    d = df_f['Estatus_Contacto'].value_counts().reset_index()
                    fig = px.pie(d, values='count', names='Estatus_Contacto', hole=0.5, color='Estatus_Contacto', color_discrete_map={'A tiempo':'#4472C4', 'Fuera':'#ED7D31'})
                    st.plotly_chart(fig, use_container_width=True)
                    with st.expander("Ver Detalle de Tabla"):
                        st.dataframe(df_f.style.apply(estilo_contacto, axis=1), use_container_width=True)

            link = LINKS_TIMELINE.get((selected_year, sel_mes_num))
            if link: st.markdown(f'<center><a href="{link}" target="_blank" style="text-decoration:none; border:2px solid #4472C4; padding:10px; border-radius:8px; color:#4472C4; font-weight:bold;">🔗 Ver Línea de Tiempo</a></center>', unsafe_allow_html=True)

    # --- PÁGINA 4: RESUMEN ANUAL ---
    elif pagina == "4. Resumen Anual":
        st.title(f"📈 Resumen Anual {selected_year}")
        df_anual = df[df['FIN'].dt.year == selected_year].copy()
        if not df_anual.empty:
            total = len(df_anual); tiempo = len(df_anual[df_anual['DIAS'] <= 7])
            c1, c2 = st.columns(2)
            c1.metric(f"Total Tickets {selected_year}", total)
            c2.metric("Eficiencia Anual Promedio", f"{(tiempo/total*100):.1f}%")
            
            df_anual['Cumple'] = df_anual['DIAS'].apply(lambda x: 1 if x <= 7 else 0)
            tendencia = df_anual.groupby(df_anual['FIN'].dt.month)['Cumple'].mean() * 100
            fig_line = px.line(x=[meses_map[m] for m in tendencia.index if m in meses_map], y=tendencia.values, markers=True)
            st.plotly_chart(fig_line, use_container_width=True)
            
            # MOSTRAR TABLA LIMPIA (Sin estilos de colores)
            with st.expander("Ver Todos los Tickets del Año"):
                st.dataframe(df_anual, use_container_width=True)
        else:
            st.info(f"Sin datos cerrados para {selected_year}.")

    # --- PÁGINA 5: ESCALADOS ---
    elif pagina == "5. Escalados":
        st.title("🚀 Escalados (Histórico Total)")
        df_esc = load_escalados()
        if df_esc is not None:
            c1, c2 = st.columns(2)
            motivos = df_esc['Motivo'].unique()
            color_p = {m: px.colors.qualitative.Prism[i % 10] for i, m in enumerate(motivos)}
            df_f_e = df_esc[df_esc['dias_transcurridos'] > 7]
            df_d_e = df_esc[df_esc['dias_transcurridos'] <= 7]
            with c1: st.plotly_chart(px.pie(df_f_e, names='Motivo', title="Fuera de Tiempo", color='Motivo', color_discrete_map=color_p), use_container_width=True)
            with c2: st.plotly_chart(px.pie(df_d_e, names='Motivo', title="En Tiempo", color='Motivo', color_discrete_map=color_p), use_container_width=True)
            st.markdown("---")
            st.dataframe(df_esc.sort_values(by='dias_transcurridos', ascending=False).style.apply(lambda r: [f'background-color: {hex_to_rgba("#DC3545" if r.dias_transcurridos > 7 else "#28A745")}; color:black']*len(r), axis=1), use_container_width=True)

else:
    st.error("Error al cargar Tickets año.xlsx")
