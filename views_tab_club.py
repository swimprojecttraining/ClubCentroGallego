# views_tab_club.py (Módulo de Gestión Administrativa del Club)
import streamlit as st
import pandas as pd
import datetime

def renderizar_tab_club():
    """
    Pestaña principal de administración del club.
    Entorno autónomo para control financiero, estatus de atletas y correspondencia.
    """
    st.markdown("## 🏛️ Centro de Control Administrativo")
    st.caption("Gestión financiera, estado de cuotas y herramientas institucionales.")
    st.markdown("---")

    supabase = st.session_state.get("supabase")
    if not supabase:
        st.error("❌ Error de conexión: No se encontró la instancia de Supabase en la sesión.")
        return

    # Contenedor de sub-secciones en la pantalla principal
    subtab_pagos, subtab_atletas, subtab_comunicacion = st.tabs([
        "💳 Control Financiero y Pagos", 
        "👥 Estado de Plantilla y Atletas", 
        "📄 Comunicados y Correspondencia"
    ])

    # =========================================================================
    # SUB-PESTAÑA 1: CONTROL FINANCIERO Y PAGOS
    # =========================================================================
    with subtab_pagos:
        st.markdown("### 💰 Control de Cuotas y Solvencias")
        
        # --- FILTROS SUPERIORES ---
        col_temp, col_mes, col_estado, col_buscar = st.columns([1, 1, 1, 2])
        
        año_actual = datetime.date.today().year
        mes_actual = datetime.date.today().month

        with col_temp:
            temporada_sel = st.number_input("Temporada:", min_value=2020, max_value=2030, value=año_actual, key="club_temp")
        
        with col_mes:
            mes_sel = st.selectbox("Mes:", ["Todos"] + list(range(1, 13)), index=mes_actual, key="club_mes")

        with col_estado:
            estado_sel = st.selectbox("Estatus:", ["Todos", "Solvente", "Pendiente", "Exonerado"], key="club_est")

        with col_buscar:
            busqueda_texto = st.text_input("🔍 Buscar Atleta:", placeholder="Nombre o usuario...", key="club_busq")

        # --- CARGA DE DATOS ---
        try:
            # 1. Cargar Nadadores activos
            res_usuarios = supabase.table("usuarios")\
                .select("id, nombre, usuario, estatus, email")\
                .eq("rol", "Nadador")\
                .execute()
            
            df_nadadores = pd.DataFrame(res_usuarios.data) if res_usuarios.data else pd.DataFrame()
        except Exception as e:
            st.error(f"Error al cargar lista de nadadores: {e}")
            df_nadadores = pd.DataFrame()

        if df_nadadores.empty:
            st.warning("No hay nadadores registrados en la base de datos.")
            return

        # 2. Cargar registros de pagos para la temporada
        try:
            res_pagos = supabase.table("control_pagos")\
                .select("*")\
                .eq("temporada", temporada_sel)\
                .execute()
            
            df_pagos = pd.DataFrame(res_pagos.data) if res_pagos.data else pd.DataFrame()
        except Exception as e:
            df_pagos = pd.DataFrame()

        # --- CRUCE Y PROCESAMIENTO DE DATOS ---
        cols_mostrar = ["nombre", "usuario", "estado_pago", "monto", "fecha_pago", "referencia_pago", "observaciones"]

        if not df_pagos.empty:
            if mes_sel != "Todos":
                df_pagos_filtrado = df_pagos[df_pagos["mes"] == int(mes_sel)]
            else:
                df_pagos_filtrado = df_pagos
            
            df_merged = pd.merge(df_nadadores, df_pagos_filtrado, left_on="id", right_on="usuario_id", how="left")
        else:
            df_merged = df_nadadores.copy()
            df_merged["estado_pago"] = "Pendiente"
            df_merged["monto"] = 0.0
            df_merged["fecha_pago"] = None
            df_merged["referencia_pago"] = ""
            df_merged["observaciones"] = ""

        # Normalización robusta de columnas por si faltan en el merge
        for col in cols_mostrar:
            if col not in df_merged.columns:
                df_merged[col] = "Pendiente" if col == "estado_pago" else (0.0 if col == "monto" else "")

        df_merged["estado_pago"] = df_merged["estado_pago"].fillna("Pendiente")
        df_merged["monto"] = df_merged["monto"].fillna(0.0)

        # Filtro de estatus
        if estado_sel != "Todos":
            df_merged = df_merged[df_merged["estado_pago"] == estado_sel]

        # Filtro por búsqueda de texto
        if busqueda_texto:
            df_merged = df_merged[
                df_merged["nombre"].str.contains(busqueda_texto, case=False, na=False) |
                df_merged["usuario"].str.contains(busqueda_texto, case=False, na=False)
            ]

        # --- TARJETAS MÉTRICAS (KPIs) ---
        m1, m2, m3, m4 = st.columns(4)
        
        total_recaudado = df_merged["monto"].sum()
        cant_solventes = len(df_merged[df_merged["estado_pago"] == "Solvente"])
        cant_pendientes = len(df_merged[df_merged["estado_pago"] == "Pendiente"])
        cant_exonerados = len(df_merged[df_merged["estado_pago"] == "Exonerado"])

        m1.metric("Total Recaudado ($)", f"${total_recaudado:,.2f}")
        m2.metric("🟢 Solventes", cant_solventes)
        m3.metric("🔴 Pendientes", cant_pendientes)
        m4.metric("⚪ Exonerados", cant_exonerados)

        st.markdown("---")

        # --- TABLA PRINCIPAL DE PAGOS ---
        df_display = df_merged[cols_mostrar].copy()
        df_display.columns = ["Atleta", "Usuario", "Estado", "Monto ($)", "Fecha Pago", "N° Referencia", "Observaciones"]

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # --- FORMULARIO DE REGISTRO / ACTUALIZACIÓN DE PAGO ---
        st.markdown("---")
        with st.expander("📝 **Registrar / Actualizar Pago de Atleta**", expanded=False):
            with st.form("form_registrar_pago"):
                c1, c2, c3 = st.columns([2, 1, 1])
                
                with c1:
                    atleta_id_sel = st.selectbox(
                        "Seleccionar Atleta:", 
                        options=df_nadadores["id"].tolist(),
                        format_func=lambda x: df_nadadores[df_nadadores["id"] == x]["nombre"].values[0]
                    )
                with c2:
                    mes_pago = st.selectbox("Mes Afectado:", list(range(1, 13)), index=mes_actual - 1)
                with c3:
                    monto_pago = st.number_input("Monto Recibido ($):", min_value=0.0, step=5.0)

                c4, c5, c6 = st.columns([1, 1, 2])
                with c4:
                    nuevo_estado = st.selectbox("Estatus de Pago:", ["Solvente", "Pendiente", "Exonerado"])
                with c5:
                    fecha_pago_val = st.date_input("Fecha del Pago:", value=datetime.date.today())
                with c6:
                    ref_pago_val = st.text_input("N° Referencia / Comprobante:", placeholder="Ej: Transf-998231")

                obs_pago_val = st.text_input("Observaciones / Notas de pago:")

                btn_guardar_pago = st.form_submit_button("💾 Registrar Estatus Administrativo", use_container_width=True)

                if btn_guardar_pago:
                    registro_pago = {
                        "usuario_id": atleta_id_sel,
                        "temporada": temporada_sel,
                        "mes": mes_pago,
                        "monto": monto_pago,
                        "estado_pago": nuevo_estado,
                        "fecha_pago": str(fecha_pago_val),
                        "referencia_pago": ref_pago_val,
                        "observaciones": obs_pago_val
                    }

                    try:
                        supabase.table("control_pagos").upsert(registro_pago).execute()
                        st.success("✅ Pago y estatus administrativo actualizados correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar pago en base de datos: {e}")

# =========================================================================
    # SUB-PESTAÑA 2: ESTADO DE PLANTILLA Y ATLETAS
    # =========================================================================
    with subtab_atletas:
        st.markdown("### 👥 Gestión de Plantilla y Atletas")
        st.caption("Control de atletas activos, inactivos y actualización de datos de la plantilla institucional.")
        st.info("💡 **Nota pendiente:** Próximamente se incluirá el campo de cédula de identidad en la actualización de registros.")

        # Cargar todos los nadadores incluyendo fecha de nacimiento y categoría
        try:
            res_plantilla = supabase.table("usuarios")\
                .select("id, nombre, email, estatus, fecha_nacimiento, categoria")\
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
                    placeholder="Nombre o correo electrónico...", 
                    key="busq_plantilla"
                )

            df_p_filtrado = df_plantilla.copy()
            
            # Aplicar filtro de estatus si existe la columna
            if estatus_filtro != "Todos" and "estatus" in df_p_filtrado.columns:
                df_p_filtrado = df_p_filtrado[df_p_filtrado["estatus"] == estatus_filtro]

            # Aplicar filtro de búsqueda de texto (excluyendo usuario)
            if busqueda_plantilla:
                df_p_filtrado = df_p_filtrado[
                    df_p_filtrado["nombre"].str.contains(busqueda_plantilla, case=False, na=False) |
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
            cols_p_mostrar = ["nombre", "email", "fecha_nacimiento", "categoria", "estatus"]
            cols_disponibles = [c for c in cols_p_mostrar if c in df_p_filtrado.columns]
            
            df_p_display = df_p_filtrado[cols_disponibles].copy()
            
            # Diccionario de renombrado limpio y adaptado
            nombres_columnas = {
                "nombre": "Atleta",
                "email": "Correo Electrónico",
                "fecha_nacimiento": "Fecha de Nacimiento",
                "categoria": "Categoría",
                "estatus": "Estatus"
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
                        format_func=lambda x: df_plantilla[df_plantilla['id'] == x]['nombre'].values[0]
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
    # =========================================================================
    # SUB-PESTAÑAS PENDIENTES (PASO 3)
    # =========================================================================

    with subtab_comunicacion:
        st.info("🛠️ En construcción: Módulo de Comunicados, Circulares y Emisión de Constancias.")
