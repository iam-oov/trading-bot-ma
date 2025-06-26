# main.py

from application.app_config import configure_app
import time


def main():
    # Puedes cambiar 'bybit' por 'binance' para cambiar el proveedor de datos
    alarm_evaluator = configure_app(exchange_to_use='bybit')

    # Ejemplo de configuración de una alarma (esto podría venir de una DB o un archivo)
    my_alarm_config = {
        'symbol': 'ETHUSDT',
        'interval': '1h',
        'condition_type': 'price_below',  # O 'price_above'
        'threshold': 3500.0              # Precio en USD
    }

    print("\nIniciando monitoreo de alarma (Ctrl+C para salir)...")
    while True:
        try:
            alarm_triggered = alarm_evaluator.evaluate_alarm(my_alarm_config)
            if alarm_triggered:
                print(
                    f"¡ALERTA! Alarma disparada para {my_alarm_config['symbol']} (precio {'por debajo' if my_alarm_config['condition_type'] == 'price_below' else 'por encima'} de {my_alarm_config['threshold']})")
                # Aquí podrías añadir lógica para enviar notificaciones, ejecutar operaciones, etc.
                break  # Para el ejemplo, salimos después de disparar una vez
            else:
                print(
                    f"Alarma para {my_alarm_config['symbol']} no disparada. (Umbral: {my_alarm_config['threshold']})")

            time.sleep(10)  # Espera 10 segundos antes de la próxima evaluación
        except KeyboardInterrupt:
            print("\nMonitoreo de alarma detenido.")
            break
        except Exception as e:
            print(f"Error general en el bucle principal: {e}")
            # Espera más si hay un error para evitar bucles rápidos
            time.sleep(30)


if __name__ == "__main__":
    main()
