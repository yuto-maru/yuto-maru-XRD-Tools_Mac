from pathlib import Path
from setuptools import setup
from version import VERSION

APP = ["launcher.py"]

tool_files = []
tools_dir = Path("tools")
if tools_dir.exists():
    tool_files = [str(p) for p in tools_dir.iterdir() if p.is_file()]

DATA_FILES = []
if tool_files:
    # XRD Tools.app/Contents/Resources/tools に入る
    DATA_FILES.append(("tools", tool_files))

if Path("version.py").exists():
    DATA_FILES.append(("", ["version.py"]))

OPTIONS = {
    "argv_emulation": False,
    "packages": [],
    "plist": {
        "CFBundleName": "XRD Tools",
        "CFBundleDisplayName": "XRD Tools",
        "CFBundleIdentifier": "jp.local.xrdtools",
        "CFBundleVersion": VERSION,
        "CFBundleShortVersionString": VERSION,
    },
}

# XRD.icns が同じフォルダにあればFinder/Dockアイコンとして使う
if Path("XRD.icns").exists():
    OPTIONS["iconfile"] = "XRD.icns"

setup(
    app=APP,
    name="XRD Tools",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
