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
    if token_url is None or token_url == "":
        # Limpieza de URL y mensaje de bloqueo directo
        st.query_params.clear()
        st.markdown(
            """
            <div style="
                background-color: #ffebe9;
                border: 1px solid #ffc1c0;
                color: #cf222e;
                padding: 20px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 15px;
                margin: 40px auto;
                max-width: 600px;
                text-align: center;
                box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
            ">
                🔒 <b>Acceso Denegado:</b> No está autorizado a entrar directamente a este nodo. Debe iniciar sesión a través del Hub Central.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    es_valido, resultado_o_error = validar_token_handshake(
        token_url, SECRET_EXCLUSIVO_LOCAL
    )

    if not es_valido:
        # 1. Limpiamos la URL para evitar reejecuciones en bucle
        st.query_params.clear()

        # 2. Renderizamos la tarjeta de bloqueo centralizada
        st.markdown(
            f"""
            <div style="
                background-color: #ffebe9;
                border: 1px solid #ffc1c0;
                color: #cf222e;
                padding: 20px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 15px;
                margin: 40px auto;
                max-width: 600px;
                text-align: center;
                box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
            ">
                🔒 <b>Acceso Denegado:</b> {resultado_o_error}
            </div>
            """,
            unsafe_allow_html=True,
        )
        # 3. Bloqueamos la ejecución para que NO aparezca la pantalla de Login
        st.stop()
        
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
