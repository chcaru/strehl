"""Reference-free comparison of two renders of one stack.

usage: compare.py A.tif B.tif [tile]

Both inputs are 16-bit sRGB from the same writer. They are decoded to linear
light with the exact sRGB EOTF. Tiles are classified ONCE from arm A's luma
gradient (so the classification cannot favour B): `flat` = bottom 30% of tiles
by median gradient, `edge` = top 15%.

Reported per class (median over tiles, and B/A ratio):
  luma_hf   : RMS of luma minus its 5x5 box mean        (detail OR noise)
  chroma_hf : RMS of high-passed (R-G, B-G) in linear    (false colour / chroma noise)
  luma_vhf  : RMS of the 3x3 Laplacian of luma           (finest scale)

Direction of fooling: luma_hf rises with noise as well as detail, so a B/A
increase on `edge` is only read as sharpening if `flat` does not rise with it.
chroma_hf falls when real colour detail is blurred as well as when false colour
is removed; at f/15 effective aperture real chroma detail near Nyquist is weak.
"""
import sys
import numpy as np
import tifffile
from scipy.ndimage import uniform_filter, laplace


def lin(path):
    a = tifffile.imread(path).astype(np.float32) / 65535.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def main():
    a, b = lin(sys.argv[1]), lin(sys.argv[2])
    t = int(sys.argv[3]) if len(sys.argv) > 3 else 64
    assert a.shape == b.shape
    h, w, _ = a.shape
    h, w = h // t * t, w // t * t

    def feats(x):
        y = 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]
        y, x = y[:h, :w], x[:h, :w]
        yhf = y - uniform_filter(y, 5)
        c1, c2 = x[..., 0] - x[..., 1], x[..., 2] - x[..., 1]
        chf = np.sqrt((c1 - uniform_filter(c1, 5)) ** 2 + (c2 - uniform_filter(c2, 5)) ** 2)
        lap = laplace(y)
        def tile(m, f):
            return f(m.reshape(h // t, t, w // t, t), axis=(1, 3))
        return y, {
            "luma_hf": np.sqrt(tile(yhf ** 2, np.mean)),
            "chroma_hf": np.sqrt(tile(chf ** 2, np.mean)),
            "luma_vhf": np.sqrt(tile(lap ** 2, np.mean)),
            "mean_y": tile(y, np.mean),
        }

    ya, fa = feats(a)
    _, fb = feats(b)
    gy, gx = np.gradient(uniform_filter(ya, 3))
    g = np.hypot(gy, gx).reshape(h // t, t, w // t, t)
    gmed = np.median(g, axis=(1, 3)) / np.maximum(fa["mean_y"], 1e-4)
    lit = fa["mean_y"] > 0.02
    q30, q85 = np.quantile(gmed[lit], [0.30, 0.85])
    classes = {"flat": lit & (gmed <= q30), "edge": lit & (gmed >= q85), "all": lit}
    diff = np.abs(a - b)
    print(f"tiles {gmed.size}, lit {lit.sum()}; max |A-B| linear {diff.max():.5f}, "
          f"mean {diff.mean():.6f}")
    for cname, m in classes.items():
        parts = []
        for k in ("luma_hf", "chroma_hf", "luma_vhf"):
            va, vb = np.median(fa[k][m]), np.median(fb[k][m])
            r = np.median(fb[k][m] / np.maximum(fa[k][m], 1e-12))
            parts.append(f"{k} A {va:.6f} B {vb:.6f} B/A {r:.4f}")
        print(f"{cname:5s} n={m.sum():5d}  " + " | ".join(parts))


if __name__ == "__main__":
    main()
