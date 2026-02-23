import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Dinámico de Excel",
    page_icon="📊",
    layout="wide"
)

# Estilo personalizado
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(show_spinner="Analizando archivo...")
def procesar_archivo(uploaded_file):
    """Lee el archivo y detecta automáticamente dónde empieza la tabla real"""
    try:
        # Leemos las primeras 50 líneas para entender la estructura
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None, nrows=50)
        else:
            df_raw = pd.read_excel(uploaded_file, header=None, nrows=50)
            
        # Buscamos la fila que tenga la mayor cantidad de columnas con datos
        # (Esto suele ser la fila de los encabezados reales de la tabla)
        header_idx = 0
        max_cols = 0
        for i, row in df_raw.iterrows():
            non_nulls = row.notna().sum()
            if non_nulls > max_cols:
                max_cols = non_nulls
                header_idx = i
                
        # Reiniciamos el archivo y leemos saltando las filas de títulos superiores
        uploaded_file.seek(0)
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, skiprows=header_idx)
        else:
            df = pd.read_excel(uploaded_file, skiprows=header_idx)
            
        # Limpiamos los nombres de las columnas de caracteres raros (como flechas) y espacios
        df.columns = df.columns.astype(str).str.replace('↑', '').str.replace('→', '').str.strip()
        
        # Eliminamos columnas que estén 100% vacías
        df = df.dropna(how='all', axis=1)
        
        # Convertimos a numérico lo que parezca número (para que los gráficos funcionen)
        for col in df.columns:
            try:
                # Intenta convertir a número ignorando los errores en textos
                df_numeric = pd.to_numeric(df[col], errors='coerce')
                # Si al menos el 20% de la columna son números, la consideramos numérica
                if df_numeric.notna().mean() > 0.2:
                    df[col] = df_numeric
            except:
                pass
                
        return df
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return pd.DataFrame()

def main():
    st.title("📊 Dashboard Dinámico de Datos")
    st.markdown("Carga tu archivo y el sistema detectará automáticamente tus columnas.")
    
    st.sidebar.header("📁 Carga de Archivo")
    uploaded_file = st.sidebar.file_uploader("Sube tu archivo Excel o CSV", type=["xlsx", "csv"])

    if uploaded_file is not None:
        # 1. Cargar datos inteligentemente
        df = procesar_archivo(uploaded_file)
        
        if df.empty:
            return

        # 2. Mostrar la tabla real extraída
        st.subheader("📋 Datos Extraídos de tu Archivo")
        st.markdown(f"Se encontraron **{len(df)} filas** y **{len(df.columns)} columnas** útiles.")
        st.dataframe(df, use_container_width=True)

        st.markdown("---")
        
        # 3. Graficador dinámico basado en las columnas que EXISTEN
        st.subheader("📈 Analiza tus Datos")
        
        # Separar columnas por tipo para facilitar la selección
        cols_texto = df.select_dtypes(include=['object', 'string']).columns.tolist()
        cols_numeros = df.select_dtypes(include=['number']).columns.tolist()
        
        # Si pandas no detectó bien los tipos, usamos todas
        if not cols_texto: cols_texto = list(df.columns)
        if not cols_numeros: cols_numeros = list(df.columns)

        # Buscar valores por defecto lógicos para tu archivo específico
        def_agrupar = next((c for c in cols_texto if 'name' in c.lower() or 'nombre' in c.lower()), cols_texto[0])
        def_graficar = [c for c in cols_numeros if 'hour' in c.lower() or 'hora' in c.lower()]
        
        col1, col2 = st.columns(2)
        with col1:
            col_agrupar = st.selectbox(
                "1. Agrupar datos por (Ej: Nombres, Proyectos):", 
                cols_texto, 
                index=cols_texto.index(def_agrupar) if def_agrupar in cols_texto else 0
            )
        with col2:
            cols_graficar = st.multiselect(
                "2. Valores a sumar y graficar (Ej: Horas Totales):", 
                cols_numeros,
                default=def_graficar if def_graficar else [cols_numeros[-1]]
            )

        # Si el usuario seleccionó qué graficar
        if col_agrupar and cols_graficar:
            # Agrupar y sumar
            df_grouped = df.groupby(col_agrupar)[cols_graficar].sum().reset_index()
            
            # Limpiar filas de "Subtotales" que los reportes suelen traer al final
            df_grouped = df_grouped[~df_grouped[col_agrupar].astype(str).str.contains('Subtotal|Total', case=False, na=False)]
            
            # Mostrar métricas rápidas de lo que seleccionó
            st.markdown("### Resumen")
            metric_cols = st.columns(len(cols_graficar))
            for i, col_num in enumerate(cols_graficar):
                total = df_grouped[col_num].sum()
                metric_cols[i].metric(f"Total {col_num}", f"{total:,.2f}")

            # Mostrar Gráfico
            fig = px.bar(
                df_grouped.sort_values(by=cols_graficar[0], ascending=False), 
                x=col_agrupar, 
                y=cols_graficar,
                barmode='group',
                template="plotly_white",
                title=f"Suma de valores por {col_agrupar}"
            )
            fig.update_layout(legend_title_text='Métricas')
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("👈 Sube tu archivo a la izquierda para comenzar.")

if __name__ == "__main__":
    main()
