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
from views_tab_club import renderizar_tab_club
from views_tab_entrenador import renderizar_tab_entrenador
from views_tab_grafico import renderizar_tab_grafico
from views_tab_importar import renderizar_tab_importar
from views_tab_marcas import renderizar_tab_marcas
from views_tab_pizarra import renderizar_tab_pizarra
from views_tab_reportes import renderizar_tab_reportes


def mostrar_vista_enrutador():
  """Función maestra de inicialización que actúa como 'Director de Orquesta'.

  Captura los parámetros de la barra lateral y distribuye de forma aislada
  el flujo hacia archivos independientes dentro de la carpeta views.
  """
  rol_usuario = st.session_state.get("rol", "Nadador")

  # --- SI ES ROL CLUB, ACTIVAMOS EL MODO CLUB ANTES DE DIBUJAR EL SIDEBAR ---
  if rol_usuario == "Club":
    st.session_state["active_tab"] = "tab_club"

  # Ejecutamos la barra lateral y extraemos su diccionario
  datos_sidebar = renderizar_sidebar_completo()

  # --- Actualizar session_state globalmente ---
  st.session_state.update(datos_sidebar)

  # --- ENRUTAMIENTO EXCLUSIVO PARA ROL CLUB ---
  if rol_usuario == "Club":
    tab_club, = st.tabs(["🏛️ Gestión Administrativa"])
    with tab_club:
      renderizar_tab_club()

    # Espaciado global
    st.markdown(
        """
        <style>
            .block-container.block-container {
                padding-top: 0.1rem;
            }
            .main > div {
                padding-bottom: 5rem;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )
    return

  # --- ENRUTAMIENTO PARA EL RESTO DE ROLES (Nadadores, Entrenadores, Admin) ---
  titulo_grafico = st.session_state.get("titulo_grafico")
  simulacion_externa = st.session_state.get("simulacion_externa", False)
  modo_equipo = st.session_state.get("modo_equipo", False)

  # Encabezado dinámico según rol y simulación
  if modo_equipo:
    st.markdown(
        "### 🏊‍♂️ Planificación y control de resultados de competencia:"
        " Comparativo"
    )
  elif simulacion_externa:
    st.markdown(f"### 🧪 Simulación de Escenarios: {titulo_grafico}")
  else:
    nombre_nadador = st.session_state.get(
        "nadador_seleccionado_nombre", "Atleta"
    )
    st.markdown(
        "### 🏊‍♂️ Planificación y control de resultados de competencia:"
        f" {nombre_nadador}"
    )

  genero_str = (
      "Masculino (M)"
      if st.session_state.get("nadador_seleccionado_genero") == "M"
      else "Femenino (F)"
  )
  cat_str = st.session_state.get("nadador_seleccionado_categoria", "")
  st.markdown(
      f"**Género:** {genero_str} | **Categoría de Competencia Activa:**"
      f" `{cat_str}`"
  )
  st.markdown("---")

  # Segregación de pestañas según el Modo Simulación
  if simulacion_externa:
    st.info(
        "⚠️ **Modo Simulación Externa Activo.** El módulo de gestión y control"
        " de marcas se encuentra oculto para evitar alteraciones accidentales"
        " en la base de datos real."
    )
    tab_grafico, = st.tabs(["📝 Gráfico de Proyecciones"])
  else:
    (
        tab_grafico,
        tab_pizarra,
        tab_reportes,
        tab_marcas,
        tab_importar,
        tab_entrenador,
        tab_asignaciones,
        tab_calendario,
        tab_admin,
    ) = st.tabs([
        "📉 Gráfico de Proyecciones",
        "📝 Pizarra Diaria",
        "📊 Reportes de Entrenamiento",
        "📋 Resultados de competencias",
        "📋 Importar Resultados de competencias",
        "⏱️ Configurar Marcas Mínimas",
        "🎯 Asignaciones de Nadadores",
        "📅 Calendario Anual de Competencias",
        "🛡️ Consola Global (Admin)",
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
    with tab_importar:
      renderizar_tab_importar()
    with tab_entrenador:
      renderizar_tab_entrenador()
    with tab_asignaciones:
      renderizar_tab_asignaciones()
    with tab_calendario:
      renderizar_tab_calendario()
    with tab_admin:
      renderizar_tab_admin()

  # 🎨 Espaciado global para evitar el efecto de "contenido apretado"
  st.markdown(
      """
        <style>
            .block-container.block-container {
                padding-top: 0.1rem;
            }
            .main > div {
                padding-bottom: 5rem;
            }
        </style>
    """,
      unsafe_allow_html=True,
  )
