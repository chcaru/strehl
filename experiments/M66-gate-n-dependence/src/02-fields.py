"""M66 step 2 - decode each stack once and cache its regularised focus cube.

The pipeline is M52's verified re-implementation of the shipped operator, with
every constant parsed from the crate rather than retyped:

    luma   = 0.5 * (max(G1-black,0) + max(G2-black,0))            plane.rs
    grad   = 0.125 * hypot(Sobel_x, Sobel_y), replicate border    focus.rs
    focus  = clamped_box(grad, WINDOW_RADIUS) / max(sigma_L, EPS) focus.rs + noise.rs
    reg    = clamped_box(focus, REGULARISER_RADIUS)               merge.rs

Nothing about the frame count enters any line of it. That is the point: the
cube is computed once per stack and every N in the sweep is a subset of it, so
the operator, the noise model, the regulariser and the pixel set are identical
across N by construction.

Caches float32 at full plane resolution AND on a 4x-decimated grid. Control K5
compares the two. `data/` is gitignored and regenerable.

RULE 32: `raw_image_visible` is a VIEW. Every read copies inside the `with`.
"""

import json
import pathlib
import sys
import time

import numpy as np
import rawpy
from scipy.ndimage import uniform_filter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from m66 import (  # noqa: E402
    BASE_ISO,
    BLACK,
    CORPUS,
    DATA,
    GAIN_DIVISOR,
    OUT,
    READ_NOISE_E_HIGH,
    READ_NOISE_E_LOW,
    REGULARISER_RADIUS,
    SECOND_BASE_ISO,
    SIGMA_EPS,
    SOBEL_SCALE,
    WINDOW_RADIUS,
    banner,
)

DECIMATE = 4
_COUNT_CACHE = {}


def counts(n, r):
    i = np.arange(n)
    return (np.minimum(i + r, n - 1) - np.maximum(i - r, 0) + 1).astype(np.float64)


def clamped_box(a, r):
    """Mean over a (2r+1)^2 window intersected with the plane -- boxfilter.rs."""
    n = 2 * r + 1
    s = uniform_filter(a, size=n, mode="constant", cval=0.0) * float(n * n)
    key = (a.shape, r)
    d = _COUNT_CACHE.get(key)
    if d is None:
        d = counts(a.shape[0], r)[:, None] * counts(a.shape[1], r)[None, :]
        _COUNT_CACHE[key] = d
    return s / d


def sobel_mag(a):
    p = np.pad(a, 1, mode="edge")

    def at(dy, dx):
        return p[1 + dy : 1 + dy + a.shape[0], 1 + dx : 1 + dx + a.shape[1]]

    gx = at(-1, 1) + 2.0 * at(0, 1) + at(1, 1) - at(-1, -1) - 2.0 * at(0, -1) - at(1, -1)
    gy = at(1, -1) + 2.0 * at(1, 0) + at(1, 1) - at(-1, -1) - 2.0 * at(-1, 0) - at(-1, 1)
    return np.hypot(SOBEL_SCALE * gx, SOBEL_SCALE * gy)


def green_luma_sigma(luma, iso):
    g = max(iso, BASE_ISO) / GAIN_DIVISOR
    rn = READ_NOISE_E_HIGH if iso >= SECOND_BASE_ISO else READ_NOISE_E_LOW
    read_dn = rn * g
    var = g * np.maximum(luma, 0.0) + read_dn * read_dn
    return np.sqrt(0.25 * (var + var))


def luma_of(path):
    with rawpy.imread(path) as rr:
        v = rr.raw_image_visible
        h = (v.shape[0] // 2) * 2
        w = (v.shape[1] // 2) * 2
        g1 = np.array(v[0:h:2, 1:w:2], dtype=np.float64)
        g2 = np.array(v[1:h:2, 0:w:2], dtype=np.float64)
    return 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))


def regularised_field(path, iso):
    luma = luma_of(path)
    f = clamped_box(sobel_mag(luma), WINDOW_RADIUS)
    f /= np.maximum(green_luma_sigma(luma, iso), SIGMA_EPS)
    return clamped_box(f, REGULARISER_RADIUS).astype(np.float32)


def iso_of(path):
    import exifread

    with open(path, "rb") as fh:
        tags = exifread.process_file(fh, stop_tag="EXIF ISOSpeedRatings", details=False)
    for key in ("EXIF ISOSpeedRatings", "Image ISOSpeedRatings"):
        if key in tags:
            v = tags[key].values
            return float(v[0] if isinstance(v, list) else v)
    raise SystemExit(f"no ISO in EXIF: {path}")


def build(stack, keep_full):
    d = pathlib.Path(CORPUS) / stack
    files = sorted(str(p) for p in d.iterdir() if p.suffix.upper() == ".ARW")
    isos = sorted({iso_of(p) for p in files})
    if len(isos) != 1:
        raise SystemExit(f"{stack}: ISO is not constant across the stack: {isos}")
    iso = isos[0]
    t0 = time.time()
    d4, full = [], []
    for i, p in enumerate(files):
        r = regularised_field(p, iso)
        d4.append(np.ascontiguousarray(r[::DECIMATE, ::DECIMATE]))
        if keep_full:
            full.append(r)
        if i == 0:
            shape = r.shape
    cube4 = np.stack(d4)
    DATA.mkdir(parents=True, exist_ok=True)
    np.save(DATA / f"{stack}-d{DECIMATE}.npy", cube4)
    if keep_full:
        np.save(DATA / f"{stack}-full.npy", np.stack(full))
    dt = time.time() - t0
    print(
        f"  {stack:<15} N={len(files):>3}  ISO {iso:>5.0f}  plane {shape[0]}x{shape[1]}"
        f"  d{DECIMATE} {cube4.shape[1]}x{cube4.shape[2]}"
        f"  full={'yes' if keep_full else 'no':<3}  [{dt:.0f}s]"
    )
    return {
        "stack": stack,
        "dir": str(d),
        "frames": len(files),
        "iso": iso,
        "plane_shape": list(shape),
        "d4_shape": list(cube4.shape[1:]),
        "kept_full": bool(keep_full),
        "seconds": dt,
    }


# 109MSDCF and coffee-bubbles carry control K5, so they keep a full-resolution cube.
PLAN = [
    ("109MSDCF", True),
    ("coffee-bubbles", True),
    ("119MSDCF", False),
    ("113MSDCF", False),
    ("112MSDCF", False),
    ("foam", False),
    ("coffee-bean", False),
    ("bee-1", False),
]

if __name__ == "__main__":
    only = sys.argv[1:] or [s for s, _ in PLAN]
    banner("M66 step 2 - regularised focus cubes, one decode per stack")
    meta_path = OUT / "02-fields.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    for stack, keep_full in PLAN:
        if stack not in only:
            continue
        meta[stack] = build(stack, keep_full)
        OUT.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nwrote {meta_path}")
