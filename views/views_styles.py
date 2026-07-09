# -------------------------------------------------------------
# REGLAS DE ESTILO CSS GLOBAL PARA LA INTERFAZ
# -------------------------------------------------------------
import streamlit as st

def aplicar_estilos_globales():
    st.markdown(
        """
    <style>
    /* === REMOVER EL ESPACIO EN BLANCO SUPERIOR (PADDING) === */
    .block-container {
        padding-top: 1rem !important;    /* Reduce el espacio superior al mínimo */
        padding-bottom: 0rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    
    /* Opcional: Si quieres pegar el título aún más arriba eliminando el margen del header invisible */
    stDecoration {
        display: none !important;
    }
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
        background-image: none !important;
        height: 2.5rem !important; /* Reduce la altura del header del sistema */
    }

    /* === TUS ESTILOS EXISTENTES === */
    div[data-testid="stMetricValue"] { font-size: 16px !important; }
    div[data-testid="stMetricLabel"] { font-size: 11px !important; }
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] .css-10trblm, section[data-testid="stSidebar"] h4 {
        font-size: 12px !important;
    }
    
/* === NUEVO ESQUEMA DE ESTILIZACIÓN GLOBAL PARA TODAS LAS TABLAS === */
    .stDataFrame div[data-testid="stTable"] table, table.dataframe, .tabla-estilizada {
        border-collapse: collapse !important;
        width: 100% !important;
        max-width: 100% !important; /* 🔥 Evita que el HTML empuje el borde derecho del teléfono */
        table-layout: auto !important; /* 🔥 Permite que las columnas se encojan de forma elástica */
        border: none !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }
    
    .stDataFrame div[data-testid="stTable"] th, table.dataframe th, .tabla-estilizada th {
        background-color: #F2F4F4 !important;  
        color: #2C3E50 !important;             
        font-weight: 600 !important;           
        padding: 6px 10px !important;          /* 🌟 Compactado para que no sature el móvil */
        border-top: 1px solid #111111 !important;    
        border-bottom: 1px solid #111111 !important; 
        border-left: none !important;
        border-right: none !important;
        font-size: 11px !important;            /* 🌟 Fuente reducida (de 13px a 11px) para que quepa en pantalla chica */
        text-align: center !important;
        white-space: nowrap !important;        /* 🔥 Evita que los encabezados hagan saltos de línea toscos */
    }
    
    .stDataFrame div[data-testid="stTable"] td, table.dataframe td, .tabla-estilizada td {
        padding: 6px 10px !important;          /* 🌟 Espaciado interno más bajo y móvil-friendly */
        border-bottom: 1px solid #E5E7E9 !important; 
        border-top: none !important;
        border-left: none !important;
        border-right: none !important;
        font-size: 11px !important;            /* 🌟 Datos balanceados */
        color: #34495E !important;
        text-align: center !important;
    }
    
    /* Resaltado especial elegante para la última fila de Totales o Resúmenes */
    table.dataframe tr:last-child td, .tabla-estilizada tr:last-child td {
        font-weight: bold !important;
        border-bottom: 2px solid #111111 !important;
        background-color: #FAFAFA !important;
    }

    /* === CONTROL DE MEDIOS: REGLAS EXCLUSIVAS PARA MÓVILES (PANTALLAS ANGOSTAS) === */
    @media screen and (max-width: 640px) {
        /* 🚨 ESCUDO ANTIDESBORDE GENERAL PARA EL HTML:
           Si la tabla histórica tiene muchas columnas (Edad, Tiempo, WA, Evento, Fecha) y no cabe horizontalmente,
           en vez de estirar y deformar la aplicación, mantendrá la app perfectamente encuadrada
           y le permitirá al usuario deslizar el dedo hacia los lados de forma fluida sobre la tabla. */
        .stDataFrame, .tabla-estilizada, div[data-testid="stTable"] {
            display: block !important;
            width: 100% !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch; /* Suaviza el deslizamiento en iPhones/Safari */
        }
        
        /* Ajuste opcional para las métricas: las apila verticalmente en celulares si se enciman */
        div[data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 8px !important;
        }
        div[data-testid="stMetric"] {
            width: 100% !important;
            padding: 4px 0px !important;
        }
    }
/* =================================================================
   🔥 BOTONES CSS FLUIDOS (ADAPTATIVOS)
   ================================================================= */

div[data-testid="stTabBar"] {
    background-color: transparent !important;
    border-bottom: 2px solid #E5E7E9 !important;
    padding: 0px 0px 8px 0px !important;       
    gap: 10px !important;                       
    margin-top: -10px !important;
    /* En móviles permite deslizar los botones horizontalmente si no caben */
    overflow-x: auto !important;
    display: flex !important;
    flex-wrap: nowrap !important;
}

button[data-testid="stTab"] {
    font-size: 13px !important;  
    font-weight: 600 !important;               
    color: #566573 !important;                 
    background-color: #F8F9F9 !important;      
    border: 1px solid #D5DBDB !important;      
    border-radius: 8px !important;             
    
    /* El botón se adapta al texto en lugar de tener un tamaño fijo */
    padding: 8px 16px !important;              
    white-space: nowrap !important;             /* Mantiene el texto limpio en una línea */
    flex-shrink: 0 !important;                  /* Evita que el móvil aplaste el botón */
    
    box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.05) !important;
    transition: all 0.2s ease !important;
}

button[data-testid="stTab"]:hover {
    background-color: #EBEDEF !important; 
    color: #1C2833 !important;            
    border-color: #AEB6BF !important;
    box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1) !important; 
    transform: translateY(-1px) !important;   
}

button[data-testid="stTab"][aria-selected="true"] {
    background-color: #2C3E50 !important; 
    color: #FFFFFF !important;            
    border-color: #2C3E50 !important;
    font-weight: bold !important;
    box-shadow: inset 0px 2px 4px rgba(0, 0, 0, 0.2), 0px 4px 6px rgba(0, 0, 0, 0.15) !important;
}

div[data-testid="stTabHighlight"] {
    background-color: transparent !important;
    display: none !important;
}

    @media print {
        .no-print { display: none !important; }
        .print-only { display: block !important; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

def spc():
    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
