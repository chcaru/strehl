"""M95 arm 4 - price each resampling step on the full-resolution path.

Terms (all 7032x4688, 16-bit, LINEAR camera-native, same binary, this session):

  A  = rawpy/LibRaw decode of DSC00150.ARW          no strehl code at all
  B0 = strehl 1-frame, STREHL_ALIGN=0               MHC demosaic, NO resample
  B1 = strehl 1-frame, alignment ON  (k=0.9974)     MHC demosaic, ONE CatmullRom gather
  D  = strehl 299-frame gate 0, STREHL_ALIGN=0      election, NO resample
  C  = strehl 299-frame gate 0, alignment ON (k=0.9315)  election + ONE gather + zoom

B0 -> B1 isolates ONE resample on real data with 0.26% of geometry change.
D  -> C  is the same gather plus the 6.85% coverage zoom.
A  -> B0 is the demosaic-algorithm difference and nothing else.

Every image is integrated over a band scaled by its own coverage factor k, so all
terms cover the same SCENE frequency band without resampling any pixel data.
"""

import json
import os
import sys

import numpy as np

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
R = r"C:\dev\strehl-out\M95-resample"

# band in cyc/px of an UNSCALED (k=1) render
BAND = (0.30, 0.48)
LOWBAND = (0.02, 0.10)
TILE = 256
NTILES = 40
SEARCH = 24  # +-px integer registration search half-width

IMAGES = {
    "A": dict(path=os.path.join(R, "rawpy-A.npy"), k=1.0),
    "B0": dict(path=os.path.join(R, "single-noalign.tif"), k=1.0),
    "B1": dict(path=os.path.join(R, "single-strehl.tif"), k=0.9974),
    "D": dict(path=os.path.join(R, "merge-g0-noalign.tif"), k=1.0),
    "C": dict(path=os.path.join(R, "merge-g0-linear.tif"), k=0.9315),
}


def load_luma(path):
    if path.endswith(".npy"):
        rgb = np.load(path)
    else:
        import tifffile

        rgb = tifffile.imread(path)
    rgb = rgb.astype(np.float32)
    # linear luma; weights are the Bayer site census, not a colour standard
    return 0.25 * rgb[..., 0] + 0.50 * rgb[..., 1] + 0.25 * rgb[..., 2]


def pick_tiles(img, n=NTILES, tile=TILE):
    """K9: sharpest tiles BY GRADIENT ON B0, so the single frame is in focus there.

    Selecting on the merge would flatter the merge."""
    h, w = img.shape
    m = 3 * tile  # keep tiles off the frame edge, where the coverage crop bites
    ys = range(m, h - m - tile, tile)
    xs = range(m, w - m - tile, tile)
    scored = []
    for y in ys:
        for x in xs:
            t = img[y : y + tile, x : x + tile]
            gy = np.diff(t, axis=0)
            gx = np.diff(t, axis=1)
            scored.append((float(gy.var() + gx.var()), y, x))
    scored.sort(reverse=True)
    # spread them: greedily take tiles that do not touch an already-taken one
    taken = []
    for s, y, x in scored:
        if all(abs(y - ty) >= tile or abs(x - tx) >= tile for _, ty, tx in taken):
            taken.append((s, y, x))
        if len(taken) == n:
            break
    return [(y, x) for _, y, x in taken]


def register(ref, img, y, x, tile=TILE, search=SEARCH):
    """K10: integer-only registration. Sub-pixel resampling would add blur to the
    exact quantity being measured (SYNTHESIS: image metrology)."""
    a = ref[y : y + tile, x : x + tile]
    a = a - a.mean()
    h, w = img.shape
    best = (-2.0, 0, 0)
    y0, y1 = y - search, y + search
    x0, x1 = x - search, x + search
    if y0 < 0 or x0 < 0 or y1 + tile > h or x1 + tile > w:
        return None
    big = img[y0 : y1 + tile, x0 : x1 + tile]
    fa = np.fft.rfft2(a, s=big.shape)
    fb = np.fft.rfft2(big - big.mean())
    cc = np.fft.irfft2(fa.conj() * fb, s=big.shape)
    idx = np.unravel_index(np.argmax(cc), cc.shape)
    dy = idx[0] if idx[0] <= search * 2 else idx[0] - cc.shape[0]
    dx = idx[1] if idx[1] <= search * 2 else idx[1] - cc.shape[1]
    dy -= 0
    dx -= 0
    # cc index 0 corresponds to offset (y0, x0)
    oy, ox = y0 + dy, x0 + dx
    if not (0 <= oy <= h - tile and 0 <= ox <= w - tile):
        return None
    b = img[oy : oy + tile, ox : ox + tile]
    an = a / (np.linalg.norm(a) + 1e-9)
    bn = (b - b.mean()) / (np.linalg.norm(b - b.mean()) + 1e-9)
    best = (float((an * bn).sum()), oy - y, ox - x)
    return best


_W = None


def window(tile=TILE):
    global _W
    if _W is None:
        w = np.hanning(tile).astype(np.float64)
        _W = np.outer(w, w)
    return _W


def radial_power(t):
    t = t.astype(np.float64)
    t = t - t.mean()
    f = np.fft.fftshift(np.fft.fft2(t * window(t.shape[0])))
    p = (f.real**2 + f.imag**2) / t.size
    n = t.shape[0]
    c = n // 2
    yy, xx = np.mgrid[0:n, 0:n]
    fr = np.sqrt((yy - c) ** 2 + (xx - c) ** 2) / n  # cyc/px
    return p, fr


def band_ratio(t, k):
    """log10( mean power in the scene high band / mean power in the scene low band ).

    Both bands are scaled by this image's own coverage factor k, so the SAME SCENE
    frequencies are integrated in every term with no pixel data resampled."""
    p, fr = radial_power(t)
    hi = (fr >= BAND[0] * k) & (fr < BAND[1] * k)
    lo = (fr >= LOWBAND[0] * k) & (fr < LOWBAND[1] * k)
    if hi.sum() == 0 or lo.sum() == 0:
        return None
    return float(np.log10(p[hi].mean()) - np.log10(p[lo].mean()))


def gauss_blur(img, sigma):
    r = int(np.ceil(4 * sigma))
    x = np.arange(-r, r + 1, dtype=np.float64)
    g = np.exp(-(x**2) / (2 * sigma**2))
    g /= g.sum()
    out = np.apply_along_axis(lambda m: np.convolve(m, g, mode="same"), 0, img)
    out = np.apply_along_axis(lambda m: np.convolve(m, g, mode="same"), 1, out)
    return out.astype(np.float32)


def main():
    want = sys.argv[1:] if len(sys.argv) > 1 else list(IMAGES)
    imgs = {}
    for name in want:
        p = IMAGES[name]["path"]
        if not os.path.exists(p):
            print(f"MISSING {name}: {p}")
            continue
        imgs[name] = load_luma(p)
        print(f"loaded {name}: {imgs[name].shape} mean={imgs[name].mean():.1f}")

    if "B0" not in imgs:
        print("B0 is the tile-selection reference and is required")
        return 2

    tiles = pick_tiles(imgs["B0"])
    print(f"\nK9 tiles: {len(tiles)} sharpest {TILE}px tiles by gradient on B0")

    # planted-blur variants of B0 (K6 sensitivity, K13 power control)
    planted = {}
    for s in (0.25, 0.5, 1.0):
        planted[f"blur{s}"] = None  # filled per tile, cheaper than blurring 33 MP

    rows = {}
    reg = {}
    for name, img in imgs.items():
        vals, offs, ccs = [], [], []
        for y, x in tiles:
            if name == "B0":
                oy = ox = 0
                cc = 1.0
            else:
                r = register(imgs["B0"], img, y, x)
                if r is None:
                    continue
                cc, oy, ox = r
            t = img[y + oy : y + oy + TILE, x + ox : x + ox + TILE]
            if t.shape != (TILE, TILE):
                continue
            v = band_ratio(t, IMAGES[name]["k"])
            if v is None:
                continue
            vals.append(v)
            offs.append((oy, ox))
            ccs.append(cc)
        rows[name] = np.array(vals)
        reg[name] = dict(
            mean_cc=float(np.mean(ccs)),
            max_abs_off=int(max(max(abs(a), abs(b)) for a, b in offs)) if offs else -1,
            n=len(vals),
        )
        print(
            f"  {name:3s}: n={len(vals):3d}  mean log10(hi/lo) = {np.mean(vals):+.4f}"
            f"   reg cc={reg[name]['mean_cc']:.4f} max|off|={reg[name]['max_abs_off']}px"
        )

    # K6 / K13: plant known blurs on B0's own tiles
    print("\n--- K6/K13 planted blur on B0 tiles (instrument response) ---")
    planted_vals = {}
    for s in (0.25, 0.5, 1.0):
        vals = []
        for y, x in tiles:
            pad = 8
            t = imgs["B0"][y - pad : y + TILE + pad, x - pad : x + TILE + pad]
            tb = gauss_blur(t.astype(np.float64), s)[pad:-pad, pad:-pad]
            vals.append(band_ratio(tb, 1.0))
        planted_vals[s] = np.array(vals)
        d = planted_vals[s] - rows["B0"]
        print(f"  sigma={s:4.2f} px : delta = {d.mean():+.4f} dex   (sd {d.std():.4f})")

    print("\n--- K7 null: B0 against itself ---")
    print(f"  delta = {(rows['B0'] - rows['B0']).mean():+.6f} dex")

    res = dict(
        tiles=tiles,
        band=BAND,
        lowband=LOWBAND,
        tile=TILE,
        per_image={k: dict(mean=float(v.mean()), sd=float(v.std()), n=int(v.size)) for k, v in rows.items()},
        registration=reg,
        planted={str(k): float((v - rows["B0"]).mean()) for k, v in planted_vals.items()},
        raw={k: v.tolist() for k, v in rows.items()},
    )
    with open(os.path.join(OUT, "x1_pairs.json"), "w") as f:
        json.dump(res, f, indent=1)
    print(f"\nwrote {os.path.join(OUT, 'x1_pairs.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
