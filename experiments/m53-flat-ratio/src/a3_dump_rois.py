"""M53 step 3a -- dump every 109MSDCF flat ROI so the Rust control can be run
on byte-identical, REAL input.

The negative control (step 3b) has to plant a noise explosion of known size on
a REAL, STRUCTURED ROI and then ask the OLD and NEW statistics what they see.
Decoding ARW is not the part under test, so it is done once here, in the loader
whose convention step 1 already reconciled against M41's `load_two`, and the
result is handed to Rust as plain f32.  That way the Rust side exercises the
SHIPPED `strehl_core::flat_ratio` code and nothing else.

Output: out/a3_rois_109.f32   n * h * w little-endian f32, frame-major
        out/a3_rois_109.json  the header the Rust side reads

Read-only corpora are never written.  Rule 32: every rawpy view is copied
inside the `with`.
"""
import os
import glob
import json

import numpy as np
import rawpy

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
os.makedirs(OUT, exist_ok=True)

BLACK = 512.0
STACK = r"C:\dev\macro\test\109MSDCF"
ROI = (1356, 32, 512, 512)  # x, y, w, h in plane (quad) coordinates


def quad_green_roi(path, roi):
    """Black-subtracted (G1 + G2) / 2 over an ROI in plane coordinates.

    Identical convention to `strehl-cli`'s `roi_green` and to M41's
    `a2_run.load_two`: RGGB, G1 at (row 0, col 1), G2 at (row 1, col 0).
    """
    x, y, w, h = roi
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        g1 = v[2 * y:2 * (y + h):2, 2 * x + 1:2 * (x + w) + 1:2].astype(np.float32)
        g2 = v[2 * y + 1:2 * (y + h) + 1:2, 2 * x:2 * (x + w):2].astype(np.float32)
    return 0.5 * (g1 + g2) - BLACK


def main():
    paths = sorted(glob.glob(os.path.join(STACK, "*.ARW")))
    if not paths:
        raise SystemExit(f"no ARW under {STACK}")
    x, y, w, h = ROI

    rois = np.empty((len(paths), h, w), dtype=np.float32)
    for i, p in enumerate(paths):
        rois[i] = quad_green_roi(p, ROI)

    blob = os.path.join(OUT, "a3_rois_109.f32")
    rois.tofile(blob)

    header = {
        "stack": STACK,
        "frames": len(paths),
        "roi": {"x": x, "y": y, "w": w, "h": h},
        "black": BLACK,
        "dtype": "f32le",
        "layout": "frame-major, then row-major",
        "blob": os.path.basename(blob),
        "mean_dn": float(rois.mean()),
        "per_frame_mean_dn": [float(v) for v in rois.mean(axis=(1, 2))],
        "per_frame_raw_sd_dn": [float(v) for v in rois.std(axis=(1, 2))],
        # Sourced from the shipped CLI's own printed line for this stack and
        # ROI ("model predicts : sigma 8.770 DN"), i.e. from the calibrated
        # noise model, NOT from either statistic under test (rule 35).
        "model_sigma_dn": 8.770,
        "model_sigma_source": "strehl merge 109MSDCF --flat-roi 1356,32,512,512, out/a4_after.log line 72",
    }
    with open(os.path.join(OUT, "a3_rois_109.json"), "w", encoding="utf-8") as f:
        json.dump(header, f, indent=2)

    print(f"wrote {blob}  {rois.nbytes} bytes")
    print(f"frames {len(paths)}  roi {ROI}  mean {rois.mean():.3f} DN")
    print("per-frame raw sd DN: " + " ".join(f"{v:.2f}" for v in rois.std(axis=(1, 2))))


if __name__ == "__main__":
    main()
