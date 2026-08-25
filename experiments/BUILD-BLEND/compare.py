"""Put the shipped merge and the Laplacian multi-band merge side by side.

Two rules this script exists to obey:

* **The two arms go through the SAME conversion.** Both TIFFs are read with
  `tifffile`, asserted `uint16`, truncated `>> 8` and Lanczos-resampled to the
  same long edge -- the exact recipe in `scripts/gallery_view.py`. If the arms
  were converted differently, every tone difference in the comparison would be
  ambiguous between "the merge changed" and "the viewer changed".
* **Never `PIL.Image.open` a 16-bit RGB TIFF.** It silently hands back 8 bits.
  It has corrupted results on this project before. The assert is the guard and
  it is deliberately not wrapped in a fallback.

Full frames are the primary judging surface, because crop-level judging is how
the halo stayed hidden for weeks. The 1:1 rim strip this script also writes is
*supplementary evidence about a defect already visible at full frame*, not a
substitute for looking at the frame.

    python compare.py <subject> <control.tiff> <blend.tiff> <outdir> [long-edge]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

BAR = 44          # label bar height, px
GUTTER = 16       # gap between the two arms
BG = (24, 24, 24)
FG = (240, 240, 240)


def read16(path: Path) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path} is {a.dtype}, expected uint16"
    assert a.ndim == 3 and a.shape[2] == 3, f"{path} has shape {a.shape}, expected HxWx3"
    return a


def to_view(a: np.ndarray) -> Image.Image:
    """16 -> 8 bit by truncation, matching `gallery_view.py` and any viewer."""
    return Image.fromarray((a >> 8).astype(np.uint8), mode="RGB")


def label(img: Image.Image, text: str) -> Image.Image:
    out = Image.new("RGB", (img.width, img.height + BAR), BG)
    out.paste(img, (0, BAR))
    d = ImageDraw.Draw(out)
    d.text((10, BAR // 2), text, fill=FG, anchor="lm")
    return out


def pair(left: Image.Image, lt: str, right: Image.Image, rt: str, title: str) -> Image.Image:
    left, right = label(left, lt), label(right, rt)
    h = max(left.height, right.height)
    out = Image.new("RGB", (left.width + GUTTER + right.width, h + BAR), BG)
    d = ImageDraw.Draw(out)
    d.text((10, BAR // 2), title, fill=FG, anchor="lm")
    out.paste(left, (0, BAR))
    out.paste(right, (left.width + GUTTER, BAR))
    return out


def rim_window(ctrl: np.ndarray, blend: np.ndarray, side: int = 900) -> tuple[int, int]:
    """Find where the two arms disagree most, at the scale a rim lives at.

    Not a quality metric and not scored -- a *pointer*, so the 1:1 strip is
    aimed at the place the arms actually differ rather than at a crop chosen by
    hand, which is how flattering crops get picked. The statistic is deliberately
    the low-frequency difference: a rim is a step in the low frequencies, which
    is exactly what a per-pixel selection can produce and a band-limited merge
    cannot.
    """
    h, w, _ = ctrl.shape
    step = 8
    a = ctrl[::step, ::step, :].astype(np.float32).mean(axis=2)
    b = blend[::step, ::step, :].astype(np.float32).mean(axis=2)
    d = np.abs(a - b)
    # Box-blur the difference to ~the rim's own scale so a few hot pixels
    # cannot pin the window, the way a single-max statistic gets pinned by one
    # specular highlight.
    k = 12
    c = np.cumsum(np.cumsum(np.pad(d, ((1, 0), (1, 0))), axis=0), axis=1)
    hh, ww = d.shape
    if hh <= 2 * k or ww <= 2 * k:
        return (max(0, (h - side) // 2), max(0, (w - side) // 2))
    box = (c[2 * k:, 2 * k:] - c[:-2 * k, 2 * k:] - c[2 * k:, :-2 * k] + c[:-2 * k, :-2 * k])
    iy, ix = np.unravel_index(int(np.argmax(box)), box.shape)
    cy, cx = (iy + k) * step, (ix + k) * step
    y = int(np.clip(cy - side // 2, 0, max(0, h - side)))
    x = int(np.clip(cx - side // 2, 0, max(0, w - side)))
    return y, x


def main() -> int:
    if len(sys.argv) not in (5, 6):
        print(__doc__, file=sys.stderr)
        return 2
    subject, ctrl_p, blend_p, outdir = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    long_edge = int(sys.argv[5]) if len(sys.argv) == 6 else 2000
    outdir.mkdir(parents=True, exist_ok=True)

    ctrl, blend = read16(ctrl_p), read16(blend_p)
    assert ctrl.shape == blend.shape, (
        f"the arms are different sizes: control {ctrl.shape} vs blend {blend.shape}. "
        "They must come from the same geometry or the comparison is meaningless."
    )

    # ---- full frame, the primary judging surface -------------------------
    cv, bv = to_view(ctrl), to_view(blend)
    cv.thumbnail((long_edge, long_edge), Image.LANCZOS)
    bv.thumbnail((long_edge, long_edge), Image.LANCZOS)
    full = pair(
        cv, "CONTROL  per-pixel selection + gather  (pin-859edac, the gallery binary)",
        bv, "BLEND  Laplacian multi-band merge",
        f"{subject}  --  FULL FRAME, both arms through the identical gallery_view recipe",
    )
    fp = outdir / f"sxs-{subject}.jpg"
    full.save(fp, quality=95, subsampling=0, optimize=True)
    print(f"{fp.name}  {full.size[0]}x{full.size[1]}")

    # ---- 1:1 at the place the arms disagree most -------------------------
    side = 900
    y, x = rim_window(ctrl, blend, side)
    cc = to_view(ctrl[y:y + side, x:x + side])
    bc = to_view(blend[y:y + side, x:x + side])
    crop = pair(
        cc, "CONTROL", bc, "BLEND",
        f"{subject}  --  1:1, largest low-frequency disagreement, at ({x}, {y})",
    )
    cp = outdir / f"rim-{subject}.jpg"
    crop.save(cp, quality=95, subsampling=0, optimize=True)
    print(f"{cp.name}  {crop.size[0]}x{crop.size[1]}  window=({x},{y})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
