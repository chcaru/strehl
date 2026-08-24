import os
import numpy as np
import tifffile
from PIL import Image

OUT = r"C:\dev\strehl-out\ORCH-look"
os.makedirs(OUT, exist_ok=True)
D = r"C:\dev\strehl-out\M86-align"

# ALIGNED vs ZOOMNULL is the clean comparison: same resampler, same FOV,
# registration deliberately discarded in the null. UNALIGNED has a different
# FOV (fit_to_cover k=0.9315) so its crops are NOT co-located and it is shown
# only for reference, never measured against the other two.
imgs = {
    "aligned": tifffile.imread(os.path.join(D, "bee-3-ALIGNED.tif")),
    "zoomnull": tifffile.imread(os.path.join(D, "bee3-zoomnull.tif")),
}

H, W = imgs["aligned"].shape[:2]
print("dims", H, W)
assert imgs["zoomnull"].shape[:2] == (H, W), "null is not FOV-matched"

# thumbnail was 1400x933; map eyeballed features back to full res
S = W / 1400.0
CROPS = {
    "wing-venation": (int(300 * S), int(100 * S)),
    "thorax-hair":   (int(800 * S), int(300 * S)),
    "leg-spines":    (int(250 * S), int(560 * S)),
    "head-eye":      (int(900 * S), int(650 * S)),
}
N = 640


def tenengrad(g):
    gx = np.zeros_like(g); gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    return float((gx * gx + gy * gy).mean())


rows = []
for name, (x, y) in CROPS.items():
    x = max(0, min(W - N, x)); y = max(0, min(H - N, y))
    tiles = []
    stats = {}
    for k in ("aligned", "zoomnull"):
        c = imgs[k][y:y + N, x:x + N].astype(np.float32)
        g = c.mean(axis=2)
        stats[k] = tenengrad(g)
        tiles.append(np.clip(c / 257.0, 0, 255).astype(np.uint8))
    sep = np.full((N, 8, 3), 255, np.uint8)
    Image.fromarray(np.concatenate([tiles[0], sep, tiles[1]], axis=1)).save(
        os.path.join(OUT, "crop-%s.png" % name))
    r = stats["aligned"] / stats["zoomnull"]
    rows.append((name, stats["aligned"], stats["zoomnull"], r))
    print("%-14s aligned %10.1f  zoomnull %10.1f  ratio %.4f" % (
        name, stats["aligned"], stats["zoomnull"], r))

print()
print("LEFT = aligned, RIGHT = zoomnull (FOV- and resampler-matched null)")
print("whole-frame, for comparison with M86's 0.9859:")
ga = imgs["aligned"].astype(np.float32).mean(axis=2)
gz = imgs["zoomnull"].astype(np.float32).mean(axis=2)
print("  whole-frame tenengrad ratio %.4f" % (tenengrad(ga) / tenengrad(gz)))
