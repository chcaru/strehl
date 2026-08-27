r"""What is the PITCH of the cross-hatch visible in the master's band field, and
is it in the MASTER or in the GATE'S OWN boxblur?

orch_blotch.boxblur runs a double cumsum in whatever dtype it is handed;
lum_of() returns float32, so the cumulative sum reaches ~1e10 in float32 and the
4-corner difference is a catastrophic cancellation.  That is a candidate source
of a periodic-looking texture that lives in the INSTRUMENT, not the picture.
So compute the identical band field twice -- gate dtype and float64 -- and
difference them, then find the pitch spectrally in each.

  python vr_pitch.py SUBJECT [--src=K]
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402
from orch_blotch import boxblur as gate_boxblur, LO_R, HI_R   # noqa: E402


def box64(a, r):
    if r < 1:
        return a.astype(np.float64).copy()
    p = np.pad(a.astype(np.float64), r, mode="edge")
    c = np.cumsum(np.cumsum(p, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)), mode="constant")
    k = 2 * r + 1
    s = (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k])
    return s / (k * k)


def band(blk, bb):
    return (bb(blk, LO_R // 2) - bb(blk, HI_R // 2)) / max(float(np.mean(blk)), 1e-12)


def peaks(B, tag, n=8):
    f = B - B.mean()
    h = np.hanning(f.shape[0])[:, None] * np.hanning(f.shape[1])[None, :]
    P = np.abs(np.fft.rfft2(f * h)) ** 2
    W = f.shape[0]
    tot = P.sum()
    idx = []
    Pw = P.copy()
    Pw[:3, :3] = 0
    # kill the low-frequency subject: everything with radius < W/45 px^-1
    vv, uu = np.meshgrid(np.fft.fftfreq(W) * W, np.arange(P.shape[1]), indexing="ij")
    rad = np.hypot(vv, uu)
    Pw[rad < 20] = 0
    print("  %-26s sd %.6f   power>r20 %.3f%% of total" % (tag, float(np.std(B)),
                                                           100 * Pw.sum() / max(tot, 1e-30)))
    flat = np.argsort(Pw.ravel())[::-1][:n]
    for i in flat:
        v, u = np.unravel_index(i, P.shape)
        vs = v if v <= W // 2 else v - W
        py = W / abs(vs) if vs else np.inf
        px = W / u if u else np.inf
        print("      peak u=%3d v=%4d  pitch_x=%6.1f pitch_y=%6.1f  power %.3f%%"
              % (u, vs, px, py, 100 * Pw[v, u] / max(Pw.sum(), 1e-30)))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "1")
                for a in sys.argv[1:] if a.startswith("--"))
    subj = args[0]
    with open(os.path.join(V.OUT, "source_%s.json" % subj)) as fh:
        S = json.load(fh)
    wy, wx = S["master"]["blotch"]["y"], S["master"]["blotch"]["x"]
    W = V.BWIN
    win = V.lum_of(V.read_rgb(V.master_path(subj)))[wy:wy + W, wx:wx + W]
    print("SUBJECT %s window (%d,%d) mean %.1f" % (subj, wy, wx, win.mean()))
    B32 = band(win, gate_boxblur)
    B64 = band(win, box64)
    d = B32 - B64
    print("  gate float32 band sd %.6f | float64 band sd %.6f | difference sd %.3g"
          " (%.4f%% of band)" % (float(np.std(B32)), float(np.std(B64)), float(np.std(d)),
                                 100 * np.std(d) / max(np.std(B64), 1e-30)))
    peaks(B32, "gate float32 band")
    peaks(B64, "float64 band")
    peaks(d.astype(np.float64), "float32 MINUS float64")


if __name__ == "__main__":
    main()
