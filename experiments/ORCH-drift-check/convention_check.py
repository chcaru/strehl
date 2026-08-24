"""Does any plausible radius-convention ratio land on the measured CA gain?

ORCH told M107 that a normalised-radius convention error lands "in this numeric
neighbourhood". That was pattern-matching. This checks it.

Measured (M111 re-analysis of ORCH's ring table):
  inside support, n=6 rings, mean 1.4562, 95% CI [1.4256, 1.4867]
  all seven rings, mean 1.4454, 95% CI [1.4095, 1.4814]
"""
import itertools
import math

W, H = 7032, 4688

hw, hh = W / 2.0, H / 2.0
hd = math.hypot(hw, hh)
fw, fh_, fd = float(W), float(H), math.hypot(W, H)

NORMS = {
    "half-width": hw,
    "half-height": hh,
    "half-diagonal": hd,
    "full-width": fw,
    "full-height": fh_,
    "full-diagonal": fd,
}

CI_IN = (1.4256, 1.4867)
CI_ALL = (1.4095, 1.4814)
MEAN_IN = 1.4562

print("frame %d x %d   aspect %.6f" % (W, H, W / H))
print("half-width %.1f  half-height %.1f  half-diagonal %.1f" % (hw, hh, hd))
print()
print("Ratios of one normalisation to another (a fit/apply mismatch is such a ratio):")
print()

hits_in, hits_all, rows = [], [], []
for (na, va), (nb, vb) in itertools.permutations(NORMS.items(), 2):
    r = va / vb
    if not (1.0 < r < 3.0):
        continue
    rows.append((r, na, nb))

# a mismatch can also appear under a square root, e.g. if one side works in
# squared radius
for (na, va), (nb, vb) in itertools.permutations(NORMS.items(), 2):
    r = math.sqrt(va / vb)
    if 1.0 < r < 3.0:
        rows.append((r, "sqrt(%s" % na, "%s)" % nb))

rows.sort()
seen = set()
for r, na, nb in rows:
    key = round(r, 6)
    if key in seen:
        continue
    seen.add(key)
    tag = ""
    if CI_IN[0] <= r <= CI_IN[1]:
        tag = "  <== INSIDE inside-support CI"
        hits_in.append((r, na, nb))
    elif CI_ALL[0] <= r <= CI_ALL[1]:
        tag = "  <-- inside all-rings CI only"
        hits_all.append((r, na, nb))
    print("  %-22s / %-16s = %.4f%s" % (na, nb, r, tag))

print()
print("Named constants for comparison:")
for name, v in [
    ("sqrt(2)", math.sqrt(2)),
    ("aspect W/H", W / H),
    ("4/3", 4 / 3),
    ("pi/2", math.pi / 2),
    ("sqrt(H/W)+1", math.sqrt(H / W) + 1),
]:
    inside = CI_IN[0] <= v <= CI_IN[1]
    print("  %-14s %.4f   %s" % (name, v, "INSIDE inside-support CI" if inside else "outside"))

print()
print("=" * 66)
if hits_in:
    print("Convention ratios inside the inside-support CI:")
    for r, na, nb in hits_in:
        print("   %.4f  = %s / %s" % (r, na, nb))
else:
    print("NO simple convention ratio lands inside the inside-support CI")
    print("[%.4f, %.4f]." % CI_IN)
    print()
    print("The measured gain sits in the GAP between the two most natural")
    print("candidates: sqrt(2) = %.4f below it and the aspect ratio %.4f above." % (math.sqrt(2), W / H))
    print("Both are excluded by the same interval that excludes sqrt(2).")
    print()
    print("VERDICT: this WEAKENS ORCH's convention-bug lead. It does not kill it")
    print("- a convention error composed with any other factor is not on this")
    print("list, and the CI is statistical only, carrying no systematic term -")
    print("but ORCH should not have told M107 the arithmetic 'lands in this")
    print("neighbourhood' without running it.")
print("=" * 66)
