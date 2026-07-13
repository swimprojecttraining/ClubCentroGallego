import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# 📦 IMPORTACIONES NECESARIAS
from formulas_lib_funciones import resolver_k_individual, calcular_curva_atleta, formatear_a_minutos
from conections_supabase_cache import (
    obtener_marcas_referencia_cache, 
    obtener_historial_hitos_cache
)

def renderizar_tab_grafico(datos_sidebar):
    # =====================================================================
    # 1. EXTRACCIÓN Y DATOS DESDE CACHÉ
    # =====================================================================
    modo_equipo = datos_sidebar.get("modo_equipo", False)
    simulacion_externa = datos_sidebar.get("simulacion_externa", False)
    tipo_vista = datos_sidebar.get("tipo_vista", "Macro (Historial Completo)")
    
    # Datos de contexto para las consultas a Supabase
    prueba = datos_sidebar.get("prueba_seleccionada", "")
    genero = datos_sidebar.get("genero_atleta", "M")
    categoria = datos_sidebar.get("categoria_atleta", "")
    usuario_id = datos_sidebar.get("usuario_id")

    # Fetch de datos directo desde la cache (sin depender del sidebar)
    referencias_raw = obtener_marcas_referencia_cache(prueba, genero, categoria) if not simulacion_externa else []
    hitos_raw = obtener_historial_hitos_cache(usuario_id) if not simulacion_externa else []

    # =====================================================================
    # 2. LÓGICA DE DIBUJO (Usando subplots para evitar Segmentation Fault)
    # =====================================================================
    fig, ax = plt.subplots(figsize=(8, 10))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, pos: formatear_a_minutos(y)))
    
    # ... (Aquí iría tu lógica de cálculo de la curva y = ... ) ...
    # [Mantén tu lógica de calcular_curva_atleta aquí igual que antes]
    
    # =====================================================================
    # 3. LÍNEAS DE REFERENCIA (USANDO DATOS DE CACHÉ)
    # =====================================================================
    # Procesamos referencias_raw en lugar de datos_sidebar
    for ref in referencias_raw:
        val = float(ref.get("tiempo", 0))
        label = ref.get("nombre_marca", "Ref")
        ax.axhline(y=val, color="gray", linestyle=":", linewidth=0.6, alpha=0.7)
        ax.text(0.1, val, f"{label}: {formatear_a_minutos(val)}", fontsize=7, color="gray")

    # =====================================================================
    # 4. HITOS (SOLO MICRO)
    # =====================================================================
    if "Micro" in tipo_vista and hitos_raw:
        for hito in hitos_raw:
            # Asumiendo que el objeto hito tiene 'edad' y 'nombre'
            edad_h = float(hito.get("edad", 0))
            ax.axvline(x=edad_h, color="#2ECC71", linestyle="--", linewidth=0.7)
            ax.text(edad_h + 0.05, 0.5, hito.get("nombre", "Comp"), rotation=90, fontsize=7)

    # =====================================================================
    # 5. RENDERIZADO FINAL (CORRECCIÓN DE DEPRECACIÓN)
    # =====================================================================
    ax.set_title(datos_sidebar.get("titulo_grafico", "Proyección"))
    ax.grid(True, linestyle=':', alpha=0.6)
    
    # CORRECCIÓN DE DEPRECACIÓN:
    st.pyplot(fig, width='stretch')
