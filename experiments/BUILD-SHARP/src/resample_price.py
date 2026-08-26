"""Price one Catmull-Rom resample as a function of its sub-pixel displacement.

Context
-------
A message routed to ORCH hypothesises that the lateral-CA correction's BLUE
channel "pays a full interpolation blur for a shift it cannot deliver": its
measured radial displacement is 0.039 px, statistically indistinguishable from
the untouched green reference, while `caprice.py` measures blue losing 9.36% of
its edge high-frequency energy.

That is a resampling-loss question, which is BUILD-SHARP's lane (step 1c of the
original mandate: "count the number of resampling operations a pixel undergoes
and measure the MTF cost of each"). It is answerable in closed form and with no
render, because the kernel is OUR OWN and is known to machine precision.

The key fact the hypothesis appears to miss
-------------------------------------------
Catmull-Rom is an INTERPOLATING kernel. At zero sub-pixel phase its taps are
exactly [0, 1, 0, 0] and the resample is the EXACT IDENTITY -- not approximately,
exactly. This is already asserted in restore.rs's
`kernels_are_interpolating_and_preserve_dc` test. So the blur cost of a resample
is not a constant that you either pay or avoid; it is a function of phase that
vanishes at phi = 0 and peaks at phi = 0.5.

The question is therefore quantitative, and it inverts: what displacement would
a single Catmull-Rom resample need in order to cost 9.36% of edge HF amplitude?
If that displacement is far above blue's measured 0.039 px, the resample cannot
be the source of the loss and the "free blur" story is wrong -- whatever else is
true about blue.

The tap formula here is the same one independently re-derived and CONFIRMED to
5e-5 against a simulated gather in `restore_check.py`. It is not taken on trust
from restore.rs; restore.rs was checked against it.
"""

from __future__ import annotations

import numpy as np

# Catmull-Rom, a = -0.5. Identical to strehl-core's `restore::tap`.
def tap(x: float) -> float:
    x = abs(x)
    if x < 1.0:
        return 1.5 * x**3 - 2.5 * x**2 + 1.0
    if x < 2.0:
        return -0.5 * x**3 + 2.5 * x**2 - 4.0 * x + 2.0
    return 0.0


def mtf(f: float, phi: float) -> float:
    """Amplitude response of a Catmull-Rom resample by `phi`, at frequency `f`.

    Compared against an IDEAL shift by the same phi, which has unit amplitude at
    every frequency. So this is the blur the resample costs, with the intended
    displacement divided out; a value of 1.0 means the resample was free.
    """
    ns = np.arange(-1, 3)
    w = np.array([tap(n - phi) for n in ns])
    w = w / w.sum()
    return float(abs(np.sum(w * np.exp(-2j * np.pi * f * (ns - phi)))))


def phase_averaged(f: float, samples: int = 4096) -> float:
    return float(np.mean([mtf(f, p) for p in np.linspace(0.0, 1.0, samples, endpoint=False)]))


def invert(loss: float, f: float) -> float:
    """Smallest |phi| whose resample costs `loss` fractional amplitude at `f`."""
    target = 1.0 - loss
    lo, hi = 0.0, 0.5
    if mtf(f, hi) > target:
        return float("nan")  # even the worst phase cannot cost this much
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if mtf(f, mid) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main() -> None:
    print("Catmull-Rom resample cost vs sub-pixel displacement")
    print("(1.000 = the resample was free; an ideal shift is 1.000 everywhere)\n")

    bands = [0.15, 0.25, 0.35, 0.40, 0.50]
    print(f"{'phi px':>8} " + " ".join(f"{'f=' + format(f, '.2f'):>9}" for f in bands))
    for phi in [0.0, 0.010, 0.039, 0.050, 0.100, 0.152, 0.200, 0.300, 0.500]:
        row = " ".join(f"{mtf(f, phi):9.5f}" for f in bands)
        mark = ""
        if abs(phi - 0.039) < 1e-9:
            mark = "   <- BLUE's measured radial displacement"
        if abs(phi - 0.152) < 1e-9:
            mark = "   <- RED's measured radial displacement"
        print(f"{phi:8.3f} {row}{mark}")

    print(f"\n{'phase-avg':>8} " + " ".join(f"{phase_averaged(f):9.5f}" for f in bands))

    print("\n\nINVERSION: what displacement is needed to cost a given HF amplitude loss?")
    print(f"{'loss':>8} " + " ".join(f"{'f=' + format(f, '.2f'):>9}" for f in bands))
    for loss in [0.01, 0.02, 0.05, 0.0936, 0.15]:
        cells = []
        for f in bands:
            p = invert(loss, f)
            cells.append("  IMPOSS." if np.isnan(p) else f"{p:9.4f}")
        mark = "   <- blue's measured HF energy loss" if abs(loss - 0.0936) < 1e-9 else ""
        print(f"{loss * 100:7.2f}% " + " ".join(cells) + mark)

    print("\n\nTHE POINT, stated as a ratio:")
    for f in [0.25, 0.35, 0.50]:
        cost = 1.0 - mtf(f, 0.039)
        need = invert(0.0936, f)
        print(
            f"  at f={f:.2f} cyc/px: a 0.039 px resample costs {cost * 100:.4f}% amplitude; "
            f"costing 9.36% needs {'>0.5 px (impossible)' if np.isnan(need) else f'{need:.4f} px'}"
            + ("" if np.isnan(need) else f", which is {need / 0.039:.0f}x blue's displacement")
        )

    print("\nCONTROL -- the two facts that make this checkable rather than asserted:")
    print(f"  identity at phi=0, f=Nyquist : {mtf(0.5, 0.0):.12f}  (must be exactly 1)")
    print(f"  DC preserved at phi=0.5      : {mtf(0.0, 0.5):.12f}  (must be exactly 1)")
    print(f"  worst case, phi=0.5 @ Nyquist: {mtf(0.5, 0.5):.5f}  (the 'full' blur being invoked)")


if __name__ == "__main__":
    main()
