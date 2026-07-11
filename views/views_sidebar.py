import streamlit as st
import pandas as pd
from formulas_lib_funciones import calcular_categoria_competencia

def renderizar_sidebar_acceso_y_gestion():
    # 1. Identificación de usuario registrado
    st.sidebar.markdown(f"**Usuario:** {st.session_state.get('nombre_usuario', 'Usuario')}")
    
    # 2. Nivel de acceso
    nivel = st.session_state.get('nivel_acceso', 'Invitado')
    st.sidebar.markdown(f"**Nivel:** :green[{nivel}]")
    
    # 3. Botones del sistema
    if st.sidebar.button("🚪 Salir del Sistema"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
        
    st.sidebar.divider()
    
    if st.sidebar.button("🔄 Refrescar Datos (Limpiar Caché)"):
        st.cache_data.clear()
        st.rerun()
        
    st.sidebar.divider()
    
    # 4. Panel de Navegación de Atletas
    rol_actual = st.session_state.get('rol', 'Invitado')
    
    if rol_actual in ["Head Coach", "Entrenador", "Administrador"]:
        st.sidebar.subheader("🎯 Panel de Navegación de Atletas")
        try:
            supabase = st.session_state.supabase
            
            # Filtrado basado en tu tabla intermedia "asignaciones"
            if rol_actual == "Entrenador":
                resp_asig = supabase.table("asignaciones").select("atleta_id").eq("entrenador_id", st.session_state.usuario_id).execute()
                ids_asignados = [reg["atleta_id"] for reg in resp_asig.data] if resp_asig.data else []
                
                if ids_asignados:
                    resp_atletas = supabase.table("usuarios").select("id, nombre, genero, fecha_nacimiento").eq("rol", "Nadador").eq("estatus", "Activo").in_("id", ids_asignados).execute()
                else:
                    resp_atletas = None 
            else:
                # Head Coach y Administrador tienen acceso global
                resp_atletas = supabase.table("usuarios").select("id, nombre, genero, fecha_nacimiento").eq("rol", "Nadador").eq("estatus", "Activo").execute()
            
            if resp_atletas and resp_atletas.data:
                df_atl = pd.DataFrame(resp_atletas.data)
                dict_atletas = dict(zip(df_atl["id"], df_atl["nombre"]))
                
                sel_id = st.sidebar.selectbox("Monitorear Nadador:", options=list(dict_atletas.keys()), format_func=lambda x: dict_atletas[x])
                atleta_row = df_atl[df_atl["id"] == sel_id].iloc[0]
                
                st.session_state.nadador_seleccionado_id = int(atleta_row["id"])
                st.session_state.nadador_seleccionado_nombre = atleta_row["nombre"]
                st.session_state.nadador_seleccionado_genero = atleta_row["genero"]
                
                # --- BLINDAJE DE LA CATEGORÍA ---
                resultado_cat = calcular_categoria_competencia(atleta_row["fecha_nacimiento"])
                st.session_state.nadador_seleccionado_categoria = resultado_cat[0] if isinstance(resultado_cat, tuple) else str(resultado_cat)
                
            else:
                st.sidebar.warning("⚠️ No tienes nadadores asignados.")
                st.session_state.nadador_seleccionado_id = None
                
        except Exception as e:
            st.sidebar.error(f"Error cargando nómina de atletas: {e}")
            
    else:
        # Lógica para cuando el usuario es "Nadador"
        st.session_state.nadador_seleccionado_id = st.session_state.get('usuario_id')
        st.session_state.nadador_seleccionado_nombre = st.session_state.get('nombre_nadador')
        st.session_state.nadador_seleccionado_genero = st.session_state.get('genero')
        st.session_state.nadador_seleccionado_categoria = st.session_state.get('categoria_atleta', 'Sin Categoría')

    # Retorno final que evita errores en views_tab_router
    return {
        "titulo_grafico": "Rendimiento del Atleta",
        "simulacion_externa": False
    }
