"""M38 §1 - which gradient convention did M2 use?

The estimation merge's detail invariant reports mean |grad| over a detail ROI.
Run on `109MSDCF` it gives 18.4576 DN/px on ROI 1630,1044 and 29.7240 on ROI
64,800 for the middle frame. M2-verification published 11.89 and 18.58 for the
same two ROIs on the same frames.

The ratios are 1.552 and 1.600. Both bracket pi/2 = 1.5708, which is exactly the
expected ratio of E[sqrt(dx^2+dy^2)] to E[|dx|] for an isotropic Gaussian field.
That is a mechanism hypothesis, not a finding: M2's harness is not preserved in
the repository, so it cannot be read.

So test it. Compute every plausible convention on the same data with an
INDEPENDENT implementation (rawpy + numpy, sharing no code with the Rust
pipeline) and see which one lands on M2's published numbers.

A ~2 px ROI offset is expected and accepted: rawpy's visible crop is 7028 px
wide where the Rust decoder's active area is 7032. The quantity under test is a
RATIO between conventions computed on identical pixels, so a small common offset
cannot manufacture or hide a 1.58x factor.

Writes out/01-gradient-conventions.json.
"""

import json
import pathlib

import numpy as np
import rawpy

STACK = pathlib.Path(r"D:\personal\macro\109MSDCF")
BLACK = 512.0
# (x, y, w, h) in plane coordinates, exactly as passed to `strehl merge`.
ROIS = {
    "1630,1044": (1630, 1044, 256, 256),
    "64,800": (64, 800, 256, 256),
}
# What M2-verification.md:101-103 published for the single middle frame.
M2_PUBLISHED = {"1630,1044": 11.89, "64,800": 18.58}
# What `strehl merge` measured for the same frame and ROI.
STREHL_MEASURED = {"1630,1044": 18.4576, "64,800": 29.7240}

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"


def green_plane(path):
    """Black-subtracted (G1 + G2) / 2 on the RGGB green sublattice."""
    with rawpy.imread(str(path)) as raw:
        cfa = raw.raw_image_visible.astype(np.float64)
    h, w = cfa.shape
    h -= h % 2
    w -= w % 2
    cfa = cfa[:h, :w] - BLACK
    g1 = cfa[0::2, 1::2]
    g2 = cfa[1::2, 0::2]
    return 0.5 * (g1 + g2)


def conventions(v):
    """Every gradient definition someone might reasonably have written."""
    dx = np.diff(v, axis=1)[:-1, :]
    dy = np.diff(v, axis=0)[:, :-1]
    sob_x = np.abs(v[2:, 2:] - v[2:, :-2] + 2 * (v[1:-1, 2:] - v[1:-1, :-2]) + v[:-2, 2:] - v[:-2, :-2])
    sob_y = np.abs(v[2:, 2:] - v[:-2, 2:] + 2 * (v[2:, 1:-1] - v[:-2, 1:-1]) + v[2:, :-2] - v[:-2, :-2])
    return {
        "iso_mean_sqrt_dx2_dy2": float(np.mean(np.hypot(dx, dy))),
        "mean_abs_dx_only": float(np.mean(np.abs(dx))),
        "mean_abs_dy_only": float(np.mean(np.abs(dy))),
        "mean_abs_dx_and_dy_pooled": float(np.mean(np.abs(np.concatenate([dx.ravel(), dy.ravel()])))),
        "mean_half_sum_abs": float(np.mean(0.5 * (np.abs(dx) + np.abs(dy)))),
        "rms_sqrt_dx2_dy2": float(np.sqrt(np.mean(dx**2 + dy**2))),
        "sobel_iso_over_8": float(np.mean(np.hypot(sob_x, sob_y)) / 8.0),
    }


def main():
    paths = sorted(STACK.glob("*.ARW"))
    middle = len(paths) // 2
    plane = green_plane(paths[middle])

    result = {
        "stack": str(STACK),
        "frames": len(paths),
        "middle_index": middle,
        "middle_file": paths[middle].name,
        "plane_shape_hw": list(plane.shape),
        "rois": {},
    }
    print(f"frames {len(paths)}, middle index {middle} = {paths[middle].name}")
    print(f"green plane {plane.shape} (h, w)")

    for label, (x, y, w, h) in ROIS.items():
        roi = plane[y : y + h, x : x + w]
        conv = conventions(roi)
        published = M2_PUBLISHED[label]
        rust = STREHL_MEASURED[label]
        # Which convention reproduces M2, and how closely?
        ranked = sorted(conv.items(), key=lambda kv: abs(kv[1] / published - 1.0))
        result["rois"][label] = {
            "roi_xywh": [x, y, w, h],
            "roi_mean_dn": float(roi.mean()),
            "conventions": conv,
            "m2_published": published,
            "strehl_measured": rust,
            "best_match_to_m2": ranked[0][0],
            "best_match_rel_err": abs(ranked[0][1] / published - 1.0),
            "iso_over_dx_ratio": conv["iso_mean_sqrt_dx2_dy2"] / conv["mean_abs_dx_only"],
            "python_iso_vs_rust_iso": conv["iso_mean_sqrt_dx2_dy2"] / rust,
        }
        print(f"\nROI {label}  mean {roi.mean():.1f} DN   M2 published {published}")
        for k, val in conv.items():
            print(f"   {k:28s} {val:9.4f}   x{val / published:6.3f} of M2")
        print(f"   -> closest to M2: {ranked[0][0]} ({100 * abs(ranked[0][1] / published - 1):.2f}% off)")
        print(f"   -> iso / |dx| = {conv['iso_mean_sqrt_dx2_dy2'] / conv['mean_abs_dx_only']:.4f}  (pi/2 = {np.pi / 2:.4f})")
        print(f"   -> python iso / rust iso = {conv['iso_mean_sqrt_dx2_dy2'] / rust:.4f}  (1.0 = harnesses agree)")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "01-gradient-conventions.json").write_text(json.dumps(result, indent=2))
    print(f"\nwrote {OUT / '01-gradient-conventions.json'}")


if __name__ == "__main__":
    main()
