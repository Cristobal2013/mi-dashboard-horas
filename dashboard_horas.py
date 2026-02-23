import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Ejecutivo de Horas",
    page_icon="💼",
    layout="wide"
)

# Estilo personalizado para un look más "Ejecutivo"
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    h1, h2, h3 { color: #2c3e50; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stMetric {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #2980b9;
    }
    .stMetric label { color: #7f8c8d !important; font-size: 16px !important; font-weight: 600; }
    .stMetric [data-testid="stMetricValue"] { color: #2c3e50; font-size: 32px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(show_spinner="Analizando estructura del reporte...")
def procesar_archivo_ejecutivo(uploaded_file):
    """Lógica avanzada para leer reportes matriciales (ej. exportaciones de Salesforce)"""
    try:
        is_csv = uploaded_file.name.endswith('.csv')
        
        # 1. Leer primeras líneas para encontrar dónde empieza la tabla
        if is_csv:
            df_raw = pd.read_csv(uploaded_file, header=None, nrows=30)
        else:
            df_raw = pd.read_excel(uploaded_file, header=None, nrows=30)
            
        header_idx = 0
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains('Owner Name|Nombre', case=False, na=False).any():
                header_idx = i
                break
                
        # 2. Verificar si es un reporte con doble encabezado (Work Type arriba, Métricas abajo)
        is_multi = False
        if header_idx > 0:
            prev_row = df_raw.iloc[header_idx - 1].astype(str).str.lower()
            if prev_row.str.contains('work type|billable|tipo').any():
                is_multi = True
                
        uploaded_file.seek(0)
        
        # 3. Leer y aplanar encabezados (Ej: convierte "Billable" y "Hours" a "Billable - Hours")
        if is_multi:
            if is_csv:
                df = pd.read_csv(uploaded_file, skiprows=header_idx-1, header=[0, 1])
            else:
                df = pd.read_excel(uploaded_file, skiprows=header_idx-1, header=[0, 1])
            
            cols_l0 = pd.Series(df.columns.get_level_values(0)).replace(r'^Unnamed:.*', pd.NA, regex=True).ffill()
            cols_l1 = df.columns.get_level_values(1)
            
            new_cols = []
            for c0, c1 in zip(cols_l0, cols_l1):
                c0_clean = str(c0).replace('→', '').replace('↑', '').strip()
                c1_clean = str(c1).replace('→', '').replace('↑', '').strip()
                
                if pd.isna(c0) or c0_clean == '' or 'unnamed' in c0_clean.lower() or c0_clean.lower() == c1_clean.lower():
                    new_cols.append(c1_clean)
                else:
                    new_cols.append(f"{c0_clean} - {c1_clean}")
            df.columns = new_cols
        else:
            if is_csv:
                df = pd.read_csv(uploaded_file, skiprows=header_idx)
            else:
                df = pd.read_excel(uploaded_file, skiprows=header_idx)
            df.columns = df.columns.astype(str).str.replace('↑', '').str.replace('→', '').str.strip()
            
        # 4. Limpieza final de datos
        df = df.dropna(how='all', axis=1) # Quitar columnas 100% vacías
        
        owner_col = next((c for c in df.columns if 'owner name' in c.lower() or 'nombre' in c.lower()), None)
        if owner_col:
            # Eliminar filas de "Subtotal" y "Total" que ensucian los gráficos
            df = df[~df[owner_col].astype(str).str.contains('Subtotal|Total', case=False, na=False)]
            df = df.dropna(subset=[owner_col])
            
        # Convertir todo lo que sea número a formato numérico real
        for col in df.columns:
            try:
                df_numeric = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
                if df_numeric.notna().mean() > 0.05:
                    df[col] = df_numeric.fillna(0)
            except:
                pass
                
        return df, owner_col
    except Exception as e:
        st.error(f"Error procesando archivo: {e}")
        return pd.DataFrame(), None

def main():
    st.title("💼 Dashboard Ejecutivo de Rendimiento")
    st.markdown("Visualización de **Team Utilization**, **Billable** y **Non-Billable** extraídos automáticamente de tu reporte.")
    
    st.sidebar.header("📁 Carga de Reporte")
    uploaded_file = st.sidebar.file_uploader("Sube tu exportación (Excel o CSV)", type=["xlsx", "csv"])

    if uploaded_file is not None:
        df, owner_col = procesar_archivo_ejecutivo(uploaded_file)
        
        if df.empty or not owner_col:
            st.error("No se encontraron datos válidos. Asegúrate de que el archivo contiene la columna 'Owner Name'.")
            return

        # --- AUTO-DETECCIÓN DE MÉTRICAS CLAVE ---
        # Buscar la columna de Utilización Total (Generalmente "Total - Team Utilization")
        col_utilization = next((c for c in df.columns if 'total - team utilization' in c.lower()), None)
        if not col_utilization:
            col_utilization = next((c for c in df.columns if 'team utilization' in c.lower()), None)

        # Buscar columnas Billable / Non-Billable (Generalmente "Billable - Total Billable Hours")
        col_billable = next((c for c in df.columns if 'billable - total' in c.lower() and 'non' not in c.lower()), None)
        col_non_billable = next((c for c in df.columns if 'non-billable - total' in c.lower()), None)
        
        # Fallbacks por si cambian de nombre en el Excel
        if not col_billable: col_billable = next((c for c in df.columns if 'billable' in c.lower() and 'non' not in c.lower() and 'hour' in c.lower()), None)
        if not col_non_billable: col_non_billable = next((c for c in df.columns if 'non-billable' in c.lower() and 'hour' in c.lower()), None)

        # --- SECCIÓN: KPIs EJECUTIVOS ---
        st.markdown("### 📊 Indicadores Clave del Equipo")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_empleados = df[owner_col].nunique()
            st.metric("Miembros del Equipo", total_empleados)
            
        with col2:
            if col_utilization:
                avg_util = df[col_utilization].mean() * 100 # Convertir decimal a porcentaje
                st.metric("Team Utilization Promedio", f"{avg_util:.1f}%")
            else:
                st.metric("Team Utilization", "N/A")
                
        with col3:
            if col_billable:
                tot_bill = df[col_billable].sum()
                st.metric("Total Billable (Hrs)", f"{tot_bill:,.1f}")
            else:
                st.metric("Total Billable", "N/A")
                
        with col4:
            if col_non_billable:
                tot_non_bill = df[col_non_billable].sum()
                st.metric("Total Non-Billable (Hrs)", f"{tot_non_bill:,.1f}")
            else:
                st.metric("Total Non-Billable", "N/A")

        st.markdown("---")

        # --- SECCIÓN: GRÁFICOS EJECUTIVOS ---
        row1_col1, row1_col2 = st.columns((3, 2))

        with row1_col1:
            st.markdown("#### ⏳ Distribución de Horas por Consultor")
            if col_billable and col_non_billable:
                # Preparamos los datos para un gráfico de barras apiladas
                df_chart = df[[owner_col, col_billable, col_non_billable]].copy()
                df_chart = df_chart.melt(id_vars=[owner_col], value_vars=[col_billable, col_non_billable], 
                                         var_name='Tipo de Hora', value_name='Horas')
                
                # Renombrar para que se vea limpio en el gráfico
                df_chart['Tipo de Hora'] = df_chart['Tipo de Hora'].apply(lambda x: 'Billable' if 'non' not in x.lower() else 'Non-Billable')
                
                fig_hours = px.bar(
                    df_chart, 
                    x=owner_col, 
                    y='Horas', 
                    color='Tipo de Hora',
                    barmode='stack',
                    color_discrete_map={'Billable': '#27ae60', 'Non-Billable': '#e74c3c'},
                    template='plotly_white'
                )
                fig_hours.update_layout(xaxis_title="Consultor", yaxis_title="Suma de Horas", legend_title=None, margin=dict(t=20))
                st.plotly_chart(fig_hours, use_container_width=True)
            else:
                st.info("No se detectaron columnas claras de Billable/Non-Billable para generar este gráfico.")

        with row1_col2:
            st.markdown("#### 🎯 Team Utilization por Consultor")
            if col_utilization:
                df_util = df[[owner_col, col_utilization]].copy()
                df_util['Utilización (%)'] = df_util[col_utilization] * 100
                df_util = df_util.sort_values(by='Utilización (%)', ascending=True)

                fig_util = px.bar(
                    df_util, 
                    x='Utilización (%)', 
                    y=owner_col, 
                    orientation='h',
                    text_auto='.1f',
                    color='Utilización (%)',
                    color_continuous_scale='Blues',
                    template='plotly_white'
                )
                fig_util.update_layout(xaxis_title="%", yaxis_title="", coloraxis_showscale=False, margin=dict(t=20))
                st.plotly_chart(fig_util, use_container_width=True)
            else:
                st.info("No se detectó la columna 'Team Utilization'.")

        # --- SECCIÓN: TABLA DETALLADA ---
        with st.expander("📄 Ver Matriz de Datos Extraída", expanded=False):
            st.markdown("Esta es la tabla procesada y limpiada a partir de tu reporte original.")
            # Aplicar formato de % a la columna de utilización si existe
            format_dict = {}
            if col_utilization:
                format_dict[col_utilization] = '{:.1%}'
            st.dataframe(df.style.format(format_dict), use_container_width=True)

    else:
        st.info("👈 Sube tu exportación semanal a la izquierda para generar el reporte ejecutivo.")

if __name__ == "__main__":
    main()
