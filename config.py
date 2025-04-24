# config.py
import os
import sys
import time
import random
import importlib

def generate_pin():
    """Generates a unique PIN based on date and time."""
    date_str = time.strftime('%d%m')
    time_str = time.strftime('%H%M%S')
    random_number = random.randint(10000, 99999)
    return f'{date_str}/{time_str}{random_number}'

def load_constants_module(module_suffix='base'):
    """Loads the specified constants module, falling back to base."""
    module_name = f'constants.{module_suffix}'
    try:
        constants = importlib.import_module(module_name)
        print(f"Using constants: {module_name}")
        return constants, module_name
    except ImportError:
        print(f"Warning: Constants module '{module_name}' not found. Using 'constants.base'.")
        module_name = 'constants.base'
        try:
            constants = importlib.import_module(module_name)
            print(f"Using constants: {module_name}")
            return constants, module_name
        except ImportError as e:
            # Use print directly here as logger might not be available yet
            print(f"CRITICAL Error: Could not import base constants module 'constants.base'. Verify it exists.", file=sys.stderr)
            print(f"Details: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"CRITICAL Error: Unexpected error loading constants module '{module_name}'.", file=sys.stderr)
            print(f"Details: {e}", file=sys.stderr)
            sys.exit(1)

def parse_arguments():
    """
    Parses command line arguments to determine mode, log prefix, and trading overrides.
    Returns exactly three values: log_prefix (str), overrides (dict), is_dev (bool).
    """
    args = sys.argv[1:]
    mode = 'base' # Default mode
    custom_log_prefix = None
    overrides = {}
    is_dev = False

    if not args:
        # No arguments provided, use defaults
        return mode, overrides, is_dev # Return default prefix 'base'

    # Check for 'dev' mode first
    if args[0] == 'dev':
        mode = 'dev'
        is_dev = True
        print("Development Mode Activated.")
        args = args[1:] # Consume 'dev' argument

    # Check if the *next* argument looks like a custom prefix (not a number)
    # This allows `runner.py dev custom_prefix` or `runner.py custom_prefix`
    if args and not args[0].replace('.', '', 1).isdigit():
        custom_log_prefix = args[0]
        print(f"Using custom log prefix: {custom_log_prefix}")
        args = args[1:] # Consume prefix argument

    # Remaining args are potential TRADING parameter overrides
    if args:
        # Load base constants temporarily ONLY to get the expected keys for overrides
        # This avoids loading the full final constants before overrides are known
        temp_constants_module_name = 'constants.base'
        try:
            temp_constants = importlib.import_module(temp_constants_module_name)
            if hasattr(temp_constants, 'TRADING') and isinstance(temp_constants.TRADING, dict):
                keys = list(temp_constants.TRADING.keys())
                modified_trading_params = False
                for i, arg in enumerate(args):
                    if i < len(keys):
                        key = keys[i]
                        try:
                            overrides[key] = round(float(arg), 2)
                            print(f"TRADING parameter override: {key} = {overrides[key]}")
                            modified_trading_params = True
                        except ValueError:
                            # If we haven't processed overrides yet AND haven't set a custom prefix,
                            # treat this non-numeric arg as the prefix.
                            if not modified_trading_params and custom_log_prefix is None and not is_dev:
                                custom_log_prefix = arg
                                print(f"Using custom log prefix: {arg}")
                                # Don't consume the arg here, let loop continue in case it's the only arg
                            else:
                                print(f"Argument '{arg}' ignored (expected number for override or prefix already set).", file=sys.stderr)
                        except KeyError:
                            # This shouldn't happen if keys are from temp_constants.TRADING
                            print(f"Warning: Key '{key}' (from base) somehow not found for override.", file=sys.stderr)
                    else:
                        # If we haven't processed overrides yet AND haven't set a custom prefix,
                        # treat this extra arg as the prefix.
                        if not modified_trading_params and custom_log_prefix is None and not is_dev:
                            custom_log_prefix = arg
                            print(f"Using custom log prefix: {arg}")
                        else:
                            print(f"Extra argument '{arg}' ignored.", file=sys.stderr)

            else:
                print(f"Warning: {temp_constants_module_name}.TRADING not found or not a dictionary. Cannot process overrides.", file=sys.stderr)
                # Treat remaining args as potential prefix if none set
                if args and custom_log_prefix is None and not is_dev:
                    custom_log_prefix = args[0]
                    print(f"Using custom log prefix (fallback): {custom_log_prefix}")


        except ImportError:
            print(f"Warning: Could not import '{temp_constants_module_name}' to get override keys.", file=sys.stderr)
            # Treat remaining args as potential prefix if none set
            if args and custom_log_prefix is None and not is_dev:
                custom_log_prefix = args[0]
                print(f"Using custom log prefix (fallback): {custom_log_prefix}")


    # Determine the final log prefix to use
    # Priority: custom_log_prefix > dev > base
    if custom_log_prefix:
        log_prefix = custom_log_prefix
    elif is_dev:
        log_prefix = 'dev'
    else:
        log_prefix = 'base' # Default if no prefix and not dev

    # --- IMPORTANT: Ensure exactly three values are returned ---
    return log_prefix, overrides, is_dev

# --- Main Configuration Loading ---
PIN = generate_pin()
CURRENT_TIME_STR = time.strftime('%H:%M:%S')

# Parse arguments first to know which constants to load and if overrides exist
# This line expects parse_arguments() to return exactly 3 values
LOG_PREFIX, TRADING_OVERRIDES, IS_DEV = parse_arguments()

# Load the appropriate constants module based on determined prefix/mode
# If overrides were applied without a specific prefix, load 'base' and apply overrides later
constants_suffix_to_load = LOG_PREFIX if not IS_DEV else 'dev'
CONSTANTS, MODULE_NAME = load_constants_module(constants_suffix_to_load)

# Apply overrides if any were parsed
if TRADING_OVERRIDES and hasattr(CONSTANTS, 'TRADING') and isinstance(CONSTANTS.TRADING, dict):
    print("Applying TRADING parameter overrides...")
    for key, value in TRADING_OVERRIDES.items():
        if key in CONSTANTS.TRADING:
            CONSTANTS.TRADING[key] = value
            print(f"  Applied: {key} = {value}")
        else:
            print(f"  Warning: Override key '{key}' not found in loaded constants '{MODULE_NAME}'.", file=sys.stderr)
elif TRADING_OVERRIDES:
    print(f"Warning: Overrides parsed, but CONSTANTS.TRADING not found or not a dict in '{MODULE_NAME}'. Overrides ignored.", file=sys.stderr)


# Define Log Path using the final LOG_PREFIX
LOG_PATH = os.path.join('log', LOG_PREFIX, PIN.replace('/', os.sep)) # Ensure OS-agnostic path

# --- Other Settings ---
SERVER_URL = 'http://127.0.0.1:5000'
BINANCE_API_KEY = '' # Keep API keys out of source code ideally
BINANCE_API_SECRET = '' # Use environment variables or a secure config file

# Sound Settings (Safely access attributes)
SOUND_ACTIVE = getattr(CONSTANTS, 'SOUND', {}).get('ACTIVE', False)
SOUND_PATH = getattr(CONSTANTS, 'SOUND', {}).get('PATH', None)

# Notification Settings (Safely access attributes)
NOTIFICATIONS_ACTIVE = getattr(CONSTANTS, 'NOTIFICATIONS', {}).get('ACTIVE', False)
NOTIFICATION_TIMEOUT = getattr(CONSTANTS, 'CLOSE_NOTIFICATION_TIMEOUT', 10) # Default 10s

# Trading Parameters (ensure defaults if keys are missing in the loaded module)
DEFAULT_TRADING_PARAMS = {
    "STOP_LOSS_PERCENTAGE": 0.3,
    "TAKE_PROFIT_PERCENTAGE": 0.5,
    "VARIATION_PERCENTAGE": 0.5,
    "VARIATION_100K_PERCENTAGE": 1.0,
    "VARIATION_FAST_PERCENTAGE": 1.0,
}
# Get the TRADING dict safely, default to empty dict if not present
TRADING_PARAMS = getattr(CONSTANTS, 'TRADING', {})
if not isinstance(TRADING_PARAMS, dict):
    print(f"Warning: CONSTANTS.TRADING in '{MODULE_NAME}' is not a dictionary. Using defaults.", file=sys.stderr)
    TRADING_PARAMS = {} # Reset to empty dict

# Ensure all default keys exist, using defaults if necessary
for key, default in DEFAULT_TRADING_PARAMS.items():
    if key not in TRADING_PARAMS:
        print(f"Warning: Key '{key}' missing in {MODULE_NAME}.TRADING. Using default: {default}", file=sys.stderr)
        TRADING_PARAMS[key] = default


# Operational Settings (Safely access attributes)
MAX_CONCURRENT_OPERATIONS = getattr(CONSTANTS, 'MAX_CONCURRENT_OPERATIONS', 5)
SCAN_TICKER_CYCLE_TIME = getattr(CONSTANTS, 'SCAN_TICKER_CYCLE_TIME', 60)
EVALUATION_CYCLE_TIME = getattr(CONSTANTS, 'EVALUATION_CYCLE_TIME', 30)
ACTIVE_LOG = getattr(CONSTANTS, 'ACTIVE_LOG', True) # Default to True if not specified

# Constant Names (Safely access attributes, provide defaults)
WIN_NAME = getattr(CONSTANTS, 'WIN', {}).get('name', 'WIN')
LOSE_NAME = getattr(CONSTANTS, 'LOSE', {}).get('name', 'LOSE')
IN_PROGRESS_NAME = getattr(CONSTANTS, 'IN_PROGRESS', {}).get('name', 'IN_PROGRESS')
FAST_SHORT_NAME = getattr(CONSTANTS, 'FAST_SHORT', {}).get('name', 'FAST_SHORT')
LONG_NAME = getattr(CONSTANTS, 'LONG', {}).get('name', 'LONG')
SHORT_NAME = getattr(CONSTANTS, 'SHORT', {}).get('name', 'SHORT')

# Type definitions using the names derived above (ensure defaults if missing)
TYPE_DEFINITIONS = {
    LONG_NAME: getattr(CONSTANTS, 'LONG', {'name': LONG_NAME, 'emoji': '📈'}),
    SHORT_NAME: getattr(CONSTANTS, 'SHORT', {'name': SHORT_NAME, 'emoji': '📉'}),
    FAST_SHORT_NAME: getattr(CONSTANTS, 'FAST_SHORT', {'name': FAST_SHORT_NAME, 'emoji': '⚡️'})
}
# Ensure the dictionaries themselves exist if accessed directly elsewhere
if not hasattr(CONSTANTS, 'LONG'): CONSTANTS.LONG = TYPE_DEFINITIONS[LONG_NAME]
if not hasattr(CONSTANTS, 'SHORT'): CONSTANTS.SHORT = TYPE_DEFINITIONS[SHORT_NAME]
if not hasattr(CONSTANTS, 'FAST_SHORT'): CONSTANTS.FAST_SHORT = TYPE_DEFINITIONS[FAST_SHORT_NAME]


# Initial Results Structure using derived names
INITIAL_RESULTS = {
    WIN_NAME: {FAST_SHORT_NAME: 0, LONG_NAME: 0, SHORT_NAME: 0},
    LOSE_NAME: {FAST_SHORT_NAME: 0, LONG_NAME: 0, SHORT_NAME: 0},
    IN_PROGRESS_NAME: {FAST_SHORT_NAME: 0, LONG_NAME: 0, SHORT_NAME: 0}
}

def print_config_summary():
    print('--- Configuration Summary ---')
    print(f'PIN: {PIN}')
    print(f'Log Prefix: {LOG_PREFIX}')
    print(f'Log Path: {LOG_PATH}')
    print(f'Development Mode: {IS_DEV}')
    print(f'Constants Module Used: {MODULE_NAME}')
    print(f'Server URL: {SERVER_URL}')
    print(f'File Logging Active: {ACTIVE_LOG}')
    print(f'Notifications Active: {NOTIFICATIONS_ACTIVE}')
    print(f'Sound Active: {SOUND_ACTIVE}')
    print('Trading Parameters (Active):')
    # Print from TRADING_PARAMS which includes defaults/overrides
    for key, value in TRADING_PARAMS.items():
        print(f'  {key}: {value}%')
    print('---------------------------')
