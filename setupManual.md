# XRD Tools 利用者向けセットアップガイド（macOS）

## 1. はじめに

XRD Toolsは、MacにインストールされているPython 3を利用して動作します。
完全なスタンドアロン版ではないため、初回のみ以下の準備が必要です。

必要なもの

- Python 3
- tkinter
- numpy
- pandas
- matplotlib
- scipy
- pyperclip
- Pillow

Pythonは、tkinterが同梱されるpython.org公式版の使用を推奨します。
Homebrew版Pythonが入っている場合でも、XRD Tools用としてpython.org公式版を
追加でインストールできます。

## 2. Python 3をインストールする

1. WebブラウザでPython公式サイトのmacOS向けダウンロードページを開きます。

<https://www.python.org/downloads/macos/>

2. 最新の安定版にある「Download macOS installer」を選び、
```text
.pkg形式のインストーラーをダウンロードします。
```

3. ダウンロードした.pkgファイルをダブルクリックします。

4. 画面の案内に従い、標準設定のままインストールします。

5. インストール後、「アプリケーション」フォルダ内に作成された
```text
「Python 3.x」フォルダを開きます。
```

6. 「Install Certificates.command」がある場合は、
```text
ダブルクリックして実行します。
```

python.org公式版では、通常、Python本体へのリンクが次の場所に作成されます。

```text
/usr/local/bin/python3
```

Python本体の実体は、通常、次のような場所にあります。

```text
/Library/Frameworks/Python.framework/Versions/3.x/bin/python3
```

## 3. Python 3が使用できるか確認する

「ターミナル」アプリを開き、以下をコピーして実行します。

```text
/usr/local/bin/python3 --version
```

「Python 3.x.x」のように表示されれば、Pythonのインストールは完了しています。

次に、Pythonの実体を確認します。

```text
/usr/local/bin/python3 -c "import sys; print(sys.executable)"
```

次のような場所が表示されれば正常です。

```text
/Library/Frameworks/Python.framework/Versions/3.x/bin/python3
```

## 4. tkinterを確認する

以下をターミナルで実行します。

```text
/usr/local/bin/python3 -m tkinter
```

小さなテストウィンドウが開けば、tkinterは正常に使用できます。
確認後はテストウィンドウを閉じてください。

重要：

- tkinterは「pip install tkinter」ではインストールできません。
- python.org公式版には、通常tkinterが同梱されています。
- 「No module named tkinter」または「No module named _tkinter」と表示された場合は、
python.org公式版Pythonを再インストールしてください。

## 5. XRD Toolsに必要なライブラリをインストールする

以下のコマンドをターミナルに貼り付けて実行します。

```text
/usr/local/bin/python3 -m pip install --user numpy pandas matplotlib scipy pyperclip pillow
```

インストールには数分かかる場合があります。
処理が止まって見える場合でも、完了メッセージが表示されるまで待ってください。

pipの更新を求められた場合は、以下を実行できます。

```text
/usr/local/bin/python3 -m pip install --user --upgrade pip
```

その後、もう一度ライブラリのインストールコマンドを実行してください。

## 6. 必要なライブラリをまとめて確認する

以下をターミナルで実行します。

```text
/usr/local/bin/python3 -c "import tkinter, numpy, pandas, matplotlib, scipy, pyperclip; from PIL import Image; print('XRD Tools setup OK')"
```

次のように表示されれば、準備完了です。

```text
XRD Tools setup OK
```

## 7. XRD Toolsを起動する

1. 配布されたZIPファイルを展開します。

2. 「XRD Tools.app」をダブルクリックします。

3. macOSの警告で開けない場合は、「XRD Tools.app」をControlキーを押しながら
```text
クリックし、「開く」を選択します。
```

4. 確認画面でもう一度「開く」を選択します。

5. 使用したい機能をXRD Toolsの画面から選択します。

各ツールを起動すると、ターミナルのウィンドウが開く場合があります。
ツールを使用している間は、そのターミナルを閉じないでください。

## 8. Python 3の選択画面が表示された場合

XRD ToolsがPython 3を自動検出できなかった場合は、
Python本体を選択する画面が表示されます。

まず、次のファイルを選択してください。

```text
/usr/local/bin/python3
```

選択できない場合は、次のフォルダを開き、使用中のバージョンのpython3を選択します。

```text
/Library/Frameworks/Python.framework/Versions/
```

例：

```text
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3
```

## 9. よくあるエラーと対処方法

### ModuleNotFoundError: No module named 'numpy' など

アプリが使用するPythonに必要なライブラリが入っていません。
以下をもう一度実行してください。

```text
/usr/local/bin/python3 -m pip install --user numpy pandas matplotlib scipy pyperclip pillow
```

インストール状況は、例えば以下で確認できます。

```text
/usr/local/bin/python3 -m pip show numpy
```

### ModuleNotFoundError: No module named 'tkinter'

tkinterはpipではインストールできません。
python.org公式版Pythonをインストールし直してください。

確認コマンド：

```text
/usr/local/bin/python3 -m tkinter
```

### externally-managed-environment と表示される

Homebrew版Pythonに対してpipを実行している可能性があります。
本ガイドでは「--break-system-packages」は使用せず、
python.org公式版の次のPythonを使用してください。

```text
/usr/local/bin/python3
```

Pythonの実体を確認するコマンド：

```text
/usr/local/bin/python3 -c "import sys; print(sys.executable)"
```

「/Library/Frameworks/Python.framework/」から始まる場所が表示されれば、
python.org公式版です。

### XRD Toolsが別のPythonを記憶している

以下をターミナルで実行すると、XRD Toolsが記憶したPythonの場所をリセットできます。

```text
rm ~/.xrd_tools_launcher_settings.json
```

その後、XRD Toolsを開き直してください。

### Python3が見つかりません と表示される

以下を順番に実行して確認してください。

```text
ls -l /usr/local/bin/python3
```

```text
/usr/local/bin/python3 --version
```

どちらも正常であれば、XRD ToolsのPython選択画面で
「/usr/local/bin/python3」を手動で選択してください。

### インストール後も同じエラーが出る

Macに複数のPythonが入っている可能性があります。
以下の2つを実行し、同じPythonを使用しているか確認してください。

```text
/usr/local/bin/python3 -c "import sys; print(sys.executable)"
```

```text
/usr/local/bin/python3 -m pip --version
```

どちらにも「/Library/Frameworks/Python.framework/Versions/3.x/」が
含まれていることを確認してください。

## 10. アンインストールについて

XRD Toolsだけを削除する場合は、「XRD Tools.app」をゴミ箱へ移動します。

XRD Toolsが記憶した設定も削除する場合は、以下を実行します。

```text
rm ~/.xrd_tools_launcher_settings.json
```

Pythonやライブラリは、ほかのPythonソフトでも使用される可能性があるため、
必要がなければ削除しないことを推奨します。

## 11. 参考

Python公式 macOSダウンロードページ

<https://www.python.org/downloads/macos/>

Python公式 tkinterドキュメント

<https://docs.python.org/3/library/tkinter.html>

Python公式 macOS利用ガイド

<https://docs.python.org/3/using/mac.html>

以上
