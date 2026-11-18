"""Q4 prototype: the fusion with every band brought back to the election's
amplitude, and everything coarser than the fused bands taken from the
election ("calibrated fusion"), built from finished renders.

  python -X utf8 calibrated-fusion.py OUT_PREFIX E_ODD.tif E_EVEN.tif F_ODD.tif F_EVEN.tif [--coarsest 32]

The dark lift of the depth-guided fusion is a loss of contrast: averaging
frames across focus passes each band at a little under the in-focus frame's
amplitude (2 % at 0.05 cycles/px, 18 % at 0.25, measured), and a 1 % loss of
a bright-against-dark contrast is a 10-20 % rise of the dark side. The fix
tried here is the simplest one a merge could apply to its own levels: one
gain per band, the ratio of the election's signal to the fusion's.

Bands: undecimated differences of Gaussians at 0, 1, 2, 4, ... px up to
--coarsest, linear values. Per band and channel

  g_k = < E_k(this half) E_k(other half) > / < F_k(this half) E_k(other half) >

(the other half's noise is independent, so neither product is biased by
noise; both halves' estimates are averaged), then

  C = lowpass_coarsest(E) + sum_k g_k F_k.

Writes OUT_PREFIX-odd.tif / -even.tif and prints the gains.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    coarsest = float(sys.argv[sys.argv.index('--coarsest') + 1]) if '--coarsest' in sys.argv else 32.0
    if '--coarsest' in sys.argv:
        args.remove(sys.argv[sys.argv.index('--coarsest') + 1])
    prefix, eo, ee, fo, fe = args
    scales = [1.0]
    while scales[-1] < coarsest:
        scales.append(scales[-1] * 2)
    dev = fp.DEV

    def load(f):
        return torch.from_numpy(tifffile.imread(f).astype(np.float32)).to(dev).permute(2, 0, 1)

    def split(x):
        out, prev = [], x
        for s in scales:
            g = fp.gauss(x, s)
            out.append(prev - g)
            prev = g
        return out, prev

    E = [load(eo), load(ee)]
    F = [load(fo), load(fe)]
    out = [torch.zeros_like(E[0]), torch.zeros_like(E[1])]
    print('band (px)      ' + ' '.join(f'{("0-" if i == 0 else f"{scales[i - 1]:.0f}-") + f"{s:.0f}":>8s}' for i, s in enumerate(scales)))
    for c in range(3):
        eb, el, fb = [], [], []
        for h in range(2):
            b, low = split(E[h][c])
            eb.append(b)
            el.append(low)
            fb.append(split(F[h][c])[0])
        gains = []
        for k in range(len(scales)):
            num = float((eb[0][k].double() * eb[1][k].double()).mean())
            den = 0.5 * (float((fb[0][k].double() * eb[1][k].double()).mean()) + float((fb[1][k].double() * eb[0][k].double()).mean()))
            gains.append(num / den)
        for h in range(2):
            acc = el[h].clone()
            for k in range(len(scales)):
                acc += gains[k] * fb[h][k]
            out[h][c] = acc.clamp(0, 65535)
        print(f'gain {"RGB"[c]}         ' + ' '.join(f'{g:8.4f}' for g in gains))
        del eb, el, fb
    for h, name in enumerate(('odd', 'even')):
        tifffile.imwrite(f'{prefix}-{name}.tif', out[h].permute(1, 2, 0).round().cpu().numpy().astype(np.uint16), photometric='rgb')


if __name__ == '__main__':
    with torch.no_grad():
        main()
