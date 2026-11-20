"""S2: raw value statistics of A7CR uncompressed frames.

Black level, used range, histogram occupancy (codes never used inside the used range, and
periodic combing), centre against corner (a position-dependent digital gain would give
position-dependent gaps), and the border outside the default crop.
"""
import numpy as np

import common as c

c.below_normal()
FRAMES = [(c.SCARAB, 1), (c.SCARAB, 400), (c.SCARAB, 780), (c.REPEAT_A, 1), (c.STACK107, 200)]
CROP = (32, 20, 9504, 6336)  # x, y, w, h from the ARW's default crop tags


def occupancy(v, label):
    h = np.bincount(v.ravel(), minlength=1 << 16)
    used = np.nonzero(h)[0]
    lo, hi = int(used[0]), int(used[-1])
    # the range holding 99.98 % of samples, to ignore sparse tails
    cs = np.cumsum(h)
    a = int(np.searchsorted(cs, 1e-4 * cs[-1]))
    b = int(np.searchsorted(cs, (1 - 1e-4) * cs[-1]))
    inner = h[a:b + 1]
    empty = int((inner == 0).sum())
    # combing: ratio of even-code to odd-code counts and the strongest short period
    even, odd = inner[(np.arange(a, b + 1) % 2) == 0].sum(), inner[(np.arange(a, b + 1) % 2) == 1].sum()
    lsb = [(int((v & ((1 << k) - 1) == 0).mean() * 1e6) / 1e4) for k in (1, 2, 3)]
    # roughness of the histogram: relative second difference against Poisson expectation
    hh = inner.astype(np.float64)
    core = hh[1:-1] > 400
    d2 = (hh[2:] - 2 * hh[1:-1] + hh[:-2])[core]
    exp = np.sqrt(6 * hh[1:-1][core])
    rough = float(np.sqrt(np.mean((d2 / exp) ** 2))) if core.any() else float('nan')
    print('   %-22s n=%9d min %5d max %5d  0.01-99.99 %% range [%5d, %5d] empty codes inside %5d of %5d  even/odd %.4f  %%(v mod 2,4,8 == 0) %s  hist roughness %.2f (1 = Poisson)'
          % (label, v.size, lo, hi, a, b, empty, b - a + 1, even / max(odd, 1), lsb, rough))
    return h


for run, frame in FRAMES:
    cfa = c.cfa_of(run, frame)
    h, w = cfa.shape
    x0, y0, cw, ch = CROP
    print('== %s frame %d  %d x %d' % (run, frame, w, h))
    occupancy(cfa, 'whole strip')
    act = cfa[y0:y0 + ch, x0:x0 + cw]
    for name, (dy, dx) in (('site (0,0)', (0, 0)), ('site (0,1)', (0, 1)), ('site (1,0)', (1, 0)), ('site (1,1)', (1, 1))):
        occupancy(act[dy::2, dx::2], 'active ' + name)
    occupancy(act[ch // 2 - 512:ch // 2 + 512, cw // 2 - 512:cw // 2 + 512], 'centre 1024^2')
    occupancy(act[:1024, :1024], 'top-left 1024^2')
    occupancy(act[-1024:, -1024:], 'bottom-right 1024^2')
    borders = {'left 32 cols': cfa[:, :x0], 'right %d cols' % (w - x0 - cw): cfa[:, x0 + cw:],
               'top 20 rows': cfa[:y0, :], 'bottom %d rows' % (h - y0 - ch): cfa[y0 + ch:, :]}
    for name, v in borders.items():
        v = v.astype(np.float64)
        print('   border %-16s n=%8d mean %8.2f sd %7.2f min %5d max %5d  distinct %d'
              % (name, v.size, v.mean(), v.std(), v.min(), v.max(), len(np.unique(v))))
    dark = act[act < np.percentile(act[::16, ::16], 0.5)]
    print('   darkest 0.5 %% of active: mean %.2f sd %.2f (black level is near the lowest mean seen)' % (dark.mean(), dark.std()))
    c.drop(run, frame) if (run, frame) not in ((c.SCARAB, 1), (c.SCARAB, 400), (c.REPEAT_A, 1)) else None
