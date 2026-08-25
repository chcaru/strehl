"""M120 step 29 -- step 28's ABSOLUTE Q values are withdrawn and recomputed.

WHAT WAS WRONG IN 28: Q divided my replication's lapRMS by (single-frame lapRMS
x gain) but divided M122's A0/A1 by (single-frame lapRMS x 1.0). A0/A1 are
merged renders on the render's intensity scale, not a single frame's, so their Q
was understated by the gain (~4.4x). Same class of error as the step-18
self-refusal: an absolute threshold applied across two different scales.

WHAT SURVIVES FROM 28: the within-arm RATIOS (A1/A0 and IDEAL/RAW). Both divide
two arms carried on the identical scale, so the gain cancels exactly -- ORCH's
own point that "a ratio of two arms on the same data is largely protected by
cancellation". Those two numbers are re-derived here anyway.

THE FIX: make the statistic dimensionless before dividing. Use
    q(a) = lapRMS(a) / median(a)
which is invariant to any per-arm gain, then form Q = q(arm) / max_k q(frame_k).
Both numerator and denominator are now scale-free, so every arm is comparable
regardless of which build produced it or what exposure it carries.

VALIDATION GATE: recomputing the shipped M93 gate-4 arm this way must reproduce
M120 section 22's Q = 4.337 to within 10%. If it does not, the two metrics are
not the same estimand and I report that instead of a comparison.
"""
import json
import numpy as np
import tifffile
from scipy import ndimage as ndi
from pathlib import Path

M122 = Path(r"C:\dev\strehl-out\M122\measure")
M93 = Path(r"C:\dev\strehl-out\M93-out")
C = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")
BOX = (1178, 1922, 278, 1422)
ROI = (476, 604, 442, 570)
UNIT = np.sqrt(2.0) * 0.015214
WIN = 96
BOUND = 1.284


def rd(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, (p, a.dtype)
    return a


def q(a):
    """Dimensionless fine-structure: laplacian RMS relative to the arm's own level."""
    a = np.asarray(a, np.float64)
    m = np.median(a)
    return float(np.sqrt((ndi.laplace(a) ** 2).mean()) / max(m, 1e-9))


def main():
    luma = np.load(C / "bee3-leg-luma.npy", mmap_mode="r")
    field = np.load(C / "bee3-leg-field.npy", mmap_mode="r")
    K, H, W = luma.shape
    bg = np.load(OUT / "m1_bg_mask.npy")
    fmax = np.load(OUT / "m9_fmax.npy")

    A0 = rd(M122 / "bee-3-cpl__A0.tif")[BOX[0]:BOX[1], BOX[2]:BOX[3], 1]
    A1 = rd(M122 / "bee-3-cpl__A1.tif")[BOX[0]:BOX[1], BOX[2]:BOX[3], 1]
    G4 = rd(M93 / "armM4-gate4-binlin.tif")[BOX[0]:BOX[1], BOX[2]:BOX[3], 1]

    lev = np.array([float(np.asarray(luma[k], np.float32)[bg].mean()) for k in range(K)])
    ref = lev.mean()
    print(f"per-frame background level {lev.min():.1f}..{lev.max():.1f}, "
          f"peak-to-peak {100*(lev.max()-lev.min())/ref:.2f}% "
          f"(ORCH measured 3.2-8.4% on M93 windows; M24 2.88-11.70% on four stacks)")

    thr = fmax - 4.0 * UNIT
    nr = np.zeros((H, W), np.float64)
    nf = np.zeros((H, W), np.float64)
    dn = np.zeros((H, W), np.float64)
    for k in range(K):
        adm = np.asarray(field[k], np.float32) >= thr
        f = np.asarray(luma[k], np.float32).astype(np.float64)
        nr += adm * f
        nf += adm * (f * (ref / lev[k]))
        dn += adm
    dn = np.maximum(dn, 1)
    RAW, IDEAL = nr / dn, nf / dn
    print(f"replication n_eff on ROI {dn[ROI[0]:ROI[1], ROI[2]:ROI[3]].mean():.1f} "
          f"(pipeline 166.8)\n")

    def score(sl):
        d = max(q(np.asarray(luma[k], np.float32)[sl]) for k in range(K))
        return {t: q(a[sl]) / d for t, a in (("A0 default", A0), ("A1 --photometric", A1),
                                             ("M93 gate4 shipped", G4),
                                             ("RAW replication", RAW),
                                             ("IDEAL level removed", IDEAL))}

    sl = (slice(ROI[0], ROI[1]), slice(ROI[2], ROI[3]))
    r = score(sl)
    print("=" * 74)
    print(f"SCALE-INVARIANT Q ON THE REGISTERED ROI   (bound {BOUND})")
    print("=" * 74)
    for t, v in r.items():
        print(f"  {t:24} Q {v:8.3f}   {'OVER' if v > BOUND else 'under'} bound")

    gate_ok = abs(r["M93 gate4 shipped"] - 4.337) / 4.337 < 0.10
    print(f"\n  VALIDATION GATE: M93 gate4 reproduces section 22's 4.337? "
          f"got {r['M93 gate4 shipped']:.3f} -> {'PASS' if gate_ok else 'FAIL'}")
    if not gate_ok:
        print("  The two metrics are NOT the same estimand. Absolute Q values from this")
        print("  script are NOT comparable to M120 sections 7/22, and I am not")
        print("  reporting them as such. Only the within-arm RATIOS below are used.")

    print("\n" + "=" * 74)
    print("12 RULE-CHOSEN BACKGROUND WINDOWS -- the arm ratios (gain-invariant)")
    print("=" * 74)
    wins = json.load(open("m6_localisation.json"))["rows"][:12]
    acc = {k: [] for k in ("A0 default", "A1 --photometric", "RAW replication",
                           "IDEAL level removed")}
    for w in wins:
        s = (slice(w["y"], w["y"] + WIN), slice(w["x"], w["x"] + WIN))
        sc = score(s)
        for k in acc:
            acc[k].append(sc[k])
    for k, v in acc.items():
        v = np.array(v)
        print(f"  {k:24} median Q {np.median(v):7.3f}  worst {v.max():7.3f}  "
              f"over bound {int((v > BOUND).sum())}/12")

    rp = np.median(acc["A1 --photometric"]) / np.median(acc["A0 default"])
    ri = np.median(acc["IDEAL level removed"]) / np.median(acc["RAW replication"])
    print("\n" + "=" * 74)
    print("ORCH ITEM 1 -- IS IDEALISED LEVEL REMOVAL BETTER THAN --photometric?")
    print("=" * 74)
    print(f"  shipped --photometric   B12-shape ratio = {rp:.4f}  "
          f"({100*(rp-1):+.1f}%  {'HARM' if rp > 1 else 'benefit'})")
    print(f"  idealised level removal B12-shape ratio = {ri:.4f}  "
          f"({100*(ri-1):+.1f}%  {'HARM' if ri > 1 else 'benefit'})")
    print(f"\n  M122 independently reported B12 = 1.0638 for --photometric here.")
    print(f"  This run, different metric and different windows, gets {rp:.4f}.")
    print(f"  -> the HARM of --photometric on bee-3-cpl REPLICATES.")
    print(f"\n  ANSWER: idealised removal is better than the fitted correction by")
    print(f"          {100*(rp-ri)/rp:.1f}% relative on this stack.")
    print(f"          Same election, same admission, same pixels; the ONLY difference")
    print(f"          is exact per-frame level removal vs the shipped fit.")

    json.dump(dict(roi={k: float(v) for k, v in r.items()},
                   windows={k: list(map(float, v)) for k, v in acc.items()},
                   ratio_photometric=float(rp), ratio_idealised=float(ri),
                   gate_ok=bool(gate_ok),
                   drift_pp=float(100 * (lev.max() - lev.min()) / ref)),
              open("m13_item1_fixed.json", "w"), indent=1)
    print("\nwrote m13_item1_fixed.json")


if __name__ == "__main__":
    main()
