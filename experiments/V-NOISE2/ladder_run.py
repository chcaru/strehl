"""ladder_run -- R as a function of frame count, on ONE subject (M115).

PREREGISTRATION.md sec.11 fixes every choice here and was committed (7497c353)
BEFORE this file or any rung existed.  Read it before reading this.

THE QUESTION.  ORCH derives from the shipped weight law (pyramid.rs L1351-1362,
L2092-2110) that

    share_winner = 1 / (1 + SUM_{k != winner} (e_k / e_winner)^p)

in which N appears nowhere but the sum carries N-1 terms, giving a predicted
winner's share of 0.45 at N=22 falling to 0.055 at N=299.  A winner holding 5%
of the share is a coin toss between near-ties, and a coin toss does not
reproduce across two independent half-stacks.  Sec.9's R is exactly the rate at
which the two halves fail to reproduce each other.  So the mechanism predicts
R RISES WITH N, and predicts it in COARSE/DETAIL specifically while COARSE/FLAT
stays near 1.

WHAT THIS FILE DOES NOT DO.  It does not reimplement the statistic.  Every
number comes from incoh.py's own functions, imported unmodified, so a rung of
this ladder and sec.9's reading of `119` are the same instrument.  What is new
is the rung loop and the three controls sec.11.4 requires.

THREE THINGS ARE HELD CONSTANT SO THAT N IS WHAT VARIES.

  1. ALIGNMENT.  align_image_stack ran once over all 299 frames; every rung
     subsamples that one aligned set.  Re-aligning per rung would let
     registration quality track N and manufacture the predicted result.
  2. THE TILE POPULATION.  census2.py derives tiles from the SOURCE FRAMES, not
     from any merge, so the census is a property of the scene.  bee's census is
     reused at every rung, which makes it impossible for R(N) to be a
     population effect.  (Sec.8's popcheck found equal counts are not equal
     sets; here they are literally the same cells.)
  3. THE BINARY.  All four rungs are built with pin 9b05d0b7.

WHAT IS RE-DERIVED PER RUNG, because carrying it would be the confound.

  1. GEOMETRY.  V-HEADTOHEAD2 sec.7 names trusting geometry as one of three
     things that invalidated an entire pass, and enfuse's canvas genuinely
     differs per rung -- its output is the intersection of the frames it was
     given, and each rung gives it a different subset (L1 193136172 bytes
     against L4's 185 MB).  geom2.py is re-run per rung.
  2. PLANT POTENCY.  Sec.9.6 established that beta must be derived per band.
     commission() derives it from each rung's own baseline, so it is re-derived
     per rung as well, and no rung inherits another's calibration.

THE CONTROL THAT COULD VOID THE READING.  strehl self-aligns each half while
enfuse consumes the fixed aligned set, so strehl's registration -- and hence
which content sits under a fixed census cell -- could drift with N and mimic
the prediction.  Measured directly here as the integer shift of each rung's
strehl-A against L4's.  A drift that grows with N voids the reading, and is
reported rather than assumed absent.

INVOCATION (rule 47).  Rungs must already be built by ladder_build.ps1 and
geom2.py must have been run on each rung key.

    python ladder_run.py
"""
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import incoh as I                                                # noqa: E402
import hd2                                                       # noqa: E402

Comp = I.Comp
T = I.T


class WidePlacer(I.Placer):
    """incoh.Placer with a wider search and the achieved peak RECORDED.

    TWO REASONS, both measured rather than assumed.

    1. incoh.Placer searches +-REG_WIN blocks = +-32 px.  On `119` the
       strehl-vs-enfuse residual offset was (-8, -16) px, comfortably inside
       it.  On `bee` geomcrop measures (+32, -24) px -- EXACTLY ON THE
       BOUNDARY, so some tiles' true match lies outside the window and the
       search would return an edge-pinned wrong answer that looks like a
       normal one.  The window is widened rather than biased by the fitted
       offset, because biasing requires getting geomcrop's sign convention
       right and a sign error here is silent.  Widening needs no convention.

    2. incoh.Placer returns (y0, x0) and DISCARDS the correlation peak, so
       how well the placement actually worked is invisible to the caller.
       bee's geometry is the weak one on this corpus -- median tile peak
       0.23-0.26 against 0.63 planted and 0.77 on `119` -- so it is exactly
       the subject where that must be visible.  Peaks are recorded and the
       distribution is printed per rung.

    The narrow and wide windows are BOTH run per rung and both reported, so
    the effect of this change on the reading is measured, not argued.
    """

    def __init__(self, ref, mov, scale, win=I.REG_WIN):
        super().__init__(ref, mov, scale)
        self.win = int(win)
        self.peaks = []
        self.edge = 0

    def place(self, y, x, t):
        s, b = self.s, t // I.REG_D
        yb, xb = y // I.REG_D, x // I.REG_D
        if yb + b > self.rb.shape[0] or xb + b > self.rb.shape[1]:
            return None
        R = self.rb[yb:yb + b, xb:xb + b]
        R = R - R.mean()
        rn = float(np.sqrt((R * R).sum()))
        if rn <= 0:
            return None
        best, bdy, bdx = -2.0, None, None
        w = self.win
        for dy in range(-w, w + 1):
            ay = yb + dy
            if ay < 0 or ay + b > self.mb.shape[0]:
                continue
            for dx in range(-w, w + 1):
                ax = xb + dx
                if ax < 0 or ax + b > self.mb.shape[1]:
                    continue
                M = self.mb[ay:ay + b, ax:ax + b]
                M = M - M.mean()
                mn = float(np.sqrt((M * M).sum()))
                if mn <= 0:
                    continue
                c = float((R * M).sum()) / (rn * mn)
                if c > best:
                    best, bdy, bdx = c, dy, dx
        if bdy is None:
            return None
        self.peaks.append(best)
        if abs(bdy) == w or abs(bdx) == w:
            self.edge += 1
        return (int(round((y + bdy * I.REG_D) / s)),
                int(round((x + bdx * I.REG_D) / s)))

RUNGS = ("bee-L1", "bee-L1P", "bee-L2", "bee-L2P", "bee-L3", "bee-L3P",
         "bee-L4")
# The ORIGINAL sec.11 ladder, in which the half-split offset fell 9 -> 5 -> 3
# -> 1 as N rose and is therefore CONFOUNDED with N.  Kept and printed so the
# confounded numbers stay on the record next to the corrected ones.
ORIGINAL = ("bee-L1", "bee-L2", "bee-L3", "bee-L4")
# The sec.12 CORRECTED ladder: half-split offset held at 1 frame on every rung,
# so only N varies.  This is the one the branch is taken on.
CORRECTED = ("bee-L1P", "bee-L2P", "bee-L3P", "bee-L4")
REF_RUNG = "bee-L4"
CENSUS_FROM = "bee"

# sec.11.3, fixed before any rung was measured.
Q_RISING = 2.0
Q_FLAT_LO, Q_FLAT_HI = 0.67, 1.5
Q_FALLING = 0.5
# sec.11.4: a rung whose FLAT ratio leaves this is reported suspect.
FLAT_LO, FLAT_HI = 0.80, 1.25
# Sec.12.4, fixed before bee-L2P/bee-L3P existed.  phi = P_d/P_m tends to 1 as
# the halves decorrelate, so R between two saturated arms is a ratio of two
# ceilings and carries no information about degree.
SAT_MAX = 0.90
MIN_READABLE = 3


def load_rung(rung):
    """Arms, geometry and the SHARED census for one rung."""
    d = os.path.join(hd2.ROOT, rung)
    arm = os.path.join(d, "arms")
    P = {n: os.path.join(arm, f) for n, f in (
        ("sA", "strehl-A.tiff"), ("sB", "strehl-B.tiff"),
        ("eA", "coh-enfuse-A.tif"), ("eB", "coh-enfuse-B.tif"))}
    for p in P.values():
        if not os.path.exists(p):
            raise SystemExit(f"missing {p} -- build the rung first")
    with open(os.path.join(d, "geom.json"), encoding="utf-8") as fh:
        g = json.load(fh)
    if not g.get("enfuse", {}).get("ok"):
        raise SystemExit(f"{rung}: enfuse geometry fit FAILED -- refusing to read it")
    with open(os.path.join(d, "manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    z = np.load(os.path.join(hd2.ROOT, CENSUS_FROM, "census.npz"))
    return P, g["enfuse"], man, z


def shift_of(ref, mov, win=12):
    """Integer block shift of `mov` against `ref`, both strehl rasters.

    THE CONTROL SEC.11.4 NAMES.  It is deliberately not a correlation summary:
    ORCH's warning is that a self-test asserting only the MEAN of a field can
    miss a defect living at its borders, so this returns the actual (dy, dx)
    and the peak, and the caller prints all three per rung.
    """
    a = I.block_mean(ref.g, I.REG_D)
    b = I.block_mean(mov.g, I.REG_D)
    h = min(a.shape[0], b.shape[0])
    w = min(a.shape[1], b.shape[1])
    m = min(h, w) // 4
    A = a[m:h - m, m:w - m]
    A = A - A.mean()
    an = float(np.sqrt((A * A).sum()))
    best, bdy, bdx = -2.0, 0, 0
    for dy in range(-win, win + 1):
        for dx in range(-win, win + 1):
            y0, x0 = m + dy, m + dx
            if y0 < 0 or x0 < 0 or y0 + A.shape[0] > b.shape[0] or \
               x0 + A.shape[1] > b.shape[1]:
                continue
            B = b[y0:y0 + A.shape[0], x0:x0 + A.shape[1]]
            B = B - B.mean()
            bn = float(np.sqrt((B * B).sum()))
            if bn <= 0:
                continue
            c = float((A * B).sum()) / (an * bn)
            if c > best:
                best, bdy, bdx = c, dy, dx
    return bdy * I.REG_D, bdx * I.REG_D, best


def measure(rung, ref_sA=None):
    P, ge, man, z = load_rung(rung)
    cells, emax = z["cells"], z["emax"]
    flat = [int(i) for i in z["flat"]]
    det = [int(i) for i in np.argsort(emax)[-len(flat):]]
    DET = [tuple(cells[i]) for i in det]
    FLAT = [tuple(cells[i]) for i in flat]

    C = {k: Comp(dict(path=v, weights=I.W)) for k, v in P.items()}
    s = float(ge["scale"])

    # Sec.11.4 requires geometry re-derived per rung; it does not license
    # trusting the placement that geometry implies.  Both windows are run and
    # both are reported, so widening cannot quietly become the thing that
    # produced the answer.
    pl_n = WidePlacer(C["sA"], C["eA"], s, win=I.REG_WIN)
    pl = WidePlacer(C["sA"], C["eA"], s, win=2 * I.REG_WIN)

    print("=" * 104)
    print(f"RUNG {rung}   N = {man['n']}  (halves {man['n_a']} / {man['n_b']})"
          f"   stride {man['stride']}")
    print("=" * 104)
    print(f"  geometry RE-DERIVED: scale {s:.4f}  score {ge['score']:.4f}  "
          f"offset ({ge.get('off_dy')}, {ge.get('off_dx')}) px  "
          f"resampled={ge.get('resampled')}  interior={ge.get('interior')}")

    dy = dx = 0
    dpk = float("nan")
    if ref_sA is not None:
        dy, dx, dpk = shift_of(ref_sA, C["sA"])
        print(f"  strehl raster drift vs L4: dy {dy:+d} dx {dx:+d} px, "
              f"peak {dpk:.4f}  (sec.11.4 control -- a drift growing with N "
              f"would void the reading)")

    sD = I.pairs(C["sA"], C["sB"], DET)
    sF = I.pairs(C["sA"], C["sB"], FLAT)
    eD_n = I.pairs(C["eA"], C["eB"], DET, placer=pl_n)
    eD = I.pairs(C["eA"], C["eB"], DET, placer=pl)
    eF = I.pairs(C["eA"], C["eB"], FLAT, placer=pl)
    pk = np.array(pl.peaks) if pl.peaks else np.array([np.nan])
    pkn = np.array(pl_n.peaks) if pl_n.peaks else np.array([np.nan])
    print(f"  tiles: strehl {len(sD)} DETAIL / {len(sF)} FLAT;  "
          f"enfuse {len(eD)} DETAIL / {len(eF)} FLAT")
    print(f"  placement peak (wide +-{2 * I.REG_WIN * I.REG_D} px): median "
          f"{np.median(pk):.4f} min {np.nanmin(pk):.4f}; {pl.edge} tiles pinned "
          f"at the window edge")
    print(f"  placement peak (narrow +-{I.REG_WIN * I.REG_D} px, incoh's own): "
          f"median {np.median(pkn):.4f}; {pl_n.edge} pinned  "
          f"-- both reported so widening is not a hidden choice")

    rng = np.random.default_rng(20260827)
    out = {"rung": rung, "n": man["n"], "n_a": man["n_a"], "n_b": man["n_b"],
           "stride": man["stride"],
           "boffset": (int(man["stride"]) if int(man.get("boffset", -1)) < 0
                       else int(man["boffset"])),
           "scale": s, "geom_score": ge["score"],
           "geom_rms": ge.get("rms_px", float("nan")),
           "place_peak": float(np.median(pk)), "place_edge": pl.edge,
           "place_peak_narrow": float(np.median(pkn)),
           "drift_dy": dy, "drift_dx": dx,
           "drift_peak": dpk, "tiles": {"sD": len(sD), "sF": len(sF),
                                        "eD": len(eD), "eF": len(eF)},
           "bands": {}}

    fails = []
    for bname, band in I.BANDS:
        # A DEGENERATE BAND IS A READING, NOT A CRASH.  When phi >= 1 the
        # half-difference carries as much band power as the half-mean, the
        # coherent amplitude sqrt(max(P_m - P_d, 0)) clamps to exactly 0, and
        # incoh.commission divides by it.  That is not a coding accident: it
        # means the two halves share NO coherent detail in this band, which is
        # a real and important thing to have measured.  It is recorded as
        # DEGENERATE and the band is refused rather than reported, because a
        # plant sized from a zero baseline is no plant at all.
        b_ph, b_am, _ = I.phi_of(sD, band)
        b_phi, b_amp = float(np.median(b_ph)), float(np.median(b_am))
        if not (b_amp > 0) or b_phi >= 1.0:
            print(f"\n  --- {bname}: DEGENERATE, band refused ---")
            print(f"  baseline phi {b_phi:.5f} >= 1 means P_d >= P_m: the two "
                  f"halves share no coherent detail here.")
            print(f"  coherent amplitude clamps to {b_amp:.4e}, so a plant "
                  f"sized from it is no plant.  No verdict from this band.")
            out["bands"][bname] = {
                "R": float("nan"), "R_narrow": float("nan"),
                "ci": [float("nan")] * 2, "phi_s": b_phi, "phi_e": float("nan"),
                "R_flat": float("nan"), "ci_flat": [float("nan")] * 2,
                "amp_s": b_amp, "amp_e": float("nan"), "suspect": True,
                "degenerate": True, "commission": {}, "fails": ["DEGENERATE"]}
            fails.append(f"{rung}/{bname}/DEGENERATE")
            continue

        print(f"\n  --- {bname} commissioning (beta re-derived for THIS rung) ---")
        comm, f = I.commission(sD, band, bname)
        fails += [f"{rung}/{x}" for x in f]

        ps, as_, _ = I.phi_of(sD, band)
        pe, ae, _ = I.phi_of(eD, band)
        pen, _, _ = I.phi_of(eD_n, band)
        psf, _, _ = I.phi_of(sF, band)
        pef, _, _ = I.phi_of(eF, band)
        R = float(np.median(ps) / np.median(pe))
        Rn = float(np.median(ps) / np.median(pen))
        lo, hi = I.boot_ratio(ps, pe, I.NBOOT, rng)
        Rf = float(np.median(psf) / np.median(pef))
        flo, fhi = I.boot_ratio(psf, pef, I.NBOOT, rng)
        amp_s, amp_e = float(np.median(as_)), float(np.median(ae))
        susp = not (FLAT_LO <= Rf <= FLAT_HI)
        print(f"  {bname} DETAIL  strehl phi {np.median(ps):.5f}  "
              f"enfuse phi {np.median(pe):.5f}  R = {R:.3f} [{lo:.3f}, {hi:.3f}]")
        print(f"  {bname} DETAIL  under incoh's OWN narrow window: R = {Rn:.3f}"
              f"   (difference from widening: {R / Rn - 1:+.1%})")
        print(f"  {bname} FLAT    strehl phi {np.median(psf):.5f}  "
              f"enfuse phi {np.median(pef):.5f}  R = {Rf:.3f} [{flo:.3f}, {fhi:.3f}]"
              f"{'   *** OUTSIDE [0.80,1.25] -- THIS RUNG IS SUSPECT' if susp else ''}")
        print(f"  {bname} coherent amplitude  strehl {amp_s:.4e}  "
              f"enfuse {amp_e:.4e}  (phi is never printed without it)")
        out["bands"][bname] = {
            "R": R, "R_narrow": Rn, "ci": [lo, hi], "phi_s": float(np.median(ps)),
            "phi_e": float(np.median(pe)), "R_flat": Rf, "ci_flat": [flo, fhi],
            "amp_s": amp_s, "amp_e": amp_e, "suspect": bool(susp),
            "commission": comm, "fails": f}
    out["fails"] = fails
    return out, C["sA"]


def readable(o, bname):
    """Sec.12.4's gate. Returns (bool, reason).

    Three exclusions, and note that ALL THREE ONLY REMOVE RUNGS.  None of them
    can promote an unreadable rung into the branch, so adding the commissioning
    exclusion -- which sec.12.4 did not name -- cannot manufacture a verdict.
    It can only push the result toward 'no branch declared'.
    """
    b = o["bands"][bname]
    if b.get("degenerate"):
        return False, "DEGENERATE"
    if b["phi_s"] > SAT_MAX:
        return False, f"strehl phi {b['phi_s']:.3f} > {SAT_MAX}"
    if b["phi_e"] > SAT_MAX:
        return False, f"enfuse phi {b['phi_e']:.3f} > {SAT_MAX}"
    if b["fails"]:
        return False, "commissioning: " + ", ".join(b["fails"])
    return True, ""


def ladder_verdict(res, rungs, bname, label):
    """Apply sec.12.5's branch to one ladder in one band, or refuse to."""
    byr = {o["rung"]: o for o in res}
    print(f"\n  {label}  ({bname})")
    keep = []
    for r in rungs:
        okr, why = readable(byr[r], bname)
        b = byr[r]["bands"][bname]
        print(f"    {r:9s} N={byr[r]['n']:4d}  R = {b['R']:9.3f}  "
              f"{'READABLE' if okr else 'excluded: ' + why}")
        if okr:
            keep.append(r)
    lo_r, hi_r = rungs[0], rungs[-1]
    if len(keep) < MIN_READABLE or lo_r not in keep or hi_r not in keep:
        print(f"    only {len(keep)} of {len(rungs)} rungs readable"
              f"{'' if lo_r in keep and hi_r in keep else ', and an endpoint is excluded'}"
              f" -- sec.12.4 requires {MIN_READABLE} readable rungs including")
        print("    both endpoints, so NO BRANCH IS DECLARED on this ladder.")
        return {"ladder": label, "band": bname, "readable": keep,
                "Q": None, "branch": "NO-BRANCH"}
    a = byr[lo_r]["bands"][bname]
    b = byr[hi_r]["bands"][bname]
    Q = b["R"] / a["R"]
    ov = not (b["ci"][0] > a["ci"][1] or a["ci"][0] > b["ci"][1])
    if Q >= Q_RISING:
        br = "RISING"
    elif Q_FLAT_LO <= Q <= Q_FLAT_HI and ov:
        br = "FLAT"
    elif Q <= Q_FALLING:
        br = "FALLING"
    else:
        br = "MIXED"
    print(f"    Q = R({hi_r})/R({lo_r}) = {b['R']:.3f} / {a['R']:.3f} = {Q:.3f}"
          f"   (CIs {'OVERLAP' if ov else 'DISJOINT'})")
    print(f"    BRANCH: {br}   (thresholds fixed in sec.12.5 before "
          f"bee-L2P/bee-L3P existed)")
    return {"ladder": label, "band": bname, "readable": keep, "Q": Q,
            "branch": br, "ci_overlap": ov}


def main():
    res = []
    # REF_RUNG is measured first so that every other rung's raster drift is
    # measured against it; the loop below then reports in ladder order.
    rref, ref = measure(REF_RUNG, None)
    got = {REF_RUNG: rref}
    for r in RUNGS:
        if r == REF_RUNG:
            continue
        o, _ = measure(r, ref)
        got[r] = o
    res = [got[r] for r in RUNGS]

    print("\n" + "=" * 104)
    print("M115 LADDER -- R as a function of N, within subject bee-1-cpl")
    print("=" * 104)
    for bname, _ in I.BANDS:
        print(f"\n  {bname}")
        print(f"  {'rung':7s} {'N':>5s} {'off':>4s} {'R DETAIL':>10s} "
              f"{'95% CI':>20s} "
              f"{'R FLAT':>8s} {'amp s':>11s} {'amp e':>11s}  note")
        for o in res:
            b = o["bands"][bname]
            note = ("DEGENERATE" if b.get("degenerate")
                    else ("SUSPECT (flat)" if b["suspect"] else ""))
            if b["fails"]:
                note = (note + " COMMISSIONING FAILED").strip()
            print(f"  {o['rung']:7s} {o['n']:5d} {o['boffset']:4d} "
                  f"{b['R']:10.3f} "
                  f"[{b['ci'][0]:8.3f},{b['ci'][1]:8.3f}] {b['R_flat']:8.3f} "
                  f"{b['amp_s']:11.4e} {b['amp_e']:11.4e}  {note}")

    print("\n  --- controls ---")
    print(f"  {'rung':7s} {'N':>5s} {'scale':>7s} {'geom score':>11s} "
          f"{'geom rms':>9s} {'drift dy':>9s} {'drift dx':>9s} {'drift pk':>9s}")
    for o in res:
        print(f"  {o['rung']:7s} {o['n']:5d} {o['scale']:7.4f} "
              f"{o['geom_score']:11.4f} {o['geom_rms']:9.2f} "
              f"{o['drift_dy']:9d} {o['drift_dx']:9d} {o['drift_peak']:9.4f}")

    allf = [x for o in res for x in o["fails"]]
    print("\n" + "=" * 104)
    print("VERDICTS")
    print(f"  {len(allf)} commissioning arm(s) failed across all rungs and "
          f"bands; every one is listed below and none is suppressed.")
    verd = []
    for bname, _ in I.BANDS:
        verd.append(ladder_verdict(res, CORRECTED, bname,
                                   "CORRECTED ladder, offset held at 1"))
        verd.append(ladder_verdict(res, ORIGINAL, bname,
                                   "ORIGINAL sec.11 ladder, offset CONFOUNDED "
                                   "with N -- not a verdict"))
    if allf:
        print(f"\n  ALL FAILING ARMS: {', '.join(allf)}")

    out = {"rungs": res, "verdicts": verd, "fails": allf,
           "sat_max": SAT_MAX, "min_readable": MIN_READABLE}
    dst = os.path.join(hd2.ROOT, "ladder-bee2.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n  written {dst}")
    corrected_branches = [v["branch"] for v in verd
                          if v["ladder"].startswith("CORRECTED")]
    return 0 if any(b != "NO-BRANCH" for b in corrected_branches) else 1


if __name__ == "__main__":
    sys.exit(main())
