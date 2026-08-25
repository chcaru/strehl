"""Read the per-frame log-scale ladder out of a warpmap sidecar and ask whether
it is physically admissible.

Why this test exists
--------------------
Focus breathing is a property of the lens: as the focus group moves, the
magnification changes. Over a focus bracket the focus group moves in ONE
direction, monotonically, so the magnification must also change monotonically.
A fitted per-frame log-scale ladder `g_k` is therefore only admissible if it is
monotone in k, up to measurement noise.

That gives a free, model-independent error estimator. Decompose the ladder into
a smooth monotone trend plus a residual:

    g_k = trend_k + wobble_k

`trend` is the physics. `wobble` is fit error, and every bit of it is applied to
the image at render time as a spurious magnification. A wobble of w in log-scale
displaces a feature at radius r by w * r pixels, so the ladder's own roughness
converts directly into a predicted pixel disagreement at the frame edge --
which is exactly the quantity `ghost.py` measures independently on the pixels.
If the two agree, the mechanism is established.

The trend is estimated with an isotonic (monotone least-squares) fit rather than
a polynomial, because it must not assume a functional form for breathing. The
pool-adjacent-violators algorithm gives the exact L2-optimal monotone fit.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np


def read_ladder(path: Path):
    """Pull (index, g, rot, dx, dy) per frame out of the text sidecar.

    Row format is `<idx> placed <hex a_re a_im b_re b_im> # g=... rot=... dx=...`.
    Only the trailing comment is parsed; the sidecar's own header warns that the
    decimals there are a human aid, so this is a diagnostic-grade read of a
    field the renderer takes from the f64 bit patterns. The comment carries ~7
    significant figures, which is far finer than the effect being measured
    (wobble of order 1e-4), so the truncation is not load-bearing here.

    Per the header legend `| scale-1, rot, dx, dy`, `g` is (scale - 1), not a
    log-scale. A feature at radius r is therefore displaced by exactly g * r px.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("strehl-warpmap"):
        raise SystemExit(f"{path} is not a warpmap sidecar")
    rows = []
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s+(\w+)\s", line)
        if m is None or "g=" not in line:
            continue
        if m.group(2) != "placed":          # unplaced frames carry no geometry
            continue
        nums = dict(re.findall(r"\b([a-z_]+)=([-+]?[\d.]+(?:[eE][-+]?\d+)?)", line))
        if "g" not in nums:
            continue
        rows.append((int(m.group(1)), float(nums["g"]),
                     float(nums.get("rot", "nan")),
                     float(nums.get("dx", "nan")), float(nums.get("dy", "nan"))))
    if not rows:
        raise SystemExit(f"{path}: parsed no frame rows -- format changed?")
    rows.sort()
    a = np.array(rows, dtype=float)
    return a[:, 0].astype(int), a[:, 1], a[:, 2], a[:, 3], a[:, 4]


def isotonic(y: np.ndarray) -> np.ndarray:
    """Exact L2 monotone (non-increasing or non-decreasing) fit, PAVA."""
    best = None
    for sign in (+1.0, -1.0):
        v = sign * y
        # Pool adjacent violators for a non-decreasing fit of v.
        vals = list(v.astype(float))
        wts = [1.0] * len(vals)
        i = 0
        while i < len(vals) - 1:
            if vals[i] > vals[i + 1] + 0.0:
                tot = wts[i] + wts[i + 1]
                vals[i] = (vals[i] * wts[i] + vals[i + 1] * wts[i + 1]) / tot
                wts[i] = tot
                del vals[i + 1], wts[i + 1]
                if i > 0:
                    i -= 1
            else:
                i += 1
        fit = np.repeat(np.array(vals), [int(round(w)) for w in wts])
        fit = sign * fit[: len(y)]
        rss = float(np.sum((y - fit) ** 2))
        if best is None or rss < best[0]:
            best = (rss, fit)
    return best[1]


def report(name: str, k, g, r_max: float, span: int) -> dict:
    trend = isotonic(g)
    wob = g - trend
    rms = float(np.sqrt(np.mean(wob ** 2)))
    # Frame-to-frame roughness at the span the merge actually elects across.
    d = g[span:] - g[:-span]
    dt = trend[span:] - trend[:-span]
    dw = d - dt
    print(f"\n=== {name} ===")
    print(f"  frames                 {len(g)}   g range {g.min():+.6f} .. {g.max():+.6f}")
    print(f"  total breathing        {(g.max() - g.min()) * 100:.3f}% magnification")
    print(f"  monotone trend RSS     wobble RMS = {rms:.6e} log-scale")
    print(f"  -> spurious shift at r={r_max:.0f}px: {rms * r_max:.3f} px per frame")
    print(f"  span-{span} applied dg   mean |dg|   = {np.abs(d).mean():.6e}"
          f"   ({np.abs(d).mean() * r_max:.3f} px at r={r_max:.0f})")
    print(f"  span-{span} TRUE  dg    mean |dg|   = {np.abs(dt).mean():.6e}"
          f"   ({np.abs(dt).mean() * r_max:.3f} px)")
    print(f"  span-{span} ERROR dg    mean |dg|   = {np.abs(dw).mean():.6e}"
          f"   ({np.abs(dw).mean() * r_max:.3f} px)  <- spurious, applied to pixels")
    frac = float(np.abs(dw).mean() / max(np.abs(dt).mean(), 1e-12))
    print(f"  error / true           {frac:.2f}x")
    viol = int(np.sum(np.sign(np.diff(g)) != np.sign(np.median(np.diff(trend)) or 1)))
    print(f"  monotonicity           {viol}/{len(g) - 1} steps move against the trend")
    return dict(frames=len(g), wobble_rms=rms, shift_px=rms * r_max,
                span_applied=float(np.abs(d).mean() * r_max),
                span_true=float(np.abs(dt).mean() * r_max),
                span_error=float(np.abs(dw).mean() * r_max),
                error_over_true=frac, violations=viol)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("sidecars", nargs="+")
    p.add_argument("--rmax", type=float, default=2100.0,
                   help="radius to convert log-scale into pixels (frame corner)")
    p.add_argument("--span", type=int, default=16)
    p.add_argument("--out")
    a = p.parse_args()

    res = {}
    for s in a.sidecars:
        path = Path(s)
        k, g, rot, ax, ay = read_ladder(path)
        res[path.name] = report(path.name, k, g, a.rmax, a.span)
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
