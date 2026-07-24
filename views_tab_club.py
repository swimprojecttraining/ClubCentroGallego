# views_tab_club.py (Módulo de Gestión Administrativa del Club)
import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import urllib.parse
import pandas as pd
import streamlit as st

from formulas_lib_funciones import (
    calcular_categoria_competencia,
    enviar_email,
    hash_password,
)
from pdf_memo_utility import generar_pdf_memorandum_nativo


def enviar_correo_con_pdf(
    destinatario: str,
    asunto: str,
    cuerpo: str,
    pdf_bytes: bytes,
    nombre_archivo_pdf: str,
):
    """Envía un correo electrónico institucional con un PDF adjunto en memoria."""
    try:
        smtp_server = st.secrets.get("smtp", {}).get("server", "smtp.gmail.com")
        smtp_port = int(st.secrets.get("smtp", {}).get("port", 587))
        sender_email = st.secrets.get("smtp", {}).get(
            "email", "tu_club@gmail.com"
        )
        sender_password = st.secrets.get("smtp", {}).get(
            "password", "tu_app_password"
        )

        msg = MIMEMultipart()
        msg["From"] = f"Centro Gallego - Natación <{sender_email}>"
        msg["To"] = destinatario
        msg["Subject"] = asunto

        msg.attach(MIMEText(cuerpo, "plain"))

        adjunto = MIMEApplication(pdf_bytes, _subtype="pdf")
        adjunto.add_header(
            "Content-Disposition",
            "attachment",
            filename=nombre_archivo_pdf,
        )
        msg.attach(adjunto)

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True, "Correo enviado con éxito."
    except Exception as e:
        return False, f"Error al enviar correo: {str(e)}"


def renderizar_tab_club():
    """Pestaña principal de administración del club.

    Entorno autónomo para pre-registro, control financiero, plantilla técnica y
    comunicaciones.
    """
    st.markdown("## 🏛️ Centro de Control Administrativo")
    st.caption(
        "Gestión de altas, control financiero de cuotas, nómina técnica y correspondencia oficial."
    )
    st.markdown("---")

    supabase = st.session_state.get("supabase")
    if not supabase:
        st.error(
            "❌ Error de conexión: No se encontró la instancia de Supabase en la sesión."
        )
        return

    # Sub-navegación estructurada
    (
        subtab_alta,
        subtab_pagos,
        subtab_atletas,
        subtab_comunicacion,
    ) = st.tabs([
        "📝 Pre-Registro y Altas",
        "💳 Control Financiero y Pagos",
        "👥 Plantilla y Atletas",
        "📄 Comunicados y Correspondencia",
    ])

    # =========================================================================
    # SUB-PESTAÑA 1: PRE-REGISTRO Y ALTAS DE INTEGRANTES
    # =========================================================================
    with subtab_alta:
        st.markdown("### 📝 Pre-Registro y Ficha Digital de Integrantes")
        st.info(
            " Complete los campos obligatorios (*). Los datos de contacto y credenciales pueden dejarse en blanco "
            "para que el integrante los complete durante su proceso de activación."
        )

        with st.form("form_alta_usuario_club", clear_on_submit=True):
            col1, col2 = st.columns(2)

            # --- COLUMNA 1: DATOS OBLIGATORIOS DE NÓMINA ---
            with col1:
                st.markdown("#### 📌 Datos de Nómina (Obligatorios)")

                cedula = st.text_input(
                    "Cédula / Identificador *",
                    placeholder="Ej: V-12345678",
                    help="Llave única del usuario.",
                )

                nombre = st.text_input(
                    "Nombre Completo *", placeholder="Ej: Ximena Pérez"
                )

                genero = st.selectbox(
                    "Género *",
                    options=["F", "M"],
                    index=0,
                    help="Requerido para la categorización deportiva.",
                )

                fecha_nacimiento = st.date_input(
                    "Fecha de Nacimiento *",
                    value=None,
                    help="Determinante para la categoría de competencia.",
                )

                rol = st.selectbox(
                    "Rol Institucional *",
                    options=[
                        "Nadador",
                        "Entrenador",
                        "Head Coach",
                        "Club",
                        "Administrador",
                    ],
                    index=0,
                )

            # --- COLUMNA 2: CONTACTO Y CREDENCIALES (OPCIONALES) ---
            with col2:
                st.markdown("#### 🔑 Contacto y Credenciales (Opcionales)")

                email = st.text_input(
                    "Correo Electrónico",
                    placeholder="ejemplo@correo.com (Opcional)",
                )

                telefono = st.text_input(
                    "Teléfono de Contacto",
                    placeholder="+584121234567 (Opcional)",
                )

                usuario = st.text_input(
                    "Nombre de Usuario",
                    placeholder="Ej: ximena_perez (Opcional)",
                )

                contrasena = st.text_input(
                    "Contraseña Inicial",
                    type="password",
                    placeholder="Mínimo 6 caracteres (Opcional)",
                )

                estatus = st.selectbox(
                    "Estatus Inicial *",
                    options=[
                        "Pendiente",
                        "Activo",
                        "Inactivo",
                        "Retirado",
                        "Trasladado",
                    ],
                    index=0,
                    help="Se recomienda 'Pendiente' para cuentas por activar.",
                )

            btn_guardar = st.form_submit_button(
                "💾 Registrar / Emitir Ficha", use_container_width=True
            )

        if btn_guardar:
            errores = []
            if not cedula.strip():
                errores.append("La Cédula es obligatoria.")
            if not nombre.strip():
                errores.append("El Nombre Completo es obligatorio.")
            if not fecha_nacimiento:
                errores.append("La Fecha de Nacimiento es obligatoria.")

            if errores:
                for err in errores:
                    st.error(f"⚠️ {err}")
            else:
                # Saneamiento de variables (Vacíos -> None / NULL)
                cedula_val = cedula.strip().upper()
                nombre_val = nombre.strip().title()
                email_val = email.strip().lower() if email.strip() else None
                telefono_val = telefono.strip() if telefono.strip() else None
                usuario_val = usuario.strip() if usuario.strip() else None

                # Hash seguro de contraseña mediante librería centralizada
                contrasena_val = (
                    hash_password(contrasena.strip())
                    if contrasena.strip()
                    else None
                )

                payload = {
                    "cedula": cedula_val,
                    "nombre": nombre_val,
                    "genero": genero,
                    "fecha_nacimiento": str(fecha_nacimiento),
                    "rol": rol,
                    "estatus": estatus,
                    "email": email_val,
                    "telefono": telefono_val,
                    "usuario": usuario_val,
                    "contrasena": contrasena_val,
                }

                try:
                    respuesta = (
                        supabase.table("usuarios").insert(payload).execute()
                    )
                    if respuesta.data:
                        st.success(
                            f"✅ **{nombre_val}** registrado exitosamente con Cédula **{cedula_val}** y estatus **{estatus}**."
                        )

                        # Auto-envío de notificación si se suministró correo y el estatus es Pendiente
                        if email_val and estatus == "Pendiente":
                            cuerpo_inv = (
                                f"<h3>¡Hola, {nombre_val}!</h3>"
                                f"<p>Has sido registrado en el sistema del Club en estatus PENDIENTE. "
                                f"Por favor contacta al administrador o ingresa a la plataforma para completar tu activación.</p>"
                            )
                            enviar_email(
                                email_val,
                                "Notificación de Pre-Registro - Club de Natación",
                                cuerpo_inv,
                            )
                            st.info(
                                f"📩 Se ha enviado una notificación de pre-registro a **{email_val}**."
                            )

                        st.rerun()
                except Exception as e:
                    msg_error = str(e)
                    if (
                        "usuarios_cedula_key" in msg_error
                        or "duplicate key" in msg_error
                    ):
                        st.error(
                            f"⛔ Ya existe un integrante registrado con la Cédula **{cedula_val}**."
                        )
                    elif "usuarios_usuario_key" in msg_error:
                        st.error(
                            f"⛔ El nombre de usuario **'{usuario_val}'** ya está en uso."
                        )
                    else:
                        st.error(f"❌ Error en base de datos: {msg_error}")

    # =========================================================================
    # SUB-PESTAÑA 2: CONTROL FINANCIERO Y PAGOS
    # =========================================================================
    with subtab_pagos:
        st.markdown("### 💰 Control de Cuotas y Solvencias")

        col_temp, col_mes, col_estado, col_buscar = st.columns([1, 1, 1, 2])

        año_actual = datetime.date.today().year
        mes_actual = datetime.date.today().month

        with col_temp:
            temporada_sel = st.number_input(
                "Temporada:",
                min_value=2020,
                max_value=2030,
                value=año_actual,
                key="club_temp",
            )

        with col_mes:
            mes_sel = st.selectbox(
                "Mes:",
                ["Todos"] + list(range(1, 13)),
                index=mes_actual,
                key="club_mes",
            )

        with col_estado:
            estado_sel = st.selectbox(
                "Estatus:",
                ["Todos", "Solvente", "Pendiente", "Exonerado"],
                key="club_est",
            )

        with col_buscar:
            busqueda_texto = st.text_input(
                "🔍 Buscar Atleta:",
                placeholder="Nombre o usuario...",
                key="club_busq",
            )

        try:
            res_usuarios = (
                supabase.table("usuarios")
                .select("id, nombre, usuario, estatus, email")
                .eq("rol", "Nadador")
                .execute()
            )
            df_nadadores = (
                pd.DataFrame(res_usuarios.data)
                if res_usuarios.data
                else pd.DataFrame()
            )
        except Exception as e:
            st.error(f"Error al cargar lista de nadadores: {e}")
            df_nadadores = pd.DataFrame()

        if df_nadadores.empty:
            st.warning("No hay nadadores registrados en la base de datos.")
        else:
            try:
                res_pagos = (
                    supabase.table("control_pagos")
                    .select("*")
                    .eq("temporada", temporada_sel)
                    .execute()
                )
                df_pagos = (
                    pd.DataFrame(res_pagos.data)
                    if res_pagos.data
                    else pd.DataFrame()
                )
            except Exception:
                df_pagos = pd.DataFrame()

            cols_mostrar = [
                "nombre",
                "usuario",
                "estado_pago",
                "monto",
                "fecha_pago",
                "referencia_pago",
                "observaciones",
            ]

            if not df_pagos.empty:
                df_pagos_filtrado = (
                    df_pagos[df_pagos["mes"] == int(mes_sel)]
                    if mes_sel != "Todos"
                    else df_pagos
                )
                df_merged = pd.merge(
                    df_nadadores,
                    df_pagos_filtrado,
                    left_on="id",
                    right_on="usuario_id",
                    how="left",
                )
            else:
                df_merged = df_nadadores.copy()
                df_merged["estado_pago"] = "Pendiente"
                df_merged["monto"] = 0.0
                df_merged["fecha_pago"] = None
                df_merged["referencia_pago"] = ""
                df_merged["observaciones"] = ""

            for col in cols_mostrar:
                if col not in df_merged.columns:
                    df_merged[col] = (
                        "Pendiente"
                        if col == "estado_pago"
                        else (0.0 if col == "monto" else "")
                    )

            df_merged["estado_pago"] = df_merged["estado_pago"].fillna(
                "Pendiente"
            )
            df_merged["monto"] = df_merged["monto"].fillna(0.0)

            if estado_sel != "Todos":
                df_merged = df_merged[df_merged["estado_pago"] == estado_sel]

            if busqueda_texto:
                df_merged = df_merged[
                    df_merged["nombre"].str.contains(
                        busqueda_texto, case=False, na=False
                    )
                    | df_merged["usuario"].str.contains(
                        busqueda_texto, case=False, na=False
                    )
                ]

            # Métricas
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Recaudado ($)", f"${df_merged['monto'].sum():,.2f}")
            m2.metric(
                "🟢 Solventes",
                len(df_merged[df_merged["estado_pago"] == "Solvente"]),
            )
            m3.metric(
                "🔴 Pendientes",
                len(df_merged[df_merged["estado_pago"] == "Pendiente"]),
            )
            m4.metric(
                "⚪ Exonerados",
                len(df_merged[df_merged["estado_pago"] == "Exonerado"]),
            )

            st.markdown("---")

            df_display = df_merged[cols_mostrar].copy()
            df_display.columns = [
                "Atleta",
                "Usuario",
                "Estado",
                "Monto ($)",
                "Fecha Pago",
                "N° Referencia",
                "Observaciones",
            ]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            # Formulario Registrar Pago
            with st.expander(
                "📝 **Registrar / Actualizar Pago de Atleta**", expanded=False
            ):
                with st.form("form_registrar_pago"):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c1:
                        atleta_id_sel = st.selectbox(
                            "Seleccionar Atleta:",
                            options=df_nadadores["id"].tolist(),
                            format_func=lambda x: df_nadadores[
                                df_nadadores["id"] == x
                            ]["nombre"].values[0],
                        )
                    with c2:
                        mes_pago = st.selectbox(
                            "Mes Afectado:",
                            list(range(1, 13)),
                            index=mes_actual - 1,
                        )
                    with c3:
                        monto_pago = st.number_input(
                            "Monto Recibido ($):", min_value=0.0, step=5.0
                        )

                    c4, c5, c6 = st.columns([1, 1, 2])
                    with c4:
                        nuevo_estado = st.selectbox(
                            "Estatus de Pago:",
                            ["Solvente", "Pendiente", "Exonerado"],
                        )
                    with c5:
                        fecha_pago_val = st.date_input(
                            "Fecha del Pago:", value=datetime.date.today()
                        )
                    with c6:
                        ref_pago_val = st.text_input(
                            "N° Referencia / Comprobante:",
                            placeholder="Ej: Transf-998231",
                        )

                    obs_pago_val = st.text_input("Observaciones / Notas:")
                    btn_guardar_pago = st.form_submit_button(
                        "💾 Registrar Estatus Administrativo",
                        use_container_width=True,
                    )

                    if btn_guardar_pago:
                        registro_pago = {
                            "usuario_id": atleta_id_sel,
                            "temporada": temporada_sel,
                            "mes": mes_pago,
                            "monto": monto_pago,
                            "estado_pago": nuevo_estado,
                            "fecha_pago": str(fecha_pago_val),
                            "referencia_pago": ref_pago_val,
                            "observaciones": obs_pago_val,
                        }
                        try:
                            supabase.table("control_pagos").upsert(
                                registro_pago
                            ).execute()
                            st.success(
                                "✅ Pago y estatus administrativo actualizados correctamente."
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al registrar pago en BD: {e}")

    # =========================================================================
    # SUB-PESTAÑA 3: ESTADO DE PLANTILLA Y ATLETAS
    # =========================================================================
    with subtab_atletas:
        st.markdown("### 👥 Gestión de Plantilla y Atletas")
        st.caption(
            "Control de atletas activos, pendientes y actualización de estatus técnico."
        )

        try:
            res_plantilla = (
                supabase.table("usuarios")
                .select("id, cedula, nombre, email, estatus, fecha_nacimiento")
                .eq("rol", "Nadador")
                .execute()
            )
            df_plantilla = (
                pd.DataFrame(res_plantilla.data)
                if res_plantilla.data
                else pd.DataFrame()
            )
        except Exception as e:
            st.error(f"Error al cargar la plantilla de atletas: {e}")
            df_plantilla = pd.DataFrame()

        if df_plantilla.empty:
            st.warning("No hay atletas registrados en el sistema.")
        else:
            df_plantilla["categoria"] = df_plantilla["fecha_nacimiento"].apply(
                lambda f: (
                    calcular_categoria_competencia(f)[0]
                    if pd.notna(f) and f
                    else "Sin Fecha"
                )
            )

            col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
            with col_f1:
                estatus_filtro = st.selectbox(
                    "Estatus:",
                    [
                        "Todos",
                        "Pendiente",
                        "Activo",
                        "Inactivo",
                        "Suspendido",
                        "Retirado",
                    ],
                    key="filtro_estatus_plantilla",
                )
            with col_f2:
                cats_unicas = sorted([
                    str(c)
                    for c in df_plantilla["categoria"].dropna().unique()
                    if c
                ])
                categoria_filtro = st.selectbox(
                    "Categoría:",
                    ["Todas"] + cats_unicas,
                    key="filtro_cat_plantilla",
                )
            with col_f3:
                busqueda_plantilla = st.text_input(
                    "🔍 Buscar:",
                    placeholder="Cédula, Nombre o correo...",
                    key="busq_plantilla",
                )

            df_p_filtrado = df_plantilla.copy()
            if estatus_filtro != "Todos":
                df_p_filtrado = df_p_filtrado[
                    df_p_filtrado["estatus"] == estatus_filtro
                ]
            if categoria_filtro != "Todas":
                df_p_filtrado = df_p_filtrado[
                    df_p_filtrado["categoria"] == categoria_filtro
                ]
            if busqueda_plantilla:
                df_p_filtrado = df_p_filtrado[
                    df_p_filtrado["nombre"].str.contains(
                        busqueda_plantilla, case=False, na=False
                    )
                    | df_p_filtrado["cedula"].str.contains(
                        busqueda_plantilla, case=False, na=False
                    )
                    | df_p_filtrado["email"].str.contains(
                        busqueda_plantilla, case=False, na=False
                    )
                ]

            k1, k2, k3 = st.columns(3)
            k1.metric("Total Atletas Registrados", len(df_plantilla))
            k2.metric(
                "🟢 Atletas Activos",
                len(df_plantilla[df_plantilla["estatus"] == "Activo"]),
            )
            k3.metric(
                "⏳ Pendientes por Activar",
                len(df_plantilla[df_plantilla["estatus"] == "Pendiente"]),
            )

            st.markdown("---")

            cols_p_mostrar = [
                "cedula",
                "nombre",
                "email",
                "fecha_nacimiento",
                "categoria",
                "estatus",
            ]
            cols_disponibles = [
                c for c in cols_p_mostrar if c in df_p_filtrado.columns
            ]
            df_p_display = df_p_filtrado[cols_disponibles].copy()

            df_p_display.columns = [
                {
                    "cedula": "Cédula",
                    "nombre": "Atleta",
                    "email": "Correo Electrónico",
                    "fecha_nacimiento": "Fecha Nacimiento",
                    "categoria": "Categoría",
                    "estatus": "Estatus",
                }.get(c, c)
                for c in cols_disponibles
            ]

            st.dataframe(df_p_display, use_container_width=True, hide_index=True)

            with st.expander(
                "⚙️ **Actualizar Estatus Institucional de Atleta**",
                expanded=False,
            ):
                with st.form("form_actualizar_atleta_estatus"):
                    atleta_mod_id = st.selectbox(
                        "Seleccionar Atleta:",
                        options=df_plantilla["id"].tolist(),
                        format_func=lambda x: f"{df_plantilla[df_plantilla['id'] == x]['nombre'].values[0]} ({df_plantilla[df_plantilla['id'] == x]['cedula'].values[0]})",
                    )
                    nuevo_estatus_atleta = st.selectbox(
                        "Nuevo Estatus Institucional:",
                        [
                            "Pendiente",
                            "Activo",
                            "Inactivo",
                            "Suspendido",
                            "Retirado",
                        ],
                    )
                    btn_act_atleta = st.form_submit_button(
                        "💾 Guardar Cambios", use_container_width=True
                    )

                    if btn_act_atleta:
                        try:
                            supabase.table("usuarios").update(
                                {"estatus": nuevo_estatus_atleta}
                            ).eq("id", atleta_mod_id).execute()
                            st.success(
                                "✅ Estatus del atleta actualizado exitosamente."
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar en BD: {e}")

    # =========================================================================
    # SUB-PESTAÑA 4: COMUNICADOS Y CORRESPONDENCIA
    # =========================================================================
    with subtab_comunicacion:
        st.markdown("## 📜 Emisión de Documentos y Comunicación Oficial")
        st.caption(
            "Preparación de memorandums, avisos y comunicados en papel membrete con exportación a PDF y envío directo."
        )

        tab_editor, tab_export_envio = st.tabs(
            ["✍️ Editor y Maquetación", "📤 Exportación y Despacho"]
        )

        # TAB 1: EDITOR
        with tab_editor:
            plantillas = {
                "Memorandum Interno": {
                    "tipo": "Memorandum",
                    "de": "Comisión Técnica de Natación",
                    "para": "Entrenadores y Personal Técnico",
                    "asunto": (
                        "Ajuste de Horarios de Entrenamiento en Piscina Olímpica"
                    ),
                    "secciones": [
                        {
                            "subtitulo": "1. Modificación de Horarios",
                            "texto": (
                                "Se informa que a partir del próximo lunes los"
                                " entrenamientos matutinos iniciarán a las 5:30"
                                " AM."
                            ),
                        },
                        {
                            "subtitulo": "2. Control de Asistencia",
                            "texto": (
                                "Es obligatorio registrar la toma de asistencia"
                                " en la aplicación al finalizar cada bloque."
                            ),
                        },
                    ],
                    "clausulas": (
                        "* El incumplimiento reiterado afectará la asignación"
                        " de materiales."
                    ),
                },
                "Comunicado Oficial / Convocatoria": {
                    "tipo": "Comunicado Oficial",
                    "de": "Junta Directiva / Subcomisión de Natación",
                    "para": "Atletas y Representantes",
                    "asunto": "Convocatoria Chequeo Nacional de Marcas Mínimas",
                    "secciones": [
                        {
                            "subtitulo": "1. Convocatoria",
                            "texto": (
                                "Se convoca formalmente a todos los atletas"
                                " clasificados a presentarse al chequeo técnico."
                            ),
                        },
                        {
                            "subtitulo": "2. Requisitos de Inscripción",
                            "texto": (
                                "Tener la solvencia administrativa al día y"
                                " entregar copia de la cédula de identidad."
                            ),
                        },
                    ],
                    "clausulas": (
                        "* Atletas sin chequeo formal no podrán optar a avales"
                        " para campeonatos nacionales."
                    ),
                },
            }

            col_p1, col_p2 = st.columns([3, 1])
            with col_p1:
                plantilla_sel = st.selectbox(
                    "📂 Cargar Plantilla Base:",
                    list(plantillas.keys()),
                    key="select_plantilla_comunicaciones",
                )
            with col_p2:
                st.markdown(
                    "<div style='height: 28px;'></div>", unsafe_allow_html=True
                )
                if st.button(
                    "🔄 Cargar Plantilla",
                    use_container_width=True,
                    key="btn_cargar_plantilla_com",
                ):
                    p_data = plantillas[plantilla_sel]
                    st.session_state.meta_memo = {
                        "codigo": (
                            f"DOC-2026-{pd.Timestamp.now().strftime('%m%d%H%M')}"
                        ),
                        "tipo": p_data["tipo"],
                        "para": p_data["para"],
                        "de": p_data["de"],
                        "fecha": pd.Timestamp.now().strftime("%d/%m/%Y"),
                        "asunto": p_data["asunto"],
                    }
                    st.session_state.cuerpo_memo_secciones = p_data["secciones"]
                    st.session_state.clausulas_memo = p_data["clausulas"]
                    st.success("Plantilla cargada correctamente.")
                    st.rerun()

            if "meta_memo" not in st.session_state:
                st.session_state.meta_memo = {
                    "codigo": "MEMO-2026-001",
                    "tipo": "Memorandum",
                    "para": "",
                    "de": "",
                    "fecha": pd.Timestamp.now().strftime("%d/%m/%Y"),
                    "asunto": "",
                }

            if "cuerpo_memo_secciones" not in st.session_state:
                st.session_state.cuerpo_memo_secciones = [
                    {"subtitulo": "1. Asunto Principal", "texto": ""}
                ]

            if "clausulas_memo" not in st.session_state:
                st.session_state.clausulas_memo = ""

            meta = st.session_state.meta_memo

            with st.container(border=True):
                st.markdown("#### 🏛️ Datos de Cabecera")
                c1, c2, c3 = st.columns(3)
                with c1:
                    meta["codigo"] = st.text_input(
                        "N° Documento:",
                        value=meta.get("codigo", "MEMO-2026-001"),
                        key="input_memo_codigo",
                    )
                    meta["tipo"] = st.selectbox(
                        "Tipo:",
                        ["Memorandum", "Comunicado Oficial", "Resolución", "Aviso"],
                        index=0,
                        key="select_memo_tipo",
                    )
                with c2:
                    meta["para"] = st.text_input(
                        "Para:",
                        value=meta.get("para", ""),
                        key="input_memo_para",
                    )
                    meta["de"] = st.text_input(
                        "De:", value=meta.get("de", ""), key="input_memo_de"
                    )
                with c3:
                    meta["fecha"] = st.text_input(
                        "Fecha:",
                        value=meta.get("fecha", ""),
                        key="input_memo_fecha",
                    )
                    meta["asunto"] = st.text_input(
                        "Asunto:",
                        value=meta.get("asunto", ""),
                        key="input_memo_asunto",
                    )

                st.session_state.meta_memo = meta

            st.markdown("#### 📝 Cuerpo del Documento (Secciones Dinámicas)")
            secciones = st.session_state.cuerpo_memo_secciones

            for idx, sec in enumerate(secciones):
                with st.container(border=True):
                    col_s1, col_s2 = st.columns([5, 1])
                    with col_s1:
                        sec["subtitulo"] = st.text_input(
                            f"Subtítulo {idx+1}:",
                            value=sec.get("subtitulo", ""),
                            key=f"sub_com_{idx}",
                        )
                        sec["texto"] = st.text_area(
                            f"Texto {idx+1}:",
                            value=sec.get("texto", ""),
                            height=90,
                            key=f"txt_com_{idx}",
                        )
                    with col_s2:
                        st.markdown(
                            "<div style='height: 28px;'></div>",
                            unsafe_allow_html=True,
                        )
                        if (
                            st.button("🗑️", key=f"del_sec_com_{idx}")
                            and len(secciones) > 1
                        ):
                            secciones.pop(idx)
                            st.session_state.cuerpo_memo_secciones = secciones
                            st.rerun()

            if st.button("➕ Agregar Nueva Sección", key="btn_add_sec_com"):
                secciones.append({
                    "subtitulo": f"{len(secciones)+1}. Nueva Sección",
                    "texto": "",
                })
                st.session_state.cuerpo_memo_secciones = secciones
                st.rerun()

            st.markdown("#### 📜 Cláusulas y Disposiciones Finales")
            st.session_state.clausulas_memo = st.text_area(
                "Disposiciones reglamentarias o notas al pie:",
                value=st.session_state.clausulas_memo,
                height=80,
                key="area_clausulas_com",
            )

        # TAB 2: EXPORTACIÓN
        with tab_export_envio:
            st.markdown("### 📤 Generación, Exportación y Despacho Directo")

            pdf_bytes = generar_pdf_memorandum_nativo()
            nombre_pdf = f"{meta.get('codigo', 'documento')}.pdf"

            col_d1, col_d2 = st.columns([2, 2])
            with col_d1:
                st.download_button(
                    label="📥 Descargar Documento PDF (8.5 x 11 in)",
                    data=pdf_bytes,
                    file_name=nombre_pdf,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                    key="btn_download_pdf_com",
                )
            with col_d2:
                if st.button(
                    "💾 Guardar Historial en Supabase",
                    use_container_width=True,
                    key="btn_guardar_db_com",
                ):
                    try:
                        payload = {
                            "codigo_correlativo": meta.get("codigo"),
                            "tipo_documento": meta.get("tipo"),
                            "titulo": meta.get("asunto"),
                            "para_destinatario": meta.get("para"),
                            "de_emisor": meta.get("de"),
                            "asunto": meta.get("asunto"),
                            "contenido_json": (
                                st.session_state.cuerpo_memo_secciones
                            ),
                            "clausulas_texto": st.session_state.clausulas_memo,
                        }
                        supabase.table("documentos_oficiales").upsert(
                            payload, on_conflict="codigo_correlativo"
                        ).execute()
                        st.success(
                            "✅ Guardado en base de datos correctamente."
                        )
                    except Exception as e:
                        st.error(f"Error al guardar en BD: {e}")

            st.markdown("---")
            st.markdown("#### 🎯 Destinatarios y Canales de Envíos")

            try:
                res_user = (
                    supabase.table("usuarios")
                    .select("nombre, email, telefono, rol")
                    .execute()
                )
                df_destinatarios = (
                    pd.DataFrame(res_user.data)
                    if res_user.data
                    else pd.DataFrame()
                )
            except Exception:
                df_destinatarios = pd.DataFrame([
                    {
                        "nombre": "Atletas Categoría Juvenil",
                        "email": "juveniles@centrogallego.com",
                        "telefono": "+584141234567",
                        "rol": "Atletas",
                    },
                    {
                        "nombre": "Junta Directiva",
                        "email": "directiva@centrogallego.com",
                        "telefono": "+584129876543",
                        "rol": "Directiva",
                    },
                ])

            txt_resumen_wa = (
                f"🏛️ *{meta.get('tipo', 'DOCUMENTO').upper()} N°"
                f" {meta.get('codigo')}*\n\n*ASUNTO:* {meta.get('asunto')}\n*PARA:*"
                f" {meta.get('para')}\n\nEstimados miembros, adjunto remitimos"
                " la información oficial emitida."
            )

            asunto_mail = (
                f"[{meta.get('tipo')}] {meta.get('asunto')} - N°"
                f" {meta.get('codigo')}"
            )

            st.text_area(
                "Mensaje de acompañamiento (WhatsApp / Email):",
                value=txt_resumen_wa,
                height=100,
                key="txt_area_wa_msg_com",
            )

            st.markdown("##### 👥 Directorio de Despacho")

            for idx, row in df_destinatarios.iterrows():
                with st.container(border=True):
                    col_u1, col_u2, col_u3, col_u4 = st.columns(
                        [2.5, 2, 1.5, 1.5]
                    )

                    nom = row.get("nombre", "Sin Nombre")
                    email = row.get("email", "")
                    telf = (
                        str(row.get("telefono", ""))
                        .replace("+", "")
                        .replace(" ", "")
                        .replace("-", "")
                    )

                    col_u1.write(f"**{nom}**")
                    col_u2.caption(f"✉️ {email}\n📞 {telf}")

                    if telf:
                        wa_url = f"https://api.whatsapp.com/send?phone={telf}&text={urllib.parse.quote(txt_resumen_wa)}"
                        col_u3.link_button(
                            "🟢 WhatsApp",
                            wa_url,
                            use_container_width=True,
                            key=f"btn_wa_com_{idx}",
                        )
                    else:
                        col_u3.caption("Sin teléfono")

                    if email:
                        if col_u4.button(
                            "📩 Enviar PDF Mail",
                            key=f"btn_mail_com_{idx}",
                            use_container_width=True,
                        ):
                            with st.spinner(f"Enviando PDF a {email}..."):
                                ok, msg_err = enviar_correo_con_pdf(
                                    destinatario=email,
                                    asunto=asunto_mail,
                                    cuerpo=txt_resumen_wa,
                                    pdf_bytes=pdf_bytes,
                                    nombre_archivo_pdf=nombre_pdf,
                                )
                                if ok:
                                    st.success(f"¡Enviado a {nom}!")
                                else:
                                    st.error(msg_err)
                    else:
                        col_u4.caption("Sin correo")
