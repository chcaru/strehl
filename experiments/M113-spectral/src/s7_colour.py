"""M113-spectral S7: the registered S6 colour bar at n=9, plus the mechanism
behind S5's apparent failure.

PART 1 -- MECHANISM. Control B (flat-on-ruler-cpl, a subject normal to the axis)
showed a single un-aligned frame agrees with its own merge to 4.8 ppm, so the
pipeline does not manufacture needed_R. The bee single-frame deficit must then be
a property of a 3D subject: only a narrow band of the field is in focus and the
rest contributes near-zero displacement that dilutes the global fit. c4_globalfit
already applies an edge-energy floor, but a floor is not a focus test. Refit the
bee single frame on its SHARPEST windows only and see whether it rises to the
merged value.

PART 2 -- S6 AS REGISTERED. Spearman rank correlation between needed_R and scene
R/G across every stack passing the S0 instrument check. The physical argument
predicts a REDDER scene needs a LARGER correction, so the correlation must be
POSITIVE. Registered in advance as weak evidence either way, because a
three-channel ratio cannot see within-passband weighting.

flat-on-ruler-cpl is added as a ninth stack AFTER the pre-registration was
written. It is labelled post-hoc throughout. It earns its place by being the only
achromatic, flat, man-made subject available, which is the widest possible
extension of the colour range, and it is subjected to the same S0 check as the
rest.
"""
import json, os, subprocess, sys
from pathlib import Path
import numpy as np
from scipy import stats

CA_SRC = r"C:\dev\blog\death-of-software\projects\strehl\experiments\M113-ca\src"
sys.path.insert(0, CA_SRC)
import c4_globalfit as c4g                        # noqa: E402
from c4_globalfit import cs, fit_eps, EPS_R       # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s2_measure import measure_ch                 # noqa: E402

EXE = Path(r"C:\dev\strehl-out\M114-ca-verify\cargo-target\release\strehl.exe")
ROOT = Path(r"C:\dev\strehl-out\M113-spectral")
MACRO = Path(r"D:\personal\macro")
CA_LIN = Path(r"C:\dev\strehl-out\M113-ca\lin")
TILE = c4g.TILE

def arm_path(stack, which):
    a = CA_LIN / ("%s-binned-%s.tif" % (stack, which))
    return a if a.exists() else ROOT / "arms" / ("%s-binned-%s.tif" % (stack, which))

def eps_of(arr, ws=None):
    H, W = arr.shape[:2]
    cx, cy = W / 2.0, H / 2.0
    if ws is None:
        ws = c4g.grid(arr, W, H)
    m = measure_ch(arr, ws, 0, cx, cy)
    return fit_eps(m, cx, cy)[0], len(ws)

def sharpness(arr, ws):
    out = []
    for (x0, y0) in ws:
        g = np.asarray(arr[y0:y0 + TILE, x0:x0 + TILE, 1]).astype(np.float32)
        out.append(float(cs.grad_mag(g).mean()))
    return np.array(out)

def scene_colour(arr):
    """Median R/G and B/G over well-exposed pixels of the OFF arm."""
    sub = np.asarray(arr[::8, ::8, :]).astype(np.float64)
    r, g, b = sub[:, :, 0], sub[:, :, 1], sub[:, :, 2]
    ok = (g > 800) & (g < 60000) & (r > 400) & (b > 400)
    return float(np.median(r[ok] / g[ok])), float(np.median(b[ok] / g[ok])), int(ok.sum())

def main():
    c4g.STEP = 100
    out = {}

    print("=" * 94)
    print("PART 1 -- why one frame of a 3D subject under-reads: refit on sharp windows only")
    print("=" * 94)
    mech = []
    for stack, merged_val in (("bee-3-cpl", 529.9), ("couch-fibers-cpl", 654.9)):
        t = ROOT / "arms" / ("%s-1frame-off.tif" % stack)
        if not t.exists():
            continue
        a, W, H = cs.load_tiff_u16(str(t))
        ws = c4g.grid(a, W, H)
        sh = sharpness(a, ws)
        row = dict(stack=stack, merged=merged_val, n_all=len(ws))
        print("\n%s   merged = %.1f ppm   windows passing the edge floor = %d"
              % (stack, merged_val, len(ws)))
        print("  %-26s %6s %14s" % ("window subset", "n", "needed_R ppm"))
        for lbl, q in (("all (as S5 ran it)", 0.0), ("sharpest 50%", 0.50),
                       ("sharpest 25%", 0.75), ("sharpest 10%", 0.90)):
            sel = [w for w, s in zip(ws, sh) if s >= np.quantile(sh, q)] if q else ws
            e, n = eps_of(a, sel)
            print("  %-26s %6d %14.1f" % (lbl, n, -e * 1e6))
            row[lbl] = dict(n=n, needed=-e * 1e6)
        mech.append(row)
        del a
    out["mechanism"] = mech

    print("\n" + "=" * 94)
    print("PART 2 -- S6 as registered: needed_R against scene R/G")
    print("=" * 94)
    known = json.load(open(ROOT / "s3_analyse.json")) if (ROOT / "s3_analyse.json").exists() else {}

    stacks = ["tweezers-cpl", "leaf-2-cpl", "bee-1-cpl", "couch-fibers-cpl", "lavendar-cpl",
              "dry-erase-marker-head-cpl", "bee-2-cpl", "bee-3-cpl"]
    rows = []
    for st in stacks + ["flat-on-ruler-cpl"]:
        off = arm_path(st, "off")
        if not off.exists():
            print("  %-28s MISSING off arm, skipped" % st); continue
        a, W, H = cs.load_tiff_u16(str(off))
        rg, bg, npx = scene_colour(a)
        k = known.get(st, {})
        nr = k.get("needed_R"); needed = None if nr is None else nr * 1e6
        transfer = k.get("transfer")
        if needed is None:
            e, _ = eps_of(a)
            needed = -e * 1e6
        del a
        if transfer is None:
            on = arm_path(st, "on")
            if on.exists():
                b, W2, H2 = cs.load_tiff_u16(str(on))
                eon, _ = eps_of(b); del b
                aa, _, _ = cs.load_tiff_u16(str(off)); eoff, _ = eps_of(aa); del aa
                transfer = (eon - eoff) / EPS_R
        rows.append(dict(stack=st, needed=needed, rg=rg, bg=bg, transfer=transfer,
                         posthoc=(st == "flat-on-ruler-cpl")))

    print("%-28s %11s %9s %9s %10s %s" % ("stack", "needed ppm", "R/G", "B/G", "transfer", "S0"))
    for r in rows:
        tr = r["transfer"]
        ok = (tr is not None) and (0.90 <= tr <= 1.02)
        print("%-28s %11.1f %9.4f %9.4f %10s %s%s"
              % (r["stack"], r["needed"], r["rg"], r["bg"],
                 ("%.4f" % tr) if tr is not None else "n/a",
                 "PASS" if ok else ("FAIL" if tr is not None else "UNDET"),
                 "   (post-hoc)" if r["posthoc"] else ""))
        r["s0"] = bool(ok)

    keep = [r for r in rows if r["s0"]]
    out["rows"] = rows
    for lbl, sel in (("pre-registered 8", [r for r in keep if not r["posthoc"]]),
                     ("with flat-on-ruler (post-hoc)", keep)):
        if len(sel) < 4:
            continue
        n = np.array([r["needed"] for r in sel]); rg = np.array([r["rg"] for r in sel])
        bg = np.array([r["bg"] for r in sel])
        rho, pv = stats.spearmanr(rg, n)
        rho2, pv2 = stats.spearmanr(bg, n)
        print("\n%s  (n=%d)" % (lbl, len(sel)))
        print("  S6 REGISTERED  needed_R vs R/G : Spearman rho = %+.4f  p = %.4f" % (rho, pv))
        print("                 needed_R vs B/G : Spearman rho = %+.4f  p = %.4f" % (rho2, pv2))
        print("  registered requirement: rho must be POSITIVE (redder scene -> larger correction)")
        print("  RESULT: %s" % ("consistent in sign" if rho > 0 else
                                "SIGN IS WRONG -- opposite to the physical prediction"))
        out[lbl] = dict(n=len(sel), rho_rg=rho, p_rg=pv, rho_bg=rho2, p_bg=pv2,
                        rg_range=[float(rg.min()), float(rg.max())],
                        needed_range=[float(n.min()), float(n.max())])
        print("  R/G spans %.4f to %.4f (%.1f%%); needed spans %.1f to %.1f ppm (%.1f%%)"
              % (rg.min(), rg.max(), 100 * (rg.max() / rg.min() - 1),
                 n.min(), n.max(), 100 * (n.max() / n.min() - 1)))

    with open(ROOT / "s7_colour.json", "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    print("\nwrote s7_colour.json")

if __name__ == "__main__":
    main()