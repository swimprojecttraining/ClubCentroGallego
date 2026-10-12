# =============================================================================
# views_tab_router.py — v2.0 (Fase 1: refactorización incremental)
# =============================================================================
# Última actualización: 2026-10-12
#
# CHANGELOG:
#   v2.0 (2026-10-12) — Refactorización Fase 1:
#     16a — Verificación de sesión activa antes de renderizar.
#     16b — Filtro en session_state.update() para proteger claves críticas.
#     16c — CSS duplicado movido a views_styles.aplicar_estilos_router().
#     16d — Corrección de typos ("alterations" → "alteraciones").
#     16e — Limpieza de cachés de sesión del sidebar al cambiar de rol.
#     16f — Encabezado con changelog versionado.
#
# NO TOCADO:
#   - Estructura de pestañas por rol
#   - Lógica de modo simulación
#   - Encabezados dinámicos de atletas
#   - key= de los widgets
#
# PENDIENTE FASE 2:
#   [F2-40] (RESUELTO en v2.0 con filtro de claves protegidas)
#   [F2-41] (RESUELTO en views_styles v2.1)
#   [F2-42] (RESUELTO en v2.0 con limpieza de cachés al cambiar de rol)
# =============================================================================
import streamlit as st

# 1. Importación directa del sidebar
from views_sidebar import renderizar_sidebar_completo

# 2. Importación de cada pestaña
from views_tab_asignaciones import renderizar_tab_asignaciones
from views_tab_calendario import renderizar_tab_calendario
from views_tab_club import renderizar_tab_club
from views_tab_entrenador import renderizar_tab_entrenador
from views_tab_grafico import renderizar_tab_grafico
from views_tab_importar import renderizar_tab_importar
from views_tab_marcas import renderizar_tab_marcas
from views_tab_pizarra import renderizar_tab_pizarra
from views_tab_reportes import renderizar_tab_reportes
from views_tab_antropometria import renderizar_tab_antropometria

# 3. Importación de estilos del router
from views_styles import aplicar_estilos_router


# =============================================================================
# CLAVES DE SESIÓN PROTEGIDAS
# =============================================================================
# Estas claves NO deben ser sobrescritas por el dict de retorno del sidebar,
# para evitar que un cambio futuro en el sidebar rompa la autenticación o
# la conexión a la base de datos.
CLAVES_PROTEGIDAS = {
    "autenticado",
    "supabase",
    "puente_validado",
    "rol_real",
    "usuario_id",
    "usuario_logueado_id",
    "club_seleccionado",
}


# =============================================================================
# HELPER: LIMPIEZA DE CACHÉS DE SESIÓN AL CAMBIAR DE ROL
# =============================================================================
def _limpiar_caches_sesion_sidebar():
    """
    [F1-16e] Limpia las cachés de sesión del sidebar cuando cambia el rol.
    Evita que queden datos obsoletos de un rol anterior al emular otro.
    """
    for k in list(st.session_state.keys()):
        if k.startswith("_hist_sidebar_") or k.startswith("_atletas_entrenador_"):
            del st.session_state[k]


def _detectar_cambio_de_rol(rol_actual: str) -> bool:
    """
    Compara el rol actual con el último rol conocido.
    Si cambió, limpia las cachés de sesión y actualiza el registro.

    Retorna: True si hubo cambio, False si no.
    """
    if "rol_anterior_router" not in st.session_state:
        st.session_state["rol_anterior_router"] = rol_actual
        return False

    if st.session_state["rol_anterior_router"] != rol_actual:
        _limpiar_caches_sesion_sidebar()
        st.session_state["rol_anterior_router"] = rol_actual
        return True

    return False


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def mostrar_vista_enrutador():
    """Función maestra de inicialización que actúa como 'Director de Orquesta'."""

    # [F1-16a] Verificación de sesión activa antes de renderizar
    if not st.session_state.get("autenticado", False):
        st.warning(
            "⚠️ Sesión no activa. Por favor, inicie sesión desde el Hub "
            "Central."
        )
        st.stop()

    # 1. Ejecutamos la barra lateral
    datos_sidebar = renderizar_sidebar_completo()

    # [F1-16b] Filtro de claves protegidas antes del update
    # Evita sobrescribir claves críticas del sistema por accidente.
    for k, v in datos_sidebar.items():
        if k not in CLAVES_PROTEGIDAS:
            st.session_state[k] = v

    # 2. Obtenemos el rol resultante (real o simulado)
    rol_usuario = st.session_state.get("rol", "Nadador")

    # [F1-16e] Detectar cambio de rol y limpiar cachés de sesión
    _detectar_cambio_de_rol(rol_usuario)

    # 3. SI EL ROL ES "CLUB", RENDERIZAMOS ÚNICAMENTE LA PESTAÑA DEL CLUB
    if rol_usuario == "Club":
        (tab_club,) = st.tabs(["🏛️ Gestión Administrativa"])
        with tab_club:
            renderizar_tab_club()

        # [F1-16c] Estilos del router (ya no duplicados)
        aplicar_estilos_router()
        return

    # 4. ENTORNO COMPLETO (Nadador, Entrenador, Head Coach, Administrador)
    titulo_grafico = st.session_state.get("titulo_grafico")
    simulacion_externa = st.session_state.get("simulacion_externa", False)
    modo_equipo = st.session_state.get("modo_equipo", False)

    # Encabezado dinámico de atletas
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

    # --- CONTINÚA EL RENDERIZADO REGULAR DE LAS PESTAÑAS ---

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

    # Segregación de pestañas según el Modo Simulación y el Rol
    if simulacion_externa:
        st.info(
            "⚠️ **Modo Simulación Externa Activo.** El módulo de gestión y "
            "control de marcas se encuentra oculto para evitar alteraciones "
            "en la base de datos real."
        )
        (tab_grafico,) = st.tabs(["📝 Gráfico de Proyecciones"])
    elif rol_usuario in ["Entrenador", "Nadador"]:
        (
            tab_grafico,
            tab_antropometria,
            tab_pizarra,
            tab_reportes,
            tab_marcas,
            tab_calendario,
        ) = st.tabs([
            "📉 Gráfico de Proyecciones",
            "📏 Control Antropométrico y WA",
            "📝 Pizarra Diaria",
            "📊 Reportes de Entrenamiento",
            "📋 Resultados de competencias",
            "📅 Calendario Anual de Competencias",
        ])
    else:
        (
            tab_grafico,
            tab_antropometria,
            tab_pizarra,
            tab_reportes,
            tab_marcas,
            tab_importar,
            tab_entrenador,
            tab_asignaciones,
            tab_calendario,
        ) = st.tabs([
            "📉 Gráfico de Proyecciones",
            "📏 Control Antropométrico y WA",
            "📝 Pizarra Diaria",
            "📊 Reportes de Entrenamiento",
            "📋 Resultados de competencias",
            "📋 Importar Resultados de competencias",
            "⏱️ Configurar Marcas Mínimas",
            "🎯 Asignaciones de Nadadores",
            "📅 Calendario Anual de Competencias",
        ])

    # Enrutamiento directo a los archivos
    with tab_grafico:
        renderizar_tab_grafico(datos_sidebar)
    with tab_antropometria:
        renderizar_tab_antropometria(datos_sidebar)

    if not simulacion_externa:
        with tab_pizarra:
            renderizar_tab_pizarra(datos_sidebar)
        with tab_reportes:
            renderizar_tab_reportes(datos_sidebar)
        with tab_marcas:
            renderizar_tab_marcas(datos_sidebar)

        # Solo renderizamos los tabs de gestión si no es Entrenador ni Nadador
        if rol_usuario not in ["Entrenador", "Nadador"]:
            with tab_importar:
                renderizar_tab_importar()
            with tab_entrenador:
                renderizar_tab_entrenador()
            with tab_asignaciones:
                renderizar_tab_asignaciones()

        with tab_calendario:
            renderizar_tab_calendario()

    # [F1-16c] Estilos del router (una sola vez, al final)
    aplicar_estilos_router()

# === FIN DEL ARCHIVO views_tab_router.py (v2.0) ===