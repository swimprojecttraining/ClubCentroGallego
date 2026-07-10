import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from formulas_lib_funciones import (
    convertir_string_a_segundos,
    calcular_edad_decimal,
    formatear_a_minutos,
    calcular_categoria_competencia
)

def renderizar_tab_marcas(datos_sidebar):
    # --- BLINDAJE DE CONEXIÓN (El salvavidas) ---
    db = st.session_state.get("supabase")
    if db is None:
        st.error("⚠️ La sesión de base de datos no está disponible. Por favor, refresca la página.")
        st.stop()

    st.markdown("### ⏱️ Panel de Control Curricular y Marcas Oficiales")
    st.caption("Módulo centralizado para la gestión de marcas oficiales, análisis de récords personales y exportación curricular.")

    # Variables de entorno
    titulo_grafico = datos_sidebar.get("titulo_grafico", "Prueba General") if datos_sidebar else "Prueba General"
    id_atleta_actual = st.session_state.get("nadador_seleccionado_id")
    rol_usuario = st.session_state.get("rol")
    id_usuario = st.session_state.get("usuario_id")

    # --- CARPINTERÍA DE DATOS ---
    records_marcas = []
    df_procesado = pd.DataFrame()
    df_marcas_raw = pd.DataFrame()

    try:
        raw_db = db.table("marcas_historicas").select("*").eq("usuario_id", id_atleta_actual).execute()
        records_marcas = raw_db.data if raw_db else []
        
        if records_marcas:
            df_marcas_raw = pd.DataFrame(records_marcas)
            df_procesado = df_marcas_raw[df_marcas_raw["prueba"] == titulo_grafico].copy()
            if not df_procesado.empty:
                df_procesado = df_procesado.sort_values("edad").reset_index(drop=True)
                df_procesado["Edad"] = df_procesado["edad"].round(2)
                df_procesado["Tiempo"] = df_procesado["tiempo"]
                df_procesado["Evento / Fecha"] = df_procesado["nota"]
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")

    # --- ESTRUCTURA DE TABS ---
    subtab_ingreso, subtab_top_tiempos, subtab_evolucion_prueba = st.tabs([
        "📥 1. Ingresar y Gestionar Marcas",
        "🥇 2. Reporte de Mejores Tiempos", 
        "📈 3. Buscador Histórico"
    ])

    with subtab_ingreso:
        col_form, col_tabla_rapida = st.columns([1, 1.2])
        with col_form:
            with st.form("form_insertar_marca", clear_on_submit=True):
                ins_fecha_evento = st.date_input("Fecha:", value=datetime.date.today())
                ins_tiempo_str = st.text_input("Tiempo (ej: 1:13.34):")
                ins_nota = st.text_input("Evento / Lugar:")
                if st.form_submit_button("💾 Guardar"):
                    try:
                        ins_tiempo = convertir_string_a_segundos(ins_tiempo_str)
                        edad_calc = calcular_edad_decimal(st.session_state.get("fecha_nacimiento"), ins_fecha_evento)
                        db.table("marcas_historicas").insert({
                            "prueba": titulo_grafico, "edad": float(edad_calc),
                            "tiempo": float(ins_tiempo), "nota": ins_nota, "usuario_id": id_atleta_actual
                        }).execute()
                        st.success("Marca guardada")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        with col_tabla_rapida:
            if not df_procesado.empty:
                df_visual = df_procesado.copy()
                df_visual["Tiempo"] = df_visual["Tiempo"].apply(lambda x: formatear_a_minutos(float(x)))
                st.dataframe(df_visual.drop(columns=["id", "prueba", "usuario_id", "edad", "nota", "tiempo"], errors="ignore"), use_container_width=True)
                
                if rol_usuario in ["Head Coach", "Entrenador", "Administrador"]:
                    id_del = st.selectbox("Seleccione para eliminar:", options=df_procesado["id"].tolist(), format_func=lambda x: f"ID: {x}")
                    if st.button("🗑️ Eliminar Fila"):
                        db.table("marcas_historicas").delete().eq("id", int(id_del)).execute()
                        st.rerun()

    # (El resto de la lógica de análisis puede quedarse igual, 
    # simplemente sustituye las llamadas a 'ctx_supabase_mar' por 'db')
    if records_marcas:
        # ... (Mantén tu lógica de subtab_top_tiempos y subtab_evolucion_prueba aquí)
        # IMPORTANTE: Donde antes decías 'ctx_supabase_mar', ahora usa 'db'
        pass
