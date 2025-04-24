# Trading Bot MA (Moving Averages)

Un sistema de alertas de trading para el mercado de futuros de Binance, diseñado para identificar posibles oportunidades de trading basadas en variaciones de precio y análisis de medias móviles. Este bot NO ejecuta operaciones automáticas, sino que notifica al usuario sobre potenciales entradas para que éste, usando su experiencia y criterio, decida si seguirlas o no.

## Características principales

- 🔍 Análisis automatizado del mercado de futuros de Binance
- 🚨 Sistema de alertas para posibles oportunidades de trading
- 📈 Detección de patrones para estrategias: LONG, SHORT y FAST_SHORT
- 📊 Monitoreo en tiempo real de las señales activas
- 📱 Sistema de notificaciones integrado
- 📝 Registro detallado de alertas y sus resultados
- 🌐 Interfaz web para visualización de datos
- 🔔 Alertas sonoras para nuevas señales

## Requisitos previos

- Python 3.11+
- (Opcional) Claves de API de Binance (API key y Secret key)

## Instalación

1. Clona este repositorio:

   ```
   git clone <url-del-repositorio>
   cd trading-bot-ma
   ```

2. Instala las dependencias:

   ```
   pip install -r requirements.txt
   ```

   o

   ```
   uv sync
   source .venv/bin/activate
   ```

3. (Opcional) Configura tus claves de API de Binance editando el archivo `config.py`:

   ```python
   BINANCE_API_KEY = 'tu_api_key'
   BINANCE_API_SECRET = 'tu_api_secret'
   ```

## Configuración

El bot se configura a través de módulos de constantes en la carpeta `constants/`:

- `base.py`: Configuración base
- `dev.py`: Configuración para desarrollo

Parámetros de trading configurables:

- `STOP_LOSS_PERCENTAGE`: Porcentaje para el stop loss
- `TAKE_PROFIT_PERCENTAGE`: Porcentaje para el take profit
- `VARIATION_PERCENTAGE`: Porcentaje de variación para entrar en operaciones
- `VARIATION_100K_PERCENTAGE`: Porcentaje de variación para operaciones con alto volumen
- `VARIATION_FAST_PERCENTAGE`: Porcentaje para operaciones FAST_SHORT

## Uso

### Iniciar la interfaz web

Para iniciar el servidor web de monitoreo:

```
python runner.py
```

Luego accede a la interfaz en tu navegador: http://127.0.0.1:5000

## Cómo funciona

1. El bot escanea continuamente los pares de trading USDT en Binance
2. Analiza las variaciones de precio en períodos definidos
3. Cuando detecta una oportunidad según los criterios configurados, genera una alerta
4. Monitorea activamente las señales para informar su evolución
5. Registra cuando las señales alcanzan el nivel de take profit o stop loss sugerido
6. Mantiene estadísticas para ayudar al usuario a evaluar la efectividad de las alertas

## Estructura del proyecto

- `trading_bot.py`: Núcleo del bot con la lógica de trading
- `config.py`: Configuración del sistema
- `runner.py`: Script para iniciar el bot
- `server.py`: Servidor web para monitoreo
- `binance_service.py`: Servicio para interactuar con la API de Binance
- `notification_service.py`: Servicio de notificaciones
- `logger_module.py`: Módulo de registro y logging
- `constants/`: Directorio con diferentes configuraciones
- `templates/`: Plantillas HTML para la interfaz web
- `log/`: Directorio para almacenar logs de operaciones

## Seguridad

- No almacenes tus claves API directamente en el código fuente
- Usa variables de entorno o archivos de configuración separados
- Limita los permisos de tus claves API solo a lo necesario

## Descargo de responsabilidad

Este bot es para propósitos educativos y de investigación. El trading automático conlleva riesgos significativos. Úsalo bajo tu propia responsabilidad.
