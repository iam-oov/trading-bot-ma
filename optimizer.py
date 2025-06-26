import csv
import itertools
import numpy as np
import time
import os
import glob
import concurrent.futures
import threading

from backtesting import run_backtest

DATA_FOLDER = 'futures_data_1m_threaded'
RESULTS_FOLDER = 'reports_csv_threaded'
RESULTS_FILE = 'symbols.csv'
TARGET_WIN_RATE = 60.0  # Umbral WR MÍNIMO (%)
TARGET_PROFIT_FACTOR = 1.2  # Umbral PF MÍNIMO
MIN_TRADES_THRESHOLD = 10  # Mínimo trades
MAX_WORKERS = os.cpu_count()

# === Define los RANGOS de los parámetros a probar ===
sl_multiplier_range = [2.0, 2.5, 3.0]
tp_multiplier_range = [1.7, 2.0, 2.2, 2.5, 3.0]
ema_period_range = [10, 15, 20]
atr_period_range = [10, 14, 20]
max_hold_candles_range = [30]

if not os.path.exists(RESULTS_FOLDER):
    os.makedirs(RESULTS_FOLDER)

param_combinations = list(itertools.product(
    sl_multiplier_range,
    tp_multiplier_range,
    ema_period_range,
    atr_period_range,
    max_hold_candles_range
))

print("--- Iniciando Optimización Multi-Parámetro con THREADS (Any Cross Down) ---")
print(f"Carpeta de Datos: {DATA_FOLDER}")
print(f"Total de combinaciones por símbolo: {len(param_combinations)}")
print(f"Usando hasta {MAX_WORKERS} hilos.")
print("Parámetros a variar: SL Mult, TP Mult, EMA Period, ATR Period, Max Hold")
print(
    f"Guardando configs con Win Rate > {TARGET_WIN_RATE}% Y Profit Factor > {TARGET_PROFIT_FACTOR} (y >={MIN_TRADES_THRESHOLD} trades)")

csv_header = [
    'Symbol',
    'SL Multi', 'TP Multi', 'EMA Period', 'ATR Period', 'Max Hold',
    'Win Rate (%)', 'Profit Factor', 'Total Trades', 'PnL Net',
    'Num Wins', 'Num Losses', 'Avg Hold (Candles)'
]

output_file = os.path.join(RESULTS_FOLDER, RESULTS_FILE)

with open(output_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(csv_header)

data_files = glob.glob(os.path.join(DATA_FOLDER, "*_1m_data.csv"))
total_start_time = time.time()
all_results_to_write = []
total_results_found_overall = 0


def process_symbol(data_file, param_combinations, target_win_rate, target_profit_factor, min_trades_threshold):
    """
    Procesa un único archivo de datos (símbolo), ejecutando todas las combinaciones
    de parámetros y retornando los resultados que cumplen los criterios.
    """
    symbol = os.path.basename(data_file).split('_')[0]
    print(
        f"[Thread-{threading.get_ident()}] Iniciando procesamiento para: {symbol}")

    start_time = time.time()
    results_found_for_symbol = 0
    symbol_results_to_write = []

    for i, params in enumerate(param_combinations):
        sl_mult, tp_mult, ema_p, atr_p, max_hold = params

        print(f"\n[{symbol} {(i+1)}/{len(param_combinations)}] Probando: SL={sl_mult}, TP={tp_mult}, EMA={ema_p}, ATR={atr_p}, Hold={max_hold} (AnyCross)")

        try:
            results = run_backtest(
                data_file=data_file,
                sl_atr_multiplier=sl_mult,
                tp_atr_multiplier=tp_mult,
                ema_period=ema_p,
                atr_period=atr_p,
                max_hold_candles=max_hold,
                use_confluence_logic=False,
                commission_per_trade=0.0004,
                slippage_points=0.0001,
                volatility_window=20,
                verbose=False
            )

            # Evaluar resultado y guardar si cumple los criterios
            if results and results.get('total_trades', 0) >= min_trades_threshold:
                current_pf = results.get('profit_factor', 0)
                if current_pf == np.inf or current_pf > 99999:  # Manejar Infinito o valores muy grandes
                    current_pf_display = "Inf"
                    # Para la comparación numérica
                    current_pf_check = float('inf')
                else:
                    current_pf_display = f"{current_pf:.2f}"
                    current_pf_check = current_pf

                win_rate_ok = results.get('win_rate', 0) > target_win_rate
                pf_ok = current_pf_check > target_profit_factor

                if win_rate_ok and pf_ok:
                    results_found_for_symbol += 1
                    row_data = [
                        symbol,
                        sl_mult, tp_mult, ema_p, atr_p, max_hold,
                        f"{results.get('win_rate', 0):.2f}",
                        current_pf_display,
                        results.get('total_trades', 0),
                        f"{results.get('pnl_net', 0):.4f}",
                        results.get('num_wins', 0),
                        results.get('num_losses', 0),
                        f"{results.get('avg_hold_candles', 0):.1f}"
                    ]
                    symbol_results_to_write.append(row_data)

        except Exception as e:
            print(
                f"  -> ERROR [Thread-{threading.get_ident()}] Backtest para {symbol} con params {params}: {e}")

    end_time = time.time()
    print(f"[Thread-{threading.get_ident()}] === Completado {symbol} ===")
    print(
        f"[Thread-{threading.get_ident()}] Combinaciones probadas: {len(param_combinations)}")
    print(
        f"[Thread-{threading.get_ident()}] Configuraciones óptimas encontradas: {results_found_for_symbol}")
    print(
        f"[Thread-{threading.get_ident()}] Tiempo para {symbol}: {end_time - start_time:.2f} seg.")

    return symbol, results_found_for_symbol, symbol_results_to_write


with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = []
    for data_file in data_files:
        future = executor.submit(
            process_symbol,
            data_file,
            param_combinations,
            TARGET_WIN_RATE,
            TARGET_PROFIT_FACTOR,
            MIN_TRADES_THRESHOLD
        )
        futures.append(future)

    # Procesar resultados a medida que los hilos terminan
    for future in concurrent.futures.as_completed(futures):
        try:
            symbol, results_found, symbol_results = future.result()
            if symbol_results:
                all_results_to_write.extend(symbol_results)
            total_results_found_overall += results_found
            print(
                f"+++ Resultados para {symbol} recibidos (encontrados: {results_found}) +++")
        except Exception as e:
            print(f"!!! Error al procesar el resultado de un hilo: {e}")


if all_results_to_write:
    print(
        f"\nEscribiendo {len(all_results_to_write)} resultados válidos en {output_file}...")
    try:
        with open(output_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(all_results_to_write)
        print("Escritura completada.")
    except Exception as e:
        print(f"!!! ERROR al escribir los resultados finales en el CSV: {e}")
else:
    print("\nNo se encontraron configuraciones óptimas para guardar en ningún símbolo.")


print("\n===== Optimización Multi-Parámetro (Threaded) Completada para todos los símbolos =====")
print(f"Se procesaron {len(data_files)} archivos de datos.")
print(
    f"Total de configuraciones óptimas encontradas: {total_results_found_overall}")
print(f"Todos los resultados se guardaron en: {output_file}")
print(f"Tiempo total de ejecución: {time.time() - total_start_time:.2f} seg.")
