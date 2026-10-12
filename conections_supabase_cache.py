# -------------------------------------------------------------
# CACHÉ INTELIGENTE PARA CONSULTAS A SUPABASE (OPTIMIZACIÓN DE RENDIMIENTO)
# -------------------------------------------------------------
# v2.5 — Fase 1: refactorización incremental
# Última actualización: 2026-10-12
#
# CHANGELOG:
#   v2.5 (2026-10-12) — Adiciones para views_tab_club.py:
#     - Nueva función get_invitaciones_pendientes()
#     - Nueva función get_pagos_por_temporada(temporada)
#     - Nueva función get_documentos_correlativos(tipo_documento, anio)
#     - Nueva función invalidar_cache_pagos()
#     - Nueva función invalidar_cache_invitaciones()
#
#   v2.4 (2026-10-12) — Adiciones para views_tab_pizarra.py:
#     - Nueva función get_bitacora_rango(fecha_desde, fecha_hasta, atleta_ids)
#     - Nueva función invalidar_cache_bitacora()
#
#   v2.3 (2026-10-12) — Adición para views_tab_entrenador.py:
#     - Nueva función invalidar_cache_referencias()
#
#   v2.2 (2026-10-11) — Adiciones para views_tab_calendario.py:
#     - Nueva función get_competencias(temporada)
#     - Nueva función get_hitos_por_competencia(competencia_id)
#     - Nuevas funciones invalidar_cache_competencias()
#       e invalidar_cache_hitos_por_competencia()
#
#   v2.1 (2026-10-11) — Adiciones para views_tab_antropometria.py:
#     - Nueva función get_evaluaciones_antropometricas(usuario_id)
#     - Nueva función invalidar_cache_antropometria()
#
#   v2.0 (2026-10-10) — Refactorización inicial Fase 1:
#     - Cliente Supabase singleton con @st.cache_resource
#     - 12 wrappers de compatibilidad hacia atrás
#     - Nuevas funciones get_* unificadas
#     - Nueva función get_marcas_historicas_bulk para evitar N+1
#     - Funciones invalidar_cache_*() para invalidación quirúrgica
#
#   v1.0 — Versión original (obsoleta, no disponible)
# -------------------------------------------------------------
import streamlit as st
import pandas as pd


# =============================================================================
# CLIENTE SUPABASE ÚNICO (SINGLETON POR PROCESO DEL SERVIDOR)
# =============================================================================
@st.cache_resource(show_spinner=False)
def _crear_cliente_supabase():
    """
    Crea el cliente Supabase UNA sola vez por proceso de Streamlit.
    Todos los usuarios del servidor comparten esta instancia (es thread-safe).
    """
    from supabase import create_client
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def get_db():
    """Devuelve el cliente Supabase cacheado."""
    return _crear_cliente_supabase()


def _get_db():
    """
    Compatibilidad: algunas vistas llaman a _get_db() directamente.
    Ahora simplemente redirige al singleton.
    """
    return get_db()


# =============================================================================
# USUARIOS — UNA SOLA FUNCIÓN PARA TODOS LOS CASOS
# =============================================================================
@st.cache_data(ttl=1800, show_spinner=False)
def get_usuarios(rol: str | None = None, estatus: str | None = None) -> list[dict]:
    """
    Query única y cacheada sobre la tabla 'usuarios'.
    Filtra en Postgres, no en pandas.
    """
    db = get_db()
    try:
        q = db.table("usuarios").select(
            "id, nombre, email, usuario, genero, rol, estatus, fecha_nacimiento, cedula, telefono"
        )
        if rol:
            q = q.eq("rol", rol)
        if estatus:
            q = q.eq("estatus", estatus)
        return q.execute().data or []
    except Exception as e:
        print(f"[get_usuarios] {e}")
        return []


@st.cache_data(ttl=1800, show_spinner=False)
def get_usuario_por_id(usuario_id: int) -> dict | None:
    """Devuelve un usuario puntual. Si ya está en caché general, la reutiliza."""
    if not usuario_id:
        return None
    # Intento 1: buscar en la lista completa ya cacheada
    usuarios = get_usuarios()
    for u in usuarios:
        if u.get("id") == usuario_id:
            return u
    # Intento 2: query puntual por si no está en la general
    db = get_db()
    try:
        res = (
            db.table("usuarios")
            .select("id, nombre, genero, rol, estatus, fecha_nacimiento")
            .eq("id", usuario_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[get_usuario_por_id] {e}")
        return None


# =============================================================================
# ASIGNACIONES — ÚNICA FUENTE DE VERDAD
# =============================================================================
@st.cache_data(ttl=1800, show_spinner=False)
def get_atletas_asignados(entrenador_id: int) -> list[int]:
    """IDs de atletas activos asignados a un entrenador."""
    if not entrenador_id:
        return []
    db = get_db()
    try:
        res = (
            db.table("asignaciones")
            .select("atleta_id")
            .eq("entrenador_id", entrenador_id)
            .eq("activo", True)
            .execute()
        )
        return [r["atleta_id"] for r in (res.data or []) if r.get("atleta_id")]
    except Exception as e:
        print(f"[get_atletas_asignados] {e}")
        return []


# =============================================================================
# MARCAS HISTÓRICAS
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_marcas_historicas(
    usuario_id: int,
    prueba: str | None = None,
    columnas: str = "id, prueba, edad, tiempo, nota",
) -> list[dict]:
    if not usuario_id:
        return []
    db = get_db()
    try:
        q = db.table("marcas_historicas").select(columnas).eq("usuario_id", usuario_id)
        if prueba:
            q = q.eq("prueba", prueba)
        q = q.order("edad", desc=False)
        return q.execute().data or []
    except Exception as e:
        print(f"[get_marcas_historicas] {e}")
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_marcas_historicas_bulk(usuario_ids: tuple, prueba: str) -> pd.DataFrame:
    if not usuario_ids:
        return pd.DataFrame()
    db = get_db()
    try:
        res = (
            db.table("marcas_historicas")
            .select("id, usuario_id, prueba, edad, tiempo, nota")
            .in_("usuario_id", list(usuario_ids))
            .eq("prueba", prueba)
            .order("edad", desc=False)
            .execute()
        )
        return pd.DataFrame(res.data or [])
    except Exception as e:
        print(f"[get_marcas_historicas_bulk] {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_marcas_historicas_bulk_sin_prueba(usuario_ids: tuple) -> pd.DataFrame:
    if not usuario_ids:
        return pd.DataFrame()
    db = get_db()
    try:
        res = (
            db.table("marcas_historicas")
            .select("id, usuario_id, prueba, edad, tiempo, nota")
            .in_("usuario_id", list(usuario_ids))
            .order("edad", desc=False)
            .execute()
        )
        return pd.DataFrame(res.data or [])
    except Exception as e:
        print(f"[get_marcas_historicas_bulk_sin_prueba] {e}")
        return pd.DataFrame()


# =============================================================================
# MARCAS DEL EQUIPO
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_marcas_equipo(lista_ids: tuple, prueba: str) -> pd.DataFrame:
    if not lista_ids:
        return pd.DataFrame()
    db = get_db()
    try:
        res = (
            db.table("marcas")
            .select("usuario_id, nombre, genero, prueba, tiempo_segundos, fecha_competencia")
            .eq("prueba", prueba)
            .in_("usuario_id", list(lista_ids))
            .execute()
        )
        df = pd.DataFrame(res.data or [])
        if not df.empty:
            df["tiempo_segundos"] = pd.to_numeric(df["tiempo_segundos"], errors="coerce")
        return df
    except Exception as e:
        print(f"[get_marcas_equipo] {e}")
        return pd.DataFrame()


# =============================================================================
# CATÁLOGOS ESTÁTICOS
# =============================================================================
@st.cache_data(ttl=86400, show_spinner=False)
def get_catalogo_competencias() -> list[dict]:
    db = get_db()
    try:
        return db.table("catalogo_competencias").select("*").execute().data or []
    except Exception as e:
        print(f"[get_catalogo_competencias] {e}")
        return []


@st.cache_data(ttl=86400, show_spinner=False)
def get_marcas_referencia(prueba: str, genero: str, categoria: str) -> list[dict]:
    db = get_db()
    try:
        return (
            db.table("marcas_referencia")
            .select("*")
            .eq("prueba", prueba)
            .eq("genero", genero)
            .eq("categoria", categoria)
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"[get_marcas_referencia] {e}")
        return []


# =============================================================================
# HITOS
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_hitos_atleta(nadador_id: int) -> dict | None:
    if not nadador_id:
        return None
    db = get_db()
    try:
        res = (
            db.table("historial_hitos")
            .select("*, catalogo_competencias(*)")
            .eq("usuario_id", nadador_id)
            .execute()
        )
        return {"hitos": res.data or []}
    except Exception as e:
        print(f"[get_hitos_atleta] {e}")
        return None


# =============================================================================
# BITÁCORA DE ENTRENAMIENTOS
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_bitacora_atleta(atleta_id: int) -> list[dict]:
    if not atleta_id:
        return []
    db = get_db()
    try:
        res = (
            db.table("bitacora_entrenamientos")
            .select("*")
            .eq("atleta_id", atleta_id)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[get_bitacora_atleta] {e}")
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_bitacora_rango(
    fecha_desde: str,
    fecha_hasta: str,
    atleta_ids: tuple | None = None,
) -> list[dict]:
    if not fecha_desde or not fecha_hasta:
        return []
    db = get_db()
    try:
        q = (
            db.table("bitacora_entrenamientos")
            .select(
                "fecha, identificador_carril, metros_totales, "
                "desglose_estilos, desglose_intensidad, implementos_usados, "
                "atleta_id, pizarra_original"
            )
            .gte("fecha", fecha_desde)
            .lte("fecha", fecha_hasta)
        )
        if atleta_ids:
            q = q.in_("atleta_id", list(atleta_ids))
        q = q.order("fecha", desc=True)
        return q.execute().data or []
    except Exception as e:
        print(f"[get_bitacora_rango] {e}")
        return []


# =============================================================================
# ANTROPOMETRÍA
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_evaluaciones_antropometricas(usuario_id: int) -> list[dict]:
    if not usuario_id:
        return []
    db = get_db()
    try:
        res = (
            db.table("evaluaciones_antropometricas")
            .select("*")
            .eq("usuario_id", usuario_id)
            .order("fecha_evaluacion", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[get_evaluaciones_antropometricas] {e}")
        return []


# =============================================================================
# CALENDARIO Y HITOS
# =============================================================================
@st.cache_data(ttl=1800, show_spinner=False)
def get_competencias(temporada: int | None = None) -> list[dict]:
    db = get_db()
    try:
        q = db.table("catalogo_competencias").select("*")
        if temporada is not None:
            q = q.eq("temporada", temporada)
        q = q.order("fecha_inicio", desc=False)
        return q.execute().data or []
    except Exception as e:
        print(f"[get_competencias] {e}")
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_hitos_por_competencia(competencia_id: int) -> list[dict]:
    if not competencia_id:
        return []
    db = get_db()
    try:
        res = (
            db.table("historial_hitos")
            .select("usuario_id")
            .eq("competencia_id", competencia_id)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[get_hitos_por_competencia] {e}")
        return []


# =============================================================================
# CLUB — INVITACIONES, PAGOS, DOCUMENTOS [v2.5]
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_invitaciones_pendientes() -> list[dict]:
    """
    [v2.5] Devuelve las invitaciones no usadas, ordenadas por fecha
    de creación descendente.
    """
    db = get_db()
    try:
        res = (
            db.table("invitaciones")
            .select("*")
            .eq("usado", False)
            .order("creado_en", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[get_invitaciones_pendientes] {e}")
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_pagos_por_temporada(temporada: int) -> list[dict]:
    """
    [v2.5] Devuelve los registros de control_pagos de una temporada.
    """
    if temporada is None:
        return []
    db = get_db()
    try:
        res = (
            db.table("control_pagos")
            .select("*")
            .eq("temporada", temporada)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[get_pagos_por_temporada] {e}")
        return []


@st.cache_data(ttl=600, show_spinner=False)
def get_documentos_correlativos(tipo_documento: str, anio: int) -> list[dict]:
    """
    [v2.5] Devuelve los correlativos de documentos oficiales del tipo
    y año indicados. Se usa para calcular el siguiente número consecutivo.
    """
    db = get_db()
    prefix_map = {
        "Memorándum": "MEM",
        "Circular": "CIR",
        "Correspondencia": "COR",
    }
    prefix = prefix_map.get(tipo_documento, "DOC")
    try:
        res = (
            db.table("documentos_oficiales")
            .select("codigo_correlativo")
            .eq("tipo_documento", tipo_documento)
            .ilike("codigo_correlativo", f"{prefix}-{anio}-%")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[get_documentos_correlativos] {e}")
        return []


# =============================================================================
# INVALIDACIÓN DE CACHÉ
# =============================================================================
def invalidar_cache_marcas():
    get_marcas_historicas.clear()
    get_marcas_historicas_bulk.clear()
    get_marcas_historicas_bulk_sin_prueba.clear()
    get_marcas_equipo.clear()


def invalidar_cache_usuarios():
    get_usuarios.clear()
    get_usuario_por_id.clear()


def invalidar_cache_asignaciones():
    get_atletas_asignados.clear()


def invalidar_cache_hitos():
    get_hitos_atleta.clear()
    get_hitos_por_competencia.clear()


def invalidar_cache_antropometria():
    get_evaluaciones_antropometricas.clear()


def invalidar_cache_competencias():
    get_competencias.clear()


def invalidar_cache_referencias():
    get_marcas_referencia.clear()


def invalidar_cache_bitacora():
    get_bitacora_atleta.clear()
    get_bitacora_rango.clear()


def invalidar_cache_pagos():
    """[v2.5] Limpia la caché de control de pagos."""
    get_pagos_por_temporada.clear()


def invalidar_cache_invitaciones():
    """[v2.5] Limpia la caché de invitaciones pendientes."""
    get_invitaciones_pendientes.clear()


def invalidar_toda_la_cache():
    get_usuarios.clear()
    get_usuario_por_id.clear()
    get_atletas_asignados.clear()
    get_marcas_historicas.clear()
    get_marcas_historicas_bulk.clear()
    get_marcas_historicas_bulk_sin_prueba.clear()
    get_marcas_equipo.clear()
    get_catalogo_competencias.clear()
    get_marcas_referencia.clear()
    get_hitos_atleta.clear()
    get_hitos_por_competencia.clear()
    get_bitacora_atleta.clear()
    get_bitacora_rango.clear()
    get_evaluaciones_antropometricas.clear()
    get_competencias.clear()
    get_invitaciones_pendientes.clear()
    get_pagos_por_temporada.clear()
    get_documentos_correlativos.clear()


# =============================================================================
# WRAPPERS DE COMPATIBILIDAD HACIA ATRÁS
# =============================================================================

# --- Usuarios ---
def obtener_nadadores_activos_cache():
    return get_usuarios(rol="Nadador", estatus="Activo")


def obtener_usuario_por_id_cache(usuario_id):
    return get_usuario_por_id(usuario_id)


def obtener_usuarios_por_rol_cache(rol="Entrenador"):
    return get_usuarios(rol=rol)


# --- Asignaciones ---
def obtener_atletas_asignados_cache(id_entrenador):
    return get_atletas_asignados(id_entrenador)


# --- Marcas históricas ---
def obtener_marcas_historicas_cache(prueba, usuario_id):
    return get_marcas_historicas(usuario_id=usuario_id, prueba=prueba)


def obtener_todo_el_historial_cache(usuario_id):
    return get_marcas_historicas(usuario_id=usuario_id)


# --- Marcas de referencia ---
def obtener_marcas_referencia_cache(prueba, genero, categoria):
    return get_marcas_referencia(prueba=prueba, genero=genero, categoria=categoria)


# --- Marcas del equipo ---
def obtener_marcas_equipo_cache(supabase_cliente, lista_ids_nadadores, prueba_seleccionada):
    ids_tuple = tuple(lista_ids_nadadores) if lista_ids_nadadores else ()
    return get_marcas_equipo(ids_tuple, prueba_seleccionada)


# --- Hitos ---
def obtener_historial_hitos_cache(nadador_id):
    res = get_hitos_atleta(nadador_id)
    return res.get("hitos", []) if res else []


# --- Catálogo de competencias ---
def obtener_catalogo_competencias_cache():
    return get_catalogo_competencias()


# --- Bitácora ---
def obtener_bitacora_atleta_cache(atleta_id):
    return get_bitacora_atleta(atleta_id)


# =============================================================================
# FIN DEL ARCHIVO — v2.5
# =============================================================================