import streamlit as st
import pandas as pd
import io
from datetime import datetime
import xml.etree.ElementTree as ET


# Diccionario para normalizar los códigos del archivo .hy3
MAPEO_PRUEBAS = {
    "0050Fr": "50 Libre", "0100Fr": "100 Libre", "0200Fr": "200 Libre", 
    "0400Fr": "400 Libre", "0800Fr": "800 Libre", "1500Fr": "1500 Libre", 
    "0050Br": "50 Pecho", "0100Br": "100 Pecho", "0200Br": "200 Pecho", 
    "0050Bk": "50 Espalda", "0100Bk": "100 Espalda", "0200Bk": "200 Espalda", 
    "0050Fy": "50 Mariposa", "0100Fy": "100 Mariposa", "0200Fy": "200 Mariposa", 
    "0200IM": "200 Combinado", "0400IM": "400 Combinado"
}

def parsear_lenex(archivo_stream):
    """
    Parsea un archivo Lenex (.lxf) y lo convierte a un DataFrame compatible.
    """
    tree = ET.parse(archivo_stream)
    root = tree.getroot()
    
    resultados = []
    
    # Navegamos por el árbol XML (Lenex -> MEETS -> MEET -> SESSIONS -> SESSION -> EVENTS -> EVENT -> HEATS -> HEAT -> RESULT)
    for result in root.findall(".//RESULT"):
        athlete = result.find("ATHLETE")
        if athlete:
            nombre = f"{athlete.get('lastname')} {athlete.get('firstname')}"
            
            # Buscamos el tiempo (normalmente guardado en 'swimtime')
            tiempo = result.get("swimtime") 
            
            # Buscamos el evento
            event = result.find("../../..") # Subimos en el árbol al evento
            prueba = event.get("event")
            
            resultados.append({
                "Nadador": nombre,
                "Evento": prueba,
                "Tiempo": tiempo # Aquí aplicarás la misma lógica de conversión a segundos
            })
            
    return pd.DataFrame(resultados)

def parsear_hy3(archivo_texto):
    resultados = []
    nadador_actual = None
    for linea in archivo_texto:
        if len(linea) < 2: continue
        record_type = linea[0:2]
        if record_type == "D1":
            apellido = linea[12:22].strip()
            nombre = linea[27:47].strip()
            nadador_actual = f"{nombre} {apellido}"
        elif record_type == "F1" and nadador_actual:
            evento = linea[12:18].strip()
            tiempo_raw = linea[32:38].strip()
            if tiempo_raw:
                resultados.append({
                    "Nadador": nadador_actual,
                    "Evento": evento,
                    "Tiempo": tiempo_raw
                })
    return pd.DataFrame(resultados)

def normalizar_prueba(codigo):
    return MAPEO_PRUEBAS.get(codigo, codigo)

def convertir_hy3_a_segundos(valor):
    """
    Convierte string '012010' a 80.10
    """
    s = str(valor).strip()
    if len(s) != 6 or not s.isdigit():
        return 0.0
    
    minutos = int(s[0:2])
    segundos = int(s[2:4])
    centesimas = int(s[4:6])
    
    return (minutos * 60) + segundos + (centesimas / 100)

def guardar_en_bd(df_procesado, nombre_competencia):
    supabase = st.session_state.supabase
    # Asume que 'supabase' está definido globalmente en tu app
    usuarios_db = supabase.table("usuarios").select("id, nombre, fecha_nacimiento").execute()
    usuarios_dict = {u['nombre'].lower(): {'id': u['id'], 'nacimiento': u['fecha_nacimiento']} for u in usuarios_db.data}
    
    registros_a_insertar = []
    for _, fila in df_procesado.iterrows():
        nombre_file = fila['Nadador'].lower()
        user_info = next((u for name, u in usuarios_dict.items() if name in nombre_file or nombre_file in name), None)
        
        if user_info:
            fecha_nac = pd.to_datetime(user_info['nacimiento'])
            edad_calculada = (datetime.now() - fecha_nac).days / 365.25
            registro = {
                "usuario_id": user_info['id'],
                "prueba": normalizar_prueba(fila['Evento']),
                "tiempo": float(fila['Tiempo']),
                "edad": round(edad_calculada, 2),
                "nota": nombre_competencia
            }
            registros_a_insertar.append(registro)
    
    # Debug: ver qué se va a insertar
    st.json(registros_a_insertar)
    
    if registros_a_insertar:
        try:
            # Descomenta la siguiente línea cuando estés listo para guardar de verdad
            supabase.table("marcas_historicas").insert(registros_a_insertar).execute()
            return True, len(registros_a_insertar)
        except Exception as e:
            return False, str(e)
    return False, "No se encontraron usuarios coincidentes."

def renderizar_tab_importar():
    st.markdown("### 📥 Importación de Competencias (HY3 / Lenex)")
    # 1. Actualizado para aceptar nuevos formatos
    archivo_subido = st.file_uploader("Selecciona el archivo (.hy3, .lxf, .len, .xml)", type=['hy3', 'txt', 'lxf', 'len', 'xml'])
    
    if archivo_subido:
        # 2. Identificar formato
        extension = archivo_subido.name.split('.')[-1].lower()
        df = pd.DataFrame()
        
        try:
            if extension == 'hy3':
                stringio = io.StringIO(archivo_subido.getvalue().decode("utf-8"))
                df = parsear_hy3(stringio)
            elif extension in ['lxf', 'len']:
                df = parsear_lenex(archivo_subido)
            else:
                st.error("Formato no soportado.")
                return

            if not df.empty:
                # 3. Conversión de tiempo estandarizada
                df['Tiempo'] = df['Tiempo'].apply(convertir_hy3_a_segundos)
                st.success(f"✅ ¡Archivo {extension.upper()} procesado!")
                st.dataframe(df, use_container_width=True)
                
                nombre_comp = st.text_input("Nombre de la Competencia (nota):")
                if st.button("💾 Validar y Guardar en BD"):
                    if nombre_comp:
                        exito, msg = guardar_en_bd(df, nombre_comp)
                        if exito:
                            st.success(f"Simulación completa: {msg} registros preparados.")
                        else:
                            st.error(f"Error: {msg}")
                    else:
                        st.warning("Escribe el nombre de la competencia.")
            else:
                st.error("No se encontraron datos válidos en el archivo.")
                
        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")
