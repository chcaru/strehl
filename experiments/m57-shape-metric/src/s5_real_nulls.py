"""M57 S5 -- real-data nulls whose truth is KNOWN, and the noise axis.

PR6 failed: the disjoint-subset contrast reads 0.19-0.54 px on every real cell.
That contrast has no ground truth on real data -- S2 measured the analogous
plant contrast and the ORACLE agreed with dsig to 0.0004 px, so a non-zero
reading there is not evidence of estimator error.  What is missing is a real
null whose truth is known EXACTLY.  Two exist, and neither needs ground truth
about the scene:

  N1  ADD INDEPENDENT NOISE to each half-merge.  The common transfer is
      untouched, so the true equivalent-blur difference is EXACTLY 0 px, on
      any scene, at any level.  A metric that confuses noise with resolution
      must move.  This is requirement 2 stated as a null instead of a contrast.

  N2  SCALE ONE HALF.  Fact 701 measures P_a/P_b = 1.30 on real half-merges;
      truth is EXACTLY 0 px.  (S3 ran this as PR7; repeated here across a
      wider range so the exponent, not just one point, is measured.)

RULE 39.  N1 and N2 are the nulls.  PR4's planted 0.10 px is the signal.  The
planted wrong answer is the claim "adding 3x the merged noise is worth at
least 0.02 px of resolution", which the harness must reject.

RULE 20 -- what makes this FAIL.  If |dsig| under N1 at 3x noise exceeds
0.02 px (a fifth of the planted signal, and the resolution difference the
project actually argues about) on any cell, K1 does not separate noise from
resolution on real data and the family is dead.

RULE 10.  The noise added is referenced to the MERGED temporal sigma, measured
from the profile model, never to a spatial standard deviation of the scene.
"""
import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m57lib as K  # noqa: E402

ROOT = r"D:\personal\macro"
PAD = 32
G, RN_E = 1.14469, 1.47
PLANT_SB = 0.10
ISO = 500

STACKS = {
    "112MSDCF": dict(rois={"flat": (2747, 32, 512, 512),
                           "detail": (1671, 1373, 512, 512)}, lo=6, hi=68),
    "113MSDCF": dict(rois={"flat": (2747, 32, 512, 512),
                           "centre": (916, 1501, 512, 512)}, lo=0, hi=63),
    "foam":     dict(rois={"flat": (2747, 32, 512, 512),
                           "centre": (916, 1501, 512, 512)}, lo=0, hi=62),
    "109MSDCF": dict(rois={"flat": (2747, 32, 512, 512),
                           "centre": (916, 1501, 512, 512)}, lo=0, hi=22),
}


def main():
    t0 = time.time()
    res = {}
    print("=" * 78)
    print("M57 S5 -- real-data nulls with KNOWN truth.  Flat ROI first (rule 9).")
    print(f"  profile.rs: g(ISO {ISO}) = {K.gain_dn_per_e(ISO):.5f} DN/e-, "
          f"read noise {K.read_noise_e(ISO):.4f} e- (M48-corrected value; the "
          f"merges above use m41lib's frozen {RN_E})")
    print("=" * 78)
    worst = 0.0
    worst_cell = None

    for sname, cfg in STACKS.items():
        files = sorted(glob.glob(os.path.join(ROOT, sname, "*.ARW")))
        files = files[cfg["lo"]:cfg["hi"]]
        for rname, roi in cfg["rois"].items():
            cube = K.load_cube(files, roi, pad=PAD)
            nf = cube.shape[0]
            fine, coarse, reg = K.L1.focus_fields(cube, G, RN_E)
            ia, ib = K.splits(nf)["parity"]
            ma, nea = K.merge_subset(cube, coarse, reg, ia, pad=PAD)
            mb, neb = K.merge_subset(cube, coarse, reg, ib, pad=PAD)
            lvl = float(np.median(ma))
            # rule 10: TEMPORAL sigma from the calibrated model, not a
            # spatial standard deviation of the scene.
            s1 = float(np.sqrt(K.M.noise_var_dn(lvl, K.gain_dn_per_e(ISO),
                                                K.read_noise_e(ISO))))
            sm = s1 / np.sqrt(nea)
            key = f"{sname}/{rname}"
            rs1 = K.RingStats(ma, mb)
            sig = K.dsig(rs1, K.RingStats(K.M.blur(ma, PLANT_SB),
                                          K.M.blur(mb, PLANT_SB)))
            print("\n" + "=" * 78)
            print(f"{key}   {nf} frames   level {lvl:.1f} DN   n_eff "
                  f"{nea:.3f}   single-frame sigma {s1:.3f} DN   merged "
                  f"{sm:.3f} DN   ({time.time()-t0:.0f}s)")
            print(f"  SIGNAL: planted {PLANT_SB} px blur -> dsig "
                  f"{K.fmt(sig['px'])} +- {sig['se_px']:.2e}")
            r = dict(n_eff=nea, level=lvl, sigma_merged=sm,
                     signal=sig["px"], signal_se=sig["se_px"])

            # ---------------------------------------------- N1 noise null
            print("  N1 NULL -- independent noise added to each half."
                  "  TRUTH IS EXACTLY 0 px.")
            print("      x merged sigma   added DN     dsig px     se(jack)"
                  "     |dsig|/signal")
            rng = np.random.default_rng(57_000 + abs(hash(key)) % 1000)
            n1 = {}
            for mult in (1.0, 2.0, 3.0):
                add = sm * mult
                aa = ma + rng.standard_normal(ma.shape).astype(np.float32) * add
                bb = mb + rng.standard_normal(mb.shape).astype(np.float32) * add
                d = K.dsig(rs1, K.RingStats(aa, bb))
                frac = abs(d["px"]) / abs(sig["px"])
                print(f"      {mult:14.1f}   {add:8.3f}   {K.fmt(d['px'])}"
                      f"   {d['se_px']:9.2e}   {frac:14.4f}")
                n1[f"{mult}"] = dict(dsig=d["px"], se=d["se_px"], added=add)
                if mult == 3.0 and np.isfinite(d["px"]):
                    if abs(d["px"]) > worst:
                        worst, worst_cell = abs(d["px"]), key
            r["n1"] = n1

            # ---- the matched-cost pair, on real data, in one table --------
            hp0 = K.L1.hp_sd(ma)
            hp_n = K.L1.hp_sd(ma + rng.standard_normal(ma.shape
                                                       ).astype(np.float32) * sm * 3)
            hp_b = K.L1.hp_sd(K.M.blur(ma, PLANT_SB))
            print(f"  matched-cost check on the SAME cell: hp_sd baseline "
                  f"{hp0:.4f}, +3x noise {hp_n:.4f} ({100*(hp_n/hp0-1):+.2f}%), "
                  f"{PLANT_SB} px blur {hp_b:.4f} ({100*(hp_b/hp0-1):+.2f}%)")
            r["hp"] = dict(base=hp0, noise3=hp_n, blur=hp_b)

            # ---------------------------------------------- N2 gain null
            print("  N2 NULL -- ONE half scaled (fact 701 measures 1.30 real)."
                  "  TRUTH IS EXACTLY 0 px.")
            print("      lambda     one-sided dsig px      both-sided dsig px")
            n2 = {}
            for lam in (1.10, 1.30, 3.00):
                d1 = K.dsig(K.RingStats(ma * lam, mb),
                            K.RingStats(K.M.blur(ma, PLANT_SB) * lam,
                                        K.M.blur(mb, PLANT_SB)))
                d2 = K.dsig(K.RingStats(ma * lam, mb * lam),
                            K.RingStats(K.M.blur(ma, PLANT_SB) * lam,
                                        K.M.blur(mb, PLANT_SB) * lam))
                print(f"      {lam:6.2f}     {d1['px']-sig['px']:+18.3e}"
                      f"     {d2['px']-sig['px']:+18.3e}")
                n2[f"{lam}"] = dict(one=d1["px"] - sig["px"],
                                    both=d2["px"] - sig["px"])
            r["n2"] = n2
            res[key] = r
            del cube, fine, coarse, reg

    print("\n" + "=" * 78)
    print(f"RULE 39 planted wrong answer: 'adding 3x the merged noise is worth"
          f" at least 0.02 px of resolution'")
    print(f"  worst |dsig| under N1 at 3x noise, over all cells: {worst:.5f} px"
          f"  ({worst_cell})")
    print(f"  -> claim {'SURVIVES' if worst >= 0.02 else 'REJECTED'}")
    print(f"  PR13 (N1) verdict: {'FAIL' if worst > 0.02 else 'PASS'}")
    print("=" * 78)
    res["_n1_worst"] = dict(px=worst, cell=worst_cell,
                            verdict="FAIL" if worst > 0.02 else "PASS")
    with open(os.path.join(K.OUT, "s5_real_nulls.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/s5_real_nulls.json  ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
