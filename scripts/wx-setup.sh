#!/bin/sh
set -eu

WX_CMD="${WX_BIN:-$(command -v wx || true)}"
if [ -z "$WX_CMD" ]; then
  echo "wx not found. Install explicitly: npm install -g @jackwener/wx-cli@0.3.0" >&2
  exit 1
fi
WX_DIR=$(dirname "$WX_CMD")
if [ -x "$WX_DIR/node" ]; then
  PATH="$WX_DIR:$PATH"
  export PATH
fi

echo "Using: $WX_CMD"
echo "Starting local wx-cli discovery. No key will be printed by this script."
"$WX_CMD" init
"$(dirname "$0")/wx-doctor.sh"
