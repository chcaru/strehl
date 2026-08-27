"""Look at the smooth-tone crop my GOOD verdicts actually rested on.

ORCH's finding is that a crop chosen by maximum high-frequency energy cannot
speak to smooth-tone defects.  My lane is NOT blind in that way: compare.py
picks its FLAT site with `np.argmin(src)` -- the block with the LEAST
high-frequency energy anywhere in the frame -- and that is precisely the
complementary crop.

That is not a defence, because having the right sample did not help.  The only
statistic I ran on it is `tri.pixel_noise`, the residual after a 3x3 MEDIAN.
A 3x3 median passes anything much larger than 3 px through untouched, so the
residual at a 40-100 px dust disc is approximately zero.  I had the correct
crop and an instrument band-limited to about one pixel, and I called the field
clean on its silence.

So: LOOK first.  ORCH's dust was "blatant under a 30x linear stretch" and an
eye at 1:1 beat four statistics tonight.  This renders every FLAT tile, both
arms, as a background-subtracted stretch, with the stretch gain STATED on each
tile so nothing here can be read as a bare "clean".

The tiles are camera-linear 16-bit, straight from compare.py's npz cache -- no
tone curve, no PIL, no 8-bit truncation anywhere in the path.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402

TILES = os.path.join(tri.OUT, "tiles")
OUT = os.path.join(tri.OUT, "smooth")
BG_SIGMA = 64.0    # >> dust scale (40-100 px), so the disc SURVIVES detrending
SHOW_DN = 40.0     # full 8-bit swing maps to +/- this many DN


def detrend(t: np.ndarray, sigma: float = BG_SIGMA) -> np.ndarray:
    """Remove illumination, keep anything at or below the dust scale.

    THE HAZARD ORCH JUST DOCUMENTED IS HERE: a detrending window comparable to
    the feature you are probing is a high-pass that deletes it, and the silence
    then reads as absence.  Their fixed 65-tap window gave a planted seam a
    gain of exactly 1.0x.  `recovery()` below measures this rather than
    assuming it, and the number is printed.
    """
    from scipy import ndimage
    return t - ndimage.gaussian_filter(t.astype(np.float32), sigma)


def recovery(shape: tuple[int, int], radius: float, depth_dn: float) -> float:
    """What fraction of a planted disc of this size SURVIVES detrend()?

    A gain near 1.0 means the detrend is transparent to the feature.  A gain
    near 0 means the filter ate the thing being probed, which is the failure
    that makes silence meaningless.  Anchored: a plant that does not land
    raises instead of returning a flattering number.
    """
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    disc = ((yy - h / 2) ** 2 + (xx - w / 2) ** 2) <= radius ** 2
    assert disc.sum() > 0, "PLANT DID NOT LAND -- disc is empty"
    flat = np.full((h, w), 60000.0, np.float32)
    flat[disc] -= depth_dn
    got = -detrend(flat)[disc].mean()
    assert np.isfinite(got), "PLANT DID NOT LAND -- non-finite recovery"
    return float(got / depth_dn)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    files = sorted(f for f in os.listdir(TILES) if f.endswith(".FLAT.npz"))
    if not files:
        return int(print("no FLAT tiles cached") or 1)

    # ---- commissioning: state the gain BEFORE reading any tile -------------
    print("DETREND RECOVERY (fraction of a planted disc that survives, "
          f"BG_SIGMA={BG_SIGMA:g}):")
    for rad in (20.0, 35.0, 50.0):
        g = recovery((512, 512), rad, 20.0)
        print(f"  disc r={rad:4.0f} px  ->  {g:5.3f}"
              f"{'   <== FILTER ATE IT' if g < 0.5 else ''}")

    rows = []
    for fn in files:
        sub = fn[:-len(".FLAT.npz")]
        z = np.load(os.path.join(TILES, fn))
        for arm in ("merge", "frame"):
            t = z[arm].astype(np.float32)
            d = detrend(t)
            from scipy import ndimage
            # boost disc-shaped excursions at the dust scale
            sm = ndimage.gaussian_filter(d, 8.0)
            rows.append({
                "subject": sub, "arm": arm, "tile": t, "res": d,
                "mean": float(t.mean()),
                "darkest": float(sm.min()),
                "brightest": float(sm.max()),
                "res_sd": float(d.std()),
            })

    # ---- contact sheet, merge arm, stretch gain stamped on every tile ------
    merge = [r for r in rows if r["arm"] == "merge"]
    cols, cell, pad, hdr = 6, 260, 6, 54
    n = len(merge)
    rws = (n + cols - 1) // cols
    W = cols * (cell + pad) + pad
    H = hdr + rws * (cell + pad + 26) + pad
    sheet = Image.new("RGB", (W, H), (16, 16, 16))
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, 10), "FLAT site (lowest high-frequency energy in frame), "
            "MERGE arm, camera-linear.", fill=(235, 235, 235))
    dr.text((pad, 26), f"background removed at sigma={BG_SIGMA:g} px; "
            f"grey = local background, full swing = +/-{SHOW_DN:g} DN of 65535 "
            f"(x{65535 / (2 * SHOW_DN):.0f} linear stretch)", fill=(190, 190, 190))
    for i, r in enumerate(merge):
        v = np.clip(r["res"] / SHOW_DN * 127.0 + 128.0, 0, 255).astype(np.uint8)
        im = Image.fromarray(v).resize((cell, cell), Image.BILINEAR)
        x = pad + (i % cols) * (cell + pad)
        y = hdr + (i // cols) * (cell + pad + 26)
        sheet.paste(im, (x, y))
        dr.text((x, y + cell + 2), r["subject"][:34], fill=(225, 225, 225))
        dr.text((x, y + cell + 13),
                f"dark {r['darkest']:+6.1f} DN  sd {r['res_sd']:5.2f}",
                fill=(170, 170, 170))
    p = os.path.join(OUT, "flat-smooth-merge.png")
    sheet.save(p)
    print(f"\nwrote {p}  ({W}x{H}, {len(merge)} subjects)")

    print("\ndeepest smooth-scale DARK excursion, both arms, in DN "
          "(sorted; merge-only would not separate optics from merge):")
    print(f"  {'subject':36s} {'merge':>8s} {'frame':>8s} {'m-f':>8s}")
    by = {}
    for r in rows:
        by.setdefault(r["subject"], {})[r["arm"]] = r
    for sub in sorted(by, key=lambda s: by[s]["merge"]["darkest"]):
        m, f = by[sub]["merge"]["darkest"], by[sub]["frame"]["darkest"]
        print(f"  {sub:36s} {m:8.1f} {f:8.1f} {m - f:8.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
