r"""Remove the resolution confound from the darkening test.

--srgb renders full-res 4688x7032; --linear-srgb renders binned 2344x3516.
So "srgb shows -206.7 DN, linear shows -1.8 DN" confounds the tone stage with a
2x resolution difference. Box-downsample the srgb pair 2x to the linear grid and
re-measure. Box-downsampling preserves local means, so if the darkening is a
tone artifact it must survive; if it is a resolution artifact it must vanish.

Also reports the shift as a FRACTION of the site level, since the two spaces
have different absolute scales and DN are not comparable across them.
"""
import os

import numpy as np
import tifffile

S = 256
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\bf112"


def lum(p):
    a = tifffile.imread(p)
    return a[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])


def bin2(a):
    H, W = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    return a[:H, :W].reshape(H // 2, 2, W // 2, 2).mean(axis=(1, 3))


def sites(a):
    g = np.hypot(*np.gradient(a))
    H, W = a.shape
    ny, nx = H // S, W // S
    tg = g[:ny * S, :nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))
    o = np.argsort(tg.ravel())
    out = []
    for grp in (o[:12], o[-12:]):
        m = np.zeros(a.shape, bool)
        for f in grp:
            ty, tx = divmod(int(f), nx)
            m[ty * S:(ty + 1) * S, tx * S:(tx + 1) * S] = True
        out.append(m)
    return out


def measure(a, b, tag):
    fm, em = sites(a)
    g = np.median(a) / np.median(b)
    b1 = b * g
    la, lb = a[fm].mean(), b1[fm].mean()
    ea, eb = a[em].mean(), b1[em].mean()
    print("  %-34s FLAT %8.1f -> %8.1f  lift %+8.1f DN (%+6.3f%%)   EDGE lift %+8.1f DN (%+6.3f%%)"
          % (tag, la, lb, lb - la, 100 * (lb - la) / la, eb - ea, 100 * (eb - ea) / ea))


print("darkening of the FLAT sites under arm F4 = 4,1,1,1,1,1,1")
print("(ORCH's own gain-only median correction applied in every row)\n")
sa, sb = lum(os.path.join(OUT, "srgb__A-unset.tiff")), lum(os.path.join(OUT, "srgb__F4.tiff"))
measure(sa, sb, "--srgb        full-res 4688x7032")
measure(bin2(sa), bin2(sb), "--srgb        box-binned to 2344x3516")
la_, lb_ = lum(os.path.join(OUT, "lin__A-unset.tiff")), lum(os.path.join(OUT, "lin__F4.tiff"))
measure(la_, lb_, "--linear-srgb binned 2344x3516")
