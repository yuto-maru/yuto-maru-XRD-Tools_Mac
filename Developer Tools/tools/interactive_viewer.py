#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Interactive TIFF Viewer

Tkinterの1つのウィンドウ内に、以下を統合したmacOS向けビューア。

- TIFFファイル選択
- 画像表示
- Low / High percentile調整
- Linear / Log切替
- 16-bit TIFF保存

Matplotlibのplt.show()は使用せず、FigureCanvasTkAggをTkinterへ直接埋め込む。
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
from PIL import Image
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


class InteractiveViewer:
    def __init__(self, root: tk.Tk, initial_path: str | None = None) -> None:
        self.root = root
        self.root.title("Interactive TIFF Viewer")
        self.root.minsize(900, 650)
        self._center_window(1200, 820)

        self.image_path: Path | None = None
        self.image_array: np.ndarray | None = None
        self.image_artist = None
        self.colorbar = None
        self._update_job: str | None = None

        self.low_var = tk.DoubleVar(value=1.0)
        self.high_var = tk.DoubleVar(value=99.0)
        self.scale_mode_var = tk.StringVar(value="linear")
        self.low_label_var = tk.StringVar(value="Low: 1.0 %")
        self.high_label_var = tk.StringVar(value="High: 99.0 %")
        self.file_var = tk.StringVar(value="ファイル未選択")
        self.status_var = tk.StringVar(value="TIFFファイルを選択してください。")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        if initial_path:
            self.root.after(100, lambda: self.load_image(initial_path))
        else:
            # ウィンドウを先に表示してからファイル選択を開く。
            self.root.after(150, self.choose_file)

    # =========================================================
    # UI
    # =========================================================

    def _center_window(self, width: int, height: int) -> None:
        self.root.update_idletasks()

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        width = min(width, max(850, screen_width - 80))
        height = min(height, max(600, screen_height - 100))

        x = max(20, (screen_width - width) // 2)
        y = max(20, (screen_height - height) // 2)

        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=8)
        main.pack(fill=tk.BOTH, expand=True)

        # 上部：ファイル操作
        top = ttk.Frame(main)
        top.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(
            top,
            text="TIFFを開く",
            command=self.choose_file,
        ).pack(side=tk.LEFT)

        ttk.Label(
            top,
            textvariable=self.file_var,
            anchor=tk.W,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 8))

        ttk.Button(
            top,
            text="保存",
            command=self.save_image,
        ).pack(side=tk.RIGHT)

        # 中央：画像
        plot_frame = ttk.Frame(main)
        plot_frame.pack(fill=tk.BOTH, expand=True)

        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("No image")
        self.ax.set_axis_off()
        self.figure.subplots_adjust(
            left=0.06,
            right=0.90,
            bottom=0.08,
            top=0.94,
        )

        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(
            self.canvas,
            plot_frame,
            pack_toolbar=False,
        )
        toolbar.update()
        toolbar.pack(fill=tk.X)

        # 下部：画像調整
        controls = ttk.LabelFrame(
            main,
            text="表示調整",
            padding=8,
        )
        controls.pack(fill=tk.X, pady=(8, 0))

        # Low
        low_row = ttk.Frame(controls)
        low_row.pack(fill=tk.X, pady=2)

        ttk.Label(
            low_row,
            textvariable=self.low_label_var,
            width=14,
        ).pack(side=tk.LEFT)

        low_scale = ttk.Scale(
            low_row,
            from_=0.0,
            to=50.0,
            variable=self.low_var,
            command=self._on_slider_change,
        )
        low_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # High
        high_row = ttk.Frame(controls)
        high_row.pack(fill=tk.X, pady=2)

        ttk.Label(
            high_row,
            textvariable=self.high_label_var,
            width=14,
        ).pack(side=tk.LEFT)

        high_scale = ttk.Scale(
            high_row,
            from_=50.0,
            to=100.0,
            variable=self.high_var,
            command=self._on_slider_change,
        )
        high_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Linear / Log
        mode_row = ttk.Frame(controls)
        mode_row.pack(fill=tk.X, pady=(7, 0))

        ttk.Label(mode_row, text="表示スケール").pack(side=tk.LEFT)

        ttk.Radiobutton(
            mode_row,
            text="Linear",
            variable=self.scale_mode_var,
            value="linear",
            command=self.update_display,
        ).pack(side=tk.LEFT, padx=(10, 4))

        ttk.Radiobutton(
            mode_row,
            text="Log",
            variable=self.scale_mode_var,
            value="log",
            command=self.update_display,
        ).pack(side=tk.LEFT, padx=4)

        ttk.Button(
            mode_row,
            text="初期値に戻す",
            command=self.reset_controls,
        ).pack(side=tk.RIGHT)

        # ステータスバー
        ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor=tk.W,
            relief=tk.SUNKEN,
            padding=(8, 4),
        ).pack(side=tk.BOTTOM, fill=tk.X)

        # ショートカット
        self.root.bind("<Command-o>", lambda _event: self.choose_file())
        self.root.bind("<Control-o>", lambda _event: self.choose_file())
        self.root.bind("<Command-s>", lambda _event: self.save_image())
        self.root.bind("<Control-s>", lambda _event: self.save_image())
        self.root.bind("<Escape>", lambda _event: self.close())

    # =========================================================
    # File loading
    # =========================================================

    def choose_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="TIFFファイルを選択",
            filetypes=[
                ("TIFF files", "*.tif *.tiff"),
                ("All files", "*.*"),
            ],
        )

        if not path:
            self.status_var.set("ファイル選択がキャンセルされました。")
            return

        self.load_image(path)

    def load_image(self, path: str | os.PathLike[str]) -> None:
        image_path = Path(path).expanduser()

        if not image_path.exists():
            messagebox.showerror(
                "読み込みエラー",
                f"ファイルが見つかりません。\n{image_path}",
                parent=self.root,
            )
            return

        try:
            with Image.open(image_path) as image:
                array = np.asarray(image, dtype=np.float32)

                # RGB/RGBA TIFFは輝度画像へ変換する。
                if array.ndim == 3:
                    array = np.asarray(
                        image.convert("F"),
                        dtype=np.float32,
                    )

        except Exception as exc:
            messagebox.showerror(
                "読み込みエラー",
                str(exc),
                parent=self.root,
            )
            return

        if array.ndim != 2:
            messagebox.showerror(
                "読み込みエラー",
                f"2次元画像として読み込めませんでした。\nshape={array.shape}",
                parent=self.root,
            )
            return

        finite_mask = np.isfinite(array)
        if not np.any(finite_mask):
            messagebox.showerror(
                "読み込みエラー",
                "有限の画素値がありません。",
                parent=self.root,
            )
            return

        self.image_path = image_path
        self.image_array = array

        self.file_var.set(image_path.name)
        self.root.title(f"Interactive TIFF Viewer — {image_path.name}")

        self.reset_controls(update=False)
        self.update_display()

        self.status_var.set(
            f"読み込み完了：{image_path.name} "
            f"({array.shape[1]} × {array.shape[0]})"
        )

    # =========================================================
    # Image processing / display
    # =========================================================

    def process_image(self) -> np.ndarray:
        if self.image_array is None:
            raise RuntimeError("画像が読み込まれていません。")

        data = self.image_array.astype(np.float32, copy=True)

        finite_mask = np.isfinite(data)
        if not np.all(finite_mask):
            finite_values = data[finite_mask]
            replacement = (
                float(np.nanmedian(finite_values))
                if finite_values.size
                else 0.0
            )
            data[~finite_mask] = replacement

        if self.scale_mode_var.get() == "log":
            data = np.clip(data, 0.0, None)
            positive = data[data > 0.0]

            if positive.size:
                offset = float(np.percentile(positive, 1.0))
                if not math.isfinite(offset) or offset <= 0:
                    offset = float(np.min(positive))
            else:
                offset = 1.0

            data = np.log10(data + offset)

        low_percentile = float(self.low_var.get())
        high_percentile = float(self.high_var.get())

        vmin = float(np.percentile(data, low_percentile))
        vmax = float(np.percentile(data, high_percentile))

        if not math.isfinite(vmin):
            vmin = float(np.nanmin(data))
        if not math.isfinite(vmax):
            vmax = float(np.nanmax(data))
        if vmax <= vmin:
            vmax = vmin + 1e-6

        processed = (data - vmin) / (vmax - vmin)
        return np.clip(processed, 0.0, 1.0)

    def update_display(self) -> None:
        if self.image_array is None:
            return

        try:
            processed = self.process_image()
        except Exception as exc:
            self.status_var.set(f"表示更新エラー：{exc}")
            return

        mode_text = (
            "LOG"
            if self.scale_mode_var.get() == "log"
            else "LINEAR"
        )

        if self.image_artist is None:
            self.ax.clear()
            self.image_artist = self.ax.imshow(
                processed,
                vmin=0.0,
                vmax=1.0,
                origin="upper",
            )
            self.ax.set_axis_off()

            if self.colorbar is not None:
                try:
                    self.colorbar.remove()
                except Exception:
                    pass

            self.colorbar = self.figure.colorbar(
                self.image_artist,
                ax=self.ax,
                fraction=0.046,
                pad=0.04,
            )
        else:
            self.image_artist.set_data(processed)
            self.image_artist.set_clim(0.0, 1.0)

        title_name = (
            self.image_path.name
            if self.image_path is not None
            else "TIFF"
        )
        self.ax.set_title(f"{title_name} — {mode_text}")
        self.canvas.draw_idle()

        self.status_var.set(
            f"{mode_text}表示："
            f"Low {self.low_var.get():.1f} % / "
            f"High {self.high_var.get():.1f} %"
        )

    def _on_slider_change(self, _value: str) -> None:
        self.low_label_var.set(
            f"Low: {self.low_var.get():.1f} %"
        )
        self.high_label_var.set(
            f"High: {self.high_var.get():.1f} %"
        )

        # スライダーを動かしている間の過剰な再描画を抑える。
        if self._update_job is not None:
            try:
                self.root.after_cancel(self._update_job)
            except Exception:
                pass

        self._update_job = self.root.after(
            40,
            self._run_scheduled_update,
        )

    def _run_scheduled_update(self) -> None:
        self._update_job = None
        self.update_display()

    def reset_controls(self, update: bool = True) -> None:
        self.low_var.set(1.0)
        self.high_var.set(99.0)
        self.scale_mode_var.set("linear")
        self.low_label_var.set("Low: 1.0 %")
        self.high_label_var.set("High: 99.0 %")

        if update:
            self.update_display()

    # =========================================================
    # Save
    # =========================================================

    def save_image(self) -> None:
        if self.image_array is None or self.image_path is None:
            messagebox.showinfo(
                "保存",
                "先にTIFFファイルを読み込んでください。",
                parent=self.root,
            )
            return

        try:
            processed = self.process_image()
        except Exception as exc:
            messagebox.showerror(
                "保存エラー",
                str(exc),
                parent=self.root,
            )
            return

        scale_type = self.scale_mode_var.get()
        default_name = (
            f"{self.image_path.stem}_"
            f"{scale_type}_"
            f"{int(round(self.low_var.get()))}-"
            f"{int(round(self.high_var.get()))}.tif"
        )

        save_path = filedialog.asksaveasfilename(
            parent=self.root,
            title="処理画像を保存",
            initialdir=str(self.image_path.parent),
            initialfile=default_name,
            defaultextension=".tif",
            filetypes=[
                ("TIFF files", "*.tif *.tiff"),
                ("All files", "*.*"),
            ],
        )

        if not save_path:
            self.status_var.set("保存をキャンセルしました。")
            return

        save_data = np.round(processed * 65535.0).astype(np.uint16)

        try:
            Image.fromarray(save_data).save(save_path)
        except Exception as exc:
            messagebox.showerror(
                "保存エラー",
                str(exc),
                parent=self.root,
            )
            return

        self.status_var.set(f"保存完了：{save_path}")
        messagebox.showinfo(
            "保存完了",
            f"保存しました。\n{save_path}",
            parent=self.root,
        )

    # =========================================================
    # Close
    # =========================================================

    def close(self) -> None:
        if self._update_job is not None:
            try:
                self.root.after_cancel(self._update_job)
            except Exception:
                pass
            self._update_job = None

        try:
            self.root.quit()
        finally:
            self.root.destroy()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive TIFF Viewer"
    )
    parser.add_argument(
        "image_path",
        nargs="?",
        default=None,
        help="起動時に開くTIFFファイル",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    root = tk.Tk()
    InteractiveViewer(root, initial_path=args.image_path)
    root.mainloop()


if __name__ == "__main__":
    main()
