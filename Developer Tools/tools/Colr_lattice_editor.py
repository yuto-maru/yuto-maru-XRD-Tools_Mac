#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Colr構造の逆格子指数付け

- 実測q値からデバイ環を描画
- Colr構造の対称性と消滅則を適用
- 任意の2ピークとミラー指数から格子定数a, bを算出
- 逆格子点を選択し、指数付け表をコピー
"""

from __future__ import annotations

import colorsys
import math
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


TWO_PI = 2.0 * math.pi
DEFAULT_Q_TEXT = "1.89 3.39 3.80 4.33 5.76"


# Colr相で一般に用いられるHermann–Mauguin表記。
# 図に示された系統的消滅条件を保持する。
SPACE_GROUP_OPTIONS = ("C2/m", "P2₁/a", "P2/a", "P2m")
SPACE_GROUP_INFO = {
    "C2/m": {
        "rule": "hk：h+kが奇数の反射は消滅（例：(21)は消滅）",
    },
    "P2₁/a": {
        "rule": "h0：hが奇数、0k：kが奇数の反射は消滅（例：(21)は出現）",
    },
    "P2/a": {
        "rule": "0k：kが奇数の反射は消滅",
    },
    "P2m": {
        "rule": "すべてのhk反射が出現",
    },
}


@dataclass(frozen=True)
class LatticePoint:
    h: int
    k: int
    q: float
    x: float
    y: float


def parse_q_values(text: str) -> np.ndarray:
    """Parse spaces, commas, semicolons, tabs, or newlines into sorted unique q values."""
    cleaned = (
        text.replace(",", " ")
        .replace(";", " ")
        .replace("\t", " ")
        .replace("\n", " ")
    )
    values = []
    for token in cleaned.split():
        value = float(token)
        if not math.isfinite(value) or value <= 0:
            raise ValueError("q値には有限の正の数を入力してください。")
        values.append(value)

    if len(values) < 2:
        raise ValueError("正のq値を2つ以上入力してください。")

    # Preserve physically distinct peaks while removing exact/near-exact duplicates.
    unique_values = np.array(sorted(set(round(v, 12) for v in values)), dtype=float)
    if len(unique_values) < 2:
        raise ValueError("異なる正のq値を2つ以上入力してください。")
    return unique_values


def solve_reciprocal_spacings(
    q1: float,
    h1: int,
    k1: int,
    q2: float,
    h2: int,
    k2: int,
) -> tuple[float, float]:
    """
    Solve:
        q_i^2 = h_i^2 a*^2 + k_i^2 b*^2

    Returns
    -------
    (a_star, b_star)

    The two assigned reflections must provide linearly independent equations.
    """
    if (h1 == 0 and k1 == 0) or (h2 == 0 and k2 == 0):
        raise ValueError("(0,0)は回折ピークに割り当てられません。")

    matrix = np.array(
        [[float(h1 * h1), float(k1 * k1)],
         [float(h2 * h2), float(k2 * k2)]],
        dtype=float,
    )
    rhs = np.array([q1 * q1, q2 * q2], dtype=float)

    determinant = float(np.linalg.det(matrix))
    if abs(determinant) < 1e-12:
        raise ValueError(
            "指定した2組の(h,k)は独立ではありません。\n"
            "h²:k²の比が異なる反射を選択してください。"
        )

    a2, b2 = np.linalg.solve(matrix, rhs)
    if a2 <= 0 or b2 <= 0:
        raise ValueError(
            "この2組の指数割り当てでは物理的に妥当な解が得られません。\n"
            "a*²とb*²はどちらも正である必要があります。"
        )

    return math.sqrt(float(a2)), math.sqrt(float(b2))


class ColrInteractiveApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Colr構造の逆格子編集・指数付け")
        self.root.minsize(1120, 720)
        self._center_window(1380, 850)

        self.q_values = parse_q_values(DEFAULT_Q_TEXT)
        self.a_star = 1.0
        self.b_star = 1.6
        self.selected_hk: set[tuple[int, int]] = set()
        self.current_points: list[LatticePoint] = []

        # ◆は(110)逆格子点とは独立した操作ハンドルとして扱う。
        # ダブルクリックした位置を、(a*, b*)からの相対位置として保持する。
        self.handle_offset_x = 0.18 * self.a_star
        self.handle_offset_y = 0.12 * self.b_star
        self.dragging_handle = False
        self.drag_last_x: float | None = None
        self.drag_last_y: float | None = None
        self.pending_click_job = None

        self.status_var = tk.StringVar(value="準備完了")
        self.plot_title_var = tk.StringVar(value="Colr構造の逆格子")

        self.q_text_var = tk.StringVar(value=DEFAULT_Q_TEXT)
        self.lattice_type_var = tk.StringVar(value="C2/m")
        self.symmetry_info_var = tk.StringVar(value=self._symmetry_info_text())
        self.a_value_var = tk.StringVar()
        self.b_value_var = tk.StringVar()
        self.ratio_var = tk.StringVar()

        self.peak1_var = tk.StringVar()
        self.peak2_var = tk.StringVar()
        self.h1_var = tk.StringVar(value="1")
        self.k1_var = tk.StringVar(value="1")
        self.h2_var = tk.StringVar(value="2")
        self.k2_var = tk.StringVar(value="0")

        self.hmax_var = tk.StringVar(value="8")
        self.kmax_var = tk.StringVar(value="8")
        self.tolerance_var = tk.StringVar(value="2.0")
        self.show_labels_var = tk.BooleanVar(value=True)
        self.show_grid_var = tk.BooleanVar(value=True)
        self.show_ring_labels_var = tk.BooleanVar(value=True)
        self.ring_label_mode_var = tk.StringVar(value="q")

        self._build_ui()
        self._update_peak_choices()
        self._update_derived_values()
        self.redraw()

    # ------------------------------------------------------------------
    # Window / UI
    # ------------------------------------------------------------------

    def _center_window(self, width: int, height: int) -> None:
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = min(width, max(900, screen_w - 80))
        height = min(height, max(650, screen_h - 100))
        x = max(20, (screen_w - width) // 2)
        y = max(20, (screen_h - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=8)
        outer.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(outer, width=350)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        left.pack_propagate(False)

        right = ttk.Frame(outer)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_controls(left)
        self._build_plot(right)

        status = ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor=tk.W,
            relief=tk.SUNKEN,
            padding=(8, 4),
        )
        status.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_controls(self, parent: ttk.Frame) -> None:
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        control_frame = ttk.Frame(canvas)

        control_frame.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas_window = canvas.create_window((0, 0), window=control_frame, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(canvas_window, width=event.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        title = ttk.Label(
            control_frame,
            text="Colr構造の逆格子編集・指数付け",
        )
        title.pack(anchor=tk.W, pady=(2, 8))

        # Experimental q
        q_box = ttk.LabelFrame(control_frame, text="1. 実測デバイ環", padding=8)
        q_box.pack(fill=tk.X, pady=4)

        ttk.Label(
            q_box,
            text="q値（空白・カンマ・改行で区切る）",
        ).pack(anchor=tk.W)

        q_entry = ttk.Entry(q_box, textvariable=self.q_text_var)
        q_entry.pack(fill=tk.X, pady=(3, 6))
        q_entry.bind("<Return>", lambda _event: self.apply_q_values())

        ttk.Button(
            q_box,
            text="q値を反映",
            command=self.apply_q_values,
        ).pack(fill=tk.X)

        ttk.Label(
            q_box,
            text="qが nm⁻¹ の場合はa,bもnm、qが Å⁻¹ の場合はa,bもÅ",
            foreground="#555555",
            wraplength=315,
        ).pack(anchor=tk.W, pady=(5, 0))

        # Two-peak fit
        fit_box = ttk.LabelFrame(
            control_frame,
            text="2. 任意の2ピークへの指数割り当て",
            padding=8,
        )
        fit_box.pack(fill=tk.X, pady=4)

        header = ttk.Frame(fit_box)
        header.pack(fill=tk.X)
        ttk.Label(header, text="").grid(row=0, column=0, padx=2)
        ttk.Label(header, text="q", anchor=tk.CENTER).grid(row=0, column=1, padx=2)
        ttk.Label(header, text="h", anchor=tk.CENTER).grid(row=0, column=2, padx=2)
        ttk.Label(header, text="k", anchor=tk.CENTER).grid(row=0, column=3, padx=2)

        row1 = ttk.Frame(fit_box)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="ピーク1", width=7).grid(row=0, column=0, padx=2)
        self.peak1_combo = ttk.Combobox(
            row1, textvariable=self.peak1_var, state="readonly", width=12
        )
        self.peak1_combo.grid(row=0, column=1, padx=2)
        ttk.Entry(row1, textvariable=self.h1_var, width=5).grid(row=0, column=2, padx=2)
        ttk.Entry(row1, textvariable=self.k1_var, width=5).grid(row=0, column=3, padx=2)

        row2 = ttk.Frame(fit_box)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="ピーク2", width=7).grid(row=0, column=0, padx=2)
        self.peak2_combo = ttk.Combobox(
            row2, textvariable=self.peak2_var, state="readonly", width=12
        )
        self.peak2_combo.grid(row=0, column=1, padx=2)
        ttk.Entry(row2, textvariable=self.h2_var, width=5).grid(row=0, column=2, padx=2)
        ttk.Entry(row2, textvariable=self.k2_var, width=5).grid(row=0, column=3, padx=2)

        ttk.Button(
            fit_box,
            text="2ピークから格子定数 a, b を算出",
            command=self.fit_from_two_peaks,
        ).pack(fill=tk.X, pady=(5, 0))

        # Lattice controls
        lattice_box = ttk.LabelFrame(
            control_frame,
            text="3. 逆格子",
            padding=8,
        )
        lattice_box.pack(fill=tk.X, pady=4)

        ttk.Label(
            lattice_box,
            text="Colr構造の対称性（Hermann–Mauguin記号）",
        ).pack(anchor=tk.W)
        lattice_combo = ttk.Combobox(
            lattice_box,
            textvariable=self.lattice_type_var,
            state="readonly",
            values=SPACE_GROUP_OPTIONS,
        )
        lattice_combo.pack(fill=tk.X, pady=(2, 4))
        lattice_combo.bind("<<ComboboxSelected>>", lambda _event: self._lattice_changed())

        ttk.Label(
            lattice_box,
            textvariable=self.symmetry_info_var,
            foreground="#555555",
            wraplength=315,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 6))

        result_box = ttk.Frame(lattice_box)
        result_box.pack(fill=tk.X, pady=(2, 2))

        ttk.Label(
            result_box,
            textvariable=self.a_value_var,
        ).pack(anchor=tk.W, pady=1)
        ttk.Label(
            result_box,
            textvariable=self.b_value_var,
        ).pack(anchor=tk.W, pady=1)
        ttk.Label(
            result_box,
            textvariable=self.ratio_var,
        ).pack(anchor=tk.W, pady=(1, 3))

        ttk.Label(
            lattice_box,
            text="図中をダブルクリック：◆の位置を指定\n"
                 "◆をドラッグ：逆格子の縦横比を変更\n"
                 "Cキー：選択点をコピー／右クリック：選択解除",
            foreground="#555555",
        ).pack(anchor=tk.W, pady=(3, 6))

        action_row = ttk.Frame(lattice_box)
        action_row.pack(fill=tk.X, pady=(3, 0))

        ttk.Button(
            action_row,
            text="自動選択",
            command=self.auto_select_matching_points,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        ttk.Button(
            action_row,
            text="選択解除",
            command=self.clear_selection,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        ttk.Button(
            action_row,
            text="表をコピー",
            command=self.copy_selected_table,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        # Display and matching
        display_box = ttk.LabelFrame(
            control_frame,
            text="4. 格子点表示とピーク照合",
            padding=8,
        )
        display_box.pack(fill=tk.X, pady=4)

        limits = ttk.Frame(display_box)
        limits.pack(fill=tk.X)
        ttk.Label(limits, text="hの最大値").grid(row=0, column=0, padx=2, pady=2)
        ttk.Entry(limits, textvariable=self.hmax_var, width=6).grid(
            row=0, column=1, padx=2, pady=2
        )
        ttk.Label(limits, text="kの最大値").grid(row=0, column=2, padx=2, pady=2)
        ttk.Entry(limits, textvariable=self.kmax_var, width=6).grid(
            row=0, column=3, padx=2, pady=2
        )

        tolerance = ttk.Frame(display_box)
        tolerance.pack(fill=tk.X)
        ttk.Label(tolerance, text="一致許容誤差（%）").grid(
            row=0, column=0, padx=2, pady=2
        )
        ttk.Entry(tolerance, textvariable=self.tolerance_var, width=8).grid(
            row=0, column=1, padx=2, pady=2
        )

        ttk.Checkbutton(
            display_box,
            text="ミラー指数ラベルを表示",
            variable=self.show_labels_var,
            command=self.redraw,
        ).pack(anchor=tk.W)
        ttk.Checkbutton(
            display_box,
            text="逆格子グリッドを表示",
            variable=self.show_grid_var,
            command=self.redraw,
        ).pack(anchor=tk.W)
        ring_label_row = ttk.Frame(display_box)
        ring_label_row.pack(fill=tk.X)

        ttk.Checkbutton(
            ring_label_row,
            text="環上に値を表示",
            variable=self.show_ring_labels_var,
            command=self.redraw,
        ).pack(side=tk.LEFT)

        ttk.Radiobutton(
            ring_label_row,
            text="q値",
            variable=self.ring_label_mode_var,
            value="q",
            command=self.redraw,
        ).pack(side=tk.LEFT, padx=(10, 2))

        ttk.Radiobutton(
            ring_label_row,
            text="d値",
            variable=self.ring_label_mode_var,
            value="d",
            command=self.redraw,
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            display_box,
            text="再描画",
            command=self.redraw,
        ).pack(fill=tk.X, pady=(5, 2))

        # Selection table
        table_box = ttk.LabelFrame(
            control_frame,
            text="選択した逆格子点",
            padding=6,
        )
        table_box.pack(fill=tk.BOTH, expand=True, pady=4)

        columns = ("miller", "qcalc", "dcalc", "qexp", "error")
        self.tree = ttk.Treeview(
            table_box,
            columns=columns,
            show="headings",
            height=8,
        )
        headings = {
            "miller": "(hk0)",
            "qcalc": "q計算値",
            "dcalc": "d計算値",
            "qexp": "q実測値",
            "error": "誤差 %",
        }
        widths = {
            "miller": 58,
            "qcalc": 68,
            "dcalc": 68,
            "qexp": 68,
            "error": 58,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor=tk.CENTER)

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self._remove_tree_selection)

    def _build_plot(self, parent: ttk.Frame) -> None:
        # 日本語タイトルはMatplotlib内ではなく、OS標準フォントを使うTkinter側に表示する。
        ttk.Label(
            parent,
            textvariable=self.plot_title_var,
            anchor=tk.CENTER,
        ).pack(fill=tk.X, pady=(0, 4))

        self.figure = Figure(figsize=(8.8, 7.5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.09, right=0.98, bottom=0.09, top=0.98)

        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(self.canvas, parent, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(fill=tk.X)
        self.toolbar = toolbar

        self.canvas.mpl_connect("button_press_event", self.on_mouse_press)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("button_release_event", self.on_mouse_release)
        self.canvas.mpl_connect("key_press_event", self.on_key_press)

    # ------------------------------------------------------------------
    # Input and lattice state
    # ------------------------------------------------------------------

    def apply_q_values(self) -> None:
        try:
            self.q_values = parse_q_values(self.q_text_var.get())
        except Exception as exc:
            messagebox.showerror("q値の入力エラー", str(exc), parent=self.root)
            return

        self._update_peak_choices()
        self.redraw()
        self.status_var.set(f"実測q値を{len(self.q_values)}個読み込みました。")

    def _update_peak_choices(self) -> None:
        values = [self._format_q(q) for q in self.q_values]
        self.peak1_combo["values"] = values
        self.peak2_combo["values"] = values

        if values:
            if self.peak1_var.get() not in values:
                self.peak1_var.set(values[0])
            if self.peak2_var.get() not in values:
                self.peak2_var.set(values[min(1, len(values) - 1)])

    def fit_from_two_peaks(self) -> None:
        try:
            q1 = float(self.peak1_var.get())
            q2 = float(self.peak2_var.get())
            h1 = self._parse_index(self.h1_var.get(), "ピーク1のh")
            k1 = self._parse_index(self.k1_var.get(), "ピーク1のk")
            h2 = self._parse_index(self.h2_var.get(), "ピーク2のh")
            k2 = self._parse_index(self.k2_var.get(), "ピーク2のk")

            for peak_name, h, k in (("ピーク1", h1, k1), ("ピーク2", h2, k2)):
                if (h, k) != (0, 0) and not self._is_allowed(h, k):
                    raise ValueError(
                        f"{peak_name}に指定した({h}{k})は、"
                        f"{self.lattice_type_var.get()}の消滅則では出現しません。\n"
                        f"{SPACE_GROUP_INFO[self.lattice_type_var.get()]['rule']}"
                    )

            a_star, b_star = solve_reciprocal_spacings(
                q1, h1, k1, q2, h2, k2
            )
        except Exception as exc:
            messagebox.showerror("最適化エラー", str(exc), parent=self.root)
            return

        self.a_star = a_star
        self.b_star = b_star
        self._sync_spacing_vars()
        self.redraw()

        q1_calc = math.hypot(h1 * self.a_star, k1 * self.b_star)
        q2_calc = math.hypot(h2 * self.a_star, k2 * self.b_star)
        self.status_var.set(
            "格子定数a,bの算出が完了しました："
            f"({h1}{k1}) {q1_calc:.5f}, ({h2}{k2}) {q2_calc:.5f}."
        )

    def _lattice_changed(self) -> None:
        self.symmetry_info_var.set(self._symmetry_info_text())
        self.selected_hk = {
            (h, k)
            for h, k in self.selected_hk
            if self._is_allowed(h, k)
        }
        self.redraw()
        self.status_var.set(
            f"空間群を{self.lattice_type_var.get()}に変更しました。"
        )

    def _sync_spacing_vars(self) -> None:
        self._update_derived_values()

    def _update_derived_values(self) -> None:
        # 単位格子枠
        self.ax.plot(
            [0.0, self.a_star, self.a_star, 0.0, 0.0],
            [0.0, 0.0, self.b_star, self.b_star, 0.0],
            linewidth=1.5,
            color="#666666",
            zorder=7,
        )

        # ◆は(110)点から独立させ、任意位置に表示する。
        handle_x = self.a_star + self.handle_offset_x
        handle_y = self.b_star + self.handle_offset_y

        # 単位格子の右上角と操作ハンドルの対応を示す補助線
        self.ax.plot(
            [self.a_star, handle_x],
            [self.b_star, handle_y],
            linestyle="--",
            linewidth=1.0,
            color="#777777",
            alpha=0.85,
            zorder=8,
        )
        self.ax.scatter(
            [handle_x],
            [handle_y],
            marker="D",
            s=95,
            facecolor="white",
            edgecolor="#222222",
            linewidth=1.4,
            zorder=9,
            clip_on=False,
        )

        a = TWO_PI / self.a_star
        b = TWO_PI / self.b_star
        self.a_value_var.set(f"a = {a:.5f}")
        self.b_value_var.set(f"b = {b:.5f}")
        self.ratio_var.set(f"a/b = {a / b:.5f}")


    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def redraw(self, preserve_limits: bool = False) -> None:
        old_xlim = self.ax.get_xlim()
        old_ylim = self.ax.get_ylim()

        try:
            hmax, kmax = self._get_hk_max()
        except ValueError:
            return

        self.ax.clear()
        q_limit = self._default_q_limit()
        theta = np.linspace(0.0, math.pi / 2.0, 500)

        # Experimental Debye-ring arcs
        # 各デバイ環を区別できるよう、環ごとに異なる色を割り当てる。
        ring_count = max(len(self.q_values), 1)
        for ring_index, q in enumerate(self.q_values):
            hue = (0.08 + ring_index / ring_count) % 1.0
            ring_color = colorsys.hsv_to_rgb(hue, 0.72, 0.78)

            x = q * np.cos(theta)
            y = q * np.sin(theta)
            self.ax.plot(
                x,
                y,
                linewidth=1.35,
                color=ring_color,
                alpha=0.86,
                zorder=1,
            )
            if self.show_ring_labels_var.get():
                if self.ring_label_mode_var.get() == "d":
                    ring_label_value = TWO_PI / q
                else:
                    ring_label_value = q

                self.ax.text(
                    q,
                    0.015 * q_limit,
                    f"{ring_label_value:.2f}",
                    fontsize=8,
                    color=ring_color,
                    ha="center",
                    va="bottom",
                    clip_on=True,
                )

        # Reciprocal-lattice grid
        if self.show_grid_var.get():
            for h in range(hmax + 1):
                x = h * self.a_star
                if x <= q_limit * 1.02:
                    self.ax.axvline(
                        x,
                        linewidth=0.65,
                        color="#AAAAAA",
                        alpha=0.40,
                        zorder=0,
                    )
            for k in range(kmax + 1):
                y = k * self.b_star
                if y <= q_limit * 1.02:
                    self.ax.axhline(
                        y,
                        linewidth=0.65,
                        color="#AAAAAA",
                        alpha=0.40,
                        zorder=0,
                    )

        self.current_points = self._generate_visible_points(hmax, kmax, q_limit)

        if self.current_points:
            xs = [point.x for point in self.current_points]
            ys = [point.y for point in self.current_points]
            self.ax.scatter(
                xs,
                ys,
                s=28,
                facecolor="#222222",
                edgecolor="white",
                linewidth=0.35,
                zorder=3,
            )

            if self.show_labels_var.get():
                label_offset = 0.012 * q_limit
                for point in self.current_points:
                    self.ax.text(
                        point.x + label_offset,
                        point.y + label_offset,
                        f"({point.h}{point.k})",
                        fontsize=7,
                        color="#222222",
                        zorder=4,
                        clip_on=True,
                    )

        selected_points = [
            point
            for point in self.current_points
            if (point.h, point.k) in self.selected_hk
        ]
        if selected_points:
            self.ax.scatter(
                [point.x for point in selected_points],
                [point.y for point in selected_points],
                s=95,
                facecolor="none",
                edgecolor="#D62728",
                linewidth=1.8,
                zorder=6,
            )

        a = TWO_PI / self.a_star
        b = TWO_PI / self.b_star
        space_group = self.lattice_type_var.get()
        self.plot_title_var.set(
            f"Colr構造の逆格子（{space_group}）　a = {a:.5f}、b = {b:.5f}"
        )
        self.ax.set_title("")
        self.ax.set_xlabel(r"$q_x$")
        self.ax.set_ylabel(r"$q_y$")
        self.ax.set_aspect("equal", adjustable="box")
        self.ax.grid(False)

        if preserve_limits and self._valid_limits(old_xlim, old_ylim):
            self.ax.set_xlim(old_xlim)
            self.ax.set_ylim(old_ylim)
        else:
            self.ax.set_xlim(0.0, q_limit)
            self.ax.set_ylim(0.0, q_limit)

        self.canvas.draw_idle()
        self._update_derived_values()
        self._refresh_tree()

    def _generate_visible_points(
        self,
        hmax: int,
        kmax: int,
        q_limit: float,
    ) -> list[LatticePoint]:
        points = []
        for h in range(hmax + 1):
            for k in range(kmax + 1):
                if h == 0 and k == 0:
                    continue
                if not self._is_allowed(h, k):
                    continue

                x = h * self.a_star
                y = k * self.b_star
                q = math.hypot(x, y)
                if x <= q_limit * 1.02 and y <= q_limit * 1.02:
                    points.append(LatticePoint(h=h, k=k, q=q, x=x, y=y))

        points.sort(key=lambda point: (point.q, point.h, point.k))
        return points

    # ------------------------------------------------------------------
    # Plot interaction
    # ------------------------------------------------------------------

    def on_mouse_press(self, event) -> None:
        if self._toolbar_is_active():
            return
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return

        if event.button == 3:
            self._cancel_pending_point_click()
            self.clear_selection()
            return
        if event.button != 1:
            return

        # ダブルクリックした位置へ、◆だけを移動する。
        # a*、b*自体はこの操作では変更しない。
        if bool(getattr(event, "dblclick", False)):
            self._cancel_pending_point_click()
            self.handle_offset_x = float(event.xdata) - self.a_star
            self.handle_offset_y = float(event.ydata) - self.b_star
            self.redraw(preserve_limits=False)
            self.status_var.set(
                "ダブルクリックした位置へ操作ハンドル◆を移動しました。"
            )
            return

        handle_x = self.a_star + self.handle_offset_x
        handle_y = self.b_star + self.handle_offset_y
        q_limit = max(self.ax.get_xlim()[1], self.ax.get_ylim()[1])
        handle_distance = math.hypot(
            event.xdata - handle_x,
            event.ydata - handle_y,
        )

        if handle_distance <= 0.045 * q_limit:
            self._cancel_pending_point_click()
            self.dragging_handle = True
            self.drag_last_x = float(event.xdata)
            self.drag_last_y = float(event.ydata)
            self.status_var.set("◆をドラッグして逆格子を変更中です。")
            return

        # ダブルクリック時に最初の1クリックで格子点が選択されないよう、
        # 格子点選択を少し遅らせる。
        self._cancel_pending_point_click()
        click_x = float(event.xdata)
        click_y = float(event.ydata)
        self.pending_click_job = self.root.after(
            230,
            lambda x=click_x, y=click_y: self._run_pending_point_click(x, y),
        )

    def on_mouse_move(self, event) -> None:
        if not self.dragging_handle:
            return
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        if self.drag_last_x is None or self.drag_last_y is None:
            return

        current_x = float(event.xdata)
        current_y = float(event.ydata)
        delta_x = current_x - self.drag_last_x
        delta_y = current_y - self.drag_last_y

        minimum = max(float(np.max(self.q_values)) * 0.002, 1e-6)
        old_a_star = self.a_star
        old_b_star = self.b_star
        self.a_star = max(self.a_star + delta_x, minimum)
        self.b_star = max(self.b_star + delta_y, minimum)

        # 軸の下限に達した場合も、次の移動量が不連続にならないよう更新する。
        self.drag_last_x = current_x - (old_a_star + delta_x - self.a_star)
        self.drag_last_y = current_y - (old_b_star + delta_y - self.b_star)

        # ◆の相対位置は維持したまま、逆格子だけを変形する。
        self.redraw(preserve_limits=False)

    def on_mouse_release(self, _event) -> None:
        if not self.dragging_handle:
            return

        self.dragging_handle = False
        self.drag_last_x = None
        self.drag_last_y = None
        self.status_var.set(
            f"逆格子を更新しました：a = {TWO_PI / self.a_star:.5f}, "
            f"b = {TWO_PI / self.b_star:.5f}"
        )

    def _run_pending_point_click(self, x: float, y: float) -> None:
        self.pending_click_job = None
        self._toggle_nearest_lattice_point(x, y)

    def _cancel_pending_point_click(self) -> None:
        if self.pending_click_job is None:
            return
        try:
            self.root.after_cancel(self.pending_click_job)
        except tk.TclError:
            pass
        self.pending_click_job = None

    def on_key_press(self, event) -> None:
        if event.key is None:
            return
        key = str(event.key).lower()
        if key == "c":
            self.copy_selected_table()
        elif key in ("escape", "delete", "backspace"):
            self.clear_selection()

    def _toggle_nearest_lattice_point(self, x: float, y: float) -> None:
        if not self.current_points:
            return

        nearest = min(
            self.current_points,
            key=lambda point: (point.x - x) ** 2 + (point.y - y) ** 2,
        )
        distance = math.hypot(nearest.x - x, nearest.y - y)
        q_limit = max(self.ax.get_xlim()[1], self.ax.get_ylim()[1])
        if distance > 0.035 * q_limit:
            return

        hk = (nearest.h, nearest.k)
        if hk in self.selected_hk:
            self.selected_hk.remove(hk)
            action = "選択解除："
        else:
            self.selected_hk.add(hk)
            action = "選択："

        self.redraw(preserve_limits=True)
        self.status_var.set(f"{action}({nearest.h}{nearest.k}0)")

    # ------------------------------------------------------------------
    # Matching, table, clipboard
    # ------------------------------------------------------------------

    def auto_select_matching_points(self) -> None:
        try:
            tolerance_percent = float(self.tolerance_var.get())
            if tolerance_percent < 0 or not math.isfinite(tolerance_percent):
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "許容誤差の入力エラー",
                "一致許容誤差には0以上の有限値を入力してください。",
                parent=self.root,
            )
            return

        # 実測q値と逆格子点の候補ペアを作り、誤差の小さい順に
        # 1対1で割り当てる。各実測q値につき最大1点、
        # 各逆格子点も最大1つの実測q値にのみ対応させる。
        candidates = []
        for q_index, q_exp in enumerate(self.q_values):
            for point in self.current_points:
                rel_error = abs(point.q - q_exp) / q_exp
                if rel_error * 100.0 <= tolerance_percent:
                    candidates.append(
                        (
                            rel_error,
                            abs(point.q - q_exp),
                            point.q,
                            point.h,
                            point.k,
                            q_index,
                            point,
                        )
                    )

        candidates.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2],
                item[3],
                item[4],
            )
        )

        used_q_indices = set()
        used_points = set()
        selected = set()

        for _rel_error, _abs_error, _q_calc, _h, _k, q_index, point in candidates:
            hk = (point.h, point.k)
            if q_index in used_q_indices or hk in used_points:
                continue

            used_q_indices.add(q_index)
            used_points.add(hk)
            selected.add(hk)

        self.selected_hk = selected
        self.redraw(preserve_limits=True)

        unmatched_count = len(self.q_values) - len(used_q_indices)
        if unmatched_count == 0:
            self.status_var.set(
                f"実測q値{len(self.q_values)}個に対し、"
                f"逆格子点を1点ずつ自動選択しました。"
            )
        else:
            self.status_var.set(
                f"実測q値{len(self.q_values)}個中{len(used_q_indices)}個に、"
                f"逆格子点を1点ずつ割り当てました。"
                f"未割り当て：{unmatched_count}個"
            )

    def clear_selection(self) -> None:
        self.selected_hk.clear()
        self.redraw(preserve_limits=True)
        self.status_var.set("選択した逆格子点をすべて解除しました。")

    def copy_selected_table(self) -> None:
        selected_points = [
            point
            for point in self.current_points
            if (point.h, point.k) in self.selected_hk
        ]

        if not selected_points:
            self.status_var.set("コピーする逆格子点が選択されていません。")
            return

        selected_points = [
            point for point in selected_points
            if point.q > 0
        ]
        selected_points.sort(
            key=lambda point: TWO_PI / point.q,
            reverse=True,
        )

        if not selected_points:
            self.status_var.set("d値を計算できる逆格子点がありません。")
            return

        d_max = max(TWO_PI / point.q for point in selected_points)
        rows = []

        for point in selected_points:
            d_calc = TWO_PI / point.q
            rows.append(
                [
                    f"{point.h}{point.k}0",
                    str(point.h),
                    str(point.k),
                    "0",
                    f"{d_calc:.6f}",
                    f"{d_calc / d_max:.6f}",
                ]
            )

        clipboard_text = "\n".join(
            "\t".join(row)
            for row in rows
        )

        self.root.clipboard_clear()
        self.root.clipboard_append(clipboard_text)
        self.root.update_idletasks()

        self.status_var.set(
            f"選択した{len(rows)}点の数値データをコピーしました。"
        )

    def _refresh_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        points = [
            point
            for point in self.current_points
            if (point.h, point.k) in self.selected_hk
        ]
        points.sort(key=lambda point: (point.q, point.h, point.k))

        for point in points:
            d_calc = TWO_PI / point.q
            q_exp, _delta, rel_error = self._nearest_experimental_peak(point.q)
            self.tree.insert(
                "",
                tk.END,
                iid=f"{point.h},{point.k}",
                values=(
                    f"{point.h}{point.k}0",
                    f"{point.q:.4f}",
                    f"{d_calc:.4f}",
                    f"{q_exp:.4f}",
                    f"{rel_error * 100.0:.2f}",
                ),
            )

    def _remove_tree_selection(self, _event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        for item in selection:
            try:
                h_text, k_text = item.split(",", maxsplit=1)
                self.selected_hk.discard((int(h_text), int(k_text)))
            except Exception:
                continue
        self.redraw(preserve_limits=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _nearest_experimental_peak(self, q_calc: float) -> tuple[float, float, float]:
        index = int(np.argmin(np.abs(self.q_values - q_calc)))
        q_exp = float(self.q_values[index])
        delta = q_calc - q_exp
        relative = abs(delta) / q_exp
        return q_exp, delta, relative

    def _symmetry_info_text(self) -> str:
        space_group = self.lattice_type_var.get()
        info = SPACE_GROUP_INFO[space_group]
        return f"消滅則：{info['rule']}"

    def _is_allowed(self, h: int, k: int) -> bool:
        """選択中のColr空間群に対して(hk)反射が許容されるか判定する。"""
        if h == 0 and k == 0:
            return False

        space_group = self.lattice_type_var.get()

        if space_group == "C2/m":
            # hk: h+k = 2n+1 disappear
            return (h + k) % 2 == 0

        if space_group == "P2₁/a":
            # h0: h = 2n+1 and 0k: k = 2n+1 disappear.
            # General hk reflections such as (21) are allowed.
            if k == 0 and h % 2 == 1:
                return False
            if h == 0 and k % 2 == 1:
                return False
            return True

        if space_group == "P2/a":
            # 0k: k = 2n+1 disappear
            if h == 0 and k % 2 == 1:
                return False
            return True

        if space_group == "P2m":
            # All hk reflections appear.
            return True

        # Unknown symbols are treated conservatively as disallowed.
        return False

    def _get_hk_max(self) -> tuple[int, int]:
        try:
            hmax = int(self.hmax_var.get())
            kmax = int(self.kmax_var.get())
            if hmax < 1 or kmax < 1 or hmax > 100 or kmax > 100:
                raise ValueError
            return hmax, kmax
        except ValueError:
            messagebox.showerror(
                "指数範囲の入力エラー",
                "hとkの最大値には1～100の整数を入力してください。",
                parent=self.root,
            )
            raise ValueError

    def _default_q_limit(self) -> float:
        """実測環、単位格子、独立操作ハンドルが収まる表示上限を計算する。"""
        if len(self.q_values) == 0:
            experimental_limit = 5.0
        else:
            experimental_limit = float(np.max(self.q_values)) * 1.12

        handle_x = self.a_star + self.handle_offset_x
        handle_y = self.b_star + self.handle_offset_y
        lattice_limit = max(
            self.a_star,
            self.b_star,
            handle_x,
            handle_y,
        ) * 1.22

        return max(experimental_limit, lattice_limit, 1e-6)

    def _toolbar_is_active(self) -> bool:
        mode = getattr(self.toolbar, "mode", "")
        return bool(mode)

    @staticmethod
    def _valid_limits(
        xlim: tuple[float, float],
        ylim: tuple[float, float],
    ) -> bool:
        return (
            len(xlim) == 2
            and len(ylim) == 2
            and all(math.isfinite(value) for value in (*xlim, *ylim))
            and xlim[1] > xlim[0]
            and ylim[1] > ylim[0]
        )

    @staticmethod
    def _parse_index(text: str, name: str) -> int:
        try:
            value = int(text)
        except ValueError as exc:
            raise ValueError(f"{name}には整数を入力してください。") from exc
        if value < 0:
            raise ValueError(f"{name}には0以上の整数を入力してください。")
        return value

    @staticmethod
    def _format_q(q: float) -> str:
        return f"{q:.8g}"


def main() -> None:
    root = tk.Tk()
    app = ColrInteractiveApp(root)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
