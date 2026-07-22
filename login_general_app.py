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
                # Inicialización limpia para Club / Administrador / Entrenadores
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
    Función principal que renderiza el Login, Registro y Recuperación.
    Llamada directamente desde root_app.py tras validar el handshake.
    """
    # Inicialización de estados de registro si no existen
    if "reg_codigo_verificacion" not in st.session_state:
        st.session_state.reg_codigo_verificacion = None
    if "reg_datos_temporales" not in st.session_state:
        st.session_state.reg_datos_temporales = None
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

    # Si entramos aquí, asumimos que st.session_state.puente_validado ya es True gracias al root_app.py.
    # Si por algún motivo se perdió la instancia de base de datos, la conectamos usando las credenciales locales
    if not st.session_state.supabase:
        try:
            st.session_state.supabase = create_client(
                st.secrets["SUPABASE_URL"], 
                st.secrets["SUPABASE_KEY"]
            )
            # Extraemos el nombre del club desde los secrets o por defecto
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
            tab_login, tab_registro, tab_recuperar = st.tabs(["🔑 Iniciar Sesión", "📝 Registro de Usuarios", "🔄 Recuperar Contraseña"])
            
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
                            
            # --- TAB REGISTRO ---
            with tab_registro:
                st.markdown("### 📝 Registro de Nuevas Cuentas")
                if st.session_state.reg_codigo_verificacion:
                    st.info(f"Se ha enviado un código de verificación al correo: **{st.session_state.reg_datos_temporales['email']}**")
                    with st.form("form_verificacion_registro"):
                        codigo_ingresado = st.text_input("Ingrese el código temporal de 6 dígitos:")
                        
                        if st.form_submit_button("Confirmar y Registrar Cuenta"):
                            if codigo_ingresado.strip() == str(st.session_state.reg_codigo_verificacion):
                                try:
                                    instancia_supabase_club.table("usuarios").insert(st.session_state.reg_datos_temporales).execute()
                                    status_inicial = st.session_state.reg_datos_temporales["estatus"]
                                    nuevo_nombre = st.session_state.reg_datos_temporales["nombre"]
                                    nuevo_rol = st.session_state.reg_datos_temporales["rol"]
                                    nuevo_email = st.session_state.reg_datos_temporales["email"]
                                    
                                    # ✨ SIN CORRUPCIÓN: Alineación corregida perfectamente
                                    if status_inicial == "Pendiente":
                                        enviar_email("Cuenta en Revisión", f"Hola {nuevo_nombre}, tu cuenta de {nuevo_rol} ha sido registrada. Está pendiente de revisión por el administrador.", nuevo_email)
                                        enviar_email("Nuevo Registro Pendiente", f"El usuario {nuevo_nombre} ({nuevo_rol}) se ha registrado. Email: {nuevo_email}. Favor revisar en consola admin.", st.secrets["EMAIL_ADMIN"])
                                        st.success(f"¡Registro exitoso como **{nuevo_rol}**! Tu cuenta debe ser aprobada por el administrador.")
                                    else:
                                        st.success(f"¡Registro exitoso como **{nuevo_rol}**! Ya puede iniciar sesión.")
                                    
                                    st.session_state.reg_codigo_verificacion = None
                                    st.session_state.reg_datos_temporales = None
                                    st.rerun()
                                except Exception as reg_err:
                                    st.error(f"Error en registro: {reg_err}")
                            else:
                                st.error("❌ El código ingresado es incorrecto. Inténtelo de nuevo.")
                            
                        if st.button("❌ Cancelar Registro"):
                            st.session_state.reg_codigo_verificacion = None
                            st.session_state.reg_datos_temporales = None
                            st.rerun()
                else:
                    nuevo_rol = st.selectbox("Seleccione el Rol para la nueva cuenta:", options=["Nadador", "Head Coach", "Entrenador", "Club", "Administrador"], key="reg_rol_selector")
                    es_nadador_reg = (nuevo_rol == "Nadador")
                    
                    with st.form("form_registro_dinamico"):
                        nuevo_nombre = st.text_input("Nombre completo:")
                        nuevo_usuario = st.text_input("Nombre de Usuario (Alias):", placeholder="ejemplo: alberto_jordan o maria_jimenez")
                        nuevo_email = st.text_input("Correo Electrónico:", placeholder="ejemplo: altair19@gmail.com")
                        
                        nueva_contrasena = st.text_input("Establecer Contraseña:", type="password")
                        confirmar_contrasena = st.text_input("Confirmar Contraseña:", type="password")
                        
                        nuevo_genero = None
                        nueva_fecha_nac = None
                        
                        if es_nadador_reg:
                            st.markdown("---")
                            st.markdown("##### 🧬 Datos Biométricos Requeridos (Categorías Feveda)")
                            nuevo_genero = st.selectbox("Género:", options=["F", "M"], format_func=lambda x: "Femenino" if x == "F" else "Masculino")
                            nueva_fecha_nac = st.date_input("Fecha de Nacimiento:", min_value=datetime.date(1950, 1, 1), max_value=datetime.date.today())
                        
                        if st.form_submit_button("🚀 Enviar Código de Verificación"):
                            if nuevo_nombre and nuevo_usuario and nueva_contrasena and confirmar_contrasena and nuevo_email:
                                if nueva_contrasena != confirmar_contrasena:
                                    st.error("❌ Las contraseñas no coinciden.")
                                else:
                                    nuevo_usuario_clean = nuevo_usuario.strip().lower()
                                    try:
                                        chequeo = instancia_supabase_club.table("usuarios").select("id").eq("usuario", nuevo_usuario_clean).execute()
                                        if chequeo.data:
                                            st.error("El nombre de usuario ya está tomado.")
                                        else:
                                            codigo_temp = random.randint(100000, 999999)
                                            status_inicial = "Pendiente" if nuevo_rol in ["Head Coach", "Entrenador", "Club", "Administrador"] else "Activo"
                                            
                                            st.session_state.reg_datos_temporales = {
                                                "nombre": nuevo_nombre, 
                                                "usuario": nuevo_usuario_clean, 
                                                "email": nuevo_email.strip(),
                                                "contrasena": hash_password(nueva_contrasena),
                                                "rol": nuevo_rol, 
                                                "estatus": status_inicial,
                                                "genero": nuevo_genero if es_nadador_reg else None,
                                                "fecha_nacimiento": nueva_fecha_nac.isoformat() if (es_nadador_reg and nueva_fecha_nac) else None
                                            }
                                            
                                            cuerpo_mail = f"Hola {nuevo_nombre},\n\nTu código temporal de verificación para registrarte en el sistema dentro del club {st.session_state.club_seleccionado} es: {codigo_temp}\n\nSi no solicitaste este registro, ignora este correo."
                                            if enviar_email("Código de Verificación de Registro", cuerpo_mail, nuevo_email.strip()):
                                                st.session_state.reg_codigo_verificacion = codigo_temp
                                                st.success("📩 Código enviado con éxito. Revise su bandeja de entrada.")
                                                st.rerun()
                                            else:
                                                st.error("No se pudo enviar el correo de verificación.")
                                    except Exception as reg_err:
                                        st.error(f"Error en validación: {reg_err}")
                            else:
                                st.error("Por favor complete todos los datos obligatorios del formulario.")

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
