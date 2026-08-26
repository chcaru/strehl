"""Does ORCH's measured far-field bowl survive on uncontaminated data?

ORCH registered criterion (a) from a profile of ca-ctrl/ca-blend-*.tiff. Those
two files declare in their own ImageDescription that they are sRGB-encoded AND
tone-mapped, with DIFFERENT per-image black/white points per arm (black 0.011119
vs 0.000000). rimprofile.py then applies its own srgb() on top.

This script asks one question with one answer: convert ORCH's published "of 255"
rows back to DN at the operating point their own published pair pins, and compare
them to the same rows measured on untoned linear renders of the same capture.

The test has a built-in control that makes it falsifiable rather than merely
suggestive:

  If the toning is the explanation, the CONTROL arm should transfer (it was toned
  with an ordinary black point) while the BLEND arm should not (its black point
  collapsed to exactly 0.000000, which is the signature of >=0.1% of pixels at
  zero luminance).

  If instead my untoned renders are simply different pictures, or my instrument
  disagrees with ORCH's, then BOTH arms should fail to transfer, by similar
  factors. That outcome would refute the tone explanation and I would have to
  accept the bowl as measured.

So the discriminating quantity is the RATIO OF THE TWO TRANSFER ERRORS, not
either one alone.
"""
import numpy as np

# ORCH's operating point, pinned by the two numbers they published together.
ORCH_REF_DN = 59630.0
ORCH_REF_ENC = 248.1

# ORCH's published table (of 255, vs far field), corrected instrument.
ORCH = {  # d: (control, blend)
    2:   (-41.56, -40.17),
    90:  (-7.69,  -4.09),
    175: (-3.17,  -3.42),
    350: (-0.50,  -2.69),
    550: (-0.79,  -3.15),
}

# Measured here on UNTONED LINEAR renders of the same capture, deficit vs each
# arm's own far field, shared mask and shared encode white (bowl/ladder.txt).
MINE = {  # d: (control, blend mc0)
    2:   (-4584, -4743),
    90:  (-1095,  -219),
    175:  (-748,  -181),
    350:  (-319,  -271),
    550:  (-222,  -413),
}


def enc_to_dn():
    """Invert enc = 255*srgb(l/white) around ORCH's far field."""
    y = ORCH_REF_ENC / 255.0
    x = ((y + 0.055) / 1.055) ** 2.4
    white = ORCH_REF_DN / x
    dsrgb = 1.055 * (1 / 2.4) * x ** (1 / 2.4 - 1)
    slope = 255.0 * dsrgb / white           # of 255 per DN
    return slope, white


slope, white = enc_to_dn()
print(f"ORCH operating point: far field {ORCH_REF_DN:.0f} DN = {ORCH_REF_ENC} of 255")
print(f"  implied encode white = {white:.0f} DN")
print(f"  slope                = {slope:.6f} of 255 per DN   (1.0 of 255 = {1/slope:.0f} DN)")
print()

print("ORCH's rows converted to DN, against the same rows measured untoned")
print()
print(f"  {'d':>5}  {'--------- CONTROL ---------':^32}  {'---------- BLEND ----------':^32}")
print(f"  {'':>5}  {'ORCH DN':>10}{'mine DN':>10}{'ratio':>12}  "
      f"{'ORCH DN':>10}{'mine DN':>10}{'ratio':>12}")
crat, brat = [], []
for d in sorted(ORCH):
    oc, ob = (v / slope for v in ORCH[d])
    mc, mb = MINE[d]
    rc = oc / mc if mc else float("nan")
    rb = ob / mb if mb else float("nan")
    print(f"  {d:>5}  {oc:>10.0f}{mc:>10.0f}{rc:>12.2f}  {ob:>10.0f}{mb:>10.0f}{rb:>12.2f}")
    crat.append(abs(rc))
    brat.append(abs(rb))

print()
# The far-field rows are the ones criterion (a) is about.
far = [d for d in sorted(ORCH) if d >= 350]
fc = np.median([abs(ORCH[d][0] / slope / MINE[d][0]) for d in far])
fb = np.median([abs(ORCH[d][1] / slope / MINE[d][1]) for d in far])
print(f"median transfer ratio over the criterion-(a) rows (d >= 350):")
print(f"  CONTROL arm : {fc:.2f}x")
print(f"  BLEND   arm : {fb:.2f}x")
print(f"  discriminating ratio (blend/control) = {fb/fc:.2f}x")
print()
if fb / fc > 2.0:
    print("  The control arm transfers and the blend arm does not, by a wide")
    print("  margin. Both were profiled by the same instrument on the same")
    print("  capture, so an instrument or subject difference would have moved")
    print("  BOTH. What differs between them is that the blend file was toned")
    print("  with a collapsed black point (0.000000) and the control was not.")
    print()
    print("  => the far-field bowl ORCH measured is dominated by the per-image")
    print("     tone applied to the blend arm, not by the merge.")
else:
    print("  Both arms transfer similarly. The tone explanation is REFUTED and")
    print("  the bowl must be accepted as measured.")

print()
print("residual real bowl on untoned data, blend minus control, in DN:")
for d in far:
    exc = abs(MINE[d][1]) - abs(MINE[d][0])
    print(f"  d={d:>4}: {exc:+6.0f} DN excess over control "
          f"= {exc*slope:+.2f} of 255 at ORCH's operating point "
          f"(their bar: 1.00)")
