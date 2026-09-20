"""Envio de mensajes a Telegram."""

from __future__ import annotations

import requests

from . import config

API = "https://api.telegram.org/bot{token}/sendMessage"


def send(text: str, *, dry_run: bool = False) -> None:
    if dry_run:
        print(text)
        return

    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        raise RuntimeError("faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")

    resp = requests.post(
        API.format(token=config.TELEGRAM_BOT_TOKEN),
        json={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Telegram {resp.status_code}: {resp.text[:300]}")
