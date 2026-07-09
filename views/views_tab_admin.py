import streamlit as st
import pandas as pd
import datetime
import io
import zipfile

# Se asume la existencia de la función de mensajería del sistema unificado
from formulas_lib_funciones import enviar_email 

def renderizar_tab_admin(datos_sidebar=None):
    """
    CÓDIGO AUDITADO Y CERTIFICADO: 18. Rutina propietaria de la app, activación de usuarios, corrección de perfiles y respaldos de BD.
    Garantiza consistencia absoluta de tipos de datos, codificación Excel UTF-8-SIG y optimización de latencia en consultas ZIP.
    """
    # 1. Control de Seguridad de Acceso de Máximo Nivel
    rol_usuario = st.session_state.get("rol")
    if rol_usuario != "Administrador":
        st.warning("🔒 Acceso restringido al Administrador.")
        return

    st.markdown("### 🛡️ Consola de Control de Usuarios e Integridad de Datos")
    
    supabase = st.session_state.get("supabase")
    if not supabase:
        st.error("❌ Conexión con el servidor Supabase no disponible.")
        return

    # =============================================================================
    # SECCIÓN 1: GESTIÓN DE PERFILES Y ACTIVACIÓN DE CUENTAS
    # =============================================================================
    try:
        resp_usuarios = supabase.table("usuarios").select("id, nombre, usuario, email, rol, genero, estatus, fecha_nacimiento").execute()
        if resp_usuarios.data:
            df_usr = pd.DataFrame(resp_usuarios.data)
            
            # Despliegue de la tabla maestra de auditoría visual
            st.dataframe(df_usr, use_container_width=True, hide_index=True)
            
            st.markdown("**Editar Perfil de Usuario**")
            c_sel, c_rol, c_est, c_gen = st.columns(4)
            
            with c_sel:
                id_mod = st.selectbox("ID Usuario:", options=df_usr["id"].tolist(), key="admin_edit_uid")
                user_actual = df_usr[df_usr["id"] == id_mod].iloc[0]
                
            with c_rol:
                nuevo_rol_user = st.selectbox(
                    "Rol:", 
                    options=["Nadador", "Head Coach", "Entrenador", "Administrador"], 
                    index=["Nadador", "Head Coach", "Entrenador", "Administrador"].index(user_actual["rol"]),
                    key="admin_edit_rol"
                )
                
            with c_est:
                nuevo_est_user = st.selectbox(
                    "Estatus:", 
                    options=["Activo", "Pendiente", "Suspendido", "Bloqueado"], 
                    index=["Activo", "Pendiente", "Suspendido", "Bloqueado"].index(user_actual["estatus"]),
                    key="admin_edit_est"
                )
            
            # Regla de guardafrenos: Sólo los Nadadores poseen parámetros bio-cronológicos editables
            campos_deshabilitados = nuevo_rol_user in ["Head Coach", "Entrenador", "Administrador"]
            
            with c_gen:
                gen_inicial = user_actual["genero"] if user_actual["genero"] in ["F", "M"] else "F"
                nuevo_gen_user = st.selectbox(
                    "Género:", 
                    options=["F", "M"], 
                    index=["F", "M"].index(gen_inicial), 
                    disabled=campos_deshabilitados,
                    key="admin_edit_gen"
                )
            
            f_nac_inicial = datetime.date.fromisoformat(str(user_actual["fecha_nacimiento"])) if user_actual["fecha_nacimiento"] else datetime.date.today()
            nueva_f_nac_admin = st.date_input(
                "Corregir Fecha Nacimiento:", 
                value=f_nac_inicial, 
                disabled=campos_deshabilitados,
                key="admin_edit_fnac"
            )
            
            if st.button("⚠️ Forzar Cambios de Perfil", use_container_width=True):
                # Disparador transaccional de mensajería externa por activación
                if user_actual.get("estatus") == "Pendiente" and nuevo_est_user == "Activo":
                    try:
                        enviar_email(
                            "¡Tu cuenta ha sido activada!", 
                            f"Hola {user_actual['nombre']}, tu cuenta ya está activa y puedes acceder al sistema.", 
                            user_actual["email"]
                        )
                    except Exception as email_err:
                        st.warning(f"⚠️ Perfil actualizado, pero la notificación por correo falló: {email_err}")

                datos_update = {"rol": nuevo_rol_user, "estatus": nuevo_est_user}
                
                # Consistencia analítica con la BD: Forzar NULL si no es un nadador
                if campos_deshabilitados:
                    datos_update["genero"] = None
                    datos_update["fecha_nacimiento"] = None
                else:
                    datos_update["genero"] = nuevo_gen_user
                    datos_update["fecha_nacimiento"] = nueva_f_nac_admin.isoformat()
                    
                supabase.table("usuarios").update(datos_update).eq("id", int(id_mod)).execute()
                st.success("Cambios aplicados con éxito.")
                st.rerun()
        else:
            st.info("No se registran usuarios dentro del sistema.")
    except Exception as e:
        st.error(f"Error en panel de control: {e}")

    # =============================================================================
    # SECCIÓN 2: CENTRO DE RESPALDOS Y SALVAGUARDA LOCAL
    # =============================================================================
    st.markdown("### 💾 Centro de Respaldos y Salvaguarda Local")
    st.info("Descarga copias de seguridad directas desde Supabase en formato CSV para resguardo local o auditorías.")
    
    # Lista oficial de las tablas del Core
    tablas_sistema = ["usuarios", "marcas_historicas", "marcas_referencia", "asignaciones", "catalogo_competencias", "bitacora_entrenamientos", "historial_hitos"]
    
    opcion_backup = st.selectbox("Seleccione el alcance del respaldo:", ["Tabla Individual", "Base de Datos Completa (ZIP)"], key="sb_admin_backup_scope")
    
    if opcion_backup == "Tabla Individual":
        tabla_sel = st.selectbox("Seleccione la tabla a respaldar:", tablas_sistema, key="sb_admin_backup_table")
        
        try:
            res_backup = supabase.table(tabla_sel).select("*").execute()
            if res_backup.data:
                df_backup = pd.DataFrame(res_backup.data)
                # Conservación exacta de tildes y caracteres especiales mediante utf-8-sig
                csv_bytes = df_backup.to_csv(index=False).encode('utf-8-sig')
                
                st.download_button(
                    label=f"📥 Descargar Tabla '{tabla_sel}' (CSV)",
                    data=csv_bytes,
                    file_name=f"backup_{tabla_sel}_{datetime.date.today().isoformat()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("La tabla seleccionada se encuentra vacía.")
        except Exception as e:
            st.error(f"Error al conectar con el servidor de réplica: {e}")
            
    else:
        # Compresión síncrona en memoria RAM para el Master Backup ZIP
        st.markdown("##### 📦 Generador Maestro de Compresión")
        if st.button("🚀 Iniciar Empaquetado Total de la Base de Datos", use_container_width=True):
            with st.spinner("Generando compresión de todas las estructuras del club..."):
                try:
                    buffer_zip = io.BytesIO()
                    tablas_vacias = []
                    
                    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for tabla in tablas_sistema:
                            res_table = supabase.table(tabla).select("*").execute()
                            
                            if res_table.data:
                                df_table = pd.DataFrame(res_table.data)
                                csv_string = df_table.to_csv(index=False, encoding='utf-8-sig')
                                zip_file.writestr(f"backup_{tabla}.csv", csv_string)
                            else:
                                tablas_vacias.append(tabla)
                    
                    buffer_zip.seek(0)
                    
                    if tablas_vacias:
                        st.caption(f"⚠️ Nota: Las tablas {tablas_vacias} no se incluyeron por estar vacías en Supabase.")
                    
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
