"""M95 arm 4, corrected instrument. Supersedes x1_pairs.py, which is kept as a record.

THREE DEFECTS IN x1_pairs.py, all found by its own controls:

 1. REGISTRATION WRAPAROUND. The cross-correlation argmax was decoded over the whole
    circular FFT range, so a wraparound peak was reported as a valid offset. D printed
    max|off| = 124 px and C printed 279 px from a +-24 px search, which is impossible.
    Fixed: the argmax is restricted to the physically valid 0..2*SEARCH window.

 2. NO GEOMETRIC PREDICTION. C's field of view is scaled to 0.9315, so a scene point at
    radius r in B0 sits at radius r/0.9315 in C -- up to 300 px away at the frame edge,
    far outside any sane blind search. Fixed: the tile position is predicted through the
    known coverage scale and the search only refines it.

 3. TRUNCATED BLUR KERNEL. gauss_blur used radius ceil(4*sigma), so sigma = 0.25 px got a
    3-tap kernel of [3.4e-4, 0.99932, 3.4e-4] -- a delta, not a blur. The control duly
    read -0.0011 dex and looked like an instrument floor when it was a kernel artifact.
    Fixed: the blur is applied in the frequency domain as exp(-2 pi^2 sigma^2 f^2), which
    is exact for a continuous Gaussian and cannot truncate.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
R = r"C:\dev\strehl-out\M95-resample"

BAND = (0.30, 0.48)
LOWBAND = (0.02, 0.10)
TILE = 256
NTILES = 40
SEARCH = 24
CC_FLOOR = 0.50

IMAGES = {
    "A": dict(path=os.path.join(R, "rawpy-A.npy"), k=1.0, what="rawpy/LibRaw decode, no strehl code"),
    "B0": dict(path=os.path.join(R, "single-noalign.tif"), k=1.0, what="strehl 1 frame, NO resample"),
    "B1": dict(path=os.path.join(R, "single-strehl.tif"), k=0.9974, what="strehl 1 frame, ONE CatmullRom gather"),
    "D": dict(path=os.path.join(R, "merge-g0-noalign.tif"), k=1.0, what="strehl 299f gate 0, NO resample"),
    "C": dict(path=os.path.join(R, "merge-g0-linear.tif"), k=0.9315, what="strehl 299f gate 0, gather + 0.9315 zoom"),
}


def load_luma(path):
    if path.endswith(".npy"):
        rgb = np.load(path)
    else:
        import tifffile

        rgb = tifffile.imread(path)
    rgb = rgb.astype(np.float32)
    return 0.25 * rgb[..., 0] + 0.50 * rgb[..., 1] + 0.25 * rgb[..., 2]


def pick_tiles(img, n=NTILES, tile=TILE):
    h, w = img.shape
    m = 3 * tile
    scored = []
    for y in range(m, h - m - tile, tile):
        for x in range(m, w - m - tile, tile):
            t = img[y : y + tile, x : x + tile]
            scored.append((float(np.diff(t, axis=0).var() + np.diff(t, axis=1).var()), y, x))
    scored.sort(reverse=True)
    taken = []
    for s, y, x in scored:
        if all(abs(y - ty) >= tile or abs(x - tx) >= tile for _, ty, tx in taken):
            taken.append((s, y, x))
        if len(taken) == n:
            break
    return [(y, x) for _, y, x in taken]


def predict(y, x, k, shape, tile=TILE):
    """DEFECT 2 FIX. The render shows a fraction k of the field stretched to full
    dimensions, so a scene point at radius r from the centre appears at r/k."""
    h, w = shape
    cy, cx = h / 2.0, w / 2.0
    ty, tx = y + tile / 2.0, x + tile / 2.0
    py = cy + (ty - cy) / k - tile / 2.0
    px = cx + (tx - cx) / k - tile / 2.0
    return int(round(py)), int(round(px))


def register(ref, img, y, x, k, tile=TILE, search=SEARCH):
    """Integer-only registration: sub-pixel resampling would add blur to the exact
    quantity being measured."""
    a = ref[y : y + tile, x : x + tile]
    a = a - a.mean()
    h, w = img.shape
    py, px = predict(y, x, k, img.shape, tile)
    y0, x0 = py - search, px - search
    span = 2 * search + tile
    if y0 < 0 or x0 < 0 or y0 + span > h or x0 + span > w:
        return None
    big = img[y0 : y0 + span, x0 : x0 + span]
    cc = np.fft.irfft2(np.fft.rfft2(a, s=big.shape).conj() * np.fft.rfft2(big - big.mean()), s=big.shape)
    # DEFECT 1 FIX: only 0..2*search is a physically reachable offset; the rest is
    # circular wraparound and must never be chosen.
    valid = cc[: 2 * search + 1, : 2 * search + 1]
    iy, ix = np.unravel_index(np.argmax(valid), valid.shape)
    oy, ox = y0 + iy, x0 + ix
    b = img[oy : oy + tile, ox : ox + tile]
    if b.shape != (tile, tile):
        return None
    an = a / (np.linalg.norm(a) + 1e-9)
    bn = (b - b.mean()) / (np.linalg.norm(b - b.mean()) + 1e-9)
    return float((an * bn).sum()), oy, ox, int(iy - search), int(ix - search)


_W = {}


def window(n):
    if n not in _W:
        w = np.hanning(n).astype(np.float64)
        _W[n] = np.outer(w, w)
    return _W[n]


def freqs(n):
    c = n // 2
    yy, xx = np.mgrid[0:n, 0:n]
    return np.sqrt((yy - c) ** 2 + (xx - c) ** 2) / n


def band_ratio(t, k):
    t = t.astype(np.float64)
    t = t - t.mean()
    f = np.fft.fftshift(np.fft.fft2(t * window(t.shape[0])))
    p = (f.real**2 + f.imag**2) / t.size
    fr = freqs(t.shape[0])
    hi = (fr >= BAND[0] * k) & (fr < BAND[1] * k)
    lo = (fr >= LOWBAND[0] * k) & (fr < LOWBAND[1] * k)
    return float(np.log10(p[hi].mean()) - np.log10(p[lo].mean()))


def fourier_blur(t, sigma):
    """DEFECT 3 FIX. Exact continuous-Gaussian blur, applied as a transfer function.
    A sampled kernel truncates at small sigma and silently becomes a delta."""
    n = t.shape[0]
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    h = np.exp(-2.0 * np.pi**2 * sigma**2 * (fy**2 + fx**2))
    return np.fft.ifft2(np.fft.fft2(t.astype(np.float64)) * h).real


def main():
    want = [a for a in sys.argv[1:]] or list(IMAGES)
    imgs = {}
    for name in want:
        p = IMAGES[name]["path"]
        if not os.path.exists(p):
            print(f"  MISSING {name}: {p}")
            continue
        imgs[name] = load_luma(p)
    if "B0" not in imgs:
        print("B0 is the tile-selection reference and is required")
        return 2

    tiles = pick_tiles(imgs["B0"])
    print(f"K9: {len(tiles)} sharpest {TILE}px tiles by gradient ON B0 (the single frame)\n")

    print(f"{'term':4s} {'n':>3s} {'log10(hi/lo)':>13s} {'sd':>7s} {'reg cc':>7s} {'refine dy,dx':>13s}  what")
    rows, meta = {}, {}
    for name in want:
        if name not in imgs:
            continue
        img, k = imgs[name], IMAGES[name]["k"]
        vals, ccs, refines, dropped = [], [], [], 0
        for y, x in tiles:
            if name == "B0":
                cc, oy, ox, ry, rx = 1.0, y, x, 0, 0
            else:
                r = register(imgs["B0"], img, y, x, k)
                if r is None:
                    dropped += 1
                    continue
                cc, oy, ox, ry, rx = r
            if cc < CC_FLOOR:
                dropped += 1
                continue
            vals.append(band_ratio(img[oy : oy + TILE, ox : ox + TILE], k))
            ccs.append(cc)
            refines.append(max(abs(ry), abs(rx)))
        rows[name] = np.array(vals)
        meta[name] = dict(n=len(vals), dropped=dropped, mean_cc=float(np.mean(ccs)), max_refine=int(max(refines)))
        print(
            f"{name:4s} {len(vals):3d} {np.mean(vals):+13.4f} {np.std(vals):7.4f} "
            f"{np.mean(ccs):7.4f} {max(refines):13d}  {IMAGES[name]['what']}"
        )
        if dropped:
            print(f"       ({dropped} tiles dropped: cc < {CC_FLOOR} or off-frame)")

    print("\n--- K6 / K13: planted Fourier-exact Gaussian blur on B0's own tiles ---")
    planted = {}
    for s in (0.10, 0.25, 0.50, 1.00):
        v = np.array([band_ratio(fourier_blur(imgs["B0"][y : y + TILE, x : x + TILE], s), 1.0) for y, x in tiles])
        d = v - rows["B0"]
        planted[s] = float(d.mean())
        print(f"  sigma = {s:4.2f} px  ->  {d.mean():+.4f} dex   (sd {d.std():.4f})")

    print("\n--- K7 null ---")
    nullv = float((rows["B0"] - rows["B0"]).mean())
    print(f"  B0 vs B0 : {nullv:+.6f} dex")

    print("\n--- deltas, common tiles only ---")
    deltas = {}
    base = "B0"
    pairs = [("B0", "B1"), ("B0", "D"), ("D", "C"), ("B0", "C"), ("A", "B0")]
    for u, v in pairs:
        if u not in rows or v not in rows or rows[u].size == 0 or rows[v].size == 0:
            continue
        n = min(rows[u].size, rows[v].size)
        d = float(rows[v][:n].mean() - rows[u][:n].mean())
        deltas[f"{u}->{v}"] = d
        print(f"  {u:2s} -> {v:2s} : {d:+.4f} dex   ({10**abs(d):.3f}x power, {10**(abs(d)/2):.3f}x amplitude)")

    print("\n--- K8 anchor separation gate ---")
    sep = abs(planted[1.00] - nullv)
    ok = sep >= 0.30
    print(f"  null {nullv:+.4f} .. sigma=1.0 px {planted[1.00]:+.4f}  ->  separation {sep:.4f} dex")
    print(f"  gate (>= 0.30 dex): {'PASS' if ok else 'FAIL'}")
    for kk, vv in deltas.items():
        inside = min(nullv, planted[1.00]) <= vv <= max(nullv, planted[1.00])
        print(f"  {kk:8s} {vv:+.4f} inside anchors: {inside}")

    json.dump(
        dict(
            band=BAND,
            lowband=LOWBAND,
            tile=TILE,
            per_image={k: dict(mean=float(v.mean()), sd=float(v.std()), **meta[k]) for k, v in rows.items()},
            deltas=deltas,
            planted={str(k): v for k, v in planted.items()},
            null=nullv,
            anchor_sep=sep,
            anchor_gate_pass=bool(ok),
            raw={k: v.tolist() for k, v in rows.items()},
            tiles=tiles,
        ),
        open(os.path.join(OUT, "x2_pairs.json"), "w"),
        indent=1,
    )
    print(f"\nwrote {os.path.join(OUT, 'x2_pairs.json')}")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
