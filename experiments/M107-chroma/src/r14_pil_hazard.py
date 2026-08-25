"""R14 -- what PIL's silent 16->8 bit narrowing would have done to MY metric.

M107 never used PIL: every TIFF read in experiments/M107-chroma/src is
`tifffile.imread` and every raw read is `rawpy.imread` (grep-verified, 0 hits
for PIL/Image.open). So this milestone's exposure is nil.

ORCH's fleet hazard notice asks us not to argue from first principles that
8 bits would have been enough -- "that is exactly the argument that would have
hidden this". So this script does not argue. It emulates the loss on the real
R13 A/B and re-runs the real R13 estimator, to convert ORCH's general warning
("a floor of ~128 counts under every difference") into a measured statement on
an actual strehl metric.

The lateral-CA A/B is ORCH's "most suspect of all" category by construction:
the entire signal is a sub-pixel resample difference, so it lives in exactly
the counts that an 8-bit quantum destroys.

BARS -- registered before running, per AGENTS.md.

  H1  MAGNITUDE.  The median |on - off| over textured pixels, in 16-bit
      counts, versus the 8-bit quantum of 257 counts.  If the median
      difference is BELOW 257 the signal is entirely inside the quantisation
      error and PIL would have had to destroy it.  I expect it is below.
      Falsified if the median exceeds 257 counts.

  H2  DID IT ACTUALLY BREAK.  Re-run the R13 X1 transfer check on 8-bit-
      narrowed copies.  True-uint16 reference: applied/eps_r = 0.8338.
      I register that the 8-bit value will differ MATERIALLY, |delta| > 0.05.
      Falsified if the 8-bit transfer check lands within 0.05 of 0.8338 --
      in which case this metric was robust to the hazard and I must say so.

  H3  THE FAILURE MODE.  I register the prediction that the 8-bit number will
      be a PLAUSIBLE one -- finite, right order of magnitude, not NaN and not
      absurd -- because ORCH's thesis is that the danger is a believable
      number rather than an error.  Falsified if it returns NaN/inf or a
      value off by more than 10x, which would make the hazard self-announcing
      and therefore much less dangerous than claimed.

H2 and H3 are deliberately opposed in spirit: H2 asks whether it moved, H3
asks whether the move would have been noticed. The hazard is only as bad as
ORCH says if BOTH hold.
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r13_clean_calib import EPS, R13, estimate  # noqa: E402

QUANTUM = 257.0  # one 8-bit step expressed in 16-bit counts (65535/255)


def narrow(a):
    """Emulate PIL.Image.open()'s silent uint16 -> uint8 RGB collapse."""
    return (a.astype(np.float64) / QUANTUM).astype(np.uint8).astype(np.float32) * QUANTUM


def transfer(ro, go, rn, gn):
    e_off = estimate(ro, go)["rad"]
    e_on = estimate(rn, gn)["rad"]
    return (e_on - e_off) / EPS, e_off, e_on


def main():
    print("=" * 70)
    print("R14 -- PIL 16->8 bit hazard, measured on the real M107 A/B")
    print("=" * 70)

    off = tifffile.imread(os.path.join(R13, "off.tif"))
    on = tifffile.imread(os.path.join(R13, "on.tif"))
    print(f"\ntrue read via tifffile: {off.shape} {off.dtype}  "
          f"levels off={len(np.unique(off))} on={len(np.unique(on))}")
    nb = narrow(off)
    print(f"after PIL-equivalent narrowing: levels={len(np.unique(nb))}  "
          f"({len(np.unique(off))/max(len(np.unique(nb)),1):.0f}x loss)")

    ro, go = off[..., 0].astype(np.float32), off[..., 1].astype(np.float32)
    rn, gn = on[..., 0].astype(np.float32), on[..., 1].astype(np.float32)

    print("\nH1  MAGNITUDE OF THE SIGNAL vs THE 8-BIT QUANTUM")
    d = np.abs(rn - ro)
    gy, gx = np.gradient(ro)
    tex = (gx * gx + gy * gy) > np.percentile(gx * gx + gy * gy, 90.0)
    med = float(np.median(d[tex]))
    p90 = float(np.percentile(d[tex], 90.0))
    frac = float((d[tex] < QUANTUM).mean())
    print(f"    red channel |on - off| on the top-decile textured pixels")
    print(f"    median {med:8.1f} counts   p90 {p90:8.1f} counts")
    print(f"    one 8-bit quantum = {QUANTUM:.0f} counts")
    print(f"    fraction of the signal below one quantum: {100*frac:.1f}%")
    h1 = med < QUANTUM
    print(f"    H1 {'HOLDS' if h1 else 'FALSIFIED'} -- signal is "
          f"{'inside' if h1 else 'above'} the quantisation error")

    print("\nH2/H3  THE TRANSFER CHECK, BOTH WAYS")
    t16, o16, n16 = transfer(ro, go, rn, gn)
    t8, o8, n8 = transfer(narrow(off[..., 0]), narrow(off[..., 1]),
                          narrow(on[..., 0]), narrow(on[..., 1]))
    print(f"    uint16 (tifffile) : off {o16*1e6:+8.1f}  on {n16*1e6:+8.1f}  "
          f"applied/eps_r = {t16:.4f}")
    print(f"    uint8  (PIL-equiv): off {o8*1e6:+8.1f}  on {n8*1e6:+8.1f}  "
          f"applied/eps_r = {t8:.4f}")
    delta = abs(t8 - t16)
    h2 = delta > 0.05
    print(f"    delta {delta:.4f}   H2 {'HOLDS' if h2 else 'FALSIFIED'} "
          f"-- the hazard {'moves' if h2 else 'does not move'} this metric")

    plausible = np.isfinite(t8) and 0.1 * abs(t16) < abs(t8) < 10.0 * abs(t16)
    print(f"    H3 {'HOLDS' if plausible else 'FALSIFIED'} -- the 8-bit value is "
          f"{'plausible (no alarm would have sounded)' if plausible else 'self-announcing'}")

    print("\n" + "=" * 70)
    print(f"VERDICT: hazard is {'REAL AND SILENT' if (h2 and plausible) else 'not both real and silent'}"
          f" on this metric.  M107 exposure: NIL (tifffile throughout).")
    print("=" * 70)


if __name__ == "__main__":
    main()
