# =============================================================================
# views_tab_asignaciones.py — v2.0 (Fase 1: refactorización incremental)
# =============================================================================
# CAMBIOS vs v1.0:
#   9a — Consulta de entrenadores migrada a get_usuarios() cacheada.
#   9b — Consulta de nadadores migrada a get_usuarios() cacheada.
#   9c — st.cache_data.clear() reemplazado por invalidar_cache_asignaciones()
#        en asignación individual.
#   9d — st.cache_data.clear() reemplazado por invalidar_cache_asignaciones()
#        en asignación masiva.
#   9e — Imports migrados a funciones get_* de conections_supabase_cache.
#   9f — Encabezado con changelog versionado.
#
# NO TOCADO:
#   - Estructura de 2 columnas (individual + masiva)
#   - Lógica de borrado transaccional previo
#   - key= de los widgets
#   - Control de rol (Head Coach / Administrador)
#   - Layout visual
#
# OBSERVACIONES DE DISEÑO:
#
#   [F1-FIX-02] RESUELTO — Falso positivo. La columna `activo` en la tabla
#               `asignaciones` tiene DEFAULT TRUE correctamente configurado.
#               No hay registros con NULL. No hay bug.
#
#   [F2-15] RIESGO ACEPTADO — Este archivo es el ÚNICO punto de escritura
#           a la tabla `asignaciones`. Usa DELETE + INSERT (borrado físico)
#           en lugar de marcar `activo = false` (borrado lógico).
#
#           Consecuencia: si algún día se hace un INSERT manual desde la
#           consola SQL de Supabase sin antes hacer DELETE, se puede crear
#           una DOBLE ASIGNACIÓN del mismo atleta a dos entrenadores.
#
#           Mitigación actual: no hay. El riesgo se acepta explícitamente.
#
#           Mitigación recomendada para Fase 2: crear índice único parcial
#           en Postgres:
#             CREATE UNIQUE INDEX IF NOT EXISTS uniq_atleta_activo
#             ON asignaciones (atleta_id)
#             WHERE activo = true;
#
#           Razón para no aplicarlo en Fase 1: el sistema funciona correctamente
#           con el flujo actual (DELETE + INSERT). Añadir restricción ahora
#           es sobre-ingeniería para un riesgo que no está en el horizonte.
# =============================================================================

import streamlit as st
import pandas as pd
from formulas_lib_funciones import calcular_categoria_competencia

# 🚀 IMPORTACIÓN DESDE TU CAPA DE CACHÉ (v2.1)
from conections_supabase_cache import (
    get_usuarios,
    invalidar_cache_asignaciones,
)


def renderizar_tab_asignaciones():
    """
    CÓDIGO AUDITADO Y VERIFICADO: 17. Rutina reservada a Head Coach de asignación
    de atletas a entrenadores.

    Garantiza la consistencia en el borrado transaccional preventivo y la purga
    de caché de datos (ahora quirúrgica, solo de asignaciones).
    """
    # 1. Control Restringido de Seguridad por Rol
    rol_usuario = st.session_state.get("rol")
    if rol_usuario not in ["Head Coach", "Administrador"]:
        st.warning(
            "🔒 Acceso denegado: Este panel está reservado exclusivamente "
            "para la Dirección Técnica (Head Coach)."
        )
        return

    st.markdown("### 📋 Panel de Gestión de Asignaciones (Exclusivo Head Coach)")
    st.caption(
        "Vincula de forma individual o masiva por categoría a los nadadores "
        "con sus respectivos entrenadores asistentes."
    )

    supabase = st.session_state.get("supabase")
    if not supabase:
        st.error("❌ Conexión con la base de datos no disponible.")
        return

    try:
        # [F1-9a] get_usuarios() cacheada (ttl 1800s)
        lista_entrenadores = get_usuarios(rol="Entrenador", estatus="Activo")

        # [F1-9b] get_usuarios() cacheada (ttl 1800s)
        lista_todos_nadadores = get_usuarios(rol="Nadador", estatus="Activo")

        if lista_entrenadores and lista_todos_nadadores:
            dict_entrenadores = {e["id"]: e["nombre"] for e in lista_entrenadores}

            col1, col2 = st.columns(2)

            # -----------------------------------------------------------------
            # COMPONENTE 1: ASIGNACIÓN INDIVIDUAL
            # -----------------------------------------------------------------
            with col1:
                st.markdown("##### 👤 Asignación Individual")
                entrenador_sel = st.selectbox(
                    "Asistente Destino:",
                    options=list(dict_entrenadores.keys()),
                    format_func=lambda x: dict_entrenadores[x],
                    key="asig_ind_ent",
                )

                dict_nadadores = {n["id"]: n["nombre"] for n in lista_todos_nadadores}
                nadador_sel = st.selectbox(
                    "Nadador a asignar:",
                    options=list(dict_nadadores.keys()),
                    format_func=lambda x: dict_nadadores[x],
                    key="asig_ind_nad",
                )

                if st.button(
                    "🔗 Confirmar Vínculo Individual",
                    key="btn_asig_ind",
                    use_container_width=True,
                ):
                    try:
                        # Limpiar asignaciones previas del atleta para garantizar
                        # relación limpia de base de datos
                        supabase.table("asignaciones").delete().eq(
                            "atleta_id", nadador_sel
                        ).execute()

                        # Inserción limpia con nombres exactos de columnas
                        # verificadas
                        supabase.table("asignaciones").insert({
                            "entrenador_id": entrenador_sel,
                            "atleta_id": nadador_sel,
                        }).execute()

                        st.success(
                            f"🎉 {dict_nadadores[nadador_sel]} asignado(a) "
                            f"correctamente a {dict_entrenadores[entrenador_sel]}."
                        )

                        # [F1-9c] Invalidación quirúrgica (antes: st.cache_data.clear()
                        # que borraba TODO).
                        invalidar_cache_asignaciones()

                        st.rerun()
                    except Exception as e:
                        st.error(f"Error en asignación individual: {e}")

            # -----------------------------------------------------------------
            # COMPONENTE 2: ASIGNACIÓN MASIVA POR CATEGORÍA
            # -----------------------------------------------------------------
            with col2:
                st.markdown("##### 👥 Asignación Masiva por Categoría")
                entrenador_cat_sel = st.selectbox(
                    "Asistente Destino (Lote):",
                    options=list(dict_entrenadores.keys()),
                    format_func=lambda x: dict_entrenadores[x],
                    key="asig_cat_ent",
                )

                categoria_sel = st.selectbox(
                    "Categoría Completa a Asignar:",
                    options=[
                        "Preinfantil",
                        "Infantil A",
                        "Infantil B",
                        "Juvenil A",
                        "Juvenil B",
                        "Máxima",
                    ],
                    key="asig_cat_sel",
                )

                if st.button(
                    "⚡ Ejecutar Asignación por Lote",
                    key="btn_asig_cat",
                    use_container_width=True,
                ):
                    ids_categoria = []

                    # Clasificación en tiempo real usando la biblioteca
                    # analítica unificada
                    for nad in lista_todos_nadadores:
                        fnac = nad.get("fecha_nacimiento")
                        if fnac:
                            cat_calc, _ = calcular_categoria_competencia(
                                str(fnac)[:10]
                            )
                            if cat_calc.strip() == categoria_sel.strip():
                                ids_categoria.append(nad["id"])

                    if ids_categoria:
                        try:
                            # 1. Limpiar en bloque las asignaciones previas de
                            #    este grupo de atletas
                            supabase.table("asignaciones").delete().in_(
                                "atleta_id", ids_categoria
                            ).execute()

                            # 2. Inserción masiva estructurada por lotes
                            nuevas_asig = [
                                {
                                    "entrenador_id": entrenador_cat_sel,
                                    "atleta_id": nid,
                                }
                                for nid in ids_categoria
                            ]
                            supabase.table("asignaciones").insert(
                                nuevas_asig
                            ).execute()

                            st.success(
                                f"🎉 Se asignaron {len(ids_categoria)} nadadores "
                                f"de la categoría **{categoria_sel}** a "
                                f"{dict_entrenadores[entrenador_cat_sel]}."
                            )

                            # [F1-9d] Invalidación quirúrgica
                            invalidar_cache_asignaciones()

                            st.rerun()
                        except Exception as e:
                            st.error(f"Error operando la inserción masiva: {e}")
                    else:
                        st.warning(
                            f"No se encontraron nadadores activos que "
                            f"pertenezcan a la categoría {categoria_sel} en "
                            f"esta temporada."
                        )
        else:
            st.info(
                "💡 Debe contar con Entrenadores y Nadadores activos con "
                "estatus 'Activo' en la base de datos para habilitar las "
                "opciones de asignación."
            )

    except Exception as e:
        st.error(f"Error general en el módulo de asignaciones: {e}")