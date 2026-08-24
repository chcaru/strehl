"""M92 S8 -- applying this milestone's own readability clause before its bars.

PREREGISTRATION section 3 says: "If the drop rate exceeds 10% on any stack the
arm is reported as unreadable."  Section 5 then sets numeric bars on `alpha` and
`Null(24)`.  Those two clauses collide on the real-dark arm, because the strict
NaN policy censors the high-N rungs on the noisy stacks -- `109MSDCF` drops
99.2% of (draw, subset) pairs at N = 24, so its `Null(24)` is a near-single
observation and its `alpha` is fitted partly on rungs that section 3 declares
unreadable.

This script resolves the collision in the open and in one direction only:
readability is decided FIRST, because it governs whether a number exists at all,
and the bars are then applied to the rungs that survive.  Both the full-ladder
and readable-ladder exponents are reported for every arm so the effect of the
restriction is visible rather than assumed.

It also emits the derived consistency check tying the measured cross-ROI
correlation to the measured global variance fraction:

    rbar_pred = (g - 1/m) / (1 - 1/m)

where `g` = Var_r(mean_i d[i,r]) / mean_i Var_r(d[i,r]) is S6's `global %` and
`m` is the ROI count.  Under independence `g -> 1/m` and `rbar_pred -> 0`.
Agreement between `rbar_pred` and the directly measured `rbar` is evidence that
the coupling really is the single per-draw global scalar S6's demeaning
identified, and not something the correlation estimator is inventing.

Reads only what S2/S3/S6 already wrote.  Runs no null draws.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402

E = 0.1754          # M82's largest finite central sharpness price, fact 1140
DROP_BAR = 0.10     # PREREGISTRATION section 3
FATAL = 0.15        # PREREGISTRATION section 5, NO SHIP
SHIP = 0.40         # PREREGISTRATION section 5, SHIP


def fit(ns, rms):
    x = np.log10(np.asarray(ns, float))
    y = -np.log10(np.asarray(rms, float))
    if len(x) < 3:
        return np.nan, np.nan
    a, b = np.polyfit(x, y, 1)
    yh = a * x + b
    ss = float(((y - yh) ** 2).sum())
    st = float(((y - y.mean()) ** 2).sum())
    return float(a), (1 - ss / st if st > 0 else np.nan)


def main():
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    s3 = json.load(open(os.path.join(M92.OUT, "s3_dark_corr.json")))
    s2 = json.load(open(os.path.join(M92.OUT, "s2_null_averaging.json")))
    s6 = json.load(open(os.path.join(M92.OUT, "s6_slope_native.json")))

    log("=" * 78)
    log("M92 S8 -- readability applied BEFORE the bars.")
    log(f"  a rung is readable if its (draw,subset) drop rate <= {DROP_BAR:.0%}")
    log(f"  E = {E} px (M82 largest finite price)   fatal alpha < {FATAL}"
        f"   SHIP alpha >= {SHIP}")
    log("=" * 78)

    rows = []
    for tag, blob in (("S3", s3), ("S2", s2)):
        for stack, srec in sorted(blob.items()):
            for arm, rec in srec.get("arms", {}).items():
                lad = rec.get("ladder")
                if not lad:
                    continue
                key = f"{stack} | {arm}"
                ns = sorted(int(k) for k in lad)
                rd = [(n, lad[str(n)]) for n in ns]
                keep = [(n, e) for n, e in rd
                        if e.get("drop_frac", 1.0) <= DROP_BAR]
                full_a, full_r2 = fit([n for n, _ in rd],
                                      [e["rms"] for _, e in rd])
                if len(keep) >= 3:
                    ka, kr2 = fit([n for n, _ in keep],
                                  [e["rms"] for _, e in keep])
                else:
                    ka, kr2 = np.nan, np.nan
                nmax = keep[-1][0] if keep else 0
                n1 = lad[str(ns[0])]["rms"]
                cp = rec.get("corr_pairwise") or rec.get("corr") or {}
                rbar = cp.get("rbar", np.nan)
                rows.append(dict(tag=tag, key=key, full_alpha=full_a,
                                 full_r2=full_r2, read_alpha=ka, read_r2=kr2,
                                 n_readable=nmax, n_rungs=len(keep), null1=n1,
                                 null_at_max=(keep[-1][1]["rms"] if keep
                                              else np.nan),
                                 rbar=rbar))

    log("")
    log(f"  {'arm':>44} {'a full':>7} {'a read':>7} {'Nmax':>5} {'rungs':>6}"
        f" {'Null(1)':>8} {'Null(Nmax)':>11} {'floor':>7}")
    for r in rows:
        rb = r["rbar"]
        fl = (r["null1"] * np.sqrt(max(rb, 0.0))
              if rb is not None and np.isfinite(rb) else np.nan)
        log(f"  {r['key']:>44} {r['full_alpha']:>7.4f} {r['read_alpha']:>7.4f}"
            f" {r['n_readable']:>5d} {r['n_rungs']:>6d} {r['null1']:>8.5f}"
            f" {r['null_at_max']:>11.5f} {fl:>7.5f}")

    log("")
    log("=" * 78)
    log("  DERIVED consistency check: does the measured cross-ROI correlation")
    log("  equal what S6's global variance fraction predicts?")
    log("    rbar_pred = (g - 1/m) / (1 - 1/m),  g = S6 global %, m = 24 ROIs")
    log("  Independence gives g = 1/m = 4.167% and rbar_pred = 0.")
    log("=" * 78)
    log(f"  {'matrix':>34} {'g %':>7} {'rbar_pred':>10} {'rbar meas':>10}"
        f" {'diff':>8}")
    dd = []
    for name, v in sorted(s6.items()):
        g = v.get("global_var_frac")
        rm = v.get("rbar_pairwise")
        if g is None or rm is None or not np.isfinite(rm):
            continue
        m = v["n_roi"]
        pred = (g - 1.0 / m) / (1.0 - 1.0 / m)
        dd.append(pred - rm)
        log(f"  {name:>34} {100*g:>7.2f} {pred:>+10.5f} {rm:>+10.5f}"
            f" {pred-rm:>+8.5f}")
    dd = np.array(dd)
    log("")
    log(f"  across {len(dd)} matrices: median |pred - measured| ="
        f" {np.median(np.abs(dd)):.5f}, max = {np.abs(dd).max():.5f}")

    log("")
    log("=" * 78)
    log("  SENSITIVITY CLAUSE (section 4) resolved in slope-native coordinates.")
    log("  alpha_b and alpha_px live in the same coordinate; alpha_sqrt is")
    log("  alpha_b/2 by arithmetic.  A disagreement about INDEPENDENCE would")
    log("  show as alpha_b != alpha_px, not as alpha_sqrt != alpha_px.")
    log("=" * 78)
    d = np.array([abs(v["alpha_b"] - v["alpha_px"]) for v in s6.values()
                  if np.isfinite(v.get("alpha_b", np.nan))
                  and np.isfinite(v.get("alpha_px", np.nan))])
    rr = np.array([v["ratio_to_half"] for v in s6.values()
                   if np.isfinite(v.get("ratio_to_half", np.nan))])
    log(f"  |alpha_b - alpha_px| over {len(d)} matrices:"
        f" median {np.median(d):.4f}  max {d.max():.4f}")
    log(f"  alpha_sqrt / (alpha_b/2)  over {len(rr)} matrices:"
        f" median {np.median(rr):.4f}  range {rr.min():.4f}..{rr.max():.4f}")

    log("")
    log("=" * 78)
    log("  N required for Null(N) < E, readable rungs only, real-dark arm.")
    log("=" * 78)
    for stack, srec in sorted(s3.items()):
        for arm, rec in srec.get("arms", {}).items():
            if "A2 dark / disjoint" != arm:
                continue
            lad = rec["ladder"]
            ns = sorted(int(k) for k in lad)
            got = None
            for n in ns:
                e = lad[str(n)]
                if e.get("drop_frac", 1.0) <= DROP_BAR and e["rms"] < E:
                    got = n
                    break
            allrung = next((n for n in ns if lad[str(n)]["rms"] < E), None)
            nm = rec.get("ladder_nanmean", {})
            nmreq = next((n for n in ns
                          if nm.get(str(n), {}).get("rms", 9e9) < E), None)
            log(f"  {stack:>16}  N_req(readable) = {got}"
                f"   N_req(any rung) = {allrung}"
                f"   N_req(NaN-tolerant) = {nmreq}")

    out = dict(rows=rows, drop_bar=DROP_BAR, E=E)
    with open(os.path.join(M92.OUT, "s8_readable.json"), "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    with open(os.path.join(M92.OUT, "s8_readable.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\nwrote out/s8_readable.{json,log}")


if __name__ == "__main__":
    main()
