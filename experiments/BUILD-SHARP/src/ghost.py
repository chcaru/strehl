"""Where is the ghost, and which way does it point?

BUILD-RENDER saw a leg edge appearing more than once on `bee-1-cpl`. That is
two frames disagreeing about where the edge is, so this measures the residual
displacement field between two ADJACENT gathered frames -- the two the merge
actually elects between -- as a function of image radius.

The discriminator is DIRECTION, not magnitude:

  * Focus breathing changes magnification. Its residual is RADIAL and grows
    linearly with radius from the scale centre. The signed radial mean is
    non-zero and has a slope.
  * Estimator jitter is isotropic. Its direction is uncorrelated with the
    radial direction, so the SIGNED radial mean is zero at every radius no
    matter how large the jitter is.

A magnitude-only plot cannot tell these apart -- both make |shift| grow if the
noise grows. The signed radial projection has a null that jitter must satisfy,
which is why it is the statistic and |shift| is only reported beside it.

Sub-pixel without resampling
----------------------------
Project rule: registration for measurement uses integer-only shifts, because
sub-pixel resampling adds blur to the quantity being measured. That rule is
about not resampling the DATA. Here the sub-pixel refinement is a parabola fit
to the CORRELATION SURFACE, which never touches the image, so the measured
planes are never resampled. The integer argmax is reported alongside so the
refinement can be checked for doing anything perverse.

Controls (all three run by default; none of them is optional)
------------------------------------------------------------
  self   frame i against ITSELF. Must read exactly 0.000 at every radius.
         Catches a broken estimator, a bad origin, or a windowing bug.
  plant  frame i against a KNOWN magnification of itself. Must recover
         (s-1)*r with the right slope AND the right sign. This is the only
         control that proves the instrument can see the effect being hunted;
         without it a null result is uninterpretable.
  none   the same pair gathered through the IDENTITY. Breathing is unremoved
         here, so this must show a large radial slope. It is the upper bound
         the treatment is trying to beat.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import affine_transform

TILE = 128
STRIDE = 160
MAXSHIFT = 6.0
MIN_CONTRAST = 1.5e-3   # tile sd below this is flat; its correlation is noise
MIN_SHARPNESS = 3.0     # peak / surface sd


def load(path: Path, w: int, h: int) -> np.ndarray:
    a = np.fromfile(path, dtype="<f4")
    assert a.size == w * h, f"{path.name}: {a.size} samples, expected {w * h}"
    return a.reshape(h, w).astype(np.float64)


def parabola(y0: float, y1: float, y2: float) -> float:
    """Vertex offset of the parabola through (-1,y0),(0,y1),(1,y2), in [-1,1]."""
    d = y0 - 2.0 * y1 + y2
    if d >= 0.0:                      # not concave: no interior maximum
        return 0.0
    return float(np.clip(0.5 * (y0 - y2) / d, -1.0, 1.0))


def tile_shift(a: np.ndarray, b: np.ndarray):
    """Displacement that best maps `b` onto `a`, in pixels. None if unreliable."""
    if a.std() < MIN_CONTRAST or b.std() < MIN_CONTRAST:
        return None
    n = a.shape[0]
    win = np.outer(np.hanning(n), np.hanning(n))
    fa = np.fft.rfft2((a - a.mean()) * win)
    fb = np.fft.rfft2((b - b.mean()) * win)
    c = np.fft.irfft2(fa * np.conj(fb), s=a.shape)
    c = np.fft.fftshift(c)
    mid = n // 2
    r = int(MAXSHIFT) + 1
    sub = c[mid - r:mid + r + 1, mid - r:mid + r + 1]
    j, i = np.unravel_index(int(np.argmax(sub)), sub.shape)
    if j == 0 or i == 0 or j == sub.shape[0] - 1 or i == sub.shape[1] - 1:
        return None                   # peak on the edge of the search window
    peak = sub[j, i]
    if peak <= 0 or peak / (c.std() + 1e-12) < MIN_SHARPNESS:
        return None
    dy = (j - r) + parabola(sub[j - 1, i], peak, sub[j + 1, i])
    dx = (i - r) + parabola(sub[j, i - 1], peak, sub[j, i + 1])
    if abs(dx) > MAXSHIFT or abs(dy) > MAXSHIFT:
        return None
    return dx, dy, (i - r), (j - r)


def field(a: np.ndarray, b: np.ndarray, cx: float, cy: float, margin: int = 0):
    """Per-tile radial / tangential residual against radius.

    Returns a dict keyed by tile origin `(x, y)` so that two arms can be
    compared on the SAME tiles. That pairing is not optional: the arms admit
    different numbers of tiles (the aligned arm admitted 48 where the unaligned
    admitted 63 on one span-16 pair), so an unpaired mean compares two different
    populations of image content and the difference could be entirely selection.

    `margin` excludes tiles within that many pixels of the plane border. This is
    not cosmetic either. The aligned arm gathers through a placement that can
    displace content by tens of pixels at large radius (g = -0.018 moves a
    feature at r = 2100 by 38 px), so a corner tile can be partly filled from
    outside the source plane. Border fill correlates with itself and is read as
    a residual the identity-gathered arm never sees. Measured: excluding 200 px
    changed the span-1 verdict from "alignment is 15x worse at the corner" to
    "alignment removes 60-96% of the radial term". The unexcluded reading was an
    artefact of this instrument, not a property of the aligner.
    """
    h, w = a.shape
    out = {}
    for y in range(margin, h - TILE - margin, STRIDE):
        for x in range(margin, w - TILE - margin, STRIDE):
            s = tile_shift(a[y:y + TILE, x:x + TILE], b[y:y + TILE, x:x + TILE])
            if s is None:
                continue
            dx, dy, ix, iy = s
            px, py = x + TILE / 2 - cx, y + TILE / 2 - cy
            r = float(np.hypot(px, py))
            if r < 50.0:
                continue              # radial direction undefined at the origin
            ux, uy = px / r, py / r
            out[(x, y)] = (r, dx * ux + dy * uy, -dx * uy + dy * ux,
                           float(np.hypot(dx, dy)))
    return out or None


def as_arrays(f, keys=None):
    """Pack a tile dict into arrays, optionally restricted to `keys`."""
    if f is None:
        return None
    ks = [k for k in (keys if keys is not None else f) if k in f]
    if not ks:
        return None
    d = np.array([f[k] for k in ks])
    return dict(r=d[:, 0], radial=d[:, 1], tang=d[:, 2], mag=d[:, 3])


def summarise(name: str, f, note: str = "") -> dict:
    if f is None:
        print(f"  {name:<26} NO ADMISSIBLE TILES")
        return {}
    r, rad, tan = f["r"], f["radial"], f["tang"]
    # Slope through the origin: a pure magnification gives radial = (s-1)*r.
    slope = float(np.sum(r * rad) / np.sum(r * r))
    edges = [0, 600, 1000, 1400, 1800, 3000]
    bins = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (r >= lo) & (r < hi)
        if m.sum() >= 3:
            bins.append((lo, hi, int(m.sum()), float(rad[m].mean()),
                         float(np.abs(tan[m]).mean()), float(f["mag"][m].mean())))
    print(f"  {name:<26} n={len(r):<5} slope={slope * 1e4:+8.4f} px/kpx"
          f"  mean|shift|={f['mag'].mean():.4f} px"
          f"  mean_radial={rad.mean():+.4f}  mean|tang|={np.abs(tan).mean():.4f}"
          f"  {note}")
    for lo, hi, n, mr, mt, mm in bins:
        print(f"      r {lo:>4}-{hi:<4} n={n:<4} radial={mr:+.4f}  |tang|={mt:.4f}  |shift|={mm:.4f}")
    return dict(name=name, n=len(r), slope_px_per_kpx=slope * 1e4,
                mean_abs_shift=float(f["mag"].mean()),
                mean_radial=float(rad.mean()),
                mean_abs_tang=float(np.abs(tan).mean()),
                bins=[dict(lo=lo, hi=hi, n=n, radial=mr, abs_tang=mt, abs_shift=mm)
                      for lo, hi, n, mr, mt, mm in bins])


def magnify(a: np.ndarray, s: float, cx: float, cy: float) -> np.ndarray:
    """Magnify `a` about (cx,cy) by `s`. Used ONLY to build the positive control."""
    m = np.array([[1.0 / s, 0.0], [0.0, 1.0 / s]])
    off = np.array([cy - cy / s, cx - cx / s])
    return affine_transform(a, m, offset=off, order=3, mode="reflect")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--margin", type=int, default=0)
    ap.add_argument("--plant", type=float, default=1.0005,
                    help="magnification for the positive control")
    a = ap.parse_args()
    d = Path(a.dir)
    man = json.loads((d / "manifest.json").read_text())
    w, h, cx, cy, span = man["width"], man["height"], man["cx"], man["cy"], man["span"]
    print(f"plane {w}x{h}, scale centre ({cx}, {cy}), span {span}")
    print(f"tile {TILE} stride {STRIDE} maxshift {MAXSHIFT}\n")

    out = {"manifest": man, "pairs": {}}
    for i in man["pairs"]:
        j = i + span
        print(f"pair {i} -> {j}   (dg = "
              f"{man['placements'][str(j)]['g'] - man['placements'][str(i)]['g']:+.6f})")
        aw = load(d / f"f{i}_warp.f32", w, h)
        bw = load(d / f"f{j}_warp.f32", w, h)
        an = load(d / f"f{i}_none.f32", w, h)
        bn = load(d / f"f{j}_none.f32", w, h)

        res = {}
        res["self"] = summarise("CONTROL self (must be 0)",
                                as_arrays(field(aw, aw, cx, cy, a.margin)))
        pl = magnify(aw, a.plant, cx, cy)
        res["plant"] = summarise(
            f"CONTROL plant x{a.plant}", as_arrays(field(aw, pl, cx, cy, a.margin)),
            note=f"<- expect |slope| = {(a.plant - 1.0) * 1e4:.4f}")

        # POSITIVE CONTROL: apply the aligner's OWN recorded correction to the
        # unaligned pair, analytically. This has the exact structure of the
        # treatment (a pure magnification about the scale centre) and a known
        # correct magnitude, so it asks the one question that matters about this
        # instrument: can it SEE a correction it knows to be right?
        #
        # If applying the true correction fails to reduce the measured residual,
        # the instrument is not measuring registration at this span -- it is
        # being dominated by the genuine change in image content between two
        # frames at different focus, which plain correlation cannot separate
        # from a shift. In that case no aligned-vs-unaligned verdict at this
        # span is admissible. The sign convention of `g` is a documentation
        # question rather than a data one, so both signs are reported; the
        # control passes only if one clearly helps and the other clearly hurts.
        dg = man["placements"][str(j)]["g"] - man["placements"][str(i)]["g"]
        base = as_arrays(field(an, bn, cx, cy, a.margin))
        for sgn in (+1.0, -1.0):
            c = as_arrays(field(an, magnify(bn, 1.0 + sgn * dg, cx, cy),
                                cx, cy, a.margin))
            res[f"truth{sgn:+.0f}"] = summarise(
                f"CONTROL truth-corr {sgn:+.0f}dg", c,
                note=f"<- vs uncorrected {base['mag'].mean():.4f} px"
                     if base else "")

        # The two arms that are compared to each other are scored on the
        # INTERSECTION of the tiles both admitted, so the comparison is paired.
        fn = field(an, bn, cx, cy, a.margin)
        fw = field(aw, bw, cx, cy, a.margin)
        both = sorted(set(fn or {}) & set(fw or {}))
        print(f"    paired tiles: {len(both)}  (unaligned admitted "
              f"{len(fn or {})}, aligned {len(fw or {})})")
        res["none"] = summarise("CONTROL unaligned  [paired]", as_arrays(fn, both))
        res["warp"] = summarise("TREATMENT aligned  [paired]", as_arrays(fw, both))
        if both:
            mn = np.mean([fn[k][3] for k in both])
            mw = np.mean([fw[k][3] for k in both])
            worse = sum(1 for k in both if fw[k][3] > fn[k][3])
            print(f"    PAIRED VERDICT: aligned {mw:.4f} px vs unaligned {mn:.4f} px"
                  f"  ratio {mw / mn:.3f}x   aligned worse on {worse}/{len(both)} tiles")
            res["paired"] = dict(aligned=float(mw), unaligned=float(mn),
                                 ratio=float(mw / mn), worse=worse, n=len(both))
        out["pairs"][str(i)] = res
        print()

    (d / "ghost.json").write_text(json.dumps(out, indent=1))
    print(f"wrote {d / 'ghost.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
