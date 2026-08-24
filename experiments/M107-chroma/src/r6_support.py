"""R6 -- the RADIAL SUPPORT of the -704.5 ppm lateral-CA fit.

The orchestrator asks a question about support, not goodness of fit: lateral CA
is zero at the optical centre by construction and grows with field height, so a
radial coefficient is most load-bearing exactly where a macro subject usually
has nothing in frame. A high R^2 over a narrow radial band is entirely
consistent with an unconstrained extrapolation into the corners.

This does NOT re-derive M109's result and does not read its files. It asks the
same question of MY fit set, from my own data, independently.

## GEOMETRY -- corrected after the first run, see BAR S0

The first version of this script normalised by hypot(3516,2344)/2, the half
diagonal of the half-resolution CFA PLANE. That produced r_max = 1.575, which
is impossible: no point in the frame is further from the centre than the half
diagonal. `rx`,`ry` in e1_raw_edges.json are centre-relative FULL-RESOLUTION
SENSEL coordinates (common.py:17 -- "every plane sample carries a true sensel
coordinate"), so the correct normaliser is hypot(7032,4688)/2. S0 now asserts
this rather than assuming it.

Note this does NOT affect eps: the fit solves d = eps*(r.n) with d and r both
in sensels, so eps is dimensionless and unit-consistent either way. What it
affected was only this support statistic.

## BARS, REGISTERED BEFORE THE RUN

  S0  GEOMETRY GUARD. Every gated ROI must satisfy |rx| <= SENSEL_W/2 and
      |ry| <= SENSEL_H/2, and r_max must be <= 1.0. A radius above 1.0 is
      geometrically impossible and means the normaliser is wrong. This bar
      exists because the first run of this script violated it and I did not
      notice from the verdict line -- only the S5 control flagged it.

  S1  The gated set is exactly the 20 ROIs fact 1414 claims. Anything else and
      the coefficient in optics.rs is not the one this script describes.

  S2  THE DECIDING BAR. Maximum field height r_max.
        r_max >= 0.85  -> support reaches the corner region; the corner
                          correction is INTERPOLATED and the question closes.
        r_max <  0.85  -> the corner correction is EXTRAPOLATED, and the honest
                          form is "UNDECIDABLE beyond r = r_max".
      I expect this to FAIL. Registering the expectation so a pass is
      informative and cannot be claimed after the fact.

  S3  Per-annulus population over 10 equal-width annuli in r. An annulus with
      n = 0 constrains nothing. Reported as counts, NOT as a coefficient --
      M109's 2-bin Spearman read +1.0000 on a uniform-random null, so a
      correlation over a starved support is not evidence and I will not
      compute one.

  S4  Extrapolation factor at the corner = 1.0 / r_max. For a pure radial
      magnification d = eps*r, displacement is linear in r, so the corner value
      is the largest MEASURED value scaled by exactly 1/r_max. That factor is
      the honest statement of how much of the corner correction comes from the
      model's shape rather than from measured points.

  S5  TWO-SIDED INSTRUMENT CHECK. A support statistic must be able to say both
      words. My first attempt compared r_max against a uniform draw over the
      same band, which is biased low by construction (the max of n draws from
      [a,b] undershoots b) -- a bad bar, and it failed for that reason rather
      than for a real one. Replaced with a genuine pair, same n:
        S5a POSITIVE control -- radii uniform over [0,1] MUST report r_max
            >= 0.85 (adequate). Proves the instrument can say "adequate".
        S5b NEGATIVE control -- radii confined to [0.20,0.40] MUST report
            r_max < 0.85 (starved). Proves it can say "starved".
      If either control fails, S2's verdict on the real data means nothing.
"""
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT
from e2_lateral import gated

ROWS = json.load(open(os.path.join(OUT, "json", "e1_raw_edges.json")))["rows"]

# Full-resolution sensel geometry. The CFA plane is half this in each axis.
SENSEL_W, SENSEL_H = 7032.0, 4688.0
HALF_DIAG = float(np.hypot(SENSEL_W, SENSEL_H) / 2.0)

NB = 10
BAR_S2 = 0.85


def support(r_norm, label):
    counts, edges = np.histogram(r_norm, bins=NB, range=(0.0, 1.0))
    print(f"  {label}: n={len(r_norm)}  r_min={r_norm.min():.3f}  "
          f"r_max={r_norm.max():.3f}  r_median={np.median(r_norm):.3f}")
    print("    annulus      r range      n")
    for i, c in enumerate(counts):
        mark = "" if c else "   <- EMPTY"
        print(f"      {i:2d}      {edges[i]:.2f}-{edges[i+1]:.2f}   {c:4d}{mark}")
    return counts, float(r_norm.max())


def main():
    keep, _why = gated(ROWS)
    stacks = sorted({r["stack"] for r in keep})
    print("=" * 68)
    print("R6 -- radial support of the lateral-CA fit")
    print("=" * 68)

    rx = np.array([r["rx"] for r in keep], float)
    ry = np.array([r["ry"] for r in keep], float)
    r_norm = np.hypot(rx, ry) / HALF_DIAG

    print(f"\nS0  geometry guard  (normaliser = hypot({SENSEL_W:.0f},{SENSEL_H:.0f})/2"
          f" = {HALF_DIAG:.1f} sensels)")
    print(f"    |rx|max = {np.abs(rx).max():.0f}  (limit {SENSEL_W/2:.0f})")
    print(f"    |ry|max = {np.abs(ry).max():.0f}  (limit {SENSEL_H/2:.0f})")
    s0 = bool(np.abs(rx).max() <= SENSEL_W / 2 and np.abs(ry).max() <= SENSEL_H / 2
              and r_norm.max() <= 1.0)
    print(f"    S0 {'PASS' if s0 else 'FAIL -- normaliser wrong, all bars below void'}")

    print(f"\nS1  gated ROIs = {len(keep)}   (bar: exactly 20)")
    print(f"    S1 {'PASS' if len(keep) == 20 else 'FAIL'}")
    for s in stacks:
        print(f"      {s}: {sum(1 for r in keep if r['stack'] == s)} ROIs")

    print("\nS3  per-annulus population (real fit set)")
    counts, r_max = support(r_norm, "real")
    print(f"    annuli with zero support: {[i for i, c in enumerate(counts) if c == 0]}")

    print(f"\nS2  r_max = {r_max:.3f}   (bar: >= {BAR_S2} for interpolation)")
    s2 = r_max >= BAR_S2
    print(f"    S2 {'PASS -- corner INTERPOLATED' if s2 else 'FAIL -- corner EXTRAPOLATED'}")

    print(f"\nS4  extrapolation factor at the corner = 1/r_max = {1.0/r_max:.2f}x")
    print("    The corner correction is the largest MEASURED displacement")
    print(f"    scaled by {1.0/r_max:.2f}, from the model's shape alone.")

    print("\nS5  two-sided instrument check")
    rng = np.random.default_rng(0x00C0_FFEE_1107)
    n = len(r_norm)
    _, rmax_pos = support(rng.uniform(0.0, 1.0, n), "S5a+")
    s5a = rmax_pos >= BAR_S2
    print(f"    S5a positive control r_max={rmax_pos:.3f} -> "
          f"{'PASS -- can report ADEQUATE' if s5a else 'FAIL'}")
    _, rmax_neg = support(rng.uniform(0.20, 0.40, n), "S5b-")
    s5b = rmax_neg < BAR_S2
    print(f"    S5b negative control r_max={rmax_neg:.3f} -> "
          f"{'PASS -- can report STARVED' if s5b else 'FAIL'}")

    print("\n" + "=" * 68)
    if not (s0 and s5a and s5b):
        print("VERDICT: INSTRUMENT NOT TRUSTWORTHY -- no claim made")
    else:
        print(f"VERDICT: {'SUPPORT ADEQUATE' if s2 else f'UNDECIDABLE BEYOND r = {r_max:.2f}'}")
    print("=" * 68)


if __name__ == "__main__":
    main()
