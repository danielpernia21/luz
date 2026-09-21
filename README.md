# Luz ⚡

Bot de Telegram que cada mañana te dice **a qué hora conviene poner la lavadora y el
lavavajillas** según el precio horario de la luz, y te vuelve a avisar 10 minutos antes.

## Cómo funciona

1. **09:00 (hora de Madrid)** — descarga los 24 precios PVPC del día y busca la **franja de
   3 horas seguidas** con el precio medio más bajo. Te envía el resumen con la mejor franja,
   dos alternativas, la franja a evitar y el ahorro estimado.
2. **10 minutos antes** de esa franja — te manda un recordatorio corto para que la pongas.

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
| `TELEGRAM_CHAT_ID` | Dónde escribe el bot: tu chat privado o un canal |

### Enviar a un canal en vez de a un chat privado

1. En el canal: *Administrators → Add Administrator* y añade tu bot. Le basta el permiso
   **Post Messages**.
2. Publica cualquier mensaje en el canal (Telegram solo guarda las actualizaciones 24 h).
3. Saca el id del canal:

   ```bash
   TELEGRAM_BOT_TOKEN=... python scripts/chat_id.py
   ```

   El del canal es el que aparece con tipo `channel` y empieza por `-100`.
4. Guárdalo:

   ```bash
   gh secret set TELEGRAM_CHAT_ID -R danielpernia21/luz --body "-1001234567890"
   ```

Si el canal es público, puedes usar directamente su alias (`@minombredecanal`) como
`TELEGRAM_CHAT_ID`, sin necesidad del paso 3.

Ajustes opcionales por variable de entorno (`luzbot/config.py`):

| Variable | Por defecto | Qué hace |
|---|---|---|
| `DURACION_H` | `3` | Horas seguidas que dura el ciclo |
| `HORA_MIN` / `HORA_MAX` | `9` / `22` | Horario en el que puede caber el ciclo |
| `LAVADORA_KWH` / `LAVAVAJILLAS_KWH` | `1.0` / `1.2` | Consumo por ciclo, para calcular el ahorro |
| `HORA_RESUMEN` | `9` | Hora del mensaje de la mañana |
| `RESUMEN_LIMITE_H` | `11` | Hasta qué hora se sigue intentando el resumen |
| `AVISO_ANTES_MIN` | `10` | Antelación del recordatorio |
| `AVISO_VENTANA_MIN` / `AVISO_RETRASO_MIN` | `12` / `10` | Cuánto adelanto o retraso se acepta en el recordatorio |

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

El cron de GitHub Actions solo entiende UTC (y España cambia entre UTC+1 y UTC+2), pero el
problema de verdad es otro: **`schedule` es *best effort***. Se retrasa 15–30 minutos con
frecuencia y a veces se salta ejecuciones enteras, así que una sola ejecución por mensaje no
garantiza nada.

Por eso cada mensaje se **sondea varias veces** y quien decide es el script, comparando con la
hora real de `Europe/Madrid`:

- **Resumen**: sondeos entre las 09:00 y las 10:50; se envía en el primero que encuentre precios.
- **Recordatorio**: dos sondeos por hora (minutos 50 y 57 UTC); se envía si a la franja le faltan
  ≤ 12 minutos, o si acaba de empezar hace ≤ 10.

Para que los sondeos de repuesto no dupliquen el mensaje, el envío deja un fichero `.enviado`
que el workflow guarda en la **cache con clave del día** (`luz-<modo>-<fecha>`). Si la marca ya
existe, el job se salta el checkout y todo lo demás en unos segundos.

Coste aproximado: ~34 ejecuciones al día, casi todas de unos 10 s pero facturadas al minuto
(≈1.000 min/mes de los 2.000 gratuitos de un repo privado).

## Cambio de hora

Los domingos en que cambia la hora el día tiene 23 o 25 horas. El bot lo contempla: no exige
las 24 horas en la tabla (solo las del horario operativo) y, cuando las 02:00 llegan repetidas
en octubre, se queda con la primera.

## Sobre los precios

Son el término de facturación de energía activa del PVPC (indicador ESIOS 1001), **sin IVA ni
impuesto especial de electricidad**; los mensajes lo indican. Los impuestos son porcentajes que
multiplican todas las horas por igual, así que no alteran cuál es la franja más barata.

## Que GitHub no apague el cron

GitHub desactiva los workflows programados de un repositorio tras **60 días sin actividad**.
El workflow `keepalive.yml` hace un commit vacío el día 1 de cada mes para evitarlo.

Si aun así llegara a desactivarse, GitHub te avisa por correo y se vuelve a activar con un clic
en *Actions → Luz → Enable workflow*.
