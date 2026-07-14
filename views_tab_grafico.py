import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# 📦 IMPORTACIONES DE FUNCIONES LOCALES
from formulas_lib_funciones import (
    resolver_k_individual, 
    calcular_curva_atleta, 
    formatear_a_minutos, 
    calcular_edad_decimal
)
from conections_supabase_cache import (
    obtener_marcas_referencia_cache, 
    obtener_historial_hitos_cache
)

def renderizar_tab_grafico(datos_sidebar):
    """
    Renderiza el gráfico de rendimiento combinando proyecciones exponenciales,
    datos históricos reales y referencias obtenidas directamente desde Supabase.
    """
    # =====================================================================
    # 1. EXTRACCIÓN DE VARIABLES Y CONTEXTO
    # =====================================================================
    modo_equipo = datos_sidebar.get("modo_equipo", False)
    simulacion_externa = datos_sidebar.get("simulacion_externa", False)
    tipo_vista = datos_sidebar.get("tipo_vista", "Macro (Historial Completo)")
    titulo_grafico = datos_sidebar.get("titulo_grafico", "Proyección de Rendimiento")
    
    t_peak = float(datos_sidebar.get("t_peak", 23.0))
    T_target = float(datos_sidebar.get("T_target", 0.0))
    h = float(datos_sidebar.get("factor_h", 0.35))
    edad_intermedia = float(datos_sidebar.get("t_intermedia", 18.0))

    prueba = datos_sidebar.get("prueba", datos_sidebar.get("prueba_seleccionada", ""))
    genero = datos_sidebar.get("genero", datos_sidebar.get("genero_atleta", "M"))
    categoria = datos_sidebar.get("categoria", datos_sidebar.get("categoria_atleta", ""))
    usuario_id = datos_sidebar.get("usuario_id", datos_sidebar.get("id", ""))

    # =====================================================================
    # 2. CONSULTAS A LA CACHÉ DE SUPABASE
    # =====================================================================
    m_ano = float(datos_sidebar.get("m_ano", 0.0))
    m_panam_b = float(datos_sidebar.get("m_panam_b", 0.0))
    m_panam_a = float(datos_sidebar.get("m_panam_a", 0.0))
    m_wa_b = float(datos_sidebar.get("m_wa_b", 0.0))
    m_wa_a = float(datos_sidebar.get("m_wa_a", 0.0))
    wr = float(datos_sidebar.get("m_wr", 25.0))

    referencias_raw = obtener_marcas_referencia_cache(prueba, genero, categoria)
    hitos_raw = obtener_historial_hitos_cache(usuario_id) if not simulacion_externa and not modo_equipo else []

    if referencias_raw:
        ref_data = referencias_raw[0]
        m_ano = float(ref_data.get("m_ano", m_ano) or m_ano)
        m_panam_b = float(ref_data.get("m_panam_b", m_panam_b) or m_panam_b)
        m_panam_a = float(ref_data.get("m_panam_a", m_panam_a) or m_panam_a)
        m_wa_b = float(ref_data.get("m_wa_b", m_wa_b) or m_wa_b)
        m_wa_a = float(ref_data.get("m_wa_a", m_wa_a) or m_wa_a)
        wr = float(ref_data.get("m_wr", wr) or wr)

    # =====================================================================
    # 3. RECOPILACIÓN ORGANIZADA DE DATOS SEGÚN ESCENARIO
    # =====================================================================
    df_procesado = pd.DataFrame() # Inicialización segura para exportación

    if modo_equipo:
        lista_atletas = datos_sidebar.get("lista_atletas_filtrados", [])
        df_global = datos_sidebar.get("df_global_marcas", pd.DataFrame())
        if df_global.empty or not lista_atletas:
            st.info("No hay atletas que cumplan con los filtros seleccionados.")
            return
    else:
        if simulacion_externa:
            t0 = float(datos_sidebar.get("t0", 10.0))
            T0 = float(datos_sidebar.get("T0", 0.0))
            t_pb = float(datos_sidebar.get("t_pb", 12.0))
            T_pb = float(datos_sidebar.get("T_pb", 0.0))
            if T0 == 0.0 or T_pb == 0.0:
                st.info("Ingrese valores válidos en el simulador del panel lateral (T0 y T_pb).")
                return
        else:
            df_procesado = datos_sidebar.get("df_procesado")
            if df_procesado is None or df_procesado.empty:
                st.info("No hay marcas históricas registradas para este nadador en la prueba seleccionada.")
                return
            df_procesado = df_procesado.sort_values(by="Edad").reset_index(drop=True)
            t0 = float(df_procesado.iloc[0]["Edad"])
            T0 = float(df_procesado.iloc[0]["Tiempo"])
            idx_pb = df_procesado["Tiempo"].idxmin()
            t_pb = float(df_procesado.loc[idx_pb, "Edad"])
            T_pb = float(df_procesado.loc[idx_pb, "Tiempo"])

    # =====================================================================
    # 4. GESTIÓN DE ENCABEZADOS E INTERFAZ (INCLUYENDO MÉTRICAS)
    # =====================================================================
    if simulacion_externa:
        st.warning("⚠️ Modo Simulación Activo: Proyecciones basadas estrictamente en los parámetros ingresados.")
        st.subheader("Modo Simulación Externa (Proyección Aislada)")
    elif modo_equipo:
        st.subheader(f"Modo Equipo: {titulo_grafico}")
    else:
        st.subheader(f"Modo Individual - Vista {tipo_vista}: {titulo_grafico}")

    # CÁLCULO DE LAS MÉTRICAS SUPERIORES (Restaurado)
    if not modo_equipo and T0 != 0.0 and T_pb != 0.0:
        k_principal = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
        D_principal = T_pb - T_target
        c3_val = np.interp(edad_intermedia, np.linspace(t0, t_peak, 300), calcular_curva_atleta(np.linspace(t0, t_peak, 300), t0, T0, t_pb, T_pb, t_peak, T_target, k_principal, h))
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(label="Factor de Ajuste (k)", value=f"{k_principal:.4f}")
        with c2:
            st.metric(label="Margen de Deriva (D)", value=f"{formatear_a_minutos(D_principal)}")
        with c3:
            st.metric(label=f"Proyección a los {edad_intermedia} años", value=formatear_a_minutos(c3_val))

    # =====================================================================
    # 5. CONFIGURACIÓN DEL LIENZO MATPLOTLIB
    # =====================================================================
    fig = plt.figure(figsize=(8.5, 11.0))
    ax = fig.add_axes([0.14, 0.58, 0.72, 0.33])
    formatter = FuncFormatter(lambda y, pos: formatear_a_minutos(y))
    ax.yaxis.set_major_formatter(formatter)

    # Cálculos de curva (Atleta Principal / Simulación) (Corregido el +3)
    if not modo_equipo or (modo_equipo and T0 != 0.0):
        k = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
        edades_curva = np.linspace(t0, t_peak, 300) 
        curva_ind = calcular_curva_atleta(edades_curva, t0, T0, t_pb, T_pb, t_peak, T_target, k, h)
        c3 = np.interp(edad_intermedia, edades_curva, curva_ind)

    # =====================================================================
    # 6. DIBUJO DE CURVAS POR ESCENARIO
    # =====================================================================
    colores_equipo = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

    if modo_equipo:
        for idx, atleta in enumerate(lista_atletas):
            atleta_id = atleta.get("id")
            atleta_nombre = atleta.get("nombre")
            df_atleta = df_global[df_global["usuario_id"] == atleta_id].copy()
            if df_atleta.empty: continue
            
            # Garantizar que existe 'edad' y 'tiempo' para que no colapse
            if "edad" not in df_atleta.columns and "fecha_competencia" in df_atleta.columns:
                fecha_nac = atleta.get("fecha_nacimiento")
                df_atleta["edad"] = df_atleta["fecha_competencia"].apply(lambda x: calcular_edad_decimal(fecha_nac, x))
            
            if "tiempo" not in df_atleta.columns and "tiempo_segundos" in df_atleta.columns:
                df_atleta["tiempo"] = df_atleta["tiempo_segundos"]

            df_atleta = df_atleta.dropna(subset=["edad", "tiempo"]).sort_values(by="edad").reset_index(drop=True)
            if df_atleta.empty: continue

            t0_i = float(df_atleta.iloc[0]["edad"])
            T0_i = float(df_atleta.iloc[0]["tiempo"])
            idx_pb_i = df_atleta["tiempo"].idxmin()
            t_pb_i = float(df_atleta.loc[idx_pb_i, "edad"])
            T_pb_i = float(df_atleta.loc[idx_pb_i, "tiempo"])
            
            if T0_i == 0.0 or T_pb_i == 0.0: continue
            
            color_actual = colores_equipo[idx % len(colores_equipo)]
                
            # Curva Proyectada
            k_i = resolver_k_individual(t0_i, T0_i, t_pb_i, T_pb_i, t_peak, T_target)
            edades_curva_i = np.linspace(t0_i, t_peak, 300)
            curva_i = calcular_curva_atleta(edades_curva_i, t0_i, T0_i, t_pb_i, T_pb_i, t_peak, T_target, k_i, h)
            
            ax.plot(edades_curva_i, curva_i, label=f"Proy. {atleta_nombre}", color=color_actual, alpha=0.6, linewidth=1.2, linestyle='-')
            
            # Evolución Real y Marcador PB (Restaurado)
            ax.plot(df_atleta["edad"], df_atleta["tiempo"], color=color_actual, linestyle="--", linewidth=1.0, alpha=0.8)
            ax.scatter(df_atleta["edad"], df_atleta["tiempo"], color=color_actual, s=15, zorder=3)
            ax.scatter(t_pb_i, T_pb_i, color=color_actual, marker="*", edgecolor="black", s=80, zorder=5)

        lim_x_min, lim_x_max = ax.get_xlim()
        lim_y_inferior, lim_y_superior = ax.get_ylim()
        
    else:
        ax.plot(edades_curva, curva_ind, color='blue', label='Proyección Fisiológica', linewidth=1.5)
        
        if simulacion_externa:
            ax.set_xlim([t0 - 0.5, t_peak + 1.0])
        else:
            ax.plot(df_procesado["Edad"], df_procesado["Tiempo"], 'ro-', label="Marcas Reales", markersize=4)
            if "Micro" in tipo_vista:
                ax.set_xlim([datos_sidebar.get("edad_min_zoom", t0), datos_sidebar.get("edad_max_zoom", t_peak)])
            else:
                ax.set_xlim([t0 - 0.5, t_peak + 1.0])

        lim_x_min, lim_x_max = ax.get_xlim()
        lim_y_inferior, lim_y_superior = ax.get_ylim()

        # =====================================================================
        # 7. DIBUJO DE PUNTOS CRÍTICOS Y ETIQUETAS
        # =====================================================================
        offset_y = (lim_y_superior - lim_y_inferior) * 0.025
        estilo_bbox = dict(boxstyle="round,pad=0.25", fc="#F8F9F9", ec="#BDC3C7", alpha=0.9, linewidth=0.5)

        if not simulacion_externa:
            if df_procesado is not None and not df_procesado.empty:
                ax.plot(df_procesado["Edad"], df_procesado["Tiempo"], color="#D55E00", linestyle="--", linewidth=1.0, alpha=0.6, label="Evolución Real")
                ax.scatter(df_procesado["Edad"], df_procesado["Tiempo"], color="#D55E00", edgecolor="black", s=25, linewidths=0.6, zorder=3)

            if lim_x_min <= t0 <= lim_x_max and lim_y_inferior <= T0 <= lim_y_superior:
                ax.scatter(t0, T0, color="#7F8C8D", edgecolor="black", s=35, linewidths=0.6, zorder=4)
                ax.text(t0 + 0.1, T0, f"P. Start\n{t0:.2f}a\n{formatear_a_minutos(T0)}", fontsize=8, va="bottom", ha="left", bbox=estilo_bbox)
                ax.axvline(x=t0, color="#7F8C8D", linestyle=":", linewidth=0.7, alpha=0.5)

            if lim_x_min <= t_pb <= lim_x_max and lim_y_inferior <= T_pb <= lim_y_superior:
                ax.scatter(t_pb, T_pb, color="#F1C40F", marker="*", edgecolor="black", s=100, linewidths=0.6, zorder=5, label="PB Actual")
                ax.text(t_pb + 0.15, T_pb, f"PB Actual\n{t_pb:.2f}a\n{formatear_a_minutos(T_pb)}", fontsize=8, va="center", ha="left", bbox=estilo_bbox)
                ax.axvline(x=t_pb, color="red", linestyle="--", linewidth=0.7, alpha=0.4)

            if lim_x_min <= edad_intermedia <= lim_x_max and lim_y_inferior <= c3 <= lim_y_superior:
                ax.scatter(edad_intermedia, c3, color="red", marker="o", s=30, zorder=5)
                ax.text(edad_intermedia, c3 + offset_y, f"Consulta: {edad_intermedia:.1f}a\n{formatear_a_minutos(c3)}", fontsize=8, va="bottom", ha="center", bbox=estilo_bbox)
                ax.axvline(x=edad_intermedia, color="red", linestyle=":", linewidth=0.7, alpha=0.4)

            if lim_x_min <= t_peak <= lim_x_max and lim_y_inferior <= T_target <= lim_y_superior:
                ax.scatter(t_peak, T_target, color="#2ECC71", marker="s", edgecolor="black", s=35, linewidths=0.6, zorder=4, label="Meta Peak")
                ax.text(t_peak - 0.1, T_target, f"Meta Peak\n{t_peak:.2f}a\n{formatear_a_minutos(T_target)}", fontsize=8, va="bottom", ha="right", bbox=estilo_bbox)
                ax.axvline(x=t_peak, color="#2ECC71", linestyle=":", linewidth=0.7, alpha=0.5)
        
        elif simulacion_externa:
            st.markdown("### 🔍 Consultar Proyección en Edad Específica")
            t_intermedia = st.slider("Edad a consultar:", min_value=float(t0), max_value=float(t_peak), value=float(t_pb), step=0.25)
            
            # (Corregido) El bug de k_simulada: Ahora se calcula correctamente
            k_simulada = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
            
            # Cálculo de la curva de simulación
            T_intermedia = np.interp(t_intermedia, np.linspace(t0, t_peak, 300), calcular_curva_atleta(np.linspace(t0, t_peak, 300), t0, T0, t_pb, T_pb, t_peak, T_target, k_simulada, h))
            
            ax.scatter(t0, T0, color="#7F8C8D", edgecolor="black", s=35, linewidths=0.6, zorder=5)
            ax.text(t0 + 0.1, T0, f"Inicio Sim.\n{formatear_a_minutos(T0)}", va="bottom", ha="left", bbox=estilo_bbox, fontsize=8)
            ax.axvline(x=t0, color="#7F8C8D", linestyle=":", linewidth=0.7, alpha=0.5)
            
            ax.scatter(t_pb, T_pb, color="#F1C40F", marker="*", edgecolor="black", s=100, linewidths=0.6, zorder=5)
            ax.text(t_pb + 0.15, T_pb, f"PB Control\n{formatear_a_minutos(T_pb)}", va="center", ha="left", bbox=estilo_bbox, fontsize=8)
            ax.axvline(x=t_pb, color="red", linestyle="--", linewidth=0.7, alpha=0.4)
            
            ax.scatter(t_peak, T_target, color="#2ECC71", marker="s", edgecolor="black", s=35, linewidths=0.6, zorder=5)
            ax.text(t_peak - 0.1, T_target, f"Meta Sim.\n{formatear_a_minutos(T_target)}", va="bottom", ha="right", bbox=estilo_bbox, fontsize=8)
            ax.axvline(x=t_peak, color="#2ECC71", linestyle=":", linewidth=0.7, alpha=0.5)
            
            ax.scatter(t_intermedia, T_intermedia, color="purple", marker="X", edgecolor="black", s=60, zorder=6)
            ax.text(t_intermedia, T_intermedia + offset_y, f"Proyección: {t_intermedia}a\n{formatear_a_minutos(T_intermedia)}", va="bottom", ha="center", bbox=estilo_bbox, fontsize=8, color="purple")
            ax.axvline(x=t_intermedia, color="purple", linestyle=":", linewidth=0.7, alpha=0.4)
            
            st.info(f"⏱️ Tiempo proyectado a los **{t_intermedia} años**: {formatear_a_minutos(T_intermedia)}")

        # =====================================================================
        # 8. MARCAS DE REFERENCIA E HITOS (DATOS CACHÉ DE SUPABASE)
        # =====================================================================
        if not simulacion_externa:
            x_texto = lim_x_min + (lim_x_max - lim_x_min) * 0.02
            
            # (Corregido) Restauración de los colores distintivos de referencias
            colores_referencias = ["#A06000", "#006644", "#8e44ad", "#2980b9", "#d35400", "#7f8c8d"]
            
            if isinstance(referencias_raw, list):
                for idx_ref, ref in enumerate(referencias_raw):
                    val_str = ref.get("tiempo", 0)
                    try:
                        val = float(val_str)
                    except (ValueError, TypeError):
                        continue
                        
                    if val > 0 and lim_y_inferior <= val <= lim_y_superior:
                        nombre_marca = ref.get("nombre_marca", ref.get("nombre", "Marca Mínima"))
                        color_linea = colores_referencias[idx_ref % len(colores_referencias)]
                        ax.axhline(y=val, color=color_linea, linestyle=":", linewidth=0.8, alpha=0.8)
                        desplazamiento_y = (lim_y_superior - lim_y_inferior) * 0.008
                        ax.text(x_texto, val + desplazamiento_y, f"{nombre_marca}: {formatear_a_minutos(val)}", color=color_linea, fontsize=7.5, va="bottom", ha="left")

            if "Micro" in tipo_vista and isinstance(hitos_raw, list):
                for hito in hitos_raw:
                    edad_hito_str = hito.get("edad", 0)
                    try:
                        edad_hito = float(edad_hito_str)
                    except (ValueError, TypeError):
                        continue
                        
                    if lim_x_min <= edad_hito <= lim_x_max:
                        comp_data = hito.get("catalogo_competencias", {})
                        nombre_evento = comp_data.get("nombre_corto", "Competencia") if isinstance(comp_data, dict) else "Evento Programado"

                        ax.axvline(x=edad_hito, color="#2ECC71", linestyle="--", linewidth=0.8, alpha=0.6, zorder=5)
                        y_pos = lim_y_inferior + ((lim_y_superior - lim_y_inferior) * 0.03)
                        ax.text(
                            x=edad_hito + 0.02, y=y_pos, 
                            s=nombre_evento, 
                            color="#2ECC71", fontsize=8, weight="bold",
                            rotation=90, va="bottom", ha="left", alpha=0.85, zorder=6
                        )

        # =====================================================================
        # 9. TABLAS NATIVAS INFERIORES (SOLO INDIVIDUAL/REAL)
        # =====================================================================
        df_table_render = datos_sidebar.get("df_procesado")
        
        if not simulacion_externa and not modo_equipo and df_table_render is not None and not df_table_render.empty:
            if 'id' in df_table_render.columns:
                df_table_render = df_table_render.drop(columns=['id'])
                
            df_vista_tabla = df_table_render.copy()
            if 'Tiempo' in df_vista_tabla.columns:
                df_vista_tabla['Tiempo'] = df_vista_tabla['Tiempo'].apply(lambda x: formatear_a_minutos(x).replace(" s", "") if isinstance(x, (int, float)) else x)
            
            total_filas = len(df_vista_tabla)
            limite_filas_por_bloque = 18
            es_modo_micro = ("Micro" in tipo_vista)
            anchos_columnas = [0.25, 0.25, 0.25, 0.25] if es_modo_micro and len(df_vista_tabla.columns) == 4 else [0.15, 0.25, 0.60]
            
            def estilizar_tabla_nativo(instancia_tabla):
                instancia_tabla.auto_set_font_size(False)
                instancia_tabla.set_fontsize(8.5)
                instancia_tabla.scale(1.0, 1.3)
                for (row, col), cell in instancia_tabla.get_celld().items():
                    cell.set_linewidth(0.5)            
                    cell.set_edgecolor('#E5E7EB')       
                    if row == 0:
                        cell.set_text_props(color='black', weight='bold')
                        cell.set_facecolor('#C0C0C0')
                    else:
                        cell.set_facecolor('#F8F9F9' if row % 2 == 0 else 'white')

            if total_filas <= limite_filas_por_bloque:
                ax_table = fig.add_axes([0.14, 0.054, 0.72, 0.48])
                ax_table.axis('off')
                mpl_table = ax_table.table(cellText=df_vista_tabla.values, colLabels=df_vista_tabla.columns, cellLoc='center', loc='upper center', colWidths=anchos_columnas)
                estilizar_tabla_nativo(mpl_table)
            else:
                if total_filas > 36: df_vista_tabla = df_vista_tabla.iloc[:36]
                df_bloque_izq = df_vista_tabla.iloc[:limite_filas_por_bloque]
                df_bloque_der = df_vista_tabla.iloc[limite_filas_por_bloque:]
                
                ax_table1 = fig.add_axes([0.14, 0.054, 0.34, 0.48])
                ax_table1.axis('off')
                mpl_table1 = ax_table1.table(cellText=df_bloque_izq.values, colLabels=df_bloque_izq.columns, cellLoc='center', loc='upper center', colWidths=anchos_columnas)
                estilizar_tabla_nativo(mpl_table1)
                
                ax_table2 = fig.add_axes([0.52, 0.054, 0.34, 0.54])
                ax_table2.axis('off')
                mpl_table2 = ax_table2.table(cellText=df_bloque_der.values, colLabels=df_bloque_der.columns, cellLoc='center', loc='upper center', colWidths=anchos_columnas)
                estilizar_tabla_nativo(mpl_table2)

    # Configuración final
    ax.set_title(titulo_grafico, fontsize=12, pad=15)
    ax.set_xlabel("Edad (Años)", fontsize=10)
    ax.set_ylabel("Tiempo (mm:ss.00)", fontsize=10)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='upper right', fontsize=9)

    # 🚀 Renderizado final (Evita el Deprecation Warning)
    st.pyplot(fig, width='stretch')

    # -------------------------------------------------------------------------
    # ST.MARKDOWN - CENTRO DE EXPORTACIÓN (Restaurado e integrado al final)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🖨️ Centro de Exportación de Reportes y Gráficos")
    
    # Preparamos DataFrames según el modo de visualización
    export_df = pd.DataFrame()
    if modo_equipo and "df_global_marcas" in datos_sidebar and not datos_sidebar["df_global_marcas"].empty:
        export_df = datos_sidebar["df_global_marcas"].drop(columns=["id", "usuario_id"], errors="ignore")
    elif not modo_equipo and df_procesado is not None and not df_procesado.empty:
        export_df = df_procesado.drop(columns=["id", "usuario_id"], errors="ignore")
    
    if len(export_df) > 0:
        csv_data = export_df.to_csv(index=False).encode('utf-8')
        txt_string = export_df.to_string(index=False)
        
        # 1. Creamos el "escudo" inicializando la variable en None
        img_buffer = None
        
        if modo_equipo and not lista_atletas:
            st.warning("No se encontraron atletas activos con los criterios de segmentación elegidos.")
        else:
            # 2. Solo intentamos guardar si la figura realmente existe en esta ejecución
            if 'fig' in locals() and fig is not None:
                img_buffer = io.BytesIO()
                fig.savefig(img_buffer, format="png", bbox_inches=None, dpi=300)
                img_buffer.seek(0)
        
        c_exp1, c_exp2, c_exp3 = st.columns(3)
        with c_exp1:
            st.download_button(label="📥 Descargar Historial (CSV)", data=csv_data, file_name=f"marcas_{titulo_grafico}_{st.session_state.get('nadador_seleccionado_nombre', 'equipo')}.csv", mime="text/csv")
        with c_exp2:
            st.download_button(label="📄 Descargar Datos (TXT)", data=txt_string, file_name=f"reporte_{titulo_grafico}_{st.session_state.get('nadador_seleccionado_nombre', 'equipo')}.txt", mime="text/plain")
        with c_exp3:
            # 3. Protegemos el botón: si no hay buffer de imagen, no se rompe la app
            if img_buffer is not None:
                st.download_button(label="🖼️ Guardar Gráfico Completo", data=img_buffer, file_name=f"grafico_{titulo_grafico}_{st.session_state.get('nadador_seleccionado_nombre', 'equipo')}.png", mime="image/png")
            else:
                st.info("📉 Gráfico no disponible.")
    else:
        st.info("Sin datos para exportar en este momento.")

    # 🧹 LIMPIEZA DE MEMORIA (EVITA EL SEGMENTATION FAULT)
    plt.close(fig)
