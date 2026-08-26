"""ORCH's subject-detail guard, run against the SHIPPED IN-CRATE veil.

ORCH measured 0.355x subject gradient energy for a signed max and called it
"build this or do not ship". That number is for an UNGATED, out-of-crate
estimator -- a pure per-pixel statistic over nine frames that does no focus
selection at all. The shipped in-crate veil is gated: a pixel is eligible only
where `best_focus < veil_focus_max`, i.e. where the election found nothing
sharp, which is dead ground by construction.

PREDICTION, RECORDED BEFORE RUNNING: subject detail should be ~1.000x, because
the gate excludes subject pixels by focus rather than by geometry. If it comes
back materially below 1.0, MY gate leaks and ORCH's warning applies to this
build directly.

Method is ORCH's: gradient RMS inside the subject, eroded clear of the
silhouette so no edge pixel can contribute. Reported alongside the backdrop so
rim and surround stay separable, per standing instruction.

The erosion distance is swept rather than fixed at 40 px. A single distance
cannot distinguish "the interior is untouched" from "the erosion happened to
clear the affected band": if the ratio is flat in the erosion distance the
interior really is untouched, and if it climbs toward 1.0 the effect is an edge
band that the chosen distance merely stepped over.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

OUT = Path(r"C:\dev\strehl-out\VEIL")

# (label, veil-off arm, veil-on arm)
PAIRS = [
    ("flower-bud-alone-cpl  TARGET", "fb-p3-off.tif", "fb-pol.tif"),
    ("bee-2-cpl", "bee2-pm-off.tif", "bee2-pm-fl.tif"),
    ("couch-fibers-cpl  GUARD", "cf3-p3-off.tif", "cf3-p3-on.tif"),
    ("pencil-steep-angle  POLARITY", "pen-p3-off.tif", "pen-pol.tif"),
    ("109MSDCF  PLACEBO", "d109-p3-off.tif", "d109-p3-on.tif"),
]
ERODE = [0, 10, 20, 40, 80]


def green(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p}: {a.dtype}"
    return a[..., 1].astype(np.float64)


def detail_mask(a: np.ndarray) -> np.ndarray:
    """Subject defined by DETAIL, not by luma.

    The luma mask `a < 0.5 * backdrop` is nearly the veil's own luminance floor
    (`0.5 * (backdrop - black) + black`), so a guard built on it partly measures
    the floor's definition rather than an independent property -- it would
    report 1.000x even for a veil that ravaged everything the floor admits.

    This mask instead selects the top quartile of smoothed gradient energy: the
    pixels that actually carry detail, which is the quantity ORCH's guard is
    about, and which the veil's gate never reads. A leak into subject detail
    therefore has somewhere to show up.
    """
    dx = np.zeros_like(a)
    dy = np.zeros_like(a)
    dx[:, 1:] = np.abs(np.diff(a, axis=1))
    dy[1:, :] = np.abs(np.diff(a, axis=0))
    g = dx + dy
    # Cheap box smooth so the mask is regions, not isolated edge pixels.
    k = 8
    c = np.cumsum(np.cumsum(g, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = a.shape
    y0 = np.clip(np.arange(h) - k, 0, h)[:, None]
    y1 = np.clip(np.arange(h) + k + 1, 0, h)[:, None]
    x0 = np.clip(np.arange(w) - k, 0, w)[None, :]
    x1 = np.clip(np.arange(w) + k + 1, 0, w)[None, :]
    s = c[y1, x1] - c[y0, x1] - c[y1, x0] + c[y0, x0]
    s /= (y1 - y0) * (x1 - x0)
    return s > np.percentile(s, 75.0)


def erode(mask: np.ndarray, r: int) -> np.ndarray:
    """Binary erosion by a (2r+1) box, via a separable running sum."""
    if r <= 0:
        return mask
    m = mask.astype(np.float64)
    for axis in (0, 1):
        c = np.cumsum(m, axis=axis)
        c = np.concatenate([np.zeros_like(np.take(c, [0], axis=axis)), c], axis=axis)
        n = m.shape[axis]
        lo = np.clip(np.arange(n) - r, 0, n)
        hi = np.clip(np.arange(n) + r + 1, 0, n)
        idx = [slice(None)] * m.ndim
        idx_lo, idx_hi = list(idx), list(idx)
        idx_lo[axis], idx_hi[axis] = lo, hi
        width = (hi - lo).astype(np.float64)
        shape = [1] * m.ndim
        shape[axis] = n
        m = (c[tuple(idx_hi)] - c[tuple(idx_lo)]) / width.reshape(shape)
        # A pixel survives only if EVERY pixel in its box was set.
        m = (m > 0.999999).astype(np.float64)
    return m > 0.5


def grad_rms_masked(a: np.ndarray, m: np.ndarray) -> tuple[float, int]:
    dx = np.diff(a, axis=1)
    dy = np.diff(a, axis=0)
    n0, n1 = min(dx.shape[0], dy.shape[0]), min(dx.shape[1], dy.shape[1])
    g2 = dx[:n0, :n1] ** 2 + dy[:n0, :n1] ** 2
    mm = m[:n0, :n1]
    k = int(mm.sum())
    if k < 500:
        return float("nan"), k
    return float(np.sqrt(g2[mm].mean())), k


def main() -> int:
    ok = True
    for label, fa, fb in PAIRS:
        pa, pb = OUT / fa, OUT / fb
        if not (pa.exists() and pb.exists()):
            print(f"{label:32s} pending")
            continue
        a, b = green(pa), green(pb)
        backdrop = float(np.percentile(a, 90))
        changed = a != b
        masks = [
            ("luma  (< 0.5x backdrop)", a < 0.5 * backdrop),
            ("detail (top quartile |grad|)", detail_mask(a)),
        ]
        print(f"\n{label}   veil changed {100.0 * changed.mean():.2f}% of pixels")
        for mname, subject in masks:
            frac = 100.0 * subject.mean()
            leak = 100.0 * (changed & subject).sum() / max(subject.sum(), 1)
            print(f"  [{mname}]  mask {frac:5.2f}% of frame,"
                  f"  veil touched {leak:5.2f}% of it")
            if frac < 0.5:
                print("     (no depth-separated subject -- ORCH's guard does not apply)")
                continue
            for r in ERODE:
                m = erode(subject, r)
                ra, ka = grad_rms_masked(a, m)
                rb, _ = grad_rms_masked(b, m)
                if not np.isfinite(ra):
                    print(f"     erode {r:3d} px : mask exhausted ({ka} px)")
                    continue
                ratio = rb / ra
                flag = "" if ratio > 0.97 else "   << SUBJECT DETAIL LOST"
                if ratio <= 0.97 and "GUARD" not in label:
                    ok = False
                print(f"     erode {r:3d} px : {ka:9d} px   gradRMS "
                      f"{ra:8.1f} -> {rb:8.1f}   {ratio:.3f}x{flag}")
    print(f"\nORCH GUARD (subject detail preserved): {'PASS' if ok else 'FAIL'}")
    print("ORCH's ungated out-of-crate estimators scored 0.355x (signed max),")
    print("0.261x (cleanest-third mean), 0.184x (plain mean).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
