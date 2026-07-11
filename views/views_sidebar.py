import streamlit as st
import pandas as pd
from formulas_lib_funciones import calcular_categoria_competencia


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
    
    # 5. Panel de Navegación de Atletas (Conexión Real)
    st.sidebar.subheader("🎯 Panel de Navegación de Atletas")
    
    try:
        # Llamar a la conexión de Supabase que ya está en la memoria
        supabase = st.session_state.supabase
        
        # Lógica de carga según tu rol (Head Coach / Entrenador / Admin)
        if st.session_state.rol == "Entrenador":
            resp_asig = supabase.table("asignaciones").select("atleta_id").eq("entrenador_id", st.session_state.usuario_id).execute()
            ids_asignados = [reg["atleta_id"] for reg in resp_asig.data] if resp_asig.data else []
            if ids_asignados:
                resp_atletas = supabase.table("usuarios").select("id, nombre, genero, fecha_nacimiento").eq("rol", "Nadador").eq("estatus", "Activo").in_("id", ids_asignados).execute()
            else:
                resp_atletas = None
        else:
            # Head Coach y Admin tienen acceso global
            resp_atletas = supabase.table("usuarios").select("id, nombre, genero, fecha_nacimiento").eq("rol", "Nadador").eq("estatus", "Activo").execute()
    
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
                nadador_info = df_atl[df_atl['id'] == st.session_state.selector_nadador_real].iloc[0]
                
                st.session_state.nadador_seleccionado_id = st.session_state.selector_nadador_real
                st.session_state.nadador_seleccionado_nombre = nadador_info['nombre']
                
                # Ahora esto leerá el dato real de la base de datos
                st.session_state.nadador_seleccionado_genero = nadador_info.get('genero', 'N/A')
                
                # Cálculo dinámico usando tu función externa
                fecha_nac = nadador_info.get('fecha_nacimiento')
                st.session_state.nadador_seleccionado_categoria = calcular_categoria_competencia(fecha_nac)
                
                st.rerun()
                
        else:
            st.sidebar.warning("⚠️ No tienes nadadores asignados.")
    
    except Exception as e:
        st.sidebar.error(f"Error en conexión: {e}")
    
    # 🔥 FIX: Diccionario completo sin excepts duplicados al final
    return {
        "titulo_grafico": "Rendimiento del Atleta",
        "simulacion_externa": False
    }
