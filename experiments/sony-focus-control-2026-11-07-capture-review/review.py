"""Commission breathing nuisance fit, summarize local response, and render witnesses."""
import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import rawpy
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/sony-focus-control-capture-review"
HERE = Path(__file__).resolve().parent
cv2.setNumThreads(1)


def module(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    diagnostic = module("pair-response")
    inventory = json.loads((OUT / "inventory.json").read_text())
    bands = json.loads((OUT / "band-results.json").read_text())
    pairs = json.loads((OUT / "pair-response.json").read_text())
    summaries, displays = [], []
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    for run_id, run in enumerate(inventory["sessions"], 1):
        slope = bands["parameters"]["slopes"][run_id - 1]
        baseline = next(r for r in bands["records"] if r["run"] == run_id and r["ordinal"] == 1)
        centre = float(np.median([f["centre_green_px"] for f in baseline["fits"]]))
        first = np.load(OUT / "green-cfa" / f"run-{run_id}-01.npy").astype(np.float32)
        h, w = first.shape
        # A pure magnification change exceeds the local scale terms measured in
        # these adjacent pairs. This tests nuisance rejection, not lens physics.
        transform = cv2.getRotationMatrix2D((w / 2, h / 2), 0, 1.0003)
        transform[:, 2] += np.array([.12, -.08])
        scaled = cv2.warpAffine(first, transform, (w, h), flags=cv2.INTER_CUBIC,
                                borderMode=cv2.BORDER_REPLICATE)
        breathing = diagnostic.response(first, scaled, slope, centre)
        assert abs(breathing["focus_response"]) < .006, breathing

        # A separate, known spatial-blur intervention must activate the actual
        # pair operator. It does not calibrate the real lens's focus distance.
        yy, xx = np.ogrid[:h, :w]
        weight = np.clip(.5 + (yy + slope * (xx - w / 2) - centre) / 800, 0, 1).astype(np.float32)
        blurred = gaussian_filter(first, 2)
        blur_plus = diagnostic.response(first, first + weight * (blurred - first), slope, centre)
        blur_minus = diagnostic.response(first, first + (1 - weight) * (blurred - first), slope, centre)
        assert blur_plus["focus_response"] > .02, blur_plus
        assert blur_minus["focus_response"] < -.02, blur_minus

        records = pairs["runs"][run_id - 1]["pairs"]
        fine = np.array([[next(r["focus_response"] for r in records
                              if r["kind"] == "fine" and r["repeat"] == repeat and r["step"] == step)
                          for step in range(6)] for repeat in range(3)], dtype=np.float32)
        # The observed plateaus define local empirical optical increments.
        # This is descriptive and post hoc, not a hypothesis-test p-value.
        plateau = np.median(fine[:, [0, 2, 3]], axis=1)
        active = np.median(fine[:, [1, 4, 5]], axis=1)
        quantum = np.abs(active - plateau)
        native = np.array([r["focus_response"] for r in records if r["kind"] == "native"], dtype=np.float32)
        native_ratio = float(np.median(np.abs(native)) / np.median(quantum))
        shuffled = []
        rng = np.random.default_rng(4607)
        for _ in range(200):
            random_rows = np.stack([row[rng.permutation(6)] for row in fine])
            contrast = np.median(random_rows[:, [0, 2, 3]], axis=1) - np.median(random_rows[:, [1, 4, 5]], axis=1)
            shuffled.append(float(np.mean(contrast)))
        observed = float(np.mean(plateau - active))
        # Scrambling must erase the average association; the range includes
        # occasional rediscoveries of this post-hoc pattern and is reported.
        assert abs(float(np.mean(shuffled))) < observed * .25
        summary = {"run": run_id, "pure_scale_control": breathing,
                   "spatial_blur_controls": {"positive": blur_plus, "negative": blur_minus},
                   "fine_response_by_repeat": fine.tolist(), "plateau_response": plateau.tolist(),
                   "moving_response": active.tolist(), "local_response_increment": quantum.tolist(),
                   "native_response": native.tolist(), "native_to_smallest_repeatable_response_ratio": native_ratio,
                   "ratio_limit": "Local response estimate, opposite movement directions; not calibrated physical distance or resolution gain.",
                   "shuffle": {"seed": 4607, "count": 200, "observed_contrast": observed,
                               "shuffled_mean": float(np.mean(shuffled)), "shuffled_range": [min(shuffled), max(shuffled)],
                               "inference": "Descriptive order control only; pattern chosen after viewing data."}}
        summaries.append(summary)

        axis = axes[run_id - 1]
        # Normalize each run by its own median repeatable increment. Do not
        # compare absolute coefficients across subjects or exposure settings.
        normalized = -(fine - plateau[:, None]) / np.median(quantum)
        for repeat in range(3):
            axis.scatter(np.arange(6) + (repeat - 1) * .09, normalized[repeat], s=36,
                         label=f"Repeat {repeat + 1}")
        axis.scatter(np.full(len(native), 6.5), np.abs(native) / np.median(quantum), s=27,
                     marker="x", color="#444444", label="Native width 1")
        axis.axhline(0, color="#888888", linewidth=.7)
        axis.axhline(1, color="#aaaaaa", linestyle="--", linewidth=.7)
        axis.set_xticks([0, 1, 2, 3, 4, 5, 6.5], ["0→1", "1→2", "2→3", "3→4", "4→6", "6→8", "Native"])
        axis.set_xlabel("Command offsets compared")
        axis.set_title("Irregular slide" if run_id == 1 else "Regular checkerboard")
        axis.set_ylim(-.2, 4)
        axis.grid(axis="y", alpha=.15)
        axis.legend(fontsize=8, loc="upper left")
        print(f"Run {run_id}: local response ratio {native_ratio:.3f}; scale placebo {breathing['focus_response']:.6f}", flush=True)

        # Fixed transform within each run, including the fine-step witnesses.
        with rawpy.imread(run["frames"][0]["path"]) as raw:
            white_balance = list(raw.camera_whitebalance)
        origin = (3300, 2400) if run_id == 1 else (3330, 2230)
        for ordinal in [1, 9, 11, 12, 13, 15, 23, 56, 64]:
            with rawpy.imread(run["frames"][ordinal - 1]["path"]) as raw:
                rgb = raw.postprocess(demosaic_algorithm=rawpy.DemosaicAlgorithm.LINEAR,
                                      use_camera_wb=False, use_auto_wb=False, user_wb=white_balance,
                                      no_auto_bright=True, bright=4, user_black=512, user_sat=15360,
                                      output_color=rawpy.ColorSpace.sRGB, output_bps=8,
                                      gamma=(2.222, 4.5), four_color_rgb=False, user_flip=0)
            assert rgb.shape[:2] == (4688, 7028), rgb.shape
            picture = Image.fromarray(rgb)
            x, y = origin
            crop = picture.crop((x, y, x + 400, y + 400))
            crop_path = OUT / f"run-{run_id}-image-{ordinal:02d}-native.png"
            crop.save(crop_path)
            overview_path = OUT / f"run-{run_id}-image-{ordinal:02d}-fixed-overview.jpg"
            picture.thumbnail((1400, 1000), Image.Resampling.LANCZOS)
            picture.save(overview_path, quality=95)
            displays.append({"run": run_id, "ordinal": ordinal, "crop": str(crop_path),
                             "overview": str(overview_path), "origin": origin, "size": [400, 400],
                             "white_balance": white_balance, "rendered_rgb_max": int(rgb.max()),
                             "at_255_fraction": float(np.mean(rgb == 255))})
        print(f"Run {run_id}: 9 fixed-development overviews and native crops rendered", flush=True)
    axes[0].set_ylabel("Optical response / local smallest repeatable response")
    fig.suptitle("Fine focus commands: repeated plateaus and jumps\nGeometry/brightness fitted separately; not a resolution score", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "fine-focus-response.png", dpi=160)
    plt.close(fig)
    result = {"source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "workers": 1,
              "runs": summaries, "display": {"demosaic": "LibRaw LINEAR", "black": 512, "white": 15360,
              "bright": 4, "gamma": [2.222, 4.5], "auto_bright": False, "color": "sRGB", "bits": 8,
              "sharpen": "none", "wb": "fixed to first frame within each run", "records": displays}}
    (OUT / "review.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
