# logger_module.py
import queue
import threading
import os
import time
import json
from colorama import Fore, init

init(autoreset=True) # Initialize colorama

class SharedLogger:
    """Handles console logging with colors and stores logs for web UI."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SharedLogger, cls).__new__(cls)
                cls._instance._initialize(*args, **kwargs)
            return cls._instance

    def _initialize(self, max_queue_size=1000):
        """Initializes the log queue and colors."""
        self.log_messages = queue.Queue(maxsize=max_queue_size)
        self.web_colors = { # CSS Colors for web UI
            "GREEN": "color: green;",
            "RED": "color: red;",
            "default": "color: black;" # Default web color
        }
        self.console_colors = { # Colorama Fore colors for console
            "GREEN": Fore.GREEN,
            "RED": Fore.RED,
            "default": Fore.WHITE # Default console color
        }
        self._log_to_console = True # Flag to control console output

    def enable_console_log(self, enable=True):
        self._log_to_console = enable

    def get_web_color_style(self, color_name="default"):
        """Gets the CSS style for a color name."""
        return self.web_colors.get(color_name.upper(), self.web_colors["default"])

    def log_message(self, message, color="default"):
        """Logs a message to console (if enabled) and stores for web UI."""
        upper_color = color.upper()
        # Store message and original color name for potential web use
        if self.log_messages.full():
            try:
                self.log_messages.get_nowait() # Remove oldest if full
            except queue.Empty:
                pass
        self.log_messages.put((message, color)) # Store with original case color name

        # Print to console if enabled
        if self._log_to_console:
            console_color = self.console_colors.get(upper_color, self.console_colors["default"])
            print(f"{console_color}{message}")

    def get_all_logs_for_web(self):
        """Retrieves all logs formatted for the web UI."""
        messages = []
        # Safely copy queue contents without blocking producers too long
        with self._lock:
            temp_storage = list(self.log_messages.queue)

        for msg, color_name in reversed(temp_storage): # Show newest first typically
            color_style = self.get_web_color_style(color_name)
            messages.append((msg, color_style))
        return messages # Returns list of (message, css_style)

# --- File Logging Functions ---

def setup_file_logging(log_path):
    """Creates the necessary log directory."""
    if not config.ACTIVE_LOG:
        return False
    try:
        os.makedirs(log_path, exist_ok=True)
        logger.log_message(f"Log directory ensured: {log_path}")
        return True
    except OSError as e:
        logger.log_message(f"Error creating log directory '{log_path}': {e}", "RED")
        return False

def _get_operation_filename(log_path, operation_type_name, tick, entry_price, status_prefix=""):
    """Constructs the standard filename for an operation log."""
    # Generate a suffix from the entry price to add uniqueness
    price_str = f"{entry_price:.8f}" # Use fixed precision for consistency
    sufix = price_str.split('.')[-1][-3:] if '.' in price_str else price_str[-3:]
    filename = f"{status_prefix}{operation_type_name}-{tick}-{sufix}.txt"
    return os.path.join(log_path, filename)

def log_operation_start(log_path, pin, trading_params, operation_details):
    """Writes the initial log file for a new operation."""
    if not config.ACTIVE_LOG:
        return

    tick = operation_details['tick']
    op_type = operation_details['type']
    entry_price = operation_details['entry_price']
    tp = operation_details['tp']
    sl = operation_details['sl']

    filepath = _get_operation_filename(log_path, op_type["name"], tick, entry_price)

    try:
        with open(filepath, 'w') as file:
            file.write(f'PIN: {pin}\n')
            # Write trading parameters used for this operation
            for key, value in trading_params.items():
                file.write(f'{key}: {value}%\n')
            file.write('-----------------\n')
            file.write(f'{op_type.get("emoji","?")}{op_type["name"]}: {tick}\n')
            file.write(f'Hour: {time.strftime("%H:%M:%S")}\n')
            file.write(f'EntryPrice: {entry_price}\n')
            file.write(f'TakeProfit: {tp}\n')
            file.write(f'StopLoss: {sl}\n')
            file.write('-----------------\n')
            # Add header for progress logs
            file.write('Timestamp;EntryPrice;CurrentPrice;Difference%\n')

    except IOError as e:
        logger.log_message(f"I/O error creating operation log {filepath}: {e}", "RED")
    except Exception as e:
        logger.log_message(f"Unexpected error writing operation log {filepath}: {e}", "RED")


def log_operation_progress(log_path, operation_details, current_price, difference):
    """Appends the current progress of an operation to its log file."""
    if not config.ACTIVE_LOG:
        return

    tick = operation_details['tick']
    op_type = operation_details['type']
    entry_price = operation_details['entry_price']

    filepath = _get_operation_filename(log_path, op_type["name"], tick, entry_price)

    # Check if file exists, might not if initial creation failed
    if not os.path.exists(filepath):
        # Optionally log this warning, or attempt to recreate header?
        # logger.log_message(f"Warning: Progress log file not found, cannot append: {filepath}", "RED")
        return

    try:
        with open(filepath, 'a') as file:
            file.write(f'{time.strftime("%H:%M:%S")};{entry_price};{current_price};{difference}%\n')
    except IOError as e:
        logger.log_message(f"I/O error appending progress to {filepath}: {e}", "RED")
    except Exception as e:
        logger.log_message(f"Unexpected error appending progress to {filepath}: {e}", "RED")

def finalize_operation_log(log_path, operation_details, final_status, current_price, final_difference):
    """Appends final status to the log file and renames it with the status prefix."""
    if not config.ACTIVE_LOG:
        return

    tick = operation_details['tick']
    op_type = operation_details['type']
    entry_price = operation_details['entry_price']

    original_filepath = _get_operation_filename(log_path, op_type["name"], tick, entry_price)
    final_filepath = _get_operation_filename(log_path, op_type["name"], tick, entry_price, status_prefix=f"{final_status}-")

    if not os.path.exists(original_filepath):
        logger.log_message(f"Warning: Cannot finalize - log file not found: {original_filepath}", "RED")
        return

    try:
        # Append final status
        with open(original_filepath, 'a') as file:
            file.write('-----------------\n')
            file.write(f'FINAL STATUS: {final_status}\n')
            file.write(f'Final Price: {current_price}\n')
            file.write(f'Final Difference: {final_difference}%\n')
            file.write(f'End Time: {time.strftime("%H:%M:%S")}\n')

        # Rename the file
        time.sleep(0.1) # Small delay before rename, might help on some systems
        os.rename(original_filepath, final_filepath)
        logger.log_message(f"Finalized and renamed log: {final_filepath}")

    except IOError as e:
        logger.log_message(f"I/O error finalizing/renaming log {original_filepath} to {final_filepath}: {e}", "RED")
        # Attempt to write failure note in original file if rename fails
        try:
            with open(original_filepath, 'a') as file:
                file.write(f'\n--- RENAME FAILED to {final_filepath} ---\n')
        except Exception:
            pass # Ignore errors during fallback logging
    except Exception as e:
        logger.log_message(f"Unexpected error finalizing/renaming log {original_filepath}: {e}", "RED")


def log_results_to_json(log_path, pin, results_summary, stats):
    """Saves the aggregated results and statistics to a JSON file."""
    if not config.ACTIVE_LOG:
        return

    filepath = os.path.join(log_path, 'results.json')
    output_data = {
        "pin": pin,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "results_summary": results_summary,
        "stats": stats,
    }

    try:
        # Ensure directory exists (might be redundant if setup_file_logging was called)
        os.makedirs(log_path, exist_ok=True)
        with open(filepath, 'w') as file:
            json.dump(output_data, file, indent=2)
        # logger.log_message(f"Results saved to {filepath}") # Optional: log success
    except IOError as e:
        logger.log_message(f"I/O error saving results to {filepath}: {e}", "RED")
    except TypeError as e:
        logger.log_message(f"Type error preparing data for results.json: {e}", "RED")
    except Exception as e:
        logger.log_message(f"Unexpected error saving results.json: {e}", "RED")


# --- Initialization ---
import config

# Create the shared logger instance
logger = SharedLogger()
