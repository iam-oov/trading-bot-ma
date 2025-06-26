import pandas as pd
import plotly.graph_objects as go
# import io # Si usas la cadena de texto

# --- Asume que tienes los 100k datos en 'large_data.csv' ---
# Cambia esto a la ruta de tu archivo real
file_path = 'futures_data_1m_threaded_one/BANUSDT_1m_data.csv'

try:
    # --- 1. Cargar los datos ---
    print(f"Cargando datos desde '{file_path}'...")
    # Usar 'parse_dates' directamente puede ser eficiente
    df = pd.read_csv(file_path, parse_dates=['Timestamp'])
    print(f"Se cargaron {len(df)} filas.")

    # Nota: Plotly no requiere estrictamente que Timestamp sea el índice,
    # pero puede ser útil tenerlo para otras operaciones.
    # df.set_index('Timestamp', inplace=True) # Opcional para Plotly

    print("Primeras filas de datos:")
    print(df.head())

    # --- 2. Crear la figura interactiva con Plotly ---
    print("\nGenerando gráfico interactivo con Plotly...")
    fig = go.Figure(data=[go.Candlestick(x=df['Timestamp'],
                                         open=df['Open'],
                                         high=df['High'],
                                         low=df['Low'],
                                         close=df['Close'])])

    # --- 3. Añadir interactividad y diseño (opcional pero recomendado) ---
    fig.update_layout(
        title='Gráfico de Velas Japonesas Interactivo (100k puntos)',
        xaxis_title='Timestamp',
        yaxis_title='Precio',
        xaxis_rangeslider_visible=False  # Oculta el 'rangeslider' si no lo quieres
    )

    # --- 4. Mostrar el gráfico ---
    # Esto abrirá una pestaña en tu navegador web o mostrará el gráfico
    # inline si estás en un entorno como Jupyter Notebook/Lab.
    fig.show()
    print("Gráfico generado. Revisa tu navegador o salida de Jupyter.")

except FileNotFoundError:
    print(f"Error: No se encontró el archivo en la ruta '{file_path}'.")
except Exception as e:
    print(f"Ocurrió un error inesperado: {e}")
