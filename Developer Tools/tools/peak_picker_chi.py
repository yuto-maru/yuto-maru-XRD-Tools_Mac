import argparse
import os
import sys
from pathlib import Path

import matplotlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import TextBox, Button
from scipy.signal import find_peaks
import pyperclip


# === Load data (.chi) ===
def load_data(filepath, skip_rows=4):
    """
    .chi (空白 or タブ区切り) を読み込み。

    Peak PickerではError列を使用しないため、
    Error列だけがNaNの行は削除しない。
    QまたはIntensityがNaNの行だけ削除する。
    """
    data = pd.read_csv(filepath, skiprows=skip_rows, sep=r"\s+", header=None)
    data.columns = ['Q', 'Intensity', 'Error']

    before = len(data)
    data = data.dropna(subset=['Q', 'Intensity']).reset_index(drop=True)
    after = len(data)

    if after < before:
        print(
            f"Warning: removed {before - after} rows because Q or Intensity was NaN."
        )

    error_nan = int(data['Error'].isna().sum())
    if error_nan > 0:
        print(
            f"Note: {error_nan} rows have NaN in Error column. "
            "They are kept because Error is not used."
        )

    return data


# === Peak detection ===
def detect_peaks(intensity, height, distance):
    peaks, properties = find_peaks(intensity, height=height, distance=distance)
    return peaks, properties


def choose_files_by_dialog():
    """引数なしで直接起動した場合用。sample複数選択 → ref 1つ選択。"""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as e:
        print(f"tkinter dialog is not available: {e}")
        return [], None

    root = tk.Tk()
    root.withdraw()
    root.update()

    sample_files = filedialog.askopenfilenames(
        title="Sample .chi files を選択（複数選択可）",
        filetypes=[("CHI files", "*.chi"), ("All files", "*.*")],
    )
    if not sample_files:
        root.destroy()
        return [], None

    ref_file = filedialog.askopenfilename(
        title="Reference .chi file を1つ選択",
        filetypes=[("CHI files", "*.chi"), ("All files", "*.*")],
    )
    root.destroy()

    if not ref_file:
        return [], None

    return list(sample_files), ref_file


def get_files_from_args_or_dialog():
    parser = argparse.ArgumentParser(
        description="Peak picker for .chi files with reference subtraction."
    )
    parser.add_argument("sample_files", nargs="*", help="sample .chi files")
    parser.add_argument("--ref", dest="ref_file", default=None, help="reference .chi file")
    args = parser.parse_args()

    # launcher から渡された場合
    if args.sample_files and args.ref_file:
        return [str(Path(p).expanduser()) for p in args.sample_files], str(Path(args.ref_file).expanduser())

    # sampleだけ/--refだけの中途半端な指定はエラーにする
    if args.sample_files and not args.ref_file:
        print("Reference file is missing. Use: python peak_picker_chi.py --ref REF.chi sample1.chi sample2.chi")
        return [], None

    if args.ref_file and not args.sample_files:
        print("Sample files are missing. Use: python peak_picker_chi.py --ref REF.chi sample1.chi sample2.chi")
        return [], None

    # 直接実行した場合はダイアログで選ぶ
    return choose_files_by_dialog()


def main():
    chi_files, ref_path = get_files_from_args_or_dialog()

    if not chi_files:
        print("No .chi sample files selected.")
        return

    if not ref_path:
        print("No reference .chi file selected.")
        return

    chi_files = sorted(chi_files, key=lambda p: os.path.basename(p))

    print("Detected / selected .chi sample files:")
    for f in chi_files:
        print(f)

    print(f"\nReference: {ref_path}")

    # === Initial values / inherited values ===
    # Applyで変更した値は current_params に保存され、次の .chi ファイルにも引き継がれる
    current_params = {
        "scale": 1.0,
        "height": 450.0,
        "distance": 5,
    }

    ref_data = load_data(ref_path)

    instruction_text = (
        "Click index: Select / Deselect\n"
        "Press C: Copy selected peaks\n"
        "Press Q: Next file\n"
        "Press Z: Zoom to rectangle (toggle)\n"
        "Manual ON: Click curve to add/remove nearest index\n"
        "Edit boxes + Apply: Re-detect peaks"
    )

    print("\n=== Instructions ===")
    print(instruction_text)

    # === Process each sample (.chi) ===
    for sample_file in chi_files:
        sample_name = os.path.basename(sample_file)
        print(f"\nProcessing: {sample_file}")

        sample_data = load_data(sample_file)

        if len(sample_data) != len(ref_data):
            print(f"Length mismatch. Skipping: {sample_name}")
            print(f"  sample length = {len(sample_data)}")
            print(f"  ref length    = {len(ref_data)}")
            continue

        # Current parameters for this window
        # 前のファイルでApplyした値を初期値として使う
        params = current_params.copy()

        # Objects that change after recalculation
        state = {
            "diff_intensity": None,
            "peaks": np.array([], dtype=int),
            "selected": set(),
            "text_objects": {},
            "line_diff": None,
            "peak_plot": None,
            "manual_mode": False,
            "manual_indices": set(),
            "manual_artists": {},
        }

        # === Plot ===
        # 横幅を維持したままウィンドウを縦方向に拡張し、文字の重なりを防ぐ。
        fig, ax = plt.subplots(figsize=(9.6, 9.0))
        plt.subplots_adjust(left=0.08, right=0.98, top=0.84, bottom=0.19)
        # box_aspectは「高さ / 幅」。0.75でプロット枠が横:縦 = 4:3。
        ax.set_box_aspect(0.75)

        ax.set_title(sample_name)
        ax.set_xlabel("Q")
        ax.set_ylabel("Sample - scale*Ref")
        ax.grid(True)

        # === instruction text (outside plot) ===
        fig.text(
            0.01, 0.98,
            instruction_text,
            fontsize=10,
            verticalalignment='top'
        )

        # === TextBox / Button area ===
        ax_scale_label = plt.axes([0.05, 0.105, 0.22, 0.03])
        ax_scale_label.axis("off")
        ax_scale_label.text(0.0, 0.5, "Reference scale factor", fontsize=10, va="center")

        ax_scale = plt.axes([0.05, 0.055, 0.22, 0.045])
        scale_box = TextBox(ax_scale, "", initial=str(params["scale"]))

        ax_height_label = plt.axes([0.33, 0.105, 0.22, 0.03])
        ax_height_label.axis("off")
        ax_height_label.text(0.0, 0.5, "Min peak height", fontsize=10, va="center")

        ax_height = plt.axes([0.33, 0.055, 0.22, 0.045])
        height_box = TextBox(ax_height, "", initial=str(params["height"]))

        ax_distance_label = plt.axes([0.61, 0.105, 0.22, 0.03])
        ax_distance_label.axis("off")
        ax_distance_label.text(0.0, 0.5, "Peak distance", fontsize=10, va="center")

        ax_distance = plt.axes([0.61, 0.055, 0.22, 0.045])
        distance_box = TextBox(ax_distance, "", initial=str(params["distance"]))

        ax_manual = plt.axes([0.86, 0.115, 0.10, 0.045])
        manual_button = Button(ax_manual, "Manual OFF")

        ax_apply = plt.axes([0.86, 0.055, 0.10, 0.045])
        apply_button = Button(ax_apply, "Apply")

        def recalculate_and_redraw(reset_view=False):
            """Recalculate diff and peaks, then redraw peak markers/text."""
            scale = params["scale"]
            height = params["height"]
            distance = params["distance"]

            diff_intensity = sample_data['Intensity'] - scale * ref_data['Intensity']
            peaks, _ = detect_peaks(diff_intensity, height, distance)

            state["diff_intensity"] = diff_intensity
            state["peaks"] = peaks
            state["selected"] = set()
            state["text_objects"] = {}

            # Applyによる再検出時は、手動追加した点をリセットする。
            for marker, _txt in list(state["manual_artists"].values()):
                try:
                    marker.remove()
                except Exception:
                    pass
            state["manual_indices"] = set()
            state["manual_artists"] = {}

            # Main line
            if state["line_diff"] is None:
                (line_diff,) = ax.plot(sample_data['Q'], diff_intensity)
                state["line_diff"] = line_diff
            else:
                state["line_diff"].set_ydata(diff_intensity)

            # Peak markers
            if state["peak_plot"] is not None:
                state["peak_plot"].remove()
                state["peak_plot"] = None

            # Old labels
            for txt in list(ax.texts):
                txt.remove()

            if len(peaks) > 0:
                (peak_plot,) = ax.plot(
                    sample_data['Q'].iloc[peaks],
                    diff_intensity.iloc[peaks],
                    'ro'
                )
                state["peak_plot"] = peak_plot

                # Display index near peaks
                for idx in peaks:
                    q = sample_data['Q'].iloc[idx]
                    y = diff_intensity.iloc[idx]

                    txt = ax.text(
                        q, y, str(idx),
                        color='blue',
                        fontsize=9,
                        picker=True
                    )
                    state["text_objects"][txt] = idx
            else:
                print("No peaks detected with current settings.")

            ax.set_ylabel(f"Sample - {scale}*Ref")
            ax.set_title(
                f"{sample_name}   scale={scale}, height={height}, distance={distance}, peaks={len(peaks)}"
            )

            if reset_view:
                ax.relim()
                ax.autoscale_view()

            fig.canvas.draw_idle()

        def apply_settings(event=None):
            try:
                new_scale = float(scale_box.text.strip() or params["scale"])
                new_height = float(height_box.text.strip() or params["height"])
                new_distance = int(float(distance_box.text.strip() or params["distance"]))

                if new_distance < 1:
                    print("Peak distance must be >= 1.")
                    return

                params["scale"] = new_scale
                params["height"] = new_height
                params["distance"] = new_distance

                # 次のファイルにもこの値を引き継ぐ
                current_params["scale"] = new_scale
                current_params["height"] = new_height
                current_params["distance"] = new_distance

                print(
                    f"Updated: scale={new_scale}, "
                    f"height={new_height}, distance={new_distance}"
                )

                recalculate_and_redraw(reset_view=True)

            except ValueError:
                print("Invalid input. Use numbers: scale=float, height=float, distance=integer.")

        def toggle_manual_mode(_event=None):
            state["manual_mode"] = not state["manual_mode"]

            if state["manual_mode"]:
                manual_button.label.set_text("Manual ON")
                manual_button.ax.set_facecolor("#DDEEFF")
                print(
                    "Manual selection ON: click close to the curve "
                    "to add/remove the nearest data index."
                )
            else:
                manual_button.label.set_text("Manual OFF")
                manual_button.ax.set_facecolor("0.85")
                print("Manual selection OFF.")

            fig.canvas.draw_idle()

        manual_button.on_clicked(toggle_manual_mode)
        apply_button.on_clicked(apply_settings)

        # Enter in a TextBox also applies settings
        scale_box.on_submit(apply_settings)
        height_box.on_submit(apply_settings)
        distance_box.on_submit(apply_settings)

        # === Mouse click (select / deselect) ===
        def on_pick(event):
            # Manual ON中は通常のpick処理を止め、
            # 下の曲線クリック処理だけを使う。
            if state["manual_mode"]:
                return

            txt = event.artist
            if txt not in state["text_objects"]:
                return

            idx = state["text_objects"][txt]
            selected = state["selected"]

            if idx in selected:
                selected.remove(idx)
                txt.set_color('blue')
            else:
                selected.add(idx)
                txt.set_color('red')

            fig.canvas.draw_idle()

        def find_text_for_index(idx):
            for txt, mapped_idx in state["text_objects"].items():
                if mapped_idx == idx:
                    return txt
            return None

        def remove_manual_index(idx):
            artists = state["manual_artists"].pop(idx, None)
            if artists is None:
                return

            marker, txt = artists
            state["manual_indices"].discard(idx)
            state["selected"].discard(idx)
            state["text_objects"].pop(txt, None)

            try:
                marker.remove()
            except Exception:
                pass
            try:
                txt.remove()
            except Exception:
                pass

        def add_manual_index(idx):
            q = float(sample_data['Q'].iloc[idx])
            y = float(state["diff_intensity"].iloc[idx])

            (marker,) = ax.plot(
                [q],
                [y],
                marker="s",
                linestyle="None",
                markersize=6,
                color="#FF8C00",
                zorder=6,
            )
            txt = ax.text(
                q,
                y,
                str(idx),
                color="red",
                fontsize=9,
                picker=True,
                zorder=7,
            )

            state["manual_indices"].add(idx)
            state["selected"].add(idx)
            state["manual_artists"][idx] = (marker, txt)
            state["text_objects"][txt] = idx

        def on_manual_click(event):
            if not state["manual_mode"]:
                return
            if event.button != 1 or event.inaxes is not ax:
                return
            if event.x is None or event.y is None:
                return
            if state["diff_intensity"] is None:
                return

            toolbar = fig.canvas.manager.toolbar
            if toolbar is not None and getattr(toolbar, "mode", ""):
                return

            q_array = sample_data['Q'].to_numpy(dtype=float)
            y_array = state["diff_intensity"].to_numpy(dtype=float)

            # 画面上の距離で、クリック位置に最も近い曲線上の点を選ぶ。
            curve_pixels = ax.transData.transform(
                np.column_stack((q_array, y_array))
            )
            click_pixel = np.array([float(event.x), float(event.y)])
            distances = np.linalg.norm(curve_pixels - click_pixel, axis=1)
            idx = int(np.argmin(distances))

            # 曲線から離れた場所の誤クリックは無視する。
            if float(distances[idx]) > 35.0:
                print("Click closer to the plotted curve.")
                return

            if idx in state["manual_indices"]:
                remove_manual_index(idx)
                print(f"Manual index removed: {idx}")
            elif idx in set(int(i) for i in state["peaks"]):
                txt = find_text_for_index(idx)
                if txt is None:
                    return

                if idx in state["selected"]:
                    state["selected"].remove(idx)
                    txt.set_color("blue")
                    print(f"Detected index deselected: {idx}")
                else:
                    state["selected"].add(idx)
                    txt.set_color("red")
                    print(f"Detected index selected: {idx}")
            else:
                add_manual_index(idx)
                print(
                    f"Manual index added: {idx}, "
                    f"Q={q_array[idx]:.6f}"
                )

            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("pick_event", on_pick)
        fig.canvas.mpl_connect("button_press_event", on_manual_click)

        # === Keyboard actions ===
        def on_key(event):

            # COPY selected peaks
            if event.key and event.key.lower() == "c":

                selected = state["selected"]
                diff_intensity = state["diff_intensity"]
                scale = params["scale"]

                if not selected:
                    print("No peaks selected.")
                    return

                selected_sorted = sorted(selected)
                output_lines = []

                for idx in selected_sorted:

                    col0 = idx
                    col1 = sample_data['Q'].iloc[idx]
                    col2 = scale * ref_data['Intensity'].iloc[idx]
                    col3 = sample_data['Intensity'].iloc[idx]
                    col4 = diff_intensity.iloc[idx]
                    col5 = col4
                    col6 = 2 * np.pi / col1

                    line = (f"{col0}\t{col1:.6f}\t{col2:.6f}\t"
                            f"{col3:.6f}\t{col4:.6f}\t"
                            f"{col5:.6f}\t{col6:.6f}")

                    output_lines.append(line)

                text_block = "\n".join(output_lines)

                pyperclip.copy(text_block)

                print("\nCopied:\n")
                print(text_block)

            # NEXT file
            elif event.key and event.key.lower() == "q":
                # Qで次のファイルへ進む前に、入力欄の値を次回用に保存する
                try:
                    current_params["scale"] = float(scale_box.text.strip() or params["scale"])
                    current_params["height"] = float(height_box.text.strip() or params["height"])
                    current_params["distance"] = int(float(distance_box.text.strip() or params["distance"]))
                except ValueError:
                    print("Invalid input. Keeping previous settings for next file.")
                plt.close(fig)

            # ZOOM TO RECTANGLE
            elif event.key and event.key.lower() == "z":
                toolbar = fig.canvas.manager.toolbar
                if toolbar is not None:
                    toolbar.zoom()
                else:
                    print("Toolbar not available.")

        fig.canvas.mpl_connect("key_press_event", on_key)

        # Initial draw
        recalculate_and_redraw(reset_view=True)

        plt.show()

    print("\nAll files processed.")


if __name__ == "__main__":
    main()
