"""Imprime los chat_id que el bot puede ver, para configurar TELEGRAM_CHAT_ID.

Uso:  python scripts/chat_id.py
Lee el token de la variable TELEGRAM_BOT_TOKEN o lo pide por teclado.
"""

from __future__ import annotations

import os
import sys

import requests


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or input("Token del bot: ").strip()
    if not token:
        print("Hace falta el token que te dio @BotFather.")
        return 1

    resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=30)
    datos = resp.json()
    if not datos.get("ok"):
        print(f"Telegram ha respondido con un error: {datos}")
        return 1

    # Un mismo chat puede aparecer en varias actualizaciones; se deduplica por id.
    chats = {}
    for update in datos["result"]:
        for clave in ("message", "channel_post", "edited_message", "my_chat_member"):
            chat = (update.get(clave) or {}).get("chat")
            if chat:
                chats[chat["id"]] = chat

    if not chats:
        print(
            "No veo ningun chat todavia. Prueba a:\n"
            "  - escribirle algo al bot por privado, o\n"
            "  - en el canal: añadir el bot como administrador y publicar un mensaje.\n"
            "Telegram solo guarda las actualizaciones 24 horas."
        )
        return 1

    print(f"{'chat_id':>16}  tipo        nombre")
    for chat in chats.values():
        nombre = chat.get("title") or chat.get("username") or chat.get("first_name", "")
        print(f"{chat['id']:>16}  {chat['type']:<10}  {nombre}")

    print("\nGuardalo con:")
    print('  gh secret set TELEGRAM_CHAT_ID -R danielpernia21/luz --body "EL_ID"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
