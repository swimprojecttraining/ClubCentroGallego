import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- IMPORTACIONES DEL ECOSISTEMA MODULAR ---
# Asumiendo que los archivos están en el mismo directorio raíz según las instrucciones
from formulas_lib_funciones_2 import (
    resolver_k_individual,
    calcular_curva_atleta,
    formatear_a_minutos,
    procesar_mejor_marca_historica,
    calcular_puntos_wa
)
from connections_supabase_cache_2 import (
    obtener_historial_hitos_cache
)

def renderizar_tab_grafico(payload: dict):
    """
    Motor principal de renderizado para la pestaña de gráficos.
    Procesa el payload emitido por views_sidebar.py y genera las proyecciones.
    """
    # ---------------------------------------------------------
    # 1. DESEMPAQUETADO DEL PAYLOAD (SIDEBAR)
    # ---------------------------------------------------------
    usuario_id = payload.get("usuario_id")
    genero = payload.get("genero", "M")
    categoria = payload.get("categoria", "")
    prueba = payload.get("titulo_grafico", "")
    simulacion_externa = payload.get("simulacion_externa", False)
    modo_equipo = payload.get("modo_equipo", False)
    
    # Parámetros Matemáticos y Limites
    t0 = float(payload.get("t0", 10.0))
    T0 = float(payload.get("T0", 100.0))
    t_peak = float(payload.get("t_peak", 23.0))
    T_target = float(payload.get("T_target", 50.0))
    t_pb = float(payload.get("t_pb", 12.0))
    T_pb = float(payload.get("T_pb", 80.0))
    factor_h = float(payload.get("factor_h", 0.35))
    t_intermedia = float(payload.get("t_intermedia", 16.40))
    
    # Control de Vista
    tipo_vista = payload.get("tipo_vista", "Macro (Historial Completo)")
    edad_min_zoom = payload.get("edad_min_zoom", 0)
    edad_max_zoom = payload.get("edad_max_zoom", 100)
    
    # Datos y Referencias
    df_procesado = payload.get("df_procesado", pd.DataFrame())
    df_global_marcas = payload.get("df_global_marcas", pd.DataFrame())
    lista_atletas_filtrados = payload.get("lista_atletas_filtrados", [])
    
    m_ano = payload.get("m_ano", 0.0)
    m_panam_b = payload.get("m_panam_b", 0.0)
    m_panam_a = payload.get("m_panam_a", 0.0)
    m_wa_b = payload.get("m_wa_b", 0.0)
    m_wa_a = payload.get("m_wa_a", 0.0)
    m_wr = payload.get("m_wr", 25.0)

    # ---------------------------------------------------------
    # 1.1 LÓGICA DE FUENTE DE DATOS (BIFURCACIÓN)
    # ---------------------------------------------------------
    if simulacion_externa:
        # MODO SIMULACIÓN: Usamos estrictamente los inputs del Sidebar
        eff_t0 = float(payload.get("t0", 10.0))
        eff_T0 = float(payload.get("T0", 100.0))
        
        # El resto de parámetros de simulación vienen del payload
        k_global = resolver_k_individual(eff_t0, eff_T0, t_pb, T_pb, t_peak, T_target)
        
        # En simulación, el historial suele estar vacío o no debe usarse para el trazado
        df_plot = pd.DataFrame() 
    else:
        # MODO NORMAL: Extraemos valores reales de la BD vía la función histórica
        res_historico = procesar_mejor_marca_historica(df_procesado)
        if res_historico:
            eff_t0, eff_T0, _, _ = res_historico
        else:
            eff_t0, eff_T0 = t0, T0 # Fallback
            
        k_global = resolver_k_individual(eff_t0, eff_T0, t_pb, T_pb, t_peak, T_target)
        df_plot = df_procesado
    # ---------------------------------------------------------
    # 2. ENCABEZADOS Y ALERTAS
    # ---------------------------------------------------------
    if simulacion_externa:
        st.markdown(f"## 🎢 Simulación de Escenarios: {prueba}")
        st.markdown(f"**Género:** {genero} | **Categoría de Competencia Activa:** `{categoria}`")
        st.info("⚠️ **Modo Simulación Externa Activo.** El módulo de gestión y control de marcas se encuentra oculto para evitar alteraciones accidentales en la base de datos real.")
    elif modo_equipo:
        st.markdown(f"## 👥 Planificación y control de resultados de competencia: Comparativo")
        st.markdown(f"**Género:** {payload.get('filtro_genero', 'Todos')} | **Categoría de Competencia Activa:** `{categoria if payload.get('tipo_filtro') == 'Categoría Etaria' else 'Múltiple'}`")
    else:
        nombre_atleta = st.session_state.get("nadador_seleccionado_nombre", "Atleta")
        st.markdown(f"## 📈 Curva de Rendimiento Asintótica - {prueba}")
        st.markdown(f"**Género:** {genero} | **Categoría de Competencia Activa:** `{categoria}`")

    st.markdown("---")

    # ---------------------------------------------------------
    # 3. CÁLCULO DE MÉTRICAS GLOBALES (PANEL SUPERIOR)
    # ---------------------------------------------------------
    # Para el panel superior, usamos los valores del sidebar (el principal)
    try:
        k_global = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
        margen_d = round(T_pb - T_target, 2)
        arr_t_int = np.array([t_intermedia])
        T_intermedia = calcular_curva_atleta(arr_t_int, t0, T0, t_pb, T_pb, t_peak, T_target, k_global, factor_h)[0]
    except Exception:
        k_global, margen_d, T_intermedia = 0.0, 0.0, 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Factor de Ajuste Fisiológico (k)", f"{k_global:.4f}")
    col2.metric("Margen de Deriva de Seguridad (D)", f"{margen_d:.2f} s")
    col3.metric(f"Proyección a los {t_intermedia:.1f} años", f"{T_intermedia:.2f} s")

    st.write("") # Espaciador

    # ---------------------------------------------------------
    # 4. CONFIGURACIÓN BASE DEL GRÁFICO PLOTLY
    # ---------------------------------------------------------
    fig = go.Figure()

    # Añadir Líneas de Referencia Horizontales (Piso del Gráfico)
    referencias = [
        ("Mín. Año", m_ano, "orange"),
        ("PANAM Jr B", m_panam_b, "teal"),
        ("PANAM Jr A", m_panam_a, "blue"),
        ("WA B", m_wa_b, "brown"),
        ("WA A", m_wa_a, "red"),
        ("World Record", m_wr, "black")
    ]
    
    for nombre_ref, valor_ref, color in referencias:
        if valor_ref and valor_ref > 0:
            fig.add_hline(
                y=valor_ref, 
                line_dash="dot", 
                line_width=1, 
                line_color=color,
                annotation_text=f"{nombre_ref}: {formatear_a_minutos(valor_ref)}",
                annotation_position="bottom left",
                annotation_font=dict(size=10, color=color)
            )

    # ---------------------------------------------------------
    # 5. RENDERIZADO: MODO EQUIPO
    # ---------------------------------------------------------
    if modo_equipo:
        titulo_figura = f"Análisis Comparativo de Equipo - {prueba}"
        
        if df_global_marcas.empty or not lista_atletas_filtrados:
            st.warning("No hay marcas registradas para los atletas y filtros seleccionados en esta prueba.")
        else:
            colores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
            
            for idx, atleta in enumerate(lista_atletas_filtrados):
                atleta_id = atleta["id"]
                nombre_atleta = atleta["nombre"]
                color_atleta = colores[idx % len(colores)]
                
                df_atleta = df_global_marcas[df_global_marcas["usuario_id"] == atleta_id].copy()
                if df_atleta.empty:
                    continue
                    
                df_atleta = df_atleta.sort_values(by="edad").reset_index(drop=True)
                
                # Obtener variables históricas reales del atleta
                a_t0, a_T0, a_t_pb, a_T_pb = procesar_mejor_marca_historica(
                    df_atleta.rename(columns={"edad": "Edad", "tiempo": "Tiempo"})
                )
                
                if a_t0 is None:
                    continue
                
                # Proyección Fisiológica Estimada (Línea Gris Punteada)
                a_k = resolver_k_individual(a_t0, a_T0, a_t_pb, a_T_pb, t_peak, T_target)
                edades_proy = np.linspace(a_t0, t_peak, 100)
                tiempos_proy = calcular_curva_atleta(edades_proy, a_t0, a_T0, a_t_pb, a_T_pb, t_peak, T_target, a_k, factor_h)
                
                # Trazo de Proyección (Solo se muestra en leyenda una vez)
                fig.add_trace(go.Scatter(
                    x=edades_proy, y=tiempos_proy, mode='lines',
                    line=dict(color='gray', dash='dot', width=1.5),
                    name="Proyección fisiológica estimada",
                    showlegend=(idx == 0), hoverinfo='skip'
                ))
                
                # Evolución Real (Línea Continua + Puntos)
                fig.add_trace(go.Scatter(
                    x=df_atleta["edad"], y=df_atleta["tiempo"], mode='lines+markers',
                    name=f"Evolución real - {nombre_atleta}",
                    line=dict(color=color_atleta, width=2),
                    marker=dict(size=6, symbol='circle'),
                    text=[formatear_a_minutos(t) for t in df_atleta["tiempo"]],
                    hovertemplate="<b>%{text}</b><br>Edad: %{x:.2f}a<extra></extra>"
                ))
                
                # Marcador Final (Estrella)
                fig.add_trace(go.Scatter(
                    x=[df_atleta["edad"].iloc[-1]], y=[df_atleta["tiempo"].iloc[-1]], mode='markers',
                    marker=dict(size=10, symbol='star', color=color_atleta, line=dict(width=1, color='black')),
                    showlegend=False, hoverinfo='skip'
                ))
                
        df_export = df_global_marcas # Para la tabla de exportación

    # ---------------------------------------------------------
    # 6. RENDERIZADO: MODO INDIVIDUAL / SIMULACIÓN
    # ---------------------------------------------------------
    else:
        titulo_figura = f"Curva de Rendimiento Asintótica - {prueba}<br>Atleta: {st.session_state.get('nadador_seleccionado_nombre', 'N/A')} | Categoría: {categoria}"
        df_export = df_procesado.copy()
        
        # Generar Curva Continua Matemática Principal
        edades_proy = np.linspace(t0, t_peak, 150)
        tiempos_proy = calcular_curva_atleta(edades_proy, t0, T0, t_pb, T_pb, t_peak, T_target, k_global, factor_h)
        
        fig.add_trace(go.Scatter(
            x=edades_proy, y=tiempos_proy, mode='lines',
            line=dict(color='#008080', width=3), # Teal
            name="Proyección Fisiológica",
            text=[formatear_a_minutos(t) for t in tiempos_proy],
            hovertemplate="Edad: %{x:.2f}a<br>Proyección: <b>%{text}</b><extra></extra>"
        ))
        
        # Historial Real (PBs)
        if not df_procesado.empty:
            fig.add_trace(go.Scatter(
                x=df_procesado["Edad"], y=df_procesado["Tiempo"], mode='lines+markers',
                line=dict(color='#e67e22', width=1.5, dash='dash'), # Naranja punteado
                marker=dict(size=6, color='#e67e22'),
                name="Evolución Real (PBs)",
                text=[formatear_a_minutos(t) for t in df_procesado["Tiempo"]],
                hovertemplate="Edad: %{x:.2f}a<br>Marca: <b>%{text}</b><extra></extra>"
            ))
            
        # Puntos Claves: Start, PB Actual, Punto Consultado, Meta Peak
        puntos_x = [t0, t_pb, t_intermedia, t_peak]
        puntos_y = [T0, T_pb, T_intermedia, T_target]
        textos = ["P. Start", "PB Actual", f"Consulta: {t_intermedia:.2f}a", "Meta Peak"]
        colores_pt = ['gray', 'gold', 'red', 'mediumseagreen']
        simbolos = ['circle', 'star', 'circle', 'square']
        nombres_leyenda = ['P. Start', 'PB Actual de Control', 'Punto Consultado', 'Meta Peak']
        
        for px, py, txt, c, sym, leg_name in zip(puntos_x, puntos_y, textos, colores_pt, simbolos, nombres_leyenda):
            # Solo mostrar Start en leyenda si se desea, por simplicidad replicamos estilo de imagen
            mostrar_leyenda = True if leg_name in ['PB Actual de Control', 'Punto Consultado', 'Meta Peak'] else False
            
            fig.add_trace(go.Scatter(
                x=[px], y=[py], mode='markers+text',
                marker=dict(size=12 if sym == 'star' else 8, symbol=sym, color=c, line=dict(width=1, color='black')),
                name=leg_name,
                text=[f"{txt}<br>{formatear_a_minutos(py)}"],
                textposition="top center" if txt != "PB Actual" else "bottom center",
                showlegend=mostrar_leyenda,
                hoverinfo='skip'
            ))

        # --- LÓGICA VISTA MICRO (VENTANA ANUAL) ---
        if tipo_vista == "Micro (Ventana Anual)":
            fig.update_xaxes(range=[edad_min_zoom, edad_max_zoom])
            
            # Obtener competencias futuras del caché para marcarlas en la ventana
            hitos = obtener_historial_hitos_cache(usuario_id)
            if hitos:
                for hito in hitos:
                    edad_h = hito.get("edad_hito")
                    if edad_h and (edad_min_zoom <= edad_h <= edad_max_zoom):
                        fecha_str = hito.get("fecha_evento", "")
                        nombre_ev = hito.get("nombre_hito", "Evento")
                        # Calcular tiempo proyectado para ese hito
                        arr_h = np.array([edad_h])
                        t_proy_h = calcular_curva_atleta(arr_h, t0, T0, t_pb, T_pb, t_peak, T_target, k_global, factor_h)[0]
                        
                        fig.add_vline(
                            x=edad_h, line_width=1, line_dash="dash", line_color="mediumseagreen",
                            annotation_text=f"{nombre_ev} - {fecha_str}",
                            annotation_position="bottom right",
                            annotation_textangle=-90,
                            annotation_font=dict(color="mediumseagreen", size=10)
                        )

    # ---------------------------------------------------------
    # 7. ESTILIZACIÓN FINAL DEL GRÁFICO
    # ---------------------------------------------------------
    fig.update_layout(
        title=dict(text=f"<b>{titulo_figura}</b>", x=0.5, font=dict(size=18), y=0.95),
        xaxis=dict(title="Edad del Atleta (Años)", gridcolor='rgba(0,0,0,0.05)', showline=True, linewidth=1, linecolor='black'),
        yaxis=dict(
            title="Tiempo de Carrera (Segundos)", 
            gridcolor='rgba(0,0,0,0.05)',
            showline=True, linewidth=1, linecolor='black',
            tickformat=".2f" # Fallback visual, idealmente se usa tickvals/ticktext para formato M:SS
        ),
        template="plotly_white",
        legend=dict(
            orientation="v", y=0.99, x=0.75, 
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="lightgray", borderwidth=1
        ),
        margin=dict(l=50, r=30, t=80, b=50),
        height=550
    )

    # Convertir el eje Y a etiquetas amigables MM:SS
    if df_export is not None and not df_export.empty:
        # Extraer min y max aproximado de tiempos para generar los ticks
        if modo_equipo:
            y_min = df_global_marcas['tiempo'].min() * 0.9
            y_max = df_global_marcas['tiempo'].max() * 1.1
        else:
            y_min = min(T_target, T_intermedia) * 0.9
            y_max = max(T0, T_pb) * 1.1
            
        tick_vals = np.linspace(y_min, y_max, num=8)
        fig.update_layout(
            yaxis=dict(
                tickmode='array',
                tickvals=tick_vals,
                ticktext=[formatear_a_minutos(val) for val in tick_vals]
            )
        )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # ---------------------------------------------------------
    # 8. TABLA DE DATOS INFERIOR
    # ---------------------------------------------------------
    st.write("")
    df_tabla = pd.DataFrame()
    
    if modo_equipo:
        # En modo equipo, la tabla de exportación maneja la raw data.
        st.caption("Los datos detallados del equipo están disponibles en el Centro de Exportación.")
    else:
        if tipo_vista == "Macro (Historial Completo)":
            if not df_procesado.empty:
                df_tabla = df_procesado.copy()
                df_tabla["Tiempo"] = df_tabla["Tiempo"].apply(lambda x: formatear_a_minutos(float(x)))
                df_tabla["Edad"] = df_tabla["Edad"].apply(lambda x: f"{float(x):.2f} a")
                df_tabla["WA"] = df_procesado["Tiempo"].apply(lambda x: f"{calcular_puntos_wa(x, m_wr)} pts")
                # Reorganizar columnas
                df_tabla = df_tabla[["Edad", "Tiempo", "WA", "Evento / Fecha"]]
                st.dataframe(df_tabla, use_container_width=True, hide_index=True)
            else:
                st.dataframe(pd.DataFrame({"Edad":["-"], "Tiempo":["-"], "WA":["-"], "Evento / Fecha":["Sin marcas históricas registradas"]}), use_container_width=True, hide_index=True)
                
        elif tipo_vista == "Micro (Ventana Anual)":
            # Tabla de proyecciones para competencias futuras
            hitos = obtener_historial_hitos_cache(usuario_id)
            datos_tabla_micro = []
            if hitos:
                for hito in hitos:
                    edad_h = hito.get("edad_hito")
                    if edad_h and (edad_min_zoom <= edad_h <= edad_max_zoom):
                        arr_h = np.array([edad_h])
                        t_proy_h = calcular_curva_atleta(arr_h, t0, T0, t_pb, T_pb, t_peak, T_target, k_global, factor_h)[0]
                        datos_tabla_micro.append({
                            "Competencia / Evento": hito.get("nombre_hito", ""),
                            "Fecha": hito.get("fecha_evento", ""),
                            "Edad": f"{edad_h:.2f} a",
                            "Marca Proyectada": formatear_a_minutos(t_proy_h) + " s"
                        })
            if datos_tabla_micro:
                df_tabla = pd.DataFrame(datos_tabla_micro)
                st.dataframe(df_tabla, use_container_width=True, hide_index=True)
            else:
                st.info("No hay competencias programadas en el rango de edad seleccionado.")

    st.markdown("---")

    # ---------------------------------------------------------
    # 9. CENTRO DE EXPORTACIÓN DE REPORTES Y GRÁFICOS
    # ---------------------------------------------------------
    st.subheader("🖨️ Centro de Exportación de Reportes y Gráficos")
    col_dl1, col_dl2, col_dl3 = st.columns(3)
    
    # 9.1 Exportar Historial a CSV
    csv_data = df_export.to_csv(index=False).encode('utf-8') if df_export is not None else b""
    col_dl1.download_button(
        label="📥 Descargar Historial (CSV)",
        data=csv_data,
        file_name=f"historial_{prueba.replace(' ', '_').lower()}.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    # 9.2 Exportar Datos a TXT (Resumen del modelo)
    txt_content = f"--- Resumen de Proyección: {prueba} ---\n"
    txt_content += f"Atleta/Modo: {'Equipo' if modo_equipo else st.session_state.get('nadador_seleccionado_nombre')}\n"
    txt_content += f"Factor k: {k_global:.4f}\nMargen D: {margen_d:.2f} s\n"
    col_dl2.download_button(
        label="📄 Descargar Datos (TXT)",
        data=txt_content.encode('utf-8'),
        file_name=f"resumen_{prueba.replace(' ', '_').lower()}.txt",
        mime="text/plain",
        use_container_width=True
    )
    
    # 9.3 Exportar Gráfico a PNG
    try:
        # Requiere el paquete 'kaleido' instalado en el entorno
        img_bytes = fig.to_image(format="png", engine="kaleido", width=1000, height=600, scale=2)
        col_dl3.download_button(
            label="🖼️ Guardar Gráfico (Imagen PNG)",
            data=img_bytes,
            file_name=f"proyeccion_{prueba.replace(' ', '_').lower()}.png",
            mime="image/png",
            use_container_width=True
        )
    except Exception as e:
        # Fallback si 'kaleido' no está disponible
        col_dl3.button("🖼️ Guardar Gráfico (Imagen PNG)", disabled=True, help="El motor de exportación PNG ('kaleido') no está instalado o falló.", use_container_width=True)
