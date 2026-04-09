import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import numpy as np
from calendar import monthrange
from datetime import datetime

st.set_page_config(page_title="Reporte TI", layout="wide")

# --- CONFIGURACIÓN DE FERIADOS ---
FERIADOS = [
    '2025-01-01', '2025-02-03', '2025-03-17', '2025-05-01', '2025-09-16', 
    '2025-11-17', '2025-12-25', '2026-01-01', '2026-02-02', '2026-03-16'
]
feriados_np = np.array(FERIADOS, dtype='datetime64[D]')

# ... (Mantenemos los LINKS_TIMELINE y CSS igual)

# --- FUNCIONES DE LÓGICA ---
def contar_dias_habiles(inicio, fin):
    try:
        if pd.isna(inicio) or pd.isna(fin): return 0
        start = np.datetime64(inicio, 'D')
        end = np.datetime64(fin, 'D')
        if start > end: return 0
        return int(np.busday_count(start, end, holidays=feriados_np))
    except: return 0

# --- NUEVA FUNCIÓN PARA ESCALADOS ---
def load_escalados():
    archivo = "Datos escalados.xlsx"
    if os.path.exists(archivo):
        try:
            df_esc = pd.read_excel(archivo)
            df_esc.columns = df_esc.columns.str.strip()
            if 'inicio' in df_esc.columns:
                df_esc['inicio'] = pd.to_datetime(df_esc['inicio'], dayfirst=True, errors='coerce')
                # Calculamos días hábiles hasta hoy
                hoy = pd.Timestamp.now()
                df_esc['dias_transcurridos'] = df_esc['inicio'].apply(lambda x: contar_dias_habiles(x, hoy))
            return df_esc
        except: return None
    return None

# ... (Mantenemos las demás funciones de estilo y lógica igual)

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

# --- APP ---
df = load_data()
df_esc = load_escalados() # NUEVO: Carga de datos escalados

if df is not None:
    # ... (Mantenemos la lógica de sidebar y navegación igual hasta llegar a la Página 4)
    
    # [AQUÍ SE MANTIENEN LAS PÁGINAS 1, 2 y 3 SIN CAMBIOS...]
    # (Omitido por brevedad, pero se mantiene exactamente igual en tu archivo)

    # --- PÁGINA 4: RESUMEN ANUAL ---
    if pagina == "4. Resumen Anual":
        st.title(f"📈 Resumen Anual {selected_year}")
        df_anual = df[df['FIN'].dt.year == selected_year].copy()
        if not df_anual.empty:
            # ... (Toda tu lógica de métricas y gráfico de tendencia se queda igual)
            total, tiempo = len(df_anual), len(df_anual[df_anual['DIAS'] <= 7])
            c1, c2 = st.columns(2)
            c1.metric(f"Total Tickets {selected_year}", total)
            c2.metric("Promedio Eficiencia Anual", f"{(tiempo/total*100):.1f}%")

            st.markdown("---")
            st.markdown("### 📈 Tendencia: Tickets Cerrados en Tiempo (7 días hábiles)")
            df_anual['Cumple'] = df_anual['DIAS'].apply(lambda x: 1 if x <= 7 else 0)
            tendencia = df_anual.groupby(df_anual['FIN'].dt.month)['Cumple'].mean() * 100
            if selected_year == anio_actual: tendencia = tendencia[tendencia.index < mes_actual]

            fig_line = px.line(x=[meses_map[m] for m in tendencia.index], y=tendencia.values, markers=True, text=[f"{v:.1f}%" for v in tendencia.values])
            fig_line.update_traces(line_color='#4472C4', line_width=4, marker_size=12, textposition='top center')
            fig_line.update_layout(yaxis_title="% Eficiencia Solución", xaxis_title=None, yaxis_range=[0, 115], font=dict(size=16), height=450)
            st.plotly_chart(fig_line, use_container_width=True)

            # --- NUEVA SECCIÓN: ESCALADOS ---
            st.markdown("---")
            st.header("🚀 Tickets Escalados")
            
            if df_esc is not None and not df_esc.empty:
                # Filtrar por año seleccionado si es necesario (asumiendo que 'inicio' define el año)
                df_esc_y = df_esc[df_esc['inicio'].dt.year == selected_year].copy()
                
                if not df_esc_y.empty:
                    col_esc1, col_esc2 = st.columns(2)

                    # 1. Tickets con más de 7 días (Fuera de tiempo)
                    df_mas_7 = df_esc_y[df_esc_y['dias_transcurridos'] > 7]
                    with col_esc1:
                        st.subheader("⚠️ Escalados > 7 Días")
                        if not df_mas_7.empty:
                            d_m7 = df_mas_7['Motivo'].value_counts().reset_index()
                            d_m7.columns = ['Motivo', 'Cantidad']
                            fig_m7 = px.pie(d_m7, values='Cantidad', names='Motivo', hole=0.4,
                                           color_discrete_sequence=px.colors.qualitative.Set2)
                            fig_m7.update_layout(height=450, legend=dict(orientation="h", yanchor="bottom", y=-0.5))
                            st.plotly_chart(fig_m7, use_container_width=True)
                        else:
                            st.success("No hay tickets escalados con más de 7 días.")

                    # 2. Tickets con 7 días o menos (A tiempo)
                    df_menos_7 = df_esc_y[df_esc_y['dias_transcurridos'] <= 7]
                    with col_esc2:
                        st.subheader("✅ Escalados ≤ 7 Días")
                        if not df_menos_7.empty:
                            d_l7 = df_menos_7['Motivo'].value_counts().reset_index()
                            d_l7.columns = ['Motivo', 'Cantidad']
                            fig_l7 = px.pie(d_l7, values='Cantidad', names='Motivo', hole=0.4,
                                           color_discrete_sequence=px.colors.qualitative.Pastel)
                            fig_l7.update_layout(height=450, legend=dict(orientation="h", yanchor="bottom", y=-0.5))
                            st.plotly_chart(fig_l7, use_container_width=True)
                        else:
                            st.info("No hay tickets escalados recientes.")
                    
                    with st.expander("Ver tabla detallada de escalados"):
                        st.dataframe(df_esc_y[['Ticket', 'Problema', 'Usuario', 'Motivo', 'inicio', 'dias_transcurridos']])
                else:
                    st.info(f"No hay datos de escalados para el año {selected_year}.")
            else:
                st.warning("No se encontró el archivo 'Datos escalados.xlsx' o está vacío.")
        else:
            st.info(f"Sin datos de cierre para el resumen anual de {selected_year}.")

else:
    st.error("No se encontró 'Tickets año.xlsx'")
