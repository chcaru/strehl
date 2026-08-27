"""Answer ORCH's standing pre-flight question against my own section 12 null.

QUESTION: "What property of the input decides whether this check can see anything,
and have I varied it?"

For the radial statistic in l2_falsecolour.py the answer is r.max() OF THE MASKED
POPULATION, because line 205 sets the band edges with
    edges = np.linspace(0, r.max() + 1e-9, 7)
so the axis SELF-NORMALISES per subject. Band 5 means "as far out as this subject's
mask reached", which is not the same radius on two subjects. I compared
flower-bud 1.31x against coffee-bubbles 1.66x across that axis and never reported it.

This uses the SHIPPED edge_mask, imported not reimplemented -- a reimplementation
would be a different instrument and could not audit this one.
"""
import numpy as np, tifffile, l2_falsecolour as L

for nm, path in [("flower-bud CA-on", "C:/dev/strehl-out/BUILD-HIGHLIGHT/flowerbud/M1-caon-kneeoff.tif"),
                 ("coffee     CA-on", "C:/dev/strehl-out/BUILD-HIGHLIGHT/ladder/K3-stack-demo.tif")]:
    img = tifffile.imread(path).astype(np.float32) / 65535.0
    cr, cb, y = L.colour_diff(img)
    m, _thr = L.edge_mask(y, img, 99.5)
    h, w = y.shape
    yy, xx = np.nonzero(m)
    cy, cx = h / 2.0, w / 2.0
    r = np.hypot((yy - cy) / cy, (xx - cx) / cx)
    edges = np.linspace(0, r.max() + 1e-9, 7)
    cnt = [int(((r >= edges[i]) & (r < edges[i + 1])).sum()) for i in range(6)]
    print("%s  n_mask=%-8d r.max()=%.4f" % (nm, len(r), r.max()))
    print("     band centres r : " + " ".join("%.3f" % ((edges[i]+edges[i+1])/2) for i in range(6)))
    print("     band counts    : " + " ".join("%8d" % c for c in cnt))
    print("     min band count : %d  (instrument returns None only below 20)" % min(cnt))
    del img, cr, cb, y, m


