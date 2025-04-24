# binance_service.py
from binance.client import Client
import sys
from logger_module import logger
import config

class BinanceService:
    """Handles interactions with the Binance API."""

    def __init__(self, api_key=None, api_secret=None, tld='com'):
        """Initializes the Binance client."""
        self.client = None
        # Use keys from config, but allow overriding
        key = api_key if api_key else config.BINANCE_API_KEY
        secret = api_secret if api_secret else config.BINANCE_API_SECRET
        try:
            self.client = Client(key, secret, tld=tld)
            # Test connection
            self.client.futures_ping()
            logger.log_message("Binance client initialized and connected.", "GREEN")
        except Exception as e:
            logger.log_message(f"CRITICAL Error initializing Binance client: {e}", "RED")
            # Depending on severity, you might want to exit or handle this
            # sys.exit(1) # Or raise an exception
            self.client = None # Ensure client is None if connection failed

    def is_connected(self):
        """Check if the client was initialized successfully."""
        return self.client is not None

    def get_usdt_futures_symbols(self):
        """Gets all symbols ending with USDT from Binance Futures."""
        if not self.is_connected():
            logger.log_message("Binance client not available (get_usdt_futures_symbols).", "RED")
            return []
        try:
            tickers = self.client.futures_symbol_ticker()
            return [tick['symbol'] for tick in tickers if tick['symbol'].endswith('USDT')]
        except Exception as e:
            logger.log_message(f"Error getting symbols from Binance: {e}", "RED")
            return []

    def get_futures_klines(self, symbol, interval=Client.KLINE_INTERVAL_1MINUTE, limit=30):
        """Gets candlestick data for a specific futures symbol."""
        if not self.is_connected():
            logger.log_message(f"Binance client not available (get_futures_klines for {symbol}).", "RED")
            return None
        try:
            return self.client.futures_klines(symbol=symbol, interval=interval, limit=limit)
        except Exception as e:
            logger.log_message(f"Error getting klines for {symbol}: {e}", "RED")
            return None

    def get_futures_ticker_info(self, symbol):
        """Gets general ticker information for a futures symbol."""
        if not self.is_connected():
            logger.log_message(f"Binance client not available (get_futures_ticker_info for {symbol}).", "RED")
            return None
        try:
            return self.client.futures_ticker(symbol=symbol)
        except Exception as e:
            logger.log_message(f"Error getting ticker info for {symbol}: {e}", "RED")
            return None

# --- Create a global instance for easy import ---
# This instance will be created when the module is imported
binance_service = BinanceService()
