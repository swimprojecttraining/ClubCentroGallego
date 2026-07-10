import streamlit as st
import pandas as pd
import datetime
import io
import zipfile
from supabase import create_client, Client
# Se asume la existencia de la función de mensajería del sistema unificado
from formulas_lib_funciones import enviar_email 

def renderizar_tab_admin(datos_sidebar=None):
    global supabase
    if "supabase" in st.session_state and st.session_state.supabase:
        supabase = st.session_state.supabase
    else:
        st.error("❌ Error: La conexión a Supabase no ha sido inicializada en el login.")
        return
    if st.session_state.rol == "Administrador":
        st.markdown("### 🛡️ Consola de Control de Usuarios e Integridad de Datos")      
        try:
            resp_usuarios = supabase.table("usuarios").select("id, nombre, usuario, email, rol, genero, estatus, fecha_nacimiento").execute()
            if resp_usuarios.data:
                df_usr = pd.DataFrame(resp_usuarios.data)
                st.dataframe(df_usr, use_container_width=True)
                
                st.markdown("**Editar Perfil de Usuario**")
                c_sel, c_rol, c_est, c_gen = st.columns(4)
                with c_sel:
                    id_mod = st.selectbox("ID Usuario:", options=df_usr["id"].tolist())
                    user_actual = df_usr[df_usr["id"] == id_mod].iloc[0]
                with c_rol:
                    nuevo_rol_user = st.selectbox("Rol:", options=["Nadador", "Head Coach", "Entrenador", "Administrador"], index=["Nadador", "Head Coach", "Entrenador", "Administrador"].index(user_actual["rol"]))
                with c_est:
                    nuevo_est_user = st.selectbox("Estatus:", options=["Activo", "Pendiente", "Suspendido", "Bloqueado"], index=["Activo", "Pendiente", "Suspendido", "Bloqueado"].index(user_actual["estatus"]))
                
                campos_deshabilitados = nuevo_rol_user in ["Head Coach", "Entrenador", "Administrador"]
                
                with c_gen:
                    gen_inicial = user_actual["genero"] if user_actual["genero"] in ["F", "M"] else "F"
                    nuevo_gen_user = st.selectbox("Género:", options=["F", "M"], index=["F", "M"].index(gen_inicial), disabled=campos_deshabilitados)
                
                f_nac_inicial = datetime.date.fromisoformat(str(user_actual["fecha_nacimiento"])) if user_actual["fecha_nacimiento"] else datetime.date.today()
                nueva_f_nac_admin = st.date_input("Corregir Fecha Nacimiento:", value=f_nac_inicial, disabled=campos_deshabilitados)
                
                if st.button("⚠️ Forzar Cambios de Perfil"):
                    if user_actual.get("estatus") == "Pendiente" and nuevo_est_user == "Activo":
                        enviar_email(
                            "¡Tu cuenta ha sido activada!", 
                            f"Hola {user_actual['nombre']}, tu cuenta ya está activa y puedes acceder al sistema.", 
                            user_actual["email"]
                        )

                    datos_update = {"rol": nuevo_rol_user, "estatus": nuevo_est_user}
                    if campos_deshabilitados:
                        datos_update["genero"] = None
                        datos_update["fecha_nacimiento"] = None
                    else:
                        datos_update["genero"] = nuevo_gen_user
                        datos_update["fecha_nacimiento"] = nueva_f_nac_admin.isoformat()
                        
                    supabase.table("usuarios").update(datos_update).eq("id", int(id_mod)).execute()
                    st.success("Cambios aplicados con éxito.")
                    st.rerun()
        except Exception as e:
            st.error(f"Error en panel de control: {e}")
        st.markdown("### 💾 Centro de Respaldos y Salvaguarda Local")
        st.info("Descarga copias de seguridad directas desde Supabase en formato CSV para resguardo local o auditorías.")
        
        # Lista oficial de las tablas del Core
        tablas_sistema = ["usuarios", "marcas_historicas", "marcas_referencia", "asignaciones", "catalogo_competencias", "bitacora_entrenamientos", "historial_hitos"]
        
        opcion_backup = st.selectbox("Seleccione el alcance del respaldo:", ["Tabla Individual", "Base de Datos Completa (ZIP)"])
        
        if opcion_backup == "Tabla Individual":
            tabla_sel = st.selectbox("Seleccione la tabla a respaldar:", tablas_sistema)
            
            try:
                res_backup = supabase.table(tabla_sel).select("*").execute()
                if res_backup.data:
                    df_backup = pd.DataFrame(res_backup.data)
                    csv_bytes = df_backup.to_csv(index=False).encode('utf-8-sig')
                    
                    st.download_button(
                        label=f"📥 Descargar Tabla '{tabla_sel}' (CSV)",
                        data=csv_bytes,
                        file_name=f"backup_{tabla_sel}_{datetime.date.today().isoformat()}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("La tabla seleccionada se encuentra vacía.")
            except Exception as e:
                st.error(f"Error al conectar con el servidor de réplica: {e}")
        
        else:
            # =============================================================================
            # LÓGICA MASTER COMPLETADA: COMPRESIÓN EN MEMORIA (ZIP)
            # =============================================================================
            
            with st.spinner("Generando compresión de todas las estructuras del club..."):
                try:
                    # 1. Crear un búfer de bytes en memoria para el archivo ZIP
                    buffer_zip = io.BytesIO()
                    
                    # 2. Abrir el contenedor ZIP en modo escritura
                    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        tablas_vacias = []
                        
                        # Recorrer cada tabla del sistema para extraerla individualmente
                        for tabla in tablas_sistema:
                            res_table = supabase.table(tabla).select("*").execute()
                            
                            if res_table.data:
                                df_table = pd.DataFrame(res_table.data)
                                # Convertir la tabla a CSV crudo en formato string
                                csv_string = df_table.to_csv(index=False, encoding='utf-8-sig')
                                # Escribir el string directamente como un archivo independiente dentro del ZIP
                                zip_file.writestr(f"backup_{tabla}.csv", csv_string)
                            else:
                                tablas_vacias.append(tabla)
                    
                    # 3. Mover el puntero del búfer al principio para que Streamlit pueda leerlo completo
                    buffer_zip.seek(0)
                    
                    # Mostrar advertencias si hubo tablas que no aportaron datos
                    if tablas_vacias:
                        st.caption(f"⚠️ Nota: Las tablas {tablas_vacias} no se incluyeron por estar vacías en Supabase.")
                    
                    # 4. Renderizar el botón de descarga del ZIP maestro listo e instantáneo
                    st.success("✅ Respaldo total empaquetado de forma exitosa.")
                    st.download_button(
                        label="📥 Descargar Base de Datos Completa (ZIP)",
                        data=buffer_zip.getvalue(),
                        file_name=f"MASTER_BACKUP_CLUB_{datetime.date.today().isoformat()}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"Error crítico durante el empaquetado del Master Backup: {e}")
        try:
            resp_usuarios = supabase.table("usuarios").select("id, nombre, usuario, email, rol, genero, estatus, fecha_nacimiento").execute()
            if resp_usuarios.data:
                df_usr = pd.DataFrame(resp_usuarios.data)
                st.dataframe(df_usr, use_container_width=True)
                
                st.markdown("**Editar Perfil de Usuario**")
                c_sel, c_rol, c_est, c_gen = st.columns(4)
                with c_sel:
                    id_mod = st.selectbox("ID Usuario:", options=df_usr["id"].tolist())
                    user_actual = df_usr[df_usr["id"] == id_mod].iloc[0]
                with c_rol:
                    nuevo_rol_user = st.selectbox("Rol:", options=["Nadador", "Head Coach", "Entrenador", "Administrador"], index=["Nadador", "Head Coach", "Entrenador", "Administrador"].index(user_actual["rol"]))
                with c_est:
                    nuevo_est_user = st.selectbox("Estatus:", options=["Activo", "Pendiente", "Suspendido", "Bloqueado"], index=["Activo", "Pendiente", "Suspendido", "Bloqueado"].index(user_actual["estatus"]))
                
                campos_deshabilitados = nuevo_rol_user in ["Head Coach", "Entrenador", "Administrador"]
                
                with c_gen:
                    gen_inicial = user_actual["genero"] if user_actual["genero"] in ["F", "M"] else "F"
                    nuevo_gen_user = st.selectbox("Género:", options=["F", "M"], index=["F", "M"].index(gen_inicial), disabled=campos_deshabilitados)
                
                f_nac_inicial = datetime.date.fromisoformat(str(user_actual["fecha_nacimiento"])) if user_actual["fecha_nacimiento"] else datetime.date.today()
                nueva_f_nac_admin = st.date_input("Corregir Fecha Nacimiento:", value=f_nac_inicial, disabled=campos_deshabilitados)
                
                if st.button("⚠️ Forzar Cambios de Perfil"):
                    if user_actual.get("estatus") == "Pendiente" and nuevo_est_user == "Activo":
                        enviar_email(
                            "¡Tu cuenta ha sido activada!", 
                            f"Hola {user_actual['nombre']}, tu cuenta ya está activa y puedes acceder al sistema.", 
                            user_actual["email"]
                        )

                    datos_update = {"rol": nuevo_rol_user, "estatus": nuevo_est_user}
                    if campos_deshabilitados:
                        datos_update["genero"] = None
                        datos_update["fecha_nacimiento"] = None
                    else:
                        datos_update["genero"] = nuevo_gen_user
                        datos_update["fecha_nacimiento"] = nueva_f_nac_admin.isoformat()
                        
                    supabase.table("usuarios").update(datos_update).eq("id", int(id_mod)).execute()
                    st.success("Cambios aplicados con éxito.")
                    st.rerun()
        except Exception as e:
            st.error(f"Error en panel de control: {e}")
        st.markdown("### 💾 Centro de Respaldos y Salvaguarda Local")
        st.info("Descarga copias de seguridad directas desde Supabase en formato CSV para resguardo local o auditorías.")
        
        # Lista oficial de las tablas del Core
        tablas_sistema = ["usuarios", "marcas_historicas", "marcas_referencia", "asignaciones", "catalogo_competencias", "bitacora_entrenamientos", "historial_hitos"]
        
        opcion_backup = st.selectbox("Seleccione el alcance del respaldo:", ["Tabla Individual", "Base de Datos Completa (ZIP)"])
        
        if opcion_backup == "Tabla Individual":
            tabla_sel = st.selectbox("Seleccione la tabla a respaldar:", tablas_sistema)
            
            try:
                res_backup = supabase.table(tabla_sel).select("*").execute()
                if res_backup.data:
                    df_backup = pd.DataFrame(res_backup.data)
                    csv_bytes = df_backup.to_csv(index=False).encode('utf-8-sig')
                    
                    st.download_button(
                        label=f"📥 Descargar Tabla '{tabla_sel}' (CSV)",
                        data=csv_bytes,
                        file_name=f"backup_{tabla_sel}_{datetime.date.today().isoformat()}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("La tabla seleccionada se encuentra vacía.")
            except Exception as e:
                st.error(f"Error al conectar con el servidor de réplica: {e}")
        
        else:
            # =============================================================================
            # LÓGICA MASTER COMPLETADA: COMPRESIÓN EN MEMORIA (ZIP)
            # =============================================================================
            
            with st.spinner("Generando compresión de todas las estructuras del club..."):
                try:
                    # 1. Crear un búfer de bytes en memoria para el archivo ZIP
                    buffer_zip = io.BytesIO()
                    
                    # 2. Abrir el contenedor ZIP en modo escritura
                    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        tablas_vacias = []
                        
                        # Recorrer cada tabla del sistema para extraerla individualmente
                        for tabla in tablas_sistema:
                            res_table = supabase.table(tabla).select("*").execute()
                            
                            if res_table.data:
                                df_table = pd.DataFrame(res_table.data)
                                # Convertir la tabla a CSV crudo en formato string
                                csv_string = df_table.to_csv(index=False, encoding='utf-8-sig')
                                # Escribir el string directamente como un archivo independiente dentro del ZIP
                                zip_file.writestr(f"backup_{tabla}.csv", csv_string)
                            else:
                                tablas_vacias.append(tabla)
                    
                    # 3. Mover el puntero del búfer al principio para que Streamlit pueda leerlo completo
                    buffer_zip.seek(0)
                    
                    # Mostrar advertencias si hubo tablas que no aportaron datos
                    if tablas_vacias:
                        st.caption(f"⚠️ Nota: Las tablas {tablas_vacias} no se incluyeron por estar vacías en Supabase.")
                    
                    # 4. Renderizar el botón de descarga del ZIP maestro listo e instantáneo
                    st.success("✅ Respaldo total empaquetado de forma exitosa.")
                    st.download_button(
                        label="📥 Descargar Base de Datos Completa (ZIP)",
                        data=buffer_zip.getvalue(),
                        file_name=f"MASTER_BACKUP_CLUB_{datetime.date.today().isoformat()}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"Error crítico durante el empaquetado del Master Backup: {e}")
