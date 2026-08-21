#!/bin/sh
set -eu

ROOT="${WX_CLI_HOME:-$HOME/.wx-cli}"
CONFIG="$ROOT/config.json"

command -v jq >/dev/null || { echo "missing jq" >&2; exit 1; }
[ -f "$CONFIG" ] || { echo "missing $CONFIG; run scripts/wx-setup.sh" >&2; exit 1; }

KEYS=$(jq -r '.keys_file // empty' "$CONFIG")
case "$KEYS" in
  /*) ;;
  "") KEYS="$ROOT/all_keys.json" ;;
  *) KEYS="$ROOT/$KEYS" ;;
esac

[ -f "$KEYS" ] || { echo "keys file is missing (path withheld)" >&2; exit 1; }
COUNT=$(jq '[to_entries[] | select(.value.enc_key? | type == "string")]|length' "$KEYS")
echo "wx-cli config: ok"
echo "discovered database keys: $COUNT (values withheld)"
