"""C8: commission the noise-subtracted band amplitude."""
import numpy as np, tri, os, sys
rng = np.random.default_rng(11)
fail = []
N = 512

def shaped_noise(sd, n=N):
    """White noise low-passed like a demosaic, so its PSD falls toward Nyquist."""
    w = rng.normal(0, 1, (n + 4, n + 4)).astype(np.float32)
    k = np.array([0.25, 0.5, 0.25], np.float32)
    w = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 0, w)
    w = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 1, w)
    w = w[2:2 + n, 2:2 + n]
    return (w / w.std() * sd).astype(np.float32)

# C8a: a pure-noise tile must yield ~ZERO signal in every band.
flat = 8000.0 + shaped_noise(40.0)
tmpl, tn = tri.noise_template(flat)
other = 8000.0 + shaped_noise(40.0)
S = tri.band_amp_sig(other, 1.0, tmpl, tn)
print(f"C8a pure noise -> signal  high={S['high']:.3f} DN "
      f"(total {S['high_tot']:.3f}, noise est {S['high_noise']:.3f})")
if S["high"] > 0.30 * S["high_tot"]: fail.append("C8a residual too large")

# C8b: noise level must not change the recovered SIGNAL.  Same detail, two very
#      different noise levels -- the whole point, since merge and frame differ
#      in noise by ~2x.
x = np.arange(N, dtype=np.float32)
detail = 300.0 * np.sin(2 * np.pi * 0.36 * x)[None, :] * np.ones((N, 1), np.float32)
rec = {}
for sd in (10.0, 40.0, 80.0, 160.0):
    t, tnn = tri.noise_template(8000.0 + shaped_noise(sd))
    S = tri.band_amp_sig(8000.0 + detail + shaped_noise(sd), 1.0, t, tnn)
    rec[sd] = S["high"]
    print(f"C8b noise sd={sd:6.1f} DN -> signal high={S['high']:8.3f} DN "
          f"(total {S['high_tot']:8.3f}, noise est {S['high_noise']:7.3f})")
v = np.array(list(rec.values()))
spread = float(v.max() / v.min() - 1.0)
print(f"C8b signal spread across a 16x noise range = {spread*100:.1f}%")
if spread > 0.15: fail.append(f"C8b spread {spread:.3f}")

# C8c: teeth.  Tested in the REGIME THAT MATTERS -- 119MSDCF DETAIL has merge
#      high-band 62.8 DN against a ~50 DN noise floor, i.e. signal ~= noise.
#      A strong-signal test would pass trivially and prove nothing.
weak = 40.0 * np.sin(2 * np.pi * 0.36 * x)[None, :] * np.ones((N, 1), np.float32)
raw = {sd: tri.band_amp(8000.0 + weak + shaped_noise(sd), 1.0)["high"]
       for sd in (10.0, 160.0)}
print(f"C8c uncorrected weak signal: sd=10 -> {raw[10.0]:.3f} DN, "
      f"sd=160 -> {raw[160.0]:.3f} DN "
      f"({raw[160.0]/raw[10.0]:.2f}x FALSE gain from noise alone)")
if raw[160.0] / raw[10.0] < 1.3: fail.append("C8c control has no teeth")
cor = {}
for sd in (10.0, 160.0):
    t2, tn2 = tri.noise_template(8000.0 + shaped_noise(sd))
    cor[sd] = tri.band_amp_sig(8000.0 + weak + shaped_noise(sd), 1.0, t2, tn2)["high"]
print(f"C8c   corrected weak signal: sd=10 -> {cor[10.0]:.3f} DN, "
      f"sd=160 -> {cor[160.0]:.3f} DN "
      f"({cor[160.0]/cor[10.0]:.2f}x residual, expect ~1.00)")
if not (0.75 <= cor[160.0] / cor[10.0] <= 1.35): fail.append("C8c weak-regime")

# C8d: the recovered amplitude must be RIGHT, not merely stable.  A sine of
#      amplitude a has band amplitude proportional to a; check linearity.
t, tnn = tri.noise_template(8000.0 + shaped_noise(40.0))
prev = None
for a in (75.0, 150.0, 300.0):
    d = a * np.sin(2 * np.pi * 0.36 * x)[None, :] * np.ones((N, 1), np.float32)
    s = tri.band_amp_sig(8000.0 + d + shaped_noise(40.0), 1.0, t, tnn)["high"]
    print(f"C8d amplitude {a:6.1f} DN -> signal {s:9.3f} DN"
          + (f"   ratio vs prev = {s/prev:.3f} (expect 2.000)" if prev else ""))
    if prev is not None and not (1.85 <= s / prev <= 2.15): fail.append(f"C8d a={a}")
    prev = s

print("\nC8 " + ("FAIL " + "; ".join(fail) if fail else "PASS"))
sys.exit(1 if fail else 0)
