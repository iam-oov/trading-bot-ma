from pybit.unified_trading import HTTP
import os
from typing import List, Dict, Union

from domain.ports.financial_data_provider import FinancialDataProvider


class BybitAPIAdapter(FinancialDataProvider):
    """
    Adaptador para obtener datos financieros de la API de Bybit.
    Implementa la interfaz FinancialDataProvider.
    """

    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key if api_key else os.getenv('BYBIT_API_KEY')
        self.api_secret = api_secret if api_secret else os.getenv(
            'BYBIT_API_SECRET')
        if not self.api_key or not self.api_secret:
            print("ADVERTENCIA: Las claves de API de Bybit no fueron proporcionadas o no están en las variables de entorno. Esto podría causar fallos.")
            # Puedes decidir si esto es un error fatal o si solo quieres un aviso
        self.client = HTTP(testnet=False, api_key=self.api_key,
                           api_secret=self.api_secret)

    def get_candlestick_data(self, symbol: str, interval: str, limit: int = 500) -> List[Dict[str, Union[str, float, int]]]:
        """
        Obtiene datos de velas (candlesticks) de Bybit.
        """
        bybit_interval_map = {
            '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
            '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720',
            '1d': 'D', '1w': 'W', '1M': 'M'
        }
        bybit_interval = bybit_interval_map.get(interval)
        if not bybit_interval:
            raise ValueError(
                f"Intervalo '{interval}' no soportado por el adaptador de Bybit.")

        try:
            response = self.client.get_kline(
                category='spot',  # Ajusta a 'linear' o 'inverse' si necesitas futuros/perpetuos
                symbol=symbol.upper(),
                interval=bybit_interval,
                limit=limit
            )

            klines = response['result']['list']
        except Exception as e:
            print(f"Error al obtener klines de Bybit para {symbol}: {e}")
            raise  # Re-lanza la excepción

        formatted_klines = []
        for kline in klines:
            # Bybit kline format: ["start_time", "open", "high", "low", "close", "volume", "turnover"]
            formatted_klines.append({
                'open_time': int(kline[0]),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5]),
                # Calcula close_time sumando la duración del intervalo a open_time
                'close_time': int(kline[0]) + self._interval_to_ms(bybit_interval) - 1,
                # Equivalente a quote_asset_volume en Binance
                'turnover': float(kline[6])
            })
        return formatted_klines

    def get_current_price(self, symbol: str) -> float:
        """
        Obtiene el precio actual de un símbolo de Bybit.
        """
        try:
            response = self.client.get_tickers(
                category='spot', symbol=symbol.upper())  # O 'linear'

            if response['result']['list']:
                return float(response['result']['list'][0]['lastPrice'])
            else:
                raise ValueError(
                    f"No se encontró ticker para el símbolo {symbol} en Bybit.")
        except Exception as e:
            print(
                f"Error al obtener precio actual de Bybit para {symbol}: {e}")
            raise  # Re-lanza la excepción

    def _interval_to_ms(self, interval: str) -> int:
        """
        Convierte el intervalo de Bybit a milisegundos para calcular close_time.
        """
        if interval.endswith('m'):  # Minutos
            return int(interval[:-1]) * 60 * 1000
        elif interval.endswith('h'):  # Horas
            return int(interval[:-1]) * 60 * 60 * 1000
        elif interval == 'D':  # Día
            return 24 * 60 * 60 * 1000
        elif interval == 'W':  # Semana
            return 7 * 24 * 60 * 60 * 1000
        elif interval == 'M':  # Mes
            # Esto es una aproximación, ya que los meses tienen diferente duración
            return 30 * 24 * 60 * 60 * 1000
        return 0  # Si el intervalo no es reconocido, retorna 0 o lanza un error
