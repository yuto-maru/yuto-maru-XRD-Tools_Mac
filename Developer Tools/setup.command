#!/bin/bash

# XRD Tools専用仮想環境を作成・更新する。
# Pythonのマイナーバージョンには固定しない。
# Apple Siliconではarm64、Intel Macではx86_64に統一し、
# Python本体とNumPy/SciPy等のバイナリ拡張の混在を防ぐ。

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$HOME/.xrd_tools_venv"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
ARCH_FILE="$VENV_DIR/.xrd_tools_arch"
REQUIREMENTS_HASH_FILE="$VENV_DIR/.xrd_tools_requirements.sha256"
AUTO_MODE="${XRD_SETUP_AUTO_MODE:-0}"

unset PYTHONHOME
unset PYTHONPATH
unset __PYVENV_LAUNCHER__
unset TCL_LIBRARY
unset TK_LIBRARY
unset VIRTUAL_ENV
unset MPLBACKEND
unset ARCHPREFERENCE
export PYTHONNOUSERSITE=1

pause_and_exit() {
    local code="${1:-1}"
    if [ "$AUTO_MODE" != "1" ]; then
        echo
        read -r -p "Enterキーを押して終了してください..."
    fi
    exit "$code"
}

if [ "$(/usr/sbin/sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" = "1" ]; then
    TARGET_ARCH="arm64"
else
    TARGET_ARCH="x86_64"
fi

run_target() {
    /usr/bin/arch "-$TARGET_ARCH" "$@"
}

python_version() {
    local py="$1"
    run_target "$py" -c 'import sys; print(sys.version.split()[0])' 2>/dev/null
}

python_arch() {
    local py="$1"
    run_target "$py" -c 'import platform; print(platform.machine())' 2>/dev/null
}

base_python_is_usable() {
    local py="$1"
    [ -x "$py" ] || return 1

    run_target "$py" - <<'PY' >/dev/null 2>&1
import platform
import sys
if sys.version_info.major != 3:
    raise RuntimeError("Python 3 is required")
if platform.machine() not in ("arm64", "x86_64"):
    raise RuntimeError("Unsupported architecture")

import tkinter as tk
import venv

root = tk.Tk()
root.withdraw()
root.update_idletasks()
root.destroy()
PY
}

runtime_is_usable() {
    local py="$1"
    [ -x "$py" ] || return 1

    run_target "$py" - <<'PY' >/dev/null 2>&1
import sys
if sys.version_info.major != 3:
    raise RuntimeError("Python 3 is required")

import tkinter as tk
import numpy
import pandas
import matplotlib
import scipy.signal
import pyperclip
import PIL.Image
import openpyxl

root = tk.Tk()
root.withdraw()
root.update_idletasks()
root.destroy()
PY
}

install_runtime_packages() {
    local py="$1"
    local repair="${2:-0}"

    run_target "$py" -m pip install --upgrade --no-cache-dir pip setuptools wheel || return 1

    if [ -f "$REQUIREMENTS_FILE" ]; then
        if [ "$repair" = "1" ]; then
            run_target "$py" -m pip install \
                --force-reinstall --no-cache-dir \
                -r "$REQUIREMENTS_FILE" || return 1
        else
            run_target "$py" -m pip install \
                --upgrade-strategy only-if-needed --no-cache-dir \
                -r "$REQUIREMENTS_FILE" || return 1
        fi
    else
        if [ "$repair" = "1" ]; then
            run_target "$py" -m pip install \
                --force-reinstall --no-cache-dir \
                numpy pandas matplotlib scipy pyperclip Pillow openpyxl || return 1
        else
            run_target "$py" -m pip install \
                --upgrade-strategy only-if-needed --no-cache-dir \
                numpy pandas matplotlib scipy pyperclip Pillow openpyxl || return 1
        fi
    fi
}

write_environment_info() {
    local py="$1"
    printf '%s\n' "$TARGET_ARCH" > "$ARCH_FILE"

    if [ -f "$REQUIREMENTS_FILE" ]; then
        /usr/bin/shasum -a 256 "$REQUIREMENTS_FILE" | /usr/bin/awk '{print $1}' \
            > "$REQUIREMENTS_HASH_FILE"
    fi

    {
        echo "Python: $py"
        echo "Version: $(python_version "$py")"
        echo "Architecture: $(python_arch "$py")"
        echo "Created: $(date '+%Y-%m-%d %H:%M:%S')"
    } > "$VENV_DIR/.xrd_tools_environment"
}

show_success() {
    local py="$VENV_DIR/bin/python3"
    echo
    echo "========================================"
    echo "セットアップが完了しました。"
    echo "専用環境    : $VENV_DIR"
    echo "Python      : $(python_version "$py")"
    echo "Architecture: $(python_arch "$py")"
    echo "========================================"

    if [ "$AUTO_MODE" = "1" ]; then
        echo
        echo "XRD Toolsを自動的に起動します。"
    fi

    pause_and_exit 0
}

echo "========================================"
echo "          XRD Tools Setup"
echo "========================================"
echo "Target architecture: $TARGET_ARCH"
echo

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "requirements.txtが見つかりません:"
    echo "  $REQUIREMENTS_FILE"
    pause_and_exit 1
fi

if [ -x "$VENV_DIR/bin/python3" ]; then
    echo "既存の専用環境を確認しています..."
    echo "Python: $VENV_DIR/bin/python3"
    echo

    if runtime_is_usable "$VENV_DIR/bin/python3"; then
        echo "既存環境は正常です。"
        write_environment_info "$VENV_DIR/bin/python3"
        show_success
    fi

    echo "既存環境のバイナリライブラリを同じアーキテクチャで修復します..."
    if install_runtime_packages "$VENV_DIR/bin/python3" 1 \
       && runtime_is_usable "$VENV_DIR/bin/python3"; then
        write_environment_info "$VENV_DIR/bin/python3"
        show_success
    fi

    BACKUP_DIR="${VENV_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
    echo
    echo "既存環境を退避します:"
    echo "  $BACKUP_DIR"
    mv "$VENV_DIR" "$BACKUP_DIR" || pause_and_exit 1
fi

CANDIDATES=()

add_candidate() {
    local candidate="${1:-}"
    [ -n "$candidate" ] || return 0
    [ "$candidate" = "/usr/bin/python3" ] && return 0

    local existing
    for existing in "${CANDIDATES[@]}"; do
        [ "$existing" = "$candidate" ] && return 0
    done
    CANDIDATES+=("$candidate")
}

add_candidate "/Library/Frameworks/Python.framework/Versions/Current/bin/python3"

if command -v python3 >/dev/null 2>&1; then
    add_candidate "$(command -v python3)"
fi

add_candidate "/opt/homebrew/bin/python3"
add_candidate "/usr/local/bin/python3"
add_candidate "/opt/local/bin/python3"

shopt -s nullglob
for py in \
    /Library/Frameworks/Python.framework/Versions/*/bin/python3 \
    /opt/homebrew/bin/python3.* \
    /usr/local/bin/python3.* \
    /opt/homebrew/opt/python@*/bin/python3* \
    /usr/local/opt/python@*/bin/python3* \
    /opt/local/bin/python3.*
do
    case "$(basename "$py")" in
        *-config|*config*) continue ;;
    esac
    add_candidate "$py"
done
shopt -u nullglob

SELECTED_BASE=""

for BASE_PYTHON in "${CANDIDATES[@]}"; do
    [ -x "$BASE_PYTHON" ] || continue

    echo "確認中: $BASE_PYTHON"
    if ! base_python_is_usable "$BASE_PYTHON"; then
        echo "  使用不可（$TARGET_ARCH、Python 3、venv、Tkinterの確認に失敗）"
        continue
    fi

    echo "  Python $(python_version "$BASE_PYTHON") / $(python_arch "$BASE_PYTHON")"
    echo "  専用環境を作成しています..."

    rm -rf "$VENV_DIR"
    if ! run_target "$BASE_PYTHON" -m venv "$VENV_DIR"; then
        echo "  venvの作成に失敗しました。"
        rm -rf "$VENV_DIR"
        continue
    fi

    VENV_PYTHON="$VENV_DIR/bin/python3"
    echo "  必要ライブラリを導入しています..."

    if install_runtime_packages "$VENV_PYTHON" 0 \
       && runtime_is_usable "$VENV_PYTHON"; then
        SELECTED_BASE="$BASE_PYTHON"
        write_environment_info "$VENV_PYTHON"
        break
    fi

    echo "  このPythonでは必要環境を完成できませんでした。"
    rm -rf "$VENV_DIR"
done

if [ -z "$SELECTED_BASE" ]; then
    echo
    echo "自動検出したPython 3では環境を作成できませんでした。"
    echo "Tkinterと$TARGET_ARCHを使用できるPython 3本体のフルパスを入力してください。"
    echo "何も入力せずEnterを押すと終了します。"
    echo
    read -r -p "Python 3のパス: " MANUAL_PYTHON

    if [ -n "$MANUAL_PYTHON" ] && base_python_is_usable "$MANUAL_PYTHON"; then
        rm -rf "$VENV_DIR"
        if run_target "$MANUAL_PYTHON" -m venv "$VENV_DIR" \
           && install_runtime_packages "$VENV_DIR/bin/python3" 0 \
           && runtime_is_usable "$VENV_DIR/bin/python3"; then
            SELECTED_BASE="$MANUAL_PYTHON"
            write_environment_info "$VENV_DIR/bin/python3"
        else
            rm -rf "$VENV_DIR"
        fi
    fi
fi

if [ -z "$SELECTED_BASE" ] || [ ! -x "$VENV_DIR/bin/python3" ]; then
    echo
    echo "XRD Tools用の環境を作成できませんでした。"
    echo
    echo "次を確認してください:"
    echo "・Python 3がインストールされている"
    echo "・そのPythonが$TARGET_ARCHに対応している"
    echo "・そのPythonでTkinterを使用できる"
    echo "・インターネットに接続されている"
    pause_and_exit 1
fi

show_success
