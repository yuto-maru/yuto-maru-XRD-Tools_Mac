# XRD Tools 開発者向け README（macOS）

このREADMEは、XRD Tools macOS版のソース管理、専用Python環境、ビルド、更新、配布、トラブル確認のための開発者向け資料である。

利用者向けの操作方法は、別途「XRD Tools 使用マニュアル」を参照すること。

---

## 1. 基本方針

macOS版 XRD Toolsは、py2appを使用しない軽量 `.app` 方式で構成する。

- 解析ツール本体はPythonスクリプトとして管理する
- Python本体やNumPy、SciPy、Matplotlibなどを `.app` に直接バンドルしない
- 各ユーザーのMac上にXRD Tools専用Python環境を作成する
- ランチャーおよび全解析ツールは専用環境のPythonで実行する
- 専用環境の作成、必要ライブラリの導入、更新、修復はアプリ側で自動的に行う
- Apple SiliconおよびIntel Macの両方に対応する
- 利用者へは原則として `XRD Tools.app` のみを配布する
- `setup.command` や `requirements.txt` は `.app` 内部へ含める

専用Python環境：

```text
~/.xrd_tools_venv
```

---

## 2. 解析ツール

ランチャーから起動する主なツール：

| 表示名 | ファイル名 |
|---|---|
| Peak Picker (.chi) | `peak_picker_chi.py` |
| Peak Picker (.dat) | `peak_picker_dat.py` |
| Col Oblique Indexing | `peak_Colob.py` |
| Col Rectangular Indexing | `peak_Colr.py` |
| Colr Lattice Editor | `Colr_lattice_editor.py` |
| TIF Viewer | `interactive_viewer.py` |
| Excel → Word Table | `excel_to_word_table.py` |

### TIF Viewerについて

`interactive_viewer.py` は、TIF画像を簡易的に確認するための2D Viewerとして扱う。

Fit2Dとの完全一致が保証されない積分処理は、正式機能として再導入しない。

---

## 3. 推奨ソース構成

```text
XRD_Tools_macOS/
├── launcher.py
├── version.py
├── requirements.txt
├── setup.command
├── build.command
├── make_release_zip.command
├── XRD.icns                  # 任意
└── tools/
    ├── peak_picker_chi.py
    ├── peak_picker_dat.py
    ├── peak_Colob.py
    ├── peak_Colr.py
    ├── Colr_lattice_editor.py
    ├── interactive_viewer.py
    └── excel_to_word_table.py
```

---

## 4. version.py

バージョン番号および作者名は `version.py` で管理する。

例：

```python
VERSION = "x.y"
AUTHOR = "Yuto Maruyama"
```

新しいリリースを作成する場合は、最初に `VERSION` を更新する。

この値はランチャー表示、`Info.plist`、配布ZIP名などに使用する。

---

## 5. requirements.txt

XRD Tools専用環境へ導入するPythonライブラリを管理する。

基本ライブラリ：

```text
numpy
pandas
matplotlib
scipy
pyperclip
Pillow
openpyxl
```

Python側では以下も必要。

```text
tkinter
venv
```

`tkinter` と `venv` は通常pipではなく、ベースPython側で使用可能である必要がある。

### ライブラリを追加する場合

`requirements.txt` を更新するとともに、`setup.command` 内の専用環境正常性確認処理にも必要に応じてimportチェックを追加する。

---

## 6. `.app` の構造

ビルド後の概略構造：

```text
XRD Tools.app/
└── Contents/
    ├── Info.plist
    ├── MacOS/
    │   └── XRD Tools
    └── Resources/
        ├── launcher.py
        ├── version.py
        ├── setup.command
        ├── requirements.txt
        ├── XRD.icns
        └── tools/
```

アプリ内部には、専用環境を作成するためのファイルと各解析ツールを収録する。

---

## 7. 初回起動の流れ

`XRD Tools.app` 起動時に以下を確認する。

1. `~/.xrd_tools_venv/bin/python3` が存在するか
2. 専用環境のCPUアーキテクチャが現在のMacと一致するか
3. `requirements.txt` のハッシュが前回セットアップ時と一致するか

専用環境が存在しない、破損している、requirementsが変更されている場合は、アプリ内の `setup.command` を自動実行する。

利用者が手動でvenvを作成する必要はない。

---

## 8. Apple Silicon / Intel Mac

macOS版は以下の両方に対応する。

```text
Apple Silicon → arm64
Intel Mac     → x86_64
```

アーキテクチャ判定：

```bash
/usr/sbin/sysctl -n hw.optional.arm64
```

解析ツールは、専用環境を作成したアーキテクチャと同じ条件で実行する。

```bash
/usr/bin/arch -arm64
```

または

```bash
/usr/bin/arch -x86_64
```

これにより、Python本体とNumPy/SciPy等のバイナリ拡張のアーキテクチャ混在を防ぐ。

`Info.plist` の `LSArchitecturePriority` には両方を指定する。

特定の最低macOSバージョンは原則として固定しない。

---

## 9. ベースPythonの探索

`setup.command` は使用可能なPython 3を自動探索する。

主な探索先：

```text
/Library/Frameworks/Python.framework/Versions/
/opt/homebrew/bin/
/usr/local/bin/
/opt/local/bin/
```

および

```bash
command -v python3
```

の結果。

使用するPythonは以下を満たす必要がある。

- Python 3
- 現在のMacのCPUアーキテクチャで実行できる
- `venv` が使用できる
- `tkinter` が使用できる

Pythonのマイナーバージョンは固定しない。

---

## 10. 専用Python環境

専用環境：

```text
~/.xrd_tools_venv
```

専用Python：

```text
~/.xrd_tools_venv/bin/python3
```

ランチャーおよび各解析ツールは、必ずこのPythonから実行する。

macOSのFramework Pythonでは、Tkinter起動後の `sys.executable` がvenv外のPython.appを指す場合があるため、ツール起動用Pythonとして `sys.executable` を無条件に使用しない。

---

## 11. 専用環境の管理ファイル

専用環境内には、必要に応じて以下を保存する。

```text
~/.xrd_tools_venv/.xrd_tools_arch
~/.xrd_tools_venv/.xrd_tools_requirements.sha256
~/.xrd_tools_venv/.xrd_tools_environment
```

### `.xrd_tools_arch`

専用環境のCPUアーキテクチャ。

```text
arm64
```

または

```text
x86_64
```

### `.xrd_tools_requirements.sha256`

`requirements.txt` のSHA-256。

requirementsが変更された場合、次回起動時に再セットアップを案内するために使用する。

---

## 12. 専用環境の修復

既存の専用環境が存在する場合は、まずライブラリおよびTkinterが正常に使用できるか確認する。

異常がある場合は、

1. 必要ライブラリを再インストール
2. 専用環境を再確認
3. それでも失敗する場合は既存環境をバックアップ
4. 新しい専用環境を作成

という順で処理する。

既存環境を直接削除するより、バックアップ後に再作成する方が安全。

---

## 13. ログ

主なログ：

```text
~/Library/Logs/XRD Tools.log
~/Library/Logs/XRD Tools Setup.log
~/Library/Logs/XRD Tools Tools.log
```

### XRD Tools.log

アプリ本体の起動情報。

### XRD Tools Setup.log

専用環境の作成・更新・修復時のログ。

### XRD Tools Tools.log

各解析ツールのstdout/stderr。

解析ツールが異常終了した場合は、まずこのログを確認する。

Matplotlib設定：

```text
~/Library/Application Support/XRD Tools/matplotlib
```

---

## 14. ランチャーの表示設定

MacごとのTk表示差を抑えるため、ランチャーは

```python
root.tk.call("tk", "scaling", 1.0)
```

に固定する。

カードタイトルについては、MacごとのTk/Helveticaフォントメトリクス差を抑えるため、起動時にフォントサイズを実測して補正する。

基準：

```text
Font                     Helvetica Bold
Reference text           Peak Picker (.chi)
Reference width          174 px
Reference linespace      24 px
Reference nominal size   -21 px
```

`launcher.py` を更新する場合、この補正処理を誤って削除しないこと。

---

## 15. Peak Pickerの起動

Peak Picker (.chi) / (.dat) はランチャー側で以下の順にファイル選択を行う。

1. sampleファイルを複数選択
2. referenceファイルを1つ選択

その後、概ね以下の形式でPeak Pickerスクリプトへ引数を渡す。

```text
--ref <reference> <sample1> <sample2> ...
```

この処理を変更する場合は、Peak Picker側のコマンドライン引数処理と整合させる。

---

## 16. build.command

`build.command` は軽量 `.app` を作成するための開発者用ビルドスクリプト。

主な処理：

1. 必須ファイルを確認
2. `version.py` からVersionを取得
3. 既存の `dist` を削除
4. `.app` のディレクトリ構造を作成
5. launcher / setup / requirements / toolsをコピー
6. `Info.plist` を生成
7. `XRD.icns` が存在すればアイコンを設定
8. `plutil` でInfo.plistを検証
9. 可能であればad-hoc codesign
10. 配布ZIPを作成

現在の構成では以下を使用しない。

```text
setup.py
py2app
pyi_runtime_hook.py
```

---

## 17. ビルド方法

必要に応じて実行権限を付ける。

```bash
chmod +x build.command
chmod +x setup.command
chmod +x make_release_zip.command
```

ビルド：

```bash
/bin/bash build.command
```

またはFinderから `build.command` をダブルクリックする。

---

## 18. ビルド出力

例：

```text
dist/XRD Tools.app
XRD_Tools_v<version>.zip
```

配布ZIPには

```text
XRD Tools.app
```

のみを含める。

利用者へ以下を個別配布する必要はない。

```text
setup.command
requirements.txt
launcher.py
tools/
```

---

## 19. アイコン

プロジェクトルートに

```text
XRD.icns
```

が存在する場合は、ビルド時にアプリアイコンとして使用する。

存在しない場合でもビルドは可能。

---

## 20. コード署名

現在の軽量ビルドでは、利用可能な場合にad-hoc署名を行うことがある。

例：

```bash
codesign --force --deep --sign -
```

これは正式なDeveloper ID署名やnotarizationではない。

広範囲に外部配布する場合は、Developer ID署名およびApple notarizationを別途検討する。

---

## 21. ツールを更新する場合

既存ツールを修正した場合：

```text
tools/<対象ファイル>.py
```

を更新し、`build.command` を再実行する。

原則として既存ツールを直接上書きしながら開発するより、新しい機能は独立した新規ファイルとして追加し、動作確認後にランチャーへ登録する。

---

## 22. 新しいツールを追加する場合

最低限以下を変更する。

1. 新しい `.py` ファイルを `tools/` に追加
2. `launcher.py` に起動処理を追加
3. ランチャー画面にカードまたはボタンを追加
4. 必要なら `requirements.txt` を更新
5. 必要なら `setup.command` のimportチェックを更新

---

## 23. requirements変更時

依存ライブラリを追加・変更する場合：

1. `requirements.txt` を更新
2. `setup.command` のimportチェックを更新
3. Versionを更新
4. 再ビルド
5. 既存専用環境があるMacで更新動作を確認
6. 新規環境で初回セットアップを確認

requirementsのハッシュが変わるため、既存ユーザーにも次回起動時に更新セットアップが案内される。

---

## 24. Version更新時

`version.py` の

```python
VERSION = "x.y"
```

を変更して再ビルドする。

配布ZIP名はVersionに合わせて自動生成する。

---

## 25. 配布前チェック

- [ ] Versionが正しい
- [ ] 最新の解析ツールがすべて入っている
- [ ] `requirements.txt` が最新
- [ ] 初回セットアップが動作する
- [ ] 既存venvを再利用できる
- [ ] requirements変更時に更新セットアップが動作する
- [ ] Peak Picker (.chi) が起動する
- [ ] Peak Picker (.dat) が起動する
- [ ] Col Oblique Indexingが起動する
- [ ] Col Rectangular Indexingが起動する
- [ ] Colr Lattice Editorが起動する
- [ ] TIF Viewerが起動する
- [ ] Excel → Word Tableが起動する
- [ ] ファイル選択ダイアログが正常
- [ ] ランチャー表示が崩れていない
- [ ] ログが正常に出力される
- [ ] Apple Siliconで動作する
- [ ] 可能であればIntel Macでも確認する
- [ ] `XRD.icns` が正しく反映される
- [ ] 配布ZIPに `XRD Tools.app` 以外が含まれていない

---

## 26. 開発時に維持する重要仕様

以下は現行設計の重要部分。

```text
専用Python環境
requirements hash判定
.xrd_tools_arch
/usr/bin/archによるCPUアーキテクチャ統一
ログ出力
Mac間フォント補正
アプリ内setup.command
```

単純化のためにこれらを削除すると、PCごとのPython環境差やCPUアーキテクチャ差が再発する可能性がある。

---

## 27. 最終配布物

利用者へ配布するもの：

```text
XRD_Tools_v<version>.zip
```

ZIP内：

```text
XRD Tools.app
```

ソースコード、ビルドスクリプト、requirements、setupファイルは開発者側で管理する。

---

以上
