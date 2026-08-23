"""03 -- M61 PRE-REGISTRATION: does the estimator have the power to see H1?

=============================================================================
THIS DOCSTRING IS PART OF THE PRE-REGISTRATION and is committed with 02
before either is run.
=============================================================================

Rule 20 says: before running a gate, write down the input that would make it
FAIL, and check such an input exists.  Rule 39 says: do not report a ratio
without the null it is measured against.  Rule 34 says: a plant that supplies
its own noise constant cannot validate that constant.

So this script does exactly one job.  It plants a KNOWN conversion gain in a
synthetic frame pair built from a real 109MSDCF plane, runs `02-ptc-ladder`'s
estimator functions UNCHANGED on it, and asks whether the estimator returns
the planted value.  It then plants `g / 2.174` -- the exact size of the effect
M48c's fact 17 predicts -- and asks whether the estimator returns 0.460.

**Per rule 34 this validates the OPERATOR and cannot validate the
calibration.**  It proves the measurement in script 02 has the power to reject
H0 if H1 is true.  It says nothing whatever about the sensor.

CASES, AND THE ACCEPTANCE CRITERION FOR EACH, FIXED HERE
--------------------------------------------------------
Scene: `109MSDCF` frame 11, plane G1, 3x3-box-smoothed so the planted surface
is a surface and not a noise field, expressed in electrons as
`(DN - 512) / g_plant`.  Two frames are then rendered as

    DN = round( Poisson(S) * g_plant + Normal(0, RN_e * g_plant) ) + 512

  1. `flat-g366`   g_plant = 0.36630 (the ISO-160 model value), no shift,
     no level change.
     ACCEPT if the estimator returns g within +-5% of 0.36630.
  2. `flat-g168`   g_plant = 0.36630 / 2.174 = 0.16850, otherwise identical.
     ACCEPT if the estimator returns g/0.36630 within +-0.05 of 0.460.
     **This is the case that proves the experiment can detect H1.**
  3. `shift-g366`  g_plant = 0.36630, plus a 0.20 px horizontal sub-pixel
     shift between the two frames and a +1.0% multiplicative level change on
     the second -- i.e. the two nuisances the estimator's `u` covariate is
     built to absorb, at the scale M29 (0.07-0.22 green px adjacent-frame
     warp) and M24 (0.91%-11.70% peak-to-peak level drift) measured.
     ACCEPT if the estimator returns g within +-5% of 0.36630.
  4. `iso1000-g229` g_plant = 2.28938 with the scene scaled so the mean DN is
     ~250, i.e. the ISO-1000 regime of `foam` / `coffee-bubbles`.
     ACCEPT if the estimator returns g within +-5% of 2.28938.
     This checks that the estimator is not level-dependent between the
     high-ISO regime and the control regime, which is artefact 1 in 02's list.
  5. `iso1000-g105` g_plant = 2.28938 / 2.174 at the SAME DN level as case 4
     (the scene's electron count is scaled up so the DN level is unchanged).
     ACCEPT if the estimator returns g/2.28938 within +-0.05 of 0.460.
  6. `null-doubled`  case 1 with the rendered noise multiplied by sqrt(2)
     after the fact.  The estimator MUST return ~2x the planted gain.  If it
     returns 0.36630 anyway it is pinned to something other than the data and
     every other case is vacuous.

A case that misses its band is a FAILURE of the estimator and is reported as
one; the pre-registration does not allow a band to be widened afterwards.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m61-ptc-high-iso/src/03-power-control.py
"""

from __future__ import annotations

import importlib.util
import os
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "power-control.txt")
STACK = r"D:\personal\macro\109MSDCF"
BLACK = 512.0
RN_E = 4.20
SEED = 20260823
LINES: list[str] = []


def say(s: str = "") -> None:
    print(s, flush=True)
    LINES.append(s)


def load_ladder():
    spec = importlib.util.spec_from_file_location(
        "ladder", os.path.join(HERE, "02-ptc-ladder.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def box3(a: np.ndarray) -> np.ndarray:
    k = np.ones(3, dtype=np.float64) / 3.0
    b = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 1, a)
    return np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 0, b)


def scene_electrons(g_ref: float) -> np.ndarray:
    """The real 109MSDCF G1 plane as a smooth electron surface."""
    import glob

    import rawpy

    fs = sorted(glob.glob(os.path.join(STACK, "*.ARW")))
    with rawpy.imread(fs[11]) as rr:
        pl = np.asarray(rr.raw_image_visible[0::2, 1::2],
                        dtype=np.float64).copy()
    dn = np.maximum(pl - BLACK, 1.0)
    return box3(dn) / g_ref


def render(S: np.ndarray, g: float, rng, shift_px: float = 0.0,
           level: float = 1.0, noise_mult: float = 1.0):
    """Two independent frames of the same electron surface, as uint16 raw DN."""
    def one(scene):
        e = rng.poisson(np.maximum(scene, 0.0)).astype(np.float64)
        n = (e - scene) * noise_mult + scene
        dn = n * g + rng.normal(0.0, RN_E * g * noise_mult, size=scene.shape)
        return np.clip(np.round(dn + BLACK), 0, 16383).astype(np.uint16)

    s2 = S
    if shift_px:
        s2 = (1.0 - shift_px) * S + shift_px * np.roll(S, -1, axis=1)
    return one(S), one(s2 * level)


def run_case(L, tag: str, a, b, g_plant: float, g_ref: float, band, kind):
    m, v, u, ok = L.tile_stats(a, b)
    m, v, u = m[ok], v[ok], u[ok]
    lo = float(np.percentile(m, 1.0))
    hi = float(np.percentile(m, 99.5))
    est = L.bin_estimates(m, v, u, lo, hi)
    gA = L.fit_ptc([(e[0], e[1], e[2]) for e in est])[0]
    gB = L.fit_ptc([(e[0], e[3], e[4]) for e in est])[0]
    gC = L.fit_ptc([(e[0], e[5], e[6]) for e in est])[0]
    if kind == "abs":
        val, target = gA / g_plant, 1.0
        txt = f"gA/g_plant = {val:.4f}"
    else:
        val, target = gA / g_ref, 0.460
        txt = f"gA/g_ref = {val:.4f}"
    good = band[0] <= val <= band[1]
    say(f"  {tag:<14} planted g {g_plant:>8.5f}   measured gA {gA:>8.5f} "
        f"gB {gB:>8.5f} gC {gC:>8.5f}")
    say(f"                 mean level {m.mean():>8.1f} DN   {txt}   "
        f"band [{band[0]:.3f},{band[1]:.3f}]   "
        f"=> {'PASS' if good else 'FAIL'}")
    return good


def main() -> int:
    t0 = time.time()
    L = load_ladder()
    rng = np.random.default_rng(SEED)
    say("M61 script 03 -- power control for the estimator (rule 20 / 34 / 39)")
    say(f"seed {SEED}; estimator functions imported from 02-ptc-ladder.py, "
        f"TILE={L.TILE} N_BINS={L.N_BINS} qA={L.Q_A}")
    say()

    g160 = 160.0 / 436.8
    g1000 = 1000.0 / 436.8
    results = []

    say("cases 1-3: ISO-160 regime")
    S = scene_electrons(g160)
    say(f"  scene: 109MSDCF frame 11 G1, 3x3 boxed, "
        f"{S.shape} px, mean {S.mean():.0f} e-, "
        f"i.e. {S.mean() * g160:.0f} DN at g={g160:.5f}")
    a, b = render(S, g160, rng)
    results.append(("flat-g366", run_case(L, "flat-g366", a, b, g160, g160,
                                          (0.95, 1.05), "abs")))
    a, b = render(S * 2.174, g160 / 2.174, rng)
    results.append(("flat-g168", run_case(L, "flat-g168", a, b, g160 / 2.174,
                                          g160, (0.410, 0.510), "rel")))
    a, b = render(S, g160, rng, shift_px=0.20, level=1.01)
    results.append(("shift-g366", run_case(L, "shift-g366", a, b, g160, g160,
                                           (0.95, 1.05), "abs")))
    say()

    say("cases 4-5: ISO-1000 regime (mean level ~250 DN)")
    S1000 = S * (g160 / g1000) * (250.0 / (S.mean() * g160))
    a, b = render(S1000, g1000, rng)
    results.append(("iso1000-g229", run_case(L, "iso1000-g229", a, b, g1000,
                                             g1000, (0.95, 1.05), "abs")))
    a, b = render(S1000 * 2.174, g1000 / 2.174, rng)
    results.append(("iso1000-g105", run_case(L, "iso1000-g105", a, b,
                                             g1000 / 2.174, g1000,
                                             (0.410, 0.510), "rel")))
    say()

    say("case 6: the null for the control -- noise scaled by sqrt(2)")
    a, b = render(S, g160, rng, noise_mult=np.sqrt(2.0))
    m, v, u, ok = L.tile_stats(a, b)
    est = L.bin_estimates(m[ok], v[ok], u[ok],
                          float(np.percentile(m[ok], 1.0)),
                          float(np.percentile(m[ok], 99.5)))
    gA = L.fit_ptc([(e[0], e[1], e[2]) for e in est])[0]
    good = 1.85 <= gA / g160 <= 2.15
    say(f"  null-doubled   planted g {g160:.5f} with sqrt(2)x noise   "
        f"measured gA {gA:.5f}   ratio {gA / g160:.4f}   "
        f"band [1.85,2.15]   => {'PASS' if good else 'FAIL'}")
    results.append(("null-doubled", good))
    say()

    npass = sum(1 for _, g in results if g)
    say(f"VERDICT: {npass}/{len(results)} pre-registered cases pass.")
    if npass == len(results):
        say("The estimator recovers a planted gain, recovers a planted "
            "2.174x gain error as 0.460, is not fooled by a 0.20 px shift "
            "plus a 1% level step, works in both level regimes, and is not "
            "pinned (case 6 moves it by 2x).  Script 02's comparison has "
            "power to reject H0.")
    else:
        say("At least one case failed.  Script 02's numbers must be read "
            "against this failure.")
    say(f"[{time.time() - t0:.0f}s]")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
