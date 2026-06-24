#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export CARGO_TARGET_DIR="$ROOT/src-tauri/target"

echo "Building CGV Writer…"
npm run tauri -- build --bundles app

APP_SRC="$CARGO_TARGET_DIR/release/bundle/macos/CGV Writer.app"
APP_DEST="/Applications/CGV Writer.app"

if [[ ! -d "$APP_SRC" ]]; then
  echo "Build finished but app bundle not found at:" >&2
  echo "  $APP_SRC" >&2
  exit 1
fi

echo "Installing to $APP_DEST"
rm -rf "$APP_DEST"
cp -R "$APP_SRC" "$APP_DEST"
touch "$APP_DEST"

echo "Done. Opening CGV Writer…"
open "$APP_DEST"
