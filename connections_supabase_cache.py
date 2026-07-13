# -------------------------------------------------------------
# CACHÉ INTELIGENTE PARA CONSULTAS A SUPABASE (OPTIMIZACIÓN DE RENDIMIENTO)
# -------------------------------------------------------------
import streamlit as st

# --- FUNCIÓN AUXILIAR DE ACCESO ---
def _get_db():
    """Retorna la instancia de Supabase de la sesión o None."""
    return st.session_state.get("supabase")

# --- CACHÉ INTELIGENTE ---

@st.cache_data(ttl=86400, show_spinner=False)
def obtener_marcas_referencia_cache(prueba, genero, categoria):
    supabase = _get_db()
    if not supabase: return []
    try:
        ref_resp = supabase.table("marcas_referencia").select("*") \
            .eq("prueba", prueba).eq("genero", genero).eq("categoria", categoria).execute()
        return ref_resp.data if ref_resp.data else []
    except Exception: return []

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_usuario_por_id_cache(usuario_id):
    supabase = _get_db()
    if not supabase: return None
    try:
        response = supabase.table("usuarios").select("id, nombre, genero, rol, estatus, fecha_nacimiento") \
            .eq("id", usuario_id).execute()
        return response.data[0] if response.data else None
    except Exception: return None

@st.cache_data(ttl=300, show_spinner=False)
def obtener_historial_hitos_cache(nadador_id):
    """Historial de hitos y competencias"""
    supabase = _get_db()
    if not supabase: return []
    try:
        # Nota: La relación con catalogo_competencias depende de que esté bien configurada en Supabase
        res = supabase.table("historial_hitos").select("*, catalogo_competencias(*)") \
            .eq("usuario_id", nadador_id).execute()
        return res.data if res.data else []
    except Exception: return []

@st.cache_data(ttl=300, show_spinner=False)
def obtener_marcas_historicas_cache(prueba, usuario_id):
    supabase = _get_db()
    if not supabase: return []
    try:
        response = supabase.table("marcas_historicas").select("id, edad, tiempo, nota") \
            .eq("prueba", prueba).eq("usuario_id", usuario_id).order("edad", desc=False).execute()
        return response.data if response.data else []
    except Exception: return []

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_catalogo_competencias_cache():
    supabase = _get_db()
    if not supabase: return []
    try:
        response = supabase.table("catalogo_competencias").select("*").execute()
        return response.data if response.data else []
    except Exception: return []
