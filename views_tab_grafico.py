import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# 📦 IMPORTACIONES LOCALES
from formulas_lib_funciones import (
    resolver_k_individual, 
    calcular_curva_atleta, 
    formatear_a_minutos, 
    calcular_edad_decimal
)

def renderizar_tab_grafico(datos_sidebar):
    # =====================================================================
    # 1. EXTRACCIÓN DE VARIABLES LOCALES (RÁPIDA, SIN CONSULTAS A BD)
    # =====================================================================
    modo_equipo = datos_sidebar.get("modo_equipo", False)
    simulacion_externa = datos_sidebar.get("simulacion_externa", False)
    
    # Textos
    nombre_atleta = datos_sidebar.get("nadador_seleccionado_nombre", datos_sidebar.get("nombre", "Atleta Seleccionado"))
    categoria = datos_sidebar.get("categoria", datos_sidebar.get("categoria_atleta", "Sin Categoría"))
    prueba = datos_sidebar.get("prueba", datos_sidebar.get("prueba_seleccionada", "Prueba no definida"))

    # Parámetros Matemáticos
    t_peak = float(datos_sidebar.get("t_peak", 23.0))
    T_target = float(datos_sidebar.get("T_target", 0.0))
    h = float(datos_sidebar.get("factor_h", 0.35))
    edad_intermedia = float(datos_sidebar.get("t_intermedia", 16.1)) # Viene directo del sidebar
    
    # Referencias (directo del sidebar para máxima velocidad)
    m_ano = float(datos_sidebar.get("m_ano", 0.0))
    m_panam_b = float(datos_sidebar.get("m_panam_b", 0.0))
    m_panam_a = float(datos_sidebar.get("m_panam_a", 0.0))
    m_wa_b = float(datos_sidebar.get("m_wa_b", 0.0))
    m_wa_a = float(datos_sidebar.get("m_wa_a", 0.0))
    wr = float(datos_sidebar.get("m_wr", 23.59))

    # =====================================================================
    # 2. GESTIÓN DE DATOS Y ENCABEZADOS (MÉTRICAS)
    # =====================================================================
    df_procesado = pd.DataFrame()
    t0 = T0 = t_pb = T_pb = 0.0

    if modo_equipo:
        lista_atletas = datos_sidebar.get("lista_atletas_filtrados", datos_sidebar.get("atletas_seleccionados", []))
        df_global = datos_sidebar.get("df_global_marcas", datos_sidebar.get("df_global", pd.DataFrame()))
        if df_global is None or df_global.empty or not lista_atletas:
            st.warning("No hay datos suficientes para dibujar el modo equipo.")
            return
    else:
        if simulacion_externa:
            t0 = float(datos_sidebar.get("t0", 10.0))
            T0 = float(datos_sidebar.get("T0", 0.0))
            t_pb = float(datos_sidebar.get("t_pb", 12.0))
            T_pb = float(datos_sidebar.get("T_pb", 0.0))
            if T0 == 0.0 or T_pb == 0.0: return
        else:
            df_procesado = datos_sidebar.get("df_procesado")
            if df_procesado is None or df_procesado.empty: return
            df_procesado = df_procesado.sort_values(by="Edad").reset_index(drop=True)
            t0 = float(df_procesado.iloc[0]["Edad"])
            T0 = float(df_procesado.iloc[0]["Tiempo"])
            idx_pb = df_procesado["Tiempo"].idxmin()
            t_pb = float(df_procesado.loc[idx_pb, "Edad"])
            T_pb = float(df_procesado.loc[idx_pb, "Tiempo"])

    # MÉTRICAS SUPERIORES (Idénticas a la Imagen 1)
    if not modo_equipo and T0 != 0.0 and T_pb != 0.0:
        k_principal = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
        D_principal = T_pb - T_target
        c3_val = np.interp(edad_intermedia, np.linspace(t0, t_peak, 300), calcular_curva_atleta(np.linspace(t0, t_peak, 300), t0, T0, t_pb, T_pb, t_peak, T_target, k_principal, h))
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(label="Factor de Ajuste Fisiológico (k)", value=f"{k_principal:.4f}")
        with c2:
            st.metric(label="Margen de Deriva de Seguridad...", value=f"{D_principal:.2f} s")
        with c3:
            st.metric(label=f"Proyección a los {edad_intermedia} años", value=f"{c3_val:.2f} s")

    # =====================================================================
    # 3. CONFIGURACIÓN DEL LIENZO MATPLOTLIB (EXACTO A IMAGEN 1)
    # =====================================================================
    fig = plt.figure(figsize=(8.5, 11.0))
    # Eje principal del gráfico (Ajustado para no aplastar la curva)
    ax = fig.add_axes([0.14, 0.52, 0.76, 0.35])
    
    formatter = FuncFormatter(lambda y, pos: f"{y:.2f} s")
    ax.yaxis.set_major_formatter(formatter)

    # Título nativo dentro del gráfico
    if not modo_equipo:
        ax.set_title(f"Curva de Rendimiento Asintótica - {prueba}\nAtleta: {nombre_atleta} | Categoría: {categoria}", fontsize=12, pad=15)

    if not modo_equipo or (modo_equipo and T0 != 0.0):
        k = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
        edades_curva = np.linspace(t0, t_peak, 300) 
        curva_ind = calcular_curva_atleta(edades_curva, t0, T0, t_pb, T_pb, t_peak, T_target, k, h)

    # =====================================================================
    # 4. DIBUJO DE CURVAS Y MARGENES
    # =====================================================================
    if modo_equipo:
        colores_equipo = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        for idx, atleta in enumerate(lista_atletas):
            atleta_id = atleta.get("id", atleta.get("usuario_id"))
            col_id = "usuario_id" if "usuario_id" in df_global.columns else "id"
            df_atleta = df_global[df_global[col_id] == atleta_id].copy()
            if df_atleta.empty: continue
            
            df_atleta = df_atleta.sort_values(by="Edad").reset_index(drop=True)
            t0_i = float(df_atleta.iloc[0]["Edad"])
            T0_i = float(df_atleta.iloc[0]["Tiempo"])
            idx_pb_i = df_atleta["Tiempo"].idxmin()
            t_pb_i = float(df_atleta.loc[idx_pb_i, "Edad"])
            T_pb_i = float(df_atleta.loc[idx_pb_i, "Tiempo"])
            
            color_actual = colores_equipo[idx % len(colores_equipo)]
            k_i = resolver_k_individual(t0_i, T0_i, t_pb_i, T_pb_i, t_peak, T_target)
            curva_i = calcular_curva_atleta(np.linspace(t0_i, t_peak, 300), t0_i, T0_i, t_pb_i, T_pb_i, t_peak, T_target, k_i, h)
            
            ax.plot(np.linspace(t0_i, t_peak, 300), curva_i, label=atleta.get("nombre", f"Atleta {idx+1}"), color=color_actual, linewidth=1.5)
            ax.plot(df_atleta["Edad"], df_atleta["Tiempo"], color=color_actual, linestyle="--", marker='o', markersize=4)
            ax.scatter(t_pb_i, T_pb_i, color=color_actual, marker="*", edgecolor="black", s=80, zorder=5)
    else:
        # Curva de Proyección (Teal) y Marcas Reales (Naranja Punteado)
        ax.plot(edades_curva, curva_ind, color='teal', label='Proyección Fisiológica', linewidth=1.8)
        if not simulacion_externa:
            ax.plot(df_procesado["Edad"], df_procesado["Tiempo"], color='#d35400', linestyle="--", marker='o', markersize=4, label="Evolución Real (PBs)")
            
        # Elementos invisibles solo para rellenar la Leyenda como en la Imagen 1
        ax.scatter([], [], color='#F1C40F', marker='*', edgecolor='black', s=100, label='PB Actual de Control')
        ax.scatter([], [], color='red', marker='o', s=35, label='Punto Consultado')
        ax.scatter([], [], color='#2ECC71', marker='s', edgecolor='black', s=35, label='Meta Peak')

    # Ajuste de Márgenes (X y Y) para respiración visual
    if not modo_equipo:
        margen_y = (T0 - T_target) * 0.15
        ax.set_xlim([t0 - 0.8, t_peak + 1.0])
        ax.set_ylim([T_target - margen_y, T0 + margen_y])
    
    lim_x_min, lim_x_max = ax.get_xlim()
    lim_y_inferior, lim_y_superior = ax.get_ylim()

    # =====================================================================
    # 5. DIBUJO DE PUNTOS CRÍTICOS (ETIQUETAS EXACTAS)
    # =====================================================================
    estilo_bbox = dict(boxstyle="round,pad=0.3", fc="white", ec="#BDC3C7", alpha=0.9, linewidth=0.5)

    if not modo_equipo:
        # Start
        ax.scatter(t0, T0, color="#7F8C8D", edgecolor="black", s=35, zorder=4)
        ax.text(t0 + 0.15, T0, f"P. Start\n{t0:.2f}a\n{T0:.2f} s", fontsize=8, va="bottom", ha="left", bbox=estilo_bbox)

        # PB Actual
        ax.scatter(t_pb, T_pb, color="#F1C40F", marker="*", edgecolor="black", s=120, zorder=5)
        ax.text(t_pb + 0.15, T_pb, f"PB Actual\n{t_pb:.2f}a\n{T_pb:.2f} s", fontsize=8, va="center", ha="left", bbox=estilo_bbox)

        # Meta Peak
        ax.scatter(t_peak, T_target, color="#2ECC71", marker="s", edgecolor="black", s=40, zorder=4)
        ax.text(t_peak, T_target + 0.5, f"Meta Peak\n{t_peak:.2f}a\n{T_target:.2f} s", fontsize=8, va="bottom", ha="center", bbox=estilo_bbox)
    
        # Punto Consultado (T_intermedia del Sidebar)
        k_sim = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
        T_dinamico = np.interp(edad_intermedia, np.linspace(t0, t_peak, 300), calcular_curva_atleta(np.linspace(t0, t_peak, 300), t0, T0, t_pb, T_pb, t_peak, T_target, k_sim, h))
        
        ax.scatter(edad_intermedia, T_dinamico, color="red", marker="o", edgecolor="black", s=40, zorder=6)
        ax.text(edad_intermedia, T_dinamico + 0.8, f"Consulta: {edad_intermedia}a\n{T_dinamico:.2f} s", va="bottom", ha="center", bbox=estilo_bbox, fontsize=8)

    # =====================================================================
    # 6. DIBUJO DE MARCAS MÍNIMAS (COLORES SOLICITADOS)
    # =====================================================================
    if not simulacion_externa:
        x_texto = lim_x_min + (lim_x_max - lim_x_min) * 0.02
        
        # Mapeo exacto de Nombres y Colores
        # Naranja, Verde, Cyan, Morado, Rojo, Azul
        referencias = [
            ("Mín. Año", m_ano, "#E67E22"),      # Naranja
            ("PANAM Jr B", m_panam_b, "#2ECC71"), # Verde
            ("PANAM Jr A", m_panam_a, "#00BCD4"), # Cyan
            ("WA B", m_wa_b, "#9B59B6"),          # Morado
            ("WA A", m_wa_a, "#E74C3C"),          # Rojo
            ("World Record", wr, "#3498DB")       # Azul
        ]
        
        for nombre_marca, valor_tiempo, color_linea in referencias:
            if valor_tiempo > 0 and lim_y_inferior <= valor_tiempo <= lim_y_superior:
                ax.axhline(y=valor_tiempo, color=color_linea, linestyle=":", linewidth=0.8, alpha=0.8)
                desplazamiento_y = (lim_y_superior - lim_y_inferior) * 0.008
                ax.text(x_texto, valor_tiempo + desplazamiento_y, f"{nombre_marca}: {valor_tiempo:.2f}", color=color_linea, fontsize=7.5, va="bottom", ha="left")

    # =====================================================================
    # 7. TABLA INFERIOR (EXACTA A IMAGEN 1)
    # =====================================================================
    df_table_render = datos_sidebar.get("df_procesado")
    
    if not simulacion_externa and not modo_equipo and df_table_render is not None and not df_table_render.empty:
        df_vista_tabla = df_table_render.drop(columns=['id', 'usuario_id'], errors='ignore').copy()
        if 'Tiempo' in df_vista_tabla.columns:
            df_vista_tabla['Tiempo'] = df_vista_tabla['Tiempo'].apply(lambda x: f"{x:.2f} s" if isinstance(x, (int, float)) else x)
        if 'Edad' in df_vista_tabla.columns:
            df_vista_tabla['Edad'] = df_vista_tabla['Edad'].apply(lambda x: f"{x:.2f} a" if isinstance(x, (int, float)) else x)
        
        ax_table = fig.add_axes([0.14, 0.02, 0.76, 0.40]) # Ubicada justo debajo
        ax_table.axis('off')
        
        anchos_cols = [0.15, 0.15, 0.15, 0.55] if len(df_vista_tabla.columns) == 4 else [1/len(df_vista_tabla.columns)] * len(df_vista_tabla.columns)
        
        t_obj = ax_table.table(cellText=df_vista_tabla.values, colLabels=df_vista_tabla.columns, cellLoc='center', loc='upper center', colWidths=anchos_cols)
        t_obj.auto_set_font_size(False)
        t_obj.set_fontsize(8.5)
        t_obj.scale(1.0, 1.4)
        
        for (r, c), cell in t_obj.get_celld().items():
            cell.set_linewidth(0.5)            
            cell.set_edgecolor('#E5E7EB')       
            if r == 0:
                cell.set_text_props(color='black', weight='bold')
                cell.set_facecolor('#C0C0C0')
            else:
                cell.set_facecolor('#F8F9F9' if r % 2 == 0 else 'white')

    ax.set_xlabel("Edad del Atleta (Años)", fontsize=10)
    ax.set_ylabel("Tiempo de Carrera (Segundos)", fontsize=10)
    ax.grid(True, linestyle=':', alpha=0.6)
    if not simulacion_externa:
        ax.legend(loc='upper right', fontsize=8, framealpha=0.9, edgecolor="#BDC3C7")

    st.pyplot(fig, width='stretch')

    # =====================================================================
    # 8. CENTRO DE EXPORTACIÓN
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
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format="png", bbox_inches=None, dpi=300)
        img_buffer.seek(0)
        
        c_exp1, c_exp2, c_exp3 = st.columns(3)
        with c_exp1:
            st.download_button("📥 Descargar Historial (CSV)", data=csv_data, file_name="marcas_export.csv", mime="text/csv")
        with c_exp3:
            st.download_button("🖼️ Guardar Gráfico Completo", data=img_buffer, file_name="grafico_export.png", mime="image/png")

    plt.close(fig)
