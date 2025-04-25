import asyncio
import websockets
import json


async def listen_to_currency(uri, currency_name):
    """
    Escucha el WebSocket de Binance para un par de criptomonedas específico.
    Args:
        uri (str): URI del WebSocket de Binance.
        currency_name (str): Nombre de la criptomoneda.
    """
    while True:
        try:

            async with websockets.connect(uri) as websocket:
                print(f"Conectado a {currency_name} en {uri}")

                while True:
                    try:
                        message = await websocket.recv()

                        try:
                            data = json.loads(message)

                            print(
                                f"[{currency_name}] Símbolo: {data.get('s', 'N/A')}, Precio: {data.get('c', 'N/A')}")
                        except json.JSONDecodeError:
                            print(
                                f"[{currency_name}] Mensaje no JSON recibido: {message}")
                        except Exception as e:
                            print(
                                f"[{currency_name}] Error procesando mensaje: {e}")
                            print(
                                f"[{currency_name}] Mensaje original: {message}")

                    except websockets.exceptions.ConnectionClosedOK:
                        print(f"[{currency_name}] Conexión cerrada limpiamente.")
                        break
                    except websockets.exceptions.ConnectionClosedError as e:
                        print(
                            f"[{currency_name}] Conexión cerrada con error: {e}")
                        break
                    except Exception as e:
                        print(
                            f"[{currency_name}] Error inesperado recibiendo: {e}")
                        break

        except websockets.exceptions.InvalidURI:
            print(f"[{currency_name}] Error: URI inválida - {uri}")
            break
        except ConnectionRefusedError:
            print(f"[{currency_name}] Error: Conexión rechazada por el servidor.")
        except Exception as e:
            print(f"[{currency_name}] Error conectando o en el bucle principal: {e}")

        print(f"[{currency_name}] Intentando reconectar en 5 segundos...")
        await asyncio.sleep(5)


async def main():
    uri_btc = "wss://fstream.binance.com/ws/btcusdt@ticker"

    task1 = asyncio.create_task(
        listen_to_currency(uri_btc, "Bitcoin (BTC/USDT)"))

    await asyncio.gather(task1)


if __name__ == "__main__":
    print("Iniciando cliente WebSocket...")
    print("Presiona Ctrl+C para detener.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCerrando conexiones...")
    finally:
        print("Programa terminado.")
