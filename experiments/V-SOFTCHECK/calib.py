"""Empirical white-noise gains.

softcheck._white_gain integrates the CONTINUOUS DoG transfer function.
scipy.ndimage.gaussian_filter convolves a SAMPLED, TRUNCATED kernel, and at
sigma=0.35 that is a poor approximation to the continuous one.  The self-test
caught it: predicted/measured is 1.076 at (0.7,1.4) and 2.638 at (0.35,0.7),
so the noise-subtraction constant C_NOISE was wrong by 2.45x.  Measure it.
"""
import numpy as np, softcheck as S
rng = np.random.default_rng(1)
def gain(s, reps=4, n=2048):
    v = []
    for r in range(reps):
        x = rng.standard_normal((n, n)).astype(np.float32)
        v.append(float((S.dog(x, s)**2).mean()))
    return float(np.mean(v)), float(np.std(v))
for tag, mid, hi in (("linear gauge", (0.7,1.4), (0.35,0.7)),
                     ("sRGB gauge  ", (1.4,2.8), (0.7,1.4))):
    gm, sm = gain(mid); gh, sh = gain(hi)
    ana = S._white_gain(*mid)/S._white_gain(*hi)
    print(f"{tag}: G_mid={gm:.6f}+-{sm:.1e}  G_hi={gh:.6f}+-{sh:.1e}  "
          f"C_NOISE measured={gm/gh:.6f}  analytic={ana:.6f}  ratio={gm/gh/ana:.4f}")
