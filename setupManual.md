# XRD Tools 利用者向けセットアップガイド（macOS）

## 1. はじめに

XRD Toolsは、MacにインストールされているPython 3を利用して動作します。

初回起動時に、XRD Toolsが必要な専用Python環境を自動的に作成し、
必要なPythonライブラリも自動でインストールします。

そのため、利用者が次の作業を手動で行う必要はありません。

- XRD Tools専用の仮想環境を作成する
- `numpy`、`pandas`、`matplotlib`、`scipy` などを個別にインストールする
- XRD Tools用のPythonパスを設定する
- 専用環境のPythonを手動で選択する

通常は、Python 3が使用できるMacで **XRD Tools.appをダブルクリックするだけ** でセットアップできます。

---

## 2. 利用に必要なもの

必要なものは次のとおりです。

- macOS
- インターネット接続（初回セットアップ時）
- Python 3
- tkinterが使用できるPython 3

XRD Toolsで使用する次のライブラリは、初回セットアップ時に自動で専用環境へインストールされます。

- numpy
- pandas
- matplotlib
- scipy
- pyperclip
- Pillow
- openpyxl

すでに使用可能なPython 3とtkinterがインストールされている場合は、
Pythonを追加でインストールする必要はありません。

---

## 3. XRD Toolsを起動する

1. 配布されたZIPファイルを展開します。

2. 展開したフォルダ内の **XRD Tools.app** をダブルクリックします。

3. 初回起動時、XRD Tools専用環境がまだ作成されていない場合は、
   セットアップの案内が表示されます。

4. 画面の案内に従ってセットアップを開始します。

5. セットアップ処理では、XRD Toolsが自動的に使用可能なPython 3を確認し、
   専用環境と必要なライブラリを準備します。

6. セットアップ完了後、XRD Toolsを起動します。

初回セットアップ中は、ターミナルのウィンドウが表示される場合があります。
処理が完了するまでは、そのウィンドウを閉じないでください。

---

## 4. 初回セットアップで自動的に行われること

XRD Toolsは初回セットアップ時に、主に次の処理を自動で行います。

1. Mac内にある使用可能なPython 3を確認する
2. Python 3でtkinterが使用できることを確認する
3. XRD Tools専用環境を次の場所に作成する

```bash
~/.xrd_tools_venv
```

4. 専用環境へ必要なPythonライブラリをインストールする
5. 専用環境が正常に使用できることを確認する
6. 以後、XRD Tools本体と各解析ツールをこの専用Python環境で実行する

この専用環境はXRD Tools専用です。
Mac全体のPython環境や、ほかのPythonプロジェクトには影響しません。

### 利用者が手動で行う必要のない操作

次のようなコマンドを利用者が実行する必要はありません。

```bash
python3 -m venv ~/.xrd_tools_venv
pip install numpy
pip install scipy
pip install matplotlib
```

これらはXRD Toolsのセットアップ機能が自動的に処理します。

---

## 5. macOSの警告でXRD Toolsを開けない場合

初回起動時、macOSのセキュリティ機能により
XRD Tools.appをそのまま開けない場合があります。

その場合は、次の手順を試してください。

1. **XRD Tools.app** をControlキーを押しながらクリックします。
2. メニューから **「開く」** を選択します。
3. 確認画面が表示された場合は、もう一度 **「開く」** を選択します。

一度許可すると、通常は次回以降ダブルクリックで起動できます。

---

## 6. Python 3が入っているか分からない場合

まずXRD Tools.appを起動してください。

使用可能なPython 3が見つかれば、XRD ToolsがそのPythonを利用して
専用環境を自動作成します。

Python 3が見つからない場合や、tkinterが使用できない場合のみ、
Python 3をインストールしてください。

### 推奨：python.org公式版Python

最も簡単なのは、python.org公式版Pythonを使用する方法です。

1. 次のページを開きます。

<https://www.python.org/downloads/macos/>

2. macOS用のPython 3インストーラー（`.pkg`）をダウンロードします。
3. ダウンロードした`.pkg`をダブルクリックします。
4. 画面の案内に従い、標準設定でインストールします。
5. インストール完了後、もう一度XRD Tools.appを起動します。

python.org公式版には通常tkinterが含まれているため、
XRD Tools用として扱いやすい方法です。

---

## 7. Homebrew版Pythonを使用する場合

すでにHomebrewを使用している場合は、Homebrew版Pythonも利用できます。

Pythonをインストールする場合：

```bash
brew install python
```

HomebrewではPythonとtkinterが別パッケージになっている場合があります。

Pythonのバージョンを確認します。

```bash
PYVER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "$PYVER"
```

対応するtkinterをインストールします。

```bash
brew install "python-tk@$PYVER"
```

tkinterを確認する場合：

```bash
python3 -m tkinter
```

小さなテストウィンドウが開けば使用できます。

この確認後は、専用環境を手動で作成する必要はありません。
XRD Tools.appを起動すれば、XRD Toolsが自動で専用環境を準備します。

---

## 8. 通常の起動

初回セットアップが完了した後は、

**XRD Tools.appをダブルクリックするだけ**

で起動できます。

XRD Toolsは、次の専用環境のPythonを使用します。

```bash
~/.xrd_tools_venv/bin/python3
```

Peak Picker、Indexing、TIF Viewerなどの各解析ツールも、
同じXRD Tools専用Python環境から起動します。

---

## 9. XRD Toolsを更新する場合

新しいバージョンのXRD Toolsを入手した場合は、
基本的にXRD Tools.appを新しいものへ置き換えるだけです。

XRD Tools専用環境

```bash
~/.xrd_tools_venv
```

はユーザーのホームフォルダに保存されているため、
通常はXRD Tools.appを置き換えてもそのまま保持されます。

新しいバージョンでライブラリ構成の変更などが必要になった場合は、
XRD Tools側から再セットアップが案内される場合があります。
その場合は画面の案内に従ってください。

---

## 10. セットアップに失敗する場合

### 10-1. Pythonが見つからない

python.org公式版Python 3をインストールしてから、
もう一度XRD Tools.appを起動してください。

<https://www.python.org/downloads/macos/>

### 10-2. tkinterが使用できない

python.org公式版Pythonを使用している場合は、
Pythonを公式インストーラーから再インストールしてください。

Homebrew版Pythonを使用している場合は、
使用中のPythonと同じバージョンの`python-tk`を確認してください。

例：

```bash
PYVER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
brew install "python-tk@$PYVER"
```

### 10-3. セットアップ途中でエラーになった

まずXRD Tools.appを終了し、もう一度起動してセットアップを実行してください。

専用環境の削除や再作成は通常必要ありません。

繰り返し失敗する場合に限り、開発者から案内された手順に従って
専用環境を再作成してください。

---

## 11. XRD Tools専用環境について

XRD Toolsは次のフォルダを専用Python環境として使用します。

```bash
~/.xrd_tools_venv
```

この環境はXRD Tools専用であり、

- macOSのシステムPython
- HomebrewのPython
- python.org公式版Python
- ほかのPython仮想環境

を直接変更するものではありません。

通常の利用では、このフォルダを手動で操作する必要はありません。

---

## 12. アンインストール

XRD Tools本体を削除する場合は、
**XRD Tools.app** を削除します。

XRD Tools専用Python環境も完全に削除したい場合のみ、
次のフォルダを削除します。

```bash
~/.xrd_tools_venv
```

XRD Toolsのランチャー設定も削除する場合は、
次のファイルを削除します。

```bash
~/.xrd_tools_launcher_settings.json
```

これらを削除しても、
MacにインストールされているPython本体やHomebrewには影響しません。

---

## 13. 参考

Python公式 macOSダウンロードページ

<https://www.python.org/downloads/macos/>

Python公式 tkinterドキュメント

<https://docs.python.org/3/library/tkinter.html>

Python公式 venvドキュメント

<https://docs.python.org/3/library/venv.html>

Homebrew公式サイト

<https://brew.sh/>

Homebrew Pythonパッケージ

<https://formulae.brew.sh/formula/python>

Homebrew tkinterパッケージ

<https://formulae.brew.sh/formula/python-tk>

---

以上
