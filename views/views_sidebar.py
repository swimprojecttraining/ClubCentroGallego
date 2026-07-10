import streamlit as st
import pandas as pd
import datetime

# 📦 IMPORTACIÓN DESDE TU LIBRERÍA REAL DE FUNCIONES
from formulas_lib_funciones import (
    calcular_categoria_competencia,
    formatear_a_minutos,
    convertir_string_a_segundos
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
        
    supabase_local = st.session_state.supabase

    # -------------------------------------------------------------
    # CONTROL DE SESIÓN GENERAL
    # -------------------------------------------------------------
    st.sidebar.markdown(f"**Usuario:** {st.session_state.nombre_nadador}  \n**Nivel:** `{st.session_state.rol}`")
    if st.sidebar.button("🚪 Salir del Sistema"):
        st.session_state.autenticado = False
        st.rerun()

    # 🔄 BOTÓN DE ACTUALIZACIÓN CON RESGUARDO DE CONEXIÓN (NOMBRE INTUITIVO)
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
    # 🎯 PANEL DE NAVEGACIÓN DE ATLETAS (Filtros por Rol)
    # -------------------------------------------------------------
    if st.session_state.rol in ["Head Coach", "Entrenador", "Administrador"]:
        spc()
        st.sidebar.subheader("🎯 Panel de Navegación de Atletas")
        try:
            if st.session_state.rol == "Entrenador":
                # Consulta filtrada por la tabla intermedia 'asignaciones'
                resp_asig = supabase_local.table("asignaciones").select("atleta_id").eq("entrenador_id", st.session_state.usuario_id).eq("activo", True).execute()
                ids_asignados = [reg["atleta_id"] for reg in resp_asig.data] if resp_asig.data else []
                
                if ids_asignados:
                    resp_atletas = supabase_local.table("usuarios").select("id, nombre, genero, fecha_nacimiento").eq("rol", "Nadador").eq("estatus", "Activo").in_("id", ids_asignados).execute()
                else:
                    resp_atletas = None  # No tiene nadadores asignados activos
            else:
                # Head Coach y Administrador tienen acceso global
                resp_atletas = supabase_local.table("usuarios").select("id, nombre, genero, fecha_nacimiento").eq("rol", "Nadador").eq("estatus", "Activo").execute()
            
            if resp_atletas and resp_atletas.data:
                df_atl = pd.DataFrame(resp_atletas.data)
                dict_atletas = dict(zip(df_atl["id"], df_atl["nombre"]))
                
                sel_id = st.sidebar.selectbox("Monitorear Nadador:", options=list(dict_atletas.keys()), format_func=lambda x: dict_atletas[x])
                atleta_row = df_atl[df_atl["id"] == sel_id].iloc[0]
                
                st.session_state.nadador_seleccionado_id = int(atleta_row["id"])
                st.session_state.nadador_seleccionado_nombre = atleta_row["nombre"]
                # 🎯 CORRECCIÓN GÉNERO: Evaluamos de forma segura si viene como código corto o completo
                gen_raw = atleta_row.get("genero", "M")
                if gen_raw in ["Masculino", "M"]:
                    st.session_state.nadador_seleccionado_genero = "M"
                else:
                    st.session_state.nadador_seleccionado_genero = "F"
                # 🎯 CORRECCIÓN CATEGORÍA: Consumimos la categoría precalculada de la fila
                st.session_state.nadador_seleccionado_categoria = atleta_row["categoria"]
                # Guardamos la edad técnica en el estado de la sesión
                st.session_state["nadador_seleccionado_edad_tecnica"] = atleta_row["edad"]
                
            else:
                st.sidebar.warning("⚠️ No tienes nadadores asignados en este momento.")
                st.session_state.nadador_seleccionado_id = None
        except Exception as e:
            st.error(f"Error cargando nómina de atletas filtrada: {e}")
        else:
            st.session_state.nadador_seleccionado_id = st.session_state.get("usuario_id")
            st.session_state.nadador_seleccionado_nombre = st.session_state.get("nombre_nadador", "Atleta")
            st.session_state.nadador_seleccionado_genero = st.session_state.get("genero", "F")
            
            # Extraemos su fecha de nacimiento del login para corregir el "Error Formato" heredado
            fecha_nac_login = st.session_state.get("fecha_nacimiento")
            
            if fecha_nac_login:
                # Purgamos cualquier residuo de horas antes de calcular
                fecha_limpia = str(fecha_nac_login).strip()[:10].replace("/", "-")
                cat_real, edad_real = calcular_categoria_competencia(fecha_limpia)
                st.session_state.nadador_seleccionado_categoria = cat_real
                st.session_state["nadador_seleccionado_edad_tecnica"] = edad_real
            else:
                # Respaldo si no hay fecha en el estado de la sesión
                st.session_state.nadador_seleccionado_categoria = st.session_state.get("categoria_atleta", "Infantil A")

    # Variables colectivas inicializadas exactamente igual al modelo original
    modo_equipo = False
    tipo_filtro = "Todos los Atletas"
    filtro_genero = "Todos"
    cat_sel = None
    ids_sel = []

    # -------------------------------------------------------------
    # 👥 ANÁLISIS COLECTIVO
    # -------------------------------------------------------------
    if st.session_state.rol in ["Head Coach", "Entrenador", "Administrador"]:
        spc()
        st.sidebar.subheader("👥 Análisis Colectivo")
        modo_equipo = st.sidebar.checkbox("Activar Comparativa de Equipo", value=False)
        
        if modo_equipo:
            spc()
            st.sidebar.subheader("🔍 Filtros de Segmentación de Equipo")
            filtro_genero = st.sidebar.radio("Segmentar por Género:", options=["Todos", "Femenino (F)", "Masculino (M)"])
            tipo_filtro = st.sidebar.radio("Segmentar adicionalmente por:", options=["Todos los Atletas", "Categoría Etaria", "Atletas Específicos"])
            
            try:
                resp_preload = supabase_local.table("usuarios").select("id, nombre, fecha_nacimiento, genero").eq("rol", "Nadador").eq("estatus", "Activo").execute()
                atletas_preload = resp_preload.data if resp_preload.data else []
                
                if filtro_genero == "Femenino (F)":
                    atletas_preload = [a for a in atletas_preload if a["genero"] == "F"]
                elif filtro_genero == "Masculino (M)":
                    atletas_preload = [a for a in atletas_preload if a["genero"] == "M"]

                if tipo_filtro == "Categoría Etaria" and atletas_preload:
                    categorias_disponibles = sorted(list(set([calcular_categoria_competencia(a["fecha_nacimiento"])[0] for a in atletas_preload])))
                    if categorias_disponibles:
                        cat_sel = st.sidebar.selectbox("Seleccione la categoría:", options=categorias_disponibles)
                        
                elif tipo_filtro == "Atletas Específicos" and atletas_preload:
                    dict_nom = {a["id"]: a["nombre"] for a in atletas_preload}
                    if dict_nom:
                        ids_sel = st.sidebar.multiselect("Seleccione nadadores:", options=list(dict_nom.keys()), format_func=lambda x: dict_nom[x])
            except Exception as e:
                st.sidebar.error("Error cargando los filtros secundarios.")

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
    # 🏁 EXTRACCIÓN ALINEADA CON 'marcas_referencia' (Tipos Numeric)
    # -------------------------------------------------------------
    if es_preinfantil:
        def get_m_ano_infantil_a(prueba_str):
            try:
                resp = supabase_local.table("marcas_referencia").select("m_ano")\
                    .eq("prueba", prueba_str)\
                    .eq("genero", st.session_state.nadador_seleccionado_genero)\
                    .eq("categoria", "Infantil A").execute()
                if resp.data and resp.data[0].get("m_ano") is not None:
                    return float(resp.data[0]["m_ano"])  # Cast de numeric a float seguro
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
            ref_resp = supabase_local.table("marcas_referencia").select("m_ano, m_panam_b, m_panam_a, m_wa_b, m_wa_a, m_wr")\
                .eq("prueba", titulo_grafico)\
                .eq("genero", st.session_state.nadador_seleccionado_genero)\
                .eq("categoria", st.session_state.nadador_seleccionado_categoria).execute()
            if ref_resp.data:
                ref_data = ref_resp.data[0]
                m_ano = float(ref_data["m_ano"]) if ref_data["m_ano"] is not None else 0.0
                m_panam_b = float(ref_data["m_panam_b"]) if ref_data["m_panam_b"] is not None else 0.0
                m_panam_a = float(ref_data["m_panam_a"]) if ref_data["m_panam_a"] is not None else 0.0
                m_wa_b = float(ref_data["m_wa_b"]) if ref_data["m_wa_b"] is not None else 0.0
                m_wa_a = float(ref_data["m_wa_a"]) if ref_data["m_wa_a"] is not None else 0.0
                m_wr = float(ref_data["m_wr"]) if ref_data["m_wr"] is not None else 25.0
        except Exception as e:
            st.error(f"Error extrayendo marcas de la categoría: {e}")

    # -------------------------------------------------------------
    # 🚨 MODO SIMULACIÓN Y EXTRACCIÓN HISTÓRICA DE PB
    # -------------------------------------------------------------
    spc()
    st.sidebar.subheader("🚨 Simulación de Escenarios")
    simulacion_externa = st.sidebar.checkbox("Activar Modo Simulación Externa", value=False)

    try:
        response = supabase_local.table("marcas_historicas") \
            .select("id, edad, tiempo, nota") \
            .eq("prueba", titulo_grafico) \
            .eq("usuario_id", st.session_state.nadador_seleccionado_id) \
            .order("edad", desc=False).execute() 
            
        if response.data:
            df_procesado = pd.DataFrame(response.data)
            df_procesado = df_procesado.rename(columns={"edad": "Edad", "tiempo": "Tiempo", "nota": "Evento / Fecha"})
            
            df_procesado["Edad"] = pd.to_numeric(df_procesado["Edad"], errors='coerce')
            df_procesado["Tiempo"] = pd.to_numeric(df_procesado["Tiempo"], errors='coerce')
            df_procesado = df_procesado.dropna(subset=["Edad", "Tiempo"]).sort_values("Edad").reset_index(drop=True)
            
            db_t0 = float(df_procesado.iloc[0]["Edad"])
            db_T0 = float(df_procesado.iloc[0]["Tiempo"])
            n_registros = len(df_procesado)
            
            if n_registros == 1:
                db_t_pb, db_T_pb = db_t0, db_T0
            elif n_registros == 2:
                if float(df_procesado.iloc[-1]["Tiempo"]) <= float(df_procesado.iloc[-2]["Tiempo"]):
                    db_t_pb, db_T_pb = float(df_procesado.iloc[-1]["Edad"]), float(df_procesado.iloc[-1]["Tiempo"])
                else:
                    db_t_pb, db_T_pb = float(df_procesado.iloc[-2]["Edad"]), float(df_procesado.iloc[-2]["Tiempo"])
            else:
                indice_min_tiempo = df_procesado["Tiempo"].idxmin()
                posicion_desde_el_final = (n_registros - 1) - indice_min_tiempo
                
                if posicion_desde_el_final >= 2:
                    db_t_pb, db_T_pb = float(df_procesado.iloc[-1]["Edad"]), float(df_procesado.iloc[-1]["Tiempo"])
                else:
                    t_ultima, t_penultima = float(df_procesado.iloc[-1]["Tiempo"]), float(df_procesado.iloc[-2]["Tiempo"])
                    if t_ultima <= t_penultima:
                        db_t_pb, db_T_pb = float(df_procesado.iloc[-1]["Edad"]), t_ultima
                    else:
                        db_t_pb, db_T_pb = float(df_procesado.iloc[-2]["Edad"]), t_penultima
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

    # ⏱️ CONTENEDOR INYECTADO (Aparece visualmente arriba de los parámetros)
    with contenedor_sliders:
        spc()
        st.markdown("**⏱️ Rapidez de Deriva e Intervalo**")
        h = st.slider("Factor ajustable de rapidez de deriva (h):", min_value=0.1, max_value=1.0, value=0.35, step=0.05)
        t_intermedia = st.slider("Consultar Edad Intermedia:", min_value=float(t0), max_value=float(t_peak), value=float(round((t0+t_peak)/2, 1)), step=0.1)

    # Clausula informativa obligatoria para nadadores no colectivos
    if not modo_equipo and st.session_state.rol == "Nadador":
        st.sidebar.markdown("---")
        st.sidebar.caption("📅 *Requerido proyectar cada 3 meses hasta los 18 años para verificar marcas, asistir a campeonatos y optar por becas universitarias nacionales e internacionales.*")

    # Retorno unificado de empaquetado para el script principal
    return {
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
        "df_procesado": df_procesado
    }
