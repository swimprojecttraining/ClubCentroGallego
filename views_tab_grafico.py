import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# 📦 IMPORTACIONES ACTIVADAS
from formulas_lib_funciones import resolver_k_individual, calcular_curva_atleta, formatear_a_minutos

def renderizar_tab_grafico(datos_sidebar):
    """
    Fase 1: Inicialización y recopilación de datos para la vista del gráfico.
    """
    # =====================================================================
    # 1. EXTRACCIÓN DE VARIABLES COMUNES DE CONTROL Y OBJETIVO
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

    # =====================================================================
    # 2. GESTIÓN DE ENCABEZADOS Y AVISOS DE INTERFAZ
    # =====================================================================
    if simulacion_externa:
        st.warning("⚠️ Modo Simulación Activo: Las pestañas de datos históricos han sido ocultadas. Mostrando proyecciones basadas estrictamente en los parámetros ingresados.")
        st.subheader("Modo Simulación Externa (Proyección Aislada)")
    elif modo_equipo:
        st.subheader(f"Modo Equipo: {titulo_grafico}")
    else:
        st.subheader(f"Modo Individual - Vista {tipo_vista}: {titulo_grafico}")

    # =====================================================================
    # 3. RECOPILACIÓN ORGANIZADA DE DATOS SEGÚN ESCENARIO
    # =====================================================================
    
    # --- ESCENARIO A: MODO EQUIPO ---
    if modo_equipo:
        lista_atletas = datos_sidebar.get("lista_atletas_filtrados", [])
        df_global = datos_sidebar.get("df_global_marcas", pd.DataFrame())
        
        if not lista_atletas or df_global.empty:
            st.info("No hay atletas que cumplan con los filtros seleccionados para proyectar el equipo.")
            return
            
    # --- ESCENARIO B: MODO INDIVIDUAL O SIMULACIÓN ---
    else:
        if simulacion_externa:
            # MODO SIMULACIÓN
            t0 = float(datos_sidebar.get("t0", 10.0))
            T0 = float(datos_sidebar.get("T0", 0.0))
            t_pb = float(datos_sidebar.get("t_pb", 12.0))
            T_pb = float(datos_sidebar.get("T_pb", 0.0))
            
            if T0 == 0.0 or T_pb == 0.0:
                st.info("Por favor, ingrese valores válidos en el simulador del panel lateral (T0 y T_pb).")
                return
        else:
            # MODO INDIVIDUAL REAL (Extracción de la base de datos)
            df_procesado = datos_sidebar.get("df_procesado")
            
            if df_procesado is None or df_procesado.empty:
                st.info("No hay marcas históricas registradas para este nadador en la prueba seleccionada.")
                return
                
            # Ordenar cronológicamente por edad para garantizar que t0 sea el primer registro real
            df_procesado = df_procesado.sort_values(by="Edad").reset_index(drop=True)
            
            t0 = float(df_procesado.iloc[0]["Edad"])
            T0 = float(df_procesado.iloc[0]["Tiempo"])
            
            idx_pb = df_procesado["Tiempo"].idxmin()
            t_pb = float(df_procesado.loc[idx_pb, "Edad"])
            T_pb = float(df_procesado.loc[idx_pb, "Tiempo"])
            
            if tipo_vista == "Micro (Ventana Anual)":
                edad_min_zoom = datos_sidebar.get("edad_min_zoom", t0)
                edad_max_zoom = datos_sidebar.get("edad_max_zoom", t_peak)

    # =====================================================================
    # 4. CONFIGURACIÓN INICIAL DEL LIENZO MATPLOTLIB
    # =====================================================================
    fig = plt.figure(figsize=(8.5, 11.0))
    ax = fig.add_axes([0.14, 0.58, 0.72, 0.33])
    
    formatter = FuncFormatter(lambda y, pos: formatear_a_minutos(y))
    ax.yaxis.set_major_formatter(formatter)

    # Cálculos Comunes (Atleta Principal / Simulación)
    if not modo_equipo or (modo_equipo and T0 != 0.0):
        # Usamos las funciones matemáticas importadas de la librería
        k = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
        c1 = k
        c2 = T_pb - T_target
        
        edades_curva = np.linspace(t0, t_peak + 3, 300) # Extendido un poco post-peak para ver deriva
        curva_ind = calcular_curva_atleta(edades_curva, t0, T0, t_pb, T_pb, t_peak, T_target, k, h)
        
        c3 = np.interp(edad_intermedia, edades_curva, curva_ind)

    # =====================================================================
    # 5. BIFURCACIÓN DE DIBUJO POR ESCENARIO
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
    else:
        # Dibujo de la proyección base
        ax.plot(edades_curva, curva_ind, color='blue', label='Proyección Fisiológica', linewidth=1.5)
        
        if simulacion_externa:
            ax.set_xlim([t0 - 0.5, t_peak + 1.0])
        else:
            # Usando mayúsculas correctas según lo que procesa formulas_lib_funciones
            ax.plot(df_procesado["Edad"], df_procesado["Tiempo"], 'ro-', label="Marcas Reales", markersize=4)
            
            if tipo_vista == "Micro (Ventana Anual)":
                ax.set_xlim([edad_min_zoom, edad_max_zoom])
            else:
                ax.set_xlim([t0 - 0.5, t_peak + 1.0])

        # =====================================================================
        # 6. DIBUJO DE PUNTOS CRÍTICOS Y ETIQUETAS
        # =====================================================================
        if not simulacion_externa:
            lim_x_min, lim_x_max = ax.get_xlim()
            lim_y_inferior, lim_y_superior = ax.get_ylim()
            
            offset_y = (lim_y_superior - lim_y_inferior) * 0.025
            estilo_bbox = dict(boxstyle="round,pad=0.25", fc="#F8F9F9", ec="#BDC3C7", alpha=0.9, linewidth=0.5)

            if df_procesado is not None and not df_procesado.empty:
                ax.plot(df_procesado["Edad"], df_procesado["Tiempo"], color="#D55E00", linestyle="--", linewidth=1.0, alpha=0.6, label="Evolución Real (PBs)")
                ax.scatter(df_procesado["Edad"], df_procesado["Tiempo"], color="#D55E00", edgecolor="black", s=25, linewidths=0.6, zorder=3)

            # Puntos de Control: Start, PB, Consulta e Hito Peak
            if lim_x_min <= t0 <= lim_x_max and lim_y_inferior <= T0 <= lim_y_superior:
                ax.scatter(t0, T0, color="#7F8C8D", edgecolor="black", s=35, linewidths=0.6, zorder=4)
                ax.text(t0 + 0.1, T0, f"P. Start\n{t0:.2f}a\n{formatear_a_minutos(T0)}", fontsize=8, va="bottom", ha="left", bbox=estilo_bbox)
                ax.axvline(x=t0, color="#7F8C8D", linestyle=":", linewidth=0.7, alpha=0.5)

            if lim_x_min <= t_pb <= lim_x_max and lim_y_inferior <= T_pb <= lim_y_superior:
                ax.scatter(t_pb, T_pb, color="#F1C40F", marker="*", edgecolor="black", s=100, linewidths=0.6, zorder=5, label="PB Actual de Control")
                ax.text(t_pb + 0.15, T_pb, f"PB Actual\n{t_pb:.2f}a\n{formatear_a_minutos(T_pb)}", fontsize=8, va="center", ha="left", bbox=estilo_bbox)
                ax.axvline(x=t_pb, color="red", linestyle="--", linewidth=0.7, alpha=0.4)

            if lim_x_min <= edad_intermedia <= lim_x_max and lim_y_inferior <= c3 <= lim_y_superior:
                ax.scatter(edad_intermedia, c3, color="red", marker="o", s=30, zorder=5, label="Punto Consultado")
                ax.text(edad_intermedia, c3 + offset_y, f"Consulta: {edad_intermedia:.1f}a\n{formatear_a_minutos(c3)}", fontsize=8, va="bottom", ha="center", bbox=estilo_bbox)
                ax.axvline(x=edad_intermedia, color="red", linestyle=":", linewidth=0.7, alpha=0.4)

            if lim_x_min <= t_peak <= lim_x_max and lim_y_inferior <= T_target <= lim_y_superior:
                ax.scatter(t_peak, T_target, color="#2ECC71", marker="s", edgecolor="black", s=35, linewidths=0.6, zorder=4, label="Meta Peak")
                ax.text(t_peak - 0.1, T_target, f"Meta Peak\n{t_peak:.2f}a\n{formatear_a_minutos(T_target)}", fontsize=8, va="bottom", ha="right", bbox=estilo_bbox)
                ax.axvline(x=t_peak, color="#2ECC71", linestyle=":", linewidth=0.7, alpha=0.5)

        # =====================================================================
        # 7. TABLAS NATIVAS INFERIORES DE MATPLOTLIB
        # =====================================================================
        df_table_render = datos_sidebar.get("df_procesado") # Se renderiza la tabla histórica procesada
        
        if not simulacion_externa and df_table_render is not None and not df_table_render.empty:
            
            # Preparamos la tabla para que se vea bonita (evitamos mostrar el ID si está)
            if 'id' in df_table_render.columns:
                df_table_render = df_table_render.drop(columns=['id'])
                
            # Formateamos la columna 'Tiempo' para la tabla
            df_vista_tabla = df_table_render.copy()
            df_vista_tabla['Tiempo'] = df_vista_tabla['Tiempo'].apply(lambda x: formatear_a_minutos(x).replace(" s", ""))
            
            total_filas = len(df_vista_tabla)
            limite_filas_por_bloque = 18
            
            anchos_columnas = [0.15, 0.25, 0.60] # Edad, Tiempo, Evento
            
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
                mpl_table = ax_table.table(
                    cellText=df_vista_tabla.values, 
                    colLabels=df_vista_tabla.columns, 
                    cellLoc='center', loc='upper center', 
                    colWidths=anchos_columnas
                )
                estilizar_tabla_nativo(mpl_table)
            else:
                if total_filas > 36: df_vista_tabla = df_vista_tabla.iloc[:36]
                df_bloque_izq = df_vista_tabla.iloc[:limite_filas_por_bloque]
                df_bloque_der = df_vista_tabla.iloc[limite_filas_por_bloque:]
                
                anchos_doble = [0.15, 0.25, 0.60]
                
                ax_table1 = fig.add_axes([0.14, 0.054, 0.34, 0.48])
                ax_table1.axis('off')
                mpl_table1 = ax_table1.table(cellText=df_bloque_izq.values, colLabels=df_bloque_izq.columns, cellLoc='center', loc='upper center', colWidths=anchos_doble)
                estilizar_tabla_nativo(mpl_table1)
                
                ax_table2 = fig.add_axes([0.52, 0.054, 0.34, 0.54])
                ax_table2.axis('off')
                mpl_table2 = ax_table2.table(cellText=df_bloque_der.values, colLabels=df_bloque_der.columns, cellLoc='center', loc='upper center', colWidths=anchos_doble)
                estilizar_tabla_nativo(mpl_table2)

        # Configuración final de títulos y leyendas
        ax.set_title(titulo_grafico, fontsize=12, pad=15)
        ax.set_xlabel("Edad (Años)", fontsize=10)
        ax.set_ylabel("Tiempo (mm:ss.00)", fontsize=10)
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend(loc='upper right', fontsize=9)

        # 🚀 Renderizado final en Streamlit
        st.pyplot(fig, use_container_width=True)
