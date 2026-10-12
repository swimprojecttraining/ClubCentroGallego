# =============================================================================
# views_tab_club.py — v2.0 (Fase 1: refactorización incremental)
# =============================================================================
# CAMBIOS vs v1.0:
#   11a — Imports migrados a funciones get_* del cache v2.5.
#   11b — Insert/update de usuarios invalida caché de usuarios.
#   11c — Insert/update de invitaciones invalida caché de invitaciones.
#   11d — Helper _generar_html_correo_token() elimina duplicación de HTML.
#   11e — Feedback explícito en todos los botones (F2-21).
#   11f — Eliminado st.session_state["supabase"] → get_db().
#   11g — Helpers para cálculo de correlativo con caché.
#   11h — Encabezado con changelog versionado.
#
# NO TOCADO:
#   - Lógica de negocio (inserts, updates, backups)
#   - Estructura de sub-tabs
#   - key= de los widgets
#   - Formato de los HTML generados
#
# PENDIENTE FASE 2:
#   [F2-34] Cachear control_pagos tras insert.
#   [F2-35] Extraer generación de HTML de correos a helper (RESUELTO v2.0).
#   [F2-36] Añadir @st.fragment a render_pre_alta_atleta.
#   [F2-37] Añadir key= únicos a los widgets de club.
#   [F2-38] Manejo robusto de errores en generar_zip_bd_completa.
# =============================================================================
import streamlit as st
import datetime
import pandas as pd
import urllib.parse
import io
import zipfile
import json
import base64
import random
import secrets

# Importaciones centralizadas desde la librería de utilidades
from formulas_lib_funciones import (
    calcular_categoria_competencia,
    generar_codigo_invitacion,
    calcular_expiracion_token,
    enviar_correo_con_pdf,
)
from pdf_memo_utility import generar_pdf_memorandum_nativo

# 🚀 IMPORTACIÓN DESDE TU CAPA DE CACHÉ (v2.5)
from conections_supabase_cache import (
    get_db,
    get_usuarios,
    get_usuario_por_id,
    get_invitaciones_pendientes,
    get_pagos_por_temporada,
    get_documentos_correlativos,
    invalidar_cache_usuarios,
    invalidar_cache_invitaciones,
    invalidar_cache_pagos,
)


# =============================================================================
# HELPERS INTERNOS
# =============================================================================
def _nombre_club() -> str:
    """
    Devuelve el nombre del club desde session_state o secrets.
    Centraliza la lógica para evitar repeticiones.
    """
    return (
        st.session_state.get("club_seleccionado")
        or st.secrets.get("NOMBRE_CLUB_LOCAL", "Swimming Club")
    )


def _generar_html_correo_token(nombre_destinatario: str, nombre_club: str,
                                rol: str, token: str) -> str:
    """
    [F1-11d] Genera el HTML del correo con el token de acceso.
    Antes esta estructura estaba duplicada en 2 lugares.
    """
    return f"""
                <div style="font-family: Arial, sans-serif; padding: 20px; color: #333; max-width: 500px; border: 1px solid #eee; border-radius: 8px;">
                    <h2 style="color: #1a5276; margin-top: 0;">¡Hola, {nombre_destinatario}!</h2>
                    <p>Has sido registrado(a) en la plantilla oficial de <strong>{nombre_club}</strong> con el rol de <strong>{rol}</strong>.</p>
                    <p>Tu código de 6 dígitos para acceder al portal web es:</p>
                    <div style="background-color: #f2f4f4; padding: 15px; font-weight: bold; font-size: 24px; letter-spacing: 5px; color: #2e86c1; border-radius: 6px; text-align: center; margin: 20px 0;">
                        {token}
                    </div>
                    <p style="font-size: 12px; color: #7f8c8d;">Este código es de uso personal y expira en 24 horas.</p>
                </div>
                """


# =============================================================================
# PRE-ALTA DE ATLETAS / INTEGRANTES
# =============================================================================
def render_pre_alta_atleta(supabase, id_usuario_club):
    st.markdown("### ➕ Registro Directo de Integrantes a la Nómina")
    st.caption(
        "Al guardar los datos mínimos, el integrante queda registrado como "
        "ACTIVO de inmediato en la nómina del club."
    )

    pa_nombre = st.text_input("Nombre Completo:", key="pa_nombre")
    pa_email = st.text_input("Correo Electrónico:", key="pa_email")
    ROLES_DISPONIBLES_ALTA = ("Nadador", "Entrenador", "Head Coach", "Club")
    pa_rol = st.selectbox(
        "Rol Asignado:", options=ROLES_DISPONIBLES_ALTA, key="pa_rol"
    )

    if pa_rol not in ROLES_DISPONIBLES_ALTA:
        st.error("❌ El rol seleccionado no es válido.")
        st.stop()

    pa_genero = st.selectbox(
        "Género:",
        options=["F", "M"],
        format_func=lambda x: "Femenino" if x == "F" else "Masculino",
        key="pa_genero",
    )
    pa_fecha_nac = st.date_input(
        "Fecha de Nacimiento:",
        min_value=datetime.date(1950, 1, 1),
        max_value=datetime.date.today(),
        key="pa_fecha_nac",
    )

    pa_cedula = st.text_input("Cédula / Documento (Opcional):", key="pa_cedula")
    pa_telefono = st.text_input("Teléfono (Opcional):", key="pa_telefono")

    # --- BOTÓN DE REGISTRO DE NUEVO INTEGRANTE ---
    if st.button(
        "🚀 Registrar e Incorporar a la Nómina (Activo)",
        type="primary",
        use_container_width=True,
        key="btn_registrar_nomina",
    ):
        if (
            not pa_nombre
            or not pa_email
            or not pa_rol
            or not pa_genero
            or not pa_fecha_nac
        ):
            st.error(
                "⚠️ Los 5 campos básicos (Nombre, Email, Rol, Género y "
                "Fecha de Nacimiento) son obligatorios."
            )
        else:
            try:
                email_limpio = pa_email.strip().lower()

                # 1. Registro directo en la tabla de usuarios
                payload_usuario = {
                    "nombre": pa_nombre.strip(),
                    "email": email_limpio,
                    "rol": pa_rol,
                    "genero": pa_genero,
                    "fecha_nacimiento": pa_fecha_nac.isoformat(),
                    "cedula": pa_cedula.strip() if pa_cedula else None,
                    "telefono": pa_telefono.strip() if pa_telefono else None,
                    "estatus": "Activo",
                }

                supabase.table("usuarios").insert(payload_usuario).execute()

                # [F1-11b] Invalidación de caché de usuarios tras insert
                invalidar_cache_usuarios()

                # 2. Inactivar tokens anteriores pendientes
                try:
                    supabase.table("invitaciones").update(
                        {"usado": True}
                    ).eq("email", email_limpio).eq("usado", False).execute()

                    # [F1-11c] Invalidación tras update masivo de invitaciones
                    invalidar_cache_invitaciones()
                except Exception:
                    pass

                # 3. Generación de Token Numérico de 6 Dígitos (Vigencia 24h)
                token_invitacion = f"{secrets.randbelow(900000) + 100000}"
                expiracion = (
                    datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(hours=24)
                ).isoformat()

                payload_invitacion = {
                    "token": token_invitacion,
                    "nombre": pa_nombre.strip(),
                    "email": email_limpio,
                    "rol": pa_rol,
                    "expira_en": expiracion,
                    "usado": False,
                    "creado_por": id_usuario_club,
                }

                supabase.table("invitaciones").insert(payload_invitacion).execute()

                # [F1-11c] Invalidación tras insert de invitación
                invalidar_cache_invitaciones()

                # 4. Envío de Correo Inicial
                nombre_club = _nombre_club()
                asunto = (
                    f"Código de Acceso Web ({token_invitacion}) - {nombre_club}"
                )
                cuerpo_html = _generar_html_correo_token(
                    pa_nombre, nombre_club, pa_rol, token_invitacion
                )

                exito, msg_correo = enviar_correo_con_pdf(
                    destinatario=email_limpio,
                    asunto=asunto,
                    cuerpo_html=cuerpo_html,
                )

                # [F1-11e] Feedback explícito
                st.success(
                    f"✅ Integrante **{pa_nombre}** registrado como "
                    f"**ACTIVO** (rol: {pa_rol})."
                )
                if not exito:
                    st.info(
                        f"ℹ️ Registro completado en BD. "
                        f"(Aviso de envío SMTP: {msg_correo})"
                    )
            except Exception as e:
                st.error(f"❌ Error al guardar el usuario en la base de datos: {e}")

    # --- CONSULTA, AUTO-RENOVACIÓN Y ENVÍO DE TOKENS ---
    st.markdown("---")
    with st.expander(
        "🔑 **Consultar y Enviar Tokens de Acceso Web**", expanded=False
    ):
        try:
            # [F1-11a] get_invitaciones_pendientes() cacheada (ttl 300s)
            df_inv_raw = get_invitaciones_pendientes()

            # FILTRO DEFENSIVO: la query ya filtra por usado=False, pero
            # confirmamos en memoria por si acaso
            df_inv = (
                pd.DataFrame(df_inv_raw)
                if df_inv_raw
                else pd.DataFrame()
            )

            if not df_inv.empty and "usado" in df_inv.columns:
                df_inv = df_inv[df_inv["usado"] == False]

            if df_inv.empty:
                st.info("ℹ️ No hay tokens de acceso web pendientes.")
            else:
                df_inv["email_norm"] = (
                    df_inv["email"].astype(str).str.strip().str.lower()
                )
                df_validos = df_inv.drop_duplicates(
                    subset=["email_norm"], keep="first"
                )

                # Desactivar registros viejos duplicados
                ids_obsoletos = df_inv[
                    ~df_inv["id"].isin(df_validos["id"])
                ]["id"].tolist()
                if ids_obsoletos:
                    for id_obsoleto in ids_obsoletos:
                        try:
                            supabase.table("invitaciones").update(
                                {"usado": True}
                            ).eq("id", id_obsoleto).execute()
                        except Exception:
                            pass
                    # [F1-11c] Invalidar tras limpieza masiva
                    invalidar_cache_invitaciones()

                ahora_utc = datetime.datetime.now(datetime.timezone.utc)
                hubo_autorenovacion = False

                # 1. EVALUAR AUTO-RENOVACIÓN SILENCIOSA
                for idx, row in df_validos.iterrows():
                    expira_str = row.get("expira_en")
                    esta_vencido = False
                    if expira_str:
                        try:
                            expira_dt = datetime.datetime.fromisoformat(
                                expira_str.replace("Z", "+00:00")
                            )
                            if ahora_utc > expira_dt:
                                esta_vencido = True
                        except Exception:
                            pass

                    # Si transcurrieron las 24h, genera un nuevo token
                    if esta_vencido:
                        try:
                            supabase.table("invitaciones").update(
                                {"usado": True}
                            ).eq("id", row.get("id")).execute()
                            nuevo_token = (
                                f"{secrets.randbelow(900000) + 100000}"
                            )
                            nueva_expiracion = (
                                ahora_utc + datetime.timedelta(hours=24)
                            ).isoformat()

                            payload_nuevo = {
                                "token": nuevo_token,
                                "nombre": row.get("nombre"),
                                "email": row.get("email"),
                                "rol": row.get("rol"),
                                "expira_en": nueva_expiracion,
                                "usado": False,
                                "creado_por": id_usuario_club,
                            }
                            supabase.table("invitaciones").insert(
                                payload_nuevo
                            ).execute()
                            hubo_autorenovacion = True
                        except Exception:
                            pass

                # Recargar la vista si algún token fue auto-renovado
                if hubo_autorenovacion:
                    invalidar_cache_invitaciones()
                    st.rerun()

                st.caption(
                    "A continuación se muestra el código vigente para "
                    "cada integrante:"
                )

                # 2. VISTA Y BOTÓN ÚNICO DE ENVÍO
                for idx, row in df_validos.iterrows():
                    c_inv1, c_inv2, c_inv3 = st.columns([2.5, 1.5, 1.5])

                    with c_inv1:
                        st.write(
                            f"**{row.get('nombre', 'Sin Nombre')}** "
                            f"({row.get('rol', 'Sin Rol')})"
                        )
                        st.caption(f"Email: {row.get('email', 'N/A')}")

                    with c_inv2:
                        st.code(row.get("token", ""), language=None)

                    with c_inv3:
                        if st.button(
                            "📩 Enviar Código",
                            key=f"btn_enviar_{row.get('id', idx)}",
                            use_container_width=True,
                        ):
                            nombre_club = _nombre_club()
                            token_code = row.get("token", "")
                            asunto = (
                                f"Código de Acceso Web ({token_code}) - "
                                f"{nombre_club}"
                            )
                            cuerpo_html = _generar_html_correo_token(
                                row.get("nombre"),
                                nombre_club,
                                row.get("rol"),
                                token_code,
                            )
                            exito, msg = enviar_correo_con_pdf(
                                destinatario=row.get("email"),
                                asunto=asunto,
                                cuerpo_html=cuerpo_html,
                            )
                            if exito:
                                st.success("📩 ¡Enviado!")
                            else:
                                st.error(f"❌ Error: {msg}")

        except Exception as e:
            st.error(f"❌ Error al consultar tokens: {e}")

# === FIN ENTREGA 1/4 ===
# NO GUARDES AÚN — CONTINÚA CON LA ENTREGA 2/4 EN EL SIGUIENTE MENSAJE


# =============================================================================
# PLANTILLA Y NÓMINAS (SUB-TAB COMPLETO)
# =============================================================================
def render_nominas_y_plantilla(id_usuario_club, supabase):
    """
    [F1-11a] Renderiza el sub-tab de Plantilla y Nóminas.
    Migra todas las consultas a get_usuarios() cacheada.
    """
    st.markdown("### 👥 Administración de Nómina de Usuarios")
    st.caption(
        "Control institucional de integrantes, edición de perfiles y "
        "consulta de nóminas."
    )

    # --- Pre-Alta de Integrantes ---
    with st.expander(
        "➕ **1. Pre-Alta de Integrantes (Emisión OTP)**", expanded=False
    ):
        if id_usuario_club and supabase:
            render_pre_alta_atleta(supabase, id_usuario_club)
        else:
            st.warning("Error de sesión: No se identificó el usuario emisor.")

    # --- Carga única de usuarios (cacheada) ---
    ROLES_PLANTILLA_CLUB = ["Nadador", "Entrenador", "Head Coach", "Club"]

    # [F1-11a] get_usuarios() cacheada + filtrado en pandas
    todos_los_usuarios = get_usuarios()
    if todos_los_usuarios:
        df_todos_usuarios = pd.DataFrame(todos_los_usuarios)
        # Filtrar por roles permitidos
        if "rol" in df_todos_usuarios.columns:
            df_todos_usuarios = df_todos_usuarios[
                df_todos_usuarios["rol"].isin(ROLES_PLANTILLA_CLUB)
            ].copy()
    else:
        df_todos_usuarios = pd.DataFrame()

    if not df_todos_usuarios.empty:
        # --- Editar Ficha de Usuario ---
        with st.expander(
            "⚙️ **2. Actualizar Estatus y Ficha de Usuario (Cualquier Rol)**",
            expanded=False,
        ):
            usuario_mod_id = st.selectbox(
                "Seleccionar Usuario a Modificar:",
                options=df_todos_usuarios["id"].tolist(),
                format_func=lambda x: (
                    f"{df_todos_usuarios[df_todos_usuarios['id'] == x]['nombre'].values[0]} | "
                    f"Rol: {df_todos_usuarios[df_todos_usuarios['id'] == x]['rol'].values[0]} | "
                    f"Estatus: {df_todos_usuarios[df_todos_usuarios['id'] == x]['estatus'].values[0]}"
                ),
                key="select_user_global_edit",
            )

            row_user = df_todos_usuarios[
                df_todos_usuarios["id"] == usuario_mod_id
            ].iloc[0]

            fecha_nac_val = datetime.date(2010, 1, 1)
            if (
                pd.notna(row_user.get("fecha_nacimiento"))
                and row_user.get("fecha_nacimiento")
            ):
                try:
                    fecha_nac_val = pd.to_datetime(
                        row_user["fecha_nacimiento"]
                    ).date()
                except Exception:
                    pass

            with st.form("form_editar_ficha_usuario_global"):
                c_e1, c_e2 = st.columns(2)
                with c_e1:
                    edit_nombre = st.text_input(
                        "Nombre Completo:",
                        value=str(row_user.get("nombre", "")),
                    )
                    edit_email = st.text_input(
                        "Correo Electrónico:",
                        value=str(row_user.get("email", "")),
                    )
                    edit_cedula = st.text_input(
                        "Cédula / Documento:",
                        value=str(
                            row_user.get("cedula", "")
                            if pd.notna(row_user.get("cedula"))
                            else ""
                        ),
                    )

                    roles_disp = [
                        "Nadador", "Entrenador", "Head Coach", "Club",
                    ]
                    rol_act = row_user.get("rol", "Nadador")
                    idx_rol = (
                        roles_disp.index(rol_act)
                        if rol_act in roles_disp
                        else 0
                    )
                    edit_rol = st.selectbox(
                        "Rol Institucional:", roles_disp, index=idx_rol
                    )

                with c_e2:
                    edit_telefono = st.text_input(
                        "Teléfono:",
                        value=str(
                            row_user.get("telefono", "")
                            if pd.notna(row_user.get("telefono"))
                            else ""
                        ),
                    )
                    edit_fecha_nac = st.date_input(
                        "Fecha de Nacimiento:", value=fecha_nac_val
                    )

                    estatus_opciones = [
                        "Activo", "Inactivo", "Suspendido", "Retirado",
                    ]
                    estatus_actual = row_user.get("estatus", "Activo")
                    idx_estatus = (
                        estatus_opciones.index(estatus_actual)
                        if estatus_actual in estatus_opciones
                        else 0
                    )
                    edit_estatus = st.selectbox(
                        "Estatus del Usuario:",
                        estatus_opciones,
                        index=idx_estatus,
                    )

                btn_guardar_ficha = st.form_submit_button(
                    "💾 Guardar Cambios en Ficha de Usuario",
                    use_container_width=True,
                )

                if btn_guardar_ficha:
                    payload = {
                        "nombre": edit_nombre,
                        "email": edit_email,
                        "cedula": edit_cedula,
                        "rol": edit_rol,
                        "telefono": edit_telefono,
                        "fecha_nacimiento": str(edit_fecha_nac),
                        "estatus": edit_estatus,
                    }
                    try:
                        supabase.table("usuarios").update(payload).eq(
                            "id", usuario_mod_id
                        ).execute()

                        # [F1-11b] Invalidación de caché de usuarios
                        invalidar_cache_usuarios()

                        # [F1-11e] Feedback explícito
                        st.success(
                            f"✅ Usuario **{edit_nombre}** actualizado "
                            f"correctamente. (Rol: {edit_rol}, "
                            f"Estatus: {edit_estatus})"
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al actualizar usuario: {e}")

    st.markdown("---")

    # --- Nóminas separadas: Nadadores / Técnica ---
    tab_nomina_nadadores, tab_nomina_tecnica = st.tabs([
        "🏊 NÓMINA NADADORES", "📋 NÓMINA TÉCNICA",
    ])

    with tab_nomina_nadadores:
        df_nadadores_nom = (
            df_todos_usuarios[df_todos_usuarios["rol"] == "Nadador"].copy()
            if not df_todos_usuarios.empty
            else pd.DataFrame()
        )

        if df_nadadores_nom.empty:
            st.info("ℹ️ No hay atletas registrados en la Nómina de Nadadores.")
        else:
            # Aseguramos que las columnas existan
            for col_opt in ["cedula", "telefono", "fecha_nacimiento", "email"]:
                if col_opt not in df_nadadores_nom.columns:
                    df_nadadores_nom[col_opt] = ""

            df_nadadores_nom["categoria"] = df_nadadores_nom[
                "fecha_nacimiento"
            ].apply(
                lambda f: (
                    calcular_categoria_competencia(f)[0]
                    if pd.notna(f) and f
                    else "Sin Fecha"
                )
            )

            f1, f2, f3 = st.columns(3)
            with f1:
                est_f = st.selectbox(
                    "Estatus:",
                    ["Todos", "Activo", "Inactivo", "Suspendido"],
                    key="f_est_nad",
                )
            with f2:
                cats_unicas = sorted([
                    str(c)
                    for c in df_nadadores_nom["categoria"].dropna().unique()
                    if c
                ])
                cat_f = st.selectbox(
                    "Categoría:", ["Todas"] + cats_unicas, key="f_cat_nad"
                )
            with f3:
                busq_f = st.text_input(
                    "🔍 Buscar Atleta:",
                    placeholder="Nombre, cédula...",
                    key="f_busq_nad",
                )

            df_nad_filtrado = df_nadadores_nom.copy()
            if est_f != "Todos":
                df_nad_filtrado = df_nad_filtrado[
                    df_nad_filtrado["estatus"] == est_f
                ]
            if cat_f != "Todas":
                df_nad_filtrado = df_nad_filtrado[
                    df_nad_filtrado["categoria"] == cat_f
                ]
            if busq_f:
                df_nad_filtrado = df_nad_filtrado[
                    df_nad_filtrado["nombre"].astype(str).str.contains(
                        busq_f, case=False, na=False
                    )
                    | df_nad_filtrado["cedula"].astype(str).str.contains(
                        busq_f, case=False, na=False
                    )
                ]

            k1, k2, k3 = st.columns(3)
            k1.metric("Total Nadadores", len(df_nadadores_nom))
            k2.metric(
                "🟢 Activos",
                len(df_nadadores_nom[df_nadadores_nom["estatus"] == "Activo"]),
            )
            k3.metric(
                "⚪ Inactivos / Otros",
                len(
                    df_nadadores_nom[
                        df_nadadores_nom["estatus"] != "Activo"
                    ]
                ),
            )

            cols_disp_nad = [
                "nombre", "cedula", "email", "telefono",
                "fecha_nacimiento", "categoria", "estatus",
            ]
            df_nad_disp = df_nad_filtrado[
                [c for c in cols_disp_nad if c in df_nad_filtrado.columns]
            ].copy()
            df_nad_disp.columns = [
                "Atleta", "Cédula", "Correo Electrónico", "Teléfono",
                "Fecha Nac.", "Categoría", "Estatus",
            ]
            st.dataframe(
                df_nad_disp, use_container_width=True, hide_index=True
            )

    with tab_nomina_tecnica:
        roles_tecnicos = ["Entrenador", "Head Coach", "Club"]
        df_tecnica = (
            df_todos_usuarios[
                df_todos_usuarios["rol"].isin(roles_tecnicos)
            ].copy()
            if not df_todos_usuarios.empty
            else pd.DataFrame()
        )

        if df_tecnica.empty:
            st.info("ℹ️ No hay personal técnico registrado.")
        else:
            cols_tec = [
                "nombre", "rol", "cedula", "email", "telefono", "estatus",
            ]
            df_tec_disp = df_tecnica[
                [c for c in cols_tec if c in df_tecnica.columns]
            ].copy()
            df_tec_disp.columns = [
                "Nombre y Apellido", "Rol Técnico", "Cédula",
                "Correo Electrónico", "Teléfono", "Estatus",
            ]
            st.dataframe(
                df_tec_disp, use_container_width=True, hide_index=True
            )

# === FIN ENTREGA 2/4 ===
# NO GUARDES AÚN — CONTINÚA CON LA ENTREGA 3/4 EN EL SIGUIENTE MENSAJE


# =============================================================================
# HELPERS DE DOCUMENTOS OFICIALES (con caché)
# =============================================================================
def obtener_logo_base64(supabase):
    """
    Obtiene el logo institucional en Base64 desde Supabase Storage.
    NOTA: Esta función sigue usando supabase directo porque Storage no
    pasa por PostgREST, así que no se puede cachear con st.cache_data.
    Se cachea el resultado en session_state para evitar descargas repetidas.
    """
    cache_key = "_logo_club_b64_cache"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    try:
        data = supabase.storage.from_("Archivos").download("logo_club.png")
        resultado = f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except Exception:
        # Placeholder 1x1 pixel transparente
        resultado = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSU2EUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        )
    st.session_state[cache_key] = resultado
    return resultado


def calcular_siguiente_correlativo(tipo_documento: str) -> str:
    """
    [F1-11g] Calcula el siguiente correlativo usando
    get_documentos_correlativos() cacheada (ttl 600s).

    Genera códigos como MEM-2026-001, CIR-2026-001, COR-2026-001.
    """
    anio_actual = datetime.datetime.now().year
    prefix_map = {
        "Memorándum": "MEM",
        "Circular": "CIR",
        "Correspondencia": "COR",
    }
    prefix = prefix_map.get(tipo_documento, "DOC")

    try:
        # [F1-11g] Función cacheada (ttl 600s)
        res_data = get_documentos_correlativos(tipo_documento, anio_actual)

        if res_data:
            ultimo_correlativo = res_data[0]["codigo_correlativo"]
            num_secuencia = int(ultimo_correlativo.split("-")[-1]) + 1
        else:
            num_secuencia = 1

        return f"{prefix}-{anio_actual}-{num_secuencia:03d}"
    except Exception:
        return f"{prefix}-{anio_actual}-001"


def generar_html_comunicado(
    logo_b64, nombre_club, tipo_doc, correlativo, fecha,
    destinatario, remitente, asunto, cuerpo,
):
    """
    Genera el HTML maquetado con dimensiones y estilo para la hoja del PDF.
    Sin cambios respecto a v1.0 (mantener estructura visual idéntica).
    """
    cuerpo_formateado = cuerpo.replace("\n", "<br>")

    html = f"""
    <div style="
        width: 100%;
        max-width: 700px;
        margin: 0 auto;
        padding: 25px;
        border: 1px solid #ddd;
        background-color: #ffffff;
        font-family: Arial, sans-serif;
        color: #2c3e50;
        box-sizing: border-box;
    ">
        <table style="width: 100%; border-bottom: 2px solid #003366; padding-bottom: 10px; margin-bottom: 15px;">
            <tr>
                <td style="width: 20%; vertical-align: middle;">
                    <img src="{logo_b64}" style="max-height: 65px; width: auto;" alt="Logo Club">
                </td>
                <td style="width: 80%; text-align: right; vertical-align: middle;">
                    <h2 style="margin: 0; color: #003366; font-size: 18px; text-transform: uppercase;">{nombre_club}</h2>
                    <p style="margin: 2px 0 0 0; font-size: 11px; color: #666;">Sistema Oficial de Control y Gestión Deportivo</p>
                </td>
            </tr>
        </table>

        <div style="text-align: center; margin-bottom: 15px;">
            <h3 style="margin: 0; font-size: 16px; text-transform: uppercase; letter-spacing: 1px; color: #111;">{tipo_doc}</h3>
            <span style="font-size: 12px; font-weight: bold; color: #d9534f;">N° {correlativo}</span>
        </div>

        <table style="width: 100%; font-size: 12px; margin-bottom: 15px; line-height: 1.4;">
            <tr>
                <td style="width: 15%; font-weight: bold;">FECHA:</td>
                <td>{fecha}</td>
            </tr>
            <tr>
                <td style="font-weight: bold;">PARA:</td>
                <td>{destinatario}</td>
            </tr>
            <tr>
                <td style="font-weight: bold;">DE:</td>
                <td>{remitente}</td>
            </tr>
            <tr>
                <td style="font-weight: bold;">ASUNTO:</td>
                <td style="font-weight: bold; color: #003366;">{asunto}</td>
            </tr>
        </table>

        <hr style="border: None; border-top: 1px solid #eee; margin: 10px 0;">

        <div style="font-size: 12px; line-height: 1.6; text-align: justify; min-height: 180px; margin-bottom: 30px;">
            {cuerpo_formateado}
        </div>

        <table style="width: 100%; margin-top: 40px; text-align: center; font-size: 11px;">
            <tr>
                <td style="width: 30%;"></td>
                <td style="width: 40%; border-top: 1px solid #333; padding-top: 5px;">
                    <strong>{remitente}</strong><br>
                    <span>Firma / Sello Oficial</span>
                </td>
                <td style="width: 30%;"></td>
            </tr>
        </table>
    </div>
    """
    return html


# =============================================================================
# SUB-TAB: COMUNICADOS Y CORRESPONDENCIA
# =============================================================================
def render_comunicados_y_correspondencia(supabase, id_usuario_club):
    st.markdown(
        """
        <style>
            div[data-testid="stVerticalBlock"] > div { gap: 0.3rem !important; }
            .stTextInput label, .stSelectbox label, .stTextArea label, .stDateInput label {
                font-size: 0.85rem !important;
                margin-bottom: -4px !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h4 style='margin:0; padding:0;'>📨 Emisión y Despacho con PDF Adjunto</h4>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Genere comunicados con correlativo automático, vista previa y "
        "despacho en PDF al correo del destinatario."
    )

    col_sel1, col_sel2 = st.columns([1.5, 1])
    with col_sel1:
        tipo_plantilla = st.selectbox(
            "Tipo de Documento Oficial:",
            options=["Memorándum", "Circular", "Correspondencia"],
            key="com_tipo_plantilla",
        )
    with col_sel2:
        # [F1-11g] Cálculo con función cacheada
        correlativo_auto = calcular_siguiente_correlativo(tipo_plantilla)
        correlativo = st.text_input(
            "N° Correlativo (Autogenerado):",
            value=correlativo_auto,
            key="com_correlativo",
        )

    st.markdown("---")

    col_izq, col_der = st.columns([1.1, 0.9])

    with col_izq:
        st.markdown("##### 📝 Datos del Documento")
        fecha_emision = st.date_input(
            "Fecha de Emisión:",
            value=datetime.date.today(),
            key="com_fecha",
        )

        if tipo_plantilla == "Memorándum":
            destinatario = st.text_input(
                "Para (Destinatario):",
                placeholder="Ej: Cuerpo Técnico y Entrenadores",
                key="com_dest",
            )
            remitente = st.text_input(
                "De (Remitente):",
                placeholder="Ej: Junta Directiva",
                key="com_rem",
            )
        elif tipo_plantilla == "Circular":
            destinatario = st.text_input(
                "Dirigido a:",
                value="A Toda la Comunidad de Atletas y Representantes",
                key="com_dest",
            )
            remitente = st.text_input(
                "Emisor:",
                placeholder="Ej: Coordinación de Deportes",
                key="com_rem",
            )
        else:
            destinatario = st.text_input(
                "Institución / Destinatario Ext.:",
                placeholder="Ej: FEVEDA / Asociación de Deportes",
                key="com_dest",
            )
            remitente = st.text_input(
                "Remitente Oficial:",
                placeholder="Ej: Presidencia del Club",
                key="com_rem",
            )

        asunto = st.text_input(
            "Asunto / Título:",
            placeholder="Ej: Convocatoria a Chequeo Técnico",
            key="com_asunto",
        )
        email_destino = st.text_input(
            "Correo Electrónico de Destino (para envío del PDF):",
            placeholder="ejemplo@correo.com",
            key="com_email_destino",
        )

        plantillas_defecto = {
            "Memorándum": (
                "Por medio de la presente, se les instruye lo siguiente:\n\n"
                "1. Fecha de inicio: \n"
                "2. Indicaciones generales:\n\n"
                "Sin otro particular."
            ),
            "Circular": (
                "Estimados Nadadores, Representantes y Personal Técnico,\n\n"
                "Nos dirigimos a ustedes para informarles que...\n\n"
                "Agradecemos de antemano su receptividad y apoyo."
            ),
            "Correspondencia": (
                "Nos dirigimos a su respetable institución con el motivo "
                "de solicitar/comunicar lo siguiente:\n\n"
                "En espera de su pronta y favorable respuesta, quedamos "
                "de ustedes."
            ),
        }

        cuerpo = st.text_area(
            "Cuerpo del Documento:",
            value=plantillas_defecto[tipo_plantilla],
            height=160,
            key=f"com_cuerpo_{tipo_plantilla.lower()}",
        )

    nombre_club = _nombre_club()
    logo_b64 = obtener_logo_base64(supabase)
    html_documento = generar_html_comunicado(
        logo_b64, nombre_club, tipo_plantilla, correlativo,
        fecha_emision.strftime("%d/%m/%Y"), destinatario, remitente,
        asunto, cuerpo,
    )

    with col_der:
        st.markdown("##### 👁️ Vista Previa del Documento")
        st.components.v1.html(html_documento, height=430, scrolling=True)

    st.markdown("---")
    if st.button(
        f"📄 Registrar en BD y Enviar PDF de {tipo_plantilla}",
        type="primary",
        use_container_width=True,
        key="btn_emitir_documento",
    ):
        if not correlativo or not destinatario or not asunto or not cuerpo:
            st.error(
                "⚠️ Debe completar los campos obligatorios del documento "
                "antes de despachar."
            )
        else:
            try:
                # Guardar en la tabla 'documentos_oficiales'
                payload = {
                    "codigo_correlativo": correlativo.strip(),
                    "tipo_documento": tipo_plantilla,
                    "titulo": asunto.strip(),
                    "para_destinatario": destinatario.strip(),
                    "de_emisor": remitente.strip(),
                    "fecha_emision": fecha_emision.isoformat(),
                    "asunto": asunto.strip(),
                    "contenido_json": {
                        "cuerpo": cuerpo.strip(),
                        "html": html_documento,
                    },
                    "clausulas_texto": cuerpo.strip(),
                    "estatus": "Enviado",
                    "creado_por": str(id_usuario_club),
                }

                supabase.table("documentos_oficiales").insert(payload).execute()

                # [F1-11e] Feedback explícito
                st.success(
                    f"💾 Documento **{correlativo}** registrado con éxito "
                    f"en la Base de Datos."
                )

                # Envío por correo con la función unificada
                if email_destino.strip():
                    asunto_correo = f"[{tipo_plantilla}] {correlativo} - {asunto}"
                    nombre_archivo_pdf = f"{correlativo}.pdf"

                    exito_envio, msg_envio = enviar_correo_con_pdf(
                        destinatario=email_destino.strip(),
                        asunto=asunto_correo,
                        cuerpo_html=html_documento,
                    )

                    if exito_envio:
                        st.success(
                            f"📩 Documento enviado exitosamente a "
                            f"**{email_destino}**."
                        )
                    else:
                        st.warning(
                            f"⚠️ Documento registrado en la BD, pero falló "
                            f"el correo: {msg_envio}"
                        )
                else:
                    st.info(
                        "ℹ️ No se especificó correo electrónico de destino; "
                        "el documento quedó registrado exclusivamente en el "
                        "histórico de la BD."
                    )

            except Exception as e:
                st.error(f"❌ Error al procesar la comunicación: {e}")

# === FIN ENTREGA 3/4 ===
# NO GUARDES AÚN — CONTINÚA CON LA ENTREGA 4/4 EN EL SIGUIENTE MENSAJE


# =============================================================================
# SUB-TAB: CONTROL FINANCIERO Y PAGOS
# =============================================================================
def render_control_financiero(supabase):
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

    # [F1-11a] get_usuarios() cacheada, filtrado por rol Nadador
    lista_nadadores = get_usuarios(rol="Nadador")

    # Columnas específicas para control financiero
    if lista_nadadores:
        df_nadadores = pd.DataFrame(lista_nadadores)
        # Nos quedamos solo con las columnas necesarias
        cols_nad = ["id", "nombre", "usuario", "estatus", "email"]
        df_nadadores = df_nadadores[
            [c for c in cols_nad if c in df_nadadores.columns]
        ].copy()
        # Si no hay columna "usuario", la creamos vacía para compatibilidad
        if "usuario" not in df_nadadores.columns:
            df_nadadores["usuario"] = ""
    else:
        df_nadadores = pd.DataFrame()

    if df_nadadores.empty:
        st.warning("⚠️ No hay nadadores registrados en la base de datos.")
        return

    # [F1-11a] get_pagos_por_temporada() cacheada
    pagos_raw = get_pagos_por_temporada(temporada_sel)
    df_pagos = pd.DataFrame(pagos_raw) if pagos_raw else pd.DataFrame()

    cols_mostrar = [
        "nombre", "usuario", "estado_pago", "monto",
        "fecha_pago", "referencia_pago", "observaciones",
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

    df_merged["estado_pago"] = df_merged["estado_pago"].fillna("Pendiente")
    df_merged["monto"] = df_merged["monto"].fillna(0.0)

    if estado_sel != "Todos":
        df_merged = df_merged[df_merged["estado_pago"] == estado_sel]

    if busqueda_texto:
        df_merged = df_merged[
            df_merged["nombre"].str.contains(
                busqueda_texto, case=False, na=False
            )
            | df_merged["usuario"].astype(str).str.contains(
                busqueda_texto, case=False, na=False
            )
        ]

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
        "Atleta", "Usuario", "Estado", "Monto ($)",
        "Fecha Pago", "N° Referencia", "Observaciones",
    ]
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.markdown("---")
    with st.expander("📝 **Registrar / Actualizar Pago de Atleta**", expanded=False):
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
                    "Mes Afectado:", list(range(1, 13)), index=mes_actual - 1
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

            obs_pago_val = st.text_input("Observaciones / Notas de pago:")
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

                    # [F1-11b] Invalidación de caché de pagos
                    invalidar_cache_pagos()

                    # [F1-11e] Feedback explícito
                    st.success(
                        f"✅ Pago registrado correctamente. "
                        f"Atleta ID {atleta_id_sel} | "
                        f"Mes {mes_pago} | "
                        f"Estatus: {nuevo_estado}"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al registrar pago: {e}")


# =============================================================================
# HELPERS DE RESPALDOS
# =============================================================================
def generar_zip_bd_completa(supabase):
    """
    Exporta todas las tablas clave del club en archivos CSV dentro
    de un contenedor ZIP.
    """
    tablas = [
        "usuarios", "invitaciones", "control_pagos",
        "marcas_historicas", "bitacora_entrenamientos",
        "documentos_oficiales",
    ]
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for tabla in tablas:
            try:
                res = supabase.table(tabla).select("*").execute()
                if res.data:
                    df = pd.DataFrame(res.data)
                    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
                    zf.writestr(f"{tabla}.csv", csv_bytes)
            except Exception:
                continue

    buffer.seek(0)
    return buffer


def generar_expediente_atleta_zip(supabase, atleta_id, nombre_atleta):
    """
    Genera el paquete completo de datos de un atleta específico
    para traslado o archivo personal.
    """
    buffer = io.BytesIO()
    tablas_atleta = [
        ("perfil_usuario", "usuarios", "id"),
        ("historial_pagos", "control_pagos", "usuario_id"),
        ("historial_marcas", "marcas_historicas", "usuario_id"),
        ("bitacora_entrenamientos", "bitacora_entrenamientos", "atleta_id"),
    ]

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for prefijo, tabla, columna_id in tablas_atleta:
            try:
                res = (
                    supabase.table(tabla)
                    .select("*")
                    .eq(columna_id, atleta_id)
                    .execute()
                )
                if res.data:
                    df = pd.DataFrame(res.data)
                    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
                    zf.writestr(f"{prefijo}_{atleta_id}.csv", csv_bytes)
            except Exception:
                continue

    buffer.seek(0)
    return buffer


# =============================================================================
# SUB-TAB: RESPALDOS DE BASE DE DATOS
# =============================================================================
def render_respaldos(supabase):
    st.markdown("### 💾 Respaldo y Portabilidad de Datos del Club")
    st.caption(
        "Herramientas autónomas de backup por tabla individual, archivo "
        "ZIP global y expedientes individuales de traslado."
    )

    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        with st.container(border=True):
            st.markdown("##### 📄 1. Exportar Tabla Individual")
            st.caption(
                "Descarga una tabla específica de Supabase en formato CSV."
            )

            tabla_sel_resp = st.selectbox(
                "Seleccionar Tabla:",
                [
                    "usuarios", "invitaciones", "control_pagos",
                    "marcas_referencia", "marcas_historicas",
                    "catalogo_competencias", "historial_hitos",
                    "bitacora_entrenamientos", "asignaciones",
                    "documentos_oficiales", "plantillas_documentos",
                ],
                key="select_tabla_individual_resp",
            )

            if st.button(
                "🔍 Cargar Datos de Tabla",
                use_container_width=True,
                key="btn_cargar_tabla_resp",
            ):
                try:
                    res_t = supabase.table(tabla_sel_resp).select("*").execute()
                    if res_t.data:
                        df_res_t = pd.DataFrame(res_t.data)
                        # [F1-11e] Feedback explícito
                        st.success(
                            f"✅ Tabla **{tabla_sel_resp}** cargada: "
                            f"**{len(res_t.data)}** registros listos para descargar."
                        )
                        st.download_button(
                            label=f"📥 Descargar `{tabla_sel_resp}.csv`",
                            data=df_res_t.to_csv(index=False).encode("utf-8-sig"),
                            file_name=f"{tabla_sel_resp}_{datetime.date.today()}.csv",
                            mime="text/csv",
                            use_container_width=True,
                            key=f"dl_tabla_{tabla_sel_resp}",
                        )
                    else:
                        st.warning(
                            f"⚠️ La tabla **{tabla_sel_resp}** no contiene "
                            f"registros."
                        )
                except Exception as e:
                    st.error(f"❌ Error al consultar tabla: {e}")

    with col_r2:
        with st.container(border=True):
            st.markdown("##### 📦 2. Backup Completo (ZIP)")
            st.caption(
                "Genera un archivo comprimido ZIP con todas las tablas "
                "del sistema."
            )

            if st.button(
                "⚙️ Generar Backup Completo",
                use_container_width=True,
                key="btn_generar_zip_bd",
            ):
                with st.spinner("Generando archivo ZIP de la BD..."):
                    zip_buffer = generar_zip_bd_completa(supabase)

                    # [F1-11e] Feedback explícito
                    st.success(
                        "✅ Backup generado correctamente. "
                        "Descárgalo con el botón inferior."
                    )
                    st.download_button(
                        label="📥 Descargar Backup General (.zip)",
                        data=zip_buffer,
                        file_name=f"Backup_BD_Club_{datetime.date.today()}.zip",
                        mime="application/zip",
                        type="primary",
                        use_container_width=True,
                        key="dl_zip_bd_completa",
                    )

    with col_r3:
        with st.container(border=True):
            st.markdown("##### 🏊 3. Expediente del Atleta")
            st.caption(
                "Paquete de datos de un atleta para archivo personal "
                "o traslado a otro club."
            )

            # [F1-11a] get_usuarios() cacheada, filtrado por Nadador
            lista_atl_resp = get_usuarios(rol="Nadador")

            if lista_atl_resp:
                atleta_exp_id = st.selectbox(
                    "Seleccionar Atleta:",
                    options=[a["id"] for a in lista_atl_resp],
                    format_func=lambda x: next(
                        (
                            f"{a['nombre']} ({a.get('cedula', 'Sin Doc')})"
                            for a in lista_atl_resp
                            if a["id"] == x
                        ),
                        "Atleta",
                    ),
                    key="select_atleta_expediente",
                )

                nom_atl_exp = next(
                    (
                        a["nombre"]
                        for a in lista_atl_resp
                        if a["id"] == atleta_exp_id
                    ),
                    "Atleta",
                )

                if st.button(
                    "📄 Empaquetar Expediente",
                    use_container_width=True,
                    key="btn_emp_exp_atleta",
                ):
                    with st.spinner(
                        f"Empaquetando expediente de {nom_atl_exp}..."
                    ):
                        zip_atleta = generar_expediente_atleta_zip(
                            supabase, atleta_exp_id, nom_atl_exp
                        )
                        # [F1-11e] Feedback explícito
                        st.success(
                            f"✅ Expediente de **{nom_atl_exp}** "
                            f"empaquetado correctamente."
                        )
                        st.download_button(
                            label="📥 Descargar Expediente Atleta (.zip)",
                            data=zip_atleta,
                            file_name=(
                                f"Expediente_"
                                f"{nom_atl_exp.replace(' ', '_')}_"
                                f"{datetime.date.today()}.zip"
                            ),
                            mime="application/zip",
                            type="primary",
                            use_container_width=True,
                            key="dl_expediente_atleta",
                        )
            else:
                st.caption("ℹ️ No hay atletas disponibles para empaquetar.")


# =============================================================================
# FUNCIÓN PRINCIPAL (PUNTO DE ENTRADA)
# =============================================================================
def renderizar_tab_club():
    """
    Centro de Control Administrativo.

    NOTA: pese al nombre del archivo, esta vista solo es accesible para
    el rol "Club". Ver [F2-27] para análisis de arranque en 0.
    """
    st.markdown("### 🏛️ Centro de Control Administrativo")
    st.caption(
        "Gestión financiera, gobernanza de nóminas, correspondencia y "
        "respaldos de base de datos."
    )
    st.markdown("---")

    # [F1-11f] get_db() en lugar de st.session_state["supabase"]
    try:
        supabase = get_db()
        if not supabase:
            st.error("❌ Error de conexión: cliente Supabase no disponible.")
            return
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return

    id_usuario_club = st.session_state.get("usuario_id")

    subtab_pagos, subtab_atletas, subtab_comunicacion, subtab_respaldos = st.tabs([
        "💳 Control Financiero y Pagos",
        "👥 Plantilla y Nóminas",
        "📄 Comunicados y Correspondencia",
        "💾 Respaldos de BD",
    ])

    # 1. CONTROL FINANCIERO Y PAGOS
    with subtab_pagos:
        render_control_financiero(supabase)

    # 2. PLANTILLA Y NÓMINAS
    with subtab_atletas:
        render_nominas_y_plantilla(id_usuario_club, supabase)

    # 3. COMUNICADOS Y CORRESPONDENCIA
    with subtab_comunicacion:
        render_comunicados_y_correspondencia(supabase, id_usuario_club)

    # 4. RESPALDOS DE BASE DE DATOS
    with subtab_respaldos:
        render_respaldos(supabase)

# === FIN DEL ARCHIVO views_tab_club.py (v2.0) ===