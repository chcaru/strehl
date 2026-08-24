"""Compare two renders on MATCHED CONTENT, which is the only way this is valid.

WHY EVERY EARLIER ATTEMPT WAS INADMISSIBLE, INCLUDING MINE. Registration
changes the rendered field of view: an aligned render sits in the reference
frame's field of view, an unregistered one blends the fields of view of frames
spanning 23.9% of magnification. So comparing two arms AT THE SAME PIXEL
COORDINATE compares different scene content. My own radial4.py reported GAINED
at 24.5x ZOOMNULL in the outer band; looking at the image showed the outer band
holds bristles in one arm and smooth white barrel in the other. That is a
content shift wearing a sharpness ratio's clothes, and it is the same class of
error as M86's fake 1.4565x.

WHAT THIS DOES INSTEAD. Recover the similarity between the two renders by the
same FFT/NCC scale ladder used to measure the ground-truth drift, then bring
BOTH arms onto a common intermediate grid -- A magnified by sqrt(s), B by
1/sqrt(s) -- so each pays exactly one resampling of equal magnitude. Comparing
a resampled arm against an untouched one would hand the untouched one a
sharpness win for free; this is why the split is symmetric.

Sharpness is then gradient energy on the common valid region. That functional
is only trusted because it is scored against a planted blur (below) and against
a graded registration dose measured independently by signtest.py.
"""

import json
import sys

import numpy as np
import tifffile
from scipy.ndimage import binary_erosion, gaussian_filter, map_coordinates


def load(path: str) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    return (a[:, :, 1] if a.ndim == 3 else a).astype(np.float64)


def block(a: np.ndarray, f: int) -> np.ndarray:
    h, w = (a.shape[0] // f) * f, (a.shape[1] // f) * f
    return a[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))


def ncc(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    if d == 0:
        return 0.0
    c = np.fft.irfft2(np.fft.rfft2(a) * np.conj(np.fft.rfft2(b)), s=a.shape)
    return float(c.max() / d)


def scale_about_centre(a: np.ndarray, s: float, order: int = 3) -> np.ndarray:
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    return map_coordinates(a, [(yy - cy) * s + cy, (xx - cx) * s + cx],
                           order=order, mode="constant", cval=np.nan)


def find_scale(a: np.ndarray, b: np.ndarray) -> tuple[float, float, bool]:
    """Magnification to apply to b so it matches a. Bounds are hard and a hit
    is reported: an earlier version of this ladder walked outside its bracket
    and returned one identical value for four unrelated subjects."""
    LO, HI = 0.70, 1.45
    lo, hi = LO, HI
    best = (1.0, -1.0)
    A, B = block(a, 4), block(b, 4)
    for _ in range(4):
        for s in np.linspace(lo, hi, 15):
            v = ncc(A, np.nan_to_num(scale_about_centre(B, 1.0 / s, order=1),
                                     nan=float(B.mean())))
            if v > best[1]:
                best = (float(s), v)
        span = (hi - lo) / 7.0
        lo, hi = max(LO, best[0] - span), min(HI, best[0] + span)
    step = (hi - lo) / 14.0
    return best[0], best[1], abs(best[0] - LO) < step or abs(best[0] - HI) < step


def energy(a: np.ndarray) -> np.ndarray:
    gy = np.zeros_like(a)
    gx = np.zeros_like(a)
    gy[:-1, :] = np.diff(a, axis=0)
    gx[:, :-1] = np.diff(a, axis=1)
    return gy * gy + gx * gx


def compare(a: np.ndarray, b: np.ndarray, label: str) -> dict:
    s, v, railed = find_scale(a, b)
    r = np.sqrt(s)
    # A is shrunk by sqrt(s), B magnified by sqrt(s): both land on the same
    # intermediate grid having each been resampled once, by equal amounts.
    A = scale_about_centre(a, r)
    B = scale_about_centre(b, 1.0 / r)
    m = np.isfinite(A) & np.isfinite(B) & (A > 0) & (B > 0)
    m = binary_erosion(m, np.ones((49, 49), bool))
    A = np.where(m, A, 0.0)
    B = np.where(m, B, 0.0)
    ea, eb = energy(A), energy(B)

    h, w = A.shape
    yy, xx = np.mgrid[0:h, 0:w]
    rad = np.hypot(yy - (h - 1) / 2.0, xx - (w - 1) / 2.0)
    rad /= rad.max()

    resid = float(ncc(block(np.where(m, A, A[m].mean()), 4),
                      block(np.where(m, B, B[m].mean()), 4)))
    print(f"\n--- {label} ---")
    print(f"  matched at magnification {s:.5f} (ncc {v:.4f}, railed={railed}); "
          f"mask keeps {100 * m.mean():.2f}%")
    print(f"  post-match ncc {resid:.4f}")
    bands = []
    for lo, hi in ((0.0, 0.35), (0.35, 0.70), (0.70, 1.01)):
        q = m & (rad >= lo) & (rad < hi)
        if q.sum() < 1000:
            continue
        ratio = float(ea[q].mean() / eb[q].mean())
        bands.append(dict(lo=lo, hi=hi, n=int(q.sum()), ratio=ratio))
        print(f"    r {lo:.2f}-{hi:.2f}  n={q.sum():>8}  A/B sharpness {ratio:.4f}")
    return dict(label=label, scale=s, ncc=v, railed=railed,
                post_ncc=resid, mask=float(m.mean()), bands=bands)


def main(argv: list[str]) -> int:
    out, base = argv[1], argv[2]
    arms = {n: load(rf"{base}\marker-{n}.tif")
            for n in ("UNALIGNED", "ZOOMNULL", "ALIGNED", "GAINED", "JITTER")}

    # PLANT FIRST. An arm against a deliberately blurred copy of itself must
    # read clearly above 1.0, or the functional cannot see softness at all and
    # nothing below it is admissible.
    z = arms["ZOOMNULL"]
    print("=== CONTROLS ===")
    ctl = [compare(z, z, "PLACEBO ZOOMNULL vs itself (want ratio 1.0000)"),
           compare(z, gaussian_filter(z, 1.0),
                   "PLANT ZOOMNULL vs itself blurred sigma=1.0 (want >> 1)")]

    print("\n=== TREATMENT (A/B > 1 means A is sharper) ===")
    res = [compare(arms["GAINED"], arms["ZOOMNULL"], "GAINED vs ZOOMNULL (89.5% of drift removed)"),
           compare(arms["ALIGNED"], arms["ZOOMNULL"], "ALIGNED vs ZOOMNULL (33.3%, as shipped)"),
           compare(arms["UNALIGNED"], arms["ZOOMNULL"], "UNALIGNED vs ZOOMNULL (0%, resampling only)"),
           compare(arms["GAINED"], arms["JITTER"], "GAINED vs JITTER (plant: 8.855 px added)")]

    with open(out, "w", encoding="utf-8") as fh:
        json.dump(dict(controls=ctl, treatments=res), fh, indent=2)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
