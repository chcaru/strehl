"""Self-measured vs shipped: the comparison the transfer objection turns on.

Reads the per-stack fits from `c1_lateral.py` and lays them beside the shipped
`a7c2-fe100gm-2xtc-x4cpl` record, which carries eps_r = -704.5e-6, eps_b = None
(blue is an exact no-op) and, in the form that is actually applied, no
translation.

Three questions:

1. Does the self-measured coefficient agree with the shipped one on the two
   stacks the shipped one was fitted on? If self-measurement cannot reproduce an
   in-sample fit it has no business replacing an out-of-sample one.
2. How much does the true coefficient vary between stacks? That variation is the
   size of the error a transferred scalar commits, and it is the whole reason the
   correction is off by default.
3. Is the residual variation small enough that transfer would have been fine
   after all -- in which case self-measurement is unnecessary -- or large enough
   that it is not?

Every row carries the G1-vs-G2 null fitted by the identical code path, and both
the raw and the null-corrected coefficient, in the same table (rule 3).
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

SHIPPED_EPS_R = -704.5e-6
PPM = 1e6
STACKS = ["tweezers-cpl", "bee-3-cpl", "coffee-bean", "lavendar-cpl",
          "couch-fibers-cpl", "bee-2-cpl"]
IN_SAMPLE = {"tweezers-cpl", "bee-3-cpl"}


def load(stack):
    with open(os.path.join(common.OUT, "json", f"c1_lateral_{stack}.json")) as fh:
        return json.load(fh)


def main():
    out = {"shipped_eps_r": SHIPPED_EPS_R, "stacks": {}}
    js = {s: load(s) for s in STACKS}

    print("=" * 108)
    print("SELF-MEASURED LATERAL CA, PER STACK")
    print("shipped profile: eps_R = -704.5 ppm, eps_B = None (blue uncorrected), "
          "translation not applied")
    print("=" * 108)
    print(f"{'stack':>18} {'in-samp':>8} {'n':>5} "
          f"{'eps_R raw':>10} {'null':>8} {'eps_R corr':>11} {'CI':>21} "
          f"{'R2':>6} {'vs shipped':>11}")
    rows = []
    for s in STACKS:
        h = js[s]["headline"]
        R, G2 = h["R"], h["G2"]
        rel = 100.0 * (R["eps_null_corrected"] - SHIPPED_EPS_R) / abs(SHIPPED_EPS_R)
        ci = f"[{R['eps_lo']*PPM:7.1f},{R['eps_hi']*PPM:7.1f}]"
        print(f"{s:>18} {'YES' if s in IN_SAMPLE else '-':>8} {R['n']:5d} "
              f"{R['eps']*PPM:10.1f} {G2['eps']*PPM:8.1f} "
              f"{R['eps_null_corrected']*PPM:11.1f} {ci:>21} "
              f"{R['r2']:6.3f} {rel:+10.1f}%")
        rows.append({"stack": s, "in_sample": s in IN_SAMPLE,
                     "n": R["n"], "eps_r_raw": R["eps"],
                     "null": G2["eps"], "eps_r": R["eps_null_corrected"],
                     "eps_lo": R["eps_lo"], "eps_hi": R["eps_hi"],
                     "r2": R["r2"], "perm_p": R["perm_p"],
                     "rel_to_shipped_pct": rel})
    out["stacks"]["R"] = rows

    print()
    print(f"{'stack':>18} {'n':>5} "
          f"{'eps_B raw':>10} {'null':>8} {'eps_B corr':>11} {'CI':>21} "
          f"{'R2':>6} {'flat over gate?':>16}")
    rowsb = []
    for s in STACKS:
        h = js[s]["headline"]
        B, G2 = h["B"], h["G2"]
        lad = [r for r in js[s]["ladder"] if r["label"].startswith("B@")
               and r["gate"] >= 5e4]
        vals = np.array([r["eps_null_corrected"] for r in lad])
        spread = (100.0 * (vals.max() - vals.min()) / abs(np.median(vals))
                  if len(vals) and np.median(vals) != 0 else float("nan"))
        ci = f"[{B['eps_lo']*PPM:7.1f},{B['eps_hi']*PPM:7.1f}]"
        print(f"{s:>18} {B['n']:5d} {B['eps']*PPM:10.1f} {G2['eps']*PPM:8.1f} "
              f"{B['eps_null_corrected']*PPM:11.1f} {ci:>21} {B['r2']:6.3f} "
              f"{spread:14.0f}%")
        rowsb.append({"stack": s, "n": B["n"], "eps_b_raw": B["eps"],
                      "null": G2["eps"], "eps_b": B["eps_null_corrected"],
                      "eps_lo": B["eps_lo"], "eps_hi": B["eps_hi"],
                      "r2": B["r2"], "perm_p": B["perm_p"],
                      "gate_spread_pct": spread})
    out["stacks"]["B"] = rowsb

    # ---- the transfer arithmetic ----------------------------------------
    print()
    print("=" * 108)
    print("WHAT TRANSFER COSTS")
    print("=" * 108)
    er = np.array([r["eps_r"] for r in rows])
    print(f"eps_R across {len(er)} stacks: median {np.median(er)*PPM:.1f} ppm, "
          f"range [{er.min()*PPM:.1f}, {er.max()*PPM:.1f}] ppm, "
          f"spread {100*(er.max()-er.min())/abs(np.median(er)):.0f}% of median")
    print(f"shipped scalar is {SHIPPED_EPS_R*PPM:.1f} ppm\n")
    print("If a single scalar is applied to every stack, the residual "
          "aberration left behind\nis |eps_true - eps_applied| * r. At the "
          "corner (r = 1 in normalised field height,\n2112 plane px) that is:\n")
    print(f"{'stack':>18} {'eps_true':>10} {'left by shipped':>16} "
          f"{'left by self':>13} {'left by median':>15}")
    med = float(np.median(er))
    resid = []
    for r in rows:
        e = r["eps_r"]
        halfdiag = 2112.0
        a = abs(e - SHIPPED_EPS_R) * halfdiag
        b = 0.0
        c = abs(e - med) * halfdiag
        print(f"{r['stack']:>18} {e*PPM:10.1f} {a:14.3f}px {b:11.3f}px "
              f"{c:13.3f}px")
        resid.append({"stack": r["stack"], "shipped_px": a, "self_px": b,
                      "median_px": c})
    out["corner_residual_px"] = resid
    ships = np.array([r["shipped_px"] for r in resid])
    meds = np.array([r["median_px"] for r in resid])
    print(f"\n{'mean':>18} {'':>10} {ships.mean():14.3f}px {0.0:11.3f}px "
          f"{meds.mean():13.3f}px")
    print(f"{'worst':>18} {'':>10} {ships.max():14.3f}px {0.0:11.3f}px "
          f"{meds.max():13.3f}px")
    out["shipped_mean_residual_px"] = float(ships.mean())
    out["median_mean_residual_px"] = float(meds.mean())

    # ---- in-sample reproduction -----------------------------------------
    print()
    print("=" * 108)
    print("IN-SAMPLE REPRODUCTION")
    print("=" * 108)
    ins = [r for r in rows if r["in_sample"]]
    print("M107 fitted -704.5 ppm on tweezers-cpl and bee-3-cpl jointly. "
          "Measuring each\nseparately with an independent instrument gives:")
    for r in ins:
        print(f"  {r['stack']:>16}  {r['eps_r']*PPM:8.1f} ppm  "
              f"({r['rel_to_shipped_pct']:+.1f}% vs the joint fit)")
    two = np.array([r["eps_r"] for r in ins])
    print(f"  {'joint mean':>16}  {two.mean()*PPM:8.1f} ppm  "
          f"({100*(two.mean()-SHIPPED_EPS_R)/abs(SHIPPED_EPS_R):+.1f}%)")
    print(f"\nThe two stacks M107 pooled differ from each other by "
          f"{100*abs(two[0]-two[1])/abs(two.mean()):.0f}%.")
    print("That is the transfer problem stated in the units of the thing being "
          "transferred:\na scalar fitted jointly on two scenes that disagree by "
          "that much cannot describe\neither of them, let alone a third.")
    out["in_sample"] = {"stacks": [r["stack"] for r in ins],
                        "eps": [r["eps_r"] for r in ins],
                        "mean": float(two.mean())}

    # ---- null behaviour, and rule 4 --------------------------------------
    print()
    print("=" * 108)
    print("THE NULL (rule 3: reported beside every number above; rule 4: checked "
          "on the binning axis)")
    print("=" * 108)
    print(f"{'stack':>18} {'null eps':>9} {'null CI':>21} {'null rms px':>12} "
          f"{'null radial trend (detrans, ppm by annulus)':>46}")
    for s in STACKS:
        h = js[s]["headline"]
        G2 = h["G2"]
        ci = f"[{G2['eps_lo']*PPM:7.1f},{G2['eps_hi']*PPM:7.1f}]"
        tr = "  ".join(f"{b['eps_detrans']*PPM:+.0f}" for b in G2["radial"])
        print(f"{s:>18} {G2['eps']*PPM:9.1f} {ci:>21} {G2['rms']:12.4f} "
              f"{tr:>46}")
    print("\nThe null is fitted by the identical code path on the identical "
          "tiles. It is not\nan additive-random stand-in: G1 and G2 are two real "
          "lattices at one wavelength,\nso the null shares the treatment's "
          "correlation length, its radial profile and its\nsampling geometry, and "
          "differs from it only in carrying no chromatic signal.")

    common.dump("c2_compare", out)
    print("\nwrote c2_compare.json")


if __name__ == "__main__":
    main()
