# trading_bot.py
import sys
import time
import threading
import socketio
import copy

# --- Import Configuration and Services ---
try:
    import config # Loads constants, parses args, sets up paths etc.
    # Import logger instance and file logging functions
    from logger_module import logger, setup_file_logging, log_operation_start, \
                            log_operation_progress, finalize_operation_log, \
                            log_results_to_json
    from binance_service import binance_service # Initialized instance
    from notification_service import notification_service # Initialized instance
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import core modules: {e}", file=sys.stderr)
    print("Ensure config.py, logger_module.py, binance_service.py, notification_service.py exist and are correct.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"CRITICAL ERROR during initial imports: {e}", file=sys.stderr)
    sys.exit(1)


# --- Socket.IO Client Setup ---
sio_client = socketio.Client(logger=False, engineio_logger=False)
connected_to_server = False

@sio_client.event
def connect():
    global connected_to_server
    connected_to_server = True
    logger.log_message(f'Trading Bot (PIN: {config.PIN}) connected to server.', 'GREEN')
    send_log_to_server(f'Trading Bot (PIN: {config.PIN}) connected to server.', 'GREEN')
    # Send initial stats and active operations upon connection
    send_stats_to_server()
    send_active_operations_to_server() # Send current state


@sio_client.event
def connect_error(data):
    global connected_to_server
    if connected_to_server: # Only log if it was previously connected
        logger.log_message(f'Connection to server failed: {data}', 'RED')
    connected_to_server = False

@sio_client.event
def disconnect():
    global connected_to_server
    if connected_to_server: # Log only if it was previously connected
        logger.log_message('Disconnected from server.', 'RED')
    connected_to_server = False

def send_log_to_server(message, color="default"):
    """Attempts to send the log to the server if connected."""
    global connected_to_server
    if connected_to_server:
        try:
            web_color_style = logger.get_web_color_style(color)
            sio_client.emit('log_from_script', {'message': message, 'color': web_color_style})
        except socketio.exceptions.BadNamespaceError:
            logger.log_message("Socket.IO connection lost (BadNamespaceError), attempting reconnect implicitly.", "RED")
            connected_to_server = False # Mark as disconnected
        except Exception as e:
            logger.log_message(f"Error sending log to server: {e}", "RED")


# --- Wrap logger.log_message to also send to server ---
original_log_message = logger.log_message
def wrapped_log_message(message, color="default"):
    """Logs locally and sends to Socket.IO server."""
    original_log_message(message, color) # Log to console first
    send_log_to_server(message, color) # Then attempt to send

# Replace the logger's method with the wrapped one
logger.log_message = wrapped_log_message

# --- Function to Send Statistics ---
def send_stats_to_server():
    """Calculates and sends current statistics to the server if connected."""
    global connected_to_server
    if not connected_to_server:
        return

    try:
        in_progress_count = sum(results.get(config.IN_PROGRESS_NAME, {}).values())
        winning_count = sum(results.get(config.WIN_NAME, {}).values())
        losing_count = sum(results.get(config.LOSE_NAME, {}).values())
        total_finished = winning_count + losing_count
        efficiency = round(winning_count * 100 / total_finished, 2) if total_finished > 0 else 0.0

        stats_data = {
            "pin": config.PIN,
            "in_progress": in_progress_count,
            "wins": winning_count,
            "losses": losing_count,
            "total_finished": total_finished,
            "efficiency": f"{efficiency:.2f}%",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        sio_client.emit('stats_from_script', stats_data)

    except socketio.exceptions.BadNamespaceError:
        logger.log_message("Socket.IO connection lost (BadNamespaceError) while sending stats.", "RED")
        connected_to_server = False
    except Exception as e:
        logger.log_message(f"Error calculating or sending statistics: {e}", "RED")

# --- Function to Send Active Operations ---
def send_active_operations_to_server():
    """Collects details of active operations and sends them to the server."""
    global connected_to_server
    if not connected_to_server:
        return

    active_ops_list = []
    try:
        # Iterate safely over a copy of items in case dict changes
        for tick, op_data in list(possible_operations.items()):
            if op_data.get('is_active', False):
                # Calculate current difference if possible (might be slightly stale)
                current_diff = op_data.get('last_difference', 0.0)

                active_ops_list.append({
                    'tick': tick,
                    'type_name': op_data['type'].get('name', 'N/A'),
                    'type_emoji': op_data['type'].get('emoji', '?'),
                    'entry_price': f"{op_data.get('entry_price', 0):.5f}",
                    'difference': f"{current_diff:.2f}%",
                    'difference_raw': current_diff,
                    'tp': f"{op_data.get('tp', 0):.5f}",
                    'sl': f"{op_data.get('sl', 0):.5f}",
                    'start_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(op_data.get('start_time', 0))),
                })

        # Sort list alphabetically by ticker for consistent display
        active_ops_list.sort(key=lambda x: x['tick'])

        sio_client.emit('active_ops_from_script', active_ops_list)
        # logger.log_message(f"Sent {len(active_ops_list)} active operations to server.") # Optional debug

    except socketio.exceptions.BadNamespaceError:
        logger.log_message("Socket.IO connection lost (BadNamespaceError) while sending active ops.", "RED")
        connected_to_server = False
    except Exception as e:
        logger.log_message(f"Error collecting or sending active operations: {e}", "RED")


# --- Bot State ---
possible_operations = {} # Stores active and recently finished operations
results = copy.deepcopy(config.INITIAL_RESULTS)


# --- Core Trading Logic Functions ---

def calculate_variation(price1, price2):
    """Calculates percentage variation."""
    if price1 <= 0: return 0.0
    try:
        p1 = float(price1)
        p2 = float(price2)
        if p1 == 0: return 0.0
        return round(((p1 - p2) / p1) * 100, 2)
    except (ValueError, TypeError):
        logger.log_message(f"Error converting prices to float for variation calculation: {price1}, {price2}", "RED")
        return 0.0

def calculate_tp_sl(operation_type, current_price):
    """Calculates Take Profit and Stop Loss values."""
    tp_perc = config.TRADING_PARAMS.get('TAKE_PROFIT_PERCENTAGE', 0.5)
    sl_perc = config.TRADING_PARAMS.get('STOP_LOSS_PERCENTAGE', 0.3)
    try:
        price = float(current_price)
        if price <= 0: return 0.0, 0.0
        if operation_type['name'] == config.LONG_NAME:
            tp = round(price + (price * tp_perc / 100), 8)
            sl = round(price - (price * sl_perc / 100), 8)
        else:
            tp = round(price - (price * tp_perc / 100), 8)
            sl = round(price + (price * sl_perc / 100), 8)
        sl = max(0.00000001, sl)
        return tp, sl
    except (ValueError, TypeError):
        logger.log_message(f"Error calculating TP/SL for price {current_price}", "RED")
        return 0.0, 0.0

def calculate_difference(entry_price, current_price, operation_type):
    """Calculates the percentage difference."""
    try:
        entry = float(entry_price)
        current = float(current_price)
        if entry <= 0: return 0.0
        difference = round(((current - entry) / entry) * 100, 2)
        if operation_type['name'] != config.LONG_NAME:
            difference *= -1
        return difference
    except (ValueError, TypeError):
        logger.log_message(f"Error calculating difference: {entry_price}, {current_price}", "RED")
        return 0.0

def check_deactivation(operation_type, current_price, operation_data):
    """Checks if an operation should be deactivated based on TP/SL."""
    tp = operation_data.get('tp')
    sl = operation_data.get('sl')
    if tp is None or sl is None:
        logger.log_message(f"Missing TP/SL in operation data for {operation_data.get('tick', 'N/A')}", "RED")
        return False, None
    try:
        price = float(current_price)
        win_or_lose = None
        deactivate = False
        if operation_type['name'] == config.LONG_NAME:
            if price >= tp: deactivate, win_or_lose = True, config.WIN_NAME
            elif price <= sl: deactivate, win_or_lose = True, config.LOSE_NAME
        else:
            if price <= tp: deactivate, win_or_lose = True, config.WIN_NAME
            elif price >= sl: deactivate, win_or_lose = True, config.LOSE_NAME
        return deactivate, win_or_lose
    except (ValueError, TypeError):
        logger.log_message(f"Error checking deactivation for price {current_price}", "RED")
        return False, None


# --- Operation Processing ---

def process_entry_condition(tick, variation, operation_type_name, current_price):
    """Processes a potential entry."""
    try:
        var_perc = config.TRADING_PARAMS.get('VARIATION_PERCENTAGE', 0.5)
        var_100k_perc = config.TRADING_PARAMS.get('VARIATION_100K_PERCENTAGE', 1.0)
        operation_type = config.TYPE_DEFINITIONS.get(operation_type_name)
        if not operation_type:
            logger.log_message(f"Unknown operation type name: {operation_type_name}", "RED")
            return

        if variation >= var_perc:
            info = binance_service.get_futures_ticker_info(tick)
            if info is None or 'quoteVolume' not in info:
                logger.log_message(f"Could not get volume info for {tick} to check entry condition.", "RED")
                return
            volume = float(info.get('quoteVolume', 0))
            if volume > 100_000_000 or variation >= var_100k_perc:
                trigger_new_operation(tick, operation_type, current_price)
    except KeyError as e:
        logger.log_message(f"Error: Key '{e}' missing in config.TRADING_PARAMS (process_entry).", "RED")
    except (ValueError, TypeError) as e:
        logger.log_message(f"Data error when processing entry for {tick}: {e}", "RED")
    except Exception as e:
        logger.log_message(f"Unexpected error in process_entry_condition for {tick}: {e}", "RED")


def trigger_new_operation(tick, operation_type, current_price):
    """Initiates a new trading operation if limits allow."""
    try:
        # Check if operation already active
        if tick in possible_operations and possible_operations[tick].get('is_active', False):
            return

        # --- ENFORCE MAX CONCURRENT OPERATIONS LIMIT ---
        active_ops_count = sum(1 for op in possible_operations.values() if op.get('is_active', False))
        if active_ops_count >= config.MAX_CONCURRENT_OPERATIONS:
            logger.log_message(f"Max concurrent operations ({config.MAX_CONCURRENT_OPERATIONS}) reached. Ignoring potential entry for {tick}.", "YELLOW")
            return

        tp, sl = calculate_tp_sl(operation_type, current_price)
        if tp == 0.0 and sl == 0.0:
            logger.log_message(f"Failed to calculate TP/SL for {tick}, cannot start operation.", "RED")
            return

        operation_data = {
            'tick': tick,
            'type': operation_type,
            'entry_price': current_price,
            'tp': tp,
            'sl': sl,
            'start_time': time.time(),
            'is_active': True,
            'status': config.IN_PROGRESS_NAME,
            'last_difference': 0.0 # Initialize last known difference
        }
        possible_operations[tick] = operation_data
        results[config.IN_PROGRESS_NAME][operation_type['name']] += 1

        log_title = f'NEW OPERATION - PIN: {config.PIN}'
        log_msg = f'{operation_type.get("emoji","?")}{operation_type["name"]}: {tick}'
        logger.log_message('-----------------')
        logger.log_message(log_title)
        logger.log_message(log_msg, "GREEN")
        logger.log_message(f'Entry Price: {current_price}')
        logger.log_message(f'Take profit: {tp}')
        logger.log_message(f'Stop loss: {sl}')
        logger.log_message('-----------------')

        log_operation_start(config.LOG_PATH, config.PIN, config.TRADING_PARAMS, operation_data)

        notification_title = f'{operation_type.get("emoji","?")}{operation_type["name"]}\n{tick}'
        notification_message = f'Entry Price: {current_price}\nTake profit: {tp}\nStop loss: {sl}'
        notification_service.show_notification(notification_title, notification_message)
        notification_service.play_alert_sound()

        # Send updated stats and active operations list
        send_stats_to_server()
        send_active_operations_to_server()

    except KeyError as e:
        logger.log_message(f"Error accessing config or results key during operation trigger: {e}", "RED")
    except Exception as e:
        logger.log_message(f"Unexpected error triggering operation for {tick}: {e}", "RED")


# --- Evaluation Logic ---

def evaluate_variation_from_klines(tick, klines):
    """Evaluates price variations from kline data."""
    if not klines or len(klines) < 2:
        return
    try:
        first_candle_index = 0
        last_closed_candle_index = len(klines) - 1
        initial_price = float(klines[first_candle_index][4])
        final_price = float(klines[last_closed_candle_index][4])
        if initial_price == 0: return

        if initial_price > final_price:
            variation = calculate_variation(initial_price, final_price)
            process_entry_condition(tick, variation, config.LONG_NAME, final_price)
        elif final_price > initial_price:
            variation = calculate_variation(final_price, initial_price)
            process_entry_condition(tick, variation, config.SHORT_NAME, final_price)

        if len(klines) >= 3:
            prev_prev_price = float(klines[last_closed_candle_index - 2][4])
            current_price = final_price
            if prev_prev_price == 0: return
            if current_price > prev_prev_price:
                fast_variation = calculate_variation(current_price, prev_prev_price)
                var_fast_perc = config.TRADING_PARAMS.get('VARIATION_FAST_PERCENTAGE', 1.0)
                if fast_variation >= var_fast_perc:
                    trigger_new_operation(tick, config.TYPE_DEFINITIONS[config.FAST_SHORT_NAME], current_price)
    except IndexError:
        logger.log_message(f"Index error evaluating variation for {tick} (klines len: {len(klines)}).", "RED")
    except (ValueError, TypeError) as e:
        logger.log_message(f"Data error evaluating variation for {tick}: {e}", "RED")
    except Exception as e:
        logger.log_message(f"Unexpected error in evaluate_variation_from_klines for {tick}: {e}", "RED")


def evaluate_active_operations():
    """Evaluates the evolution of all active operations."""
    operations_to_finalize = []
    stats_changed = False
    active_ops_list_updated = False # Flag to check if differences updated

    active_ticks = [tick for tick, op in possible_operations.items() if op.get('is_active', False)]
    if not active_ticks:
        return

    for tick in active_ticks:
        operation_data = possible_operations.get(tick)
        if not operation_data or not operation_data.get('is_active'):
            continue

        try:
            info = binance_service.get_futures_ticker_info(tick)
            if info is None or 'lastPrice' not in info:
                logger.log_message(f"Could not get current price for {tick} during evaluation.", "RED")
                continue

            current_price = float(info['lastPrice'])
            entry_price = operation_data['entry_price']
            operation_type = operation_data['type']

            difference = calculate_difference(entry_price, current_price, operation_type)

            # --- Store the latest difference in the operation data ---
            if operation_data.get('last_difference') != difference:
                possible_operations[tick]['last_difference'] = difference
                active_ops_list_updated = True # Mark that differences changed

            color = "GREEN" if difference >= 0 else "RED"
            tp_str = f"{operation_data.get('tp', 'N/A'):.8f}" if isinstance(operation_data.get('tp'), float) else 'N/A'
            sl_str = f"{operation_data.get('sl', 'N/A'):.8f}" if isinstance(operation_data.get('sl'), float) else 'N/A'
            logger.log_message(f"Eval: {tick} ({operation_type['name']}) Diff: {difference:.2f}%", color)

            log_operation_progress(config.LOG_PATH, operation_data, current_price, difference)

            deactivate, final_status = check_deactivation(operation_type, current_price, operation_data)

            if deactivate:
                logger.log_message(f"Operation {tick} hit {final_status} at price {current_price:.8f} (Diff: {difference:.2f}%)", "GREEN" if final_status == config.WIN_NAME else "RED")
                operations_to_finalize.append({
                    'tick': tick,
                    'final_status': final_status,
                    'final_price': current_price,
                    'final_difference': difference,
                    'operation_data': operation_data
                })
                stats_changed = True
                active_ops_list_updated = True # List will change as one is removed

        except (ValueError, TypeError) as e:
            logger.log_message(f"Data error evaluating operation {tick}: {e}", "RED")
        except Exception as e:
            logger.log_message(f"Unexpected error evaluating operation {tick}: {e}", "RED")

    # --- Finalize Operations ---
    if operations_to_finalize:
        logger.log_message(f"[Eval] Finalizing {len(operations_to_finalize)} operations.")

    for item in operations_to_finalize:
        tick_to_finalize = item['tick']
        op_data = item['operation_data']
        op_type = op_data['type']
        final_status = item['final_status']

        if tick_to_finalize in possible_operations:
            possible_operations[tick_to_finalize]['is_active'] = False
            possible_operations[tick_to_finalize]['status'] = final_status
            possible_operations[tick_to_finalize]['final_price'] = item['final_price']
            possible_operations[tick_to_finalize]['final_difference'] = item['final_difference']
            possible_operations[tick_to_finalize]['end_time'] = time.time()

            try:
                results[final_status][op_type['name']] += 1
                if results[config.IN_PROGRESS_NAME][op_type['name']] > 0:
                    results[config.IN_PROGRESS_NAME][op_type['name']] -= 1
                else:
                    logger.log_message(f"Warning: In-progress count for {op_type['name']} was already 0 when finalizing {tick_to_finalize}.", "YELLOW")
            except KeyError:
                logger.log_message(f"Error: Key not found updating results for {tick_to_finalize} ({op_type['name']}/{final_status}).", "RED")

            finalize_operation_log(config.LOG_PATH, op_data, final_status, item['final_price'], item['final_difference'])
        else:
            logger.log_message(f"Error: Tried to finalize operation {tick_to_finalize}, but it was not found in possible_operations.", "RED")

    # --- Save Aggregated Results and Send Updates if Changed ---
    if stats_changed:
        save_aggregated_results() # Sends both stats and active ops list
    elif active_ops_list_updated:
        # Only send updated active ops if stats didn't change but differences did
        send_active_operations_to_server()


def save_aggregated_results():
    """Calculates stats, saves results summary to JSON, and sends updates to server."""
    stats = None
    try:
        in_progress_count = sum(results.get(config.IN_PROGRESS_NAME, {}).values())
        winning_count = sum(results.get(config.WIN_NAME, {}).values())
        losing_count = sum(results.get(config.LOSE_NAME, {}).values())
        total_finished = winning_count + losing_count
        efficiency = round(winning_count * 100 / total_finished, 2) if total_finished > 0 else 0.0

        stats = {
            "in_progress_operations_count": in_progress_count,
            "winning_operations_count": winning_count,
            "losing_operations_count": losing_count,
            "total_finished_operations": total_finished,
            "total_operations_recorded": total_finished + in_progress_count,
            "finished_operations_efficiency_percentage": efficiency,
        }

        if config.ACTIVE_LOG:
            log_results_to_json(config.LOG_PATH, config.PIN, results, stats)

        # Send both stats and the updated active operations list
        send_stats_to_server()
        send_active_operations_to_server()

    except Exception as e:
        logger.log_message(f"Error calculating/saving aggregated results or sending updates: {e}", "RED")


# --- Main Execution Cycles ---

def scanner_cycle():
    """Periodically scans coins for potential entries."""
    while True:
        try:
            if not binance_service.is_connected():
                logger.log_message("Scanner: Binance client not connected, skipping scan.", "RED")
                time.sleep(config.SCAN_TICKER_CYCLE_TIME)
                continue

            symbols = binance_service.get_usdt_futures_symbols()
            if not symbols:
                logger.log_message("Scanner: No USDT symbols found or error fetching.", "YELLOW")
            else:
                processed_count = 0
                for tick in symbols:
                    klines = binance_service.get_futures_klines(tick, limit=30)
                    if klines:
                        evaluate_variation_from_klines(tick, klines)
                        processed_count += 1
        except Exception as e:
            logger.log_message(f"CRITICAL error in scanner cycle: {e}", "RED")
            time.sleep(config.SCAN_TICKER_CYCLE_TIME * 2)
        time.sleep(config.SCAN_TICKER_CYCLE_TIME)


def evaluation_cycle():
    """Periodically evaluates active operations."""
    logger.log_message("Evaluation cycle started.", "GREEN")
    while True:
        try:
            time.sleep(config.EVALUATION_CYCLE_TIME)
            if not binance_service.is_connected():
                logger.log_message("Evaluator: Binance client not connected, skipping evaluation.", "RED")
                continue
            evaluate_active_operations() # This now handles sending updates if needed
        except Exception as e:
            logger.log_message(f"CRITICAL error in evaluation cycle: {e}", "RED")
            time.sleep(config.EVALUATION_CYCLE_TIME) # Wait even after error


def connect_to_socketio_server():
    """Attempts to connect to the Socket.IO server."""
    original_log_message(f"Attempting to connect to Socket.IO server at {config.SERVER_URL}...")
    try:
        sio_client.connect(config.SERVER_URL, wait_timeout=10)
    except socketio.exceptions.ConnectionError as e:
        original_log_message(f"Could not connect to Socket.IO server: {e}. Web logs/stats unavailable.", "RED")
    except Exception as e:
        original_log_message(f"Unexpected error connecting to Socket.IO server: {e}", "RED")


def main():
    """Main function to start the bot."""
    try:
        config.print_config_summary()
    except Exception as e:
        original_log_message(f"Error printing config summary: {e}", "RED")

    setup_file_logging(config.LOG_PATH)

    if not binance_service.is_connected():
        original_log_message("CRITICAL: Binance client failed to initialize. Bot cannot start.", "RED")
        sys.exit(1)

    connect_to_socketio_server()

    logger.log_message(f'Starting Trading Bot Cycles... PIN: {config.PIN}', 'GREEN')

    scanner_thread = threading.Thread(target=scanner_cycle, daemon=True)
    evaluation_thread = threading.Thread(target=evaluation_cycle, daemon=True)

    scanner_thread.start()
    evaluation_thread.start()

    try:
        while True:
            if not connected_to_server:
                original_log_message("Attempting to reconnect to Socket.IO server...")
                connect_to_socketio_server()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.log_message("\nInterruption received (Ctrl+C). Stopping bot...", "RED")
    except Exception as e:
        logger.log_message(f"\nUNEXPECTED ERROR in main loop: {e}. Stopping bot...", "RED")
    finally:
        if connected_to_server:
            logger.log_message("Disconnecting from Socket.IO server...")
            sio_client.disconnect()
        original_log_message("Trading Bot cycles terminating.")
        original_log_message("Trading Bot script finished.")
        print("Trading Bot script finished.")


if __name__ == "__main__":
    main()
