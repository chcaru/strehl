"""Automatic subject mask from through-focus evidence (brief Q9, Q10).

Input: the per-plane summaries of extract-planes.py (1/8-scale maps). The mask asks one
question of every block: did anything here come into focus inside the planned range, or does
it differ from the backdrop? Steps:

1. Noise floor of the fine focus energy against level (lower envelope over all planes), so
   energy is in units of what sensor noise alone would give.
2. Planes registered by one magnification rate about the frame centre (focus breathing),
   estimated from the thumbnails themselves.
3. Focus evidence = the largest noise-normalised energy over the planes used (after a
   3-plane mean along focus). Backdrop evidence = how far the block's through-focus mean
   level sits from the backdrop's (the border-connected, never-in-focus region).
4. Mask = evidence above the sensitivity, cleaned (close, fill, small parts dropped), grown by
   the buffer. Outline traced to polygons.

  python subject-mask.py <planes dir> <out prefix> [--every K] [--sensitivity S] [--buffer B]
"""
import argparse
import json
import pathlib

import numpy as np
from scipy import ndimage

ap = argparse.ArgumentParser()
ap.add_argument('planes')
ap.add_argument('out')
ap.add_argument('--every', type=int, default=1, help='use every K-th plane (a sparse survey)')
ap.add_argument('--sensitivity', type=float, default=3.0, help='how far above the quiet backdrop evidence must stand (2 x this many lower-side spreads)')
ap.add_argument('--buffer', type=int, default=2, help='grow the mask by this many blocks (8 sensor px each)')
ap.add_argument('--no-register', action='store_true')
ap.add_argument('--grow', type=float, default=0.0, help='hysteresis: also take evidence this many spreads above the quiet mode where it touches the sure subject (0 = off)')
a = ap.parse_args()
d = pathlib.Path(a.planes)
planes = json.loads((d / 'planes.json').read_text())[::a.every]
fine = np.stack([np.load(d / ('plane-%04d.npz' % p['ordinal']))['fine'] for p in planes]).astype(np.float32)
mean = np.stack([np.load(d / ('plane-%04d.npz' % p['ordinal']))['mean_G'].astype(np.float32) for p in planes])
n, h, w = fine.shape
print('planes', n, 'grid', h, 'x', w)

# 1. noise floor: 5th percentile of energy in log-spaced level bins, pooled over planes, fitted
# as a line and raised to the median by the ratio measured where nothing is ever in focus
lv = mean.ravel()[::7]
en = fine.ravel()[::7]
edges = np.concatenate([[-1.0], np.geomspace(5e-4, max(float(lv.max()), 1e-3), 22)])
xs, ys, ratio = [], [], None
for lo, hi in zip(edges[:-1], edges[1:]):
    m = (lv >= lo) & (lv < hi)
    if m.sum() > 500:
        xs.append(max(lv[m].mean(), 0.0))
        ys.append(np.percentile(en[m], 5))
        if ratio is None:
            ratio = float(np.median(en[m]) / ys[-1])   # the darkest bin: backdrop, noise only
slope, offset = np.polyfit(xs, ys, 1, w=1 / np.array(ys))
offset = max(offset, ys[0] * 0.5)
floor = ratio * (slope * np.maximum(mean, 0) + offset)
print('noise floor: energy = %.3e * level + %.3e (median; lower envelope x %.2f, %d bins)' % (ratio * slope, ratio * offset, ratio, len(xs)))
z = fine / floor
z = np.stack([ndimage.uniform_filter(k, 3) for k in z])


# 2. registration: one magnification rate per plane about the centre
def rescale(img, s):
    cy, cx = (h - 1) / 2, (w - 1) / 2
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return ndimage.map_coordinates(img, [cy + (yy - cy) / s, cx + (xx - cx) / s], order=1, mode='nearest')


rate = 0.0
if not a.no_register and n >= 8:
    i, j = n // 4, 3 * n // 4
    ref = ndimage.gaussian_filter(mean[i], 3)
    mov = ndimage.gaussian_filter(mean[j], 3)
    best = None
    for s in np.linspace(0.96, 1.04, 81):
        c = np.corrcoef(ref[20:-20, 20:-20].ravel(), rescale(mov, s)[20:-20, 20:-20].ravel())[0, 1]
        if best is None or c > best[0]:
            best = (c, s)
    rate = np.log(best[1]) / (j - i)   # log scale per plane (of the planes used)
    print('registration: plane %d onto %d needs scale %.4f (corr %.4f): %.1f ppm per plane used' % (j, i, best[1], best[0], 1e6 * rate))
    mid = n // 2
    for k in range(n):
        s = float(np.exp(-rate * (k - mid)))
        if abs(s - 1) > 2e-4:
            z[k] = rescale(z[k], s)
            mean[k] = rescale(mean[k], s)

# 3. evidence
zs = ndimage.uniform_filter1d(z, 3, axis=0, mode='nearest') if n >= 3 else z
focus = zs.max(0)
depth = zs.argmax(0)
level = np.median(mean, 0)
# The largest of N noisy values is itself well above 1, by an amount that depends on the number
# of planes and on the sensor's dark statistics. So the threshold is set against the frame's own
# quiet population: the low mode of log evidence and its lower-side spread.
lf = np.log(np.maximum(focus, 1e-3))
low = lf[lf <= np.percentile(lf, 60)]
hist, edges_ = np.histogram(low, bins=120)
hist = ndimage.uniform_filter1d(hist.astype(np.float64), 5)
mode = 0.5 * (edges_[hist.argmax()] + edges_[hist.argmax() + 1])
spread = max(mode - np.percentile(lf[lf < mode], 16), 0.02)
if np.exp(mode) > 6.0:      # no quiet population: the subject fills the frame
    cut = a.sensitivity
    print('no quiet backdrop found (evidence mode %.1f x the noise floor); absolute threshold %.1f' % (np.exp(mode), cut))
else:
    cut = float(np.exp(mode + (2.0 * a.sensitivity) * spread))
    print('quiet population: evidence mode %.2f x the noise floor, lower spread %.3f (log); threshold %.2f' % (np.exp(mode), spread, cut))
quiet = focus < np.exp(mode + 3 * spread)
border = np.zeros((h, w), bool)
border[:6] = border[-6:] = True
border[:, :6] = border[:, -6:] = True
lab, _ = ndimage.label(quiet)
ids = np.unique(lab[border & quiet])
backdrop = np.isin(lab, ids[ids > 0])
if backdrop.sum() < 0.02 * h * w:
    backdrop = quiet
b_med = np.median(level[backdrop])
b_mad = 1.4826 * np.median(np.abs(level[backdrop] - b_med)) + 1e-6
differs = np.abs(level - b_med) / b_mad
print('backdrop: %.1f %% of the frame, level %.4f +- %.4f' % (100 * backdrop.mean(), b_med, b_mad))

# 4. mask
in_focus = focus >= cut
raw = in_focus | ((differs >= 12 * a.sensitivity) & (level > b_med + 0.002))
if a.grow:
    # hysteresis: weaker evidence counts where it touches the sure subject
    weak = (focus >= np.exp(mode + a.grow * spread)) | (differs >= 4 * a.grow)
    wl, _ = ndimage.label(weak | raw)
    raw = np.isin(wl, np.unique(wl[raw])) & (wl > 0)
m = ndimage.binary_closing(raw, iterations=3)
# enclosed backdrop stays out unless it is small
holes = ndimage.binary_fill_holes(m) & ~m
hl, hk = ndimage.label(holes)
if hk:
    hs = ndimage.sum(holes, hl, range(1, hk + 1))
    m |= np.isin(hl, [i + 1 for i, s in enumerate(hs) if s < 0.0005 * h * w])
m = ndimage.binary_opening(m, iterations=1)
lab, k = ndimage.label(m)
sizes = ndimage.sum(m, lab, range(1, k + 1))
keep = [i + 1 for i, s in enumerate(sizes) if s >= max(60, 0.002 * h * w)]
m = np.isin(lab, keep)
if a.buffer:
    m = ndimage.binary_dilation(m, iterations=a.buffer)
print('mask: %.2f %% of the frame in %d part(s); focus-only %.2f %%, backdrop-difference-only %.2f %%' % (
    100 * m.mean(), len(keep), 100 * (in_focus & m).mean(), 100 * (~in_focus & raw & m).mean()))

# planes at which the subject is in focus (the bounds a survey would suggest)
if m.any():
    dz = depth[m & in_focus]
    lo, hi = np.percentile(dz, [0.5, 99.5])
    print('subject in focus from plane %d to %d of the %d used (ordinals %d..%d)' % (lo, hi, n, planes[int(lo)]['ordinal'], planes[int(hi)]['ordinal']))


# outline -> polygons (Moore boundary of each part, then Douglas-Peucker)
def outline(part):
    pad = np.pad(part, 1)
    ys_, xs_ = np.nonzero(pad & ~ndimage.binary_erosion(pad))
    start = (ys_[0], xs_[0])
    nbrs = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    pts, cur, back = [start], start, 6
    for _ in range(4 * pad.size):
        for t in range(8):
            q = (back + 1 + t) % 8
            y, x = cur[0] + nbrs[q][0], cur[1] + nbrs[q][1]
            if pad[y, x]:
                back = (q + 4) % 8
                cur = (y, x)
                break
        else:
            break
        if cur == start:
            break
        pts.append(cur)
    return np.array(pts, np.float32) - 1


def simplify(p, eps):
    if len(p) < 3:
        return p
    a_, b_ = p[0], p[-1]
    ab = b_ - a_
    den = np.hypot(*ab) + 1e-9
    dist = np.abs(ab[0] * (p[:, 1] - a_[1]) - ab[1] * (p[:, 0] - a_[0])) / den
    i = int(dist.argmax())
    if dist[i] <= eps:
        return np.array([a_, b_])
    return np.vstack([simplify(p[:i + 1], eps)[:-1], simplify(p[i:], eps)])


polys = []
lab, k = ndimage.label(m)
for i in range(1, k + 1):
    o = outline(lab == i)
    half = len(o) // 2
    s = np.vstack([simplify(o[:half + 1], 1.5)[:-1], simplify(o[half:], 1.5)])
    polys.append([[round(float(x + 0.5) / w, 5), round(float(y + 0.5) / h, 5)] for y, x in s])
    print('part %d: outline %d points -> polygon %d points' % (i, len(o), len(s)))
out = pathlib.Path(a.out)
out.parent.mkdir(parents=True, exist_ok=True)
np.savez_compressed(str(out) + '.npz', mask=m, focus=focus.astype(np.float32), depth=depth.astype(np.int16), differs=differs.astype(np.float32), level=level)
pathlib.Path(str(out) + '.json').write_text(json.dumps({'grid': [w, h], 'planes_used': n, 'every': a.every, 'sensitivity': a.sensitivity,
                                                         'buffer': a.buffer, 'ppm_per_plane': 1e6 * rate, 'share': float(m.mean()), 'polygons': polys}))
try:
    from PIL import Image
    g = np.clip(np.sqrt(np.clip(level / max(np.percentile(level, 99.5), 1e-6), 0, 1)), 0, 1)
    rgb = np.stack([g, g, g], -1)
    edge = m & ~ndimage.binary_erosion(m, iterations=2)
    rgb[edge] = [1.0, 0.85, 0.1]
    rgb[~m] *= 0.45
    Image.fromarray((rgb * 255).astype(np.uint8)).save(str(out) + '.png')
    ev = np.clip(np.log10(np.maximum(focus, 1)) / 3, 0, 1)
    Image.fromarray((ev * 255).astype(np.uint8)).save(str(out) + '-evidence.png')
except ImportError:
    pass
