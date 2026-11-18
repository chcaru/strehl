"""R10 follow-up: make red's and blue's edge spread equal green's with a
per-channel, per-band gain measured from the stack's own edges.

  python -X utf8 edge-match.py OUT_PREFIX MASK_A.tif IMG_A.tif MASK_B.tif IMG_B.tif [--write]

Why: dark ground next to bright detail carries more red and blue than green
(rim-colour.py), at every radius: the channels' blurs differ in their wings,
which a diffraction-and-aperture model per channel does not describe.

Classes come from the MASK images (independent of the image they score:
use the other half-stack). Green smoothed at 1 px: bright above 50 % of the
99.5th percentile, dark below 12 %. Bins of distance from the bright/dark
boundary on both sides (dark pixels by distance to the nearest bright pixel,
bright pixels by distance to the nearest dark pixel), a far-dark class
(100 px and beyond) and a bright plateau (20 px and beyond inside bright).

Per channel c the edge spread is e_c(bin) = (mean_c(bin) - D_c) / (B_c - D_c),
D and B the far-dark and plateau means: a shape, free of the edge's colour.
Basis: the channel's own bands b_j = G(c, s_j) - G(c, 2 s_j), s = 1, 2, 4,
8, 16 px. A corrected channel c' = c + sum_j a_j b_j has
e'_c = e_c + sum_j a_j mean(b_j, bin) / (B_c - D_c), linear in a. The gains
are the ridge least-squares solution of e'_c = e_green over all bins, fitted
on image A and scored on image B (other half-stack: independent noise,
classes from the opposite half).

Reported: gains 1 + a_j per band; the rim (dark side, percentage points of
the bright level above green) before and after, on A and on B; the same on
the bright side; the noise cost (variance of the half-stack difference in
each band, after over before).

Placebo: gains fitted to make red match green applied to blue, and the
reverse, must not remove the other channel's rim equally well (if they do,
the fit is only a generic sharpening).

Fooled by: edges whose two sides differ in colour in a way that varies with
distance (translucent scale rims); a subject whose bright and dark classes
are not the same materials everywhere.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch
from scipy.ndimage import distance_transform_edt, gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp

SIGMAS = [1.0, 2.0, 4.0, 8.0, 16.0]
DARK_EDGES = [2.5, 3.5, 5, 7, 10, 15, 30, 100]
BRIGHT_EDGES = [2.5, 3.5, 5, 7, 10, 15, 20]
RIDGE = 1e-4


def classes(mask_path):
    g = gaussian_filter(tifffile.imread(mask_path)[..., 1].astype(np.float32), 1.0)
    top = np.percentile(g, 99.5)
    dark, bright = g < 0.12 * top, g > 0.50 * top
    dd = distance_transform_edt(~bright)
    db = distance_transform_edt(~dark)
    lab = np.zeros(g.shape, np.int8)                 # 0 unused
    names = []
    k = 1
    for lo, hi in zip(DARK_EDGES[:-1], DARK_EDGES[1:]):
        lab[dark & (dd >= lo) & (dd < hi)] = k
        names.append(f'dark {lo:g}-{hi:g}')
        k += 1
    for lo, hi in zip(BRIGHT_EDGES[:-1], BRIGHT_EDGES[1:]):
        lab[bright & (db >= lo) & (db < hi)] = k
        names.append(f'bright {lo:g}-{hi:g}')
        k += 1
    lab[dark & (dd >= 100)] = k
    lab[bright & (db >= 20)] = k + 1
    return torch.from_numpy(lab).to(fp.DEV), names, k, k + 1


def bands(x):
    out, prev = [], fp.gauss(x, SIGMAS[0])
    for s in SIGMAS:
        nxt = fp.gauss(x, 2 * s)
        out.append(prev - nxt)
        prev = nxt
    return out


def class_means(x, lab, n):
    flat, l = x.flatten().double(), lab.flatten().long()
    s = torch.zeros(n + 1, dtype=torch.float64, device=x.device).scatter_add_(0, l, flat)
    c = torch.zeros(n + 1, dtype=torch.float64, device=x.device).scatter_add_(0, l, torch.ones_like(flat))
    return (s / c.clamp(min=1)).cpu().numpy()


def measure(img, lab, nbins, kd, kb):
    """Per channel: class means of the channel and of each of its bands."""
    res = []
    for c in range(3):
        m0 = class_means(img[c], lab, kb)
        mb = [class_means(b, lab, kb) for b in bands(img[c])]
        res.append((m0, np.array(mb)))
    return res


def esf(m0, mb, a, nbins, kd, kb):
    v = m0 + (a[:, None] * mb).sum(0)
    return (v[1:nbins + 1] - v[kd]) / (v[kb] - v[kd])


def main():
    prefix, mask_a, img_a, mask_b, img_b = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
    dev = fp.DEV

    def load(f):
        return torch.from_numpy(tifffile.imread(f).astype(np.float32)).to(dev).permute(2, 0, 1)

    A, B = load(img_a), load(img_b)
    lab_a, names, kd, kb = classes(mask_a)
    lab_b, _, _, _ = classes(mask_b)
    nb = len(names)
    MA, MB = measure(A, lab_a, nb, kd, kb), measure(B, lab_b, nb, kd, kb)
    zero = np.zeros(len(SIGMAS))
    eg_a, eg_b = esf(*MA[1], zero, nb, kd, kb), esf(*MB[1], zero, nb, kd, kb)
    report = {'bins': names, 'sigmas': SIGMAS, 'green_esf': {'A': eg_a.tolist(), 'B': eg_b.tolist()}, 'channels': {}}
    gains = {}
    for c, name in ((0, 'R'), (2, 'B')):
        m0, mb = MA[c]
        e0 = esf(m0, mb, zero, nb, kd, kb)
        J = (mb[:, 1:nb + 1] - mb[:, kd:kd + 1]).T / (m0[kb] - m0[kd])        # [bins, bands]
        a = np.linalg.solve(J.T @ J + RIDGE * np.eye(len(SIGMAS)), J.T @ (eg_a - e0))
        gains[c] = a
    ndark = len(DARK_EDGES) - 1
    for c, name in ((0, 'R'), (2, 'B')):
        rows = {}
        other = gains[2 if c == 0 else 0]
        for arm, a in (('as is', zero), ('matched', gains[c]), ('placebo (other channel\'s gains)', other)):
            ea, eb = esf(*MA[c], a, nb, kd, kb), esf(*MB[c], a, nb, kd, kb)
            rows[arm] = {'A_minus_green_pp': (100 * (ea - eg_a)).tolist(), 'B_minus_green_pp': (100 * (eb - eg_b)).tolist()}
            print(f'{name} {arm:32s} fit image, dark side ' + ' '.join(f'{100 * v:+6.2f}' for v in (ea - eg_a)[:ndark])
                  + ' | bright side ' + ' '.join(f'{100 * v:+6.2f}' for v in (ea - eg_a)[ndark:]))
            print(f'{"":34s} other half, dark side ' + ' '.join(f'{100 * v:+6.2f}' for v in (eb - eg_b)[:ndark])
                  + ' | bright side ' + ' '.join(f'{100 * v:+6.2f}' for v in (eb - eg_b)[ndark:]))
        # noise cost per band from the half-stack difference (A and B are the two halves)
        d = bands(A[c] - B[c])
        cost = []
        full = A[c] - B[c]
        corr = full + sum(float(gains[c][j]) * d[j] for j in range(len(SIGMAS)))
        hp = lambda x: x - fp.gauss(x, 4.0)
        cost_total = float((hp(corr) ** 2).mean() / (hp(full) ** 2).mean())
        for j in range(len(SIGMAS)):
            cost.append(float((1 + gains[c][j]) ** 2))
        rows['gains'] = (1 + gains[c]).tolist()
        rows['noise_power_ratio_below_4px'] = cost_total
        report['channels'][name] = rows
        print(f'{name} gains by band (sigma {", ".join(f"{s:g}-{2 * s:g}" for s in SIGMAS)} px): ' + ' '.join(f'{1 + v:.3f}' for v in gains[c])
              + f'; noise power of the half-stack difference under 4 px: x{cost_total:.3f}')
    print('bins: ' + ', '.join(names))
    print('green edge spread (fit image): ' + ' '.join(f'{100 * v:.2f}' for v in eg_a))
    Path(prefix + '.json').write_text(json.dumps(report, indent=1) + '\n')
    if '--write' in sys.argv:
        for tag, img in (('a', A), ('b', B)):
            res = img.clone()
            for c in (0, 2):
                for j, b in enumerate(bands(img[c])):
                    res[c] += float(gains[c][j]) * b
            tifffile.imwrite(f'{prefix}-{tag}.tif', res.clamp(0, 65535).round().permute(1, 2, 0).cpu().numpy().astype(np.uint16))
            print('wrote', f'{prefix}-{tag}.tif')


if __name__ == '__main__':
    with torch.no_grad():
        main()
