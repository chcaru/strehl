"""M111 -- the premise the recommended fix rests on, measured rather than argued.

The proposal is to replace pass two's boolean admit/reject with a weight that
falls off smoothly in the response margin. Its whole claim to remove the seams
without costing sharpness is this: AT a plateau seam the two competing frames
are nearly tied in response, so a soft weight blends them there, while away from
seams the winner is far ahead and keeps its dominance.

That is a factual claim about the winner field and it is checkable. If
`best_focus` is discontinuous across election seams, the frames are NOT tied
there, the argument fails, and the recommendation should not be made.

Measured, in the low-admission flat population and its controls:
  * |delta best_focus| across seams against |delta best_focus| off seams;
  * the runner-up margin is not dumped, so `best_focus` continuity is the
    available proxy and is reported as such.
"""

import os

import numpy as np
import tifffile
from scipy import ndimage

RENDER = r"C:\dev\strehl-out\M111\render"
FLAT_SD, LOW_N, HIGH_N, MARGIN = 300.0, 8, 64, 64


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def plane_luma(p):
    y = luma(tifffile.imread(p))
    return 0.25 * (y[0::2, 0::2] + y[1::2, 0::2] + y[0::2, 1::2] + y[1::2, 1::2])


def local_sd(y, r=4):
    k = 2 * r + 1
    m = ndimage.uniform_filter(y, k, mode="nearest")
    m2 = ndimage.uniform_filter(y * y, k, mode="nearest")
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def across(idx, f, mask):
    dh = idx[:, 1:] != idx[:, :-1]
    dv = idx[1:, :] != idx[:-1, :]
    mh = mask[:, 1:] & mask[:, :-1]
    mv = mask[1:, :] & mask[:-1, :]
    v = np.concatenate([np.abs(f[:, 1:] - f[:, :-1])[mh], np.abs(f[1:, :] - f[:-1, :])[mv]])
    on = np.concatenate([dh[mh], dv[mv]])
    return float(np.median(v[on])), float(np.median(v[~on])), int(on.sum())


def main():
    st = os.path.join(RENDER, "state-r8")
    y = plane_luma(os.path.join(RENDER, "marker-dump.tif"))
    idx = np.load(os.path.join(st, "best_index.npy"))
    bf = np.load(os.path.join(st, "best_focus.npy"))
    ne = np.load(os.path.join(st, "n_eff_gate4.00.npy"))
    inner = np.zeros(y.shape, bool)
    inner[MARGIN:-MARGIN, MARGIN:-MARGIN] = True
    flat = (local_sd(y) < FLAT_SD) & inner
    pops = {
        "low  (flat, n_eff<=8)": flat & (ne <= LOW_N),
        "high (flat, n_eff>=64)": flat & (ne >= HIGH_N),
        "rough (textured)": (local_sd(y) >= FLAT_SD * 4) & inner,
    }
    tol = 4.0 * np.sqrt(2.0) * 0.015214
    print(f"gate-4 admission tolerance = {tol:.6f} focus units\n")
    print(f"{'population':>24} {'|d bf| on seam':>15} {'off seam':>10} {'ratio':>7}"
          f" {'on/tol':>8} {'|d idx| on seam':>16}")
    for nm, m in pops.items():
        on, off, n = across(idx, bf, m)
        di = idx.astype(np.int32)
        dh = np.abs(di[:, 1:] - di[:, :-1])
        dv = np.abs(di[1:, :] - di[:-1, :])
        mh = m[:, 1:] & m[:, :-1]
        mv = m[1:, :] & m[:-1, :]
        dd = np.concatenate([dh[mh], dv[mv]])
        dd = dd[dd > 0]
        print(f"{nm:>24} {on:15.5f} {off:10.5f} {on / max(off, 1e-9):7.3f}"
              f" {on / tol:8.3f} {np.median(dd):16.0f}   (n={n})")
    print("\nread: a seam is a place where the winner LABEL jumps by a large number of")
    print("frames while the winner RESPONSE barely moves. That is the tie the soft")
    print("weight would blend, and it is why a blend can remove the seam without")
    print("giving up the winner where the winner is genuinely ahead.")


if __name__ == "__main__":
    main()
