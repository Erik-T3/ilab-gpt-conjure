#!/bin/zsh
set -e
set -o pipefail
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

BUNDLE_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="${BUNDLE_DIR}/app"
DATA_DIR="${BUNDLE_DIR}/data"
PYTHON_FRAMEWORK="${BUNDLE_DIR}/python/Python.framework"
PYTHON_BIN="${BUNDLE_DIR}/python/Python.framework/Versions/3.11/bin/python3"
PORT="8787"
URL="http://127.0.0.1:${PORT}/"
HEALTH_URL="${URL}api/health"
WAIT_ATTEMPTS=60

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Portable Python was not found at ${PYTHON_BIN}."
  read -r "?Press Enter to close..."
  exit 1
fi

if [ ! -f "${APP_DIR}/portable_webui_app.py" ]; then
  echo "Portable app files were not found at ${APP_DIR}."
  read -r "?Press Enter to close..."
  exit 1
fi

clear_macos_quarantine() {
  if ! command -v xattr >/dev/null 2>&1; then
    return 0
  fi

  local needs_clear=0
  local bundle_path
  for bundle_path in "$BUNDLE_DIR" "$PYTHON_FRAMEWORK" "$PYTHON_BIN"; do
    if xattr -p com.apple.quarantine "$bundle_path" >/dev/null 2>&1; then
      needs_clear=1
      break
    fi
  done

  if [ "$needs_clear" -eq 0 ]; then
    return 0
  fi

  echo "Detected macOS quarantine attributes on this portable bundle."
  echo "Removing quarantine from: ${BUNDLE_DIR}"
  xattr -dr com.apple.quarantine "$BUNDLE_DIR" 2>/dev/null || true

  if xattr -p com.apple.quarantine "$PYTHON_FRAMEWORK" >/dev/null 2>&1 || \
     xattr -p com.apple.quarantine "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "macOS may still block the bundled Python framework."
    echo "Run this command in Terminal, then start again:"
    echo "  xattr -dr com.apple.quarantine \"${BUNDLE_DIR}\""
    read -r "?Press Enter to close..."
    exit 1
  fi

  echo "Quarantine attributes removed for the portable bundle."
}

clear_macos_quarantine

mkdir -p "${DATA_DIR}/logs"
export ILAB_CONJURE_DATA_DIR="${DATA_DIR}"
export PYTHONPATH="${APP_DIR}:${APP_DIR}/.deps"
CERTIFI_CA_BUNDLE="${APP_DIR}/.deps/certifi/cacert.pem"
if [ -f "$CERTIFI_CA_BUNDLE" ]; then
  export SSL_CERT_FILE="$CERTIFI_CA_BUNDLE"
  export REQUESTS_CA_BUNDLE="$CERTIFI_CA_BUNDLE"
fi
LOG_FILE="${DATA_DIR}/logs/webui-server.log"
AUTH_SETTINGS_PATH="${DATA_DIR}/webui-auth-settings.json"
VERSION_FILE="${BUNDLE_DIR}/portable-version.txt"
LATEST_RELEASE_URL="https://api.github.com/repos/kadevin/ilab-gpt-conjure/releases/latest"
"$PYTHON_BIN" -m codex_image.webui.startup_auth --settings-path "$AUTH_SETTINGS_PATH" >/dev/null

cd "$APP_DIR"

check_latest_release_notice() {
  if [ "${ILAB_SKIP_VERSION_CHECK:-}" = "1" ]; then
    return 0
  fi
  if [ ! -f "$VERSION_FILE" ] || ! command -v curl >/dev/null 2>&1; then
    return 0
  fi

  local current_version
  current_version="$(head -n 1 "$VERSION_FILE" | tr -d '[:space:]')"
  if [ -z "$current_version" ]; then
    return 0
  fi

  local release_json
  release_json="$(curl -fsSL --connect-timeout 1 --max-time 2 \
    -H "User-Agent: ilab-gpt-conjure-portable-launcher" \
    "$LATEST_RELEASE_URL" 2>/dev/null)" || return 0

  local latest_version
  latest_version="$(printf "%s" "$release_json" | "$PYTHON_BIN" -c '
import json
import re
import sys

current = sys.argv[1].strip()
try:
    latest = str(json.load(sys.stdin).get("tag_name") or "").strip()
except Exception:
    raise SystemExit(0)

def parse(value):
    match = re.match(r"^[vV]?(\d+)\.(\d+)\.(\d+)", value.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())

current_parts = parse(current)
latest_parts = parse(latest)
if current_parts and latest_parts and latest_parts > current_parts:
    print(".".join(str(part) for part in latest_parts))
' "$current_version" 2>/dev/null || true)"

  if [ -n "$latest_version" ]; then
    echo "New version available: v${latest_version}. Close WebUI and run \"Update WebUI Portable.command\" to update."
  fi
}

webui_is_ready() {
  "$PYTHON_BIN" - "$HEALTH_URL" <<'PY' >/dev/null 2>&1
import sys
from urllib.request import urlopen

with urlopen(sys.argv[1], timeout=0.5) as response:
    if response.status != 200:
        raise SystemExit(1)
PY
}

wait_for_webui() {
  local attempt=0
  while [ "$attempt" -lt "$WAIT_ATTEMPTS" ]; do
    if webui_is_ready; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 0.5
  done
  return 1
}

echo "Starting iLab GPT Conjure at ${URL}"
echo "Data directory: ${DATA_DIR}"
echo "Writing server log to ${LOG_FILE}"
check_latest_release_notice

if webui_is_ready; then
  echo "WebUI is already running at ${URL}"
  open "$URL" >/dev/null 2>&1 || true
  exit 0
fi

"$PYTHON_BIN" -m uvicorn portable_webui_app:app --host 127.0.0.1 --port "$PORT" --no-access-log >> "$LOG_FILE" 2>&1 &
SERVER_PID="$!"

if wait_for_webui; then
  open "$URL" >/dev/null 2>&1 || true
else
  echo "WebUI did not become ready within 30 seconds. Check ${LOG_FILE}."
fi

wait "$SERVER_PID"
