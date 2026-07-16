import streamlit as st
import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io

def renderizar_tab_reportes(datos_sidebar=None):
    """
    CÓDIGO MODULAR OPTIMIZADO Y BLINDADO (PRODUCCIÓN)
    Version: 2.0 (Resiliente a esquemas, descarga completa e inmunidad IDOR)
    """
    st.markdown("### 📊 Panel de Control y Análisis de Carga Individual")
    st.caption("Define la ventana temporal y evalúa el volumen biomecánico o modela el rendimiento científico de un atleta específico.")

    # =============================================================================
    # 1. TEMPORALIDAD DE LOS REPORTES (MANEJO DE VENTANAS CRÍTICAS)
    # =============================================================================
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
        index=3,  # Defecto en 42 días por relevancia del CTL
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

    # =============================================================================
    # 2. RESOLUCIÓN DE NÓMINA SEGURA POR ROL
    # =============================================================================
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
                    else:
                        st.warning("⚠️ No posees atletas asignados bajo tu perfil de Entrenador.")
                else:
                    st.error("❌ Error de sesión: No se detectó ID único de Entrenador.")

            elif rol_usuario in ["Head Coach", "Administrador"]:
                resp_sb = ctx_supabase_rep.table("usuarios").select("id, nombre, email, genero, fecha_nacimiento").eq("rol", "Nadador").eq("estatus", "Activo").execute()
                if resp_sb.data:
                    atletas_pool_rep = resp_sb.data
            else:
                # [CORRECCIÓN] Cierre explícito de seguridad para roles desconocidos
                st.error("🔒 Rol no autorizado para visualizar reportes de rendimiento.")
                return

        except Exception as e:
            st.error(f"Error al cargar nómina para reportes: {e}")
            return

    # Desplegar selector de Atleta Único
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
        
        # 🛡️ [BLINDAJE CRÍTICO ANTI-IDOR] Validación forzosa en el backend
        if atleta_sel_id not in dict_nom_rep:
            st.error("🔒 Acción denegada: Intento de acceso a un registro de atleta no autorizado.")
            st.stop()
        
        nombre_atleta_safename = dict_nom_rep[atleta_sel_id].lower().replace(' ', '_')
        st.success(f"🎯 Analizando el perfil de: {dict_nom_rep[atleta_sel_id]}")
        st.markdown("---")
        
        # =============================================================================
        # 3. EXTRACCIÓN Y PREPARACIÓN DE DATOS DEL ATLETA SELECCIONADO
        # =============================================================================
        with st.spinner("Compilando históricos de entrenamiento..."):
            try:
                query_rep = ctx_supabase_rep.table("bitacora_entrenamientos").select("*").eq("atleta_id", atleta_sel_id)
                if fecha_limite:
                    query_rep = query_rep.gte("fecha", str(fecha_limite))
                
                data_historica = query_rep.execute()
                records = data_historica.data if data_historica else []
                
                # Filtrar estrictamente hasta el día de hoy
                records_hasta_hoy = []
                for r in records:
                    if r.get("fecha"):
                        f_rec = datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date() if isinstance(r["fecha"], str) else r["fecha"]
                        if f_rec <= fecha_fin_rep:
                            records_hasta_hoy.append(r)
                
                if not records_hasta_hoy:
                    st.warning(f"📭 El nadador seleccionado no registra entrenamientos en la ventana temporal definida.")
                else:
                    # Inyección de Subtabs discriminados
                    subtab_volumen, subtab_fisiologico = st.tabs([
                        "🏊‍♂️ Distribución y Carga de Volumen", 
                        "📈 Modelo Fisiológico (CTL / ATL / TSB)"
                    ])
                    
                    # Rangos temporales base del atleta
                    if rango_fechas_completo is None:
                        fechas_instancias = [datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date() for r in records_hasta_hoy if r.get("fecha")]
                        rango_analisis = pd.date_range(start=min(fechas_instancias), end=max(fechas_instancias)).date if fechas_instancias else [datetime.date.today()]
                    else:
                        rango_analisis = rango_fechas_completo

# =============================================================================
                    # SUBTAB 1: DISTRIBUCIÓN Y CARGA DE VOLUMEN ACUMULATIVA (INTEGRAL EN EL TIEMPO)
                    # =============================================================================
                    with subtab_volumen:
                        st.markdown("#### 📈 Diagnóstico de Carga Acumulada y Bloques Fijos")
                        st.caption("Métricas fijas calculadas hacia atrás desde hoy, independientes de la ventana visual seleccionada.")
                        
                        # 1. CÁLCULO DE BLOQUES TEMPORALES SOLICITADOS (HACIA ATRÁS DESDE HOY)
                        hoy_date = datetime.date.today()
                        def calcular_volumen_bloque(dias_bloque):
                            limite_bloque = hoy_date - datetime.timedelta(days=dias_bloque)
                            return sum([
                                r.get("metros_totales", 0) for r in records_hasta_hoy 
                                if r.get("fecha") and (datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date() if isinstance(r["fecha"], str) else r["fecha"]) >= limite_bloque
                            ])
                        
                        vol_7d = calcular_volumen_bloque(7)
                        vol_30d = calcular_volumen_bloque(30)
                        vol_42d = calcular_volumen_bloque(42)
                        vol_90d = calcular_volumen_bloque(90)
                        
                        # Panel de control de metros absolutos
                        c_b1, c_b2, c_b3, c_b4 = st.columns(4)
                        with c_b1: st.metric(label="📆 Últimos 7 días", value=f"{vol_7d:,} m")
                        with c_b2: st.metric(label="📅 Últimos 30 días", value=f"{vol_30d:,} m")
                        with c_b3: st.metric(label="💪 Últimos 42 días (CTL)", value=f"{vol_42d:,} m")
                        with c_b4: st.metric(label="🌀 Trimestre (90d)", value=f"{vol_90d:,} m")
                        
                        st.markdown("---")
                        st.markdown("#### 🏊‍♂️ Áreas Acumulativas de Carga (Análisis de Pendientes)")
                        st.caption("La inclinación de la curva representa la tasa de carga. Una meseta horizontal (pendiente = 0) indica ausencia de entrenamiento.")

                        # 2. PREPARACIÓN DE LA MATRIZ DIARIA BASE
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
                        
                                dict_int = r.get("desglose_intensity") or r.get("desglose_intensidad") or {}
                                for k_int, v_m in dict_int.items():
                                    target_int = "Aeróbico Ligero"
                                    if "Medio" in k_int: target_int = "Aeróbico Medio"
                                    elif "Umbral" in k_int or "Sostenido" in k_int: target_int = "Umbral"
                                    elif "Sprint" in k_int or "Anaeróbico" in k_int: target_int = "Anaeróbico"
                                    row_vol[target_int] += v_m
                                    global_intensidades[target_int] += v_m
                                    
                            matriz_volumen.append(row_vol)
                            
                        df_vol_diario = pd.DataFrame(matriz_volumen).sort_values("Fecha").reset_index(drop=True)
                        
                        # 3. TRANSFORMACIÓN INTEGRAL: CALCULAR SUMAS ACUMULATIVAS (CUMSUM)
                        df_vol_acum = df_vol_diario.copy()
                        for est in estilos_lista:
                            df_vol_acum[est] = df_vol_acum[est].cumsum()
                        for inten in intensidades_lista:
                            df_vol_acum[inten] = df_vol_acum[inten].cumsum()
                        
                        # --- GRÁFICO 1: ACUMULADO POR ESTILOS ---
                        fig_est, ax_est = plt.subplots(figsize=(8.5, 3.2))
                        ax_est.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
                        ax_est.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(df_vol_acum) // 6)))
                        
                        y_estilos_acum = [df_vol_acum[est].values for est in estilos_lista]
                        colores_estilos = ["#2ecc71", "#3498db", "#9b59b6", "#e67e22", "#f1c40f", "#95a5a6"]
                        
                        ax_est.stackplot(df_vol_acum["Fecha"], *y_estilos_acum, labels=estilos_lista, colors=colores_estilos, alpha=0.80)
                        ax_est.set_ylabel("Metros Acumulados", fontsize=8)
                        ax_est.set_title("Evolución Integral del Volumen por Estilo", fontsize=9, fontweight='bold')
                        ax_est.tick_params(axis='both', labelsize=7)
                        ax_est.grid(True, linestyle=":", alpha=0.4)
                        ax_est.legend(loc="upper left", fontsize=7, ncol=3)
                        plt.tight_layout()
                        st.pyplot(fig_est)
                        
                        # --- GRÁFICO 2: ACUMULADO POR INTENSIDADES ---
                        fig_int, ax_int = plt.subplots(figsize=(8.5, 3.2))
                        ax_int.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
                        ax_int.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(df_vol_acum) // 6)))
                        
                        y_intensidades_acum = [df_vol_acum[inten].values for inten in intensidades_lista]
                        # Semáforo fisiológico de carga: verde (suave) a rojo (anaeróbico)
                        colores_intensidades = ["#27ae60", "#f1c40f", "#e67e22", "#c0392b"] 
                        
                        ax_int.stackplot(df_vol_acum["Fecha"], *y_intensidades_acum, labels=intensidades_lista, colors=colores_intensidades, alpha=0.80)
                        ax_int.set_ylabel("Metros Acumulados", fontsize=8)
                        ax_int.set_title("Evolución Integral del Volumen por Zona de Intensidad", fontsize=9, fontweight='bold')
                        ax_int.tick_params(axis='both', labelsize=7)
                        ax_int.grid(True, linestyle=":", alpha=0.4)
                        ax_int.legend(loc="upper left", fontsize=7, ncol=2)
                        plt.tight_layout()
                        st.pyplot(fig_int)

                        # Guardar Gráficos combinados en buffer
                        buf_png_vol = io.BytesIO()
                        fig_est.savefig(buf_png_vol, format="png", dpi=300)
                        st.download_button("🖼️ Guardar Tendencia de Estilos (PNG)", data=buf_png_vol.getvalue(), file_name=f"acumulado_estilos_{nombre_atleta_safename}.png", mime="image/png")

                        # 4. MATRIZ DE AUDITORÍA DIARIA (Mantiene la transparencia de los datos crudos)
                        st.markdown("##### 📋 Matriz de Auditoría de Volúmenes Diarios")
                        df_tabla_vol = df_vol_diario.copy()
                        fila_totales_vol = {"Fecha": "TOTAL ACUMULADO"}
                        for col in columnas_vol[1:]:
                            fila_totales_vol[col] = df_tabla_vol[col].sum()
                            
                        df_tabla_vol["Fecha"] = df_tabla_vol["Fecha"].map(lambda x: x.strftime("%Y-%m-%d") if isinstance(x, (datetime.date, datetime.datetime)) else str(x))
                        df_tabla_vol = pd.concat([df_tabla_vol, pd.DataFrame([fila_totales_vol])], ignore_index=True)
                        st.write(df_tabla_vol.to_html(index=False, classes="tabla-estilizada"), unsafe_allow_html=True)
                        
                        # Exportaciones analíticas estándar
                        csv_unificado_data = df_tabla_vol.to_csv(index=False).encode('utf-8')
                        st.download_button(label="📥 Descargar Historial de Auditoría (CSV)", data=csv_unificado_data, file_name=f"auditoria_volumen_{nombre_atleta_safename}.csv", mime="text/csv", use_container_width=True)

# =============================================================================
                    # SUBTAB 2: ANÁLISIS CIENTÍFICO INDIVIDUAL (TRIMP EXPONENCIAL - ADIMENSIONAL)
                    # =============================================================================
                    with subtab_fisiologico:
                        st.markdown("### 📈 Modelo Fisiológico TRIMP Exponencial (Adimensional)")
                        
                        with st.expander("📘 Metodología de Carga por Esfuerzo Percibido (Foster & Bannister)", expanded=False):
                            st.markdown("**Fórmula del Impulso de Entrenamiento de Alta Intensidad:**")
                            st.latex(r"\text{Carga Diaria (AU)} = \text{Volumen (Km)} \times e^{0.218 \times \text{RPE}}")
                            st.latex(r"\text{TSB \%}_t = \left( \frac{\text{CTL}_t - \text{ATL}_t}{\max(\text{CTL}_t, \text{ATL}_t)} \right) \cdot 100")
                            st.caption("Nota: El factor exponencial 0.218 penaliza severamente las sesiones de alto RPE, emulando la curva de acumulación de lactato en sangre.")

                        # Inicializar mapa de carga diaria adimensional (AU)
                        carga_diaria_au = {f: 0.0 for f in rango_analisis}
                        
                        # Mapeo interno de RPE equivalente por zona (en caso de que falte el RPE global)
                        mapeo_rpe_zonas = {
                            "Aeróbico Ligero": 3.5,
                            "Aeróbico Medio": 5.5,
                            "Umbral": 7.5,
                            "Anaeróbico": 9.5,
                            "Sprint": 10.0
                        }
                        
                        for r in records_hasta_hoy:
                            f_rec = datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date() if isinstance(r["fecha"], str) else r["fecha"]
                            if f_rec in carga_diaria_au:
                                # 1. Intentar capturar el RPE de la pizarra consolidada
                                rpe_global = r.get("rpe") or r.get("factor_exigencia")
                                
                                if rpe_global and float(rpe_global) > 0:
                                    # Conversión directa: Volumen en Km * e^(0.218 * RPE)
                                    vol_km = r.get("metros_totales", 0) / 1000.0
                                    carga_sesion = vol_km * np.exp(0.218 * float(rpe_global))
                                else:
                                    # 2. Fallback: Si no hay RPE global, calculamos de forma ponderada por metros en cada zona
                                    carga_sesion = 0.0
                                    int_dict = r.get("desglose_intensity") or r.get("desglose_intensidad") or {}
                                    for k_int, m_int in int_dict.items():
                                        rpe_zona = 3.5 # Defecto base
                                        for key_map, val_rpe in mapeo_rpe_zonas.items():
                                            if key_map in k_int:
                                                rpe_zona = val_rpe
                                                break
                                        vol_zona_km = m_int / 1000.0
                                        carga_sesion += vol_zona_km * np.exp(0.218 * rpe_zona)
                                    
                                    # 3. Salvaguarda absoluta si el registro está completamente vacío
                                    if not int_dict and r.get("metros_totales", 0) > 0:
                                        vol_km = r.get("metros_totales", 0) / 1000.0
                                        carga_sesion = vol_km * np.exp(0.218 * 5.0) # Asume un RPE 5 moderado
                                
                                carga_diaria_au[f_rec] += carga_sesion
                        
                        # Construcción del DataFrame Fisiológico
                        df_cargas = pd.DataFrame([{"Fecha": f, "Carga_AU": carga_diaria_au[f]} for f in rango_analisis])
                        df_cargas["Fecha"] = pd.to_datetime(df_cargas["Fecha"])
                        df_cargas = df_cargas.sort_values("Fecha").reset_index(drop=True)
                        
                        # Filtros Exponenciales EWM para CTL (42 días) y ATL (7 días)
                        df_cargas["CTL"] = df_cargas["Carga_AU"].ewm(span=42, adjust=False).mean()
                        df_cargas["ATL"] = df_cargas["Carga_AU"].ewm(span=7, adjust=False).mean()
                        df_cargas["TSB"] = df_cargas["CTL"] - df_cargas["ATL"]
                        
                        # Normalización del TSB% contra el máximo metabólico alcanzado
                        max_denominador = np.maximum(df_cargas["CTL"], df_cargas["ATL"])
                        df_cargas["TSB_Pct"] = ((df_cargas["TSB"] / max_denominador) * 100).fillna(0.0)
                        
                        ultima_fila = df_cargas.iloc[-1]
                        val_ctl, val_atl, val_tsb = round(float(ultima_fila["CTL"]), 1), round(float(ultima_fila["ATL"]), 1), round(float(ultima_fila["TSB"]), 1)
                        pct_tsb = round(float(ultima_fila["TSB_Pct"]), 1)
                        
                        # Semáforo de Control Fisiológico por Porcentaje
                        if pct_tsb <= -35.0: estado_forma = f"🔴 Fatiga Severa / Alerta Lesión ({pct_tsb}%)"
                        elif -35.0 < pct_tsb < -10.0: estado_forma = f"⚠️ Fase Inmunológica / Sobrecarga ({pct_tsb}%)"
                        elif -10.0 <= pct_tsb <= 10.0: estado_forma = f"🟡 Balance de Adaptación Óptima ({pct_tsb}%)"
                        elif 10.0 < pct_tsb <= 40.0: estado_forma = f"🟢 Supercompensación / Taper Competitivo (+{pct_tsb}%)"
                        else: estado_forma = f"❌ Pérdida de Estímulo / Desentrenamiento (+{pct_tsb}%)"
                        
                        c_m1, c_m2, c_m3 = st.columns(3)
                        with c_m1: st.metric("💪 Fitness (CTL)", value=f"{val_ctl} AU")
                        with c_m2: st.metric("🔥 Fatiga (ATL)", value=f"{val_atl} AU")
                        with c_m3: st.metric("🎯 Balance Fisiológico", value=f"{val_tsb} AU", delta=estado_forma)
                        
                        # --- GENERACIÓN DEL PLOT LINEAL COMPRIMIDO ---
                        fig_ban, ax1 = plt.subplots(figsize=(8.5, 3.8))
                        
                        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
                        if len(df_cargas) > 180:
                            ax1.xaxis.set_major_locator(mdates.DayLocator(interval=30))
                        elif len(df_cargas) > 42:
                            ax1.xaxis.set_major_locator(mdates.DayLocator(interval=7))
                        else:
                            ax1.xaxis.set_major_locator(mdates.DayLocator(interval=2))
                                
                        l_ctl = ax1.plot(df_cargas["Fecha"], df_cargas["CTL"], label="Fitness Crónico (CTL)", color="#1f77b4", linewidth=2.0)
                        l_atl = ax1.plot(df_cargas["Fecha"], df_cargas["ATL"], label="Fatiga Aguda (ATL)", color="#d62728", linewidth=1.5, linestyle="--")
                        b_tsb = ax1.bar(df_cargas["Fecha"], df_cargas["Carga_AU"], label="Estrés Diario (Impulso AU)", color="#2ca02c", alpha=0.15, width=1.0)
                        
                        ax1.set_ylabel("Métricas de Carga (Escala Lineal AU)", color="#1f77b4", fontsize=8)
                        ax1.tick_params(axis='y', labelcolor="#1f77b4", labelsize=7)
                        ax1.tick_params(axis='x', labelsize=7, rotation=35)
                        ax1.grid(True, linestyle=":", alpha=0.3) # Rejilla limpia gracias a la escala lineal
                        
                        # Eje derecho para el porcentaje del índice de balance (TSB %)
                        ax2 = ax1.twinx()
                        l_pct = ax2.plot(df_cargas["Fecha"], df_cargas["TSB_Pct"], label="Índice TSB (%)", color="#2c3e50", linewidth=1.8)
                        
                        ax2.axhspan(10.0, 40.0, color="#abebc6", alpha=0.25, label="🟢 Tapering / Supercompensación")
                        ax2.axhspan(-35.0, -10.0, color="#f9e79f", alpha=0.20, label="⚠️ Bloque de Sobrecarga")
                        ax2.axhline(0.0, color="#2c3e50", linestyle="-", linewidth=1.0, alpha=0.4)
                        
                        ax2.set_ylabel("Balance Porcentual Regulación (-100% a +100%)", color="#2c3e50", fontsize=8)
                        ax2.tick_params(axis='y', labelcolor="#2c3e50", labelsize=7)
                        ax2.set_ylim(-105, 105)
                        
                        lineas_totales = l_ctl + l_atl + [b_tsb] + l_pct
                        etiquetas_totales = [l.get_label() for l in lineas_totales]
                        ax1.legend(lineas_totales, etiquetas_totales, loc="upper left", fontsize=7, ncol=2)
                        
                        plt.tight_layout()
                        st.pyplot(fig_ban)
                        
                        # Guardar gráfico de Bannister
                        buf_png_ban = io.BytesIO()
                        fig_ban.savefig(buf_png_ban, format="png", dpi=300)
                        st.download_button("🖼️ Guardar Perfil Fisiológico (PNG)", data=buf_png_ban.getvalue(), file_name=f"fisiologico_{nombre_atleta_safename}.png", mime="image/png")

                        # Tabla de reporte de Bannister
                        st.markdown("##### 📋 Tabla de Valores Diarios y Métricas de Estado")
                        df_tabla_ban = df_cargas.copy()
                        df_tabla_ban["Fecha"] = df_tabla_ban["Fecha"].dt.strftime("%Y-%m-%d")
                        df_tabla_ban["Carga_AU"] = df_tabla_ban["Carga_AU"].round(1)
                        df_tabla_ban["CTL"] = df_tabla_ban["CTL"].round(1)
                        df_tabla_ban["ATL"] = df_tabla_ban["ATL"].round(1)
                        df_tabla_ban["TSB"] = df_tabla_ban["TSB"].round(1)
                        df_tabla_ban["TSB_Pct"] = df_tabla_ban["TSB_Pct"].round(1).astype(str) + " %"
                        
                        df_tabla_ban.columns = [
                            "Fecha", "Carga TRIMP (AU/Día)", "CTL (Fitness AU)", 
                            "ATL (Fatiga AU)", "TSB (Forma AU)", "TSB Relativo (% Máx)"
                        ]
                        st.write(df_tabla_ban.to_html(index=False, classes="tabla-estilizada"), unsafe_allow_html=True)
                        
                        # Exportación de datos fisiológicos
                        csv_ban_data = df_tabla_ban.to_csv(index=False).encode('utf-8')
                        txt_ban_data = df_tabla_ban.to_string(index=False).encode('utf-8')
                        
                        c_ban_exp1, c_ban_exp2 = st.columns(2)
                        with c_ban_exp1:
                            st.download_button(label="📥 Descargar Métricas Fisiológicas (CSV)", data=csv_ban_data, file_name=f"fisiologico_{nombre_atleta_safename}.csv", mime="text/csv", use_container_width=True)
                        with c_ban_exp2:
                            st.download_button(label="📄 Descargar Reporte de Carga (TXT)", data=txt_ban_data, file_name=f"carga_{nombre_atleta_safename}.txt", mime="text/plain", use_container_width=True)

            except Exception as e:
                st.error(f"Error al computar el reporte analítico avanzado: {e}")
