import subprocess
import sys
import time
import os
import signal

def run_script(script_name, args=[]):
    """
    Ejecuta un script Python especificado en un subproceso.

    Args:
        script_name (str): El nombre del archivo .py a ejecutar.
        args (list): Una lista de argumentos de línea de comandos para pasar al script.

    Returns:
        subprocess.Popen: El objeto del proceso iniciado, o None si falla.
    """
    # Asegura que se use el mismo intérprete de Python que ejecuta el runner
    python_executable = sys.executable
    # Construye la ruta completa al script asumiendo que está en el mismo directorio
    script_path = os.path.join(os.path.dirname(__file__), script_name)

    # Verifica si el script existe antes de intentar ejecutarlo
    if not os.path.exists(script_path):
        print(f"Error: El script '{script_path}' no fue encontrado.")
        return None

    command = [python_executable, script_path] + args
    print(f"Iniciando: {' '.join(command)}")
    try:
        # Inicia el subproceso.
        # stdout y stderr se mostrarán en la consola del runner.
        # preexec_fn es para manejar señales correctamente en Unix/Linux/macOS
        process = subprocess.Popen(command, preexec_fn=os.setsid if os.name != 'nt' else None)
        return process
    except FileNotFoundError:
        print(f"Error: No se encontró el ejecutable de Python '{python_executable}' o tuvo problemas.")
        return None
    except Exception as e:
        print(f"Error al iniciar '{script_name}': {e}")
        return None

if __name__ == "__main__":
    # Obtener argumentos para trading_bot.py (todos excepto el nombre del runner)
    trading_bot_args = sys.argv[1:]

    server_process = None
    bot_process = None
    processes = [] # Lista para mantener los procesos activos

    original_sigint_handler = signal.getsignal(signal.SIGINT)

    def signal_handler(sig, frame):
        """Manejador de señal para terminar subprocesos en Ctrl+C."""
        print("\nInterrupción detectada (Ctrl+C). Terminando procesos...")
        # Iterar en orden inverso podría ser más seguro si hay dependencias
        for p in reversed(processes):
            if p and p.poll() is None: # Si el proceso existe y sigue corriendo
                print(f"Terminando proceso {p.pid}...")
                try:
                    # Enviar SIGTERM (o SIGINT) al grupo de procesos en Unix
                    if os.name != 'nt':
                        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                    else: # En Windows, terminate es la mejor opción estándar
                        p.terminate()
                except ProcessLookupError:
                    print(f"Proceso {p.pid} ya no existía.")
                except Exception as e:
                    print(f"Error al terminar proceso {p.pid}: {e}")
        # Restaurar el handler original por si acaso
        signal.signal(signal.SIGINT, original_sigint_handler)
        # Salir del script principal
        sys.exit(1)

    # Registrar el manejador de señal para SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # 1. Iniciar server.py
        print("--- Iniciando Servidor (server.py) ---")
        server_process = run_script("server.py")
        if server_process:
            processes.append(server_process)
        else:
            print("Fallo al iniciar el servidor. Abortando.")
            sys.exit(1) # Salir si el servidor no pudo iniciar

        # 2. Esperar un poco para que el servidor esté listo
        wait_time = 3
        print(f"\n--- Esperando {wait_time} segundos para que el servidor inicie completamente... ---")
        time.sleep(wait_time)

        # 3. Iniciar trading_bot.py con sus argumentos
        print(f"\n--- Iniciando Bot de Trading (trading_bot.py) con args: {trading_bot_args} ---")
        bot_process = run_script("trading_bot.py", trading_bot_args)
        if bot_process:
            processes.append(bot_process)
        else:
            print("Fallo al iniciar el bot de trading. Terminando servidor...")
            # No es necesario llamar al signal_handler aquí, el finally lo hará
            raise RuntimeError("Fallo al iniciar el bot") # Provoca la ejecución del finally

        print("\n--- Servidor y Bot iniciados. Presiona Ctrl+C para detener todo. ---")

        # 4. Mantener el runner vivo y esperar a que los procesos terminen
        # Comprobar periódicamente si los procesos han terminado
        while True:
            all_terminated = True
            for p in processes:
                if p.poll() is None: # poll() devuelve None si sigue corriendo
                    all_terminated = False
                    break
            if all_terminated:
                print("Ambos subprocesos han terminado.")
                break
            time.sleep(5) # Revisar cada 5 segundos

    except Exception as e:
        print(f"\nError inesperado en el runner: {e}")
        # El signal_handler o el finally se encargarán de limpiar

    finally:
        # Asegurarse de que el signal handler se ejecute al final
        # si no se llamó por Ctrl+C (ej. si un proceso terminó inesperadamente)
        # Llama a la lógica de limpieza si no fue por KeyboardInterrupt
        if signal.getsignal(signal.SIGINT) == signal_handler:
            print("\n--- Limpieza final ---")
            # Llama a la misma lógica que el handler para asegurar la terminación
            for p in reversed(processes):
                if p and p.poll() is None:
                    print(f"Limpiando proceso {p.pid}...")
                    try:
                        if os.name != 'nt':
                            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                        else:
                            p.terminate()
                        p.wait(timeout=5) # Esperar un poco a que termine
                    except ProcessLookupError:
                        pass # Ya no existe
                    except subprocess.TimeoutExpired:
                        print(f"Proceso {p.pid} no terminó a tiempo, forzando...")
                        p.kill() # Forzar si terminate no funcionó
                    except Exception as e:
                        print(f"Error en limpieza final del proceso {p.pid}: {e}")

        print("Runner finalizado.")
