#!/bin/bash

# dist/XRD Tools.appだけを配布ZIPへ収録する。
# setup.commandとrequirements.txtはapp内部に含まれるため、
# 利用者が別ファイルを手動実行する必要はない。

set -euo pipefail
cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"

pause_if_needed() {
    if [ "${XRD_BUILD_NO_PAUSE:-0}" != "1" ]; then
        echo
        read -r -p "Enterキーを押して終了してください..."
    fi
}

VERSION="$(/usr/bin/awk -F= '
/^[[:space:]]*VERSION[[:space:]]*=/ {
    value=$2
    gsub(/[[:space:]\047\042]/, "", value)
    print value
    exit
}' "$PROJECT_DIR/version.py")"

if [ -z "$VERSION" ]; then
    echo "version.pyからVERSIONを取得できませんでした。"
    pause_if_needed
    exit 1
fi

APP_DIR="$PROJECT_DIR/dist/XRD Tools.app"
ZIP_PATH="$PROJECT_DIR/XRD_Tools_v${VERSION}.zip"

if [ ! -d "$APP_DIR" ]; then
    echo "アプリが見つかりません: $APP_DIR"
    echo "先にbuild.commandを実行してください。"
    pause_if_needed
    exit 1
fi

rm -rf "$PROJECT_DIR/release"
rm -f "$ZIP_PATH"

/usr/bin/xattr -cr "$APP_DIR" 2>/dev/null || true
/usr/bin/ditto -c -k --sequesterRsrc --keepParent "$APP_DIR" "$ZIP_PATH"

if [ ! -f "$ZIP_PATH" ]; then
    echo "ZIP作成に失敗しました。"
    pause_if_needed
    exit 1
fi

echo "Created: $ZIP_PATH"
echo "ZIP contents: XRD Tools.app only"
echo "App remains only in: $APP_DIR"
pause_if_needed
