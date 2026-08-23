"""M57 S4 -- the MODEL-VIOLATION DIAGNOSTIC.

POST-HOC.  This statistic did not exist when PREREGISTRATION.md was committed.
It was designed AFTER S1 measured K1 failing PR1 on the PM_M ladder, and it is
labelled post-hoc everywhere it appears.  Its own kill condition is
pre-registered here, in this docstring, before it was run:

  PR12 (post-hoc, pre-registered before running).  `gof` = residual RMS of the
  dsig log-ratio fit divided by the log-ratio sweep the fitted Gaussian
  accounts for.  It is USEFUL only if, at every rung where K1's sign is wrong
  on the PM_M ladder, gof is at least 3x its value for a genuine Gaussian blur
  producing the same |dsig|.  If a PM_M rung that fools K1 has a gof
  indistinguishable from honest blur, PR12 fails and the diagnostic is
  discarded rather than reported as a safeguard.

RULE 18 -- how the diagnostic itself can be fooled.  An adversary who injects
COMMON structure with an exactly Gaussian spectral shape produces a small gof
and a wrong dsig.  The diagnostic detects SHAPE violation, not injection.  It
cannot make K1 safe against a shape-matched adversary and is not claimed to.

RULE 39.  Every comparison here is against the matched honest-blur control at
the same |dsig|, which is the null, plus a planted wrong answer.
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m57lib as K  # noqa: E402


def solve_inc(fn, target, lo=0.0, hi=64.0, it=48):
    """Bisect an INCREASING function for fn(x) = target.

    M55 e5's `solve_sb` bisects a DECREASING function (blur lowers hp_sd).  The
    PM_M amplitude search is the opposite direction and reusing that helper
    silently returns 0, which is how the first run of this file reported a
    `fake amp` of 0.0000 in every row.  Recorded here rather than quietly fixed.
    """
    for _ in range(it):
        mid = 0.5 * (lo + hi)
        if fn(mid) > target:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def main():
    t0 = time.time()
    m46out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "m46-detail-metric", "out")
    z = np.load(os.path.join(m46out, "b1_merges.npz"))
    b1 = json.load(open(os.path.join(m46out, "b1_results.json")))
    g, rn_e = b1["rois"]["g"], b1["rois"]["rn_e"]
    PAD = 32
    print("=" * 78)
    print("M57 S4 -- POST-HOC model-violation diagnostic `gof` (PR12)")
    print("=" * 78)
    print("  gof = residual RMS of the log[C2/C1] fit, divided by the sweep the")
    print("  fitted Gaussian accounts for.  Dimensionless.  0 = the two")
    print("  configurations really do differ by a Gaussian.")
    res = {}

    for roi, ne_key in (("flat", "112_flat"), ("detail", "112_detail")):
        lat = z[("f112" if roi == "flat" else "d112")].astype(np.float32)
        lat = lat[PAD:-PAD, PAD:-PAD] if lat.shape[0] > 512 else lat
        n_eff = b1["n_eff"][ne_key]
        rho = b1["twocap"]["flat"]["at_fsig"] / (1 - b1["twocap"]["flat"]["at_fsig"]) \
            / b1["n_eff"]["112_flat"]
        lvl = float(np.median(lat))
        sig1 = float(np.sqrt(K.M.noise_var_dn(lvl, g, rn_e)))
        sig_m = sig1 / np.sqrt(n_eff)
        fpn = K.M.make_fpn(lat.shape, 4242, np.sqrt(rho) * sig1)
        rng = np.random.default_rng(90210)

        def pair(sb, fake=0.0, fseed=17):
            """PM_M: destroy resolution by `sb`, then add a fixed texture COMMON
            to both halves at amplitude `fake` (M55 section 3.1)."""
            base = K.M.blur(lat, sb) if sb > 0 else lat
            if fake > 0:
                fr = np.random.default_rng(fseed)
                t = fr.standard_normal(lat.shape).astype(np.float32)
                t = t - K.M.blur(t, 1.0)                 # high-pass texture
                t = t / float(np.std(t)) * fake
                base = base + t
            a = base + fpn + rng.standard_normal(lat.shape).astype(np.float32) * sig_m
            b = base + fpn + rng.standard_normal(lat.shape).astype(np.float32) * sig_m
            return K.RingStats(a, b)

        rs0 = pair(0.0)
        base_hp = K.L1.hp_sd(lat)
        print("\n" + "-" * 78)
        print(f"  ROI {roi}   level {lvl:.1f} DN   baseline hp_sd {base_hp:.4f} DN")
        print("-" * 78)
        print("     source                sb    fake amp   true MTF(f_sig)"
              "     dsig px       gof      gof/honest")
        rows = {}
        honest = {}
        # ---- honest Gaussian blur: the CONTROL / null for the diagnostic ---
        for sb in (0.25, 0.50, 1.00, 2.00):
            d = K.dsig(rs0, pair(sb))
            honest[sb] = d
            print(f"     honest Gaussian {sb:7.2f}      0.0000"
                  f"      {K.gauss_mtf(K.F_SIG, sb):12.6f}   {K.fmt(d['px'])}"
                  f"  {K.fmt(d['gof'],9,5)}        1.000")
            rows[f"honest_{sb}"] = dict(dsig=d["px"], gof=d["gof"])
        # ---- PM_M: same blur, plus a common texture matched on hp_sd -------
        for sb in (0.25, 0.50, 1.00, 2.00):
            def hp_of(amp, sb=sb):
                fr = np.random.default_rng(17)
                t = fr.standard_normal(lat.shape).astype(np.float32)
                t = t - K.M.blur(t, 1.0)
                t = t / float(np.std(t)) * amp
                return K.L1.hp_sd(K.M.blur(lat, sb) + t)
            amp = solve_inc(hp_of, base_hp)
            d = K.dsig(rs0, pair(sb, fake=amp))
            ratio = d["gof"] / honest[sb]["gof"] if honest[sb]["gof"] else np.nan
            print(f"     PM_M adversary  {sb:7.2f} {amp:11.4f}"
                  f"      {K.gauss_mtf(K.F_SIG, sb):12.6f}   {K.fmt(d['px'])}"
                  f"  {K.fmt(d['gof'],9,5)}   {ratio:10.2f}")
            rows[f"pmm_{sb}"] = dict(dsig=d["px"], gof=d["gof"], amp=amp,
                                     gof_ratio=ratio)
        # ---- the PR12 verdict ----------------------------------------------
        bad = [sb for sb in (0.25, 0.50, 1.00, 2.00)
               if not np.isnan(rows[f"pmm_{sb}"]["dsig"])
               and rows[f"pmm_{sb}"]["dsig"] < honest[sb]["px"] * 0.5]
        print(f"     rungs where PM_M fools K1 (dsig < half the honest value):"
              f" {bad}")
        if bad:
            worst = min(rows[f"pmm_{sb}"]["gof_ratio"] for sb in bad)
            print(f"     PR12 requires gof/honest >= 3 at EVERY such rung."
                  f"  Worst is {worst:.2f} -> "
                  f"{'PASS' if worst >= 3 else 'FAIL'}")
            rows["pr12_worst_ratio"] = worst
            rows["pr12"] = "PASS" if worst >= 3 else "FAIL"
        else:
            print("     PR12 vacuous on this ROI: PM_M did not fool K1 here.")
            rows["pr12"] = "vacuous"

        # ---- pillbox: the OTF-zero case S1 found (PR8) ----------------------
        print("\n     real defocus (pillbox), where S1 found K1 non-monotone:")
        print("       r px   zeros in band     dsig px       gof")
        for r in (0.5, 1.0, 2.0, 3.0, 5.0):
            a = K.pillbox_blur(lat, r) + fpn \
                + rng.standard_normal(lat.shape).astype(np.float32) * sig_m
            b = K.pillbox_blur(lat, r) + fpn \
                + rng.standard_normal(lat.shape).astype(np.float32) * sig_m
            d = K.dsig(rs0, K.RingStats(a, b))
            nz = int(np.floor(K.F_HI / (0.6098 / r))) if r > 0 else 0
            print(f"       {r:5.2f} {nz:13d}    {K.fmt(d['px'])} {K.fmt(d['gof'],9,5)}")
            rows[f"pillbox_{r}"] = dict(dsig=d["px"], gof=d["gof"], zeros=nz)

        # ---- RULE 39 planted wrong answer for the diagnostic itself --------
        hg = [honest[sb]["gof"] for sb in (0.25, 0.50, 1.00, 2.00)]
        pg = [rows[f"pmm_{sb}"]["gof"] for sb in (0.25, 0.50, 1.00, 2.00)]
        print(f"\n     RULE 39 planted wrong answer: the claim 'gof cannot tell"
              f" PM_M from honest blur'")
        print(f"       honest gof range [{min(hg):.5f}, {max(hg):.5f}],"
              f"  PM_M gof range [{min(pg):.5f}, {max(pg):.5f}]"
              f"  -> claim {'SURVIVES' if max(hg) >= min(pg) else 'REJECTED'}")
        rows["honest_gof_range"] = [min(hg), max(hg)]
        rows["pmm_gof_range"] = [min(pg), max(pg)]
        res[roi] = rows

    with open(os.path.join(K.OUT, "s4_diagnostic.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/s4_diagnostic.json  ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
