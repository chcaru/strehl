"""Q6 (and the floor beyond the cutoff): the halves' two-dimensional signal and
noise spectra on in-focus tiles.

  python -X utf8 spectrum2d.py OUT_PREFIX ODD.tif EVEN.tif [--flat]

Tiles as cross-channel.py (or, with --flat, the 30 % of foreground tiles with
the LEAST green high-pass energy: smooth, mostly defocused surface, where a
two-photosite-period pattern is not hidden under scene detail). Per channel,
the tile-mean S(fx, fy) = Re A conj(B) (shift removed on green) and
N = (|A|^2 + |B|^2) / 2 - S, fftshifted, saved as OUT_PREFIX-{S,N}.npy
([3, T, T]) and a log-scaled PNG of S / median(N).

Printed per channel:
- power at the three Nyquist points (0.5, 0), (0, 0.5), (0.5, 0.5) in S and
  in the auto-spectrum, against the median of the ring of bins 2-4 away
  (a two-photosite-period pattern is a spike there; a pattern modulated by
  the scene is a blob around it);
- S / N in rings beyond the diffraction cutoff, split into the axis
  neighbourhoods and the diagonal corners.

Fooled by: nothing in a ratio to neighbours except real scene content at
exactly Nyquist, which the lens does not pass on the diagonal.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp
import evaluate as ev

T = ev.T


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flat = '--flat' in sys.argv
    prefix, fa, fb = args[0], args[1], args[2]
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
    sel = ((e <= np.percentile(e[fg], 30)) if flat else (e >= np.percentile(e[fg], 70))) & fg
    sel[:1], sel[-1:], sel[:, :1], sel[:, -1:] = False, False, False, False
    clip = (A.max(0).values > 60000) | (B.max(0).values > 60000)
    clipt = torch.nn.functional.avg_pool2d(clip.float()[None, None], T, T)[0, 0].cpu().numpy() > 0.01
    sel &= ~clipt[:ty, :tx]
    tiles = [(int(x), int(y)) for y, x in np.argwhere(sel)]
    print(f'{"flat" if flat else "in-focus"} tiles {len(tiles)}')
    win = ev.hann2(T, dev)
    norm = T * T * float((win * win).sum())
    fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[:, None]
    fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[None, :]
    S = torch.zeros(3, T, T, dtype=torch.float64, device=dev)
    N = torch.zeros_like(S)
    level = torch.zeros(3, dtype=torch.float64, device=dev)
    for x, y in tiles:
        a = A[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        b = B[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        level += 0.5 * (a.mean((1, 2)) + b.mean((1, 2)))
        a = a - a.mean((1, 2), keepdim=True)
        b = b - b.mean((1, 2), keepdim=True)
        FA, FB = torch.fft.fft2(a * win), torch.fft.fft2(b * win)
        _, _, (sx, sy) = ev.pair_spectra(a[1], b[1], win)
        FB = FB * torch.exp(2j * np.pi * (fx * sx + fy * sy))
        s = (FA * FB.conj()).real / norm
        S += s
        N += (FA.abs() ** 2 + FB.abs() ** 2) / (2 * norm) - s
    S /= len(tiles)
    N /= len(tiles)
    level /= len(tiles)
    Ss = torch.fft.fftshift(S, dim=(1, 2)).cpu().numpy()
    Ns = torch.fft.fftshift(N, dim=(1, 2)).cpu().numpy()
    np.save(prefix + '-S.npy', Ss.astype(np.float32))
    np.save(prefix + '-N.npy', Ns.astype(np.float32))
    c0 = T // 2
    fxx = (np.arange(T) - c0) / T
    FX, FY = np.meshgrid(fxx, fxx)
    FR = np.hypot(FX, FY)
    print('mean level (16-bit units) R/G/B: ' + ' / '.join(f'{float(v):.0f}' for v in level))
    # index of frequency -0.5 is 0 after fftshift; +0.5 aliases onto it.
    pts = {'(0.5, 0)': (c0, 0), '(0, 0.5)': (0, c0), '(0.5, 0.5)': (0, 0)}
    for c in range(3):
        auto = Ss[c] + Ns[c]
        line = []
        for name, (iy, ix) in pts.items():
            ys = [(iy + d) % T for d in range(-4, 5)]
            xs = [(ix + d) % T for d in range(-4, 5)]
            ring_s, ring_a = [], []
            for yy in ys:
                for xx in xs:
                    dy = min((yy - iy) % T, (iy - yy) % T)
                    dx = min((xx - ix) % T, (ix - xx) % T)
                    if 2 <= max(dx, dy) <= 4:
                        ring_s.append(Ss[c][yy, xx])
                        ring_a.append(auto[yy, xx])
            line.append(f'{name}: S {Ss[c][iy, ix]:.2e} (ring {np.median(ring_s):.2e}), auto x{auto[iy, ix] / np.median(ring_a):.2f} of ring')
        print(f'{"RGB"[c]}  ' + ';  '.join(line))
        # the spike as an amplitude relative to the mean level: a pattern
        # v * (1 + a * (-1)^x) puts a^2 * level^2 * (window gain) in one bin.
        wsum = float(win.sum()) ** 2 / norm
        for name, (iy, ix) in pts.items():
            excess = max(auto[iy, ix] - np.median([auto[(iy + d) % T, (ix + e2) % T] for d in (-3, -2, 2, 3) for e2 in (-3, -2, 2, 3)]), 0)
            amp = np.sqrt(excess / wsum) / float(level[c])
            print(f'      {name}: pattern amplitude {100 * amp:.4f} % of the mean level (auto-spectrum excess over neighbours)')
        for lo, hi in ((0.40, 0.45), (0.45, 0.50), (0.56, 0.60), (0.60, 0.65), (0.65, 0.70)):
            ring = (FR >= lo) & (FR < hi)
            print(f'      ring {lo:.2f}-{hi:.2f}: S/N {Ss[c][ring].sum() / Ns[c][ring].sum():+.3f}   S {Ss[c][ring].mean():.2e}  N {Ns[c][ring].mean():.2e}')
        corner = (np.abs(FX) > 0.42) & (np.abs(FY) > 0.42)
        edge_x = (np.abs(FX) > 0.46) & (np.abs(FY) < 0.2)
        edge_y = (np.abs(FY) > 0.46) & (np.abs(FX) < 0.2)
        mid = (FR > 0.56) & ~corner
        for name, msk in (('corner |fx|,|fy|>0.42', corner), ('x edge |fx|>0.46,|fy|<0.2', edge_x), ('y edge', edge_y)):
            print(f'      {name}: S/N {Ss[c][msk].sum() / Ns[c][msk].sum():+.3f}')
    ratio = np.clip(Ss / np.median(Ns, axis=(1, 2), keepdims=True), 1e-3, 1e3)
    img = (np.log10(ratio) + 3) / 6
    Image.fromarray((np.concatenate(list(img), axis=1) * 255).astype(np.uint8)).resize((3 * 2 * T, 2 * T), Image.NEAREST).save(prefix + '-S.png')
    nimg = np.clip(Ns / np.median(Ns, axis=(1, 2), keepdims=True), 0, 2) / 2
    Image.fromarray((np.concatenate(list(nimg), axis=1) * 255).astype(np.uint8)).resize((3 * 2 * T, 2 * T), Image.NEAREST).save(prefix + '-N.png')


if __name__ == '__main__':
    with torch.no_grad():
        main()
