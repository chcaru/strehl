"""M70 s18 - re-price the matched filter against THE GATED AVERAGE AS IT BEHAVES.

The primary report compared the matched filter against an equal average of the
best 3 frames, and reported 0.23%. The owner's follow-up turn, item 3, is right
that this is the wrong incumbent: M67 measured that the shipped gate admits a
much wider set than 3 frames, and corpus fact 19 (the gated mean reaching 0.534x
single-frame noise) is the thing to beat.

Nothing new is measured here. This re-indexes s10's already-measured price list
by admitted-set size, so the value can be read off at the width the gate
actually operates at.

M67's n_eff = 6.84 at K = 25 and D(A)/D(E) = 0.4895 are SIMULATOR figures. They
are used here ONLY to point at a row of a table measured on the corpus. They are
not imported as corpus figures and no corpus claim rests on their value.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import m70lib as M  # noqa: E402
import s05_analyse as A5  # noqa: E402
import s07_unclipped as S7  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
STACKS = list(S7.APERTURE.keys())
WINDOWS = (1, 2, 3, 5, 10, 20)

# M67-focus-correctness.md, read directly. SIMULATOR figures.
M67_NEFF = 6.84
M67_K = 25
M67_DA_DE = 0.4895
M67_DE = 0.848
M67_DA = 1.733


def main() -> None:
    arch = json.load(open(os.path.join(OUT, "s10_architecture.json")))
    res = {}

    print("=" * 118)
    print("1. WHICH WINDOW IS THE SHIPPED GATE? Two independent routes, no free parameter.")
    print("=" * 118)
    print(f"  M67 measured, on its simulator at K = {M67_K}:")
    print(f"    effective frame count of the gated weighted mean   n_eff = {M67_NEFF}")
    print(f"    D(A)/D(E) = {M67_DA_DE}  ->  selector pick sits {M67_DE} frames from")
    print(f"    true focus, admitted set averages {M67_DA} frames out.")
    print(f"\n  An EQUAL average over +-W frames has n = 2W+1 and mean |offset| =")
    print(f"  W(W+1)/(2W+1). Both of M67's numbers land on the same W:\n")
    print(f"{'W':>4}{'n = 2W+1':>10}{'vs n_eff 6.84':>16}{'mean|off|':>12}{'vs D(A) 1.733':>16}")
    best = None
    for W in WINDOWS:
        n = 2 * W + 1
        mo = W * (W + 1) / (2 * W + 1)
        r1, r2 = n / M67_NEFF, mo / M67_DA
        mark = ""
        if best is None or abs(np.log(r1)) + abs(np.log(r2)) < best[1]:
            best = (W, abs(np.log(r1)) + abs(np.log(r2)))
        print(f"{W:>4}{n:>10}{r1:>15.3f}x{mo:>12.3f}{r2:>15.3f}x{mark}")
    W67 = best[0]
    print(f"\n  Closest window on BOTH measures simultaneously: W = +-{W67} "
          f"({2 * W67 + 1} frames)")
    print(f"    n:          {2 * W67 + 1} vs n_eff {M67_NEFF}   ->  "
          f"{(2 * W67 + 1) / M67_NEFF:.3f}x")
    print(f"    mean|off|:  {W67 * (W67 + 1) / (2 * W67 + 1):.4f} vs D(A) {M67_DA}   ->  "
          f"{W67 * (W67 + 1) / (2 * W67 + 1) / M67_DA:.3f}x")
    res["window_map"] = {"W": W67, "n": 2 * W67 + 1,
                         "mean_offset": W67 * (W67 + 1) / (2 * W67 + 1)}

    print("\n" + "=" * 118)
    print("2. THE PRICE LIST - matched filter over an EQUAL average of the SAME frames")
    print("   (mid band, median over textured patches; measured, s10, 12 stacks)")
    print("=" * 118)
    print(f"{'W':>4}{'n frames':>10}{'min':>10}{'median':>10}{'max':>10}{'median dB':>12}")
    res["price"] = {}
    for W in WINDOWS:
        v = np.array([r[f"mf_vs_avg_{W}"] for r in arch])
        e = {"n": 2 * W + 1, "min": float(v.min()), "median": float(np.median(v)),
             "max": float(v.max()), "median_dB": float(20 * np.log10(np.median(v)))}
        res["price"][W] = e
        star = "   <-- the gate, per M67" if W == W67 else ""
        print(f"{W:>4}{2 * W + 1:>10}{e['min']:>10.4f}{e['median']:>10.4f}"
              f"{e['max']:>10.4f}{e['median_dB']:>12.3f}{star}")

    print("\n" + "=" * 118)
    print("3. WHAT THE GATE IS ALREADY HARVESTING - relative mid-band amplitude off peak")
    print("=" * 118)
    rows = S7.corpus(verbose=False)
    ra = {}
    for m in (1, 2, 3, 5):
        v = [r[b][f"rel_amp_{m}"] for r in rows for b in M.MID_BANDS
             if np.isfinite(r[b][f"rel_amp_{m}"])]
        ra[m] = float(np.median(v)) if v else float("nan")
    frac = M67_DA - int(M67_DA)
    lo, hi = int(M67_DA), int(M67_DA) + 1
    interp = ra[lo] + frac * (ra[hi] - ra[lo])
    print(f"  median rel_amp at 1 step off peak : {ra[1]:.4f}")
    print(f"  median rel_amp at 2 steps off peak: {ra[2]:.4f}")
    print(f"  median rel_amp at 3 steps off peak: {ra[3]:.4f}")
    print(f"  median rel_amp at 5 steps off peak: {ra[5]:.4f}")
    print(f"\n  At M67's measured admitted-set defocus of {M67_DA} frames, linear")
    print(f"  interpolation gives rel_amp = {interp:.4f}. The frames the gate is")
    print(f"  already averaging carry ~{100 * interp:.0f}% of peak mid-band amplitude.")
    print("  That IS the reviewer's premise, and the shipped gate already harvests it.")
    res["rel_amp"] = {str(k): v for k, v in ra.items()}
    res["rel_amp_at_M67_DA"] = interp

    print("\n" + "=" * 118)
    print("4. THE VERDICT ARITHMETIC, RESTATED AGAINST THE RIGHT INCUMBENT")
    print("=" * 118)
    p = res["price"][W67]
    hr = np.array([r["headroom"] for r in
                   json.load(open(os.path.join(OUT, "s11_headroom.json")))["w10_sigma1.0"]])
    print(f"  Against a best-3 equal average (the primary report's comparator):")
    print(f"      MF buys {res['price'][1]['median']:.4f}x  "
          f"({100 * (res['price'][1]['median'] - 1):.2f}%)")
    print(f"  Against the gated average AS IT BEHAVES (W = +-{W67}, {2 * W67 + 1} frames):")
    print(f"      MF buys {p['median']:.4f}x  ({100 * (p['median'] - 1):.2f}%),  "
          f"range {p['min']:.4f}-{p['max']:.4f}x")
    print(f"  Bounded above, at ANY window W <= 10, by the measured headroom:")
    print(f"      min {hr.min():.4f}x  median {np.median(hr):.4f}x"
          f"  max {hr.max():.4f}x")
    res["headroom"] = {"min": float(hr.min()), "median": float(np.median(hr)),
                       "max": float(hr.max())}
    print(f"\n  Corpus fact 19, the shipped gated mean: 0.534x single-frame noise")
    print(f"      = {1 / 0.534:.3f}x SNR = {20 * np.log10(1 / 0.534):.2f} dB already banked.")
    print(f"      The MF's median prize at the gate's own width is "
          f"{p['median_dB']:.3f} dB,")
    print(f"      i.e. {100 * p['median_dB'] / (20 * np.log10(1 / 0.534)):.1f}% "
          f"of what the gate already delivers.")
    res["fact19"] = {"snr": 1 / 0.534, "dB": float(20 * np.log10(1 / 0.534))}

    with open(os.path.join(OUT, "s18_incumbent.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("\nwrote out/s18_incumbent.json")


if __name__ == "__main__":
    main()
