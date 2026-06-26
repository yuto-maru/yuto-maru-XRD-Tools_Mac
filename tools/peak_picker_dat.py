import argparse
import os
from pathlib import Path

import matplotlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import pyperclip
from matplotlib.widgets import Button, TextBox


# === Load data ===
# .dat版の読み込み条件は維持：skiprows=24, tab区切り, Q/Intensity/Error の3列

def load_data(filepath, skip_rows=24):
    data = pd.read_csv(filepath, skiprows=skip_rows, sep="\t", header=None)
    data.columns = ['Q', 'Intensity', 'Error']
    return data.dropna().reset_index(drop=True)


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
        title="Sample .dat files を選択（複数選択可）",
        filetypes=[("DAT files", "*.dat"), ("All files", "*.*")],
    )
    if not sample_files:
        root.destroy()
        return [], None

    ref_file = filedialog.askopenfilename(
        title="Reference .dat file を1つ選択",
        filetypes=[("DAT files", "*.dat"), ("All files", "*.*")],
    )
    root.destroy()

    if not ref_file:
        return [], None

    return list(sample_files), ref_file


def get_files_from_args_or_dialog():
    parser = argparse.ArgumentParser(
        description="Peak picker for .dat files with reference subtraction."
    )
    parser.add_argument("sample_files", nargs="*", help="sample .dat files")
    parser.add_argument("--ref", dest="ref_file", default=None, help="reference .dat file")
    args = parser.parse_args()

    # launcher から渡された場合
    if args.sample_files and args.ref_file:
        return [str(Path(p).expanduser()) for p in args.sample_files], str(Path(args.ref_file).expanduser())

    # sampleだけ/--refだけの中途半端な指定はエラーにする
    if args.sample_files and not args.ref_file:
        print("Reference file is missing. Use: python peak_picker_dat.py --ref REF.dat sample1.dat sample2.dat")
        return [], None

    if args.ref_file and not args.sample_files:
        print("Sample files are missing. Use: python peak_picker_dat.py --ref REF.dat sample1.dat sample2.dat")
        return [], None

    # 直接実行した場合はダイアログで選ぶ
    return choose_files_by_dialog()


def main():
    dat_files, ref_path = get_files_from_args_or_dialog()

    if not dat_files:
        print("No sample .dat files selected.")
        return

    if not ref_path:
        print("No reference .dat file selected.")
        return

    dat_files = sorted(dat_files, key=lambda p: os.path.basename(p))

    print("Detected / selected sample files:")
    for f in dat_files:
        print(f)

    print(f"\nReference: {ref_path}")

    # === Settings inherited by next file ===
    # Applyを押した時点の値が、この辞書に保存される。
    # 次のファイルでは、この値がTextBoxの初期値になる。
    settings = {
        "scale": 1.0,
        "height": 15.0,
        "distance": 5,
    }

    ref_data = load_data(ref_path)

    instruction_text = (
        "Click index: Select / Deselect\n"
        "Press C: Copy selected peaks\n"
        "Press Q: Next file\n"
        "Press Z: Zoom to rectangle (toggle)\n"
        "Edit Scale / Height / Distance, then Apply: Re-detect peaks"
    )

    print("\n=== Instructions ===")
    print(instruction_text)

    # === Loop over all sample files ===
    for sample_file in dat_files:
        sample_name = os.path.basename(sample_file)
        print(f"\nProcessing: {sample_file}")

        sample_data = load_data(sample_file)

        if len(sample_data) != len(ref_data):
            print(f"Length mismatch. Skipping: {sample_name}")
            print(f"  sample length = {len(sample_data)}")
            print(f"  ref length    = {len(ref_data)}")
            continue

        # === State for current file ===
        state = {
            "scale": settings["scale"],
            "height": settings["height"],
            "distance": settings["distance"],
            "diff_intensity": None,
            "peaks": np.array([], dtype=int),
        }

        selected = set()
        text_objects = {}
        plotted_artists = []

        # === Plot ===
        fig, ax = plt.subplots(figsize=(11, 7))
        plt.subplots_adjust(bottom=0.22, top=0.82)

        fig.text(
            0.01, 0.98,
            instruction_text,
            fontsize=10,
            verticalalignment='top'
        )

        # TextBox / Button area
        ax_scale_label = plt.axes([0.05, 0.12, 0.22, 0.03])
        ax_scale_label.axis("off")
        ax_scale_label.text(0.0, 0.5, "Reference scale factor", fontsize=10, va="center")

        ax_scale = plt.axes([0.05, 0.07, 0.22, 0.045])
        scale_box = TextBox(ax_scale, "", initial=str(state["scale"]))

        ax_height_label = plt.axes([0.33, 0.12, 0.22, 0.03])
        ax_height_label.axis("off")
        ax_height_label.text(0.0, 0.5, "Min peak height", fontsize=10, va="center")

        ax_height = plt.axes([0.33, 0.07, 0.22, 0.045])
        height_box = TextBox(ax_height, "", initial=str(state["height"]))

        ax_distance_label = plt.axes([0.61, 0.12, 0.22, 0.03])
        ax_distance_label.axis("off")
        ax_distance_label.text(0.0, 0.5, "Peak distance", fontsize=10, va="center")

        ax_distance = plt.axes([0.61, 0.07, 0.22, 0.045])
        distance_box = TextBox(ax_distance, "", initial=str(state["distance"]))

        ax_apply = plt.axes([0.86, 0.07, 0.10, 0.045])
        apply_button = Button(ax_apply, "Apply")

        def calculate_current_diff_and_peaks():
            state["diff_intensity"] = sample_data['Intensity'] - state["scale"] * ref_data['Intensity']
            state["peaks"], _ = detect_peaks(
                state["diff_intensity"],
                state["height"],
                state["distance"]
            )

        def draw_plot():
            ax.clear()
            selected.clear()
            text_objects.clear()
            plotted_artists.clear()

            diff_intensity = state["diff_intensity"]
            peaks = state["peaks"]

            ax.plot(sample_data['Q'], diff_intensity)

            if len(peaks) > 0:
                ax.plot(sample_data['Q'].iloc[peaks],
                        diff_intensity.iloc[peaks],
                        'ro')

                # === Display GLOBAL index ===
                for idx in peaks:
                    q = sample_data['Q'].iloc[idx]
                    y = diff_intensity.iloc[idx]

                    txt = ax.text(q, y, str(idx),
                                  color='blue',
                                  fontsize=9,
                                  picker=True)
                    text_objects[txt] = idx
            else:
                ax.text(
                    0.5, 0.95,
                    "No peaks detected. Change Height / Distance and Apply.",
                    transform=ax.transAxes,
                    ha="center",
                    va="top",
                    fontsize=10
                )

            ax.set_title(
                f"{sample_name}    scale={state['scale']}  height={state['height']}  distance={state['distance']}"
            )
            ax.set_xlabel("Q")
            ax.set_ylabel("Sample - scale*Ref")
            ax.grid(True)
            fig.canvas.draw_idle()

        def apply_settings(event=None):
            try:
                new_scale = float(scale_box.text.strip() or state["scale"])
                new_height = float(height_box.text.strip() or state["height"])
                new_distance = int(float(distance_box.text.strip() or state["distance"]))

                if new_distance < 1:
                    raise ValueError("Distance must be >= 1")

            except Exception as e:
                print(f"Invalid setting: {e}")
                return

            state["scale"] = new_scale
            state["height"] = new_height
            state["distance"] = new_distance

            # 次ファイルへ引き継ぐ
            settings["scale"] = new_scale
            settings["height"] = new_height
            settings["distance"] = new_distance

            calculate_current_diff_and_peaks()
            draw_plot()

            print(
                f"Applied: scale={new_scale}, height={new_height}, "
                f"distance={new_distance}, peaks={len(state['peaks'])}"
            )

        # Initial detection with inherited settings
        calculate_current_diff_and_peaks()
        draw_plot()

        apply_button.on_clicked(apply_settings)

        # Press Enter in any TextBox to apply/re-detect
        scale_box.on_submit(apply_settings)
        height_box.on_submit(apply_settings)
        distance_box.on_submit(apply_settings)

        # === Mouse click ===
        def on_pick(event):
            txt = event.artist
            if txt not in text_objects:
                return

            idx = text_objects[txt]

            if idx in selected:
                selected.remove(idx)
                txt.set_color('blue')
            else:
                selected.add(idx)
                txt.set_color('red')

            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("pick_event", on_pick)

        # === Keyboard ===
        def on_key(event):

            if event.key is None:
                return

            # COPY selected peaks
            if event.key.lower() == "c":

                if not selected:
                    print("No peaks selected.")
                    return

                selected_sorted = sorted(selected)
                diff_intensity = state["diff_intensity"]
                scale_now = state["scale"]

                output_lines = []

                for idx in selected_sorted:

                    col0 = idx
                    col1 = sample_data['Q'].iloc[idx]
                    col2 = scale_now * ref_data['Intensity'].iloc[idx]
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
            elif event.key.lower() == "q":
                # qで進んだ場合も、現在TextBoxに入っている値を次へ引き継ぐ
                apply_settings()
                plt.close(fig)

            # ZOOM TO RECTANGLE (toggle)
            elif event.key.lower() == "z":
                toolbar = fig.canvas.manager.toolbar
                if toolbar is not None:
                    toolbar.zoom()
                else:
                    print("Toolbar not available.")

        fig.canvas.mpl_connect("key_press_event", on_key)

        plt.show()

    print("\nAll files processed.")


if __name__ == "__main__":
    main()
