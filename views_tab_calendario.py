# =============================================================================
# views_tab_calendario.py — v2.0 (Fase 1: refactorización incremental)
# =============================================================================
# CAMBIOS vs v1.0:
#   10a — Consultas a catalogo_competencias migradas a get_competencias().
#   10b — Consultas a usuarios migradas a get_usuarios() cacheada.
#   10c — Consultas a marcas_historicas migradas a get_marcas_historicas_bulk_sin_prueba().
#   10d — Invalidación quirúrgica de competencias tras insert/update.
#   10e — Invalidación quirúrgica de hitos tras insert masivo.
#   10f — Insert masivo de hitos con fallback 1x1 informativo.
#   10g — Eliminada sintaxis `with ... if ... else` por `if` explícito.
#   10h — Encabezado con changelog versionado.
#
# NO TOCADO:
#   - Estructura de sub-tabs
#   - Lógica de elegibilidad internacional
#   - Cálculo de fecha de alerta
#   - Formato de exportación CSV/HTML
#   - key= de los widgets
#
# PENDIENTE FASE 2:
#   [F2-17] Extraer bloque de "Generación de Hitos" a función propia.
#   [F2-18] Mover "estimar_fecha_marca" a formulas_lib_funciones.py.
#   [F2-20] Añadir constraint UNIQUE a historial_hitos (usuario_id, competencia_id).
# =============================================================================
import datetime
import pandas as pd
import streamlit as st

# Importación de funciones core de soporte analítico
from formulas_lib_funciones import (
    calcular_edad_tecnica_al_31_dic,
    calcular_fecha_alerta,
    evaluar_elegibilidad_internacional,
    formatear_a_minutos,
)

# 🚀 IMPORTACIÓN DESDE TU CAPA DE CACHÉ (v2.2)
from conections_supabase_cache import (
    get_competencias,
    get_usuarios,
    get_marcas_historicas_bulk_sin_prueba,
    get_hitos_por_competencia,
    invalidar_cache_competencias,
    invalidar_cache_hitos_por_competencia,
)


def estimar_fecha_marca(fecha_nac_str, edad):
    """
    Calcula la fecha aproximada de la competencia sumando la edad (años)
    a la fecha de nacimiento.

    [F2-18] PENDIENTE: mover a formulas_lib_funciones.py como utilidad.
    """
    if not fecha_nac_str or edad is None:
        return ""
    try:
        if isinstance(fecha_nac_str, str):
            f_nac = datetime.date.fromisoformat(fecha_nac_str)
        else:
            f_nac = fecha_nac_str
        dias = int(float(edad) * 365.25)
        f_marca = f_nac + datetime.timedelta(days=dias)
        return f_marca.strftime("%d/%m/%Y")
    except Exception:
        return ""


def renderizar_tab_calendario():
    """
    Vista general del Calendario de Competencias estructurada en subpestañas.

    Incluye la gestión de eventos, generación de hitos y la herramienta de
    exportación de nóminas con marcas históricas para el Head Coach / Admin.
    """
    supabase = st.session_state.get("supabase")
    rol_usuario = st.session_state.get("rol_real") or st.session_state.get(
        "rol", ""
    )
    id_usuario = st.session_state.get("usuario_id")

    if not supabase:
        st.error("❌ Conexión con el servidor no disponible.")
        return

    es_staff = rol_usuario in ["Head Coach", "Administrador"]

    # [F1-10g] Cambio de `with tab_eventos if es_staff else st.container():`
    # por if/else explícito, más legible y sin ambigüedad.
    if es_staff:
        tab_eventos, tab_inscripciones = st.tabs(
            ["📅 Calendario y Hitos", "📋 Planilla de Inscripción"]
        )
        contexto_eventos = tab_eventos
        contexto_inscripciones = tab_inscripciones
    else:
        contexto_eventos = st.container()
        contexto_inscripciones = None

    # ============================================================
    # SUBPESTAÑA 1: CALENDARIO Y HITOS
    # ============================================================
    with contexto_eventos:
        temporada_actual = datetime.date.today().year
        st.markdown(
            f"**Competencias Programadas - Temporada {temporada_actual}**"
        )

        dict_comps = {}
        # [F1-10a] get_competencias() cacheada (ttl 1800s)
        resp_comp_data = get_competencias(temporada=temporada_actual)

        if resp_comp_data:
            df_comp = pd.DataFrame(resp_comp_data)
            df_comp["fecha_inicio"] = pd.to_datetime(
                df_comp["fecha_inicio"]
            ).dt.strftime("%d-%m-%Y")
            df_comp["fecha_fin"] = pd.to_datetime(
                df_comp["fecha_fin"]
            ).dt.strftime("%d-%m-%Y")
            st.dataframe(
                df_comp[[
                    "nombre_evento",
                    "ente_rector",
                    "categoria_evento",
                    "fecha_inicio",
                    "fecha_fin",
                ]],
                use_container_width=True,
                hide_index=True,
            )
            dict_comps = {
                f"{c['nombre_evento']} ({c['fecha_inicio']})": c
                for c in resp_comp_data
            }
        else:
            st.info(
                "No hay competencias registradas para la temporada"
                f" {temporada_actual}."
            )

        if es_staff:
            st.markdown("---")
            col_add, col_edit = st.columns(2)

            with col_add:
                st.markdown("**➕ Programar Nueva Competencia**")
                with st.form("form_add_comp", clear_on_submit=True):
                    add_temp = st.number_input(
                        "Temporada:", min_value=2024, value=temporada_actual
                    )
                    add_nombre = st.text_input("Nombre del Evento:")
                    add_ente = st.selectbox(
                        "Ente Rector:", ["FEVEDA", "PANAM", "SURAM", "WA"]
                    )
                    add_cat = st.selectbox(
                        "Nivel:", ["Nacional", "Internacional"]
                    )
                    c1, c2 = st.columns(2)
                    add_f_ini = c1.date_input("Inicio:")
                    add_f_fin = c2.date_input("Fin:")

                    if st.form_submit_button("💾 Guardar"):
                        if add_f_fin < add_f_ini:
                            st.error(
                                "La fecha de fin no puede ser anterior a la "
                                "de inicio."
                            )
                        elif not add_nombre:
                            st.error("Nombre obligatorio.")
                        else:
                            supabase.table("catalogo_competencias").insert({
                                "temporada": add_temp,
                                "nombre_evento": add_nombre,
                                "ente_rector": add_ente,
                                "categoria_evento": add_cat,
                                "fecha_inicio": add_f_ini.isoformat(),
                                "fecha_fin": add_f_fin.isoformat(),
                                "creador_id": id_usuario,
                            }).execute()

                            # [F1-10d] Invalidación quirúrgica de competencias
                            invalidar_cache_competencias()

                            st.rerun()

            with col_edit:
                st.markdown("**✏️ Auditar / Posponer**")
                if dict_comps:
                    comp_sel = st.selectbox(
                        "Seleccionar:", list(dict_comps.keys())
                    )
                    datos_c = dict_comps[comp_sel]
                    with st.form("form_edit_comp"):
                        edit_nombre = st.text_input(
                            "Nombre:", value=datos_c["nombre_evento"]
                        )
                        c_i, c_f = st.columns(2)
                        edit_f_ini = c_i.date_input(
                            "Inicio:",
                            value=datetime.date.fromisoformat(
                                datos_c["fecha_inicio"]
                            ),
                        )
                        edit_f_fin = c_f.date_input(
                            "Fin:",
                            value=datetime.date.fromisoformat(
                                datos_c["fecha_fin"]
                            ),
                        )
                        if st.form_submit_button("🔄 Aplicar"):
                            supabase.table("catalogo_competencias").update({
                                "fecha_inicio": edit_f_ini.isoformat(),
                                "fecha_fin": edit_f_fin.isoformat(),
                                "nombre_evento": edit_nombre,
                            }).eq("id", datos_c["id"]).execute()

                            # [F1-10d] Invalidación quirúrgica
                            invalidar_cache_competencias()

                            st.rerun()

            st.markdown("---")
            st.markdown("### 🎯 Generación de Hitos")
            if dict_comps:
                comp_ins = st.selectbox(
                    "Competencia a procesar:",
                    options=list(dict_comps.keys()),
                )
                datos_ins = dict_comps[comp_ins]

                if st.button("🚀 Procesar Nómina"):
                    with st.spinner("Evaluando normativas..."):
                        try:
                            # [F1-10a] get_hitos_por_competencia() cacheada
                            hitos_existentes = get_hitos_por_competencia(
                                datos_ins["id"]
                            )
                            set_ids_existentes = {
                                h["usuario_id"] for h in hitos_existentes
                            }

                            # [F1-10b] get_usuarios() cacheada
                            atletas = get_usuarios(
                                rol="Nadador", estatus="Activo"
                            )

                            contadores = {
                                "elegibles": 0,
                                "ineligibles": 0,
                                "omitidos": 0,
                            }

                            # [F1-10f] Acumulamos hitos para insert masivo
                            nuevos_hitos = []

                            for atleta in atletas:
                                if atleta["id"] in set_ids_existentes:
                                    contadores["omitidos"] += 1
                                    continue

                                edad_t = calcular_edad_tecnica_al_31_dic(
                                    atleta["fecha_nacimiento"],
                                    datos_ins["temporada"],
                                )
                                elegible, motivo = evaluar_elegibilidad_internacional(
                                    edad_t, datos_ins["ente_rector"]
                                )
                                f_alerta = calcular_fecha_alerta(
                                    datos_ins["fecha_inicio"], 15
                                )

                                nuevos_hitos.append({
                                    "usuario_id": atleta["id"],
                                    "competencia_id": datos_ins["id"],
                                    "temporada_auditada": datos_ins["temporada"],
                                    "elegible": elegible,
                                    "motivo_ineligibilidad": (
                                        motivo if not elegible else None
                                    ),
                                    "estado_cumplimiento": "Pendiente",
                                    "fecha_alerta": f_alerta.isoformat(),
                                })

                                contadores[
                                    "elegibles" if elegible else "ineligibles"
                                ] += 1

                            # =========================================================
                            # [F1-10f] INSERCIÓN: masiva con fallback 1x1
                            # =========================================================
                            if not nuevos_hitos:
                                st.info("ℹ️ No hay hitos nuevos para insertar.")
                            else:
                                try:
                                    # Intento rápido: 1 sola query
                                    supabase.table("historial_hitos").insert(
                                        nuevos_hitos
                                    ).execute()

                                    st.success(
                                        f"✅ Proceso completado. "
                                        f"{len(nuevos_hitos)} hitos insertados."
                                    )
                                    st.info(
                                        f"📊 {contadores['elegibles']} elegibles | "
                                        f"{contadores['ineligibles']} ineligibles | "
                                        f"{contadores['omitidos']} ya registrados."
                                    )

                                    # [F1-10e] Invalidación de caché
                                    invalidar_cache_hitos_por_competencia()
                                    st.rerun()

                                except Exception as e_masivo:
                                    # Fallback: insert 1x1 para identificar culpables
                                    st.warning(
                                        f"⚠️ El INSERT masivo falló. "
                                        f"Iniciando diagnóstico individual "
                                        f"para identificar los registros problemáticos..."
                                    )

                                    exitosos = []
                                    fallidos = []

                                    for hito in nuevos_hitos:
                                        try:
                                            supabase.table(
                                                "historial_hitos"
                                            ).insert(hito).execute()
                                            exitosos.append(hito["usuario_id"])
                                        except Exception as e_ind:
                                            fallidos.append({
                                                "usuario_id": hito["usuario_id"],
                                                "error": str(e_ind),
                                            })

                                    # Reporte de resultados del fallback
                                    if exitosos:
                                        st.success(
                                            f"✅ {len(exitosos)} hitos insertados "
                                            f"correctamente en el reintento individual."
                                        )

                                    if fallidos:
                                        st.error(
                                            f"❌ {len(fallidos)} hitos NO pudieron "
                                            f"insertarse. Detalle:"
                                        )
                                        with st.expander(
                                            f"Ver {len(fallidos)} registros fallidos"
                                        ):
                                            for f in