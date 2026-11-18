"""Q3: does the four-tap gather leave a periodic pattern in the noise (and so
in the fine detail)?

  python -X utf8 phase-pattern.py OUT.json A.tif [B.tif] [--centre X,Y] [--size N]

Every frame is gathered at a sub-pixel phase that cycles across the output
(the coverage fit scales every frame, so the phase advances about 0.0173 px
per output px: a 57 px period, slightly different per frame). A four-tap
Catmull-Rom attenuates the finest detail and the noise most at phase 0.5 and
not at all at phase 0, so the local noise power should carry a grid with
that period.

Instrument: green; with two inputs the difference A - B (scene cancels to
first order), with one input the image itself on smooth pixels only. Fine
residual h = x - gauss(x, 1 px); v = h^2 / local level (shot noise is
proportional to level), block-averaged 2 x 2. In an N-px square about
--centre (default the frame centre, where every frame's phase field nearly
coincides) v is detrended (divided by its own 24-block Gaussian) and folded
along x and along y for every trial period 30-90 px; the first-harmonic modulation depth (peak to
peak over mean) is reported for the best period, with the median depth over
all trial periods as the instrument's floor.

Also printed: the closed-form noise power of the kernel by phase, for the
predicted depth: 1.0 at phase 0 and sum(w^2) = 0.641 at phase 0.5 per axis.
A one-axis fold averages the other axis, so the predicted one-axis depth is
(1 - 0.641) / mean = 0.44 for one gathered frame's white noise, less after
the high-pass and less still when frames with different phases are merged.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    centre = [int(v) for v in sys.argv[sys.argv.index('--centre') + 1].split(',')] if '--centre' in sys.argv else None
    size = int(sys.argv[sys.argv.index('--size') + 1]) if '--size' in sys.argv else 2048
    for flag in ('--centre', '--size'):
        if flag in sys.argv:
            args.remove(sys.argv[sys.argv.index(flag) + 1])
    out, files = Path(args[0]), args[1:]
    dev = fp.DEV
    imgs = [torch.from_numpy(tifffile.memmap(f)[..., 1].astype(np.float32)).to(dev) for f in files]
    H, W = imgs[0].shape
    cx, cy = centre or (W // 2, H // 2)
    x0, y0 = cx - size // 2, cy - size // 2
    crop = [im[y0:y0 + size, x0:x0 + size] for im in imgs]
    level = fp.gauss(crop[0], 8.0).clamp(min=50)
    if len(crop) == 2:
        d = crop[0] - crop[1]
        ok = torch.ones_like(d)
    else:
        d = crop[0]
        hp = (d - fp.gauss(d, 2.0)) ** 2
        local = fp.gauss(hp, 6.0) / level
        ok = (local < 1.3 * local.median()).float()
    h = d - fp.gauss(d, 1.0)
    v = h * h / level
    vb = F.avg_pool2d((v * ok)[None, None], 2)[0, 0]
    wb = F.avg_pool2d(ok[None, None], 2)[0, 0]
    trend = fp.gauss(vb, 24.0) / fp.gauss(wb, 24.0).clamp(min=1e-3)
    rel = torch.where(wb > 0.5, vb / wb.clamp(min=1e-3) / trend.clamp(min=1e-12), torch.ones_like(vb))
    wgt = (wb > 0.5).double()
    n = rel.shape[0]
    pos = torch.arange(n, device=dev, dtype=torch.float64) * 2 + 1.0       # block centres, px
    res = {'files': files, 'centre': [cx, cy], 'size': size, 'usable_fraction': float(wgt.mean()), 'axes': {}}
    periods = np.arange(30.0, 90.01, 0.25)
    for axis, name in ((1, 'x'), (0, 'y')):
        prof = (rel.double() * wgt).sum(1 - axis) / wgt.sum(1 - axis).clamp(min=1)      # mean over the other axis
        depths = []
        for P in periods:
            # first harmonic of the fold: amplitude of cos/sin at period P,
            # as a depth (peak to peak over mean); no bins, so no empty bins.
            ph = 2 * np.pi * pos / P
            m = prof.mean()
            a = ((prof - m) * torch.cos(ph)).mean() * 2
            b = ((prof - m) * torch.sin(ph)).mean() * 2
            depths.append(float(2 * torch.sqrt(a * a + b * b) / m))
        depths = np.array(depths)
        k = int(depths.argmax())
        res['axes'][name] = {'best_period_px': float(periods[k]), 'depth': float(depths[k]), 'floor_median_depth': float(np.median(depths)),
                             'depths': depths.tolist()}
        top = np.argsort(depths)[::-1][:4]
        print(f'{name}: best period {periods[k]:.2f} px, first-harmonic depth {depths[k]:.4f} (median over trial periods {np.median(depths):.4f}); '
              + 'top: ' + ', '.join(f'{periods[i]:.2f} px {depths[i]:.4f}' for i in top))
    res['periods'] = periods.tolist()
    # Local version: in a merge different regions come from frames of
    # different magnification, so the period differs from place to place
    # (45-81 px over this stack). Per 512 px tile the squared first-harmonic
    # depth by period, averaged over tiles; the excess of the 45-81 px range
    # over the periods outside it is the rms local modulation.
    tb = 256
    lp = np.arange(30.0, 120.01, 0.5)
    for axis, name in ((1, 'x'), (0, 'y')):
        acc = np.zeros(len(lp))
        cnt = 0
        for ty in range(0, n - tb + 1, tb):
            for tx in range(0, n - tb + 1, tb):
                r = rel[ty:ty + tb, tx:tx + tb].double()
                w = wgt[ty:ty + tb, tx:tx + tb]
                if float(w.mean()) < 0.6:
                    continue
                prof = (r * w).sum(1 - axis) / w.sum(1 - axis).clamp(min=1)
                q = pos[:tb]
                m = prof.mean()
                d2 = []
                for P in lp:
                    ph = 2 * np.pi * q / P
                    a = ((prof - m) * torch.cos(ph)).mean() * 2
                    b = ((prof - m) * torch.sin(ph)).mean() * 2
                    d2.append(float(4 * (a * a + b * b) / (m * m)))
                acc += np.array(d2)
                cnt += 1
        if cnt == 0:
            continue
        acc /= cnt
        inside = (lp >= 45) & (lp <= 81)
        floor = float(np.median(acc[~inside]))
        peak = float(acc[inside].max())
        res['axes'][name]['local'] = {'tiles': cnt, 'peak_depth2': peak, 'floor_depth2': floor, 'period_at_peak': float(lp[inside][acc[inside].argmax()])}
        print(f'{name} local ({cnt} tiles of 512 px): rms depth at best period {np.sqrt(peak):.4f} ({lp[inside][acc[inside].argmax()]:.1f} px), '
              f'outside 45-81 px {np.sqrt(floor):.4f}; excess {np.sqrt(max(peak - floor, 0)):.4f}')
    out.write_text(json.dumps(res) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
