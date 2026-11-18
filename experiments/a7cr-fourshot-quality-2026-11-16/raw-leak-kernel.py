"""R7: what is the green-coherent fine detail in red and blue? Its spatial
kernel, measured in the raw frames.

  python -X utf8 raw-leak-kernel.py OUT.json MEMBER_CACHE [--planes 20,60,100,140,180]

Two candidates put green's fine detail into the red and blue samples at
green's own position:
  spectral    the red (blue) filter passes some of the light green's image
              is made of: the leak is green's image at the same site,
              G-transfer T(f) = k at every frequency and direction;
  crosstalk   charge or light from the four edge-adjacent photosites, all
              green on a Bayer sensor: the leak is green's image through the
              kernel [0 1 0; 1 0 1; 0 1 0] / 4, T(f) = k (cos 2 pi fx +
              cos 2 pi fy) / 2: on the axes it falls to 0.5 k at 0.25
              cycles/px and 0.1 k at 0.4; on the diagonal it is zero at
              |f| = 0.354 and negative beyond.

Measured per assembled group (fp.assemble: integer offsets, nothing
interpolated; red, blue and the two green samples of a site come from
different exposures, so every product below is free of common noise):

    T_c(fx, fy) = sum Re(F_c conj F_G) / sum Re(F_Ga conj F_Gb)

over in-focus tiles of the listed planes, in raw units (not white
balanced). On this subject red's and blue's own fine detail is nearly
independent of green's (round 1), so above about 0.2 cycles/px T is the leak
kernel itself. Reported by radial bin in two sectors: within 15 degrees of
an axis, within 15 degrees of a diagonal.

Fooled by: own-band detail that is coherent with green (adds an isotropic,
falling term: large at coarse scale, hence the coarse bins are not the
leak); lateral colour of the own band (it only lowers that term); member
motion (0.05-0.1 px: a few per cent of phase at 0.4 cycles/px).
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp
import evaluate as ev

T = 256
EDGES = [0.04, 0.08, 0.12, 0.16, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]


def arg(name, default=None):
    for i, tok in enumerate(sys.argv):
        if tok == name:
            return sys.argv[i + 1]
    return default


def main():
    out, cache = Path(sys.argv[1]), sys.argv[2]
    run = fp.Run(cache)
    planes = [int(v) for v in arg('--planes', '20,60,100,140,180').split(',')]
    dev = fp.DEV
    win = ev.hann2(T, dev)
    fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[:, None]
    fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[None, :]
    fr = torch.sqrt(fx * fx + fy * fy)
    ang = torch.rad2deg(torch.atan2(fy.abs().expand(T, T), fx.abs().expand(T, T)))      # 0..90
    axis = (ang < 15) | (ang > 75)
    diag = (ang > 30) & (ang < 60)
    num = {c: torch.zeros(T, T, dtype=torch.float64, device=dev) for c in (0, 2)}
    den = torch.zeros(T, T, dtype=torch.float64, device=dev)
    own = {c: torch.zeros(T, T, dtype=torch.float64, device=dev) for c in (0, 2)}
    tiles = 0
    for p in planes:
        m = run.meta[p]
        rgb, _, gdiff = fp.assemble(run.members(p), m['offsets'], m['gains'], run.P)
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
        for y, x in np.argwhere(sel):
            sl = (slice(y * T, (y + 1) * T), slice(x * T, (x + 1) * T))
            a = rgb[(slice(None),) + sl].double()
            d = gdiff[sl].double()
            a = a - a.mean((1, 2), keepdim=True)
            d = d - d.mean()
            Fa = torch.fft.fft2(a * win)
            Fd = torch.fft.fft2(d * win)
            Fga, Fgb = Fa[1] + 0.5 * Fd, Fa[1] - 0.5 * Fd
            den += (Fga * Fgb.conj()).real
            for c in (0, 2):
                num[c] += (Fa[c] * Fa[1].conj()).real
                own[c] += Fa[c].abs() ** 2
            tiles += 1
        print(f'plane {p}: {tiles} tiles so far', flush=True)
        del rgb
    report = {'planes': planes, 'tiles': tiles, 'edges': EDGES, 'channels': {}}
    print('cycles/px:            ' + ' '.join(f'{0.5 * (lo + hi):6.3f}' for lo, hi in zip(EDGES[:-1], EDGES[1:])))
    for c, name in ((0, 'R'), (2, 'B')):
        rows = {}
        for sname, sec in (('axes', axis), ('diagonals', diag)):
            vals = []
            for lo, hi in zip(EDGES[:-1], EDGES[1:]):
                mk = sec & (fr >= lo) & (fr < hi)
                vals.append(float(num[c][mk].sum() / den[mk].sum()))
            rows[sname] = vals
            print(f'{name} T, {sname:9s}:       ' + ' '.join(f'{v:+6.3f}' for v in vals))
        report['channels'][name] = rows
    # what the crosstalk kernel would give for k = the 0.16-0.25 axis value / its kernel there
    for sname, sec in (('axes', axis), ('diagonals', diag)):
        vals = []
        for lo, hi in zip(EDGES[:-1], EDGES[1:]):
            mk = sec & (fr >= lo) & (fr < hi)
            kern = 0.5 * (torch.cos(2 * np.pi * fx) + torch.cos(2 * np.pi * fy)).expand(T, T)
            vals.append(float((kern * den)[mk].sum() / den[mk].sum()))
        print(f'crosstalk kernel, {sname:9s}: ' + ' '.join(f'{v:+6.3f}' for v in vals) + '   (times k; the spectral kernel is 1 everywhere)')
        report[f'crosstalk_kernel_{sname}'] = vals
    out.write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
