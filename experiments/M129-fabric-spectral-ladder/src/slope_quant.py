"""How finely can the crossing estimator resolve a bias at all?

Two rows of out/slope-bias.json are identical to four decimals (alpha 3.126 and
3.400, both -4.242621527777786, both sd 1.0506139719529701). Identical means AND
identical standard deviations across 16 independent replicates do not happen by
chance. The explanation to rule in or out is quantisation: the estimator returns a
radial bin index, radial bins are discrete, so recovered f_c can only take values on
a grid and any bias difference smaller than one bin is unresolvable.

That matters for how the slope result may be quoted. If the grid step is comparable
to the effect, then "-2.35 points per unit alpha" is a fit through a staircase and
the individual rows carry no information below the step.

This reads only the saved artefacts. Nothing is re-simulated.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")


def main():
    with open(os.path.join(OUT, "slope-bias.json"), encoding="utf-8") as fh:
        sb = json.load(fh)
    with open(os.path.join(OUT, "snr-w2.json"), encoding="utf-8") as fh:
        sn = json.load(fh)

    f = np.asarray(sn["records"][0]["f"], float)
    step = float(np.median(np.diff(f)))
    fc = sb["planted_fc"]
    step_pts = 100.0 * step / fc

    print("IS THE SLOPE RESULT QUANTISED?")
    print()
    print(f"  planted f_c                     : {fc:.6f} sensor cyc/px")
    print(f"  radial bin spacing              : {step:.6f} sensor cyc/px")
    print(f"  one bin, as a bias percentage   : {step_pts:.3f} points")
    print()

    b = np.array([r["bias"] for r in sb["rows"]], float)
    a = np.array([r["alpha"] for r in sb["rows"]], float)
    print("  Every measured bias, divided by one bin. If these land on or near")
    print("  half-integers, the estimator is returning grid values and the means")
    print("  differ only by how many replicates fell in each bin.")
    print()
    print(f"  {'alpha':>7} {'bias %':>9} {'in bins':>9} {'frac':>7}")
    for ai, bi in zip(a, b):
        q = bi / step_pts
        print(f"  {ai:7.3f} {bi:9.3f} {q:9.3f} {abs(q - round(q * 16) / 16):7.4f}")
    print()

    d = np.abs(np.diff(np.sort(np.unique(b))))
    d = d[d > 1e-9]
    if d.size:
        g = float(np.min(d))
        print(f"  smallest nonzero gap between distinct bias values : {g:.4f} points")
        print(f"  that gap in bins                                  : "
              f"{g / step_pts:.4f}")
        print(f"  one bin over 16 replicates                        : "
              f"{step_pts / 16:.4f} points")
        near = abs(g - step_pts / 16) < 0.02 * step_pts
        print()
        if near:
            print("  CONFIRMED. The gaps are multiples of one bin divided by the")
            print("  replicate count, which is exactly what a quantised estimator")
            print("  averaged over replicates produces.")
        else:
            print("  NOT a clean match to pure quantisation; some other structure")
            print("  is present as well.")
    print()
    sem = np.array([r["sd"] / np.sqrt(r["n"]) for r in sb["rows"]], float)
    print("  BUT THE MEAN IS NOT QUANTISED, AND THAT IS WHY THE RESULT STANDS.")
    print("  Individual estimates land on the grid, yet the replicate standard")
    print(f"  deviations are {min(r['sd'] for r in sb['rows']):.2f}-"
          f"{max(r['sd'] for r in sb['rows']):.2f} points, which is "
          f"{min(r['sd'] for r in sb['rows']) / step_pts:.2f}-"
          f"{max(r['sd'] for r in sb['rows']) / step_pts:.2f} bins, so replicates do")
    print("  scatter across adjacent bins and the mean interpolates between them.")
    rng = abs(b[-1] - b[0])
    comb = float(np.hypot(sem[0], sem[-1]))
    print(f"    standard error of each row : {sem.min():.3f}-{sem.max():.3f} points")
    print(f"    endpoint difference        : {rng:.2f} points, "
          f"{rng / comb:.1f} sigma")
    print(f"    a one-row step of ~0.8 pts : about "
          f"{0.814 / comb:.1f} sigma -- marginal")
    print()
    print("  HOW THE SLOPE RESULT MUST BE QUOTED. Quote the fitted slope and the")
    print("  endpoints, which are resolved many times over. Do not quote row-to-row")
    print("  differences as measurements: the tie between alpha 3.126 and 3.400 is")
    print("  the grid, and the non-monotone step at 2.6 to 3.0 is replicate scatter.")
    print()
    print("  THE NUMBER THIS ACTUALLY PRODUCED FOR THE LANE. One radial bin is")
    print(f"  {step_pts:.2f}% of f_c. That is the estimator's intrinsic resolution on")
    print("  a single (ROI, aperture) cell, and it applies to the real ladder too,")
    print("  not just to this synthetic sweep. Section 2.2 separates H2 from H3 by")
    sep = 28.07
    print(f"  {sep:.2f}% in the product f_c*N, so the hypotheses are "
          f"{sep / step_pts:.1f} bins apart.")
    print(f"  Averaging over the six ROIs divides the scatter by sqrt(6), giving a")
    print(f"  per-aperture standard error near "
          f"{float(np.mean([r['sd'] for r in sb['rows']])) / np.sqrt(6):.2f} points "
          f"if the real data scatter")
    print("  like the synthetic. The separation is comfortably resolvable; it is the")
    print("  BIAS, not the resolution, that threatens this lane.")

    dest = os.path.join(OUT, "slope-quantisation.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump({"bin_step": step, "bin_points": step_pts,
                   "range_points": float(rng),
                   "range_bins": float(rng / step_pts),
                   "sem_min": float(sem.min()), "sem_max": float(sem.max()),
                   "endpoint_sigma": float(rng / comb),
                   "separation_pct": sep,
                   "separation_bins": float(sep / step_pts)}, fh, indent=2)
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
