# server.py
import config
import json
import os
import sys
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, send_from_directory, request
import eventlet
eventlet.monkey_patch()  # Important: Patch standard libraries for eventlet


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from logger_module import logger
except ImportError as e:
    print("Error: Could not import 'logger' from 'logger_module'. Ensure the file exists and has no errors.")
    print(f"Error details: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error importing logger_module: {e}", file=sys.stderr)
    sys.exit(1)


# --- Flask App Setup ---
template_dir = os.path.abspath(os.path.join(
    os.path.dirname(__file__), 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))

if not os.path.exists(os.path.join(template_dir, 'index.html')):
    print(
        f"Error: Template file 'index.html' not found in '{template_dir}'", file=sys.stderr)
    sys.exit(1)

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config['SECRET_KEY'] = os.environ.get(
    'FLASK_SECRET_KEY', 'a_default_secret_key_for_dev!')

# --- SocketIO Setup ---
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# --- Store last known state ---
last_stats = {"message": "Esperando estadísticas del bot..."}
last_active_ops = []  # Store list of active operations

# --- Routes ---


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/static/<path:filename>')
def static_files(filename):
    if not os.path.isdir(app.static_folder):
        print(
            f"Error: Static folder '{app.static_folder}' not found.", file=sys.stderr)
        return "Static folder not found", 404
    if '..' in filename or filename.startswith('/'):
        return "Invalid path", 400
    return send_from_directory(app.static_folder, filename)


# --- SocketIO Event Handlers ---

@socketio.on('connect')
def handle_web_connect():
    """Handles new WebSocket connections from web browsers."""
    client_sid = request.sid
    logger.log_message(f'Web client connected: {client_sid}')
    try:
        # Send the global configuration
        global_config = {
            'trading_params': config.TRADING_PARAMS,
            'business_params': {
                'MAX_CONCURRENT_OPERATIONS': config.MAX_CONCURRENT_OPERATIONS,
                'EVALUATION_CYCLE_TIME': config.EVALUATION_CYCLE_TIME,
            }
        }
        emit('global_config', global_config, room=client_sid)

        # Send existing logs
        existing_logs = logger.get_all_logs_for_web()
        for msg, color_style in existing_logs:
            emit('new_log', {'message': msg,
                 'color': color_style}, room=client_sid)

        # Send last known stats
        if last_stats:
            emit('stats_update', last_stats, room=client_sid)

        # --- Send last known active operations ---
        if last_active_ops:
            emit('active_ops_update', last_active_ops, room=client_sid)

    except Exception as e:
        logger.log_message(
            f"Error getting or sending existing data to {client_sid}: {e}", "RED")


@socketio.on('disconnect')
def handle_web_disconnect():
    """Handles WebSocket disconnections from web browsers."""
    client_sid = request.sid
    logger.log_message(f'Web client disconnected: {client_sid}')

# Handler for logs


@socketio.on('log_from_script')
def handle_log_from_script(data):
    """Receives logs from bot and relays to browsers."""
    message = data.get('message', '')
    color_style = data.get('color', 'color: black;')
    log_data_for_web = {'message': message, 'color': color_style}
    emit('new_log', log_data_for_web, broadcast=True)

# Handler for stats


@socketio.on('stats_from_script')
def handle_stats_from_script(data):
    """Receives statistics from bot and relays to browsers."""
    global last_stats
    if isinstance(data, dict):
        last_stats = data
        emit('stats_update', data, broadcast=True)
    else:
        logger.log_message(
            f"Received invalid stats data format from script: {type(data)}", "RED")


@socketio.on('active_ops_from_script')
def handle_active_ops_from_script(data):
    """Receives active operations list from bot and relays to browsers."""
    global last_active_ops
    if isinstance(data, list):
        last_active_ops = data  # Update last known list
        # Broadcast the new list
        emit('active_ops_update', data, broadcast=True)
    else:
        logger.log_message(
            f"Received invalid active ops data format from script: {type(data)}", "RED")


# --- Main Execution ---
if __name__ == '__main__':
    print("-----------------------------------------------------")
    print("Starting Flask-SocketIO server...")
    # ... (rest of the startup messages) ...
    print("-----------------------------------------------------")
    print("Server accessible at http://127.0.0.1:5000")
    print("-----------------------------------------------------")
    try:
        socketio.run(app, host='0.0.0.0', port=5000,
                     debug=False, use_reloader=False)
    except Exception as e:
        print(f"Failed to start server: {e}", file=sys.stderr)
        sys.exit(1)
    print("Server shutdown.")
