import streamlit as st
import pandas as pd
import datetime
import urllib.parse
import json
from formulas_lib_funciones import (
    calcular_categoria_competencia, 
    obtener_atletas_filtrados_supabase
)

def renderizar_tab_pizarra(datos_sidebar):
    """
    Controlador maestro: Orquesta la lógica sin fragmentación, 
    asegurando la persistencia del estado en st.session_state.
    """
    supabase = st.session_state.get("supabase")
    
    # 1. Seguridad: Acceso restringido a equipo técnico
    if st.session_state.rol not in ["Head Coach", "Entrenador", "Administrador"]:
        st.warning("🔒 Sección restringida.")
        return

    # 2. Inicialización de Estado (Pilar de la pizarra)
    if "pizarra_entrenamiento" not in st.session_state:
        st.session_state.pizarra_entrenamiento = []

    # 3. Router de pestañas interno
    subtab_crear, subtab_reportes = st.tabs(["✍️ Diseñar Menú del Día", "📊 Reportes e Historial"])

    with subtab_crear:
        _render_diseno_y_difusion()
    
    with subtab_reportes:
        _render_biblioteca_y_reportes(supabase)

# --- FIN DEL CAPITULO 1 ---
# --- CAPÍTULO 2: CAPA 1 - LÓGICA DE DISEÑO Y DIFUSIÓN ---

def _render_diseno_y_difusion():
    """
    Contiene la lógica exacta del original: 
    Formulario de series (c_rep, c_dist, c_est) y Módulo de Difusión.
    """
    st.markdown("### 📋 Estructura del Entrenamiento de Hoy")
    st.caption("Diseña la sesión agregando bloques. Al finalizar, controla la asistencia para imputar la carga.")

    # 1. Formulario de ingreso (Fidelidad total al original)
    with st.expander("➕ Añadir nueva serie al entrenamiento", expanded=True):
        c_rep, c_dist, c_est = st.columns(3)
        with c_rep: repeticiones = st.number_input("Repeticiones:", min_value=1, value=1)
        with c_dist: distancia = st.number_input("Distancia (m):", min_value=25, step=25, value=100)
        with c_est: estilo = st.selectbox("Estilo:", ["Libre", "Espalda", "Pecho", "Mariposa", "Variado"])
        
        ejercicio = st.text_input("Descripción / Ejercicio:")
        implementos = st.multiselect("Implementos:", ["Aletas", "Paletas", "Snorkel", "Tabla", "Pullbuoy"])
        
        if st.button("✅ Agregar a la Pizarra"):
            st.session_state.pizarra_entrenamiento.append({
                "rep": repeticiones, "dist": distancia, "est": estilo, 
                "ej": ejercicio, "implementos": implementos
            })
            st.rerun()

    # 2. Visualización y Gestión de la Pizarra
    if st.session_state.pizarra_entrenamiento:
        for idx, serie in enumerate(st.session_state.pizarra_entrenamiento):
            st.write(f"**{serie['rep']} x {serie['dist']}m {serie['est']}** - {serie['ej']} ({', '.join(serie['implementos'])})")
            if st.button(f"🗑️ Eliminar serie {idx + 1}", key=f"del_{idx}"):
                st.session_state.pizarra_entrenamiento.pop(idx)
                st.rerun()

        # 3. Módulo de Difusión (Irrenunciable)
        st.divider()
        st.markdown("#### 📤 Difusión del Entrenamiento")
        texto_rutina = "Rutina del Día:\n" + "\n".join([f"- {s['rep']}x{s['dist']}m {s['est']}" for s in st.session_state.pizarra_entrenamiento])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button("📥 Descargar TXT", data=texto_rutina, file_name="rutina.txt")
        with col2:
            st.link_button("💬 WhatsApp", url=f"https://wa.me/?text={urllib.parse.quote(texto_rutina)}")
        with col3:
            st.link_button("📧 Enviar Correo", url=f"mailto:?subject=Rutina&body={urllib.parse.quote(texto_rutina)}")
    else:
        st.info("La pizarra está vacía. ¡Agrega series para comenzar!")

# --- FIN DE LA CAPA 1 ---
# --- CAPÍTULO 3: CAPA 2 - MOTOR DE REHIDRATACIÓN Y BIBLIOTECA ---

def _render_biblioteca_y_reportes(supabase):
    """
    Motor de búsqueda histórica y rehidratación. 
    Limpia las notas cronológicas para inyectar una rutina pura al diseñador.
    """
    st.markdown("#### 🔍 Biblioteca de Rutinas")
    
    # 1. Filtro de búsqueda (Buscamos rutinas de los últimos 60 días)
    fecha_limite = (datetime.date.today() - datetime.timedelta(days=60)).isoformat()
    try:
        historial = supabase.table("pizarra_entrenamiento").select("*").gte("fecha", fecha_limite).order("fecha", desc=True).execute().data
        
        if historial:
            df_hist = pd.DataFrame(historial)
            # Selector de rutina para evitar el desorden de múltiples expanders
            seleccion = st.dataframe(
                df_hist[["fecha", "carril", "notas"]], 
                use_container_width=True, 
                selection_mode="single-row", 
                on_select="rerun"
            )
            
            if len(seleccion["selection"]["rows"]) > 0:
                idx = seleccion["selection"]["rows"][0]
                rutina_sel = historial[idx]
                
                st.divider()
                st.markdown(f"**Detalle de la rutina: {rutina_sel['fecha']} - {rutina_sel['carril']}**")
                st.json(rutina_sel.get("bloques", []))
                
                if st.button("🔄 Reinyectar al Diseñador"):
                    # MOTOR DE LIMPIEZA: Reconstrucción pura de bloques
                    bloques_reconstruidos = []
                    for bloque in rutina_sel.get("bloques", []):
                        bloques_reconstruidos.append({
                            "rep": bloque.get("rep"),
                            "dist": bloque.get("dist"),
                            "est": bloque.get("est"),
                            "ej": bloque.get("ej"),
                            "implementos": bloque.get("implementos", []),
                            "notas": "" # ✨ LIMPIEZA: Removida anotación cronológica
                        })
                    st.session_state.pizarra_entrenamiento = bloques_reconstruidos
                    st.success("¡Plan inyectado con éxito! Ve a 'Diseñar Menú del Día'.")
                    st.rerun()
        else:
            st.info("💡 No hay rutinas en el periodo seleccionado.")
            
    except Exception as err:
        st.error(f"Error procesando biblioteca: {err}")

# --- FIN DE LA CAPA 2 ---
# --- CAPÍTULO 4: CAPA 3 - CONSOLIDACIÓN FINAL E IMPUTACIÓN (VERSION FINAL) ---

def _render_consolidacion_final(supabase):
    """
    Gestiona la lógica de consolidación: Filtra atletas mediante 
    la biblioteca central y registra la carga en la bitácora.
    """
    st.divider()
    st.markdown("#### 💾 Consolidar y Registrar Jornada")
    
    # 1. Obtención del pool de atletas (Función desde formulas_lib_funciones)
    from formulas_lib_funciones import obtener_atletas_filtrados_supabase
    atletas_pool = obtener_atletas_filtrados_supabase()
    
    # 2. UI: Filtros de selección de atletas
    c_f1, c_f2 = st.columns(2)
    with c_f1:
        categorias = ["Todos"] + sorted(list(set(a.get('categoria', 'Sin Categoria') for a in atletas_pool)))
        filtro_cat = st.selectbox("Categoría:", categorias)
    with c_f2:
        carril_imputacion = st.text_input("Identificador de Carril:", "Carril 1")
    
    atletas_finales = [a for a in atletas_pool if filtro_cat == "Todos" or a.get('categoria') == filtro_cat]
    st.info(f"Atletas a imputar: {len(atletas_finales)}")

    # 3. Consolidación
    if st.button("🚀 Consolidar en Base de Datos"):
        if not st.session_state.pizarra_entrenamiento:
            st.error("La pizarra está vacía.")
            return
            
        # Cálculos de desglose (como en tu original)
        volumen_total = sum(blk['rep'] * blk['dist'] for blk in st.session_state.pizarra_entrenamiento)
        desglose_estilos = {}
        desglose_int = {}
        for blk in st.session_state.pizarra_entrenamiento:
            mts = blk['rep'] * blk['dist']
            desglose_estilos[blk['est']] = desglose_estilos.get(blk['est'], 0) + mts
            # Nota: Asegúrate de capturar 'intensidad' en tu formulario de Capa 1 si la necesitas aquí
        
        # Preparación de registros masivos
        registros = []
        for at in atletas_finales:
            registros.append({
                "atleta_id": at['id'],
                "fecha": str(datetime.date.today()),
                "identificador_carril": carril_imputacion,
                "metros_totales": int(volumen_total),
                "desglose_estilos": desglose_estilos,
                "desglose_intensidad": desglose_int,
                "implementos_usados": list(set([imp for blk in st.session_state.pizarra_entrenamiento for imp in blk['implementos']]))
            })
            
        try:
            supabase.table("bitacora_entrenamientos").insert(registros).execute()
            st.success(f"✅ Registro exitoso para {len(registros)} atletas.")
            st.session_state.pizarra_entrenamiento = []
            st.rerun()
        except Exception as e:
            st.error(f"Error en consolidación: {e}")

# --- FIN DE LA CAPA 3 ---
with subtab_crear:
        _render_diseno_y_difusion()      # Capa 1
        _render_consolidacion_final(supabase) # Capa 3