import streamlit as st
import pandas as pd
import plotly.express as px
import re

# Configuración de la página
st.set_page_config(page_title="Dashboard IT - Clasificación Original", layout="wide")

# --- FUNCIONES DE PROCESAMIENTO ---
def limpiar_texto(texto):
    if pd.isna(texto): return ""
    texto = str(texto).lower()
    texto = re.sub(r'[^a-z0-9\s]', '', texto)
    return texto.strip()

def clasificar(texto):
    # DICCIONARIO DE CATEGORÍAS
    categorias = {
        'IT Tips': ['tips', 'it tip', 'ittip'],
        'AMD': ['amd','autentica'],
        'SAP': ['sap'],
        'KVS': ['kvs'],
        'VW':['vw'],
        'Zscaler':['zscaler','z scaler','z-scaler'],
        'Permisos': ['ingreso', 'permiso'],
        'Escaneo': ['escaneo', 'scan mensual', 'scaneo mensual', 'fileover', 'rvs','actualizacin','24h2'],
        'Scanner': ['digitalizacion', 'scanner', 'escaner', 'digitalizar'],
        'Revisión de Toner': ['toner', 'tonner', 'revisión de toner', 'revision de toner','tner'],
        'Actualizaciones': ['actualizacion', 'update', 'parche', 'actualizar', 'upgrade','asap'],
        'Accesos': ['acceso', 'accesos', 'permiso', 'ingreso','ngreso','access'],
        'Contraseñas': ['contrasea', 'pssw', 'usuario', 'bloqueo', 'login', 'perfil', 'reset','password', 'clave','passwork','screen','patas'],
        'Hardware': ['laptop','manos libres','speaker','bocina','contenedor','consola','cinta','etiqueta','galaxy','tapes','ipad','routers','almacen', 'pc', 'monitor', 'teclado', 'mouse', 'pantalla', 'cargador', 'equipo', 'hardware', 'ups', 'diadema','tableta','inventario','stock','extensor','dispositivo','lugar','site','ubicacion','atornillador','usb','pdu','rack','material','maquina','bandas'],
        'Impresoras': ['impresora', 'impresion', 'prt', 'zebra', 'plotter','impresin','imprimir'],
        'Red': ['red', 'wifi', 'internet', 'conexion', 'nodo', 'cable', 'vpn', 'ethernet', 'switch'],
        'Software': ['excel','creeform', 'office', 'windows', 'outlook', 'teams', 'chrome', 'software', 'adobe', 'zoom', 'solidworks', 'autocad', 'visio', 'powerpoint', 'word', 'outlook', 'correo','instalacin','instalar','nstalar', 'nstalacin','activacin','licencia'],
        'Seguridad': ['reinstalacion','reinstalacin','camara', 'video', 'biometrico', 'seguridad', 'vigilancia', 'alarma'],
        'Telefonía': ['telefono','iphone', 'extencion', 'conmutador', 'avaya', 'llamada','telfono', 'celular','movil','mvil'],
        'Correo': ['correo', 'email', 'outlook', 'exchange','8id','mail','mailbox','listado'],
        'Archivo': ['one drive','7zip','zip','sharepoint', 'cloud', 'nube', 'dropbox', 'google drive', 'archivo', 'documento','pdf','imagen'],
        'MONETA': ['moneta','op','factur'],
    }
    
    for cat, palabras in categorias.items():
        if any(p in texto for p in palabras): 
            return cat
    return 'Otros'

def clasificar_tipo(texto):
    # MODIFICACIÓN: Si el ticket es de SAP, ignorar reglas de programación y marcar como Soporte
    if 'sap' in texto:
        return 'Servicio de Soporte'
    
    # Reglas para Actividades Programadas
    palabras_programadas = ['escaneo', 'it tips', 'ittip', 'mensual', 'preventivo', 'scan mensual','fileover','rvs','it tip','revision','revisn']
    if any(p in texto for p in palabras_programadas):
        return 'Actividad Programada'
    
    return 'Servicio de Soporte'

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        # Intenta cargar el Excel
        df = pd.read_excel('Tickets año.xlsx', sheet_name='Sheet1')
    except:
        # Si falla (ej. en entornos sin Excel), intenta el CSV
        df = pd.read_csv('Tickets año.xlsx - Sheet1.csv')
    
    # Procesamiento de columnas
    df['FALLA_LIMPIA'] = df['FALLA'].apply(limpiar_texto)
    df['CATEGORIA'] = df['FALLA_LIMPIA'].apply(clasificar)
    df['TIPO'] = df['FALLA_LIMPIA'].apply(clasificar_tipo)
    df['DIAS'] = pd.to_numeric(df['DIAS'], errors='coerce').fillna(0)
    return df

df = cargar_datos()

# --- SIDEBAR ---
st.sidebar.header("Filtros")
usuarios = st.sidebar.multiselect("Filtrar por Usuarios", options=df['USUARIO'].unique())
df_filtrado = df.copy()
if usuarios:
    df_filtrado = df_filtrado[df_filtrado['USUARIO'].isin(usuarios)]

# --- CUERPO PRINCIPAL ---
st.title("📊 Dashboard de Gestión IT")

# 1. GRÁFICA PRINCIPAL (PASTEL)
st.subheader("Distribución: Soporte vs. Programados")
fig_pie = px.pie(df_filtrado, names='TIPO', hole=0.4,
                 color='TIPO',
                 color_discrete_map={'Servicio de Soporte': '#E74C3C', 'Actividad Programada': '#3498DB'})
st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# 2. DESGLOSE EN DOS COLUMNAS
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("🛠️ Desglose Soporte")
    df_soporte = df_filtrado[df_filtrado['TIPO'] == 'Servicio de Soporte']
    if not df_soporte.empty:
        fig_sop = px.bar(df_soporte['CATEGORIA'].value_counts().reset_index(),
                        x='count', y='CATEGORIA', orientation='h',
                        color='count', 
                        color_continuous_scale='Reds',
                        labels={'count':'Tickets', 'CATEGORIA':''})
        st.plotly_chart(fig_sop, use_container_width=True)
    else:
        st.info("No hay datos de Soporte con los filtros seleccionados.")

with col_der:
    st.subheader("📅 Desglose Programados")
    df_prog = df_filtrado[df_filtrado['TIPO'] == 'Actividad Programada']
    if not df_prog.empty:
        fig_prog = px.bar(df_prog['CATEGORIA'].value_counts().reset_index(),
                         x='count', y='CATEGORIA', orientation='h',
                         color='count', 
                         color_continuous_scale='Blues',
                         labels={'count':'Tickets', 'CATEGORIA':''})
        st.plotly_chart(fig_prog, use_container_width=True)
    else:
        st.info("No hay datos de Actividades Programadas.")

# Tabla detalle final
st.subheader("📋 Detalle de Tickets")
st.dataframe(df_filtrado[['N° TICKET', 'USUARIO', 'TIPO', 'CATEGORIA', 'FALLA', 'DIAS']], 
             use_container_width=True, 
             hide_index=True)