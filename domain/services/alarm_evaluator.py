from typing import Dict, Any
from domain.ports.financial_data_provider import FinancialDataProvider


class AlarmEvaluator:
    """
    Servicio de dominio para evaluar condiciones de alarma.
    Depende de la interfaz FinancialDataProvider para obtener datos.
    """

    def __init__(self, data_provider: FinancialDataProvider):
        self.data_provider = data_provider

    def evaluate_alarm(self, alarm_config: Dict[str, Any]) -> bool:
        """
        Evalúa si una alarma debe dispararse basándose en su configuración.

        Args:
            alarm_config (Dict): Configuración de la alarma (ej. {'symbol': 'BTCUSDT', 'interval': '1h', 'condition_type': 'price_above', 'threshold': 70000}).

        Returns:
            bool: True si la alarma debe dispararse, False en caso contrario.
        """
        symbol = alarm_config.get('symbol')
        interval = alarm_config.get('interval')
        condition_type = alarm_config.get('condition_type')
        threshold = alarm_config.get('threshold')

        if not all([symbol, condition_type, threshold]):
            raise ValueError("Configuración de alarma incompleta.")

        try:
            current_price = self.data_provider.get_current_price(symbol)
            print(f"[{symbol}] Precio actual: {current_price}")

            if condition_type == 'price_above':
                return current_price > threshold
            elif condition_type == 'price_below':
                return current_price < threshold
            # Aquí podrías añadir lógica más compleja que use get_candlestick_data
            # Por ejemplo, evaluar un RSI, Media Móvil, etc.
            # klines = self.data_provider.get_candlestick_data(symbol, interval, limit=50)
            # ...lógica de cálculo de indicador y evaluación...

        except Exception as e:
            print(f"Error al evaluar alarma para {symbol}: {e}")
            return False  # La alarma no se dispara si hay un error al obtener datos

        return False  # Condición no satisfecha por defecto
