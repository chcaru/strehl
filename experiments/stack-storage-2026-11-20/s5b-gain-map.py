"""S5(a): a per-photosite gain map learned from the stack's own frames (the fixed pattern a
spatial coder cannot see), for the estimator's gain-map variant.

  python s5b-gain-map.py OUT.npy [N_FRAMES]

From N frames spread through the scarab stack (never planes 100-102, which S5 codes), per
site plane: r = S / gauss(S, 2 plane px) - 1 with S the signal above black; weights are the
inverse of r's noise variance by the product's model, zero where S < 200 DN or where the
local mean square of r exceeds 1.5 x that noise (scene detail in focus). The map is the
weighted mean, shrunk towards zero by kappa^2 / (kappa^2 + its own noise variance) with the
body's measured kappa (0.30 / 0.35 / 0.35 / 0.40 %). Saved as float16 (R, G1, G2, B planes
of the active area), the layout of the 2026-11-16 calibration map it is compared with.
"""
import sys

import cv2
import numpy as np

import common as c

c.below_normal()
cv2.setNumThreads(4)
out = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 64
BLACK, GAIN, READ = 512.0, 0.4040, 1.334
KAPPA = (0.0030, 0.0035, 0.0035, 0.0040)
x0, y0, cw, ch = 32, 20, 9504, 6336
planes = [p for p in np.linspace(2, 195, n).round().astype(int) if p not in (99, 100, 101, 102, 103)]
num = np.zeros((4, ch // 2, cw // 2), dtype=np.float64)
den = np.zeros((4, ch // 2, cw // 2), dtype=np.float64)
for i, p in enumerate(planes):
    frame = 4 * (int(p) - 1) + 1 + (i % 4)
    cfa = c.cfa_of(c.SCARAB, frame)[y0:y0 + ch, x0:x0 + cw].astype(np.float32) - BLACK
    c.drop(c.SCARAB, frame)
    for s, (dy, dx) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))):
        S = cfa[dy::2, dx::2]
        sm = cv2.GaussianBlur(S, (0, 0), 2.0, borderType=cv2.BORDER_REFLECT)
        ok = sm > 200
        smc = np.maximum(sm, 1.0)
        r = S / smc - 1.0
        nv = (GAIN * smc + READ * READ) / (smc * smc)
        local = cv2.blur(r * r, (9, 9), borderType=cv2.BORDER_REFLECT)
        ok &= local < 1.5 * nv
        w = np.where(ok, 1.0 / nv, 0.0)
        num[s] += w * r
        den[s] += w
    if (i + 1) % 8 == 0:
        print('frames', i + 1, 'of', len(planes), flush=True)
m = np.zeros_like(num, dtype=np.float32)
for s in range(4):
    g = num[s] / np.maximum(den[s], 1e-9)
    nvar = 1.0 / np.maximum(den[s], 1e-9)
    shrink = KAPPA[s] ** 2 / (KAPPA[s] ** 2 + nvar)
    shrink[den[s] <= 0] = 0
    covered = den[s] > 0
    print('site %d: raw map sd %.4f %%, its noise sd (median) %.4f %%, shrink factor median %.3f, covered %.1f %% of photosites, shrunk map sd %.4f %%'
          % (s, 100 * g[covered].std(), 100 * np.sqrt(np.median(nvar[covered])), np.median(shrink[covered]), 100 * covered.mean(), 100 * (g * shrink)[covered].std()))
    m[s] = (g * shrink).astype(np.float32)
np.save(out, m.astype(np.float16))
ref = np.load(str(c.ROOT / 'outputs/a7cr-fourshot-quality/q2-prnu-map.npy'), mmap_mode='r')
for s in range(4):
    a = m[s][200:-200:3, 200:-200:3].ravel()
    b = np.asarray(ref[s][200:-200:3, 200:-200:3], dtype=np.float32).ravel()
    print('site %d: correlation with the 2026-11-16 calibration-burst map (other scene, other day) %.3f' % (s, np.corrcoef(a, b)[0, 1]))
# storage: entropy of the map quantised to steps of 0.05 %, 0.1 %, 0.2 %
for step in (0.0005, 0.001, 0.002):
    bits = 0.0
    for s in range(4):
        q = np.rint(m[s] / step).astype(np.int64).ravel()
        q -= q.min()
        h = np.bincount(q)
        h = h[h > 0] / q.size
        bits += float(-(h * np.log2(h)).sum()) * q.size
    print('map quantised to %.2f %% steps: %.1f MB (static entropy)' % (100 * step, bits / 8e6))
