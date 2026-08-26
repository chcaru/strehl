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


def silhouette_score(img: np.ndarray) -> np.ndarray:
    """Per-tile density of SUBJECT-AGAINST-BACKGROUND boundary.

    `edge` finds the strongest coarse gradient in the frame, and on a subject
    that fills the frame that is an INTERNAL boundary: on bee-1-cpl it landed in
    the middle of the hair mass, which is the one place the cut-out artifact
    cannot be. But the artifact -- the bright rim that reads as a badly cut-out
    sticker -- lives specifically where the subject occludes the BACKGROUND, so
    the site has to be defined by that relationship rather than by contrast.

    Background is identified without assuming it is light or dark, because this
    corpus has both (white sweeps for flowers and bees, black fields for frost
    and foam): it is the luminance mode of the LOW-TEXTURE population. A sweep
    is smooth, so it dominates the flat pixels; the subject does not. Pixels
    near that level and locally smooth are background, and the morphological
    gradient of that mask is exactly the occluding boundary.

    Returns a tile grid, so it can be scored the same way as the others."""
    lum = img.astype(np.float32).mean(2)
    small = lum[::4, ::4]  # 4x decimation: the mask is a coarse structure

    # Local roughness, and the "smooth" population that a sweep dominates.
    rough = ndi.uniform_filter(small ** 2, 9) - ndi.uniform_filter(small, 9) ** 2
    np.maximum(rough, 0, out=rough)
    rough = np.sqrt(rough)
    smooth = rough < np.percentile(rough, 40)
    if smooth.sum() < smooth.size * 0.01:
        return np.zeros_like(tile_stat(lum, lambda t: 0.0))

    # Mode of the smooth population, taken as a histogram peak rather than a
    # median: with a bimodal frame (bright sweep + large dark subject) a median
    # can land between the two and describe neither.
    vals = small[smooth]
    hist, edges = np.histogram(vals, bins=128)
    level = 0.5 * (edges[hist.argmax()] + edges[hist.argmax() + 1])
    tol = max(float(vals.std()), 1.0) * 2.0

    bg = (np.abs(small - level) < tol) & smooth
    bg = ndi.binary_closing(bg, np.ones((5, 5)))
    bg = ndi.binary_opening(bg, np.ones((5, 5)))
    # Morphological gradient: 1 where the mask changes, i.e. the occluding edge.
    boundary = ndi.binary_dilation(bg, np.ones((3, 3))) ^ ndi.binary_erosion(bg, np.ones((3, 3)))

    # ...but "not background" is not the same as "subject". On bee-1-cpl the
    # first version of this scored highest where the white sweep meets the
    # table below it: two smooth regions at slightly different levels, a long
    # clean line, and no occlusion anywhere near it. An OCCLUDING boundary has
    # subject on one side, so the boundary only counts where textured pixels
    # are adjacent to it. This is what makes the site the cut-out artifact's
    # home rather than merely a place where the image changes.
    textured = rough > np.percentile(rough, 75)
    boundary = boundary & ndi.binary_dilation(textured, np.ones((7, 7)))

    # Back to full-frame tile coordinates.
    full = np.zeros(lum.shape, np.float32)
    full[:small.shape[0] * 4:4, :small.shape[1] * 4:4] = boundary
    full = ndi.uniform_filter(full, 9)
    return tile_stat(full, lambda t: float(t.mean()))


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
        ("silhouette", silhouette_score(img), "max", None),
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
    ap.add_argument("--ref", help="arm shown first in composites; inferred if only one")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--display", default="linear-srgb", choices=["linear-srgb", "none"])
    ap.add_argument("--scale", type=float, default=1.0,
                    help="fixed exposure scale before the display transform")
    a = ap.parse_args()

    arms = {}
    for d in a.dirs:
        for t in d.glob(f"{a.subject}--*.tiff"):
            arms[t.name[len(a.subject) + 2:-5]] = t
        # gallery.ps1 writes <subject>.tiff, one arm per directory, so fall back
        # to naming the arm after the directory. Without this the instrument
        # only works on its own harness's output, which is the wrong way round:
        # the gallery is the thing that actually has to be judged.
        plain = d / f"{a.subject}.tiff"
        if plain.exists():
            arms.setdefault(d.name.split(".")[0], plain)
    if not arms:
        raise SystemExit(f"no {a.subject}[--arm].tiff under {', '.join(str(d) for d in a.dirs)}")
    if a.ref is None:
        if len(arms) != 1:
            raise SystemExit(f"--ref is required with {len(arms)} arms: {', '.join(sorted(arms))}")
        a.ref = next(iter(arms))
    if a.ref not in arms:
        raise SystemExit(f"--ref {a.ref!r} not among arms: {', '.join(sorted(arms))}")

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
