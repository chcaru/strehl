"""M104 C3 -- diagnosing C2's RED, and repairing D_nyq into a meter.

C2's DOSE control went RED: D_nyq read +0.15032, +0.13109, +0.11751, +0.06074
for planted enlargements of 1.010, 1.030, 1.0735, 1.150 -- it DECREASES as the
resample gets bigger.  A metric that cannot rank doses is not a meter.

DIAGNOSIS.  Both arms were cropped to the same 384 px ROI.  An arm enlarged by
`mag` therefore covers 384/mag as much OBJECT, so the two spectra were computed
over different object extents with different object-frequency resolution, and
the band [0.30/mag, 0.48/mag] spanned a different number of FFT bins in each.
The comparison was apples-to-apples in pixels and apples-to-oranges in object
space -- which is the same class of error as measuring per-pixel sharpness on
an image that changed size, only subtler.

REPAIR.  Crop the enlarged arm to round(384 * mag) px, so both ROIs cover the
SAME OBJECT, and probe it over [0.30/mag, 0.48/mag].  The two FFTs then sample
the object-frequency axis identically and the band spans the same number of
bins in both.  Nothing else changes.

This is a refinement of an instrument, made against PLANTED doses with known
ground truth and before any post-fix number exists.  If it goes monotone, D_nyq
is a meter and the magnitude bars stand.  If it stays red, D_nyq is a detector
only -- fine for "is the resample gone?", not fine for "how big was it?" -- and
the magnitude bar must be withdrawn rather than quietly leaned on.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m104lib as L

OUT = Path(__file__).resolve().parent.parent / "out"
BASE = Path(L.RENDERS) / "flat-on-ruler-cpl-PRE-A0-g0.tif"
COLS, ROWS = 8, 6
DOSES = [1.000000, 1.010000, 1.030078, 1.073537, 1.150000]

log = []


def say(s=""):
    print(s)
    log.append(s)


def matched(ref, test, seed, mag):
    """D_nyq with the test ROI enlarged to cover the same object."""
    n_r = L.ROI
    n_t = int(round(n_r * mag))
    gr = L.roi_grid(*ref.shape, n=n_r, cols=COLS, rows=ROWS)
    gt = L.roi_grid(*test.shape, n=n_t, cols=COLS, rows=ROWS)
    out = []
    for i in sorted(seed):
        if i >= len(gr) or i >= len(gt):
            continue
        Pr, _ = L.power(L.crop(ref, gr[i], n_r))
        Pt, _ = L.power(L.crop(test, gt[i], n_t))
        cr = L.find_comb_near(Pr, seed[i]["fy"], seed[i]["fx"])
        if cr is None:
            continue
        Sr, Br, _ = L.probe(Pr, cr[0], cr[1])
        if Br <= 0 or Sr / Br < L.INERT_MIN:
            continue
        na = L.band_power_abs(Pr, L.NYQ_LO, L.NYQ_HI)
        nb = L.band_power_abs(Pt, L.NYQ_LO / mag, L.NYQ_HI / mag)
        if na and nb and na > 0 and nb > 0:
            out.append(float(np.log10(na / nb)))
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    L.ROI = 384
    a = L.green(BASE)
    seed = L.seed_combs(a, cols=COLS, rows=ROWS)

    say("=" * 78)
    say("M104 C3 -- D_nyq with matched OBJECT extent (repair of C2's RED)")
    say(f"  base : {BASE.name}  ({a.shape[1]} x {a.shape[0]})")
    say("  test ROI enlarged to round(384 * mag) so both cover the same object")
    say("=" * 78)
    say()
    say(f"{'planted':>10} {'ROI_test':>9} {'D_nyq':>10} {'SE':>8} {'sigma':>8} "
        f"{'power':>8} {'dex/%':>9}  n")

    rows_out, prev, monotone = [], None, True
    for s in DOSES:
        b = L.catmull_rom_scale(a, s)
        v = matched(a, b, seed, s)
        m = float(np.mean(v))
        se = float(np.std(v, ddof=1) / np.sqrt(len(v))) if len(v) > 1 else 0.0
        sig = m / se if se > 0 else (0.0 if m == 0 else float("inf"))
        per = m / ((s - 1) * 100) if s != 1.0 else float("nan")
        if prev is not None and not (m > prev):
            monotone = False
        prev = m
        say(f"{s:10.6f} {int(round(384*s)):9d} {m:+10.5f} {se:8.5f} {sig:8.2f} "
            f"{10**m:8.4f} {per:9.5f} {len(v):3d}")
        rows_out.append(dict(planted=s, d_nyq=m, se=se, sigma=sig,
                             per_pct=per, n=len(v)))
    say()
    null = rows_out[0]
    ok_null = abs(null["d_nyq"]) < 1e-12
    say(f"NULL   s = 1.000000 -> D_nyq = {null['d_nyq']:+.3e}   "
        f"-> {'GREEN' if ok_null else 'RED'}")
    say(f"DOSE   monotone increasing: {monotone} -> "
        f"{'GREEN -- D_nyq is a METER' if monotone else 'RED -- D_nyq is a DETECTOR only'}")
    say()
    say("NOTE ON THE NULL.  At s = 1.000 every gather offset is exactly")
    say("integer, so Catmull-Rom is the identity and D_nyq is 0 for a trivial")
    say("reason.  This control proves the code path runs; it does NOT prove the")
    say("kernel smooths.  The dose arms are what prove that.")

    res = dict(doses=rows_out, null_ok=ok_null, monotone=monotone)
    (OUT / "c3_matched.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (OUT / "c3_matched.log").write_text("\n".join(log), encoding="utf-8")


if __name__ == "__main__":
    main()
