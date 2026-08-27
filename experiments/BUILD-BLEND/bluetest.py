"""Is the blue-led crush an ACHROMATIC undershoot, or a chroma-path bug?

ORCH's hypothesis: blue is not special. Blue has the smallest pedestal in
camera-linear space, so an achromatic undershoot of D DN drives B to zero
first while R and G survive it. If true, a per-channel clamp treats a symptom,
and clamping channels independently at zero converts an achromatic undershoot
into an irreversible yellow-green cast.

ORCH proposed testing this by reading the reference's per-channel pedestal at
the zero sites. That is necessary but not sufficient: a low blue pedestal is
consistent with BOTH stories, because a chroma bug would also show up
preferentially where blue is already low.

THE SHARPER TEST, and the one this script leads with: at sites where ONLY blue
reached zero, measure what happened to R and G.

    achromatic undershoot  blend - ctrl is roughly EQUAL and NEGATIVE in all
                           three channels. R and G fell by about the same DN
                           that drove B through zero; they merely had further
                           to fall. The predicted delta magnitude is
                           ctrl_B at those sites, since B landed exactly on 0.

    chroma-path bug        blend_R ~ ctrl_R and blend_G ~ ctrl_G at those
                           sites. Only blue moved.

These predictions are quantitative and mutually exclusive, so the measurement
can come out either way. Reported with the pedestals ORCH asked for.

Usage:  python bluetest.py <CTRL.tiff> <BLEND.tiff>
"""

import sys

import numpy as np
import tifffile


def q(name, a):
    if a.size == 0:
        print(f"  {name:<28} (empty)")
        return
    p = np.percentile(a, [25, 50, 75])
    print(f"  {name:<28} p25 {p[0]:9.1f}   p50 {p[1]:9.1f}   p75 {p[2]:9.1f}")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    ctrl = tifffile.imread(sys.argv[1]).astype(np.int32)
    blend = tifffile.imread(sys.argv[2]).astype(np.int32)
    if ctrl.shape != blend.shape:
        raise SystemExit(f"SHAPE MISMATCH {ctrl.shape} vs {blend.shape}")

    z = [blend[..., c] == 0 for c in range(3)]
    zr = [ctrl[..., c] == 0 for c in range(3)]
    n = z[0].size
    print(f"shape {ctrl.shape}")
    print("\nper-channel exact-zero rise over reference:")
    for c, nm in enumerate("RGB"):
        print(f"  {nm}  ctrl {zr[c].mean()*100:8.4f}%   blend {z[c].mean()*100:8.4f}%"
              f"   rise {(z[c].sum()-zr[c].sum())/n*100:+8.4f}%")

    b_only = z[2] & ~z[0] & ~z[1]
    print(f"\nblue-ONLY zero sites: {int(b_only.sum())} px ({b_only.mean()*100:.4f}%)")
    if b_only.sum() == 0:
        print("  no blue-only zeros; this build does not exhibit the defect")
        return 0

    # ORCH's requested pedestal read.
    print("\nREFERENCE pedestal at the blue-only zero sites:")
    for c, nm in enumerate("RGB"):
        q(f"ctrl {nm}", ctrl[..., c][b_only])
    print("  frame-wide reference pedestal, for scale:")
    for c, nm in enumerate("RGB"):
        q(f"ctrl {nm} (all px)", ctrl[..., c].ravel())

    # THE DISCRIMINATOR.
    print("\nblend - ctrl at the SAME blue-only zero sites:")
    d = [(blend[..., c] - ctrl[..., c])[b_only] for c in range(3)]
    for c, nm in enumerate("RGB"):
        q(f"delta {nm}", d[c])

    med = [float(np.median(x)) for x in d]
    predicted = float(np.median(ctrl[..., 2][b_only]))
    print(f"\n  blue fell by (median)                {med[2]:9.1f} DN")
    print(f"  achromatic story predicts R and G also fell by about {-predicted:9.1f} DN")
    print(f"  R actually fell by                   {med[0]:9.1f} DN")
    print(f"  G actually fell by                   {med[1]:9.1f} DN")

    # Ratio of observed R/G movement to the movement the achromatic story
    # requires. Near 1 => achromatic. Near 0 => chroma-only.
    fr = med[0] / med[2] if med[2] != 0 else float("nan")
    fg = med[1] / med[2] if med[2] != 0 else float("nan")
    print(f"\n  R movement as a fraction of B movement  {fr:6.3f}")
    print(f"  G movement as a fraction of B movement  {fg:6.3f}")

    print("\nVERDICT")
    if fr > 0.6 and fg > 0.6:
        print("  ACHROMATIC UNDERSHOOT. R and G fell by a comparable DN and")
        print("  simply had further to fall. A per-channel zero clamp treats a")
        print("  symptom and would convert this into a yellow-green cast; the")
        print("  fix belongs in the reconstruction and must preserve channel ratio.")
    elif fr < 0.25 and fg < 0.25:
        print("  CHROMA-PATH BUG. R and G barely moved at sites where blue was")
        print("  driven through zero. ORCH's achromatic hypothesis is refuted and")
        print("  the defect is specific to the blue path.")
    else:
        print(f"  MIXED (R {fr:.3f}, G {fg:.3f}). Neither story is clean; report")
        print("  the deltas rather than a one-word verdict.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
