# =============================================================================
# views_sidebar.py — v2.0 (Fase 1: refactorización incremental)
# =============================================================================
# CAMBIOS vs v1.0:
#   1. Imports migrados a funciones get_* (con wrappers de compatibilidad
#      disponibles, pero se usan las nuevas directamente).
#   2. §3 Entrenador: carga de atletas unificada con caché de sesión.
#   3. §5 Modo Equipo: reutiliza atletas ya cargados en §3 (evita 2 queries).
#   4. §7 Historial: cacheado en session_state por (atleta_id, prueba).
#   5. Fix bug: nadador_seleccionado_fecha_nacimiento ahora se persiste.
#   6. Helper _persistir_atleta_sel() para evitar duplicación.
#
# NO TOCADO (deliberadamente):
#   - CSS, keys de widgets, sliders, checkboxes, layout visual
#   - Estructura del dict de retorno (compatibilidad total)
#   - Lógica de marcas de referencia (§6)
#
# PENDIENTE FASE 2 (no aplicar hasta que todos los archivos estén migrados):
#   [F2-1] §7 — Mover carga de historial y cálculo de PB al gráfico.
#   [F2-2] §4 — Reemplazar st.stop() por retorno {"prueba_valida": False}.
#   [F2-3] §11 — Aplanar el dict de retorno (48 claves → sub-dicts).
#   [F2-4] §5 — Extraer bloque "modo equipo" a función propia.
#   [F2-5] Aplicar @st.fragment a sliders finales.
# =============================================================================
import datetime
from datetime import timedelta
import pandas as pd
import streamlit as st

# 🎨 IMPORTACIÓN DESDE TU MÓDULO DE ESTILOS VISUALES
from views_styles import spc

# 📦 IMPORTACIÓN DESDE TU LIBRERÍA REAL DE FUNCIONES
from formulas_lib_funciones import (
    calcular_categoria_competencia,
    convertir_string_a_segundos,
    formatear_a_minutos,
    obtener_pruebas_por_categoria,
    procesar_mejor_marca_historica,
)

# 🚀 IMPORTACIÓN DESDE TU CAPA DE CACHÉ (v2.0)
from conections_supabase_cache import (
    get_atletas_asignados,
    get_marcas_equipo,
    get_marcas_historicas,
    get_marcas_referencia,
    get_usuarios,
    get_usuario_por_id,
)


# =============================================================================
# HELPERS INTERNOS
# =============================================================================
def _persistir_atleta_sel(atleta_row: dict) -> None:
    """
    Persiste la selección de atleta en session_state.
    Antes esta lógica estaba duplicada en 3 ramas del sidebar.
    """
    if atleta_row is None:
        return
    st.session_state["nadador_seleccionado_id"] = int(atleta_row["id"])
    st.session_state["nadador_seleccionado_nombre"] = atleta_row["nombre"]
    st.session_state["nadador_seleccionado_genero"] = atleta_row.get("genero", "M")

    # FIX: antes esta clave nunca se seteaba → el gráfico recibía siempre "2014-12-30"
    fecha_nac = atleta_row.get("fecha_nacimiento")
    st.session_state["nadador_seleccionado_fecha_nacimiento"] = fecha_nac

    if fecha_nac:
        try:
            cat_calc, _ = calcular_categoria_competencia(fecha_nac)
        except Exception:
            cat_calc = "Sin Categoría"
    else:
        cat_calc = "Sin Categoría"
    st.session_state["nadador_seleccionado_categoria"] = cat_calc


def ordenar_atletas_jerarquicamente(lista_atletas):
    """Ordena atletas por:
    1º Categoría/Edad (Menor a Mayor) 2º Género (Femenino -> Masculino) 3º Nombre
    alfabético (A -> Z)
    """
    if not lista_atletas:
        return []

    def key_ordenamiento(atleta):
        if not isinstance(atleta, dict):
            return (999, "Z", "")

        fn = atleta.get("fecha_nacimiento")
        if pd.isna(fn) or not fn:
            edad = 999
        else:
            try:
                _, edad = calcular_categoria_competencia(fn)
            except Exception:
                edad = 999

        genero = str(atleta.get("genero") or "Z").upper()
        nombre = str(atleta.get("nombre") or "").strip().upper()
        return (edad, genero, nombre)

    return sorted(lista_atletas, key=key_ordenamiento)


def _atletas_del_entrenador_actual(entrenador_id, rol_real) -> list[dict]:
    """
    Devuelve (y cachea en session_state) los atletas del entrenador indicado.
    Evita la doble consulta que había entre §3 y §5 del sidebar original.
    """
    if entrenador_id is None:
        return []

    cache_key = f"_atletas_entrenador_{entrenador_id}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    todos = get_usuarios(rol="Nadador", estatus="Activo")
    asignados = set(get_atletas_asignados(entrenador_id))

    atletas = [
        a for a in todos
        if str(a.get("id")) in {str(x) for x in asignados}
    ]
    atletas = ordenar_atletas_jerarquicamente(atletas)
    st.session_state[cache_key] = atletas
    return atletas


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def renderizar_sidebar_completo():
  """Renderiza el sidebar completo con soporte de emulación para el Administrador."""
  if "supabase" not in st.session_state or st.session_state.supabase is None:
    st.error("No hay una conexión activa a la base de datos.")
    st.stop()

  # -------------------------------------------------------------
  # 0. INICIALIZACIÓN DE VARIABLES GLOBALES
  # -------------------------------------------------------------
  edad_min_zoom = 0.0
  edad_max_zoom = 100.0
  t0 = 10.0
  T0 = 30.0
  t_peak = 23.0
  T_target = 25.0
  t_pb = 12.0
  T_pb = 28.0
  factor_h = 0.35
  t_intermedia = 16.5
  tipo_vista = "Macro (Historial Completo)"
  simulacion_externa = False
  modo_equipo = False
  filtro_genero = "Todos"
  tipo_filtro = "Todos los Atletas"
  cat_sel = None
  ids_sel = []
  lista_atletas = []
  df_global = pd.DataFrame()
  df_procesado = pd.DataFrame()

  m_ano, m_panam_b, m_panam_a, m_wa_b, m_wa_a, m_wr = (
      0.0, 0.0, 0.0, 0.0, 0.0, 25.0,
  )

  # -------------------------------------------------------------
  # 1. IDENTIFICACIÓN Y EMULACIÓN DE ROL (ADMINISTRADOR)
  # -------------------------------------------------------------
  ROLES_OFICIALES = [
      "Nadador",
      "Entrenador",
      "Head Coach",
      "Club",
      "Administrador",
  ]

  if "rol_real" not in st.session_state:
    st.session_state["rol_real"] = st.session_state.get("rol", "Nadador")

  rol_real = st.session_state["rol_real"]
  nombre_mostrar = st.session_state.get("nombre_usuario") or st.session_state.get(
      "nombre_nadador", "Usuario"
  )

  st.sidebar.markdown(
      f"**Usuario:** {nombre_mostrar}  \n**Nivel Real:** `{rol_real}`"
  )

  if rol_real == "Administrador":
    st.sidebar.markdown(
        "<hr style='margin: 8px 0; border-top: 1px solid #0055ff;'/>",
        unsafe_allow_html=True,
    )
    st.sidebar.caption("🛠️ **Modo Emulación (Administrador)**")

    rol_actual_simulado = st.session_state.get("rol", "Administrador")
    idx_defecto = (
        ROLES_OFICIALES.index(rol_actual_simulado)
        if rol_actual_simulado in ROLES_OFICIALES
        else 4
    )

    rol_efectivo = st.sidebar.selectbox(
        "Simular vista como:",
        options=ROLES_OFICIALES,
        index=idx_defecto,
        key="selector_emulacion_rol",
    )

    if rol_efectivo != st.session_state.get("rol"):
      st.session_state["rol"] = rol_efectivo
      st.rerun()

  if st.sidebar.button("🚪 Salir del Sistema"):
    st.session_state.autenticado = False
    st.rerun()

  rol_activo = st.session_state.get("rol", "Nadador")

  # -------------------------------------------------------------
  # 2. SALIDA TEMPRANA SI EL ROL EMULADO ES "CLUB"
  # -------------------------------------------------------------
  if rol_activo == "Club":
    st.sidebar.markdown(
        "<hr style='margin: 12px 0; border-top: 1px solid #ccc;'/>",
        unsafe_allow_html=True,
    )
    st.sidebar.subheader("🏛️ Sesión del Club")
    st.sidebar.info("Panel de gestión administrativa activo.")

    return {
        "usuario_id": st.session_state.get("usuario_logueado_id")
        or st.session_state.get("usuario_id"),
        "fecha_nacimiento": st.session_state.get("nadador_seleccionado_fecha_nacimiento"),
        "genero": "M",
        "nombre": nombre_mostrar,
        "categoria": "",
        "titulo_grafico": "Gestión de Club",
        "simulacion_externa": simulacion_externa,
        "modo_equipo": modo_equipo,
        "filtro_genero": filtro_genero,
        "tipo_filtro": tipo_filtro,
        "cat_sel": cat_sel,
        "ids_sel": ids_sel,
        "lista_atletas_filtrados": lista_atletas,
        "df_global_marcas": df_global,
        "t0": t0,
        "T0": T0,
        "t_peak": t_peak,
        "T_target": T_target,
        "t_pb": t_pb,
        "T_pb": T_pb,
        "tipo_vista": tipo_vista,
        "edad_min_zoom": edad_min_zoom,
        "edad_max_zoom": edad_max_zoom,
        "factor_h": factor_h,
        "t_intermedia": t_intermedia,
        "df_procesado": df_procesado,
        "m_ano": m_ano,
        "m_panam_b": m_panam_b,
        "m_panam_a": m_panam_a,
        "m_wa_b": m_wa_b,
        "m_wa_a": m_wa_a,
        "m_wr": m_wr,
    }

  # -------------------------------------------------------------
  # 3. PANEL UNIFICADO DE NAVEGACIÓN Y SELECCIÓN DE ATLETAS
  # -------------------------------------------------------------
  if rol_activo in ["Head Coach", "Administrador"]:
    spc()
    st.sidebar.subheader("🎯 Panel de Navegación de Atletas")
    try:
      atletas_disponibles = ordenar_atletas_jerarquicamente(
          get_usuarios(rol="Nadador", estatus="Activo") or []
      )

      if atletas_disponibles:
        df_atl = pd.DataFrame(atletas_disponibles)
        dict_atletas = dict(zip(df_atl["id"], df_atl["nombre"]))

        sel_id = st.sidebar.selectbox(
            "Monitorear Nadador:",
            options=list(dict_atletas.keys()),
            format_func=lambda x: dict_atletas[x],
            key="sb_atleta_selector",
        )
        atleta_row = df_atl[df_atl["id"] == sel_id].iloc[0].to_dict()
        _persistir_atleta_sel(atleta_row)
      else:
        st.sidebar.warning("⚠️ No hay nadadores registrados.")
    except Exception as e:
      st.error(f"Error cargando atletas: {e}")

  elif rol_activo == "Entrenador":
    spc()
    st.sidebar.subheader("🎯 Panel de Entrenador")
    try:
      id_entrenador_evaluar = None

      # CASO A: Administrador Emulando Rol Entrenador
      if rol_real == "Administrador":
        todos_entrenadores = get_usuarios(rol="Entrenador") or []

        dict_entrenadores = {}
        for u in todos_entrenadores:
          if isinstance(u, dict):
            uid = u.get("id") if u.get("id") is not None else u.get("usuario_id")
            nom = (
                u.get("nombre")
                or u.get("nombre_completo")
                or f"Entrenador {uid}"
            )
            if uid is not None:
              dict_entrenadores[uid] = nom

        if dict_entrenadores:
          id_entrenador_evaluar = st.sidebar.selectbox(
              "👨‍🏫 Seleccionar Entrenador a Simular:",
              options=list(dict_entrenadores.keys()),
              format_func=lambda x: dict_entrenadores.get(x, "Entrenador"),
              key="sb_entrenador_simular_selector",
          )
        else:
          st.sidebar.warning(
              "⚠️ No hay entrenadores registrados en la tabla de usuarios."
          )
      # CASO B: Entrenador Real en su sesión
      else:
        id_entrenador_evaluar = st.session_state.get(
            "usuario_logueado_id"
        ) or st.session_state.get("usuario_id")

      # CONSULTA DE ASIGNACIONES (unificada y cacheada)
      if id_entrenador_evaluar is not None:
        atletas_disponibles = _atletas_del_entrenador_actual(
            id_entrenador_evaluar, rol_real
        )

        if atletas_disponibles:
          df_atl = pd.DataFrame(atletas_disponibles)
          dict_atletas = dict(zip(df_atl["id"], df_atl["nombre"]))

          sel_id = st.sidebar.selectbox(
              "🏊‍♂️ Atletas Asignados:",
              options=list(dict_atletas.keys()),
              format_func=lambda x: dict_atletas[x],
              key="sb_atleta_entrenador_selector",
          )
          atleta_row = df_atl[df_atl["id"] == sel_id].iloc[0].to_dict()
          _persistir_atleta_sel(atleta_row)
        else:
          st.sidebar.warning(
              "⚠️ No hay nadadores asignados a este entrenador."
          )
    except Exception as e:
      st.error(f"Error cargando atletas asignados: {e}")

  else:
    # 🏊‍♂️ ROL NADADOR
    if rol_real == "Administrador":
      spc()
      st.sidebar.subheader("🏊‍♂️ Selección de Nadador a Simular")
      atletas_disponibles = ordenar_atletas_jerarquicamente(
          get_usuarios(rol="Nadador", estatus="Activo") or []
      )

      if atletas_disponibles:
        df_atl = pd.DataFrame(atletas_disponibles)
        dict_atletas = dict(zip(df_atl["id"], df_atl["nombre"]))

        sel_id = st.sidebar.selectbox(
            "Simular sesión del atleta:",
            options=list(dict_atletas.keys()),
            format_func=lambda x: dict_atletas[x],
            key="sb_atleta_simular_nadador",
        )
        atleta_row = df_atl[df_atl["id"] == sel_id].iloc[0].to_dict()
        _persistir_atleta_sel(atleta_row)
      else:
        st.sidebar.warning("⚠️ No hay atletas disponibles.")
    else:
      st.session_state["nadador_seleccionado_id"] = st.session_state.get(
          "usuario_logueado_id"
      ) or st.session_state.get("usuario_id")
      st.session_state["nadador_seleccionado_nombre"] = st.session_state.get(
          "nombre_nadador"
      )
      st.session_state["nadador_seleccionado_genero"] = st.session_state.get(
          "genero", "M"
      )
      st.session_state["nadador_seleccionado_categoria"] = (
          st.session_state.get("categoria_atleta", "")
      )
      # FIX: garantizar que exista la clave aunque el nadador no la haya seteado
      if "nadador_seleccionado_fecha_nacimiento" not in st.session_state:
        st.session_state["nadador_seleccionado_fecha_nacimiento"] = (
            st.session_state.get("fecha_nacimiento")
        )

  # -------------------------------------------------------------
  # 4. SELECCIÓN DE PRUEBA
  # -------------------------------------------------------------
  spc()
  st.sidebar.subheader("📊 Ajustes por prueba")

  cat_atleta = st.session_state.get("nadador_seleccionado_categoria") or ""
  es_preinfantil = (
      cat_atleta.startswith("Preinfantil") if cat_atleta else False
  )

  lista_pruebas = (
      obtener_pruebas_por_categoria(cat_atleta)
      if cat_atleta
      else ["--- Seleccione Nadador ---"]
  )
  if not lista_pruebas:
    lista_pruebas = ["--- Sin Pruebas Disponibles ---"]

  index_default = 1 if len(lista_pruebas) > 1 else 0
  titulo_grafico = st.sidebar.selectbox(
      "Estilo y Distancia:", options=lista_pruebas, index=index_default
  )

  if titulo_grafico.startswith("---"):
    st.sidebar.info("👆 Selecciona un atleta o prueba válida para continuar.")
    # [F2-2] PENDIENTE: reemplazar por retorno {"prueba_valida": False}
    st.stop()

  st.session_state["prueba_seleccionada"] = titulo_grafico

  # -------------------------------------------------------------
  # 5. ANÁLISIS COLECTIVO (MODO EQUIPO)
  # -------------------------------------------------------------
  if rol_activo in ["Head Coach", "Administrador", "Entrenador"]:
    spc()
    st.sidebar.subheader("👥 Análisis Colectivo")
    modo_equipo = st.sidebar.checkbox(
        "Activar Comparativa de Equipo", value=False
    )

    if modo_equipo:
      spc()
      st.sidebar.subheader("🔍 Filtros de Segmentación de Equipo")
      filtro_genero = st.sidebar.radio(
          "Segmentar por Género:",
          options=["Todos", "Femenino (F)", "Masculino (M)"],
      )
      tipo_filtro = st.sidebar.radio(
          "Segmentar adicionalmente por:",
          options=[
              "Todos los Atletas",
              "Categoría Etaria",
              "Atletas Específicos",
          ],
      )

      try:
        # CAMBIO: reutiliza atletas ya cargados en §3 (evita 2 queries)
        if rol_activo == "Entrenador" and rol_real != "Administrador":
          id_coach = st.session_state.get(
              "usuario_logueado_id"
          ) or st.session_state.get("usuario_id")
          atletas_preload = list(
              _atletas_del_entrenador_actual(id_coach, rol_real)
          )
        else:
          atletas_preload = list(
              ordenar_atletas_jerarquicamente(
                  get_usuarios(rol="Nadador", estatus="Activo") or []
              )
          )

        if filtro_genero == "Femenino (F)":
          atletas_preload = [
              a for a in atletas_preload if a.get("genero") == "F"
          ]
        elif filtro_genero == "Masculino (M)":
          atletas_preload = [
              a for a in atletas_preload if a.get("genero") == "M"
          ]

        if tipo_filtro == "Categoría Etaria" and atletas_preload:
          cat_list = [
              calcular_categoria_competencia(a.get("fecha_nacimiento"))[0]
              for a in atletas_preload
              if a.get("fecha_nacimiento")
          ]
          categorias_disponibles = sorted(list(set(cat_list)))
          if categorias_disponibles:
            cat_sel = st.sidebar.selectbox(
                "Seleccione la categoría:", options=categorias_disponibles
            )
            lista_atletas = [
                a
                for a in atletas_preload
                if a.get("fecha_nacimiento")
                and calcular_categoria_competencia(a.get("fecha_nacimiento"))[0]
                == cat_sel
            ]

        elif tipo_filtro == "Atletas Específicos" and atletas_preload:
          dict_nom = {
              a["id"]: a["nombre"]
              for a in atletas_preload
              if "id" in a and "nombre" in a
          }
          if dict_nom:
            ids_sel = st.sidebar.multiselect(
                "Seleccione nadadores:",
                options=list(dict_nom.keys()),
                format_func=lambda x: dict_nom[x],
            )
            lista_atletas = [
                a for a in atletas_preload if a.get("id") in ids_sel
            ]
        else:
          lista_atletas = atletas_preload

        if (
            lista_atletas
            and titulo_grafico
            and not titulo_grafico.startswith("---")
        ):
          lista_ids_filtrados = [a["id"] for a in lista_atletas if "id" in a]
          # CAMBIO: get_marcas_equipo recibe una tupla (hashable) → caché real
          df_global = get_marcas_equipo(
              tuple(lista_ids_filtrados), titulo_grafico
          )

      except Exception as e:
        st.sidebar.error(f"Error cargando los filtros secundarios: {e}")

  # -------------------------------------------------------------
  # 6. EXTRACCIÓN ALINEADA CON 'marcas_referencia'
  # -------------------------------------------------------------
  contenedor_sliders = st.sidebar.container()

  if es_preinfantil:

    def get_m_ano_infantil_a(prueba_str):
      try:
        ref_resp = get_marcas_referencia(
            prueba_str,
            st.session_state.get("nadador_seleccionado_genero", "M"),
            "Infantil A",
        )
        if ref_resp and ref_resp[0].get("m_ano") is not None:
          return float(ref_resp[0]["m_ano"])
      except Exception:
        pass
      return 0.0

    if titulo_grafico.startswith("25 "):
      estilo = titulo_grafico.split(" ")[1]
      ref_50 = get_m_ano_infantil_a(f"50 {estilo}")
      m_ano = ref_50 / 2.0
      m_wr = m_ano * 0.8 if m_ano > 0 else 15.0
    elif titulo_grafico == "50 Libre":
      m_ano = get_m_ano_infantil_a("50 Libre")
      m_wr = m_ano * 0.