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
    # 1. EXTRACCIÓN DE VARIABLES Y CONTEXTO (CON FALLBACKS ROBUSTOS)
    # =====================================================================
    modo_equipo = datos_sidebar.get("modo_equipo", False)
    simulacion_externa = datos_sidebar.get("simulacion_externa", False)
    tipo_vista = datos_sidebar.get("tipo_vista", "Macro (Historial Completo)")
    
    # Datos de Atleta para encabezados
    nombre_atleta = datos_sidebar.get("nadador_seleccionado_nombre", datos_sidebar.get("nombre", "Atleta Seleccionado"))
    categoria = datos_sidebar.get("categoria", datos_sidebar.get("categoria_atleta", "Sin Categoría"))
    prueba = datos_sidebar.get("prueba", datos_sidebar.get("prueba_seleccionada", "Prueba no definida"))
    genero = datos_sidebar.get("genero", datos_sidebar.get("genero_atleta", "M"))
    usuario_id = datos_sidebar.get("usuario_id", datos_sidebar.get("id", ""))

    # Parámetros Matemáticos
    t_peak = float(datos_sidebar.get("t_peak", 23.0))
    T_target = float(datos_sidebar.get("T_target", 0.0))
    h = float(datos_sidebar.get("factor_h", 0.35))
    edad_intermedia_fija = float(datos_sidebar.get("t_intermedia", 18.0))

    # =====================================================================
    # 2. CONSULTAS A LA CACHÉ DE SUPABASE Y MARCAS MÍNIMAS
    # =====================================================================
    # Extraemos del sidebar o dejamos en 0.0
    m_ano = float(datos_sidebar.get("m_ano", 0.0))
    m_panam_b = float(datos_sidebar.get("m_panam_b", 0.0))
    m_panam_a = float(datos_sidebar.get("m_panam_a", 0.0))
    m_wa_b = float(datos_sidebar.get("m_wa_b", 0.0))
    m_wa_a = float(datos_sidebar.get("m_wa_a", 0.0))
    wr = float(datos_sidebar.get("m_wr", 25.0))

    referencias_raw = obtener_marcas_referencia_cache(prueba, genero, categoria)
    hitos_raw = obtener_historial_hitos_cache(usuario_id) if not simulacion_externa and not modo_equipo else []

    # Si Supabase trae datos, sobreescribimos respetando tu esquema de base de datos
    if referencias_raw and isinstance(referencias_raw, list) and len(referencias_raw) > 0:
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
    df_procesado = pd.DataFrame() 

    if modo_equipo:
        # Fallbacks múltiples por si el nombre de tu variable difiere
        lista_atletas = datos_sidebar.get("lista_atletas_filtrados", datos_sidebar.get("atletas_seleccionados", []))
        df_global = datos_sidebar.get("df_global_marcas", datos_sidebar.get("df_global", pd.DataFrame()))
        
        if df_global.empty or not lista_atletas:
            st.warning("⚠️ No hay atletas que cumplan con los filtros o la variable de datos globales está vacía.")
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
                st.info(f"No hay marcas históricas registradas para {nombre_atleta} en {prueba}.")
                return
            df_procesado = df_procesado.sort_values(by="Edad").reset_index(drop=True)
            t0 = float(df_procesado.iloc[0]["Edad"])
            T0 = float(df_procesado.iloc[0]["Tiempo"])
            idx_pb = df_procesado["Tiempo"].idxmin()
            t_pb = float(df_procesado.loc[idx_pb, "Edad"])
            T_pb = float(df_procesado.loc[idx_pb, "Tiempo"])

    # =====================================================================
    # 4. GESTIÓN DE ENCABEZADOS E INTERFAZ (METRICAS RESTAURADAS)
    # =====================================================================
    if simulacion_externa:
        st.warning("⚠️ Modo Simulación Activo: Proyecciones basadas estrictamente en los parámetros ingresados.")
        st.subheader("Modo Simulación Externa (Proyección Aislada)")
    elif modo_equipo:
        st.subheader(f"👥 Modo Equipo | {prueba}")
    else:
        # Encabezado corregido con Nombre y Categoría
        st.subheader(f"👤 {nombre_atleta} | {categoria} | {prueba}")
        st.caption(f"Vista: {tipo_vista}")

    # CÁLCULO DE LAS MÉTRICAS SUPERIORES
    if not modo_equipo and T0 != 0.0 and T_pb != 0.0:
        k_principal = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
        D_principal = T_pb - T_target
        c3_val = np.interp(edad_intermedia_fija, np.linspace(t0, t_peak, 300), calcular_curva_atleta(np.linspace(t0, t_peak, 300), t0, T0, t_pb, T_pb, t_peak, T_target, k_principal, h))
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(label="Factor de Ajuste (k)", value=f"{k_principal:.4f}")
        with c2:
            st.metric(label="Margen de Deriva (D)", value=f"{formatear_a_minutos(D_principal)}")
        with c3:
            st.metric(label=f"Proyección a {edad_intermedia_fija} años", value=formatear_a_minutos(c3_val))

    # =====================================================================
    # 5. CONFIGURACIÓN DEL LIENZO MATPLOTLIB
    # =====================================================================
    fig = plt.figure(figsize=(8.5, 11.0))
    ax = fig.add_axes([0.14, 0.58, 0.72, 0.33])
    formatter = FuncFormatter(lambda y, pos: formatear_a_minutos(y))
    ax.yaxis.set_major_formatter(formatter)

    if not modo_equipo or (modo_equipo and T0 != 0.0):
        k = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
        edades_curva = np.linspace(t0, t_peak, 300) 
        curva_ind = calcular_curva_atleta(edades_curva, t0, T0, t_pb, T_pb, t_peak, T_target, k, h)

    # =====================================================================
    # 6. DIBUJO DE CURVAS POR ESCENARIO
    # =====================================================================
    colores_equipo = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

    if modo_equipo:
        for idx, atleta in enumerate(lista_atletas):
            atleta_id = atleta.get("id", atleta.get("usuario_id"))
            atleta_nombre = atleta.get("nombre", f"Atleta {idx+1}")
            
            # Filtro robusto por si la columna se llama id o usuario_id
            col_id = "usuario_id" if "usuario_id" in df_global.columns else "id"
            df_atleta = df_global[df_global[col_id] == atleta_id].copy()
            
            if df_atleta.empty: continue
            
            # Transformación de columnas al vuelo (Seguro contra variaciones de nombre)
            if "edad" not in df_atleta.columns and "fecha_competencia" in df_atleta.columns:
                fecha_nac = atleta.get("fecha_nacimiento")
                df_atleta["edad"] = df_atleta["fecha_competencia"].apply(lambda x: calcular_edad_decimal(fecha_nac, x))
            
            if "tiempo" not in df_atleta.columns and "tiempo_segundos" in df_atleta.columns:
                df_atleta["tiempo"] = df_atleta["tiempo_segundos"]

            # Dropeamos nulos para evitar colapsos
            df_atleta = df_atleta.dropna(subset=["edad", "tiempo"]).sort_values(by="edad").reset_index(drop=True)
            if df_atleta.empty: continue

            t0_i = float(df_atleta.iloc[0]["edad"])
            T0_i = float(df_atleta.iloc[0]["tiempo"])
            idx_pb_i = df_atleta["tiempo"].idxmin()
            t_pb_i = float(df_atleta.loc[idx_pb_i, "edad"])
            T_pb_i = float(df_atleta.loc[idx_pb_i, "tiempo"])
            
            if T0_i == 0.0 or T_pb_i == 0.0: continue
            
            color_actual = colores_equipo[idx % len(colores_equipo)]
            k_i = resolver_k_individual(t0_i, T0_i, t_pb_i, T_pb_i, t_peak, T_target)
            edades_curva_i = np.linspace(t0_i, t_peak, 300)
            curva_i = calcular_curva_atleta(edades_curva_i, t0_i, T0_i, t_pb_i, T_pb_i, t_peak, T_target, k_i, h)
            
            ax.plot(edades_curva_i, curva_i, label=f"{atleta_nombre}", color=color_actual, alpha=0.5, linewidth=1.2, linestyle='-')
            ax.plot(df_atleta["edad"], df_atleta["tiempo"], color=color_actual, linestyle="--", linewidth=1.0, alpha=0.8)
            ax.scatter(df_atleta["edad"], df_atleta["tiempo"], color=color_actual, s=15, zorder=3)
            ax.scatter(t_pb_i, T_pb_i, color=color_actual, marker="*", edgecolor="black", s=80, zorder=5)

    else:
        ax.plot(edades_curva, curva_ind, color='blue', label='Proyección', linewidth=1.5)
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
    # 7. DIBUJO DE PUNTOS CRÍTICOS Y SLIDER DE SIMULACIÓN CORREGIDO
    # =====================================================================
    offset_y = (lim_y_superior - lim_y_inferior) * 0.025
    estilo_bbox = dict(boxstyle="round,pad=0.25", fc="#F8F9F9", ec="#BDC3C7", alpha=0.9, linewidth=0.5)

    if not simulacion_externa and not modo_equipo:
        if lim_x_min <= t0 <= lim_x_max and lim_y_inferior <= T0 <= lim_y_superior:
            ax.scatter(t0, T0, color="#7F8C8D", edgecolor="black", s=35, zorder=4)
            ax.text(t0 + 0.1, T0, f"Start\n{t0:.2f}a", fontsize=8, va="bottom", ha="left", bbox=estilo_bbox)

        if lim_x_min <= t_pb <= lim_x_max and lim_y_inferior <= T_pb <= lim_y_superior:
            ax.scatter(t_pb, T_pb, color="#F1C40F", marker="*", edgecolor="black", s=100, zorder=5)
            ax.text(t_pb + 0.15, T_pb, f"PB\n{formatear_a_minutos(T_pb)}", fontsize=8, va="center", ha="left", bbox=estilo_bbox)

        if lim_x_min <= t_peak <= lim_x_max and lim_y_inferior <= T_target <= lim_y_superior:
            ax.scatter(t_peak, T_target, color="#2ECC71", marker="s", edgecolor="black", s=35, zorder=4)
            ax.text(t_peak - 0.1, T_target, f"Meta\n{formatear_a_minutos(T_target)}", fontsize=8, va="bottom", ha="right", bbox=estilo_bbox)
    
    elif simulacion_externa:
        st.markdown("### 🔍 Mover Edad de Consulta (Simulador)")
        # Este slider ahora sí fuerza la actualización local de la curva dinámica
        t_slider = st.slider("Edad proyectada:", min_value=float(t0), max_value=float(t_peak), value=float(t_pb), step=0.25)
        
        k_simulada = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
        T_dinamico = np.interp(t_slider, np.linspace(t0, t_peak, 300), calcular_curva_atleta(np.linspace(t0, t_peak, 300), t0, T0, t_pb, T_pb, t_peak, T_target, k_simulada, h))
        
        ax.scatter(t0, T0, color="#7F8C8D", s=35, zorder=5)
        ax.scatter(t_pb, T_pb, color="#F1C40F", marker="*", edgecolor="black", s=100, zorder=5)
        ax.scatter(t_peak, T_target, color="#2ECC71", marker="s", s=35, zorder=5)
        
        # Marcador dinámico que obedece al slider
        ax.scatter(t_slider, T_dinamico, color="purple", marker="X", edgecolor="black", s=60, zorder=6)
        ax.text(t_slider, T_dinamico + offset_y, f"{t_slider}a\n{formatear_a_minutos(T_dinamico)}", va="bottom", ha="center", bbox=estilo_bbox, fontsize=8, color="purple")
        st.success(f"⏱️ Tiempo calculado a los {t_slider} años: **{formatear_a_minutos(T_dinamico)}**")

    # =====================================================================
    # 8. DIBUJO DE MARCAS MÍNIMAS (REESCRITO PARA COINCIDIR CON TU DB)
    # =====================================================================
    if not simulacion_externa:
        x_texto = lim_x_min + (lim_x_max - lim_x_min) * 0.02
        
        # Mapeo directo de las columnas extraídas arriba
        diccionario_marcas = {
            "WR": wr,
            "WA A": m_wa_a,
            "WA B": m_wa_b,
            "PANAM A": m_panam_a,
            "PANAM B": m_panam_b,
            "Mínimo Año": m_ano
        }
        
        colores_referencias = ["#7f8c8d", "#d35400", "#2980b9", "#8e44ad", "#006644", "#A06000"]
        idx_color = 0
        
        for nombre_marca, valor_tiempo in diccionario_marcas.items():
            if valor_tiempo > 0 and lim_y_inferior <= valor_tiempo <= lim_y_superior:
                color_linea = colores_referencias[idx_color % len(colores_referencias)]
                ax.axhline(y=valor_tiempo, color=color_linea, linestyle=":", linewidth=0.8, alpha=0.8)
                desplazamiento_y = (lim_y_superior - lim_y_inferior) * 0.008
                ax.text(x_texto, valor_tiempo + desplazamiento_y, f"{nombre_marca}: {formatear_a_minutos(valor_tiempo)}", color=color_linea, fontsize=7.5, va="bottom", ha="left")
                idx_color += 1

        # =====================================================================
        # 9. DIBUJO DE HITOS EN MODO MICRO (COMPATIBILIDAD FORZADA)
        # =====================================================================
        if "Micro" in tipo_vista:
            # Soporte por si hitos_raw es lista pura o diccionario { "hitos": [...] }
            lista_hitos = hitos_raw.get("hitos", []) if isinstance(hitos_raw, dict) else (hitos_raw if isinstance(hitos_raw, list) else [])
            
            for hito in lista_hitos:
                edad_hito_str = hito.get("edad", hito.get("edad_tecnica", 0))
                try:
                    edad_hito = float(edad_hito_str)
                except (ValueError, TypeError):
                    continue
                    
                if lim_x_min <= edad_hito <= lim_x_max:
                    comp_data = hito.get("catalogo_competencias", {})
                    nombre_evento = comp_data.get("nombre_corto", hito.get("nombre", "Evento")) if isinstance(comp_data, dict) else "Competencia"

                    ax.axvline(x=edad_hito, color="#2ECC71", linestyle="--", linewidth=0.8, alpha=0.6, zorder=5)
                    y_pos = lim_y_inferior + ((lim_y_superior - lim_y_inferior) * 0.03)
                    ax.text(x=edad_hito + 0.02, y=y_pos, s=nombre_evento, color="#2ECC71", fontsize=8, weight="bold", rotation=90, va="bottom", ha="left")

    # =====================================================================
    # 10. TABLAS NATIVAS INFERIORES (SOLO INDIVIDUAL/REAL)
    # =====================================================================
    df_table_render = datos_sidebar.get("df_procesado")
    
    if not simulacion_externa and not modo_equipo and df_table_render is not None and not df_table_render.empty:
        df_vista_tabla = df_table_render.drop(columns=['id', 'usuario_id'], errors='ignore').copy()
        if 'Tiempo' in df_vista_tabla.columns:
            df_vista_tabla['Tiempo'] = df_vista_tabla['Tiempo'].apply(lambda x: formatear_a_minutos(x).replace(" s", "") if isinstance(x, (int, float)) else x)
        
        total_filas = len(df_vista_tabla)
        limite_filas = 18
        anchos_cols = [0.25]*len(df_vista_tabla.columns) if "Micro" in tipo_vista else [0.15, 0.25, 0.60]
        
        def estilizar_tabla(tabla_obj):
            tabla_obj.auto_set_font_size(False)
            tabla_obj.set_fontsize(8.5)
            tabla_obj.scale(1.0, 1.3)
            for (r, c), cell in tabla_obj.get_celld().items():
                cell.set_linewidth(0.5)            
                cell.set_edgecolor('#E5E7EB')       
                if r == 0:
                    cell.set_text_props(color='black', weight='bold')
                    cell.set_facecolor('#C0C0C0')
                else:
                    cell.set_facecolor('#F8F9F9' if r % 2 == 0 else 'white')

        if total_filas <= limite_filas:
            ax_table = fig.add_axes([0.14, 0.054, 0.72, 0.48])
            ax_table.axis('off')
            t_obj = ax_table.table(cellText=df_vista_tabla.values, colLabels=df_vista_tabla.columns, cellLoc='center', loc='upper center', colWidths=anchos_cols)
            estilizar_tabla(t_obj)
        else:
            if total_filas > 36: df_vista_tabla = df_vista_tabla.iloc[:36]
            ax_t1 = fig.add_axes([0.14, 0.054, 0.34, 0.48])
            ax_t1.axis('off')
            t1_obj = ax_t1.table(cellText=df_vista_tabla.iloc[:limite_filas].values, colLabels=df_vista_tabla.columns, cellLoc='center', loc='upper center', colWidths=anchos_cols)
            estilizar_tabla(t1_obj)
            
            ax_t2 = fig.add_axes([0.52, 0.054, 0.34, 0.54])
            ax_t2.axis('off')
            t2_obj = ax_t2.table(cellText=df_vista_tabla.iloc[limite_filas:].values, colLabels=df_vista_tabla.columns, cellLoc='center', loc='upper center', colWidths=anchos_cols)
            estilizar_tabla(t2_obj)

    ax.set_xlabel("Edad (Años)", fontsize=10)
    ax.set_ylabel("Tiempo (mm:ss.00)", fontsize=10)
    ax.grid(True, linestyle=':', alpha=0.6)
    if not simulacion_externa: ax.legend(loc='upper right', fontsize=9)

    st.pyplot(fig, width='stretch')

    # =====================================================================
    # 11. CENTRO DE EXPORTACIÓN (INTACTO)
    # =====================================================================
    st.markdown("---")
    st.markdown("### 🖨️ Centro de Exportación de Reportes y Gráficos")
    
    export_df = pd.DataFrame()
    if modo_equipo and "df_global_marcas" in datos_sidebar and not datos_sidebar["df_global_marcas"].empty:
        export_df = datos_sidebar["df_global_marcas"].drop(columns=["id", "usuario_id"], errors="ignore")
    elif not modo_equipo and df_procesado is not None and not df_procesado.empty:
        export_df = df_procesado.drop(columns=["id", "usuario_id"], errors="ignore")
    
    if len(export_df) > 0:
        csv_data = export_df.to_csv(index=False).encode('utf-8')
        txt_string = export_df.to_string(index=False)
        img_buffer = None
        
        if 'fig' in locals() and fig is not None:
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format="png", bbox_inches=None, dpi=300)
            img_buffer.seek(0)
        
        c_exp1, c_exp2, c_exp3 = st.columns(3)
        with c_exp1:
            st.download_button(label="📥 Descargar Historial (CSV)", data=csv_data, file_name=f"marcas_export.csv", mime="text/csv")
        with c_exp2:
            st.download_button(label="📄 Descargar Datos (TXT)", data=txt_string, file_name=f"reporte_export.txt", mime="text/plain")
        with c_exp3:
            if img_buffer is not None:
                st.download_button(label="🖼️ Guardar Gráfico Completo", data=img_buffer, file_name=f"grafico_export.png", mime="image/png")
    else:
        st.info("Sin datos para exportar en este momento.")

    plt.close(fig)
