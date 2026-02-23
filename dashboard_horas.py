import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

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
    """, unsafe_allow_stdio=True)

def generate_sample_data():
    """Genera datos de ejemplo si no se sube un archivo"""
    nombres = ['Ana García', 'Carlos Ruiz', 'Elena Beltrán', 'David Lyon', 'Sofía Vega']
    proyectos = ['Proyecto Alfa', 'Proyecto Beta', 'Mantenimiento', 'Reuniones']
    fechas = pd.date_range(start='2023-10-01', end='2023-10-31', freq='D')
    
    data = []
    for fecha in fechas:
        for nombre in nombres:
            import random
            if random.random() > 0.2: # Simular que no todos trabajan todos los días
                data.append({
                    'Fecha': fecha,
                    'Nombre': nombre,
                    'Proyecto': random.choice(proyectos),
                    'Horas': random.uniform(2, 8),
                    'Descripción': 'Tarea estándar'
                })
    return pd.DataFrame(data)

def main():
    st.title("⏱️ Dashboard de Horas del Equipo")
    st.markdown("Carga tu archivo Excel para analizar el rendimiento y la distribución del tiempo.")

    # Sidebar - Carga de Archivo
    st.sidebar.header("Configuración")
    uploaded_file = st.sidebar.file_uploader("Sube tu archivo Excel o CSV", type=["xlsx", "csv"])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Asegurar formato de fecha
            df['Fecha'] = pd.to_datetime(df['Fecha'])
            st.sidebar.success("¡Archivo cargado con éxito!")
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
            return
    else:
        st.info("💡 Usando datos de ejemplo. Sube tu propio archivo en la barra lateral para personalizar.")
        df = generate_sample_data()

    # --- FILTROS ---
    st.sidebar.subheader("Filtros de Datos")
    
    # Filtro de fecha
    min_date = df['Fecha'].min().to_pydatetime()
    max_date = df['Fecha'].max().to_pydatetime()
    date_range = st.sidebar.date_input("Rango de fechas", [min_date, max_date])

    # Filtro de Nombre
    all_names = ["Todos"] + list(df['Nombre'].unique())
    selected_name = st.sidebar.selectbox("Miembro del equipo", all_names)

    # Filtro de Proyecto
    all_projects = ["Todos"] + list(df['Proyecto'].unique())
    selected_project = st.sidebar.selectbox("Proyecto", all_projects)

    # Aplicar filtros
    mask = (df['Fecha'].dt.date >= date_range[0]) & (df['Fecha'].dt.date <= date_range[1])
    if selected_name != "Todos":
        mask &= (df[ 'Nombre'] == selected_name)
    if selected_project != "Todos":
        mask &= (df['Proyecto'] == selected_project)
    
    df_filtered = df[mask]

    # --- MÉTRICAS ---
    col1, col2, col3, col4 = st.columns(4)
    
    total_horas = df_filtered['Horas'].sum()
    promedio_diario = total_horas / len(df_filtered['Fecha'].unique()) if not df_filtered.empty else 0
    num_personas = df_filtered['Nombre'].nunique()
    num_proyectos = df_filtered['Proyecto'].nunique()

    with col1:
        st.metric("Total Horas", f"{total_horas:.1f}h")
    with col2:
        st.metric("Promedio Diario", f"{promedio_diario:.1f}h")
    with col3:
        st.metric("Miembros Activos", num_personas)
    with col4:
        st.metric("Proyectos", num_proyectos)

    st.markdown("---")

    # --- GRÁFICOS ---
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        st.subheader("Horas por Miembro del Equipo")
        fig_names = px.bar(
            df_filtered.groupby('Nombre')['Horas'].sum().reset_index(),
            x='Nombre',
            y='Horas',
            color='Nombre',
            text_auto='.1f',
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        st.plotly_chart(fig_names, use_container_width=True)

    with row1_col2:
        st.subheader("Distribución por Proyecto")
        fig_pie = px.pie(
            df_filtered.groupby('Proyecto')['Horas'].sum().reset_index(),
            values='Horas',
            names='Proyecto',
            hole=0.4,
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("Evolución Temporal de Horas")
    df_time = df_filtered.groupby(df_filtered['Fecha'].dt.date)['Horas'].sum().reset_index()
    fig_line = px.line(
        df_time,
        x='Fecha',
        y='Horas',
        markers=True,
        template="plotly_white",
        line_shape="spline"
    )
    fig_line.update_traces(line_color='#1f77b4')
    st.plotly_chart(fig_line, use_container_width=True)

    # --- TABLA DE DATOS ---
    with st.expander("Ver tabla de datos detallada"):
        st.dataframe(df_filtered.sort_values(by='Fecha', ascending=False), use_container_width=True)
        
        # Opción de descarga
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar reporte filtrado (CSV)",
            data=csv,
            file_name='reporte_horas_filtrado.csv',
            mime='text/csv',
        )

if __name__ == "__main__":
    main()