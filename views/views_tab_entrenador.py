import streamlit as st
import pandas as pd

def renderizar_tab_entrenador(datos_sidebar=None):
    """
    CÓDIGO AUDITADO Y CORREGIDO: 15. Rutina de captura de marcas mínimas para asistir a eventos nacionales e internacionales.
    Garantiza consistencia absoluta en estados de bloqueo de inputs y control de duplicados en Supabase.
    """
    # 1. Validación de Roles de Seguridad Estricta
    rol_usuario = st.session_state.get("rol")
    if rol_usuario not in ["Head Coach", "Administrador"]:
        st.warning("🔒 Requiere credenciales de Head Coach.")
        return

    st.markdown("### ⚙️ Umbrales de Competencia para la Categoría")
    
    # 2. Recuperación de Contexto de Sesión
    supabase = st.session_state.get("supabase") # Contexto inyectado
    titulo_grafico = st.session_state.get("prueba_activa_seleccionada", "50m Libre")
    genero_atleta = st.session_state.get("nadador_seleccionado_genero")
    es_preinfantil = st.session_state.get("es_preinfantil", False)

    # 3. Evaluación de la Regla de Excepción para Pruebas Cortas o Preinfantiles
    pruebas_excluidas = ['25 Libre', '25 Espalda', '25 Pecho', '25 Mariposa', '100 Combinado']
    
    if titulo_grafico in pruebas_excluidas or es_preinfantil:
        st.info(f"💡 **Aviso:** Las marcas de referencia para pruebas Preinfantiles ({titulo_grafico}) se calculan automáticamente basándose en las marcas mínimas de 50m de la categoría Infantil A. No se configuran manualmente en este panel para proteger la integridad de los cálculos.")
        return

    # 4. Selector de Categoría Reglamentaria
    u_cat = st.selectbox("Categoría a Modificar u Organizar:", options=["Infantil A", "Infantil B", "Juvenil A", "Juvenil B", "Máxima"])
    
    db_m_ano, db_m_panam_b, db_m_panam_a, db_m_wa_b, db_m_wa_a, db_m_wr = None, None, None, None, None, None
    
    # Extracción y Precarga en Caliente desde marcas_referencia
    try:
        ref_dinamica = supabase.table("marcas_referencia").select("*")\
            .eq("prueba", titulo_grafico)\
            .eq("genero", genero_atleta)\
            .eq("categoria", u_cat).execute()
            
        if ref_dinamica.data:
            r_det = ref_dinamica.data[0]
            db_m_ano = float(r_det["m_ano"]) if r_det["m_ano"] is not None else None
            db_m_panam_b = float(r_det["m_panam_b"]) if r_det["m_panam_b"] is not None else None
            db_m_panam_a = float(r_det["m_panam_a"]) if r_det["m_panam_a"] is not None else None
            db_m_wa_b = float(r_det["m_wa_b"]) if r_det["m_wa_b"] is not None else None
            db_m_wa_a = float(r_det["m_wa_a"]) if r_det["m_wa_a"] is not None else None
            db_m_wr = float(r_det["m_wr"]) if r_det["m_wr"] is not None else None
    except Exception:
        pass

    # 5. Formulario de Captura con Bloqueo Nativo (Disabled) Verificado
    with st.form("form_update_referencias"):
        u_ano = st.number_input("Marca Mínima Año (seg):", value=db_m_ano if db_m_ano is not None else 0.0, disabled=(db_m_ano is None))
        u_panamb = st.number_input("PANAM Jr - Marca B (seg):", value=db_m_panam_b if db_m_panam_b is not None else 0.0, disabled=(db_m_panam_b is None))
        u_panama = st.number_input("PANAM Jr - Marca A (seg):", value=db_m_panam_a if db_m_panam_a is not None else 0.0, disabled=(db_m_panam_a is None))
        u_wab = st.number_input("World Aquatics - Marca B (seg):", value=db_m_wa_b if db_m_wa_b is not None else 0.0, disabled=(db_m_wa_b is None))
        u_waa = st.number_input("World Aquatics - Marca A (seg):", value=db_m_wa_a if db_m_wa_a is not None else 0.0, disabled=(db_m_wa_a is None))
        u_wr = st.number_input("Récord Mundial de Estilo Absoluto:", value=db_m_wr if db_m_wr is not None else 25.0, disabled=(db_m_wr is None))
        
        if st.form_submit_button("⚡ Guardar Configuración de Tiempos"):
            up_data = {}
            if db_m_ano is not None: up_data["m_ano"] = u_ano
            if db_m_panam_b is not None: up_data["m_panam_b"] = u_panamb
            if db_m_panam_a is not None: up_data["m_panam_a"] = u_panama
            if db_m_wa_b is not None: up_data["m_wa_b"] = u_wab
            if db_m_wa_a is not None: up_data["m_wa_a"] = u_waa
            if db_m_wr is not None: up_data["m_wr"] = u_wr
            
            if up_data:
                try:
                    # Inyección exacta respetando la restricción de llave única compuesta (on_conflict)
                    supabase.table("marcas_referencia").upsert({
                        "prueba": titulo_grafico, 
                        "genero": genero_atleta,
                        "categoria": u_cat, 
                        **up_data
                    }, on_conflict="prueba,genero,categoria").execute()
                    
                    st.success(f"Tiempos de referencia actualizados para {u_cat}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al guardar en base de datos: {e}")
