import streamlit as st
from conexion views_login_app.py supabase
# 1. Definimos la función en el mismo archivo para prueba rápida
def renderizar_sidebar_acceso_y_gestion(supabase):
    st.sidebar.markdown(f"**Usuario:** Alvaro Gallegos") # Ajusta según tu lógica real
    st.sidebar.markdown(f"**Nivel:** :green[Administrador]")
    
    if st.sidebar.button("🚪 Salir del Sistema"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
        
    st.sidebar.divider()
    
    if st.sidebar.button("🔄 Refrescar Datos (Limpiar Caché)"):
        st.cache_data.clear()
        st.rerun()
        
    st.sidebar.divider()

# 2. Llamamos a la función
renderizar_sidebar_acceso_y_gestion()
# 5. Panel de Navegación de Atletas (Conexión Real)
st.sidebar.subheader("🎯 Panel de Navegación de Atletas")

try:
    # Lógica de carga según tu rol (Head Coach / Entrenador / Admin)
    if st.session_state.rol == "Entrenador":
        resp_asig = supabase.table("asignaciones").select("atleta_id").eq("entrenador_id", st.session_state.usuario_id).execute()
        ids_asignados = [reg["atleta_id"] for reg in resp_asig.data] if resp_asig.data else []
        if ids_asignados:
            resp_atletas = supabase.table("usuarios").select("id, nombre").eq("rol", "Nadador").eq("estatus", "Activo").in_("id", ids_asignados).execute()
        else:
            resp_atletas = None
    else:
        # Head Coach y Admin tienen acceso global
        resp_atletas = supabase.table("usuarios").select("id, nombre").eq("rol", "Nadador").eq("estatus", "Activo").execute()

    if resp_atletas and resp_atletas.data:
        df_atl = pd.DataFrame(resp_atletas.data)
        # Diccionario para que el selectbox muestre nombres pero maneje IDs
        dict_atletas = dict(zip(df_atl["id"], df_atl["nombre"]))
        
        # Selección inicial segura
        if "nadador_seleccionado_id" not in st.session_state:
            st.session_state.nadador_seleccionado_id = list(dict_atletas.keys())[0]

        sel_id = st.sidebar.selectbox(
            "Monitorear Nadador:", 
            options=list(dict_atletas.keys()), 
            format_func=lambda x: dict_atletas[x],
            key="selector_nadador_real"
        )

        # Si el usuario cambió la selección en el sidebar, actualizamos el estado
        if st.session_state.selector_nadador_real != st.session_state.nadador_seleccionado_id:
            st.session_state.nadador_seleccionado_id = st.session_state.selector_nadador_real
            # Actualizamos también el nombre para consistencia
            st.session_state.nadador_seleccionado_nombre = dict_atletas[sel_id]
            st.rerun()
            
    else:
        st.sidebar.warning("⚠️ No tienes nadadores asignados.")

except Exception as e:
    st.sidebar.error(f"Error en conexión: {e}")
# 3. Aquí iría el resto de tu app...
st.title("Probando el nuevo Sidebar")
