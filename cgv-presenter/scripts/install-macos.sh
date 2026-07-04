#!/bin/bash
set -euo pipefail

APP_NAME="CGV Presenter.app"
TARGET="/Applications/$APP_NAME"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_APP=""

if [[ -d "$SCRIPT_DIR/../$APP_NAME" ]]; then
  SOURCE_APP="$SCRIPT_DIR/../$APP_NAME"
elif [[ -d "./$APP_NAME" ]]; then
  SOURCE_APP="./$APP_NAME"
else
  echo "Could not find $APP_NAME next to this script."
  echo "Use Install CGV Presenter instead, or unzip the full release folder first."
  exit 1
fi

echo "Installing CGV Presenter..."
rm -rf "$TARGET"
cp -R "$SOURCE_APP" "$TARGET"
xattr -cr "$TARGET"
open "$TARGET"
