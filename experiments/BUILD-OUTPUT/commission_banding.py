"""Commission banding.py.  It reported 0.0% in all 10 strata; a detector whose
threshold can never be reached prints exactly that, forever, on every input.

The arms drive the instrument in BOTH directions, because a suite that only
plants degradations cannot distinguish a metric that is blind to a defect from
one that is perverse on it -- this project has shipped that bug.

  NULL   real subject                      -> must stay ~0
  R1     noise-free ramp, treads ~3 px      -> must stay ~0  (0.25 mm: correctly invisible)
  R2     noise-free ramp, treads ~8 px      -> must FIRE
  R3     noise-free ramp, treads ~40 px     -> must FIRE HARDER than R2  (monotone)
  Q6     R3 quantised to 6 bits             -> must FIRE at least as hard as R3
  DITH   R3 + 0.6-code noise                -> must GO QUIET   (IMPROVEMENT ARM)

DITH is the arm that matters most.  The claim this whole measurement rests on is
that real sensor noise dithers the quantiser and dissolves the staircase.  If
planting that dither on a KNOWN-banded input does not quiet the detector, then
the explanation offered for the 0.0% is wrong even if the 0.0% is right.

Everything is pushed through banding.tile_stats/summarise -- the same functions
that produced the corpus numbers, not a reimplementation of them.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import banding as B  # noqa: E402

H = W = 1024
RNG = np.random.default_rng(7)


def ramp(tread_px, base_code, noise_codes=0.0, bits=8):
    """16-bit smooth ramp whose 8-bit quantisation has treads `tread_px` wide."""
    step16 = 257.0 / tread_px                     # DN per pixel
    x = np.arange(W, dtype=np.float64)[None, :] * step16
    a16 = base_code * 257.0 + np.repeat(x, H, axis=0)
    if noise_codes:
        a16 = a16 + RNG.normal(0.0, noise_codes * 257.0, a16.shape)
    a16 = np.clip(a16, 0, 65535)
    q = 2 ** (16 - bits)
    a8 = np.clip(np.rint(a16 / q), 0, 2 ** bits - 1)
    if bits != 8:                                  # re-expand to 8-bit codes
        a8 = a8 * (2 ** (8 - bits))
    return a16, a8.astype(np.uint8)


def run(label, a16, a8):
    st = B.tile_stats(a16, a8)
    rows = B.summarise(st)
    tot = sum(n for _, n, _ in rows)
    bn = sum(r["banded_n"] for _, n, r in rows if n)
    pct = 100.0 * bn / tot if tot else float("nan")
    best = max((r for _, n, r in rows if n), key=lambda r: r["banded"], default=None)
    print(f"  {label:<34}{tot:>6} tiles  banded {bn:>4}/{tot:<5} = {pct:>6.1f}%"
          f"   tread {best['tread_mm']:.3f} mm  dL* {best['dL']:.2f}"
          if best else f"  {label:<34} no tiles")
    return pct


def main():
    d = np.diff(B.LSTAR)
    base = int(np.argmax(d))
    print(f"dL* per 8-bit code peaks at code {base} -> {d[base]:.3f} L*"
          f"   (threshold {B.MIN_DL}); ramps are placed there so the arm tests"
          f" TREAD, not the dL* gate\n")

    fails = []

    a16, a8 = B.load("tweezers-cpl")
    n_null = run("NULL  real tweezers-cpl", a16[:, :, 1], a8[:, :, 1])
    del a16, a8

    p1 = run("R1    noise-free, tread ~3 px", *ramp(3.0, base))
    p2 = run("R2    noise-free, tread ~8 px", *ramp(8.0, base))
    p3 = run("R3    noise-free, tread ~40 px", *ramp(40.0, base))
    q6 = run("Q6    R3 at 6 bits", *ramp(40.0, base, bits=6))
    dth = run("DITH  R3 + 0.6-code noise", *ramp(40.0, base, noise_codes=0.6))

    print()

    def check(name, cond, got):
        print(f"  {'PASS' if cond else 'FAIL':<5} {name:<52} {got}")
        if not cond:
            fails.append(name)

    check("NULL: real subject stays quiet", n_null < 1.0, f"{n_null:.1f}%")
    check("R1: 3-px (0.25 mm) treads correctly NOT banding", p1 < 1.0, f"{p1:.1f}%")
    check("R2: 8-px treads FIRE", p2 > 50.0, f"{p2:.1f}%")
    check("R3: 40-px treads FIRE", p3 > 50.0, f"{p3:.1f}%")
    check("POTENCY monotone in tread: R1 < R2 <= R3",
          p1 < p2 <= p3 + 1e-9, f"{p1:.1f} < {p2:.1f} <= {p3:.1f}")
    check("Q6: coarser quantisation no better than R3", q6 >= p3 - 1e-9,
          f"{q6:.1f}% vs {p3:.1f}%")
    check("IMPROVEMENT: planted dither QUIETS a known-banded input",
          dth < p3 / 2.0, f"{dth:.1f}% vs banded {p3:.1f}%")

    print()
    if fails:
        print(f"COMMISSIONING: FAIL -- {len(fails)} arm(s): {fails}")
        return 1
    print("COMMISSIONING: PASS -- the detector fires on planted banding, scales")
    print("  with tread width, and is quieted by planted dither.  Its 0.0% on the")
    print("  corpus is therefore a fact about the corpus, and the dither")
    print("  explanation for that 0.0% is itself demonstrated, not asserted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

