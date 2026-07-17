import streamlit as st
import pandas as pd
import io

def parsear_hy3(archivo_texto):
    """
    Lee el archivo línea por línea y extrae datos basándose en índices fijos.
    """
    resultados = []
    nadador_actual = None

    # Iteramos sobre las líneas del archivo subido
    for linea in archivo_texto:
        if len(linea) < 2: continue # Saltar líneas vacías
        
        record_type = linea[0:2]
        
        # D1: Capturamos el nadador actual
        if record_type == "D1":
            # Ajusta estos índices según las pruebas que hagamos con tu archivo real
            apellido = linea[12:32].strip() 
            nombre = linea[32:52].strip()
            nadador_actual = f"{nombre} {apellido}"
            
        # F1: Capturamos la prueba y asociamos al nadador actual
        elif record_type == "F1" and nadador_actual:
            # El evento suele estar en la posición 12-22
            evento = linea[12:22].strip()
            # El tiempo suele estar en la posición 22-28
            tiempo_raw = linea[22:30].strip()
            
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