"""B11: is the radial question even DECIDABLE on this artefact?

Registered in PREREGISTRATION.md addendum B11 before this file was written,
after B10 failed its own controls and disqualified itself.

B10 asked "is the residual radial". Both its controls failed: only 2 of 20
annuli cleared the minimum denominator, both outer, so Spearman was +1.0000
degenerately on two points and outer/inner was nan for want of an inner annulus.
`radial.py` is deliberately left untouched -- it is the registered instrument,
it behaved correctly, and editing it would turn a reported failure into a silent
repair.

B11 asks the prior question B10's failure exposed: does the population span
enough field height for "radial" to mean anything? It reports the full joint
profile with NO minimum-denominator cut and applies a decidability precondition
fixed before the run.

Read-only. Renders nothing.
"""

import numpy as np

from magenta import load, magenta_mask

OUT = r"C:\dev\strehl-out\M109"
AFTER = rf"{OUT}\marker-argmax-e024-after.tif"

NBINS = 20
SUPPORT_MIN = 5000     # eligible px required in an annulus for it to count as support
INNER_MAX_R = 0.50     # "some annulus below this" ...
OUTER_MIN_R = 0.85     # ... and "some annulus above this"


def main() -> None:
    a = load(AFTER)
    resid = magenta_mask(a)

    h, w = a.shape[:2]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) / np.hypot(cy, cx)

    nsat = (a >= 1.0).sum(axis=2)
    eligible = (nsat >= 1) & (nsat <= 2)

    edges = np.linspace(0.0, 1.0, NBINS + 1)
    mid = 0.5 * (edges[:-1] + edges[1:])
    idx = np.clip(np.digitize(r, edges) - 1, 0, NBINS - 1)

    tot = np.bincount(idx.ravel(), minlength=NBINS)
    elig = np.bincount(idx[eligible], minlength=NBINS)
    frin = np.bincount(idx[resid], minlength=NBINS)
    fr_in_el = np.bincount(idx[resid & eligible], minlength=NBINS)

    print(f"frame {w}x{h}")
    print(f"eligible total {int(elig.sum())}   fringe total {int(frin.sum())}")
    print()
    print("    r      total px   eligible   fringe   fringe&elig   fringe/elig(ppm)")
    for i in range(NBINS):
        d = (fr_in_el[i] / elig[i] * 1e6) if elig[i] else float("nan")
        print(f"    {mid[i]:.3f} {tot[i]:10d} {elig[i]:10d} {frin[i]:8d} {fr_in_el[i]:13d} "
              f"{d:16.1f}")

    inner_ok = bool(((mid < INNER_MAX_R) & (elig >= SUPPORT_MIN)).any())
    outer_ok = bool(((mid > OUTER_MIN_R) & (elig >= SUPPORT_MIN)).any())

    top = int(elig.max())
    conc = 100.0 * elig[elig >= SUPPORT_MIN].sum() / max(1, elig.sum())
    nsup = int((elig >= SUPPORT_MIN).sum())
    print()
    print(f"annuli with >= {SUPPORT_MIN} eligible px: {nsup} of {NBINS} "
          f"(holding {conc:.1f} % of all eligible pixels; largest annulus {top})")
    print(f"support below r={INNER_MAX_R}: {inner_ok}    support above r={OUTER_MIN_R}: {outer_ok}")

    print()
    print("=== verdict ===")
    if not (inner_ok and outer_ok):
        print("UNDECIDABLE-BY-SUPPORT.")
        print("The eligible population does not span field height, so no rho and no")
        print("outer/inner ratio is reported -- the registered consequence.")
        missing = []
        if not inner_ok:
            missing.append(f"no annulus below r={INNER_MAX_R} has {SUPPORT_MIN}+ eligible px")
        if not outer_ok:
            missing.append(f"no annulus above r={OUTER_MIN_R} has {SUPPORT_MIN}+ eligible px")
        for m in missing:
            print(f"  - {m}")
        print()
        print("What this DOES establish, and what it does not:")
        print("  - The blown-highlight population is spatially localised, not spread")
        print("    across the field. Whatever the residual is, it is co-located with")
        print("    the clipped region rather than distributed by field height.")
        print("  - It does NOT establish that lateral CA is absent. The corners are")
        print("    untested because there is nothing there to fringe, not because")
        print("    fringing was looked for and not found.")
        return

    print("DECIDABLE -- the eligible population spans field height.")
    print("Re-run the B10 instrument; its support precondition is met.")


if __name__ == "__main__":
    main()
