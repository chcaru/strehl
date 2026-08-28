import io, sys
F="vc_ca.py"; t=io.open(F,encoding="utf-8").read()

old = t[t.index("def profile(img_c, py, px, nx, ny):"):t.index("def shift(pa, pb):")]
new = '''def profile(img_c, py, px, nx, ny):
    """Mean intensity along the outward normal, sampled by interpolation.

    DEFECT FIXED: the previous implementation binned pixels by `digitize` into
    unit bins of t. That is orientation-dependent -- at 0/90 deg each bin takes a
    clean row/column, but at 45 deg the projections land at multiples of 0.707
    and alias against the unit bins. Commissioning measured the resulting gain as
    1.000 at 0 deg, 0.936 at 20/70 deg and **0.170 at 45 deg**. Sampling on an
    explicit (t, u) lattice with cubic interpolation is orientation-independent.
    """
    mx, my = -ny, nx                      # unit vector perpendicular to n
    ts = np.arange(-HALF, HALF + 1, 1.0)
    us = np.arange(-PERP, PERP + 1, 1.0)
    T, U = np.meshgrid(ts, us)
    ys = py + T * ny + U * my
    xs = px + T * nx + U * mx
    m = int(HALF + PERP + 4)
    y0, y1 = int(py) - m, int(py) + m + 1
    x0, x1 = int(px) - m, int(px) + m + 1
    if y0 < 0 or x0 < 0 or y1 > img_c.shape[0] or x1 > img_c.shape[1]:
        return None
    win = img_c[y0:y1, x0:x1].astype(np.float32)
    v = map_coordinates(win, [(ys - y0).ravel(), (xs - x0).ravel()],
                        order=3, mode="nearest")
    return v.reshape(U.shape).mean(axis=0).astype(np.float32)


'''
t = t.replace(old, new, 1)
t = t.replace("import numpy as np, tifffile",
              "import numpy as np, tifffile\nfrom scipy.ndimage import map_coordinates", 1)
t = t.replace("HALF        = 24      # profile half-length in sensels",
              "HALF        = 24      # profile half-length in sensels\nPERP        = 12      # half-width averaged along the edge", 1)
io.open(F,"w",newline="\n",encoding="utf-8").write(t)
print("profile() rewritten: lattice sampling, orientation-independent")
