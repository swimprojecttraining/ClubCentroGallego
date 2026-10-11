# -------------------------------------------------------------
# CACHÉ INTELIGENTE PARA CONSULTAS A SUPABASE (OPTIMIZACIÓN DE RENDIMIENTO)
# -------------------------------------------------------------
# v2.0 — Refactorización incremental con compatibilidad total
#
# CAMBIOS vs v1.0:
#   1. Cliente Supabase singleton con @st.cache_resource (no se recrea por rerun)
#   2. Nuevas funciones unificadas: get_usuarios, get_marcas_historicas, etc.
#   3. Nuevas funciones bulk: get_marcas_historicas_bulk, get_marcas_equipo
#   4. Las funciones antiguas (obtener_*_cache) se mantienen como WRAPPERS
#      que llaman a las nuevas. NADA se rompe.
#   5. Invalidación explícita: invalidar_cache_marcas() tras inserts/updates
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
            "id, nombre, email, genero, rol, estatus, fecha_nacimiento"
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
# MARCAS HISTÓRICAS — UNA función que sirve para todos los casos
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_marcas_historicas(
    usuario_id: int,
    prueba: str | None = None,
    columnas: str = "id, prueba, edad, tiempo, nota",
) -> list[dict]:
    """
    Reemplaza a obtener_marcas_historicas_cache + obtener_todo_el_historial_cache.
    Si `prueba` es None, trae todo el historial del atleta.
    """
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
    """
    Trae las marcas de MÚLTIPLES atletas en UNA SOLA query.
    Reemplaza el patrón N+1 (un for con una query por atleta).

    IMPORTANTE: `usuario_ids` debe ser una tupla (hashable), no una lista.
    """
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


# =============================================================================
# MARCAS DEL EQUIPO — query con IN (evita N+1)
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_marcas_equipo(lista_ids: tuple, prueba: str) -> pd.DataFrame:
    """
    Reemplaza a obtener_marcas_equipo_cache.
    Usa `tuple` (hashable) para que st.cache_data funcione de verdad.
    """
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
# CATÁLOGOS ESTÁTICOS — ttl largo
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
# HITOS — una sola función, no dos
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_hitos_atleta(nadador_id: int) -> dict | None:
    """
    Unifica obtener_historial_hitos_cache y obtener_datos_hitos_atleta.
    Devuelve {'hitos': [...]} o None.
    """
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


# =============================================================================
# INVALIDACIÓN DE CACHÉ (llamar tras inserts/updates)
# =============================================================================
def invalidar_cache_marcas():
    """Limpia la caché de marcas. Úsala tras insertar/editar marcas."""
    get_marcas_historicas.clear()
    get_marcas_historicas_bulk.clear()
    get_marcas_equipo.clear()


def invalidar_cache_usuarios():
    """Limpia la caché de usuarios. Úsala tras insertar/editar usuarios."""
    get_usuarios.clear()
    get_usuario_por_id.clear()


def invalidar_cache_asignaciones():
    """Limpia la caché de asignaciones."""
    get_atletas_asignados.clear()


def invalidar_cache_hitos():
    """Limpia la caché de hitos."""
    get_hitos_atleta.clear()


def invalidar_toda_la_cache():
    """Limpieza total. Útil como botón de emergencia en el sidebar del admin."""
    get_usuarios.clear()
    get_usuario_por_id.clear()
    get_atletas_asignados.clear()
    get_marcas_historicas.clear()
    get_marcas_historicas_bulk.clear()
    get_marcas_equipo.clear()
    get_catalogo_competencias.clear()
    get_marcas_referencia.clear()
    get_hitos_atleta.clear()
    get_bitacora_atleta.clear()


# =============================================================================
# =============================================================================
# WRAPPERS DE COMPATIBILIDAD HACIA ATRÁS
# =============================================================================
# Estas funciones mantienen los NOMBRES ANTIGUOS para no romper las 11 pestañas
# que las importan. Internamente llaman a las nuevas. Cuando todas las pestañas
# estén migradas, se pueden borrar.
# =============================================================================
# =============================================================================


# --- Usuarios ---
def obtener_nadadores_activos_cache():
    """[DEPRECATED] Usar get_usuarios(rol='Nadador', estatus='Activo')"""
    return get_usuarios(rol="Nadador", estatus="Activo")


def obtener_usuario_por_id_cache(usuario_id):
    """[DEPRECATED] Usar get_usuario_por_id(usuario_id)"""
    return get_usuario_por_id(usuario_id)


def obtener_usuarios_por_rol_cache(rol="Entrenador"):
    """[DEPRECATED] Usar get_usuarios(rol=rol)"""
    return get_usuarios(rol=rol)


# --- Asignaciones ---
def obtener_atletas_asignados_cache(id_entrenador):
    """[DEPRECATED] Usar get_atletas_asignados(entrenador_id)"""
    return get_atletas_asignados(id_entrenador)


# --- Marcas históricas ---
def obtener_marcas_historicas_cache(prueba, usuario_id):
    """[DEPRECATED] Usar get_marcas_historicas(usuario_id, prueba=prueba)"""
    # Compatibilidad con la firma antigua (prueba, usuario_id)
    return get_marcas_historicas(usuario_id=usuario_id, prueba=prueba)


def obtener_todo_el_historial_cache(usuario_id):
    """[DEPRECATED] Usar get_marcas_historicas(usuario_id)"""
    return get_marcas_historicas(usuario_id=usuario_id)


# --- Marcas de referencia ---
def obtener_marcas_referencia_cache(prueba, genero, categoria):
    """[DEPRECATED] Usar get_marcas_referencia(prueba, genero, categoria)"""
    return get_marcas_referencia(prueba=prueba, genero=genero, categoria=categoria)


# --- Marcas del equipo ---
def obtener_marcas_equipo_cache(supabase_cliente, lista_ids_nadadores, prueba_seleccionada):
    """
    [DEPRECATED] Usar get_marcas_equipo(tuple(lista_ids), prueba).
    Nota: El primer argumento (supabase_cliente) se ignora. Ya no se necesita.
    """
    # Convertimos la lista a tupla para que sea hashable y cacheable
    ids_tuple = tuple(lista_ids_nadadores) if lista_ids_nadadores else ()
    return get_marcas_equipo(ids_tuple, prueba_seleccionada)


# --- Hitos ---
def obtener_historial_hitos_cache(nadador_id):
    """[DEPRECATED] Usar get_hitos_atleta(nadador_id)"""
    res = get_hitos_atleta(nadador_id)
    return res.get("hitos", []) if res else []


# --- Catálogo de competencias ---
def obtener_catalogo_competencias_cache():
    """[DEPRECATED] Usar get_catalogo_competencias()"""
    return get_catalogo_competencias()


# --- Bitácora ---
def obtener_bitacora_atleta_cache(atleta_id):
    """[DEPRECATED] Usar get_bitacora_atleta(atleta_id)"""
    return get_bitacora_atleta(atleta_id)


# =============================================================================
# FIN DEL ARCHIVO
# =============================================================================