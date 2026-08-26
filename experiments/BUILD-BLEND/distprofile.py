"""Where, in distance from a silhouette, do the two arms actually differ?

ORCH's correction (update 1) makes this the load-bearing check on my arm.
`STREHL_ONLY_FRAME` showed that across 470 px of backdrop the arms `off`, `on`,
`frame000` and `frame298` are superimposed within noise, all rising ~4%. Two of
those contain no election at all, so that 4% is the scene's own illumination
field. The operative conclusion was stated plainly:

    the merge departs from the single-frame reference ONLY within ~10-20 px of
    the silhouette ... anything that "fixes" the backdrop further out than
    ~20 px is editing the scene's real illumination gradient out of the
    photograph. Do not do that.

So a multi-band merge that removed the rim by quietly lifting the whole
backdrop would be a WORSE outcome than the rim, and a whole-frame statistic
cannot tell the two apart. This bins the difference between the arms by
distance from the silhouette, so a broad backdrop edit and a confined rim fix
have different signatures and cannot be confused.

The silhouette is defined from the CONTROL frame's own content -- the gradient
of a heavily blurred luma -- and never from the difference between the arms,
which would be circular.

`SUPPORT_RADIUS = SOBEL_RADIUS(1) + WINDOW_RADIUS(13) = 14 px` in `focus.rs`
is the shipped merge's own support, so the predicted rim zone is ~14 px and the
bins straddle it.

A flat exposure difference between the arms would raise every bin at once, so
each bin reports the difference BOTH raw and after the global gain is divided
out. The two columns disagreeing is itself the diagnosis.

    python distprofile.py <label> <control.tiff> <blend.tiff>
    python distprofile.py --commission <control.tiff>
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, gaussian_filter

BINS = [(0, 5), (5, 10), (10, 20), (20, 40), (40, 80), (80, 160), (160, 10**9)]
EDGE_PCTL = 99.0     # the strongest 1% of coarse gradient magnitude is "silhouette"
SIGMA = 8.0          # coarse: depth boundaries, not texture


def read16(path: Path) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path} is {a.dtype}, expected uint16"
    assert a.ndim == 3 and a.shape[2] == 3, f"{path} has shape {a.shape}, expected HxWx3"
    return a


def luma(a: np.ndarray) -> np.ndarray:
    f = a.astype(np.float32)
    return 0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1] + 0.0722 * f[:, :, 2]


def silhouette_distance(ctrl: np.ndarray) -> np.ndarray:
    """Distance in px to the nearest strong COARSE luma edge of the control."""
    sm = gaussian_filter(ctrl, SIGMA)
    gy, gx = np.gradient(sm)
    mag = np.hypot(gx, gy)
    thr = np.percentile(mag, EDGE_PCTL)
    return distance_transform_edt(mag < thr).astype(np.float32)


def robust_gain(ctrl: np.ndarray, blend: np.ndarray) -> tuple[float, float]:
    """Median blend/ctrl over UNCLIPPED, non-black pixels.

    The mean ratio is not usable here. This arm carries no photometric
    normalisation, so it sits at a slightly different linear exposure, and on a
    subject with a large bright backdrop that backdrop is near the saturation
    ceiling and cannot move. A mean ratio therefore averages a compressed
    region with an uncompressed one and UNDER-ESTIMATES the true gain, which
    leaves a residue in every distance bin and makes a purely global exposure
    difference look like a broad backdrop edit.

    That is not hypothetical: it is exactly the reading this script produced
    before this function existed. The median over pixels that are free to move
    is the estimator that does not have that failure.

    Returns (gain, fraction of pixels excluded as clipped).
    """
    hi = 60000.0
    lo = 1000.0
    m = (ctrl > lo) & (ctrl < hi) & (blend > lo) & (blend < hi)
    clipped = 1.0 - float(m.mean())
    if m.sum() < 1000:
        return float(blend.mean() / ctrl.mean()), clipped
    return float(np.median(blend[m] / ctrl[m])), clipped


def profile(label: str, ctrl: np.ndarray, blend: np.ndarray) -> list[tuple]:
    dist = silhouette_distance(ctrl)
    gain, clipped = robust_gain(ctrl, blend)
    raw = blend - ctrl
    degained = blend / gain - ctrl

    rows = []
    for lo, hi in BINS:
        m = (dist >= lo) & (dist < hi)
        n = int(m.sum())
        if n == 0:
            continue
        sat = float(((ctrl[m] >= 60000.0) | (blend[m] >= 60000.0)).mean())
        rows.append((
            lo, hi, n, 100.0 * n / dist.size,
            float(ctrl[m].mean()),
            float(np.sqrt(np.mean(raw[m] ** 2))),
            float(np.sqrt(np.mean(degained[m] ** 2))),
            float(degained[m].mean()),
            100.0 * sat,
        ))
    return rows, (gain, clipped)


def show(label: str, rows: list[tuple], gaininfo: tuple[float, float]) -> None:
    gain, clipped = gaininfo
    print(f"=== {label} ===")
    print(f"  silhouette = strongest {100-EDGE_PCTL:.0f}% of coarse (sigma {SIGMA:.0f} px) "
          f"luma gradient in the CONTROL, not in the difference")
    print(f"  global gain blend/ctrl = {gain:.4f}  (ROBUST median over unclipped "
          f"pixels; {100*clipped:.1f}% of the frame excluded as clipped or black)")
    print()
    print(f"  {'dist px':>10} {'% frame':>8} {'ctrl mean':>10} "
          f"{'RMS diff':>10} {'RMS degained':>13} {'mean degained':>14} {'sat%':>6}")
    print(f"  {'-'*10} {'-'*8} {'-'*10} {'-'*10} {'-'*13} {'-'*14} {'-'*6}")
    for lo, hi, n, pct, cm, rr, rd, md, sat in rows:
        span = f"{lo}-{hi}" if hi < 10**8 else f"{lo}+"
        print(f"  {span:>10} {pct:>7.1f}% {cm:>10.1f} {rr:>10.1f} {rd:>13.1f} "
              f"{md:>+14.1f} {sat:>5.1f}%")
    print()
    if len(rows) >= 3:
        near = rows[0][6]
        far = rows[-1][6]
        ratio = f"{near/far:.2f}x" if far > 1e-9 else "n/a (far bin is exactly 0)"
        print(f"  near ({rows[0][0]}-{rows[0][1]} px) / far ({rows[-1][0]}+ px) "
              f"degained RMS ratio = {ratio}")
        print(f"  A CONFINED fix is a large ratio. A backdrop EDIT is a ratio near 1.")
    print()


def commission(src: Path) -> int:
    """A null and a planted rim. Both must read as designed or nothing is admissible."""
    l = luma(read16(src))
    print(f"commissioning distprofile.py on {src.name}  ({l.shape[1]} x {l.shape[0]} px)")
    print()
    ok = True

    rows, gain = profile("null", l, l.copy())
    zero = all(abs(r[5]) < 1e-6 and abs(r[6]) < 1e-6 for r in rows)
    print("NULL -- control against itself; every difference must be 0")
    show("NULL (control vs itself)", rows, gain)
    print(f"  {'PASS' if zero else '*** FAIL -- a null must be exactly zero'}")
    ok &= zero
    print()

    # POSITIVE CONTROL: a rim confined to <=14 px of the silhouette, the shipped
    # merge's own SUPPORT_RADIUS. The probe must localise it to the near bins.
    dist = silhouette_distance(l)
    planted = l.copy()
    rim = (dist > 0) & (dist <= 14)
    planted[rim] += 900.0
    rows_p, gain_p = profile("planted", l, planted)
    # The gate reads the RAW column for localisation. The de-gained column
    # cannot be used for this control: the plant itself lifts the global mean
    # by 0.06%, and dividing that out necessarily leaves a level-proportional
    # residue in every bin. That residue is the normalisation working, not the
    # probe failing, and gating on it would condemn a probe that is correct.
    # The de-gained column is commissioned separately, by requiring that it
    # still SEPARATES near from far.
    raw_near, raw_far = rows_p[0][5], rows_p[-1][5]
    deg_near, deg_far = rows_p[0][6], rows_p[-1][6]
    localised = raw_near > 100.0 and raw_far < 1.0
    # deg_far == 0 is PERFECT separation, not a failure. With the robust
    # estimator the plant does not move the median gain at all, so the
    # de-gained far field is exactly zero. An earlier version of this gate
    # required deg_far > 0 and therefore failed the probe precisely when it
    # was working perfectly.
    sep_ratio = float("inf") if deg_far <= 1e-9 else deg_near / deg_far
    separates = sep_ratio > 5.0
    print("POSITIVE CONTROL -- a +900 DN rim planted within 14 px of the silhouette")
    show("PLANTED RIM (confined to <=14 px)", rows_p, gain_p)
    print(f"  raw: near RMS {raw_near:.1f} must be > 100, far RMS {raw_far:.4f} must be < 1")
    print(f"       {'PASS -- the probe localises a rim it was not told about' if localised else '*** FAIL -- probe cannot localise a known rim'}")
    print(f"  de-gained: near/far {sep_ratio:.1f}x must be > 5")
    print(f"       {'PASS -- normalisation preserves the localisation' if separates else '*** FAIL -- normalisation destroys the localisation'}")
    ok &= localised and separates
    print()

    print("COMMISSIONED -- distprofile readings are admissible" if ok
          else "*** NOT COMMISSIONED -- withdraw every distprofile number")
    return 0 if ok else 1


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--commission":
        return commission(Path(sys.argv[2]))
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    label, cp, bp = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    lc, lb = luma(read16(cp)), luma(read16(bp))
    assert lc.shape == lb.shape, f"shape mismatch {lc.shape} vs {lb.shape}"
    rows, gain = profile(label, lc, lb)
    show(label, rows, gain)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
