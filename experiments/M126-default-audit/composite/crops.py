"""M126 composite: integer crops, no resampling, fixed display transform.

Crop locations were chosen BY EYE from overview_A.png, not by maximum
disagreement -- ORCH's rule: a max-disagreement crop lands in a flat region
and tells you about noise while telling you nothing about detail.
"""
import sys, json, os
import numpy as np
import tifffile  # hard import -- no PIL fallback for reads
from PIL import Image, ImageDraw  # 8-bit WRITE only

TAG = sys.argv[1] if len(sys.argv) > 1 else "109MSDCF"
ARMS = sys.argv[2].split(",") if len(sys.argv) > 2 else ["A", "B", "E", "D0", "D"]
ROOT = rf"C:\dev\strehl-out\M126-COMPOSITE\{TAG}"
OUT = rf"C:\dev\strehl-out\M126-COMPOSITE\crops"
os.makedirs(OUT, exist_ok=True)

CROPS = json.load(open(rf"{ROOT}\crops.json"))
S = 512


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p}: dtype {a.dtype}, expected uint16"
    return a


d = json.load(open(rf"{ROOT}\display.json"))
LO = np.array(d["lo"], np.float32)
HI = np.array(d["hi"], np.float32)


def disp(a):
    f = (a.astype(np.float32) - LO) / np.maximum(HI - LO, 1.0)
    return (np.clip(f, 0, 1) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)


imgs = {}
for arm in ARMS:
    p = rf"{ROOT}\lin\{arm}.tif"
    if os.path.exists(p):
        imgs[arm] = load(p)
    else:
        print(f"  MISSING {p}")

stats = []
for name, (x0, y0) in CROPS.items():
    tiles = []
    for arm, im in imgs.items():
        c = im[y0:y0 + S, x0:x0 + S]           # integer slice, no resampling
        save = disp(c)
        fn = rf"{OUT}\{TAG}-{name}-{arm}.png"
        Image.fromarray(save).save(fn)
        tiles.append((arm, save))
        base = imgs.get("A")
        if base is not None:
            b = base[y0:y0 + S, x0:x0 + S].astype(np.int32)
            dd = c.astype(np.int32) - b
            stats.append(dict(crop=name, arm=arm,
                              mad=float(np.abs(dd).mean()),
                              pct_diff=float((dd != 0).mean() * 100),
                              # gradient energy: a SUPPORTING sharpness proxy only
                              grad=float(np.mean(np.abs(np.diff(c.astype(np.float32),
                                                               axis=1))))))
    # montage, labelled, 1:1 pixels
    W = S * len(tiles)
    m = Image.new("RGB", (W, S + 22), (0, 0, 0))
    for i, (arm, t) in enumerate(tiles):
        m.paste(Image.fromarray(t), (i * S, 22))
    dr = ImageDraw.Draw(m)
    for i, (arm, _) in enumerate(tiles):
        dr.text((i * S + 6, 5), f"{arm}", fill=(255, 255, 0))
    m.save(rf"{OUT}\{TAG}-{name}-MONTAGE.png")
    print(f"wrote {name}: {len(tiles)} arms at ({x0},{y0})")

json.dump(stats, open(rf"{OUT}\{TAG}-stats.json", "w"), indent=1)
print()
print(f"{'crop':10s} {'arm':4s} {'MAD vs A':>10s} {'%diff':>8s} {'grad':>9s}")
for s in stats:
    print(f"{s['crop']:10s} {s['arm']:4s} {s['mad']:10.2f} {s['pct_diff']:8.2f} {s['grad']:9.2f}")
