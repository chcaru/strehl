"""Independent re-derivation of `restore::gather_mtf`, and the ceiling it implies.

Two jobs, both adversarial toward `crates/strehl-core/src/restore.rs`, which is
BUILD-SHARP's own prior work and therefore cannot be trusted on its own tests.

1. RE-DERIVE THE MTF BY SIMULATION, not by the same closed form. `gather_mtf`
   builds the taps and evaluates their DFT analytically. Here a real sinusoid is
   really resampled by a real Catmull-Rom gather at a fixed sub-pixel phase, and
   the amplitude ratio is fitted out of the resampled samples. Two independent
   routes to the same number, or a defect.

2. THE CEILING. `18.6% of blur variance` is a variance share, and a variance
   share is not an edge-width share. Removing a fraction v of the variance
   narrows a width by 1 - sqrt(1 - v), so 18.6% of variance is 9.8% of width
   even for a PERFECT correction. The Wiener gain is then capped by the
   calibrated noise well below the ideal 1/H, so the realisable share is smaller
   again. This prints both, so the expected result is on the record before the
   filter is wired rather than after.
"""

from __future__ import annotations

import numpy as np

PHASE_SAMPLES = 64


def catmull_rom(t: float) -> float:
    a = abs(t)
    if a < 1.0:
        return 1.5 * a**3 - 2.5 * a**2 + 1.0
    if a < 2.0:
        return -0.5 * a**3 + 2.5 * a**2 - 4.0 * a + 2.0
    return 0.0


def mtf_by_simulation(
    f: float,
    phase_samples: int = PHASE_SAMPLES,
    n: int = 4096,
    tap_fn=catmull_rom,
    support: tuple[int, int] = (-1, 3),
) -> float:
    """Resample a real sinusoid and fit its amplitude out of the result.

    Deliberately shares no code path with `gather_mtf`: it never forms the DFT
    of the taps. It builds the signal, gathers it, and fits the gathered samples
    against a sin/cos basis by least squares.

    Least squares rather than the textbook `2 * mean(x * cos)` projection,
    because that factor of 2 is wrong at f = 0 and at f = 0.5. At Nyquist
    `sin(2 pi * 0.5 * k)` is identically zero on the integer grid, the component
    is its own conjugate, and the correct normalisation is 1x. The first version
    of this checker used the factor of 2 everywhere and reported Catmull-Rom's
    Nyquist MTF as 1.2501 against restore.rs's 0.6251 -- exactly 2x -- and
    called the module WRONG. The module was right. Least squares gets both the
    interior and the degenerate endpoint without a special case, because the
    zero column simply contributes nothing.
    """
    x = np.arange(n, dtype=np.float64)
    sig = np.cos(2.0 * np.pi * f * x)
    lo, hi = support
    amps = []
    for p in range(phase_samples):
        phi = (p + 0.5) / phase_samples
        acc = np.zeros(n)
        wsum = 0.0
        for tap_i in range(lo, hi):
            w = tap_fn(tap_i - phi)
            wsum += w
            acc += w * np.roll(sig, -tap_i)
        acc /= wsum
        s = slice(64, n - 64)
        xs = x[s]
        basis = np.stack(
            [np.cos(2.0 * np.pi * f * xs), np.sin(2.0 * np.pi * f * xs)], axis=1
        )
        coef, *_ = np.linalg.lstsq(basis, acc[s], rcond=None)
        amps.append(float(np.hypot(coef[0], coef[1])))
    return float(np.mean(amps))


def bilinear(t: float) -> float:
    return max(0.0, 1.0 - abs(t))


def check_mtf() -> None:
    print("1. RE-DERIVATION OF THE GATHER MTF (Catmull-Rom), by simulation\n")
    print(f"{'f (cyc/sample)':>16}{'restore.rs claims':>19}{'simulated':>12}{'diff':>10}")
    # 0.49 is a continuity control on the Nyquist endpoint: if the endpoint were
    # still being normalised wrongly it would sit far off the trend at 0.49.
    claimed = {0.25: 0.9402, 0.40: 0.7425, 0.49: None, 0.50: 0.6251}
    worst = 0.0
    for f, want in claimed.items():
        got = mtf_by_simulation(f)
        if want is None:
            print(f"{f:16.2f}{'(control)':>19}{got:12.4f}{'':>10}")
            continue
        worst = max(worst, abs(got - want))
        print(f"{f:16.2f}{want:19.4f}{got:12.4f}{got - want:+10.5f}")
    verdict = "CONFIRMED" if worst < 5e-3 else "DISAGREES"
    print(f"\n   largest disagreement {worst:.5f} -> {verdict}")

    # COMMISSIONING. A checker that only ever says CONFIRMED has proved nothing.
    # Substitute a kernel restore.rs does NOT claim these numbers for and
    # require the checker to notice.
    plant = mtf_by_simulation(0.40, tap_fn=bilinear, support=(0, 2))
    caught = abs(plant - 0.7425) > 5e-3
    print(
        f"   commissioning: bilinear at f=0.40 simulates {plant:.4f} against the "
        f"Catmull-Rom claim 0.7425 -> {'CAUGHT' if caught else 'MISSED'}"
    )
    if not caught:
        raise SystemExit("checker is inert: it cannot tell two kernels apart")
    print()


def wiener_gain(h: np.ndarray, nsr: float) -> np.ndarray:
    """G = H / (H^2 + sigma^2/S), clamped at 1 from below as the module does."""
    g = h / (h * h + nsr)
    return np.clip(g, 1.0, None)


def ceiling(var_share: float = 0.186) -> None:
    print("2. THE CEILING: a variance share is not a width share\n")
    perfect = 1.0 - np.sqrt(1.0 - var_share)
    print(f"   resampling is {100*var_share:.1f}% of blur VARIANCE")
    print(f"   a PERFECT zero-phase correction narrows the edge by "
          f"{100*perfect:.1f}%, not {100*var_share:.1f}%\n")

    f = np.linspace(1e-3, 0.5, 256)
    h = np.array([_mtf_analytic(v) for v in f])
    print(f"{'sigma^2/S':>12}{'max gain':>10}{'gain@0.25':>11}{'gain@Nyq':>10}"
          f"{'loss recovered':>16}{'width gain':>12}")
    for nsr in (0.0, 1e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1):
        g = wiener_gain(h, nsr)
        resid = h * g
        # Fraction of the gather's own MTF loss that is bought back, weighted by
        # frequency because edge width is set by the whole curve, not one point.
        recovered = np.trapezoid(resid - h, f) / np.trapezoid(1.0 - h, f)
        # Width share, on the same variance bookkeeping as `perfect` above.
        width = 1.0 - np.sqrt(1.0 - var_share * recovered)
        print(f"{nsr:12.0e}{g.max():10.3f}{np.interp(0.25, f, g):11.3f}"
              f"{g[-1]:10.3f}{100*recovered:15.1f}%{100*width:11.2f}%")
    print("\n   sigma^2/S is the ONLY knob and it is not free: it comes from the\n"
          "   calibrated noise model and the image's own power spectrum.\n")


def _mtf_analytic(f: float) -> float:
    acc = 0.0
    for p in range(PHASE_SAMPLES):
        phi = (p + 0.5) / PHASE_SAMPLES
        taps = [(n - phi, catmull_rom(n - phi)) for n in range(-1, 3)]
        s = sum(v for _, v in taps)
        re = sum(v / s * np.cos(2 * np.pi * f * d) for d, v in taps)
        im = sum(v / s * np.sin(2 * np.pi * f * d) for d, v in taps)
        acc += np.hypot(re, im)
    return acc / PHASE_SAMPLES


if __name__ == "__main__":
    check_mtf()
    ceiling()
