import streamlit as st
import pandas as pd
# Importamos la función directamente desde tu librería de fórmulas[cite: 2]
from formulas_lib_funciones import formatear_a_minutos, convertir_string_a_segundos, obtener_pruebas_por_categoria

# 1. Fragmento aislado para la selección rápida de categorías y pruebas
@st.fragment
def contenedor_seleccion_pruebas():
    # Selección de categoría
    u_cat = st.selectbox(
        "Categoría a Modificar u Organizar:", 
        options=["Infantil A", "Infantil B", "Juvenil A", "Juvenil B", "Máxima"],
        key="sb_categoria_entrenador"
    )
    
    # Llamada directa a tu función local en formulas_lib_funciones
    lista_pruebas_restringida = obtener_pruebas_por_categoria(u_cat)
    
    # Selección de la prueba activa
    prueba_local_activa = st.selectbox(
        f"🏊‍♂️ Seleccione la Prueba para {u_cat}:", 
        options=lista_pruebas_restringida,
        index=1 if len(lista_pruebas_restringida) > 1 else 0,
        key="sb_prueba_entrenador_ingreso"
    )
    
    # Guardamos en session_state para comunicarnos con el resto del archivo
    st.session_state["entrenador_cat_activa"] = u_cat
    st.session_state["entrenador_prueba_activa"] = prueba_local_activa


def renderizar_tab_entrenador():
    """
    CÓDIGO MODULAR EVOLUCIONADO.
    Indentación limpia corregida a 4 espacios planos para evitar fallos de despliegue.[cite: 2]
    Optimizado con @st.fragment usando las funciones nativas de formulas_lib_funciones.
    """
    global supabase
    if "supabase" in st.session_state and st.session_state.supabase:[cite: 2]
        supabase = st.session_state.supabase[cite: 2]
    else:
        st.error("❌ Conexión no inicializada en Session State.")[cite: 2]
        return[cite: 2]

    if st.session_state.get("rol") not in ["Head Coach", "Administrador"]:[cite: 2]
        st.warning("🔒 Requiere credenciales de Head Coach.")[cite: 2]
        return[cite: 2]

    st.markdown("### ⚙️ Umbrales de Competencia para la Categoría")[cite: 2]
    
    # 2. Renderizado veloz del fragmento
    contenedor_seleccion_pruebas()
    
    # Recuperamos las variables asignadas por el fragmento
    u_cat = st.session_state.get("entrenador_cat_activa", "Infantil A")
    titulo_grafico = st.session_state.get("entrenador_prueba_activa", "50 Libre")
    
    genero_atleta = st.session_state.get("nadador_seleccionado_genero", "F")[cite: 2]
    es_preinfantil = st.session_state.get("es_preinfantil", False)[cite: 2]

    # Control de exclusiones basado en la prueba activa elegida en el fragmento
    pruebas_excluidas = ['25 Libre', '25 Espalda', '25 Pecho', '25 Mariposa', '100 Combinado'][cite: 2]
    if titulo_grafico in pruebas_excluidas or es_preinfantil:[cite: 2]
        st.info(f"💡 **Aviso:** Las marcas de referencia para pruebas Preinfantiles ({titulo_grafico}) se calculan automáticamente.")[cite: 2]
        return[cite: 2]
    
    db_m_ano, db_m_panam_b, db_m_panam_a, db_m_wa_b, db_m_wa_a, db_m_wr = None, None, None, None, None, None[cite: 2]
    
    try:
        ref_dinamica = supabase.table("marcas_referencia").select("*").eq("prueba", titulo_grafico).eq("genero", genero_atleta).eq("categoria", u_cat).execute()[cite: 2]
        if ref_dinamica.data:[cite: 2]
            r_det = ref_dinamica.data[0][cite: 2]
            db_m_ano = float(r_det["m_ano"]) if r_det["m_ano"] is not None else None[cite: 2]
            db_m_panam_b = float(r_det["m_panam_b"]) if r_det["m_panam_b"] is not None else None[cite: 2]
            db_m_panam_a = float(r_det["m_panam_a"]) if r_det["m_panam_a"] is not None else None[cite: 2]
            db_m_wa_b = float(r_det["m_wa_b"]) if r_det["m_wa_b"] is not None else None[cite: 2]
            db_m_wa_a = float(r_det["m_wa_a"]) if r_det["m_wa_a"] is not None else None[cite: 2]
            db_m_wr = float(r_det["m_wr"]) if r_det["m_wr"] is not None else None[cite: 2]
    except Exception as e:
        st.caption(f"Nota en precarga: {e}")[cite: 2]

    st.caption(f"📋 Configurando tiempos para **{titulo_grafico}** ({'Femenino' if genero_atleta == 'F' else 'Masculino'})")[cite: 2]

    with st.form("form_update_referencias"):[cite: 2]
        st.write("✍️ *Ingrese los tiempos en formato `mm:ss.hh` o segundos decimales*")[cite: 2]
        
        col1, col2 = st.columns(2)[cite: 2]
        with col1:[cite: 2]
            in_ano = st.text_input("Marca Mínima Año (mm:ss.hh):", value=formatear_a_minutos(db_m_ano))[cite: 2]
            in_panamb = st.text_input("PANAM Jr - Marca B (mm:ss.hh):", value=formatear_a_minutos(db_m_panam_b))[cite: 2]
            in_panama = st.text_input("PANAM Jr - Marca A (mm:ss.hh):", value=formatear_a_minutos(db_m_panam_a))[cite: 2]
        with col2:[cite: 2]
            in_wab = st.text_input("World Aquatics - Marca B (mm:ss.hh):", value=formatear_a_minutos(db_m_wa_b))[cite: 2]
            in_waa = st.text_input("World Aquatics - Marca A (mm:ss.hh):", value=formatear_a_minutos(db_m_wa_a))[cite: 2]
            in_wr = st.text_input("Récord Mundial Absoluto (mm:ss.hh):", value=formatear_a_minutos(db_m_wr) if db_m_wr is not None else "25.00")[cite: 2]
        
        if st.form_submit_button("⚡ Guardar Configuración de Tiempos"):[cite: 2]
            try:
                u_ano = convertir_string_a_segundos(in_ano) if in_ano != "0.00" else None[cite: 2]
                u_panamb = convertir_string_a_segundos(in_panamb) if in_panamb != "0.00" else None[cite: 2]
                u_panama = convertir_string_a_segundos(in_panama) if in_panama != "0.00" else None[cite: 2]
                u_wab = convertir_string_a_segundos(in_wab) if in_wab != "0.00" else None[cite: 2]
                u_waa = convertir_string_a_segundos(in_waa) if in_waa != "0.00" else None[cite: 2]
                u_wr = convertir_string_a_segundos(in_wr) if in_wr != "0.00" else None[cite: 2]
                
                up_data = {}[cite: 2]
                if u_ano is not None: up_data["m_ano"] = u_ano[cite: 2]
                if u_panamb is not None: up_data["m_panam_b"] = u_panamb[cite: 2]
                if u_panama is not None: up_data["m_panam_a"] = u_panama[cite: 2]
                if u_wab is not None: up_data["m_wa_b"] = u_wab[cite: 2]
                if u_waa is not None: up_data["m_wa_a"] = u_waa[cite: 2]
                if u_wr is not None: up_data["m_wr"] = u_wr[cite: 2]
                
                if up_data:[cite: 2]
                    supabase.table("marcas_referencia").upsert({[cite: 2]
                        "prueba": titulo_grafico, [cite: 2]
                        "genero": genero_atleta,[cite: 2]
                        "categoria": u_cat, [cite: 2]
                        **up_data[cite: 2]
                    }, on_conflict="prueba,genero,categoria").execute()[cite: 2]
                    
                    st.success(f"🎉 Tiempos procesados y guardados con éxito para la categoría {u_cat}.")[cite: 2]
                    st.rerun()[cite: 2]
                else:
                    st.warning("⚠️ No se detectaron cambios numéricos válidos.")[cite: 2]
            except Exception as e:
                st.error(f"❌ Error al procesar o guardar los tiempos: {e}")[cite: 2]
