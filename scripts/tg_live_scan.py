#!/usr/bin/env python3
"""Scan selected Telegram groups live through the existing tg-cli session."""

import argparse
import asyncio
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path


def ensure_imports() -> None:
    try:
        import tg_cli.client  # noqa: F401
        return
    except ModuleNotFoundError:
        pass
    candidates = []
    if os.environ.get("TG_CLI_SITE_PACKAGES"):
        candidates.append(Path(os.environ["TG_CLI_SITE_PACKAGES"]))
    candidates.extend(Path.home().glob(".local/share/uv/tools/kabi-tg-cli/lib/python*/site-packages"))
    for candidate in candidates:
        if candidate.is_dir():
            sys.path.insert(0, str(candidate))
            return


def sender_name(message) -> str:
    sender = getattr(message, "_sender", None) or getattr(message, "sender", None)
    if sender is None:
        return str(getattr(message, "sender_id", "") or "")
    name = " ".join(filter(None, [getattr(sender, "first_name", ""), getattr(sender, "last_name", "")])).strip()
    return name or getattr(sender, "username", "") or getattr(sender, "title", "")


async def scan(args) -> dict:
    ensure_imports()
    import tg_cli.client as tg_client
    from tg_cli.client import connect

    tg_client._default_api_warned = True
    pattern = re.compile(args.name_regex, re.IGNORECASE) if args.name_regex else None
    wanted_ids = set(args.chat_id)
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=args.hours)
    records, chats = [], []

    async with connect() as client:
        async for dialog in client.iter_dialogs():
            latest = getattr(dialog, "date", None)
            if latest and latest.tzinfo is None:
                latest = latest.replace(tzinfo=dt.timezone.utc)
            if latest and latest < since:
                continue
            if dialog.id not in wanted_ids and not (pattern and pattern.search(dialog.name or "")):
                continue

            chat = {"chat_id": dialog.id, "chat_name": dialog.name or "", "unread": dialog.unread_count, "records": 0}
            async for message in client.iter_messages(dialog.entity, limit=args.limit_per_chat):
                observed = message.date
                if observed and observed.tzinfo is None:
                    observed = observed.replace(tzinfo=dt.timezone.utc)
                if observed and observed < since:
                    break
                content = message.text or message.message or ""
                if not content.strip():
                    continue
                records.append({
                    "chat_id": dialog.id,
                    "chat_name": dialog.name or "",
                    "message_ref": f"{dialog.id}:{message.id}",
                    "sender": sender_name(message),
                    "timestamp": observed.isoformat() if observed else "",
                    "content": content,
                })
                chat["records"] += 1
            chats.append(chat)
    return {"ok": True, "source": "telegram_live", "chats": chats, "data": records}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--limit-per-chat", type=int, default=100)
    parser.add_argument("--name-regex", default="")
    parser.add_argument("--chat-id", type=int, action="append", default=[])
    args = parser.parse_args()
    if not args.name_regex and not args.chat_id:
        parser.error("provide --name-regex or at least one --chat-id")
    print(json.dumps(asyncio.run(scan(args)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
