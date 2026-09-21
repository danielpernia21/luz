"""Configuracion: valores por defecto sobreescribibles por variables de entorno."""

from __future__ import annotations

import os
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")

# Duracion del ciclo (horas completas) que debe caber en la franja elegida.
DURACION_H = int(os.environ.get("DURACION_H", "3"))

# La franja debe empezar y terminar dentro de [HORA_MIN, HORA_MAX].
HORA_MIN = int(os.environ.get("HORA_MIN", "9"))
HORA_MAX = int(os.environ.get("HORA_MAX", "22"))

# Consumo estimado por ciclo, para calcular el ahorro en euros.
LAVADORA_KWH = float(os.environ.get("LAVADORA_KWH", "1.0"))
LAVAVAJILLAS_KWH = float(os.environ.get("LAVAVAJILLAS_KWH", "1.2"))

# Hora a la que se manda el resumen del dia (hora de Madrid).
HORA_RESUMEN = int(os.environ.get("HORA_RESUMEN", "9"))

# El cron de GitHub se retrasa a menudo, asi que el resumen se sigue intentando
# hasta esta hora (excluida) y el workflow se encarga de que solo salga uno.
RESUMEN_LIMITE_H = int(os.environ.get("RESUMEN_LIMITE_H", "11"))

# Antelacion con la que se quiere el recordatorio.
AVISO_ANTES_MIN = int(os.environ.get("AVISO_ANTES_MIN", "10"))

# Tolerancia del recordatorio: vale si faltan como mucho estos minutos...
AVISO_VENTANA_MIN = int(os.environ.get("AVISO_VENTANA_MIN", "12"))

# ...o si la franja acaba de empezar hace menos de estos (cron retrasado).
AVISO_RETRASO_MIN = int(os.environ.get("AVISO_RETRASO_MIN", "10"))

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
