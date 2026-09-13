#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/Quarries.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$ROOT/assets/Quarries.icns" "$APP/Contents/Resources/Quarries.icns"
cat > "$APP/Contents/MacOS/quarries" <<'APP_EOF'
#!/usr/bin/env bash
set -euo pipefail
RUNTIME="$HOME/Library/Application Support/Quarries/runtime/.venv/bin/quarries"
if [[ ! -x "$RUNTIME" ]]; then
  osascript -e 'display alert "Quarries runtime is missing" message "Run install.sh from a Quarries release folder to install or repair the application." as critical'
  exit 1
fi
LOG="$HOME/Library/Logs/Quarries.log"
mkdir -p "$(dirname "$LOG")"
OLD_PIDS="$(lsof -tiTCP:8787 -sTCP:LISTEN 2>/dev/null || true)"
for pid in $OLD_PIDS; do
  cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  if [[ "$cmd" == *"Quarries"* || "$cmd" == *"quarries"* ]]; then
    kill "$pid" 2>/dev/null || true
  else
    osascript -e 'display alert "Port 8787 is already in use" message "Another application is using Quarries port 8787. Close it and reopen Quarries." as critical'
    exit 1
  fi
done
sleep 0.5
exec "$RUNTIME" >>"$LOG" 2>&1
APP_EOF
chmod 0755 "$APP/Contents/MacOS/quarries"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleDevelopmentRegion</key><string>English</string>
  <key>CFBundleExecutable</key><string>quarries</string>
  <key>CFBundleIconFile</key><string>Quarries.icns</string>
  <key>CFBundleIdentifier</key><string>com.richmack.quarries</string>
  <key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
  <key>CFBundleName</key><string>Quarries</string>
  <key>CFBundleDisplayName</key><string>Quarries</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.10.6</string>
  <key>CFBundleVersion</key><string>0.10.6</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST

echo "Built $APP"
