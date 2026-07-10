import streamlit as st

# 1. Definimos la función en el mismo archivo para prueba rápida
def renderizar_sidebar_acceso_y_gestion():
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

# 3. Aquí iría el resto de tu app...
st.title("Probando el nuevo Sidebar")