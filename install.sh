#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
SYSTEM_BIN="/usr/local/bin"
SYSTEM_MAN="/usr/local/share/man/man1"
USER_BIN="$HOME/.local/bin"

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

echo
echo "Quarries installed."
echo "Launcher: $BIN_DEST"
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
