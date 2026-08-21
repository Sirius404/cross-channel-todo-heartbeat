#!/usr/bin/env python3
"""Select large, idle Codex sessions and run the guarded image repairer."""

import argparse
import json
import sqlite3
import subprocess
import time
from pathlib import Path


def main() -> int:
    root = Path(__file__).parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".codex/sessions")
    parser.add_argument("--state-db", type=Path, default=Path.home() / ".codex/state_5.sqlite")
    parser.add_argument("--repair", type=Path, default=root / "scripts/codex-session-image-repair.mjs")
    parser.add_argument("--protected-cwd", action="append", default=[])
    parser.add_argument("--min-mb", type=int, default=100)
    parser.add_argument("--min-age-minutes", type=int, default=30)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    db = sqlite3.connect(f"file:{args.state_db}?mode=ro", uri=True)
    rows = db.execute("SELECT rollout_path, cwd FROM threads WHERE rollout_path IS NOT NULL").fetchall()
    cwd_by_path = {
        str(Path(path).resolve()): str(Path(cwd).resolve()) if cwd else ""
        for path, cwd in rows
    }
    protected = {str(Path(item).resolve()) for item in args.protected_cwd}
    cutoff = time.time() - args.min_age_minutes * 60
    minimum = args.min_mb * 1024 * 1024
    candidates = [
        path for path in args.sessions.rglob("*.jsonl")
        if "archived_sessions" not in path.parts and path.stat().st_size > minimum and path.stat().st_mtime < cutoff
    ]
    summary = {"scanned": len(candidates), "modified": 0, "unchanged": 0, "skipped_open": 0, "skipped_protected": 0, "failed": 0, "before": 0, "after": 0}

    for path in candidates:
        before = path.stat().st_size
        if cwd_by_path.get(str(path.resolve())) in protected:
            summary["skipped_protected"] += 1
            summary["before"] += before
            summary["after"] += before
            continue
        command = [str(args.repair), "--all-images", str(path)]
        if args.apply:
            command.insert(1, "--apply")
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode:
            if "refusing to modify open session" in result.stderr:
                summary["skipped_open"] += 1
            else:
                summary["failed"] += 1
            summary["before"] += before
            summary["after"] += before
            continue
        record = json.loads(result.stdout.strip().splitlines()[-1])
        after = int(record.get("after", record.get("projected", before)))
        summary["before"] += before
        summary["after"] += after
        if record.get("unchanged") or not args.apply:
            summary["unchanged"] += 1
        else:
            summary["modified"] += 1

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
