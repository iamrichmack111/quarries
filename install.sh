#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/quarries" <<EOF
#!/usr/bin/env bash
exec "$ROOT/.venv/bin/quarries" "\$@"
EOF
chmod +x "$HOME/.local/bin/quarries"

if command -v xdg-user-dir >/dev/null 2>&1; then
    APPS="$HOME/.local/share/applications"
    mkdir -p "$APPS"
    cat > "$APPS/quarries.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Quarries
Comment=The Archive remembers. The Watcher listens.
Exec=$HOME/.local/bin/quarries
Terminal=true
Categories=Utility;Office;
EOF
    chmod +x "$APPS/quarries.desktop"
fi

echo
echo "The Archive is ready."
echo
echo "Install local models:"
echo "  ollama pull huihui_ai/qwen3.5-abliterated:4b"
echo "  ollama pull nomic-embed-text"
echo
echo "Run:"
echo "  quarries"
