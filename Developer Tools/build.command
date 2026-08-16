#!/bin/bash

# py2appを使用せず、XRD Tools専用venvのPythonを呼び出す
# 軽量なmacOS .appバンドルを作成する。
# アプリは特定のPython 3.xバージョンに固定せず、初回セットアップをapp内から自動実行する。

set -u

cd "$(dirname "$0")" || exit 1
PROJECT_DIR="$(pwd)"

pause_and_exit() {
    local code="${1:-1}"
    echo
    read -r -p "Enterキーを押して終了してください..."
    exit "$code"
}

echo "========================================"
echo "  XRD Tools Lightweight Release Builder"
echo "========================================"
echo

required=(
    "launcher.py"
    "version.py"
    "tools"
    "setup.command"
    "requirements.txt"
    "make_release_zip.command"
)
for item in "${required[@]}"; do
    if [ ! -e "$PROJECT_DIR/$item" ]; then
        echo "必要なファイルが見つかりません: $item"
        pause_and_exit 1
    fi
done

VERSION="$(/usr/bin/awk -F= '
/^[[:space:]]*VERSION[[:space:]]*=/ {
    value=$2
    gsub(/[[:space:]\047\042]/, "", value)
    print value
    exit
}' "$PROJECT_DIR/version.py")"

if [ -z "$VERSION" ]; then
    echo "version.pyからVERSIONを取得できませんでした。"
    pause_and_exit 1
fi

APP_NAME="XRD Tools.app"
DIST_DIR="$PROJECT_DIR/dist"
APP_DIR="$DIST_DIR/$APP_NAME"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

printf 'Version: %s\n' "$VERSION"
echo "Cleaning..."
rm -rf "$DIST_DIR"
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR/tools"

echo "Creating lightweight app bundle..."

cat > "$MACOS_DIR/XRD Tools" <<'APP_LAUNCHER'
#!/bin/bash

APP_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RESOURCES="$APP_ROOT/Contents/Resources"
SETUP_SCRIPT="$RESOURCES/setup.command"
REQUIREMENTS_FILE="$RESOURCES/requirements.txt"

VENV_DIR="$HOME/.xrd_tools_venv"
VENV_PYTHON="$VENV_DIR/bin/python3"
ARCH_FILE="$VENV_DIR/.xrd_tools_arch"
REQUIREMENTS_HASH_FILE="$VENV_DIR/.xrd_tools_requirements.sha256"

SUPPORT_DIR="$HOME/Library/Application Support/XRD Tools"
SETUP_RUNNER="$SUPPORT_DIR/Run XRD Tools Setup.command"
LOG_DIR="$HOME/Library/Logs"
LOG_FILE="$LOG_DIR/XRD Tools.log"
SETUP_LOG="$LOG_DIR/XRD Tools Setup.log"
MPL_DIR="$SUPPORT_DIR/matplotlib"

mkdir -p "$SUPPORT_DIR" "$LOG_DIR" "$MPL_DIR"

escape_applescript() {
    printf '%s' "$1" | /usr/bin/sed 's/\\/\\\\/g; s/"/\\"/g'
}

show_alert() {
    local message
    message="$(escape_applescript "$1")"
    /usr/bin/osascript -e \
        "display alert \"XRD Tools\" message \"$message\" as critical" \
        >/dev/null 2>&1
}

confirm_setup() {
    /usr/bin/osascript <<'OSA' >/dev/null 2>&1
try
    display dialog "XRD Toolsの初回セットアップが必要です。\n\n必要なPython環境とライブラリを準備します。初回のみ数分かかる場合があり、インターネット接続が必要です。" with title "XRD Tools" buttons {"キャンセル", "セットアップを開始"} default button "セットアップを開始" cancel button "キャンセル" with icon note
    return 0
on error number -128
    return 1
end try
OSA
}

# 旧py2app版や他の仮想環境から受け継いだPython/Tcl設定を解除する。
unset PYTHONHOME
unset PYTHONPATH
unset __PYVENV_LAUNCHER__
unset TCL_LIBRARY
unset TK_LIBRARY
unset VIRTUAL_ENV
unset MPLBACKEND
unset ARCHPREFERENCE

export PYTHONNOUSERSITE=1
export MPLCONFIGDIR="$MPL_DIR"
export TK_SILENCE_DEPRECATION=1
export PATH="$VENV_DIR/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if [ "$(/usr/sbin/sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" = "1" ]; then
    NATIVE_ARCH="arm64"
else
    NATIVE_ARCH="x86_64"
fi

requirements_hash() {
    if [ -f "$REQUIREMENTS_FILE" ]; then
        /usr/bin/shasum -a 256 "$REQUIREMENTS_FILE" 2>/dev/null \
            | /usr/bin/awk '{print $1}'
    fi
}

environment_needs_setup() {
    [ -x "$VENV_PYTHON" ] || return 0
    [ -f "$ARCH_FILE" ] || return 0
    [ "$(cat "$ARCH_FILE" 2>/dev/null)" = "$NATIVE_ARCH" ] || return 0

    local expected_hash saved_hash
    expected_hash="$(requirements_hash)"
    saved_hash="$(cat "$REQUIREMENTS_HASH_FILE" 2>/dev/null)"

    [ -n "$expected_hash" ] || return 0
    [ "$saved_hash" = "$expected_hash" ] || return 0

    return 1
}

start_embedded_setup() {
    if [ ! -x "$SETUP_SCRIPT" ] || [ ! -f "$REQUIREMENTS_FILE" ]; then
        show_alert "アプリ内のセットアップファイルが不足しています。XRD Toolsを再度ダウンロードしてください。"
        exit 1
    fi

    if ! confirm_setup; then
        exit 0
    fi

    cat > "$SETUP_RUNNER" <<RUNNER
#!/bin/bash

unset PYTHONHOME
unset PYTHONPATH
unset __PYVENV_LAUNCHER__
unset TCL_LIBRARY
unset TK_LIBRARY
unset VIRTUAL_ENV
unset MPLBACKEND
unset ARCHPREFERENCE

export XRD_SETUP_AUTO_MODE=1

echo "========================================"
echo "       XRD Tools Initial Setup"
echo "========================================"
echo
echo "セットアップ中はこのウィンドウを閉じないでください。"
echo

/bin/bash "$SETUP_SCRIPT" 2>&1 | /usr/bin/tee "$SETUP_LOG"
status=\${PIPESTATUS[0]}

if [ "\$status" -eq 0 ]; then
    echo
    echo "セットアップが完了しました。XRD Toolsを起動します。"
    sleep 2
    /usr/bin/open "$APP_ROOT"
    exit 0
fi

echo
echo "セットアップに失敗しました。"
echo "ログ: $SETUP_LOG"
echo
read -r -p "Enterキーを押して終了してください..."
exit "\$status"
RUNNER

    chmod +x "$SETUP_RUNNER"
    /usr/bin/open -a Terminal "$SETUP_RUNNER"
    exit 0
}

if environment_needs_setup; then
    start_embedded_setup
fi

TARGET_ARCH="$(cat "$ARCH_FILE" 2>/dev/null)"
case "$TARGET_ARCH" in
    arm64|x86_64) ;;
    *) TARGET_ARCH="$NATIVE_ARCH" ;;
esac

PYTHON_CMD=(/usr/bin/arch "-$TARGET_ARCH" "$VENV_PYTHON")

{
    echo
    echo "========================================"
    echo "XRD Tools launch: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "App: $APP_ROOT"
    echo "Python: $VENV_PYTHON"
    echo "Architecture: $TARGET_ARCH"
    "${PYTHON_CMD[@]}" --version
    echo "========================================"
} >>"$LOG_FILE" 2>&1

"${PYTHON_CMD[@]}" "$RESOURCES/launcher.py" >>"$LOG_FILE" 2>&1
status=$?

if [ "$status" -ne 0 ]; then
    # 専用環境の破損が疑われる場合に、手動でsetup.commandを探させず
    # app内セットアップを案内する。
    answer=$(/usr/bin/osascript <<OSA 2>/dev/null
try
    display dialog "XRD Toolsの起動に失敗しました。\n\n専用環境を自動修復しますか？\n\nログ:\n$LOG_FILE" with title "XRD Tools" buttons {"キャンセル", "環境を修復"} default button "環境を修復" cancel button "キャンセル" with icon caution
    return button returned of result
on error number -128
    return "キャンセル"
end try
OSA
)
    if [ "$answer" = "環境を修復" ]; then
        rm -f "$REQUIREMENTS_HASH_FILE"
        start_embedded_setup
    fi
fi

exit "$status"
APP_LAUNCHER

chmod +x "$MACOS_DIR/XRD Tools"

cp "$PROJECT_DIR/launcher.py" "$RESOURCES_DIR/launcher.py"
cp "$PROJECT_DIR/version.py" "$RESOURCES_DIR/version.py"
cp "$PROJECT_DIR/setup.command" "$RESOURCES_DIR/setup.command"
cp "$PROJECT_DIR/requirements.txt" "$RESOURCES_DIR/requirements.txt"
chmod +x "$RESOURCES_DIR/setup.command"

# tools内の隠しファイルを除き、現在の全ツールをそのまま収録する。
find "$PROJECT_DIR/tools" -maxdepth 1 -type f ! -name '.*' -exec cp {} "$RESOURCES_DIR/tools/" \;

if [ -f "$PROJECT_DIR/XRD.icns" ]; then
    cp "$PROJECT_DIR/XRD.icns" "$RESOURCES_DIR/XRD.icns"
fi

cat > "$CONTENTS_DIR/Info.plist" <<EOF_PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>XRD Tools</string>
    <key>CFBundleDisplayName</key>
    <string>XRD Tools</string>
    <key>CFBundleExecutable</key>
    <string>XRD Tools</string>
    <key>CFBundleIdentifier</key>
    <string>jp.local.xrdtools</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleVersion</key>
    <string>${VERSION}</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
EOF_PLIST

if [ -f "$PROJECT_DIR/XRD.icns" ]; then
    cat >> "$CONTENTS_DIR/Info.plist" <<'EOF_ICON'
    <key>CFBundleIconFile</key>
    <string>XRD.icns</string>
EOF_ICON
fi

cat >> "$CONTENTS_DIR/Info.plist" <<'EOF_PLIST_END'
    <key>LSArchitecturePriority</key>
    <array>
        <string>arm64</string>
        <string>x86_64</string>
    </array>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF_PLIST_END

printf 'APPL????' > "$CONTENTS_DIR/PkgInfo"
/usr/bin/plutil -lint "$CONTENTS_DIR/Info.plist" || pause_and_exit 1

/usr/bin/xattr -cr "$APP_DIR" 2>/dev/null || true
if command -v codesign >/dev/null 2>&1; then
    /usr/bin/codesign --force --deep --sign - "$APP_DIR" >/dev/null 2>&1 || true
fi

if [ ! -d "$APP_DIR" ]; then
    echo "アプリ作成に失敗しました。"
    pause_and_exit 1
fi

echo "Creating release package..."
XRD_BUILD_NO_PAUSE=1 /bin/bash "$PROJECT_DIR/make_release_zip.command" || pause_and_exit 1

echo
echo "========================================"
echo "Completed"
echo "App : $APP_DIR"
echo "ZIP : $PROJECT_DIR/XRD_Tools_v${VERSION}.zip"
echo "========================================"
echo
echo "この構成ではsetup.py、py2app、pyi_runtime_hook.pyを使用しません。"
pause_and_exit 0
