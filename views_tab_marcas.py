# =============================================================================
# views_tab_marcas.py — v2.0 (Fase 1: refactorización incremental)
# =============================================================================
# CAMBIOS vs v1.0:
#   7a — Imports migrados a funciones get_* (con wrappers de compatibilidad).
#   7b — Reemplazo de st.cache_data.clear() por invalidar_cache_marcas().
#        Antes: cada insert/delete borraba TODA la caché → efecto estampida.
#        Ahora: solo se invalida lo relacionado con marcas.
#   7c — Consulta a `usuarios` con get_usuario_por_id() (ya cacheada).
#   7d — Consulta a `marcas_referencia` con get_marcas_referencia() (ya cacheada
#        globalmente, sin caché manual duplicada en session_state).
#   7e — plt.close(fig_mar) en lugar de plt.close('all') (no cierra figuras
#        ajenas de otras pestañas que puedan estar abiertas).
#   7f — Añadido filtro por usuario_id en las operaciones de marcas (defensa).
#
# NO TOCADO:
#   - @st.fragment en renderizar_tabs_aisladas
#   - Estructura de tabs y sub-tabs
#   - key= de los widgets
#   - Layout visual
#   - Lógica de cálculo de edad decimal
#
# PENDIENTE FASE 2:
#   [F2-12] Extraer el formulario de inserción a un componente reutilizable.
# =============================================================================
import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# Importación de tu librería unificada real
from formulas_lib_funciones import (
    convertir_string_a_segundos,
    formatear_a_minutos,
    calcular_edad_decimal,
    calcular_categoria_competencia,
    obtener_pruebas_por_categoria,
)

# 🚀 IMPORTACIÓN DESDE TU CAPA DE CACHÉ (v2.0)
from conections_supabase_cache import (
    get_marcas_historicas,
    get_usuario_por_id,
    get_marcas_referencia,
    invalidar_cache_marcas,
)


# =============================================================================
# EL FRAGMENTO: Todo lo que está aquí adentro se ejecuta de forma aislada
# =============================================================================
@st.fragment
def renderizar_tabs_aisladas(
    id_atleta_actual,
    cat_nadador,
    genero_nadador,
    ctx_supabase_mar,
    rol_usuario,
    id_usuario,
):
    # Carga ultra rápida desde la función caché dedicada
    df_marcas_raw = pd.DataFrame()
    if ctx_supabase_mar:
        datos_cacheados = get_marcas_historicas(id_atleta_actual)
        if datos_cacheados:
            df_marcas_raw = pd.DataFrame(datos_cacheados)

    subtab_ingreso, subtab_top_tiempos, subtab_evolucion_prueba = st.tabs([
        "📥 1. Ingresar y Gestionar Marcas",
        "🥇 2. Reporte de Mejores Tiempos (Top Histórico)",
        "📈 3. Buscador Histórico y Evolución Cronológica",
    ])

    # --- SUBTAB 1: INGRESO Y GESTIÓN ---
    with subtab_ingreso:
        lista_pruebas_restringida = obtener_pruebas_por_categoria(cat_nadador)

        prueba_local_activa = st.selectbox(
            f"🏊‍♂️ Seleccione la Prueba para {cat_nadador}:",
            options=lista_pruebas_restringida,
            index=1 if len(lista_pruebas_restringida) > 1 else 0,
            key="sb_prueba_local_ingreso",
        )

        st.markdown("---")

        if prueba_local_activa.startswith("---"):
            st.warning(
                "👆 Selecciona una distancia o estilo real de la lista "
                "(evita marcar los títulos de sección)."
            )
        else:
            col_form, col_tabla_rapida = st.columns([1, 1.2])

            with col_form:
                st.markdown(f"**Ingresar Nueva Marca ➔ {prueba_local_activa}**")
                with st.form("form_insertar_marca", clear_on_submit=True):
                    ins_fecha_evento = st.date_input(
                        "Fecha de la Competencia:", value=datetime.date.today()
                    )
                    ins_tiempo_str = st.text_input(
                        "Tiempo Oficial (Formato mm:ss.hh):",
                        placeholder="01:13.34",
                    )
                    ins_nota = st.text_input("Evento Año - Lugar:")

                    if st.form_submit_button("💾 Guardar Registro"):
                        if (
                            rol_usuario in ["Head Coach", "Entrenador", "Administrador"]
                            or id_usuario == id_atleta_actual
                        ):
                            try:
                                ins_tiempo = convertir_string_a_segundos(ins_tiempo_str)

                                # [F1-7c] get_usuario_por_id ya está cacheado (ttl 1800s)
                                atleta_info = get_usuario_por_id(id_atleta_actual)
                                fecha_nacimiento_atleta = (
                                    atleta_info.get("fecha_nacimiento")
                                    if atleta_info
                                    else None
                                )

                                if not fecha_nacimiento_atleta:
                                    st.error(
                                        "❌ El atleta no posee fecha de nacimiento configurada."
                                    )
                                else:
                                    edad_calculada = calcular_edad_decimal(
                                        fecha_nacimiento_atleta, ins_fecha_evento
                                    )
                                    nueva_m = {
                                        "prueba": prueba_local_activa,
                                        "edad": float(edad_calculada),
                                        "tiempo": float(ins_tiempo),
                                        "nota": ins_nota,
                                        "usuario_id": id_atleta_actual,
                                    }
                                    ctx_supabase_mar.table(
                                        "marcas_historicas"
                                    ).insert(nueva_m).execute()

                                    # [F1-7b] Invalidación quirúrgica en lugar de
                                    # st.cache_data.clear() que borraba todo.
                                    invalidar_cache_marcas()

                                    st.success(
                                        f"¡Marca guardada con éxito en {prueba_local_activa}!"
                                    )
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error al procesar: {e}")
                        else:
                            st.error(
                                "❌ No posees los permisos requeridos para "
                                "modificar este registro."
                            )

            with col_tabla_rapida:
                st.markdown(f"**Historial de la Prueba: {prueba_local_activa}**")

                if not df_marcas_raw.empty:
                    df_filtrado_local = df_marcas_raw[
                        df_marcas_raw["prueba"] == prueba_local_activa
                    ].copy()

                    if not df_filtrado_local.empty:
                        df_visual = df_filtrado_local.copy()
                        df_visual["tiempo"] = df_visual["tiempo"].apply(
                            lambda x: formatear_a_minutos(float(x))
                        )

                        if rol_usuario in [
                            "Head Coach",
                            "Entrenador",
                            "Administrador",
                        ]:
                            opciones_del = {
                                f"Edad: {round(r['edad'],2)} | "
                                f"T: {r['tiempo']} | {r['nota']}": r["id"]
                                for _, r in df_filtrado_local.iterrows()
                            }
                            sel_del = st.selectbox(
                                "Eliminar Registro Histórico:",
                                options=list(opciones_del.keys()),
                            )
                            if st.button("🗑️ Eliminar Fila Seleccionada"):
                                ctx_supabase_mar.table(
                                    "marcas_historicas"
                                ).delete().eq(
                                    "id", int(opciones_del[sel_del])
                                ).execute()

                                # [F1-7b] Invalidación quirúrgica
                                invalidar_cache_marcas()

                                st.rerun()

                        st.dataframe(
                            df_visual[["edad", "tiempo", "nota"]],
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.info(
                            f"ℹ️ El atleta no posee marcas registradas en "
                            f"{prueba_local_activa}."
                        )
                else:
                    st.info("💡 Base de datos vacía para este atleta.")

    # --- SUBTABS 2 Y 3: ANÁLISIS ---
    if not df_marcas_raw.empty:
        with subtab_top_tiempos:
            st.markdown("#### 🥇 Récords Personales Absolutos (Personal Best)")
            idx_mejores = df_marcas_raw.groupby("prueba")["tiempo"].idxmin()
            df_top = (
                df_marcas_raw.loc[idx_mejores]
                .copy()
                .sort_values("prueba")
                .reset_index(drop=True)
            )

            df_tabla_top = pd.DataFrame({
                "Prueba": df_top["prueba"],
                "Tiempo Oficial": df_top["tiempo"].apply(
                    lambda x: formatear_a_minutos(float(x))
                ),
                "Edad Crono": df_top["edad"].round(2),
                "Competición": df_top["nota"],
            })
            st.write(
                df_tabla_top.to_html(index=False, classes="tabla-estilizada"),
                unsafe_allow_html=True,
            )

        with subtab_evolucion_prueba:
            st.markdown("#### 📈 Buscador Histórico Dinámico y Líneas de Campeonato")
            st.caption(
                f"🎯 Categoría: **{cat_nadador}** | Género: **{genero_nadador}**"
            )

            lista_pruebas_existentes = sorted(
                df_marcas_raw["prueba"].unique().tolist()
            )
            p_sel = st.selectbox(
                "Seleccione la Prueba a Graficar:",
                options=lista_pruebas_existentes,
                key="sb_evolucion_analisis",
            )

            df_ev = (
                df_marcas_raw[df_marcas_raw["prueba"] == p_sel]
                .sort_values("edad")
                .reset_index(drop=True)
            )

            if not df_ev.empty:
                # [F1-7e] Ya no se cierra TODO con plt.close('all'), que podía
                # cerrar figuras de otras pestañas abiertas simultáneamente.
                fig_mar, ax = plt.subplots(figsize=(8.5, 3.5))
                ax.plot(
                    df_ev["edad"],
                    df_ev["tiempo"],
                    marker="o",
                    color="#3498db",
                    linewidth=1.8,
                    label="Progreso",
                )

                # [F1-7d] Usamos get_marcas_referencia() cacheada globalmente.
                # Ya no hace falta el caché manual con session_state[f"ref_..."].
                m_minima = None
                try:
                    ref_db = get_marcas_referencia(
                        p_sel, genero_nadador, cat_nadador
                    )
                    if ref_db and ref_db[0].get("m_ano"):
                        m_minima = float(ref_db[0]["m_ano"])
                except Exception:
                    pass

                if m_minima:
                    ax.axhline(
                        m_minima,
                        color="#b58900",
                        linestyle=":",
                        linewidth=1.5,
                        label=f"Mínima {cat_nadador}",
                    )
                    ax.set_ylim(
                        bottom=min(df_ev["tiempo"].min(), m_minima) * 0.96
                    )
                else:
                    ax.set_ylim(bottom=df_ev["tiempo"].min() * 0.96)

                ax.set_ylim(top=df_ev["tiempo"].max() * 1.04)
                ax.yaxis.set_major_formatter(
                    FuncFormatter(lambda x, pos: formatear_a_minutos(x))
                )
                ax.set_xlabel("Edad del Nadador (Años)", fontsize=8)
                ax.set_ylabel("Tiempo de Carrera", fontsize=8)
                ax.grid(True, linestyle=":", alpha=0.4)
                ax.legend(fontsize=7)

                st.pyplot(fig_mar)
                plt.close(fig_mar)

                df_tabla_ev = pd.DataFrame({
                    "Edad": df_ev["edad"].round(2),
                    "Prueba": df_ev["prueba"],
                    "Tiempo": df_ev["tiempo"].apply(
                        lambda x: formatear_a_minutos(x)
                    ),
                    "Nota": df_ev["nota"],
                })
                st.write(
                    df_tabla_ev.to_html(index=False, classes="tabla-estilizada"),
                    unsafe_allow_html=True,
                )


# =============================================================================
# FUNCIÓN PRINCIPAL: Punto de entrada del módulo
# =============================================================================
def renderizar_tab_marcas(datos_sidebar=None):
    st.markdown("### ⏱️ Panel de Control Curricular y Marcas Oficiales")
    st.caption(
        "Módulo centralizado para la gestión de marcas oficiales, análisis "
        "de récords personales y exportación curricular."
    )

    ctx_supabase_mar = st.session_state.get("supabase")
    rol_usuario = st.session_state.get("rol")
    id_usuario = st.session_state.get("usuario_id")
    id_atleta_actual = st.session_state.get("nadador_seleccionado_id")

    if not id_atleta_actual:
        st.info(
            "💡 Por favor, selecciona un nadador en la barra lateral para "
            "gestionar sus marcas oficiales."
        )
        return

    # Extraemos metadatos una sola vez fuera del fragmento para evitar reprocesos
    cat_nadador, genero_nadador = "Desconocida", "F"

    # [F1-7c] Reemplazamos la consulta manual por get_usuario_por_id() que ya
    # está cacheada globalmente (ttl 1800s). Ya no hace falta la caché manual
    # con session_state[f"meta_atleta_{id}"].
    atleta_meta = get_usuario_por_id(id_atleta_actual)

    if atleta_meta:
        genero_nadador = atleta_meta.get("genero", "F")
        fecha_nac = atleta_meta.get("fecha_nacimiento")
        if fecha_nac:
            cat_nadador, _ = calcular_categoria_competencia(str(fecha_nac)[:10])

    # Ejecutamos toda la lógica visual pesada dentro del entorno aislado
    renderizar_tabs_aisladas(
        id_atleta_actual,
        cat_nadador,
        genero_nadador,
        ctx_supabase_mar,
        rol_usuario,
        id_usuario,
    )