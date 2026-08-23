"""M60 step 1 — survey the candidate stacks and render previews for HAND labelling.

Read-only against D:\\personal\\macro. Writes only into ../fig and ../data.

Why previews: the labels for occlusion cells must NOT come from the focus volume
(AGENTS rule 17 / discipline on circularity -- M21's first number was 85%
tautology because it binned bimodality against an argmax field from the same
volume). So the cells are marked by eye on rendered frames.
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.abspath(os.path.join(HERE, "..", "fig"))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))

STACKS = ["bee-1", "bee-2", "bee-3", "wrapped-text-1", "wrapped-text-2",
          "109MSDCF", "coffee-bean", "112MSDCF", "113MSDCF"]


def meta(path):
    import rawpy
    with rawpy.imread(path) as r:
        o = r.other
        shape = r.raw_image_visible.shape
        pat = r.raw_pattern.tolist()
        return dict(iso=float(o.iso_speed), shutter=float(o.shutter_speed),
                    aperture=float(o.aperture), focal=float(o.focal_length),
                    ts=o.timestamp, shape=shape, pattern=pat)


def preview(stack, k, out, downs=8):
    fs = L.frames(stack)
    g = L.load_green_raw(fs[k])
    g = g[: (g.shape[0] // downs) * downs, : (g.shape[1] // downs) * downs]
    g = g.reshape(g.shape[0] // downs, downs, g.shape[1] // downs, downs).mean((1, 3))
    v = np.clip((g - L.BLACK) / (L.WHITE - L.BLACK), 0, 1) ** (1 / 2.2)
    from PIL import Image
    Image.fromarray((v * 255).astype(np.uint8)).save(out)
    return g.shape


if __name__ == "__main__":
    rows = []
    for s in STACKS:
        fs = L.frames(s)
        m0 = meta(fs[0])
        mN = meta(fs[-1])
        span = int((mN["ts"] - m0["ts"]).total_seconds())
        print("%-13s n=%-4d ISO %-6.0f  %.4fs f/%-4.1f  %.0fmm  active %s  pattern %s  span %ds"
              % (s, len(fs), m0["iso"], m0["shutter"], m0["aperture"], m0["focal"],
                 m0["shape"], m0["pattern"], span))
        rows.append((s, len(fs), m0["iso"], m0["shutter"], m0["aperture"], m0["focal"], span))
    with open(os.path.join(DATA, "01-survey.csv"), "w", encoding="utf-8") as fh:
        fh.write("stack,frames,iso,shutter_s,aperture_marked,focal_mm,capture_span_s\n")
        for r in rows:
            fh.write("%s,%d,%.0f,%.6f,%.1f,%.0f,%d\n" % r)

    print()
    for s in ["bee-1", "bee-2", "bee-3", "wrapped-text-1", "wrapped-text-2"]:
        n = len(L.frames(s))
        for frac, tag in ((0.0, "first"), (0.5, "mid"), (1.0, "last")):
            k = min(n - 1, int(round(frac * (n - 1))))
            out = os.path.join(FIG, "01-%s-%s-k%03d.png" % (s, tag, k))
            sh = preview(s, k, out)
            print("wrote %s  (%dx%d, 8x binned green)" % (out, sh[1], sh[0]))
