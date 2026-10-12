# =============================================================================
# views_tab_entrenador.py — v2.0 (Fase 1: refactorización incremental)
# =============================================================================
# CAMBIOS vs v1.0:
#   12a — Eliminado `global supabase` (anti-patrón). Se usa get_db().
#   12b — Consulta a marcas_referencia migrada a get_marcas_referencia().
#   12c — Invalidación quirúrgica de referencias tras guardar.
#   12d — Añadidas categorías Preinfantiles A/B/C al selector.
#   12e — Campo "Mínima Año" oculto para Preinfantiles.
#   12f — Propagación de TODAS las marcas internacionales (no solo WR)
#         a todas las categorías del mismo (prueba, género).
#   12g — Feedback explícito en el guardado (F2-21).
#   12h — Encabezado con changelog versionado.
#
# NO TOCADO:
#   - @st.fragment
#   - Estructura del formulario (excepto el campo condicional)
#   - key= de los widgets
#   - Validación de rol
#
# PENDIENTE FASE 2:
#   [F2-23] Renombrar archivo (es panel de Head Coach, no de Entrenador).
#   [F2-26] Evaluar si agregar checkbox "propagar internacionales" para
#           casos de excepciones puntuales.
# =============================================================================
import streamlit as st
import pandas as pd
from formulas_lib_funciones import (
    formatear_a_minutos,
    convertir_string_a_segundos,
    obtener_pruebas_por_categoria,
)

# 🚀 IMPORTACIÓN DESDE TU CAPA DE CACHÉ (v2.3)
from conections_supabase_cache import (
    get_db,
    get_marcas_referencia,
    invalidar_cache_referencias,
)


# =============================================================================
# CATEGORÍAS DISPONIBLES EN EL SISTEMA
# =============================================================================
# Preinfantiles: sin marca nacional (m_ano). Solo internacionales.
# Resto: con marca nacional + internacionales.
CATEGORIAS_DISPONIBLES = [
    "Preinfantil A",
    "Preinfantil B",
    "Preinfantil C",
    "Infantil A",
    "Infantil B",
    "Juvenil A",
    "Juvenil B",
    "Máxima",
]


def _es_categoria_preinfantil(categoria: str) -> bool:
    """Devuelve True si la categoría es Preinfantil (sin marca nacional)."""
    return bool(categoria) and categoria.startswith("Preinfantil")


# =============================================================================
# FORMULARIO REACTIVO (AISLADO EN @st.fragment)
# =============================================================================
@st.fragment
def contenedor_formulario_entrenador():
    # 1. Selección de categoría, género y prueba
    col_cat, col_gen = st.columns(2)
    with col_cat:
        u_cat = st.selectbox(
            "Categoría a Modificar u Organizar:",
            options=CATEGORIAS_DISPONIBLES,
            key="sb_categoria_entrenador",
        )
    with col_gen:
        genero_sel = st.selectbox(
            "Género:",
            options=["Femenino", "Masculino"],
            key="sb_genero_entrenador",
        )

    # Mapeo a formato de base de datos ('F' / 'M')
    genero_atleta = "F" if genero_sel == "Femenino" else "M"

    lista_pruebas_restringida = obtener_pruebas_por_categoria(u_cat)

    titulo_grafico = st.selectbox(
        f"🏊‍♂️ Seleccione la Prueba para {u_cat} ({genero_sel}):",
        options=lista_pruebas_restringida,
        index=1 if len(lista_pruebas_restringida) > 1 else 0,
        key="sb_prueba_entrenador_ingreso",
    )

    # [F1-12e] Detectamos si la categoría es Preinfantil.
    es_preinfantil = _es_categoria_preinfantil(u_cat)

    # Control de exclusiones (pruebas sin marcas de referencia configurables)
    pruebas_excluidas = [
        "25 Libre", "25 Espalda", "25 Pecho", "25 Mariposa", "100 Combinado",
    ]
    if titulo_grafico in pruebas_excluidas or es_preinfantil and titulo_grafico.startswith("25 "):
        st.info(
            f"💡 **Aviso:** Las marcas de referencia para la prueba "
            f"**{titulo_grafico}** se calculan automáticamente."
        )
        return

    # 2. Carga dinámica de marcas desde Supabase (vía cache v2.3)
    db_m_ano = None
    db_m_panam_b = None
    db_m_panam_a = None
    db_m_wa_b = None
    db_m_wa_a = None
    db_m_wr = None

    try:
        # [F1-12b] get_marcas_referencia() cacheada
        ref_dinamica = get_marcas_referencia(
            prueba=titulo_grafico,
            genero=genero_atleta,
            categoria=u_cat,
        )
        if ref_dinamica:
            r_det = ref_dinamica[0]
            db_m_ano = (
                float(r_det["m_ano"]) if r_det.get("m_ano") is not None else None
            )
            db_m_panam_b = (
                float(r_det["m_panam_b"])
                if r_det.get("m_panam_b") is not None
                else None
            )
            db_m_panam_a = (
                float(r_det["m_panam_a"])
                if r_det.get("m_panam_a") is not None
                else None
            )
            db_m_wa_b = (
                float(r_det["m_wa_b"]) if r_det.get("m_wa_b") is not None else None
            )
            db_m_wa_a = (
                float(r_det["m_wa_a"]) if r_det.get("m_wa_a") is not None else None
            )
            db_m_wr = (
                float(r_det["m_wr"]) if r_det.get("m_wr") is not None else None
            )
    except Exception as e:
        st.caption(f"Nota en precarga: {e}")

    st.caption(f"📋 Configurando tiempos para **{titulo_grafico}** ({genero_sel})")

    # Aviso de propagación de internacionales
    st.info(
        "💡 **Aviso:** Las marcas internacionales (PANAM Jr B/A, WA B/A, WR) "
        "se propagarán a **todas las categorías** de la misma prueba y género. "
        "Solo la Marca Mínima Año es específica de la categoría seleccionada."
    )

    # 3. Formulario de edición
    with st.form("form_update_referencias"):
        st.write(
            "✍️ *Ingrese los tiempos en formato `mm:ss.hh` o segundos "
            "decimales. Dejar en `0.00` mantiene el valor actual.*"
        )

        col1, col2 = st.columns(2)
        with col1:
            # [F1-12e] Campo condicional: solo se muestra si NO es Preinfantil
            if not es_preinfantil:
                in_ano = st.text_input(
                    "Marca Mínima Año (mm:ss.hh):",
                    value=formatear_a_minutos(db_m_ano),
                )
            else:
                in_ano = None
                st.caption(
                    "ℹ️ Las categorías Preinfantiles no tienen marca mínima "
                    "de participación nacional."
                )

            in_panamb = st.text_input(
                "PANAM Jr - Marca B (mm:ss.hh):",
                value=formatear_a_minutos(db_m_panam_b),
            )
            in_panama = st.text_input(
                "PANAM Jr - Marca A (mm:ss.hh):",
                value=formatear_a_minutos(db_m_panam_a),
            )

        with col2:
            in_wab = st.text_input(
                "World Aquatics - Marca B (mm:ss.hh):",
                value=formatear_a_minutos(db_m_wa_b),
            )
            in_waa = st.text_input(
                "World Aquatics - Marca A (mm:ss.hh):",
                value=formatear_a_minutos(db_m_wa_a),
            )
            in_wr = st.text_input(
                "Récord Mundial Absoluto (mm:ss.hh):",
                value=(
                    formatear_a_minutos(db_m_wr)
                    if db_m_wr is not None
                    else "25.00"
                ),
            )

        if st.form_submit_button("⚡ Guardar Configuración de Tiempos"):
            try:
                # ============================================
                # A. Construir payload de marca NACIONAL (m_ano)
                # ============================================
                up_nacional = {}
                if not es_preinfantil and in_ano is not None:
                    in_ano_clean = in_ano.strip()
                    if in_ano_clean and in_ano_clean != "0.00":
                        up_nacional["m_ano"] = convertir_string_a_segundos(
                            in_ano_clean
                        )

                # ============================================
                # B. Construir payload de marcas INTERNACIONALES
                # ============================================
                up_internacional = {}

                def _add_if_valor(dict_destino, key, valor_str):
                    """Helper: añade el valor si no es 0.00 ni vacío."""
                    if valor_str and valor_str.strip() and valor_str.strip() != "0.00":
                        dict_destino[key] = convertir_string_a_segundos(
                            valor_str.strip()
                        )

                _add_if_valor(up_internacional, "m_panam_b", in_panamb)
                _add_if_valor(up_internacional, "m_panam_a", in_panama)
                _add_if_valor(up_internacional, "m_wa_b", in_wab)
                _add_if_valor(up_internacional, "m_wa_a", in_waa)
                _add_if_valor(up_internacional, "m_wr", in_wr)

                # ============================================
                # C. Validar que haya algo para guardar
                # ============================================
                if not up_nacional and not up_internacional:
                    st.warning(
                        "⚠️ No se detectaron cambios numéricos válidos. "
                        "Los campos dejados en `0.00` o vacíos no modifican "
                        "los valores existentes."
                    )
                    st.stop()

                # ============================================
                # D. Guardar marca NACIONAL solo en la categoría activa
                # ============================================
                db = get_db()
                n_nacional = 0
                if up_nacional:
                    db.table("marcas_referencia").update(up_nacional).eq(
                        "prueba", titulo_grafico
                    ).eq("genero", genero_atleta).eq("categoria", u_cat).execute()
                    n_nacional = len(up_nacional)

                # ============================================
                # E. Propagar marcas INTERNACIONALES a todas las categorías
                # ============================================
                n_internacional = 0
                if up_internacional:
                    db.table("marcas_referencia").update(up_internacional).eq(
                        "prueba", titulo_grafico
                    ).eq("genero", genero_atleta).execute()
                    n_internacional = len(up_internacional)

                # ============================================
                # F. Invalidar caché de referencias
                # ============================================
                # [F1-12c] Sin esto, el gráfico y otras pestañas mostrarían
                # valores obsoletos durante hasta 24h.
                invalidar_cache_referencias()

                # ============================================
                # G. Feedback explícito
                # ============================================
                # [F1-12g] Mensaje claro de lo que se hizo
                mensaje_partes = []
                if n_nacional > 0:
                    mensaje_partes.append(
                        f"• **{n_nacional}** marca(s) nacional(es) "
                        f"actualizada(s) en **{u_cat}**."
                    )
                if n_internacional > 0:
                    mensaje_partes.append(
                        f"• **{n_internacional}** marca(s) internacional(es) "
                        f"propagada(s) a **todas las categorías** de "
                        f"{titulo_grafico} - {genero_sel}."
                    )

                st.success(
                    "✅ **Configuración guardada correctamente:**\n\n"
                    + "\n".join(mensaje_partes)
                )
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error al procesar o guardar los tiempos: {e}")


# =============================================================================
# FUNCIÓN PRINCIPAL (PUNTO DE ENTRADA)
# =============================================================================
def renderizar_tab_entrenador():
    """
    Panel de configuración de umbrales de competencia.

    NOTA: pese al nombre del archivo, esta vista solo es accesible para
    Head Coach / Administrador. Ver [F2-23] para renombrado futuro.
    """
    # [F1-12a] Eliminado `global supabase`. Validamos conexión con get_db().
    try:
        db = get_db()
        if not db:
            st.error("❌ Conexión no inicializada en Session State.")
            return
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return

    if st.session_state.get("rol") not in ["Head Coach", "Administrador"]:
        st.warning(
            "🔒 Requiere credenciales de Head Coach o Administrador para "
            "acceder a este panel."
        )
        return

    st.markdown("### ⚙️ Umbrales de Competencia para la Categoría")

    # Invocamos el contenedor fragmentado de manera limpia
    contenedor_formulario_entrenador()