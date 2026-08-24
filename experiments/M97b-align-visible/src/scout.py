"""Scout a subject for the alignment-visibility test.

M97 measured that correcting registration on bee-3-cpl improves the render
only at large radius, and that a whole-frame metric cannot see it because the
bee is central: median tile gradient energy falls 767661 -> 4135 from centre
band to corner band, so the treatment region contains no subject.

If that is right, then EVERY whole-frame null the project has recorded
(M86's 0.9859x Tenengrad, M85's 0.985x) is explained by averaging a
large-radius win into a centre-dominated mean, and the fix is not a cleverer
metric but a SUBJECT WITH DETAIL AT LARGE RADIUS.

This picks one. For each candidate stack it reports two numbers from two
frames only, so it is cheap:

  drift  -- ground-truth scale of the last frame relative to the first, by
            FFT normalised cross-correlation maximised over a scale ladder.
            Independent of any strehl code or sidecar.
  edge/centre -- ratio of gradient energy in the outer radius band to the
            centre band. This is the number that decides whether a radially
            resolved metric has anything to measure. bee-3 scores ~0.005.

The subject I want scores HIGH on both. A stack that drifts a lot but has no
edge detail cannot demonstrate anything, and neither can a stack that is
detailed everywhere but does not drift.
"""

import json
import sys
from pathlib import Path

import numpy as np
import rawpy


def green(path: Path, ds: int = 4) -> np.ndarray:
    """Green CFA sub-lattice, block-mean downsampled. One colour only, so no
    interpolation ever mixes channels."""
    with rawpy.imread(str(path)) as r:
        raw = r.raw_image_visible.astype(np.float32)
        pat = r.raw_pattern
    gy, gx = [(y, x) for y in (0, 1) for x in (0, 1) if pat[y, x] == 1][0]
    g = raw[gy::2, gx::2]
    h, w = (g.shape[0] // ds) * ds, (g.shape[1] // ds) * ds
    return g[:h, :w].reshape(h // ds, ds, w // ds, ds).mean(axis=(1, 3))


def ncc(a: np.ndarray, b: np.ndarray) -> float:
    """Peak normalised cross-correlation over all translations, via FFT.
    Translation capture range is therefore unlimited."""
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    if d == 0:
        return 0.0
    c = np.fft.irfft2(np.fft.rfft2(a) * np.conj(np.fft.rfft2(b)), s=a.shape)
    return float(c.max() / d)


def zoom(a: np.ndarray, s: float) -> np.ndarray:
    from scipy.ndimage import map_coordinates

    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    return map_coordinates(a, [(yy - cy) * s + cy, (xx - cx) * s + cx], order=1,
                           mode="constant", cval=float(a.mean()))


def drift(a: np.ndarray, b: np.ndarray) -> tuple[float, float, bool]:
    """Magnification that must be applied to b to register it onto a.

    Returns (scale, ncc, railed). The rail flag is not decoration: the first
    version of this function let the refinement bracket walk outside its own
    bounds, and it returned scale=1.1722 for FOUR different subjects --
    identical values across unrelated scenes, which is a search hitting a stop,
    not a measurement. Bounds are now hard and a hit is reported.
    """
    LO, HI = 0.85, 1.35
    lo, hi = LO, HI
    best = (1.0, -1.0)
    step = (hi - lo) / 12.0
    for _ in range(4):
        for s in np.linspace(lo, hi, 13):
            # zoom(b, 1/s) magnifies b by s, so the returned number is a
            # magnification directly and needs no mental inversion later.
            v = ncc(a, zoom(b, 1.0 / s))
            if v > best[1]:
                best = (float(s), v)
        span = (hi - lo) / 6.0
        lo, hi = max(LO, best[0] - span), min(HI, best[0] + span)
        step = (hi - lo) / 12.0
    railed = abs(best[0] - LO) < step or abs(best[0] - HI) < step
    return best[0], best[1], railed


def radial_detail(a: np.ndarray) -> float:
    """Outer-band over centre-band STRUCTURE energy.

    Gradient of the raw frame is dominated by shot noise, which is spatially
    uniform and therefore reports a flat background as detailed: the first
    version of this scored bee-3 at 1.621 when the rendered frame measures
    ~0.005. Low-pass first, so what is left is scene structure rather than
    per-pixel noise, and use mean squared gradient so a few genuinely detailed
    tiles are not medianed away by surrounding emptiness.
    """
    from scipy.ndimage import gaussian_filter

    s = gaussian_filter(a, 1.5)
    gy = np.diff(s, axis=0)[:, :-1]
    gx = np.diff(s, axis=1)[:-1, :]
    e = gy * gy + gx * gx
    h, w = e.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(yy - (h - 1) / 2.0, xx - (w - 1) / 2.0)
    r /= r.max()
    centre = e[r < 0.25].mean()
    outer = e[r > 0.70].mean()
    return float(outer / centre) if centre > 0 else 0.0


def main(argv: list[str]) -> int:
    out = argv[1]

    # Controls first. A scale ladder that has not been shown to recover a
    # planted scale is not an instrument, and this one has already lied once.
    d0 = Path(r"D:\personal\macro") / argv[2]
    f0 = sorted(d0.glob("*.ARW"))[0]
    ref = green(f0)
    s, v, rail = drift(ref, ref)
    print(f"CONTROL self-vs-self       scale={s:.4f} ncc={v:.4f} railed={rail}  (want 1.0000)")
    for plant in (1.1500, 0.9000):
        s, v, rail = drift(ref, zoom(ref, plant))
        # zoom(ref, plant) shrinks by 1/plant, so it must be magnified by plant.
        print(f"CONTROL planted {plant:.4f}    scale={s:.4f} ncc={v:.4f} railed={rail}  "
              f"err={s - plant:+.4f}")
    print()
    sys.stdout.flush()

    rows = []
    for name in argv[2:]:
        d = Path(r"D:\personal\macro") / name
        fs = sorted(d.glob("*.ARW"))
        if len(fs) < 2:
            print(f"{name}: skipped, {len(fs)} frames")
            continue
        a, b = green(fs[0]), green(fs[-1])
        s, v, rail = drift(a, b)
        ec = radial_detail(a)
        rows.append(dict(stack=name, frames=len(fs), magnification=s, ncc=v,
                         railed=rail, edge_centre=ec))
        flag = "  *** RAILED, UNUSABLE ***" if rail else ""
        print(f"{name:<36} n={len(fs):>3}  mag={s:.4f}  ncc={v:.4f}  "
              f"edge/centre={ec:.3f}{flag}")
        sys.stdout.flush()

    print()
    print("ranked by (drift magnitude) x (edge detail) -- both must be large:")
    ok = [r for r in rows if not r["railed"]]
    for r in sorted(ok, key=lambda r: abs(1 - r["magnification"]) * r["edge_centre"],
                    reverse=True):
        print(f"  {r['stack']:<36} score={abs(1-r['magnification'])*r['edge_centre']:.5f}")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
