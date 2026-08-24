"""M95 arm 12b - ringing on real occluding edges, corrected instrument.

Bars R4, R5 and R6 were registered in PRE-REGISTRATION.md ADDENDUM 5 and
committed at 35c40c2 BEFORE this file existed.

ADDENDUM 4's instrument failed its own power control: it recovered 7.2% of a
planted 2000 DN ring, because `excess = max(0, A - localmax_C)` cannot report an
overshoot smaller than the local headroom `localmax_C - C`, and at an edge that
headroom is the height of the step. It is blind exactly where it was aimed.

This one measures the same exact `excess` quantity, but only on pixels where the
headroom is small and stated, so absorption cannot hide the effect:

  SENSITIVE = localmax_C - C < 200 DN and C - localmin_C < 200 DN
  NEAR      = SENSITIVE, within 2 px of a top-decile-gradient pixel, not itself one
  FAR       = SENSITIVE, more than 8 px from any top-decile-gradient pixel

The same selection is applied to both bins, so NEAR vs FAR is like-for-like.

R4 : lanczos3 NEAR excess >= 3x its FAR excess          (rule 9 flat control)
R5 : lanczos2 NEAR excess < 1/3 of lanczos3 NEAR excess (does B27 transfer)
R6 : plant +2000 DN on NEAR and recover >= 80%          (is it alive)

Every verdict is printed whichever way it falls.
"""

import json
import pathlib
import sys

import numpy as np
import tifffile

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

DST = pathlib.Path(r"C:\dev\strehl-out\M95-montage")
OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(parents=True, exist_ok=True)

REF = "catmull-rom"
CHALLENGERS = ["lanczos2", "lanczos3"]
STRIP = 1024
HALO = 12
PLANT_DN = 2000.0
HEADROOM = 200.0
NEAR_R = 2
FAR_R = 8

R4_MIN_RATIO = 3.0
R5_MAX_FRAC = 1.0 / 3.0
R6_MIN_RECOVERY = 0.80


def load16(p):
    a = tifffile.imread(str(p))
    if a.dtype != np.uint16:
        sys.exit(f"REFUSING TO MEASURE: {p.name} loaded as {a.dtype}, expected uint16.")
    return a


def luma32(a):
    return (0.2126 * a[..., 0].astype(np.float32)
            + 0.7152 * a[..., 1].astype(np.float32)
            + 0.0722 * a[..., 2].astype(np.float32))


def winmax(a, r):
    p = np.pad(a, r, mode="edge")
    return np.lib.stride_tricks.sliding_window_view(p, (2 * r + 1, 2 * r + 1)).max(axis=(-2, -1))


def winmin(a, r):
    p = np.pad(a, r, mode="edge")
    return np.lib.stride_tricks.sliding_window_view(p, (2 * r + 1, 2 * r + 1)).min(axis=(-2, -1))


def gradmag(a):
    p = np.pad(a, 1, mode="edge")
    return np.maximum(np.abs(p[2:, 1:-1] - p[:-2, 1:-1]),
                      np.abs(p[1:-1, 2:] - p[1:-1, :-2]))


def main():
    print("loading the shipping default (catmull-rom) ...")
    C = load16(DST / f"bee3-{REF}.tif")
    h, w = C.shape[:2]
    print(f"  {C.shape} {C.dtype}")

    samp = []
    for y0 in range(0, h, STRIP):
        samp.append(gradmag(luma32(C[y0:min(h, y0 + STRIP)]))[::4, ::4].ravel())
    hi_t = float(np.quantile(np.concatenate(samp), 0.90))
    del samp
    print(f"\nEDGE threshold (top decile of reference gradient): {hi_t:.0f} DN")
    print(f"SENSITIVE: local headroom below {HEADROOM:.0f} DN in both directions")
    print(f"NEAR: within {NEAR_R} px of an edge pixel   FAR: beyond {FAR_R} px\n")

    def bands(y0, y1):
        """Return (cl_core, near, far) for a strip, computed with a halo so the
        dilations are correct at strip boundaries."""
        ya, yb = max(0, y0 - HALO), min(h, y1 + HALO)
        cl = luma32(C[ya:yb])
        g = gradmag(cl)
        e = (g > hi_t).astype(np.float32)
        near_d = winmax(e, NEAR_R) > 0
        far_d = winmax(e, FAR_R) > 0
        cmax = winmax(cl, 1)
        cmin = winmin(cl, 1)
        sens = ((cmax - cl) < HEADROOM) & ((cl - cmin) < HEADROOM)
        near = sens & near_d & ~(e > 0)
        far = sens & ~far_d
        o0, o1 = y0 - ya, (y0 - ya) + (y1 - y0)
        return (cl[o0:o1], cmax[o0:o1], cmin[o0:o1],
                near[o0:o1], far[o0:o1], (ya, yb))

    def measure(arm_arr, label):
        acc = {b: [0.0, 0, 0.0] for b in ("NEAR", "FAR")}
        for y0 in range(0, h, STRIP):
            y1 = min(h, y0 + STRIP)
            cl, cmax, cmin, near, far, _ = bands(y0, y1)
            al = luma32(arm_arr[y0:y1])
            ex = np.maximum(0.0, np.maximum(al - cmax, cmin - al))
            for b, m in (("NEAR", near), ("FAR", far)):
                if m.any():
                    acc[b][0] += float(ex[m].sum())
                    acc[b][1] += int(m.sum())
                    acc[b][2] = max(acc[b][2], float(ex[m].max()))
        res = {b: {"mean_excess": acc[b][0] / max(acc[b][1], 1),
                   "max_excess": acc[b][2], "n": acc[b][1]} for b in ("NEAR", "FAR")}
        print(f"  {label}")
        print(f"    {'bin':5s} {'n px':>11s} {'mean excess DN':>16s} {'max excess DN':>15s}")
        for b in ("NEAR", "FAR"):
            r = res[b]
            print(f"    {b:5s} {r['n']:11d} {r['mean_excess']:16.2f} {r['max_excess']:15.0f}")
        return res

    print("=== EXCESS ON SENSITIVE PIXELS, NEAR vs FAR FROM EDGES ===")
    results = {}
    for arm in CHALLENGERS:
        A = load16(DST / f"bee3-{arm}.tif")
        results[arm] = measure(A, f"{arm} vs {REF}")
        del A
        print()

    print(f"=== R6 - PLANTED RING, +{PLANT_DN:.0f} DN on NEAR pixels ===")
    s, n = 0.0, 0
    for y0 in range(0, h, STRIP):
        y1 = min(h, y0 + STRIP)
        cl, cmax, cmin, near, far, _ = bands(y0, y1)
        pl = cl.copy()
        pl[near] += PLANT_DN
        ex = np.maximum(0.0, np.maximum(pl - cmax, cmin - pl))
        if near.any():
            s += float(ex[near].sum())
            n += int(near.sum())
    r6_mean = s / max(n, 1)
    r6_frac = r6_mean / PLANT_DN
    r6_ok = r6_frac >= R6_MIN_RECOVERY
    print(f"  planted on {n} NEAR pixels")
    print(f"  recovered mean NEAR excess: {r6_mean:.1f} DN ({100.0 * r6_frac:.1f}% of planted)")
    print(f"  R6 bar: recover >= {R6_MIN_RECOVERY:.0%}  ->  {'PASS' if r6_ok else 'FAIL'}")
    if not r6_ok:
        print("  This instrument is retired too and the ringing question is unanswered by me.")

    print("\n=== VERDICTS AGAINST THE REGISTERED BARS ===")
    l3, l2 = results["lanczos3"], results["lanczos2"]
    r4 = l3["NEAR"]["mean_excess"] / max(l3["FAR"]["mean_excess"], 1e-9)
    r4_ok = r4 >= R4_MIN_RATIO
    print(f"  R4  lanczos3 NEAR/FAR excess = {l3['NEAR']['mean_excess']:.2f} / "
          f"{l3['FAR']['mean_excess']:.2f} = {r4:.2f}x  (bar >= {R4_MIN_RATIO:.1f}x)"
          f"  ->  {'PASS' if r4_ok else 'FAIL'}")
    if not r4_ok:
        print("      lanczos3's overshoot does NOT concentrate near edges. By the bar I")
        print("      registered, this is not ringing and I must not call it ringing.")
    r5 = l2["NEAR"]["mean_excess"] / max(l3["NEAR"]["mean_excess"], 1e-9)
    r5_ok = r5 < R5_MAX_FRAC
    print(f"  R5  lanczos2 NEAR excess = {l2['NEAR']['mean_excess']:.2f} DN, "
          f"{r5:.3f} of lanczos3's {l3['NEAR']['mean_excess']:.2f} DN  "
          f"(bar < {R5_MAX_FRAC:.3f})  ->  {'PASS' if r5_ok else 'FAIL'}")
    if not r5_ok:
        print("      B27's synthetic step said lanczos2 rings exactly like catmull-rom.")
        print("      On real edges it does not. The synthetic step misled me.")
    print(f"  R6  {'PASS' if r6_ok else 'FAIL'}")

    rec = {"hi_t": hi_t, "headroom": HEADROOM, "results": results,
           "R4": {"ratio": r4, "bar": R4_MIN_RATIO, "pass": bool(r4_ok)},
           "R5": {"frac": r5, "bar": R5_MAX_FRAC, "pass": bool(r5_ok)},
           "R6": {"recovered": r6_mean, "frac": r6_frac, "pass": bool(r6_ok)}}
    (OUT / "x9_ringing2.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print("\nEND OF CORRECTED RINGING MEASUREMENT")


if __name__ == "__main__":
    main()
