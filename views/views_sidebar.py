import streamlit as st

def renderizar_sidebar_acceso_y_gestion():
    # 1. Identificación de usuario registrado
    # Se asume que estos valores ya vienen del sistema de login principal
    st.sidebar.markdown(f"**Usuario:** {st.session_state.get('nombre_usuario', 'Usuario')}")
    
    # 2. Nivel de acceso
    nivel = st.session_state.get('nivel_acceso', 'Invitado')
    st.sidebar.markdown(f"**Nivel:** :green[{nivel}]")
    
    # 3. Botón de salir del sistema
    if st.sidebar.button("🚪 Salir del Sistema"):
        # Lógica de limpieza de sesión
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
        
    st.sidebar.divider()
    
    # 4. Botón de pánico de limpieza de caché
    if st.sidebar.button("🔄 Refrescar Datos (Limpiar Caché)"):
        st.cache_data.clear()
        st.rerun()
        
    st.sidebar.divider()
