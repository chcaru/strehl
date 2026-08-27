"""ARMS + GEOMETRY for the clipping / occlusion-rim free-field head-to-head.

One loader, used identically by the real comparison and by every control, so
the harness cannot manufacture a difference between them.

WHAT AN ARM IS HERE.  The GREEN plane in linear light, plus a container-ceiling
mask.  Green is chosen because `rimcmp.py` v3 was commissioned on the green
plane and because green is the least-interpolated channel of a Bayer demosaic.

WHY THESE THREE ARMS ARE COMPARABLE.  Every arm is fused from strehl's OWN
`--linear-srgb --demosaic` TIFFs (V-NOISE/noisefree.py, and the arm paths come
from V-NOISE2/hd2.py `paths_for` rather than being restated here).  Demosaic
and white balance are therefore identical on every side and the only remaining
difference is the stacking algorithm.

GEOMETRY IS INTEGER-ONLY.  Nothing is ever resampled.  The measured similarity
scale selects corresponding INTEGER pixel windows, exactly as
V-HEADTOHEAD/h2h.py does, because sub-pixel resampling adds blur to the very
quantity a rim gauge measures -- and because V-HEADTOHEAD sec.4 measured that a
Catmull-Rom upscale alone MANUFACTURES a +19.05% bright rim.  An instrument
that resampled one arm would be reporting that number.

The residual translation between arms is measured here rather than assumed:
V-NOISE2 RESULTS.md sec.5.3 records that the inherited `Arm.rgb` applies scale
with NO offset and that the residual on 119 is dy -8, dx -16 px.  That is
corrected here, by an integer shift, and the correction is reported.
"""
import os
import sys

import numpy as np
import tifffile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-NOISE2"))
from hd2 import paths_for, bits_of, scales_for, SUBJECTS         # noqa: E402

KEYS = ("strehl", "enfuse", "fs15-coh")


def _green_and_clip(path, bits):
    """Green plane as float32 in [0,1], plus the container-ceiling mask.

    These arms are TIFF-compressed and so are not memory-mappable; the raw
    array is read once, the two derived planes extracted blockwise, and the
    raw array released immediately.  Retaining it would hold ~240 MB per arm
    for no reason, and three arms plus a commissioning copy is what makes a
    harness die halfway through a control.
    """
    a = tifffile.imread(path)
    if a.ndim != 3:
        raise SystemExit(f"{path}: expected an RGB raster, got shape {a.shape}")
    a = a[:, :, :3]
    den = float(2 ** bits - 1)
    top = 2 ** bits - 1
    h, w = a.shape[0], a.shape[1]
    g = np.empty((h, w), np.float32)
    clip = np.zeros((h, w), bool)
    for y0 in range(0, h, 512):
        y1 = min(y0 + 512, h)
        blk = a[y0:y1]
        g[y0:y1] = blk[:, :, 1].astype(np.float32) / den
        clip[y0:y1] = (blk >= top).any(axis=2)
    del a
    return g, clip


class Arm:
    """Green plane, ceiling mask, and the integer map from STREHL coordinates
    into this arm's own raster."""

    def __init__(self, key, path, label, bits, scale, off=(0, 0)):
        self.key = key
        self.path = path
        self.label = label
        self.bits = bits
        self.scale = float(scale)
        self.off = (int(off[0]), int(off[1]))
        self.g, self.clip = _green_and_clip(path, bits)
        self.h, self.w = self.g.shape

    def tile_of(self, y, x, T):
        """(y, x, T) in strehl coordinates -> this arm's INTEGER window, or
        None if it does not fit.  Integer rounding only; never a resample."""
        s = self.scale
        ys = int(round(y / s)) + self.off[0]
        xs = int(round(x / s)) + self.off[1]
        ts = int(round(T / s))
        if ys < 0 or xs < 0 or ys + ts > self.h or xs + ts > self.w:
            return None
        return ys, xs, ts

    def rois_for(self, grid, T):
        out = []
        for (y, x) in grid:
            t = self.tile_of(y, x, T)
            if t is not None:
                out.append((t[0], t[1]))
        return out

    def tsize(self, T):
        return int(round(T / self.scale))


def measure_offset(ref, arm, scale, half=384, maxshift=48):
    """Integer translation between two arms, by normalised correlation of a
    central crop over an integer shift grid, coarse-to-fine.

    Deliberately NOT phase correlation on the whole frame: these arms differ in
    noise by up to 3.9x (V-NOISE2 sec.3), and a whole-frame phase peak is
    dominated by the shared low frequencies, which is where a scale error hides.
    An explicit integer search reports the shift it actually used, and its own
    runner-up alongside it, so a flat correlation surface -- which would mean
    the offset is not determined -- is visible rather than hidden behind a
    confident-looking integer.
    """
    cy, cx = ref.shape[0] // 2, ref.shape[1] // 2
    a = np.array(ref[cy - half:cy + half, cx - half:cx + half], np.float32)
    a -= a.mean()
    na = float(np.sqrt((a * a).sum()))
    by, bx = int(round(cy / scale)), int(round(cx / scale))

    def score(dy, dx):
        y0, x0 = by - half + dy, bx - half + dx
        if y0 < 0 or x0 < 0 or y0 + 2 * half > arm.shape[0] \
                or x0 + 2 * half > arm.shape[1]:
            return -2.0
        b = np.array(arm[y0:y0 + 2 * half, x0:x0 + 2 * half], np.float32)
        b -= b.mean()
        nb = float(np.sqrt((b * b).sum()))
        if na < 1e-9 or nb < 1e-9:
            return -2.0
        return float((a * b).sum()) / (na * nb)

    best, bo = -2.0, (0, 0)
    for dy in range(-maxshift, maxshift + 1, 4):
        for dx in range(-maxshift, maxshift + 1, 4):
            r = score(dy, dx)
            if r > best:
                best, bo = r, (dy, dx)
    seen = {}
    for dy in range(bo[0] - 4, bo[0] + 5):
        for dx in range(bo[1] - 4, bo[1] + 5):
            seen[(dy, dx)] = score(dy, dx)
    bo = max(seen, key=seen.get)
    best = seen[bo]
    # PROMINENCE, against a FAR shift rather than against the neighbour.
    # A first version of this compared the peak to the best of its own 3x3
    # neighbourhood and reported 0.9444 vs 0.9441 -- which looks like a flat,
    # undetermined surface but is simply what adjacent shifts of a smooth image
    # always look like.  A prominence measure whose baseline is the peak's own
    # neighbour cannot detect a flat surface, because the two move together.
    # The baseline here is the correlation at +/-24 px, far outside any
    # plausible residual, where a determined peak must fall away.
    far = max(score(bo[0] + dy, bo[1] + dx)
              for dy, dx in ((24, 0), (-24, 0), (0, 24), (0, -24)))
    return bo, best, far


def build(subject, offsets=None):
    """All three arms for one subject.  `offsets` is {armkey: (dy,dx)}."""
    _, spec = paths_for(subject)
    sc = scales_for(subject)
    arms = {}
    for k in KEYS:
        pa, pb, lab = spec[k]
        if not os.path.exists(pa):
            raise SystemExit(f"{subject}/{k}: MISSING {pa}")
        off = (offsets or {}).get(k, (0, 0))
        arms[k] = Arm(k, pa, lab, bits_of(pa), sc[k], off)
    return arms


def half_path(subject, key):
    """The B half of an arm, for the noise-matching control."""
    _, spec = paths_for(subject)
    return spec[key][1]


def detail_grid(g, T=256, keep=0.50, margin=64, max_rois=140, seed=7):
    """A COMMON ROI grid in strehl coordinates, chosen by gradient energy.

    Rim gauges have no power on ramps (V-HEADTOHEAD sec.2), so ROIs are drawn
    from the detail half of the frame.  The grid is computed ONCE on strehl and
    reused for every arm, so all arms are asked about the same scene content;
    letting each arm pick its own detail tiles would compare different
    populations of edges and is the obvious way to lose this argument.
    """
    h, w = g.shape
    cells, energy = [], []
    for y in range(margin, h - T - margin, T):
        for x in range(margin, w - T - margin, T):
            t = g[y:y + T:4, x:x + T:4]
            gy, gx = np.gradient(t.astype(np.float32))
            energy.append(float(np.hypot(gx, gy).mean()))
            cells.append((y, x))
    energy = np.array(energy)
    thr = np.percentile(energy, 100.0 * (1.0 - keep))
    sel = [c for c, e in zip(cells, energy) if e >= thr]
    if len(sel) > max_rois:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(sel), max_rois, replace=False)
        sel = [sel[i] for i in sorted(idx)]
    return sel
