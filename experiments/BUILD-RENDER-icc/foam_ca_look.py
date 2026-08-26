"""foam CA A/B: pictures at 1:1 of the specular rims, plus a commissioned number.

The instrument here is PICTURES. This project has a documented history of green
metrics over bad images, so the crops are the deliverable and the statistic is
secondary and explicitly commissioned.

Arms come from ONE binary rendered minutes apart, in --linear-srgb, so this is a
same-binary A/B needing no green restriction and no tone curve is in the way of
the measurement. A display curve is applied ONLY to make the PNG viewable, and
it is the SAME curve with the SAME exposure on both arms -- otherwise the eye is
comparing two gradings rather than two renders.

Site selection is automatic and radius-ordered, because lateral CA is radial: it
grows toward the corners and vanishes at the centre. Choosing corner sites plus
one central control means the pictures can REFUTE the mechanism, not merely
illustrate it -- if the centre shows as much colour as the corner, what we are
looking at is not lateral CA, and on this subject it would more likely be the
thin-film iridescence that foam genuinely has.

Crops are written as PNG. Never JPEG a 100% artifact crop: the codec invents and
destroys exactly the chroma detail under examination.

Never PIL for 16-bit RGB: it silently downconverts to 8 bits.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import tifffile
from PIL import Image

D = pathlib.Path(r"C:\dev\strehl-out\BUILD-RENDER-foamca")
OUT = D / "crops"
CROP = 360          # 1:1 crop edge, px
NSITE = 5           # 4 corner-most sites + 1 central control


def load(p: pathlib.Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p.name}: dtype {a.dtype}, expected uint16"
    assert a.ndim == 3 and a.shape[2] == 3, f"{p.name}: shape {a.shape}"
    return a


def srgb_oetf(x: np.ndarray) -> np.ndarray:
    """Linear -> sRGB, for DISPLAY only. Never feed the result to a statistic."""
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


def edge_chroma(rgb: np.ndarray) -> tuple[float, float]:
    """Chroma error at bright rims, and the same in flat areas as a control.

    Returns (rim, flat), both in LINEAR light.

    A colour fringe is a channel MISREGISTRATION, so it shows as R and B
    departing from G specifically where there is a bright edge. Two exclusions
    matter and the first version of this function got both wrong:

    * Dark pixels are excluded. |R-G|/G with G near zero is a ratio of noise to
      nothing; on a dark subject like foam it dominates the average completely
      and the statistic then reports the shadows, not the highlights.
    * A flat-region control is measured alongside, because a CA warp RESAMPLES
      R and B, and resampling smooths noise by an amount that grows with the
      shift -- which grows with radius. That would mimic radial fringe removal
      exactly. If the flat control falls as much as the rim figure, what has
      been measured is interpolation smoothing and not aberration.
    """
    g = rgb[:, :, 1].astype(np.float64)
    r = rgb[:, :, 0].astype(np.float64)
    b = rgb[:, :, 2].astype(np.float64)
    gy, gx = np.gradient(g)
    mag = np.hypot(gx, gy)

    bright = g >= 0.20 * float(g.max())        # near the specular rims only
    if bright.sum() < 64:
        return float("nan"), float("nan")

    hi = np.percentile(mag[bright], 75.0)
    lo = np.percentile(mag[bright], 25.0)
    rim = bright & (mag >= hi)
    flat = bright & (mag <= lo)

    def chroma(m: np.ndarray) -> float:
        if m.sum() < 32:
            return float("nan")
        d = np.maximum(g[m], 1.0)
        return float((np.abs(r[m] - g[m]) / d + np.abs(b[m] - g[m]) / d).mean())

    return chroma(rim), chroma(flat)


def pick_sites(on: np.ndarray) -> list[tuple[int, int, float]]:
    """Bright specular rims, one per grid cell, ordered by radius from centre."""
    h, w, _ = on.shape
    g = on[:, :, 1].astype(np.float64)
    gy, gx = np.gradient(g)
    mag = np.hypot(gx, gy)
    bright = g >= np.percentile(g, 99.0)
    score = mag * bright                       # a rim: bright AND changing fast
    cy, cx = h / 2.0, w / 2.0
    half = float(np.hypot(cy, cx))

    cells, step = [], CROP
    for y0 in range(0, h - CROP, step * 2):
        for x0 in range(0, w - CROP, step * 2):
            sub = score[y0:y0 + CROP, x0:x0 + CROP]
            s = float(sub.sum())
            if s <= 0:
                continue
            yy, xx = y0 + CROP // 2, x0 + CROP // 2
            r = float(np.hypot(yy - cy, xx - cx)) / half
            cells.append((s, yy, xx, r))
    if not cells:
        return []

    cells.sort(key=lambda t: -t[0])
    strong = cells[:60]                        # strongest rims anywhere
    strong.sort(key=lambda t: -t[3])           # then corner-most first
    picked = [(y, x, r) for _, y, x, r in strong[:NSITE - 1]]
    centre = min(strong, key=lambda t: t[3])
    picked.append((centre[1], centre[2], centre[3]))
    return picked


def main() -> int:
    on_p, off_p = D / "on.tif", D / "off.tif"
    for p in (on_p, off_p):
        if not p.exists():
            print(f"missing {p}")
            return 2
    on, off = load(on_p), load(off_p)
    assert on.shape == off.shape, f"arm geometry differs {on.shape} vs {off.shape}"
    OUT.mkdir(parents=True, exist_ok=True)
    h, w, _ = on.shape
    print(f"geometry {w}x{h}   arms: on.tif (CORRECTING) / off.tif (off)\n")

    sites = pick_sites(on)
    if not sites:
        print("no specular rim sites found")
        return 2

    print(f"{'site':<16}{'x':>6}{'y':>6}{'r/half':>8}"
          f"{'rim OFF':>10}{'rim ON':>9}{'rim drop':>10}"
          f"{'flat OFF':>10}{'flat ON':>9}{'flat drop':>11}")
    rows = []
    for i, (yy, xx, r) in enumerate(sites):
        y0 = int(np.clip(yy - CROP // 2, 0, h - CROP))
        x0 = int(np.clip(xx - CROP // 2, 0, w - CROP))
        a = off[y0:y0 + CROP, x0:x0 + CROP]
        b = on[y0:y0 + CROP, x0:x0 + CROP]
        ra, fa = edge_chroma(a)
        rb, fb = edge_chroma(b)

        def pct(x0v: float, x1v: float) -> float:
            return (x0v - x1v) / x0v * 100.0 if x0v and np.isfinite(x0v) and x0v > 0 else float("nan")

        rdrop, fdrop = pct(ra, rb), pct(fa, fb)
        tag = "CENTRE-CONTROL" if i == len(sites) - 1 else f"corner{i + 1}"
        print(f"{tag:<16}{x0:>6}{y0:>6}{r:>8.3f}"
              f"{ra:>10.4f}{rb:>9.4f}{rdrop:>9.1f}%"
              f"{fa:>10.4f}{fb:>9.4f}{fdrop:>10.1f}%")
        rows.append((tag, x0, y0, r, rdrop, fdrop))

        # Side-by-side at 1:1. The display scale is taken from the OFF arm's own
        # crop, so the picture is actually visible on a dark subject, and the
        # SAME scale is applied to both arms so the eye compares renders and not
        # two gradings. A global scale rendered these crops solid black.
        scale = 1.0 / max(float(np.percentile(a[:, :, 1], 99.5)), 1.0)
        panel = np.zeros((CROP, CROP * 2 + 8, 3), np.uint8)
        for j, arm in enumerate((a, b)):
            disp = srgb_oetf(np.clip(arm.astype(np.float64) * scale, 0, 1))
            panel[:, j * (CROP + 8):j * (CROP + 8) + CROP] = (disp * 255 + 0.5).astype(np.uint8)
        Image.fromarray(panel).save(OUT / f"{tag}_x{x0}_y{y0}.png")

    corners = [r for r in rows if r[0].startswith("corner") and np.isfinite(r[4])]
    centre = [r for r in rows if r[0] == "CENTRE-CONTROL" and np.isfinite(r[4])]
    print()
    if corners and centre:
        mc = float(np.mean([r[4] for r in corners]))
        mf = float(np.mean([r[5] for r in corners if np.isfinite(r[5])]))
        print(f"mean corner RIM reduction {mc:.1f}%   corner FLAT control {mf:.1f}%"
              f"   centre rim {centre[0][4]:.1f}%")
        if not (mc > centre[0][4]):
            print("RADIAL ORDERING FAILED: the centre changed as much as the "
                  "corners. That is not lateral CA; do not label it as such.")
        elif not (mc > 2.0 * mf):
            print("CONFOUNDED: the flat control fell nearly as much as the rims, "
                  "so this is consistent with resampling smoothing rather than "
                  "fringe removal. Do not cite the rim number as aberration.")
        else:
            print("HELD ON BOTH CONTROLS: the reduction is radial (corners >> "
                  "centre) and rim-specific (rims >> flat), which is the "
                  "signature of lateral CA and not of resampling smoothing.")
    print(f"\nwrote {len(rows)} 1:1 PNG panels to {OUT}  (left = CA OFF, right = CA ON)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
