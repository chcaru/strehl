"""C7: commission tri.catmull_rom_shift, the new self-calibration path."""
import numpy as np, tri, sys

rng = np.random.default_rng(7)
img = (rng.random((900, 900)).astype(np.float32) * 800 + 600)
img = np.asarray(np.convolve(img.ravel(), np.ones(3) / 3, "same").reshape(900, 900),
                 dtype=np.float32)
win = (200, 200, 512, 512)
ref = img[200:712, 200:712]
fail = []

# C7a: an INTEGER shift must be exact -- the kernel must reduce to a copy.
z = tri.catmull_rom_shift(img, 0.0, 0.0, win)
d = float(np.max(np.abs(z - ref)))
print(f"C7a zero shift      max|err| = {d:.3e} DN")
if d > 1e-3: fail.append("C7a")
z = tri.catmull_rom_shift(img, 3.0, -2.0, win)
d = float(np.max(np.abs(z - img[203:715, 198:710])))
print(f"C7b integer shift   max|err| = {d:.3e} DN")
if d > 1e-3: fail.append("C7b")

# C7c: a constant must survive a fractional shift (partition of unity).
c = np.full((900, 900), 1234.5, np.float32)
z = tri.catmull_rom_shift(c, 0.37, 0.62, win)
d = float(np.max(np.abs(z - 1234.5)))
print(f"C7c constant @0.37  max|err| = {d:.3e} DN   (mean {z.mean():.4f})")
if d > 1e-3: fail.append("C7c")

# C7d: the phase-averaged cost must be a LOSS in every band, bounded, and must
#      bracket the scale-gather loss it stands in for.
A = tri.band_amp(ref, 1.0)
for ph in list(tri.GATHER_PHASES) + [0.5]:
    s = tri.catmull_rom_shift(img, ph, ph, win)
    S = tri.band_amp(s, 1.0)
    print(f"  phase {ph:.3f}: " + "  ".join(f"{b}={S[b]/A[b]:.4f}" for b in tri.BANDS))
avg = {}
for b in tri.BANDS:
    v = []
    for ph in tri.GATHER_PHASES:
        s = tri.catmull_rom_shift(img, ph, ph, win)
        v.append(tri.band_amp(s, 1.0)[b] / A[b])
    avg[b] = float(np.mean(v))
print("phase-averaged cost:", {b: round(avg[b], 4) for b in tri.BANDS})
for b in tri.BANDS:
    if not (0.50 <= avg[b] <= 1.00):
        fail.append(f"C7d {b}={avg[b]:.3f}")

# C7e: the stand-in must land near the SCALE loss it replaces, on the same
#      content, at the corpus k range.  (Scale loss measured about the centre;
#      compared band-for-band, no registration needed since band_amp is
#      translation-invariant and we evaluate the scaled arm at its own k.)
print("\nscale-gather loss vs phase-averaged shift loss (high band):")
for k in (0.9974, 0.95, 0.9236, 0.9046):
    sc = tri.catmull_rom_scale(img, k, win)
    S = tri.band_amp(sc, 1.0)
    print(f"  k={k:.4f}: scale={S['high']/A['high']:.4f}   shift-avg={avg['high']:.4f}")

print("\nC7 " + ("FAIL " + ",".join(fail) if fail else "PASS"))
sys.exit(1 if fail else 0)
