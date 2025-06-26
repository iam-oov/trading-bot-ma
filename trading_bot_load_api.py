import asyncio
import websockets
import json
import pandas as pd
import pandas_ta as ta
import numpy as np
import traceback
from datetime import timedelta, timezone
import os
import pygame
import requests
from colorama import init, Fore


FIXED_THRESHOLDS_L2 = {
    "rsi_thresh": 71,
    # "stoch_thresh": 83,
    # "stoch_k": 14,
    "wpr_thresh": -17,
    "cci_thresh": 120
}

symbol_configs = {
    # "BRUSDT":    {"sl_mult": 2.5, "tp_mult": 2.2, "ema_p": 15, "atr_p": 20, "hold": 30, "rsi_p": 14, "cci_p": 20, "stoch_d": 3, "stoch_smooth_k": 3, "wpr_p": 14, "vol_ma_p": 20, "min_cross_down": 1, **FIXED_THRESHOLDS_L2},
    # "MAVIAUSDT": {"sl_mult": 2.0, "tp_mult": 2.5, "ema_p": 10, "atr_p": 10, "hold": 30, "rsi_p": 14, "cci_p": 20, "stoch_d": 3, "stoch_smooth_k": 3, "wpr_p": 14, "vol_ma_p": 20, "min_cross_down": 1, **FIXED_THRESHOLDS_L2},
    # "MUBARAKUSDT": {"sl_mult": 2.5, "tp_mult": 2.2, "ema_p": 10, "atr_p": 20, "hold": 30, "rsi_p": 14, "cci_p": 20, "stoch_d": 3, "stoch_smooth_k": 3, "wpr_p": 14, "vol_ma_p": 20, "min_cross_down": 1, **FIXED_THRESHOLDS_L2},
    "SHELLUSDT": {"sl_mult": 5.0, "tp_mult": 4.0, "ema_p": 20, "atr_p": 20, "hold": 30, "rsi_p": 7, "cci_p": 20, "stoch_d": 3, "stoch_smooth_k": 3, "wpr_p": 14, "vol_ma_p": 20, "min_cross_down": 1, **FIXED_THRESHOLDS_L2},
    # "TUTUSDT":   {"sl_mult": 3, "tp_mult": 2.2, "ema_p": 20, "atr_p": 20, "hold": 30, "rsi_p": 14, "cci_p": 20, "stoch_d": 3, "stoch_smooth_k": 3, "wpr_p": 14, "vol_ma_p": 20, "min_cross_down": 1, **FIXED_THRESHOLDS_L2},
    # "REDUSDT":   {"sl_mult": 2.5, "tp_mult": 3.0, "ema_p": 20, "atr_p": 10, "hold": 30, "rsi_p": 14, "cci_p": 20, "stoch_d": 3, "stoch_smooth_k": 3, "wpr_p": 14, "vol_ma_p": 20, "min_cross_down": 1, **FIXED_THRESHOLDS_L2},
    # "JELLYJELLYUSDT": {"sl_mult": 3, "tp_mult": 2.2, "ema_p": 10, "atr_p": 20, "hold": 30, "rsi_p": 14, "cci_p": 20, "stoch_d": 3, "stoch_smooth_k": 3, "wpr_p": 14, "vol_ma_p": 20, "min_cross_down": 1, **FIXED_THRESHOLDS_L2},
}
SYMBOLS = list(symbol_configs.keys())

MAX_HISTORY_CANDLES = 100
WEBSOCKET_URI_TEMPLATE = "wss://fstream.binance.com/stream?streams={streams}"
RECONNECT_DELAY_SECONDS = 5
SOUND_FILE_PATH = 'media/piano.mp3'
SIMULATED_ENTRY_DELAY_SECONDS = 10
SIMULATED_TRADE_TIMEOUT_MINUTES = 45
SIMULATED_TRADE_TIMEOUT = timedelta(minutes=SIMULATED_TRADE_TIMEOUT_MINUTES)
KLINE_REST_URL = "https://fapi.binance.com/fapi/v1/klines"

init(autoreset=True)

alert_sound = None
try:
    pygame.mixer.init()
    if os.path.isfile(SOUND_FILE_PATH):
        alert_sound = pygame.mixer.Sound(SOUND_FILE_PATH)
        print(f"Sonido de alerta cargado desde: {SOUND_FILE_PATH}")
    else:
        print(
            f"Advertencia: Archivo sonido no encontrado '{SOUND_FILE_PATH}'.")
except Exception as e:
    print(f"Error inicializando Pygame Mixer: {e}")
    alert_sound = None


class SymbolMonitor:
    def __init__(self, symbol: str, config: dict):
        self.symbol = symbol
        self.config = config
        stream_kline = f"{self.symbol.lower()}@kline_1m"
        stream_price = f"{self.symbol.lower()}@markPrice@1s"
        self.uri = WEBSOCKET_URI_TEMPLATE.format(
            streams=f"{stream_kline}/{stream_price}")
        self.df = pd.DataFrame(
            columns=['Open', 'High', 'Low', 'Close', 'Volume'])
        self.current_mark_price: float | None = None
        self.active_simulated_trade: dict | None = None
        self.alert_details_pending: dict | None = None
        self.last_rest_kline_close_time_ms: int | None = None
        self.counter = 0
        self._load_initial_history()

    def _load_initial_history(self):
        """Carga el historial inicial de velas usando la API REST."""
        print(
            f"[{self.symbol}] Cargando historial inicial ({MAX_HISTORY_CANDLES} velas)...")
        try:
            # Pedimos N+1 para asegurar que tenemos N completas para los indicadores
            params = {'symbol': self.symbol, 'interval': '1m',
                      'limit': MAX_HISTORY_CANDLES + 1}
            response = requests.get(KLINE_REST_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Necesitamos al menos 2 para calcular la última hora de cierre
            if not data or len(data) < 2:
                print(
                    f"[{self.symbol}] No se recibieron suficientes datos históricos ({len(data) if data else 0}). Iniciando con DF vacío.")
                return

            # Convertir a DataFrame
            df_hist = pd.DataFrame(data, columns=[
                'Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close time',
                'Quote asset volume', 'Number of trades', 'Taker buy base asset volume',
                'Taker buy quote asset volume', 'Ignore'
            ])
            df_hist = df_hist[['Open', 'High', 'Low',
                               'Close', 'Volume', 'Close time']].copy()
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df_hist[col] = pd.to_numeric(df_hist[col], errors='coerce')
            # Limpiar si hubo error de conversión
            df_hist.dropna(subset=['Open', 'High', 'Low',
                           'Close', 'Volume'], inplace=True)
            df_hist['Timestamp'] = pd.to_datetime(
                df_hist['Close time'], unit='ms', utc=True)
            df_hist.set_index('Timestamp', inplace=True)
            df_hist = df_hist[['Open', 'High', 'Low', 'Close', 'Volume']]

            if df_hist.empty:
                print(
                    f"[{self.symbol}] DataFrame histórico vacío después del procesamiento.")
                return

            # Guardar el timestamp de la última vela REST
            # Close time de la última vela en la lista
            self.last_rest_kline_close_time_ms = int(data[-1][6])

            # Sobreescribir self.df con los datos históricos (tomamos las últimas MAX_HISTORY_CANDLES)
            self.df = df_hist.iloc[-MAX_HISTORY_CANDLES:]

            print(f"[{self.symbol}] Historial cargado OK. {len(self.df)} velas. Última REST cierra UTC: {pd.to_datetime(self.last_rest_kline_close_time_ms, unit='ms', utc=True)}")

        except requests.exceptions.RequestException as e:
            print(
                f"[{self.symbol}] Error API REST cargando historial: {e}. Iniciando con DF vacío.")
        except Exception as e:
            print(
                f"[{self.symbol}] Error procesando historial REST: {e}. Iniciando con DF vacío.")
            traceback.print_exc()

    def _update_dataframe(self, kline_data):
        """Añade vela cerrada WS y mantiene historial."""
        try:
            timestamp_ms = kline_data['T']
            timestamp = pd.to_datetime(timestamp_ms, unit='ms', utc=True)
            new_candle = pd.DataFrame({'Open': [float(kline_data['o'])], 'High': [float(kline_data['h'])], 'Low': [float(
                kline_data['l'])], 'Close': [float(kline_data['c'])], 'Volume': [float(kline_data['v'])]}, index=[timestamp])
            self.df = pd.concat([self.df, new_candle])
            if not self.df.index.is_unique:
                self.df = self.df[~self.df.index.duplicated(keep='last')]
            self.df = self.df.sort_index()
            if len(self.df) > MAX_HISTORY_CANDLES:
                self.df = self.df.iloc[-MAX_HISTORY_CANDLES:]
            return True
        except Exception as e:
            print(f"[{self.symbol}] Error actualizando DataFrame WS: {e}")
            return False

    def _calculate_indicators(self):
        """Calcula indicadores sobre una copia del DataFrame."""
        try:
            params = self.config
            min_required_rows = max(params['rsi_p'], params['wpr_p'], params['cci_p'],
                                    params['ema_p'], params['atr_p'], params.get('vol_ma_p', 20)) + 2
            if len(self.df) < min_required_rows:
                return None

            # Calcular indicadores
            df_calc = self.df.copy()
            df_calc.ta.rsi(length=params['rsi_p'], append=True)
            # df_calc.ta.stoch(k=params['stoch_k'], d=params.get(
            #     'stoch_d', 3), smooth_k=params.get('stoch_smooth_k', 3), append=True)
            df_calc.ta.willr(length=params['wpr_p'], append=True)
            df_calc.ta.cci(length=params['cci_p'], append=True)
            df_calc.ta.ema(length=params['ema_p'], append=True)
            df_calc.ta.atr(length=params['atr_p'], append=True)
            df_calc['Volume_MA'] = df_calc['Volume'].rolling(
                window=params.get('vol_ma_p', 20), min_periods=1).mean()
            df_calc.rename(
                columns={
                    f'RSI_{params["rsi_p"]}': 'RSI',
                    f'WILLR_{params["wpr_p"]}': 'WPR',
                    f'CCI_{params["cci_p"]}_0.015': 'CCI',
                    f'EMA_{params["ema_p"]}': 'EMA_Micro',
                    f'ATRr_{params["atr_p"]}': 'ATR'
                },
                inplace=True,
                errors='ignore'
            )
            required_cols = ['RSI', 'WPR',
                             'CCI', 'EMA_Micro', 'ATR', 'Volume_MA']

            if not all(col in df_calc.columns for col in required_cols):
                return None

            # Calcular Micro-Trend
            df_calc['MicroTrend_Up'] = (df_calc['Close'] > df_calc['EMA_Micro']) & (
                df_calc['EMA_Micro'] > df_calc['EMA_Micro'].shift(1))
            df_calc['MicroTrend_Down'] = (df_calc['Close'] < df_calc['EMA_Micro']) & (
                df_calc['EMA_Micro'] < df_calc['EMA_Micro'].shift(1))
            df_calc['MicroTrend'] = np.select([df_calc['MicroTrend_Up'], df_calc['MicroTrend_Down']], [
                                              'Alcista', 'Bajista'], default='Lateral')
            df_calc.dropna(inplace=True)
            return df_calc
        except Exception as e:
            print(f"[{self.symbol}] Error calculando indicadores: {e}")
            traceback.print_exc()
            return None

    def _check_signal(self, df_calc):
        """Verifica la lógica de la señal basada en min_cross_down + Filtros."""
        if len(df_calc) < 2:
            return False
        last_row = df_calc.iloc[-1]
        prev_row = df_calc.iloc[-2]
        params = self.config
        # Verificar NaNs en la última fila para columnas esenciales para la lógica
        check_cols_last = ['RSI', 'WPR', 'CCI',
                           'EMA_Micro', 'Volume', 'Volume_MA', 'MicroTrend']
        check_cols_prev = ['RSI', 'WPR', 'CCI',
                           'EMA_Micro']  # Para el chequeo de cruce OB
        if last_row[check_cols_last].isnull().any() or prev_row[check_cols_prev].isnull().any():
            # print(f"[{self.symbol} DEBUG] NaN encontrado en fila previa o última para chequeo de señal.") # Debug
            return False

        # Obtener umbrales (fijos L2)
        rsi_thresh = params['rsi_thresh']
        # stoch_thresh = params['stoch_thresh']
        wpr_thresh = params['wpr_thresh']
        cci_thresh = params['cci_thresh']

        # Chequeo Sobrecompra
        prev_rsi_ob = prev_row['RSI'] > rsi_thresh
        last_rsi_ob = last_row['RSI'] > rsi_thresh
        # prev_stoch_ob = prev_row['STOCH_K'] > stoch_thresh
        # last_stoch_ob = last_row['STOCH_K'] > stoch_thresh
        prev_wpr_ob = prev_row['WPR'] < wpr_thresh
        last_wpr_ob = last_row['WPR'] < wpr_thresh
        prev_cci_ob = prev_row['CCI'] > cci_thresh
        last_cci_ob = last_row['CCI'] > cci_thresh

        # Chequeo Cruce Hacia Abajo
        cond_rsi_cross_down = prev_rsi_ob and not last_rsi_ob
        # cond_stoch_cross_down = prev_stoch_ob and not last_stoch_ob
        cond_wpr_cross_down = prev_wpr_ob and not last_wpr_ob
        cond_cci_cross_down = prev_cci_ob and not last_cci_ob

        cross_down_count = (cond_rsi_cross_down +
                            cond_wpr_cross_down + cond_cci_cross_down)
        required_count = self.config.get('min_cross_down', 1)
        cond_signal_trigger = cross_down_count >= required_count

        # Filtros
        cond_trend_filter = last_row['MicroTrend'] != 'Alcista'
        cond_volume_ok = last_row['Volume'] > last_row['Volume_MA']

        # Señal Final
        signal_active = cond_signal_trigger and cond_trend_filter

        # --- LOGS DETALLADOS DEL CHEQUEO ---
        if cross_down_count > 0:
            print(
                f"\n--- [{self.symbol} CHECK @ {last_row.name.strftime('%H:%M:%S')}] ---")
            print(
                f"  RSI: {last_row['RSI']:.1f}(Th:{rsi_thresh}) Cross:{cond_rsi_cross_down}")
            # print(
            #     f"  STK: {last_row['STOCH_K']:.1f}(Th:{stoch_thresh}) Cross:{cond_stoch_cross_down}")
            print(
                f"  WPR: {last_row['WPR']:.1f}(Th:{wpr_thresh}) Cross:{cond_wpr_cross_down}")
            print(
                f"  CCI: {last_row['CCI']:.1f}(Th:{cci_thresh}) Cross:{cond_cci_cross_down}")
            print(
                f"  => Cross Count: {cross_down_count} (Req>={required_count}) -> Trigger OK? {cond_signal_trigger}")
            print(
                f"  Trend: {last_row['MicroTrend']} -> Trend OK? {cond_trend_filter}")
            # print(
            #     f"  Volume: {last_row['Volume']:.0f}(MA:{last_row['Volume_MA']:.0f}) -> Vol OK? {cond_volume_ok}")
            print(f"  ==> FINAL SIGNAL ACTIVE? {signal_active} <===")
            print("-" * (20 + len(self.symbol)))
        # ------------------------------------
        return signal_active

    def _play_alert_sound(self):
        """Reproduce el sonido de alerta usando Pygame Mixer."""
        global alert_sound
        if alert_sound:
            try:
                alert_sound.play()
            except Exception as e:
                print(f"Adv [{self.symbol}]: Pygame Sound Error: {e}")

    def _log_simulated_trade(self, exit_reason, exit_price, exit_time):
        """Imprime detalles del trade simulado."""
        self._play_alert_sound()
        trade = self.active_simulated_trade
        if not trade:
            return

        duration = exit_time - trade['entry_time']
        pnl_abs = trade['entry_price'] - exit_price
        pnl_pct = (pnl_abs / trade['entry_price']) * \
            100 if trade['entry_price'] != 0 else 0
        result = "Win" if pnl_abs > 0 else "Loss"
        log_message = (f"---\n[{self.symbol}] TRADE SIM CERRADO:\n  Razón: {exit_reason}\n  Entr:{trade['entry_price']:.5f}({trade['entry_time'].strftime('%H:%M:%S')}) Sal:{exit_price:.5f}({exit_time.strftime('%H:%M:%S')})\n"
                       f"  SL/TP:{trade['sl_price']:.5f}/{trade['tp_price']:.5f}\n  Dur:{str(duration).split('.')[0]} PnL:{pnl_abs:.5f} ({pnl_pct:.2f}%)\n  Resultado: {result}\n---")
        print(Fore.YELLOW + log_message)
        self.active_simulated_trade = None  # Marcar trade como cerrado

    async def _handle_simulated_entry(self):
        """Espera Ns, registra entrada y activa el monitoreo del trade."""
        if self.alert_details_pending is None:
            return
        alert_info = self.alert_details_pending
        print(f"[{self.symbol}] Alerta Recibida. Esperando {SIMULATED_ENTRY_DELAY_SECONDS}s para entrada simulada...")
        await asyncio.sleep(SIMULATED_ENTRY_DELAY_SECONDS)
        entry_price = self.current_mark_price
        self.alert_details_pending = None

        if entry_price is None:
            print(
                f"[{self.symbol}] Mark Price no disponible tras {SIMULATED_ENTRY_DELAY_SECONDS}s. Simulación cancelada.")
            return

        if entry_price >= alert_info['sl_price'] or entry_price <= alert_info['tp_price']:
            print(f"[{self.symbol}] Precio entrada ({entry_price:.5f}) ya cruzó SL/TP inicial ({alert_info['sl_price']:.5f}/{alert_info['tp_price']:.5f}). Simulación cancelada.")
            return

        self.active_simulated_trade = {
            "entry_time": pd.Timestamp.now(tz=timezone.utc), "entry_price": entry_price,
            "sl_price": alert_info['sl_price'], "tp_price": alert_info['tp_price'],
            "alert_time": alert_info['alert_time'], "alert_close_price": alert_info['alert_close_price'],
            "atr_at_alert": alert_info['atr']
        }
        print(
            Fore.CYAN + f"[{self.symbol}] >> ENTRADA SIMULADA CORTO @ {entry_price:.5f} TP: {alert_info['tp_price']:.5f} SL: {alert_info['sl_price']:.5f}")

    def _generate_alert_and_start_simulation(self, df_calc):
        """Imprime alerta inicial y lanza la tarea de simulación de entrada."""
        if self.active_simulated_trade is not None or self.alert_details_pending is not None:
            return

        last_row = df_calc.iloc[-1]
        timestamp = last_row.name
        current_atr = last_row['ATR']
        if pd.isna(current_atr) or current_atr <= 0:
            print(f"[{self.symbol}] ALERTA CORTA en {timestamp}, pero ATR inválido.")
            return

        self._play_alert_sound()

        sl_price = last_row['Close'] + (self.config['sl_mult'] * current_atr)
        tp_price = last_row['Close'] - (self.config['tp_mult'] * current_atr)
        self.alert_details_pending = {
            "alert_time": timestamp, "alert_close_price": last_row['Close'], "sl_price": sl_price, "tp_price": tp_price, "atr": current_atr}
        alert_message = (f"---> ALERTA CORTA DETECTADA (Iniciando Simulación) <---\n"
                         f"Símbolo: {self.symbol} @ {timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
                         f"Precio Vela: {last_row['Close']:.5f} | SL Sug: {sl_price:.5f} | TP Sug: {tp_price:.5f}")
        print(Fore.CYAN + "*" * 35)
        print(Fore.CYAN + alert_message)
        print(Fore.CYAN + "*" * 35)
        asyncio.create_task(self._handle_simulated_entry())

    async def process_message(self, message):
        """Procesa mensajes WS, maneja sync con REST y gestiona simulación."""
        self.counter += 1
        if self.counter % 90 == 0:
            print(Fore.BLUE + '*' * 20)
            self.counter = 0

        try:
            data = json.loads(message)
            stream = data.get('stream', '')
            kline_str = data['data']['e']

            # --- Manejo de Mark Price ---
            if stream.endswith('@markPrice@1s'):
                mark_price = float(data['data']['p'])
                price_time_ms = data['data']['E']
                self.current_mark_price = mark_price

                if self.active_simulated_trade:
                    trade = self.active_simulated_trade
                    exit_reason = None
                    exit_price = None
                    now_utc = pd.to_datetime(
                        price_time_ms, unit='ms', utc=True)
                    if mark_price >= trade['sl_price']:
                        exit_reason = "Stop Loss Hit"
                        exit_price = trade['sl_price']
                    elif mark_price <= trade['tp_price']:
                        exit_reason = "Take Profit Hit"
                        exit_price = trade['tp_price']
                    elif (now_utc - trade['entry_time']) >= SIMULATED_TRADE_TIMEOUT:
                        exit_reason = f"Time Exit ({SIMULATED_TRADE_TIMEOUT_MINUTES} min)"
                        exit_price = mark_price
                    if exit_reason:
                        if pd.isna(exit_price):
                            exit_price = mark_price
                        self._log_simulated_trade(
                            exit_reason, exit_price, now_utc)

            # --- Manejo de Kline ---
            elif kline_str == 'kline':
                kline = data['data']['k']
                if kline['x']:  # Vela cerrada
                    ws_kline_close_time_ms = kline['T']

                    # --- Chequeo de Sincronización con REST ---
                    if self.last_rest_kline_close_time_ms is not None:
                        if ws_kline_close_time_ms <= self.last_rest_kline_close_time_ms:
                            # print(f"[{self.symbol} DEBUG] Ignorando vela WS duplicada/antigua de REST.") # Debug
                            return  # Ignorar vela
                        else:
                            # print(f"[{self.symbol} DEBUG] Primera vela WS válida. Desactivando chequeo REST.") # Debug
                            self.last_rest_kline_close_time_ms = None  # Desactivar chequeo
                    # --- Fin Chequeo Sincronización ---

                    # Proceder normalmente si pasó el chequeo o ya estaba desactivado
                    if self._update_dataframe(kline):
                        df_with_indicators = self._calculate_indicators()
                        if df_with_indicators is not None:
                            if self.active_simulated_trade is None and self.alert_details_pending is None:
                                signal_active = self._check_signal(
                                    df_with_indicators)
                                if signal_active:
                                    self._generate_alert_and_start_simulation(
                                        df_with_indicators)

        except json.JSONDecodeError:
            print(f"[{self.symbol}] Error JSON: {message[:100]}...")
        except KeyError as e:
            print(f"[{self.symbol}] KeyError procesando msg: {e} - Mensaje: {data}")
        except Exception as e:
            print(f"[{self.symbol}] Error procesando msg: {e}")
            traceback.print_exc()

    async def connect(self):
        """Bucle principal para streams combinados."""
        while True:
            try:
                async with websockets.connect(self.uri) as ws:
                    print(f"Conectado a streams combinados para {self.symbol}")
                    async for message in ws:
                        await self.process_message(message)
            except websockets.exceptions.ConnectionClosed as e:
                print(f"WS cerrado {self.symbol}: {e}. Reconectando...")
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)
            except websockets.exceptions.InvalidURI:
                print(f"Error URI para {self.symbol}: {self.uri}. Deteniendo.")
                break
            except Exception as e:
                print(f"Error WS {self.symbol}: {e}. Reconectando...")
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)


# --- Función Principal Async ---
async def main():
    monitors = []
    for symbol in SYMBOLS:
        if symbol in symbol_configs:
            monitors.append(SymbolMonitor(symbol, symbol_configs[symbol]))
        else:
            print(f"Advertencia: No config for {symbol}. Saltando.")
    if not monitors:
        print("Error: No símbolos para monitorear.")
        return
    tasks = [asyncio.create_task(monitor.connect()) for monitor in monitors]
    print(f"Lanzando {len(tasks)} monitores para: {', '.join(SYMBOLS)}")
    await asyncio.gather(*tasks)

# --- Punto de Entrada ---
if __name__ == "__main__":
    print("Iniciando Sistema de Alertas Trading Bot Final...")
    print(f"Monitoreando {len(SYMBOLS)} símbolos.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCerrando conexiones...")
    finally:
        if pygame.mixer.get_init():
            pygame.mixer.quit()
            print("Pygame Mixer cerrado.")
        print("Sistema de Alertas detenido.")
