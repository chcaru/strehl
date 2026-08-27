"""Locate and render the worst individual halo site, not just the corpus statistic.

orch_halo.py reports a median over thousands of profiles, which is the right number for
ranking renders and the wrong artifact for understanding a mechanism. A lane fixing the
halo needs a place to look: an (x,y) in a named master where the defect is strongest, and
a picture of it at a stated gain.

Method: reuse orch_halo's own edge finder and profile machinery unmodified -- same gates,
same normalisation -- but keep the per-profile overshoot instead of collapsing to the
median, then rank sites. Rendering uses a fixed linear window around each crop's own median
so the gain is stated and printed, per the lesson that a per-block percentile stretch makes
severity incomparable between crops.
"""
import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from orch_halo import (BAND, DS, HALF, MIN_STEP_FRAC, PLATEAU_FRAC, bilinear,  # noqa: E402
                       downsample, edge_points, robust_step)

CROP = 420


def png_rgb(a8, path):
    import zlib
    import struct
    h, w, _ = a8.shape
    raw = b"".join(b"\x00" + a8[i].tobytes() for i in range(h))

    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c))

    pathlib.Path(path).write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b""))


def site_overshoots(img, pts, gy, gx, min_step):
    t = np.arange(-HALF, HALF + 1, dtype=np.float32)
    a, b = BAND
    out = []
    for (py, px) in pts:
        g = np.hypot(gy[py, px], gx[py, px])
        if g <= 0:
            continue
        ny, nx = gy[py, px] / g, gx[py, px] / g
        v = bilinear(img, py + t * ny, px + t * nx)
        lo = float(v[:15].mean())
        hi = float(v[-15:].mean())
        step = abs(hi - lo)
        if step < min_step:
            continue
        lf = abs(float(v[:20].mean()) - float(v[20:40].mean()))
        rf = abs(float(v[-20:].mean()) - float(v[-40:-20].mean()))
        if max(lf, rf) > PLATEAU_FRAC * step:
            continue
        p = (v - lo) / (hi - lo)
        oh = float(np.max(p[HALF + a:HALF + b]) - 1.0)
        ol = float(0.0 - np.min(p[HALF - b:HALF - a]))
        out.append((max(oh, ol), py, px, ny, nx, step))
    out.sort(key=lambda r: -r[0])
    return out


def main(argv):
    src = pathlib.Path(argv[0]) if argv else pathlib.Path(
        r"C:\dev\strehl-out\SHIP-V2\tweezers-cpl--SHIP-V2.tiff")
    outdir = pathlib.Path(r"C:\dev\strehl-out\ORCH-HALOSITE")
    outdir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(4242)

    a = tifffile.imread(str(src))
    rgb16 = a[:, :, :3]
    del a
    lum = (0.2126 * rgb16[:, :, 0] + 0.7152 * rgb16[:, :, 1]
           + 0.0722 * rgb16[:, :, 2]).astype(np.float32)
    img = downsample(lum, DS).astype(np.float32)
    del lum
    ms = robust_step(img)
    pts, gy, gx, thr = edge_points(img, rng)
    sites = site_overshoots(img, pts, gy, gx, ms)
    print(f"{src.name}: {len(pts)} edge points, {len(sites)} passed the gates")
    print(f"min_step {ms:.1f} DN (frac {MIN_STEP_FRAC}), plateau frac {PLATEAU_FRAC}")
    if not sites:
        print("no sites")
        return 1

    # Spread the chosen sites out; the top-N by score cluster on one boundary.
    chosen = []
    for s in sites:
        if all(abs(s[1] - c[1]) + abs(s[2] - c[2]) > 200 for c in chosen):
            chosen.append(s)
        if len(chosen) == 4:
            break

    print(f"\n{'rank':>4s} {'overshoot':>10s} {'x':>6s} {'y':>6s} {'step DN':>9s} "
          f"{'normal':>16s}")
    for i, (ov, py, px, ny, nx, step) in enumerate(chosen):
        print(f"{i:4d} {ov:10.4f} {px * DS:6d} {py * DS:6d} {step:9.1f} "
              f"({ny:+.2f},{nx:+.2f})")

    H, W, _ = rgb16.shape
    # One window for every crop, from the whole master, so severity is comparable
    # between crops and the gain is a stated constant rather than a per-block fit.
    lo_g = float(np.percentile(rgb16[::8, ::8], 0.2))
    hi_g = float(np.percentile(rgb16[::8, ::8], 99.8))
    span = hi_g - lo_g
    gain = 255.0 / span
    print(f"\ndisplay window {lo_g:.0f}..{hi_g:.0f} DN (span {span:.0f}), "
          f"gain {gain:.5f} lev/DN, identical for every crop")
    for i, (ov, py, px, ny, nx, step) in enumerate(chosen):
        cy, cx = py * DS, px * DS
        y0 = int(np.clip(cy - CROP // 2, 0, H - CROP))
        x0 = int(np.clip(cx - CROP // 2, 0, W - CROP))
        blk = rgb16[y0:y0 + CROP, x0:x0 + CROP].astype(np.float32)
        v = np.clip((blk - lo_g) * gain, 0, 255)
        clip = float(((blk < lo_g) | (blk > hi_g)).mean())
        name = f"{src.stem}-halo{i}-x{x0}-y{y0}.png"
        png_rgb(v.astype(np.uint8), outdir / name)
        print(f"  wrote {name}   clip {100 * clip:.2f}%")
    print(f"\n-> {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
