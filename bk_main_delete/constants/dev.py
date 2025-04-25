# Trading parameters
TRADING = {
    'STOP_LOSS_PERCENTAGE': 0.5,  # Stop loss percentage per operation
    'TAKE_PROFIT_PERCENTAGE': 0.5,  # Take profit percentage per operation

    'VARIATION_PERCENTAGE': 2,  # variation to activate the operation of possible pairs
    'VARIATION_100K_PERCENTAGE': 2,  # variation for pairs with volume less than 100k
    'VARIATION_FAST_PERCENTAGE': 0.8,  # variation for rapid upward movements
    'LOG_PATH': 'log/',  # Path to the log file
}

# Program config
ACTIVE_LOG = True
CLOSE_NOTIFICATION_TIMEOUT = 2  # seconds
EVALUATION_CYCLE_TIME = 15  # seconds
SCAN_TICKER_CYCLE_TIME = 27  # seconds
MAX_CONCURRENT_OPERATIONS = 15  # maximum number of concurrent operations
SOUND = {
    'ACTIVE': False,
    'PATH': 'media/piano.wav',
}
NOTIFICATIONS = {
    'ACTIVE': False,
}
WIN = {
    'name': 'WIN',
    'emoji': '🟣🟢'
}
LOSE = {
    'name': 'LOSE',
    'emoji': '🟣🔴'
}
IN_PROGRESS = {
    'name': 'IN_PROGRESS',
    'emoji': '🟣🟡'
}

# Operation types
FAST_SHORT = {
    'name': 'FAST_SHORT',
    'emoji': '🟣🔴🔥'
}
LONG = {
    'name': 'LONG',
    'emoji': '🟣🟢'
}
SHORT = {
    'name': 'SHORT',
    'emoji': '🟣🔴'
}
