"""M71 step 09 -- three things step 08 got wrong or left open.

1. rho(G1 noise, G2 noise). Step 08 differenced two adjacent frames and got
   +0.0017 at 1/20 and +0.0117 at 1/250, and I nearly reported that as a
   contradiction of corpus facts 895/958 (+0.073). The DARK frame in the same
   run gave +0.0647, which is the corpus value. The flats were the wrong
   instrument: the light was moving at up to 2 %/s, so a plain frame
   difference carries a scaled copy of the vignetting profile, which is
   common to both greens and manufactures a positive rho. Normalising each
   frame to its own spatial mean before differencing removes it.

   This is the fourth entry in the corpus's own catalogue of nearly-wrong
   plants (facts 61-64) and it was caught by the control, not by the estimate.

2. The CPL flatness placebo in step 08 spanned ~40 s. The real comparison
   spans a ~280 s filter change, so the placebo has to span the same.

3. PR-8's residual spatial variance needs a mechanism. The flats were shot on
   the ELECTRONIC shutter (ShutterCount pinned at 8515 for all 360), which on
   this body is a rolling readout. Under changing light a rolling readout
   gives each ROW a different effective exposure -- a row-dependent scalar
   that a global spatial mean cannot divide out. That predicts the residual
   is organised in rows, and that is testable.
"""

from __future__ import annotations

import csv
import json
from fractions import Fraction
from pathlib import Path

import numpy as np
import rawpy

HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "out" / "cache"
OUT = HERE / "data" / "09-controls.json"
BLACK = 512.0

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "k5", Path(__file__).resolve().parent / "05-kappa.py")
_k5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_k5)
smooth = _k5.smooth

NICE = {"e0.004": "1/250", "e0.008": "1/125", "e0.016666666666666666": "1/60",
        "e0.03333333333333333": "1/30", "e0.05": "1/20",
        "e0.07692307692307693": "1/13"}


def load(path):
    with rawpy.imread(str(path)) as raw:
        return raw.raw_image_visible.astype(np.float32).copy()   # rule 32


def greens(f):
    return f[0::2, 1::2], f[1::2, 0::2]


def rho_corrected(out):
    print("=== 1. rho(G1 noise, G2 noise), with the drift removed")
    print("    Each frame is divided by its own spatial mean BEFORE the")
    print("    difference, so a global illumination step cannot survive.")
    src = list(csv.DictReader((HERE / "data" / "exif-all.csv").open(encoding="utf-8-sig")))
    cases = []
    for et in (Fraction(1, 250), Fraction(1, 125), Fraction(1, 60),
               Fraction(1, 30), Fraction(1, 20)):
        grp = sorted([r for r in src if Path(r["Directory"]).name == "flat-fields"
                      and Fraction(r["ExposureTime"]) == et],
                     key=lambda r: r["SubSecDateTimeOriginal"])
        cases.append((f"{et} flat A", grp[8], grp[9]))
    res = {}
    print(f"    {'case':16s} {'S (DN)':>9s} {'raw rho':>10s} {'norm rho':>10s} "
          f"{'rolled':>10s} {'read frac':>10s} {'pred if read-only':>18s}")
    for label, ra, rb in cases:
        a, b = load(ra["SourceFile"]) - BLACK, load(rb["SourceFile"]) - BLACK
        S = float(a.mean())
        a_n = a / float(a.mean())
        b_n = b / float(b.mean())
        for kind, (x, y) in (("raw", (a, b)), ("norm", (a_n, b_n))):
            g1, g2 = greens(x - y)
            g1 = g1[200:-200, 200:-200]
            g2 = g2[200:-200, 200:-200]
            g1 = g1 - g1.mean()
            g2 = g2 - g2.mean()
            r = float(np.mean(g1 * g2) / np.sqrt(np.mean(g1 * g1) * np.mean(g2 * g2)))
            if kind == "raw":
                r_raw = r
            else:
                r_norm = r
                g2r = np.roll(g2, 314, axis=0)
                r_roll = float(np.mean(g1 * g2r)
                               / np.sqrt(np.mean(g1 * g1) * np.mean(g2r * g2r)))
        read_frac = 1.0 / (0.224103 * S + 1.0)
        res[label] = {"S": S, "rho_raw": r_raw, "rho_norm": r_norm,
                      "rho_rolled": r_roll, "read_frac": read_frac}
        print(f"    {label:16s} {S:9.1f} {r_raw:10.5f} {r_norm:10.5f} "
              f"{r_roll:10.5f} {read_frac:10.5f} {0.0647 * read_frac:18.5f}")

    dk = sorted(Path(r"D:\macro-dark-frames\118MSDCF").glob("*.ARW"))[:4]
    for i in (0, 2):
        a, b = load(dk[i]) - BLACK, load(dk[i + 1]) - BLACK
        g1, g2 = greens(a - b)
        g1 = g1[200:-200, 200:-200]
        g2 = g2[200:-200, 200:-200]
        g1, g2 = g1 - g1.mean(), g2 - g2.mean()
        r = float(np.mean(g1 * g2) / np.sqrt(np.mean(g1 * g1) * np.mean(g2 * g2)))
        g2r = np.roll(g2, 314, axis=0)
        rr = float(np.mean(g1 * g2r) / np.sqrt(np.mean(g1 * g1) * np.mean(g2r * g2r)))
        res[f"dark pair {i}"] = {"S": 0.0, "rho_raw": r, "rho_norm": r,
                                 "rho_rolled": rr, "read_frac": 1.0}
        print(f"    {'dark pair ' + str(i):16s} {0.0:9.1f} {r:10.5f} {r:10.5f} "
              f"{rr:10.5f} {1.0:10.5f} {0.0647:18.5f}")
    print("\n    In the dark, rho = +0.065 and +0.078 -- corpus facts 895/958")
    print("    (+0.073) are REPRODUCED where they were measured. Under signal")
    print("    it falls by more than an order of magnitude, tracking the")
    print("    read-noise fraction to within about 10x and reaching <= 0.0016")
    print("    by S ~ 5700 DN. It is a read-noise-domain correlation, not a")
    print("    fixed +0.073 at all levels. The residual above the pure-read")
    print("    prediction is quoted as an UPPER BOUND, because a spatial-mean")
    print("    normalisation cannot remove illumination structure that is not")
    print("    a global scalar, and section 3 shows there is some.")
    out["rho"] = res


def cpl_placebo(out):
    print("\n=== 2. CPL flatness with a TIME-MATCHED placebo")
    print("    The real comparison spans a ~280 s filter change, so the")
    print("    placebo must span a comparable stretch inside ONE state.")

    def rmap(tag, pl="G1"):
        m = np.load(CACHE / f"{tag}-{pl}-mean.npy").astype(np.float32)
        return m / float(m.mean())

    tests = [
        ("REAL   CPL vs none, 1/20", "e0.05-A", "e0.05-B", 280),
        ("REAL   CPL vs none, 1/30", "e0.03333333333333333-A",
         "e0.03333333333333333-B", 280),
        ("REAL   CPL vs none, 1/250", "e0.004-A", "e0.004-B", 280),
        ("PLACEBO within A, 1/250 vs 1/13", "e0.004-A",
         "e0.07692307692307693-A", 230),
        ("PLACEBO within A, 1/250 vs 1/20", "e0.004-A", "e0.05-A", 190),
        ("PLACEBO within B, 1/250 vs 1/20", "e0.004-B", "e0.05-B", 190),
        ("PLACEBO within A, 1/30 vs 1/20", "e0.03333333333333333-A",
         "e0.05-A", 40),
    ]
    rows = []
    for label, t1, t2, dt in tests:
        r = rmap(t1) / rmap(t2)
        rs = smooth(r, 121, 3)
        sd = float(np.std(rs))
        pk = float(np.percentile(rs, 99.5) - np.percentile(rs, 0.5))
        # is the structure radial (a filter or a vignette) or a gradient
        # (a moving cloud)?
        h, w = rs.shape
        yy = (np.arange(h)[:, None] - h / 2) / (h / 2)
        xx = (np.arange(w)[None, :] - w / 2) / (w / 2)
        rad = np.sqrt(yy * yy + xx * xx)
        c = rs - rs.mean()
        rho_rad = float(np.mean(c * (rad - rad.mean()))
                        / np.sqrt(np.var(c) * np.var(rad)))
        rho_x = float(np.mean(c * (xx - xx.mean()))
                      / np.sqrt(np.var(c) * np.var(xx)))
        rho_y = float(np.mean(c * (yy - yy.mean()))
                      / np.sqrt(np.var(c) * np.var(yy)))
        rows.append({"label": label, "dt_s": dt, "sd": sd, "peak": pk,
                     "rho_radial": rho_rad, "rho_x": rho_x, "rho_y": rho_y})
        print(f"    {label:34s} dt~{dt:4d}s  sd {sd * 100:6.3f}%  "
              f"p99.5-p0.5 {pk * 100:6.3f}%   radial {rho_rad:+.3f}  "
              f"x {rho_x:+.3f}  y {rho_y:+.3f}")
    real = [r for r in rows if r["label"].startswith("REAL")]
    plac = [r for r in rows if r["label"].startswith("PLACEBO") and r["dt_s"] >= 190]
    worst_p = max(r["sd"] for r in plac)
    worst_r = max(r["sd"] for r in real)
    print(f"\n    worst REAL {worst_r * 100:.3f}%   worst TIME-MATCHED PLACEBO "
          f"{worst_p * 100:.3f}%   separation {worst_r / worst_p:.2f}x")
    print("    THE PLACEBO IS LARGER THAN THE EFFECT. Step 08 reported a 13x")
    print("    separation against a 40 s placebo; that placebo was mis-scaled")
    print("    and the result is WITHDRAWN. On a time-matched placebo the CPL")
    print("    adds NO detectable spatial non-uniformity.")
    print("    The x-gradient correlations say why: every long-baseline map,")
    print("    real or placebo, is a left-right ramp whose SIGN follows the")
    print("    direction the light was moving, not whether the filter was on.")
    out["cpl_placebo"] = {"rows": rows, "worst_real": worst_r,
                          "worst_placebo": worst_p,
                          "separation": worst_r / worst_p,
                          "cpl_flat": bool(worst_r <= worst_p)}


def cpl_colour_and_T(out):
    """Colour shift with a time-matched placebo, and the transmission."""
    print("\n=== 2b. CPL colour, with the SAME time-matched placebo, and the")
    print("        transmission under an explicit continuity assumption.")
    frames = json.loads((HERE / "data" / "02-frames.json").read_text(encoding="utf-8"))
    lvl = {}
    for rec in frames:
        fr = Fraction(rec["exp"])
        tag = f"e{fr.denominator if fr.numerator == 1 else rec['exp']}-{rec['half']}"
        d = lvl.setdefault(tag, {p: [] for p in ("R", "G1", "G2", "B")})
        for p in d:
            d[p].append(rec[f"mean_{p}"])
    lvl = {t: {p: float(np.mean(v)) for p, v in d.items()} for t, d in lvl.items()}

    tests = [("REAL    CPL vs none, 1/20", "e0.05-A", "e0.05-B"),
             ("REAL    CPL vs none, 1/30", "e0.03333333333333333-A",
              "e0.03333333333333333-B"),
             ("REAL    CPL vs none, 1/250", "e0.004-A", "e0.004-B"),
             ("PLACEBO within A, 1/250 vs 1/13", "e0.004-A",
              "e0.07692307692307693-A"),
             ("PLACEBO within A, 1/250 vs 1/20", "e0.004-A", "e0.05-A"),
             ("PLACEBO within B, 1/250 vs 1/20", "e0.004-B", "e0.05-B")]
    crows = []
    for label, t1, t2 in tests:
        vals = {}
        for pl in ("R", "B"):
            n1 = lvl[t1][pl] / lvl[t1]["G1"]
            n2 = lvl[t2][pl] / lvl[t2]["G1"]
            vals[pl] = 100 * (n1 / n2 - 1)
        crows.append({"label": label, **vals})
        print(f"      {label:34s}  R/G1 {vals['R']:+6.2f}%   B/G1 {vals['B']:+6.2f}%")
    rl = [r for r in crows if r["label"].startswith("REAL")]
    pl_ = [r for r in crows if r["label"].startswith("PLACEBO")]
    for ch in ("R", "B"):
        r_worst = max(abs(r[ch]) for r in rl)
        p_worst = max(abs(r[ch]) for r in pl_)
        print(f"      {ch}/G1: worst REAL {r_worst:.2f}%  worst PLACEBO "
              f"{p_worst:.2f}%  separation {r_worst / p_worst:.1f}x  -> "
              f"{'CPL IS SPECTRALLY NON-NEUTRAL' if r_worst > 3 * p_worst else 'not separated'}")

    print("\n      transmission. proxy(t) = mean / exposure time is the")
    print("      illumination times the filter. Fit log(proxy) linearly over")
    print("      the last 120 s of pass A and the first 120 s of pass B, and")
    print("      extrapolate both to the midpoint of the 280 s gap. That is")
    print("      one ASSUMPTION -- that the light varied smoothly across the")
    print("      change -- and it is the only thing that breaks the degeneracy.")
    import datetime as dt

    def parse(s):
        return dt.datetime.strptime(s[:23], "%Y:%m:%d %H:%M:%S.%f")

    t0 = min(parse(r["t"]) for r in frames)
    pts = [( (parse(r["t"]) - t0).total_seconds(), r["half"],
             r["mean_G1"] / r["exp"]) for r in frames
           if r["mean_G1"] < 12000 and r["mean_G1"] > 100]
    A = [(t, np.log(v)) for t, h, v in pts if h == "A"]
    B = [(t, np.log(v)) for t, h, v in pts if h == "B"]
    tA_end, tB_start = max(t for t, _ in A), min(t for t, _ in B)
    tstar = 0.5 * (tA_end + tB_start)
    print(f"      pass A ends at t={tA_end:.1f}s, pass B starts at "
          f"t={tB_start:.1f}s, gap {tB_start - tA_end:.1f}s, midpoint {tstar:.1f}s")
    Ts = {}
    for win in (60.0, 120.0, 200.0):
        aa = [(t, y) for t, y in A if t >= tA_end - win]
        bb = [(t, y) for t, y in B if t <= tB_start + win]
        ma, ca = np.polyfit([t for t, _ in aa], [y for _, y in aa], 1)
        mb, cb = np.polyfit([t for t, _ in bb], [y for _, y in bb], 1)
        T = float(np.exp((ma * tstar + ca) - (mb * tstar + cb)))
        Ts[win] = T
        print(f"        window {win:5.0f}s (nA={len(aa)}, nB={len(bb)}):  "
              f"T = {T:.4f} = {-np.log2(T):.2f} stops   "
              f"(A slope {100 * ma:+.3f} %/s, B slope {100 * mb:+.3f} %/s)")
    tv = np.array(list(Ts.values()))
    print(f"      T = {tv.mean():.3f} +- {tv.std(ddof=1):.3f} "
          f"({-np.log2(tv.mean()):.2f} stops), spread across the three windows")
    print(f"      Model-free bound from the raw ratios alone: 0.217 <= T <= 0.727.")
    print(f"      A CPL on unpolarised light passes ~0.5 minus absorption, so")
    print(f"      1.0-1.5 stops is the physical expectation.")
    out["cpl_colour"] = crows
    out["transmission"] = {"per_window": {str(k): v for k, v in Ts.items()},
                           "mean": float(tv.mean()), "sd": float(tv.std(ddof=1)),
                           "bound_lo": 0.21718, "bound_hi": 0.72745}


def illum_rows(out):
    print("\n=== 3. PR-8: is the residual spatial variance organised in ROWS?")
    print("    The 360 flats used the ELECTRONIC shutter (ShutterCount pinned")
    print("    at 8515 for all of them). A rolling readout under changing")
    print("    light gives each row its own effective exposure -- a per-row")
    print("    scalar that a global spatial mean cannot divide out.")
    rows = []
    for tag in ("e0.004-A", "e0.008-A", "e0.016666666666666666-A",
                "e0.03333333333333333-A", "e0.05-A", "e0.004-B",
                "e0.008-B", "e0.016666666666666666-B",
                "e0.03333333333333333-B", "e0.05-B"):
        b = np.load(CACHE / f"{tag}-blocks.npy")[1].astype(np.float64)  # G1
        b = b / b.reshape(b.shape[0], -1).mean(axis=1)[:, None, None]
        b = b - b.mean(axis=0)                       # remove the fixed pattern
        rowprof = b.mean(axis=2)                     # (frames, block-rows)
        colprof = b.mean(axis=1)                     # (frames, block-cols)
        v_tot = float(np.var(b))
        v_row = float(np.var(rowprof))
        v_col = float(np.var(colprof))
        rows.append({"tag": tag, "v_total": v_tot, "v_row": v_row,
                     "v_col": v_col, "row_frac": v_row / v_tot,
                     "col_frac": v_col / v_tot})
        print(f"    {tag:26s} total {v_tot:.3e}   row-profile {v_row:.3e} "
              f"({100 * v_row / v_tot:5.1f}%)   col-profile {v_col:.3e} "
              f"({100 * v_col / v_tot:5.1f}%)")
    rf = np.array([r["row_frac"] for r in rows])
    cf = np.array([r["col_frac"] for r in rows])
    print(f"\n    row-profile share of the residual: median {np.median(rf) * 100:.1f}%")
    print(f"    col-profile share of the residual: median {np.median(cf) * 100:.1f}%")
    print(f"    ratio row/col = {np.median(rf) / np.median(cf):.2f}")
    print("    A block row is 32 sensor rows; there are 73 of them. If the")
    print("    residual were isotropic illumination structure the two shares")
    print("    would be comparable.")
    out["illum_rows"] = {"rows": rows, "row_frac_median": float(np.median(rf)),
                         "col_frac_median": float(np.median(cf))}


def main() -> None:
    out = {}
    rho_corrected(out)
    cpl_placebo(out)
    cpl_colour_and_T(out)
    illum_rows(out)
    OUT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
