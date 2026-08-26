"""Owner's caution, tested first: is the jaggedness real at 1:1, or is it the JPEG?

The owner saw the outline on a 2400 px JPEG downsampled ~2.93x from the 7032 px
render. Both downsampling and JPEG can manufacture apparent stair-stepping, and he
explicitly asked for this to be killed if it is an artifact. So: crop the LINEAR
16-bit TIFF at 1:1, no resampling of any kind, at the coordinates he named, and
put it beside the same region of the JPEG upsampled to the same scale.

If the steps are present at 1:1 in the TIFF they are in the render. If they appear
only in the JPEG column, his reading dies and that is the finding.

Nothing here is autoscaled per panel: one fixed tone transform, chosen from the
paper white, is applied to every panel. Autoscaling would change apparent edge
contrast between the two columns and make the comparison meaningless.
"""
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tifffile
from PIL import Image

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT\bee")
PICS = OUT / "pics"
MERGE = OUT / "D-merge.tif"
JPEG = pathlib.Path(r"C:\dev\strehl-out\gallery-1cacb61\bee-1-cpl.jpg")

# The owner's coordinates are in his 2400 px-long-edge view. Converted below once
# the true render width is known, so the scale factor is measured not assumed.
OWNER_VIEW_LONG_EDGE = 2400
OWNER_BOXES = {                    # (x0, y0, x1, y1) in the owner's 2400 px view
    "left-foreleg": (100, 550, 600, 900),
    "upper-left-body": (250, 380, 700, 700),
}
ZOOM = 380                          # half-size of the 1:1 crop actually drawn


def tone(rgb, ref):
    return np.clip(rgb.astype(np.float64) / (ref / 0.92), 0, 1) ** (1 / 2.2)


def main():
    PICS.mkdir(parents=True, exist_ok=True)
    img = tifffile.imread(str(MERGE))
    assert img.dtype == np.uint16, img.dtype
    h, w = img.shape[:2]
    scale = max(h, w) / OWNER_VIEW_LONG_EDGE
    print(f"render {w} x {h}; owner's view scale factor {scale:.4f}")

    # Paper white, from a corner known to be background, so the tone is fixed.
    ref = np.percentile(img[:400, :400].reshape(-1, 3), 99, axis=0).astype(np.float64)
    print(f"paper-white reference {ref.round().astype(int)} DN")

    jp = np.asarray(Image.open(JPEG)).astype(np.float64) / 255.0
    jh, jw = jp.shape[:2]
    jscale = max(jh, jw) / OWNER_VIEW_LONG_EDGE
    print(f"jpeg {jw} x {jh}")

    for name, (x0, y0, x1, y1) in OWNER_BOXES.items():
        cx, cy = int(0.5 * (x0 + x1) * scale), int(0.5 * (y0 + y1) * scale)
        cx = int(np.clip(cx, ZOOM, w - ZOOM)); cy = int(np.clip(cy, ZOOM, h - ZOOM))
        crop = img[cy - ZOOM:cy + ZOOM, cx - ZOOM:cx + ZOOM]

        jcx, jcy = int(0.5 * (x0 + x1) * jscale), int(0.5 * (y0 + y1) * jscale)
        jz = max(4, int(round(ZOOM * jscale / scale)))
        jcx = int(np.clip(jcx, jz, jw - jz)); jcy = int(np.clip(jcy, jz, jh - jz))
        jcrop = jp[jcy - jz:jcy + jz, jcx - jz:jcx + jz]

        fig, axes = plt.subplots(1, 2, figsize=(17, 8.8))
        axes[0].imshow(tone(crop, ref), interpolation="nearest")
        axes[0].set_title(f"LINEAR 16-bit TIFF, 1:1, no resampling\n"
                          f"{2 * ZOOM} x {2 * ZOOM} px at ({cx}, {cy})", fontsize=12)
        axes[1].imshow(np.clip(jcrop, 0, 1), interpolation="nearest")
        axes[1].set_title(f"the JPEG the owner looked at, same region\n"
                          f"{2 * jz} x {2 * jz} px, {scale / jscale:.2f}x coarser",
                          fontsize=12)
        for ax in axes:
            ax.set_xticks([]); ax.set_yticks([])
        fig.suptitle(f"bee-1-cpl {name}: is the stair-stepping in the render or the JPEG?",
                     fontsize=14)
        fig.tight_layout()
        p = PICS / f"BEE1-{name}.png"
        fig.savefig(p, dpi=100); plt.close(fig)
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
