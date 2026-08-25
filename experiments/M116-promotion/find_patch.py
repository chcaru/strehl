"""find_patch.py — locate piecewise-constant structure on the SHIPPED render.

Two diagnostics, both for FINDING a region to crop, neither reported as a
measurement:

  1. an image of the n_eff map, because a random election can only reach the
     output where the gate is narrow. Where n_eff is large the winner is
     irrelevant and the patchwork cannot propagate.
  2. a tile ranking by coarse gradient-energy CONCENTRATION. A piecewise
     constant field puts its gradient on thin closed curves, so a small
     fraction of pixels carries most of the energy. A smooth ramp and pure
     noise both spread it out. Restricted to low-contrast tiles so that hairs
     and antennae, which are also sparse and strong, cannot win.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = Path(r"C:\dev\strehl-out\M116")
OUT = ROOT / "images-patch"
OUT.mkdir(parents=True, exist_ok=True)
S = sys.argv[1] if len(sys.argv) > 1 else "bee-3-cpl"
ARM = sys.argv[2] if len(sys.argv) > 2 else "A0"
TILE, BIN, TOPQ = 256, 4, 0.02


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def binned(x, f):
    h, w = x.shape
    h2, w2 = (h // f) * f, (w // f) * f
    return x[:h2, :w2].reshape(h2 // f, f, w2 // f, f).mean(axis=(1, 3))


nf = ROOT / "maps" / f"{S}__T1-neff.tif"
if nf.exists():
    m = tifffile.imread(nf)
    m = m[..., 0] if m.ndim == 3 else m
    m = m.astype(np.float32)
    print(f"n_eff map {m.shape}: min {m.min():.2f} med {np.median(m):.2f} "
          f"max {m.max():.2f}")
    for thr in (2, 5, 10, 20, 50):
        print(f"   frac n_eff < {thr:3d} : {float((m < thr).mean()):.4f}")
    sm = binned(m, 3)
    u8 = np.clip(sm / max(m.max(), 1e-9) * 255, 0, 255).astype(np.uint8)
    Image.fromarray(u8).save(OUT / f"{S}__neff-map.png")
    print(f"wrote {OUT / f'{S}__neff-map.png'}  (white = many frames admitted)")
else:
    m = None
    print(f"NO n_eff map at {nf}")

g = luma(tifffile.imread(ROOT / "measure" / f"{S}__{ARM}.tif").astype(np.float32))
H, W = g.shape
rows = []
for y in range(0, H - TILE + 1, TILE):
    for x in range(0, W - TILE + 1, TILE):
        t = binned(g[y:y + TILE, x:x + TILE], BIN)
        gy, gx = np.gradient(t)
        e = np.sqrt(gy ** 2 + gx ** 2).ravel()
        tot = e.sum()
        if tot <= 0:
            continue
        k = max(1, int(round(TOPQ * e.size)))
        conc = float(np.sort(e)[-k:].sum() / tot)
        contrast = float(t.std() / max(t.mean(), 1e-9))
        neff = float(np.median(m[y:y + TILE, x:x + TILE])) if m is not None else -1
        rows.append((conc, contrast, neff, y, x))

cmed = float(np.median([r[1] for r in rows]))
cand = [r for r in rows if r[1] < cmed]
cand.sort(reverse=True)
print(f"\n{len(rows)} tiles, contrast median {cmed:.4f}, "
      f"{len(cand)} below it (defocused half)")
print("top concentration among defocused tiles:")
print(f"{'conc':>7} {'contrast':>9} {'n_eff':>7}  origin")
for conc, contrast, neff, y, x in cand[:12]:
    print(f"{conc:7.4f} {contrast:9.4f} {neff:7.2f}  y={y} x={x}")
