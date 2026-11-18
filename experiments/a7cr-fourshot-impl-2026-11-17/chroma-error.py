"""Item 3: how well does each finished arm's red, green and blue match that
channel's own content, scored against an independent half-stack?

  python -X utf8 chroma-error.py OUT.json RAW_ODD.tif RAW_EVEN.tif NAME=ODD.tif [NAME=ODD.tif ...]

RAW_ODD / RAW_EVEN: the halves of an arm with no chroma filter
(`STREHL_CARRY_RGB=raw`, same restoration). Each NAME=ODD.tif is the odd half
of an arm that differs from RAW only in its chroma step, so its noise is
the raw odd half's, filtered, and independent of RAW_EVEN's.

Tiles: 256 px where RAW_EVEN's green high-pass energy is in the top 30 %
and under 1 % of pixels are near clipping. Per tile, channel and radial bin
(0.01 cycles/px), Hann window:
  S_c = Re <A_c conj(B_c)>              raw halves' shared power (signal)
  N_c = <|A_c|^2 + |B_c|^2> / 2 - S_c   one raw half's noise power
  E_c(X) = <|X_c - B_c|^2> - N_c        squared error of arm X's estimate of
                                        channel c's noise-free content
Reported: E / S integrated over 0.10-0.25 and 0.25-0.40 cycles/px, in % (100 %
is what writing no fine detail at all would score), and each arm's noise
power in those bands relative to the raw arm's (from <|X_c|^2> - <Re X_c
conj B_c>, which is X's own noise power when X's signal matches B's).

Control: the raw odd half itself as an arm (RAW=RAW_ODD) must read E = N,
i.e. E / S equal to the raw noise-to-signal ratio.
Fooled by: content both halves share that is not scene (sensor pattern is
independent between channels at a site, so it cannot favour borrowing);
one subject.
"""
import json
import sys

import numpy as np
import tifffile

T = 256
BIN = 0.01
NB = 72


def main():
    out = sys.argv[1]
    a = tifffile.imread(sys.argv[2]).astype(np.float32)
    b = tifffile.imread(sys.argv[3]).astype(np.float32)
    arms = [(s.split('=', 1)[0], tifffile.imread(s.split('=', 1)[1]).astype(np.float32)) for s in sys.argv[4:]]
    h, w, _ = b.shape
    g = b[..., 1]
    from scipy.ndimage import gaussian_filter
    hp = gaussian_filter((g - gaussian_filter(g, 2.0)) ** 2, 8.0)
    clip = 0.95 * float(np.percentile(b, 99.99))
    cands = []
    for y in range(0, h - T, T):
        for x in range(0, w - T, T):
            t = b[y:y + T, x:x + T]
            if (t > clip).mean() > 0.01:
                continue
            cands.append((float(hp[y:y + T, x:x + T].mean()), y, x))
    cands.sort(reverse=True)
    tiles = [(y, x) for _, y, x in cands[:max(1, int(0.3 * len(cands)))]]
    win = np.outer(np.hanning(T), np.hanning(T)).astype(np.float32)
    norm = float((win ** 2).sum())
    fy, fx = np.meshgrid(np.fft.fftfreq(T), np.fft.fftfreq(T), indexing='ij')
    rbin = np.minimum((np.hypot(fx, fy) / BIN).astype(int), NB)
    S = np.zeros((3, NB))
    N = np.zeros((3, NB))
    E = {n: np.zeros((3, NB)) for n, _ in arms}
    P = {n: np.zeros((3, NB)) for n, _ in arms}
    cnt = np.bincount(rbin.ravel(), minlength=NB + 1)[:NB]

    def ft(t):
        return np.fft.fft2((t - t.mean()) * win)

    def rad(v):
        return np.bincount(rbin.ravel(), weights=v.ravel(), minlength=NB + 1)[:NB]

    for y, x in tiles:
        for c in range(3):
            A = ft(a[y:y + T, x:x + T, c])
            B = ft(b[y:y + T, x:x + T, c])
            s = (A * B.conj()).real
            S[c] += rad(s) / norm
            N[c] += rad((np.abs(A) ** 2 + np.abs(B) ** 2) / 2 - s) / norm
            for n, im in arms:
                X = ft(im[y:y + T, x:x + T, c])
                E[n][c] += rad(np.abs(X - B) ** 2) / norm
                P[n][c] += rad(np.abs(X) ** 2 - (X * B.conj()).real) / norm
    k = len(tiles) * np.maximum(cnt, 1)
    S, N = S / k, N / k
    centres = (np.arange(NB) + 0.5) * BIN
    bands = {'0.10-0.25': (0.10, 0.25), '0.25-0.40': (0.25, 0.40)}
    report = {'tiles': len(tiles), 'arms': {}}
    print(f'tiles {len(tiles)}; E / S in %, and noise power relative to the raw half, per channel R G B')
    for n, _ in arms:
        e = E[n] / k - N
        p = P[n] / k
        row = {}
        for bn, (lo, hi) in bands.items():
            m = (centres >= lo) & (centres < hi)
            row[bn] = {
                'error_pct': [100 * float(e[c][m].sum() / S[c][m].sum()) for c in range(3)],
                'noise_ratio': [float(p[c][m].sum() / N[c][m].sum()) for c in range(3)],
            }
        report['arms'][n] = row
        print(f'{n:12s} ' + '   '.join(
            f'{bn}: error {"/".join(f"{v:.1f}" for v in row[bn]["error_pct"])} noise {"/".join(f"{v:.2f}" for v in row[bn]["noise_ratio"])}'
            for bn in bands))
    with open(out, 'w') as f:
        json.dump(report, f, indent=1)


if __name__ == '__main__':
    main()
