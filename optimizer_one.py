import csv
import itertools
import numpy as np
import time
import os
import glob
from backtesting import run_backtest

# --- Parámetros de Optimización ---
DATA_FOLDER = 'futures_data_1m_threaded_one'
RESULTS_FOLDER = 'reports_csv_one'
RESULTS_FILE = 'symbols.csv'
TARGET_WIN_RATE = 60.0  # Umbral WR MÍNIMO (%)
TARGET_PROFIT_FACTOR = 1.2  # Umbral PF MÍNIMO
MIN_TRADES_THRESHOLD = 10  # Mínimo trades

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

print("--- Iniciando Optimización Multi-Parámetro (Any Cross Down) ---")
print(f"Carpeta de Datos: {DATA_FOLDER}")
print(f"Total de combinaciones por símbolo: {len(param_combinations)}")
print("Parámetros a variar: SL Mult, TP Mult, EMA Period, ATR Period, Max Hold")
print(
    f"Guardando configs con Win Rate > {TARGET_WIN_RATE}% Y Profit Factor > {TARGET_PROFIT_FACTOR} (y >={MIN_TRADES_THRESHOLD} trades)")

csv_header = [
    'Symbol',
    'SL Multi', 'TP Multi', 'EMA Period', 'ATR Period', 'Max Hold',
    'Win Rate (%)', 'Profit Factor', 'Total Trades', 'PnL Net',
    'Num Wins', 'Num Losses', 'Avg Hold (Candles)'
]

output_file = f"{RESULTS_FOLDER}/{RESULTS_FILE}"
with open(output_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(csv_header)

data_files = glob.glob(f"{DATA_FOLDER}/*_1m_data.csv")
total_start_time = time.time()
total_results_found = 0

for data_file in data_files:
    symbol = os.path.basename(data_file).split('_')[0]

    print(f"\n\n==== Procesando símbolo: {symbol} ====")
    print(f"Archivo de datos: {data_file}")
    print(f"Resultados se guardarán en: {output_file}")

    start_time = time.time()
    results_found = 0

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
            if results and results.get('total_trades', 0) >= MIN_TRADES_THRESHOLD:
                current_pf = results.get('profit_factor', 0)
                if current_pf == np.inf:
                    current_pf = 99999

                win_rate_ok = results.get('win_rate', 0) > TARGET_WIN_RATE
                pf_ok = current_pf > TARGET_PROFIT_FACTOR

                if win_rate_ok and pf_ok:
                    results_found += 1
                    total_results_found += 1
                    with open(output_file, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            symbol,
                            sl_mult, tp_mult, ema_p, atr_p, max_hold,
                            f"{results.get('win_rate', 0):.2f}",
                            f"{current_pf:.2f}" if current_pf != 99999 else "Inf",
                            results.get('total_trades', 0),
                            f"{results.get('pnl_net', 0):.4f}",
                            results.get('num_wins', 0),
                            results.get('num_losses', 0),
                            f"{results.get('avg_hold_candles', 0):.1f}"
                        ])
            elif results:
                pass  # Ignorar si hay muy pocos trades

        except Exception as e:
            print(
                f"  -> ERROR durante el backtest para {symbol} con params {params}: {e}")

    print(f"\n--- Optimización para {symbol} Completada ---")
    print(f"Se probaron {len(param_combinations)} combinaciones.")
    print(
        f"Se encontraron y guardaron {results_found} configuraciones óptimas para {symbol}")
    print(
        f"Tiempo de optimización para {symbol}: {time.time() - start_time:.2f} seg.")

print("\n===== Optimización Multi-Parámetro Completada para todos los símbolos =====")
print(f"Se procesaron {len(data_files)} archivos de datos.")
print(f"Total de configuraciones encontradas: {total_results_found}")
print(f"Todos los resultados se guardaron en: {output_file}")
print(f"Tiempo total de ejecución: {time.time() - total_start_time:.2f} seg.")
