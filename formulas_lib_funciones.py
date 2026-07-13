import hashlib
import random
import datetime
from cryptography.fernet import Fernet
import streamlit as st
import numpy as np
from scipy.optimize import fsolve
import pandas as pd

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
# MOTOR DE EVALUACIÓN DE HITOS Y COMPETENCIAS
# -------------------------------------------------------------
def calcular_edad_tecnica_al_31_dic(fecha_nacimiento, temporada_activa):
    """
    Calcula la edad del nadador al 31 de diciembre del año en curso, 
    según la normativa técnica para categorización.
    """
    if isinstance(fecha_nacimiento, str):
        fecha_nacimiento = datetime.datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()        
    edad_tecnica = temporada_activa - fecha_nacimiento.year
    return edad_tecnica

def evaluar_elegibilidad_internacional(edad_tecnica, ente_rector):
    """
    Verifica si el nadador cumple con la edad mínima para eventos internacionales.
    Retorna: (Booleano de elegibilidad, Motivo de rechazo o None)
    """
    entes_internacionales = ["PANAM AQUATICS", "WORLD AQUATICS"]
    if ente_rector in entes_internacionales:
        if edad_tecnica < 14:
            return False, f"Edad técnica insuficiente ({edad_tecnica} años). Mínimo requerido: 14 años."
    return True, None

def calcular_fecha_alerta(fecha_inicio_competencia, dias_anticipacion=15):
    """
    Calcula la fecha exacta en la que el cron/sistema debe notificar al atleta.
    """
    if isinstance(fecha_inicio_competencia, str):
        fecha_inicio_competencia = datetime.datetime.strptime(fecha_inicio_competencia, '%Y-%m-%d').date()
        
    fecha_alerta = fecha_inicio_competencia - datetime.timedelta(days=dias_anticipacion)
    return fecha_alerta
# -------------------------------------------------------------
# TRANSFORMACIÓN DE TIEMPOS DE SEGUNDOS (ss,00) A MINUTOS (mm:ss,00)
# -------------------------------------------------------------
def formatear_a_minutos(segundos_flotante: float) -> str:
    """Convierte segundos (ej: 84.15) a formato de natación M:SS.hh (ej: 1:24.15)"""
    try:
        if segundos_flotante <= 0 or pd.isna(segundos_flotante):
            return "-"
        minutos = int(segundos_flotante // 60)
        segundos = segundos_flotante % 60      
        if minutos > 0:
            return f"{minutos}:{segundos:05.2f}"  # M:SS.hh (fuerza 2 dígitos en segundos)
        else:
            return f"{segundos:.2f}"            # Si es menor a un minuto, lo deja en segundos
    except (ValueError, TypeError):
        return "-"

def convertir_string_a_segundos(tiempo_str: str) -> float:
    """
    Convierte un string formateado (M:SS.hh o SS.hh) a segundos flotantes.
    Ejemplos: '1:13.34' -> 73.34 | '46.28' -> 46.28
    """
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
# FUNCIÓN DE CALCULO DE EDAD_HITO (MÓDULO INDEPENDIENTE)
# -------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=600)  # Almacena en caché por 10 minutos
def obtener_datos_hitos_atleta(nadador_id):
    """
    Consulta de forma segura y aislada la información del atleta.
    Al estar decorada con @st.cache_data, Streamlit garantiza que NO 
    se generen loops infinitos ni sobrecargas a Supabase.
    """
    try:
        res_atleta = supabase.table("usuarios") \
            .select("fecha_nacimiento") \
            .eq("id", nadador_id) \
            .execute()
            
        res_hitos = supabase.table("historial_hitos") \
            .select("*, catalogo_competencias(*)") \
            .eq("usuario_id", nadador_id) \
            .execute()            
        if res_atleta.data and res_atleta.data[0].get("fecha_nacimiento"):
            return {
                "fecha_nacimiento": res_atleta.data[0]["fecha_nacimiento"],
                "hitos": res_hitos.data if res_hitos.data else []
            }
    except Exception as e:
        print(f"Error interno en consulta cacheada de Supabase: {e}")
    return None

def sincronizar_hitos_competencias_atleta(nadador_id, fecha_nacimiento, genero_atleta):
    """
    Revisa el catálogo de competencias y asegura que el atleta tenga creados sus hitos
    para las competencias Nacionales e Internacionales de la temporada actual.
    """
    try:
        supabase_client = st.session_state.get("supabase")
        if not supabase_client:
            return
        # 1. Obtener el catálogo global de competencias
        competencias = obtener_catalogo_competencias_cache()
        if not competencias:
            return
        # 2. Obtener los hitos que ya tiene registrados el nadador actualmente
        hitos_actuales = supabase_client.table("historial_hitos") \
            .select("competencia_id") \
            .eq("usuario_id", nadador_id) \
            .execute()        
        ids_competencias_registradas = [h["competencia_id"] for h in hitos_actuales.data] if hitos_actuales.data else []
        # 3. Evaluar qué competencias le corresponden y faltan por registrar
        for comp in competencias:
            comp_id = comp.get("id")
            # Evitamos duplicados si ya existe el hito para esta competencia
            if comp_id in ids_competencias_registradas:
                continue
            tipo_evento = str(comp.get("categoria_evento", "")).upper()            
            # Filtramos estrictamente por Nacional o Internacional (con restricción)
            if "NACIONAL" in tipo_evento or "INTERNACIONAL" in tipo_evento:
                fecha_inicio_str = comp.get("fecha_inicio")               
                if fecha_inicio_str:
                    fecha_comp = pd.to_datetime(fecha_inicio_str).date()                    
                    # Calcular la edad exacta que tendrá el atleta en esa competencia
                    edad_en_evento = calcular_edad_decimal(fecha_nacimiento, fecha_comp)                   
                    # Estructurar el nuevo registro de hito alineado con tu backend
                    nuevo_hito = {
                        "usuario_id": nadador_id,
                        "competencia_id": comp_id,
                        "nombre_hito": comp.get("nombre_evento", "Campeonato Obligatorio"),
                        "fecha_evento": fecha_inicio_str,
                        "edad_hito": float(round(edad_en_evento, 2)),
                        "descripcion": f"Sincronizado automáticamente para la temporada {comp.get('temporada', '')}"
                    }                    
                    # Insertar en la tabla historial_hitos de Supabase
                    supabase_client.table("historial_hitos").insert(nuevo_hito).execute()                    
        # Forzar la limpieza del caché local de hitos para que cargue los nuevos de inmediato
        st.cache_data.clear()
    except Exception as e:
        print(f"Error silencioso en la sincronización automática de hitos: {e}")

# -------------------------------------------------------------
# LÓGICA DE CATEGORÍAS ETARIAS (Edad cumplida al 31 de Diciembre)
# -------------------------------------------------------------
def calcular_categoria_competencia(fecha_nac_str):
    if not fecha_nac_str:
        return "Desconocida", 0
    try:
        fecha_nac = datetime.date.fromisoformat(str(fecha_nac_str))
    except Exception:
        return "Error Formato", 0
        
    ano_actual = datetime.date.today().year 
    edad_competencia = ano_actual - fecha_nac.year
    
    if 5 <= edad_competencia <= 6:
        cat = "Preinfantil A"
    elif 7 <= edad_competencia <= 8:
        cat = "Preinfantil B"
    elif edad_competencia == 9:
        cat = "Preinfantil C"
    elif 10 <= edad_competencia < 12:
        cat = "Infantil A"
    elif 12 <= edad_competencia < 14:
        cat = "Infantil B"
    elif 14 <= edad_competencia < 16:
        cat = "Juvenil A"
    elif 16 <= edad_competencia < 18:
        cat = "Juvenil B"
    elif 18 <= edad_competencia < 25:
        cat = "Máxima"
    elif edad_competencia >= 25:
        cat = "Máster"
    else:
        cat = "Semillero / Menor"
    return cat, edad_competencia

def calcular_edad_decimal(fecha_nacimiento_str, fecha_marca):
    if not fecha_nacimiento_str or not fecha_marca:
        return None
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
# FUNCIÓN AUXILIAR: CONSULTA Y FILTRADO DE ATLETAS (ETAPA 2)
# -------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def obtener_atletas_filtrados_supabase():
    """Consulta la base de datos y devuelve una lista de diccionarios con la data de los atletas."""
    try:
        supabase = st.session_state.get("supabase_client")
        if not supabase:
            return []
        
        # Ajusta "usuarios" por el nombre exacto de tu tabla si difiere
        response = supabase.table("usuarios").select("id, nombre, email, genero, fecha_nacimiento").execute()
        if not response.data:
            return []
            
        lista_atletas = []
        for usuario in response.data:
            # Extraemos los campos asegurando que existan
            nombre = usuario.get("nombre", "Sin Nombre")
            email = usuario.get("email", "")
            genero = usuario.get("genero", "M") # 'M' o 'F'
            fecha_nac = usuario.get("fecha_nacimiento")
            
            # Usamos tu función para calcular la categoría y la edad
            categoria, edad = calcular_categoria_competencia(fecha_nac)
            
            # Solo agregamos si tiene un correo válido registrado
            if email and email.strip() != "":
                lista_atletas.append({
                    "id": usuario.get("id"),
                    "nombre": nombre,
                    "email": email,
                    "genero": "Masculino" if genero == "M" else "Femenino",
                    "genero_codigo": genero,
                    "categoria": categoria,
                    "edad": edad
                })
        return lista_atletas
    except Exception as e:
        st.error(f"Error al consultar base de datos de atletas: {e}")
        return []
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

# -------------------------------------------------------------
# FUNCIÓN DE ENVÍO DE CORREOS (MÓDULO INDEPENDIENTE)
# -------------------------------------------------------------
def enviar_email(asunto, cuerpo, destinatario):
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["EMAIL_REMITE"]
        msg['To'] = destinatario
        msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo, 'plain'))
        with smtplib.SMTP_SSL(st.secrets["EMAIL_SMTP_SERVER"], int(st.secrets["EMAIL_SMTP_PORT"])) as server:
            server.login(st.secrets["EMAIL_REMITE"], st.secrets["EMAIL_PASSWORD"])
            server.sendmail(st.secrets["EMAIL_REMITE"], destinatario, msg.as_string())
        return True
    except Exception as e:
        print(f"Error al enviar email: {e}")
        return False
#==========================================================================================================
# MOTOR MATEMÁTICO DOBLE CALCULO DE CURVA AJUSTADO
#==========================================================================================================
def resolver_k_individual(eq_t0, eq_T0, eq_t_pb, eq_T_pb, eq_t_peak, eq_T_target):
    if eq_t_peak > eq_t0 and eq_t_pb > eq_t0:
        tau_eq = (eq_t_pb - eq_t0) / (eq_t_peak - eq_t0)
        def ecuacion_k_eq(k_val):
            ter_exp = (np.exp(-k_val * tau_eq) - np.exp(-k_val)) / (1 - np.exp(-k_val))
            return (eq_T_target + (eq_T0 - eq_T_target) * ter_exp) - eq_T_pb
        k_opt_eq, _, _, _ = fsolve(ecuacion_k_eq, 1.0, full_output=True)
        return k_opt_eq[0]
    return 0.4

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

def procesar_mejor_marca_historica(df_procesado):
    """
    Calcula los puntos t0, T0, t_pb, T_pb extraídos de la lógica histórica.
    Centralizado para limpieza de Sidebar.
    """
    if df_procesado.empty:
        return None, None, None, None
    
    # Asegurar tipos
    df = df_procesado.copy()
    df["Edad"] = pd.to_numeric(df["Edad"], errors='coerce')
    df["Tiempo"] = pd.to_numeric(df["Tiempo"], errors='coerce')
    df = df.dropna(subset=["Edad", "Tiempo"]).sort_values("Edad").reset_index(drop=True)
    
    if df.empty:
        return None, None, None, None

    db_t0 = float(df.iloc[0]["Edad"])
    db_T0 = float(df.iloc[0]["Tiempo"])
    n_registros = len(df)
    
    if n_registros == 1:
        db_t_pb, db_T_pb = db_t0, db_T0
    elif n_registros == 2:
        if float(df.iloc[-1]["Tiempo"]) <= float(df.iloc[-2]["Tiempo"]):
            db_t_pb, db_T_pb = float(df.iloc[-1]["Edad"]), float(df.iloc[-1]["Tiempo"])
        else:
            db_t_pb, db_T_pb = float(df.iloc[-2]["Edad"]), float(df.iloc[-2]["Tiempo"])
    else:
        indice_min_tiempo = df["Tiempo"].idxmin()
        posicion_desde_el_final = (n_registros - 1) - indice_min_tiempo
        
        if posicion_desde_el_final >= 2:
            db_t_pb, db_T_pb = float(df.iloc[-1]["Edad"]), float(df.iloc[-1]["Tiempo"])
        else:
            t_ultima, t_penultima = float(df.iloc[-1]["Tiempo"]), float(df.iloc[-2]["Tiempo"])
            if t_ultima <= t_penultima:
                db_t_pb, db_T_pb = float(df.iloc[-1]["Edad"]), t_ultima
            else:
                db_t_pb, db_T_pb = float(df.iloc[-2]["Edad"]), t_penultima
    
    return db_t0, db_T0, db_t_pb, db_T_pb
