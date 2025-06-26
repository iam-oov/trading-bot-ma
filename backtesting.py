# backtesting.py (Versión Final con Umbrales Dinámicos, Lógica de Señal Variable y Rename ATR corregido)
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import traceback


def assign_vol_level(vol, quantiles):
    """Asigna un nivel de volatilidad (1-5) basado en cuantiles."""
    if pd.isna(vol):
        return np.nan
    # Manejar caso donde los cuantiles podrían no ser estrictamente crecientes
    # o vol podría estar fuera de los rangos esperados debido a NaNs previos
    try:
        if vol <= quantiles.iloc[0]:  # <= 20%
            return 1
        elif vol <= quantiles.iloc[1]:  # <= 40%
            return 2
        elif vol <= quantiles.iloc[2]:  # <= 60%
            return 3
        elif vol <= quantiles.iloc[3]:  # <= 80%
            return 4
        else:  # > 80%
            return 5
    except IndexError:  # Si quantiles no tiene suficientes elementos
        return np.nan
    except Exception:  # Otro error inesperado
        return np.nan


def run_backtest(
    data_file: str,
    # --- Parámetros de Indicadores ---
    rsi_period: int = 14,
    stoch_k: int = 14,
    stoch_d: int = 3,
    stoch_smooth_k: int = 3,
    wpr_period: int = 14,
    cci_period: int = 20,
    ema_period: int = 10,
    atr_period: int = 14,
    # --- Umbrales Dinámicos (Diccionarios por nivel) ---
    rsi_overbought_thresholds: dict = {1: 73},
    stoch_k_overbought_thresholds: dict = {1: 83},
    wpr_overbought_thresholds: dict = {1: -17},
    cci_overbought_thresholds: dict = {1: 120},
    # --- Parámetros de Estrategia ---
    sl_atr_multiplier: float = 2.0,
    tp_atr_multiplier: float = 1.5,
    max_hold_candles: int = 30,
    commission_per_trade: float = 0.0004,
    slippage_points: float = 0.0001,
    # --- Parámetros Volatilidad Propia ---
    volatility_window: int = 20,
    # --- Parámetro Confluencia / Lógica de Señal ---
    min_confluence_indicators: int = 2,  # Usado solo si use_confluence_logic=True
    use_confluence_logic: bool = True,  # True=Confluencia >=N; False=Any Cross Down
    verbose: bool = True
) -> dict:
    """ Ejecuta backtest con umbrales dinámicos y lógica de señal variable. """

    start_time = time.time()
    signal_logic_desc = f"Confluencia >= {min_confluence_indicators}" if use_confluence_logic else "Any Indicator Cross Down"
    if verbose:
        print(
            f"\n--- Iniciando Backtest (Umbrales Dinámicos + Señal: {signal_logic_desc}) ---")

    # --- Cargar Datos Intradía ---
    try:
        df = pd.read_csv(data_file, index_col='Timestamp', parse_dates=True)
        if verbose:
            print(
                f"Datos intradía cargados: {df.shape[0]} filas. Período: {df.index.min()} a {df.index.max()}")
    except Exception as e:
        print(f"Error cargando datos: {e}")
        return {}

    # --- Pre-cálculo: Niveles de Volatilidad Diaria ---
    if verbose:
        print("Pre-calculando niveles de volatilidad diaria...")
    try:
        df_daily = df['Close'].resample('D').last().to_frame()
        if df_daily.empty:
            raise ValueError("Resample diario vacío.")
        df_daily['log_return'] = np.log(
            df_daily['Close'] / df_daily['Close'].shift(1))
        df_daily['rolling_vol'] = df_daily['log_return'].rolling(
            window=volatility_window).std() * np.sqrt(365)
        df_daily.dropna(subset=['rolling_vol'], inplace=True)
        if df_daily['rolling_vol'].count() < 5:
            raise ValueError(
                f"Pocos datos de volatilidad ({df_daily['rolling_vol'].count()}) para cuantiles.")
        quantiles = df_daily['rolling_vol'].quantile([0.2, 0.4, 0.6, 0.8])
        if quantiles.isnull().any():
            raise ValueError("Cuantiles NaN.")
        df_daily['Volatility_Level'] = df_daily['rolling_vol'].apply(
            lambda x: assign_vol_level(x, quantiles))
        df_daily.dropna(subset=['Volatility_Level'], inplace=True)
        df['Date'] = df.index.date
        daily_levels_map = df_daily['Volatility_Level'].to_dict()
        daily_levels_map = {k.date() if isinstance(
            k, pd.Timestamp) else k: v for k, v in daily_levels_map.items()}
        df['Volatility_Level'] = df['Date'].map(daily_levels_map)
        # df['Volatility_Level'].fillna(method='ffill', inplace=True)
        df['Volatility_Level'] = df['Volatility_Level'].ffill()
        df.dropna(subset=['Volatility_Level'], inplace=True)
        df['Volatility_Level'] = df['Volatility_Level'].astype(int)
        df.drop(columns=['Date'], inplace=True)
        if verbose:
            print("Niveles de volatilidad asignados.")
    except Exception as e:
        print(f"Error calculando volatilidad diaria: {e}")
        traceback.print_exc()
        return {}

    # --- Calcular Indicadores Intradía ---
    if verbose:
        print("Calculando indicadores intradía...")
    try:
        df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
        # Calcular todos los indicadores necesarios
        df.ta.rsi(length=rsi_period, append=True)
        df.ta.stoch(k=stoch_k, d=stoch_d, smooth_k=stoch_smooth_k, append=True)
        df.ta.willr(length=wpr_period, append=True)
        df.ta.cci(length=cci_period, append=True)
        df.ta.ema(length=ema_period, append=True)  # EMA para micro-trend
        df.ta.atr(length=atr_period, append=True)  # ATR para SL/TP

        # --- Rename ---
        # ¡¡REVISA Y AJUSTA LAS CLAVES (IZQUIERDA) SI LOS NOMBRES GENERADOS SON DIFERENTES!!
        df.rename(columns={
            f'RSI_{rsi_period}': 'RSI',  # Verifica este
            # Verifica este
            f'STOCHk_{stoch_k}_{stoch_d}_{stoch_smooth_k}': 'STOCH_K',
            f'WILLR_{wpr_period}': 'WPR',  # Verifica este
            f'CCI_{cci_period}_0.015': 'CCI',  # Verifica este (puede variar)
            f'EMA_{ema_period}': 'EMA_Micro',  # Verifica este
            # --- Clave ATR ajustada según tu indicación ---
            f'ATRr_{atr_period}': 'ATR'
            # -------------------------------------------
        }, inplace=True, errors='ignore')

        # --- Verificación Post-Rename ---
        required_cols = ['RSI', 'STOCH_K', 'WPR', 'CCI', 'EMA_Micro', 'ATR']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(
                f"Error Critico: Faltan columnas esenciales después del rename: {missing_cols}")
            print(f"Columnas actuales en el DataFrame: {df.columns.to_list()}")
            # Considera imprimir df.ta.indicators() o revisar la documentación de tu pandas_ta
            return {}  # Fallar si falta alguna columna esencial

        # Calcular Filtro de Micro-Tendencia
        df['MicroTrend_Up'] = (df['Close'] > df['EMA_Micro']) & (
            df['EMA_Micro'] > df['EMA_Micro'].shift(1))
        df['MicroTrend_Down'] = (df['Close'] < df['EMA_Micro']) & (
            df['EMA_Micro'] < df['EMA_Micro'].shift(1))
        df['MicroTrend'] = np.select([df['MicroTrend_Up'], df['MicroTrend_Down']], [
                                     'Alcista', 'Bajista'], default='Lateral')

        # Limpiar NaNs finales de indicadores y cálculos de tendencia
        df.dropna(inplace=True)
        if verbose:
            print("Indicadores intradía y micro-tendencia calculados.")

    except Exception as e:
        print(
            f"Error durante el cálculo o renombrado de indicadores intradía: {e}")
        traceback.print_exc()
        return {}

    # --- 4. Generar Señales (Umbrales Dinámicos y Lógica de Señal Variable) ---
    signal_logic_desc_short = "Confl>=N" if use_confluence_logic else "AnyCross"
    if verbose:
        print(f"Generando señales ({signal_logic_desc_short})...")
    try:
        # Crear columnas de umbrales dinámicos
        df['RSI_Thresh'] = df['Volatility_Level'].map(
            rsi_overbought_thresholds)
        df['STOCH_Thresh'] = df['Volatility_Level'].map(
            stoch_k_overbought_thresholds)
        df['WPR_Thresh'] = df['Volatility_Level'].map(
            wpr_overbought_thresholds)
        df['CCI_Thresh'] = df['Volatility_Level'].map(
            cci_overbought_thresholds)

        # Identificar sobrecompra usando umbrales dinámicos
        df['RSI_is_OB'] = df['RSI'] > df['RSI_Thresh']
        df['STOCH_is_OB'] = df['STOCH_K'] > df['STOCH_Thresh']
        df['WPR_is_OB'] = df['WPR'] < df['WPR_Thresh']  # WPR usa '<'
        df['CCI_is_OB'] = df['CCI'] > df['CCI_Thresh']

        # Identificar cruce hacia abajo para CADA indicador
        cond_rsi_cross_down = df['RSI_is_OB'].shift(1) & ~df['RSI_is_OB']
        cond_stoch_cross_down = df['STOCH_is_OB'].shift(1) & ~df['STOCH_is_OB']
        cond_wpr_cross_down = df['WPR_is_OB'].shift(1) & ~df['WPR_is_OB']
        cond_cci_cross_down = df['CCI_is_OB'].shift(1) & ~df['CCI_is_OB']

        # Filtro de Micro-Tendencia (usando EMA_Micro)
        cond_trend_filter = df['MicroTrend'] != 'Alcista'

        # --- Seleccionar Lógica de Señal ---
        if use_confluence_logic:
            # Lógica de Confluencia
            df['Cross_Down_Count'] = (cond_rsi_cross_down.astype(int) + cond_stoch_cross_down.astype(int) +
                                      cond_wpr_cross_down.astype(int) + cond_cci_cross_down.astype(int))
            cond_signal_trigger = df['Cross_Down_Count'] >= min_confluence_indicators
        else:
            VOL_MA_PERIOD = 20  # Período para la media móvil de volumen
            df['Volume_MA'] = df['Volume'].rolling(window=VOL_MA_PERIOD).mean()
            cond_volume_ok = df['Volume'] > df['Volume_MA']

            # Lógica Simple: Cualquier indicador cruza hacia abajo
            cond_signal_trigger = cond_rsi_cross_down | cond_stoch_cross_down | cond_wpr_cross_down | cond_cci_cross_down

            # Señal final (Disparador de Señal Y Filtro de Micro-Tendencia Y Filtro de Volumen)
            df['Signal_Short'] = cond_signal_trigger & cond_trend_filter & cond_volume_ok
        # --- Fin Selección Lógica ---

        # Limpiar NaNs finales
        df.dropna(subset=['RSI_is_OB', 'STOCH_is_OB', 'WPR_is_OB', 'CCI_is_OB',
                          'Signal_Short', 'ATR', 'Volume_MA'], inplace=True)
        num_signals = df['Signal_Short'].sum()
        if verbose:
            print(
                f"Señales generadas ({signal_logic_desc_short}). {num_signals} señales potenciales encontradas.")
        if num_signals == 0:
            return {'win_rate': 0, 'total_trades': 0}

    except Exception as e:
        print(f"Error durante la generación de señales: {e}")
        traceback.print_exc()
        return {}

    # --- 5. Simulación de Backtesting (Loop Principal) ---
    if verbose:
        print("Iniciando simulación...")
    trades = []
    active_trade = None
    # (El bucle for es idéntico a la versión anterior)
    for i in range(len(df)):
        if df['Signal_Short'].iloc[i] and active_trade is None:
            entry_price = df['Close'].iloc[i]
            entry_time = df.index[i]
            atr_value = df['ATR'].iloc[i]
            if pd.isna(atr_value) or atr_value <= 0:
                continue  # Chequeo robusto de ATR
            stop_loss = entry_price + (sl_atr_multiplier * atr_value)
            take_profit = entry_price - (tp_atr_multiplier * atr_value)
            # Simple validación de precios SL/TP
            if stop_loss <= entry_price or take_profit >= entry_price:
                continue  # Evitar SL/TP inválidos
            entry_price_adjusted = entry_price * (1 - slippage_points)
            cost_entry = entry_price_adjusted * commission_per_trade
            active_trade = {'entry_time': entry_time, 'entry_price': entry_price_adjusted, 'stop_loss': stop_loss,
                            'take_profit': take_profit, 'entry_candle_index': i, 'cost': cost_entry, 'atr_at_entry': atr_value}
        elif active_trade is not None:
            current_candle_index = i
            start_candle_index = active_trade['entry_candle_index']
            exit_reason = None
            exit_price = None
            # Chequeo de salida (importante el orden si High>=SL y Low<=TP en la misma vela)
            # Damos prioridad al SL
            if df['High'].iloc[current_candle_index] >= active_trade['stop_loss']:
                exit_reason = 'Stop Loss'
                exit_price = active_trade['stop_loss']
            elif df['Low'].iloc[current_candle_index] <= active_trade['take_profit']:
                exit_reason = 'Take Profit'
                exit_price = active_trade['take_profit']
            elif current_candle_index - start_candle_index >= max_hold_candles:
                exit_reason = 'Time Exit'
                exit_price = df['Close'].iloc[current_candle_index]

            if exit_reason:
                # Asegurarse que exit_price no sea NaN (podría pasar con Time Exit si el Close es NaN)
                if pd.isna(exit_price):
                    # Fallback
                    exit_price = df['Close'].iloc[current_candle_index]
                if pd.isna(exit_price):
                    # Fallback extremo
                    exit_price = active_trade['entry_price']

                exit_price_adjusted = exit_price * (1 + slippage_points)
                cost_exit = exit_price_adjusted * commission_per_trade
                pnl = active_trade['entry_price'] - exit_price_adjusted
                pnl_net = pnl - active_trade['cost'] - cost_exit
                result = 'Win' if pnl_net > 0 else 'Loss'
                trades.append({'entry_time': active_trade['entry_time'], 'entry_price': active_trade['entry_price'], 'exit_time': df.index[current_candle_index],
                               'exit_price': exit_price_adjusted, 'sl': active_trade['stop_loss'], 'tp': active_trade['take_profit'],
                               'atr_at_entry': active_trade['atr_at_entry'], 'pnl_gross': pnl, 'pnl_net': pnl_net,
                               'result': result, 'exit_reason': exit_reason, 'hold_duration': current_candle_index - start_candle_index + 1})
                active_trade = None

    if verbose:
        print(f"Simulación completada. {len(trades)} trades ejecutados.")

    # --- 6. Calcular y Retornar Resultados ---
    if not trades:
        return {'win_rate': 0, 'total_trades': 0, 'pnl_net': 0, 'profit_factor': 0}
    # (Cálculo de métricas idéntico)
    results_df = pd.DataFrame(trades)
    total_trades = len(results_df)
    winning_trades = results_df[results_df['result'] == 'Win']
    losing_trades = results_df[results_df['result'] == 'Loss']
    num_wins = len(winning_trades)
    num_losses = len(losing_trades)
    win_rate = (num_wins / total_trades) * 100 if total_trades > 0 else 0
    total_pnl_net = results_df['pnl_net'].sum()
    gross_profit = winning_trades['pnl_gross'].sum()
    gross_loss = abs(losing_trades['pnl_gross'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
    end_time = time.time()
    duration = end_time - start_time
    if verbose:
        print(
            f"Cálculo de métricas completado. Duración total: {duration:.2f} segundos.")
    # Devolvemos info útil
    return {
        'signal_logic': signal_logic_desc,
        'sl_multiplier': sl_atr_multiplier, 'tp_multiplier': tp_atr_multiplier,
        'thresholds': 'dynamic',
        'win_rate': win_rate, 'total_trades': total_trades, 'pnl_net': total_pnl_net,
        'profit_factor': profit_factor, 'num_wins': num_wins, 'num_losses': num_losses,
        'avg_hold_candles': results_df['hold_duration'].mean() if total_trades > 0 else 0
    }


# --- Bloque Standalone ---
if __name__ == "__main__":
    print("Ejecutando backtesting.py como script principal...")
    # ¡¡IMPORTANTE: CAMBIA ESTO A LA RUTA DE TU ARCHIVO DE DATOS!!
    default_data_file = 'results/TUTUSDT_1m_8months.csv'

    # --- Prueba 1: SIN CONFLUENCIA ---
    # --- Prueba 1: SIN CONFLUENCIA ---
    print("\n" + "="*40)
    # Mensaje actualizado
    print("--- Probando SIN CONFLUENCIA (Candidato 3 con Costos x2) ---")
    print("="*40)
    results_any_cost_test = run_backtest(
        data_file=default_data_file,
        use_confluence_logic=False,      # Lógica Simple
        # --- Parámetros del Candidato 3 ---
        sl_atr_multiplier=3.0,
        tp_atr_multiplier=2.0,
        ema_period=20,
        atr_period=14,
        max_hold_candles=20,
        # --- Costos Aumentados (x2) ---
        commission_per_trade=0.0008,  # Doble de comisión
        slippage_points=0.0002,     # Doble de slippage
        # ------------------------------
        verbose=True  # Muestra detalle
    )
    if results_any_cost_test:
        # Mensaje actualizado
        print("\n--- Resultados (SIN Confluencia, Costos x2) ---")
        # (El bucle for para imprimir resultados sigue igual)
        for key, value in results_any_cost_test.items():
            if isinstance(value, float) and key not in ['sl_multiplier', 'tp_multiplier']:
                # Imprimir con 4 decimales para PnL
                print(f"{key.replace('_', ' ').title()}: {value:.4f}")
            else:
                print(f"{key.replace('_', ' ').title()}: {value}")
