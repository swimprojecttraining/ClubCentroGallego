import streamlit as st
import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io

def renderizar_tab_reportes(datos_sidebar=None):
    """
    CÓDIGO AUDITADO: 13. Rutina de reportes de consolidación de volúmenes y carga fisiológica.
    Fidelidad total a la escala symlog, subpestañas de volumen/fisiología y matriz de auditoría.
    """
    st.markdown("### 📊 Panel de Control y Análisis de Carga Individual")
    st.caption("Define la ventana temporal y evalúa el volumen biomecánico o modela el rendimiento científico de un atleta específico.")

    # 1. Temporalidad de los Reportes
    opciones_tiempo = {
        "7 días (Última semana - ATL)": 7,
        "28 días (Ciclo Corto)": 28,
        "30 días (Mensual)": 30,
        "42 días (Carga Crónica - CTL)": 42,
        "90 días (Macrociclo Trimestral)": 90,
        "180 días (Semestral)": 180,
        "365 días (Anual)": 365,
        "Total Histórico": None
    }
    
    ventana_sel = st.selectbox(
        "⏳ Ventana Temporal de Análisis:",
        options=list(opciones_tiempo.keys()),
        index=3,
        key="rep_selectbox_temporalidad"
    )
    
    dias_atras = opciones_tiempo[ventana_sel]
    fecha_fin_rep = datetime.date.today()

    if dias_atras:
        fecha_limite = fecha_fin_rep - datetime.timedelta(days=dias_atras)
        rango_fechas_completo = pd.date_range(start=fecha_limite + datetime.timedelta(days=1), end=fecha_fin_rep).date
    else:
        fecha_limite = None
        rango_fechas_completo = None

    st.markdown("---")

    # 2. Resolución de Nómina Segura por Rol
    ctx_supabase_rep = st.session_state.get("supabase")
    atletas_pool_rep = []
    rol_usuario = st.session_state.get("rol")
    id_usuario = st.session_state.get("usuario_id")

    if ctx_supabase_rep:
        try:
            if rol_usuario == "Nadador":
                resp_sb = ctx_supabase_rep.table("usuarios").select("id, nombre, email, genero, fecha_nacimiento").eq("id", id_usuario).execute()
                if resp_sb.data:
                    atletas_pool_rep = resp_sb.data
            elif rol_usuario == "Entrenador":
                if id_usuario:
                    resp_asig_rep = ctx_supabase_rep.table("asignaciones").select("atleta_id").eq("entrenador_id", id_usuario).execute()
                    ids_autorizados_rep = [reg["atleta_id"] for reg in resp_asig_rep.data] if resp_asig_rep.data else []
                    if ids_autorizados_rep:
                        resp_sb = ctx_supabase_rep.table("usuarios").select("id, nombre, email, genero, fecha_nacimiento").in_("id", ids_autorizados_rep).eq("rol", "Nadador").eq("estatus", "Activo").execute()
                        if resp_sb.data:
                            atletas_pool_rep = resp_sb.data
            elif rol_usuario in ["Head Coach", "Administrador"]:
                resp_sb = ctx_supabase_rep.table("usuarios").select("id, nombre, email, genero, fecha_nacimiento").eq("rol", "Nadador").eq("estatus", "Activo").execute()
                if resp_sb.data:
                    atletas_pool_rep = resp_sb.data
        except Exception as e:
            st.error(f"Error al cargar nómina para reportes: {e}")

    if not atletas_pool_rep:
        st.info("💡 No hay atletas disponibles para generar reportes.")
    else:
        dict_nom_rep = {a["id"]: a["nombre"] for a in atletas_pool_rep}
        atleta_sel_id = st.selectbox(
            "🏊‍♂️ Seleccione el Nadador a Analizar:",
            options=list(dict_nom_rep.keys()),
            format_func=lambda x: dict_nom_rep.get(x, "Cargando atleta..."),
            key="rep_selectbox_atleta_unico"
        )
        
        nombre_atleta_safename = dict_nom_rep[atleta_sel_id].lower().replace(' ', '_')
        st.success(f"🎯 Analizando el perfil de: {dict_nom_rep[atleta_sel_id]}")
        st.markdown("---")
        
        # 3. Extracción de Datos de la Bitácora de Entrenamientos
        with st.spinner("Compilando históricos de entrenamiento..."):
            try:
                query_rep = ctx_supabase_rep.table("bitacora_entrenamientos").select("*").eq("atleta_id", atleta_sel_id)
                if fecha_limite:
                    query_rep = query_rep.gte("fecha", str(fecha_limite))
                
                data_historica = query_rep.execute()
                records = data_historica.data if data_historica else []
                
                records_hasta_hoy = []
                for r in records:
                    if r.get("fecha"):
                        f_rec = datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date() if isinstance(r["fecha"], str) else r["fecha"]
                        if f_rec <= fecha_fin_rep:
                            records_hasta_hoy.append(r)
                
                if not records_hasta_hoy:
                    st.warning(f"📭 El nadador seleccionado no registra entrenamientos en la ventana temporal definida.")
                else:
                    subtab_volumen, subtab_fisiologico = st.tabs([
                        "🏊‍♂️ Distribución y Carga de Volumen", 
                        "📈 Modelo Fisiológico (CTL / ATL / TSB)"
                    ])
                    
                    if rango_fechas_completo is None:
                        fechas_instancias = [datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date() for r in records_hasta_hoy if r.get("fecha")]
                        rango_analisis = pd.date_range(start=min(fechas_instancias), end=max(fechas_instancias)).date if fechas_instancias else [datetime.date.today()]
                    else:
                        rango_analisis = rango_fechas_completo

                    # SUBTAB 1: VOLUMEN
                    with subtab_volumen:
                        volumen_acumulado = sum([r.get("metros_totales", 0) for r in records_hasta_hoy])
                        st.metric(label="🏊‍♂️ Volumen Total Ejecutado", value=f"{volumen_acumulado:,} metros")
                        
                        estilos_lista = ["Libre", "Espalda", "Pecho", "Mariposa", "Combinado", "Otros"]
                        intensidades_lista = ["Aeróbico Ligero", "Aeróbico Medio", "Umbral", "Anaeróbico"]
                        columnas_vol = ["Fecha"] + estilos_lista + intensidades_lista + ["Total Día"]
                        
                        matriz_volumen = []
                        global_estilos = {e: 0 for e in estilos_lista}
                        global_intensidades = {i: 0 for i in intensidades_lista}
                        
                        for f in rango_analisis:
                            dia_recs = [r for r in records_hasta_hoy if (datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date() if isinstance(r["fecha"], str) else r["fecha"]) == f]
                            row_vol = {col: 0 for col in columnas_vol}
                            row_vol["Fecha"] = f
                            
                            for r in dia_recs:
                                dict_est = r.get("desglose_estilos") or {}
                                for k_est, v_m in dict_est.items():
                                    target_est = k_est if k_est in estilos_lista else "Otros"
                                    row_vol[target_est] += v_m
                                    row_vol["Total Día"] += v_m
                                    global_estilos[target_est] += v_m
                    
                                dict_int = r.get("desglose_intensidad") or {}
                                for k_int, v_m in dict_int.items():
                                    target_int = "Aeróbico Ligero"
                                    if "Medio" in k_int: target_int = "Aeróbico Medio"
                                    elif "Umbral" in k_int or "Sostenido" in k_int: target_int = "Umbral"
                                    elif "Sprint" in k_int or "Anaeróbico" in k_int: target_int = "Anaeróbico"
                                    row_vol[target_int] += v_m
                                    global_intensidades[target_int] += v_m
                                    
                            matriz_volumen.append(row_vol)
                            
                        df_vol_diario = pd.DataFrame(matriz_volumen).sort_values("Fecha").reset_index(drop=True)
                        
                        fig_vol, ax1 = plt.subplots(figsize=(8.5, 3.8))
                        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
                        if len(df_vol_diario) > 42:
                            ax1.xaxis.set_major_locator(mdates.DayLocator(interval=7))
                        else:
                            ax1.xaxis.set_major_locator(mdates.DayLocator(interval=2))
                            
                        y_estilos = [df_vol_diario[est].values for est in estilos_lista]
                        colores_estilos = ["#2ecc71", "#3498db", "#9b59b6", "#e67e22", "#f1c40f", "#95a5a6"]
                        
                        ax1.stackplot(df_vol_diario["Fecha"], *y_estilos, labels=[f"Estilo: {est}" for est in estilos_lista], colors=colores_estilos, alpha=0.65)
                        ax1.set_xlabel("Línea Temporal del Calendario", fontsize=8)
                        ax1.set_ylabel("Volumen por Estilo (Metros)", fontsize=8)
                        ax1.set_yscale('symlog', linthresh=500)
                        ax1.grid(True, linestyle=":", alpha=0.3)
                        
                        ax2 = ax1.twinx()
                        config_lineas_int = [
                            {"color": "#27ae60", "linestyle": "-",  "marker": "x"},
                            {"color": "#f39c12", "linestyle": "--", "marker": "*"},
                            {"color": "#d35400", "linestyle": "-.", "marker": ">"},
                            {"color": "#c0392b", "linestyle": ":",  "marker": "d"}
                        ]
                        for idx, inten in enumerate(intensidades_lista):
                            cfg = config_lineas_int[idx]
                            ax2.plot(df_vol_diario["Fecha"], df_vol_diario[inten], label=f"Zona: {inten}", color=cfg["color"], linewidth=1.5, linestyle=cfg["linestyle"], marker=cfg["marker"], markersize=4)
                            
                        ax2.set_ylabel("Volumen por Intensidad (Metros)", fontsize=8)
                        ax2.set_yscale('symlog', linthresh=500)
                        
                        lines1, labels1 = ax1.get_legend_handles_labels()
                        lines2, labels2 = ax2.get_legend_handles_labels()
                        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=7, ncol=3)
                        plt.tight_layout()
                        st.pyplot(fig_vol)
                        
                        # Matriz de Auditoría HTML
                        st.markdown("##### 📋 Matriz de Auditoría de Volúmenes Diarios")
                        df_tabla_vol = df_vol_diario.copy()
                        fila_totales_vol = {"Fecha": "TOTAL ACUMULADO"}
                        for col in columnas_vol[1:]:
                            fila_totales_vol[col] = df_tabla_vol[col].sum()
                        df_tabla_vol["Fecha"] = df_tabla_vol["Fecha"].map(lambda x: x.strftime("%Y-%m-%d"))
                        df_tabla_vol = pd.concat([df_tabla_vol, pd.DataFrame([fila_totales_vol])], ignore_index=True)
                        st.write(df_tabla_vol.to_html(index=False, classes="tabla-estilizada"), unsafe_allow_html=True)

                    # SUBTAB 2: BANNISTER FISIOLÓGICO
                    with subtab_fisiologico:
                        st.markdown("### 📈 Modelo Fisiológico Bannister Híbrido")
                        mapeo_factores = {"Aeróbico Ligero": 1.0, "Aeróbico Medio": 1.2, "Umbral": 1.4, "Anaeróbico": 1.7, "Sprint": 1.7}
                        vol_diario_map = {f: 0.0 for f in rango_analisis}
                        
                        for r in records_hasta_hoy:
                            f_rec = datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date() if isinstance(r["fecha"], str) else r["fecha"]
                            if f_rec in vol_diario_map:
                                int_dict = r.get("desglose_intensidad") or {}
                                subtotal_ponderado = 0.0
                                for k_int, m_int in int_dict.items():
                                    factor = next((f_val for key_map, f_val in mapeo_factores.items() if key_map in k_int), 1.0)
                                    subtotal_ponderado += (m_int * factor)
                                if not int_dict:
                                    subtotal_ponderado = r.get("metros_totales", 0) * r.get("factor_exigencia", 1.0)
                                vol_diario_map[f_rec] += subtotal_ponderado
                        
                        df_cargas = pd.DataFrame([{"Fecha": f, "Volumen": vol_diario_map[f]} for f in rango_analisis])
                        df_cargas["Fecha"] = pd.to_datetime(df_cargas["Fecha"])
                        df_cargas = df_cargas.sort_values("Fecha").reset_index(drop=True)
                        
                        df_cargas["CTL"] = df_cargas["Volumen"].ewm(span=42, adjust=False).mean()
                        df_cargas["ATL"] = df_cargas["Volumen"].ewm(span=7, adjust=False).mean()
                        df_cargas["TSB"] = df_cargas["CTL"] - df_cargas["ATL"]
                        
                        max_denominador = np.maximum(df_cargas["CTL"], df_cargas["ATL"])
                        df_cargas["TSB_Pct"] = ((df_cargas["TSB"] / max_denominador) * 100).fillna(0.0)
                        
                        ultima_fila = df_cargas.iloc[-1]
                        val_ctl, val_atl, val_tsb = int(ultima_fila["CTL"]), int(ultima_fila["ATL"]), int(ultima_fila["TSB"])
                        pct_tsb = round(float(ultima_fila["TSB_Pct"]), 1)
                        
                        c_m1, c_m2, c_m3 = st.columns(3)
                        with c_m1: st.metric("💪 Fitness (CTL)", value=f"{val_ctl:,} m")
                        with c_m2: st.metric("🔥 Fatiga (ATL)", value=f"{val_atl:,} m")
                        with c_m3: st.metric("🎯 Índice Balance (TSB %)", value=f"{pct_tsb}%")
                        
                        fig_ban, ax1 = plt.subplots(figsize=(8.5, 3.8))
                        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
                        ax1.plot(df_cargas["Fecha"], df_cargas["CTL"], label="Fitness Crónico (CTL)", color="#1f77b4", linewidth=2.0)
                        ax1.plot(df_cargas["Fecha"], df_cargas["ATL"], label="Fatiga Aguda (ATL)", color="#d62728", linewidth=1.5, linestyle="--")
                        ax1.bar(df_cargas["Fecha"], df_cargas["TSB"], label="Balance Neto (TSB m)", color="#2ca02c", alpha=0.20, width=1.0)
                        ax1.set_yscale('symlog', linthresh=500)
                        ax1.grid(True, linestyle=":", alpha=0.2)
                        
                        ax2 = ax1.twinx()
                        ax2.plot(df_cargas["Fecha"], df_cargas["TSB_Pct"], label="Índice TSB Acotado (%)", color="#2c3e50", linewidth=1.8)
                        ax2.set_ylim(-105, 105)
                        
                        plt.tight_layout()
                        st.pyplot(fig_ban)
                        
                        df_tabla_ban = df_cargas.copy()
                        df_tabla_ban["Fecha"] = df_tabla_ban["Fecha"].dt.strftime("%Y-%m-%d")
                        df_tabla_ban.columns = ["Fecha", "Metros Ponderados", "CTL", "ATL", "TSB", "TSB %"]
                        st.write(df_tabla_ban.to_html(index=False, classes="tabla-estilizada"), unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error al computar el reporte: {e}")
