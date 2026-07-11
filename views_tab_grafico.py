# =============================================================================
# INTEGRACIÓN CORRECTA EN: views/views_tab_grafico.py
# =============================================================================
import io
import datetime
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# Importaciones requeridas desde sus librerías de funciones unificadas
try:
    from formulas_lib_funciones import (
        resolver_k_individual,
        calcular_curva_atleta,
        formatear_a_minutos,
        calcular_categoria_competencia,
        calcular_puntos_wa,
        obtener_datos_hitos_atleta
    )
except ImportError:
    from formulas_lib_funciones import (
        resolver_k_individual,
        calcular_curva_atleta,
        formatear_a_minutos,
        calcular_categoria_competencia
    )
    def calcular_puntos_wa(tiempo, wr):
        if wr <= 0 or tiempo <= 0:
            return 0
        return int(1000 * (wr / tiempo) ** 3)
        
    def obtener_datos_hitos_atleta(nadador_id):
        return None

def renderizar_tab_grafico(datos_sidebar):
    # 1. Extracción de variables de control pasadas por el diccionario
    titulo_grafico = datos_sidebar.get("titulo_grafico", "")
    simulacion_externa = datos_sidebar.get("simulacion_externa", False)
    modo_equipo = datos_sidebar.get("modo_equipo", False)
    df_procesado = datos_sidebar.get("df_procesado", pd.DataFrame())
    
    # Parámetros globales fijos o de configuración del sistema
    supabase = st.session_state.get("supabase") 
    t_peak = float(st.session_state.get("t_peak", 18.0))
    h = float(st.session_state.get("h_factor", 0.05))
    t_intermedia = float(st.session_state.get("t_intermedia", 15.0))
    
    # Variables de límites de cortes regulatorios (m_wr, m_ano, etc.)
    m_wr = float(st.session_state.get("m_wr", 0.0))
    m_ano = float(st.session_state.get("m_ano", 0.0))
    m_panam_a = float(st.session_state.get("m_panam_a", 0.0))
    m_panam_b = float(st.session_state.get("m_panam_b", 0.0))
    m_wa_a = float(st.session_state.get("m_wa_a", 0.0))
    m_wa_b = float(st.session_state.get("m_wa_b", 0.0))
    es_preinfantil = st.session_state.get("es_preinfantil", False)

    fig = None  # Inicialización de la figura para evitar NameError en exportación

    # -------------------------------------------------------------
    # BIFURCACIÓN PRINCIPAL DE RENDIMIENTO
    # -------------------------------------------------------------
    if modo_equipo:
        # MODO EQUIPO: Métricas contextualizadas al Colectivo
        c1, c2, c3 = st.columns(3)
        with c1: st.metric(label="Análisis de Rendimiento", value="Modo Equipo")
        with c2: st.metric(label="Prueba Evaluada", value=titulo_grafico)
        with c3: st.metric(label="Corte de Proyección Base", value=f"{t_peak:.1f} años")

        try:
            # Captura de filtros desde la UI/Session State
            filtro_genero = st.session_state.get("filtro_genero", "Todos")
            tipo_filtro = st.session_state.get("tipo_filtro", "Todos los Atletas")
            cat_sel = st.session_state.get("categoria_seleccionada", None)
            ids_sel = st.session_state.get("atletas_especificos_ids", [])

            # Descarga masiva inicial
            resp_todos = supabase.table("usuarios").select("id, nombre, fecha_nacimiento, genero").eq("rol", "Nadador").eq("estatus", "Activo").execute()
            atletas_lista = resp_todos.data if resp_todos.data else []
            
            if filtro_genero == "Femenino (F)":
                atletas_lista = [a for a in atletas_lista if a.get("genero") == "F"]
            elif filtro_genero == "Masculino (M)":
                atletas_lista = [a for a in atletas_lista if a.get("genero") == "M"]
    
            atletas_filtrados = []
            if tipo_filtro == "Todos los Atletas":
                atletas_filtrados = atletas_lista
            elif tipo_filtro == "Categoría Etaria" and cat_sel:
                atletas_filtrados = [a for a in atletas_lista if a.get("categoria") == cat_sel]
            elif tipo_filtro == "Atletas Específicos" and ids_sel:
                atletas_filtrados = [a for a in atletas_lista if a["id"] in ids_sel]
    
            if not atletas_filtrados:
                st.warning("No se encontraron atletas activos con los criterios de segmentación elegidos.")
                return

            lista_ids = [atl["id"] for atl in atletas_filtrados]
            
            res_marcas_colectivo = supabase.table("marcas_historicas")\
                .select("usuario_id, edad, tiempo, nota")\
                .eq("prueba", titulo_grafico)\
                .in_("usuario_id", lista_ids)\
                .order("edad", desc=False).execute()
                
            df_global_marcas = pd.DataFrame(res_marcas_colectivo.data) if res_marcas_colectivo.data else pd.DataFrame()
            
            if df_global_marcas.empty:
                st.info("No se hallaron marcas en la base de datos para los nadadores seleccionados en esta prueba.")
                return

            fig = plt.figure(figsize=(8.5, 11.0))
            ax = fig.add_axes([0.14, 0.58, 0.72, 0.33])
            
            formateador_eje_y = FuncFormatter(lambda x, pos: formatear_a_minutos(x))
            ax.yaxis.set_major_formatter(formateador_eje_y)
            
            colores = plt.get_cmap("tab10", len(atletas_filtrados))
            hay_datos_visibles = False
            linea_fisiologica_anotada = False
            
            todas_las_edades_0 = []
            todos_los_tiempos_colectivo = []
            datos_atletas_cargados = []
            
            for idx, atl in enumerate(atletas_filtrados):
                a_id = atl["id"]
                a_nom = atl["nombre"]
                
                if a_id in df_global_marcas["usuario_id"].values:
                    df_atl_m = df_global_marcas[df_global_marcas["usuario_id"] == a_id].copy()
                    df_atl_m = df_atl_m.rename(columns={"edad": "Edad", "tiempo": "Tiempo", "nota": "Evento / Fecha"})
                    hay_datos_visibles = True
                    
                    todas_las_edades_0.append(float(df_atl_m.iloc[0]["Edad"]))
                    todos_los_tiempos_colectivo.extend(df_atl_m["Tiempo"].tolist())
                    
                    datos_atletas_cargados.append({
                        "nom": a_nom,
                        "df": df_atl_m,
                        "color": colores(idx)
                    })

            if hay_datos_visibles:
                edad_0_min_colectivo = min(todas_las_edades_0)
                lim_x_min = max(4.0, edad_0_min_colectivo - 0.5)
                lim_x_max = t_peak + 1.0
                ax.set_xlim(lim_x_min, lim_x_max)
                
                peor_tiempo_colectivo = max(todos_los_tiempos_colectivo)
                lim_y_inferior = m_wr * 0.95 if m_wr > 0 else peor_tiempo_colectivo * 0.5
                lim_y_superior = peor_tiempo_colectivo + (peor_tiempo_colectivo * 0.05)
                ax.set_ylim(lim_y_inferior, lim_y_superior)
                
                for item in datos_atletas_cargados:
                    df_atl_m = item["df"]
                    color_curr = item["color"]
                    a_nom = item["nom"]
                    
                    t0_i = float(df_atl_m.iloc[0]["Edad"])
                    T0_i = float(df_atl_m.iloc[0]["Tiempo"])
                    idx_pb_i = df_atl_m["Tiempo"].idxmin()
                    t_pb_i = float(df_atl_m.loc[idx_pb_i, "Edad"])
                    T_pb_i = float(df_atl_m.loc[idx_pb_i, "Tiempo"])
                    
                    T_target_i = st.session_state.get(f"target_{a_id}", m_wr if m_wr > 0 else T_pb_i * 0.9)
                    
                    k_i = resolver_k_individual(t0_i, T0_i, t_pb_i, T_pb_i, t_peak, T_target_i)
                    edades_curva_i = np.linspace(t0_i, t_peak, 300)
                    tiempos_curva_i = calcular_curva_atleta(edades_curva_i, t0_i, T0_i, t_pb_i, T_pb_i, t_peak, T_target_i, k_i, h)
                    
                    if not linea_fisiologica_anotada:
                        ax.plot(edades_curva_i, tiempos_curva_i, color="#7F8C8D", linestyle=":", linewidth=1.2, label="Proyección fisiológica estimada")
                        linea_fisiologica_anotada = True
                    else:
                        ax.plot(edades_curva_i, tiempos_curva_i, color="#7F8C8D", linestyle=":", linewidth=1.2)
                    
                    ax.plot(df_atl_m["Edad"], df_atl_m["Tiempo"], color=color_curr, linestyle="-", linewidth=1.5, label=f"Evolución real - {a_nom}")
                    ax.scatter(df_atl_m["Edad"], df_atl_m["Tiempo"], color=color_curr, edgecolor="black", s=25, linewidths=0.5, zorder=3)
                    ax.scatter(t_pb_i, T_pb_i, color=color_curr, marker="*", edgecolor="black", s=80, linewidths=0.5, zorder=5)

                x_texto = lim_x_min + 0.1
                if not es_preinfantil:
                    referencias = [
                        {"val": m_ano, "lbl": "Mín. Año", "col": "#A06000", "va": "bottom"}, 
                        {"val": m_panam_b, "lbl": "PANAM Jr B", "col": "#006644", "va": "bottom"},      
                        {"val": m_panam_a, "lbl": "PANAM Jr A", "col": "#2A658A", "va": "top"},   
                        {"val": m_wa_b, "lbl": "WA B", "col": "#943100", "va": "bottom"},            
                        {"val": m_wa_a, "lbl": "WA A", "col": "#883963", "va": "top"},          
                        {"val": m_wr, "lbl": "World Record", "col": "#2C3E50", "va": "top"}   
                    ]
                    for r in referencias:
                        if r["val"] > 0 and lim_y_inferior <= r["val"] <= lim_y_superior:
                            ax.axhline(y=r["val"], color=r["col"], linestyle=":", linewidth=0.6, alpha=0.7)
                            desplazamiento_y = (lim_y_superior - lim_y_inferior) * 0.006 if r["va"] == "bottom" else -((lim_y_superior - lim_y_inferior) * 0.006)
                            tiempo_lbl_formateado = formatear_a_minutos(r["val"]).replace(" s", "")
                            ax.text(x_texto, r["val"] + desplazamiento_y, f"{r['lbl']}: {tiempo_lbl_formateado}", color=r["col"], fontsize=7, va=r["va"], ha="left")
                else:
                    if m_ano > 0:
                        ax.axhline(y=m_ano, color="#A06000", linestyle="--", linewidth=0.6, alpha=0.7)
                        m_ano_formateado = formatear_a_minutos(m_ano).replace(" s", "")
                        ax.text(x_texto, m_ano - ((lim_y_superior - lim_y_inferior) * 0.006), f"Target (Base Inf. A): {m_ano_formateado}", color="#A06000", fontsize=7, va="top", ha="left")
                
                ax.set_title(f"Análisis Comparativo de Equipo - {titulo_grafico}", fontsize=12, pad=10)
                ax.set_xlabel("Edad del Atleta (Años)", fontsize=9.5)
                ax.set_ylabel("Tiempo de Carrera (Segundos)", fontsize=9.5)
                ax.grid(True, which="both", axis="both", linestyle=":", color="#CCD1D1", linewidth=0.5)
                ax.set_axisbelow(True)
                ax.legend(loc="upper right", fontsize=8, framealpha=0.8)
                
                st.pyplot(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error procesando los segmentos de equipo: {e}")

    else:
        # -------------------------------------------------------------
        # MODO INDIVIDUAL O SIMULACIÓN (Métricas individuales reales)
        # -------------------------------------------------------------
        # Extracción segura de controles de vista desde el diccionario de la barra lateral
        tipo_vista = datos_sidebar.get("tipo_vista", "Macro (Perspectiva Global)")
        edad_min_zoom = float(datos_sidebar.get("edad_min_zoom", 10.0))
        edad_max_zoom = float(datos_sidebar.get("edad_max_zoom", 18.0))

        # Recuperación de marcas individuales del atleta seleccionado activo
        k = float(st.session_state.get("k_atleta_activo", 0.4))
        T_pb = float(st.session_state.get("T_pb_activo", 0.0))
        T_target = float(st.session_state.get("T_target_activo", 0.0))
        t0 = float(st.session_state.get("t0_activo", 10.0))
        T0 = float(st.session_state.get("T0_activo", 0.0))
        t_pb = float(st.session_state.get("t_pb_activo", 12.0))

        val_T0 = T0
        val_T_pb = T_pb

        c1, c2, c3 = st.columns(3)
        with c1: st.metric(label="Factor de Ajuste Fisiológico (k)", value=f"{k:.4f}")
        with c2: st.metric(label="Margen de Deriva de Seguridad (D)", value=f"{(T_pb - T_target):.2f} s")
        with c3: 
            T_intermedia_val = float(calcular_curva_atleta([t_intermedia], t0, T0, t_pb, T_pb, t_peak, T_target, k, h)[0])
            tiempo_formateado = formatear_a_minutos(T_intermedia_val) 
            st.metric(label=f"Proyección a los {t_intermedia:.1f} años", value=tiempo_formateado)

        # Lienzo Gráfico Individual
        fig = plt.figure(figsize=(8.5, 11.0))
        ax = fig.add_axes([0.14, 0.58, 0.72, 0.33])
        formateador_eje_y = FuncFormatter(lambda x, pos: formatear_a_minutos(x))
        ax.yaxis.set_major_formatter(formateador_eje_y)

        edades_curva = np.linspace(t0, t_peak, 300)
        tiempos_curva = calcular_curva_atleta(edades_curva, t0, T0, t_pb, T_pb, t_peak, T_target, k, h)
        
        todos_los_tiempos_ind = [T0, T_pb, T_target]
        if not simulacion_externa and len(df_procesado) > 0:
            todos_los_tiempos_ind.extend(df_procesado["Tiempo"].tolist())
    
        if tipo_vista == "Micro (Ventana Anual)":
            edades_ventana = np.linspace(edad_min_zoom, edad_max_zoom, 300)
            tiempos_curva_ventana = calcular_curva_atleta(edades_ventana, t0, T0, t_pb, T_pb, t_peak, T_target, k, h).tolist()
            
            tiempos_reales_ventana = []
            if not simulacion_externa and len(df_procesado) > 0:
                for _, row in df_procesado.iterrows():
                    if edad_min_zoom <= row["Edad"] <= edad_max_zoom:
                        tiempos_reales_ventana.append(row["Tiempo"])
                        
            todos_tiempos_v = tiempos_curva_ventana + tiempos_reales_ventana
            
            if todos_tiempos_v:
                t_min_v = min(todos_tiempos_v)
                t_max_v = max(todos_tiempos_v)
            else:
                t_min_v = min(tiempos_curva)
                t_max_v = max(tiempos_curva)
    
            margen_y = max(0.5, (t_max_v - t_min_v) * 0.15)
            lim_y_inferior = t_min_v - margen_y
            lim_y_superior = t_max_v + margen_y
            
            lim_x_min = edad_min_zoom
            lim_x_max = edad_max_zoom
        else:
            peor_tiempo_ind = max(todos_los_tiempos_ind)
            lim_y_inferior = m_wr * 0.92 if m_wr > 0 else min(todos_los_tiempos_ind) * 0.90
            lim_y_superior = peor_tiempo_ind + (peor_tiempo_ind * 0.08)
            
            if len(df_procesado) > 0:
                min_edad_real = float(df_procesado["Edad"].min())
                lim_x_min = min(float(t0), min_edad_real) - 0.5
            else:
                lim_x_min = max(4.0, float(t0) - 0.5)
                
            lim_x_max = t_peak + 1.0
    
        ax.set_xlim(lim_x_min, lim_x_max)
        ax.set_ylim(lim_y_inferior, lim_y_superior)
        ax.set_autoscale_on(False)
    
        datos_tabla_micro = []
        nadador_id = st.session_state.get("nadador_seleccionado_id")
        
        if nadador_id and tipo_vista == "Micro (Ventana Anual)":
            datos_atleta = obtener_datos_hitos_atleta(nadador_id)
            if datos_atleta and datos_atleta.get("fecha_nacimiento"):
                try:
                    fecha_nacimiento_real = datetime.date.fromisoformat(str(datos_atleta["fecha_nacimiento"])[:10])
                except Exception:
                    fecha_nacimiento_real = None
                
                if fecha_nacimiento_real:
                    for hito in datos_atleta.get("hitos", []):
                        try:
                            comp_info = hito.get("catalogo_competencias")
                            if not comp_info:
                                continue
                            
                            fecha_comp_str = comp_info.get("fecha_inicio") or comp_info.get("fecha")
                            if not fecha_comp_str:
                                continue
                            
                            if isinstance(fecha_comp_str, str):
                                fecha_evento_real = datetime.date.fromisoformat(fecha_comp_str[:10])
                            elif isinstance(fecha_comp_str, (datetime.date, datetime.datetime)):
                                fecha_evento_real = fecha_comp_str if isinstance(fecha_comp_str, datetime.date) else fecha_comp_str.date()
                            else:
                                continue
                            
                            dias_de_vida = (fecha_evento_real - fecha_nacimiento_real).days
                            edad_hito_calculada = dias_de_vida / 365.25
    
                            if lim_x_min <= edad_hito_calculada <= lim_x_max:
                                es_elegible = hito.get("elegible", True)
                                color_linea = "#2ECC71" if es_elegible else "#E74C3C" 
                                estilo_linea = "--" if es_elegible else ":"
                                
                                ax.axvline(
                                    x=edad_hito_calculada, 
                                    color=color_linea, 
                                    linestyle=estilo_linea, 
                                    linewidth=0.7, 
                                    alpha=0.6, 
                                    zorder=5
                                )
                                
                                y_pos = lim_y_inferior + ((lim_y_superior - lim_y_inferior) * 0.03)
                                nombre_evento = comp_info.get("nombre_evento") or "Competencia"
                                nombre_corto = nombre_evento[:18] + "..." if len(nombre_evento) > 18 else nombre_evento
                                
                                ax.text(
                                    x=edad_hito_calculada + 0.015, 
                                    y=y_pos, 
                                    s=f"{nombre_corto} {fecha_evento_real.strftime('%d/%m/%Y')}", 
                                    color=color_linea, 
                                    fontsize=7.5, 
                                    weight="light",
                                    rotation=90, 
                                    va="bottom", 
                                    ha="left", 
                                    alpha=0.85, 
                                    zorder=6
                                )
    
                                tiempo_proyectado_val = calcular_curva_atleta(
                                    [edad_hito_calculada], t0, T0, t_pb, T_pb, t_peak, T_target, k, h
                                )[0]
                                
                                datos_tabla_micro.append({
                                    "Competencia / Evento": nombre_evento,
                                    "Fecha": fecha_evento_real.strftime('%d/%m/%Y'),
                                    "Edad": f"{edad_hito_calculada:.2f} a",
                                    "Marca Proyectada": f"{formatear_a_minutos(tiempo_proyectado_val)} s"
                                })
                        except Exception as e_hito:
                            print(f"Advertencia procesando hito individual: {e_hito}")
    
        if datos_tabla_micro:
            datos_tabla_micro.sort(key=lambda x: float(x["Edad"].replace(" a", "").strip()))
    
        ax.plot(edades_curva, tiempos_curva, color="#007A87", linewidth=1.8, label="Proyección Fisiológica")
    
        if not simulacion_externa and len(df_procesado) > 0:
            ax.plot(df_procesado["Edad"], df_procesado["Tiempo"], color="#D55E00", linestyle="--", linewidth=1.0, alpha=0.6, label="Evolución Real (PBs)")
            ax.scatter(df_procesado["Edad"], df_procesado["Tiempo"], color="#D55E00", edgecolor="black", s=25, linewidths=0.6, zorder=3)
    
        offset_y = (lim_y_superior - lim_y_inferior) * 0.025
        estilo_bbox = dict(boxstyle="round,pad=0.25", fc="#F8F9F9", ec="#BDC3C7", alpha=0.9, linewidth=0.5)
    
        if lim_x_min <= t0 <= lim_x_max and lim_y_inferior <= T0 <= lim_y_superior:
            ax.scatter(t0, T0, color="#7F8C8D", edgecolor="black", s=35, linewidths=0.6, zorder=4)
            ax.text(t0 + 0.1, T0, f"P. Start\n{t0:.2f}a\n{formatear_a_minutos(val_T0)}", fontsize=8, va="bottom", ha="left", bbox=estilo_bbox)
            ax.axvline(x=t0, color="#7F8C8D", linestyle=":", linewidth=0.7, alpha=0.5)
    
        if lim_x_min <= t_pb <= lim_x_max and lim_y_inferior <= T_pb <= lim_y_superior:
            ax.scatter(t_pb, T_pb, color="#F1C40F", marker="*", edgecolor="black", s=100, linewidths=0.6, zorder=5, label="PB Actual de Control")
            ax.text(t_pb + 0.15, T_pb, f"PB Actual\n{t_pb:.2f}a\n{formatear_a_minutos(val_T_pb)}", fontsize=8, va="center", ha="left", bbox=estilo_bbox)
            ax.axvline(x=t_pb, color="red", linestyle="--", linewidth=0.7, alpha=0.4)
    
        if lim_x_min <= t_intermedia <= lim_x_max and lim_y_inferior <= T_intermedia_val <= lim_y_superior:
            ax.scatter(t_intermedia, T_intermedia_val, color="red", marker="o", s=30, zorder=5, label="Punto Consultado")
            ax.text(t_intermedia, T_intermedia_val + offset_y, f"Consulta: {t_intermedia:.1f}a\n{formatear_a_minutos(T_intermedia_val)}", fontsize=8, va="bottom", ha="center", bbox=estilo_bbox)
            ax.axvline(x=t_intermedia, color="red", linestyle=":", linewidth=0.7, alpha=0.4)
    
        if lim_x_min <= t_peak <= lim_x_max and lim_y_inferior <= T_target <= lim_y_superior:
            ax.scatter(t_peak, T_target, color="#2ECC71", marker="s", edgecolor="black", s=35, linewidths=0.6, zorder=4, label="Meta Peak")
            ax.text(t_peak - 0.1, T_target, f"Meta Peak\n{t_peak:.2f}a\n{formatear_a_minutos(T_target)}", fontsize=8, va="bottom", ha="right", bbox=estilo_bbox)
            ax.axvline(x=t_peak, color="#2ECC71", linestyle=":", linewidth=0.7, alpha=0.5)
    
        x_texto = lim_x_min + (lim_x_max - lim_x_min) * 0.05
        if not es_preinfantil:
            referencias = [
                {"val": m_ano, "lbl": "Mín. Año", "col": "#A06000", "va": "bottom"}, 
                {"val": m_panam_b, "lbl": "PANAM Jr B", "col": "#006644", "va": "bottom"},      
                {"val": m_panam_a, "lbl": "PANAM Jr A", "col": "#2A658A", "va": "top"},   
                {"val": m_wa_b, "lbl": "WA B", "col": "#943100", "va": "bottom"},                
                {"val": m_wa_a, "lbl": "WA A", "col": "#883963", "va": "top"},            
                {"val": m_wr, "lbl": "World Record", "col": "#2C3E50", "va": "top"}   
            ]
            
            for r in referencias:
                if r["val"] > 0 and lim_y_inferior <= r["val"] <= lim_y_superior:
                    ax.axhline(y=r["val"], color=r["col"], linestyle=":", linewidth=0.6, alpha=0.7)
                    desplazamiento_y = (lim_y_superior - lim_y_inferior) * 0.006 if r["va"] == "bottom" else -((lim_y_superior - lim_y_inferior) * 0.006)
                    tiempo_lbl_formateado = formatear_a_minutos(r["val"]).replace(" s", "")
                    ax.text(x_texto, r["val"] + desplazamiento_y, f"{r['lbl']}: {tiempo_lbl_formateado}", color=r["col"], fontsize=7, va=r["va"], ha="left")
        else:
            if m_ano > 0:
                ax.axhline(y=m_ano, color="#A06000", linestyle="--", linewidth=0.6, alpha=0.7)
                m_ano_formateado = formatear_a_minutos(m_ano).replace(" s", "")
                ax.text(x_texto, m_ano - ((lim_y_superior - lim_y_inferior) * 0.006), f"Target (Base Inf. A): {m_ano_formateado}", color="#A06000", fontsize=7, va="top", ha="left")
        
        if simulacion_externa:
            ax.set_title(f"Simulación de Escenarios - {titulo_grafico}", fontsize=12, pad=10)
        else:
            nombre_n = st.session_state.get('nadador_seleccionado_nombre', 'Atleta')
            cat_n = st.session_state.get('nadador_seleccionado_categoria', 'General')
            ax.set_title(f"Curva de Rendimiento Asintótica - {titulo_grafico}\nAtleta: {nombre_n} | Categoría: {cat_n}", fontsize=12, pad=10)
    
        ax.set_xlabel("Edad del Atleta (Años)", fontsize=9.5)
        ax.set_ylabel("Tiempo de Carrera (Segundos)", fontsize=9.5)
        ax.grid(True, which="both", axis="both", linestyle=":", color="#CCD1D1", linewidth=0.5)
        ax.set_axisbelow(True) 
        
        tamano_leyenda = 6.5 if tipo_vista == "Micro (Ventana Anual)" else 8
        ax.legend(loc="upper right", fontsize=tamano_leyenda, framealpha=0.8)
    
        df_table_render = None
        es_modo_micro_tabla = (tipo_vista == "Micro (Ventana Anual)")
    
        if es_modo_micro_tabla:
            if datos_tabla_micro:
                df_table_render = pd.DataFrame(datos_tabla_micro)
                anchos_columnas = [0.46, 0.18, 0.16, 0.20]
            else:
                df_table_render = pd.DataFrame([{
                    "Competencia / Evento": "No hay hitos o competencias en este rango de edad",
                    "Fecha": "-",
                    "Edad": "-",
                    "Tiempo Prog.": "-"
                }])
                anchos_columnas = [0.52, 0.16, 0.16, 0.16]
        else:
            if not simulacion_externa and len(df_procesado) > 0:
                df_table_render = df_procesado[["Edad", "Tiempo", "Evento / Fecha"]].copy()
                
                wr_referencia_real = m_wr
                
                df_table_render["WA"] = df_table_render["Tiempo"].apply(
                    lambda x: calcular_puntos_wa(x, wr_referencia_real)
                )
                
                df_table_render = df_table_render[["Edad", "Tiempo", "WA", "Evento / Fecha"]]
                
                df_table_render["Edad"] = df_table_render["Edad"].map(lambda x: f"{x:.2f} a")
                df_table_render["Tiempo"] = df_table_render["Tiempo"].apply(formatear_a_minutos)
                df_table_render["WA"] = df_table_render["WA"].map(lambda x: f"{x} pts" if x > 0 else "-")
                
                anchos_columnas = [0.13, 0.13, 0.14, 0.60]
            else:
                df_table_render = pd.DataFrame([{
                    "Edad": "-", 
                    "Tiempo": "-", 
                    "WA": "-",
                    "Evento / Fecha": "Sin marcas históricas registradas"
                }])
                anchos_columnas = [0.13, 0.13, 0.14, 0.60]
    
        if df_table_render is not None and not df_table_render.empty:
            total_filas = len(df_table_render)
            limite_filas_por_bloque = 18
            
            def estilizar_tabla_nativo(instancia_tabla):
                instancia_tabla.auto_set_font_size(False)
                instancia_tabla.set_fontsize(8.5)
                instancia_tabla.scale(1.0, 1.3)
                for (row, col), cell in instancia_tabla.get_celld().items():
                    cell.set_linewidth(0.5)
                    cell.set_edgecolor('#E5E7EB')
                    if row == 0:
                        cell.set_text_props(color='black', weight='light')
                        cell.set_facecolor('#C0C0C0')
                    else:
                        cell.set_facecolor('#F8F9F9' if row % 2 == 0 else 'white')
    
            if total_filas <= limite_filas_por_bloque:
                ax_table = fig.add_axes([0.14, 0.054, 0.72, 0.48])
                ax_table.axis('off')
                mpl_table = ax_table.table(
                    cellText=df_table_render.values, 
                    colLabels=df_table_render.columns, 
                    cellLoc='center', 
                    loc='upper center', 
                    colWidths=anchos_columnas
                )
                estilizar_tabla_nativo(mpl_table)
            else:
                if total_filas > 36: 
                    df_table_render = df_table_render.iloc[:32]
                df_bloque_izq = df_table_render.iloc[:limite_filas_por_bloque]
                df_bloque_der = df_table_render.iloc[limite_filas_por_bloque:]
                
                anchos_doble = anchos_columnas if es_modo_micro_tabla else [0.15, 0.15, 0.16, 0.54]
                
                ax_table1 = fig.add_axes([0.14, 0.054, 0.34, 0.48])
                ax_table1.axis('off')
                mpl_table1 = ax_table1.table(cellText=df_bloque_izq.values, colLabels=df_bloque_izq.columns, cellLoc='center', loc='upper center', colWidths=anchos_doble)
                estilizar_tabla_nativo(mpl_table1)
                
                ax_table2 = fig.add_axes([0.52, 0.054, 0.34, 0.54])
                ax_table2.axis('off')
                mpl_table2 = ax_table2.table(cellText=df_bloque_der.values, colLabels=df_bloque_der.columns, cellLoc='center', loc='upper center', colWidths=anchos_doble)
                estilizar_tabla_nativo(mpl_table2)
    
        st.pyplot(fig, use_container_width=True)
    
    # -------------------------------------------------------------------------
    # ST.MARKDOWN - CENTRO DE EXPORTACIÓN
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🖨️ Centro de Exportación de Reportes y Gráficos")
    
    if len(df_procesado) > 0 or modo_equipo:
        export_df = df_procesado.drop(columns=["id", "usuario_id"], errors="ignore")
        csv_data = export_df.to_csv(index=False).encode('utf-8')
        txt_string = export_df.to_string(index=False)
        
        img_buffer = None
        
        if 'fig' in locals() and fig is not None:
            try:
                img_buffer = io.BytesIO()
                fig.savefig(img_buffer, format="png", bbox_inches=None, dpi=300)
                img_buffer.seek(0)
            except Exception as e_exp:
                print(f"Error generando imagen de exportación: {e_exp}")
        
        c_exp1, c_exp2, c_exp3 = st.columns(3)
        with c_exp1:
            st.download_button(label="📥 Descargar Historial (CSV)", data=csv_data, file_name=f"marcas_{titulo_grafico}_{st.session_state.get('nadador_seleccionado_nombre', 'equipo')}.csv", mime="text/csv")
        with c_exp2:
            st.download_button(label="📄 Descargar Datos (TXT)", data=txt_string, file_name=f"reporte_{titulo_grafico}_{st.session_state.get('nadador_seleccionado_nombre', 'equipo')}.txt", mime="text/plain")
        with c_exp3:
            if img_buffer is not None:
                st.download_button(label="🖼️ Guardar Gráfico Completo (Imagen PNG - Tamaño Carta)", data=img_buffer, file_name=f"grafico_{titulo_grafico}_{st.session_state.get('nadador_seleccionado_nombre', 'equipo')}.png", mime="image/png")
            else:
                st.info("📉 Gráfico no disponible para descarga PNG.")
