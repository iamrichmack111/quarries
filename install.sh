#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
SYSTEM_BIN="/usr/local/bin"
SYSTEM_MAN="/usr/local/share/man/man1"
USER_BIN="$HOME/.local/bin"
MAC_APP_SOURCE="$ROOT/Quarries.app"
MAC_APP_DEST=""

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -e "$ROOT"

TMP_LAUNCHER="$(mktemp)"
cat > "$TMP_LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/quarries" "\$@"
EOF
chmod 0755 "$TMP_LAUNCHER"

if mkdir -p "$SYSTEM_BIN" 2>/dev/null && install -m 0755 "$TMP_LAUNCHER" "$SYSTEM_BIN/quarries" 2>/dev/null; then
  BIN_DEST="$SYSTEM_BIN/quarries"
elif command -v sudo >/dev/null 2>&1; then
  sudo mkdir -p "$SYSTEM_BIN"
  sudo install -m 0755 "$TMP_LAUNCHER" "$SYSTEM_BIN/quarries"
  BIN_DEST="$SYSTEM_BIN/quarries"
else
  mkdir -p "$USER_BIN"
  install -m 0755 "$TMP_LAUNCHER" "$USER_BIN/quarries"
  BIN_DEST="$USER_BIN/quarries"
fi
rm -f "$TMP_LAUNCHER"

if [[ -f "$ROOT/man/quarries.1" ]]; then
  if mkdir -p "$SYSTEM_MAN" 2>/dev/null && install -m 0644 "$ROOT/man/quarries.1" "$SYSTEM_MAN/quarries.1" 2>/dev/null; then
    :
  elif command -v sudo >/dev/null 2>&1; then
    sudo mkdir -p "$SYSTEM_MAN"
    sudo install -m 0644 "$ROOT/man/quarries.1" "$SYSTEM_MAN/quarries.1"
  else
    mkdir -p "$HOME/.local/share/man/man1"
    install -m 0644 "$ROOT/man/quarries.1" "$HOME/.local/share/man/man1/quarries.1"
  fi
fi

if [[ "$(uname -s)" == "Darwin" && -d "$MAC_APP_SOURCE" ]]; then
  if [[ -d "/Applications" && -w "/Applications" ]]; then
    rm -rf "/Applications/Quarries.app"
    cp -R "$MAC_APP_SOURCE" "/Applications/Quarries.app"
    MAC_APP_DEST="/Applications/Quarries.app"
  elif command -v sudo >/dev/null 2>&1; then
    sudo rm -rf "/Applications/Quarries.app"
    sudo cp -R "$MAC_APP_SOURCE" "/Applications/Quarries.app"
    MAC_APP_DEST="/Applications/Quarries.app"
  else
    mkdir -p "$HOME/Applications"
    rm -rf "$HOME/Applications/Quarries.app"
    cp -R "$MAC_APP_SOURCE" "$HOME/Applications/Quarries.app"
    MAC_APP_DEST="$HOME/Applications/Quarries.app"
  fi
fi

echo
echo "Quarries installed."
echo "Launcher: $BIN_DEST"
if [[ -n "$MAC_APP_DEST" ]]; then
  echo "macOS app: $MAC_APP_DEST"
fi
echo
echo "Install Ollama models:"
echo "  ollama pull huihui_ai/qwen3.5-abliterated:4b"
echo "  ollama pull gemma3:4b"
echo "  ollama pull embeddinggemma"
echo
echo "Run from anywhere:"
echo "  quarries"
echo "Manual:"
echo "  man quarries"
echo
echo "Your personal database is preserved at:"
echo "  $HOME/.local/share/quarries/archive.qry"
echo "Installing or upgrading Quarries does not delete it."
