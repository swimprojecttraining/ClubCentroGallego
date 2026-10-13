# =============================================================================
# login_general_app.py — v2.2 (Fase 1: refactorización incremental)
# =============================================================================
# Última actualización: 2026-10-12
#
# CHANGELOG:
#
#   v2.2 (2026-10-12) — Fix crítico de conexión al autenticar:
#     - Se restaura "supabase" en LLAVES_INFRAESTRUCTURA de
#       limpiar_sesion_al_autenticar() para no borrarla al autenticar.
#     - Se re-inicializa st.session_state["supabase"] = get_db() tras
#       la limpieza en login_usuario().
#     - Resultado: las pestañas que aún leen st.session_state["supabase"]
#       ya no fallan con "No se encontró conexión activa".
#
#   v2.1 (2026-10-12) — Compatibilidad inicial con pestañas:
#     - Se inicializa session_state["supabase"] como alias del singleton
#       get_db() en mostrar_pantalla_login().
#
#   v2.0 (2026-10-12) — Refactorización Fase 1:
#     17a — [F1-FIX-01] Fix: enviar_email con argumentos nombrados.
#     17b — Migración a get_db() singleton.
#     17c — Eliminado obtener_cliente_supabase() (código muerto).
#     17d — Invalidación quirúrgica tras updates.
#     17e — CLUB_DESDE_SECRETS movido dentro de función.
#     17g — Imports no usados eliminados.
#     17h — Feedback explícito en activación OTP y cambio de contraseña.
#     17i — key= únicos en widgets de formularios.
#
# NO TOCADO:
#   - Lógica de autenticación (hash, validación)
#   - Estructura de tabs (Login, OTP, Recuperación)
#   - CSS del login
#   - key= existentes
#
# PENDIENTE FASE 2:
#   [F2-44] Migrar todas las pestañas a get_db() directamente y eliminar
#           la dependencia de st.session_state["supabase"].
# =============================================================================
import base64
import datetime
import os
import random

# 📦 IMPORTACIÓN DESDE LA LIBRERÍA DE FUNCIONES
from formulas_lib_funciones import (
    calcular_categoria_competencia,
    enviar_email,
    hash_password,
)
import streamlit as st

# 🚀 IMPORTACIÓN DEL SINGLETON DE CONEXIÓN
from conections_supabase_cache import (
    get_db,
    invalidar_cache_usuarios,
    invalidar_cache_invitaciones,
)


# =============================================================================
# HELPERS DE UI
# =============================================================================
def aplicar_fondo_pantalla_institucional(
    nombre_archivo_imagen="Fondo_de_pantalla_Swimprojecttraining.png",
):
    """Lee una imagen desde la raíz del proyecto, la convierte a Base64
    e inyecta CSS seguro en stApp con velo agua fresco y centrado.
    """
    if os.path.exists(nombre_archivo_imagen):
        with open(nombre_archivo_imagen, "rb") as f:
            data_imagen = f.read()
        encoded_imagen = base64.b64encode(data_imagen).decode()

        ext = nombre_archivo_imagen.split(".")[-1].lower()
        mime_type = "png" if ext == "png" else "jpeg"

        css_fondo = f"""
        <style>
        .stApp {{
            background-image: linear-gradient(135deg, rgba(186, 230, 253, 0.70), rgba(207, 250, 254, 0.82)), url("data:image/{mime_type};base64,{encoded_imagen}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        
        .block-container {{
            padding-top: 3.5rem !important;
            max-width: 1100px !important;
        }}

        [data-testid="stForm"] {{
            background-color: rgba(255, 255, 255, 0.96) !important;
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0px 10px 30px rgba(6, 182, 212, 0.25);
            border: 1.5px solid rgba(103, 232, 249, 0.8);
        }}

        button {{
            pointer-events: auto !important;
            z-index: 99999 !important;
        }}
        </style>
        """
        st.markdown(css_fondo, unsafe_allow_html=True)


def _nombre_club_local() -> str:
    """Devuelve el nombre del club desde secrets (con fallback)."""
    try:
        return st.secrets.get("NOMBRE_CLUB_LOCAL", "Swimming Club")
    except Exception:
        return "Swimming Club"


# =============================================================================
# PURGA DE SEGURIDAD
# =============================================================================
def limpiar_sesion_al_autenticar():
    """
    [F1-17f] Limpia todas las claves de sesión excepto las de infraestructura.

    v2.2: se restaura "supabase" en las claves preservadas para mantener
    compatibilidad con las pestañas que aún leen st.session_state["supabase"].
    En Fase 2 [F2-44] se migrarán todas las pestañas a get_db() y se podrá
    eliminar esta excepción.
    """
    LLAVES_INFRAESTRUCTURA = {
        "puente_validado",
        "club_seleccionado",
        "supabase",
    }

    for key in list(st.session_state.keys()):
        if key not in LLAVES_INFRAESTRUCTURA:
            del st.session_state[key]


# =============================================================================
# AUTENTICACIÓN
# =============================================================================
def login_usuario(user, password):
    """
    [F1-17b] Verifica credenciales usando el singleton get_db().
    """
    try:
        user_lower = user.strip().lower()
        hashed_pw = hash_password(password)
        db = get_db()

        response = (
            db.table("usuarios")
            .select("id, nombre, genero, rol, estatus, fecha_nacimiento")
            .eq("usuario", user_lower)
            .eq("contrasena", hashed_pw)
            .execute()
        )

        if response.data:
            user_data = response.data[0]

            if user_data.get("estatus") == "Inactivo":
                st.session_state["login_mensaje_error"] = (
                    "⚠️ Aún no puedes ingresar. Debes contactar con la "
                    "administración."
                )
                return False

            limpiar_sesion_al_autenticar()

            # [F1-17b] v2.2: Re-inicializar el alias de conexión tras la
            # limpieza para compatibilidad con pestañas no migradas.
            st.session_state["supabase"] = get_db()

            st.session_state.autenticado = True
            st.session_state.usuario_id = user_data["id"]
            st.session_state.usuario_logueado_id = user_data["id"]
            st.session_state.nombre_usuario = user_data["nombre"]
            st.session_state.nombre_nadador = user_data["nombre"]
            st.session_state.genero = user_data.get("genero", "M")

            rol_db = str(user_data.get("rol", "Nadador")).strip()
            st.session_state.rol = rol_db
            st.session_state.rol_real = rol_db
            st.session_state.rol_emulado = None

            st.session_state.fecha_nacimiento = user_data.get("fecha_nacimiento")

            if st.session_state.rol == "Nadador":
                if st.session_state.fecha_nacimiento:
                    cat, ed_c = calcular_categoria_competencia(
                        st.session_state.fecha_nacimiento
                    )
                else:
                    cat, ed_c = "Sin Categoría", 0

                st.session_state.categoria_atleta = cat
                st.session_state.edad_comp_atleta = ed_c
                st.session_state.nadador_seleccionado_id = user_data["id"]
                st.session_state.nadador_seleccionado_nombre = user_data["nombre"]
                st.session_state.nadador_seleccionado_genero = user_data.get(
                    "genero", "F"
                )
                st.session_state.nadador_seleccionado_categoria = cat
                st.session_state.nadador_seleccionado_fecha_nacimiento = (
                    user_data.get("fecha_nacimiento")
                )
            else:
                st.session_state.categoria_atleta = None
                st.session_state.edad_comp_atleta = None
                st.session_state.nadador_seleccionado_id = None
                st.session_state.nadador_seleccionado_nombre = None
                st.session_state.nadador_seleccionado_genero = None
                st.session_state.nadador_seleccionado_categoria = None
                st.session_state.nadador_seleccionado_fecha_nacimiento = None

            st.session_state["login_mensaje_error"] = None
            return True

        st.session_state["login_mensaje_error"] = (
            "Credenciales incorrectas o cuenta en revisión. Verifique sus datos."
        )
        return False
    except Exception as e:
        st.session_state["login_mensaje_error"] = f"Error en Login: {e}"
        return False


# =============================================================================
# CALLBACK PRE-RENDERIZADO
# =============================================================================
def callback_procesar_login():
    """
    Ejecuta la validación ANTES del UI, usando get_db().
    """
    usuario = st.session_state.get("login_input_usuario", "").strip()
    contrasena = st.session_state.get("login_input_contrasena", "")

    if not usuario or not contrasena:
        st.session_state["login_mensaje_error"] = (
            "Por favor ingrese usuario y contraseña."
        )
        return

    login_usuario(usuario, contrasena)


# =============================================================================
# PANTALLA PRINCIPAL
# =============================================================================
def mostrar_pantalla_login():
    """
    Función principal que renderiza el Login, Certificación por Pre-Alta
    (OTP) y Recuperación.
    """
    # 🛡️ 1. GUARD DE SALIDA TEMPRANA
    if st.session_state.get("autenticado", False):
        return

    aplicar_fondo_pantalla_institucional(
        "Fondo_de_pantalla_Swimprojecttraining.png"
    )

    if "rec_codigo_verificacion" not in st.session_state:
        st.session_state.rec_codigo_verificacion = None
    if "rec_datos_temporales" not in st.session_state:
        st.session_state.rec_datos_temporales = None

    # [F1-17b] Verificación de conexión e inicialización del alias
    try:
        db_check = get_db()
        if not db_check:
            st.error(
                "❌ Error de infraestructura: no se pudo conectar con la "
                "base de datos."
            )
            st.stop()
        # Alias del singleton en session_state para compatibilidad con
        # pestañas no migradas.
        if (
            "supabase" not in st.session_state
            or not st.session_state["supabase"]
        ):
            st.session_state["supabase"] = db_check
    except Exception as e:
        st.error(
            f"❌ Error de infraestructura al conectar base de datos: {e}"
        )
        st.stop()

    # ------------------------------------------------------------
    # 2. INTERFAZ CENTRADA Y BALANCEADA
    # ------------------------------------------------------------
    nombre_club = _nombre_club_local()

    st.markdown(
        f"<h2 style='text-align: center; color: #0F172A; margin-bottom: 2px;'>"
        f"🏊‍♂️ {nombre_club}</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h4 style='text-align: center; color: #475569; margin-bottom: 25px;'>"
        "Sistema de Control de Entrenamientos y Rendimiento</h4>",
        unsafe_allow_html=True,
    )

    col_izq, col_centro, col_der = st.columns([1, 2.2, 1])

    with col_centro:
        tab_login, tab_registro_otp, tab_recuperar = st.tabs([
            "🔑 Iniciar Sesión",
            "📝 Registro (Pre-Alta OTP)",
            "🔄 Recuperar Contraseña",
        ])

        # --- TAB LOGIN ---
        with tab_login:
            st.caption(
                "Nota: Los nombres de usuario se procesan en minúsculas."
            )

            if st.session_state.get("login_mensaje_error"):
                st.error(st.session_state["login_mensaje_error"])

            with st.form("form_login"):
                st.text_input(
                    "Usuario:", key="login_input_usuario"
                )
                st.text_input(
                    "Contraseña:",
                    type="password",
                    key="login_input_contrasena",
                )

                st.form_submit_button(
                    "Ingresar",
                    use_container_width=True,
                    on_click=callback_procesar_login,
                )

        # --- TAB REGISTRO PRE-ALTA OTP ---
        with tab_registro_otp:
            st.markdown("### 📝 Registro de Usuarios (Pre-Alta)")
            st.caption(
                "Introduce el código OTP enviado por el club para verificar "
                "tus datos institucionales y activar tu cuenta."
            )

            with st.form("form_activar_prealta"):
                otp_token_input = st.text_input(
                    "Código OTP (6 dígitos):",
                    max_chars=6,
                    placeholder="Ej: 489123",
                    key="otp_input_token",
                )
                email_prealta_input = st.text_input(
                    "Correo electrónico registrado en la pre-alta:",
                    key="otp_input_email",
                )

                st.markdown("---")
                st.markdown("##### 🔐 Credenciales y Acceso Definitivo")
                nuevo_alias_pa = st.text_input(
                    "Nombre de Usuario (Alias) deseado:",
                    placeholder="ej: alberto_jordan",
                    key="otp_input_alias",
                )
                nueva_clave_pa = st.text_input(
                    "Establecer Contraseña:",
                    type="password",
                    key="otp_input_clave",
                )
                confirmar_clave_pa = st.text_input(
                    "Confirmar Contraseña:",
                    type="password",
                    key="otp_input_clave2",
                )

                if st.form_submit_button(
                    "🚀 Certificar y Activar Cuenta", use_container_width=True
                ):
                    if (
                        not otp_token_input
                        or not email_prealta_input
                        or not nuevo_alias_pa
                        or not nueva_clave_pa
                    ):
                        st.error("⚠️ Todos los campos son obligatorios.")
                    elif nueva_clave_pa != confirmar_clave_pa:
                        st.error("❌ Las contraseñas no coinciden.")
                    else:
                        try:
                            email_clean = email_prealta_input.strip().lower()
                            alias_clean = nuevo_alias_pa.strip().lower()
                            db = get_db()

                            res_inv = (
                                db.table("invitaciones")
                                .select("*")
                                .eq("token", otp_token_input.strip())
                                .eq("email", email_clean)
                                .eq("usado", False)
                                .execute()
                            )

                            if not res_inv.data:
                                st.error(
                                    "❌ Código OTP inválido, expirado o el "
                                    "correo no coincide."
                                )
                            else:
                                invitacion = res_inv.data[0]
                                expira_en = datetime.datetime.fromisoformat(
                                    invitacion["expira_en"].replace(
                                        "Z", "+00:00"
                                    )
                                )

                                if (
                                    datetime.datetime.now(
                                        datetime.timezone.utc
                                    )
                                    > expira_en
                                ):
                                    st.error(
                                        "⌛ El código OTP ha expirado "
                                        "(vigencia de 24 horas). Solicite "
                                        "uno nuevo a la administración."
                                    )
                                else:
                                    res_alias = (
                                        db.table("usuarios")
                                        .select("id")
                                        .eq("usuario", alias_clean)
                                        .execute()
                                    )
                                    if res_alias.data:
                                        st.error(
                                            f"❌ El alias de usuario "
                                            f"**{alias_clean}** ya está "
                                            f"registrado. Por favor elija otro."
                                        )
                                    else:
                                        payload_actualizacion = {
                                            "usuario": alias_clean,
                                            "contrasena": hash_password(
                                                nueva_clave_pa
                                            ),
                                            "estatus": "Activo",
                                        }

                                        db.table("usuarios").update(
                                            payload_actualizacion
                                        ).eq("email", email_clean).execute()

                                        db.table("invitaciones").update(
                                            {"usado": True}
                                        ).eq("id", invitacion["id"]).execute()

                                        invalidar_cache_usuarios()
                                        invalidar_cache_invitaciones()

                                        st.success(
                                            f"🎉 ¡Activación completada "
                                            f"exitosamente para "
                                            f"**{invitacion.get('nombre')}**!"
                                            f"\n\nYa puedes iniciar sesión "
                                            f"con tu usuario **{alias_clean}**."
                                        )
                        except Exception as pa_err:
                            st.error(
                                f"❌ Error al procesar la activación: "
                                f"{pa_err}"
                            )

        # --- TAB RECUPERAR ---
        with tab_recuperar:
            st.markdown("### Restablecer Contraseña")

            if st.session_state.rec_codigo_verificacion:
                st.info(
                    "Se ha enviado un código de seguridad a la dirección "
                    "vinculada."
                )
                with st.form("form_verificacion_recuperacion"):
                    codigo_rec_ingresado = st.text_input(
                        "Ingrese el código temporal de recuperación:",
                        key="rec_input_codigo",
                    )

                    if st.form_submit_button(
                        "Validar Código y Cambiar Contraseña",
                        use_container_width=True,
                    ):
                        if str(codigo_rec_ingresado).strip() == str(
                            st.session_state.rec_codigo_verificacion
                        ):
                            try:
                                datos = st.session_state.rec_datos_temporales
                                db = get_db()
                                db.table("usuarios").update(
                                    {"contrasena": datos["nueva_contrasena"]}
                                ).eq("id", datos["user_id"]).execute()

                                invalidar_cache_usuarios()

                                st.success(
                                    "✅ Contraseña actualizada correctamente. "
                                    "Ya puede iniciar sesión con su nueva "
                                    "contraseña."
                                )
                                st.session_state.rec_codigo_verificacion = None
                                st.session_state.rec_datos_temporales = None
                            except Exception as rec_err:
                                st.error(
                                    f"❌ Error al actualizar la contraseña: "
                                    f"{rec_err}"
                                )
                        else:
                            st.error("❌ El código ingresado es incorrecto.")

                if st.button(
                    "❌ Cancelar Recuperación", use_container_width=True
                ):
                    st.session_state.rec_codigo_verificacion = None
                    st.session_state.rec_datos_temporales = None
                    st.rerun()
            else:
                with st.form("form_recuperacion"):
                    rec_usuario = st.text_input(
                        "Nombre de Usuario (Alias):",
                        key="rec_input_usuario",
                    )
                    rec_email = st.text_input(
                        "Correo Electrónico Asociado:",
                        key="rec_input_email",
                    )
                    nueva_clave = st.text_input(
                        "Nueva Contraseña Deseada:",
                        type="password",
                        key="rec_input_clave",
                    )
                    confirmar_clave = st.text_input(
                        "Confirmar Nueva Contraseña:",
                        type="password",
                        key="rec_input_clave2",
                    )

                    if st.form_submit_button(
                        "🔄 Solicitar Código de Recuperación",
                        use_container_width=True,
                    ):
                        if not (
                            rec_usuario
                            and rec_email
                            and nueva_clave
                            and confirmar_clave
                        ):
                            st.error(
                                "Todos los campos del formulario de "
                                "recuperación son obligatorios."
                            )
                        elif nueva_clave != confirmar_clave:
                            st.error(
                                "La confirmación no coincide con la nueva "
                                "contraseña introducida."
                            )
                        else:
                            rec_usuario_clean = rec_usuario.strip().lower()
                            try:
                                db = get_db()
                                verificacion = (
                                    db.table("usuarios")
                                    .select("id, estatus, nombre")
                                    .eq("usuario", rec_usuario_clean)
                                    .eq("email", rec_email.strip())
                                    .execute()
                                )
                                if verificacion.data:
                                    user_info = verificacion.data[0]
                                    if user_info.get("estatus") in [
                                        "Suspendido", "Bloqueado",
                                    ]:
                                        st.error(
                                            "Esta cuenta se encuentra "
                                            "suspendida o bloqueada por la "
                                            "administración."
                                        )
                                    else:
                                        codigo_rec_temp = random.randint(
                                            100000, 999999
                                        )
                                        st.session_state.rec_datos_temporales = {
                                            "user_id": user_info["id"],
                                            "nueva_contrasena": hash_password(
                                                nueva_clave
                                            ),
                                        }

                                        cuerpo_rec_mail = (
                                            f"Hola {user_info['nombre']},\n\n"
                                            f"Has solicitado un "
                                            f"restablecimiento de contraseña. "
                                            f"Tu código de seguridad temporal "
                                            f"es: {codigo_rec_temp}\n\n"
                                            f"Si no realizaste esta acción, "
                                            f"contacta de inmediato al "
                                            f"administrador."
                                        )

                                        # [F1-17a] FIX [F1-FIX-01]:
                                        # Argumentos nombrados correctos.
                                        if enviar_email(
                                            destinatario=rec_email.strip(),
                                            asunto=(
                                                "Código de Seguridad - "
                                                "Recuperación de Contraseña"
                                            ),
                                            cuerpo_html=cuerpo_rec_mail,
                                        ):
                                            st.session_state.rec_codigo_verificacion = (
                                                codigo_rec_temp
                                            )
                                            st.success(
                                                "📩 Código de seguridad "
                                                "enviado al correo electrónico."
                                            )
                                            st.rerun()
                                        else:
                                            st.error(
                                                "❌ Error al enviar el correo "
                                                "de recuperación. Verifique "
                                                "con el administrador."
                                            )
                                else:
                                    st.error(
                                        "❌ Los datos proporcionados no "
                                        "coinciden con ningún registro activo."
                                    )
                            except Exception as rec_err:
                                st.error(
                                    f"❌ Error durante el proceso de "
                                    f"restablecimiento: {rec_err}"
                                )

    st.stop()