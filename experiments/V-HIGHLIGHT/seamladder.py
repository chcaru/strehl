"""Commission the seam claim -- v2.

v1 was broken: it scored the GLOBAL max adjacent-bin jump, which a natural 60 DN
feature elsewhere dominated, so a 16 DN plant never became the maximum and the
ladder read a constant 60.00 and said "deaf".  That would have made me withdraw
a sound claim because my test of the test was wrong.  Score AT the plant, and
anchor so a plant that fails to apply raises.
"""
import numpy as np, tifffile

OFF = r"C:\dev\strehl-out\V-HIGHLIGHT\foam-lin-OFF.tiff"
DEF = r"C:\dev\strehl-out\V-HIGHLIGHT\foam-lin-DEF.tiff"
a = tifffile.imread(OFF).astype(np.float64)
b = tifffile.imread(DEF).astype(np.float64)
lvl = a.max(axis=2).ravel()
dr = (b - a).max(axis=2).ravel()

BIN, LO, HI = 100.0, 41000.0, 47000.0
edges = np.arange(LO, HI + BIN, BIN)
idx = np.digitize(lvl, edges) - 1
valid = (idx >= 0) & (idx < len(edges) - 1)
STEP_AT = 43000.0
kedge = int((STEP_AT - LO) / BIN)          # index of the bin starting at STEP_AT

def curve(delta):
    dd = dr + (delta * (lvl > STEP_AT) if delta else 0.0)
    out = np.full(len(edges) - 1, np.nan)
    for k in range(len(edges) - 1):
        m = valid & (idx == k)
        if m.sum() >= 200:
            out[k] = np.median(dd[m])
    return out

base = curve(0.0)
if not (np.isfinite(base[kedge]) and np.isfinite(base[kedge - 1])):
    raise SystemExit("ANCHOR FAILED: plant boundary bins are empty -- cannot score")

def jump_at(c):
    return abs(c[kedge] - c[kedge - 1])

nat = jump_at(base)
fin = np.isfinite(base)
alljumps = np.abs(np.diff(base[fin]))
others = np.sort(alljumps)[:-1]            # exclude the single largest feature
noise = np.percentile(others, 95)
print("foam, 16-bit via tifffile, %d populated bins of %d DN" % (fin.sum(), BIN))
print("natural jump AT the plant boundary (%d DN) : %.2f DN" % (STEP_AT, nat))
print("95th pct of other adjacent-bin jumps        : %.2f DN" % noise)
print("largest natural jump anywhere               : %.2f DN" % alljumps.max())
print()
print("  %8s %12s %12s %10s" % ("A (DN)", "jump@plant", "excess", "detected?"))
detected = None
for A in (0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0):
    c = curve(A)
    if np.allclose(c[fin], base[fin]):
        raise SystemExit("ANCHOR FAILED: plant of %.2f DN changed nothing" % A)
    j = jump_at(c)
    exc = j - nat
    hit = j > noise
    if hit and detected is None:
        detected = A
    print("  %8.2f %12.2f %12.2f %10s" % (A, j, exc, "YES" if hit else "no"))
print()
print("plant lands: excess tracks A one-for-one (%.2f DN per DN)"
      % ((jump_at(curve(16.0)) - nat) / 16.0))
if detected is not None:
    print()
    print("SMALLEST PLANTED SEAM DETECTED: %.2f DN" % detected)
    print("Correct form of the Phase 1 claim:")
    print("  'no seam at or above %.2f DN in the level-binned response on foam'" % detected)
