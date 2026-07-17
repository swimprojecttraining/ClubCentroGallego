import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# Importaciones de tu librería lógica
from formulas_lib_funciones import (
    convertir_string_a_segundos, 
    formatear_a_minutos, 
    calcular_edad_decimal, 
    calcular_categoria_competencia,
    obtener_pruebas_por_categoria  # <--- Traemos tu función limpia
)

# Tu nueva función optimizada "Cero Riesgos"
from connections_supabase_cache import obtener_todo_el_historial_cache

def renderizar_tab_marcas(datos_sidebar=None):
    st.markdown("### ⏱️ Panel de Control Curricular y Marcas Oficiales")
    st.caption("Módulo centralizado para la gestión de marcas oficiales, análisis de récords personales y exportación curricular.")

    ctx_supabase_mar = st.session_state.get("supabase")
    rol_usuario = st.session_state.get("rol")
    id_usuario = st.session_state.get("usuario_id")
    id_atleta_actual = st.session_state.get("nadador_seleccionado_id")

    if not id_atleta_actual:
        st.info("💡 Por favor, selecciona un nadador en la barra lateral para gestionar sus marcas oficiales.")
        return

    # =============================================================================
    # 📊 SELECCIÓN DE PRUEBA (Exactamente después del return, directo al Sidebar)
    # =============================================================================
    spc()  # Tu espaciador nativo
    st.sidebar.subheader("📊 Ajustes por prueba")

    cat_atleta = st.session_state.nadador_seleccionado_categoria
    es_preinfantil = cat_atleta.startswith("Preinfantil") if cat_atleta else False

    # Reducción mágica: la función genera el listado reglamentario
    lista_pruebas = obtener_pruebas_por_categoria(cat_atleta)

    # Tu componente original intacto
    titulo_grafico = st.sidebar.selectbox("Estilo y Distancia:", options=lista_pruebas, index=1)

    if titulo_grafico.startswith("---"):
        st.sidebar.info("👆 Selecciona una distancia específica en el menú superior para ver o editar los datos.")
        st.stop()

    st.session_state["prueba_seleccionada"] = titulo_grafico

    # =============================================================================
    # ⚡ CARGA DESDE TU FUNCIÓN EN connections_supabase_cache.py (Cero Viajes por Red)
    # =============================================================================
    df_marcas_raw = pd.DataFrame()
    if ctx_supabase_mar:
        datos_cacheados = obtener_todo_el_historial_cache(id_atleta_actual)
        if datos_cacheados:
            df_marcas_raw = pd.DataFrame(datos_cacheados)

    # Obtención de metadatos de categoría para las líneas de los gráficos
    cat_nadador, genero_nadador = "Desconocida", "F"
    try:
        atleta_meta = ctx_supabase_mar.table("usuarios").select("fecha_nacimiento, genero").eq("id", id_atleta_actual).execute().data
        if atleta_meta:
            genero_nadador = atleta_meta[0].get("genero", "F")
            cat_nadador, _ = calcular_categoria_competencia(str(atleta_meta[0]["fecha_nacimiento"])[:10])
    except Exception:
        pass

    # Estructura de Subpestañas principales
    subtab_ingreso, subtab_top_tiempos, subtab_evolucion_prueba = st.tabs([
        "📥 1. Ingresar y Gestionar Marcas",
        "🥇 2. Reporte de Mejores Tiempos (Top Histórico)", 
        "📈 3. Buscador Histórico y Evolución Cronológica"
    ])

    # =============================================================================
    # SUBTAB 1: INGRESO Y GESTIÓN (Filtrado local usando 'titulo_grafico')
    # =============================================================================
    with subtab_ingreso:
        col_form, col_tabla_rapida = st.columns([1, 1.2])
        
        with col_form:
            st.markdown(f"**Ingresar Nueva Marca ➔ {titulo_grafico}**")
            with st.form("form_insertar_marca", clear_on_submit=True):
                ins_fecha_evento = st.date_input("Fecha de la Competencia:", value=datetime.date.today())
                ins_tiempo_str = st.text_input("Tiempo Oficial (Formato mm:ss.hh):", placeholder="01:13.34")
                ins_nota = st.text_input("Evento Año - Lugar:")
                
                if st.form_submit_button("💾 Guardar Registro"):
                    if rol_usuario in ["Head Coach", "Entrenador", "Administrador"] or id_usuario == id_atleta_actual:
                        try:
                            ins_tiempo = convertir_string_a_segundos(ins_tiempo_str)
                            fecha_nacimiento_atleta = atleta_meta[0]["fecha_nacimiento"] if atleta_meta else None
                            
                            if not fecha_nacimiento_atleta:
                                st.error("❌ El atleta no posee fecha de nacimiento configurada.")
                            else:
                                edad_calculada = calcular_edad_decimal(fecha_nacimiento_atleta, ins_fecha_evento)
                                nueva_m = {
                                    "prueba": titulo_grafico, 
                                    "edad": float(edad_calculada), 
                                    "tiempo": float(ins_tiempo),
                                    "nota": ins_nota, 
                                    "usuario_id": id_atleta_actual
                                }
                                ctx_supabase_mar.table("marcas_historicas").insert(nueva_m).execute()
                                
                                st.cache_data.clear()
                                st.success(f"¡Marca guardada con éxito!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al procesar: {e}")
                    else:
                        st.error("❌ No tienes autorización para modificar estos registros.")
        
        with col_tabla_rapida:
            st.markdown(f"**Historial de la Prueba: {titulo_grafico}**")
            if not df_marcas_raw.empty:
                # Filtrado instantáneo en memoria RAM
                df_filtrado_local = df_marcas_raw[df_marcas_raw["prueba"] == titulo_grafico].copy()
                
                if not df_filtrado_local.empty:
                    df_visual = df_filtrado_local.copy()
                    df_visual["tiempo"] = df_visual["tiempo"].apply(lambda x: formatear_a_minutos(float(x)))
                    
                    if rol_usuario in ["Head Coach", "Entrenador", "Administrador"]:
                        opciones_del = {
                            f"Edad: {round(r['edad'],2)} | T: {r['tiempo']} | {r['nota']}": r['id'] 
                            for _, r in df_filtrado_local.iterrows()
                        }
                        sel_del = st.selectbox("Eliminar Registro Histórico:", options=list(opciones_del.keys()))
                        if st.button("🗑️ Eliminar Fila Seleccionada"):
                            ctx_supabase_mar.table("marcas_historicas").delete().eq("id", int(opciones_del[sel_del])).execute()
                            st.cache_data.clear()
                            st.rerun()
                    
                    st.dataframe(df_visual[["edad", "tiempo", "nota"]], use_container_width=True, hide_index=True)
                else:
                    st.info(f"ℹ️ El atleta no posee marcas registradas en {titulo_grafico}.")
            else:
                st.info("💡 Base de datos vacía para este atleta.")

    # =============================================================================
    # SUBTAB 2: REPORTES DE MEJORES TIEMPOS
    # =============================================================================
    with subtab_top_tiempos:
        st.markdown("#### 🥇 Récords Personales Absolutos (Personal Best)")
        if not df_marcas_raw.empty:
            idx_mejores = df_marcas_raw.groupby('prueba')['tiempo'].idxmin()
            df_top = df_marcas_raw.loc[idx_mejores].copy().sort_values("prueba").reset_index(drop=True)
            
            df_tabla_top = pd.DataFrame({
                "Prueba": df_top["prueba"],
                "Tiempo Oficial": df_top["tiempo"].apply(lambda x: formatear_a_minutos(float(x))),
                "Edad Crono": df_top["edad"].round(2),
                "Competición": df_top["nota"]
            })
            st.dataframe(df_tabla_top, use_container_width=True, hide_index=True)
        else:
            st.info("No hay marcas disponibles.")

    # =============================================================================
    # SUBTAB 3: GRÁFICO DE EVOLUCIÓN
    # =============================================================================
    with subtab_evolucion_prueba:
        st.markdown("#### 📈 Buscador Histórico Dinámico y Líneas de Campeonato")
        if not df_marcas_raw.empty:
            lista_pruebas_existentes = sorted(df_marcas_raw["prueba"].unique().tolist())
            idx_defecto = lista_pruebas_existentes.index(titulo_grafico) if titulo_grafico in lista_pruebas_existentes else 0
                
            p_sel = st.selectbox("Seleccione la Prueba a Graficar:", options=lista_pruebas_existentes, index=idx_defecto, key="sb_evolucion_analisis")
            df_ev = df_marcas_raw[df_marcas_raw["prueba"] == p_sel].sort_values("edad").reset_index(drop=True)
            
            if not df_ev.empty:
                fig_mar, ax = plt.subplots(figsize=(8.5, 3.5))
                ax.plot(df_ev["edad"], df_ev["tiempo"], marker="o", color="#3498db", linewidth=1.8, label="Progreso")
                
                m_minima = None
                try:
                    ref_db = ctx_supabase_mar.table("marcas_referencia").select("m_ano").eq("prueba", p_sel).eq("categoria", cat_nadador).eq("genero", genero_nadador).execute().data
                    if ref_db and ref_db[0].get("m_ano"):
                        m_minima = float(ref_db[0]["m_ano"])
                except Exception:
                    pass
                
                if m_minima:
                    ax.axhline(m_minima, color="#b58900", linestyle=":", linewidth=1.5, label=f"Mínima {cat_nadador}")
                    ax.set_ylim(bottom=min(df_ev["tiempo"].min(), m_minima) * 0.96)
                else:
                    ax.set_ylim(bottom=df_ev["tiempo"].min() * 0.96)
                
                ax.set_ylim(top=df_ev["tiempo"].max() * 1.04)
                ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: formatear_a_minutos(x)))
                ax.set_xlabel("Edad del Nadador (Años)", fontsize=8)
                ax.set_ylabel("Tiempo de Carrera", fontsize=8)
                ax.grid(True, linestyle=":", alpha=0.4)
                ax.legend(fontsize=7)
                st.pyplot(fig_mar)
                
                df_tabla_ev = pd.DataFrame({
                    "Edad": df_ev["edad"].round(2),
                    "Tiempo": df_ev["tiempo"].apply(lambda x: formatear_a_minutos(x)),
                    "Nota": df_ev["nota"]
                })
                st.dataframe(df_tabla_ev, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos históricos para graficar.")
