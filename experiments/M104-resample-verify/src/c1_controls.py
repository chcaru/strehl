"""M104 C1 -- controls.  These run BEFORE any baseline number is read.

An instrument that has not been shown to move when it should, and to hold
still when it should not, cannot return a PASS or a FAIL -- it can only return
a number.  Rule 39 requires the negative control to be made to go red EXACTLY,
not approximately: fact 1231 records a bar registered at 100.000000% catching a
defect of 21 pixels in 8.25 million that any bar phrased "~100%" would have
waved through.

  SELF   same array both sides.                  mag == 1.000000 EXACTLY
  NCX    plant a resample of exactly 1.030000.   mag == 1.030000 +/- 0.004,
         and the "no magnification" bar must go RED.  This is the negative
         control: if a planted 3% enlargement read as 1.000, then a post-fix
         reading of 1.000 would mean nothing, because the instrument would
         report 1.000 for a render that still had the defect.
  DOSE   plant 1.000 / 1.010 / 1.030 / 1.075.    each +/- 0.004, monotone.
         1.075 is chosen to bracket bee-3-cpl's actual 1/k = 1.0735.
  DIM    crop to different output DIMENSIONS at unchanged sampling.
         mag == 1.000 +/- 0.004.  This is the orchestrator's trap turned into
         a control: M95's fix changes the emitted dimensions, so an instrument
         that reacted to dimensions would report the fix as a success purely
         because the picture got smaller.
  PL     placebo -- swap reference and test.     mag -> 1/mag within 1e-6,
         checked PER ROI.  Swapping cannot change any optical property, so a
         residue here is the instrument reading its own asymmetry.
  INERT  the comb must clear its sidebands by >= 3 on >= 8 ROIs, or the ruler
         is NO EVIDENCE rather than a null result.

FIRST RUN FAILED, AND IS REPORTED AS A FAILURE.  Four of seven controls went
red: DOSE at 1.075 read 0.9537 +/- 0.1297, DIM read 0.9910 +/- 0.0541, PL left
a residue of 1.3e-3, and INERT found 7 live ROIs against a bar of 8.  Three
causes, all in the instrument and none in the renders:

  1. the test arm's comb was searched GLOBALLY and filtered only by angle.  A
     comb and its own 2nd harmonic share an angle, so ROIs whose harmonic
     outran their fundamental returned mag ~ 2 or ~ 0.5.  Fixed by seeding the
     search from a frozen prior and constraining it to +/- 15% -- twice the
     largest effect measured here, so it cannot force the answer.
  2. magnifications were averaged ARITHMETICALLY.  A ratio's reciprocal-
     invariant average is the geometric mean, and PL is unsatisfiable without
     one.  Fixed.
  3. the INERT gate was applied to the reference arm only, so the ROI sample
     changed under swap.  Fixed by requiring both arms to clear.

The ROI geometry (384 px, 8 x 6, non-overlapping, 14 live) was selected by
c0_geometry.py against the CONTROL image, before any baseline number existed.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m104lib as L

OUT = Path(__file__).resolve().parent.parent / "out"
BASE = Path(L.RENDERS) / "flat-on-ruler-cpl-PRE-A0-g0.tif"

TOL = 0.004
DOSES = [1.000, 1.010, 1.030, 1.075]
COLS, ROWS = 8, 6

log = []


def say(s=""):
    print(s)
    log.append(s)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    L.ROI = 384

    a = L.green(BASE)
    h, w = a.shape
    say("=" * 78)
    say("M104 C1 -- instrument controls (run before any baseline number)")
    say(f"  base : {BASE.name}   {w} x {h}")
    say(f"  ROI  : {L.ROI}px, {COLS}x{ROWS} non-overlapping, sub-bin centroid")
    say(f"  seed : frozen from this image; search window +/- {L.RAD_TOL:.0%} "
        f"radial, {L.ANG_TOL} rad angular")
    say(f"  tol  : +/- {TOL}")
    say("=" * 78)
    say()

    seed = L.seed_combs(a, cols=COLS, rows=ROWS)
    res, verdicts = {}, []

    # ---------------------------------------------------------------- INERT
    rows = L.measure_pair(a, a, seed, COLS, ROWS)
    sb = [r["sb_ref"] for r in rows]
    ok_inert = len(rows) >= 8
    say(f"INERT  live ROIs (S/B >= {L.INERT_MIN} on BOTH arms) : {len(rows)} "
        f"of {COLS*ROWS}")
    say(f"       S/B  min {min(sb):.2f}  median {np.median(sb):.2f}  max {max(sb):.2f}")
    say(f"       bar: >= 8 live ROIs              -> {'GREEN' if ok_inert else 'RED'}")
    verdicts.append(("INERT", ok_inert))
    res["inert"] = dict(live=len(rows), total=COLS * ROWS, sb_min=min(sb),
                        sb_med=float(np.median(sb)))
    say()

    # ----------------------------------------------------------------- SELF
    m, se, n = L.gmean_se([r["mag"] for r in rows])
    dev = max(abs(r["mag"] - 1.0) for r in rows)
    ok_self = dev == 0.0
    say(f"SELF   mag = {m:.9f}   worst per-ROI deviation {dev:.3e}   (n={n})")
    say(f"       bar: EXACTLY 1.000000000         -> {'GREEN' if ok_self else 'RED'}")
    verdicts.append(("SELF", ok_self))
    res["self"] = dict(mag=m, worst_dev=dev, n=n)
    say()

    # ------------------------------------------------------------ NCX + DOSE
    say(f"{'DOSE':>6} {'planted':>9} {'measured':>11} {'SE':>9} {'err':>10} "
        f"{'n':>4}  verdict")
    dose_rows, prev, monotone = [], None, True
    for s in DOSES:
        rr = L.measure_pair(a, L.resample(a, s), seed, COLS, ROWS)
        m, se, n = L.gmean_se([r["mag"] for r in rr])
        err = m - s
        ok = abs(err) <= TOL
        if prev is not None and not (m > prev):
            monotone = False
        prev = m
        say(f"{'':>6} {s:9.6f} {m:11.6f} {se:9.6f} {err:+10.6f} {n:4d}  "
            f"{'GREEN' if ok else 'RED'}")
        dose_rows.append(dict(planted=s, mag=m, se=se, err=err, n=n, ok=ok))
    ok_dose = all(d["ok"] for d in dose_rows) and monotone
    say(f"       monotone increasing: {monotone}")
    say(f"       bar: every dose within +/- {TOL} and monotone "
        f"-> {'GREEN' if ok_dose else 'RED'}")
    verdicts.append(("DOSE", ok_dose))
    res["dose"] = dose_rows
    say()

    ncx = [d for d in dose_rows if d["planted"] == 1.030][0]
    sig = abs(ncx["mag"] - 1.0) / ncx["se"] if ncx["se"] > 0 else float("inf")
    red = sig > 2.0
    say(f"NCX    planted EXACTLY 1.030000  ->  measured {ncx['mag']:.6f} "
        f"+/- {ncx['se']:.6f}")
    say(f"       read against the POST-FIX bar |mag - 1| <= 2 SE : "
        f"{sig:.2f} sigma from 1.000")
    say(f"       bar: MUST GO RED                 -> "
        f"{'GREEN (it went red)' if red else 'RED (it passed -- instrument is blind)'}")
    verdicts.append(("NCX", red))
    res["ncx"] = dict(planted=1.030, mag=ncx["mag"], se=ncx["se"], sigma=sig,
                      went_red=red)
    say()

    # ------------------------------------------------------------------ DIM
    for frac in (0.90, 0.80):
        ch, cw = int(h * frac), int(w * frac)
        y0, x0 = (h - ch) // 2, (w - cw) // 2
        rr = L.measure_pair(a, a[y0:y0 + ch, x0:x0 + cw], seed, COLS, ROWS)
        m, se, n = L.gmean_se([r["mag"] for r in rr])
        ok = abs(m - 1.0) <= TOL
        say(f"DIM    {w}x{h} vs {cw}x{ch} (crop, NO resample)   "
            f"mag = {m:.6f} +/- {se:.6f}  n={n}")
        say(f"       bar: 1.000 +/- {TOL}              -> {'GREEN' if ok else 'RED'}")
        verdicts.append((f"DIM{int(frac*100)}", ok))
        res[f"dim{int(frac*100)}"] = dict(dims=[cw, ch], mag=m, se=se, n=n, ok=ok)
    say()

    # ------------------------------------------------------------------- PL
    b = L.resample(a, 1.030)
    fwd = {r["roi"]: r["mag"] for r in L.measure_pair(a, b, seed, COLS, ROWS)}
    rev = {r["roi"]: r["mag"] for r in L.measure_pair(b, a, seed, COLS, ROWS)}
    shared = sorted(set(fwd) & set(rev))
    resid = max(abs(fwd[i] * rev[i] - 1.0) for i in shared) if shared else float("inf")
    gf = L.gmean_se([fwd[i] for i in shared])[0]
    gr = L.gmean_se([rev[i] for i in shared])[0]
    ok_pl = resid <= 1e-6 and abs(gf * gr - 1.0) <= 1e-6
    say(f"PL     per-ROI worst |fwd*rev - 1| = {resid:.3e}   over {len(shared)} ROIs")
    say(f"       geometric means {gf:.9f} and {gr:.9f}, product {gf*gr:.12f}")
    say(f"       bar: <= 1e-6                     -> {'GREEN' if ok_pl else 'RED'}")
    verdicts.append(("PL", ok_pl))
    res["pl"] = dict(worst=resid, gmean_fwd=gf, gmean_rev=gr,
                     product=gf * gr, n=len(shared), ok=ok_pl)
    say()

    say("-" * 78)
    for name, ok in verdicts:
        say(f"  {name:<8} {'GREEN' if ok else 'RED'}")
    allok = all(ok for _, ok in verdicts)
    say(f"  {'ALL':<8} "
        f"{'GREEN -- instrument admitted' if allok else 'RED -- instrument NOT admitted'}")
    say("-" * 78)

    res["all_green"] = allok
    res["geometry"] = dict(roi=L.ROI, cols=COLS, rows=ROWS,
                           rad_tol=L.RAD_TOL, ang_tol=L.ANG_TOL)
    (OUT / "c1_controls.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (OUT / "c1_controls.log").write_text("\n".join(log), encoding="utf-8")


if __name__ == "__main__":
    main()
