"""R4: do frames on opposite sides of a tile's focus combine coherently?

  python -X utf8 rank-check.py SERIES_FOCUS.npz

Input: series-focus.py's npz (per tile, channel and band, the matrix P of
products between the 17 registered frames around the tile's focus; noise is
independent between frames, so off-diagonal entries are noise-free).

Per band, green, median over tiles, in units of the best frame's
signal-to-noise (equal noise per frame assumed):
  magnitude bound   sum of the frames' own powers (neighbour products) over
                    the largest: what ideal weights could use if every
                    frame held the same image
  signed rank-1     the largest eigenvalue of P with its diagonal completed
                    by a rank-1 fit: the best single combination with
                    weights of either sign
  rank-2            the same with two components
  positive matched  weights proportional to each frame's amplitude
and the share of frame pairs at least six apart on opposite sides of focus
whose product is negative.

If the frames held one image through different real transfers, rank-1 would
reach the magnitude bound. On this subject it does not, and far pairs are as
often negative as positive: over a tile, different parts are in focus in
different frames (see point-focus.py for the per-pixel version).
"""
import sys

import numpy as np


def complete(Pm, rank, iters=200):
    off = 1 - np.eye(len(Pm))
    M = Pm.copy()
    for _ in range(iters):
        w, v = np.linalg.eigh(M)
        w, v = w[::-1][:rank], v[:, ::-1][:, :rank]
        L = (v * np.clip(w, 0, None)) @ v.T
        M = Pm * off + np.diag(np.diag(L))
    return np.linalg.eigvalsh(M)[::-1]


def main():
    z = np.load(sys.argv[1])
    P = z['Preg'].astype(np.float64)
    n, _, nb, nw, _ = P.shape
    half = nw // 2
    bands = z['bands']
    off = 1 - np.eye(nw)
    for b in range(nb):
        r1, r2, mag, pos, sgn = [], [], [], [], []
        for i in range(n):
            Pm = P[i, 1, b]
            q = np.array([Pm[j, j + 1] for j in range(nw - 1)])
            hmax2 = q.max()
            if hmax2 <= 0:
                continue
            w1, w2 = complete(Pm, 1), complete(Pm, 2)
            r1.append(w1[0] / hmax2)
            r2.append((w2[0] + max(w2[1], 0)) / hmax2)
            mag.append(np.clip(q, 0, None).sum() / hmax2 * nw / (nw - 1))
            h = np.sqrt(np.clip(0.5 * (np.r_[0, q] + np.r_[q, 0]), 0, None))
            s2 = (np.outer(h, h) * Pm * off).sum() / (h.sum() ** 2 - (h ** 2).sum())
            pos.append(s2 / hmax2 / ((h ** 2).sum() / h.sum() ** 2))
            far = [(k, l) for k in range(half - 2) for l in range(half + 3, nw) if l - k >= 6]
            sgn.append(np.mean([Pm[k, l] < 0 for k, l in far]))
        print(f'G band {bands[b][0]:.2f}-{bands[b][1]:.2f}: magnitude bound {np.median(mag):.1f}; signed rank-1 {np.median(r1):.1f}; '
              f'rank-2 {np.median(r2):.1f}; positive matched {np.median(pos):.1f}; far opposite-side pairs negative {100 * np.mean(sgn):.0f} %')


if __name__ == '__main__':
    main()
