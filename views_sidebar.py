import streamlit as st
import pandas as pd
import datetime

# 📦 IMPORTACIÓN DESDE TU LIBRERÍA REAL DE FUNCIONES
from formulas_lib_funciones import (
    calcular_categoria_competencia,
    formatear_a_minutos,
    convertir_string_a_segundos,
    procesar_mejor_marca_historica
)

# 🚀 IMPORTACIÓN DESDE TU CAPA DE CACHÉ
# (Asegúrate de que el nombre coincida con tu archivo real, ej: conections_supabase_cache)
from conections_supabase_cache import (
    obtener_atletas_asignados_cache,
    obtener_nadadores_activos_cache,
    obtener_marcas_historicas_cache,
    obtener_marcas_referencia_cache,
    obtener_marcas_equipo_cache
)

# 🎨 IMPORTACIÓN DESDE TU MÓDULO DE ESTILOS VISUALES
from views_styles import spc


def renderizar_sidebar_completo():
    """
    Renderiza el centro de mandos interactivo (SIDEBAR) respetando rigurosamente
    las posiciones, variables de simulación y controles del modelo original.
    """
    # 🔐 Garantizar el aislamiento usando la conexión dinámica del club seleccionado
    if "supabase" not in st.session_state or st.session_state.supabase is None:
        st.error("No hay una conexión activa a la base de datos de ningún club.")
        st.stop()

    # -------------------------------------------------------------
    # CONTROL DE SESIÓN GENERAL
    # -------------------------------------------------------------
    st.sidebar.markdown(f"**Usuario:** {st.session_state.nombre_nadador}  \n**Nivel:** `{st.session_state.rol}`")
    if st.sidebar.button("🚪 Salir del Sistema"):
        st.session_state.autenticado = False
        st.rerun()

    # 🔄 BOTÓN DE ACTUALIZACIÓN CON RESGUARDO DE CONEXIÓN
    with st.sidebar:
        st.markdown("<hr style='width: 30%; margin: 8px auto; border-top: 1px solid #ccc;'/>", unsafe_allow_html=True)
        if st.sidebar.button("🔄 Actualizar datos"):
            # Resguardo preventivo anti-desconexión
            conexion_segura = st.session_state.supabase
            autenticado_seguro = st.session_state.autenticado
            
            st.cache_data.clear()
            
            st.session_state.supabase = conexion_segura
            st.session_state.autenticado = autenticado_seguro
            st.toast("⚡ Datos del club y marcas actualizados.", icon="ℹ️")
            st.rerun()

    # -------------------------------------------------------------
    # 🎯 PANEL DE NAVEGACIÓN DE ATLETAS (Filtros por Rol con Caché)
    # -------------------------------------------------------------
    if st.session_state.rol in ["Head Coach", "Entrenador", "Administrador"]:
        spc()
        st.sidebar.subheader("🎯 Panel de Navegación de Atletas")
        try:
            # Reemplazo de consulta directa por Caché
            atletas_disponibles = obtener_nadadores_activos_cache()
            
            if st.session_state.rol == "Entrenador":
                ids_asignados = obtener_atletas_asignados_cache(st.session_state.usuario_id)
                if ids_asignados:
                    atletas_disponibles = [a for a in atletas_disponibles if a["id"] in ids_asignados]
                else:
                    atletas_disponibles = [] # No tiene nadadores asignados activos
            
            if atletas_disponibles:
                df_atl = pd.DataFrame(atletas_disponibles)
                dict_atletas = dict(zip(df_atl["id"], df_atl["nombre"]))
                
                sel_id = st.sidebar.selectbox("Monitorear Nadador:", options=list(dict_atletas.keys()), format_func=lambda x: dict_atletas[x])
                atleta_row = df_atl[df_atl["id"] == sel_id].iloc[0]
                
                st.session_state.nadador_seleccionado_id = int(atleta_row["id"])
                st.session_state.nadador_seleccionado_nombre = atleta_row["nombre"]
                st.session_state.nadador_seleccionado_genero = atleta_row["genero"]
                
                cat_calc, _ = calcular_categoria_competencia(atleta_row["fecha_nacimiento"])
                st.session_state.nadador_seleccionado_categoria = cat_calc
            else:
                st.sidebar.warning("⚠️ No tienes nadadores asignados en este momento. (Por defecto asignados al Head Coach)")
                st.session_state.nadador_seleccionado_id = None
        except Exception as e:
            st.error(f"Error cargando nómina de atletas filtrada: {e}")
    else:
        st.session_state.nadador_seleccionado_id = st.session_state.usuario_id
        st.session_state.nadador_seleccionado_nombre = st.session_state.nombre_nadador
        st.session_state.nadador_seleccionado_genero = st.session_state.genero
        st.session_state.nadador_seleccionado_categoria = st.session_state.categoria_atleta

    # Variables colectivas inicializadas exactamente igual al modelo original
    modo_equipo = False
    tipo_filtro = "Todos los Atletas"
    filtro_genero = "Todos"
    cat_sel = None
    ids_sel = []

    # -------------------------------------------------------------
    # 👥 ANÁLISIS COLECTIVO (Con Caché)
    # -------------------------------------------------------------
    if st.session_state.rol in ["Head Coach", "Entrenador", "Administrador"]:
        spc()
        st.sidebar.subheader("👥 Análisis Colectivo")
# 👥 ANÁLISIS COLECTIVO (Versión de Depuración)
        modo_equipo = st.sidebar.checkbox("Activar Comparativa de Equipo", value=False)
        
        # --- INICIALIZACIÓN SEGURA Y OBLIGATORIA ---
        lista_atletas = []
        df_global = pd.DataFrame()
        
        if modo_equipo:
            spc()
            st.sidebar.subheader("🔍 Filtros de Segmentación de Equipo")
            filtro_genero = st.sidebar.radio("Segmentar por Género:", options=["Todos", "Femenino (F)", "Masculino (M)"])
            tipo_filtro = st.sidebar.radio("Segmentar adicionalmente por:", options=["Todos los Atletas", "Categoría Etaria", "Atletas Específicos"])

            # --- SIN TRY/EXCEPT PARA VER EL ERROR REAL ---
            atletas_preload = obtener_nadadores_activos_cache()
            
            # Debug: ¿Qué nos trae el caché?
            if atletas_preload is None:
                st.sidebar.error("Error: obtener_nadadores_activos_cache() devuelve None")
            else:
                # 1. Filtro Género
                if filtro_genero == "Femenino (F)":
                    atletas_preload = [a for a in atletas_preload if a.get("genero") == "F"]
                elif filtro_genero == "Masculino (M)":
                    atletas_preload = [a for a in atletas_preload if a.get("genero") == "M"]

                # 2. Asignación y otros filtros
                if tipo_filtro == "Todos los Atletas":
                    lista_atletas = atletas_preload
                
                elif tipo_filtro == "Categoría Etaria":
                    # Usamos .get() por seguridad
                    categorias_disponibles = sorted(list(set([calcular_categoria_competencia(a.get("fecha_nacimiento"))[0] for a in atletas_preload if a.get("fecha_nacimiento")])))
                    if categorias_disponibles:
                        cat_sel = st.sidebar.selectbox("Seleccione la categoría:", options=categorias_disponibles)
                        lista_atletas = [a for a in atletas_preload if calcular_categoria_competencia(a.get("fecha_nacimiento"))[0] == cat_sel]
                
                elif tipo_filtro == "Atletas Específicos":
                    dict_nom = {a["id"]: a["nombre"] for a in atletas_preload}
                    ids_sel = st.sidebar.multiselect("Seleccione nadadores:", options=list(dict_nom.keys()), format_func=lambda x: dict_nom[x])
                    lista_atletas = [a for a in atletas_preload if a["id"] in ids_sel]

                # 3. Consulta final
                if lista_atletas:
                    ids_consulta = [a["id"] for a in lista_atletas]
                    df_global = obtener_marcas_equipo_cache(st.session_state.supabase, ids_consulta, titulo_grafico)

    # -------------------------------------------------------------
    # 📊 AJUSTES DINÁMICOS POR CATEGORÍA Y LISTADO DE PRUEBAS
    # -------------------------------------------------------------
    spc()
    st.sidebar.subheader("📊 Ajustes por prueba")

    cat_atleta = st.session_state.nadador_seleccionado_categoria
    es_preinfantil = cat_atleta.startswith("Preinfantil") if cat_atleta else False

    if es_preinfantil:
        lista_pruebas = [
            '--- 🏊‍♂️ LIBRE ---', '25 Libre', '50 Libre',
            '--- 🏊‍♂️ ESPALDA ---', '25 Espalda',
            '--- 🏊‍♂️ MARIPOSA ---', '25 Mariposa',
            '--- 🏊‍♂️ PECHO ---', '25 Pecho',
            '--- 🏊‍♂️ COMBINADO ---', '100 Combinado'
        ]
    elif cat_atleta == "Infantil A":
        lista_pruebas = [
            '--- 🏊‍♂️ LIBRE ---', '50 Libre', '100 Libre', '200 Libre', '400 Libre',
            '--- 🏊‍♂️ ESPALDA ---', '50 Espalda',
            '--- 🏊‍♂️ MARIPOSA ---', '50 Mariposa',
            '--- 🏊‍♂️ PECHO ---', '50 Pecho',
            '--- 🏊‍♂️ COMBINADO ---', '200 Combinado'
        ]
    elif cat_atleta == "Infantil B":
        lista_pruebas = [
            '--- 🏊‍♂️ LIBRE ---', '50 Libre', '100 Libre', '200 Libre', '400 Libre', '800 Libre',
            '--- 🏊‍♂️ ESPALDA ---', '50 Espalda', '100 Espalda', '200 Espalda',
            '--- 🏊‍♂️ MARIPOSA ---', '50 Mariposa', '100 Mariposa', '200 Mariposa',
            '--- 🏊‍♂️ PECHO ---', '50 Pecho', '100 Pecho', '200 Pecho',
            '--- 🏊‍♂️ COMBINADO ---', '200 Combinado'
        ]
    else:
        lista_pruebas = [
            '--- 🏊‍♂️ LIBRE ---', '50 Libre', '100 Libre', '200 Libre', '400 Libre', '800 Libre', '1500 Libre',
            '--- 🏊‍♂️ ESPALDA ---', '50 Espalda', '100 Espalda', '200 Espalda',
            '--- 🏊‍♂️ MARIPOSA ---', '50 Mariposa', '100 Mariposa', '200 Mariposa',
            '--- 🏊‍♂️ PECHO ---', '50 Pecho', '100 Pecho', '200 Pecho',
            '--- 🏊‍♂️ COMBINADO ---', '200 Combinado', '400 Combinado'
        ]

    titulo_grafico = st.sidebar.selectbox("Estilo y Distancia:", options=lista_pruebas, index=1)

    if titulo_grafico.startswith("---"):
        st.sidebar.info("👆 Selecciona una distancia específica en el menú superior para ver o editar los datos.")
        st.stop()

    contenedor_sliders = st.sidebar.container()
    m_ano, m_panam_b, m_panam_a, m_wa_b, m_wa_a, m_wr = 0.0, 0.0, 0.0, 0.0, 0.0, 25.0

    # -------------------------------------------------------------
    # 🏁 EXTRACCIÓN ALINEADA CON 'marcas_referencia' (Con Caché)
    # -------------------------------------------------------------
    if es_preinfantil:
        def get_m_ano_infantil_a(prueba_str):
            try:
                ref_resp = obtener_marcas_referencia_cache(prueba_str, st.session_state.nadador_seleccionado_genero, "Infantil A")
                if ref_resp and ref_resp[0].get("m_ano") is not None:
                    return float(ref_resp[0]["m_ano"])  
            except Exception:
                pass
            return 0.0

        if titulo_grafico.startswith("25 "):
            estilo = titulo_grafico.split(" ")[1]
            ref_50 = get_m_ano_infantil_a(f"50 {estilo}")
            m_ano = ref_50 / 2.0  
            m_wr = m_ano * 0.8 if m_ano > 0 else 15.0 
        elif titulo_grafico == "50 Libre":
            m_ano = get_m_ano_infantil_a("50 Libre")
            m_wr = m_ano * 0.8 if m_ano > 0 else 30.0
        elif titulo_grafico == "100 Combinado":
            m_l = get_m_ano_infantil_a("50 Libre")
            m_e = get_m_ano_infantil_a("50 Espalda")
            m_p = get_m_ano_infantil_a("50 Pecho")
            m_m = get_m_ano_infantil_a("50 Mariposa")
            
            if all(v > 0 for v in [m_l, m_e, m_p, m_m]):
                m_ano = ((m_l + m_e + m_p + m_m) / 2.0) * 1.15
            else:
                m_ano = 0.0
            m_wr = m_ano * 0.8 if m_ano > 0 else 70.0
    else:
        try:
            ref_resp = obtener_marcas_referencia_cache(titulo_grafico, st.session_state.nadador_seleccionado_genero, st.session_state.nadador_seleccionado_categoria)
            if ref_resp:
                ref_data = ref_resp[0]
                m_ano = float(ref_data["m_ano"]) if ref_data["m_ano"] is not None else 0.0
                m_panam_b = float(ref_data["m_panam_b"]) if ref_data["m_panam_b"] is not None else 0.0
                m_panam_a = float(ref_data["m_panam_a"]) if ref_data["m_panam_a"] is not None else 0.0
                m_wa_b = float(ref_data["m_wa_b"]) if ref_data["m_wa_b"] is not None else 0.0
                m_wa_a = float(ref_data["m_wa_a"]) if ref_data["m_wa_a"] is not None else 0.0
                m_wr = float(ref_data["m_wr"]) if ref_data["m_wr"] is not None else 25.0
        except Exception as e:
            st.error(f"Error extrayendo marcas de la categoría: {e}")

    # -------------------------------------------------------------
    # 🚨 MODO SIMULACIÓN Y EXTRACCIÓN HISTÓRICA DE PB (Con Caché y Lógica Centralizada)
    # -------------------------------------------------------------
    spc()
    st.sidebar.subheader("🚨 Simulación de Escenarios")
    simulacion_externa = st.sidebar.checkbox("Activar Modo Simulación Externa", value=False)

    try:
        datos_historicos = obtener_marcas_historicas_cache(titulo_grafico, st.session_state.nadador_seleccionado_id)
            
        if datos_historicos:
            df_procesado = pd.DataFrame(datos_historicos)
            df_procesado = df_procesado.rename(columns={"edad": "Edad", "tiempo": "Tiempo", "nota": "Evento / Fecha"})
            
            # Llama a la función centralizada de formulas_lib_funciones.py
            db_t0, db_T0, db_t_pb, db_T_pb = procesar_mejor_marca_historica(df_procesado)
        else:
            df_procesado = pd.DataFrame(columns=["id", "Edad", "Tiempo", "Evento / Fecha"])
            db_t0, db_T0, db_t_pb, db_T_pb = None, None, None, None
    except Exception:
        df_procesado = pd.DataFrame(columns=["id", "Edad", "Tiempo", "Evento / Fecha"])
        db_t0, db_T0, db_t_pb, db_T_pb = None, None, None, None

    inputs_bloqueados = not simulacion_externa

    val_t0 = db_t0 if (db_t0 is not None) else 10.0
    val_T0 = db_T0 if (db_T0 is not None) else float(round(m_wr * 1.8, 2))
    val_t_pb = db_t_pb if (db_t_pb is not None) else 12.0
    val_T_pb = db_T_pb if (db_T_pb is not None) else float(round(m_wr * 1.3, 2))

    # Guardar en el buzón global para que la pestaña del gráfico las pueda leer
    st.session_state["val_t0"] = val_t0
    st.session_state["val_T0"] = val_T0
    st.session_state["val_t_pb"] = val_t_pb
    st.session_state["val_T_pb"] = val_T_pb

    if es_preinfantil:
        val_T_target = float(round(m_ano, 2)) if m_ano > 0 else 25.0
    else:
        val_T_target = float(round(m_wa_a * 0.99, 2)) if m_wa_a > 0 else float(round(m_wr * 1.08, 2))

    # -------------------------------------------------------------
    # 📐 PARÁMETROS DE LÍMITES Y PB (INDICADORES DE CANDADO 🔓/🔒)
    # -------------------------------------------------------------
    spc()
    if simulacion_externa:
        st.sidebar.subheader("📐 Parámetros de Límites y PB 🔓")
    else:
        st.sidebar.subheader("📐 Parámetros de Límites y PB 🔒")

    # 1. Edad Start (t0)
    t0 = st.sidebar.number_input("1. Edad Start (t0):", min_value=4.0, value=val_t0, step=0.1, disabled=inputs_bloqueados)

    # 2. Tiempo Inicial (T0)
    T0_str = st.sidebar.text_input(
        "2. Tiempo Inicial (T0):", 
        value=formatear_a_minutos(val_T0).replace(" s", ""), 
        disabled=inputs_bloqueados,
        help="Formato mm:ss.00 o ss.00"
    )
    try:
        T0 = float(convertir_string_a_segundos(T0_str))
    except ValueError:
        st.sidebar.error("❌ Formato T0 inválido. Use 'mm:ss.00'")
        T0 = float(val_T0)

    # 3. Edad Peak Proyectado
    t_peak = st.sidebar.number_input("3. Edad Peak Proyectado (t_peak):", min_value=5.0, max_value=30.0, step=1.0, value=23.0)

    # 4. Tiempo Objetivo Peak (T_target)
    T_target_str = st.sidebar.text_input(
        "4. Tiempo Objetivo Peak (T_target):", 
        value=formatear_a_minutos(val_T_target).replace(" s", ""),
        help="Formato mm:ss.00 o ss.00"
    )
    try:
        T_target = float(convertir_string_a_segundos(T_target_str))
    except ValueError:
        st.sidebar.error("❌ Formato T_target inválido. Use 'mm:ss.00'")
        T_target = float(val_T_target)

    # 5. Edad del PB de Control (t_pb)
    t_pb = st.sidebar.number_input("5. Edad del PB de Control (t_pb):", min_value=4.0, value=val_t_pb, step=0.05, disabled=inputs_bloqueados)

    # 6. Tiempo del PB de Control (T_pb)
    T_pb_str = st.sidebar.text_input(
        "6. Tiempo del PB de Control (T_pb):", 
        value=formatear_a_minutos(val_T_pb).replace(" s", ""), 
        disabled=inputs_bloqueados,
        help="Formato mm:ss.00 o ss.00"
    )
    try:
        T_pb = float(convertir_string_a_segundos(T_pb_str))
    except ValueError:
        st.sidebar.error("❌ Formato T_pb inválido. Use 'mm:ss.00'")
        T_pb = float(val_T_pb)

    # 💾 ACTUALIZACIÓN INMEDIATA DEL CACHÉ EN SESSION STATE
    st.session_state["t0_segundos"] = T0
    st.session_state["ttarget_segundos"] = T_target
    st.session_state["tpb_segundos"] = T_pb

    # -------------------------------------------------------------
    # 🔎 CONTROLES DE VISTA CON LÍMITES DINÁMICOS Y COMPLETO
    # -------------------------------------------------------------
    tipo_vista = st.sidebar.selectbox("Enfoque del Gráfico", ["Macro (Historial Completo)", "Micro (Ventana Anual)"])
    if tipo_vista == "Micro (Ventana Anual)":
        limite_inf_abs = float(t0)
        limite_sup_abs = float(t_peak)
        rango_def_min = max(limite_inf_abs, min(float(t_pb), limite_sup_abs))
        rango_def_max = min(rango_def_min + 1.0, limite_sup_abs)
        edad_min_zoom, edad_max_zoom = st.sidebar.slider(
            "🔎 Rango de la Ventana (Edad)", min_value=limite_inf_abs, max_value=limite_sup_abs,
            value=(rango_def_min, rango_def_max), step=0.1, format="%.2f años"
        )
    else:
        edad_min_zoom = 0.0
        edad_max_zoom = 100.0

# ⏱️ CONTENEDOR INYECTADO
    with contenedor_sliders:
        spc()
        st.markdown("**⏱️ Rapidez de Deriva e Intervalo**")
        h = st.slider("Factor ajustable de rapidez de deriva (h):", min_value=0.1, max_value=1.0, value=0.35, step=0.05)
        t_intermedia = st.slider("Consultar Edad Intermedia:", min_value=float(t0), max_value=float(t_peak), value=float(round((t0+t_peak)/2, 1)), step=0.1)

    # Clausula informativa obligatoria para nadadores no colectivos
    if not modo_equipo and st.session_state.rol == "Nadador":
        st.sidebar.markdown("---")
        st.sidebar.caption("📅 *Requerido proyectar cada 3 meses hasta los 18 años para verificar marcas, asistir a campeonatos y optar por becas universitarias nacionales e internacionales.*")

# --- LÓGICA CORREGIDA PARA DF_GLOBAL ---
    df_global = pd.DataFrame() 
    
    if modo_equipo:
        # Si ids_sel está vacío pero tenemos lista_atletas, extraemos los IDs de allí
        ids_para_consulta = ids_sel if ids_sel else [a["id"] for a in lista_atletas]
        
        if ids_para_consulta: # Solo consultamos si tenemos algo que buscar
            df_global = obtener_marcas_equipo_cache(st.session_state.supabase, ids_para_consulta, titulo_grafico)
        else:
            st.warning("No hay atletas detectados con los filtros actuales.")

# Retorno unificado de empaquetado para el script principal
    return {
        "usuario_id": st.session_state.get("nadador_seleccionado_id"),
        "genero": st.session_state.get("nadador_seleccionado_genero", "M"),
        "categoria": st.session_state.get("nadador_seleccionado_categoria", ""),
        "titulo_grafico": titulo_grafico,
        "simulacion_externa": simulacion_externa,
        "modo_equipo": modo_equipo,
        "filtro_genero": filtro_genero,
        "tipo_filtro": tipo_filtro,
        "cat_sel": cat_sel,
        "ids_sel": ids_sel,
        "t0": t0,
        "T0": T0,
        "t_peak": t_peak,
        "T_target": T_target,
        "t_pb": t_pb,
        "T_pb": T_pb,
        "tipo_vista": tipo_vista,
        "edad_min_zoom": edad_min_zoom,
        "edad_max_zoom": edad_max_zoom,
        "factor_h": h,
        "t_intermedia": t_intermedia,
        "df_procesado": df_procesado,
        "df_global_marcas": df_global,
        "m_ano": m_ano,
        "m_panam_b": m_panam_b,
        "m_panam_a": m_panam_a,
        "m_wa_b": m_wa_b,
        "m_wa_a": m_wa_a,
        "m_wr": m_wr
    }
