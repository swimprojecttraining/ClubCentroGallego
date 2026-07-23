# =========================================================================
    # SUB-PESTAÑA 2: ESTADO DE PLANTILLA Y ATLETAS
    # =========================================================================
    with subtab_atletas:
        st.markdown("### 👥 Gestión de Plantilla y Atletas")
        st.caption("Control de atletas activos, inactivos y actualización de datos de la plantilla institucional.")

        # Cargar todos los nadadores con sus campos principales (usando 'created_at')
        try:
            res_plantilla = supabase.table("usuarios")\
                .select("id, nombre, usuario, email, estatus, created_at")\
                .eq("rol", "Nadador")\
                .execute()
            
            df_plantilla = pd.DataFrame(res_plantilla.data) if res_plantilla.data else pd.DataFrame()
        except Exception as e:
            st.error(f"Error al cargar la plantilla de atletas: {e}")
            df_plantilla = pd.DataFrame()

        if df_plantilla.empty:
            st.warning("No hay atletas registrados en el sistema.")
        else:
            # --- FILTROS DE PLANTILLA ---
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                estatus_filtro = st.selectbox(
                    "Filtrar por Estatus de Plantilla:", 
                    ["Todos", "Activo", "Inactivo", "Suspendido", "Retirado"], 
                    key="filtro_estatus_plantilla"
                )
            with col_f2:
                busqueda_plantilla = st.text_input(
                    "🔍 Buscar en Plantilla:", 
                    placeholder="Nombre, usuario o correo...", 
                    key="busq_plantilla"
                )

            df_p_filtrado = df_plantilla.copy()
            
            # Aplicar filtro de estatus si existe la columna
            if estatus_filtro != "Todos" and "estatus" in df_p_filtrado.columns:
                df_p_filtrado = df_p_filtrado[df_p_filtrado["estatus"] == estatus_filtro]

            # Aplicar filtro de búsqueda de texto
            if busqueda_plantilla:
                df_p_filtrado = df_p_filtrado[
                    df_p_filtrado["nombre"].str.contains(busqueda_plantilla, case=False, na=False) |
                    df_p_filtrado["usuario"].str.contains(busqueda_plantilla, case=False, na=False) |
                    df_p_filtrado["email"].str.contains(busqueda_plantilla, case=False, na=False)
                ]

            # --- TARJETAS MÉTRICAS DE PLANTILLA ---
            k1, k2, k3 = st.columns(3)
            total_atletas = len(df_plantilla)
            activos_cnt = len(df_plantilla[df_plantilla["estatus"] == "Activo"]) if "estatus" in df_plantilla.columns else 0
            otros_cnt = total_atletas - activos_cnt

            k1.metric("Total Atletas Registrados", total_atletas)
            k2.metric("🟢 Atletas Activos", activos_cnt)
            k3.metric("⚪ Inactivos / Otros", otros_cnt)

            st.markdown("---")

            # --- TABLA DE PLANTILLA ---
            cols_p_mostrar = ["nombre", "usuario", "email", "estatus", "created_at"]
            cols_disponibles = [c for c in cols_p_mostrar if c in df_p_filtrado.columns]
            
            df_p_display = df_p_filtrado[cols_disponibles].copy()
            
            # Diccionario de renombrado dinámico para las columnas disponibles
            nombres_columnas = {
                "nombre": "Atleta",
                "usuario": "Usuario",
                "email": "Correo Electrónico",
                "estatus": "Estatus",
                "created_at": "Fecha de Registro"
            }
            df_p_display.columns = [nombres_columnas.get(c, c) for c in cols_disponibles]

            st.dataframe(df_p_display, use_container_width=True, hide_index=True)

            # --- FORMULARIO DE ACTUALIZACIÓN DE ESTATUS DE ATLETA ---
            st.markdown("---")
            with st.expander("⚙️ **Actualizar Estatus de Atleta en el Club**", expanded=False):
                with st.form("form_actualizar_atleta_estatus"):
                    atleta_mod_id = st.selectbox(
                        "Seleccionar Atleta:",
                        options=df_plantilla["id"].tolist(),
                        format_func=lambda x: f"{df_plantilla[df_plantilla['id'] == x]['nombre'].values[0]} (@{df_plantilla[df_plantilla['id'] == x]['usuario'].values[0]})"
                    )
                    
                    nuevo_estatus_atleta = st.selectbox(
                        "Nuevo Estatus Institucional:", 
                        ["Activo", "Inactivo", "Suspendido", "Retirado"]
                    )
                    
                    btn_act_atleta = st.form_submit_button("💾 Guardar Nuevo Estatus", use_container_width=True)

                    if btn_act_atleta:
                        try:
                            supabase.table("usuarios")\
                                .update({"estatus": nuevo_estatus_atleta})\
                                .eq("id", atleta_mod_id)\
                                .execute()
                            
                            st.success("✅ Estatus del atleta actualizado exitosamente en el sistema.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar el estatus en la base de datos: {e}")
