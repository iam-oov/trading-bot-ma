import os
from binance.client import Client
from typing import List, Dict, Union

from domain.ports.financial_data_provider import FinancialDataProvider


class BinanceAPIAdapter(FinancialDataProvider):
    """
    Adaptador para obtener datos financieros de la API de Binance.
    Implementa la interfaz FinancialDataProvider.
    """

    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key if api_key else os.getenv('BINANCE_API_KEY')
        self.api_secret = api_secret if api_secret else os.getenv(
            'BINANCE_API_SECRET')
        if not self.api_key or not self.api_secret:
            print("ADVERTENCIA: Las claves de API de Binance no fueron proporcionadas o no están en las variables de entorno. Esto podría causar fallos.")
            # Dependiendo de tus necesidades, podrías lanzar un ValueError aquí
        self.client = Client(self.api_key, self.api_secret)

    def get_candlestick_data(self, symbol: str, interval: str, limit: int = 500) -> List[Dict[str, Union[str, float, int]]]:
        """
        Obtiene datos de velas (candlesticks) de Binance.
        """
        try:
            klines = self.client.get_historical_klines(
                symbol, interval, limit=limit)

            formatted_klines = []
            for kline in klines:
                formatted_klines.append({
                    'open_time': kline[0],
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                    'close_time': kline[6],
                    'quote_asset_volume': float(kline[7]),
                    'number_of_trades': kline[8],
                    'taker_buy_base_asset_volume': float(kline[9]),
                    'taker_buy_quote_asset_volume': float(kline[10])
                })
            return formatted_klines
        except Exception as e:
            print(f"Error al obtener klines de Binance para {symbol}: {e}")
            raise  # Re-lanza la excepción

    def get_current_price(self, symbol: str) -> float:
        """
        Obtiene el precio actual de un símbolo de Binance.
        """
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            print(
                f"Error al obtener precio actual de Binance para {symbol}: {e}")
            raise  # Re-lanza la excepción
