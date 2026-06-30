# XRD Tools 利用者向けセットアップガイド（macOS）

## 1. はじめに

XRD Toolsは、MacにインストールされているPython 3を利用して動作します。
すでにPython 3がインストールされている場合は、手順8から行なってください。

必要なもの

- Python 3
- tkinter
- numpy
- pandas
- matplotlib
- scipy
- pyperclip
- Pillow

Python 3の導入方法は、次のどちらかを選べます。

【方法A】HomebrewからPython 3とtkinterを入れる
【方法B】python.org公式インストーラーからPython 3を入れる

すでに使用できるPython 3とtkinterが入っている場合は、
新しいPythonを追加する必要はありません。

**注意：**
別の方法でPython 3をすでにインストールしている状態で
Homebrew版Pythonを入れると、複数のPythonが共存します。
通常は問題ありませんが、XRD Tools用には
「~/.xrd_tools_venv」に専用環境を作成し、
そのPythonを使用することで混乱を防ぎます。

## 2. ターミナルを開く

Finderで次の順に開きます。

```bash
アプリケーション
→ ユーティリティ
→ ターミナル
```

以下のコマンドは、ターミナルへ1行ずつコピーして実行してください。

## 方法A：HomebrewからPython 3とtkinterを入れる

## 3-A. Xcode Command Line Toolsを確認する

Homebrewを使うには、Xcode Command Line Toolsが必要です。
容量の大きいXcode本体をインストールする必要はありません。

次のコマンドを実行します。

```bash
xcode-select -p
```

次のように表示されれば、すでに使用できます。

```bash
/Library/Developer/CommandLineTools
```

「no developer tools」などのエラーが表示された場合は、
次を実行します。

```bash
xcode-select --install
```

確認画面が表示されたら「インストール」を選び、
完了するまで待ってください。

インストール完了後、ターミナルを開き直して確認します。

```bash
xcode-select -p
```

まだ正しい場所が表示されない場合は、次を実行します。

```bash
sudo xcode-select --reset
sudo xcode-select --switch /Library/Developer/CommandLineTools
```

再度確認します。

```bash
xcode-select -p
```

## 4-A. Homebrewが入っているか確認する

次のコマンドを実行します。

```bash
brew --version
```

「Homebrew 〇.〇.〇」のように表示された場合は、
「5-A. Python 3をインストールする」へ進んでください。

「command not found: brew」と表示された場合は、
次のコマンドでHomebrewをインストールします。

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

途中でMacのログインパスワードを求められる場合があります。
パスワードを入力しても画面には文字や記号が表示されません。
そのまま入力してReturnキーを押してください。

インストール終了時に「Next steps」としてコマンドが表示された場合は、
画面に表示されたコマンドを必ず実行してください。

Apple Silicon（M1、M2、M3、M4など）では、
通常Homebrewは次の場所に入ります。

```bash
/opt/homebrew
```

Intel Macでは、通常次の場所に入ります。

```bash
/usr/local
```

ターミナルを開き直して、次を確認します。

```bash
brew --version
```

## 5-A. Python 3をインストールする

次を実行します。

```bash
brew update
brew install python
```

すでにインストール済みの場合は、
「already installed」などと表示されることがありますが問題ありません。

Homebrew版Pythonの場所とバージョンを確認します。

```bash
BREW_PYTHON="$(brew --prefix)/bin/python3"
"$BREW_PYTHON" --version
```

Python本体の実際の場所も確認できます。

```bash
"$BREW_PYTHON" -c "import sys; print(sys.executable)"
```

## 6-A. Homebrew版Python用のtkinterをインストールする

Homebrewでは、Python本体とtkinterが別パッケージになっています。

まず、Pythonのメジャー・マイナーバージョンを取得します。

```bash
PYVER="$("$BREW_PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "$PYVER"
```

続いて、同じバージョンのtkinterをインストールします。

```bash
brew install "python-tk@$PYVER"
```

すでに入っている場合や、修復したい場合は次を実行します。

```bash
brew reinstall "python-tk@$PYVER"
```

tkinterを確認します。

```bash
"$BREW_PYTHON" -m tkinter
```

小さなテストウィンドウが開けば正常です。
確認後はウィンドウを閉じてください。

コマンドだけで確認する場合：

```bash
"$BREW_PYTHON" -c "import tkinter; print('tkinter OK:', tkinter.TkVersion)"
```

正常なら、「7. XRD Tools専用環境を作る」へ進んでください。

## 方法B：python.org公式版Python 3を入れる

## 3-B. Python 3をインストールする

1. Webブラウザで次のページを開きます。

<https://www.python.org/downloads/macos/>

2. macOS用の.pkgインストーラーをダウンロードします。

3. ダウンロードした.pkgファイルをダブルクリックします。

4. 画面の案内に従い、標準設定のままインストールします。

5. 「アプリケーション」フォルダ内に作成された
```bash
「Python 3.x」フォルダを開きます。
```

6. 「Install Certificates.command」がある場合は、
```bash
ダブルクリックして実行します。
```

python.org公式版のPython本体は、通常、次のような場所にあります。

```bash
/Library/Frameworks/Python.framework/Versions/3.x/bin/python3
```

また、通常は次のリンクが作られます。

```bash
/usr/local/bin/python3
```

## 4-B. python.org公式版Pythonを確認する

次を実行します。

```bash
/usr/local/bin/python3 --version
```

Pythonの実体を確認します。

```bash
/usr/local/bin/python3 -c "import sys; print(sys.executable)"
```

次のような場所が表示されれば、python.org公式版です。

```bash
/Library/Frameworks/Python.framework/Versions/3.x/bin/python3
```

このPythonを使用するように設定します。

```bash
BASE_PYTHON="/usr/local/bin/python3"
```

## 5-B. tkinterを確認する

次を実行します。

```bash
"$BASE_PYTHON" -m tkinter
```

小さなテストウィンドウが開けば正常です。
python.org公式版には、通常tkinterが同梱されています。

次のエラーが出る場合は、python.org公式版Pythonを
同じバージョンのインストーラーで再インストールしてください。

```bash
ModuleNotFoundError: No module named 'tkinter'
```

または：

```bash
ModuleNotFoundError: No module named '_tkinter'
```

正常なら、「7. XRD Tools専用環境を作る」へ進んでください。

## 共通手順

## 7. 使用するPythonを設定する

Homebrew版を選んだ場合は、次を実行します。

```bash
BASE_PYTHON="$(brew --prefix)/bin/python3"
```

python.org公式版を選んだ場合は、次を実行します。

```bash
BASE_PYTHON="/usr/local/bin/python3"
```

すでに別の場所にあるPython 3を使う場合は、
その実体の完全なパスを指定します。

確認します。

```bash
"$BASE_PYTHON" --version
"$BASE_PYTHON" -m tkinter
```

Pythonのバージョンが表示され、
tkinterのテストウィンドウが開けば使用できます。

## 8. XRD Tools専用環境を作る

Homebrew版Pythonへ直接pip installすると、
「externally-managed-environment」と表示されることがあります。

これを避け、ほかのPython環境へ影響を与えないため、
XRD Tools専用の仮想環境（.xrd_tools_venv）を作成します。

以前の専用環境を作り直す場合のみ、先に削除します。

```bash
rm -rf "$HOME/.xrd_tools_venv"
```

専用環境を作成します。

```bash
"$BASE_PYTHON" -m venv "$HOME/.xrd_tools_venv"
```

専用環境のPythonを確認します。

```bash
"$HOME/.xrd_tools_venv/bin/python3" --version
```

専用環境でもtkinterを確認します。

```bash
"$HOME/.xrd_tools_venv/bin/python3" -m tkinter
```

テストウィンドウが開けば正常です。

**注意：**
専用環境はMac全体のPythonを変更しません。
不要になった場合は「~/.xrd_tools_venv」を削除するだけで元に戻せます。

## 9. 必要なライブラリをインストールする

まず、専用環境内のpipを更新します。

```bash
"$HOME/.xrd_tools_venv/bin/python3" -m pip install --upgrade pip
```

次に、必要なライブラリをインストールします。

```bash
"$HOME/.xrd_tools_venv/bin/python3" -m pip install numpy pandas matplotlib scipy pyperclip pillow
```

インストールには数分かかる場合があります。
完了するまでターミナルを閉じないでください。

この方法では「--break-system-packages」は使用しません。

## 10. すべてのライブラリを確認する

次を実行します。

```bash
"$HOME/.xrd_tools_venv/bin/python3" -c "import tkinter, numpy, pandas, matplotlib, scipy, pyperclip; from PIL import Image; print('XRD Tools setup OK')"
```

次のように表示されれば準備完了です。

```bash
XRD Tools setup OK
```

## 11. XRD Toolsを起動する

1. 配布されたZIPファイルを展開します。

2. 「XRD Tools.app」をダブルクリックします。

3. macOSの警告で開けない場合は、
```bash
XRD Tools.appをControlキーを押しながらクリックします。
```

4. 「開く」を選択します。

5. 確認画面でもう一度「開く」を選択します。

各ツールを起動すると、ターミナルのウィンドウが開く場合があります。
ツールを使用している間は、そのターミナルを閉じないでください。

XRD Toolsは、次の専用Pythonを自動検出します。

```bash
~/.xrd_tools_venv/bin/python3
```

別のPython（例えば古いバージョン3.9など）で開けてしまう場合、
過去に開いたことのあるPython3で開ける仕様になっているため、
次を実行します。

```bash
rm ~/ .xrd_tools_launcher_settings.json
```

再度開け直すと、優先順位の高いPython3を探し直してくれる。


## 12. Python 3の選択画面が表示された場合

XRD ToolsがPythonを自動検出できなかった場合は、
次のPythonを選択してください。

```bash
~/.xrd_tools_venv/bin/python3
```

ファイル選択画面でCommand + Shift + Gを押し、
次の場所を入力します。

```bash
~/.xrd_tools_venv/bin
```

表示された「python3」を選択してください。


## 13. 参考

Homebrew公式サイト

<https://brew.sh/>

Homebrewインストール説明

<https://docs.brew.sh/Installation>

Homebrew Pythonパッケージ

<https://formulae.brew.sh/formula/python>

Homebrew tkinterパッケージ

<https://formulae.brew.sh/formula/python-tk>

Python公式 macOSダウンロードページ

<https://www.python.org/downloads/macos/>

Python公式 tkinterドキュメント

<https://docs.python.org/3/library/tkinter.html>

Python公式 venvドキュメント

<https://docs.python.org/3/library/venv.html>

以上
