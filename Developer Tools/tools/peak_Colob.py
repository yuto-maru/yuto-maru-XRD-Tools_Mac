#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Colob構造の逆格子編集・指数付け

- q値をウィンドウ内で入力
- 任意の1st / 2ndピークとミラー指数から斜方格子のa, bを算出
- gammaを変更しながら逆格子を再計算
- デバイ環上の表示をq値 / d値で切り替え
- 逆格子点を選択し、指数付け表をコピー
"""

from __future__ import annotations

import colorsys
import math
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk

import numpy as np
import pyperclip
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


TWO_PI = 2.0 * math.pi
DEFAULT_Q_TEXT = (
    "2.7827 3.3936 3.9638 4.7784 5.5929 "
    "5.9594 6.8145 7.0588 7.9138"
)
GAMMA_MIN = 90.0
GAMMA_MAX = 170.0
THEORY_PRINT_COUNT = 60


@dataclass(frozen=True)
class LatticePoint:
    h: int
    k: int
    q: float
    x: float
    y: float


def parse_q_values(text: str) -> np.ndarray:
    """空白、カンマ、セミコロン、タブ、改行で区切られたq値を読み込む。"""
    cleaned = (
        text.replace(",", " ")
        .replace(";", " ")
        .replace("\t", " ")
        .replace("\n", " ")
    )

    values: list[float] = []
    for token in cleaned.split():
        value = float(token)
        if not math.isfinite(value) or value <= 0:
            raise ValueError("q値には有限の正の数を入力してください。")
        values.append(value)

    if len(values) < 2:
        raise ValueError("異なる正のq値を2つ以上入力してください。")

    unique_values = np.array(
        sorted(set(round(value, 12) for value in values)),
        dtype=float,
    )
    if len(unique_values) < 2:
        raise ValueError("異なる正のq値を2つ以上入力してください。")

    return unique_values


def reciprocal_angle_rad(gamma_deg: float) -> float:
    """直接格子角gammaに対応する逆格子角（180°−gamma）をradで返す。"""
    return math.radians(180.0 - gamma_deg)


def solve_oblique_reciprocal_lengths(
    q1: float,
    h1: int,
    k1: int,
    q2: float,
    h2: int,
    k2: int,
    gamma_deg: float,
    root_mode: str,
) -> tuple[float, float, list[tuple[float, float]]]:
    """
    任意の2反射から |a*|, |b*| を求める。

    q_hk² = h²A² + k²B² + 2hkAB cos(alpha)
    A = |a*|, B = |b*|, alpha = 180° - gamma

    r = B/A とおき、2式の比からrの二次方程式を解く。
    """
    if (h1, k1) == (0, 0) or (h2, k2) == (0, 0):
        raise ValueError("(0,0)は回折ピークに割り当てられません。")

    if not (GAMMA_MIN <= gamma_deg <= GAMMA_MAX):
        raise ValueError(
            f"gammaには{GAMMA_MIN:.0f}～{GAMMA_MAX:.0f}°を入力してください。"
        )

    alpha = reciprocal_angle_rad(gamma_deg)
    cos_alpha = math.cos(alpha)
    ratio_q2_q1 = (q2 / q1) ** 2

    # c2*r² + c1*r + c0 = 0
    c2 = float(k2 * k2 - ratio_q2_q1 * k1 * k1)
    c1 = float(
        2.0
        * cos_alpha
        * (h2 * k2 - ratio_q2_q1 * h1 * k1)
    )
    c0 = float(h2 * h2 - ratio_q2_q1 * h1 * h1)

    eps = 1e-12
    ratio_roots: list[float] = []

    if abs(c2) < eps:
        if abs(c1) < eps:
            raise ValueError(
                "指定した2組の指数ではa*とb*を一意に決定できません。\n"
                "異なる方向を含む2反射を指定してください。"
            )
        ratio_roots = [-c0 / c1]
    else:
        discriminant = c1 * c1 - 4.0 * c2 * c0
        if discriminant < -eps:
            raise ValueError(
                "このq値、指数、gammaの組合せでは正の格子定数を得られません。"
            )

        discriminant = max(discriminant, 0.0)
        sqrt_d = math.sqrt(discriminant)
        ratio_roots = [
            (-c1 + sqrt_d) / (2.0 * c2),
            (-c1 - sqrt_d) / (2.0 * c2),
        ]

    candidates: list[tuple[float, float]] = []

    for ratio_ba in ratio_roots:
        if not math.isfinite(ratio_ba) or ratio_ba <= eps:
            continue

        factor1 = (
            h1 * h1
            + 2.0 * h1 * k1 * cos_alpha * ratio_ba
            + k1 * k1 * ratio_ba * ratio_ba
        )
        if factor1 <= eps:
            continue

        a_star = q1 / math.sqrt(factor1)
        b_star = ratio_ba * a_star

        q1_check = math.sqrt(
            h1 * h1 * a_star * a_star
            + k1 * k1 * b_star * b_star
            + 2.0 * h1 * k1 * a_star * b_star * cos_alpha
        )
        q2_check = math.sqrt(
            h2 * h2 * a_star * a_star
            + k2 * k2 * b_star * b_star
            + 2.0 * h2 * k2 * a_star * b_star * cos_alpha
        )

        tolerance = 1e-7 * max(q1, q2, 1.0)
        if abs(q1_check - q1) > tolerance or abs(q2_check - q2) > tolerance:
            continue

        if a_star > eps and b_star > eps:
            candidates.append((a_star, b_star))

    # 数値的に同一の解を除く
    unique_candidates: list[tuple[float, float]] = []
    for candidate in candidates:
        if not any(
            abs(candidate[0] - old[0]) < 1e-10
            and abs(candidate[1] - old[1]) < 1e-10
            for old in unique_candidates
        ):
            unique_candidates.append(candidate)

    if not unique_candidates:
        raise ValueError(
            "正のa*とb*が得られません。\n"
            "ピーク、指数、gammaの割り当てを確認してください。"
        )

    unique_candidates.sort(key=lambda pair: pair[1])
    chosen = (
        unique_candidates[0]
        if root_mode == "min"
        else unique_candidates[-1]
    )

    return chosen[0], chosen[1], unique_candidates


def overbar_int(value: int) -> str:
    if value >= 0:
        return str(value)
    return "".join(char + "\u0304" for char in str(abs(value)))


def miller_label(h: int, k: int, include_l: bool = False) -> str:
    body = f"{overbar_int(h)}{overbar_int(k)}"
    if include_l:
        body += "0"
    return body


class ColobLatticeEditor:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Colob構造の逆格子編集・指数付け")
        self.root.minsize(1120, 720)
        self._center_window(1380, 860)

        self.q_values = parse_q_values(DEFAULT_Q_TEXT)
        self.a_star = float(self.q_values[0])
        self.b_star = float(self.q_values[1])
        self.selected_hk: set[tuple[int, int]] = set()
        self.current_points: list[LatticePoint] = []
        self.solution_candidates: list[tuple[float, float]] = []

        self.status_var = tk.StringVar(value="準備完了")
        self.plot_title_var = tk.StringVar(value="Colob構造の逆格子")

        self.q_text_var = tk.StringVar(value=DEFAULT_Q_TEXT)
        self.peak1_var = tk.StringVar()
        self.peak2_var = tk.StringVar()
        self.h1_var = tk.StringVar(value="1")
        self.k1_var = tk.StringVar(value="0")
        self.h2_var = tk.StringVar(value="0")
        self.k2_var = tk.StringVar(value="1")

        self.gamma_var = tk.StringVar(value="90.0")
        self.root_mode_var = tk.StringVar(value="max")
        self.a_value_var = tk.StringVar()
        self.b_value_var = tk.StringVar()
        self.gamma_value_var = tk.StringVar()
        self.solution_info_var = tk.StringVar()

        self.hmax_var = tk.StringVar(value="8")
        self.kmax_var = tk.StringVar(value="8")
        self.show_labels_var = tk.BooleanVar(value=True)
        self.show_grid_var = tk.BooleanVar(value=True)
        self.show_ring_labels_var = tk.BooleanVar(value=True)
        self.ring_label_mode_var = tk.StringVar(value="q")

        self._build_ui()
        self._update_peak_choices()
        self.fit_from_two_peaks(show_error=False, preserve_limits=False)

    # --------------------------------------------------------------
    # Window / UI
    # --------------------------------------------------------------

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

        left = ttk.Frame(outer, width=360)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        left.pack_propagate(False)

        right = ttk.Frame(outer)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_controls(left)
        self._build_plot(right)

        ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor=tk.W,
            relief=tk.SUNKEN,
            padding=(8, 4),
        ).pack(side=tk.BOTTOM, fill=tk.X)

    def _build_controls(self, parent: ttk.Frame) -> None:
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        control_frame = ttk.Frame(canvas)

        control_frame.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas_window = canvas.create_window(
            (0, 0),
            window=control_frame,
            anchor="nw",
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(
                canvas_window,
                width=event.width,
            ),
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(
            control_frame,
            text="Colob構造の逆格子編集・指数付け",
        ).pack(anchor=tk.W, pady=(2, 8))

        # 1. q values
        q_box = ttk.LabelFrame(
            control_frame,
            text="1. 実測デバイ環",
            padding=8,
        )
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
            text="qが nm⁻¹ の場合はa,b,dもnm、qが Å⁻¹ の場合はa,b,dもÅ",
            foreground="#555555",
            wraplength=325,
        ).pack(anchor=tk.W, pady=(5, 0))

        # 2. two arbitrary assignments
        fit_box = ttk.LabelFrame(
            control_frame,
            text="2. 任意の2ピークへの指数割り当て",
            padding=8,
        )
        fit_box.pack(fill=tk.X, pady=4)

        header = ttk.Frame(fit_box)
        header.pack(fill=tk.X)
        ttk.Label(header, text="").grid(row=0, column=0, padx=2)
        ttk.Label(header, text="q", anchor=tk.CENTER).grid(
            row=0, column=1, padx=2
        )
        ttk.Label(header, text="h", anchor=tk.CENTER).grid(
            row=0, column=2, padx=2
        )
        ttk.Label(header, text="k", anchor=tk.CENTER).grid(
            row=0, column=3, padx=2
        )

        row1 = ttk.Frame(fit_box)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="1st", width=7).grid(row=0, column=0, padx=2)
        self.peak1_combo = ttk.Combobox(
            row1,
            textvariable=self.peak1_var,
            state="readonly",
            width=12,
        )
        self.peak1_combo.grid(row=0, column=1, padx=2)
        ttk.Entry(row1, textvariable=self.h1_var, width=5).grid(
            row=0, column=2, padx=2
        )
        ttk.Entry(row1, textvariable=self.k1_var, width=5).grid(
            row=0, column=3, padx=2
        )

        row2 = ttk.Frame(fit_box)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="2nd", width=7).grid(row=0, column=0, padx=2)
        self.peak2_combo = ttk.Combobox(
            row2,
            textvariable=self.peak2_var,
            state="readonly",
            width=12,
        )
        self.peak2_combo.grid(row=0, column=1, padx=2)
        ttk.Entry(row2, textvariable=self.h2_var, width=5).grid(
            row=0, column=2, padx=2
        )
        ttk.Entry(row2, textvariable=self.k2_var, width=5).grid(
            row=0, column=3, padx=2
        )

        ttk.Button(
            fit_box,
            text="2ピークから格子定数 a, b を算出",
            command=self.fit_from_two_peaks,
        ).pack(fill=tk.X, pady=(5, 0))

        # 3. reciprocal lattice / gamma
        lattice_box = ttk.LabelFrame(
            control_frame,
            text="3. 逆格子",
            padding=8,
        )
        lattice_box.pack(fill=tk.X, pady=4)

        gamma_row = ttk.Frame(lattice_box)
        gamma_row.pack(fill=tk.X)

        gamma_input = ttk.Frame(gamma_row)
        gamma_input.pack(side=tk.LEFT, anchor=tk.N, padx=(0, 8))

        ttk.Label(gamma_input, text="γ（°）").pack(anchor=tk.W)
        gamma_entry = ttk.Entry(
            gamma_input,
            textvariable=self.gamma_var,
            width=9,
        )
        gamma_entry.pack(anchor=tk.W, pady=(2, 4))
        gamma_entry.bind(
            "<Return>",
            lambda _event: self.fit_from_two_peaks(
                preserve_limits=True
            ),
        )

        ttk.Button(
            gamma_input,
            text="反映",
            command=lambda: self.fit_from_two_peaks(
                preserve_limits=True
            ),
        ).pack(fill=tk.X)

        gamma_buttons = ttk.Frame(gamma_row)
        gamma_buttons.pack(side=tk.LEFT, fill=tk.X, expand=True)

        button_specs = (
            ("−1°", -1.0, 0, 0),
            ("+1°", 1.0, 0, 1),
            ("−0.1°", -0.1, 1, 0),
            ("+0.1°", 0.1, 1, 1),
        )

        for label, delta, row, column in button_specs:
            ttk.Button(
                gamma_buttons,
                text=label,
                command=lambda value=delta: self.adjust_gamma(value),
            ).grid(
                row=row,
                column=column,
                sticky="ew",
                padx=2,
                pady=2,
            )

        gamma_buttons.columnconfigure(0, weight=1)
        gamma_buttons.columnconfigure(1, weight=1)

        root_row = ttk.Frame(lattice_box)
        root_row.pack(fill=tk.X, pady=(2, 4))
        ttk.Label(root_row, text="解の選択").pack(side=tk.LEFT)
        root_combo = ttk.Combobox(
            root_row,
            textvariable=self.root_mode_var,
            values=("max", "min"),
            state="readonly",
            width=8,
        )
        root_combo.pack(side=tk.LEFT, padx=(6, 5))
        root_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.fit_from_two_peaks(
                preserve_limits=True
            ),
        )
        ttk.Button(
            root_row,
            text="γを90°に戻す",
            command=self.reset_gamma,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        result_box = ttk.Frame(lattice_box)
        result_box.pack(fill=tk.X, pady=(3, 2))

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
            textvariable=self.gamma_value_var,
        ).pack(anchor=tk.W, pady=1)
        ttk.Label(
            result_box,
            textvariable=self.solution_info_var,
            foreground="#555555",
        ).pack(anchor=tk.W, pady=(1, 3))

        ttk.Label(
            lattice_box,
            text="格子点をクリック：選択／再クリック：解除\n"
                 "Cキー：表をコピー／右クリック：全選択解除",
            foreground="#555555",
        ).pack(anchor=tk.W, pady=(3, 6))

        action_row = ttk.Frame(lattice_box)
        action_row.pack(fill=tk.X)

        ttk.Button(
            action_row,
            text="自動選択",
            command=self.auto_select_nearest,
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

        # 4. display
        display_box = ttk.LabelFrame(
            control_frame,
            text="4. 格子点表示",
            padding=8,
        )
        display_box.pack(fill=tk.X, pady=4)

        limits = ttk.Frame(display_box)
        limits.pack(fill=tk.X)
        ttk.Label(limits, text="hの最大値").grid(
            row=0, column=0, padx=2, pady=2
        )
        ttk.Entry(
            limits,
            textvariable=self.hmax_var,
            width=6,
        ).grid(row=0, column=1, padx=2, pady=2)
        ttk.Label(limits, text="kの最大値").grid(
            row=0, column=2, padx=2, pady=2
        )
        ttk.Entry(
            limits,
            textvariable=self.kmax_var,
            width=6,
        ).grid(row=0, column=3, padx=2, pady=2)

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

        display_actions = ttk.Frame(display_box)
        display_actions.pack(fill=tk.X, pady=(5, 2))

        ttk.Button(
            display_actions,
            text="再描画",
            command=self.redraw,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(
            display_actions,
            text="理論値を出力",
            command=self.print_current_results,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

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
            height=7,
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
            self.tree.column(
                column,
                width=widths[column],
                anchor=tk.CENTER,
            )

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self._remove_tree_selection)

    def _build_plot(self, parent: ttk.Frame) -> None:
        ttk.Label(
            parent,
            textvariable=self.plot_title_var,
            anchor=tk.CENTER,
        ).pack(fill=tk.X, pady=(0, 4))

        self.figure = Figure(figsize=(8.8, 7.5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(
            left=0.09,
            right=0.98,
            bottom=0.09,
            top=0.98,
        )

        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(
            self.canvas,
            parent,
            pack_toolbar=False,
        )
        toolbar.update()
        toolbar.pack(fill=tk.X)
        self.toolbar = toolbar

        self.canvas.mpl_connect(
            "button_press_event",
            self.on_mouse_press,
        )
        self.canvas.mpl_connect(
            "key_press_event",
            self.on_key_press,
        )

    # --------------------------------------------------------------
    # Input / fitting
    # --------------------------------------------------------------

    def apply_q_values(self) -> None:
        try:
            self.q_values = parse_q_values(self.q_text_var.get())
        except Exception as exc:
            messagebox.showerror(
                "q値の入力エラー",
                str(exc),
                parent=self.root,
            )
            return

        self._update_peak_choices()
        self.selected_hk.clear()
        self.fit_from_two_peaks(
            show_error=True,
            preserve_limits=False,
        )
        self.status_var.set(
            f"実測q値を{len(self.q_values)}個読み込みました。"
        )

    def _update_peak_choices(self) -> None:
        values = [self._format_q(q) for q in self.q_values]
        self.peak1_combo["values"] = values
        self.peak2_combo["values"] = values

        if values:
            if self.peak1_var.get() not in values:
                self.peak1_var.set(values[0])
            if self.peak2_var.get() not in values:
                self.peak2_var.set(values[min(1, len(values) - 1)])

    def fit_from_two_peaks(
        self,
        show_error: bool = True,
        preserve_limits: bool = False,
    ) -> bool:
        try:
            q1 = float(self.peak1_var.get())
            q2 = float(self.peak2_var.get())
            h1 = self._parse_index(self.h1_var.get(), "1stのh")
            k1 = self._parse_index(self.k1_var.get(), "1stのk")
            h2 = self._parse_index(self.h2_var.get(), "2ndのh")
            k2 = self._parse_index(self.k2_var.get(), "2ndのk")
            gamma_deg = self._parse_gamma()

            a_star, b_star, candidates = solve_oblique_reciprocal_lengths(
                q1,
                h1,
                k1,
                q2,
                h2,
                k2,
                gamma_deg,
                self.root_mode_var.get(),
            )
        except Exception as exc:
            if show_error:
                messagebox.showerror(
                    "格子定数の算出エラー",
                    str(exc),
                    parent=self.root,
                )
            return False

        self.a_star = a_star
        self.b_star = b_star
        self.solution_candidates = candidates
        self._update_result_values()
        self.redraw(preserve_limits=preserve_limits)

        q1_calc = self._q_hk(h1, k1)
        q2_calc = self._q_hk(h2, k2)
        self.status_var.set(
            "格子定数a,bの算出が完了しました："
            f"({miller_label(h1, k1)}) {q1_calc:.5f}, "
            f"({miller_label(h2, k2)}) {q2_calc:.5f}"
        )
        return True

    def adjust_gamma(self, delta: float) -> None:
        try:
            gamma = self._parse_gamma()
        except ValueError:
            gamma = 90.0

        gamma = min(
            GAMMA_MAX,
            max(GAMMA_MIN, round(gamma + delta, 1)),
        )
        self.gamma_var.set(f"{gamma:.1f}")
        self.fit_from_two_peaks(
            show_error=True,
            preserve_limits=True,
        )

    def reset_gamma(self) -> None:
        self.gamma_var.set("90.0")
        self.fit_from_two_peaks(
            show_error=True,
            preserve_limits=True,
        )

    def _update_result_values(self) -> None:
        gamma_deg = self._parse_gamma()
        sin_gamma = math.sin(math.radians(gamma_deg))

        a = TWO_PI / (self.a_star * sin_gamma)
        b = TWO_PI / (self.b_star * sin_gamma)

        self.a_value_var.set(f"a = {a:.5f}")
        self.b_value_var.set(f"b = {b:.5f}")
        self.gamma_value_var.set(f"γ = {gamma_deg:.1f}°")

        count = len(self.solution_candidates)
        if count > 1:
            self.solution_info_var.set(
                f"正の解：{count}組／使用中：{self.root_mode_var.get()}"
            )
        else:
            self.solution_info_var.set("正の解：1組")

    # --------------------------------------------------------------
    # Reciprocal lattice
    # --------------------------------------------------------------

    def _reciprocal_basis(self) -> tuple[np.ndarray, np.ndarray]:
        alpha = reciprocal_angle_rad(self._parse_gamma())
        a_vector = np.array([self.a_star, 0.0], dtype=float)
        b_vector = np.array(
            [
                self.b_star * math.cos(alpha),
                self.b_star * math.sin(alpha),
            ],
            dtype=float,
        )
        return a_vector, b_vector

    def _q_hk_vector(self, h: int, k: int) -> np.ndarray:
        a_vector, b_vector = self._reciprocal_basis()
        return h * a_vector + k * b_vector

    def _q_hk(self, h: int, k: int) -> float:
        return float(np.linalg.norm(self._q_hk_vector(h, k)))

    def _generate_visible_points(
        self,
        hmax: int,
        kmax: int,
        q_limit: float,
    ) -> list[LatticePoint]:
        points: list[LatticePoint] = []

        for h in range(0, hmax + 1):
            for k in range(-kmax, kmax + 1):
                if h == 0 and k == 0:
                    continue

                vector = self._q_hk_vector(h, k)
                x = float(vector[0])
                y = float(vector[1])
                q = math.hypot(x, y)

                if x < -1e-10:
                    continue
                if x > q_limit * 1.02 or abs(y) > q_limit * 1.02:
                    continue

                points.append(
                    LatticePoint(
                        h=h,
                        k=k,
                        q=q,
                        x=x,
                        y=y,
                    )
                )

        points.sort(key=lambda point: (point.q, point.h, point.k))
        return points

    def _draw_lattice_grid(
        self,
        hmax: int,
        kmax: int,
    ) -> None:
        a_vector, b_vector = self._reciprocal_basis()

        k_parameters = np.linspace(-kmax, kmax, 250)
        for h in range(0, hmax + 1):
            vectors = (
                h * a_vector[None, :]
                + k_parameters[:, None] * b_vector[None, :]
            )
            self.ax.plot(
                vectors[:, 0],
                vectors[:, 1],
                linewidth=0.65,
                color="#AAAAAA",
                alpha=0.40,
                zorder=0,
            )

        h_parameters = np.linspace(0, hmax, 250)
        for k in range(-kmax, kmax + 1):
            vectors = (
                h_parameters[:, None] * a_vector[None, :]
                + k * b_vector[None, :]
            )
            self.ax.plot(
                vectors[:, 0],
                vectors[:, 1],
                linewidth=0.65,
                color="#AAAAAA",
                alpha=0.40,
                zorder=0,
            )

    # --------------------------------------------------------------
    # Drawing
    # --------------------------------------------------------------

    def redraw(self, preserve_limits: bool = False) -> None:
        old_xlim = self.ax.get_xlim()
        old_ylim = self.ax.get_ylim()

        try:
            hmax, kmax = self._get_hk_max()
            gamma_deg = self._parse_gamma()
        except ValueError:
            return

        self.ax.clear()
        q_limit = self._default_q_limit()
        theta = np.linspace(-math.pi / 2.0, math.pi / 2.0, 600)

        # 実測デバイ環
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
                    label_value = TWO_PI / q
                    label_text = f"{label_value:.2f}"
                else:
                    label_text = f"{q:.2f}"

                self.ax.text(
                    q,
                    0.012 * q_limit,
                    label_text,
                    fontsize=8,
                    color=ring_color,
                    ha="center",
                    va="bottom",
                    clip_on=True,
                    zorder=2,
                )

        if self.show_grid_var.get():
            self._draw_lattice_grid(hmax, kmax)

        self.current_points = self._generate_visible_points(
            hmax,
            kmax,
            q_limit,
        )

        if self.current_points:
            self.ax.scatter(
                [point.x for point in self.current_points],
                [point.y for point in self.current_points],
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
                        f"({miller_label(point.h, point.k)})",
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

        sin_gamma = math.sin(math.radians(gamma_deg))
        a = TWO_PI / (self.a_star * sin_gamma)
        b = TWO_PI / (self.b_star * sin_gamma)

        h1 = self._safe_index(self.h1_var.get())
        k1 = self._safe_index(self.k1_var.get())
        h2 = self._safe_index(self.h2_var.get())
        k2 = self._safe_index(self.k2_var.get())

        self.plot_title_var.set(
            f"Colob構造の逆格子　"
            f"1st=({miller_label(h1, k1)})、"
            f"2nd=({miller_label(h2, k2)})　"
            f"a = {a:.5f}、b = {b:.5f}、γ = {gamma_deg:.1f}°"
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
            self.ax.set_ylim(-q_limit, q_limit)

        self.canvas.draw_idle()
        self._refresh_tree()

    # --------------------------------------------------------------
    # Selection / clipboard
    # --------------------------------------------------------------

    def on_mouse_press(self, event) -> None:
        if self._toolbar_is_active():
            return
        if event.inaxes != self.ax:
            return
        if event.xdata is None or event.ydata is None:
            return

        if event.button == 3:
            self.clear_selection()
            return
        if event.button != 1:
            return

        self._toggle_nearest_lattice_point(
            float(event.xdata),
            float(event.ydata),
        )

    def on_key_press(self, event) -> None:
        if event.key is None:
            return

        key = str(event.key).lower()
        if key == "c":
            self.copy_selected_table()
        elif key in ("escape", "delete", "backspace"):
            self.clear_selection()

    def _toggle_nearest_lattice_point(
        self,
        x: float,
        y: float,
    ) -> None:
        if not self.current_points:
            return

        nearest = min(
            self.current_points,
            key=lambda point: (
                (point.x - x) ** 2 + (point.y - y) ** 2
            ),
        )
        distance = math.hypot(
            nearest.x - x,
            nearest.y - y,
        )
        q_limit = self._default_q_limit()

        if distance > 0.035 * q_limit:
            return

        hk = (nearest.h, nearest.k)
        if hk in self.selected_hk:
            self.selected_hk.remove(hk)
            action = "選択解除"
        else:
            self.selected_hk.add(hk)
            action = "選択"

        self.redraw(preserve_limits=True)
        self.status_var.set(
            f"{action}：({miller_label(nearest.h, nearest.k, True)})"
        )

    def auto_select_nearest(self) -> None:
        if not self.current_points:
            return

        selected: set[tuple[int, int]] = set()
        for q_exp in self.q_values:
            point = min(
                self.current_points,
                key=lambda item: abs(item.q - q_exp),
            )
            selected.add((point.h, point.k))

        self.selected_hk = selected
        self.redraw(preserve_limits=True)
        self.status_var.set(
            f"実測q値{len(self.q_values)}個に最も近い逆格子点を選択しました。"
        )

    def clear_selection(self) -> None:
        self.selected_hk.clear()
        self.redraw(preserve_limits=True)
        self.status_var.set(
            "選択した逆格子点をすべて解除しました。"
        )

    def copy_selected_table(self) -> None:
        selected_points = [
            point
            for point in self.current_points
            if (point.h, point.k) in self.selected_hk
            and point.q > 0
        ]

        if not selected_points:
            self.status_var.set(
                "コピーする逆格子点が選択されていません。"
            )
            return

        selected_points.sort(
            key=lambda point: TWO_PI / point.q,
            reverse=True,
        )
        d_max = max(
            TWO_PI / point.q
            for point in selected_points
        )

        rows: list[str] = []
        for point in selected_points:
            d_value = TWO_PI / point.q
            rows.append(
                "\t".join(
                    [
                        miller_label(point.h, point.k, True),
                        str(point.h),
                        str(point.k),
                        "0",
                        f"{d_value:.6f}",
                        f"{d_value / d_max:.6f}",
                    ]
                )
            )

        text = "\n".join(rows)

        try:
            pyperclip.copy(text)
        except Exception:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
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
            q_exp, rel_error = self._nearest_experimental_peak(point.q)

            self.tree.insert(
                "",
                tk.END,
                iid=f"{point.h},{point.k}",
                values=(
                    miller_label(point.h, point.k, True),
                    f"{point.q:.4f}",
                    f"{d_calc:.4f}",
                    f"{q_exp:.4f}",
                    f"{rel_error * 100.0:.2f}",
                ),
            )

    def _remove_tree_selection(self, _event) -> None:
        for item in self.tree.selection():
            try:
                h_text, k_text = item.split(",", maxsplit=1)
                self.selected_hk.discard(
                    (int(h_text), int(k_text))
                )
            except Exception:
                continue

        self.redraw(preserve_limits=True)

    # --------------------------------------------------------------
    # Print
    # --------------------------------------------------------------

    def print_current_results(self) -> None:
        try:
            gamma_deg = self._parse_gamma()
            hmax, kmax = self._get_hk_max()
        except ValueError:
            return

        all_points: list[LatticePoint] = []
        for h in range(0, hmax + 1):
            for k in range(-kmax, kmax + 1):
                if (h, k) == (0, 0):
                    continue
                vector = self._q_hk_vector(h, k)
                q = float(np.linalg.norm(vector))
                all_points.append(
                    LatticePoint(
                        h=h,
                        k=k,
                        q=q,
                        x=float(vector[0]),
                        y=float(vector[1]),
                    )
                )

        all_points.sort(key=lambda point: (point.q, point.h, point.k))

        sin_gamma = math.sin(math.radians(gamma_deg))
        a = TWO_PI / (self.a_star * sin_gamma)
        b = TWO_PI / (self.b_star * sin_gamma)

        print("\n" + "=" * 72)
        print("Colob reciprocal-lattice calculation")
        print(f"a = {a:.6f}")
        print(f"b = {b:.6f}")
        print(f"gamma = {gamma_deg:.3f} deg")
        print(f"root mode = {self.root_mode_var.get()}")
        print(" rank    h    k      q_calc")

        shown: set[tuple[int, int]] = set()
        rank = 1

        for point in all_points:
            key = (point.h, point.k)
            if key in shown:
                continue
            shown.add(key)

            print(
                f"{rank:>4d}  {point.h:>3d}  {point.k:>3d}  "
                f"{point.q:>10.5f}"
            )
            rank += 1
            if rank > THEORY_PRINT_COUNT:
                break

        print("\nExperimental q: nearest theoretical reflection")
        print(" q_exp      h    k      q_calc      error(%)")

        for q_exp in self.q_values:
            point = min(
                all_points,
                key=lambda item: abs(item.q - q_exp),
            )
            error = abs(point.q - q_exp) / q_exp * 100.0
            print(
                f"{q_exp:8.4f}  {point.h:>3d}  {point.k:>3d}  "
                f"{point.q:>10.5f}  {error:>10.4f}"
            )

        print("=" * 72)
        self.status_var.set(
            "現在の格子定数と理論反射をTerminalへ出力しました。"
        )

    # --------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------

    def _nearest_experimental_peak(
        self,
        q_calc: float,
    ) -> tuple[float, float]:
        index = int(
            np.argmin(np.abs(self.q_values - q_calc))
        )
        q_exp = float(self.q_values[index])
        rel_error = abs(q_calc - q_exp) / q_exp
        return q_exp, rel_error

    def _default_q_limit(self) -> float:
        if len(self.q_values) == 0:
            return 5.0
        return max(
            float(np.max(self.q_values)) * 1.12,
            self.a_star * 1.3,
            self.b_star * 1.3,
            1e-6,
        )

    def _get_hk_max(self) -> tuple[int, int]:
        try:
            hmax = int(self.hmax_var.get())
            kmax = int(self.kmax_var.get())
            if not (1 <= hmax <= 100 and 1 <= kmax <= 100):
                raise ValueError
            return hmax, kmax
        except ValueError:
            messagebox.showerror(
                "指数範囲の入力エラー",
                "hとkの最大値には1～100の整数を入力してください。",
                parent=self.root,
            )
            raise ValueError

    def _parse_gamma(self) -> float:
        try:
            gamma = float(self.gamma_var.get())
        except ValueError as exc:
            raise ValueError(
                "gammaには数値を入力してください。"
            ) from exc

        if (
            not math.isfinite(gamma)
            or gamma < GAMMA_MIN
            or gamma > GAMMA_MAX
        ):
            raise ValueError(
                f"gammaには{GAMMA_MIN:.0f}～{GAMMA_MAX:.0f}°を入力してください。"
            )
        return gamma

    @staticmethod
    def _parse_index(text: str, name: str) -> int:
        try:
            return int(text)
        except ValueError as exc:
            raise ValueError(
                f"{name}には整数を入力してください。"
            ) from exc

    @staticmethod
    def _safe_index(text: str) -> int:
        try:
            return int(text)
        except Exception:
            return 0

    def _toolbar_is_active(self) -> bool:
        return bool(getattr(self.toolbar, "mode", ""))

    @staticmethod
    def _valid_limits(
        xlim: tuple[float, float],
        ylim: tuple[float, float],
    ) -> bool:
        return (
            len(xlim) == 2
            and len(ylim) == 2
            and all(
                math.isfinite(value)
                for value in (*xlim, *ylim)
            )
            and xlim[1] > xlim[0]
            and ylim[1] > ylim[0]
        )

    @staticmethod
    def _format_q(q: float) -> str:
        return f"{q:.8g}"


def main() -> None:
    root = tk.Tk()
    ColobLatticeEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
