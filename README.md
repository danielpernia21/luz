# Luz ⚡

Bot de Telegram que cada mañana te dice **a qué hora conviene poner la lavadora y el
lavavajillas** según el precio horario de la luz, y te vuelve a avisar 10 minutos antes.

## Cómo funciona

1. **09:00 (hora de Madrid)** — descarga los 24 precios PVPC del día y busca la **franja de
   3 horas seguidas** con el precio medio más bajo. Te envía el resumen con la mejor franja,
   dos alternativas, la franja a evitar y el ahorro estimado.
2. **~10 minutos antes** de esa franja — te manda un recordatorio corto para que la pongas.

La franja debe **empezar y terminar entre las 09:00 y las 22:00**, así que el ciclo nunca
arranca más tarde de las 19:00.

### Fuente de los precios

[API pública de Red Eléctrica](https://apidatos.ree.es), serie PVPC (indicador ESIOS 1001),
sin token ni registro. Si falla, el bot te avisa del error en vez de quedarse callado.

**Es exactamente el precio que te factura la comercializadora.** Se verificó contra una factura
real de Energía XXI (PVPC, periodo 21/07/2026–22/08/2026): las 792 horas coinciden con el
indicador 1001 con una diferencia máxima de 0,000005 €/kWh, que es solo el redondeo de la API,
que publica en €/MWh con dos decimales. La suma de los costes horarios da 90,543 € frente a los
90,55 € de la factura.

## Configuración

Secretos del repositorio (*Settings → Secrets and variables → Actions*):

| Secreto | Qué es |
|---|---|
| `TELEGRAM_BOT_TOKEN` | El token que te da @BotFather |
| `TELEGRAM_CHAT_ID` | Tu chat id (el bot te escribe ahí) |

Ajustes opcionales por variable de entorno (`luzbot/config.py`):

| Variable | Por defecto | Qué hace |
|---|---|---|
| `DURACION_H` | `3` | Horas seguidas que dura el ciclo |
| `HORA_MIN` / `HORA_MAX` | `9` / `22` | Horario en el que puede caber el ciclo |
| `LAVADORA_KWH` / `LAVAVAJILLAS_KWH` | `1.0` / `1.2` | Consumo por ciclo, para calcular el ahorro |
| `HORA_RESUMEN` | `9` | Hora del mensaje de la mañana |
| `AVISO_MARGEN_MIN` | `15` | Margen del recordatorio previo |

## Uso manual

```bash
pip install -r requirements-dev.txt

# Ver el mensaje de hoy sin enviarlo
python -m luzbot.main --mode summary --dry-run --force

# Simular el recordatorio a una hora concreta
python -m luzbot.main --mode reminder --dry-run --now 2026-09-20T12:50

pytest
```

Desde GitHub también puedes lanzarlo a mano en la pestaña **Actions → Luz → Run workflow**.

## Sobre los horarios de GitHub Actions

El cron de GitHub Actions solo entiende UTC y España cambia entre UTC+1 y UTC+2: por eso el
workflow se lanza a las dos horas UTC posibles y el propio script descarta la ejecución que no
corresponde, comparando con la hora real de `Europe/Madrid`.

El recordatorio no sondea cada 10 minutos: como las franjas siempre empiezan **en punto**, basta
con una ejecución en el minuto 47 de cada hora (≈11 ejecuciones al día de unos 15 s).

## Cambio de hora

Los domingos en que cambia la hora el día tiene 23 o 25 horas. El bot lo contempla: no exige
las 24 horas en la tabla (solo las del horario operativo) y, cuando las 02:00 llegan repetidas
en octubre, se queda con la primera.

## Sobre los precios

Son el término de facturación de energía activa del PVPC (indicador ESIOS 1001), **sin IVA ni
impuesto especial de electricidad**; los mensajes lo indican. Los impuestos son porcentajes que
multiplican todas las horas por igual, así que no alteran cuál es la franja más barata.
