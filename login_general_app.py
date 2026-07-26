import streamlit as st
from supabase import create_client, Client
import datetime
import random
import hmac
import hashlib
import base64
import time

# 📦 IMPORTACIÓN DIRECTA DESDE TU LIBRERÍA REAL DE FUNCIONES
from formulas_lib_funciones import (
    hash_password, 
    desencriptar_credencial, 
    enviar_email, 
    calcular_categoria_competencia
)

# ============================================================
# ⚙️ CONEXIÓN GLOBAL CACHEADA (A nivel raíz del archivo)
# ============================================================
@st.cache_resource
def obtener_cliente_supabase():
    """
    Crea y mantiene viva la instancia de conexión a Supabase en memoria.
    Se ejecuta una sola vez para la app y la reutilizan todos los usuarios/reruns.
    """
    return create_client(
        st.secrets["SUPABASE_URL"], 
        st.secrets["SUPABASE_KEY"]
    )

def login_usuario(user, password, client_db):
    try:
        user_lower = user.strip().lower()
        hashed_pw = hash_password(password)
        # Consulta exacta a la estructura de tu BD local
        response = client_db.table("usuarios").select("id, nombre, genero, rol, estatus, fecha_nacimiento").eq("usuario", user_lower).eq("contrasena", hashed_pw).execute()
        
        if response.data:
            user_data = response.data[0]
            
            if user_data.get("estatus") == "Pendiente":
                st.error("⚠️ Tu cuenta está en proceso de revisión por la administración. Aún no puedes ingresar.")
                return False
                
            if user_data.get("estatus", "Activo") in ["Suspendido", "Bloqueado"]:
                st.error(f"❌ Cuenta {user_data['estatus']}. Contacte a la dirección técnica.")
                return False
                
            # --- VARIABLES GENERALES PARA CUALQUIER ROL ---
            st.session_state.autenticado = True
            st.session_state.usuario_id = user_data["id"]
            st.session_state.nombre_usuario = user_data["nombre"]  # 💡 Genérico para el sistema
            st.session_state.nombre_nadador = user_data["nombre"]
            st.session_state.genero = user_data.get("genero", "M")
            st.session_state.rol = user_data.get("rol", "Nadador")
            st.session_state.fecha_nacimiento = user_data.get("fecha_nacimiento")
            
            # --- SEGREGACIÓN SEGÚN ROL DE USUARIO ---
            if st.session_state.rol == "Nadador":
                # Lógica exclusiva para atletas
                if st.session_state.fecha_nacimiento:
                    cat, ed_c = calcular_categoria_competencia(st.session_state.fecha_nacimiento)
                else:
                    cat, ed_c = "Sin Categoría", 0
                
                st.session_state.categoria_atleta = cat
                st.session_state.edad_comp_atleta = ed_c
                st.session_state.nadador_seleccionado_id = user_data["id"]
                st.session_state.nadador_seleccionado_nombre = user_data["nombre"]
                st.session_state.nadador_seleccionado_genero = user_data.get("genero", "F")
                st.session_state.nadador_seleccionado_categoria = cat
            else:
                # Inicialización limpia para Club / Administrador / Entrenadores / Head Coach
                st.session_state.categoria_atleta = None
                st.session_state.edad_comp_atleta = None
                st.session_state.nadador_seleccionado_id = None
                st.session_state.nadador_seleccionado_nombre = None
                st.session_state.nadador_seleccionado_genero = None
                st.session_state.nadador_seleccionado_categoria = None

            return True
        return False
    except Exception as e:
        st.error(f"Error en Login: {e}")
        return False


def mostrar_pantalla_login():
    """
    Función principal que renderiza el Login, Certificación por Pre-Alta (OTP) y Recuperación.
    Llamada directamente desde root_app.py tras validar el handshake.
    """
    if "rec_codigo_verificacion" not in st.session_state:
        st.session_state.rec_codigo_verificacion = None
    if "rec_datos_temporales" not in st.session_state:
        st.session_state.rec_datos_temporales = None

    # ------------------------------------------------------------
    # 1. RECEPTOR Y VALIDADOR CRIPTOGRÁFICO INTERCLUBES (HANDSHAKE)
    # ------------------------------------------------------------
    if "supabase" not in st.session_state:
        st.session_state.supabase = None
    if "club_seleccionado" not in st.session_state:
        st.session_state.club_seleccionado = None
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.supabase:
        try:
            st.session_state.supabase = create_client(
                st.secrets["SUPABASE_URL"], 
                st.secrets["SUPABASE_KEY"]
            )
            st.session_state.club_seleccionado = st.secrets.get("NOMBRE_CLUB_LOCAL", "Centro Gallego")
        except Exception as e:
            st.error(f"❌ Error de infraestructura al conectar base de datos local: {e}")
            st.stop()

    # ------------------------------------------------------------
    # 2. INTERFAZ DE PORTADA UNIFICADA MULTI-TENANT PRO
    # ------------------------------------------------------------
    if not st.session_state.autenticado:
        st.markdown(f"<h2 style='text-align: center;'>🏊‍♂️ {st.session_state.club_seleccionado}</h2>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: gray;'>Sistema de Control de Entrenamientos y Rendimiento</h4>", unsafe_allow_html=True)
        
        instancia_supabase_club = st.session_state.supabase

        c_login, _ = st.columns([1.5, 1.5])
        
        with c_login:
            tab_login, tab_registro_otp, tab_recuperar = st.tabs([
                "🔑 Iniciar Sesión", 
                "📝 Registro (Preinscrito por el club)", 
                "🔄 Recuperar Contraseña"
            ])
            
            # --- TAB LOGIN ---
            with tab_login:
                st.caption("Nota: Los nombres de usuario se procesan en minúsculas.")
                with st.form("form_login"):
                    usuario_input = st.text_input("Usuario o Correo:")
                    usuario_lower = usuario_input.lower()
                    contrasena_input = st.text_input("Contraseña:", type="password")
                    
                    if st.form_submit_button("Ingresar"):
                        if login_usuario(usuario_lower, contrasena_input, instancia_supabase_club):
                            st.success("Acceso autorizado.")
                            st.rerun()
                        else:
                            st.error("Credenciales incorrectas o cuenta en revisión. Verifique sus datos.")
                            
            # --- TAB ÚNICO DE REGISTRO: CERTIFICACIÓN DE PRE-ALTA VIA OTP ---
            with tab_registro_otp:
                st.markdown("### 📝 Registro de Usuarios (Pre-Alta)")
                st.caption("Introduce el código OTP enviado por el club y verifica tus datos para activar tu cuenta.")
                
                with st.form("form_activar_prealta"):
                    otp_token_input = st.text_input("Código OTP (6 dígitos):", max_chars=6, placeholder="Ej: 489123")
                    email_prealta_input = st.text_input("Correo electrónico registrado en la pre-alta:")
                    
                    st.markdown("---")
                    st.markdown("##### 🔐 Credenciales y Acceso Definitivo")
                    nuevo_alias_pa = st.text_input("Nombre de Usuario (Alias) deseado:", placeholder="ej: alberto_jordan")
                    nueva_clave_pa = st.text_input("Establecer Contraseña:", type="password")
                    confirmar_clave_pa = st.text_input("Confirmar Contraseña:", type="password")
                    
                    if st.form_submit_button("🚀 Certificar y Crear Cuenta", use_container_width=True):
                        if not otp_token_input or not email_prealta_input or not nuevo_alias_pa or not nueva_clave_pa:
                            st.error("⚠️ Todos los campos son obligatorios.")
                        elif nueva_clave_pa != confirmar_clave_pa:
                            st.error("❌ Las contraseñas no coinciden.")
                        else:
                            try:
                                # Consulta a la tabla 'invitaciones'
                                res_inv = instancia_supabase_club.table("invitaciones")\
                                    .select("*")\
                                    .eq("token", otp_token_input.strip())\
                                    .eq("email", email_prealta_input.strip().lower())\
                                    .eq("usado", False)\
                                    .execute()
                                
                                if not res_inv.data:
                                    st.error("❌ Código OTP inválido, expirado o el correo no coincide.")
                                else:
                                    invitacion = res_inv.data[0]
                                    expira_en = datetime.datetime.fromisoformat(invitacion["expira_en"])
                                    
                                    if datetime.datetime.now(datetime.timezone.utc) > expira_en.replace(tzinfo=datetime.timezone.utc):
                                        st.error("⌛ El código OTP ha expirado (vigencia de 24 horas). Solicite uno nuevo a la administración.")
                                    else:
                                        datos_perfil = invitacion.get("datos_perfil", {})
                                        
                                        usuario_oficial = {
                                            "nombre": invitacion["nombre"],
                                            "usuario": nuevo_alias_pa.strip().lower(),
                                            "email": invitacion["email"],
                                            "contrasena": hash_password(nueva_clave_pa),
                                            "rol": invitacion["rol"],
                                            "estatus": "Activo",
                                            "cedula": datos_perfil.get("cedula", ""),
                                            "telefono": datos_perfil.get("telefono", ""),
                                            "genero": "F" if datos_perfil.get("sexo", "Femenino") == "Femenino" else "M",
                                            "fecha_nacimiento": datos_perfil.get("fecha_nacimiento", None)
                                        }
                                        
                                        instancia_supabase_club.table("usuarios").insert(usuario_oficial).execute()
                                        instancia_supabase_club.table("invitaciones").update({"usado": True}).eq("id", invitacion["id"]).execute()
                                        
                                        st.success(f"🎉 ¡Registro completado exitosamente como **{invitacion['rol']}**! Ya puedes iniciar sesión.")
                            except Exception as pa_err:
                                st.error(f"Error al procesar el registro: {pa_err}")

            # --- TAB RECUPERAR ---
            with tab_recuperar:
                st.markdown("### Restablecer Contraseña")
                if st.session_state.rec_codigo_verificacion:
                    st.info(f"Se ha enviado un código de seguridad a la dirección vinculada.")
                    with st.form("form_verificacion_recuperacion"):
                        codigo_rec_ingresado = st.text_input("Ingrese el código temporal de recuperación:")
                        
                        if st.form_submit_button("Validar Código y Cambiar Contraseña"):
                            if codigo_rec_ingresado.strip() == str(st.session_state.rec_codigo_verificacion):
                                try:
                                    datos = st.session_state.rec_datos_temporales
                                    instancia_supabase_club.table("usuarios").update({"contrasena": datos["nueva_contrasena"]}).eq("id", datos["user_id"]).execute()
                                    st.success("✅ Contraseña actualizada correctamente. Ya puede iniciar sesión.")
                                    st.session_state.rec_codigo_verificacion = None
                                    st.session_state.rec_datos_temporales = None
                                except Exception as rec_err:
                                    st.error(f"Error al actualizar la contraseña: {rec_err}")
                            else:
                                st.error("❌ El código ingresado es incorrecto.")
                                
                    if st.button("❌ Cancelar Recuperación"):
                        st.session_state.rec_codigo_verificacion = None
                        st.session_state.rec_datos_temporales = None
                        st.rerun()
                else:
                    with st.form("form_recuperacion"):
                        rec_usuario = st.text_input("Nombre de Usuario (Alias):")
                        rec_email = st.text_input("Correo Electrónico Asociado:")
                        nueva_clave = st.text_input("Nueva Contraseña Deseada:", type="password")
                        confirmar_clave = st.text_input("Confirmar Nueva Contraseña:", type="password")
                        
                        if st.form_submit_button("🔄 Solicitar Código de Recuperación"):
                            if not (rec_usuario and rec_email and nueva_clave and confirmar_clave):
                                st.error("Todos los campos del formulario de recuperación son obligatorios.")
                            elif nueva_clave != confirmar_clave:
                                st.error("La confirmación no coincide con la nueva contraseña introducida.")
                            else:
                                rec_usuario_clean = rec_usuario.strip().lower()
                                try:
                                    verificacion = instancia_supabase_club.table("usuarios").select("id, estatus, nombre").eq("usuario", rec_usuario_clean).eq("email", rec_email.strip()).execute()
                                    if verificacion.data:
                                        user_info = verificacion.data[0]
                                        if user_info.get("estatus") in ["Suspendido", "Bloqueado"]:
                                            st.error("Esta cuenta se encuentra suspendida o bloqueada por la administración.")
                                        else:
                                            codigo_rec_temp = random.randint(100000, 999999)
                                            st.session_state.rec_datos_temporales = {
                                                "user_id": user_info["id"],
                                                "nueva_contrasena": hash_password(nueva_clave)
                                            }
                                            
                                            cuerpo_rec_mail = f"Hola {user_info['nombre']},\n\nHas solicitado un restablecimiento de contraseña. Tu código de seguridad temporal es: {codigo_rec_temp}\n\nSi no realizaste esta acción, contacta de inmediato al administrador."
                                            if enviar_email("Código de Seguridad - Recuperación de Contraseña", cuerpo_rec_mail, rec_email.strip()):
                                                st.session_state.rec_codigo_verificacion = codigo_rec_temp
                                                st.success("📩 Código de seguridad enviado al correo electrónico.")
                                                st.rerun()
                                            else:
                                                st.error("Error al enviar el correo de recuperación.")
                                    else:
                                        st.error("❌ Los datos proporcionados no coinciden con ningún registro activo.")
                                except Exception as rec_err:
                                    st.error(f"Error durante el proceso de restablecimiento: {rec_err}")                         
        st.stop()
