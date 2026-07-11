import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Importamos la librería central de lógica y estilos
from formulas_lib_funciones import (
    obtener_atletas_filtrados_supabase,
    calcular_metricas_fisiologicas
)
from views_styles import aplicar_estilos_globales

def renderizar_tab_reportes(datos_sidebar=None):
    """
    Controlador maestro de la pestaña Reportes.
    Estándar: Solo análisis individual, seguridad por rol, estilos unificados.
    """
    st.markdown("### 📊 Panel de Control y Análisis de Carga Individual")
    
    # 1. Selección de Atleta (Seguridad: Filtro estricto por usuario/entrenador)
    atletas = obtener_atletas_filtrados_supabase()
    nombres_map = {a['nombre']: a['id'] for a in atletas}
    
    col1, col2 = st.columns([2, 1])
    with col1:
        atleta_nombre = st.selectbox("Seleccionar Atleta:", list(nombres_map.keys()))
    with col2:
        opciones_tiempo = {
            "7 días (ATL)": 7,
            "42 días (CTL)": 42,
            "90 días (Macrociclo)": 90,
            "365 días (Anual)": 365,
            "Total Histórico": None
        }
        ventana_key = st.selectbox("Ventana Temporal:", list(opciones_tiempo.keys()))
        dias = opciones_tiempo[ventana_key]
    
    # 2. Ejecución de la lógica de datos
    _procesar_reporte(nombres_map[atleta_nombre], atleta_nombre, dias)

# --- FIN DEL CAPÍTULO 1 ---
# --- CAPÍTULO 2: MOTOR DE DATOS Y PESTAÑAS ---

def _procesar_reporte(atleta_id, atleta_nombre, dias):
    """
    Gestiona la conexión segura a Supabase y despliega la arquitectura de tabs.
    """
    supabase = st.session_state.get("supabase")
    
    try:
        # 1. Consulta Segura (Solo datos del atleta seleccionado)
        query = supabase.table("bitacora_entrenamientos").select("*").eq("atleta_id", atleta_id)
        if dias:
            fecha_inicio = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()
            query = query.gte("fecha", fecha_inicio)
        
        response = query.order("fecha", desc=False).execute()
        df = pd.DataFrame(response.data)
        
        if df.empty:
            st.info(f"No hay registros de entrenamiento para {atleta_nombre} en este periodo.")
            return

        # 2. Procesamiento matemático centralizado
        df = calcular_metricas_fisiologicas(df)
        # Aseguramos formato fecha para evitar errores en gráficos/tablas
        df['fecha'] = pd.to_datetime(df['fecha'])

        # 3. Estructura de Navegación (Tabs estándar)
        tab_graficos, tab_fisiologia, tab_auditoria = st.tabs([
            "📈 Gráficos de Carga", 
            "⚙️ Métricas Fisiológicas", 
            "📝 Auditoría de Datos"
        ])
        
        with tab_graficos:
            _render_graficos_fisiologicos(df)
            
        with tab_fisiologia:
            _render_tabla_auditoria_fisiologica(df, atleta_nombre)
            
        with tab_auditoria:
            _render_tabla_auditoria_datos(df, atleta_nombre)
            
    except Exception as e:
        st.error(f"Error procesando reporte: {e}")

# --- FIN DEL CAPÍTULO 2 ---
# --- CAPÍTULO 3: MOTORES DE VISUALIZACIÓN Y EXPORTACIÓN ---

def _render_graficos_fisiologicos(df):
    """
    Motor gráfico: Escala symlog (linthresh=500) y ejes duales (CTL/ATL vs TSB%).
    """
    fig_ban, ax1 = plt.subplots(figsize=(10, 5))
    
    # Eje 1: Cargas (CTL/ATL) y Balance (TSB)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax1.plot(df["fecha"], df["CTL"], label="Fitness Crónico (CTL)", color="#1f77b4", linewidth=2.0)
    ax1.plot(df["fecha"], df["ATL"], label="Fatiga Aguda (ATL)", color="#d62728", linewidth=1.5, linestyle="--")
    ax1.bar(df["fecha"], df["TSB"], label="Balance Neto (TSB m)", color="#2ca02c", alpha=0.20, width=1.0)
    ax1.set_yscale('symlog', linthresh=500)
    ax1.grid(True, linestyle=":", alpha=0.2)
    ax1.legend(loc="upper left")
    
    # Eje 2: TSB Relativo (%)
    ax2 = ax1.twinx()
    ax2.plot(df["fecha"], df["TSB_Pct"], label="Índice TSB Acotado (%)", color="#2c3e50", linewidth=1.8)
    ax2.set_ylim(-105, 105)
    ax2.legend(loc="upper right")
    
    plt.tight_layout()
    st.pyplot(fig_ban)

def _render_tabla_auditoria_fisiologica(df, nombre_atleta):
    """
    Tabla técnica de métricas fisiológicas con estilo CSS global.
    """
    df_display = df.rename(columns={
        "fecha": "Fecha",
        "metros_totales": "Metros Ponderados (Día)",
        "CTL": "CTL (Fitness m)",
        "ATL": "ATL (Fatiga m)",
        "TSB": "TSB (Forma m)",
        "TSB_Pct": "TSB Relativo Acotado (% Máx)"
    })
    
    cols = ["Fecha", "Metros Ponderados (Día)", "CTL (Fitness m)", 
            "ATL (Fatiga m)", "TSB (Forma m)", "TSB Relativo Acotado (% Máx)"]
    
    # Renderizado con estilo estándar
    st.write(df_display[cols].to_html(index=False, classes="tabla-estilizada"), unsafe_allow_html=True)
    
    _render_botones_exportacion(df_display, nombre_atleta, "fisiologico")

def _render_tabla_auditoria_datos(df, nombre_atleta):
    """
    Tabla de datos crudos con estilo CSS global.
    """
    st.write(df.to_html(index=False, classes="tabla-estilizada"), unsafe_allow_html=True)
    _render_botones_exportacion(df, nombre_atleta, "bitacora")

def _render_botones_exportacion(df, nombre_atleta, tipo):
    """
    Botones de exportación normalizados.
    """
    csv_data = df.to_csv(index=False).encode('utf-8')
    txt_data = df.to_string(index=False).encode('utf-8')
    
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📥 Descargar CSV", csv_data, f"{tipo}_{nombre_atleta.replace(' ', '_')}.csv", use_container_width=True)
    with c2:
        st.download_button("📄 Descargar TXT", txt_data, f"{tipo}_{nombre_atleta.replace(' ', '_')}.txt", use_container_width=True)

# --- FIN DEL CAPÍTULO 3 ---
# 1. Aplicación de estilos globales de la aplicación
# Esto asegura que todas las tablas y tabs hereden el CSS de views_styles.py
aplicar_estilos_globales()

# 2. Validación de sesión (Seguridad preventiva)
if "supabase" not in st.session_state:
    st.warning("Sesión expirada. Por favor, recargue la página.")
    st.stop()