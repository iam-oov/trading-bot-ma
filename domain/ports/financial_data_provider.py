from abc import ABC, abstractmethod
from typing import List, Dict, Union


class FinancialDataProvider(ABC):
    """
    Interfaz abstracta (Puerto Impulsado) para proveedores de datos financieros.
    Tu dominio solo dependerá de esta interfaz, no de implementaciones concretas.
    """

    @abstractmethod
    def get_candlestick_data(self, symbol: str, interval: str, limit: int = 500) -> List[Dict[str, Union[str, float, int]]]:
        """
        Obtiene datos de velas (candlesticks) para un símbolo y un intervalo dados.

        Args:
            symbol (str): El símbolo del par de trading (ej. 'BTCUSDT').
            interval (str): El intervalo de tiempo de la vela (ej. '1m', '5m', '1h', '1d').
            limit (int): El número máximo de velas a retornar.

        Returns:
            List[Dict]: Una lista de diccionarios, donde cada diccionario representa una vela.
                        Debe contener al menos 'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time'.
        """
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        """
        Obtiene el precio actual de un símbolo.

        Args:
            symbol (str): El símbolo del par de trading (ej. 'BTCUSDT').

        Returns:
            float: El precio actual.
        """
        pass
