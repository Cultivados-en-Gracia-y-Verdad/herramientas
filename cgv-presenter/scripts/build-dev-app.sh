#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="CGV Presenter Dev"
APP_DIR="$ROOT/out/CGV Presenter Dev.app"
LAUNCHER="$ROOT/scripts/cgv-presenter-dev-launcher.sh"
ICON="$ROOT/assets/cgv-app-icon.icns"
INSTALL="${1:-}"

if [[ ! -f "$LAUNCHER" ]]; then
  echo "Missing launcher script: $LAUNCHER" >&2
  exit 1
fi

rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"

cp "$LAUNCHER" "$APP_DIR/Contents/MacOS/CGV Presenter Dev"
chmod +x "$APP_DIR/Contents/MacOS/CGV Presenter Dev"

if [[ -f "$ICON" ]]; then
  cp "$ICON" "$APP_DIR/Contents/Resources/AppIcon.icns"
fi

cat > "$APP_DIR/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleExecutable</key>
  <string>CGV Presenter Dev</string>
  <key>CFBundleIconFile</key>
  <string>AppIcon</string>
  <key>CFBundleIdentifier</key>
  <string>org.cgv.presenter.dev</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>${APP_NAME}</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>CFBundleVersion</key>
  <string>1</string>
  <key>LSMinimumSystemVersion</key>
  <string>11.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
EOF

codesign --force --deep --sign - "$APP_DIR" >/dev/null 2>&1 || true

echo "Built $APP_DIR"

if [[ "$INSTALL" == "--install" ]]; then
  TARGET="/Applications/${APP_NAME}.app"
  rm -rf "$TARGET"
  ditto "$APP_DIR" "$TARGET"
  xattr -cr "$TARGET" 2>/dev/null || true
  codesign --force --deep --sign - "$TARGET" >/dev/null 2>&1 || true
  SUPPORT="$HOME/Library/Application Support/CGV Presenter Dev"
  mkdir -p "$SUPPORT"
  printf '%s\n' "$ROOT" > "$SUPPORT/project-root"
  echo "Installed $TARGET"
fi
