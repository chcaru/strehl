"""M95 arm 12 - ringing on real occluding edges, full frame.

Bars R1, R2 and R3 were registered in experiments/M95-kernel/PRE-REGISTRATION.md
ADDENDUM 4 and committed at 85ee287 BEFORE this file existed. They are restated
in code below and are not edited after a result is seen.

The instrument, exactly as registered:

  excess(p) = max(0, A(p) - localmax_C(p), localmin_C(p) - A(p))

over the 3x3 neighbourhood of the shipping default C, inclusive of centre. It is
the amount by which the challenger leaves the range the default holds locally.
No model, no fitted parameter, and it compares bytes.

Pixels are binned by local gradient magnitude of C: FLAT (lowest decile), MID,
EDGE (top decile).

R1 (rule 9 flat control) : lanczos3 EDGE excess >= 3x its FLAT excess.
R2 (does B27 transfer)   : lanczos2 EDGE excess < 1/3 of lanczos3 EDGE excess.
R3 (is it alive)         : plant +2000 DN on EDGE-bin pixels of C and require the
                           recovered mean EDGE excess within 20% of 2000.

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
PLANT_DN = 2000.0

R1_MIN_RATIO = 3.0
R2_MAX_FRAC = 1.0 / 3.0
R3_TOL = 0.20


def load16(p):
    a = tifffile.imread(str(p))
    if a.dtype != np.uint16:
        sys.exit(f"REFUSING TO MEASURE: {p.name} loaded as {a.dtype}, expected uint16.")
    return a


def luma32(a):
    return (0.2126 * a[..., 0].astype(np.float32)
            + 0.7152 * a[..., 1].astype(np.float32)
            + 0.0722 * a[..., 2].astype(np.float32))


def pad1(a):
    return np.pad(a, 1, mode="edge")


def win3(a):
    return np.lib.stride_tricks.sliding_window_view(pad1(a), (3, 3))


def gradmag(a):
    p = pad1(a)
    dy = np.abs(p[2:, 1:-1] - p[:-2, 1:-1])
    dx = np.abs(p[1:-1, 2:] - p[1:-1, :-2])
    return np.maximum(dy, dx)


def strips(h):
    for y0 in range(0, h, STRIP):
        yield y0, min(h, y0 + STRIP)


def main():
    print("loading the shipping default (catmull-rom) ...")
    C = load16(DST / f"bee3-{REF}.tif")
    h, w = C.shape[:2]
    print(f"  {C.shape} {C.dtype}")

    # --- gradient deciles of the reference, from a strided sample ---
    print("\nbinning by local gradient magnitude of the reference:")
    samp = []
    for y0, y1 in strips(h):
        cl = luma32(C[y0:y1])
        samp.append(gradmag(cl)[::4, ::4].ravel())
    samp = np.concatenate(samp)
    lo_t = float(np.quantile(samp, 0.10))
    hi_t = float(np.quantile(samp, 0.90))
    print(f"  FLAT  = gradient < {lo_t:.0f} DN   (lowest decile)")
    print(f"  EDGE  = gradient > {hi_t:.0f} DN   (top decile)")
    print(f"  median gradient {np.median(samp):.0f} DN, max {samp.max():.0f} DN "
          f"({samp.size} sampled pixels)")
    del samp

    def measure(arm_arr, label):
        """Mean/max excess and mean |delta| per gradient bin. Exact, byte-based."""
        acc = {b: [0.0, 0, 0.0] for b in ("FLAT", "MID", "EDGE")}   # sum, n, max
        dacc = {b: [0.0, 0] for b in ("FLAT", "MID", "EDGE")}
        for y0, y1 in strips(h):
            cl = luma32(C[y0:y1])
            al = luma32(arm_arr[y0:y1])
            wv = win3(cl)
            cmax = wv.max(axis=(-2, -1))
            cmin = wv.min(axis=(-2, -1))
            ex = np.maximum(0.0, np.maximum(al - cmax, cmin - al))
            dl = np.abs(al - cl)
            g = gradmag(cl)
            masks = {"FLAT": g < lo_t, "EDGE": g > hi_t}
            masks["MID"] = ~(masks["FLAT"] | masks["EDGE"])
            for b, m in masks.items():
                if m.any():
                    acc[b][0] += float(ex[m].sum())
                    acc[b][1] += int(m.sum())
                    acc[b][2] = max(acc[b][2], float(ex[m].max()))
                    dacc[b][0] += float(dl[m].sum())
                    dacc[b][1] += int(m.sum())
        res = {}
        for b in ("FLAT", "MID", "EDGE"):
            s, n, mx = acc[b]
            ds, dn = dacc[b]
            res[b] = {"mean_excess": s / max(n, 1), "max_excess": mx,
                      "n": n, "mean_abs_delta": ds / max(dn, 1)}
        print(f"\n  {label}")
        print(f"    {'bin':6s} {'n px':>12s} {'mean excess DN':>16s} "
              f"{'max excess DN':>15s} {'mean |delta| DN':>17s}")
        for b in ("FLAT", "MID", "EDGE"):
            r = res[b]
            print(f"    {b:6s} {r['n']:12d} {r['mean_excess']:16.2f} "
                  f"{r['max_excess']:15.0f} {r['mean_abs_delta']:17.2f}")
        return res

    print("\n=== EXCESS BY GRADIENT BIN (registered instrument) ===")
    results = {}
    for arm in CHALLENGERS:
        A = load16(DST / f"bee3-{arm}.tif")
        results[arm] = measure(A, f"{arm} vs {REF}")
        del A

    # --- R3: plant a ring of known amplitude and try to recover it ---
    print("\n=== R3 - PLANTED RING, +2000 DN on EDGE-bin pixels of the reference ===")
    acc_sum, acc_n, planted_n = 0.0, 0, 0
    for y0, y1 in strips(h):
        cl = luma32(C[y0:y1])
        g = gradmag(cl)
        edge = g > hi_t
        pl = cl.copy()
        pl[edge] += PLANT_DN
        wv = win3(cl)
        cmax = wv.max(axis=(-2, -1))
        cmin = wv.min(axis=(-2, -1))
        ex = np.maximum(0.0, np.maximum(pl - cmax, cmin - pl))
        if edge.any():
            acc_sum += float(ex[edge].sum())
            acc_n += int(edge.sum())
            planted_n += int(edge.sum())
    r3_mean = acc_sum / max(acc_n, 1)
    r3_ok = abs(r3_mean - PLANT_DN) <= R3_TOL * PLANT_DN
    print(f"  planted {PLANT_DN:.0f} DN on {planted_n} EDGE-bin pixels")
    print(f"  recovered mean EDGE excess: {r3_mean:.1f} DN "
          f"({100.0 * r3_mean / PLANT_DN:.1f}% of planted)")
    print(f"  R3 bar: within {R3_TOL:.0%} of planted  ->  {'PASS' if r3_ok else 'FAIL'}")

    # --- verdicts ---
    print("\n=== VERDICTS AGAINST THE REGISTERED BARS ===")
    l3, l2 = results["lanczos3"], results["lanczos2"]
    r1_ratio = l3["EDGE"]["mean_excess"] / max(l3["FLAT"]["mean_excess"], 1e-9)
    r1_ok = r1_ratio >= R1_MIN_RATIO
    print(f"  R1  lanczos3 EDGE/FLAT excess = {l3['EDGE']['mean_excess']:.2f} / "
          f"{l3['FLAT']['mean_excess']:.2f} = {r1_ratio:.2f}x  "
          f"(bar >= {R1_MIN_RATIO:.1f}x)  ->  {'PASS' if r1_ok else 'FAIL'}")
    if not r1_ok:
        print("      the overshoot is NOT concentrated at edges. By the bar I registered,")
        print("      this is not ringing and I must not call it ringing.")

    r2_frac = l2["EDGE"]["mean_excess"] / max(l3["EDGE"]["mean_excess"], 1e-9)
    r2_ok = r2_frac < R2_MAX_FRAC
    print(f"  R2  lanczos2 EDGE excess = {l2['EDGE']['mean_excess']:.2f} DN, "
          f"{r2_frac:.3f} of lanczos3's {l3['EDGE']['mean_excess']:.2f} DN  "
          f"(bar < {R2_MAX_FRAC:.3f})  ->  {'PASS' if r2_ok else 'FAIL'}")
    if not r2_ok:
        print("      B27's synthetic step said lanczos2 rings exactly like catmull-rom.")
        print("      On real edges it does not. The synthetic step misled me.")
    print(f"  R3  {'PASS' if r3_ok else 'FAIL'}")

    rec = {"lo_t": lo_t, "hi_t": hi_t, "results": results,
           "R1": {"ratio": r1_ratio, "bar": R1_MIN_RATIO, "pass": bool(r1_ok)},
           "R2": {"frac": r2_frac, "bar": R2_MAX_FRAC, "pass": bool(r2_ok)},
           "R3": {"recovered": r3_mean, "planted": PLANT_DN, "pass": bool(r3_ok)}}
    (OUT / "x9_ringing.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print("\nEND OF RINGING MEASUREMENT")


if __name__ == "__main__":
    main()
