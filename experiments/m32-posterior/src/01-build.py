"""M32 step 1: build a raw cube + focus volume for the posterior experiments.

Unlike M27's volume builder this keeps the RAW signal cube as well, because the
noise-referenced arm needs the per-pixel signal level to evaluate sigma(S) from
the M4 model. Everything is on the green sublattice in native DN above black.
"""
import rawpy, numpy as np, glob, os, time, json

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CACHE = os.path.join(OUT, "cache")
SRC = r"C:\dev\macro\test\coffee-bean"

BLACK = 512
ISO = 50
G = ISO / 436.8              # DN per electron   (M4)
RN_E = 4.20                  # electrons, ISO < 400   (M4)
R = 2                        # focus-measure box radius, matches M27

# centred 1024x1024 crop of the 2344x3514 green plane
CY, CX, H = 1172, 1757, 512

files = sorted(glob.glob(os.path.join(SRC, "*.ARW")))[::2]
n = len(files)
ys, xs = slice(0, 4688, 2), slice(1, 7028, 2)

t0 = time.time()
raw = np.empty((n, 2 * H, 2 * H), np.float32)
for i, f in enumerate(files):
    with rawpy.imread(f) as r:
        raw[i] = r.raw_image_visible[ys, xs][CY - H:CY + H, CX - H:CX + H]
raw -= BLACK
print(f"raw cube {raw.shape}  {raw.nbytes/1e6:.0f} MB  decoded in {time.time()-t0:.0f}s")

np.save(os.path.join(CACHE, "raw.npy"), raw)

sig = raw.mean(0)
var = G * np.clip(sig, 0, None) + (RN_E * G) ** 2
snr = np.clip(sig, 0, None) / np.sqrt(var)
meta = dict(
    n_frames=n, crop=[2 * H, 2 * H], iso=ISO, g=G, rn_e=RN_E, box_radius=R,
    signal_dn=dict(p01=float(np.percentile(sig, 1)), median=float(np.median(sig)),
                   p99=float(np.percentile(sig, 99)), max=float(sig.max())),
    snr=dict(p01=float(np.percentile(snr, 1)), median=float(np.median(snr)),
             p99=float(np.percentile(snr, 99))),
    frac_below_snr10=float((snr < 10).mean()),
    frac_clipped=float((raw.max(0) >= 16383 - BLACK).mean()),
)
print(json.dumps(meta, indent=2))
with open(os.path.join(OUT, "01-build.json"), "w") as fh:
    json.dump(meta, fh, indent=2)
