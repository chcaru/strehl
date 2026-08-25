"""M120 step 10 — the definitive measurement.

Step 9 established, by cross-correlation at NCC = 1.0000 with zero offset, that
the M87 binned-green-luma cube and the Rust unaligned renders occupy the SAME
grid, related by a pure gain of 4.4135 (constant to 4 significant figures
across 23 independently rendered frames). So the 299-frame cube is an exact,
complete, pipeline-matched denominator for the shipped renders. Step 8's
23-frame denominator is superseded and its ROI-A numbers are retracted.

Metric, unit-free so the 4.4135 gain cancels exactly:

    C(I)  = ||B I||_ROI / mean(I)_ROI          band-pass contrast
    Q(I)  = C(I) / max_k C(f_k)                over ALL 299 input frames

For SPATIALLY CONSTANT convex weights w, ||B sum w_k f_k|| <= max_k ||B f_k||
and mean(sum w_k f_k) >= min_k mean(f_k), so

    Q <= max_k mean(f_k) / min_k mean(f_k)     -- reported below as Q_BOUND

Q above that bound is a PROOF that the merge weights varied spatially, i.e.
that the merge manufactured fine structure the inputs do not contain.
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage as ndi

M93 = Path(r"C:\dev\strehl-out\M93-out")
M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
SO = Path(r"C:\dev\strehl-out")
OUT = Path(r"C:\dev\strehl-out\M120")
HERE = Path(__file__).resolve().parent

BOX = (1178, 1922, 278, 1422)
T = (330, 610, 150, 570)
R = (146, 274, 292, 420)                         # ROI in TIGHT-crop coords
CY0, CY1 = T[0] + R[0], T[0] + R[1]              # box coords
CX0, CX1 = T[2] + R[2], T[2] + R[3]
AY0, AY1 = BOX[0] + CY0, BOX[0] + CY1            # shipped-grid absolute
AX0, AX1 = BOX[2] + CX0, BOX[2] + CX1
BANDS = [(1.0, 4.0), (2.0, 8.0), (4.0, 16.0), (8.0, 32.0)]


def bp(a, s):
    a = np.asarray(a, np.float32)
    return ndi.gaussian_filter(a, s[0]) - ndi.gaussian_filter(a, s[1])


def C(a, b):
    a = np.asarray(a, np.float32)
    return float(np.sqrt((bp(a, b) ** 2).mean()) / a.mean())


def shipg(p):
    return tifffile.imread(p)[AY0:AY1, AX0:AX1, 1].astype(np.float32)


def main() -> int:
    print(f"ROI: shipped-grid absolute rows {AY0}:{AY1} cols {AX0}:{AX1} (128x128)")
    cube = np.load(M87 / "bee3-leg-luma.npy", mmap_mode="r")
    n = cube.shape[0]
    frames = np.stack([np.array(cube[k, CY0:CY1, CX0:CX1], np.float32) for k in range(n)])
    lev = frames.reshape(n, -1).mean(1)
    Cf = {b: np.array([C(f, b) for f in frames]) for b in BANDS}
    bound = float(lev.max() / lev.min())
    print(f"299 input frames: ROI level {lev.min():.0f}..{lev.max():.0f} DN "
          f"(sd {lev.std():.0f}, {100*lev.std()/lev.mean():.2f}%)")
    print(f"Q_BOUND for any spatially constant convex weighting = {bound:.4f}")

    arms = {}
    for k, p in (("SHIPPED default, gate 4 (armM4-gate4-binlin)", M93 / "armM4-gate4-binlin.tif"),
                 ("gate 0 (armM-gate0-binlin)", M93 / "armM-gate0-binlin.tif"),
                 ("gate 0 repeat (determinism)", M93 / "armM-gate0-binlin-REPEAT.tif"),
                 ("bee3-full.tif", SO / "bee3-full.tif"),
                 ("bee3-g0.tif", SO / "bee3-g0.tif"),
                 ("bee3-g1.tif", SO / "bee3-g1.tif"),
                 ("ORCH-morning/bee-3-strehl.tif", SO / "ORCH-morning" / "bee-3-strehl.tif")):
        if p.exists():
            try:
                arms[k] = shipg(p)
            except Exception as e:                                  # noqa: BLE001
                print(f"  SKIP {p.name}: {e}")
        else:
            print(f"  MISSING {p}")
    arms["M87 python gate 0 (the brief's image)"] = np.load(M87 / "bee3-leg-sel.npy")[CY0:CY1, CX0:CX1].astype(np.float32)
    arms["M87 python gate 2"] = np.load(M87 / "bee3-leg-g2.npy")[CY0:CY1, CX0:CX1].astype(np.float32)
    arms["NULL-1 plain mean of all 299 (constant w)"] = frames.mean(0)
    arms["NULL-2 single input frame"] = frames[n // 2].copy()

    pr = np.random.default_rng(7)
    ref = frames[n // 2].copy()
    yy, xx = np.mgrid[0:128, 0:128]
    sy, sx = pr.integers(0, 128, 24), pr.integers(0, 128, 24)
    cid = ((yy[None] - sy[:, None, None]) ** 2 + (xx[None] - sx[:, None, None]) ** 2).argmin(0)
    arms["POS planted patchwork (24 cells)"] = ref + pr.normal(0, float(lev.std()), 24).astype(np.float32)[cid]

    print(f"\nQ = C(I) / max_k C(f_k)  over all {n} frames    (violation iff Q > {bound:.3f})")
    print(f"{'arm':46s}" + "".join(f"{b[0]:g}-{b[1]:g}".rjust(11) for b in BANDS) + "   verdict")
    res = {}
    for name, im in arms.items():
        q = [C(im, b) / Cf[b].max() for b in BANDS]
        v = "VIOLATES" if max(q) > bound else "ok"
        res[name] = {f"{b[0]:g}-{b[1]:g}": round(x, 4) for b, x in zip(BANDS, q)}
        print(f"{name:46s}" + "".join(f"{x:11.3f}" for x in q) + f"   {v}")
    print(f"{'  input frames: median Q':46s}"
          + "".join(f"{np.median(Cf[b])/Cf[b].max():11.3f}" for b in BANDS))
    print(f"{'  max_k C(f_k)  x1e4 (denominator)':46s}"
          + "".join(f"{1e4*Cf[b].max():11.3f}" for b in BANDS))

    lo, hi = np.percentile(frames, (0.5, 99.5))
    for name, im in arms.items():
        a = np.asarray(im, np.float32)
        a = a / (a.mean() / frames[n // 2].mean())
        v = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1) ** (1 / 2.2)
        fn = "FINAL-" + "".join(c if (c.isalnum() or c == '-') else "-" for c in name)[:40].strip("-") + ".png"
        Image.fromarray(np.kron((255 * v + .5).astype(np.uint8), np.ones((4, 4), np.uint8))).save(OUT / fn)
    print(f"\nwrote FINAL-*.png crops (common level-matched stretch {lo:.0f}..{hi:.0f}) to {OUT}")

    (HERE / "final.json").write_text(json.dumps({
        "roi_shipped_grid_abs": [AY0, AY1, AX0, AX1],
        "roi_box_coords": [CY0, CY1, CX0, CX1],
        "n_frames": int(n),
        "frame_level_min_max_sd": [float(lev.min()), float(lev.max()), float(lev.std())],
        "Q_bound_constant_weights": bound,
        "denominator_maxC_x1e4": {f"{b[0]:g}-{b[1]:g}": round(1e4 * float(Cf[b].max()), 4) for b in BANDS},
        "Q": res,
    }, indent=2), encoding="utf-8")
    print(f"wrote {HERE / 'final.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
