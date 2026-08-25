"""N6 -- a narrowing LADDER on a first-moment statistic.

ORCH's correction #2 (2026-08-24 21:28) replaces the old triage with:

    "Does the statistic read pixel VALUE, or feature POSITION?"
      location  -> largely immune, bound at ~12 levels per fitted window
      dispersion -> destroyed

**That dichotomy does not contain M121's statistic, and M121's measured result
contradicts the class it would be sorted into.**  The rim is

    rim = mean_band( p(+d) - hi ) / (hi - lo)

Every term is a FIRST MOMENT -- a mean, or a difference of means.  It reads
pixel value, so ORCH's new rule sorts it with the vulnerable half; it is not a
dispersion statistic, so the stated mechanism for that vulnerability (absorbing
quantisation variance) does not apply to it.  Measured in N5, it moved -2.4%
under a 227.5x narrowing.

So there are three classes, not two:

  1. LOCATION (displacement, centroid, peak position) -- immune because the
     error is zero-mean and uncorrelated with sub-pixel position.
  2. FIRST MOMENT (mean, difference of means, ratio of such) -- ALSO largely
     immune, but for a different reason: the error is zero-mean and averages
     down over the samples in the estimate.  ORCH's rule has no slot for this.
  3. DISPERSION (sd, rms, SNR, band energy) -- destroyed, because the estimate
     IS the variance that quantisation adds to.

This script tests that claim where it is most likely to fail.  ORCH's bound is
"~12 distinct levels per fitted window, failing quietly below".  M121's rim
signal is far below that already: the headline rim is 0.0634 x 6754 DN = 428 DN,
which after the N5 narrowing is **1.7 levels**.  By a literal reading of the
bound M121 should be reporting a confident, plausible, badly wrong number.

So: run the ladder and find where the rim ACTUALLY breaks.

Per ORCH's other new instruction, the sample count of every rung is logged and
required to VARY -- "a control whose sampling saturates has tested nothing, and
it will print a clean negative."

Outputs: C:\\dev\\strehl-out\\M121\\n6\\n6-ladder.json
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from m121_io import OUT, arm_path, load_u16, luma, sha256  # noqa: E402
from runner import scan  # noqa: E402
import e2_polarity as E2  # noqa: E402

N6 = OUT / "n6"

# Bits shifted away.  0 is the untouched control; 8 is exactly the PIL defect
# commissioned in N5; beyond that we are past it, looking for the cliff.
RUNGS = [0, 4, 6, 8, 9, 10, 11, 12]

HEADLINE = "dark_object_bright_surround"
NULLROW = "bright_object_dark_surround"


def narrow(a: np.ndarray, bits: int) -> np.ndarray:
    """Shift `bits` away and restore the scale, so DN are comparable.

    Restoring the range is what keeps MIN_AMPLITUDE meaning the same thing at
    every rung.  It cannot restore the LEVELS, which is the damage under test.
    """
    if bits == 0:
        return a
    return (a >> bits).astype(np.uint32) * (1 << bits)


def levels_in(a: np.ndarray) -> int:
    return int(np.unique(a).size)


def main():
    N6.mkdir(parents=True, exist_ok=True)
    out: dict = {"rungs": []}

    max_rise = E2.commissioned_max_rise()
    p = arm_path("armM4-gate4-binlin")
    print(f"loading {p.name} ...")
    rgb = load_u16(p)
    assert rgb.dtype == np.uint16, f"shipped arm came back {rgb.dtype}"
    out["arm"] = {"path": str(p), "sha256": sha256(p)}

    print("building the object-side classifier from the CLEAN frames ...")
    # Held fixed across the ladder on purpose: the question is what narrowing
    # does to the RIM STATISTIC, so the class assignment must not also move.
    frames = [luma(load_u16(arm_path(f))) for f in E2.FRAMES]
    fmax = np.max(np.stack([E2.focus_field(f) for f in frames]), axis=0)
    classify = E2.make_classifier(fmax)
    del frames, fmax

    kw = dict(isolation_frac=E2.ISO, flat_tol=E2.FLAT_TOL, classify=classify,
              min_amplitude=E2.MIN_AMPLITUDE)

    print(f"\n{'bits':>5}{'levels':>9}{'lvl/edge':>10}{'lvl/rim':>9}"
          f"{'headline':>11}{'ret%':>8}{'null':>10}{'n_hl':>6}{'n_null':>8}")
    print("-" * 78)

    base_rim = None
    for bits in RUNGS:
        arr = narrow(rgb, bits)
        y = luma(arr)
        lv = levels_in(arr)

        r = scan(y, label=f"N6 bits={bits}", grad_percentile=E2.GRAD_PCT,
                 max_edges=E2.MAX_EDGES, max_rise=max_rise, verbose=False, **kw)
        t = E2.polarity_table(r)

        hl = t.get(HEADLINE) if isinstance(t.get(HEADLINE), dict) else None
        nu = t.get(NULLROW) if isinstance(t.get(NULLROW), dict) else None
        rim = hl.get("surround_rim") if hl else None
        nrim = nu.get("surround_rim") if nu else None
        n_hl = hl.get("n") if hl else 0
        n_nu = nu.get("n") if nu else 0

        # ORCH's instruction: count levels in the window the statistic actually
        # integrates over, not in the file.  For this estimator there are two
        # such scopes and they differ by more than an order of magnitude.
        amps = None
        if hl and r.get("bright") is not None and "amps" in r["bright"]:
            sel = np.asarray(r["bright"]["obj"]) == -1
            A = np.asarray(r["bright"]["amps"])[sel]
            amps = float(np.median(A)) if A.size else None
        step = float(1 << bits)
        lvl_edge = (amps / step) if amps else float("nan")
        lvl_rim = (abs(rim) * amps / step) if (amps and rim is not None) else float("nan")

        if bits == 0:
            base_rim = rim
        ret = (100.0 * rim / base_rim) if (base_rim and rim is not None) else float("nan")

        out["rungs"].append({
            "bits": bits, "levels_file": lv, "step_dn": step,
            "median_edge_amplitude_dn": amps,
            "levels_per_edge": lvl_edge, "levels_per_rim": lvl_rim,
            "headline_rim": rim, "headline_retained_pct": ret,
            "null_rim": nrim, "n_headline": n_hl, "n_null": n_nu,
            "headline_frac_pos": hl.get("frac_positive") if hl else None,
            "headline_w50": hl.get("w50") if hl else None,
        })
        print(f"{bits:>5}{lv:>9}{lvl_edge:>10.1f}{lvl_rim:>9.2f}"
              f"{(rim if rim is not None else float('nan')):>+11.4f}{ret:>8.1f}"
              f"{(nrim if nrim is not None else float('nan')):>+10.4f}"
              f"{n_hl:>6}{n_nu:>8}")
        del arr, y

    print("-" * 78)

    # ORCH's saturation tell, applied to my own ladder.
    ns = [g["n_headline"] for g in out["rungs"]]
    varied = len(set(ns)) > 1
    out["sampling_varied"] = varied
    out["n_headline_by_rung"] = ns
    print(f"\nsample count across rungs: {ns}")
    if not varied:
        print("  *** SATURATED -- n never moved.  Per ORCH's rule this ladder "
              "has tested nothing and its result must not be quoted. ***")
    else:
        print("  sampling varies across rungs, so the ladder is live.")

    # Where does it actually break?
    broke = [g for g in out["rungs"]
             if g["headline_retained_pct"] == g["headline_retained_pct"]
             and abs(g["headline_retained_pct"] - 100.0) > 20.0]
    out["first_break"] = broke[0] if broke else None
    if broke:
        b = broke[0]
        print(f"\nfirst rung losing >20%: bits={b['bits']}, "
              f"{b['levels_per_edge']:.1f} levels per edge amplitude, "
              f"{b['levels_per_rim']:.2f} per rim, "
              f"retained {b['headline_retained_pct']:.1f}%")
    else:
        print("\nno rung on this ladder lost more than 20% of the headline.")

    with open(N6 / "n6-ladder.json", "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(f"wrote {N6 / 'n6-ladder.json'}")


if __name__ == "__main__":
    main()
