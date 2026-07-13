import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from formulas_lib_funciones import resolver_k_individual, calcular_curva_atleta, formatear_a_minutos
from conections_supabase_cache import (
    obtener_marcas_referencia_cache, 
    obtener_historial_hitos_cache
)

def renderizar_tab_grafico(datos_sidebar):
    """
    Renderiza el gráfico de rendimiento combinando proyecciones exponenciales,
    datos históricos reales, referencias e hitos desde Supabase.
    """
    if not datos_sidebar:
        st.warning("No se recibieron datos del panel lateral.")
        return

    # =====================================================================
    # 1. EXTRACCIÓN Y SANITIZACIÓN DE PARÁMETROS GENERALES
    # =====================================================================
    modo_equipo = bool(datos_sidebar.get("modo_equipo", False))
    simulacion_externa = bool(datos_sidebar.get("simulacion_externa", False))
    tipo_vista = str(datos_sidebar.get("tipo_vista", "Macro (Historial Completo)"))
    titulo_grafico = str(datos_sidebar.get("titulo_grafico", "Proyección de Rendimiento"))
    
    usuario_id = datos_sidebar.get("usuario_id")
    genero = datos_sidebar.get("genero", "M")
    categoria = datos_sidebar.get("categoria", "")
    prueba = titulo_grafico

    # Parámetros numéricos con fallback
    t_peak = float(datos_sidebar.get("t_peak", 23.0))
    T_target = float(datos_sidebar.get("T_target", 0.0))
    h = float(datos_sidebar.get("factor_h", 0.35))
    edad_intermedia = float(datos_sidebar.get("t_intermedia", 18.0))

    # Inicialización Global Segura (Evita NameError / UnboundLocalError)
    t0 = float(datos_sidebar.get("t0", 10.0))
    T0 = float(datos_sidebar.get("T0", 0.0))
    t_pb = float(datos_sidebar.get("t_pb", 12.0))
    T_pb = float(datos_sidebar.get("T_pb", 0.0))

    # Marcas de Referencia iniciales
    m_ano = float(datos_sidebar.get("m_ano", 0.0))
    m_panam_b = float(datos_sidebar.get("m_panam_b", 0.0))
    m_panam_a = float(datos_sidebar.get("m_panam_a", 0.0))
    m_wa_b = float(datos_sidebar.get("m_wa_b", 0.0))
    m_wa_a = float(datos_sidebar.get("m_wa_a", 0.0))
    wr = float(datos_sidebar.get("m_wr", 0.0))

    # =====================================================================
    # 2. CONSULTAS A SUPABASE (REFERENCIAS E HITOS)
    # =====================================================================
    referencias_raw = []
    hitos_raw = []

    if not simulacion_externa and not modo_equipo:
        if prueba and genero:
            referencias_raw = obtener_marcas_referencia_cache(prueba, genero, categoria)
            if referencias_raw and isinstance(referencias_raw, list) and len(referencias_raw) > 0:
                ref_data = referencias_raw[0]
                m_ano = float(ref_data.get("m_ano", m_ano))
                m_panam_b = float(ref_data.get("m_panam_b", m_panam_b))
                m_panam_a = float(ref_data.get("m_panam_a", m_panam_a))
                m_wa_b = float(ref_data.get("m_wa_b", m_wa_b))
                m_wa_a = float(ref_data.get("m_wa_a", m_wa_a))
                wr = float(ref_data.get("m_wr", wr))

        if usuario_id:
            hitos_raw = obtener_historial_hitos_cache(usuario_id)

    # =====================================================================
    # 3. TITULARES Y MODO DE EJECUCIÓN
    # =====================================================================
    if simulacion_externa:
        st.warning("⚠️ Modo Simulación Activo: Proyecciones basadas estrictamente en los parámetros ingresados.")
        st.subheader("Modo Simulación Externa (Proyección Aislada)")
    elif modo_equipo:
        st.subheader(f"Modo Equipo: {titulo_grafico}")
    else:
        st.subheader(f"Modo Individual - Vista {tipo_vista}: {titulo_grafico}")

    # =====================================================================
    # 4. PREPARACIÓN DE DATOS
    # =====================================================================
    df_procesado = None
    lista_atletas = []
    df_global = pd.DataFrame()

    if modo_equipo:
        lista_atletas = datos_sidebar.get("lista_atletas_filtrados", [])
        df_global = datos_sidebar.get("df_global_marcas", pd.DataFrame())
        if df_global is None or df_global.empty:
            st.info("No hay marcas de atletas que cumplan con los filtros seleccionados.")
            return
            
    elif simulacion_externa:
        if T0 <= 0.0 or T_pb <= 0.0:
            st.info("Ingrese valores válidos de tiempo en el simulador (T0 y T_pb mayor a 0).")
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
    # 5. CONFIGURACIÓN MATPLOTLIB Y CÁLCULO DE CURVA
    # =====================================================================
    fig = plt.figure(figsize=(8.5, 11.0))
    ax = fig.add_axes([0.14, 0.58, 0.72, 0.33])
    
    formatter = FuncFormatter(lambda y, pos: formatear_a_minutos(y))
    ax.yaxis.set_major_formatter(formatter)

    curva_ind = None
    edades_curva = None
    c3 = 0.0

    if not modo_equipo and T0 > 0.0 and T_pb > 0.0:
        k = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
        edades_curva = np.linspace(t0, t_peak + 3, 300) 
        curva_ind = calcular_curva_atleta(edades_curva, t0, T0, t_pb, T_pb, t_peak, T_target, k, h)
        c3 = float(np.interp(edad_intermedia, edades_curva, curva_ind))

    # =====================================================================
    # 6. DIBUJO DE GRÁFICO (EQUIPO VS INDIVIDUAL / SIMULACIÓN)
    # =====================================================================
    if modo_equipo:
        for atleta in lista_atletas:
            atleta_id = atleta.get("id")
            atleta_nombre = atleta.get("nombre", "Atleta")
            
            df_atleta = df_global[df_global["usuario_id"] == atleta_id] if "usuario_id" in df_global.columns else pd.DataFrame()
            if df_atleta.empty: 
                continue
                
            col_edad = "edad" if "edad" in df_atleta.columns else "Edad"
            col_tiempo = "tiempo" if "tiempo" in df_atleta.columns else "Tiempo"

            df_atleta = df_atleta.sort_values(by=col_edad).reset_index(drop=True)
            t0_i = float(df_atleta.iloc[0][col_edad])
            T0_i = float(df_atleta.iloc[0][col_tiempo])
            idx_pb_i = df_atleta[col_tiempo].idxmin()
            t_pb_i = float(df_atleta.loc[idx_pb_i, col_edad])
            T_pb_i = float(df_atleta.loc[idx_pb_i, col_tiempo])
            
            if T0_i <= 0.0 or T_pb_i <= 0.0: 
                continue
                
            k_i = resolver_k_individual(t0_i, T0_i, t_pb_i, T_pb_i, t_peak, T_target)
            edades_curva_i = np.linspace(t0_i, t_peak + 3, 300)
            curva_i = calcular_curva_atleta(edades_curva_i, t0_i, T0_i, t_pb_i, T_pb_i, t_peak, T_target, k_i, h)
            
            ax.plot(edades_curva_i, curva_i, label=atleta_nombre, alpha=0.7, linewidth=1.2)
            ax.scatter(df_atleta[col_edad], df_atleta[col_tiempo], s=15, alpha=0.6)
            
        lim_x_min, lim_x_max = ax.get_xlim()
        lim_y_inferior, lim_y_superior = ax.get_ylim()

    else:
        if curva_ind is not None:
            ax.plot(edades_curva, curva_ind, color='blue', label='Proyección Fisiológica', linewidth=1.5)
        
        if "Micro" in tipo_vista and not simulacion_externa:
            ax.set_xlim([datos_sidebar.get("edad_min_zoom", t0), datos_sidebar.get("edad_max_zoom", t_peak)])
        else:
            ax.set_xlim([t0 - 0.5, t_peak + 1.0])

        lim_x_min, lim_x_max = ax.get_xlim()
        lim_y_inferior, lim_y_superior = ax.get_ylim()

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

        else:
            st.markdown("### 🔍 Consultar Proyección en Edad Específica")
            val_slider_def = float(min(max(t_pb, t0), t_peak))
            t_intermedia_sim = st.slider("Edad a consultar:", 
                                     min_value=float(t0), 
                                     max_value=float(t_peak), 
                                     value=val_slider_def, 
                                     step=0.25)
            
            k_sim = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
            curva_sim = calcular_curva_atleta(np.array([t_intermedia_sim]), t0, T0, t_pb, T_pb, t_peak, T_target, k_sim, h)
            T_intermedia = float(curva_sim[0])

            ax.scatter(t0, T0, color="#7F8C8D", edgecolor="black", s=35, linewidths=0.6, zorder=5)
            ax.text(t0 + 0.1, T0, f"Inicio Sim.\n{formatear_a_minutos(T0)}", va="bottom", ha="left", bbox=estilo_bbox, fontsize=8)
            ax.axvline(x=t0, color="#7F8C8D", linestyle=":", linewidth=0.7, alpha=0.5)
            
            ax.scatter(t_pb, T_pb, color="#F1C40F", marker="*", edgecolor="black", s=100, linewidths=0.6, zorder=5)
            ax.text(t_pb + 0.15, T_pb, f"PB Control\n{formatear_a_minutos(T_pb)}", va="center", ha="left", bbox=estilo_bbox, fontsize=8)
            ax.axvline(x=t_pb, color="red", linestyle="--", linewidth=0.7, alpha=0.4)
            
            ax.scatter(t_peak, T_target, color="#2ECC71", marker="s", edgecolor="black", s=35, linewidths=0.6, zorder=5)
            ax.text(t_peak - 0.1, T_target, f"Meta Sim.\n{formatear_a_minutos(T_target)}", va="bottom", ha="right", bbox=estilo_bbox, fontsize=8)
            ax.axvline(x=t_peak, color="#2ECC71", linestyle=":", linewidth=0.7, alpha=0.5)
            
            ax.scatter(t_intermedia_sim, T_intermedia, color="purple", marker="X", edgecolor="black", s=60, zorder=6)
            ax.text(t_intermedia_sim, T_intermedia + offset_y, f"Proyección: {t_intermedia_sim}a\n{formatear_a_minutos(T_intermedia)}", va="bottom", ha="center", bbox=estilo_bbox, fontsize=8, color="purple")
            ax.axvline(x=t_intermedia_sim, color="purple", linestyle=":", linewidth=0.7, alpha=0.4)
            
            st.info(f"⏱️ Tiempo proyectado a los **{t_intermedia_sim} años**: {formatear_a_minutos(T_intermedia)}")

    # =====================================================================
    # 7. MARCAS DE REFERENCIA E HITOS (LÍNEAS DERECHA Y VERTICALES)
    # =====================================================================
    if not simulacion_externa:
        x_texto = lim_x_min + (lim_x_max - lim_x_min) * 0.02
        
        # --- Líneas Horizontales de Referencia ---
        dict_marcas_ref = {
            "M. Año": m_ano,
            "Panam B": m_panam_b,
            "Panam A": m_panam_a,
            "WA B": m_wa_b,
            "WA A": m_wa_a,
            "R. Mundial": wr
        }
        
        for nombre_marca, val in dict_marcas_ref.items():
            if val > 0 and lim_y_inferior <= val <= lim_y_superior:
                ax.axhline(y=val, color="gray", linestyle=":", linewidth=0.7, alpha=0.7)
                desplazamiento_y = (lim_y_superior - lim_y_inferior) * 0.008
                ax.text(x_texto, val + desplazamiento_y, f"{nombre_marca}: {formatear_a_minutos(val)}", color="#555555", fontsize=7.5, va="bottom", ha="left")

        # --- Líneas Verticales de Hitos (Vista Micro) ---
        if "Micro" in tipo_vista and hitos_raw and isinstance(hitos_raw, list):
            for hito in hitos_raw:
                edad_hito_val = hito.get("edad") or hito.get("edad_hito") or hito.get("edad_atleta")
                if edad_hito_val is None:
                    continue
                try:
                    edad_hito = float(edad_hito_val)
                except (ValueError, TypeError):
                    continue
                    
                if lim_x_min <= edad_hito <= lim_x_max:
                    comp_data = hito.get("catalogo_competencias", {})
                    if isinstance(comp_data, dict):
                        nombre_evento = comp_data.get("nombre_corto") or comp_data.get("nombre") or "Competencia"
                    else:
                        nombre_evento = str(hito.get("evento", hito.get("nombre", "Evento")))

                    ax.axvline(x=edad_hito, color="#2ECC71", linestyle="--", linewidth=0.8, alpha=0.8, zorder=5)
                    y_pos = lim_y_inferior + ((lim_y_superior - lim_y_inferior) * 0.03)
                    ax.text(
                        x=edad_hito + 0.02, y=y_pos, 
                        s=nombre_evento, 
                        color="#2ECC71", fontsize=8, weight="bold",
                        rotation=90, va="bottom", ha="left", alpha=0.85, zorder=6
                    )

    # =====================================================================
    # 8. TABLA INFERIOR DE TIEMPOS
    # =====================================================================
    df_table_render = datos_sidebar.get("df_procesado")
    
    if not simulacion_externa and not modo_equipo and df_table_render is not None and not df_table_render.empty:
        df_vista_tabla = df_table_render.copy()
        if 'id' in df_vista_tabla.columns:
            df_vista_tabla = df_vista_tabla.drop(columns=['id'])
            
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
            if total_filas > 36: 
                df_vista_tabla = df_vista_tabla.iloc[:36]
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

    # =====================================================================
    # 9. FINALIZACIÓN Y RENDER
    # =====================================================================
    ax.set_title(titulo_grafico, fontsize=12, pad=15)
    ax.set_xlabel("Edad (Años)", fontsize=10)
    ax.set_ylabel("Tiempo (mm:ss.00)", fontsize=10)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='upper right', fontsize=9)

    st.pyplot(fig, width='stretch')
    plt.close(fig)
