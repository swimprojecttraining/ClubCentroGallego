# views_tab_club.py (Módulo de Gestión Administrativa, Gobernanza y Respaldos)
import streamlit as st
import datetime
import pandas as pd
import urllib.parse
import io
import zipfile
import json

# Importaciones centralizadas desde la librería de utilidades de la app
from formulas_lib_funciones import (
    calcular_categoria_competencia,
    generar_codigo_invitacion,
    calcular_expiracion_token,
    enviar_correo_con_pdf
)
from pdf_memo_utility import generar_pdf_memorandum_nativo


def render_pre_alta_atleta(supabase, id_usuario_club):
    """
    Sub-interfaz para el registro completo de Pre-Alta de integrantes.
    Captura todos los datos institucionales excepto usuario y clave (elegidos por el integrante).
    """
    with st.form("form_pre_alta_completa", clear_on_submit=True):
        st.markdown("### 📩 Pre-Alta de Usuarios")
        st.caption("Registre los datos institucionales obligatorios para generar el código OTP de activación.")
        
        with st.form("form_generar_prealta"):
            pa_nombre = st.text_input("Nombre Completo:")
            pa_email = st.text_input("Correo Electrónico:")
            pa_rol = st.selectbox("Rol Asignado:", options=["Nadador", "Entrenador", "Head Coach", "Club", "Administrador"])
            pa_genero = st.selectbox("Género:", options=["F", "M"], format_func=lambda x: "Femenino" if x == "F" else "Masculino")
            pa_fecha_nac = st.date_input("Fecha de Nacimiento:", min_value=datetime.date(1950, 1, 1), max_value=datetime.date.today())
            
            # Campos opcionales adicionales
            pa_cedula = st.text_input("Cédula / Documento (Opcional):")
            pa_telefono = st.text_input("Teléfono (Opcional):")
        
            if st.form_submit_button("🚀 Generar Código OTP de Pre-Alta", use_container_width=True):
                if not pa_nombre or not pa_email or not pa_rol or not pa_genero or not pa_fecha_nac:
                    st.error("⚠️ Los 5 campos básicos (Nombre, Email, Rol, Género y Fecha de Nacimiento) son estrictamente obligatorios.")
                else:
                    try:
                        # Generación del token OTP de 6 dígitos con expiración a 24 horas
                        token_otp = str(random.randint(100000, 999999))
                        expiracion = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)).isoformat()
                        
                        payload_invitacion = {
                            "token": token_otp,
                            "nombre": pa_nombre.strip(),
                            "email": pa_email.strip().lower(),
                            "rol": pa_rol,
                            "expira_en": expiracion,
                            "usado": False,
                            "datos_perfil": {
                                "genero": pa_genero,
                                "fecha_nacimiento": pa_fecha_nac.isoformat(),
                                "cedula": pa_cedula.strip(),
                                "telefono": pa_telefono.strip()
                            }
                        }
                        
                        # Insertar en la base de datos local del club
                        st.session_state.supabase.table("invitaciones").insert(payload_invitacion).execute()
                        
                        # Envío de correo con el código OTP
                        asunto = f"Código OTP de Activación - {st.session_state.club_seleccionado}"
                        cuerpo = f"Hola {pa_nombre},\n\nSe ha generado tu pre-alta en {st.session_state.club_seleccionado} con el rol de {pa_rol}.\n\nTu código OTP de activación es: {token_otp}\n\nEste código es válido por 24 horas. Ingresa al sistema en la pestaña 'Registro (Pre-Alta OTP)' con este código y tu correo ({pa_email}) para activar tu cuenta."
                        
                        if enviar_email(asunto, cuerpo, pa_email.strip()):
                            st.success(f"✅ Pre-Alta creada exitosamente. Código OTP **{token_otp}** enviado a **{pa_email}**.")
                        else:
                            st.warning(f"⚠️ Pre-Alta creada con OTP **{token_otp}**, pero no se pudo enviar el correo automático.")
                    except Exception as e:
                        st.error(f"Error al registrar la pre-alta: {e}")


def generar_zip_bd_completa(supabase):
    """
    Exporta todas las tablas clave del club en archivos CSV dentro de un contenedor ZIP.
    """
    tablas = ["usuarios", "invitaciones", "control_pagos", "tiempos", "asistencias", "documentos_oficiales"]
    buffer = io.BytesIO()
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for tabla in tablas:
            try:
                res = supabase.table(tabla).select("*").execute()
                if res.data:
                    df = pd.DataFrame(res.data)
                    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
                    zf.writestr(f"{tabla}.csv", csv_bytes)
            except Exception:
                continue
                
    buffer.seek(0)
    return buffer


def generar_expediente_atleta_zip(supabase, atleta_id, nombre_atleta):
    """
    Genera el paquete completo de datos de un atleta específico para traslado o archivo personal.
    """
    buffer = io.BytesIO()
    tablas_atleta = [
        ("perfil_usuario", "usuarios", "id"),
        ("historial_pagos", "control_pagos", "usuario_id"),
        ("historial_tiempos", "tiempos", "usuario_id"),
        ("control_asistencias", "asistencias", "usuario_id")
    ]
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for prefijo, tabla, columna_id in tablas_atleta:
            try:
                res = supabase.table(tabla).select("*").eq(columna_id, atleta_id).execute()
                if res.data:
                    df = pd.DataFrame(res.data)
                    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
                    zf.writestr(f"{prefijo}_{atleta_id}.csv", csv_bytes)
            except Exception:
                continue
                
    buffer.seek(0)
    return buffer


def renderizar_tab_club():
    """
    Pestaña principal de administración y gobernanza del club.
    """
    st.markdown("## 🏛️ Centro de Control Administrativo")
    st.caption("Gestión financiera, gobernanza de nóminas, correspondencia y respaldos de base de datos.")
    st.markdown("---")

    supabase = st.session_state.get("supabase")
    if not supabase:
        st.error("❌ Error de conexión: No se encontró la instancia de Supabase en la sesión.")
        return

    subtab_pagos, subtab_atletas, subtab_comunicacion, subtab_respaldos = st.tabs([
        "💳 Control Financiero y Pagos", 
        "👥 Plantilla y Nóminas", 
        "📄 Comunicados y Correspondencia",
        "💾 Respaldos de BD"
    ])

    # =========================================================================
    # SUB-PESTAÑA 1: CONTROL FINANCIERO Y PAGOS
    # =========================================================================
    with subtab_pagos:
        st.markdown("### 💰 Control de Cuotas y Solvencias")
        
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

        try:
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
        else:
            try:
                res_pagos = supabase.table("control_pagos")\
                    .select("*")\
                    .eq("temporada", temporada_sel)\
                    .execute()
                df_pagos = pd.DataFrame(res_pagos.data) if res_pagos.data else pd.DataFrame()
            except Exception:
                df_pagos = pd.DataFrame()

            cols_mostrar = ["nombre", "usuario", "estado_pago", "monto", "fecha_pago", "referencia_pago", "observaciones"]

            if not df_pagos.empty:
                df_pagos_filtrado = df_pagos[df_pagos["mes"] == int(mes_sel)] if mes_sel != "Todos" else df_pagos
                df_merged = pd.merge(df_nadadores, df_pagos_filtrado, left_on="id", right_on="usuario_id", how="left")
            else:
                df_merged = df_nadadores.copy()
                df_merged["estado_pago"] = "Pendiente"
                df_merged["monto"] = 0.0
                df_merged["fecha_pago"] = None
                df_merged["referencia_pago"] = ""
                df_merged["observaciones"] = ""

            for col in cols_mostrar:
                if col not in df_merged.columns:
                    df_merged[col] = "Pendiente" if col == "estado_pago" else (0.0 if col == "monto" else "")

            df_merged["estado_pago"] = df_merged["estado_pago"].fillna("Pendiente")
            df_merged["monto"] = df_merged["monto"].fillna(0.0)

            if estado_sel != "Todos":
                df_merged = df_merged[df_merged["estado_pago"] == estado_sel]

            if busqueda_texto:
                df_merged = df_merged[
                    df_merged["nombre"].str.contains(busqueda_texto, case=False, na=False) |
                    df_merged["usuario"].str.contains(busqueda_texto, case=False, na=False)
                ]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Recaudado ($)", f"${df_merged['monto'].sum():,.2f}")
            m2.metric("🟢 Solventes", len(df_merged[df_merged["estado_pago"] == "Solvente"]))
            m3.metric("🔴 Pendientes", len(df_merged[df_merged["estado_pago"] == "Pendiente"]))
            m4.metric("⚪ Exonerados", len(df_merged[df_merged["estado_pago"] == "Exonerado"]))

            st.markdown("---")
            df_display = df_merged[cols_mostrar].copy()
            df_display.columns = ["Atleta", "Usuario", "Estado", "Monto ($)", "Fecha Pago", "N° Referencia", "Observaciones"]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

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
                            st.success("✅ Pago registrado correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al registrar pago: {e}")

    # =========================================================================
    # SUB-PESTAÑA 2: PLANTILLA Y NÓMINAS
    # =========================================================================
    with subtab_atletas:
        st.markdown("### 👥 Administración de Plantilla y Fichas de Usuarios")
        st.caption("Control institucional de integrantes, edición de perfiles y consulta de nóminas.")

        id_usuario_club = st.session_state.get("usuario_id")

        # --- 1. MÓDULO DE PRE-ALTA DE INTEGRANTES ---
        with st.expander("➕ **1. Pre-Alta de Integrantes (Emisión OTP)**", expanded=False):
            if id_usuario_club and supabase:
                render_pre_alta_atleta(supabase, id_usuario_club)
            else:
                st.warning("Error de sesión: No se identificó el usuario emisor.")

        # Cargar todos los usuarios del club para el formulario de modificación
        try:
            res_todos = supabase.table("usuarios")\
                .select("id, nombre, email, usuario, rol, estatus, fecha_nacimiento, cedula, telefono")\
                .execute()
            df_todos_usuarios = pd.DataFrame(res_todos.data) if res_todos.data else pd.DataFrame()
        except Exception as e:
            st.error(f"Error al cargar usuarios: {e}")
            df_todos_usuarios = pd.DataFrame()

        # --- 2. FORMULARIO DE EDICIÓN DE FICHA / ESTATUS (UBICADO ARRIBA) ---
        if not df_todos_usuarios.empty:
            with st.expander("⚙️ **2. Actualizar Estatus y Ficha de Usuario (Cualquier Rol)**", expanded=False):
                st.write("Seleccione un usuario registrado para modificar sus datos personales, rol o estatus.")
                
                usuario_mod_id = st.selectbox(
                    "Seleccionar Usuario a Modificar:",
                    options=df_todos_usuarios["id"].tolist(),
                    format_func=lambda x: f"{df_todos_usuarios[df_todos_usuarios['id'] == x]['nombre'].values[0]} | Rol: {df_todos_usuarios[df_todos_usuarios['id'] == x]['rol'].values[0]} | Estatus: {df_todos_usuarios[df_todos_usuarios['id'] == x]['estatus'].values[0]}",
                    key="select_user_global_edit"
                )

                row_user = df_todos_usuarios[df_todos_usuarios["id"] == usuario_mod_id].iloc[0]

                fecha_nac_val = datetime.date(2010, 1, 1)
                if pd.notna(row_user.get("fecha_nacimiento")) and row_user.get("fecha_nacimiento"):
                    try:
                        fecha_nac_val = pd.to_datetime(row_user["fecha_nacimiento"]).date()
                    except Exception:
                        pass

                with st.form("form_editar_ficha_usuario_global"):
                    c_e1, c_e2 = st.columns(2)
                    with c_e1:
                        edit_nombre = st.text_input("Nombre Completo:", value=str(row_user.get("nombre", "")))
                        edit_email = st.text_input("Correo Electrónico:", value=str(row_user.get("email", "")))
                        edit_cedula = st.text_input("Cédula / Documento:", value=str(row_user.get("cedula", "") if pd.notna(row_user.get("cedula")) else ""))
                        
                        roles_disp = ["Nadador", "Entrenador", "Head Coach", "Administrador Club"]
                        rol_act = row_user.get("rol", "Nadador")
                        idx_rol = roles_disp.index(rol_act) if rol_act in roles_disp else 0
                        edit_rol = st.selectbox("Rol Institucional:", roles_disp, index=idx_rol)

                    with c_e2:
                        edit_telefono = st.text_input("Teléfono:", value=str(row_user.get("telefono", "") if pd.notna(row_user.get("telefono")) else ""))
                        edit_fecha_nac = st.date_input("Fecha de Nacimiento:", value=fecha_nac_val)
                        
                        estatus_opciones = ["Activo", "Inactivo", "Suspendido", "Retirado"]
                        estatus_actual = row_user.get("estatus", "Activo")
                        idx_estatus = estatus_opciones.index(estatus_actual) if estatus_actual in estatus_opciones else 0
                        edit_estatus = st.selectbox("Estatus del Usuario:", estatus_opciones, index=idx_estatus)

                    btn_guardar_ficha = st.form_submit_button("💾 Guardar Cambios en Ficha de Usuario", use_container_width=True)

                    if btn_guardar_ficha:
                        payload = {
                            "nombre": edit_nombre,
                            "email": edit_email,
                            "cedula": edit_cedula,
                            "rol": edit_rol,
                            "telefono": edit_telefono,
                            "fecha_nacimiento": str(edit_fecha_nac),
                            "estatus": edit_estatus
                        }
                        try:
                            supabase.table("usuarios").update(payload).eq("id", usuario_mod_id).execute()
                            st.success(f"✅ Usuario **{edit_nombre}** actualizado correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar usuario: {e}")

        st.markdown("---")

        # --- 3. SECCIÓN DE NÓMINAS DIVIDIDAS ---
        tab_nomina_nadadores, tab_nomina_tecnica = st.tabs(["🏊 NÓMINA NADADORES", "📋 NÓMINA TÉCNICA"])

        # NÓMINA NADADORES
        with tab_nomina_nadadores:
            df_nadadores_nom = df_todos_usuarios[df_todos_usuarios["rol"] == "Nadador"].copy() if not df_todos_usuarios.empty else pd.DataFrame()
            
            if df_nadadores_nom.empty:
                st.info("No hay atletas registrados en la Nómina de Nadadores.")
            else:
                for col_opt in ["cedula", "telefono", "fecha_nacimiento", "email"]:
                    if col_opt not in df_nadadores_nom.columns:
                        df_nadadores_nom[col_opt] = ""

                df_nadadores_nom["categoria"] = df_nadadores_nom["fecha_nacimiento"].apply(
                    lambda f: calcular_categoria_competencia(f)[0] if pd.notna(f) and f else "Sin Fecha"
                )

                f1, f2, f3 = st.columns(3)
                with f1:
                    est_f = st.selectbox("Estatus:", ["Todos", "Activo", "Inactivo", "Suspendido"], key="f_est_nad")
                with f2:
                    cats_unicas = sorted([str(c) for c in df_nadadores_nom["categoria"].dropna().unique() if c])
                    cat_f = st.selectbox("Categoría:", ["Todas"] + cats_unicas, key="f_cat_nad")
                with f3:
                    busq_f = st.text_input("🔍 Buscar Atleta:", placeholder="Nombre, cédula...", key="f_busq_nad")

                df_nad_filtrado = df_nadadores_nom.copy()
                if est_f != "Todos":
                    df_nad_filtrado = df_nad_filtrado[df_nad_filtrado["estatus"] == est_f]
                if cat_f != "Todas":
                    df_nad_filtrado = df_nad_filtrado[df_nad_filtrado["categoria"] == cat_f]
                if busq_f:
                    df_nad_filtrado = df_nad_filtrado[
                        df_nad_filtrado["nombre"].astype(str).str.contains(busq_f, case=False, na=False) |
                        df_nad_filtrado["cedula"].astype(str).str.contains(busq_f, case=False, na=False)
                    ]

                k1, k2, k3 = st.columns(3)
                k1.metric("Total Nadadores", len(df_nadadores_nom))
                k2.metric("🟢 Activos", len(df_nadadores_nom[df_nadadores_nom["estatus"] == "Activo"]))
                k3.metric("⚪ Inactivos / Otros", len(df_nadadores_nom[df_nadadores_nom["estatus"] != "Activo"]))

                cols_disp_nad = ["nombre", "cedula", "email", "telefono", "fecha_nacimiento", "categoria", "estatus"]
                df_nad_disp = df_nad_filtrado[[c for c in cols_disp_nad if c in df_nad_filtrado.columns]].copy()
                df_nad_disp.columns = ["Atleta", "Cédula", "Correo Electrónico", "Teléfono", "Fecha Nac.", "Categoría", "Estatus"]
                st.dataframe(df_nad_disp, use_container_width=True, hide_index=True)

        # NÓMINA TÉCNICA (ENTRENADORES Y HEAD COACH)
        with tab_nomina_tecnica:
            roles_tecnicos = ["Entrenador", "Head Coach", "Club"]
            df_tecnica = df_todos_usuarios[df_todos_usuarios["rol"].isin(roles_tecnicos)].copy() if not df_todos_usuarios.empty else pd.DataFrame()

            if df_tecnica.empty:
                st.info("No hay personal técnico registrado.")
            else:
                cols_tec = ["nombre", "rol", "cedula", "email", "telefono", "estatus"]
                df_tec_disp = df_tecnica[[c for c in cols_tec if c in df_tecnica.columns]].copy()
                df_tec_disp.columns = ["Nombre y Apellido", "Rol Técnico", "Cédula", "Correo Electrónico", "Teléfono", "Estatus"]
                st.dataframe(df_tec_disp, use_container_width=True, hide_index=True)

    # =========================================================================
    # SUB-PESTAÑA 3: COMUNICADOS Y CORRESPONDENCIA
    # =========================================================================
    with subtab_comunicacion:
        st.markdown("## 📜 Emisión de Documentos y Comunicación Oficial")
        st.caption("Preparación de memorandums, avisos y comunicados con exportación a PDF.")
    
        tab_editor, tab_export_envio = st.tabs(["✍️ Editor y Maquetación", "📤 Exportación y Despacho"])
    
        with tab_editor:
            plantillas = {
                "Memorandum Interno": {
                    "tipo": "Memorandum",
                    "de": "Comisión Técnica de Natación",
                    "para": "Entrenadores y Personal Técnico",
                    "asunto": "Ajuste de Horarios de Entrenamiento en Piscina Olímpica",
                    "secciones": [
                        {"subtitulo": "1. Modificación de Horarios", "texto": "Se informa que los entrenamientos iniciarán a las 5:30 AM."},
                        {"subtitulo": "2. Control de Asistencia", "texto": "Es obligatorio registrar la asistencia en la app."}
                    ],
                    "clausulas": "* Cumplimiento obligatorio."
                }
            }
    
            col_p1, col_p2 = st.columns([3, 1])
            with col_p1:
                plantilla_sel = st.selectbox("📂 Cargar Plantilla Base:", list(plantillas.keys()), key="select_plantilla_comunicaciones")
            with col_p2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🔄 Cargar Plantilla", use_container_width=True, key="btn_cargar_plantilla_com"):
                    p_data = plantillas[plantilla_sel]
                    st.session_state.meta_memo = {
                        "codigo": f"DOC-2026-{pd.Timestamp.now().strftime('%m%d%H%M')}",
                        "tipo": p_data["tipo"],
                        "para": p_data["para"],
                        "de": p_data["de"],
                        "fecha": pd.Timestamp.now().strftime("%d/%m/%Y"),
                        "asunto": p_data["asunto"]
                    }
                    st.session_state.cuerpo_memo_secciones = p_data["secciones"]
                    st.session_state.clausulas_memo = p_data["clausulas"]
                    st.rerun()
    
            if "meta_memo" not in st.session_state:
                st.session_state.meta_memo = {"codigo": "MEMO-2026-001", "tipo": "Memorandum", "para": "", "de": "", "fecha": pd.Timestamp.now().strftime("%d/%m/%Y"), "asunto": ""}
            if "cuerpo_memo_secciones" not in st.session_state:
                st.session_state.cuerpo_memo_secciones = [{"subtitulo": "1. Asunto Principal", "texto": ""}]
            if "clausulas_memo" not in st.session_state:
                st.session_state.clausulas_memo = ""
    
            meta = st.session_state.meta_memo
            with st.container(border=True):
                st.markdown("#### 🏛️ Datos de Cabecera")
                c1, c2, c3 = st.columns(3)
                with c1:
                    meta["codigo"] = st.text_input("N° Documento:", value=meta.get("codigo", "MEMO-2026-001"), key="input_memo_codigo")
                    meta["tipo"] = st.selectbox("Tipo:", ["Memorandum", "Comunicado Oficial", "Resolución"], index=0, key="select_memo_tipo")
                with c2:
                    meta["para"] = st.text_input("Para:", value=meta.get("para", ""), key="input_memo_para")
                    meta["de"] = st.text_input("De:", value=meta.get("de", ""), key="input_memo_de")
                with c3:
                    meta["fecha"] = st.text_input("Fecha:", value=meta.get("fecha", ""), key="input_memo_fecha")
                    meta["asunto"] = st.text_input("Asunto:", value=meta.get("asunto", ""), key="input_memo_asunto")
                st.session_state.meta_memo = meta
    
            secciones = st.session_state.cuerpo_memo_secciones
            for idx, sec in enumerate(secciones):
                with st.container(border=True):
                    col_s1, col_s2 = st.columns([5, 1])
                    with col_s1:
                        sec["subtitulo"] = st.text_input(f"Subtítulo {idx+1}:", value=sec.get("subtitulo", ""), key=f"sub_com_{idx}")
                        sec["texto"] = st.text_area(f"Texto {idx+1}:", value=sec.get("texto", ""), height=80, key=f"txt_com_{idx}")
                    with col_s2:
                        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                        if st.button("🗑️", key=f"del_sec_com_{idx}") and len(secciones) > 1:
                            secciones.pop(idx)
                            st.session_state.cuerpo_memo_secciones = secciones
                            st.rerun()
    
            if st.button("➕ Agregar Nueva Sección", key="btn_add_sec_com"):
                secciones.append({"subtitulo": f"{len(secciones)+1}. Nueva Sección", "texto": ""})
                st.session_state.cuerpo_memo_secciones = secciones
                st.rerun()
    
            st.session_state.clausulas_memo = st.text_area("Cláusulas / Disposiciones:", value=st.session_state.clausulas_memo, height=70, key="area_clausulas_com")
    
        with tab_export_envio:
            pdf_bytes = generar_pdf_memorandum_nativo()
            nombre_pdf = f"{meta.get('codigo', 'documento')}.pdf"
            
            st.download_button("📥 Descargar Documento PDF", data=pdf_bytes, file_name=nombre_pdf, mime="application/pdf", type="primary", use_container_width=True)

    # =========================================================================
    # SUB-PESTAÑA 4: RESPALDOS DE BASE DE DATOS (MÓDULO DE SEGURIDAD)
    # =========================================================================
    with subtab_respaldos:
        st.markdown("### 💾 Respaldo y Portabilidad de Datos del Club")
        st.caption("Herramientas autónomas de backup por tabla individual, archivo ZIP global y expedientes individuales de traslado.")

        col_r1, col_r2, col_r3 = st.columns(3)

        # MODALIDAD 1: TABLA INDIVIDUAL DE SUPABASE
        with col_r1:
            with st.container(border=True):
                st.markdown("##### 📄 1. Exportar Tabla Individual")
                st.caption("Descarga una tabla específica de Supabase en formato CSV.")
                
                tabla_sel_resp = st.selectbox(
                    "Seleccionar Tabla:",
                    ["usuarios", "invitaciones", "control_pagos", "tiempos", "asistencias", "documentos_oficiales"],
                    key="select_tabla_individual_resp"
                )
                
                if st.button("🔍 Cargar Datos de Tabla", use_container_width=True, key="btn_cargar_tabla_resp"):
                    try:
                        res_t = supabase.table(tabla_sel_resp).select("*").execute()
                        if res_t.data:
                            df_res_t = pd.DataFrame(res_t.data)
                            st.download_button(
                                label=f"📥 Descargar `{tabla_sel_resp}.csv`",
                                data=df_res_t.to_csv(index=False).encode('utf-8-sig'),
                                file_name=f"{tabla_sel_resp}_{datetime.date.today()}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        else:
                            st.warning("La tabla seleccionada no contiene registros.")
                    except Exception as e:
                        st.error(f"Error al consultar tabla: {e}")

        # MODALIDAD 2: ARCHIVO ZIP COMPLETO DE LA BASE DE DATOS
        with col_r2:
            with st.container(border=True):
                st.markdown("##### 📦 2. Backup Completo (ZIP)")
                st.caption("Genera un archivo comprimido ZIP con todas las tablas del sistema.")
                
                if st.button("⚙️ Generar Backup Completo", use_container_width=True, key="btn_generar_zip_bd"):
                    with st.spinner("Generando archivo ZIP de la BD..."):
                        zip_buffer = generar_zip_bd_completa(supabase)
                        st.download_button(
                            label="📥 Descargar Backup General (.zip)",
                            data=zip_buffer,
                            file_name=f"Backup_BD_Club_{datetime.date.today()}.zip",
                            mime="application/zip",
                            type="primary",
                            use_container_width=True
                        )

        # MODALIDAD 3: EXPEDIENTE DE TRASLADO INDIVIDUAL DEL ATLETA
        with col_r3:
            with st.container(border=True):
                st.markdown("##### 🏊 3. Expediente del Atleta")
                st.caption("Paquete de datos de un atleta para archivo personal o traslado a otro club.")
                
                try:
                    res_at_resp = supabase.table("usuarios").select("id, nombre, cedula").eq("rol", "Nadador").execute()
                    list_atl_resp = res_at_resp.data if res_at_resp.data else []
                except Exception:
                    list_atl_resp = []

                if list_atl_resp:
                    atleta_exp_id = st.selectbox(
                        "Seleccionar Atleta:",
                        options=[a["id"] for a in list_atl_resp],
                        format_func=lambda x: next(f"{a['nombre']} ({a.get('cedula', 'Sin Doc')})" for a in list_atl_resp if a["id"] == x),
                        key="select_atleta_expediente"
                    )
                    
                    nom_atl_exp = next((a["nombre"] for a in list_atl_resp if a["id"] == atleta_exp_id), "Atleta")
                    
                    if st.button("📄 Empaquetar Expediente", use_container_width=True, key="btn_emp_exp_atleta"):
                        with st.spinner(f"Empaquetando expediente de {nom_atl_exp}..."):
                            zip_atleta = generar_expediente_atleta_zip(supabase, atleta_exp_id, nom_atl_exp)
                            st.download_button(
                                label="📥 Descargar Expediente Atleta (.zip)",
                                data=zip_atleta,
                                file_name=f"Expediente_{nom_atl_exp.replace(' ', '_')}_{datetime.date.today()}.zip",
                                mime="application/zip",
                                type="primary",
                                use_container_width=True
                            )
                else:
                    st.caption("No hay atletas disponibles para empaquetar.")
