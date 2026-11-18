"""R7 control: the scale dependence of the channel displacement, measured in
the raw frames themselves (no gather, no lateral-colour correction, no
resampling, no merge).

  python -X utf8 raw-channel-shift.py OUT.json MEMBER_CACHE [--planes 20,60,100,140,180] [--tile 256]

MEMBER_CACHE: a four-shot run exported by a7cr-export-members. Each listed
plane's four members are assembled at their integer offsets (fp.assemble:
every site then holds a measured red, green and blue sample; nothing is
interpolated). Red's, green's and blue's samples at a site come from
different exposures, so their noise is independent and the cross-spectrum
of two channels within one group is unbiased.

Per plane, in-focus tiles (top 30 % of green high-pass energy among tiles
above the 15th percentile of level, no clipping). Per tile, band and channel
(red, blue), the displacement against green (phase ramp of the
cross-spectrum, channel-register.py's estimator). Tiles of all planes are
pooled and an offset plus a radial scale is fitted per band.

If the product's render shows fine red detail +425 ppm from green after a
profile correction of -464.6 ppm, the raw frames must show it about -40 ppm
from green, and coarse content about -560 ppm (blue: +33 and +205). If the
raw frames show one scale at every band, the dependence was made by the
product's gather and the finding is a bug report, not optics.

Fooled by: member motion (0.05-0.1 px, random per group: adds scatter, not a
radial term); per-plane axial colour (red and blue are read at green's focus
here, as in the product).
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp
import evaluate as ev

BANDS = [(0.03, 0.08), (0.08, 0.14), (0.14, 0.24), (0.24, 0.42)]


def arg(name, default=None):
    for i, tok in enumerate(sys.argv):
        if tok == name:
            return sys.argv[i + 1]
    return default


def main():
    out, cache = Path(sys.argv[1]), sys.argv[2]
    T = int(arg('--tile', '256'))
    run = fp.Run(cache)
    planes = [int(v) for v in arg('--planes', ','.join(str(p) for p in run.planes[::max(1, len(run.planes) // 5)][:5])).split(',')]
    dev = fp.DEV
    win = ev.hann2(T, dev)
    fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[:, None]
    fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[None, :]
    fr = torch.sqrt(fx * fx + fy * fy)
    fits = [((fr >= lo) & (fr <= hi)).double() for lo, hi in BANDS]

    def shift_of(X, fit):
        r = torch.fft.ifft2(X * fit / (X.abs() + 1e-12 * X.abs().mean())).real
        idx = int(r.argmax())
        py, px = idx // T, idx % T
        s = torch.tensor([float(px - T if px > T / 2 else px), float(py - T if py > T / 2 else py)], dtype=torch.float64, device=dev)
        for _ in range(5):
            Y = X * torch.exp(2j * np.pi * (fx * s[0] + fy * s[1]))
            w = Y.abs() * fit
            ph = torch.angle(Y)
            a = torch.stack([(w * fx * fx).sum(), (w * fx * fy).sum(), (w * fy * fy).sum()])
            b = torch.stack([(w * fx * ph).sum(), (w * fy * ph).sum()])
            det = a[0] * a[2] - a[1] * a[1]
            s = s + torch.stack([-(a[2] * b[0] - a[1] * b[1]) / det, -(a[0] * b[1] - a[1] * b[0]) / det]) / (2 * np.pi)
        return s.cpu().numpy()

    pos, S = [], {(c, b): [] for c in (0, 2) for b in range(len(BANDS))}
    for p in planes:
        m = run.meta[p]
        rgb, _, _ = fp.assemble(run.members(p), m['offsets'], m['gains'], run.P)
        _, H, W = rgb.shape
        g = rgb[1]
        hpe = (g - fp.gauss(g, 2.0)) ** 2
        ty, tx = H // T, W // T
        e = hpe[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
        lv = g[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
        fg = lv > np.percentile(lv, 15)
        sel = (e >= np.percentile(e[fg], 70)) & fg
        sel[:1], sel[-1:], sel[:, :1], sel[:, -1:] = False, False, False, False
        clip = rgb.max(0).values > 0.9 * (run.white - run.black)
        sel &= ~(torch.nn.functional.avg_pool2d(clip.float()[None, None], T, T)[0, 0].cpu().numpy() > 0.01)[:ty, :tx]
        cx, cy = (W - 1) / 2, (H - 1) / 2
        n0 = len(pos)
        for y, x in np.argwhere(sel):
            a = rgb[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
            a = a - a.mean((1, 2), keepdim=True)
            Fa = torch.fft.fft2(a * win)
            pos.append([x * T + T / 2 - cx, y * T + T / 2 - cy])
            for c in (0, 2):
                X = Fa[c] * Fa[1].conj()
                for b, fit in enumerate(fits):
                    S[(c, b)].append(shift_of(X, fit))
        print(f'plane {p}: {len(pos) - n0} in-focus tiles', flush=True)
        del rgb
    pos = np.array(pos)
    report = {'planes': planes, 'tiles': len(pos), 'bands': BANDS, 'channels': {}}
    for c, name in ((0, 'R'), (2, 'B')):
        rows = []
        for b, (lo, hi) in enumerate(BANDS):
            s = np.array(S[(c, b)])
            A = np.zeros((2 * len(pos), 3))
            A[0::2, 0] = 1
            A[1::2, 1] = 1
            A[0::2, 2], A[1::2, 2] = pos[:, 0], pos[:, 1]
            # robust: two passes, dropping tiles beyond 3 px of the fit (phase wraps at low coherence)
            keep = np.ones(len(pos), bool)
            for _ in range(2):
                k2 = np.repeat(keep, 2)
                sol, *_ = np.linalg.lstsq(A[k2], s.reshape(-1)[k2], rcond=None)
                res = (s.reshape(-1) - A @ sol).reshape(-1, 2)
                keep = np.hypot(res[:, 0], res[:, 1]) < 3.0
            rows.append({'band': [lo, hi], 'scale_ppm': float(sol[2] * 1e6), 'offset_px': [float(sol[0]), float(sol[1])],
                         'residual_rms_px': float(np.sqrt((res[keep] ** 2).sum(1).mean())), 'tiles_kept': int(keep.sum())})
            print(f'{name} against green in the raw frame, {lo:.2f}-{hi:.2f} cycles/px: scale {sol[2] * 1e6:+7.1f} ppm, offset ({sol[0]:+.3f}, {sol[1]:+.3f}) px, '
                  f'residual {rows[-1]["residual_rms_px"]:.3f} px rms over {int(keep.sum())} of {len(pos)} tiles')
        report['channels'][name] = rows
    out.write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
