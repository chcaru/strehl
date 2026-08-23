"""M23 - the per-edge response R itself, and gate (b).

Reports, per stack / span / delta:
  * the two-sided response R and its spread across edges;
  * the one-sided responses, which is what M10 P7 published (consistency check);
  * the delta-dependence criterion registered in PREREGISTRATION.md section 1.2;
  * N3, the self-pair null: real content, zero defocus difference, same
    resampler, same plant, true R = 1 by construction.

Run:  python m23_response.py > out\\response.txt
"""

import numpy as np

from m23_mc import PRIMARY_DELTA, by_delta, by_span, diff_disp_px, read_metacal, summ

STACKS = [
    ("coffee-bean", "data/coffee-bean-metacal.csv"),
    ("112MSDCF", "data/stack-112-metacal.csv"),
]
DELTAS = [1e-4, 2e-4, 4e-4, 8e-4, 1.6e-3]
SPANS = [1, 2, 8, 16, 32, 48]


def table(name, rows, field, title):
    print(f"\n  {name}  --  {title}")
    print(
        f"    {'delta':>9} {'dd px':>7} {'span':>5} "
        f"{'median':>9} {'p25':>9} {'p75':>9} {'n':>5} {'mean':>9} {'sd':>9}"
    )
    for d in DELTAS:
        rd = by_delta(rows, d)
        for s in SPANS:
            v = [getattr(r, field) for r in by_span(rd, s)]
            v = np.array([x for x in v if np.isfinite(x)])
            if v.size == 0:
                continue
            print(
                f"    {d:>9.1e} {diff_disp_px(d):>7.2f} {s:>5} {summ(v)} "
                f"{v.mean():>9.3f} {v.std(ddof=1):>9.3f}"
            )


def main() -> int:
    print("=" * 100)
    print("M23  THE PER-EDGE RESPONSE R  --  two-sided, measured on the pair it would correct")
    print("  R = (log|a(I+)| - log|a(I-)|) / (log(1+d) - log(1-d)),  I+- = F+- o F0^-1")
    print("  R = 1 means the estimator responds correctly; R < 1 means it shrinks the increment.")
    print("  FAILURE DIRECTION: R is a ratio of two small numbers.  Its per-edge noise is")
    print("  unbounded near R = 0, and E[1/R] > 1/E[R] for any R with variance, so a NOISY R")
    print("  inflates a corrected magnitude even when it carries no information at all.")
    print("=" * 100)

    store = {}
    for name, path in STACKS:
        rows = read_metacal(path, cfg="m10")
        store[name] = rows
        table(name, rows, "r_two", "TWO-SIDED R (primary)")

    print("\n" + "=" * 100)
    print("ONE-SIDED R  --  this is M10 P7's `ratio`, carried as a consistency check on fact 45")
    print("  (reuse of a prior harness is a consistency check, NOT independent evidence)")
    print("=" * 100)
    for name in store:
        rows = store[name]
        print(f"\n  {name}")
        print(f"    {'delta':>9} {'span':>5} {'R+ med':>9} {'R- med':>9} {'R2 med':>9} {'n':>5}")
        for d in DELTAS:
            rd = by_delta(rows, d)
            for s in (1, 2):
                rs = by_span(rd, s)
                if not rs:
                    continue
                rp = np.array([r.r_plus for r in rs])
                rm = np.array([r.r_minus for r in rs])
                r2 = np.array([r.r_two for r in rs])
                print(
                    f"    {d:>9.1e} {s:>5} {np.median(rp):>9.3f} {np.median(rm):>9.3f} "
                    f"{np.median(r2):>9.3f} {len(rs):>5}"
                )

    print("\n" + "=" * 100)
    print("REGISTERED delta-DEPENDENCE CRITERION (PREREGISTRATION 1.2)")
    print("  |median R(1e-4) - median R(8e-4)| > 0.15 on coffee-bean span-1")
    print("  => local linearity REFUTED => the metacalibration identity holds at no delta")
    print("=" * 100)
    cb1 = by_span(store["coffee-bean"], 1)
    lo = np.median([r.r_two for r in by_delta(cb1, 1e-4)])
    hi = np.median([r.r_two for r in by_delta(cb1, 8e-4)])
    print(f"\n  median R(1e-4) = {lo:.4f}   median R(8e-4) = {hi:.4f}   |diff| = {abs(hi-lo):.4f}")
    print(f"  VERDICT: local linearity {'REFUTED' if abs(hi - lo) > 0.15 else 'not refuted'}")

    print("\n" + "=" * 100)
    print("REGISTERED POSITIVE CONTROL: coffee-bean span-1 at delta=1e-4 must read R < 0.90")
    print("  Without it no null below has a known-real signal to be read against.")
    print("=" * 100)
    print(f"\n  median R = {lo:.4f}  ->  {'FIRES' if lo < 0.90 else 'DOES NOT FIRE'}")

    print("\n" + "=" * 100)
    print("GATE (b)  BUILT-IN PLACEBO on 112MSDCF")
    print(f"  PASS if median R over span-1 and span-2 at delta={PRIMARY_DELTA:.0e} is in [0.90, 1.10]")
    print("  FAILURE DIRECTION: a probe with no power reads R ~ 1 for a trivial reason.")
    print("  Admissible ONLY if the positive control above fires on the same code, same delta.")
    print("=" * 100)
    p112 = by_delta(store["112MSDCF"], PRIMARY_DELTA)
    v = np.array([r.r_two for r in p112 if r.span in (1, 2)])
    cbp = by_delta(store["coffee-bean"], PRIMARY_DELTA)
    vcb = np.array([r.r_two for r in cbp if r.span in (1, 2)])
    print(f"\n  112MSDCF   spans 1-2, delta={PRIMARY_DELTA:.0e}: median R = {np.median(v):.4f} "
          f"[p25 {np.percentile(v, 25):.3f}, p75 {np.percentile(v, 75):.3f}], n = {v.size}")
    print(f"  coffee-bean spans 1-2, same delta       : median R = {np.median(vcb):.4f} "
          f"[p25 {np.percentile(vcb, 25):.3f}, p75 {np.percentile(vcb, 75):.3f}], n = {vcb.size}")
    ok = 0.90 <= np.median(v) <= 1.10
    print(f"\n  gate (b) R-band: {'PASS' if ok else 'FAIL'}  "
          f"(the 1/S movement half of gate (b) is scored in m23_conserve.py)")

    print("\n" + "=" * 100)
    print("N3  SELF-PAIR NULL  --  frame k against ITSELF")
    print("  Real content, ZERO defocus difference, identical resampler, identical plant.")
    print("  True R = 1 by construction.  Any deviation is resampler + estimator, not defocus.")
    print("  This is the control M10's mechanism table (out/p6-p7-mechanism.txt) does not have:")
    print("  its P6 `resample` arm reads 1.323 / 0.863 at 0.12 / 0.24 px ONE-SIDED, so fact 45's")
    print("  attribution of the shrinkage to defocus was not closed against the resampler.")
    print("=" * 100)
    self_rows = read_metacal("data/cb-self-metacal.csv", cfg="m10")
    print(f"\n    {'delta':>9} {'dd px':>7} {'R2 med':>9} {'p25':>9} {'p75':>9} {'n':>5} "
          f"{'R+ med':>9} {'R- med':>9}")
    for d in DELTAS:
        rs = by_delta(self_rows, d)
        if not rs:
            continue
        r2 = np.array([r.r_two for r in rs])
        rp = np.array([r.r_plus for r in rs])
        rm = np.array([r.r_minus for r in rs])
        print(
            f"    {d:>9.1e} {diff_disp_px(d):>7.2f} {np.median(r2):>9.3f} "
            f"{np.percentile(r2, 25):>9.3f} {np.percentile(r2, 75):>9.3f} {r2.size:>5} "
            f"{np.median(rp):>9.3f} {np.median(rm):>9.3f}"
        )

    print("\n" + "=" * 100)
    print("HOW NOISY IS A PER-EDGE R?  --  the quantity R4 divides by, one edge at a time")
    print("  A correction divides by THIS, not by its median.  sd/|median| is the fractional")
    print("  noise a single edge's correction inherits.")
    print("=" * 100)
    for name in store:
        print(f"\n  {name}")
        print(f"    {'delta':>9} {'span':>5} {'med':>8} {'sd':>8} {'sd/|med|':>9} "
              f"{'frac |R|<0.2':>13} {'frac R<0':>9}")
        for d in DELTAS:
            for s in (1, 2):
                rs = by_span(by_delta(store[name], d), s)
                if not rs:
                    continue
                v = np.array([r.r_two for r in rs])
                med = np.median(v)
                print(
                    f"    {d:>9.1e} {s:>5} {med:>8.3f} {v.std(ddof=1):>8.3f} "
                    f"{v.std(ddof=1)/abs(med):>9.3f} {np.mean(np.abs(v) < 0.2):>13.4f} "
                    f"{np.mean(v < 0):>9.4f}"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
