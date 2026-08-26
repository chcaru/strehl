"""BUILD-CHROMA's section 25 statistic, re-implemented so it can be run on ANY
master -- before and after a fix -- rather than only on ORCH's frozen file.

WHY RE-IMPLEMENT RATHER THAN REUSE. c15/c16 hard-code
`C:\\dev\\strehl-out\\ORCH-CADEF\\foam-caon.tif` as a module-level constant. A
before/after needs the same arithmetic pointed at two different files from ONE
binary's output, so the path has to be an argument. The arithmetic below is
copied from those two scripts deliberately; where it differs it is marked.

THE THREE CONTROLS c15 EARNED THE HARD WAY, KEPT AND STRENGTHENED:

  1. THE GATE MUST BITE. c15's v1 thresholded on fractions of 65535 when the
     master's max was 52239, removed zero pixels on all eight rows, and printed
     "the elevation survives". Every gate here is a PERCENTILE of this file's own
     luminance and every one asserts `removed > 0`.

  2. THE RANDOM CONTROL MUST VARY. v1's matched-count control kept every pixel
     and reported sd 0.000. Here the subsample is asserted to be a strict subset
     AND the sd over trials is asserted non-zero.

  3. DILATION, because a pixel adjacent to a blown one is contaminated through
     the gradient.

ADDED HERE, AND NOT IN c15/c16 -- section G. BUILD-CHROMA measured the defect in
OUTPUT DN, which is a tone-mapped, matrixed quantity. The ceiling that causes it
lives in white-balanced CAMERA space, where each channel has its OWN ceiling
(R 2.8654, G 1.0689, B 1.6305 in normalised units on the reference rig). Section
G inverts the matrix and reports u = v_c / ceil_c per level decile, so the level
axis of section C can be read against the ceiling that is supposed to explain it.
If B/G climbs with level while u stays far from 1, the ceiling is NOT reachable
post-merge and a post-merge level gate cannot be the fix.

Files passed on argv are opened read-only and never modified.
"""

import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import binary_dilation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import back_to_camera, ceilings, dump

NBANDS = 6
DROP_PCT = 0.76
DILATE = 3
TRIALS = 20
RNG = np.random.default_rng(20260826)


def bands(bg, rad, rmax, mask):
    out = []
    for i in range(NBANDS):
        lo, hi = i / NBANDS * rmax, (i + 1) / NBANDS * rmax
        m = mask & (rad >= lo) & (rad < hi)
        n = int(m.sum())
        out.append((n, float(bg[m].mean()) if n else float("nan")))
    return out


def main():
    path = sys.argv[1]
    tag = sys.argv[2] if len(sys.argv) > 2 else "h3"
    wb = [float(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else None

    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    assert a.ndim == 3 and a.shape[2] == 3, f"expected HxWx3, got {a.shape}"
    f = a.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    h, w = g.shape

    print("=" * 94)
    print(f"{tag}   {path}")
    print(f"   {w} x {h}")
    print("=" * 94)

    # ---------------------------------------------------------------- A
    print()
    print("A. PER-CHANNEL CEILINGS IN THE OUTPUT")
    mx = [float(f[..., c].max()) for c in range(3)]
    for c, n in enumerate("RGB"):
        near = float((f[..., c] >= 0.999 * mx[c]).mean() * 100)
        print(f"   {n}: max {mx[c]:8.0f} ({mx[c] / 65535 * 100:6.2f}% FS)   "
              f"within 0.999x of it: {near:.4f}%   "
              f"at 65535: {(f[..., c] >= 65535).mean() * 100:.4f}%")
    print(f"   B/G ceiling ratio {mx[2] / mx[1]:.4f}   R/G {mx[0] / mx[1]:.4f}")

    # ---------------------------------------------------------------- masks
    gy, gx = np.gradient(g)
    gm = np.hypot(gx, gy)
    strong = gm >= np.percentile(gm, 99.0)
    lum = f.max(axis=2)
    thr = float(np.percentile(lum, 100 - DROP_PCT))
    hot = strong & (lum >= thr)
    assert int(hot.sum()) > 0, "no hot edge pixels; the statistic is undefined"

    # ---------------------------------------------------------------- B
    print()
    print(f"B. HUE CONSISTENCY among {int(hot.sum()):,} hot edge pixels "
          f"(top {DROP_PCT}% of luminance, >= {thr:.0f} DN)")
    sb = ((b - g) / np.maximum(g, 1.0))[hot]
    sr = ((r - g) / np.maximum(g, 1.0))[hot]
    frac_b = float((sb > 0).mean())
    for nm, hh in (("B-G", sb), ("R-G", sr)):
        print(f"   {nm}: positive on {(hh > 0).mean() * 100:5.1f}%   "
              f"mean {hh.mean():+.4f}   median {np.median(hh):+.4f}")

    # ---------------------------------------------------------------- C
    print()
    print("C. IS B/G A MONOTONE FUNCTION OF LEVEL?  (deciles of the hot set)")
    lv = lum[hot]
    rb = (b / np.maximum(g, 1.0))[hot]
    q = np.quantile(lv, np.linspace(0, 1, 11))
    means = []
    for i in range(10):
        m = (lv >= q[i]) & (lv <= q[i + 1])
        means.append(float(rb[m].mean()))
        print(f"     decile {i}  DN {q[i]:6.0f}-{q[i + 1]:6.0f}   B/G {means[-1]:.4f}")
    rises = int(sum(means[i + 1] > means[i] for i in range(9)))
    spread = means[-1] / means[0]
    print(f"   monotone rising on {rises}/9 steps, {means[0]:.4f} -> {means[-1]:.4f} "
          f"({(spread - 1) * 100:+.1f}%)")

    # ---------------------------------------------------------------- D
    yy, xx = np.mgrid[0:h, 0:w]
    rad = np.hypot(yy - (h - 1) / 2.0, xx - (w - 1) / 2.0)
    rmax = float(rad.max())
    bg = np.abs(b - g) / np.maximum(g, 1.0)
    print()
    print("D. UNGATED RADIAL BAND TABLE  (|B-G|/G on strong green edges)")
    base = bands(bg, rad, rmax, strong)
    for i, (n, v) in enumerate(base):
        tagl = "   <- centre" if i == 0 else ("   <- corner" if i == NBANDS - 1 else "")
        print(f"     band {i}  edges {n:>8,}  |B-G|/G {v:.4f}{tagl}")
    base_ratio = base[-1][1] / base[0][1]
    print(f"   corner/centre = {base_ratio:.3f}")

    # ---------------------------------------------------------------- E
    print()
    print(f"E. LEVEL GATE -- drop the top {DROP_PCT}% of luminance, dilated {DILATE}")
    n_base = int(strong.sum())
    hotd = binary_dilation(lum >= thr, iterations=DILATE)
    kept = strong & ~hotd
    removed = n_base - int(kept.sum())
    # CONTROL 1: the gate must actually do something.
    assert removed > 0, (
        f"GATE INERT: removed 0 of {n_base:,} edge pixels at threshold {thr:.0f} "
        f"(image max {lum.max():.0f}). This is c15-v1's failure; refusing to "
        f"report a pass.")
    bb = bands(bg, rad, rmax, kept)
    assert not any(n == 0 for n, _ in bb), "a radial band emptied; not interpretable"
    gated_ratio = bb[-1][1] / bb[0][1]
    print(f"   kept {int(kept.sum()):,}   removed {removed:,} "
          f"({removed / n_base * 100:.2f}% of edges)   THE GATE BIT.")
    print(f"   centre {bb[0][1]:.4f}   corner {bb[-1][1]:.4f}   "
          f"corner/centre = {gated_ratio:.3f}")

    # ---------------------------------------------------------------- F
    print()
    print(f"F. CONTROL -- matched-count RANDOM removal, {TRIALS} trials")
    idx = np.flatnonzero(strong.ravel())
    ratios = []
    for _ in range(TRIALS):
        drop = RNG.choice(idx, size=removed, replace=False)
        m = strong.copy().ravel()
        m[drop] = False
        # CONTROL 2a: the subsample must be a STRICT subset.
        assert int(m.sum()) == n_base - removed, "random control removed nothing"
        bbr = bands(bg, rad, rmax, m.reshape(h, w))
        if any(n == 0 for n, _ in bbr):
            continue
        ratios.append(bbr[-1][1] / bbr[0][1])
    ratios = np.array(ratios)
    # CONTROL 2b: a control that never varies has never been shown to work.
    assert ratios.std() > 0.0, "random control sd is 0.000 -- it is not resampling"
    sep = abs(ratios.mean() - gated_ratio) / ratios.std()
    print(f"   random  {ratios.mean():.3f} +/- {ratios.std():.3f}   "
          f"level gate {gated_ratio:.3f}   separation {sep:.1f} sd")

    # ---------------------------------------------------------------- G
    print()
    print("G. THE SAME DECILES IN WHITE-BALANCED CAMERA SPACE (added by BUILD-HIGHLIGHT)")
    ceil = ceilings(wb)
    cam = back_to_camera(a)
    u = cam / ceil[None, None, :]
    umax = np.max(u, axis=2)
    clamped = (f >= 65535).any(axis=2)
    print(f"   ceilings  R {ceil[0]:.4f}  G {ceil[1]:.4f}  B {ceil[2]:.4f}   "
          f"(post-matrix clamp fires on {clamped.mean() * 100:.4f}% of the frame)")
    print(f"     {'decile':>7} {'DN':>15} {'u_R':>7} {'u_G':>7} {'u_B':>7} "
          f"{'u_max':>7} {'clamp%':>8}")
    uq = []
    for i in range(10):
        m = (lum >= q[i]) & (lum <= q[i + 1]) & hot
        uq.append(float(umax[m].mean()))
        print(f"     {i:7d} {q[i]:7.0f}-{q[i + 1]:6.0f} "
              f"{u[..., 0][m].mean():7.4f} {u[..., 1][m].mean():7.4f} "
              f"{u[..., 2][m].mean():7.4f} {umax[m].mean():7.4f} "
              f"{clamped[m].mean() * 100:7.3f}%")
    # CONTROL 3: a scale error in the inversion would silently report u ~ 0 and
    # make every ceiling look unreachable. The hot set is the top 0.76% of the
    # frame; if it is not at least a hundredth of a ceiling, the units are wrong.
    assert umax[hot].mean() > 0.01, (
        f"u_max over the hot set is {umax[hot].mean():.6f} -- the inversion is "
        f"in the wrong units, so section G is void")
    print(f"   u_max over the hot set: mean {umax[hot].mean():.4f}  "
          f"p99 {np.percentile(umax[hot], 99):.4f}  max {umax[hot].max():.4f}")

    dump(tag, {
        "path": path, "shape": [h, w],
        "max": mx, "bg_ceiling_ratio": mx[2] / mx[1],
        "frac_b_positive": frac_b,
        "bg_by_decile": means, "monotone_steps": rises, "bg_spread": spread,
        "ungated_corner_centre": base_ratio,
        "gated_corner_centre": gated_ratio,
        "gate_removed": removed,
        "random_mean": float(ratios.mean()), "random_sd": float(ratios.std()),
        "separation_sd": float(sep),
        "umax_by_decile": uq,
        "umax_hot_mean": float(umax[hot].mean()),
        "umax_hot_max": float(umax[hot].max()),
        "clamped_frac": float(clamped.mean()),
    })


if __name__ == "__main__":
    main()
