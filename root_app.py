import streamlit as st
import time
import hmac
import hashlib
import base64
import os
import sys
import streamlit.components.v1 as components

# **********************************************************************************
# 1. CONFIGURACIÓN ÚNICA DE LA PÁGINA
# **********************************************************************************
st.set_page_config(
    page_title="Swimming Club Training Control and Performance Forecasting System", 
    layout="wide"
)
import base64
import os
import streamlit as st


# --- 1. FUNCIÓN DE FONDO CORREGIDA (RUTA ABSOLUTA) ---
def aplicar_fondo_pantalla():
  # Resolvemos la ruta exacta dentro del repositorio en Streamlit Cloud
  directorio_actual = os.path.dirname(os.path.abspath(__file__))
  ruta_fondo = os.path.join(
      directorio_actual, "Fondo_de_pantalla_Swimprojecttraining.png"
  )

  if os.path.exists(ruta_fondo):
    with open(ruta_fondo, "rb") as image_file:
      encoded_string = base64.b64encode(image_file.read()).decode()

    st.markdown(
        f"""
            <style>
            /* Fondo global de la app */
            .stApp {{
                background-image: url("data:image/png;base64,{encoded_string}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            
            /* Contenedor principal con transparencia elegante para asegurar lecturabilidad */
            div[data-testid="stMainBlockContainer"] {{
                background-color: rgba(255, 255, 255, 0.90) !important;
                border-radius: 12px;
                padding: 2.5rem !important;
                margin-top: 1.5rem;
                box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.08);
            }}
            </style>
            """,
        unsafe_allow_html=True,
    )


# Invocamos el fondo al inicio
aplicar_fondo_pantalla()


# --- 2. CANDADO DE SEGURIDAD CORREGIDO ---
SECRET_EXCLUSIVO_LOCAL = st.secrets.get(
    "CLUB_SECRET_KEY", "ClubdeNatacionCentroGallegoqazws"
)

if "puente_validado" not in st.session_state:
  st.session_state["puente_validado"] = False

params = st.query_params
token_url = params.get("auth")

# Si el puente aún no ha sido marcado como validado en la sesión
if not st.session_state["puente_validado"]:

  # A. Si no hay token en la URL ni en la sesión
  if token_url is None or token_url == "":
    st.query_params.clear()

    st.markdown(
        """
            <div style="
                background-color: #ffebe9;
                border: 1px solid #ffc1c0;
                color: #cf222e;
                padding: 24px;
                border-radius: 12px;
                font-weight: 500;
                font-size: 15px;
                margin: 30px auto 15px auto;
                max-width: 550px;
                text-align: center;
                box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
            ">
                <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">
                    🔒 Acceso Denegado
                </div>
                <div>
                    No está autorizado a entrar directamente a este nodo. Debe iniciar sesión a través del Hub Central.
                </div>
            </div>
            """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
      st.link_button(
          "🏠 Volver al Hub Central",
          "https://swimming-pro.streamlit.app",
          use_container_width=True,
      )

    st.stop()

  # B. Si hay token, lo validamos
  es_valido, resultado_o_error = validar_token_handshake(
      token_url, SECRET_EXCLUSIVO_LOCAL
  )

  if not es_valido:
    st.query_params.clear()

    st.markdown(
        f"""
            <div style="
                background-color: #ffebe9;
                border: 1px solid #ffc1c0;
                color: #cf222e;
                padding: 24px;
                border-radius: 12px;
                font-weight: 500;
                font-size: 15px;
                margin: 30px auto 15px auto;
                max-width: 550px;
                text-align: center;
                box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
            ">
                <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">
                    🔒 Acceso Denegado
                </div>
                <div>
                    {resultado_o_error}
                </div>
            </div>
            """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
      st.link_button(
          "🏠 Volver al Hub Central",
          "https://swimming-pro.streamlit.app",
          use_container_width=True,
      )

    st.stop()

  # C. Si la validación es EXITOSA: marcamos sesión y limpiamos la URL
  st.session_state["puente_validado"] = True
  st.query_params.clear()
# --- INYECCIÓN DE CSS GLOBAL OPTIMIZADO ---
st.markdown(
    """
    <style>
        /* 1. Ajuste del lienzo superior */
        .block-container {
            padding-top: 1rem !important; 
            padding-bottom: 0rem !important;
            max-width: 98% !important;     
        }
        
        /* 2. Compactar espacio muerto */
        div[data-testid="stVerticalBlock"] {
            gap: 0rem !important; 
        }
        .element-container {
            margin-bottom: 4px !important;
        }
      
        /* SegmentedControl */
        div[data-testid="stSegmentedControl"] {
            margin-top: 2px !important;    
            margin-bottom: 4px !important;
        }

        /* 4. Subpestañas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background-color: #f8f9fa;
            padding: 4px 6px 0px 6px;
            border-radius: 8px 8px 0px 0px;
            border-bottom: 1px solid #e5e7eb;
        }
        .stTabs [data-baseweb="tab"] {
            height: 32px !important;
            background-color: transparent;
            border-radius: 6px 6px 0px 0px;
            padding: 2px 10px !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            color: #6b7280 !important;
            border: none !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: #ffffff !important;
            color: #1f2937 !important;
            font-weight: 600 !important;
            border-bottom: 3px solid #3b82f6 !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)


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
            return False, f"El ticket digital de acceso ha expirado. (Transcurrido: {int(tiempo_transcurrido)}s) Debe ingresar por la puerta principal de la aplicación"
            
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
# 🛑 CANDADO DE SEGURIDAD INTERCLUBES (ASIGNACIÓN DIRECTA)
# =============================================================================

# Leemos directamente la clave configurada en tus Secrets (con respaldo idéntico)
SECRET_EXCLUSIVO_LOCAL = st.secrets.get("CLUB_SECRET_KEY", "ClubdeNatacionCentroGallegoqazws")

if "puente_validado" not in st.session_state:
    st.session_state["puente_validado"] = False

params = st.query_params
token_url = params.get("auth")

if not st.session_state["puente_validado"]:

  # 1. Si entran sin token por la URL
  if token_url is None or token_url == "":
    st.query_params.clear()

    # Tarjeta estática de aviso
    st.markdown(
        """
            <div style="
                background-color: #ffebe9;
                border: 1px solid #ffc1c0;
                color: #cf222e;
                padding: 24px;
                border-radius: 12px;
                font-weight: 500;
                font-size: 15px;
                margin: 30px auto 15px auto;
                max-width: 550px;
                text-align: center;
                box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
            ">
                <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">
                    🔒 Acceso Denegado
                </div>
                <div>
                    No está autorizado a entrar directamente a este nodo. Debe iniciar sesión a través del Hub Central.
                </div>
            </div>
            """,
        unsafe_allow_html=True,
    )

    # Botón nativo de Streamlit alineado al centro
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
      st.link_button(
          "🏠 Volver al Hub Central",
          "https://swimming-pro.streamlit.app",
          use_container_width=True,
      )

    st.stop()

  # 2. Validar el token si viene en la URL
  es_valido, resultado_o_error = validar_token_handshake(
      token_url, SECRET_EXCLUSIVO_LOCAL
  )

  # 3. Si el token expiró o la firma es inválida
  if not es_valido:
    st.query_params.clear()

    st.markdown(
        f"""
            <div style="
                background-color: #ffebe9;
                border: 1px solid #ffc1c0;
                color: #cf222e;
                padding: 24px;
                border-radius: 12px;
                font-weight: 500;
                font-size: 15px;
                margin: 30px auto 15px auto;
                max-width: 550px;
                text-align: center;
                box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
            ">
                <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">
                    🔒 Acceso Denegado
                </div>
                <div>
                    {resultado_o_error}
                </div>
            </div>
            """,
        unsafe_allow_html=True,
    )

    # Botón nativo de Streamlit alineado al centro
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
      st.link_button(
          "🏠 Volver al Hub Central",
          "https://swimming-pro.streamlit.app",
          use_container_width=True,
      )

    st.stop()

  # Si la validación pasa correctamente
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
