import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Horas de Equipo",
    page_icon="⏱️",
    layout="wide"
)

# Estilo personalizado
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

def generate_sample_data():
    """Genera datos de ejemplo si no se sube un archivo"""
    nombres = ['Ana García', 'Carlos Ruiz', 'Elena Beltrán', 'David Lyon', 'Sofía Vega']
    proyectos = ['Proyecto Alfa', 'Proyecto Beta', 'Mantenimiento', 'Reuniones']
    fechas = pd.date_range(start='2023-10-01', end='2023-10-31', freq='D')
    
    data = []
    for fecha in fechas:
        for nombre in nombres:
            import random
            if random.random() > 0.2:
                data.append({
                    'Fecha': fecha,
                    'Nombre': nombre,
                    'Proyecto': random.choice(proyectos),
                    'Horas': random.uniform(2, 8),
                })
    return pd.DataFrame(data)

def main():
    st.title("⏱️ Dashboard de Horas del Equipo")
    
    st.sidebar.header("1. Carga de Archivo")
    uploaded_file = st.sidebar.file_uploader("Sube tu archivo Excel o CSV", type=["xlsx", "csv"])

    if uploaded_file is not None:
        try:
            # Opción vital para reportes exportados con títulos arriba
            st.sidebar.markdown("---")
            st.sidebar.subheader("2. Ajuste de Lectura")
            skip_rows = st.sidebar.number_input(
                "¿Cuántas filas de encabezado saltar?", 
                min_value=0, value=0, 
                help="Aumenta este número si tu Excel tiene títulos antes de la tabla real. Para tu archivo, intenta poner 11 o 12."
            )
            
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, skiprows=skip_rows)
            else:
                df = pd.read_excel(uploaded_file, skiprows=skip_rows)
            
            # Limpiar nombres de columnas (quitar espacios extra)
            df.columns = df.columns.astype(str).str.strip()
            
            # Mostrar la tabla en bruto para ayudar al usuario a configurar
            with st.expander("👀 Ver datos en bruto (¿Se está leyendo bien la tabla?)", expanded=True):
                st.markdown("Así es como el sistema lee tu archivo. Si las columnas no tienen sentido, ajusta el número de **filas a saltar** en la barra lateral.")
                st.dataframe(df.head(10))

            # Mapeo dinámico de columnas
            st.sidebar.markdown("---")
            st.sidebar.subheader("3. Asignar Columnas")
            st.sidebar.markdown("Indica qué columna de tu archivo corresponde a cada dato:")
            
            opciones_columnas = ["--- No usar ---"] + list(df.columns)
            
            col_nombre = st.sidebar.selectbox("👤 Columna de Nombre/Empleado", opciones_columnas, index=0)
            col_horas = st.sidebar.selectbox("⏱️ Columna de Horas", opciones_columnas, index=0)
            col_proyecto = st.sidebar.selectbox("📁 Columna de Proyecto (Opcional)", opciones_columnas, index=0)
            col_fecha = st.sidebar.selectbox("📅 Columna de Fecha (Opcional)", opciones_columnas, index=0)

            # Verificar si se seleccionaron las obligatorias
            if col_nombre != "--- No usar ---" and col_horas != "--- No usar ---":
                
                # Preparar DataFrame final limpiando nulos en las horas
                df_final = df.copy()
                df_final[col_horas] = pd.to_numeric(df_final[col_horas], errors='coerce').fillna(0)
                
                # --- MÉTRICAS ---
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                total_horas = df_final[col_horas].sum()
                num_personas = df_final[col_nombre].nunique()
                
                col1.metric("Total Horas", f"{total_horas:.1f}h")
                col2.metric("Miembros del Equipo", num_personas)
                
                if col_proyecto != "--- No usar ---":
                    col3.metric("Proyectos Distintos", df_final[col_proyecto].nunique())

                # --- GRÁFICOS ---
                st.markdown("### Resumen Gráfico")
                row1_col1, row1_col2 = st.columns(2)

                with row1_col1:
                    fig_names = px.bar(
                        df_final.groupby(col_nombre)[col_horas].sum().reset_index().sort_values(by=col_horas, ascending=False),
                        x=col_nombre, y=col_horas, color=col_nombre,
                        title="Horas Totales por Persona", text_auto='.1f', template="plotly_white"
                    )
                    st.plotly_chart(fig_names, use_container_width=True)

                if col_proyecto != "--- No usar ---":
                    with row1_col2:
                        fig_pie = px.pie(
                            df_final.groupby(col_proyecto)[col_horas].sum().reset_index(),
                            values=col_horas, names=col_proyecto, hole=0.4,
                            title="Distribución de Horas por Proyecto", template="plotly_white"
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)

                # Gráfico de fecha solo si se seleccionó una columna
                if col_fecha != "--- No usar ---":
                    try:
                        df_final[col_fecha] = pd.to_datetime(df_final[col_fecha], errors='coerce')
                        df_time = df_final.dropna(subset=[col_fecha]).groupby(df_final[col_fecha].dt.date)[col_horas].sum().reset_index()
                        
                        fig_line = px.line(
                            df_time, x=col_fecha, y=col_horas, markers=True,
                            title="Evolución Temporal de Horas", template="plotly_white"
                        )
                        st.plotly_chart(fig_line, use_container_width=True)
                    except:
                        st.warning("⚠️ No se pudo procesar la columna de fecha como un formato de calendario válido.")

            else:
                st.warning("👈 Por favor, selecciona en la barra lateral al menos las columnas de **Nombre** y **Horas** para generar los gráficos.")

        except Exception as e:
            st.error(f"Error técnico al procesar: {e}")
            
    else:
        # Si no hay archivo, mostrar demo
        st.info("💡 Modo de demostración activo. Sube tu archivo a la izquierda para analizar tus datos.")
        df = generate_sample_data()
        st.dataframe(df.head()) # Muestra pequeña tabla demo

if __name__ == "__main__":
    main()
