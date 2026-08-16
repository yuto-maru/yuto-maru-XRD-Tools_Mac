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


## 2. 引き継ぎ時の作業手順

この節では、XRD Toolsの開発を引き継ぐ際の基本的な作業手順を示す。

まず、既存版をそのまま起動・ビルド・テストできる状態を再現し、その後に変更作業へ進む。

### Step 1. 開発用フォルダを複製する

配布中または動作確認済みの開発フォルダを、そのままバックアップする。

例：

```text
XRD_Tools_macOS_stable/
XRD_Tools_macOS_development/
```

新しい修正は `development` 側で行い、動作確認済みの `stable` 側は変更しない。

特に、既存ツールへ新機能を追加する場合も、可能であれば元ファイルを残し、新しいファイルとして試作する。

---

### Step 2. フォルダ構成を確認する

最低限、以下が存在することを確認する。

```text
launcher.py
version.py
requirements.txt
setup.command
build.command
make_release_zip.command
tools/
```

`tools/` 内には、ランチャーから呼び出す解析ツールが入っている。

最初にファイル名と役割を対応付けておく。

```text
peak_picker_chi.py → Peak Picker (.chi)
peak_picker_dat.py → Peak Picker (.dat)
peak_Colob.py → Col Oblique Indexing
peak_Colr.py → Col Rectangular Indexing
Colr_lattice_editor.py → Colr Lattice Editor
interactive_viewer.py → TIF Viewer
excel_to_word_table.py → Excel → Word Table
```

---

### Step 3. まず既存版をビルドする

コードを変更する前に、現在のソースから正常に `.app` を作成できることを確認する。

```bash
/bin/bash build.command
```

正常なら、以下が生成される。

```text
dist/XRD Tools.app
XRD_Tools_v<version>.zip
```

この段階でビルドできない場合は、新機能開発を始めず、まずビルド環境を復旧する。

---

### Step 4. ビルドしたアプリを起動する

`dist/XRD Tools.app` を起動し、ランチャーが表示されることを確認する。

最低限、以下を確認する。

1. XRD Toolsランチャーが開く
2. 7つのツールカードが表示される
3. 各カードをクリックできる
4. Peak Pickerではsample/reference選択画面が開く
5. 各解析ツールが起動する
6. ツール終了後もランチャーが使用できる

---

### Step 5. 専用Python環境の考え方を理解する

XRD Toolsは、開発フォルダ内のPythonではなく、利用者ごとに作成される

```text
~/.xrd_tools_venv
```

を実行環境として使用する。

重要なのは、

```text
XRD Tools.app
 ↓
setup.command
 ↓
~/.xrd_tools_venv
 ↓
launcher.py
 ↓
各tools/*.py
```

という流れである。

解析ツールを修正するときに、システムPythonへ直接 `pip install` する必要はない。

---

### Step 6. 変更するファイルを限定する

目的に応じて、変更するファイルを限定する。

#### 解析処理を変更する場合

```text
tools/<対象ツール>.py
```

を変更する。

#### ランチャーの表示やボタンを変更する場合

```text
launcher.py
```

を変更する。

#### 必要ライブラリを追加する場合

```text
requirements.txt
setup.command
```

を確認する。

#### Versionを更新する場合

```text
version.py
```

のみを変更する。

#### ビルド方法を変更する場合

```text
build.command
make_release_zip.command
```

を変更する。

ビルドスクリプトはアプリ全体へ影響するため、解析ツールの修正より慎重に扱う。

---

### Step 7. 小さな変更ごとに単体確認する

複数の変更をまとめて行わない。

推奨：

```text
1機能修正
↓
直接Pythonで確認
↓
launcher経由で確認
↓
build
↓
.appで確認
```

問題が起きたときに、どの変更が原因か分かるようにする。

---

### Step 8. ツール単体を確認する

解析ツールの修正時は、可能であればツール単体でも起動確認する。

ただし、正式な動作確認では必ずXRD Tools専用環境を使用する。

例：

```bash
"$HOME/.xrd_tools_venv/bin/python3" tools/対象ツール.py
```

Peak Pickerなど、ランチャーから引数を受け取るツールは、最終的にはランチャー経由で確認する。

---

### Step 9. launcher経由で確認する

単体で動いても、ランチャーから起動できるとは限らない。

必ず

```text
XRD Tools.app
→ 対象カード
→ 対象ツール
```

の経路でも確認する。

特に確認するもの：

- ファイル選択
- 作業ディレクトリ
- コマンドライン引数
- ログ出力
- tkinterウィンドウ表示
- Matplotlib表示
- クリップボード機能

---

### Step 10. エラーが出たらログを見る

「動かない」ときにコードをすぐ書き換えず、まずログを確認する。

```text
~/Library/Logs/XRD Tools.log
~/Library/Logs/XRD Tools Setup.log
~/Library/Logs/XRD Tools Tools.log
```

解析ツールのエラーは、まず

```text
XRD Tools Tools.log
```

を確認する。

---

### Step 11. requirementsを変更した場合

新しいPythonライブラリを使う場合は、

```text
requirements.txt
```

へ追加する。

さらに、`setup.command` のruntime確認でも、そのライブラリをimportできるか確認する。

その後、

1. 既存venvがある状態
2. 新規venvの状態

の両方でテストする。

---

### Step 12. 新しいツールを追加する場合

既存ツールを無理に上書きせず、新しい `.py` ファイルとして追加する。

手順：

```text
1. tools/ に新規.pyを追加
2. 専用venvで単体起動確認
3. launcher.py にカードまたは起動処理を追加
4. launcher経由で起動確認
5. build.commandで.app作成
6. .appから最終確認
```

---

### Step 13. TIF Viewerの方針を守る

TIF Viewerは現在、簡易2D Viewerとして扱う。

Fit2Dの完全互換が確認されていない積分機能を、検証なしで正式機能へ追加しない。

論文に使用する定量処理は、再現性・一致性を検証してから採用する。

---

### Step 14. 配布前に必ずクリーンビルドする

開発途中の `.app` をそのまま配布しない。

```bash
/bin/bash build.command
```

で新しく生成したものを使用する。

配布対象：

```text
XRD_Tools_v<version>.zip
```

ZIP内は原則として

```text
XRD Tools.app
```

のみとする。

---

### Step 15. 変更内容を記録する

引き継ぎや履歴確認のため、変更時には最低限以下を記録する。

```text
・変更日
・変更したファイル
・変更内容
・変更理由
・動作確認した環境
・既知の問題
```

可能であればGit等のバージョン管理を使用する。

---

### Step 16. 問題が起きた場合の切り分け順

問題が発生した場合は、以下の順で確認すると原因を絞りやすい。

```text
1. 元のstable版は動くか
2. 変更した.py単体は動くか
3. 専用venvで動くか
4. launcherから動くか
5. build後の.appで動くか
6. 別Macでも動くか
```

この順で確認すると、

```text
解析コードの問題
ランチャーの問題
Python環境の問題
ビルドの問題
Mac固有の問題
```

を切り分けやすい。

---

## 3. 解析ツール


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

## 4. 推奨ソース構成

```text
XRD_Tools_macOS/
├── launcher.py
├── version.py
├── requirements.txt
├── setup.command
├── build.command
├── make_release_zip.command
├── XRD.icns # 任意
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

## 5. version.py

バージョン番号および作者名は `version.py` で管理する。

例：

```python
VERSION = "x.y"
AUTHOR = "Yuto Maruyama"
```

新しいリリースを作成する場合は、最初に `VERSION` を更新する。

この値はランチャー表示、`Info.plist`、配布ZIP名などに使用する。

---

## 6. requirements.txt

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

## 7. `.app` の構造

ビルド後の概略構造：

```text
XRD Tools.app/
└── Contents/
 ├── Info.plist
 ├── MacOS/
 │ └── XRD Tools
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

## 8. 初回起動の流れ

`XRD Tools.app` 起動時に以下を確認する。

1. `~/.xrd_tools_venv/bin/python3` が存在するか
2. 専用環境のCPUアーキテクチャが現在のMacと一致するか
3. `requirements.txt` のハッシュが前回セットアップ時と一致するか

専用環境が存在しない、破損している、requirementsが変更されている場合は、アプリ内の `setup.command` を自動実行する。

利用者が手動でvenvを作成する必要はない。

---

## 9. Apple Silicon / Intel Mac

macOS版は以下の両方に対応する。

```text
Apple Silicon → arm64
Intel Mac → x86_64
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

## 10. ベースPythonの探索

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

## 11. 専用Python環境

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

## 12. 専用環境の管理ファイル

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

## 13. 専用環境の修復

既存の専用環境が存在する場合は、まずライブラリおよびTkinterが正常に使用できるか確認する。

異常がある場合は、

1. 必要ライブラリを再インストール
2. 専用環境を再確認
3. それでも失敗する場合は既存環境をバックアップ
4. 新しい専用環境を作成

という順で処理する。

既存環境を直接削除するより、バックアップ後に再作成する方が安全。

---

## 14. ログ

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

## 15. ランチャーの表示設定

MacごとのTk表示差を抑えるため、ランチャーは

```python
root.tk.call("tk", "scaling", 1.0)
```

に固定する。

カードタイトルについては、MacごとのTk/Helveticaフォントメトリクス差を抑えるため、起動時にフォントサイズを実測して補正する。

基準：

```text
Font Helvetica Bold
Reference text Peak Picker (.chi)
Reference width 174 px
Reference linespace 24 px
Reference nominal size -21 px
```

`launcher.py` を更新する場合、この補正処理を誤って削除しないこと。

---

## 16. Peak Pickerの起動

Peak Picker (.chi) / (.dat) はランチャー側で以下の順にファイル選択を行う。

1. sampleファイルを複数選択
2. referenceファイルを1つ選択

その後、概ね以下の形式でPeak Pickerスクリプトへ引数を渡す。

```text
--ref <reference> <sample1> <sample2> ...
```

この処理を変更する場合は、Peak Picker側のコマンドライン引数処理と整合させる。

---

## 17. build.command

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

## 18. ビルド方法

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

## 19. ビルド出力

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

## 20. アイコン

プロジェクトルートに

```text
XRD.icns
```

が存在する場合は、ビルド時にアプリアイコンとして使用する。

存在しない場合でもビルドは可能。

---

## 21. コード署名

現在の軽量ビルドでは、利用可能な場合にad-hoc署名を行うことがある。

例：

```bash
codesign --force --deep --sign -
```

これは正式なDeveloper ID署名やnotarizationではない。

広範囲に外部配布する場合は、Developer ID署名およびApple notarizationを別途検討する。

---

## 22. ツールを更新する場合

既存ツールを修正した場合：

```text
tools/<対象ファイル>.py
```

を更新し、`build.command` を再実行する。

原則として既存ツールを直接上書きしながら開発するより、新しい機能は独立した新規ファイルとして追加し、動作確認後にランチャーへ登録する。

---

## 23. 新しいツールを追加する場合

最低限以下を変更する。

1. 新しい `.py` ファイルを `tools/` に追加
2. `launcher.py` に起動処理を追加
3. ランチャー画面にカードまたはボタンを追加
4. 必要なら `requirements.txt` を更新
5. 必要なら `setup.command` のimportチェックを更新

---

## 24. requirements変更時

依存ライブラリを追加・変更する場合：

1. `requirements.txt` を更新
2. `setup.command` のimportチェックを更新
3. Versionを更新
4. 再ビルド
5. 既存専用環境があるMacで更新動作を確認
6. 新規環境で初回セットアップを確認

requirementsのハッシュが変わるため、既存ユーザーにも次回起動時に更新セットアップが案内される。

---

## 25. Version更新時

`version.py` の

```python
VERSION = "x.y"
```

を変更して再ビルドする。

配布ZIP名はVersionに合わせて自動生成する。

---

## 26. 配布前チェック

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

## 27. 開発時に維持する重要仕様

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

## 28. 最終配布物

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
