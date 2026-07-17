import streamlit as st
import pandas as pd
import io

def parsear_hy3(archivo_texto):
    resultados = []
    nadador_actual = None

    for linea in archivo_texto:
        if len(linea) < 2: continue
        
        record_type = linea[0:2]
        
        # D1: Nombre del nadador
        if record_type == "D1":
            # Asegúrate de que estos índices coincidan con la línea D1
            apellido = linea[7:27].strip() 
            nombre = linea[27:47].strip()
            nadador_actual = f"{nombre} {apellido}"
            
        # F1: Resultados
        elif record_type == "F1" and nadador_actual:
            # Ajuste de índices para el formato:
            # Evento en 12:18 (0050Fr)
            # Tiempo en 32:38 (002750)
            evento = linea[12:18].strip()
            tiempo_raw = linea[32:38].strip() 
            
            # Solo agregamos si encontramos tiempo
            if tiempo_raw:
                resultados.append({
                    "Nadador": nadador_actual,
                    "Evento": evento,
                    "Tiempo": tiempo_raw
                })

    return pd.DataFrame(resultados)

def renderizar_tab_importar():
    st.markdown("### 📥 Importación de Competencias (Modo Visual)")
    st.info("Sube tu archivo .hy3 para previsualizar los datos antes de guardarlos.")
    
    archivo_subido = st.file_uploader("Selecciona el archivo de resultados (.hy3)", type=['hy3', 'txt'])
    
    if archivo_subido:
        # Convertir el archivo subido (bytes) a un stream de texto
        stringio = io.StringIO(archivo_subido.getvalue().decode("utf-8"))
        
        # Procesar
        try:
            df = parsear_hy3(stringio)
            
            if not df.empty:
                st.success("✅ ¡Archivo procesado con éxito!")
                st.dataframe(df, use_container_width=True)
                
                # Aquí es donde, en el futuro, pondrás tu botón de "Guardar en Supabase"
                if st.button("💾 Validar y Guardar en BD"):
                    st.warning("Esta funcionalidad estará disponible pronto.")
            else:
                st.error("No se encontraron registros tipo D1/F1. ¿Es el formato correcto?")
                
        except Exception as e:
            st.error(f"Error al parsear el archivo: {e}")
