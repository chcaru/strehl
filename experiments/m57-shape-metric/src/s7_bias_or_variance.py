"""M57 S7 -- is the noise-null failure a BIAS or a VARIANCE?

S6 refuted the mechanism I derived.  K6 has no logarithm at all and failed the
noise null WORSE than K1 (0.464 px vs 0.343 px), so the Jensen term in
PREREGISTRATION-2.md section 2 is not the dominant cause.  Recording that the
derivation was wrong rather than quietly replacing it.

The distinction that remains matters more than the fix:

  BIAS      -- repeated independent noise draws have a non-zero MEAN.  The
               statistic is systematically wrong at real SNR and the family is
               dead.
  VARIANCE  -- the mean over draws is consistent with 0 and the scatter is
               large.  The statistic is CORRECT and UNDERPOWERED, the reported
               jackknife standard error is dishonest, and the remedy is a
               larger effective sample rather than a different statistic.

RULE 39.  This is the null's own standard error, which is what rule 39 asks for
and what S5 and S6 did not have: they each reported ONE draw.  A planted wrong
answer is included: the claim "the jackknife standard error is honest" is
tested by comparing it against the measured scatter across draws, and must be
rejected if the jackknife is anti-conservative.

PR19 (pre-registered in this docstring before the file ran).  Over R = 24
independent noise draws at each level, on the two cells that failed worst:
  (a) if |mean| > 3 x se(mean) at any level, the failure is a BIAS -> the whole
      cross-power-shape family is dead and that is the report;
  (b) if |mean| <= 3 x se(mean) and sd(draws) > 3 x median jackknife se, the
      failure is VARIANCE and the jackknife is anti-conservative -> the
      statistic survives, its published standard error does not.
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
PAD, G, RN_E, ISO = 32, 1.14469, 1.47, 500
PLANT_SB = 0.10
REPS = 24

CELLS = [
    ("109MSDCF", "centre", (916, 1501, 512, 512), 0, 22),   # worst in S5
    ("112MSDCF", "flat", (2747, 32, 512, 512), 6, 68),      # flat, rule 9
    ("112MSDCF", "detail", (1671, 1373, 512, 512), 6, 68),
]
CANDS = (("K1 dsig", K.dsig), ("K6 dsig_lin", K.dsig_lin))


def main():
    t0 = time.time()
    res = {}
    print("=" * 78)
    print("M57 S7 -- BIAS or VARIANCE?  R =", REPS, "independent noise draws.")
    print("  Truth is EXACTLY 0 px at every level.  PR19 decides.")
    print("=" * 78)

    for sname, rname, roi, lo, hi in CELLS:
        files = sorted(glob.glob(os.path.join(ROOT, sname, "*.ARW")))[lo:hi]
        cube = K.load_cube(files, roi, pad=PAD)
        nf = cube.shape[0]
        fine, coarse, reg = K.L1.focus_fields(cube, G, RN_E)
        ia, ib = K.splits(nf)["parity"]
        ma, nea = K.merge_subset(cube, coarse, reg, ia, pad=PAD)
        mb, _ = K.merge_subset(cube, coarse, reg, ib, pad=PAD)
        del cube, fine, coarse, reg
        lvl = float(np.median(ma))
        s1 = float(np.sqrt(K.M.noise_var_dn(lvl, K.gain_dn_per_e(ISO),
                                            K.read_noise_e(ISO))))
        sm = s1 / np.sqrt(nea)
        rs1 = K.RingStats(ma, mb)
        key = f"{sname}/{rname}"
        print("\n" + "=" * 78)
        print(f"{key}   {nf} frames   n_eff {nea:.3f}   merged sigma {sm:.3f} DN"
              f"   ({time.time()-t0:.0f}s)")
        sig = {nm: fn(rs1, K.RingStats(K.M.blur(ma, PLANT_SB),
                                       K.M.blur(mb, PLANT_SB)))
               for nm, fn in CANDS}
        for nm, _ in CANDS:
            print(f"  signal: planted {PLANT_SB} px -> {nm} "
                  f"{K.fmt(sig[nm]['px'])} +- {sig[nm]['se_px']:.2e}")
        print("=" * 78)
        print("   candidate      x sig    mean px    se(mean)    sd(draws)"
              "   median jack se   sd/jack   verdict")
        cell = {}
        for nm, fn in CANDS:
            for mult in (1.0, 2.0, 3.0):
                vals, jacks = [], []
                rng = np.random.default_rng(770000 + int(mult * 10)
                                            + abs(hash(key)) % 1000)
                for _ in range(REPS):
                    add = sm * mult
                    aa = ma + rng.standard_normal(ma.shape).astype(np.float32) * add
                    bb = mb + rng.standard_normal(mb.shape).astype(np.float32) * add
                    d = fn(rs1, K.RingStats(aa, bb))
                    if np.isfinite(d["px"]):
                        vals.append(d["px"])
                        jacks.append(d["se_px"])
                v = np.array(vals)
                if len(v) < 3:
                    print(f"   {nm:14s} {mult:6.1f}   too few finite draws "
                          f"({len(v)}/{REPS})")
                    continue
                mean = float(v.mean())
                sd = float(v.std(ddof=1))
                sem = sd / np.sqrt(len(v))
                mj = float(np.nanmedian(jacks))
                bias = abs(mean) > 3 * sem
                over = sd > 3 * mj
                verd = "BIAS" if bias else ("VARIANCE" if over else "ok")
                print(f"   {nm:14s} {mult:6.1f}  {mean:+10.5f}  {sem:10.5f}"
                      f"  {sd:11.5f}   {mj:14.5f}   {sd/mj:7.2f}   {verd}")
                cell[f"{nm}_{mult}"] = dict(mean=mean, se_mean=sem, sd=sd,
                                            jack=mj, n=len(v), verdict=verd)
        res[key] = cell

    # ---------------------------------------------------------- PR19 verdict
    print("\n" + "=" * 78)
    allv = [v for c in res.values() for v in c.values()]
    nbias = sum(1 for v in allv if v["verdict"] == "BIAS")
    nvar = sum(1 for v in allv if v["verdict"] == "VARIANCE")
    ratios = [v["sd"] / v["jack"] for v in allv]
    print(f"PR19 -- {len(allv)} (candidate, level, cell) combinations")
    print(f"  BIAS     (|mean| > 3 se(mean)) : {nbias}")
    print(f"  VARIANCE (sd > 3x jackknife se): {nvar}")
    print(f"  sd(draws) / jackknife se: min {min(ratios):.2f}  "
          f"median {np.median(ratios):.2f}  max {max(ratios):.2f}")
    print(f"  RULE 39 planted wrong answer: 'the jackknife standard error is "
          f"honest'")
    print(f"    -> {'REJECTED' if np.median(ratios) > 1.5 else 'SURVIVES'}"
          f" (a jackknife that were honest would give a ratio near 1)")
    print(f"  PR19 verdict: "
          f"{'BIAS -- family dead' if nbias else 'VARIANCE -- statistic survives, its published SE does not'}")
    print("=" * 78)
    res["_pr19"] = dict(n=len(allv), n_bias=nbias, n_var=nvar,
                        ratio_min=min(ratios), ratio_med=float(np.median(ratios)),
                        ratio_max=max(ratios),
                        verdict="BIAS" if nbias else "VARIANCE")
    with open(os.path.join(K.OUT, "s7_bias_or_variance.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/s7_bias_or_variance.json  ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
