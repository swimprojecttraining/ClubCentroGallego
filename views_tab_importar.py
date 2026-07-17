import pandas as pd
from datetime import datetime

# Diccionario para normalizar los códigos del archivo .hy3 a tu formato
MAPEO_PRUEBAS = {
    "0050Fr": "50 Libre", "0100Fr": "100 Libre", "0200Fr": "200 Libre", 
    "0400Fr": "400 Libre", "0800Fr": "800 Libre", "1500Fr": "1500 Libre", 
    "0050Br": "50 Pecho","0100Br": "100 Pecho",  "0200Br": "200 Pecho", 
    "0050Bk": "50 Espalda", "0100Bk": "100 Espalda", "0200Bk": "200 Espalda", 
    "0050Fy": "50 Mariposa", "0100Fy": "100 Mariposa", "0200Fy": "200 Mariposa", 
    "0200IM": "200 Combinado",  "0400IM": "400 Combinado"
    
}

def normalizar_prueba(codigo):
    return MAPEO_PRUEBAS.get(codigo, codigo) # Devuelve el normalizado o el original si no existe

def guardar_en_bd(df_procesado, nombre_competencia):
    # 1. Obtener todos los usuarios de un golpe para mapear rápido
    usuarios_db = supabase.table("usuarios").select("id, nombre, fecha_nacimiento").execute()
    usuarios_dict = {u['nombre'].lower(): {'id': u['id'], 'nacimiento': u['fecha_nacimiento']} for u in usuarios_db.data}
    
    registros_a_insertar = []
    
    for _, fila in df_procesado.iterrows():
        nombre_file = fila['Nadador'].lower()
        
        # Buscar usuario en el diccionario
        user_info = next((u for name, u in usuarios_dict.items() if name in nombre_file or nombre_file in name), None)
        
        if user_info:
            # Calcular edad al vuelo
            fecha_nac = pd.to_datetime(user_info['nacimiento'])
            edad_calculada = (datetime.now() - fecha_nac).days / 365.25
            
            # Preparar objeto para BD
            registro = {
                "usuario_id": user_info['id'],
                "prueba": normalizar_prueba(fila['Evento']),
                "tiempo": float(fila['Tiempo']), # Asegúrate que tu parser convierta mm:ss.hh a segundos
                "edad": round(edad_calculada, 2),
                "nota": nombre_competencia
            }
            registros_a_insertar.append(registro)
    
    # 2. Insertar todo el lote
    if registros_a_insertar:
        try:
            supabase.table("marcas_historicas").insert(registros_a_insertar).execute()
            return True, len(registros_a_insertar)
        except Exception as e:
            return False, str(e)
    return False, "No se encontraron usuarios coincidentes."

def renderizar_tab_importar():
    st.markdown("### 📥 Importación de Competencias (Modo Visual)")
    st.info("Sube tu archivo .hy3 para previsualizar los datos antes de guardarlos.")
    
    archivo_subido = st.file_uploader("Selecciona el archivo de resultados (.hy3)", type=['hy3', 'txt'])
    
    if archivo_subido:
        # Convertir el archivo subido (bytes) a un stream de texto
        stringio = io.StringIO(archivo_subido.getvalue().decode("utf-8"))
        
         try:
            df = parsear_hy3(stringio)
            
            if not df.empty:
                st.success("✅ ¡Archivo procesado con éxito!")
                st.dataframe(df, use_container_width=True)
                
                # --- AQUÍ ESTÁ LO QUE TE FALTA ---
                # 1. Pedir el nombre de la competencia
                nombre_comp = st.text_input("Nombre de la Competencia (se guardará en 'nota'):")
                
                # 2. El botón que llama a tu función real
                if st.button("💾 Validar y Guardar en BD"):
                    if nombre_comp:
                        # Llamamos a tu función 'guardar_en_bd' usando el 'df' que acabamos de crear
                        exito, msg = guardar_en_bd(df, nombre_comp)
                        
                        if exito:
                            st.success(f"✅ Se han guardado {msg} registros exitosamente.")
                        else:
                            st.error(f"❌ Error al guardar en BD: {msg}")
                    else:
                        st.warning("⚠️ Debes colocar un nombre a la competencia.")
            else:
                st.error("No se encontraron registros tipo D1/F1. ¿Es el formato correcto?")
                
        except Exception as e:
            st.error(f"Error al parsear el archivo: {e}")
