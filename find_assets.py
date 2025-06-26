import requests
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime, timedelta
import numpy as np

# --- Criterios de Filtrado (Ajusta si es necesario) ---
MAX_VOLUME_USDT = 75_000_000  # Menor que 75 Millones USDT
MIN_ATR_PERCENT = 10.0        # Mayor que 10%
MAX_OPEN_INTEREST_USDT = 20_000_000  # Menor que 20 Millones USDT
ATR_PERIOD = 14
# Días de velas a pedir (14 para ATR + 1 para cálculo + 1 extra)
KLINE_LIMIT = ATR_PERIOD + 2

# --- Lista de Símbolos Candidatos (¡¡IMPORTANTE: EDITA ESTA LISTA!!) ---
# Debes obtener esta lista revisando los anuncios de Binance Futures
# de los últimos ~3 meses (https://www.binance.com/en/support/announcement/c-49?navId=49)
# Asegúrate que sean perpetuos USDT-M y que existan en la API (algunos pueden ser eliminados)
candidate_symbols = ['SUSDT', 'ZETAUSDT', 'GRTUSDT', 'LINKUSDT', 'ALTUSDT', 'EIGENUSDT', 'JOEUSDT', 'ETHWUSDT', 'RENDERUSDT', 'BALUSDT', 'OMGUSDT', 'MANAUSDT', 'BSVUSDT', 'VINEUSDT', 'EGLDUSDT', 'FLMUSDT', 'STXUSDT', 'EOSUSDT', 'SANDUSDT', 'BCHUSDT', 'APTUSDT', 'DENTUSDT', 'GRIFFAINUSDT', 'LOOMUSDT', 'RSRUSDT', 'RAYSOLUSDT', 'FORMUSDT', 'WUSDT', 'LTCUSDT', 'AVAAIUSDT', 'SWELLUSDT', 'AEROUSDT', 'INITUSDT', 'BRETTUSDT', 'TUSDT', '1000SATSUSDT', 'BABYUSDT', 'AVAXUSDT', 'LPTUSDT', '1000CATUSDT', 'TONUSDT', 'BLZUSDT', 'HEIUSDT', 'MANTAUSDT', '1000BONKUSDT', 'BANKUSDT', 'BTCDOMUSDT', 'FARTCOINUSDT', 'ANIMEUSDT', 'INJUSDT', 'MOVRUSDT', 'BOMEUSDT', 'DIAUSDT', 'ALICEUSDT', 'ACXUSDT', 'MKRUSDT', 'ICXUSDT', 'RVNUSDT', 'TRUUSDT', 'DUSDT', 'XRPUSDT', 'PNUTUSDT', 'BNTUSDT', 'KERNELUSDT', '1000SHIBUSDT', 'KLAYUSDT', 'LAYERUSDT', 'EPTUSDT', 'ANKRUSDT', 'API3USDT', '1INCHUSDT', 'XCNUSDT', 'TOKENUSDT', 'MTLUSDT', 'RPLUSDT', 'COWUSDT', 'ROSEUSDT', 'FXSUSDT', 'NULSUSDT', 'GMXUSDT', 'FUNUSDT', 'HIGHUSDT', 'POWRUSDT', 'WCTUSDT', 'BADGERUSDT', 'MEWUSDT', 'QUICKUSDT', 'ACTUSDT', 'MUBARAKUSDT', 'PIPPINUSDT', '1000WHYUSDT', 'WIFUSDT', 'BONDUSDT', 'TROYUSDT', 'BICOUSDT', 'ETCUSDT', 'DOTUSDT', 'ORDIUSDT', 'NTRNUSDT', 'ZKUSDT', '1000RATSUSDT', 'CYBERUSDT', 'VIRTUALUSDT', 'AKTUSDT', '1000LUNCUSDT', 'ZILUSDT', 'STEEMUSDT', 'GOATUSDT', 'PHBUSDT', 'STGUSDT', 'WAVESUSDT', 'JASMYUSDT', 'AEVOUSDT', 'IDEXUSDT', 'ARKMUSDT', 'CAKEUSDT', 'DYMUSDT', 'KMNOUSDT', 'AERGOUSDT', 'USDCUSDT', 'MBOXUSDT', 'BNBUSDT', 'HOOKUSDT', 'MYROUSDT', 'REDUSDT', 'SYNUSDT', 'CHRUSDT', 'BATUSDT', 'IMXUSDT', 'POPCATUSDT', 'GLMRUSDT', 'COMBOUSDT', 'NEOUSDT', 'KEYUSDT', 'CTKUSDT', 'VVVUSDT', 'ALPACAUSDT', 'PUMPUSDT', 'ONDOUSDT', 'LEVERUSDT', '1000XUSDT', 'MOODENGUSDT', 'NFPUSDT', 'WAXPUSDT', 'BLURUSDT', 'DASHUSDT', 'MAVUSDT', 'LQTYUSDT', 'PLUMEUSDT', 'PYTHUSDT', 'NEIROETHUSDT', 'DEFIUSDT', 'VANRYUSDT', 'TWTUSDT', 'STRKUSDT', 'SYSUSDT', 'OMUSDT', 'MDTUSDT', 'TRXUSDT', 'SUNUSDT', 'CVXUSDT', 'ACHUSDT', 'STPTUSDT', 'ALCHUSDT', 'PROMPTUSDT', 'JUPUSDT', 'VETUSDT', 'DOGSUSDT', 'PHAUSDT', 'CELRUSDT', 'MOCAUSDT', 'SCRTUSDT', 'CATIUSDT', 'NEIROUSDT', 'FHEUSDT', 'SNXUSDT', 'SHELLUSDT', 'BBUSDT', 'SIRENUSDT', 'RENUSDT', 'SOLUSDT', 'ETHFIUSDT', 'ZRXUSDT', 'KASUSDT', 'ADAUSDT', 'KNCUSDT', 'LINAUSDT', 'RIFUSDT', 'ARCUSDT', 'LSKUSDT', 'UNFIUSDT', 'WOOUSDT', 'BROCCOLIF3BUSDT', 'MEMEUSDT', 'AXLUSDT', 'RADUSDT', 'DGBUSDT', 'LISTAUSDT', 'BERAUSDT', 'EDUUSDT', 'GMTUSDT', 'GUSDT', 'WLDUSDT', 'PENGUUSDT', 'MORPHOUSDT', 'THEUSDT', 'DEEPUSDT', 'GALAUSDT', 'BIOUSDT', 'OXTUSDT', 'ZROUSDT', 'MEMEFIUSDT', 'ASTRUSDT', 'STOUSDT', 'NILUSDT', 'MINAUSDT', 'XVGUSDT',
                     'ZEREBROUSDT', 'COOKIEUSDT', 'APEUSDT', 'MEUSDT', 'VOXELUSDT', 'VTHOUSDT', 'SUPERUSDT', 'B3USDT', 'AGLDUSDT', 'DUSKUSDT', 'BANANAUSDT', 'UMAUSDT', 'SPXUSDT', 'CELOUSDT', 'RONINUSDT', 'UNIUSDT', 'JTOUSDT', 'MAVIAUSDT', 'LUMIAUSDT', 'CHZUSDT', 'XMRUSDT', 'PONKEUSDT', 'NOTUSDT', 'TUTUSDT', 'FIOUSDT', 'COMPUSDT', 'ZENUSDT', 'POLUSDT', 'AMBUSDT', 'TNSRUSDT', 'ATOMUSDT', 'KAITOUSDT', 'RLCUSDT', 'HOTUSDT', 'FISUSDT', 'IOTAUSDT', 'QTUMUSDT', 'ALPHAUSDT', 'BNXUSDT', 'NKNUSDT', 'PERPUSDT', 'CHILLGUYUSDT', 'BMTUSDT', 'USUALUSDT', 'PORTALUSDT', 'GHSTUSDT', 'GLMUSDT', 'ACEUSDT', 'ARBUSDT', 'BAKEUSDT', 'ARKUSDT', 'SUIUSDT', 'REEFUSDT', 'BANDUSDT', 'SNTUSDT', 'SAGAUSDT', 'ONTUSDT', 'ALGOUSDT', 'DARUSDT', 'HIVEUSDT', 'REIUSDT', 'KAVAUSDT', 'POLYXUSDT', 'REZUSDT', 'IPUSDT', 'AGIXUSDT', 'LOKAUSDT', 'RAREUSDT', 'OCEANUSDT', 'LDOUSDT', 'HYPERUSDT', 'AIUSDT', 'TIAUSDT', 'AI16ZUSDT', 'SPELLUSDT', 'SONICUSDT', 'NEARUSDT', 'PROMUSDT', 'BANUSDT', 'BTCUSDT', 'CFXUSDT', 'XLMUSDT', 'PIXELUSDT', 'XTZUSDT', 'CKBUSDT', 'TURBOUSDT', '1000XECUSDT', 'DEXEUSDT', 'ENSUSDT', 'HIFIUSDT', 'METISUSDT', 'BRUSDT', 'VIDTUSDT', 'YGGUSDT', 'SANTOSUSDT', 'COTIUSDT', 'ONGUSDT', 'GASUSDT', 'SLERFUSDT', 'AUCTIONUSDT', 'FORTHUSDT', 'VELODROMEUSDT', 'ARPAUSDT', 'COSUSDT', 'HMSTRUSDT', 'AAVEUSDT', 'JELLYJELLYUSDT', 'ATHUSDT', 'CRVUSDT', 'SKLUSDT', 'ICPUSDT', 'EPICUSDT', 'BIGTIMEUSDT', 'XVSUSDT', 'ATAUSDT', 'FTMUSDT', 'BANANAS31USDT', 'YFIUSDT', 'STMXUSDT', 'PARTIUSDT', 'STRAXUSDT', '1MBABYDOGEUSDT', 'XAIUSDT', 'PENDLEUSDT', 'TRBUSDT', 'ZECUSDT', 'RUNEUSDT', 'DRIFTUSDT', 'AXSUSDT', 'DOGEUSDT', 'ONEUSDT', 'XEMUSDT', 'CETUSUSDT', 'MAGICUSDT', 'ILVUSDT', 'GUNUSDT', 'QNTUSDT', 'MELANIAUSDT', 'LITUSDT', 'ENJUSDT', 'PAXGUSDT', 'FILUSDT', 'SOLVUSDT', 'IOUSDT', 'ORCAUSDT', 'TSTUSDT', '1000000MOGUSDT', 'AIXBTUSDT', 'DYDXUSDT', 'IOSTUSDT', 'SEIUSDT', 'THETAUSDT', 'DFUSDT', 'FETUSDT', 'SLPUSDT', 'OPUSDT', 'SXPUSDT', 'SWARMSUSDT', 'LUNA2USDT', 'VICUSDT', 'TRUMPUSDT', '1000PEPEUSDT', 'CGPTUSDT', 'GTCUSDT', 'CTSIUSDT', 'FIDAUSDT', 'BROCCOLI714USDT', 'SSVUSDT', 'BELUSDT', 'ARUSDT', 'CHESSUSDT', '1000FLOKIUSDT', 'MOVEUSDT', 'FLUXUSDT', 'MLNUSDT', 'WALUSDT', 'TLMUSDT', 'ENAUSDT', 'GPSUSDT', 'ORBSUSDT', 'DEGENUSDT', 'TAOUSDT', 'HBARUSDT', 'DODOXUSDT', 'SUSHIUSDT', 'PEOPLEUSDT', 'MASKUSDT', 'SCRUSDT', 'BEAMXUSDT', 'BIDUSDT', 'OGNUSDT', 'HIPPOUSDT', 'BSWUSDT', 'NMRUSDT', 'OMNIUSDT', 'SFPUSDT', 'FLOWUSDT', 'SAFEUSDT', 'GRASSUSDT', 'USTCUSDT', 'LRCUSDT', 'RDNTUSDT', 'HFTUSDT', '1000CHEEMSUSDT', 'UXLINKUSDT', 'ETHUSDT', 'KDAUSDT', 'AVAUSDT', 'STORJUSDT', 'KSMUSDT', 'KOMAUSDT', 'VANAUSDT', 'C98USDT', 'DEGOUSDT', 'KAIAUSDT', 'IOTXUSDT', 'IDUSDT']

# --- URLs API Binance Futuros USD-M ---
BASE_URL = "https://fapi.binance.com"
TICKER_URL = f"{BASE_URL}/fapi/v1/ticker/24hr"
KLINES_URL = f"{BASE_URL}/fapi/v1/klines"
OPEN_INTEREST_URL = f"{BASE_URL}/fapi/v1/openInterest"
# Usaremos Mark Price para OI en USDT
MARK_PRICE_URL = f"{BASE_URL}/fapi/v1/premiumIndex"

# --- Función para obtener datos ---


def get_binance_data(url, params=None):
    """Obtiene datos de la API de Binance."""
    try:
        response = requests.get(
            url, params=params, timeout=10)  # Timeout de 10 seg
        response.raise_for_status()  # Lanza error para respuestas 4xx/5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  -> Error API ({url}): {e}")
        return None


# --- Procesamiento ---
qualifying_symbols = []
print(f"Analizando {len(candidate_symbols)} símbolos candidatos...")
print(
    f"Criterios: Vol < ${MAX_VOLUME_USDT/1e6:.1f}M, ATR% > {MIN_ATR_PERCENT:.1f}%, OI < ${MAX_OPEN_INTEREST_USDT/1e6:.1f}M")
print("-" * 30)

# Obtener datos de Ticker para todos los símbolos (más eficiente)
all_tickers_data = get_binance_data(TICKER_URL)
if not all_tickers_data:
    print("Error fatal: No se pudieron obtener los datos del ticker 24hr.")
    exit()

# Crear un diccionario para búsqueda rápida de ticker data por símbolo
ticker_map = {item['symbol']: item for item in all_tickers_data}

for symbol in candidate_symbols:
    print(f"Evaluando {symbol}...")
    passed_volume = False
    passed_atr = False
    passed_oi = False

    # --- 1. Chequeo de Volumen ---
    ticker_data = ticker_map.get(symbol)
    if ticker_data and 'quoteVolume' in ticker_data:
        volume_24h_usdt = float(ticker_data['quoteVolume'])
        if volume_24h_usdt < MAX_VOLUME_USDT:
            passed_volume = True
            print(f"  [V] Volumen OK: ${volume_24h_usdt/1e6:.2f}M")
        else:
            print(f"  [X] Volumen Alto: ${volume_24h_usdt/1e6:.2f}M")
            time.sleep(0.2)  # Pequeña pausa
            continue  # Pasar al siguiente símbolo si no cumple volumen
    else:
        print(
            f"  [?] No se encontró Ticker data para {symbol} o falta 'quoteVolume'. Saltando.")
        time.sleep(0.2)
        continue

    # --- 2. Chequeo de ATR% Diario ---
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=KLINE_LIMIT + 5)
                      ).timestamp() * 1000)  # Pedir un poco más por si acaso
    kline_params = {'symbol': symbol, 'interval': '1d',
                    'limit': KLINE_LIMIT, 'endTime': end_time}
    kline_data = get_binance_data(KLINES_URL, params=kline_params)

    if kline_data and len(kline_data) >= ATR_PERIOD + 1:
        # Convertir a DataFrame
        klines_df = pd.DataFrame(kline_data, columns=[
            'Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close time',
            'Quote asset volume', 'Number of trades', 'Taker buy base asset volume',
            'Taker buy quote asset volume', 'Ignore'
        ])
        klines_df['Open'] = klines_df['Open'].astype(float)
        klines_df['High'] = klines_df['High'].astype(float)
        klines_df['Low'] = klines_df['Low'].astype(float)
        klines_df['Close'] = klines_df['Close'].astype(float)
        klines_df['Volume'] = klines_df['Volume'].astype(float)
        klines_df['Timestamp'] = pd.to_datetime(
            klines_df['Close time'], unit='ms')
        klines_df.set_index('Timestamp', inplace=True)

        # Calcular ATR y ATR%
        klines_df.ta.atr(length=ATR_PERIOD, append=True)
        # --- IMPORTANTE: Verifica el nombre real de la columna ATR aquí también ---
        atr_col_name = next(
            (col for col in klines_df.columns if col.startswith('ATR')), None)
        if atr_col_name:
            klines_df.dropna(subset=[atr_col_name, 'Close'], inplace=True)
            # Evitar división por cero
            if not klines_df.empty and klines_df['Close'].iloc[-1] > 0:
                # Último valor de ATR
                atr_value = klines_df[atr_col_name].iloc[-1]
                atr_percent = (atr_value / klines_df['Close'].iloc[-1]) * 100

                if atr_percent > MIN_ATR_PERCENT:
                    passed_atr = True
                    print(f"  [V] ATR% OK: {atr_percent:.2f}%")
                else:
                    print(f"  [X] ATR% Bajo: {atr_percent:.2f}%")
            else:
                print(
                    f"  [?] No se pudo calcular ATR% (Close=0 o DF vacío después de dropna).")
        else:
            print(f"  [?] No se pudo calcular ATR (columna no encontrada).")

    else:
        print(
            f"  [?] Datos de Klines insuficientes o error API para calcular ATR%. ({len(kline_data) if kline_data else 0} velas)")

    if not passed_atr:
        time.sleep(0.2)
        continue  # Pasar al siguiente si no cumple ATR%

    # --- 3. Chequeo de Open Interest ---
    oi_data = get_binance_data(OPEN_INTEREST_URL, params={'symbol': symbol})
    mp_data = get_binance_data(MARK_PRICE_URL, params={'symbol': symbol})

    if oi_data and 'openInterest' in oi_data and mp_data and 'markPrice' in mp_data:
        try:
            open_interest_base = float(oi_data['openInterest'])
            mark_price = float(mp_data['markPrice'])
            if mark_price > 0:  # Evitar división o multiplicación por cero
                open_interest_usdt = open_interest_base * mark_price
                if open_interest_usdt < MAX_OPEN_INTEREST_USDT:
                    passed_oi = True
                    print(
                        f"  [V] Open Interest OK: ${open_interest_usdt/1e6:.2f}M")
                else:
                    print(
                        f"  [X] Open Interest Alto: ${open_interest_usdt/1e6:.2f}M")
            else:
                print(
                    f"  [?] Precio Mark inválido ({mark_price}) para calcular OI en USDT.")
        except ValueError:
            print(f"  [?] Error convirtiendo OI o Mark Price a número.")
    else:
        print(
            f"  [?] No se pudo obtener Open Interest o Mark Price para {symbol}.")

    # --- Decisión Final ---
    if passed_volume and passed_atr and passed_oi:
        print(f"  --> {symbol} CUMPLE TODOS LOS CRITERIOS")
        qualifying_symbols.append(symbol)
    else:
        print(f"  --> {symbol} NO CUMPLE.")

    # Pausa para evitar rate limits de Binance API
    time.sleep(0.3)  # Ajusta si recibes errores 429 o 418

print("-" * 30)
print("\n--- Símbolos Cualificados ---")
if qualifying_symbols:
    print(
        f"Se encontraron {len(qualifying_symbols)} símbolos que cumplen los criterios:")
    for sym in qualifying_symbols:
        print(f"- {sym}")
else:
    print("No se encontraron símbolos que cumplan todos los criterios con los umbrales definidos.")
print("-" * 30)
