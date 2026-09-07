#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_BIN="$HOME/.local/bin"
SYSTEM_BIN="/usr/local/bin"
SYSTEM_MAN="/usr/local/share/man/man1"
RUNTIME_ROOT=""
VENV=""
MAC_APP_DEST=""

if [[ "$(uname -s)" == "Darwin" ]]; then
  RUNTIME_ROOT="$HOME/Library/Application Support/Quarries/runtime"
  echo "Installing standalone macOS runtime to: $RUNTIME_ROOT"
  rm -rf "$RUNTIME_ROOT"
  mkdir -p "$RUNTIME_ROOT"
  rsync -a \
    --exclude='.git' --exclude='.venv' --exclude='Quarries.app' \
    --exclude='release' --exclude='dist' --exclude='build' \
    "$ROOT/" "$RUNTIME_ROOT/"
else
  RUNTIME_ROOT="$ROOT"
fi

VENV="$RUNTIME_ROOT/.venv"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install "$RUNTIME_ROOT"

TMP_LAUNCHER="$(mktemp)"
cat > "$TMP_LAUNCHER" <<LAUNCHER
#!/usr/bin/env bash
exec "$VENV/bin/quarries" "\$@"
LAUNCHER
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

# Explicit TUI launcher.
TMP_TUI="$(mktemp)"
cat > "$TMP_TUI" <<TUI
#!/usr/bin/env bash
exec "$VENV/bin/quarries-tui" "\$@"
TUI
chmod 0755 "$TMP_TUI"
if [[ "$BIN_DEST" == /usr/local/bin/* ]]; then
  if install -m 0755 "$TMP_TUI" "$SYSTEM_BIN/quarries-tui" 2>/dev/null; then :; else sudo install -m 0755 "$TMP_TUI" "$SYSTEM_BIN/quarries-tui"; fi
else
  install -m 0755 "$TMP_TUI" "$USER_BIN/quarries-tui"
fi
rm -f "$TMP_TUI"

if [[ -f "$ROOT/man/quarries.1" ]]; then
  if mkdir -p "$SYSTEM_MAN" 2>/dev/null && install -m 0644 "$ROOT/man/quarries.1" "$SYSTEM_MAN/quarries.1" 2>/dev/null; then :
  elif command -v sudo >/dev/null 2>&1; then
    sudo mkdir -p "$SYSTEM_MAN" && sudo install -m 0644 "$ROOT/man/quarries.1" "$SYSTEM_MAN/quarries.1"
  else
    mkdir -p "$HOME/.local/share/man/man1" && install -m 0644 "$ROOT/man/quarries.1" "$HOME/.local/share/man/man1/quarries.1"
  fi
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  "$ROOT/scripts/build_macos_app.sh"
  MAC_APP_DEST="/Applications/Quarries.app"
  echo "Installing Quarries.app to: $MAC_APP_DEST"
  if rm -rf "$MAC_APP_DEST" 2>/dev/null && cp -R "$ROOT/Quarries.app" "$MAC_APP_DEST" 2>/dev/null; then
    :
  elif command -v sudo >/dev/null 2>&1; then
    sudo rm -rf "$MAC_APP_DEST"
    sudo cp -R "$ROOT/Quarries.app" "$MAC_APP_DEST"
    sudo chown -R "$USER":staff "$MAC_APP_DEST" 2>/dev/null || true
  else
    echo "Unable to install to /Applications without administrator privileges." >&2
    exit 1
  fi
  xattr -cr "$MAC_APP_DEST" 2>/dev/null || true
  chmod +x "$MAC_APP_DEST/Contents/MacOS/Quarries" 2>/dev/null || sudo chmod +x "$MAC_APP_DEST/Contents/MacOS/Quarries"
  touch "$MAC_APP_DEST"
  LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
  [[ -x "$LSREGISTER" ]] && "$LSREGISTER" -f "$MAC_APP_DEST" >/dev/null 2>&1 || true
fi

echo
echo "Quarries v0.9.3 installed."
echo "CLI: $BIN_DEST"
[[ -n "$MAC_APP_DEST" ]] && echo "Desktop app: $MAC_APP_DEST"
echo "Runtime: $RUNTIME_ROOT"
echo "Personal data: $HOME/.local/share/quarries/archive.qry"
echo
echo "Launch GUI: quarries"
echo "Launch TUI: quarries-tui"
[[ -n "$MAC_APP_DEST" ]] && echo "Open desktop app: open '$MAC_APP_DEST'"
