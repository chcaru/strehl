"""Leave-one-out transfer: is a self-measured coefficient better than a fixed one?

THE QUESTION. The shipped lateral-CA correction is off by default for exactly one
reason, recorded in `optics.rs`: a coefficient fitted on `tweezers-cpl` recovered
95.0% of the in-sample reduction on `bee-3-cpl`, but the reverse direction
recovered only 54.1% against a registered 60% bar. Fact 52 stands as the general
warning against transferring a scalar fitted on one scene. A coefficient measured
on the stack being rendered is not a transferred coefficient, so the objection
does not apply to it -- IF self-measurement is actually more accurate than the
best available fixed number. This asks that, out of sample.

THE STATISTIC IS A DISPLACEMENT, NOT A COEFFICIENT. Applying `e_app` to a stack
whose true coefficient is `e_true` leaves a residual scale error `e_true - e_app`,
which at field radius `r` is a residual displacement `|e_true - e_app| * r` plane
px. That is the thing a reader can see at 100%, it is linear in the error, and it
does not flatter a small coefficient the way a percentage would. Reported at the
plane corner, r = 2112 px, which is normalised field height 1.0.

WHY EVERY FIXED ARM IS LEAVE-ONE-OUT. A "best fixed coefficient" chosen using the
target stack's own measurement is not a fixed coefficient, it is a self-measured
one wearing a disguise, and it would win by construction. Every fixed arm here is
computed from the OTHER five stacks only.

WHAT SELF-MEASUREMENT'S RESIDUAL ACTUALLY IS -- and this is the part that keeps
the table honest. Self-measurement is not exact. It has two error terms:

  ATTENUATION  c4 planted +1000 ppm per stack and read back 0.69-0.94 of it, so
               the raw estimate is systematically short by a stack-dependent
               factor. The `self naive` arm carries that error in full; it is
               what shipping the raw number would actually do.
  DISPERSION   after de-attenuation what is left is the sampling error, which the
               tile bootstrap already measured. The `self de-attenuated` arm
               carries the bootstrap CI half-width as its residual.

`e_true` is taken to be the de-attenuated estimate. That makes the de-attenuated
arm's residual a statement about its own precision rather than a measurement of
its accuracy, and the table says so rather than quietly scoring it zero. The
independent evidence that the de-attenuated number is the accurate one is the c4
dose ladder and the c0 planted recovery, not this table.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

SHIPPED_EPS_R = -704.5e-6
SHIPPED_EPS_B = None          # the record carries None: blue is an exact no-op
R_CORNER = 2112.0             # plane px; normalised field height 1.0
PPM = 1e6

STACKS = ["tweezers-cpl", "bee-3-cpl", "coffee-bean", "lavendar-cpl",
          "couch-fibers-cpl", "bee-2-cpl"]
# The two the shipped profile was fitted on. Transfer INTO these is in-sample
# for the shipped arm and is flagged as such rather than averaged in silently.
IN_SAMPLE = {"tweezers-cpl", "bee-3-cpl"}


def load():
    with open(os.path.join(common.OUT, "json", "c4_attenuation.json")) as fh:
        recov = {r["stack"]: r["recovery"] for r in json.load(fh)["dose"]}
    rows = {}
    for st in STACKS:
        with open(os.path.join(common.OUT, "json",
                               f"c1_lateral_{st}.json")) as fh:
            h = json.load(fh)["headline"]
        d = {"stack": st, "recovery": recov[st]}
        for ch in ("R", "B"):
            e = h[ch]["eps_null_corrected"]
            lo, hi = h[ch]["eps_lo"], h[ch]["eps_hi"]
            d[ch] = {
                "raw": e,
                # c4's dose ladder was planted on RED only. Reusing red's
                # recovery for blue assumes the attenuation is a property of the
                # stack's structure rather than of the channel. That is the same
                # gate, the same tiles and the same green reference for both, so
                # it is defensible -- but it is an assumption, not a measurement,
                # and blue's numbers here inherit it.
                "true": e / recov[st],
                # The bootstrap CI is on the raw estimate; de-attenuating scales
                # it by the same factor, so the half-width scales too.
                "half_ci": 0.5 * abs(hi - lo) / recov[st],
            }
        rows[st] = d
    return rows


def px(e_err):
    return abs(e_err) * R_CORNER


def main():
    rows = load()
    out = {"r_corner_plane_px": R_CORNER, "channels": {}}

    for ch in ("R", "B"):
        shipped = SHIPPED_EPS_R if ch == "R" else SHIPPED_EPS_B
        print("=" * 104)
        print(f"CHANNEL {ch}   residual displacement at the plane corner "
              f"(r = {R_CORNER:.0f} px), in plane px. Lower is better.")
        print("=" * 104)
        hdr = (f"{'target':>18} {'e_true':>9} {'off':>7} {'shipped':>9} "
               f"{'LOO med':>8} {'LOO worst':>10} {'LOO mean':>9} "
               f"{'self naive':>11} {'self deatt':>11}")
        print(hdr)
        recs = []
        for st in STACKS:
            e_true = rows[st][ch]["true"]
            e_raw = rows[st][ch]["raw"]
            others = [rows[o][ch]["true"] for o in STACKS if o != st]
            loo_med = float(np.median(others))
            loo_each = [px(e_true - o) for o in others]
            r = {
                "target": st,
                "e_true_ppm": e_true * PPM,
                "off": px(e_true),
                "shipped": px(e_true - shipped) if shipped is not None
                           else px(e_true),
                "shipped_in_sample": st in IN_SAMPLE,
                "loo_median": px(e_true - loo_med),
                "loo_worst": max(loo_each),
                "loo_mean": float(np.mean(loo_each)),
                "self_naive": px(e_true - e_raw),
                "self_deatt": rows[st][ch]["half_ci"] * R_CORNER,
            }
            recs.append(r)
            flag = "*" if r["shipped_in_sample"] else " "
            print(f"{st:>18} {e_true*PPM:9.1f} {r['off']:7.3f} "
                  f"{r['shipped']:8.3f}{flag} {r['loo_median']:8.3f} "
                  f"{r['loo_worst']:10.3f} {r['loo_mean']:9.3f} "
                  f"{r['self_naive']:11.3f} {r['self_deatt']:11.3f}")
        if shipped is None:
            print(f"   (shipped column == off: the record carries eps_b = None, "
                  f"so blue is an exact no-op)")
        else:
            print("   * shipped was fitted on this stack; that column is "
                  "in-sample for it and is not a transfer result")

        def col(k):
            return float(np.mean([r[k] for r in recs]))

        print(f"\n   mean over all six  off {col('off'):.3f}  "
              f"shipped {col('shipped'):.3f}  LOO-median {col('loo_median'):.3f}"
              f"  LOO-worst {col('loo_worst'):.3f}  "
              f"self-naive {col('self_naive'):.3f}  "
              f"self-deatt {col('self_deatt'):.3f}")
        oos = [r for r in recs if not r["shipped_in_sample"]]
        if oos and shipped is not None:
            print(f"   mean over the four OUT-OF-SAMPLE stacks  "
                  f"off {np.mean([r['off'] for r in oos]):.3f}  "
                  f"shipped {np.mean([r['shipped'] for r in oos]):.3f}  "
                  f"LOO-median {np.mean([r['loo_median'] for r in oos]):.3f}  "
                  f"self-naive {np.mean([r['self_naive'] for r in oos]):.3f}  "
                  f"self-deatt {np.mean([r['self_deatt'] for r in oos]):.3f}")
        print()
        out["channels"][ch] = {"rows": recs,
                               "shipped_eps_ppm": None if shipped is None
                               else shipped * PPM}

    # The directional pair optics.rs actually names, reproduced with my numbers.
    print("=" * 104)
    print("THE PAIR optics.rs NAMES, redone with self-measured coefficients")
    print("=" * 104)
    print("optics.rs records: tweezers->bee-3 recovered 95.0% in-sample-donor,")
    print("bee-3->tweezers recovered 54.1% against a registered 60% bar. Same")
    print("two stacks, my coefficients, as a fraction of the aberration removed:")
    pair = []
    for donor, targ in (("tweezers-cpl", "bee-3-cpl"),
                        ("bee-3-cpl", "tweezers-cpl")):
        for ch in ("R", "B"):
            et = rows[targ][ch]["true"]
            ed = rows[donor][ch]["true"]
            frac = 1.0 - abs(et - ed) / abs(et)
            pair.append({"donor": donor, "target": targ, "ch": ch,
                         "removed_frac": frac})
            print(f"   {ch}  {donor:>16} -> {targ:<16} removes "
                  f"{100*frac:6.1f}%   (residual {px(et-ed):.3f} px at corner)")
    out["named_pair"] = pair

    common.dump("c5_transfer", out)
    print("\nwrote c5_transfer.json")


if __name__ == "__main__":
    main()
