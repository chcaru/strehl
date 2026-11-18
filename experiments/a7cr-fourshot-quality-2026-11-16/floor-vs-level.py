"""Q2: is the halves' shared floor beyond the diffraction cutoff a
multiplicative fixed pattern?

  python -X utf8 floor-vs-level.py OUT.json ODD.tif EVEN.tif WB_R,WB_G,WB_B

Per in-focus tile (cross-channel.py's selection) and channel: mean level,
and the cross-spectrum S and noise N summed over the frequency corners
|fx|, |fy| > 0.42 cycles/px (radial 0.59-0.71: beyond red's and green's
cutoffs, where the lens passes no scene detail). Tiles are sorted by level
into quartiles.

A response non-uniformity kappa leaves fixed-pattern power (kappa x level)^2
while shot noise power grows as level, so S/N there must grow in proportion
to the level; an additive pattern falls as 1/level; anything tied to scene
detail follows the tile's detail energy, not its level. Reported per
quartile: level (raw DN and electrons, from the given white balance, 16-bit
full scale = 14848 DN, 0.4040 DN/e-), corner S/N, and the kappa that would
explain it if every merged frame carried the same pattern,
kappa_eq = sqrt(S/N x noise_power) / level, with noise_power the measured N.

Control: the same S/N against the tile's green detail energy (correlation
printed): a floor that follows detail, not level, is not PRNU.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp
import evaluate as ev

T = ev.T
FULL_DN = 14848.0
GAIN = 0.4040


def main():
    out, fa, fb = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    wb = [float(v) for v in sys.argv[4].split(',')]
    dev = fp.DEV

    def load(f):
        return torch.from_numpy(tifffile.imread(f).astype(np.float32)).to(dev).permute(2, 0, 1)

    A, B = load(fa), load(fb)
    _, H, W = A.shape
    g = A[1]
    hpe = (g - fp.gauss(g, 2.0)) ** 2
    ty, tx = H // T, W // T
    e = hpe[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
    m = g[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
    fg = m > np.percentile(m, 15)
    sel = (e >= np.percentile(e[fg], 70)) & fg
    sel[:1], sel[-1:], sel[:, :1], sel[:, -1:] = False, False, False, False
    clip = (A.max(0).values > 60000) | (B.max(0).values > 60000)
    clipt = torch.nn.functional.avg_pool2d(clip.float()[None, None], T, T)[0, 0].cpu().numpy() > 0.01
    sel &= ~clipt[:ty, :tx]
    tiles = [(int(x), int(y)) for y, x in np.argwhere(sel)]
    win = ev.hann2(T, dev)
    norm = T * T * float((win * win).sum())
    fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[:, None]
    fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[None, :]
    corner = ((fx.abs() > 0.42) & (fy.abs() > 0.42)).double()
    nb = float(corner.sum())
    rows = []
    for x, y in tiles:
        a = A[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        b = B[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        lvl = 0.5 * (a.mean((1, 2)) + b.mean((1, 2)))
        a = a - a.mean((1, 2), keepdim=True)
        b = b - b.mean((1, 2), keepdim=True)
        FA, FB = torch.fft.fft2(a * win), torch.fft.fft2(b * win)
        _, _, (sx, sy) = ev.pair_spectra(a[1], b[1], win)
        FB = FB * torch.exp(2j * np.pi * (fx * sx + fy * sy))
        s = (FA * FB.conj()).real / norm
        n = (FA.abs() ** 2 + FB.abs() ** 2) / (2 * norm) - s
        rows.append([[float(lvl[c]), float((s[c] * corner).sum() / nb), float((n[c] * corner).sum() / nb)] for c in range(3)]
                    + [[float(e[y, x]), 0.0, 0.0]])
    R = np.array(rows)                      # [tiles, 4, 3]
    report = {'tiles': len(tiles), 'channels': {}}
    for c in range(3):
        lvl, S, N = R[:, c, 0], R[:, c, 1], R[:, c, 2]
        order = np.argsort(lvl)
        qs = np.array_split(order, 4)
        raw_dn = lvl / 65535.0 * FULL_DN / wb[c]
        line = []
        rec = []
        for q in qs:
            sn = S[q].sum() / N[q].sum()
            dn = raw_dn[q].mean()
            # S is power per frequency bin, normalised so that the sum over
            # all T x T bins is a variance per pixel: a white pattern of
            # variance v reads v / T^2 in every bin.
            kappa = np.sqrt(max(S[q].mean(), 0) * T * T) / lvl[q].mean()
            line.append(f'{dn:.0f} DN ({dn / GAIN:.0f} e-): S/N {sn:+.3f}, pattern {100 * kappa:.3f} % of level')
            rec.append({'raw_dn': float(dn), 'corner_sn': float(sn), 'pattern_pct_of_level': float(100 * kappa)})
        sn_t = S / N
        report['channels']['RGB'[c]] = {'quartiles': rec,
                                        'corr_sn_level': float(np.corrcoef(sn_t, lvl)[0, 1]),
                                        'corr_sn_detail': float(np.corrcoef(sn_t, R[:, 3, 0])[0, 1]),
                                        'corr_S_level2': float(np.corrcoef(S, lvl ** 2)[0, 1])}
        print(f'{"RGB"[c]}: ' + ';  '.join(line))
        print(f'    per-tile corner S/N against level r = {np.corrcoef(sn_t, lvl)[0, 1]:+.2f}, against green detail energy r = '
              f'{np.corrcoef(sn_t, R[:, 3, 0])[0, 1]:+.2f}; S against level^2 r = {np.corrcoef(S, lvl ** 2)[0, 1]:+.2f}; '
              f'log-log slope of S on level = {np.polyfit(np.log(lvl[S > 0]), np.log(S[S > 0]), 1)[0]:.2f}, of N on level = {np.polyfit(np.log(lvl), np.log(N), 1)[0]:.2f}')
    out.write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
