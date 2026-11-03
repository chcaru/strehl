"""Per-channel focus curves: for each frame, high-pass energy of the R, G, B
CFA planes in a grid of tiles. Prints per-tile argmax frame per channel and the
sub-frame peak (parabolic) offsets R-G and B-G."""
import sys, glob, numpy as np, rawpy
from scipy.ndimage import uniform_filter
d = sys.argv[1]; step = int(sys.argv[2]) if len(sys.argv) > 2 else 1
files = sorted(glob.glob(d + '/*.ARW'))[::step]
T = 8  # tiles per side
E = []
for f in files:
    with rawpy.imread(f) as r:
        raw = r.raw_image_visible.astype(np.float32).copy()
        pat = r.raw_pattern.copy(); black = np.mean(r.black_level_per_channel)
    raw -= black
    planes = {}
    for (i, j) in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        c = pat[i, j]
        planes.setdefault(c, []).append(raw[i::2, j::2])
    ch = {'R': planes[0][0], 'G': planes[1][0], 'B': planes[2][0]}
    row = {}
    for k, p in ch.items():
        # band-pass: difference of box blurs (fine detail ~2-6 px in plane units)
        hp = uniform_filter(p, 3) - uniform_filter(p, 9)
        e = hp * hp / (uniform_filter(p, 9) ** 2 + 1e2)   # contrast-normalised
        H, W = e.shape; h, w = H // T, W // T
        row[k] = e[:h*T, :w*T].reshape(T, h, T, w).mean((1, 3))
    E.append(row)
    print('.', end='', flush=True)
print()
n = len(E)
def peak(curve):
    i = int(np.argmax(curve))
    if 0 < i < len(curve) - 1:
        a, b, c = curve[i-1], curve[i], curve[i+1]
        den = a - 2*b + c
        return i + (0.5 * (a - c) / den if den != 0 else 0)
    return float(i)
offs = {'R': [], 'B': []}; loss = {'R': [], 'B': []}
for ty in range(T):
    for tx in range(T):
        cur = {k: np.array([E[f][k][ty, tx] for f in range(n)]) for k in 'RGB'}
        g = cur['G']
        if g.max() < 3 * np.median(g):  # tile has no clear focus peak
            continue
        pg = peak(g); ig = int(np.argmax(g))
        for k in 'RB':
            offs[k].append((peak(cur[k]) - pg) * step)
            loss[k].append(cur[k][ig] / cur[k].max())
for k in 'RB':
    a = np.array(offs[k])
    print(k, '- G peak offset (frames): n', len(a), 'median %.2f' % np.median(a), 'p25 %.2f p75 %.2f' % tuple(np.percentile(a, [25, 75])))
for k in 'RB':
    a = np.array(loss[k])
    print(k, 'energy at G-best frame / own best: median %.3f p25 %.3f' % (np.median(a), np.percentile(a, 25)))
