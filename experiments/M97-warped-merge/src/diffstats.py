"""P3 and the opportunity guard.

P3  -- no NaN and no black rim, whole frame, stated as a fraction of ALL
       pixels. A 16-bit TIFF cannot hold a NaN, so the NaN question is really
       "did a NaN reach the accumulator and come out as a zero or a wrapped
       value"; the check is therefore on exact zeros and on the black rim the
       uncovered border would produce, measured radially so a rim cannot hide
       in a whole-frame average.

GUARD -- the pre-registered risk. If two renders barely differ, a null between
       them says nothing about registration. This reports how much of the image
       registration actually moved.

Usage: diffstats.py <out.json> <label>=<path> ...
"""

import json
import sys

import numpy as np
import tifffile


def load(path: str) -> np.ndarray:
    """Read at true bit depth. Pillow truncates 16-bit RGB TIFF to 8 bits."""
    return tifffile.imread(path)


def rim_profile(g: np.ndarray, nbins: int = 8) -> list[float]:
    """Fraction of exactly-zero pixels in normalised-radius annuli."""
    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    r = np.sqrt(((yy - cy) / cy) ** 2 + ((xx - cx) / cx) ** 2)
    r /= r.max()
    out = []
    for b in range(nbins):
        m = (r >= b / nbins) & (r < (b + 1) / nbins)
        out.append(float((g[m] == 0).mean()))
    return out


def main() -> None:
    dst = sys.argv[1]
    specs = [s.split("=", 1) for s in sys.argv[2:]]
    imgs = {}
    recs = []
    for label, path in specs:
        a = load(path)
        imgs[label] = a
        g = a[..., 1] if a.ndim == 3 else a
        total = g.size
        rec = {
            "label": label,
            "path": path,
            "dtype": str(a.dtype),
            "shape": list(a.shape),
            "min": int(a.min()),
            "max": int(a.max()),
            "frac_exact_zero": float((g == 0).mean()),
            "frac_below_1pct": float((g < 655).mean()),
            "n_exact_zero": int((g == 0).sum()),
            "total_px": int(total),
            "rim_zero_by_radius": rim_profile(g),
            "nonfinite_after_float": int(np.count_nonzero(~np.isfinite(g.astype(np.float64)))),
        }
        recs.append(rec)
        print(
            f"{label:18s} zero {rec['frac_exact_zero']*100:8.5f}%  "
            f"outer-annulus zero {rec['rim_zero_by_radius'][-1]*100:8.5f}%  "
            f"min {rec['min']:5d} max {rec['max']:5d}",
            flush=True,
        )

    print()
    pairs = []
    labels = [s[0] for s in specs]
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            a, b = imgs[labels[i]], imgs[labels[j]]
            if a.shape != b.shape:
                continue
            af, bf = a.astype(np.float64), b.astype(np.float64)
            d = np.abs(af - bf)
            p = {
                "a": labels[i],
                "b": labels[j],
                "frac_differing": float((d > 0).mean()),
                "mean_abs_diff": float(d.mean()),
                "p99_abs_diff": float(np.percentile(d, 99)),
            }
            pairs.append(p)
            print(
                f"{p['a']:18s} vs {p['b']:18s}  differing {p['frac_differing']*100:7.3f}%  "
                f"mean|d| {p['mean_abs_diff']:9.2f}  p99 {p['p99_abs_diff']:9.2f}  (of 65535)",
                flush=True,
            )

    with open(dst, "w", encoding="utf-8") as fh:
        json.dump({"images": recs, "pairs": pairs}, fh, indent=2)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    main()
