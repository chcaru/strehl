"""Export small scientific comparison figures; scores always use linear DN."""

import argparse
import importlib.util
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("m194b_score", HERE / "score.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def display(rgb):
    linear = np.clip(rgb / (S.WHITE - S.BLACK), 0, 1)
    return np.where(linear <= .0031308, 12.92 * linear,
                    1.055 * linear ** (1 / 2.4) - .055)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.scores.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=False)
    crop, dims, offset = data["domain"]
    x, y = S.canonical_grid(*dims, crop["x"], crop["y"])
    window = (slice(64 - offset[1], 176 - offset[1]),
              slice(64 - offset[0], 256 - offset[0]))
    records = []
    for scene in ("flat", "plane", "color"):
        repeat = 701 if scene in ("flat", "plane") else None
        rows = {row["arm"]: row for row in data["rows"]
                if row["scene"] == scene and row["repeat"] == repeat}
        actual = []
        for arm in ("single4", "full9"):
            rgb, binding = S.read_tiff(Path(rows[arm]["tiff"]["path"]))
            if binding["file_sha256"] != rows[arm]["tiff"]["file_sha256"]:
                raise ValueError("actual plotted TIFF changed")
            actual.append(rgb)
        kind = "observation" if scene in ("flat", "plane") else "ideal"
        reference = S.target(scene, x, y, kind)
        fig, axes = plt.subplots(2, 3, figsize=(12, 5.5), constrained_layout=True)
        columns = [reference, *actual]
        titles = [f"Specified {kind} target", "Single best-focus input", "Production nine-frame merge"]
        for i, (pixels, title) in enumerate(zip(columns, titles)):
            axes[0, i].imshow(display(pixels[window]), interpolation="nearest")
            axes[0, i].set_title(title, fontsize=11)
            residual = (pixels - reference)[window][..., 1]
            im = axes[1, i].imshow(residual, cmap="RdBu_r", vmin=-50, vmax=50,
                                   interpolation="nearest")
            axes[1, i].set_title("Green error, fixed ±50 DN", fontsize=10)
            for a in axes[:, i]:
                a.set_xticks([])
                a.set_yticks([])
        fig.colorbar(im, ax=axes[1, :], shrink=.8, label="Black-subtracted camera-linear DN")
        fig.suptitle(f"M194b {scene}: fixed canonical 192×112 region"
                     + (f", noise seed {repeat}" if repeat else ", noise off"), fontsize=13)
        fig.supxlabel("Top row uses the same sRGB display curve; all measurements use original linear DN. Synthetic model only.", fontsize=9)
        path = args.out / f"{scene}-comparison.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        records.append({"path": str(path), "sha256": S.sha256(path),
                        "scene": scene, "repeat": repeat,
                        "actual_file_sha256": [rows[a]["tiff"]["file_sha256"] for a in ("single4", "full9")]})
    (args.out / "plot-receipt.json").write_text(json.dumps({
        "scores_sha256": S.sha256(args.scores), "source_sha256": S.sha256(Path(__file__)),
        "figures": records, "display_scope": "pixel-nearest scientific figure; assess detail on original192x112 crops, not scaled screenshot"}, indent=2), encoding="utf-8")
    print(json.dumps({"figures": len(records), "out": str(args.out)}))


if __name__ == "__main__":
    main()
