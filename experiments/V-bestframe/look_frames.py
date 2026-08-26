"""Look at the source frames directly. Before any statistic, establish what the
stack actually contains -- a metric built on a misunderstood input is worthless."""
import numpy as np, rawpy
from pathlib import Path
from PIL import Image                    # WRITE ONLY: PNG/JPEG out. No pixel that
                                         # becomes a number is ever read through PIL.
RAW = Path(r"D:\personal\macro"); OUT = Path(r"C:\dev\strehl-out\V-BESTFRAME\images")

def sheet(subj, n=16, cols=4, crop=None, scale=1, name=""):
    fs = sorted((RAW / subj).glob("*.ARW"))
    pick = np.unique(np.linspace(0, len(fs) - 1, n).round().astype(int))
    tiles = []
    for k in pick:
        with rawpy.imread(str(fs[k])) as r:
            a = r.postprocess(output_bps=8, no_auto_bright=True, use_camera_wb=True,
                              half_size=(crop is None))
        assert a.dtype == np.uint8, f"expected uint8 preview, got {a.dtype}"
        if crop is not None:
            cy, cx, s = crop
            a = a[cy:cy + s, cx:cx + s]
        im = Image.fromarray(a)
        im = im.resize((im.width // scale, im.height // scale), Image.LANCZOS) if scale > 1 else im
        tiles.append((k, fs[k].name, im))
    w, h = tiles[0][2].size
    rows = (len(tiles) + cols - 1) // cols
    sh = Image.new("RGB", (cols * w, rows * (h + 16)), (20, 20, 20))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sh)
    for i, (k, nm, im) in enumerate(tiles):
        x, y = (i % cols) * w, (i // cols) * (h + 16)
        sh.paste(im, (x, y + 16)); d.text((x + 4, y + 3), f"k={k}  {nm}", fill=(255, 230, 120))
    out = OUT / f"{subj}--{name}.jpg"
    sh.save(out, quality=88)
    print(f"  wrote {out}  ({sh.width}x{sh.height}, {len(tiles)} frames of {len(fs)})")

OUT.mkdir(parents=True, exist_ok=True)
for s in ("flowers-cpl", "bee-1-cpl"):
    print(s)
    sheet(s, n=16, cols=4, scale=3, name="STACK-overview")
    # 1200 px window at 100%, near merge tile (1,1) of the 3x3 review grid
    sheet(s, n=16, cols=4, crop=(2300, 3300, 1200), scale=2, name="STACK-detail-centre")
