"""M60 step 2 — decode timing, drift probe, and cache the working crops.

Read-only against the corpus. Caches green-sublattice crops as .npy under ../data/cache
so the later scripts do not re-decode.

Drift: AGENTS rule 6 forbids CHAINING alignments as a solution. Here the span-1
ladder is used only as a DIAGNOSTIC of how much the frame moves, and fact 51 says
a span-1 chain UNDER-reports, so the cumulative sum below is a LOWER BOUND on the
total drift, never a correction.
"""

import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
CACHE = os.path.join(DATA, "cache")
os.makedirs(CACHE, exist_ok=True)

# Green sublattice is 2344 x 3514 for the A7C II active area (4688 x 7028).
GH, GW = 2344, 3514


def phase_shift(a, b):
    """Integer + subpixel translation of b relative to a, by phase correlation."""
    A = np.fft.rfft2(a - a.mean())
    B = np.fft.rfft2(b - b.mean())
    R = A * np.conj(B)
    R /= np.maximum(np.abs(R), 1e-12)
    c = np.fft.irfft2(R, a.shape)
    p = np.unravel_index(np.argmax(c), c.shape)
    dy = p[0] - (a.shape[0] if p[0] > a.shape[0] // 2 else 0)
    dx = p[1] - (a.shape[1] if p[1] > a.shape[1] // 2 else 0)
    return float(dy), float(dx)


def cache_crop(stack, crop, tag, step=1):
    """Decode a stack once and store the green crop cube as float32 .npy."""
    out = os.path.join(CACHE, "%s-%s.npy" % (stack, tag))
    if os.path.exists(out):
        return out
    fs = L.frames(stack)[::step]
    y0, y1, x0, x1 = crop
    cube = np.empty((len(fs), y1 - y0, x1 - x0), np.float32)
    t0 = time.time()
    for i, f in enumerate(fs):
        cube[i] = L.load_green(f, crop)
        if i % 50 == 0:
            print("   %s %3d/%d  %.1fs" % (stack, i, len(fs), time.time() - t0), flush=True)
    np.save(out, cube)
    print("   %s cached %s  %s  %.1fs  %.0f MB"
          % (stack, tag, cube.shape, time.time() - t0, cube.nbytes / 1e6))
    return out


def drift_probe(stack, n_probe=None):
    """Span-1 adjacent-frame translation on a big central tile, plus direct long edges."""
    fs = L.frames(stack)
    n = len(fs) if n_probe is None else min(n_probe, len(fs))
    cy, cx = GH // 2, GW // 2
    crop = (cy - 384, cy + 384, cx - 384, cx + 384)
    prev = L.load_green(fs[0], crop)
    first = prev.copy()
    cum = np.zeros(2)
    mx = 0.0
    step_mags = []
    for k in range(1, n):
        cur = L.load_green(fs[k], crop)
        d = phase_shift(prev, cur)
        cum += d
        step_mags.append(np.hypot(*d))
        mx = max(mx, np.hypot(*cum))
        prev = cur
    direct = []
    for k in (n // 8, n // 4, n // 2, n - 1):
        cur = L.load_green(fs[k], crop)
        direct.append((k, phase_shift(first, cur)))
    return dict(n=n, cum=cum, cum_mag=float(np.hypot(*cum)), max_cum=mx,
                median_step=float(np.median(step_mags)), max_step=float(np.max(step_mags)),
                direct=direct)


if __name__ == "__main__":
    t0 = time.time()
    _ = L.load_green(L.frames("bee-1")[0])
    print("decode+extract one green plane: %.2f s  (299 frames => %.0f s)"
          % (time.time() - t0, 299 * (time.time() - t0)))

    print("\n=== drift probe (span-1 ladder = LOWER BOUND, fact 51) ===")
    for s in ("bee-1", "bee-2", "bee-3", "wrapped-text-1", "wrapped-text-2", "109MSDCF"):
        d = drift_probe(s)
        print("%-11s n=%d  median span-1 |d| = %.2f px  max span-1 = %.2f px"
              % (s, d["n"], d["median_step"], d["max_step"]))
        print("            cumulative span-1 = (%.1f, %.1f) = %.2f px, max excursion %.2f px"
              % (d["cum"][0], d["cum"][1], d["cum_mag"], d["max_cum"]))
        for k, dd in d["direct"]:
            print("            direct 0->%-4d = (%.1f, %.1f) = %.2f px" % (k, dd[0], dd[1], np.hypot(*dd)))
    print("\ntotal %.1f s" % (time.time() - t0))
