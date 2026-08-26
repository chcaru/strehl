"""Does a subject score low because it is soft, or because it is mostly flat?

THE PROBLEM.  ORCH ranked the corpus by mean |laplacian| over an 800x800 tile and
put `119MSDCF` 26th of 26.  But a mean over a region is a property of the whole
region: a tile that is 90% flat ink and 10% razor-sharp edge averages to a low
number, and so does a tile that is uniformly mushy.  The statistic cannot tell
them apart, and on `119MSDCF` my through-focus work says the second reading is
wrong -- its sources resolve at rel 0.15 (bee-3-cpl is 0.195-0.321), its focus
peak spans 8.7 captured frames, and the merge tracks the best frame at x0.987.

This is the corpus's recurring error in a new costume.  ORCH's own retraction
established that a detail statistic in absolute units measures the subject's
CONTRAST as much as the tool; this is the same statistic measuring the subject's
COMPOSITION.  Normalising by contrast, as sharpvscontrast.py does, does not fix
it, because a flat region contributes zero to both numerator and denominator.

THE SPLIT.  Partition the tile into detail-bearing and flat pixels, then report:

    fill  -- fraction of the tile that carries any resolvable structure
    raw   -- mean |laplacian| over the WHOLE tile          (ORCH's statistic)
    cond  -- mean |laplacian| over detail-bearing pixels   (sharpness where
             there is anything to be sharp)

The exact decomposition is

    raw = fill * cond + (1 - fill) * (mean over sub-threshold pixels)

and the second term is NOT negligible: on `wrapped-text-2`, fill = 0.010 and
cond = 764, so fill*cond = 7.6 against a measured raw of 416.  That tile is a
bright white label whose sub-threshold pixels still carry ~417 DN of |laplacian|
from shot noise alone.  Quoting `raw ~= fill * cond` would therefore be wrong,
and wrong in a way that flatters sparse bright subjects.

If a subject is low on `raw` but normal on `cond`, it is a sparse subject
rendered correctly and no reshoot will change it.  If it is low on `cond` too, it
is genuinely under-resolved and belongs at the bottom.

DETAIL-BEARING is defined WITHIN each tile, as a fraction of that tile's own 99th
percentile of local detail -- never an absolute DN threshold, for exactly the
reason ORCH retracted.  All measurements are on the camera-linear masters in
tri.LIN, never on the tone-curved SHIP-V1 files.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orchsites as OS  # noqa: E402
import tri  # noqa: E402

# A pixel is detail-bearing if its local detail exceeds the 99th percentile of
# what PURE NOISE of the same magnitude produces in the same estimator -- a
# Monte-Carlo null calibrated per tile, so it is neither an absolute DN constant
# (ORCH's retraction) nor a within-tile percentile (which is degenerate: "10% of
# the tile's own p99" reports fill 1.000 on a perfectly flat tile, because a
# relative threshold always finds something).  Distinguishing flat from textured
# is inherently a comparison against noise and cannot be done any other way.
NULL_PCT = 99.0
SMOOTH = 9          # box width over which local detail density is pooled


def detail_map(y: np.ndarray) -> np.ndarray:
    """|laplacian|, pooled over a SMOOTH box so it reads density not spikes."""
    lap = np.abs(4.0 * y[1:-1, 1:-1] - y[:-2, 1:-1] - y[2:, 1:-1]
                 - y[1:-1, :-2] - y[1:-1, 2:])
    k = SMOOTH
    c = np.cumsum(np.cumsum(np.pad(lap, ((1, 0), (1, 0))), 0), 1)
    h, w = lap.shape
    ys, xs = np.arange(0, h - k), np.arange(0, w - k)
    box = (c[np.ix_(ys + k, xs + k)] - c[np.ix_(ys, xs + k)]
           - c[np.ix_(ys + k, xs)] + c[np.ix_(ys, xs)]) / float(k * k)
    return box


def null_threshold(y: np.ndarray, seed: int = 7) -> float:
    """What this estimator reports on pure noise of the tile's own magnitude.

    Synthesise a tile of the same mean level and the same measured pixel noise,
    with NO structure, and read the estimator's 99th percentile on it.  Anything
    above that is structure at a 1% false-positive rate by construction.  Doing
    it by simulation rather than by propagating sigma analytically means the
    pooling, the kernel and the percentile are all accounted for exactly.
    """
    sd = tri.pixel_noise(y)
    rng = np.random.default_rng(seed)
    synth = float(np.mean(y)) + rng.normal(0.0, max(sd, 1e-9), size=y.shape)
    return float(np.percentile(detail_map(synth), NULL_PCT))


def split(y: np.ndarray) -> tuple[float, float, float]:
    d = detail_map(y)
    m = d > null_threshold(y)
    fill = float(m.mean())
    raw = float(d.mean())
    cond = float(d[m].mean()) if m.any() else 0.0
    return fill, raw, cond


def _textured(shape, rng, amp=400.0, sd=20.0, level=2000.0):
    """Real structure: hard-edged blocks, not grain.  Grain is not detail.

    The period must be fine relative to SMOOTH, or the plant undercounts itself:
    at period 22 px the block INTERIORS are flat, only their edges are
    detail-bearing, and a planted fill of 0.25 reads as 0.172 -- a defect of the
    plant, not of the estimator.  At ~5 px every pooling window straddles an edge.
    """
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    pat = np.sign(np.sin(xx / 1.5) * np.sin(yy / 2.0))
    return level + amp * pat + rng.normal(0.0, sd, size=shape)


def commission() -> None:
    """Planted fill fractions it must recover, and three nulls."""
    rng = np.random.default_rng(11)
    n = 600
    for want in (0.25, 0.50, 0.75):
        t = np.full((n, n), 2000.0) + rng.normal(0.0, 20.0, size=(n, n))
        rows = int(round(want * n))
        t[:rows] = _textured((rows, n), rng)
        fill, _, _ = split(t)
        assert abs(fill - want) < 0.06, \
            f"C1 fill: planted {want:.2f} textured, recovered {fill:.3f}"
    # NULL: flat plus noise is not detail.
    f0, _, _ = split(np.full((n, n), 2000.0) + rng.normal(0, 20.0, (n, n)))
    assert f0 < 0.05, f"C2 null: flat+noise tile reported fill {f0:.3f}"
    # NULL: GRAIN IS NOT DETAIL.  A tile of pure high-amplitude noise carries no
    # structure; an estimator that scores it as detail-bearing would rank noisy
    # renders above clean ones, a trap this corpus has already fallen into once.
    f1, _, _ = split(np.full((n, n), 2000.0) + rng.normal(0, 300.0, (n, n)))
    assert f1 < 0.05, f"C3 null: pure grain reported fill {f1:.3f} (grain != detail)"
    # PLANT: `cond` must be blind to fill.  Same texture, two different fills,
    # must give the same conditional sharpness -- that is the whole claim.
    a = np.full((n, n), 2000.0) + rng.normal(0, 20.0, (n, n))
    b = a.copy()
    a[:int(0.3 * n)] = _textured((int(0.3 * n), n), rng)
    b[:int(0.9 * n)] = _textured((int(0.9 * n), n), rng)
    _, ra, ca = split(a)
    _, rb, cb = split(b)
    assert abs(ca - cb) / cb < 0.10, \
        f"C4 cond: same texture at 30% and 90% fill gave {ca:.1f} vs {cb:.1f}"
    assert rb > 1.8 * ra, \
        f"C5 raw: raw must track fill; 30% gave {ra:.1f}, 90% gave {rb:.1f}"
    # PLANT: `cond` must FALL when the same fill is genuinely softer.
    c = np.full((n, n), 2000.0) + rng.normal(0, 20.0, (n, n))
    c[:int(0.5 * n)] = _textured((int(0.5 * n), n), rng, amp=100.0)
    d_ = np.full((n, n), 2000.0) + rng.normal(0, 20.0, (n, n))
    d_[:int(0.5 * n)] = _textured((int(0.5 * n), n), rng, amp=400.0)
    _, _, cc = split(c)
    _, _, cd = split(d_)
    assert cd > 2.0 * cc, \
        f"C6 cond: weaker structure must score lower; {cc:.1f} vs {cd:.1f}"
    print(f"commissioning OK  (fills .25/.50/.75 recovered <0.06; flat null "
          f"{f0:.3f}; GRAIN null {f1:.3f};\n                  cond blind to fill "
          f"within {abs(ca - cb) / cb * 100:.1f}%; raw tracks fill {rb / ra:.2f}x; "
          f"cond tracks contrast {cd / cc:.2f}x)")


def main() -> int:
    commission()
    rows = []
    for sub in OS.subjects_by_rank():
        p = os.path.join(tri.LIN, sub + ".tiff")
        if not os.path.exists(p):
            print(f"  MISSING linear master: {sub}")
            continue
        y = tri.luma(tri.load16(p))
        x0, y0 = OS.site_xy(sub)
        t = y[y0:y0 + OS.TILE, x0:x0 + OS.TILE]
        fill, raw, cond = split(t)
        rows.append({"sub": sub, "fill": fill, "raw": raw, "cond": cond})
        del y

    r_raw = {r["sub"]: i + 1 for i, r in
             enumerate(sorted(rows, key=lambda r: -r["raw"]))}
    r_cond = {r["sub"]: i + 1 for i, r in
              enumerate(sorted(rows, key=lambda r: -r["cond"]))}

    out = os.path.join(tri.OUT, "fillfactor.json")
    json.dump({"n": len(rows), "null_pct": NULL_PCT, "smooth": SMOOTH,
               "space": "camera-linear masters in tri.LIN, never SHIP-V1",
               "rows": [dict(r, rk_raw=r_raw[r["sub"]], rk_cond=r_cond[r["sub"]])
                        for r in rows]},
              open(out, "w"), indent=1)

    print(f"\n{'subject':<38} {'fill':>6} {'raw':>8} {'cond':>8} "
          f"{'rk_raw':>7} {'rk_cond':>8} {'move':>6}")
    print("-" * 88)
    for r in sorted(rows, key=lambda r: r_cond[r["sub"]]):
        mv = r_raw[r["sub"]] - r_cond[r["sub"]]
        print(f"{r['sub']:<38} {r['fill']:>6.3f} {r['raw']:>8.1f} "
              f"{r['cond']:>8.1f} {r_raw[r['sub']]:>7} {r_cond[r['sub']]:>8} "
              f"{mv:>+6}")
    print(f"\nn={len(rows)}.  raw ~= fill * cond.  A subject low on `raw` but "
          f"mid-pack on `cond`\nis sparse, not soft: the tile is mostly flat "
          f"and that is the subject, not the merge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
