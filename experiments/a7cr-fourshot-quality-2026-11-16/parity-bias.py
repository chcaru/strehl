"""Does the election inflate the planes it elects on? (follow-up to Q6: the
halves share a noise-shaped floor beyond the lens's cutoff.)

  python -X utf8 parity-bias.py OUT.json ODD.tif EVEN.tif

A carried four-shot render interleaves twelve half-resolution site planes.
The election's weights come from green luma. If a frame's weight rises with
its own noisy coefficient, the elected coefficient is biased away from zero
in the planes whose noise entered the weight, and not in the others; the
bias follows the sign of the scene's coefficient, so two independent
half-stacks share it and it reads as signal.

Test: take each channel's four site planes (output pixel parity (px, py))
separately, 128 px plane tiles under cross-channel.py's in-focus tiles. Per
parity: cross-half signal S and noise N in plane-frequency bands. Absent a
bias every parity of a channel shows the same S (they sample the same image
at offset lattices). Reported: S and N per parity relative to the channel's
mean over parities, and the pair statistic

  beta = < (a_p - a_q)(b_p + b_q) > / < (a_p + a_q)(b_p + b_q) >

with a, b the two halves' high-passed planes at parities p (native) and q
(carried), each resampled to the quad centre by a half-pixel bilinear shift
(same for every arm): the excess amplitude of p over q that the other half
agrees with. Zero when nothing but noise distinguishes the planes.

Controls: the plain single-shot render (every channel demosaiced: parities
differ by which sites are native there too, so it is a positive control for
the instrument seeing a native/interpolated difference) and red/blue's
parities in the carried render.
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
P = T // 2


def main():
    out, fa, fb = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
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
    w1 = torch.hann_window(P, periodic=True, device=dev, dtype=torch.float64)
    win = w1[:, None] * w1[None, :]
    norm = P * P * float((win * win).sum())
    fy = torch.fft.fftfreq(P, device=dev, dtype=torch.float64)[:, None]
    fx = torch.fft.fftfreq(P, device=dev, dtype=torch.float64)[None, :]
    fr = torch.sqrt(fx * fx + fy * fy)
    bands = {'plane 0.05-0.15': (0.05, 0.15), 'plane 0.15-0.30': (0.15, 0.30), 'plane 0.30-0.50': (0.30, 0.50)}
    masks = {k: ((fr >= lo) & (fr < hi)).double() for k, (lo, hi) in bands.items()}
    par = [(0, 0), (1, 0), (0, 1), (1, 1)]
    S = {k: torch.zeros(3, 4, dtype=torch.float64, device=dev) for k in bands}
    N = {k: torch.zeros(3, 4, dtype=torch.float64, device=dev) for k in bands}
    for x, y in tiles:
        a = A[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        b = B[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        for c in range(3):
            for pi, (px, py) in enumerate(par):
                pa, pb = a[c, py::2, px::2], b[c, py::2, px::2]
                FA = torch.fft.fft2((pa - pa.mean()) * win)
                FB = torch.fft.fft2((pb - pb.mean()) * win)
                s = (FA * FB.conj()).real / norm
                n = (FA.abs() ** 2 + FB.abs() ** 2) / (2 * norm) - s
                for k in bands:
                    S[k][c, pi] += (s * masks[k]).sum()
                    N[k][c, pi] += (n * masks[k]).sum()
    report = {'tiles': len(tiles), 'parities': par, 'bands': {}}
    print(f'tiles {len(tiles)}; parities (px, py): {par}; RGGB native sites: R (0,0), G (1,0) and (0,1), B (1,1)')
    for k in bands:
        s, n = S[k].cpu().numpy(), N[k].cpu().numpy()
        report['bands'][k] = {'S': s.tolist(), 'N': n.tolist()}
        for c in range(3):
            print(f'  {k} {"RGB"[c]}: S / mean ' + ' '.join(f'{v:.4f}' for v in s[c] / s[c].mean())
                  + '   N / mean ' + ' '.join(f'{v:.4f}' for v in n[c] / n[c].mean())
                  + f'   S/N ' + ' '.join(f'{v:.2f}' for v in s[c] / n[c]))
    out.write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
