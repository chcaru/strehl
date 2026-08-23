"""M41 step 10 -- WHY every arm reads 0.4961 cyc/px, and whether FRC is repairable.

This is the diagnosis the run of record could not give.  a8_frc_power.py showed
that split-half FRC has no POWER on this data (a flat ROI with no scene detail
in it crosses 1/7 at Nyquist on both stacks).  It did not show the MECHANISM,
and it did not try to repair the metric before abandoning it.  Both are done
here.

PART 1 is pure arithmetic on the ring grid and on the curves already stored in
out/a6_results.json.  It re-decodes nothing and can be run in a second.  The
hypothesis it tests: 0.4961 is not a measurement at all, it is the constant
m41lib.frc_cross returns when the curve never crosses the threshold.

PART 2 asks whether any setting of the estimator repairs it: four ring counts x
four thresholds, on the detail ROI and -- rule 9, and FIRST in the printout --
on the FLAT ROI, which is the input that must make a resolution metric fail.

RULE 20, written before running.  A repair setting COUNTS only if it is both
(a) uncensored on the detail ROI for every arm, and
(b) separated: detail crossing > flat crossing by more than one ring width.
An input that produces "no repair found" exists and is what I expect: a curve
that stays above the threshold at every sampled ring, on both ROIs.  An input
that produces "repair found" also exists: a high threshold is crossed early by
any curve that decays at all, so thr=0.7 must be uncensored or the curves do not
decay -- which would itself be the finding.  Both outcomes are producible, so
the ladder is not a tautology.

Rule 15: m41lib.py and m41lib2.py are NOT edited.  The censoring-aware crossing
lives in the new m41lib3.py.  Rule 24: this script re-CHOOSES the ring count and
the threshold, which are exactly the library defaults a6 accepted.
"""
import os, sys, glob, json, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m41lib as L
import m41lib2 as L2
import m41lib3 as L3
from a2_run import load_two, core, PAD
from a4_shipped_gate import fields, arm_A_shipped, solve_gate

OUT = L.OUT
STACKS = ("109MSDCF", "119MSDCF")
NBINS = (32, 64, 128, 256)
THRS = ((1.0 / 7.0, "1/7"), (0.3, "0.30"), (0.5, "0.50"), (0.7, "0.70"))


def three_arms(cube, g, rn_e, s, t):
    """Arms A, C, D only.  B, D' and E are not needed to diagnose the metric and
    each Wiener pass is the expensive part."""
    _, reg = fields(cube, g, rn_e)
    a, _ = arm_A_shipped(cube, reg, t)
    return {"A": a,
            "C": cube.mean(0),
            "D": L2.arm_wiener2(cube, reg, g, rn_e, s, True, True)}


def main():
    fh = open(os.path.join(OUT, "a10_frc_diagnose.log"), "w", encoding="utf-8")

    def p(m):
        print(m); fh.write(m + "\n"); fh.flush()

    res = {}
    # ================================================================ PART 1
    p("=" * 78)
    p("PART 1 -- is 0.4961 a measurement?  Arithmetic only, nothing decoded.")
    p("=" * 78)
    ff64, last64 = L3.ring_grid(512, 64)
    p(f"  m41lib.frc(n=512, nbin=64): {len(ff64)} rings, width "
      f"{(ff64[1]-ff64[0])*512:.1f} px, first {ff64[0]:.6f}, LAST {last64:.8f} cyc/px")
    p(f"  m41lib.frc_cross's fallback is `return float(ff[-1])` = {last64:.4f} "
      f"printed at 4 dp -> '0.4961'.")
    p("  So '0.4961' is the RIGHT-CENSORED value: it means '>= 0.4961', i.e. the "
      "curve never fell")
    p("  below 1/7 for two adjacent rings inside the sampled band.  It is a "
      "property of the grid.")
    for nb in NBINS:
        _, lz = L3.ring_grid(512, nb)
        p(f"    nbin={nb:4d} -> fallback {lz:.6f} cyc/px   "
          f"(the 'value' moves when the BINNING moves, which a measurement would not)")
    res["fallback"] = {str(nb): L3.ring_grid(512, nb)[1] for nb in NBINS}

    with open(os.path.join(OUT, "a6_results.json")) as g0:
        a6 = json.load(g0)
    p("\n  Re-scoring every stored a6 curve with a censoring flag "
      "(m41lib3.cross, same rule):")
    ncens = ntot = 0
    res["a6_recheck"] = {}
    for st in STACKS:
        res["a6_recheck"][st] = {}
        for arm, rec in a6[st]["frc"].items():
            fr = np.array(rec["curve"]); ffq = np.array(rec["freq"])
            x, cens = L3.cross(ffq, fr, 1.0 / 7.0)
            ntot += 1; ncens += int(cens)
            res["a6_recheck"][st][arm] = dict(cross=x, censored=bool(cens),
                                              a6=rec["cross"], min_frc=float(fr.min()))
            p(f"    {st} arm {arm:2s}: a6 printed {rec['cross']:.4f}   "
              f"recomputed {x:.4f}  censored={str(cens):5s}  min FRC over all "
              f"rings {fr.min():+.4f}")
    p(f"\n  MEASURED: {ncens} of {ntot} stored detail-ROI crossings are CENSORED. "
      f"Each is the constant {last64:.4f}, not a resolution.")
    p("  DERIVED: 119MSDCF's kill-condition ratio f_D/f_A = 0.4961/0.4961 = 1.000 "
      "is a ratio of two")
    p("  censored values.  Its true content is 'both >= 0.4961', which is "
      "compatible with any ordering.")
    res["n_censored"], res["n_total"] = ncens, ntot

    # ================================================================ PART 2
    p("\n" + "=" * 78)
    p("PART 2 -- can it be repaired?  4 ring counts x 4 thresholds, FLAT ROI FIRST.")
    p("  A setting counts as a repair only if it is uncensored on the detail ROI "
      "for every arm")
    p("  AND detail exceeds flat by more than one ring width.  Pre-registered "
      "above, in the docstring.")
    p("=" * 78)
    with open(os.path.join(OUT, "rois_b.json")) as g0:
        rois = json.load(g0)
    for k, v in rois.items():
        for key in ("detail_roi", "flat_roi"):
            x, y, w, h = v[key]
            v[key] = [max(PAD, x), max(PAD, y), w, h]

    for name in STACKS:
        info = rois[name]
        files = sorted(glob.glob(os.path.join(info["dir"], "*.ARW")))
        g, rn_e = info["g"], info["rn_e"]
        t0 = time.time()
        Dc, Fc = load_two(files, tuple(info["detail_roi"]), tuple(info["flat_roi"]))
        _, regD = fields(Dc, g, rn_e)
        s, _, _ = L.calibrate_s(core(Dc), core(regD), g, rn_e, True)
        t = solve_gate(Dc, regD, 3.0)
        ev, od = np.arange(0, len(files), 2), np.arange(1, len(files), 2)
        halves = {}
        for lab, cube in (("flat", Fc), ("detail", Dc)):
            aE = three_arms(cube[ev], g, rn_e, s, t)
            aO = three_arms(cube[od], g, rn_e, s, t)
            halves[lab] = (aE, aO)
        p(f"\n=== {name}: {len(files)} frames, decode+merge {time.time()-t0:.1f}s, "
          f"s={s:.4f}, gate t={t:.4f}")

        row = {}
        curves = {}
        for lab in ("flat", "detail"):
            aE, aO = halves[lab]
            for arm in ("A", "C", "D"):
                for nb in NBINS:
                    ffq, fr, _ = L.frc(core(aE[arm]).astype(np.float64),
                                       core(aO[arm]).astype(np.float64), nbin=nb)
                    curves[(lab, arm, nb)] = (ffq, fr)

        p("    ring x threshold ladder.  'C' suffix marks a CENSORED (lower-bound) "
          "reading.")
        p(f"    {'nbin':>5s} {'thr':>5s} | " +
          " | ".join(f"{a:>16s}" for a in ("A  flat / detail", "C  flat / detail",
                                           "D  flat / detail")))
        repairs = []
        for nb in NBINS:
            for thr, tl in THRS:
                cells = []
                ok_uncens, ok_sep = True, True
                ringw = (curves[("detail", "A", nb)][0][1] -
                         curves[("detail", "A", nb)][0][0])
                for arm in ("A", "C", "D"):
                    xf, cf = L3.cross(*curves[("flat", arm, nb)], thr)
                    xd, cd = L3.cross(*curves[("detail", arm, nb)], thr)
                    row[f"{arm}|{nb}|{tl}"] = dict(flat=xf, flat_cens=bool(cf),
                                                   detail=xd, detail_cens=bool(cd))
                    cells.append(f"{xf:.4f}{'C' if cf else ' '}/{xd:.4f}"
                                 f"{'C' if cd else ' '}")
                    if cd:
                        ok_uncens = False
                    if not (xd > xf + ringw):
                        ok_sep = False
                mark = "  <== REPAIR" if (ok_uncens and ok_sep) else ""
                if ok_uncens and ok_sep:
                    repairs.append((nb, tl))
                p(f"    {nb:5d} {tl:>5s} | " + " | ".join(f"{c:>16s}" for c in cells)
                  + mark)
        p(f"    repairs found at this stack: "
          f"{repairs if repairs else 'NONE'}")

        # how much of the detail ROI's FRC is common-mode?  flat/detail at f_sig
        p("    common-mode fraction: flat-ROI FRC divided by detail-ROI FRC, at "
          "nbin=64.")
        cm = {}
        for arm in ("A", "C", "D"):
            ffq, frf = curves[("flat", arm, 64)]
            _, frd = curves[("detail", arm, 64)]
            vals = {}
            for q in (0.10, 0.20, L.F_SIG, 0.35, 0.45):
                a_ = float(np.interp(q, ffq, frf)); b_ = float(np.interp(q, ffq, frd))
                vals[f"{q:.2f}"] = a_ / b_ if abs(b_) > 1e-9 else float("nan")
            cm[arm] = vals
            p(f"      {arm:2s}: " + "  ".join(f"@{k} {v:6.3f}" for k, v in vals.items()))
        row["common_mode"] = cm
        row["repairs"] = repairs
        res[name] = row

    p("\n" + "=" * 78)
    allr = [res[s_]["repairs"] for s_ in STACKS]
    common = sorted(set(map(tuple, allr[0])) & set(map(tuple, allr[1])))
    p(f"SETTINGS THAT REPAIR ON BOTH STACKS: {common if common else 'NONE'}")
    p("=" * 78)
    res["repairs_both"] = [list(c) for c in common]
    with open(os.path.join(OUT, "a10_results.json"), "w") as g1:
        json.dump(res, g1, indent=2)
    p("wrote out/a10_results.json")
    fh.close()


if __name__ == "__main__":
    main()
