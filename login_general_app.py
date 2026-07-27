import base64
import datetime
import hashlib
import hmac
import random
import time
from supabase import Client, create_client
import streamlit as st

from formulas_lib_funciones import (
    calcular_categoria_competencia,
    desencriptar_credencial,
    enviar_email,
    hash_password,
)


@st.cache_resource
def obtener_cliente_supabase():
  return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def login_usuario(usuario_o_correo, contrasena, supabase_client):
  try:
    term_busqueda = usuario_o_correo.strip().lower()
    clave_ingresada = contrasena.strip()
    clave_hashed = hash_password(clave_ingresada)

    # 1. Buscar en la columna 'usuario'
    respuesta = (
        supabase_client.table("usuarios")
        .select("*")
        .eq("usuario", term_busqueda)
        .execute()
    )

    # 2. Si no coincide, buscar en la columna 'email'
    if not respuesta.data:
      respuesta = (
          supabase_client.table("usuarios")
          .select("*")
          .eq("email", term_busqueda)
          .execute()
      )

    if not respuesta.data:
      return False

    datos_usuario = respuesta.data[0]
    clave_db = str(datos_usuario.get("contrasena", "")).strip()

    # Comprueba contra hash SHA-256 o texto plano si hubiera usuarios antiguos
    if clave_db == clave_hashed or clave_db == clave_ingresada:
      st.session_state["usuario_actual"] = datos_usuario.get("usuario")
      st.session_state["rol_usuario"] = datos_usuario.get("rol", "entrenador")
      st.session_state["nombre_usuario"] = datos_usuario.get(
          "nombre", datos_usuario.get("usuario")
      )
      st.session_state["correo_usuario"] = datos_usuario.get("email", "")
      st.session_state["autenticado"] = True
      return True

    return False
  except Exception as e:
    st.error(f"Error en la autenticación: {e}")
    return False


def mostrar_pantalla_login():
  # Reset voluntario de sesión de usuario sin borrar banderas globales
  if st.session_state.get("logout_solicitado", False):
    st.session_state.autenticado = False
    st.session_state.pop("usuario_actual", None)
    st.session_state.pop("logout_solicitado", None)

  if "rec_codigo_verificacion" not in st.session_state:
    st.session_state.rec_codigo_verificacion = None
  if "rec_datos_temporales" not in st.session_state:
    st.session_state.rec_datos_temporales = None
  if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

  if not st.session_state.get("supabase"):
    try:
      st.session_state.supabase = obtener_cliente_supabase()
      st.session_state.club_seleccionado = st.secrets.get(
          "NOMBRE_CLUB_LOCAL", "Centro Gallego"
      )
    except Exception as e:
      st.error(f"❌ Error de conexión a la base de datos: {e}")
      st.stop()

  if not st.session_state.autenticado:
    st.markdown(
        f"<h2 style='text-align: center;'>🏊‍♂️"
        f" {st.session_state.club_seleccionado}</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h4 style='text-align: center; color: gray;'>Sistema de Gestión de"
        " Entrenamientos y Proyección de Rendimiento</h4>",
        unsafe_allow_html=True,
    )

    instancia_supabase_club = st.session_state.supabase
    c_login, _ = st.columns([1.5, 1.5])

    with c_login:
      tab_login, tab_registro_otp, tab_recuperar = st.tabs([
          "🔑 Iniciar Sesión",
          "📝 Registro (Pre-Alta OTP)",
          "🔄 Recuperar Contraseña",
      ])

      # --- TAB 1: LOGIN ---
      with tab_login:
        st.caption("Nota: Los nombres de usuario se procesan en minúsculas.")
        with st.form("form_login"):
          usuario_input = st.text_input("Usuario o Correo:")
          contrasena_input = st.text_input("Contraseña:", type="password")

          if st.form_submit_button("Ingresar", use_container_width=True):
            if login_usuario(
                usuario_input, contrasena_input, instancia_supabase_club
            ):
              st.success("Acceso autorizado.")
              st.rerun()
            else:
              st.error(
                  "Credenciales incorrectas o usuario no registrado. Verifique"
                  " sus datos."
              )

      # --- TAB 2: REGISTRO PRE-ALTA ---
      with tab_registro_otp:
        st.markdown("### 📝 Registro de Usuarios (Pre-Alta)")
        st.caption("Introduce el código OTP enviado por el club.")

        with st.form("form_activar_prealta"):
          otp_token_input = st.text_input(
              "Código OTP (6 dígitos):", max_chars=6, placeholder="Ej: 489123"
          )
          email_prealta_input = st.text_input(
              "Correo electrónico registrado en la pre-alta:"
          )
          st.markdown("---")
          st.markdown("##### 🔐 Credenciales y Acceso Definitivo")
          nuevo_alias_pa = st.text_input(
              "Nombre de Usuario (Alias) deseado:", placeholder="ej: alberto_jordan"
          )
          nueva_clave_pa = st.text_input(
              "Establecer Contraseña:", type="password"
          )
          confirmar_clave_pa = st.text_input(
              "Confirmar Contraseña:", type="password"
          )

          if st.form_submit_button(
              "🚀 Certificar y Crear Cuenta", use_container_width=True
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
                res_inv = (
                    instancia_supabase_club.table("invitaciones")
                    .select("*")
                    .eq("token", otp_token_input.strip())
                    .eq("email", email_prealta_input.strip().lower())
                    .eq("usado", False)
                    .execute()
                )

                if not res_inv.data:
                  st.error("❌ Código OTP inválido o correo no coincide.")
                else:
                  invitacion = res_inv.data[0]
                  expira_en = datetime.datetime.fromisoformat(
                      invitacion["expira_en"]
                  )

                  if datetime.datetime.now(
                      datetime.timezone.utc
                  ) > expira_en.replace(tzinfo=datetime.timezone.utc):
                    st.error("⌛ El código OTP ha expirado.")
                  else:
                    datos_perfil = invitacion.get("datos_perfil", {})
                    nombre_val = invitacion.get("nombre")
                    email_val = invitacion.get("email")
                    rol_val = invitacion.get("rol")

                    raw_genero = datos_perfil.get("genero") or datos_perfil.get(
                        "sexo"
                    )
                    genero_val = (
                        "F"
                        if raw_genero in ["F", "Femenino"]
                        else (
                            "M"
                            if raw_genero in ["M", "Masculino"]
                            else None
                        )
                    )
                    fecha_nac_val = datos_perfil.get("fecha_nacimiento")

                    usuario_oficial = {
                        "nombre": nombre_val,
                        "usuario": nuevo_alias_pa.strip().lower(),
                        "email": email_val.strip().lower(),
                        "contrasena": hash_password(nueva_clave_pa),
                        "rol": rol_val,
                        "estatus": "Activo",
                        "cedula": datos_perfil.get("cedula", ""),
                        "telefono": datos_perfil.get("telefono", ""),
                        "genero": genero_val,
                        "fecha_nacimiento": fecha_nac_val,
                    }

                    instancia_supabase_club.table("usuarios").insert(
                        usuario_oficial
                    ).execute()
                    instancia_supabase_club.table("invitaciones").update(
                        {"usado": True}
                    ).eq("id", invitacion["id"]).execute()
                    st.success(
                        f"🎉 ¡Registro completado para **{nombre_val}**! Ya"
                        " puedes iniciar sesión."
                    )
              except Exception as pa_err:
                st.error(f"Error al procesar el registro: {pa_err}")

      # --- TAB 3: RECUPERAR CONTRASEÑA ---
      with tab_recuperar:
        st.markdown("### Restablecer Contraseña")
        if st.session_state.rec_codigo_verificacion:
          st.info(
              "Se ha enviado un código de seguridad a la dirección vinculada."
          )
          with st.form("form_verificacion_recuperacion"):
            codigo_rec_ingresado = st.text_input(
                "Ingrese el código temporal de recuperación:"
            )

            if st.form_submit_button("Validar Código y Cambiar Contraseña"):
              if str(codigo_rec_ingresado).strip() == str(
                  st.session_state.rec_codigo_verificacion
              ):
                try:
                  datos = st.session_state.rec_datos_temporales
                  instancia_supabase_club.table("usuarios").update(
                      {"contrasena": datos["nueva_contrasena"]}
                  ).eq("id", datos["user_id"]).execute()
                  st.success(
                      "✅ Contraseña actualizada correctamente. Ya puede"
                      " iniciar sesión."
                  )
                  st.session_state.rec_codigo_verificacion = None
                  st.session_state.rec_datos_temporales = None
                except Exception as rec_err:
                  st.error(f"Error al actualizar contraseña: {rec_err}")
              else:
                st.error("❌ Código incorrecto.")

          if st.button("❌ Cancelar Recuperación"):
            st.session_state.rec_codigo_verificacion = None
            st.session_state.rec_datos_temporales = None
            st.rerun()
        else:
          with st.form("form_recuperacion"):
            rec_usuario = st.text_input("Nombre de Usuario (Alias):")
            rec_email = st.text_input("Correo Electrónico Asociado:")
            nueva_clave = st.text_input(
                "Nueva Contraseña Deseada:", type="password"
            )
            confirmar_clave = st.text_input(
                "Confirmar Nueva Contraseña:", type="password"
            )

            if st.form_submit_button("🔄 Solicitar Código de Recuperación"):
              if not (
                  rec_usuario and rec_email and nueva_clave and confirmar_clave
              ):
                st.error("Todos los campos son obligatorios.")
              elif nueva_clave != confirmar_clave:
                st.error("Las contraseñas no coinciden.")
              else:
                rec_usuario_clean = rec_usuario.strip().lower()
                try:
                  verificacion = (
                      instancia_supabase_club.table("usuarios")
                      .select("id, estatus, nombre")
                      .eq("usuario", rec_usuario_clean)
                      .eq("email", rec_email.strip())
                      .execute()
                  )
                  if verificacion.data:
                    user_info = verificacion.data[0]
                    codigo_rec_temp = random.randint(100000, 999999)
                    st.session_state.rec_datos_temporales = {
                        "user_id": user_info["id"],
                        "nueva_contrasena": hash_password(nueva_clave),
                    }
                    cuerpo_rec_mail = (
                        f"Hola {user_info['nombre']},\n\nTu código de seguridad"
                        f" es: {codigo_rec_temp}"
                    )
                    if enviar_email(
                        rec_email.strip(),
                        "Código de Seguridad - Recuperación de Contraseña",
                        cuerpo_rec_mail,
                    ):
                      st.session_state.rec_codigo_verificacion = (
                          codigo_rec_temp
                      )
                      st.success("📩 Código enviado al correo.")
                      st.rerun()
                    else:
                      st.error("Error al enviar el correo.")
                  else:
                    st.error("❌ Datos no encontrados.")
                except Exception as rec_err:
                  st.error(f"Error en recuperación: {rec_err}")

  st.stop()
