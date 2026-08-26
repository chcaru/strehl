"""Arms for the head-to-head.  An ARM is (green plane in LINEAR light, a map from
PRIOR raster coordinates into this arm's raster, this arm's pixels per prior px).

Everything downstream consumes an Arm, so the SAME code path runs the real
comparison, the null control, the positive control and the scale-confound
control.  That is the only way the harness can be shown not to manufacture a
difference by itself.
"""
import numpy as np, tifffile, h2h

class Arm:
    def __init__(self, name, g, mapper, scale, clipmask=None):
        self.name = name; self.g = g; self.map = mapper
        self.scale = scale; self.clip = clipmask
    def px(self, x, y):
        return self.map(x, y)

def _blocks(shape0, n=256):
    for y in range(0, shape0, n):
        yield y, min(y + n, shape0)

def prior_arm():
    a = tifffile.memmap(h2h.PRIOR, mode="r")
    g = np.ascontiguousarray(a[:, :, 1]).astype(np.float32)     # already LINEAR Rec.2020
    clip = np.zeros(g.shape, bool)
    for y0, y1 in _blocks(a.shape[0]):
        clip[y0:y1] = np.asarray(a[y0:y1], np.float32).max(axis=2) >= 1.0
    del a
    return Arm("prior", g, lambda x, y: (x, y), 1.0, clip)

def strehl_arm():
    a = tifffile.memmap(h2h.STREHL, mode="r")
    g = np.empty((a.shape[0], a.shape[1]), np.float32)
    clip = np.zeros(g.shape, bool)
    for y0, y1 in _blocks(a.shape[0]):
        blk = np.asarray(a[y0:y1], np.uint16)
        lin = h2h.strehl_to_linear(blk)          # tone + transfer + S-curve inverted
        g[y0:y1] = lin[:, :, 1].astype(np.float32)
        clip[y0:y1] = blk.max(axis=2) >= 65535
    del a
    return Arm("strehl", g, h2h.prior_to_strehl, h2h.SCALE, clip)

# ---------------- controls -----------------------------------------------
def clone_arm(arm, name=None):
    return Arm(name or (arm.name + "-clone"), arm.g, arm.map, arm.scale, arm.clip)

def blur_arm(arm, sigma, name=None):
    from scipy import ndimage
    g = ndimage.gaussian_filter(arm.g, sigma, mode="nearest")
    return Arm(name or f"{arm.name}-blur{sigma}", g, arm.map, arm.scale, arm.clip)

def rescale_arm(arm, s, name=None):
    """Reproduce EXACTLY the geometric operation strehl's coverage step applies:
    crop the field of view to 1/s and resample back up to the original raster,
    Catmull-Rom.  This measures how much apparent difference the 3.5% rescale
    can manufacture ON ITS OWN."""
    from scipy import ndimage
    h, w = arm.g.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy = (np.arange(h) - cy) / s + cy
    xx = (np.arange(w) - cx) / s + cx
    Y, X = np.meshgrid(yy, xx, indexing="ij")
    # cubic spline order 3 is scipy's closest resampler to a Catmull-Rom
    out = ndimage.map_coordinates(arm.g, [Y, X], order=3, mode="nearest").astype(np.float32)
    clip = ndimage.map_coordinates(arm.clip.astype(np.float32), [Y, X], order=1,
                                   mode="nearest") > 0.05
    def mapper(x, y, s=s, cx=cx, cy=cy):
        return (cx + (np.asarray(x, float) - cx) * s, cy + (np.asarray(y, float) - cy) * s)
    return Arm(name or f"{arm.name}-rescale{s}", out, mapper, arm.scale * s, clip)
