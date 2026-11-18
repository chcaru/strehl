"""Q4 prototype: fusion kept only where it agrees with the election within
noise ("consistency-gated fusion"), built from finished renders.

  python -X utf8 gated-fusion.py OUT_PREFIX E_ODD.tif E_EVEN.tif F_ODD.tif F_EVEN.tif [--z0 2.5 --z1 4.0]

E: the election merge (colour carry), F: the depth-guided fusion of the same
frames; odd- and even-frame half-stacks of each. Writes OUT_PREFIX-odd.tif
and -even.tif (16-bit linear RGB like the inputs), each built from that
half's own E and F only.

Per half and channel, in the square-root domain (noise roughly uniform):
D = F - E is split into undecimated bands (differences of Gaussians at
0, 1, 2, 4, 8, 16, 32 px and the 32 px residual). The fusion's noise
reduction lives in D as zero-mean noise; its defects (light spread into
shadows, lost fine contrast) live in D as structure that keeps its sign
over a band's own scale. So each band of D is smoothed at its scale,
compared with that smoothed band's noise (from the two halves' difference,
robust), and the band is kept where |z| < z0, dropped where |z| > z1, with
a cosine hand-over between:

  C = E + sum_k m_k B_k(D)

Noise scale per band: 1.4826 x median |s_odd - s_even| / sqrt(2), with s the
smoothed band. The two halves' D differ by their independent noise but share
the systematic part, so their difference isolates noise.

This is a post-merge stand-in for a robust across-focus estimator; it needs
no second pass over the frames, only both finished merges.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp

SCALES = (1.0, 2.0, 4.0, 8.0, 16.0, 32.0)
ROOT_OFFSET = 110.0     # 25 DN of 14848 in 16-bit units


def bands(d):
    out, prev = [], d
    for s in SCALES:
        g = fp.gauss(d, s)
        out.append(prev - g)
        prev = g
    out.append(prev)
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    z0 = float(sys.argv[sys.argv.index('--z0') + 1]) if '--z0' in sys.argv else 2.5
    z1 = float(sys.argv[sys.argv.index('--z1') + 1]) if '--z1' in sys.argv else 4.0
    for flag in ('--z0', '--z1'):
        if flag in sys.argv:
            args.remove(sys.argv[sys.argv.index(flag) + 1])
    prefix, eo, ee, fo, fe = args
    dev = fp.DEV

    def load(f):
        return torch.from_numpy(tifffile.imread(f).astype(np.float32)).to(dev).permute(2, 0, 1)

    def root(x):
        return torch.sqrt(x.clamp(min=0) + ROOT_OFFSET)

    E = [load(eo), load(ee)]
    F = [load(fo), load(fe)]
    out = [torch.zeros_like(E[0]), torch.zeros_like(E[1])]
    kept = np.zeros((3, len(SCALES) + 1))
    for c in range(3):
        re = [root(E[h][c]) for h in range(2)]
        B = [bands(root(F[h][c]) - re[h]) for h in range(2)]
        acc = [re[0].clone(), re[1].clone()]
        for k in range(len(SCALES) + 1):
            sm = SCALES[min(k, len(SCALES) - 1)] if k > 0 else 1.0
            s = [fp.gauss(B[h][k], sm) for h in range(2)]
            sub = (s[0] - s[1])[::7, ::7].abs().flatten()
            sigma = 1.4826 * float(sub.median()) / np.sqrt(2)
            for h in range(2):
                z = s[h].abs() / max(sigma, 1e-9)
                m = torch.where(z <= z0, torch.ones_like(z), torch.where(z >= z1, torch.zeros_like(z), 0.5 * (1 + torch.cos(np.pi * (z - z0) / (z1 - z0)))))
                acc[h] += m * B[h][k]
                kept[c, k] += 0.5 * float(m.mean())
            del s
        for h in range(2):
            out[h][c] = (acc[h] ** 2 - ROOT_OFFSET).clamp(0, 65535)
        del B, re, acc
    print('fraction of the fusion kept per band (finest first, last = 32 px residual):')
    for c in range(3):
        print(f'  {"RGB"[c]}: ' + ' '.join(f'{v:.3f}' for v in kept[c]))
    for h, name in enumerate(('odd', 'even')):
        tifffile.imwrite(f'{prefix}-{name}.tif', out[h].permute(1, 2, 0).round().cpu().numpy().astype(np.uint16), photometric='rgb')


if __name__ == '__main__':
    with torch.no_grad():
        main()
