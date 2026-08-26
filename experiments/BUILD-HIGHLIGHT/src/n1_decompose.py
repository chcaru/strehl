"""n1 -- is the residual CA-SHAPED, or is most of it not radial at all?

THE QUESTION, AND WHY IT IS THE ONE LEFT.

Lateral CA is a radial magnification error. Its displacement is `eps * r`, which
is **exactly zero at the optical centre** and grows linearly outward. That is not
an incidental property, it is what the aberration IS: `optics.rs::displacement_at`
returns `eps * radius`, and M107's own fit reports the displacement going "-> 0 at
the optical centre".

So a residual colour error of the form

    cr(r) = A + B * r

decomposes into two physically different things:

  * **B * r** -- radial, vanishing on axis. This is the CA-shaped part, and it is
    the only part a lateral-CA coefficient can ever remove.
  * **A** -- a constant offset present at r = 0. **This cannot be lateral CA**,
    because CA has no effect on axis. Whatever A is -- scene colour, matrix, a
    per-channel photometric term -- refitting or clamping a radial coefficient
    cannot touch it.

I reported in section 12 that the residual "grows 1.66x centre to corner" and let
that stand as support for candidate C. **Growth is a statement about B. It is not
a statement about how much of the defect is B.** If A dominates, then most of the
visible error is not lateral CA at all and every remedy aimed at the radial
coefficient -- ORCH's items 1, 2 and 3 -- is aimed at the minority term. That is
worth knowing before anyone edits a coefficient, so it is measured here first.

THE INSTRUMENT MUST BE SHOWN ABLE TO FAIL. `--selftest` plants known (A, B)
pairs, including a pure-radial case with A = 0 and a pure-offset case with B = 0,
and requires recovery of both. A decomposition that cannot separate the two cases
it exists to separate is not evidence.

RADIUS CONVENTION. `r` is normalised to the **full-res sensel half-diagonal**,
which is the convention `optics.rs` and M107b's r6_support.py use, so that
`support_r_max = 0.788` is directly comparable. For a 7032x4688 render the
half-diagonal is hypot(3516, 2344) = 4225.0 sensels; r = 1.0 is the corner.

Magnitudes are read in LINEAR only. Every input here is a --linear-srgb render.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import tifffile

SUPPORT_R_MAX = 0.788  # optics.rs:381, declared for the shipped profile


def radius_norm(shape) -> np.ndarray:
    """Normalised radius, full-res sensel half-diagonal = 1.0."""
    h, w = shape[:2]
    gy, gx = np.mgrid[0:h, 0:w]
    r = np.hypot(gy - (h - 1) / 2.0, gx - (w - 1) / 2.0)
    return (r / np.hypot(h / 2.0, w / 2.0)).astype(np.float32)


def decompose(cr: np.ndarray, r: np.ndarray, m: np.ndarray, nann: int = 12) -> dict:
    """Fit cr = A + B*r on per-annulus MEDIANS, and test whether a cubic helps.

    WHY MEDIANS PER ANNULUS AND NOT ORDINARY LEAST SQUARES ON THE PIXELS.
    The first version of this function ran OLS over the masked pixels and
    returned B = -0.0010 for an arm whose own published band medians fall to
    -0.5260. Both cannot be true, and the disagreement is not noise: on this
    population the mean is -0.1827 while the median is -0.2161, with no
    outlier problem at all (|cr| > 5 on 0.0000 % of pixels, luma p0.1 = 0.09).

    The divergence is physical rather than numerical, and it matters.
    **Lateral CA is ANTISYMMETRIC across an edge** -- M107-chroma records that a
    radial displacement of red produces "red excess on the inward side of an
    edge and red deficit on the outward side". A mean taken over an edge
    population therefore averages the two sides toward cancellation, which is
    precisely the signal being looked for. A median does not.

    So the statistic is the one already published in section 12 -- per-annulus
    medians -- and the line is fitted through those. `mean_median_gap` is
    reported alongside, because a large gap is itself the antisymmetry
    signature and a reader should be able to see it.
    """
    x_all = r[m].astype(np.float64)
    y_all = cr[m].astype(np.float64)

    lo, hi = float(x_all.min()), float(x_all.max())
    edges = np.linspace(lo, hi, nann + 1)
    xs, ys = [], []
    for i in range(nann):
        sel = (x_all >= edges[i]) & (x_all < edges[i + 1])
        if sel.sum() >= 200:
            xs.append(0.5 * (edges[i] + edges[i + 1]))
            ys.append(float(np.median(y_all[sel])))
    if len(xs) < 4:
        raise ValueError(f"only {len(xs)} populated annuli -- refusing to fit a line to that")
    x = np.asarray(xs)
    y = np.asarray(ys)

    b1, a1 = np.polyfit(x, y, 1)
    pred1 = a1 + b1 * x
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2_lin = 1.0 - float(((y - pred1) ** 2).sum()) / max(ss_tot, 1e-30)

    # A cubic in r. If the TRUE aberration is first-order, this buys nothing;
    # if the model shape is wrong at high field, it buys something out there.
    deg = min(3, len(x) - 1)
    c3 = np.polyfit(x, y, deg)
    pred3 = np.polyval(c3, x)
    r2_cub = 1.0 - float(((y - pred3) ** 2).sum()) / max(ss_tot, 1e-30)

    corner_total = a1 + b1 * 1.0
    return {
        "n": int(x_all.size),
        "n_annuli": int(len(x)),
        "A_constant": float(a1),
        "B_radial_per_r": float(b1),
        "r2_linear": float(r2_lin),
        "r2_cubic": float(r2_cub),
        "cubic_gain_r2": float(r2_cub - r2_lin),
        "corner_pred": float(corner_total),
        # The number that decides where a remedy must aim.
        "nonradial_share_at_corner": (
            float(abs(a1) / max(abs(corner_total), 1e-12)) if corner_total else None
        ),
        "mean_median_gap": float(y_all.mean() - np.median(y_all)),
        "band_medians": [float(v) for v in y],
        "r_min": lo,
        "r_max": hi,
        "frac_beyond_support": float((x_all > SUPPORT_R_MAX).mean()),
    }


def _mask_and_planes(img: np.ndarray, pct: float):
    y = (0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]).astype(np.float32)
    ysafe = np.maximum(y, 1e-6)
    cr = ((img[..., 0] - img[..., 1]) / ysafe).astype(np.float32)
    gy = np.abs(np.gradient(y, axis=0))
    gx = np.abs(np.gradient(y, axis=1))
    g = gy + gx
    m = (g >= np.percentile(g, pct)) & (img.max(axis=2) < 0.99)
    return cr, m


def selftest() -> None:
    rng = np.random.default_rng(5)
    h, w = 600, 900
    r = radius_norm((h, w))
    m = np.ones((h, w), dtype=bool)

    cases = [
        ("pure radial   (A=0)", 0.0, -0.30),
        ("pure offset   (B=0)", -0.20, 0.0),
        ("mixed              ", -0.15, -0.25),
    ]
    for name, a0, b0 in cases:
        cr = (a0 + b0 * r + rng.normal(0, 0.01, size=r.shape)).astype(np.float32)
        d = decompose(cr, r, m)
        assert abs(d["A_constant"] - a0) < 0.02, f"{name}: A={d['A_constant']:.4f} want {a0}"
        assert abs(d["B_radial_per_r"] - b0) < 0.02, f"{name}: B={d['B_radial_per_r']:.4f} want {b0}"
        print(
            f"  {name}  planted A={a0:+.3f} B={b0:+.3f}"
            f"  ->  recovered A={d['A_constant']:+.4f} B={d['B_radial_per_r']:+.4f}"
        )

    # The two extreme cases must be DISTINGUISHABLE, not merely each recovered.
    cr_rad = (0.0 - 0.30 * r).astype(np.float32)
    cr_off = (-0.20 + 0.0 * r).astype(np.float32)
    d_rad, d_off = decompose(cr_rad, r, m), decompose(cr_off, r, m)
    assert d_rad["nonradial_share_at_corner"] < 0.05, "pure-radial plant read as non-radial"
    assert d_off["nonradial_share_at_corner"] > 0.95, "pure-offset plant read as radial"
    print(
        f"  separation: pure-radial non-radial share ="
        f" {d_rad['nonradial_share_at_corner']:.3f},"
        f" pure-offset = {d_off['nonradial_share_at_corner']:.3f}"
    )

    # A cubic must be bought only when the truth is not a line.
    cr_lin = (-0.1 - 0.2 * r).astype(np.float32)
    cr_cub = (-0.1 - 0.2 * r**3).astype(np.float32)
    g_lin = decompose(cr_lin, r, m)["cubic_gain_r2"]
    g_cub = decompose(cr_cub, r, m)["cubic_gain_r2"]
    assert g_lin < 1e-3, f"cubic bought something on a straight line: {g_lin}"
    assert g_cub > 0.01, f"cubic bought nothing on a cubic truth: {g_cub}"
    print(f"  cubic gain: on a LINE {g_lin:.5f} (must be ~0), on a CUBIC {g_cub:.5f} (must be >0)")
    print("n1 selftest: PASS -- A and B are separable and the cubic term is not free.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--arm", nargs=2, action="append", metavar=("NAME", "PATH"))
    ap.add_argument("--bright-pct", type=float, default=99.5)
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.selftest:
        selftest()
        return 0

    res = {}
    print(f"{'arm':<18} {'n':>9} {'A (const)':>10} {'B (radial)':>11} "
          f"{'corner':>8} {'NON-radial':>11} {'cubic dR2':>10} {'>0.788':>7}")
    print("-" * 92)
    for name, path in a.arm or []:
        img = tifffile.imread(path).astype(np.float32) / 65535.0
        cr, m = _mask_and_planes(img, a.bright_pct)
        r = radius_norm(img.shape)
        d = decompose(cr, r, m)
        res[name] = d
        print(
            f"{name:<18} {d['n']:>9} {d['A_constant']:>+10.4f} {d['B_radial_per_r']:>+11.4f} "
            f"{d['corner_pred']:>+8.4f} {100 * d['nonradial_share_at_corner']:>10.1f}% "
            f"{d['cubic_gain_r2']:>10.5f} {100 * d['frac_beyond_support']:>6.1f}%"
        )
        del img, cr, m, r

    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1)
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
