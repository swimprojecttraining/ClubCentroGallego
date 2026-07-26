import streamlit as st
import time
import hmac
import hashlib
import base64
import os
import sys
import streamlit.components.v1 as components

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG & BACKGROUND
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Centro Gallego - Gestión de Entrenamientos", page_icon="🏊"
)


def aplicar_fondo_pantalla():
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
            .stApp {{
                background-image: url("data:image/png;base64,{encoded_string}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
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


aplicar_fondo_pantalla()


# -----------------------------------------------------------------------------
# 2. DECLARE FUNCTIONS FIRST (or import them)
# -----------------------------------------------------------------------------
def validar_token_handshake(token_b64, secret_key_local):
  """Decodifica el token recibido por URL, verifica correspondencia del club,

  comprueba la firma HMAC y valida la ventana de tiempo.
  """
  # Coloca aquí tu implementación existente de la función
  pass


# -----------------------------------------------------------------------------
# 3. INTERCLUB HANDSHAKE CHECK (Now line 119 can see the function above)
# -----------------------------------------------------------------------------
SECRET_EXCLUSIVO_LOCAL = st.secrets.get(
    "CLUB_SECRET_KEY", "ClubdeNatacionCentroGallegoqazws"
)

if "puente_validado" not in st.session_state:
  st.session_state["puente_validado"] = False

params = st.query_params
token_url = params.get("auth")

if not st.session_state["puente_validado"]:

  # Case A: Direct URL access without auth token
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

  # Case B: Token present -> Validate handshake
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

  # Successful handshake
  st.session_state["puente_validado"] = True
  st.query_params.clear()

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
