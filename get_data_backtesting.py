import pandas as pd
from binance.client import Client
from binance.enums import HistoricalKlinesType
from datetime import datetime, timedelta, timezone
import time
import os
import concurrent.futures

API_KEY = ""
API_SECRET = ""
OUTPUT_DIR = "futures_data_1m_threaded"
INTERVAL = Client.KLINE_INTERVAL_1MINUTE
MAX_WORKERS = 4
MAX_DAYS = 30 * 4  # 4 meses

symbols = [
    'BTCUSDT',
    '1000000MOGUSDT',
    'ARKUSDT',
    'AVAAIUSDT',
    'BABYUSDT',
    'BANUSDT',
    'BELUSDT',
    'BIDUSDT',
    'BIOUSDT',
    'BRETTUSDT',
    'BROCCOLI714USDT',
    'BROCCOLIF3BUSDT',
    'BRUSDT',
    'CHESSUSDT',
    'CHILLGUYUSDT',
    'COOKIEUSDT',
    'DEXEUSDT',
    'DUSDT',
    'ENJUSDT',
    'FHEUSDT',
    'FIOUSDT',
    'FUNUSDT',
    'GASUSDT',
    'GPSUSDT',
    'GRIFFAINUSDT',
    'GUNUSDT',
    'HIFIUSDT',
    'HIGHUSDT',
    'HIPPOUSDT',
    'JELLYJELLYUSDT',
    'KOMAUSDT',
    'LISTAUSDT',
    'LOKAUSDT',
    'LUMIAUSDT',
    'MAVIAUSDT',
    'MBOXUSDT',
    'MEMEUSDT',
    'MOODENGUSDT',
    'MUBARAKUSDT',
    'MYROUSDT',
    'NKNUSDT',
    'ORCAUSDT',
    'PEOPLEUSDT',
    'PERPUSDT',
    'PIPPINUSDT',
    'PIXELUSDT',
    'PUMPUSDT',
    'QUICKUSDT',
    'RDNTUSDT',
    'REDUSDT',
    'SHELLUSDT',
    'SIRENUSDT',
    'SPXUSDT',
    'STOUSDT',
    'SWARMSUSDT',
    'SYNUSDT',
    'TUSDT',
    'TUTUSDT',
    'USUALUSDT',
    'VINEUSDT',
    'VTHOUSDT',
    'XCNUSDT',
]


if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


def process_symbol(symbol, interval, start_str, api_key, api_secret, output_directory):
    """Obtiene, procesa y guarda datos para un solo símbolo."""
    thread_start_time = time.time()
    print(f"[Hilo {symbol}] Iniciando...")

    # Crear cliente DENTRO del hilo para mayor seguridad
    try:
        local_client = Client(api_key, api_secret)
        local_client.ping()
    except Exception as e:
        print(f"[Hilo {symbol}] ¡ERROR al crear cliente!: {e}")
        return f"Error de cliente para {symbol}"

    all_klines = []
    count = 0
    try:
        klines_generator = local_client.get_historical_klines_generator(
            symbol=symbol,
            interval=interval,
            start_str=start_str,
            klines_type=HistoricalKlinesType.FUTURES
        )

        for kline in klines_generator:
            all_klines.append(kline)
            count += 1
            if count % 100000 == 0:
                print(f"  [Hilo {symbol}] ...descargadas {count} velas...")
        print(f"[Hilo {symbol}] Descarga completa. Velas: {count}.")

    except Exception as e:
        # Podrian ser errores 429 (rate limit)
        print(f"[Hilo {symbol}] ¡ERROR durante descarga!: {e}")
        return f"Error descarga {symbol}: {e}"

    if all_klines:
        try:
            df = pd.DataFrame(all_klines, columns=[
                'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
                'Close time', 'Quote asset volume', 'Number of trades',
                'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
            ])

            numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Quote asset volume',
                            'Number of trades', 'Taker buy base asset volume', 'Taker buy quote asset volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col])

            df["Timestamp"] = pd.to_datetime(df["Open time"], unit='ms')

            # Target columns
            df = df[["Timestamp", "Open", "High", "Low", "Close", "Volume"]]

            csv_filename = os.path.join(
                output_directory, f"{symbol}_{interval}_data.csv")
            df.to_csv(csv_filename, index=False)
            print(f"  [Hilo {symbol}] Datos guardados en {csv_filename}")

        except Exception as e:
            print(
                f"[Hilo {symbol}] ¡ERROR al procesar/guardar DataFrame!: {e}")
            return f"Error procesamiento {symbol}: {e}"
    else:
        print(f"[Hilo {symbol}] No se descargaron datos.")
        return f"Sin datos para {symbol}"

    thread_end_time = time.time()
    print(
        f"[Hilo {symbol}] Finalizado. Tiempo: {thread_end_time - thread_start_time:.2f} seg.")
    return f"Completado {symbol}"


print(
    f"\n--- Iniciando proceso CONCURRENTE para {len(symbols)} símbolos (Max Workers: {MAX_WORKERS}) ---")
overall_start_time = time.time()

current_time = datetime.now(timezone.utc)
start_date_target = current_time - timedelta(days=MAX_DAYS)
start_date_str = start_date_target.strftime("%d %B, %Y")
print(f"Intentando obtener datos desde: {start_date_str}")

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    future_to_symbol = {executor.submit(
        process_symbol, symbol, INTERVAL, start_date_str, API_KEY, API_SECRET, OUTPUT_DIR): symbol for symbol in symbols}

    for future in concurrent.futures.as_completed(future_to_symbol):
        symbol_name = future_to_symbol[future]
        try:
            result_message = future.result()
            results.append(result_message)
        except Exception as exc:
            print(
                f"[Principal] ¡ERROR al ejecutar tarea para {symbol_name}!: {exc}")
            results.append(f"Excepción {symbol_name}: {exc}")

overall_end_time = time.time()
print("\n--- Resumen de Resultados ---")
completed_count = sum(1 for r in results if r and r.startswith("Completado"))
no_data_count = sum(1 for r in results if r and r.startswith("Sin datos"))
error_count = len(results) - completed_count - no_data_count
print(f"Completados exitosamente: {completed_count}")
print(f"Sin datos (o muy nuevos): {no_data_count}")
print(f"Errores: {error_count}")

for r in results:
    if not r.startswith("Completado") and not r.startswith("Sin datos"):
        print(f"  - {r}")

print(
    f"Tiempo total de ejecución: {overall_end_time - overall_start_time:.2f} segundos.")
