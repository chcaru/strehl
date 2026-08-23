"""M50 step 0 - does the cross-half covariance estimator actually work?

A null result from an unvalidated estimator is worthless: "we found no row
banding" and "our estimator cannot see row banding" produce identical output.
This plants known FPN of each kind, at known amplitude, on top of temporal noise
far larger than the plant, and checks that 01-anisotropy.py's estimator recovers
it -- and, just as importantly, that it returns zero for the components that
were not planted.

The plants are chosen adversarially against the estimator:

  A. row-only      -- must recover var_row, must report ~0 for var_col
  B. column-only   -- the mirror image; catches a transposed axis, which is the
                      single most likely bug in this whole measurement
  C. pixel-only    -- must report ~0 for BOTH row and col; catches an estimator
                      that mistakes ordinary per-pixel FPN for banding
  D. nothing       -- the placebo. Pure temporal noise. All three must be ~0,
                      and this is the case that proves a null result on real
                      darks would be believed.

Case D is the one that matters most. If the estimator reports structure on pure
noise then every number 01-anisotropy.py produces is an artefact.

The directional prediction is checked too, since that is the claim actually
under test: a row plant must give Ey > Ex, a column plant Ex > Ey, and removing
the row and column means must destroy whichever energy was inflated while
leaving ordinary per-pixel structure -- which the focus measure legitimately
wants to see -- intact.

THIS TEST HAS ALREADY EARNED ITS KEEP. Its first run failed, before any real
data was touched, on a defect in the summary statistic rather than in the
estimator: the anisotropy was written as the ratio Ey/Ex, and a row-only pattern
has no variation along x at all, so Ex is legitimately ~0 and its sign is noise.
The ratio returned -494.885 for planted row banding -- a large NEGATIVE number
for the most strongly POSITIVE case that exists. The estimator itself was
correct throughout (row plant recovered to -10.2%, placebo clean at 1.2% of the
plant amplitude). The statistic is now the bounded index (Ey - Ex) / (Ey + Ex),
and the ratio is still printed as a reminder of why it is unusable.

Temporal noise is deliberately set well above the plant amplitude so the test
exercises the regime the real data is in, where the plant is invisible in any
single frame and only the cross-half structure reveals it.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
mod = __import__("01-anisotropy")

H, W, N = 240, 320, 20
SD_TEMPORAL = 1.0
SD_PLANT = 0.30
SEED = 7


def build(rng, kind):
    """N frames of pure temporal noise plus one planted fixed pattern."""
    fixed = np.zeros((H, W), dtype=np.float64)
    if kind == "row":
        fixed += rng.normal(0, SD_PLANT, size=(H, 1))
    elif kind == "col":
        fixed += rng.normal(0, SD_PLANT, size=(1, W))
    elif kind == "pix":
        fixed += rng.normal(0, SD_PLANT, size=(H, W))
    elif kind != "none":
        raise ValueError(kind)
    frames = fixed[None, :, :] + rng.normal(0, SD_TEMPORAL, size=(N, H, W))
    return frames.astype(np.float32)


def main():
    want = SD_PLANT
    # The estimator's own noise floor, from the placebo, sets what "~0" means.
    print(
        f"plant sd = {want:.4f} DN, temporal sd = {SD_TEMPORAL:.2f} DN, "
        f"N = {N} frames, {H}x{W}\n"
    )
    print(f"{'plant':>6} | {'sd_row':>16} | {'sd_col':>16} | {'sd_pix':>16} |"
          f" {'aniso':>6} | {'after fix':>6} | {'Ey/Ex (bad)':>11}")
    print("-" * 104)
    results = {}
    for kind in ("row", "col", "pix", "none"):
        rng = np.random.default_rng(SEED)
        frames = build(rng, kind)
        r = mod.analyse_plane(frames.reshape(N, -1), (H, W), np.random.default_rng(SEED + 1))

        def fmt(key):
            m, s = r[key]
            return f"{mod.signed_sqrt(m):+7.4f}+-{mod.signed_sqrt(s):6.4f}"

        ex, ey = r["Ex"][0], r["Ey"][0]
        exf, eyf = r["Ex_fix"][0], r["Ey_fix"][0]
        aniso = mod.aniso_index(ex, ey)
        anisof = mod.aniso_index(exf, eyf)
        ratio = ey / ex if ex else float("nan")  # kept only to show why it is unusable
        print(f"{kind:>6} | {fmt('var_row')} | {fmt('var_col')} | {fmt('var_pix')} |"
              f" {'  n/a ' if aniso is None else f'{aniso:+6.3f}'} |"
              f" {'  n/a ' if anisof is None else f'{anisof:+6.3f}'} | {ratio:11.3f}")
        results[kind] = dict(
            row=mod.signed_sqrt(r["var_row"][0]),
            col=mod.signed_sqrt(r["var_col"][0]),
            pix=mod.signed_sqrt(r["var_pix"][0]),
            aniso=aniso, aniso_fix=anisof, ratio=ratio,
            Ex=ex, Ey=ey, Ex_fix=exf, Ey_fix=eyf,
        )

    # The placebo defines the floor: nothing may be called a detection unless it
    # exceeds what the estimator reports on data containing no pattern at all.
    floor = max(abs(results["none"][k]) for k in ("row", "col", "pix"))
    print(f"\nplacebo floor (largest |sd| on pure noise): {floor:.4f} DN")

    fails = []

    def check(name, cond, detail):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}: {detail}")
        if not cond:
            fails.append(name)

    print("\nrecovery:")
    for kind, key in (("row", "row"), ("col", "col"), ("pix", "pix")):
        got = results[kind][key]
        check(f"{kind} plant recovered", abs(got / want - 1) < 0.15,
              f"{got:+.4f} vs planted {want:.4f} ({100 * (got / want - 1):+.1f}%)")

    print("\nno leakage between components:")
    check("row plant leaks no column", abs(results["row"]["col"]) < 4 * floor,
          f"sd_col={results['row']['col']:+.4f} vs 4x floor {4 * floor:.4f}")
    check("col plant leaks no row", abs(results["col"]["row"]) < 4 * floor,
          f"sd_row={results['col']['row']:+.4f} vs 4x floor {4 * floor:.4f}")
    check("pixel plant leaks no row", abs(results["pix"]["row"]) < 4 * floor,
          f"sd_row={results['pix']['row']:+.4f} vs 4x floor {4 * floor:.4f}")
    check("pixel plant leaks no column", abs(results["pix"]["col"]) < 4 * floor,
          f"sd_col={results['pix']['col']:+.4f} vs 4x floor {4 * floor:.4f}")

    print("\nplacebo (this is the one that licenses a null result):")
    for k in ("row", "col", "pix"):
        v = results["none"][k]
        check(f"placebo {k} is negligible", abs(v) < 0.1 * want,
              f"{v:+.4f} DN, {100 * abs(v) / want:.1f}% of the plant amplitude")

    print("\ndirection (the claim actually under test):")
    check("row plant gives Ey > Ex", results["row"]["aniso"] > 0.90,
          f"aniso index = {results['row']['aniso']:+.4f} (+1 is pure row banding); "
          f"Ey={results['row']['Ey']:.4g} Ex={results['row']['Ex']:.4g}")
    check("col plant gives Ex > Ey", results["col"]["aniso"] < -0.90,
          f"aniso index = {results['col']['aniso']:+.4f} (-1 is pure column banding)")
    check("isotropic pixel plant is already isotropic",
          abs(results["pix"]["aniso"]) < 0.10,
          f"aniso index = {results['pix']['aniso']:+.4f}")
    # For the fix, the index is 0/0 once BOTH energies collapse, so assert the
    # collapse itself. This is stronger than an index check, not weaker.
    surv = results["row"]["Ey_fix"] / results["row"]["Ey"]
    check("row/col removal destroys the row plant's Sobel-y energy", surv < 0.05,
          f"Ey {results['row']['Ey']:.4g} -> {results['row']['Ey_fix']:.4g}, "
          f"{100 * surv:.2f}% surviving")
    survc = results["col"]["Ex_fix"] / results["col"]["Ex"]
    check("row/col removal destroys the column plant's Sobel-x energy", survc < 0.05,
          f"Ex {results['col']['Ex']:.4g} -> {results['col']['Ex_fix']:.4g}, "
          f"{100 * survc:.2f}% surviving")
    # The fix must not be a blunt instrument: ordinary per-pixel FPN, which the
    # focus measure legitimately wants to see, must survive it.
    survp = results["pix"]["Ey_fix"] / results["pix"]["Ey"]
    check("the fix preserves ordinary per-pixel structure", survp > 0.90,
          f"Ey {results['pix']['Ey']:.4g} -> {results['pix']['Ey_fix']:.4g}, "
          f"{100 * survp:.1f}% surviving")

    print("\nwhy the ratio Ey/Ex was rejected as the summary statistic:")
    print(f"  on the row plant -- the most strongly positive case that exists --")
    print(f"  Ey/Ex = {results['row']['ratio']:.3f}, because Ex is legitimately ~0")
    print(f"  ({results['row']['Ex']:+.4g}) and its sign is noise. The bounded index")
    print(f"  reports {results['row']['aniso']:+.4f} for the same data.")

    print()
    if fails:
        print(f"FAILED: {len(fails)} check(s): {', '.join(fails)}")
        sys.exit(1)
    print("all checks passed - the estimator recovers what is planted, reports")
    print("zero for what is not, and its null result is therefore meaningful.")


if __name__ == "__main__":
    main()
