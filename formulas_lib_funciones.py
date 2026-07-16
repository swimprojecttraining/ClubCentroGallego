import hashlib
import random
import datetime
from cryptography.fernet import Fernet
import streamlit as st
import numpy as np
from scipy.optimize import fsolve
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def hash_password(password: str) -> str:
    """Genera el hash SHA-256 de la contraseña para validación local."""
    return hashlib.sha256(password.encode()).hexdigest()

def desencriptar_credencial(texto_cifrado: str, llave_maestra: str) -> str:
    """Descifra en caliente las credenciales de Supabase usando AES-256."""
    try:
        fernet = Fernet(llave_maestra.encode())
        return fernet.decrypt(texto_cifrado.encode()).decode()
    except Exception as e:
        st.error(f"Error crítico de descifrado de credenciales: {e}")
        st.stop()
# -------------------------------------------------------------
# GESTIÓN DE CORREOS AUTOMATIZADOS (SMTP)
# -------------------------------------------------------------
def enviar_email(destinatario: str, asunto: str, cuerpo_html: str) -> tuple:
    """Envía notificaciones automatizadas utilizando las credenciales de entorno."""
    try:
        # Extracción de credenciales desde los secretos del entorno
        remitente = st.secrets["smtp"]["email"]
        password = st.secrets["smtp"]["password"]
        servidor = st.secrets["smtp"]["server"]
        puerto = st.secrets["smtp"].get("port", 587)

        # Configuración del mensaje
        msg = MIMEMultipart()
        msg['From'] = remitente
        msg['To'] = destinatario
        msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo_html, 'html'))

        # Conexión al servidor SMTP
        server = smtplib.SMTP(servidor, puerto)
        server.starttls()
        server.login(remitente, password)
        server.send_message(msg)
        server.quit()
        
        return True, "Correo enviado correctamente."
    except Exception as e:
        error_msg = f"Error en el servidor SMTP: {e}"
        print(error_msg)
        return False, error_msg
# -------------------------------------------------------------
# MOTOR DE EVALUACIÓN DE HITOS Y COMPETENCIAS
# -------------------------------------------------------------
def calcular_edad_tecnica_al_31_dic(fecha_nacimiento, temporada_activa):
    """Calcula la edad del nadador al 31 de diciembre del año en curso."""
    if isinstance(fecha_nacimiento, str):
        fecha_nacimiento = datetime.datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()        
    edad_tecnica = temporada_activa - fecha_nacimiento.year
    return edad_tecnica

def evaluar_elegibilidad_internacional(edad_tecnica, ente_rector):
    entes_internacionales = ["PANAM AQUATICS", "WORLD AQUATICS"]
    if ente_rector in entes_internacionales:
        if edad_tecnica < 14:
            return False, f"Edad técnica insuficiente ({edad_tecnica} años). Mínimo requerido: 14 años."
    return True, None

def calcular_fecha_alerta(fecha_inicio_competencia, dias_anticipacion=15):
    if isinstance(fecha_inicio_competencia, str):
        fecha_inicio_competencia = datetime.datetime.strptime(fecha_inicio_competencia, '%Y-%m-%d').date()
    return fecha_inicio_competencia - datetime.timedelta(days=dias_anticipacion)

# -------------------------------------------------------------
# TRANSFORMACIÓN DE TIEMPOS
# -------------------------------------------------------------
def formatear_a_minutos(segundos_flotante: float) -> str:
    """Convierte segundos a formato M:SS.hh"""
    try:
        if segundos_flotante <= 0 or pd.isna(segundos_flotante):
            return "-"
        minutos = int(segundos_flotante // 60)
        segundos = segundos_flotante % 60      
        if minutos > 0:
            return f"{minutos}:{segundos:05.2f}"
        else:
            return f"{segundos:.2f}"
    except (ValueError, TypeError):
        return "-"

def convertir_string_a_segundos(tiempo_str: str) -> float:
    try:
        tiempo_str = tiempo_str.strip()
        if ":" in tiempo_str:
            partes_minutos = tiempo_str.split(":")
            minutos = int(partes_minutos[0])
            segundos = float(partes_minutos[1])
            return float(round((minutos * 60) + segundos, 2))
        else:
            return float(round(float(tiempo_str), 2))
    except Exception:
        raise ValueError("Formato de tiempo inválido. Use 'mm:ss.00' o 'ss.00'")    

# -------------------------------------------------------------
# CÁLCULOS DE MARCAS E HITOS
# -------------------------------------------------------------
def procesar_mejor_marca_historica(df_atleta):
    """
    Calcula t0, T0, t_pb y T_pb basándose exclusivamente en la columna 'Edad'.
    Aplica la lógica del valle: Si tras el PB absoluto hay dos marcas consecutivas peores,
    el PB se anula y el nuevo punto de control es la última marca registrada.
    """
    # 1. Aseguramos orden cronológico (Edad decimal)
    df = df_atleta.sort_values(by="Edad").reset_index(drop=True)
    
    # 2. Origen (t0, T0) - El registro más antiguo (primera fila)
    t0 = float(df.iloc[0]["Edad"])
    T0 = float(df.iloc[0]["Tiempo"])
    
    # 3. PB Absoluto (el mejor tiempo de toda la historia)
    idx_pb_absoluto = df["Tiempo"].idxmin()
    t_pb = float(df.loc[idx_pb_absoluto, "Edad"])
    T_pb = float(df.loc[idx_pb_absoluto, "Tiempo"])
    
    # 4. Verificación de Valle de Rendimiento
    # Solo miramos si hay marcas posteriores al PB absoluto
    if idx_pb_absoluto < len(df) - 1:
        # Extraemos solo las marcas después del PB
        df_posterior = df.iloc[idx_pb_absoluto + 1 :].reset_index(drop=True)
        
        # Necesitamos al menos 2 marcas para confirmar un valle (dos peores seguidas)
        if len(df_posterior) >= 2:
            valle_encontrado = False
            for i in range(len(df_posterior) - 1):
                # Comparamos si ambas son peores que el PB absoluto
                if df_posterior.iloc[i]["Tiempo"] > T_pb and df_posterior.iloc[i+1]["Tiempo"] > T_pb:
                    valle_encontrado = True
                    break
            
            # 5. Si hay valle, el PB actual se convierte en la última marca (la más reciente)
            if valle_encontrado:
                t_pb = float(df.iloc[-1]["Edad"])
                T_pb = float(df.iloc[-1]["Tiempo"])
                
    return t0, T0, t_pb, T_pb

@st.cache_data(show_spinner=False, ttl=600)
def obtener_datos_hitos_atleta(nadador_id):
    try:
        supabase = st.session_state.get("supabase")
        if not supabase: return None
        
        res_atleta = supabase.table("usuarios").select("fecha_nacimiento").eq("id", nadador_id).execute()
        res_hitos = supabase.table("historial_hitos").select("*, catalogo_competencias(*)").eq("usuario_id", nadador_id).execute()            
        
        if res_atleta.data and res_atleta.data[0].get("fecha_nacimiento"):
            return {
                "fecha_nacimiento": res_atleta.data[0]["fecha_nacimiento"],
                "hitos": res_hitos.data if res_hitos.data else []
            }
    except Exception as e:
        print(f"Error interno en consulta cacheada de Supabase: {e}")
    return None

# -------------------------------------------------------------
# CATEGORÍAS Y EDADES
# -------------------------------------------------------------
def calcular_categoria_competencia(fecha_nac_str):
    if not fecha_nac_str: return "Desconocida", 0
    try:
        fecha_nac = datetime.date.fromisoformat(str(fecha_nac_str))
    except Exception:
        return "Error Formato", 0
    ano_actual = datetime.date.today().year 
    edad_competencia = ano_actual - fecha_nac.year
    if 5 <= edad_competencia <= 6: cat = "Preinfantil A"
    elif 7 <= edad_competencia <= 8: cat = "Preinfantil B"
    elif edad_competencia == 9: cat = "Preinfantil C"
    elif 10 <= edad_competencia < 12: cat = "Infantil A"
    elif 12 <= edad_competencia < 14: cat = "Infantil B"
    elif 14 <= edad_competencia < 16: cat = "Juvenil A"
    elif 16 <= edad_competencia < 18: cat = "Juvenil B"
    elif 18 <= edad_competencia < 25: cat = "Máxima"
    elif edad_competencia >= 25: cat = "Máster"
    else: cat = "Semillero / Menor"
    return cat, edad_competencia

def calcular_edad_decimal(fecha_nacimiento_str, fecha_marca):
    if not fecha_nacimiento_str or not fecha_marca: return None
    try:
        if isinstance(fecha_nacimiento_str, str):
            fecha_nac_obj = datetime.date.fromisoformat(fecha_nacimiento_str)
        else:
            fecha_nac_obj = fecha_nacimiento_str
        diferencia_dias = (fecha_marca - fecha_nac_obj).days
        edad_decimal = diferencia_dias / 365.25
        return round(edad_decimal, 2)
    except Exception:
        return None
# -------------------------------------------------------------
# FUNCIÓN CALCULAR PUNTOS WA
# -------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def calcular_puntos_wa(tiempo_atleta: float, record_mundial: float) -> int:
    """
    Calcula los puntos WA basándose en el WR específico de la prueba y género activos.
    """
    try:
        t = float(tiempo_atleta)
        wr = float(record_mundial)
        if t <= 0 or wr <= 0:
            return 0
        return max(0, int(1000 * ((wr / t) ** 3)))
    except (ValueError, TypeError):
        return 0

def dibujar_lineas_referencia(ax, ref_data, lim_x_min, lim_x_max, peor_tiempo):
    """ Dibuja las líneas de referencia en cualquier gráfico pasado por ax """
    if not ref_data: return

    # Extraemos el objeto
    ref_obj = ref_data[0] if isinstance(ref_data, list) and len(ref_data) > 0 else ref_data
    
    # Configuración de referencias
    configs = [
        {"val": "m_ano",     "lbl": "Mín. Año",    "col": "#A06000", "va": "top"},
        {"val": "m_panam_b", "lbl": "PANAM Jr B",  "col": "#006644", "va": "top"},
        {"val": "m_panam_a", "lbl": "PANAM Jr A",  "col": "#2A658A", "va": "bottom"},
        {"val": "m_wa_b",    "lbl": "WA B",        "col": "#943100", "va": "top"},
        {"val": "m_wa_a",    "lbl": "WA A",        "col": "#883963", "va": "bottom"},
        {"val": "m_wr",      "lbl": "WR",          "col": "#2C3E50", "va": "bottom"}
    ]
    
    x_pos = lim_x_min + (lim_x_max - lim_x_min) * 0.02
    
    for cfg in configs:
        if r["val"] > 0 and lim_y_inferior <= r["val"] <= lim_y_superior:
            ax.axhline(y=r["val"], color=r["col"], linestyle=":", linewidth=0.6, alpha=0.7)
            desplazamiento_y = (lim_y_superior - lim_y_inferior) * 0.006 if r["va"] == "bottom" else -((lim_y_superior - lim_y_inferior) * 0.006)
            
# CORRECCIÓN: Pasamos el valor por tu función y limpiamos el sufijo de segundos
            tiempo_lbl_formateado = formatear_a_minutos(r["val"]).replace(" s", "")
            
            ax.text(x_texto, r["val"] + desplazamiento_y, f"{r['lbl']}: {tiempo_lbl_formateado}", color=r["col"], fontsize=7, va=r["va"], ha="left")
else:
    if m_ano > 0:
        ax.axhline(y=m_ano, color="#A06000", linestyle="--", linewidth=0.6, alpha=0.7)
        
# CORRECCIÓN: Formateamos la marca base m_ano a minutos/centésimas
        m_ano_formateado = formatear_a_minutos(m_ano).replace(" s", "")
        
        ax.text(x_texto, m_ano - ((lim_y_superior - lim_y_inferior) * 0.006), f"Target (Base Inf. A): {m_ano_formateado}", color="#A06000", fontsize=7, va="top", ha="left")

# -------------------------------------------------------------
# MOTOR MATEMÁTICO DOBLE CALCULO DE CURVA AJUSTADO
# -------------------------------------------------------------
def resolver_k_individual(eq_t0, eq_T0, eq_t_pb, eq_T_pb, eq_t_peak, eq_T_target):
    # Condición ajustada: t_peak debe ser > t0 y t_pb debe ser >= t0
    if eq_t_peak > eq_t0 and eq_t_pb >= eq_t0:
        tau_eq = (eq_t_pb - eq_t0) / (eq_t_peak - eq_t0)

        def ecuacion_k_eq(k_val):
            if abs(k_val) < 1e-4: return 1e6
            try:
                denominador = 1 - np.exp(-k_val)
                if abs(denominador) < 1e-6: return 1e6
                ter_exp = (np.exp(-k_val * tau_eq) - np.exp(-k_val)) / denominador
                return (eq_T_target + (eq_T0 - eq_T_target) * ter_exp) - eq_T_pb
            except:
                return 1e6

        k_opt_eq, info, ier, msg = fsolve(ecuacion_k_eq, 1.0, full_output=True)
        
        if ier == 1:
            return float(k_opt_eq[0])
            
    # Si llegamos aquí, no se cumplió la condición o no hubo convergencia
    return none

def calcular_curva_atleta(edades_arr, eq_t0, eq_T0, eq_t_pb, eq_T_pb, eq_t_peak, eq_T_target, k_eq, h_eq):
    tiempos = []
    D_eq = eq_T_pb - eq_T_target
    for t in edades_arr:
        if t < eq_t_pb:
            tau_t = (t - eq_t0) / (eq_t_peak - eq_t0)
            ter_exp = (np.exp(-k_eq * tau_t) - np.exp(-k_eq)) / (1 - np.exp(-k_eq))
            T_t = eq_T_target + (eq_T0 - eq_T_target) * ter_exp
        else:
            T_t = eq_T_pb - D_eq * (1 - np.exp(-h_eq * (t - eq_t_pb)))
        tiempos.append(T_t)
    return np.array(tiempos)
