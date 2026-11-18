"""Q2: is there a sensor-fixed pattern in gathered four-shot frames, and how
strong?

  python -X utf8 fpn-pairs.py OUT.json BASE.tif OTHER.tif [OTHER.tif ...] [--rate R_PER_FRAME --frames K0,K1,...] [--band LO,HI --flat]

Each input is ONE frame of the stack rendered alone
(`STREHL_FRAME_PARITY=K-K`, raw carry, no restoration): the frame gathered
onto the output grid. Scene content sits at the same output position in
every frame (that is what alignment does); a pattern fixed to the sensor
does not: between frames k and j it is displaced by the difference of their
transforms, delta(p) = a (p - c) + t, a radial field whose rate a is the
frames' relative magnification change.

Instrument, first form: the frequency corners |fx|, |fy| > 0.40 cycles/px,
where the lens passes no scene detail (beyond red's and green's diffraction
cutoff). That form found nothing, for a reason worth keeping: a four-shot
assembly reads each photosite once per member, so a photosite's response
error lands on a 2 x 2 block of output pixels and the pattern's spectrum is
cos^2(pi fx) cos^2(pi fy): gone at Nyquist. Second form (--band LO,HI
--flat): a radial band where that spectrum is strong, on the smoothest
bright tiles (defocused in both frames, so the band holds no scene detail;
what scene remains is fixed to the output and reads at a = 0, t = 0). Per
256 px tile, the band's cross-correlation of the two
frames on a +-3 px grid of 0.1 px; then for every (a, tx, ty) the tiles'
correlations read at their predicted displacement and summed, normalised by
the tiles' corner-band auto-power:

  C(a, t) = sum_tiles r_tile(a (p - c) + t) / sum_tiles sqrt(P_base P_other)

Reported per pair and channel: C at a = 0, t = 0 (pattern fixed to the
scene/output), the best (a, t) and C there, and C at the best t with a
forced to zero. A sensor pattern shows a peak at a = (magnification step per
frame) x (frame distance); with --rate and --frames that prediction is
printed beside the measured rate.

C at the peak is the fixed pattern's share of the corner-band power of one
gathered frame (pattern / (pattern + noise)).

Fooled by: scene detail in the corners (none passes the lens); the
correlation's own +-1 px sidelobes (the band is near Nyquist, so r changes
sign at odd shifts; the reported peak is the largest positive C).
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp

T = 256
GRID = 3.0
STEP = 0.1


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    rate = float(sys.argv[sys.argv.index('--rate') + 1]) if '--rate' in sys.argv else None
    band = [float(v) for v in sys.argv[sys.argv.index('--band') + 1].split(',')] if '--band' in sys.argv else None
    flat = '--flat' in sys.argv
    frames = [int(v) for v in sys.argv[sys.argv.index('--frames') + 1].split(',')] if '--frames' in sys.argv else None
    for flag in ('--rate', '--frames', '--band'):
        if flag in sys.argv:
            args.remove(sys.argv[sys.argv.index(flag) + 1])
    out, base, others = Path(args[0]), args[1], args[2:]
    dev = fp.DEV

    def load(f):
        return torch.from_numpy(tifffile.imread(f).astype(np.float32)).to(dev).permute(2, 0, 1)

    A = load(base)
    _, H, W = A.shape
    ty, tx = H // T, W // T
    lvl = A[1][:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
    keep = lvl > np.percentile(lvl, 40)
    if flat:
        g = A[1]
        hp = ((g - fp.gauss(g, 2.0)) ** 2)[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy() / np.maximum(lvl, 1.0)
        keep &= hp <= np.percentile(hp[keep], 35)
    keep[:1], keep[-1:], keep[:, :1], keep[:, -1:] = False, False, False, False
    tiles = [(int(x), int(y)) for y, x in np.argwhere(keep)]
    w1 = torch.hann_window(T, periodic=True, device=dev, dtype=torch.float64)
    win = w1[:, None] * w1[None, :]
    f1 = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)
    mask = ((f1.abs()[:, None] > 0.40) & (f1.abs()[None, :] > 0.40)).double()
    if band:
        fr = torch.sqrt(f1[:, None] ** 2 + f1[None, :] ** 2)
        mask = ((fr >= band[0]) & (fr < band[1])).double()
    d = torch.arange(-GRID, GRID + STEP / 2, STEP, device=dev, dtype=torch.float64)
    E = torch.exp(-2j * np.pi * d[:, None] * f1[None, :])              # [D, T]
    nd = len(d)
    cx, cy = (W - 1) / 2, (H - 1) / 2
    pos = torch.tensor([[x * T + T / 2 - cx, y * T + T / 2 - cy] for x, y in tiles], dtype=torch.float64, device=dev)

    def ffts(img):
        res = []
        for x, y in tiles:
            a = img[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
            a = a - a.mean((1, 2), keepdim=True)
            res.append(torch.fft.fft2(a * win) * mask)
        return torch.stack(res)                                          # [tiles, 3, T, T]

    FA = ffts(A)
    PA = (FA.abs() ** 2).sum((2, 3))
    report = {'tiles': len(tiles), 'pairs': [], 'band': band, 'flat': flat,
              'mean_level_16bit': [float(v) for v in torch.stack([A[:, y * T:(y + 1) * T, x * T:(x + 1) * T].mean((1, 2)) for x, y in tiles]).mean(0)]}
    print(f'tiles {len(tiles)}, band {band or "corners"}, mean level R/G/B ' + ' / '.join(f'{v:.0f}' for v in report['mean_level_16bit']))
    a_grid = torch.arange(-0.0045, 0.0045 + 1e-9, 2e-5, device=dev, dtype=torch.float64)
    t_grid = torch.arange(-1.2, 1.2 + 1e-9, 0.1, device=dev, dtype=torch.float64)
    for oi, other in enumerate(others):
        FB = ffts(load(other))
        PB = (FB.abs() ** 2).sum((2, 3))
        X = FA * FB.conj()                                               # [tiles, 3, T, T]
        # r[tile, c, dy, dx] = sum_f X(fy, fx) exp(-2 pi i (fx dx + fy dy))
        r = torch.einsum('yf,tcfg,xg->tcyx', E, X, E).real
        den = torch.sqrt(PA * PB).sum(0)                                 # [3]
        line = {'other': other, 'channels': {}}
        for c in range(3):
            rc = r[:, c]                                                 # [tiles, D, D]
            best = (-1e9, 0.0, 0.0, 0.0)
            zero_a = (-1e9, 0.0, 0.0)
            curve = []
            for a in a_grid:
                # displacement per tile for every t: index into the grid
                dx = a * pos[:, 0][:, None, None] + t_grid[None, :, None]            # [tiles, tx, 1]
                dy = a * pos[:, 1][:, None, None] + t_grid[None, None, :]            # [tiles, 1, ty]
                ix = ((dx + GRID) / STEP).round().long().clamp(0, nd - 1).expand(-1, len(t_grid), len(t_grid))
                iy = ((dy + GRID) / STEP).round().long().clamp(0, nd - 1).expand(-1, len(t_grid), len(t_grid))
                inside = ((dx.abs() <= GRID) & (dy.abs() <= GRID)).expand(-1, len(t_grid), len(t_grid))
                ti = torch.arange(len(tiles), device=dev)[:, None, None].expand_as(ix)
                vals = torch.where(inside, rc[ti, iy, ix], torch.zeros((), dtype=torch.float64, device=dev))
                Cm = vals.sum(0) / den[c]                                              # [tx, ty]
                k = int(Cm.argmax())
                v = float(Cm.flatten()[k])
                curve.append(v)
                if v > best[0]:
                    best = (v, float(a), float(t_grid[k // len(t_grid)]), float(t_grid[k % len(t_grid)]))
                if abs(float(a)) < 1e-9:
                    zero_a = (v, float(t_grid[k // len(t_grid)]), float(t_grid[k % len(t_grid)]))
                    c00 = float(Cm[len(t_grid) // 2, len(t_grid) // 2])
            line['channels']['RGB'[c]] = {'C_scene_locked': c00, 'best': best, 'best_at_zero_rate': zero_a, 'curve': curve}
        line['a_grid'] = a_grid.cpu().numpy().tolist()
        report['pairs'].append(line)
        pred = ''
        if rate is not None and frames is not None:
            pred = f'   predicted rate {rate * (frames[oi + 1] - frames[0]) * 1e6:+.0f} ppm'
        print(Path(other).name + pred)
        for c in range(3):
            ch = line['channels']['RGB'[c]]
            b = ch['best']
            print(f'   {"RGB"[c]}: fixed to output C = {ch["C_scene_locked"]:+.4f};  best C = {b[0]:+.4f} at rate {b[1] * 1e6:+.0f} ppm, t = ({b[2]:+.1f}, {b[3]:+.1f}) px;  '
                  f'best with rate 0: {ch["best_at_zero_rate"][0]:+.4f}')
        del FB, X, r
    out.write_text(json.dumps(report) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
