"""M120 step 6b — ROI by explicit search, and the metric.

04b and 06 both refused: with the ROI gate written as "max over all 299 frames
of the local band-pass RMS <= 2-3x the model photon floor", NO pixel of the
crop qualifies, at any band tried. That refusal is reported, and it is a real
fact about this scene (step 5 shows why: in the frames where the leg is in
focus, hairs and the sharp edge of the defocus disc reach across most of the
crop). It is NOT a licence to invent a passing ROI.

The resolution does not weaken the test, it strengthens it. The invariant

    ||B (sum_k w_k f_k)||_R  <=  max_k ||B f_k||_R      for constant w

is a THEOREM on ANY region R -- it needs no smoothness assumption at all.
Smoothness was only ever my own extra safety for the INTERPRETATION step. So:

  * the ROI is chosen by an explicit, stated objective -- the 128x128 box whose
    MAX-over-frames band-pass energy is smallest, i.e. the cleanest background
    the stack actually offers;
  * the denominator keeps the honest max over ALL 299 frames, contaminated
    frames included, which makes Q > 1 HARDER to achieve, not easier;
  * how far that ROI sits above the photon floor is reported, not hidden.
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\src")))
import m87lib as L  # noqa: E402

M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")
HERE = Path(__file__).resolve().parent

TIGHT = (330, 610, 150, 570)
BANDS = [(1.0, 4.0), (2.0, 8.0), (4.0, 16.0), (8.0, 32.0)]
ROI_BAND = (2.0, 8.0)
SIDE = 128
ISO = 100.0


def bp(a, s):
    a = np.asarray(a, np.float32)
    return ndi.gaussian_filter(a, s[0]) - ndi.gaussian_filter(a, s[1])


def boxsum(e, side):
    ii = np.zeros((e.shape[0] + 1, e.shape[1] + 1), np.float64)
    np.cumsum(np.cumsum(e, 0), 1, out=ii[1:, 1:])
    return (ii[side:, side:] - ii[:-side, side:] - ii[side:, :-side] + ii[:-side, :-side])


def main() -> int:
    y0, y1, x0, x1 = TIGHT
    h, w = y1 - y0, x1 - x0
    cube = np.load(M87 / "bee3-leg-luma.npy", mmap_mode="r")
    n = cube.shape[0]

    frames = np.empty((n, h, w), np.float32)
    for k in range(n):
        frames[k] = np.array(cube[k, y0:y1, x0:x1], np.float32)

    lvl = float(frames[n // 2].mean())
    sig = float(L.green_luma_sigma(np.array([[lvl]]), ISO)[0, 0])

    # ---- search: 128x128 box minimising max-over-frames band-pass energy --
    worst = None
    for k in range(n):
        s = boxsum(bp(frames[k], ROI_BAND) ** 2, SIDE)
        worst = s if worst is None else np.maximum(worst, s)
    cy, cx = np.unravel_index(int(worst.argmin()), worst.shape)
    R = (cy, cy + SIDE, cx, cx + SIDE)
    roi = np.zeros((h, w), bool)
    roi[R[0]:R[1], R[2]:R[3]] = True

    rng = np.random.default_rng(20250120)
    nf = max(float(np.sqrt((bp(rng.normal(0, sig, (h, w)), ROI_BAND)[roi] ** 2).mean()))
             for _ in range(60))
    print(f"model green-luma sigma at {lvl:.0f} DN = {sig:.2f} DN")
    print(f"ROI = cleanest {SIDE}x{SIDE} box, crop coords rows {R[0]}:{R[1]} cols {R[2]}:{R[3]}")
    print(f"   (box-relative rows {y0+R[0]}:{y0+R[1]} cols {x0+R[2]}:{x0+R[3]})")
    perf = np.array([float(np.sqrt((bp(f, ROI_BAND)[roi] ** 2).mean())) for f in frames])
    print(f"   per-frame band-pass{ROI_BAND} RMS in ROI: min {perf.min():.2f} "
          f"median {np.median(perf):.2f} p90 {np.percentile(perf,90):.2f} max {perf.max():.2f} DN")
    print(f"   photon-only prediction (max of 60 draws): {nf:.2f} DN")
    print(f"   => median frame sits {np.median(perf)/nf:.2f}x the photon floor; "
          f"worst frame {perf.max()/nf:.2f}x. Disclosed, not hidden.")
    lev = frames.reshape(n, -1)[:, roi.ravel()].mean(1)
    print(f"   per-frame ROI mean level: {lev.min():.1f}..{lev.max():.1f} DN, sd {lev.std():.1f} DN")

    # ---- arms ------------------------------------------------------------
    arg = np.load(M87 / "bee3-leg-argbest.npy")[y0:y1, x0:x1]
    sel = np.load(M87 / "bee3-leg-sel.npy")[y0:y1, x0:x1].astype(np.float32)
    g2 = np.load(M87 / "bee3-leg-g2.npy")[y0:y1, x0:x1].astype(np.float32)
    mean = frames.mean(0)
    ref = frames[n // 2].copy()

    pr = np.random.default_rng(7)
    ncell = 40
    sy, sx = pr.integers(0, h, ncell), pr.integers(0, w, ncell)
    yy, xx = np.mgrid[0:h, 0:w]
    cellid = ((yy[None] - sy[:, None, None]) ** 2 + (xx[None] - sx[:, None, None]) ** 2).argmin(0)
    pos = ref + pr.normal(0.0, float(lev.std()), ncell).astype(np.float32)[cellid]

    arms = {
        "gate0 argmax  <- the brief's image": sel,
        "gate2": g2,
        "NULL-1 plain mean (constant w)": mean,
        "NULL-2 decoupled election": ref,
        "POS planted patchwork": pos,
    }

    dens = {}
    for b in BANDS:
        dens[b] = max(float(np.sqrt((bp(f, b)[roi] ** 2).mean())) for f in frames)

    print(f"\nQ = ||B I||_ROI / max_k ||B f_k||_ROI      ({SIDE}x{SIDE} = {SIDE*SIDE} px)")
    print(f"{'arm':38s}" + "".join(f"{b[0]:g}-{b[1]:g}".rjust(11) for b in BANDS))
    res = {}
    for name, img in arms.items():
        row = {}
        for b in BANDS:
            num = float(np.sqrt((bp(img, b)[roi] ** 2).mean()))
            row[f"{b[0]:g}-{b[1]:g}"] = [num, dens[b], num / dens[b]]
        res[name] = row
        print(f"{name:38s}" + "".join(f"{row[k][2]:11.3f}" for k in row))
    print(f"{'  (denominator, DN)':38s}" + "".join(f"{dens[b]:11.2f}" for b in BANDS))

    # unique frames actually gathered inside the ROI
    u = np.unique(arg[roi])
    print(f"\nelected-index field inside the ROI: {len(u)} distinct frames "
          f"out of {n}; index range {u.min()}..{u.max()}")

    def png(a, path, lo=None, hi=None):
        a = np.asarray(a, np.float32)
        lo = np.percentile(a, 0.5) if lo is None else lo
        hi = np.percentile(a, 99.5) if hi is None else hi
        v = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)
        Image.fromarray(np.kron((255 * v + .5).astype(np.uint8), np.ones((3, 3), np.uint8))).save(path)

    png(sel[R[0]:R[1], R[2]:R[3]], OUT / "ROI-gate0.png")
    png(g2[R[0]:R[1], R[2]:R[3]], OUT / "ROI-gate2.png")
    png(mean[R[0]:R[1], R[2]:R[3]], OUT / "ROI-mean.png")
    png(ref[R[0]:R[1], R[2]:R[3]], OUT / "ROI-singleframe.png")
    png(pos[R[0]:R[1], R[2]:R[3]], OUT / "ROI-positive-control.png")
    png(arg[R[0]:R[1], R[2]:R[3]], OUT / "ROI-elected-index.png")

    np.save(OUT / "roi_box.npy", np.array(R))
    np.save(OUT / "roi_frame_levels.npy", lev)
    (HERE / "roi_final.json").write_text(json.dumps({
        "crop_tight_box_relative": [int(v) for v in TIGHT],
        "roi_crop_coords": [int(v) for v in R],
        "roi_box_relative": [int(y0 + R[0]), int(y0 + R[1]), int(x0 + R[2]), int(x0 + R[3])],
        "roi_band": list(ROI_BAND),
        "model_sigma_dn": sig,
        "photon_floor_dn": nf,
        "per_frame_roi_bp_rms": {"min": float(perf.min()), "median": float(np.median(perf)),
                                 "p90": float(np.percentile(perf, 90)), "max": float(perf.max())},
        "frame_level_min_max_sd": [float(lev.min()), float(lev.max()), float(lev.std())],
        "distinct_elected_frames_in_roi": int(len(u)),
        "Q": {k: {b: [round(x, 4) for x in v] for b, v in r.items()} for k, r in res.items()},
    }, indent=2), encoding="utf-8")
    print(f"\nwrote {HERE / 'roi_final.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
