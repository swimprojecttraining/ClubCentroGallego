# =============================================================================
# FILE: views/views_tab_router.py (Contenedor y Enrutador de Pestañas)
# =============================================================================
import streamlit as st

# 1. Importación directa (gracias al mapeo de ruta del root_app)
from views_sidebar import renderizar_sidebar_completo

# 2. IMPORTACIÓN DE CADA PESTAÑA DE MANERA DIRECTA
from views_tab_admin import renderizar_tab_admin
from views_tab_asignaciones import renderizar_tab_asignaciones
from views_tab_calendario import renderizar_tab_calendario
from views_tab_entrenador import renderizar_tab_entrenador
from views_tab_grafico import renderizar_tab_grafico
from views_tab_marcas import renderizar_tab_marcas
from views_tab_pizarra import renderizar_tab_pizarra
from views_tab_reportes import renderizar_tab_reportes

def mostrar_vista_enrutador():
    """
    Función maestra de inicialización que actúa como 'Director de Orquesta'.
    Captura los parámetros de la barra lateral y distribuye de forma aislada
    el flujo hacia archivos independientes dentro de la carpeta views.
    """
# Ejecutamos la barra lateral y extraemos su diccionario
    datos_sidebar = renderizar_sidebar_completo()
    
    # --- LA CORRECCIÓN: Actualizar session_state globalmente ---
    st.session_state.update(datos_sidebar)
    # A partir de aquí, las pestañas ya encontrarán los datos en st.session_state
    titulo_grafico = st.session_state.get("titulo_grafico")
    simulacion_externa = st.session_state.get("simulacion_externa")
    modo_equipo = st.session_state.get("modo_equipo")

    # Encabezado dinámico según rol y simulación
    if modo_equipo:
        st.markdown(f"### 🏊‍♂️ Planificación y control de resultados de competencia: Comparativo")
    elif simulacion_externa:
        st.markdown(f"### 🧪 Simulación de Escenarios: {titulo_grafico}")
    else:
        st.markdown(f"### 🏊‍♂️ Planificación y control de resultados de competencia: {st.session_state.nadador_seleccionado_nombre}")
    st.markdown(f"**Género:** {'Masculino (M)' if st.session_state.nadador_seleccionado_genero == 'M' else 'Femenino (F)'} | **Categoría de Competencia Activa:** `{st.session_state.nadador_seleccionado_categoria}`")
    st.markdown("---")

    # Segregación de pestañas según el Modo Simulación
    if simulacion_externa:
        st.info("⚠️ **Modo Simulación Externa Activo.** El módulo de gestión y control de marcas se encuentra oculto para evitar alteraciones accidentales en la base de datos real.")
        tab_grafico, = st.tabs(["📝 Gráfico de Proyecciones"])
    else:
        tab_grafico, tab_pizarra, tab_reportes, tab_marcas, tab_entrenador, tab_asignaciones, tab_calendario, tab_admin = st.tabs([
            "📉 Gráfico de Proyecciones",
            "📝 Pizarra Diaria", 
            "📊 Reportes de Entrenamiento", 
            "📋 Resultados de competencias", 
            "⏱️ Configurar Marcas Mínimas",
            "🎯 Asignaciones de Nadadores",
            "📅 Calendario Anual de Competencias", 
            "🛡️ Consola Global (Admin)"
        ])

    # Enrutamiento directo a los archivos de la misma carpeta
    with tab_grafico:
        renderizar_tab_grafico(datos_sidebar)

    if not simulacion_externa:
        with tab_pizarra:
            renderizar_tab_pizarra(datos_sidebar)
        with tab_reportes:
            renderizar_tab_reportes(datos_sidebar)
        with tab_marcas:
            renderizar_tab_marcas(datos_sidebar)
        with tab_entrenador:
            renderizar_tab_entrenador(datos_sidebar)
        with tab_asignaciones:
            renderizar_tab_asignaciones(datos_sidebar)
        with tab_calendario:
            renderizar_tab_calendario(datos_sidebar)
        with tab_admin:
            renderizar_tab_admin(datos_sidebar)
    # 🎨 Espaciado global para evitar el efecto de "contenido apretado"
    st.markdown("""
        <style>
            /* Añade aire al final de la página */
            .main > div {
                padding-bottom: 100px;
            }
        </style>
    """, unsafe_allow_html=True)
