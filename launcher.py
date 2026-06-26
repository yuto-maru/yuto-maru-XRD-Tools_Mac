import json
import os
import sys
import shlex
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from version import VERSION, AUTHOR

def get_resource_dir():
    """
    通常のpython実行時:
        XRD_Tools_App/
            launcher.py
            tools/

    py2app実行時:
        XRD Tools.app/
            Contents/
                Resources/
                    tools/

    の両方に対応する。
    """
    if getattr(sys, "frozen", False):
        resource_path = os.environ.get("RESOURCEPATH")
        if resource_path:
            return Path(resource_path)
        return Path(sys.executable).resolve().parents[1] / "Resources"

    return Path(__file__).resolve().parent


BASE_DIR = get_resource_dir()
TOOLS_DIR = BASE_DIR / "tools"
SETTINGS_FILE = Path.home() / ".xrd_tools_launcher_settings.json"

PYTHON_CMD = ["/usr/bin/arch", "-arm64", "/usr/bin/env", "python3"]

APP_W = 760
APP_H = 760

BG_COLOR = "#D6E1FF"
CARD_COLOR = "#F9FBFF"
CARD_HOVER = "#EEF3FF"
CARD_PRESS = "#DCE8FF"
CARD_OUTLINE = "#C8D3F2"

NAVY = "#08245C"
BLUE = "#0646D9"
GREEN = "#137333"
PURPLE = "#4B1BA7"
RECT_BLUE = "#0B43A6"
TEXT = "#111111"

def load_settings():
    try:
        if SETTINGS_FILE.exists():
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_settings(settings):
    try:
        SETTINGS_FILE.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


settings = load_settings()


def remember_dir(key, path):
    try:
        p = Path(path)
        if p.is_file():
            p = p.parent
        settings[key] = str(p)
        save_settings(settings)
    except Exception:
        pass


def initial_dir(key):
    p = settings.get(key)
    if p and Path(p).exists():
        return p
    return str(Path.home())


def apple_escape(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def run_in_terminal(command):
    applescript = f"""
tell application "Terminal"
    activate
    do script "{apple_escape(command)}"
end tell
"""
    subprocess.Popen(["osascript", "-e", applescript])


def run_python_script(script_path, args=None, cwd=None):
    if args is None:
        args = []
    if cwd is None:
        cwd = BASE_DIR

    cmd_parts = [shlex.quote(x) for x in PYTHON_CMD]
    cmd_parts.append(shlex.quote(str(script_path)))
    cmd_parts.extend(shlex.quote(str(a)) for a in args)

    command = f"cd {shlex.quote(str(cwd))} && " + " ".join(cmd_parts)
    run_in_terminal(command)


def check_script(script_name):
    script_path = TOOLS_DIR / script_name
    if not script_path.exists():
        messagebox.showerror("Error", f"見つかりません:\n{script_path}")
        return None
    return script_path


def run_peak_picker(label, script_name, ext):
    script_path = check_script(script_name)
    if script_path is None:
        return

    sample_files = filedialog.askopenfilenames(
        title=f"{label}: sampleファイルを選択（複数選択可）",
        initialdir=initial_dir(f"sample_{ext}"),
        filetypes=[(f"{ext.upper()} files", f"*.{ext}"), ("All files", "*.*")],
    )
    if not sample_files:
        return

    remember_dir(f"sample_{ext}", sample_files[0])

    ref_file = filedialog.askopenfilename(
        title=f"{label}: referenceファイルを1つ選択",
        initialdir=initial_dir(f"ref_{ext}"),
        filetypes=[(f"{ext.upper()} files", f"*.{ext}"), ("All files", "*.*")],
    )
    if not ref_file:
        return

    remember_dir(f"ref_{ext}", ref_file)

    cwd = str(Path(sample_files[0]).parent)
    args = ["--ref", ref_file] + list(sample_files)
    run_python_script(script_path, args=args, cwd=cwd)


def run_normal_tool(label, script_name):
    script_path = check_script(script_name)
    if script_path is None:
        return

    # .app配布時はtoolsがアプリ内部に入るため、
    # 作業ディレクトリは書き込み可能なホームにしておく。
    run_python_script(script_path, cwd=Path.home())


def rounded_rect(canvas, x1, y1, x2, y2, r=18, **kwargs):
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def draw_chevron(x, y, color=NAVY):
    canvas.create_line(x - 7, y - 12, x + 7, y, fill=color, width=4, capstyle="round")
    canvas.create_line(x + 7, y, x - 7, y + 12, fill=color, width=4, capstyle="round")


def draw_peak_icon(x, y, color, beamline):
    # 控えめなピーク抽出アイコン
    ox, oy = x + 72, y + 60

    canvas.create_line(ox, oy, ox, oy - 34, fill="black", width=2, arrow=tk.LAST)
    canvas.create_line(ox, oy, ox + 96, oy, fill="black", width=2, arrow=tk.LAST)

    canvas.create_text(ox - 7, oy - 38, text="I", font=("Helvetica", 10, "italic"), fill="black")
    canvas.create_text(ox + 103, oy + 1, text="q", font=("Helvetica", 10, "italic"), fill="black")

    canvas.create_text(ox + 22, oy - 38, text=beamline, anchor="w",
                       font=("Helvetica", 12, "bold"), fill=color)

    gray = [
        ox + 7, oy - 5, ox + 20, oy - 4, ox + 32, oy - 7,
        ox + 46, oy - 5, ox + 62, oy - 5,
        ox + 80, oy - 5, ox + 94, oy - 5
    ]
    canvas.create_line(*gray, fill="#9AA0A6", width=1.8, smooth=True)

    pts = [
        ox + 7, oy - 5, ox + 19, oy - 5,
        ox + 30, oy - 10, ox + 38, oy - 27, ox + 47, oy - 6,
        ox + 58, oy - 6, ox + 68, oy - 33, ox + 78, oy - 6,
        ox + 86, oy - 6, ox + 93, oy - 23, ox + 99, oy - 6,
    ]
    canvas.create_line(*pts, fill=color, width=2, smooth=True)

    for px, py in [(38, -27), (68, -33), (93, -23)]:
        canvas.create_oval(
            ox + px - 3.5, oy + py - 3.5,
            ox + px + 3.5, oy + py + 3.5,
            outline="red",
            width=1.8,
            fill="white"
        )


def draw_oblique_icon(x, y):
    # コンパクトな単位格子アイコン。
    # a = 長軸（左斜辺）、b = 短軸（上辺・水平）、γ = 左上角。
    # γの弧は create_arc ではなく、左上角を中心にした曲線として直接描く。
    p4 = (x + 92, y + 22)    # top-left
    p3 = (x + 138, y + 22)   # top-right
    p1 = (x + 66, y + 66)    # bottom-left
    p2 = (x + 112, y + 66)   # bottom-right

    # unit cell
    for aa, bb in [(p4, p3), (p3, p2), (p2, p1), (p1, p4)]:
        canvas.create_line(*aa, *bb, fill=PURPLE, width=2.5)

    for px, py in [p1, p2, p3, p4]:
        canvas.create_oval(px - 3.4, py - 3.4, px + 3.4, py + 3.4, fill=PURPLE, outline=PURPLE)

    # a軸：左斜辺に平行。図形に近づける。
    ax1, ay1 = p4[0] - 13, p4[1] - 1
    ax2, ay2 = p1[0] - 13, p1[1] + 1
    canvas.create_line(ax1, ay1, ax2, ay2, fill=PURPLE, width=1.7, arrow=tk.BOTH)
    canvas.create_text(
        (ax1 + ax2) / 2 - 10,
        (ay1 + ay2) / 2,
        text="a",
        font=("Helvetica", 11, "italic", "bold"),
        fill=PURPLE
    )

    # b軸：上辺に平行。図形に近づける。
    bx1, bx2 = p4[0] + 3, p3[0] - 3
    by = p4[1] - 8
    canvas.create_line(bx1, by, bx2, by, fill=PURPLE, width=1.7, arrow=tk.BOTH)
    canvas.create_text(
        (bx1 + bx2) / 2,
        by - 10,
        text="b",
        font=("Helvetica", 11, "italic", "bold"),
        fill=PURPLE
    )

    # γ：平行四辺形の左上角そのものに合わせる。
    # 上辺方向(p4→p3)と左斜辺方向(p4→p1)の間に、内角の弧を直接描く。
    import math
    r = 12
    theta1 = math.radians(10)     # 上辺方向に近い角度
    theta2 = math.atan2(p1[1] - p4[1], p1[0] - p4[0]) - math.radians(10)

    pts = []
    steps = 16
    for i in range(steps + 1):
        t = theta1 + (theta2 - theta1) * i / steps
        pts.extend([p4[0] + r * math.cos(t), p4[1] + r * math.sin(t)])

    canvas.create_line(*pts, fill=PURPLE, width=1.7, smooth=True)

    canvas.create_text(
        p4[0] + 13,
        p4[1] + 13,
        text="γ",
        font=("Helvetica", 10, "italic", "bold"),
        fill=PURPLE
    )


def draw_rect_icon(x, y):
    # コンパクトな単位格子アイコン。
    # a = 長軸（左辺・縦）、b = 短軸（上辺・水平）。
    # 左右余白を抑え、カードからはみ出さない座標に再設計。
    left = x + 78
    top = y + 17
    right = x + 118
    bottom = y + 68

    canvas.create_rectangle(left, top, right, bottom, outline=RECT_BLUE, width=2.5)

    for px, py in [(left, top), (right, top), (left, bottom), (right, bottom)]:
        canvas.create_oval(px - 3.4, py - 3.4, px + 3.4, py + 3.4, fill=RECT_BLUE, outline=RECT_BLUE)

    # a軸：左辺に平行。図形に近づける。
    ax = left - 12
    canvas.create_line(ax, top, ax, bottom, fill=RECT_BLUE, width=1.7, arrow=tk.BOTH)
    canvas.create_text(
        ax - 11,
        (top + bottom) / 2,
        text="a",
        font=("Helvetica", 11, "italic", "bold"),
        fill=RECT_BLUE
    )

    # b軸：上辺に平行。図形に近づける。
    by = top - 8
    canvas.create_line(left + 3, by, right - 3, by, fill=RECT_BLUE, width=1.7, arrow=tk.BOTH)
    canvas.create_text(
        (left + right) / 2,
        by - 10,
        text="b",
        font=("Helvetica", 11, "italic", "bold"),
        fill=RECT_BLUE
    )

    # 左上の直角マークのみ
    s = 7
    canvas.create_line(left, top + s, left + s, top + s, fill=RECT_BLUE, width=1.7)
    canvas.create_line(left + s, top + s, left + s, top, fill=RECT_BLUE, width=1.7)


def draw_tif_icon(x, y):
    cx, cy = x + 126, y + 40

    for r, shade in [
        (23, "#CFCFCF"),
        (18, "#BEBEBE"),
        (13, "#D8D8D8"),
        (8, "#B5B5B5"),
        (4, "#D4D4D4"),
    ]:
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=shade, width=3)

    canvas.create_oval(cx - 3.5, cy - 3.5, cx + 3.5, cy + 3.5, fill="black")

    canvas.create_line(cx - 42, cy, cx + 60, cy, fill="black", width=1.8, dash=(5, 4))
    canvas.create_line(cx, cy - 34, cx, cy + 34, fill="black", width=1, dash=(5, 4))
    canvas.create_line(cx, cy, cx + 68, cy, fill="black", width=1.8, arrow=tk.LAST)
    canvas.create_text(cx + 78, cy, text="q", font=("Helvetica", 10, "italic"), fill="black")


def draw_excel_word_icon(x, y):
    ex, ey = x + 80, y + 26
    canvas.create_rectangle(ex + 12, ey, ex + 42, ey + 34, outline=GREEN, width=1.8, fill="white")
    for i in range(1, 3):
        canvas.create_line(ex + 12, ey + i * 11, ex + 42, ey + i * 11, fill="#A8CFA8", width=1)
        canvas.create_line(ex + 12 + i * 10, ey, ex + 12 + i * 10, ey + 34, fill="#A8CFA8", width=1)
    canvas.create_rectangle(ex, ey + 8, ex + 25, ey + 26, fill=GREEN, outline=GREEN)
    canvas.create_text(ex + 12.5, ey + 19, text="X", font=("Helvetica", 13, "bold"), fill="white")

    canvas.create_line(x + 128, y + 47, x + 156, y + 47, fill=BLUE, width=3, arrow=tk.LAST)

    wx, wy = x + 166, y + 26
    canvas.create_rectangle(wx + 12, wy, wx + 42, wy + 34, outline=BLUE, width=1.8, fill="white")
    for i in range(1, 3):
        canvas.create_line(wx + 18, wy + i * 11, wx + 38, wy + i * 11, fill="#9CB9F2", width=1)
    canvas.create_rectangle(wx, wy + 8, wx + 25, wy + 26, fill=BLUE, outline=BLUE)
    canvas.create_text(wx + 12.5, wy + 19, text="W", font=("Helvetica", 13, "bold"), fill="white")


root = tk.Tk()
root.title("XRD Tools")
root.geometry(f"{APP_W}x{APP_H}")
root.resizable(False, False)

canvas = tk.Canvas(root, width=APP_W, height=APP_H, bg=BG_COLOR, highlightthickness=0)
canvas.pack(fill="both", expand=True)

canvas.create_text(APP_W // 2, 52, text="XRD Tools",
                   font=("Avenir Next", 32, "bold"), fill=NAVY)


def make_card(y, title, icon_func, command, icon_dx=0):
    # カード横幅をさらに短くし、左側アイコン領域の余白を減らす
    x1, x2 = 92, APP_W - 92
    y1, y2 = y, y + 82

    rounded_rect(canvas, x1 + 2, y1 + 3, x2 + 2, y2 + 3, r=18,
                 fill="#BFC9E6", outline="")
    rect = rounded_rect(canvas, x1, y1, x2, y2, r=18,
                        fill=CARD_COLOR, outline=CARD_OUTLINE, width=1)

    # アイコンごとに横位置を微調整する
    icon_func(x1 - 22 + icon_dx, y1 + 8)

    text_id = canvas.create_text(
        292, y1 + 42,
        text=title,
        anchor="w",
        font=("Helvetica", 21, "bold"),
        fill=TEXT,
    )

    draw_chevron(x2 - 32, y1 + 42)

    hitbox = rounded_rect(canvas, x1, y1, x2, y2, r=18, fill="", outline="")

    def set_color(color):
        canvas.itemconfig(rect, fill=color)

    def on_enter(event):
        set_color(CARD_HOVER)
        canvas.config(cursor="hand2")

    def on_leave(event):
        set_color(CARD_COLOR)
        canvas.config(cursor="")

    def on_press(event):
        set_color(CARD_PRESS)

    def on_release(event):
        set_color(CARD_HOVER)
        command()

    for item in (rect, text_id, hitbox):
        canvas.tag_bind(item, "<Enter>", on_enter)
        canvas.tag_bind(item, "<Leave>", on_leave)
        canvas.tag_bind(item, "<ButtonPress-1>", on_press)
        canvas.tag_bind(item, "<ButtonRelease-1>", on_release)



make_card(104, "Peak Picker (.chi)",
          lambda x, y: draw_peak_icon(x, y, BLUE, "BL40B2"),
          lambda: run_peak_picker("Peak Picker (.chi)", "peak_picker_chi.py", "chi"),
          icon_dx=0)

make_card(194, "Peak Picker (.dat)",
          lambda x, y: draw_peak_icon(x, y, GREEN, "BL19B2"),
          lambda: run_peak_picker("Peak Picker (.dat)", "peak_picker_dat.py", "dat"),
          icon_dx=0)

make_card(284, "Col Oblique Indexing",
          draw_oblique_icon,
          lambda: run_normal_tool("Col Oblique Indexing", "peak_Colob.py"),
          icon_dx=18)

make_card(374, "Col Rectangular Indexing",
          draw_rect_icon,
          lambda: run_normal_tool("Col Rectangular Indexing", "peak_Colr.py"),
          icon_dx=18)

make_card(464, "TIF Viewer",
          draw_tif_icon,
          lambda: run_normal_tool("TIF Viewer", "interactive_viewer.py"),
          icon_dx=-20)

make_card(554, "Excel → Word Table",
          draw_excel_word_icon,
          lambda: run_normal_tool("Excel → Word Table", "excel_to_word_table.py"),
          icon_dx=-22)

canvas.create_text(APP_W // 2, 662, text=f"Version {VERSION}", font=("Helvetica", 12), fill=NAVY)
canvas.create_text(APP_W // 2, 686, text=AUTHOR, font=("Helvetica", 12), fill=NAVY)

root.mainloop()
