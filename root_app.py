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
    # 1. Si no viene ningún token por URL
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
                margin: 40px auto;
                max-width: 550px;
                text-align: center;
                box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
            ">
                <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">
                    🔒 Acceso Denegado
                </div>
                <div style="margin-bottom: 16px;">
                    No está autorizado a entrar directamente a este nodo. Debe iniciar sesión a través del Hub Central.
                </div>
                <div style="font-size: 13px; color: #8c232c; margin-bottom: 20px;">
                    Redirigiendo automáticamente al Hub Central en <span id="contador_directo">4</span> segundos...
                </div>
                <a href="https://swimming-pro.streamlit.app" target="_self" style="
                    background-color: #cf222e;
                    color: white;
                    text-decoration: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    font-weight: 600;
                    display: inline-block;
                ">
                    🏠 Volver al Hub Central
                </a>
            </div>

            <script>
                var segs = 4;
                var el_dir = document.getElementById('contador_directo');
                var timer_dir = setInterval(function() {
                    segs--;
                    if (el_dir) el_dir.innerText = segs;
                    if (segs <= 0) {
                        clearInterval(timer_dir);
                        window.location.href = "https://swimming-pro.streamlit.app";
                    }
                }, 1000);
            </script>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    # 2. Validar token si viene en la URL
    es_valido, resultado_o_error = validar_token_handshake(
        token_url, SECRET_EXCLUSIVO_LOCAL
    )

    # 3. Si el token expiró (30s) o la firma HMAC es inválida
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
                margin: 40px auto;
                max-width: 550px;
                text-align: center;
                box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
            ">
                <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">
                    🔒 Acceso Denegado
                </div>
                <div style="margin-bottom: 16px;">
                    {resultado_o_error}
                </div>
                <div style="font-size: 13px; color: #8c232c; margin-bottom: 20px;">
                    Redirigiendo automáticamente al Hub Central en <span id="contador">4</span> segundos...
                </div>
                <a href="https://swimming-pro.streamlit.app" target="_self" style="
                    background-color: #cf222e;
                    color: white;
                    text-decoration: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    font-weight: 600;
                    display: inline-block;
                ">
                    🏠 Volver al Hub Central
                </a>
            </div>

            <script>
                var segundos = 4;
                var el = document.getElementById('contador');
                var timer = setInterval(function() {{
                    segundos--;
                    if (el) el.innerText = segundos;
                    if (segundos <= 0) {{
                        clearInterval(timer);
                        window.location.href = "https://swimming-pro.streamlit.app";
                    }}
                }}, 1000);
            </script>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    # Si la validación es correcta, marcamos el puente como válido
    st.session_state["puente_validado"] = True
        
    # Si todo coincide perfectamente:
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
