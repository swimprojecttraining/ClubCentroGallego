import streamlit as st
import pandas as pd
import datetime
import urllib.parse

from formulas.formulas_lib_funciones import calcular_edad_tecnica_al_31_dic, calcular_categoria_competencia[cite: 1]

def renderizar_tab_pizarra(datos_sidebar):
    """
    Módulo operativo independiente para la Pizarra de Entrenamiento Diario,
    Difusión por Canales, Segmentación e Imputación Histórica de Carga.
    """
    # Extracción de parámetros de control desde el Sidebar Maestro[cite: 1]
    simulacion_externa = datos_sidebar.get("simulacion_externa", False)[cite: 1]
    supabase = st.session_state.get("supabase")[cite: 1]

    if simulacion_externa:[cite: 1]
        st.warning("⚠️ El módulo de gestión y control de entrenamientos está deshabilitado en Modo Simulación.")[cite: 1]
        return[cite: 1]

    # Restricción estricta de roles para el equipo técnico[cite: 1]
    if st.session_state.rol not in ["Head Coach", "Entrenador", "Administrador"]:[cite: 1]
        st.warning("🔒 Sección restringida al equipo técnico.")[cite: 1]
        return[cite: 1]

    # Definición e inicialización de las sub-pestañas internas exactas[cite: 1]
    subtab_crear, subtab_reportes = st.tabs(["✍️ Diseñar Menú del Día", "📊 Reportes e Historial"])[cite: 1]

    # =========================================================================
    # SUB-PESTAÑA 1: DISEÑO, DIFUSIÓN Y CONSOLIDACIÓN DIARIA[cite: 1]
    # =========================================================================
    with subtab_crear:[cite: 1]
        st.markdown("### 📋 Estructura del Entrenamiento de Hoy")[cite: 1]
        st.caption("Diseña la sesión agregando bloques. Al finalizar, controla la asistencia para imputar la carga individual.")[cite: 1]

        # Inicializar la pizarra en la memoria de sesión si no existe[cite: 1]
        if "pizarra_entrenamiento" not in st.session_state:[cite: 1]
            st.session_state.pizarra_entrenamiento = [][cite: 1]

        # Formulario de ingreso rápido de series[cite: 1]
        with st.expander("➕ Añadir nueva serie al entrenamiento", expanded=True):[cite: 1]
            c_rep, c_dist, c_est = st.columns(3)[cite: 1]
            with c_rep:[cite: 1]
                repeticiones = st.number_input("Repeticiones", min_value=1, value=1, step=1, key="piz_rep")[cite: 1]
            with c_dist:[cite: 1]
                distancia = st.number_input("Distancia (m)", min_value=15, value=100, step=25, key="piz_dist")[cite: 1]
            with c_est:[cite: 1]
                estilo = st.selectbox("Estilo / Foco", ["Libre", "Espalda", "Pecho", "Mariposa", "Combinado", "Piernas", "Brazos", "Técnica / Drills", "Afloje"], key="piz_est")[cite: 1]
                
            c_int, c_imp, c_not = st.columns(3)[cite: 1]
            with c_int:[cite: 1]
                intensidad = st.selectbox("Ritmo / Intensidad RPE", ["Suave (Aeróbico Ligero 3-4)", "Medio (Aeróbico Medio 5-6)", "Sostenido (Umbral 7-8)", "Ritmo de Competencia (Anaeróbico 9-10)", "Sprint (Máximo 10-11)"], key="piz_int")[cite: 1]
            with c_imp:[cite: 1]
                implementos = st.multiselect("Implementos", ["Aletas", "Paletas", "Tabla", "Pullbuoy", "Snorkel", "Paracaídas", "Ligas"], key="piz_imp")[cite: 1]
            with c_not:[cite: 1]
                notas = st.text_input("Instrucciones breves (Opcional)", placeholder="Ej: c/1:30 nado y descanso, Respiración c/3, Descanso 20s", key="piz_not")[cite: 1]

            if st.button("Añadir a la sesión", use_container_width=True, key="btn_add_piz"):[cite: 1]
                bloque = {[cite: 1]
                    "reps": repeticiones,[cite: 1]
                    "dist": distancia,[cite: 1]
                    "estilo": estilo,[cite: 1]
                    "intensidad": intensidad,[cite: 1]
                    "implementos": implementos,[cite: 1]
                    "notas": notas[cite: 1]
                }[cite: 1]
                st.session_state.pizarra_entrenamiento.append(bloque)[cite: 1]
                st.rerun()[cite: 1]

        # Visualización del entrenamiento acumulado en la sesión activa[cite: 1]
        if st.session_state.pizarra_entrenamiento:[cite: 1]
            st.markdown("---")[cite: 1]
            volumen_total = 0[cite: 1]
            fecha_difusion = st.session_state.get("piz_date_input_save", datetime.date.today())[cite: 1]
            carril_difusion = st.session_state.get("piz_carril_input_save", "")[cite: 1]
            
            # Reconstrucción dinámica del string para difusión[cite: 1]
            texto_exportacion = f"🏊‍♂️ *PLAN DE ENTRENAMIENTO DEL DÍA* - Fecha: {fecha_difusion.strftime('%d/%m/%Y') if hasattr(fecha_difusion, 'strftime') else fecha_difusion}\n"[cite: 1]
            if carril_difusion:[cite: 1]
                texto_exportacion += f"📍 *Grupo/Carril:* {carril_difusion}\n"[cite: 1]
            
            for idx, blk in enumerate(st.session_state.pizarra_entrenamiento, 1):[cite: 1]
                subtotal = blk['reps'] * blk['dist'][cite: 1]
                volumen_total += subtotal[cite: 1]
                txt_impl = f" [{', '.join(blk['implementos'])}]" if blk['implementos'] else ""[cite: 1]
                txt_not = f" - _{blk['notas']}_" if blk['notas'] else ""[cite: 1]
                texto_exportacion += f"• {blk['reps']} x {blk['dist']}m {blk['estilo']} | {blk['intensidad']}{txt_impl}{txt_not}\n"[cite: 1]

            texto_exportacion += f"\n📊 *Volumen Total:* {volumen_total:,} metros\n"[cite: 1]
            
            # Panel Informativo Visual y Métrica[cite: 1]
            st.info(texto_exportacion)[cite: 1]
            st.metric("Volumen Total de la Sesión", f"{volumen_total:,} metros")[cite: 1]
            
            c_undo, c_clear = st.columns(2)[cite: 1]
            with c_undo:[cite: 1]
                if st.button("⏪ Deshacer último bloque", use_container_width=True, key="piz_btn_undo"):[cite: 1]
                    st.session_state.pizarra_entrenamiento.pop()[cite: 1]
                    st.rerun()[cite: 1]
            with c_clear:[cite: 1]
                if st.button("🗑️ Limpiar pizarra completa", use_container_width=True, key="piz_btn_clear"):[cite: 1]
                    st.session_state.pizarra_entrenamiento = [][cite: 1]
                    st.rerun()[cite: 1]

            # =============================================================================
            # 📢 CENTRO DE DIFUSIÓN Y EXPORTACIÓN DE LA JORNADA[cite: 1]
            # =============================================================================
            st.markdown("---")[cite: 1]
            st.markdown("### 📢 Centro de Difusión y Publicación de la Pizarra")[cite: 1]
            st.caption("Genera el formato de communication para enviar a los atletas por canales digitales o preparar la hoja impresa.")[cite: 1]
            
            texto_url = urllib.parse.quote(texto_exportacion)[cite: 1]
            link_whatsapp = f"https://api.whatsapp.com/send?text={texto_url}"[cite: 1]
            link_correo = f"mailto:?subject=Plan%20de%20Entrenamiento%20{fecha_difusion}&body={texto_url}"[cite: 1]

            c_com1, c_com2, c_com3 = st.columns(3)[cite: 1]
            with c_com1:[cite: 1]
                st.link_button("🟢 Enviar por WhatsApp", link_whatsapp, use_container_width=True)[cite: 1]
            with c_com2:[cite: 1]
                st.link_button("📩 Enviar por Correo", link_correo, use_container_width=True)[cite: 1]
            with c_com3:[cite: 1]
                st.download_button([cite: 1]
                    label="🖨️ Descargar Hoja de Carril (TXT)",[cite: 1]
                    data=texto_exportacion.replace("*", ""),[cite: 1]
                    file_name=f"pizarra_{fecha_difusion}_{str(carril_difusion).replace(' ', '_') if carril_difusion else 'general'}.txt",[cite: 1]
                    mime="text/plain",[cite: 1]
                    use_container_width=True[cite: 1]
                )[cite: 1]

            with st.expander("👀 Ver vista previa del mensaje a enviar"):[cite: 1]
                st.code(texto_exportacion, language="markdown")[cite: 1]

            # =============================================================================
            # 🔍 SECCIÓN DE SEGMENTACIÓN (ASISTENCIA/CARGA)[cite: 1]
            # =============================================================================
            st.markdown("---")[cite: 1]
            st.markdown("### 🔍 Segmentación de Destinatarios (Asistencia/Carga)")[cite: 1]
            
            col_foto1, col_foto2 = st.columns(2)[cite: 1]
            with col_foto1:[cite: 1]
                filtro_genero = st.radio("Segmentar por Género:", options=["Todos", "Femenino (F)", "Masculino (M)"], horizontal=True, key="piz_radio_genero_idx")[cite: 1]
            with col_foto2:[cite: 1]
                tipo_filtro = st.radio("Segmentar adicionalmente por:", options=["Todos los Atletas", "Categoría Etaria", "Atletas Específicos"], horizontal=True, key="piz_radio_tipo_idx")[cite: 1]

            # Resolución del cliente Supabase activo[cite: 1]
            ctx_supabase = supabase if supabase else st.session_state.get("supabase_client")[cite: 1]
            atletas_pool = [][cite: 1]

            if ctx_supabase:[cite: 1]
                try:[cite: 1]
                    es_entrenador = st.session_state.get("rol") == "Entrenador"[cite: 1]
                    entrenador_id = st.session_state.get("usuario_id")[cite: 1]
                    permitir_consulta = True[cite: 1]
                    ids_autorizados = [][cite: 1]

                    if es_entrenador:[cite: 1]
                        if entrenador_id:[cite: 1]
                            resp_asig = ctx_supabase.table("asignaciones").select("atleta_id").eq("entrenador_id", entrenador_id).execute()[cite: 1]
                            if resp_asig.data:[cite: 1]
                                ids_autorizados = [reg["atleta_id"] for reg in resp_asig.data][cite: 1]
                            if not ids_autorizados:[cite: 1]
                                permitir_consulta = False[cite: 1]
                        else:[cite: 1]
                            st.error("❌ Error de sesión: No se encontró el ID del entrenador.")[cite: 1]
                            permitir_consulta = False[cite: 1]

                    if permitir_consulta:[cite: 1]
                        query_atletas = ctx_supabase.table("usuarios").select("id, nombre, email, genero, fecha_nacimiento").eq("rol", "Nadador").eq("estatus", "Activo")[cite: 1]
                        if es_entrenador:[cite: 1]
                            query_atletas = query_atletas.in_("id", ids_autorizados)[cite: 1]
                        
                        resp_sb = query_atletas.execute()[cite: 1]
                        if resp_sb.data:[cite: 1]
                            atletas_pool = resp_sb.data[cite: 1]
                    else:[cite: 1]
                        st.warning("⚠️ No tienes atletas asignados en tu perfil de Entrenador.")[cite: 1]
                except Exception as e:[cite: 1]
                    st.error(f"Error al cargar nómina desde Supabase: {e}")[cite: 1]

            # Filtrado por Género en memoria[cite: 1]
            if filtro_genero == "Femenino (F)":[cite: 1]
                atletas_pool = [a for a in atletas_pool if a.get("genero") == "F"][cite: 1]
            elif filtro_genero == "Masculino (M)":[cite: 1]
                atletas_pool = [a for a in atletas_pool if a.get("genero") == "M"][cite: 1]
          
            categorias_disponibles = sorted(list(set([[cite: 1]
                calcular_categoria_competencia(a["fecha_nacimiento"])[0][cite: 1]
                for a in atletas_pool if a.get("fecha_nacimiento")[cite: 1]
            ]))) if atletas_pool else [][cite: 1]

            dict_nom = {a["id"]: a["nombre"] for a in atletas_pool} if atletas_pool else {}[cite: 1]
            atletas_finales = [][cite: 1]

            if tipo_filtro == "Categoría Etaria":[cite: 1]
                cat_sel = st.selectbox("Seleccione la Categoría Etaria:", options=categorias_disponibles if categorias_disponibles else ["Cargando categorías activos..."], key="piz_selectbox_cat")[cite: 1]
                if categorias_disponibles:[cite: 1]
                    atletas_finales = [a for a in atletas_pool if calcular_categoria_competencia(a["fecha_nacimiento"])[0] == cat_sel][cite: 1]
            elif tipo_filtro == "Atletas Específicos":[cite: 1]
                ids_sel = st.multiselect("Seleccione Nadador(es) Individual(es):", options=list(dict_nom.keys()), format_func=lambda x: dict_nom.get(x, "Cargando atleta..."), key="piz_multiselect_atletas")[cite: 1]
                if ids_sel:[cite: 1]
                    atletas_finales = [a for a in atletas_pool if a["id"] in ids_sel][cite: 1]
            else:[cite: 1]
                atletas_finales = atletas_pool[cite: 1]

            if tipo_filtro == "Atletas Específicos" and not atletas_finales:[cite: 1]
                st.info("💡 Despliega el selector de arriba y marca al menos un nadador para habilitar el botón de consolidación.")[cite: 1]
            else:[cite: 1]
                st.success(f"🎯 Grupo confirmado para imputación: {len(atletas_finales)} atleta(s).")[cite: 1]

            # =============================================================================
            # 4. CONSOLIDACIÓN E IMPUTACIÓN HISTÓRICA EN BITÁCORA[cite: 1]
            # =============================================================================
            st.markdown("#### 💾 Consolidar y Registrar Jornada")[cite: 1]
            c_fecha, c_carril = st.columns(2)[cite: 1]
            with c_fecha:[cite: 1]
                fecha_jornada = st.date_input("Fecha de la sesión:", datetime.date.today(), key="piz_date_input_save")[cite: 1]
            with c_carril:[cite: 1]
                identificador_carril = st.text_input("Identificador / Carril (Opcional):", placeholder="Ej: Carril 3, Grupo Avanzado", key="piz_carril_input_save")[cite: 1]

            if st.button("💾 Consolidar Metros e Intensidades por Atleta", type="primary", use_container_width=True, key="btn_consolidar_piz"):[cite: 1]
                if atletas_finales:[cite: 1]
                    desglose_estilos = {}[cite: 1]
                    for blk in st.session_state.pizarra_entrenamiento:[cite: 1]
                        est = blk['estilo'][cite: 1]
                        mts = blk['reps'] * blk['dist'][cite: 1]
                        desglose_estilos[est] = desglose_estilos.get(est, 0) + mts[cite: 1]
                        
                    desglose_intensidad = {}[cite: 1]
                    for blk in st.session_state.pizarra_entrenamiento:[cite: 1]
                        inte = blk['intensidad'][cite: 1]
                        mts = blk['reps'] * blk['dist'][cite: 1]
                        desglose_intensidad[inte] = desglose_intensidad.get(inte, 0) + mts[cite: 1]

                    registros_supabase = [][cite: 1]
                    for at_obj in atletas_finales:[cite: 1]
                        fila = {[cite: 1]
                            "fecha": str(fecha_jornada),[cite: 1]
                            "atleta_id": at_obj.get("id"),[cite: 1]
                            "identificador_carril": identificador_carril if identificador_carril else "Carril Único",[cite: 1]
                            "metros_totales": int(volumen_total),[cite: 1]
                            "desglose_estilos": desglose_estilos,[cite: 1]
                            "desglose_intensidad": desglose_intensidad,[cite: 1]
                            "implementos_usados": list(set([imp for blk in st.session_state.pizarra_entrenamiento for imp in blk['implementos']])),[cite: 1]
                            # ✨ SOLUCIÓN HÍBRIDA: Salvamos el clon idéntico de la pizarra estructurada
                            "pizarra_original": st.session_state.pizarra_entrenamiento
                        }[cite: 1]
                        registros_supabase.append(fila)[cite: 1]

                    if registros_supabase and ctx_supabase:[cite: 1]
                        try:[cite: 1]
                            ctx_supabase.table("bitacora_entrenamientos").insert(registros_supabase).execute()[cite: 1]
                            
                            # 🧼 LIMPIEZA DE CACHÉ ESPECÍFICA DE STREAMLIT
                            st.cache_data.clear()
                            
                            st.success(f"💥 ¡Base de datos actualizada! Se grabaron con éxito las cargas individuales para los {len(registros_supabase)} atleta(s).")[cite: 1]
                            st.session_state.pizarra_entrenamiento = [][cite: 1]
                            st.balloons()[cite: 1]
                            st.rerun()[cite: 1]
                        except Exception as e:[cite: 1]
                            st.error(f"Error crítico al escribir en Supabase: {e}")[cite: 1]
                else:[cite: 1]
                    st.warning("⚠️ No hay atletas seleccionados en el grupo para consolidar.")[cite: 1]
        else:[cite: 1]
            st.info("💡 Diseña bloques en el formulario superior para inicializar la sesión del día.")[cite: 1]

    # =========================================================================
    # SUB-PESTAÑA 2: HISTORIAL Y DISTRIBUCIÓN FISIOLÓGICA[cite: 1]
    # =========================================================================
    with subtab_reportes:[cite: 1]
        st.markdown("### 📊 Historial y Distribución de Rutinas Consolidadas")[cite: 1]
        st.caption("Revisa el menú de entrenamientos de días anteriores basándose en la data consolidada del equipo técnico.")[cite: 1]

        ctx_supabase_rep = supabase if supabase else st.session_state.get("supabase_client")[cite: 1]

        if ctx_supabase_rep:[cite: 1]
            es_entrenador_rep = st.session_state.get("rol") == "Entrenador"[cite: 1]
            entrenador_id_rep = st.session_state.get("usuario_id")[cite: 1]
            
            permitir_consulta_rep = True[cite: 1]
            ids_autorizados_rep = [][cite: 1]

            if es_entrenador_rep:[cite: 1]
                if entrenador_id_rep:[cite: 1]
                    resp_asig_rep = ctx_supabase_rep.table("asignaciones").select("atleta_id").eq("entrenador_id", entrenador_id_rep).execute()[cite: 1]
                    if resp_asig_rep.data:[cite: 1]
                        ids_autorizados_rep = [reg["atleta_id"] for reg in resp_asig_rep.data][cite: 1]
                    if not ids_autorizados_rep:[cite: 1]
                        permitir_consulta_rep = False[cite: 1]
                else:[cite: 1]
                    st.error("❌ Error de sesión: No se detectó ID único de Entrenador.")[cite: 1]
                    permitir_consulta_rep = False[cite: 1]

            if permitir_consulta_rep:[cite: 1]
                try:[cite: 1]
                    c_b1, c_b2 = st.columns(2)[cite: 1]
                    with c_b1:[cite: 1]
                        f_desde = st.date_input("Buscar desde:", datetime.date.today() - datetime.timedelta(days=15), key="bib_f_desde")[cite: 1]
                    with c_b2:[cite: 1]
                        f_hasta = st.date_input("Hasta:", datetime.date.today(), key="bib_f_hasta")[cite: 1]

                    # ✨ Solicitamos explícitamente el nuevo campo pizarra_original en la query
                    query_records = ctx_supabase_rep.table("bitacora_entrenamientos").select("fecha, identificador_carril, metros_totales, desglose_estilos, desglose_intensidad, implementos_usados, atleta_id, pizarra_original").gte("fecha", str(f_desde)).lte("fecha", str(f_hasta))[cite: 1]
                    
                    if es_entrenador_rep and ids_autorizados_rep:[cite: 1]
                        query_records = query_records.in_("atleta_id", ids_autorizados_rep)[cite: 1]
                        
                    resp_bib = query_records.order("fecha", desc=True).execute()[cite: 1]

                    if resp_bib.data:[cite: 1]
                        # Agrupación por sesión única (Fecha y Carril)[cite: 1]
                        rutinas_unicas = {}[cite: 1]
                        for reg in resp_bib.data:[cite: 1]
                            llave = (reg["fecha"], reg["identificador_carril"])[cite: 1]
                            if llave not in rutinas_unicas:[cite: 1]
                                rutinas_unicas[llave] = reg[cite: 1]

                        st.markdown(f"#### 🔎 Rutinas encontradas ({len(rutinas_unicas)})")[cite: 1]
                        
                        for (fecha_sesion, carril_sesion), datos_sesion in rutinas_unicas.items():[cite: 1]
                            total_metros = datos_sesion.get('metros_totales', 0)[cite: 1]
                            with st.expander(f"📋 {fecha_sesion} | 📍 Grupo-Carril: {carril_sesion} | Volumen: {total_metros:,}m"):[cite: 1]
                                
                                # Reconstrucción del Plan[cite: 1]
                                texto_atleta = f"**PLAN DE ENTRENAMIENTO RECONSTRUIDO** - Fecha: {fecha_sesion}\n"[cite: 1]
                                if carril_sesion:[cite: 1]
                                    texto_atleta += f"📍 Grupo/Carril: {carril_sesion}\n"[cite: 1]
                                texto_atleta += f"📊 Volumen Total Consolidado: {total_metros:,} metros\n\n"[cite: 1]
                                
                                dict_estilos = datos_sesion.get("desglose_estilos", {})[cite: 1]
                                for est, mts in dict_estilos.items():[cite: 1]
                                    texto_atleta += f"• Bloque enfocado en {est}: total de {mts:,} metros.\n"[cite: 1]
                                
                                st.info(texto_atleta)[cite: 1]
                                
                                # Distribución Fisiológica Real en Pantalla[cite: 1]
                                st.markdown("#### 📉 Distribución Fisiológica")[cite: 1]
                                c_dist1, c_dist2 = st.columns(2)[cite: 1]
                                with c_dist1:[cite: 1]
                                    st.markdown("**Porcentaje por Estilo:**")[cite: 1]
                                    if dict_estilos:[cite: 1]
                                        datos_estilo_df = [{"Estilo / Foco": est, "Metros": mts, "%": f"{(mts/total_metros)*100:.1f}%"} for est, mts in dict_estilos.items()][cite: 1]
                                        st.dataframe(pd.DataFrame(datos_estilo_df), use_container_width=True, hide_index=True)[cite: 1]
                                with c_dist2:[cite: 1]
                                    st.markdown("**Porcentaje por Intensidad:**")[cite: 1]
                                    dict_intensidades = datos_sesion.get("desglose_intensidad", {})[cite: 1]
                                    if dict_intensidades:[cite: 1]
                                        datos_int_df = [{"Zona": inte.split("(")[0].strip(), "Metros": mts, "%": f"{(mts/total_metros)*100:.1f}%"} for inte, mts in dict_intensidades.items()][cite: 1]
                                        st.dataframe(pd.DataFrame(datos_int_df), use_container_width=True, hide_index=True)[cite: 1]

                                st.markdown("---")[cite: 1]
                                
                                # Panel de Acciones Auxiliares (Reutilización Segura)[cite: 1]
                                c_act1, c_act2 = st.columns(2)[cite: 1]
                                with c_act1:[cite: 1]
                                    # Extraemos la data de la columna híbrida
                                    pizarra_guardada = datos_sesion.get("pizarra_original")
                                    pizarra_vacia = len(st.session_state.get("pizarra_entrenamiento", [])) == 0
                                    
                                    # CONTROL DE RIESGOS: Evaluamos si hay datos activos para evitar accidentes
                                    if pizarra_vacia:
                                        label_boton = "🔄 Cargar como Plantilla en Pizarra"
                                        color_tipo = "secondary"
                                    else:
                                        label_boton = "⚠️ Reemplazar Pizarra Activa con esta Plantilla"
                                        color_tipo = "secondary"
                                        st.caption("🚨 _Nota: Cargar esta rutina borrará las series que estás editando hoy._")
                                        
                                    if st.button(label_boton, key=f"btn_tpl_{fecha_sesion}_{carril_sesion}", type=color_tipo, use_container_width=True):[cite: 1]
                                        
                                        # CAMINO A: El registro tiene la estructura JSONB completa (Nuevas Rutinas)
                                        if pizarra_guardada and isinstance(pizarra_guardada, list) and len(pizarra_guardada) > 0:
                                            st.session_state.pizarra_entrenamiento = pizarra_guardada
                                            st.success("¡Estructura de series exacta inyectada con éxito! Revisa la pestaña de diseño.")
                                        
                                        # CAMINO B: MECANISMO DE FALLBACK (Para tus 24 registros históricos de la captura)
                                        else:
                                            bloques_reconstruidos = [][cite: 1]
                                            for est, mts in dict_estilos.items():[cite: 1]
                                                bloques_reconstruidos.append({[cite: 1]
                                                    "reps": 1,[cite: 1]
                                                    "dist": int(mts),[cite: 1]
                                                    "estilo": est,[cite: 1]
                                                    "intensidad": "Medio (Aeróbico Medio 5-6)",[cite: 1]
                                                    "implementos": datos_sesion.get("implementos_usados", []),[cite: 1]
                                                    "notas": "" # Inyección limpia sin anotaciones cronológicas molestas[cite: 1]
                                                })[cite: 1]
                                            st.session_state.pizarra_entrenamiento = bloques_reconstruidos[cite: 1]
                                            st.warning("⚠️ Registro antiguo convertido: Se generó un bloque resumido por cada estilo.")
                                            
                                        st.rerun()[cite: 1]
                                        
                                with c_act2:[cite: 1]
                                    st.download_button([cite: 1]
                                        label="📋 Descargar Reporte (TXT)",[cite: 1]
                                        data=texto_atleta.replace("**", ""),[cite: 1]
                                        file_name=f"reporte_{fecha_sesion}.txt",[cite: 1]
                                        mime="text/plain",[cite: 1]
                                        key=f"dl_txt_{fecha_sesion}_{carril_sesion}",[cite: 1]
                                        use_container_width=True[cite: 1]
                                    )[cite: 1]
                    else:[cite: 1]
                        st.info("💡 No se encontraron rutinas registradas en el periodo seleccionado.")[cite: 1]
                except Exception as err:[cite: 1]
                    st.error(f"Error procesando biblioteca de rutinas: {err}")[cite: 1]
            else:[cite: 1]
                st.warning("⚠️ No posees atletas asignados en este momento bajo tu perfil de Entrenador.")[cite: 1]
