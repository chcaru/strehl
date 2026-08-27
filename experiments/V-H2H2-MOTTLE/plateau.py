"""How big are the winner plateaus, in OUTPUT pixels?

Concentration says one frame owns a coefficient. That alone is not mottle: mottle
is a SCALE. This converts the winner map into a length.

GEOMETRY, not assumption. The dump records each band's own grid. The merge runs at
3516x2344 and the render is 7032x4688, so one merge coefficient spans 2 output px,
and one band-k coefficient spans 2^k merge px:

    output px per band-k coefficient = 2^(k+1)

A run of `L` identical winners at band k therefore spans `L * 2^(k+1)` output px.
The mean run length is reported with the null for the same label distribution --
a run length of 1/(1-sum p_i^2) arises from chance alone and must be divided out,
or a stack that uses one frame heavily reads as structured when it is not.
"""
import json
import io
import os
import sys

import numpy as np
import tifffile

DUMP = r"C:\dev\strehl-out\V-H2H2\wdump"


def runs(arg, mask):
    """Mean horizontal run of identical admitted winners, and the chance null."""
    tot = n = 0
    for row_a, row_m in zip(arg, mask):
        lab = row_a[row_m]
        if lab.size == 0:
            continue
        brk = int(np.count_nonzero(lab[1:] != lab[:-1])) + 1
        tot += lab.size
        n += brk
    if n == 0:
        return float("nan"), float("nan")
    lab = arg[mask]
    _, c = np.unique(lab, return_counts=True)
    p = c / c.sum()
    return tot / n, 1.0 / max(1.0 - float((p * p).sum()), 1e-9)


def boxsd(a, r):
    a = a.astype(np.float64)
    def integ(x):
        return np.pad(np.cumsum(np.cumsum(x, axis=0), axis=1), ((1, 0), (1, 0)))
    h, w = a.shape
    i1, i2 = integ(a), integ(a * a)
    y0 = np.clip(np.arange(h) - r, 0, h); y1 = np.clip(np.arange(h) + r + 1, 0, h)
    x0 = np.clip(np.arange(w) - r, 0, w); x1 = np.clip(np.arange(w) + r + 1, 0, w)
    def win(I):
        return (I[np.ix_(y1, x1)] - I[np.ix_(y0, x1)]
                - I[np.ix_(y1, x0)] + I[np.ix_(y0, x0)])
    n = ((y1 - y0)[:, None] * (x1 - x0)[None, :]).astype(np.float64)
    m1, m2 = win(i1) / n, win(i2) / n
    out = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    assert out.shape == a.shape, "boxsd changed shape"
    return out


def main():
    prefix = os.path.join(DUMP, sys.argv[1] if len(sys.argv) > 1 else "cb")
    with io.open(prefix + "-dims.json", encoding="utf-8") as fh:
        dims = json.load(fh)
    a = tifffile.imread(os.path.join(DUMP, "off.tiff"))
    lum = a[..., 1].astype(np.float64)
    oh, ow = lum.shape
    sd = boxsd(lum, 16)
    lo = np.percentile(sd, 15)

    print("winner plateau scale, %d frames, output grid %dx%d" % (dims["frames"], ow, oh))
    print("%-3s %-6s %-9s %-9s %-9s %s"
          % ("k", "p", "px/coef", "run flat", "null", "PLATEAU (output px)"))
    for b in dims["bands"]:
        k, w, h, p = b["k"], b["w"], b["h"], b["exponent"]
        path = "%s-b%d-arg.i32" % (prefix, k)
        if not os.path.exists(path):
            continue
        arg = np.fromfile(path, dtype=np.int32).reshape(h, w)
        conc = np.fromfile("%s-b%d-conc.f32" % (prefix, k), dtype=np.float32).reshape(h, w)
        ys = (np.arange(h) * (oh / h)).astype(int).clip(0, oh - 1)
        xs = (np.arange(w) * (ow / w)).astype(int).clip(0, ow - 1)
        flat = sd[np.ix_(ys, xs)] <= lo
        m = flat & (arg >= 0) & np.isfinite(conc)
        r, null = runs(arg, m)
        scale = 2.0 ** (k + 1)
        if r != r:
            print("%-3d %-6.2f %-9.0f %-9s %-9s %s" % (k, p, scale, "n/a", "n/a", "-"))
            continue
        print("%-3d %-6.2f %-9.0f %-9.3f %-9.3f %.1f px  (chance alone: %.1f px)"
              % (k, p, scale, r, null, r * scale, null * scale))


if __name__ == "__main__":
    main()
