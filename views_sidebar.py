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

    # 1. Obtención de la categoría para alimentar tu nueva función
    cat_nadador, genero_nadador = "Desconocida", "F"
    if ctx_supabase_mar:
        try:
            atleta_meta = ctx_supabase_mar.table("usuarios").select("fecha_nacimiento, genero").eq("id", id_atleta_actual).execute().data
            if atleta_meta:
                genero_nadador = atleta_meta[0].get("genero", "F")
                cat_nadador, _ = calcular_categoria_competencia(str(atleta_meta[0]["fecha_nacimiento"])[:10])
        except Exception as e:
            st.error(f"Error al calcular metadatos: {e}")

    # =============================================================================
    # 📊 SELECTOR EN SIDEBAR COMPLETAMENTE AISLADO
    # =============================================================================
    st.sidebar.markdown("---")
    st.sidebar.subheader("⏱️ Gestión de Marcas")
    
    # Invocamos tu función de la librería
    lista_pruebas_restringida = obtener_pruebas_por_categoria(cat_nadador)
    
    # SE RECOGE EN UNA VARIABLE LOCAL. El 'key' evita que choque con la global 'prueba_seleccionada'
    prueba_sidebar_marcas = st.sidebar.selectbox(
        f"Estilo y Distancia ({cat_nadador}):", 
        options=lista_pruebas_restringida,
        index=1 if len(lista_pruebas_restringida) > 1 else 0,
        key="sb_marca_individual_exclusiva" 
    )

    # Validamos el separador visual directamente en el sidebar
    if prueba_sidebar_marcas.startswith("---"):
        st.sidebar.info("👆 Selecciona una distancia específica en el menú de la izquierda para ver o editar los datos.")
        # En vez de st.stop(), dejamos un contenedor vacío en el centro de la pantalla para no romper la app
        st.info("👈 Esperando selección de estilo/distancia válida en la barra lateral.")
        return # Sale limpiamente de la función del tab actual sin romper el resto de la página

    # =============================================================================
    # CONTINUACIÓN DEL FLUJO (Solo se ejecuta si la prueba es válida)
    # =============================================================================
    
    # Descarga del pool histórico del atleta
    df_marcas_raw = pd.DataFrame()
    if ctx_supabase_mar:
        try:
            res_inicial = ctx_supabase_mar.table("marcas_historicas").select("*").eq("usuario_id", id_atleta_actual).execute()
            if res_inicial.data:
                df_marcas_raw = pd.DataFrame(res_inicial.data)
        except Exception:
            pass

    subtab_ingreso, subtab_top_tiempos, subtab_evolucion_prueba = st.tabs([
        "📥 1. Ingresar y Gestionar Marcas",
        "🥇 2. Reporte de Mejores Tiempos (Top Histórico)", 
        "📈 3. Buscador Histórico y Evolución Cronológica"
    ])

    # SUBTAB 1: INGRESO Y GESTIÓN
    with subtab_ingreso:
        col_form, col_tabla_rapida = st.columns([1, 1.2])
        
        with col_form:
            st.markdown(f"**Ingresar Nueva Marca ➔ {prueba_sidebar_marcas}**")
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
                                    "prueba": prueba_sidebar_marcas, # Guardado limpio usando la variable del sidebar
                                    "edad": float(edad_calculada), 
                                    "tiempo": float(ins_tiempo),
                                    "nota": ins_nota, 
                                    "usuario_id": id_atleta_actual
                                }
                                ctx_supabase_mar.table("marcas_historicas").insert(nueva_m).execute()
                                st.success(f"¡Marca guardada con éxito en {prueba_sidebar_marcas}!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al procesar: {e}")
                    else:
                        st.error("❌ No tienes autorización para modificar estos registros.")
        
        with col_tabla_rapida:
            st.markdown(f"**Historial de la Prueba: {prueba_sidebar_marcas}**")
            if not df_marcas_raw.empty:
                df_filtrado_local = df_marcas_raw[df_marcas_raw["prueba"] == prueba_sidebar_marcas].copy()
                
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
                            st.rerun()
                    
                    st.dataframe(df_visual[["edad", "tiempo", "nota"]], use_container_width=True, hide_index=True)
                else:
                    st.info(f"ℹ️ El atleta no posee marcas registradas en {prueba_sidebar_marcas}.")

    # (Nota: Las subpestañas 2 y 3 seguirán funcionando igual usando 'df_marcas_raw' para sus cálculos analíticos globales)
