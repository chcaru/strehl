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

# 109MSDCF is ISO 160 and 119MSDCF is ISO 50, which is the point of dumping
# both: ISO 50 is an extended (pull) ISO whose gain SYNTHESIS fact 550
# corrected by 2x, and ISO 160 is a true gain step the fix does not touch. Any
# quantity that behaves the same on both is not resting on that constant; any
# quantity that does not, is. M47 used exactly this pairing to save facts
# 461/479 when the ISO-50 column turned out to be contaminated.
STACKS = {
    "109": dict(dir=r"C:\dev\macro\test\109MSDCF", iso=160, roi=(1356, 32, 512, 512),
                # `strehl merge ... --flat-roi 1356,32,512,512`, out/a4_after.log:
                # "model predicts  : sigma    8.770 DN"
                model_sigma=8.770,
                sigma_source="out/a4_after.log, shipped CLI, ISO 160 (fact 550 does not move it)"),
    "119": dict(dir=r"C:\dev\macro\test\119MSDCF", iso=50, roi=(1396, 32, 512, 512),
                # a2_kernel_sweep.log at the SHIPPED gain max(50,100)/436.8:
                # "model sigma 6.903 -> 9.774 DN"
                model_sigma=9.774,
                sigma_source="out/a2_kernel_sweep.log at the shipped post-fact-550 gain, ISO 50"),
}


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
    for tag, info in STACKS.items():
        paths = sorted(glob.glob(os.path.join(info["dir"], "*.ARW")))
        if not paths:
            raise SystemExit(f"no ARW under {info['dir']}")
        x, y, w, h = info["roi"]

        rois = np.empty((len(paths), h, w), dtype=np.float32)
        for i, p in enumerate(paths):
            rois[i] = quad_green_roi(p, info["roi"])

        blob = os.path.join(OUT, f"a3_rois_{tag}.f32")
        rois.tofile(blob)

        header = {
            "stack": info["dir"],
            "iso": info["iso"],
            "frames": len(paths),
            "roi": {"x": x, "y": y, "w": w, "h": h},
            "black": BLACK,
            "dtype": "f32le",
            "layout": "frame-major, then row-major",
            "blob": os.path.basename(blob),
            "mean_dn": float(rois.mean()),
            "per_frame_mean_dn": [float(v) for v in rois.mean(axis=(1, 2))],
            "per_frame_raw_sd_dn": [float(v) for v in rois.std(axis=(1, 2))],
            # From the CALIBRATED NOISE MODEL, not from either statistic under
            # test. Used ONLY to label the sigma-scaled arm of the control; the
            # sigma-free arm never touches it (fact 599).
            "model_sigma_dn": info["model_sigma"],
            "model_sigma_source": info["sigma_source"],
        }
        with open(os.path.join(OUT, f"a3_rois_{tag}.json"), "w", encoding="utf-8") as f:
            json.dump(header, f, indent=2)

        print(f"wrote {blob}  {rois.nbytes} bytes")
        print(f"  ISO {info['iso']}  frames {len(paths)}  roi {info['roi']}  "
              f"mean {rois.mean():.3f} DN  model sigma {info['model_sigma']:.3f} DN")
        print("  per-frame raw sd DN: "
              + " ".join(f"{v:.2f}" for v in rois.std(axis=(1, 2))))


if __name__ == "__main__":
    main()
