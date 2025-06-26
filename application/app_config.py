import os
from dotenv import load_dotenv

from domain.ports.financial_data_provider import FinancialDataProvider
from adapters.financial_data.binance_adapter import BinanceAPIAdapter
from adapters.financial_data.bybit_adapter import BybitAPIAdapter
from domain.services.alarm_evaluator import AlarmEvaluator


def configure_app(exchange_to_use: str = 'binance') -> AlarmEvaluator:
    """
    Configura y ensambla la aplicación inyectando las dependencias.

    Args:
        exchange_to_use (str): 'binance' o 'bybit' para seleccionar el proveedor de datos.

    Returns:
        AlarmEvaluator: Una instancia del servicio de evaluación de alarmas configurada.
    """
    load_dotenv()  # Carga las variables de entorno desde .env

    data_provider: FinancialDataProvider

    if exchange_to_use.lower() == 'binance':
        data_provider = BinanceAPIAdapter(
            api_key=os.getenv('BINANCE_API_KEY'),
            api_secret=os.getenv('BINANCE_API_SECRET')
        )
        print("Usando Binance como proveedor de datos.")
    elif exchange_to_use.lower() == 'bybit':
        data_provider = BybitAPIAdapter(
            api_key=os.getenv('BYBIT_API_KEY'),
            api_secret=os.getenv('BYBIT_API_SECRET')
        )
        print("Usando Bybit como proveedor de datos.")
    else:
        raise ValueError(
            f"Exchange '{exchange_to_use}' no soportado. Elige 'binance' o 'bybit'.")

    # Inyecta el proveedor de datos al servicio de dominio
    alarm_evaluator = AlarmEvaluator(data_provider=data_provider)

    return alarm_evaluator
