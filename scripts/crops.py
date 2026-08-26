"""Rule-sited 100% crops for print judgement, across arms of one subject.

WHY THIS EXISTS
---------------
This project has a documented history of green metrics over bad images, so the
print instrument is pictures. But a picture chosen after seeing the result is an
argument, not evidence: if I pick the crop site by eye I will pick the site that
makes my point. So every site below is the argmax or argmin of a stated
statistic over a fixed grid, computed before anything is displayed.

THE THREE SITES, AND WHY THESE THREE
------------------------------------
Each answers a question a different failure would dodge.

  edge  -- WHERE THE HALO LIVES. argmax of COARSE-scale gradient magnitude
           (Gaussian derivative, sigma=8 px) averaged per tile. Coarse on
           purpose: a fine-scale gradient finds the sharpest texture in the
           frame, which is usually not an occlusion boundary. Blurring first
           makes a silhouette outrank a fibre. This is where "a badly cut-out
           sticker" would show.

  flat  -- WHERE MERGE NOISE LIVES. argmin of per-tile std, restricted to tiles
           whose median luminance is above the frame's 20th percentile. The
           restriction is load-bearing: the flattest tile in any of these frames
           is black background, which has no merge noise in it because it has no
           merge in it. We want the flattest LIT region.

  sharp -- WHERE A BLUR WOULD SHOW. argmax of per-tile mean |Laplacian|. Any
           "fix" that works by softening loses most exactly here, which is the
           failure mode ORCH's acuity column exists to catch and which a halo
           crop alone would let through.

THE RULE THAT MAKES ARMS COMPARABLE
-----------------------------------
**Sites are computed ONCE, on one nominated arm, and applied unchanged to every
other arm.** If each arm sited itself, arm A's crop and arm B's crop would be
different places and the side-by-side would be meaningless -- the same reason a
paired image comparison registers with an integer shift rather than letting each
window float. `--site-on` names that arm; it defaults to the reference.

Likewise the display transform is FIXED and stated, never per-image autoscale.
Autoscaling each arm independently would hide precisely the level shifts (a
raised black point, a veil) that we are looking for.

OUTPUT
------
Per site: a 16-bit PNG per arm at native DN (the lossless record), an 8-bit
viewable PNG per arm, and one side-by-side composite. Never JPEG -- at 100% on
an artifact you would be looking at the codec.
"""

import argparse
import sys
from pathlib import Path

import cv2
import imageio.v3 as iio
import numpy as np
import scipy.ndimage as ndi
import tifffile

CROP = 512      # 1:1 pixels. Never resampled.
GRID = 256      # siting grid; independent of CROP so sites can be dense
SIGMA_COARSE = 8.0
LIT_PCT = 20.0  # matches accept.py's lit-population definition


def read_u16_rgb(p: Path) -> np.ndarray:
    """16-bit RGB TIFF, or refuse. PIL.Image.open silently downconverts these
    to 8 bits and has corrupted results in this project before."""
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p.name}: dtype {a.dtype}, expected uint16"
    assert a.ndim == 3 and a.shape[2] == 3, f"{p.name}: shape {a.shape}, expected HxWx3"
    return a


def tile_stat(v: np.ndarray, fn) -> np.ndarray:
    """fn applied over a GRID x GRID tiling, as a 2-D array of tile scores."""
    h, w = v.shape
    th, tw = h // GRID, w // GRID
    out = np.empty((th, tw), np.float64)
    for i in range(th):
        row = v[i * GRID:(i + 1) * GRID]
        for j in range(tw):
            out[i, j] = fn(row[:, j * GRID:(j + 1) * GRID])
    return out


def write_u16_png(p: Path, rgb: np.ndarray) -> None:
    """16-bit RGB PNG, verified on the way out.

    imageio routes this through Pillow, which cannot encode 16-bit RGB at all
    (`Cannot handle this data type: (1,1,3), <u2`). cv2 can, but the failure
    mode that matters here is not an exception -- it is a writer that quietly
    drops to 8 bits, which is the exact corruption this project has been bitten
    by before. So the file is read back and compared, and a lossy write is a
    hard error rather than a lossless-looking filename."""
    ok = cv2.imwrite(str(p), rgb[:, :, ::-1])  # cv2 is BGR
    assert ok, f"cv2 failed to write {p}"
    back = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    assert back is not None and back.dtype == np.uint16, \
        f"{p.name}: round-tripped as {None if back is None else back.dtype}, not uint16"
    assert np.array_equal(back[:, :, ::-1], rgb), f"{p.name}: 16-bit PNG did not round-trip"


def site_all(img: np.ndarray) -> dict:
    """The three sites, as (y, x) top-left crop origins. Deterministic.

    Sites are chosen in the order edge -> sharp -> flat, and each choice
    EXCLUDES the tiles already covered by an earlier crop. Without that,
    `edge` and `sharp` both picked tile (1408, 2944) on 109MSDCF -- the
    strongest silhouette in a frame is often also its sharpest detail -- and
    two of the three questions collapsed into one picture. The order is by
    priority: the halo is the defect that disqualifies prints, so it gets first
    refusal on the frame."""
    g = img[:, :, 1].astype(np.float32)
    lum = img.astype(np.float32).mean(2)
    lit_floor = np.percentile(lum, LIT_PCT)

    # edge: coarse gradient magnitude -> silhouettes, not texture
    gy = ndi.gaussian_filter(g, SIGMA_COARSE, order=(1, 0))
    gx = ndi.gaussian_filter(g, SIGMA_COARSE, order=(0, 1))
    coarse = np.hypot(gy, gx)

    lap = np.abs(ndi.laplace(g))
    lit = tile_stat(lum, lambda t: float(np.median(t)))

    plan = [
        ("edge", tile_stat(coarse, lambda t: float(t.mean())), "max", None),
        ("sharp", tile_stat(lap, lambda t: float(t.mean())), "max", None),
        ("flat", tile_stat(g, lambda t: float(t.std())), "min", lit_floor),
    ]

    h, w = g.shape
    taken = np.zeros(plan[0][1].shape, bool)
    out = {}
    for name, s, sense, floor in plan:
        s = s.astype(np.float64).copy()
        blocked = np.inf if sense == "min" else -np.inf
        if floor is not None:
            # Exclude unlit tiles rather than letting black background win.
            s[lit < floor] = blocked
        s[taken] = blocked
        idx = np.argmin(s) if sense == "min" else np.argmax(s)
        ti, tj = np.unravel_index(idx, s.shape)
        # Centre the crop on the winning tile, clamped into the frame.
        cy, cx = ti * GRID + GRID // 2, tj * GRID + GRID // 2
        y = int(np.clip(cy - CROP // 2, 0, h - CROP))
        x = int(np.clip(cx - CROP // 2, 0, w - CROP))
        out[name] = (y, x, float(s[ti, tj]))
        # Reserve every tile this crop covers, so the next site is elsewhere.
        taken[y // GRID:(y + CROP) // GRID + 1, x // GRID:(x + CROP) // GRID + 1] = True
    return out


def to_view(crop: np.ndarray, mode: str, scale: float) -> np.ndarray:
    """FIXED display transform -- identical for every arm, stated in the sidecar.
    Deliberately not per-image autoscale, which would hide level shifts."""
    x = crop.astype(np.float64) / 65535.0
    if mode == "linear-srgb":
        x = np.clip(x * scale, 0, 1)
        x = np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)
    elif mode == "none":
        x = np.clip(x * scale, 0, 1)
    else:
        raise SystemExit(f"unknown --display {mode}")
    return (x * 255.0 + 0.5).astype(np.uint8)


def label(bgr: np.ndarray, text: str) -> np.ndarray:
    out = bgr.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], 26), (0, 0, 0), -1)
    cv2.putText(out, text, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+", type=Path, help="arm directories")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--site-on", help="arm whose image fixes the crop sites (default: --ref)")
    ap.add_argument("--ref", required=True, help="arm shown first in composites")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--display", default="linear-srgb", choices=["linear-srgb", "none"])
    ap.add_argument("--scale", type=float, default=1.0,
                    help="fixed exposure scale before the display transform")
    a = ap.parse_args()

    arms = {}
    for d in a.dirs:
        for t in d.glob(f"{a.subject}--*.tiff"):
            arms[t.name[len(a.subject) + 2:-5]] = t
    if not arms:
        raise SystemExit(f"no {a.subject}--*.tiff under {', '.join(str(d) for d in a.dirs)}")
    if a.ref not in arms:
        raise SystemExit(f"--ref {a.ref} not among arms: {', '.join(sorted(arms))}")

    site_arm = a.site_on or a.ref
    if site_arm not in arms:
        raise SystemExit(f"--site-on {site_arm} not among arms: {', '.join(sorted(arms))}")

    a.out.mkdir(parents=True, exist_ok=True)
    print(f"subject   : {a.subject}")
    print(f"arms      : {', '.join(sorted(arms))}")
    print(f"sited on  : {site_arm}   (sites applied UNCHANGED to every arm)")

    sites = site_all(read_u16_rgb(arms[site_arm]))
    for k, (y, x, s) in sites.items():
        print(f"  {k:6s} y={y:5d} x={x:5d}  score={s:.4g}")

    order = [a.ref] + sorted(k for k in arms if k != a.ref)
    lines = [f"subject: {a.subject}", f"sited on: {site_arm}",
             f"display: {a.display} scale={a.scale} (FIXED across arms)",
             f"crop: {CROP}x{CROP} at 100%, never resampled", ""]

    for name, (y, x, score) in sites.items():
        panels = []
        for arm in order:
            crop = read_u16_rgb(arms[arm])[y:y + CROP, x:x + CROP]
            write_u16_png(a.out / f"{a.subject}--{name}--{arm}-16bit.png", crop)
            view = to_view(crop, a.display, a.scale)
            iio.imwrite(a.out / f"{a.subject}--{name}--{arm}.png", view)
            panels.append(label(view[:, :, ::-1], f"{arm}  [{name}]")[:, :, ::-1])
        sep = np.full((CROP, 4, 3), 255, np.uint8)
        comp = panels[0]
        for p in panels[1:]:
            comp = np.hstack([comp, sep, p])
        iio.imwrite(a.out / f"{a.subject}--{name}--COMPOSITE.png", comp)
        lines.append(f"{name}: y={y} x={x} score={score:.6g} arms={' | '.join(order)}")

    (a.out / f"{a.subject}--SITES.txt").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
