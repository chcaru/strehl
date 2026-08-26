"""Commission the s27.4 "ceiling" arm -- the instrument, not the result.

s27.4 published a `ceiling` column that reads exactly 1.0000 at every frequency,
and a `headroom` column derived from it. V-DEMOSAIC's charge is that the ceiling
arm was never commissioned: it was never shown capable of returning anything
other than 1.0, so its agreement with 1.0 is not evidence of anything, and the
headroom column is therefore just 1/D_malvar wearing a second column's clothes.

This tests that charge directly rather than accepting it. The oracle is
reconstructed as s27.4 describes it -- a least-squares fit of

    A*cos(2*pi*(fx*x + fy*y)) + B*sin(2*pi*(fx*x + fy*y)) + C

to the green quincunx samples alone, at a KNOWN (fx, fy) -- and then run against
three cases whose right answers are fixed by construction, not by measurement:

  IN-DIAMOND      |fx| + |fy| < 0.5. The tone is inside the quincunx support, so
                  the information is present and a correct ceiling returns 1.0.
                  This is the only case s27.4 ever ran.

  OUT-OF-DIAMOND  |fx| + |fy| > 0.5. The tone is OUTSIDE the support: the
                  quincunx lattice cannot distinguish it from its alias, so the
                  information is provably absent. A ceiling that still returns
                  1.0 here is measuring its own model, not the samples. THIS IS
                  THE NEGATIVE CONTROL, and it is the whole point.

  ALIAS PAIR      the tone AND its quincunx alias present together, in phase.
                  The lattice sees their sum; a fit to one of them alone cannot
                  report the amplitude of that one. Truth by construction is
                  that the single-component amplitude is NOT recoverable.

A ceiling arm that returns 1.0000 on all three is degenerate: it has been shown
incapable of reporting absence, which is the only thing a ceiling is for.
"""

from __future__ import annotations

import sys

import numpy as np

N = 256
MARGIN = 24


def quincunx_mask(n: int) -> np.ndarray:
    """Green sites of an RGGB CFA: (even row, odd col) and (odd row, even col)."""
    y, x = np.mgrid[0:n, 0:n]
    return ((y + x) % 2) == 1


def oracle_amplitude(green_full: np.ndarray, fx: float, fy: float) -> float:
    """s27.4's ceiling arm: 3-parameter LSQ fit at a KNOWN frequency, to the
    quincunx green samples alone."""
    m = quincunx_mask(N)
    m[:MARGIN, :] = m[-MARGIN:, :] = False
    m[:, :MARGIN] = m[:, -MARGIN:] = False
    y, x = np.mgrid[0:N, 0:N]
    ph = 2.0 * np.pi * (fx * x[m] + fy * y[m])
    a = np.column_stack([np.cos(ph), np.sin(ph), np.ones(ph.size)])
    coef, *_ = np.linalg.lstsq(a, green_full[m], rcond=None)
    return float(np.hypot(coef[0], coef[1])), ph.size


def tone(fx: float, fy: float, amp: float = 0.2, base: float = 0.5) -> np.ndarray:
    y, x = np.mgrid[0:N, 0:N]
    return base + amp * np.cos(2.0 * np.pi * (fx * x + fy * y))


def case(label: str, fx: float, fy: float, expect: str, img: np.ndarray) -> tuple[str, float]:
    got, nsamp = oracle_amplitude(img, fx, fy)
    ratio = got / 0.2
    print(f"  {label:<16} fx={fx:.2f} fy={fy:.2f}  |fx|+|fy|={abs(fx)+abs(fy):.2f}  "
          f"samples={nsamp:>7}  ceiling={ratio:.4f}   truth: {expect}")
    return label, ratio


def main() -> int:
    print("Commissioning the s27.4 ceiling arm.")
    print("A ceiling that cannot report absence cannot bound anything.\n")

    results = {}

    print("CASE 1 -- IN-DIAMOND (information present; correct answer 1.0)")
    for fx in (0.20, 0.35, 0.45):
        lbl, r = case(f"in {fx:.2f}", fx, 0.0, "1.0 (recoverable)", tone(fx, 0.0))
        results[lbl] = r

    print("\nCASE 2 -- OUT-OF-DIAMOND (information ABSENT; must NOT return 1.0)")
    for fx, fy in ((0.35, 0.35), (0.40, 0.40), (0.45, 0.30)):
        lbl, r = case(f"out {fx:.2f},{fy:.2f}", fx, fy, "NOT 1.0 -- outside support",
                      tone(fx, fy))
        results[lbl] = r

    print("\nCASE 3 -- ALIAS PAIR (tone + its quincunx alias; single amplitude not recoverable)")
    fx, fy = 0.35, 0.0
    ax, ay = fx - 0.5, fy - 0.5   # the quincunx alias partner
    both = tone(fx, fy) + (tone(ax, ay) - 0.5)
    lbl, r = case("alias pair", fx, fy, "NOT 1.0 -- sum is ambiguous", both)
    results[lbl] = r

    print("\n--- VERDICT ---")
    out_of_diamond = [v for k, v in results.items() if k.startswith("out ")]
    n_wrongly_unity = sum(1 for v in out_of_diamond if abs(v - 1.0) < 0.02)
    print(f"  out-of-diamond cases returning 1.0000 +/- 0.02 : "
          f"{n_wrongly_unity} of {len(out_of_diamond)}")
    if n_wrongly_unity == len(out_of_diamond):
        print("  DEGENERATE. The ceiling returns unity where the information is")
        print("  provably absent. It was never capable of reporting a shortfall,")
        print("  so 'ceiling = 1.0000 at every frequency' in s27.4 is a property of")
        print("  the instrument and not a measurement of the samples.")
        print("  => the s27.4 headroom column is 1/D_malvar and nothing more.")
    elif n_wrongly_unity == 0:
        print("  SOUND. The ceiling distinguishes present from absent information,")
        print("  so its unity readings in s27.4 are meaningful.")
    else:
        print("  PARTIAL -- discriminates on some cases and not others; unsafe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
