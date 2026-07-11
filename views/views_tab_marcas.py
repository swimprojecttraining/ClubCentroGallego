import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# Importación auditada de tu librería unificada real de funciones
from formulas_lib_funciones import (
    convertir_string_a_segundos, 
    formatear_a_minutos, 
    calcular_edad_decimal, 
    calcular_categoria_competencia
)

def renderizar_tab_marcas(datos_sidebar=None):
    """
    CÓDIGO AUDITADO: 14. Rutina de captura de marcas e historial curricular.
    Blindado contra KeyErrors y firmas de FuncFormatter en Matplotlib.
    """
    st.markdown("### ⏱️ Panel de Control Curricular y Marcas Oficiales")
    st.caption("Módulo centralizado para la gestión de marcas oficiales, análisis de récords personales y exportación curricular.")

    ctx_supabase_mar = st.session_state.get("supabase")
    rol_usuario = st.session_state.get("rol")
    id_usuario = st.session_state.get("usuario_id")
    id_atleta_actual = st.session_state.get("nadador_seleccionado_id")
    prueba_activa = st.session_state.get("prueba_activa_seleccionada", "50m Libre")

    if not id_atleta_actual:
        st.info("💡 Por favor, selecciona un nadador en la barra lateral para gestionar sus marcas oficiales.")
        return

    subtab_ingreso, subtab_top_tiempos, subtab_evolucion_prueba = st.tabs([
        "📥 1. Ingresar y Gestionar Marcas",
        "🥇 2. Reporte de Mejores Tiempos (Top Histórico)", 
        "📈 3. Buscador Histórico y Evolución Cronológica"
    ])

    df_marcas_raw = pd.DataFrame()

    if ctx_supabase_mar:
        try:
            res_inicial = ctx_supabase_mar.table("marcas_historicas").select("*").eq("usuario_id", id_atleta_actual).execute()
            if res_inicial.data:
                df_marcas_raw = pd.DataFrame(res_inicial.data) # Estructura nativa en minúsculas
        except Exception as e:
            st.error(f"Error de sincronización con base de datos: {e}")

    # SUBTAB 1: INGRESO Y GESTIÓN
    with subtab_ingreso:
        col_form, col_tabla_rapida = st.columns([1, 1.2])
        
        with col_form:
            st.markdown("**Ingresar Nueva Marca**")
            with st.form("form_insertar_marca", clear_on_submit=True):
                ins_fecha_evento = st.date_input("Fecha de la Competencia:", value=datetime.date.today())
                ins_tiempo_str = st.text_input("Tiempo Oficial (Formato mm:ss.hh):", placeholder="01:13.34")
                ins_nota = st.text_input("Evento Año - Lugar:")
                
                if st.form_submit_button("💾 Guardar Registro"):
                    try:
                        ins_tiempo = convertir_string_a_segundos(ins_tiempo_str)
                        atleta_query = ctx_supabase_mar.table("usuarios").select("fecha_nacimiento").eq("id", id_atleta_actual).execute()
                        fecha_nacimiento_atleta = atleta_query.data[0]["fecha_nacimiento"] if atleta_query.data else None
                        
                        if not fecha_nacimiento_atleta:
                            st.error("❌ El atleta no posee fecha de nacimiento configurada.")
                        else:
                            edad_calculada = calcular_edad_decimal(fecha_nacimiento_atleta, ins_fecha_evento)
                            nueva_m = {
                                "prueba": prueba_activa, 
                                "edad": float(edad_calculada), 
                                "tiempo": float(ins_tiempo),
                                "nota": ins_nota, 
                                "usuario_id": id_atleta_actual
                            }
                            ctx_supabase_mar.table("marcas_historicas").insert(nueva_m).execute()
                            st.success("¡Marca guardada con éxito!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al procesar: {e}")
        
        with col_tabla_rapida:
            st.markdown("**Registros en Base de Datos**")
            if not df_marcas_raw.empty:
                df_visual = df_marcas_raw.copy()
                df_visual["tiempo"] = df_visual["tiempo"].apply(lambda x: formatear_a_minutos(float(x)))
                
                if rol_usuario in ["Head Coach", "Entrenador", "Administrador"]:
                    opciones_del = {f"Edad: {round(r['edad'],2)} | T: {r['tiempo']} | {r['nota']}": r['id'] for _, r in df_marcas_raw.iterrows()}
                    sel_del = st.selectbox("Eliminar Fila:", options=list(opciones_del.keys()))
                    if st.button("🗑️ Eliminar"):
                        ctx_supabase_mar.table("marcas_historicas").delete().eq("id", int(opciones_del[sel_del])).execute()
                        st.rerun()
                
                st.dataframe(df_visual[["prueba", "edad", "tiempo", "nota"]], use_container_width=True, hide_index=True)

    # ACCIONES ANALÍTICAS SI EXISTEN REGISTROS
    if not df_marcas_raw.empty:
        # SUBTAB 2: TOP TIEMPOS (PBS)
        with subtab_top_tiempos:
            st.markdown("#### 🥇 Récords Personales Absolutos (Personal Best)")
            idx_mejores = df_marcas_raw.groupby('prueba')['tiempo'].idxmin()
            df_top = df_marcas_raw.loc[idx_mejores].copy().sort_values("prueba").reset_index(drop=True)
            
            df_tabla_top = pd.DataFrame({
                "Prueba": df_top["prueba"],
                "Tiempo Oficial": df_top["tiempo"].apply(lambda x: formatear_a_minutos(float(x))),
                "Edad Crono": df_top["edad"].round(2),
                "Competición": df_top["nota"]
            })
            st.write(df_tabla_top.to_html(index=False, classes="tabla-estilizada"), unsafe_allow_html=True)

        # SUBTAB 3: EVOLUCIÓN Y GRÁFICO OCRE DE MINIMAS
        with subtab_evolucion_prueba:
            st.markdown("#### 📈 Buscador Histórico Dinámico y Líneas de Campeonato")
            
            # Obtención de metadatos de categoría
            atleta_meta = ctx_supabase_mar.table("usuarios").select("fecha_nacimiento, genero").eq("id", id_atleta_actual).execute().data
            cat_nadador, edad_tec = "Desconocida", 0
            genero_nadador = "F"
            if atleta_meta:
                genero_nadador = atleta_meta[0].get("genero", "F")
                cat_nadador, edad_tec = calcular_categoria_competencia(str(atleta_meta[0]["fecha_nacimiento"])[:10])
            
            st.caption(f"🎯 Categoría: **{cat_nadador}** | Género: **{genero_nadador}**")
            
            lista_pruebas = sorted(df_marcas_raw["prueba"].unique().tolist())
            p_sel = st.selectbox("Seleccione la Prueba:", options=lista_pruebas)
            
            df_ev = df_marcas_raw[df_marcas_raw["prueba"] == p_sel].sort_values("edad").reset_index(drop=True)
            
            if not df_ev.empty:
                fig_mar, ax = plt.subplots(figsize=(8.5, 3.5))
                ax.plot(df_ev["edad"], df_ev["tiempo"], marker="o", color="#3498db", label="Progreso")
                
                # Búsqueda ocre de marcas mínimas de referencia
                m_minima = None
                try:
                    ref_db = ctx_supabase_mar.table("marcas_referencia").select("m_ano").eq("prueba", p_sel).eq("categoria", cat_nadador).eq("genero", genero_nadador).execute().data
                    if ref_db and ref_db[0].get("m_ano"):
                        m_minima = float(ref_db[0]["m_ano"])
                except Exception:
                    pass
                
                if m_minima:
                    ax.axhline(m_minima, color="#b58900", linestyle=":", label=f"Mínima {cat_nadador}")
                    ax.set_ylim(bottom=min(df_ev["tiempo"].min(), m_minima) * 0.96)
                else:
                    ax.set_ylim(bottom=df_ev["tiempo"].min() * 0.96)
                
                ax.set_ylim(top=df_ev["tiempo"].max() * 1.04)
                
                # Corrección de firma del FuncFormatter de Matplotlib auditada
                ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: formatear_a_minutos(x)))
                ax.set_xlabel("Edad del Nadador (Años)")
                ax.set_ylabel("Tiempo de Carrera")
                ax.grid(True, linestyle=":", alpha=0.4)
                ax.legend(fontsize=7)
                st.pyplot(fig_mar)
                
                df_tabla_ev = pd.DataFrame({
                    "Edad": df_ev["edad"].round(2),
                    "Prueba": df_ev["prueba"],
                    "Tiempo": df_ev["tiempo"].apply(lambda x: formatear_a_minutos(x)),
                    "Nota": df_ev["nota"]
                })
                st.write(df_tabla_ev.to_html(index=False, classes="tabla-estilizada"), unsafe_allow_html=True)