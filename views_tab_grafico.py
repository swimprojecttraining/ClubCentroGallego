import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# 📦 IMPORTACIONES DE FUNCIONES LOCALES
from formulas_lib_funciones import resolver_k_individual, calcular_curva_atleta, formatear_a_minutos
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
    
    # Parámetros dinámicos de proyección
    t_peak = float(datos_sidebar.get("t_peak", 23.0))
    T_target = float(datos_sidebar.get("T_target", 0.0))
    h = float(datos_sidebar.get("factor_h", 0.35))
    edad_intermedia = float(datos_sidebar.get("t_intermedia", 18.0))

    # Variables de contexto para Supabase (con mapeo seguro)
    prueba = datos_sidebar.get("prueba", datos_sidebar.get("prueba_seleccionada", ""))
    genero = datos_sidebar.get("genero", datos_sidebar.get("genero_atleta", "M"))
    categoria = datos_sidebar.get("categoria", datos_sidebar.get("categoria_atleta", ""))
    usuario_id = datos_sidebar.get("usuario_id", datos_sidebar.get("id", ""))
# NUEVO: Desempaquetar las variables que faltaban
    m_ano = datos_sidebar.get("m_ano", 0.0)
    m_panam_b = datos_sidebar.get("m_panam_b", 0.0)
    m_panam_a = datos_sidebar.get("m_panam_a", 0.0)
    m_wa_b = datos_sidebar.get("m_wa_b", 0.0)
    m_wa_a = datos_sidebar.get("m_wa_a", 0.0)
    wr = datos_sidebar.get("m_wr", 25.0)
    # =====================================================================
    # 2. CONSULTAS A LA CACHÉ DE SUPABASE (INDEPENDIENTES DEL SIDEBAR)
    # =====================================================================
    # CORRECCIÓN: Se cambió "no" por "not"
    if not simulacion_externa and not modo_equipo:
    # 1. Llama a la función solo con los 3 argumentos que acepta
        referencias_raw = obtener_marcas_referencia_cache(prueba, genero, categoria)
        hitos_raw = obtener_historial_hitos_cache(usuario_id, competencia_id, elegible)
    # 2. Si la consulta devolvió datos, extrae los valores de la lista
    if referencias_raw:
        ref_data = referencias_raw[0] # Tomamos la primera coincidencia
        m_ano = float(ref_data.get("m_ano", 0.0))
        m_panam_b = float(ref_data.get("m_panam_b", 0.0))
        m_panam_a = float(ref_data.get("m_panam_a", 0.0))
        m_wa_b = float(ref_data.get("m_wa_b", 0.0))
        m_wa_a = float(ref_data.get("m_wa_a", 0.0))
        wr = float(ref_data.get("m_wr", 25.0))
    else:
        # Valores por defecto si no se encuentran referencias
        m_ano, m_panam_b, m_panam_a, m_wa_b, m_wa_a, wr = 0.0, 0.0, 0.0, 0.0, 0.0, 25.0
    
    else:
        referencias_raw = []
        hitos_raw = []

    # =====================================================================
    # 3. GESTIÓN DE ENCABEZADOS E INTERFAZ
    # =====================================================================
    if simulacion_externa:
        st.warning("⚠️ Modo Simulación Activo: Proyecciones basadas estrictamente en los parámetros ingresados.")
        st.subheader("Modo Simulación Externa (Proyección Aislada)")
    elif modo_equipo:
        st.subheader(f"Modo Equipo: {titulo_grafico}")
    else:
        st.subheader(f"Modo Individual - Vista {tipo_vista}: {titulo_grafico}")

    # =====================================================================
    # 4. RECOPILACIÓN ORGANIZADA DE DATOS SEGÚN ESCENARIO
    # =====================================================================
    if modo_equipo:
        lista_atletas = datos_sidebar.get("lista_atletas_filtrados", [])
        df_global = datos_sidebar.get("df_global_marcas", pd.DataFrame())
        st.write("Contenido de df_global:", df_global) 
        if df_global.empty:
            st.warning("El DataFrame está vacío. Verifica si la consulta a la BD trajo resultados.")
        if not lista_atletas or df_global.empty:
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
    # 5. CONFIGURACIÓN DEL LIENZO MATPLOTLIB
    # =====================================================================
    fig = plt.figure(figsize=(8.5, 11.0))
    ax = fig.add_axes([0.14, 0.58, 0.72, 0.33])
    
    formatter = FuncFormatter(lambda y, pos: formatear_a_minutos(y))
    ax.yaxis.set_major_formatter(formatter)

    # Cálculos de curva (Atleta Principal / Simulación)
    if not modo_equipo or (modo_equipo and T0 != 0.0):
        k = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
        edades_curva = np.linspace(t0, t_peak + 3, 300) 
        curva_ind = calcular_curva_atleta(edades_curva, t0, T0, t_pb, T_pb, t_peak, T_target, k, h)
        c3 = np.interp(edad_intermedia, edades_curva, curva_ind)

    # =====================================================================
    # 6. DIBUJO DE CURVAS POR ESCENARIO
    # =====================================================================
    if modo_equipo:
        for atleta in lista_atletas:
            atleta_id = atleta.get("id")
            atleta_nombre = atleta.get("nombre")
            df_atleta = df_global[df_global["usuario_id"] == atleta_id]
            if df_atleta.empty: continue
                
            t0_i = float(df_atleta.iloc[0]["edad"])
            T0_i = float(df_atleta.iloc[0]["tiempo"])
            idx_pb_i = df_atleta["tiempo"].idxmin()
            t_pb_i = float(df_atleta.loc[idx_pb_i, "edad"])
            T_pb_i = float(df_atleta.loc[idx_pb_i, "tiempo"])
            
            if T0_i == 0.0 or T_pb_i == 0.0: continue
                
            k_i = resolver_k_individual(t0_i, T0_i, t_pb_i, T_pb_i, t_peak, T_target)
            edades_curva_i = np.linspace(t0_i, t_peak + 3, 300)
            curva_i = calcular_curva_atleta(edades_curva_i, t0_i, T0_i, t_pb_i, T_pb_i, t_peak, T_target, k_i, h)
            ax.plot(edades_curva_i, curva_i, label=atleta_nombre, alpha=0.6, linewidth=1.2)
            
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

        # Extraer límites actuales para cálculos de posiciones
        lim_x_min, lim_x_max = ax.get_xlim()
        lim_y_inferior, lim_y_superior = ax.get_ylim()

# =====================================================================
        # 7. DIBUJO DE PUNTOS CRÍTICOS Y ETIQUETAS
        # =====================================================================
        
        # Definimos el estilo de las etiquetas una sola vez para que aplique a ambos modos
        offset_y = (lim_y_superior - lim_y_inferior) * 0.025
        estilo_bbox = dict(boxstyle="round,pad=0.25", fc="#F8F9F9", ec="#BDC3C7", alpha=0.9, linewidth=0.5)

        if not simulacion_externa:
            if df_procesado is not None and not df_procesado.empty:
                ax.plot(df_procesado["Edad"], df_procesado["Tiempo"], color="#D55E00", linestyle="--", linewidth=1.0, alpha=0.6, label="Evolución Real")
                ax.scatter(df_procesado["Edad"], df_procesado["Tiempo"], color="#D55E00", edgecolor="black", s=25, linewidths=0.6, zorder=3)

            # Puntos de Control: Start, PB, Consulta e Hito Peak
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
        
        elif simulacion_externa:  # <-- CORRECCIÓN: Agregado el guion bajo
            
            # --- WIDGETS DE STREAMLIT (Entradas del usuario) ---
            st.markdown("### 🔍 Consultar Proyección en Edad Específica")
            t_intermedia = st.slider("Edad a consultar:", 
                                     min_value=float(t0), 
                                     max_value=float(t_peak), 
                                     value=float(t_pb), 
                                     step=0.25)
            
            # Cálculo de la curva de simulación usando la constante k calculada previamente
            # NOTA: Asegúrate de que la variable "k_simulada" exista en tu código más arriba
            T_intermedia = T0 * np.exp(-k_simulada * (t_intermedia - t0)) 
            
            # --- DIBUJO DE PUNTOS EN MODO SIMULACIÓN ---
            # 1. Punto T0 (Inicio)
            ax.scatter(t0, T0, color="#7F8C8D", edgecolor="black", s=35, linewidths=0.6, zorder=5)
            ax.text(t0 + 0.1, T0, f"Inicio Sim.\n{formatear_a_minutos(T0)}", va="bottom", ha="left", bbox=estilo_bbox, fontsize=8)
            ax.axvline(x=t0, color="#7F8C8D", linestyle=":", linewidth=0.7, alpha=0.5)
            
            # 2. Punto T_pb (Personal Best de Control)
            ax.scatter(t_pb, T_pb, color="#F1C40F", marker="*", edgecolor="black", s=100, linewidths=0.6, zorder=5)
            ax.text(t_pb + 0.15, T_pb, f"PB Control\n{formatear_a_minutos(T_pb)}", va="center", ha="left", bbox=estilo_bbox, fontsize=8)
            ax.axvline(x=t_pb, color="red", linestyle="--", linewidth=0.7, alpha=0.4)
            
            # 3. Punto T_target (Meta en el Peak)
            ax.scatter(t_peak, T_target, color="#2ECC71", marker="s", edgecolor="black", s=35, linewidths=0.6, zorder=5)
            ax.text(t_peak - 0.1, T_target, f"Meta Sim.\n{formatear_a_minutos(T_target)}", va="bottom", ha="right", bbox=estilo_bbox, fontsize=8)
            ax.axvline(x=t_peak, color="#2ECC71", linestyle=":", linewidth=0.7, alpha=0.5)
            
            # 4. Punto de Consulta (T_intermedia)
            ax.scatter(t_intermedia, T_intermedia, color="purple", marker="X", edgecolor="black", s=60, zorder=6)
            ax.text(t_intermedia, T_intermedia + offset_y, f"Proyección: {t_intermedia}a\n{formatear_a_minutos(T_intermedia)}", va="bottom", ha="center", bbox=estilo_bbox, fontsize=8, color="purple")
            ax.axvline(x=t_intermedia, color="purple", linestyle=":", linewidth=0.7, alpha=0.4)
            
            st.info(f"⏱️ Tiempo proyectado a los **{t_intermedia} años**: {formatear_a_minutos(T_intermedia)}")

        # =====================================================================
        # 8. MARCAS DE REFERENCIA E HITOS (DATOS CACHÉ DE SUPABASE)
        # =====================================================================
        if not simulacion_externa:
            x_texto = lim_x_min + (lim_x_max - lim_x_min) * 0.02
            
            # --- Líneas Horizontales (Marcas Mínimas Supabase) ---
            if isinstance(referencias_raw, list):
                for ref in referencias_raw:
                    val_str = ref.get("tiempo", 0)
                    try:
                        val = float(val_str)
                    except (ValueError, TypeError):
                        continue
                        
                    if val > 0 and lim_y_inferior <= val <= lim_y_superior:
                        nombre_marca = ref.get("nombre_marca", ref.get("nombre", "Marca Mínima"))
                        ax.axhline(y=val, color="gray", linestyle=":", linewidth=0.6, alpha=0.7)
                        desplazamiento_y = (lim_y_superior - lim_y_inferior) * 0.008
                        ax.text(x_texto, val + desplazamiento_y, f"{nombre_marca}: {formatear_a_minutos(val)}", color="gray", fontsize=7.5, va="bottom", ha="left")

            # --- Líneas Verticales (Hitos y Competencias) SOLO MICRO ---
            if "Micro" in tipo_vista and isinstance(hitos_raw, list):
                for hito in hitos_raw:
                    edad_hito_str = hito.get("edad", 0)
                    try:
                        edad_hito = float(edad_hito_str)
                    except (ValueError, TypeError):
                        continue
                        
                    if lim_x_min <= edad_hito <= lim_x_max:
                        # Extraer el nombre de la competencia desde el cruce de tablas
                        comp_data = hito.get("catalogo_competencias", {})
                        if isinstance(comp_data, dict):
                            nombre_evento = comp_data.get("nombre_corto", "Competencia")
                        else:
                            nombre_evento = "Evento Programado"

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

    # 🧹 LIMPIEZA DE MEMORIA (EVITA EL SEGMENTATION FAULT)
    plt.close(fig)
