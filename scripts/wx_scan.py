#!/usr/bin/env python3
"""Collect read-only WeChat candidate data without printing unrelated history."""

import argparse
import json
import subprocess


def run(command: list[str]) -> dict:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    try:
        data = json.loads(result.stdout) if result.stdout else None
    except json.JSONDecodeError:
        data = result.stdout.strip()
    return {"ok": result.returncode == 0, "data": data, "error": result.stderr.strip()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wx-bin", default="scripts/wx-local")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--keyword", action="append", default=[])
    args = parser.parse_args()

    payload = {
        "new_messages": run([args.wx_bin, "new-messages", "--limit", str(args.limit), "--json"]),
        "unread": run([args.wx_bin, "unread", "--filter", "private,group", "--limit", str(args.limit), "--json"]),
        "recent_sessions": run([args.wx_bin, "sessions", "--limit", str(args.limit), "--json"]),
        "keyword_matches": {},
    }
    for keyword in args.keyword:
        payload["keyword_matches"][keyword] = run([args.wx_bin, "search", keyword, "--limit", "20", "--json"])
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if any(item.get("ok") for item in payload.values() if isinstance(item, dict) and "ok" in item) else 1


if __name__ == "__main__":
    raise SystemExit(main())
