import numpy as np, tifffile, sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, (p, a.dtype)
    return a

def prev(a):
    """VIEWING ONLY. Linear camera RGB -> a display gamma so a human can see
    it. Never measure on this; measurement uses the linear 16-bit file."""
    x = a.astype(np.float64) / 65535.0
    lo, hi = np.percentile(x, 0.5), np.percentile(x, 99.7)
    x = np.clip((x - lo) / max(hi - lo, 1e-9), 0, 1) ** (1/2.2)
    return (x * 255 + 0.5).astype(np.uint8)

import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--before", required=True); ap.add_argument("--after", required=True)
ap.add_argument("--out", required=True); ap.add_argument("--tag", required=True)
ap.add_argument("--at", action="append", required=True, help="Y,X")
ap.add_argument("--half", type=int, default=160)
a = ap.parse_args()
B, A = load(a.before), load(a.after)
H, W = B.shape[:2]
os.makedirs(a.out, exist_ok=True)
from PIL import Image
for k, s in enumerate(a.at):
    y, x = (int(v) for v in s.split(","))
    y = int(np.clip(y, a.half, H - a.half)); x = int(np.clip(x, a.half, W - a.half))
    sl = (slice(y-a.half, y+a.half), slice(x-a.half, x+a.half))
    b, f = B[sl], A[sl]
    gap = np.zeros((b.shape[0], 8, 3), np.uint8)
    panel = np.concatenate([prev(b), gap, prev(f)], axis=1)
    p = os.path.join(a.out, f"{a.tag}-{k}-y{y}-x{x}-BEFORE-vs-AFTER.png")
    Image.fromarray(panel).save(p)
    print("wrote", p, panel.shape)
