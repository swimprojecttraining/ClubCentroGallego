# =============================================================================
# root_app.py — v2.0 (Fase 1: refactorización incremental)
# =============================================================================
# CAMBIOS vs v1.0:
#   6b.1 — CSS global movido a views_styles.aplicar_estilos_root().
#   6b.2 — CSS del candado movido a views_styles.aplicar_estilos_candado().
#   6b.3 — try/except al leer st.secrets: error claro si falta una clave.
#   6b.4 — Footer solo se muestra si el usuario está autenticado.
#
# NO TOCADO:
#   - validar_token_handshake() — intacta
#   - Lógica multi-tenant y handshake HMAC — intacta
#   - st.stop() y estructura de control — intactos
#   - Nombres de secrets y URL_HUB_CENTRAL — intactos
# =============================================================================
import streamlit as st
import time
import hmac
import hashlib
import base64
import os
import sys

# **********************************************************************************
# 1. CONFIGURACIÓN ÚNICA DE LA PÁGINA
# **********************************************************************************
st.set_page_config(
    page_title="Swimming Club Training Control and Performance Forecasting System",
    layout="wide"
)

# --- INYECCIÓN DE CSS GLOBAL (movido a views_styles en v2.0) ---
from views_styles import aplicar_estilos_root
aplicar_estilos_root()


def validar_token_handshake(token_b64, secret_key_local):
    """
    Decodifica el token recibido por URL, verifica que corresponda al club,
    comprueba la firma criptográfica HMAC y valida la ventana de 30 segundos.
    """
    try:
        # 1. Decodificar Base64 de forma limpia
        token_decript = base64.b64decode(token_b64.encode()).decode()
        nombre_club, timestamp_str, firma_recibida = token_decript.split("|")
        
        # 2. Comprobar expiración estricta (Máximo 30 segundos)
        tiempo_transcurrido = time.time() - int(timestamp_str)
        if tiempo_transcurrido > 30 or tiempo_transcurrido < -5:
            return False, f"El ticket digital de acceso ha expirado. (Transcurrido: {int(tiempo_transcurrido)}s) Debe ingresar por la aplicación principal y escoger de la lista el Club al que esta adscrito"
            
        # 3. Re-calcular firma con la clave local exacta
        # Forzamos un strip() para eliminar espacios invisibles que puedan venir de la BD o los Secrets
        mensaje_esperado = f"{nombre_club}|{timestamp_str}"
        firma_esperada = hmac.new(
            secret_key_local.strip().encode(), 
            mensaje_esperado.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        if hmac.compare_digest(firma_esperada, firma_recibida):
            return True, nombre_club
            
        # 💡 DEBUG AUXILIAR: Si falla, dejamos una pista en el log interno
        return False, "Firma digital del Hub inválida (No coincide el secreto interclubes)."
    except Exception as e:
        return False, f"Formato de token corrupto: {str(e)}"


# =============================================================================
# 🛑 CANDADO DE SEGURIDAD INTERCLUBES (MULTI-TENANT PURO)
# =============================================================================

# [F1-6b.3] Robustez: mensaje claro si falta un secret, en lugar de KeyError.
try:
    SECRET_EXCLUSIVO_LOCAL = st.secrets["CLUB_SECRET_KEY"]
    URL_HUB_CENTRAL = st.secrets["URL_HUB_CENTRAL"]
except KeyError as e:
    st.error(
        f"❌ Error de configuración: falta el secret `{e.args[0]}` en "
        f"`.streamlit/secrets.toml`. Contacte al administrador del sistema."
    )
    st.stop()

if "puente_validado" not in st.session_state:
  st.session_state["puente_validado"] = False

params = st.query_params
token_url = params.get("auth")

if not st.session_state["puente_validado"]:

  # CSS para alertas del candado (movido a views_styles en v2.0)
  from views_styles import aplicar_estilos_candado
  aplicar_estilos_candado()

  # 1. Acceso directo sin token
  if not token_url:
    st.error(
        "🔒 **Acceso Denegado:** Debe iniciar sesión a través del Hub Central."
    )
    st.link_button(
        "🔄 Ir al Hub Central", URL_HUB_CENTRAL, use_container_width=True
    )
    st.stop()

  # 2. Validación criptográfica de apretón de manos
  es_valido, resultado_o_error = validar_token_handshake(
      token_url, SECRET_EXCLUSIVO_LOCAL
  )

  if not es_valido:
    # Renderizado garantizado y visible en el centro de la pantalla
    st.error(f"🔒 **Acceso Denegado:** {resultado_o_error}")
    st.info(
        "💡 Los enlaces de acceso rápido vencen a los 30 segundos por razones"
        " de seguridad."
    )
    st.link_button(
        "🔄 Volver al Hub Central para Generar Nuevo Enlace",
        URL_HUB_CENTRAL,
        use_container_width=True,
    )
    st.stop()

  # 3. Acceso autorizado
  st.session_state["puente_validado"] = True

# =============================================================================
# 🔑 ENTORNO OPERATIVO DEL CLUB (EJECUCIÓN DIRECTA POST-HANDSHAKE)
# =============================================================================

if st.session_state["puente_validado"]:
    # Inyección de estilos globales
    from views_styles import aplicar_estilos_globales
    aplicar_estilos_globales()

    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    # Renderizado directo sin recargas de servidor web
    if not st.session_state["autenticado"]:
        from login_general_app import mostrar_pantalla_login
        mostrar_pantalla_login()
    else:
        from views_tab_router import mostrar_vista_enrutador
        mostrar_vista_enrutador()

# ===================================================
# 🏁 CIERRE VISUAL GLOBAL AL PIE DE TODA LA APP
# ===================================================
# [F1-6b.4] El footer solo se muestra si el usuario ya está autenticado.
# Antes aparecía también debajo del login, lo cual era confuso.
if st.session_state.get("autenticado", False):
    st.markdown(
        """
        <div style='text-align: center; margin-top: 40px; margin-bottom: 10px; color: #94a3b8; font-size: 12px; font-weight: bold; letter-spacing: 1px;'>
            --- FIN DE LA VISTA ---
        </div>
        """,
        unsafe_allow_html=True,
    )