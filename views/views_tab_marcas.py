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
    st.markdown("### ⏱️ Panel de Control Curricular y Marcas Oficiales")
    
    # 1. RECUPERACIÓN BLINDADA (El salvavidas)
    supabase_client = st.session_state.get("supabase")
    if supabase_client is None:
        st.error("Error al conectar con la base de datos: La instancia es nula. Por favor, vuelve a iniciar sesión.")
        st.stop()

    # 2. TUS VARIABLES ORIGINALES (Ahora están seguras después de validar la conexión)
    titulo_grafico = datos_sidebar.get("titulo_grafico", "Prueba General") if datos_sidebar else "Prueba General"
    es_preinfantil = datos_sidebar.get("es_preinfantil", False) if datos_sidebar else False
    
    # 3. LÓGICA DE CONSULTA
    try:
        response = supabase_client.table("marcas_historicas").select("*").execute()
        # Aquí continúa el resto de tu lógica que ya tenías...
    except Exception as e:
        st.error(f"Error al ejecutar consulta en marcas_historicas: {e}")
    
    rol_usuario = st.session_state.get("rol")
    id_usuario = st.session_state.get("usuario_id")
    id_atleta_actual = st.session_state.get("nadador_seleccionado_id")

    # =============================================================================
    # CARPINTERÍA PREVIA: EXTRACCIÓN Y PREPARACIÓN DE DATOS REALEZ
    # =============================================================================
    records_marcas = []
    df_procesado = pd.DataFrame()
    df_marcas_raw = pd.DataFrame()

    try:
        raw_db = ctx_supabase_mar.table("marcas_historicas").select("*").eq("usuario_id", id_atleta_actual).execute()
        records_marcas = raw_db.data if raw_db else []
        
        if records_marcas:
            df_marcas_raw = pd.DataFrame(records_marcas)
            # Construimos df_procesado para la Subtab 1 filtrando por la prueba bajo análisis
            df_procesado = df_marcas_raw[df_marcas_raw["prueba"] == titulo_grafico].copy()
            if not df_procesado.empty:
                df_procesado = df_procesado.sort_values("edad").reset_index(drop=True)
                # Formateamos columnas simulando la estructura esperada por tu visor original
                df_procesado["Edad"] = df_procesado["edad"].round(2)
                df_procesado["Tiempo"] = df_procesado["tiempo"]
                df_procesado["Evento / Fecha"] = df_procesado["nota"]
    except Exception as e:
        st.error(f"Error al conectar con marcas_historicas: {e}")

    # =============================================================================
    # INYECCIÓN DE LAS 3 SUBPESTAÑAS EN LA PARTE SUPERIOR DEL PANEL
    # =============================================================================
    subtab_ingreso, subtab_top_tiempos, subtab_evolucion_prueba = st.tabs([
        "📥 1. Ingresar y Gestionar Marcas",
        "🥇 2. Reporte de Mejores Tiempos (Top Histórico)", 
        "📈 3. Buscador Histórico y Evolución Cronológica"
    ])

    # =============================================================================
    # SUBTAB 1: INGRESO DE DATOS Y GESTIÓN DIRECTA DE FILAS
    # =============================================================================
    with subtab_ingreso:
        col_form, col_tabla_rapida = st.columns([1, 1.2])
        
        with col_form:
            st.markdown("**Ingresar Nueva Marca**")
            with st.form("form_insertar_marca", clear_on_submit=True):
                ins_fecha_evento = st.date_input("Fecha de la Competencia:", min_value=datetime.date(2020, 1, 1), max_value=datetime.date.today(), value=datetime.date.today())
                ins_tiempo_str = st.text_input("Tiempo Oficial (Formatos: '1:13.34' o '46.28'- use punto para centesimas):", placeholder="1:13.34")
                ins_nota = st.text_input("Evento  Año - Lugar:")
                
                if st.form_submit_button("💾 Guardar Registro"):
                    if rol_usuario in ["Head Coach", "Entrenador", "Administrador"] or id_usuario == id_atleta_actual:
                        try:
                            ins_tiempo = convertir_string_a_segundos(ins_tiempo_str)
                            fecha_nacimiento_atleta = st.session_state.get("fecha_nacimiento")
                            
                            if rol_usuario in ["Head Coach", "Entrenador", "Administrador"]:
                                atleta_query = ctx_supabase_mar.table("usuarios").select("fecha_nacimiento").eq("id", id_atleta_actual).execute()
                                if atleta_query.data:
                                    fecha_nacimiento_atleta = atleta_query.data[0]["fecha_nacimiento"]
                            
                            if not fecha_nacimiento_atleta:
                                st.error("❌ El atleta no posee fecha de nacimiento en su perfil.")
                            else:
                                edad_calculada = calcular_edad_decimal(fecha_nacimiento_atleta, ins_fecha_evento)
                                if edad_calculada is None:
                                    st.error("❌ Error al procesar la fecha de nacimiento.")
                                else:
                                    nueva_m = {
                                        "prueba": titulo_grafico, 
                                        "edad": float(edad_calculada), 
                                        "tiempo": float(ins_tiempo),
                                        "nota": ins_nota, 
                                        "usuario_id": id_atleta_actual
                                    }
                                    ctx_supabase_mar.table("marcas_historicas").insert(nueva_m).execute()
                                    st.success(f"¡Marca guardada! Convertido a {ins_tiempo}s. Edad: {edad_calculada} años.")
                                    st.rerun()
                                    
                        except ValueError as e:
                            st.error(f"❌ {e}")
                        except Exception as e:
                            st.error(f"Error al guardar el registro: {e}")
        
        with col_tabla_rapida:
            st.markdown("**Gestión de Registros Existentes**")
            if not df_procesado.empty:
                df_visual = df_procesado.copy()
                
                if "Tiempo" in df_visual.columns:
                    df_visual["Tiempo"] = df_visual["Tiempo"].apply(lambda x: formatear_a_minutos(float(x)) if pd.notna(x) else "-")
                
                if rol_usuario in ["Head Coach", "Entrenador", "Administrador"]:
                    opciones_eliminacion = {
                        f"Edad: {row['Edad']} | Tiempo: {row['Tiempo']} | {row['Evento / Fecha']}": row['id']
                        for _, row in df_procesado.iterrows()
                    }
                    seleccion_etiqueta = st.selectbox("Seleccione el registro que desea eliminar:", options=list(opciones_eliminacion.keys()), key="del_box_subtab1")
                    id_del = opciones_eliminacion[seleccion_etiqueta]
                    
                    if st.button("🗑️ Eliminar Fila", key="btn_del_subtab1"):
                        ctx_supabase_mar.table("marcas_historicas").delete().eq("id", int(id_del)).execute()
                        st.warning("Registro removido con éxito.")
                        st.rerun()
                
                st.dataframe(df_visual.drop(columns=["id", "prueba", "usuario_id", "edad", "nota", "tiempo"], errors="ignore"), use_container_width=True)
            else:
                st.info(f"💡 No hay registros en 'marcas_historicas' para la prueba {titulo_grafico}.")

    # =============================================================================
    # PROCESAMIENTO SEGURO DE ANÁLISIS COMPLETO
    # =============================================================================
    if not records_marcas:
        with subtab_top_tiempos:
            st.info("📭 Registra marcas en la Subpestaña 1 para habilitar los reportes analíticos.")
        with subtab_evolucion_prueba:
            st.info("📭 Registra marcas en la Subpestaña 1 para habilitar el buscador evolutivo.")
    else:
        try:
            # ---------------------------------------------------------------------
            # SUBTAB 2: REPORTES DE MEJORES TIEMPOS (TOP HISTÓRICO POR PRUEBA)
            # ---------------------------------------------------------------------
            with subtab_top_tiempos:
                st.markdown("#### 🥇 Récords Personales Absolutos (Personal Best)")
                st.caption("Cálculo automático de marcas mínimas por agrupación técnica de pruebas registradas.")
                
                idx_mejores = df_marcas_raw.groupby('prueba')['tiempo'].idxmin()
                df_top_historico = df_marcas_raw.loc[idx_mejores].copy().sort_values("prueba").reset_index(drop=True)
                
                df_top_historico["tiempo_formateado"] = df_top_historico["tiempo"].map(
                    lambda x: f"{int(x//60)}:{ascii(round(x%60, 2)).replace(chr(39),'')}" if x >= 60 else f"{x:.2f}"
                )
                
                df_tabla_top = pd.DataFrame({
                    "Prueba": df_top_historico["prueba"],
                    "Tiempo": df_top_historico["tiempo_formateado"],
                    "Edad al Lograrlo": df_top_historico["edad"].round(2),
                    "Detalle / Evento": df_top_historico["nota"]
                })
                
                st.write(df_tabla_top.to_html(index=False, classes="tabla-estilizada"), unsafe_allow_html=True)
                
                st.markdown("##### 📥 Exportación de Currículum de Récords")
                csv_top_data = df_tabla_top.to_csv(index=False).encode('utf-8')
                txt_top_data = df_tabla_top.to_string(index=False).encode('utf-8')
                
                c_top1, c_top2 = st.columns(2)
                with c_top1:
                    st.download_button("📥 Descargar PB (CSV)", data=csv_top_data, file_name="mejores_marcas.csv", mime="text/csv", use_container_width=True, key="dl_csv_pbs")
                with c_top2:
                    st.download_button("📄 Descargar Currículum Curricular (TXT)", data=txt_top_data, file_name="curriculum_marcas.txt", mime="text/plain", use_container_width=True, key="dl_txt_pbs")

            # ---------------------------------------------------------------------
            # SUBTAB 3: EVOLUCIÓN CRONOLÓGICA CON FILTRO POR PRUEBA
            # ---------------------------------------------------------------------
            with subtab_evolucion_prueba:
                st.markdown("#### 📈 Buscador Histórico Dinámico")
                
                categoria_nadador = None
                edad_tecnica = 0
                genero_nadador = None
                
                if id_atleta_actual:
                    try:
                        info_atleta_db = ctx_supabase_mar.table("usuarios").select("*").eq("id", id_atleta_actual).execute()
                        if info_atleta_db.data:
                            atleta_meta = info_atleta_db.data[0]
                            fecha_nac_raw = atleta_meta.get("fecha_nacimiento")
                            genero_nadador = atleta_meta.get("genero") or atleta_meta.get("sexo") or "F"
                            
                            if fecha_nac_raw:
                                fecha_nac_str = str(fecha_nac_raw)[:10]
                                categoria_nadador, edad_tecnica = calcular_categoria_competencia(fecha_nac_str)
                                st.session_state["categoria_actual"] = categoria_nadador
                                st.session_state["categoria"] = categoria_nadador
                                st.session_state["genero"] = genero_nadador
                    except Exception as e:
                        st.warning(f"⚠️ Error al calcular la categoría del atleta: {e}")
                
                if not categoria_nadador:
                    categoria_nadador = st.session_state.get("categoria") or st.session_state.get("categoria_actual")
                if not genero_nadador:
                    genero_nadador = st.session_state.get("genero") or st.session_state.get("sexo") or "F"
                
                if isinstance(categoria_nadador, str): categoria_nadador = categoria_nadador.strip()
                if isinstance(genero_nadador, str): genero_nadador = genero_nadador.strip()

                if categoria_nadador and categoria_nadador not in ["Desconocida", "Error Formato"]:
                    st.caption(f"🎯 Categoría Competencia: **{categoria_nadador}** (Edad Técnica: {edad_tecnica} años) | Género: **{genero_nadador}**")
                else:
                    st.caption("⚠️ No se pudo determinar la categoría reglamentaria. Evaluando marcas globales.")
                
                lista_pruebas_atleta = sorted(df_marcas_raw["prueba"].unique().tolist())
                prueba_sel = st.selectbox("🏊‍♂️ Seleccione la Prueba Específica a Evaluar:", options=["Todas"] + lista_pruebas_atleta, index=0, key="sb_prueba_subtab3")
                
                if prueba_sel == "Todas":
                    df_evolucion = df_marcas_raw.sort_values("edad").reset_index(drop=True)
                else:
                    df_evolucion = df_marcas_raw[df_marcas_raw["prueba"] == prueba_sel].sort_values("edad").reset_index(drop=True)
                
                df_evolucion["tiempo_formateado"] = df_evolucion["tiempo"].map(
                    lambda x: f"{int(x//60)}:{ascii(round(x%60, 2)).replace(chr(39),'')}" if x >= 60 else f"{x:.2f}"
                )

                if prueba_sel != "Todas" and len(df_evolucion) > 0:
                    fig_mar, ax = plt.subplots(figsize=(8.5, 3.5))
                    df_cronologico = df_evolucion.sort_values("edad").reset_index(drop=True)
                    t0_tiempo = float(df_cronologico["tiempo"].iloc[0])
                    
                    ax.plot(df_cronologico["edad"], df_cronologico["tiempo"], marker="o", linestyle="-", color="#3498db", linewidth=1.8, label="Tiempo Registrado")
                    
                    min_seg = df_cronologico["tiempo"].min()
                    ax.axhline(min_seg, color="#e74c3c", linestyle="--", alpha=0.6, label=f"Récord Personal ({formatear_a_minutos(min_seg)})")
                    
                    marca_minima_seg = None
                    try:
                        query_ref = ctx_supabase_mar.table("marcas_referencia").select("m_ano").eq("prueba", prueba_sel)
                        if categoria_nadador: query_ref = query_ref.eq("categoria", categoria_nadador)
                        if genero_nadador: query_ref = query_ref.eq("genero", genero_nadador)
                        ref_query = query_ref.execute()
                        if ref_query.data and ref_query.data[0].get("m_ano") is not None:
                            marca_minima_seg = float(ref_query.data[0]["m_ano"])
                    except Exception:
                        pass
                    
                    if marca_minima_seg is not None:
                        color_ocre = "#b58900"
                        ax.axhline(marca_minima_seg, color=color_ocre, linestyle=":", linewidth=1.5, alpha=0.8, label=f"Mínima {categoria_nadador}")
                        x_max = df_cronologico["edad"].max()
                        ax.text(x_max, marca_minima_seg, f" Mínima: {formatear_a_minutos(marca_minima_seg)}", color=color_ocre, va='bottom', ha='left', fontsize=7, fontweight='bold')
                        ax.set_ylim(bottom=min(min_seg, marca_minima_seg) * 0.96)
                    else:
                        ax.set_ylim(bottom=min_seg * 0.96)
                    
                    ax.set_ylim(top=t0_tiempo * 1.04)
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: formatear_a_minutos(x)))
                    ax.set_ylabel("Tiempo (Minutos)", fontsize=8)
                    ax.set_xlabel("Evolución Basada en la Edad (Años)", fontsize=8)
                    ax.tick_params(axis='both', labelsize=7)
                    ax.grid(True, linestyle=":", alpha=0.4)
                    ax.legend(fontsize=7, loc="upper right")
                    plt.tight_layout()
                    st.pyplot(fig_mar)
                
                df_tabla_ev = pd.DataFrame({
                    "Edad (Años)": df_evolucion["edad"].round(2),
                    "Prueba Realizada": df_evolucion["prueba"],
                    "Tiempo": df_evolucion["tiempo_formateado"],
                    "Referencia / Campeonato": df_evolucion["nota"]
                })
                st.write(df_tabla_ev.to_html(index=False, classes="tabla-estilizada"), unsafe_allow_html=True)
            
            csv_ev_data = df_tabla_ev.to_csv(index=False).encode('utf-8')
            txt_ev_data = df_tabla_ev.to_string(index=False).encode('utf-8')
            
            c_ev1, c_ev2 = st.columns(2)
            with c_ev1:
                st.download_button("📥 Descargar Historial Seleccionado (CSV)", data=csv_ev_data, file_name="historial_tiempos.csv", mime="text/csv", use_container_width=True, key="dl_csv_ev")
            with c_ev2:
                st.download_button("📄 Descargar Historial Seleccionado (TXT)", data=txt_ev_data, file_name="historial_tiempos.txt", mime="text/plain", use_container_width=True, key="dl_txt_ev")
        except Exception as e:
            st.error(f"Error al compilar el análisis analítico de marcas: {e}")

# =============================================================================
# VISTA GENERAL DE UMBRALES ADAPTADA AL CONTENEDOR UNIFICADO
# =============================================================================
def render_tab_config_umbrales(datos_sidebar):
    if st.session_state.rol in ["Head Coach", "Administrador"]:
        ctx_supabase_ref = datos_sidebar.get("supabase") if datos_sidebar else st.session_state.get("supabase")
        titulo_grafico = datos_sidebar.get("titulo_grafico", "Prueba General")
        es_preinfantil = datos_sidebar.get("es_preinfantil", False)

        st.markdown(f"### ⚙️ Umbrales de Competencia para la Categoría")
        
        if titulo_grafico in ['25 Libre', '25 Espalda', '25 Pecho', '25 Mariposa', '100 Combinado'] or es_preinfantil:
            st.info(f"💡 **Aviso:** Las marcas de referencia para pruebas Preinfantiles ({titulo_grafico}) se calculan automáticamente basándose en las marcas mínimas de 50m de la categoría Infantil A.")
        else:
            u_cat = st.selectbox("Categoría a Modificar u Organizar:", options=["Infantil A", "Infantil B", "Juvenil A", "Juvenil B", "Máxima"])
            db_m_ano, db_m_panam_b, db_m_panam_a, db_m_wa_b, db_m_wa_a, db_m_wr = None, None, None, None, None, None
            try:
                ref_dinamica = ctx_supabase_ref.table("marcas_referencia").select("*")\
                    .eq("prueba", titulo_grafico)\
                    .eq("genero", st.session_state.nadador_seleccionado_genero)\
                    .eq("categoria", u_cat).execute()
                if ref_dinamica.data:
                    r_det = ref_dinamica.data[0]
                    db_m_ano = float(r_det["m_ano"]) if r_det["m_ano"] is not None else None
                    db_m_panam_b = float(r_det["m_panam_b"]) if r_det["m_panam_b"] is not None else None
                    db_m_panam_a = float(r_det["m_panam_a"]) if r_det["m_panam_a"] is not None else None
                    db_m_wa_b = float(r_det["m_wa_b"]) if r_det["m_wa_b"] is not None else None
                    db_m_wa_a = float(r_det["m_wa_a"]) if r_det["m_wa_a"] is not None else None
                    db_m_wr = float(r_det["m_wr"]) if r_det["m_wr"] is not None else None
            except Exception:
                pass

            with st.form("form_update_referencias"):
                u_ano = st.number_input("Marca Mínima Año (seg):", value=db_m_ano if db_m_ano is not None else 0.0, disabled=(db_m_ano is None))
                u_panamb = st.number_input("PANAM Jr - Marca B (seg):", value=db_m_panam_b if db_m_panam_b is not None else 0.0, disabled=(db_m_panam_b is None))
                u_panama = st.number_input("PANAM Jr - Marca A (seg):", value=db_m_panam_a if db_m_panam_a is not None else 0.0, disabled=(db_m_panam_a is None))
                u_wab = st.number_input("World Aquatics - Marca B (seg):", value=db_m_wa_b if db_m_wa_b is not None else 0.0, disabled=(db_m_wa_b is None))
                u_waa = st.number_input("World Aquatics - Marca A (seg):", value=db_m_wa_a if db_m_wa_a is not None else 0.0, disabled=(db_m_wa_a is None))
                u_wr = st.number_input("Récord Mundial de Estilo Absoluto:", value=db_m_wr if db_m_wr is not None else 25.0, disabled=(db_m_wr is None))
                
                if st.form_submit_button("⚡ Guardar Configuración de Tiempos"):
                    up_data = {}
                    if db_m_ano is not None: up_data["m_ano"] = u_ano
                    if db_m_panam_b is not None: up_data["m_panam_b"] = u_panamb
                    if db_m_panam_a is not None: up_data["m_panam_a"] = u_panama
                    if db_m_wa_b is not None: up_data["m_wa_b"] = u_wab
                    if db_m_wa_a is not None: up_data["m_wa_a"] = u_waa
                    if db_m_wr is not None: up_data["m_wr"] = u_wr
                    
                    if up_data:
                        ctx_supabase_ref.table("marcas_referencia").upsert({
                            "prueba": titulo_grafico, "genero": st.session_state.nadador_seleccionado_genero,
                            "categoria": u_cat, **up_data
                        }, on_conflict="prueba,genero,categoria").execute()
                        st.success(f"Tiempos de referencia actualizados para {u_cat}.")
                        st.rerun()
    else:
        st.warning("🔒 Requires credenciales de Head Coach.")
