#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/Quarries.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$ROOT/assets/Quarries.icns" "$APP/Contents/Resources/Quarries.icns"
cat > "$APP/Contents/MacOS/Quarries" <<'APP_EOF'
#!/usr/bin/env bash
set -euo pipefail
RUNTIME="$HOME/Library/Application Support/Quarries/runtime/.venv/bin/quarries"
if [[ ! -x "$RUNTIME" ]]; then
  osascript -e 'display alert "Quarries runtime is missing" message "Run install.sh from a Quarries release folder to install or repair the application." as critical'
  exit 1
fi
LOG="$HOME/Library/Logs/Quarries.log"
mkdir -p "$(dirname "$LOG")"
exec "$RUNTIME" >>"$LOG" 2>&1
APP_EOF
chmod 0755 "$APP/Contents/MacOS/Quarries"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleDevelopmentRegion</key><string>English</string>
  <key>CFBundleExecutable</key><string>Quarries</string>
  <key>CFBundleIconFile</key><string>Quarries.icns</string>
  <key>CFBundleIdentifier</key><string>com.richmack.quarries</string>
  <key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
  <key>CFBundleName</key><string>Quarries</string>
  <key>CFBundleDisplayName</key><string>Quarries</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.9.2</string>
  <key>CFBundleVersion</key><string>0.9.2</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST

echo "Built $APP"
