"""M87 s31g -- ORCH's acceptance gate: the rendered crop, before and after.

ORCH asked for one thing above all others:

    "Please make one of your acceptance gates a rendered 100% crop of this
     exact region, before and after, and treat it as outranking any scalar
     you compute."

The reason is on the record and it is mine: I once shipped a halo correction
whose own metric reported +72.9% while it erased the bee's abdomen hairs.
In this region the correct answer and the artifact are the same signal at the
same spatial scale -- a veil that hugs a silhouette lives exactly where the
hair detail lives -- so any metric that rewards removing background
brightness near an edge also rewards removing the hairs.

SO THE SCALARS HERE ARE DELIBERATELY NOT SHARPNESS PROXIES.  Discipline 674
forbids unreferenced gradient or Laplacian energy, and it is right to: a
Laplacian metric rated a visible polygonal winner-field mosaic 2.73x sharper
than the correct render on flowers-cpl.  Instead every number below is a
DIFFERENCE BETWEEN TWO RENDERS OF THE SAME PIXELS, which needs no proxy:

    delta = after - before

partitioned by where the pixel is.  The correction is supposed to act on
BACKGROUND near a silhouette.  Any energy it spends on SUBJECT pixels is
erasure, because there is nothing else it could be.

  BAR B12, three branches, on leakage = median |delta| on subject interior
  divided by median |delta| on near background:
      <= 0.10 -> the correction is confined to the background
      >= 0.50 -> it is eating the subject
      otherwise -> LEAKY, report the number

  BAR B13, three branches, on the veil amplitude of 90-veil.py recomputed on
  the AFTER render, against the BEFORE value:
      reduced by >= 50%  -> the correction works on the real photograph
      reduced by <= 10%  -> it does not
      otherwise -> PARTIAL

  AND THE GATE ITSELF, which outranks both: BEFORE-AFTER.png at 100%.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy import ndimage
from PIL import Image

SCRATCH = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
BEFORE = SCRATCH / "s31-bee3.tif"
AFTER = SCRATCH / "s31-bee3-FIX.tif"
X0, Y0, W, H = 700, 3150, 1100, 900
HAIR = (0, 450, 0, 550)          # y0,y1,x0,x1 within the crop: the hair mass
FARFIELD_D, WIN, MIN_FAR = 70, 251, 0.06
B12_CLEAN, B12_EATING = 0.10, 0.50
B13_WORKS, B13_NOT = 50.0, 10.0


def veil_amp(g, subj, q):
    dist = ndimage.distance_transform_edt(~subj)
    far = (dist >= FARFIELD_D) & ~subj
    m = far.astype(np.float32)
    den = ndimage.uniform_filter(m, WIN)
    ref = ndimage.uniform_filter(g * m, WIN) / np.maximum(den, 1e-6)
    valid = (den >= MIN_FAR) & ~subj
    resid = g - ref
    prof = []
    for d in range(1, 141):
        s = (dist >= d) & (dist < d + 1) & valid
        if s.sum() >= 300:
            prof.append((d, float(np.median(resid[s]))))
    base = float(np.median([v for d, v in prof if d >= FARFIELD_D]))
    pd, pv = max(((d, v) for d, v in prof if 2 <= d <= 60), key=lambda t: t[1])
    return pv - base, pd, dist


def main():
    out = {}
    b = tifffile.imread(BEFORE)[Y0:Y0 + H, X0:X0 + W].astype(np.float32)
    a = tifffile.imread(AFTER)[Y0:Y0 + H, X0:X0 + W].astype(np.float32)
    gb, ga = b[:, :, 1], a[:, :, 1]
    lo, hi = float(np.percentile(gb, 1)), float(np.percentile(gb, 99))
    med, span = float(np.median(gb)), (float(np.percentile(gb, 99)) -
                                       float(np.percentile(gb, 1))) * 0.35
    q = span / 127.0
    subj = ndimage.binary_opening(
        ndimage.binary_closing(gb < med - span, np.ones((5, 5))), np.ones((3, 3)))
    print(f"=== operand ===\n  crop {gb.shape};  one output code {q:.1f} DN")
    print(f"  BEFORE {BEFORE.name}   AFTER {AFTER.name}")

    d_all = ga - gb
    print(f"  pixels changed by the correction: "
          f"{100*float((np.abs(d_all) > 0.5).mean()):.2f}% of the crop")

    amp_b, pd_b, dist = veil_amp(gb, subj, q)
    din = ndimage.distance_transform_edt(subj)
    zones = {
        "subject interior (>10 px in)": subj & (din > 10),
        "subject edge (<=10 px in)": subj & (din <= 10),
        "background near (<=40 px)": ~subj & (dist <= 40),
        "background far (>70 px)": ~subj & (dist > 70),
    }
    print("\n=== B12  where does the correction spend its energy? ===")
    print(f"  {'zone':<30} {'n':>9} {'med |d|':>9} {'p99 |d|':>9} {'med d':>9}")
    stat = {}
    for k, m in zones.items():
        v = d_all[m]
        stat[k] = (int(m.sum()), float(np.median(np.abs(v))),
                   float(np.percentile(np.abs(v), 99)), float(np.median(v)))
        print(f"  {k:<30} {stat[k][0]:9d} {stat[k][1]:9.1f} {stat[k][2]:9.1f}"
              f" {stat[k][3]:+9.1f}")
    leak = stat["subject interior (>10 px in)"][1] / max(
        stat["background near (<=40 px)"][1], 1e-9)
    b12 = ("confined to the background" if leak <= B12_CLEAN
           else "eating the subject" if leak >= B12_EATING
           else f"LEAKY, ratio {leak:.2f}")
    print(f"  leakage = subject interior / near background = {leak:.3f}")
    print(f"  B12: {b12}")
    out["zones"] = {k: list(v) for k, v in stat.items()}
    out["leakage"] = leak
    out["B12"] = b12

    print("\n=== B13  does it remove the veil on the real photograph? ===")
    amp_a, pd_a, _ = veil_amp(ga, subj, q)
    red = 100.0 * (amp_b - amp_a) / amp_b
    print(f"  BEFORE amplitude {amp_b:+.0f} DN at d={pd_b} px")
    print(f"  AFTER  amplitude {amp_a:+.0f} DN at d={pd_a} px")
    print(f"  reduction {red:+.1f}%   (works >= {B13_WORKS:.0f}%,"
          f" fails <= {B13_NOT:.0f}%)")
    b13 = ("the correction works on the real photograph" if red >= B13_WORKS
           else "it does not" if red <= B13_NOT else "PARTIAL")
    print(f"  B13: {b13}")
    out["amp_before"] = amp_b
    out["amp_after"] = amp_a
    out["reduction_pct"] = red
    out["B13"] = b13

    # ---------------- the gate itself ------------------------------------
    def view(x):
        return np.clip(x / 257.0, 0, 255).astype(np.uint8)

    vb, va = view(b), view(a)
    dv = np.clip(d_all / (2.0 * abs(amp_b)) * 127.0 + 127.0, 0, 255).astype(np.uint8)
    dv = np.dstack([dv] * 3)
    pan = np.full((H, 3 * W + 16, 3), 30, np.uint8)
    pan[:, 0:W] = vb
    pan[:, W + 8:2 * W + 8] = va
    pan[:, 2 * W + 16:] = dv
    Image.fromarray(pan).save(SCRATCH / "BEFORE-AFTER.png")
    print(f"\n=== the gate (outranks every scalar above) ===")
    print(f"  wrote {SCRATCH / 'BEFORE-AFTER.png'}"
          f"  left BEFORE | middle AFTER | right delta +/-{2*abs(amp_b):.0f} DN")

    hy0, hy1, hx0, hx1 = HAIR
    hp_ = np.full((hy1 - hy0, 2 * (hx1 - hx0) + 8, 3), 30, np.uint8)
    hp_[:, 0:hx1 - hx0] = vb[hy0:hy1, hx0:hx1]
    hp_[:, hx1 - hx0 + 8:] = va[hy0:hy1, hx0:hx1]
    Image.fromarray(hp_).save(SCRATCH / "HAIR-100PCT.png")
    print(f"  wrote {SCRATCH / 'HAIR-100PCT.png'}  the hair mass at 100%,"
          f" BEFORE | AFTER, crop y {hy0}:{hy1} x {hx0}:{hx1}")
    out["hair_crop"] = list(HAIR)

    DATA.mkdir(exist_ok=True)
    (DATA / "91-gate.json").write_text(json.dumps(out, indent=1, default=float),
                                       encoding="utf-8")
    print(f"wrote {DATA / '91-gate.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
