# -------------------------------------------------------------
# CACHÉ INTELIGENTE PARA CONSULTAS A SUPABASE (OPTIMIZACIÓN DE RENDIMIENTO)
# -------------------------------------------------------------
@st.cache_data(ttl=86400, show_spinner=False)
def obtener_marcas_referencia_cache(prueba, genero, categoria):
    """Marca de referencia: Cambia ~1 vez al año. Caché por 24h."""
    try:
        supabase = st.session_state.get("supabase_client")
        if not supabase:
            return []
        ref_resp = supabase.table("marcas_referencia").select("*") \
            .eq("prueba", prueba) \
            .eq("genero", genero) \
            .eq("categoria", categoria).execute()
        return ref_resp.data if ref_resp.data else []
    except Exception:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_usuario_por_id_cache(usuario_id):
    """Datos de usuario (fecha_nacimiento, nombre, etc.): No cambian. Caché 1h."""
    try:
        supabase = st.session_state.get("supabase_client")
        if not supabase:
            return None
        response = supabase.table("usuarios") \
            .select("id, nombre, genero, rol, estatus, fecha_nacimiento") \
            .eq("id", usuario_id) \
            .execute()
        return response.data[0] if response.data else None
    except Exception:
        return None

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_catalogo_competencias_cache():
    """Catálogo de competencias: Rara vez cambia. Caché 1h."""
    try:
        supabase = st.session_state.get("supabase_client")
        if not supabase:
            return []
        response = supabase.table("catalogo_competencias").select("*").execute()
        return response.data if response.data else []
    except Exception:
        return []

@st.cache_data(ttl=300, show_spinner=False)
def obtener_historial_hitos_cache(nadador_id):
    """Historial de hitos: Vinculado a competiciones. Caché 5 min para fluidez."""
    try:
        supabase = st.session_state.get("supabase_client")
        if not supabase:
            return []
        res_hitos = supabase.table("historial_hitos") \
            .select("*, catalogo_competencias(*)") \
            .eq("usuario_id", nadador_id) \
            .execute()
        return res_hitos.data if res_hitos.data else []
    except Exception:
        return []

@st.cache_data(ttl=300, show_spinner=False)
def obtener_marcas_historicas_cache(prueba, usuario_id):
    """Marcas históricas: Se actualizan cada 2-3 meses tras cada hito. Caché 5 min."""
    try:
        supabase = st.session_state.get("supabase_client")
        if not supabase:
            return []
        response = supabase.table("marcas_historicas") \
            .select("id, edad, tiempo, nota") \
            .eq("prueba", prueba) \
            .eq("usuario_id", usuario_id) \
            .order("edad", desc=False).execute()
        return response.data if response.data else []
    except Exception:
        return []
