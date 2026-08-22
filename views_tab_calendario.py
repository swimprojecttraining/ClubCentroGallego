import datetime
import pandas as pd
import streamlit as st

# Importación de funciones core de soporte analítico desde la librería central
from formulas_lib_funciones import (
    calcular_edad_tecnica_al_31_dic,
    calcular_fecha_alerta,
    evaluar_elegibilidad_internacional,
    formatear_a_minutos,
)


def estimar_fecha_marca(fecha_nac_str, edad):
  """Calcula la fecha aproximada de la competencia sumando la edad (años) a la fecha de nacimiento."""
  if not fecha_nac_str or edad is None:
    return ""
  try:
    if isinstance(fecha_nac_str, str):
      f_nac = datetime.date.fromisoformat(fecha_nac_str)
    else:
      f_nac = fecha_nac_str
    dias = int(float(edad) * 365.25)
    f_marca = f_nac + datetime.timedelta(days=dias)
    return f_marca.strftime("%d/%m/%Y")
  except Exception:
    return ""


def renderizar_tab_calendario():
  """Vista general del Calendario de Competencias estructurada en subpestañas.

  Incluye la gestión de eventos, generación de hitos y la herramienta de
  exportación de nóminas con marcas históricas para el Head Coach / Admin.
  """
  supabase = st.session_state.get("supabase")
  rol_usuario = st.session_state.get("rol_real") or st.session_state.get(
      "rol", ""
  )
  id_usuario = st.session_state.get("usuario_id")

  if not supabase:
    st.error("❌ Conexión con el servidor no disponible.")
    return

  es_staff = rol_usuario in ["Head Coach", "Administrador"]

  if es_staff:
    tab_eventos, tab_inscripciones = st.tabs(
        ["📅 Calendario y Hitos", "📋 Planilla de Inscripción"]
    )
  else:
    tab_eventos = st.container()

  # ============================================================
  # SUBPESTAÑA 1: CALENDARIO Y HITOS
  # ============================================================
  with tab_eventos if es_staff else st.container():
    temporada_actual = datetime.date.today().year
    st.markdown(f"**Competencias Programadas - Temporada {temporada_actual}**")

    dict_comps = {}
    try:
      resp_comp = (
          supabase.table("catalogo_competencias")
          .select("*")
          .eq("temporada", temporada_actual)
          .order("fecha_inicio", desc=False)
          .execute()
      )
      resp_comp_data = resp_comp.data if resp_comp.data else []
    except Exception as e:
      st.error(f"Error cargando calendario: {e}")
      resp_comp_data = []

    if resp_comp_data:
      df_comp = pd.DataFrame(resp_comp_data)
      df_comp["fecha_inicio"] = pd.to_datetime(
          df_comp["fecha_inicio"]
      ).dt.strftime("%d-%m-%Y")
      df_comp["fecha_fin"] = pd.to_datetime(
          df_comp["fecha_fin"]
      ).dt.strftime("%d-%m-%Y")
      st.dataframe(
          df_comp[[
              "nombre_evento",
              "ente_rector",
              "categoria_evento",
              "fecha_inicio",
              "fecha_fin",
          ]],
          use_container_width=True,
          hide_index=True,
      )
      dict_comps = {
          f"{c['nombre_evento']} ({c['fecha_inicio']})": c
          for c in resp_comp_data
      }
    else:
      st.info(
          "No hay competencias registradas para la temporada"
          f" {temporada_actual}."
      )

    if es_staff:
      st.markdown("---")
      col_add, col_edit = st.columns(2)

      with col_add:
        st.markdown("**➕ Programar Nueva Competencia**")
        with st.form("form_add_comp", clear_on_submit=True):
          add_temp = st.number_input(
              "Temporada:", min_value=2024, value=temporada_actual
          )
          add_nombre = st.text_input("Nombre del Evento:")
          add_ente = st.selectbox(
              "Ente Rector:", ["FEVEDA", "PANAM", "SURAM", "WA"]
          )
          add_cat = st.selectbox("Nivel:", ["Nacional", "Internacional"])
          c1, c2 = st.columns(2)
          add_f_ini = c1.date_input("Inicio:")
          add_f_fin = c2.date_input("Fin:")

          if st.form_submit_button("💾 Guardar"):
            if add_f_fin < add_f_ini:
              st.error("La fecha de fin no puede ser anterior a la de inicio.")
            elif not add_nombre:
              st.error("Nombre obligatorio.")
            else:
              supabase.table("catalogo_competencias").insert({
                  "temporada": add_temp,
                  "nombre_evento": add_nombre,
                  "ente_rector": add_ente,
                  "categoria_evento": add_cat,
                  "fecha_inicio": add_f_ini.isoformat(),
                  "fecha_fin": add_f_fin.isoformat(),
                  "creador_id": id_usuario,
              }).execute()
              st.rerun()

      with col_edit:
        st.markdown("**✏️ Auditar / Posponer**")
        if dict_comps:
          comp_sel = st.selectbox("Seleccionar:", list(dict_comps.keys()))
          datos_c = dict_comps[comp_sel]
          with st.form("form_edit_comp"):
            edit_nombre = st.text_input(
                "Nombre:", value=datos_c["nombre_evento"]
            )
            c_i, c_f = st.columns(2)
            edit_f_ini = c_i.date_input(
                "Inicio:",
                value=datetime.date.fromisoformat(datos_c["fecha_inicio"]),
            )
            edit_f_fin = c_f.date_input(
                "Fin:", value=datetime.date.fromisoformat(datos_c["fecha_fin"])
            )
            if st.form_submit_button("🔄 Aplicar"):
              supabase.table("catalogo_competencias").update({
                  "fecha_inicio": edit_f_ini.isoformat(),
                  "fecha_fin": edit_f_fin.isoformat(),
                  "nombre_evento": edit_nombre,
              }).eq("id", datos_c["id"]).execute()
              st.rerun()

      st.markdown("---")
      st.markdown("### 🎯 Generación de Hitos")
      if dict_comps:
        comp_ins = st.selectbox(
            "Competencia a procesar:", options=list(dict_comps.keys())
        )
        datos_ins = dict_comps[comp_ins]

        if st.button("🚀 Procesar Nómina"):
          with st.spinner("Evaluando normativas..."):
            try:
              hitos_existentes = (
                  supabase.table("historial_hitos")
                  .select("usuario_id")
                  .eq("competencia_id", datos_ins["id"])
                  .execute()
              )
              set_ids_existentes = (
                  {h["usuario_id"] for h in hitos_existentes.data}
                  if hitos_existentes.data
                  else set()
              )

              atletas = (
                  supabase.table("usuarios")
                  .select("id, nombre, fecha_nacimiento")
                  .eq("rol", "Nadador")
                  .eq("estatus", "Activo")
                  .execute()
                  .data
              )

              contadores = {"elegibles": 0, "ineligibles": 0, "omitidos": 0}
              for atleta in atletas:
                if atleta["id"] in set_ids_existentes:
                  contadores["omitidos"] += 1
                  continue

                edad_t = calcular_edad_tecnica_al_31_dic(
                    atleta["fecha_nacimiento"], datos_ins["temporada"]
                )
                elegible, motivo = evaluar_elegibilidad_internacional(
                    edad_t, datos_ins["ente_rector"]
                )
                f_alerta = calcular_fecha_alerta(datos_ins["fecha_inicio"], 15)

                supabase.table("historial_hitos").insert({
                    "usuario_id": atleta["id"],
                    "competencia_id": datos_ins["id"],
                    "temporada_auditada": datos_ins["temporada"],
                    "elegible": elegible,
                    "motivo_ineligibilidad": motivo if not elegible else None,
                    "estado_cumplimiento": "Pendiente",
                    "fecha_alerta": f_alerta.isoformat(),
                }).execute()

                contadores["elegibles" if elegible else "ineligibles"] += 1

              st.success("✅ Proceso completado.")
              st.info(
                  f"📊 {contadores['elegibles']} elegibles |"
                  f" {contadores['ineligibles']} ineligibles |"
                  f" {contadores['omitidos']} ya registrados."
              )
              st.rerun()
            except Exception as e:
              st.error(f"Error técnico: {e}")

  # ============================================================
  # SUBPESTAÑA 2: PLANILLA DE INSCRIPCIÓN (MARCAS HISTÓRICAS)
  # ============================================================
  if es_staff:
    with tab_inscripciones:
      st.markdown("### 📋 Generador de Planilla de Inscripción")
      st.caption(
          "Genera y exporta la nómina de atletas con Cédula, Fecha de"
          " Nacimiento, PBs y los últimos 4 registros por prueba."
      )

      try:
        res_nadadores = (
            supabase.table("usuarios")
            .select("id, nombre, cedula, fecha_nacimiento, genero")
            .eq("rol", "Nadador")
            .eq("estatus", "Activo")
            .order("nombre")
            .execute()
        )
        nadadores_data = res_nadadores.data if res_nadadores.data else []
      except Exception as err:
        st.error(f"Error al obtener catálogo de nadadores: {err}")
        return

      if not nadadores_data:
        st.info("No hay nadadores activos en el sistema.")
        return

      dict_nadadores = {n["nombre"]: n for n in nadadores_data}
      col_f1, col_f2 = st.columns([2, 1])

      with col_f1:
        opcion_todos = st.checkbox(
            "Seleccionar Todos los Nadadores", value=True
        )
        if opcion_todos:
          nadadores_seleccionados = list(dict_nadadores.keys())
          st.multiselect(
              "Atletas elegidos:",
              options=list(dict_nadadores.keys()),
              default=nadadores_seleccionados,
              disabled=True,
          )
        else:
          nadadores_seleccionados = st.multiselect(
              "Selecciona los nadadores a incluir:",
              options=list(dict_nadadores.keys()),
              default=[],
          )

      with col_f2:
        st.markdown("**Opciones de Salida**")
        incluir_ultimos_4 = st.checkbox(
            "Incluir últimos 4 resultados por prueba", value=True
        )
        formato_exportacion = st.radio(
            "Formato de Exportación:",
            ["CSV (Excel)", "Tabla HTML con CSS (Copiable)"],
        )

      if not nadadores_seleccionados:
        st.warning("Selecciona al menos un atleta para procesar la planilla.")
        return

      ids_seleccionados = [
          dict_nadadores[nom]["id"] for nom in nadadores_seleccionados
      ]

      if st.button(
          "🚀 Generar Tabla para Inscripción", use_container_width=True
      ):
        with st.spinner("Procesando marcas históricas..."):
          try:
            res_tiempos = (
                supabase.table("marcas_historicas")
                .select("usuario_id, prueba, tiempo, edad, created_at")
                .in_("usuario_id", ids_seleccionados)
                .order("created_at", desc=True)
                .execute()
            )
            tiempos_raw = res_tiempos.data if res_tiempos.data else []
          except Exception as err:
            st.error(f"Error al consultar marcas históricas: {err}")
            return

          registros_tabla = []

          for nombre_atleta in nadadores_seleccionados:
            atleta_info = dict_nadadores[nombre_atleta]
            uid = atleta_info["id"]
            fecha_nac = atleta_info.get("fecha_nacimiento")

            tiempos_atleta = [t for t in tiempos_raw if t["usuario_id"] == uid]

            pruebas_dict = {}
            for t in tiempos_atleta:
              pr = t["prueba"]
              if pr not in pruebas_dict:
                pruebas_dict[pr] = []
              pruebas_dict[pr].append(t)

            fila_base = {
                "Atleta": atleta_info["nombre"],
                "Cédula": atleta_info.get("cedula", "N/T"),
                "Fecha Nacimiento": fecha_nac if fecha_nac else "N/T",
                "Género": atleta_info.get("genero", "N/T"),
            }

            if not pruebas_dict:
              fila = fila_base.copy()
              fila["Prueba"] = "Sin Marcas Registradas"
              fila["PB (Mejor Tiempo)"] = "-"
              if incluir_ultimos_4:
                fila["Res 1 (Último)"] = "-"
                fila["Res 2"] = "-"
                fila["Res 3"] = "-"
                fila["Res 4"] = "-"
              registros_tabla.append(fila)

            for prueba_nombre, lista_tiempos in pruebas_dict.items():
              fila = fila_base.copy()
              fila["Prueba"] = prueba_nombre

              tiempos_validos = [
                  t["tiempo"] for t in lista_tiempos if t["tiempo"] is not None
              ]

              if tiempos_validos:
                pb_val = min(tiempos_validos)
                reg_pb = next(
                    (t for t in lista_tiempos if t["tiempo"] == pb_val), None
                )
                f_pb = (
                    estimar_fecha_marca(fecha_nac, reg_pb.get("edad"))
                    if reg_pb
                    else ""
                )
                str_pb = formatear_a_minutos(pb_val)
                fila["PB (Mejor Tiempo)"] = (
                    f"{str_pb} ({f_pb})" if f_pb else str_pb
                )
              else:
                fila["PB (Mejor Tiempo)"] = "-"

              if incluir_ultimos_4:
                ultimos_4 = lista_tiempos[:4]
                for idx in range(4):
                  col_nombre = (
                      f"Res {idx + 1} (Último)"
                      if idx == 0
                      else f"Res {idx + 1}"
                  )
                  if idx < len(ultimos_4):
                    val_t = formatear_a_minutos(ultimos_4[idx]["tiempo"])
                    f_est = estimar_fecha_marca(
                        fecha_nac, ultimos_4[idx].get("edad")
                    )
                    fila[col_nombre] = f"{val_t} ({f_est})" if f_est else val_t
                  else:
                    fila[col_nombre] = "-"

              registros_tabla.append(fila)

          df_resultado = pd.DataFrame(registros_tabla)

          st.markdown("---")
          st.markdown("#### 📄 Previsualización de Datos")
          st.dataframe(df_resultado, use_container_width=True)

          if formato_exportacion == "CSV (Excel)":
            csv_data = df_resultado.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 Descargar archivo CSV / Excel",
                data=csv_data,
                file_name="nomina_inscripciones_campeonato.csv",
                mime="text/csv",
                use_container_width=True,
            )
          else:
            html_css = f"""
                    <style>
                        .tabla-campeonato {{
                            width: 100%;
                            border-collapse: collapse;
                            font-family: 'Segoe UI', Arial, sans-serif;
                            font-size: 13px;
                        }}
                        .tabla-campeonato th {{
                            background-color: #0284C7;
                            color: white;
                            padding: 8px;
                            border: 1px solid #CBD5E1;
                            text-align: center;
                        }}
                        .tabla-campeonato td {{
                            padding: 6px;
                            border: 1px solid #CBD5E1;
                            text-align: center;
                        }}
                        .tabla-campeonato tr:nth-child(even) {{
                            background-color: #F8FAFC;
                        }}
                    </style>
                    {df_resultado.to_html(classes='tabla-campeonato', index=False)}
                    """
            st.components.v1.html(html_css, height=400, scrolling=True)
            st.download_button(
                label="📥 Descargar Archivo HTML con Estilos CSS",
                data=html_css.encode("utf-8"),
                file_name="nomina_inscripcion_estilizada.html",
                mime="text/html",
                use_container_width=True,
            )
