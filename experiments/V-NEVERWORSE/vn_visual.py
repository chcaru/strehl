r"""V-NEVERWORSE / THE VISUAL -- is the ratio's verdict visible at true 1:1?

Rule 48 and `true11.py`: the viewer resolves ~1 px detail only up to about
400 px, so every crop here is CROP=380 px cut by slicing, never resized. If it
looks soft here it is soft.

The one liberty taken, and it is stated: both crops are put through the SAME
display transform, computed once from the master
    disp(x) = 255 * clip(x / p99.5(master window), 0, 1) ** (1/2.2)
Identical constants on both sides. That is what makes the pair comparable at
all -- `--srgb` would give each image its OWN content-derived tone curve, which
is the defect this whole lane is about.

For each subject named, three crops from the same window in master geometry:
    master   the merge
    srcmin   the source frame that WON the blotch contest (the argmin)
    srcmax   the source frame that lost it (the argmax)
so a reader can see whether the argmin won by being cleaner or by being blurred.

  python vn_visual.py [subject ...]
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_lib as L                                            # noqa: E402
from orch_blotch import lum_of                                # noqa: E402
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ORCH-drift-check"))
from true11 import CROP                                       # noqa: E402

VDIR = os.path.join(L.OUT, "visual")


def disp(win, scale):
    x = np.clip(win.astype(np.float64) / scale, 0.0, 1.0) ** (1.0 / 2.2)
    return (x * 255.0 + 0.5).astype(np.uint8)


def cut(win, cy, cx):
    y0 = int(np.clip(cy - CROP // 2, 0, win.shape[0] - CROP))
    x0 = int(np.clip(cx - CROP // 2, 0, win.shape[1] - CROP))
    return win[y0:y0 + CROP, x0:x0 + CROP], y0, x0


def one(subj):
    rec = L.jload(os.path.join(L.OUT, "ratio", "%s.json" % subj))
    bw, cw = tuple(rec["bw"]), tuple(rec["cw"])
    o = rec["src_blotch"]
    mrgb = L.read_rgb(L.lin_master_path(subj))
    mlum = lum_of(mrgb)
    mwin = mrgb[bw[0]:bw[0] + L.BWIN, bw[1]:bw[1] + L.BWIN].copy()
    del mrgb
    km = rec["cover_master"]
    scale = float(np.percentile(mwin, 99.5))
    os.makedirs(VDIR, exist_ok=True)
    out = []
    c, y0, x0 = cut(mwin, L.BWIN // 2, L.BWIN // 2)
    Image.fromarray(disp(c, scale)).save(
        os.path.join(VDIR, "%s_master_%d_%d.png" % (subj, bw[1] + x0, bw[0] + y0)))
    out.append(("master", -1, float(np.std(lum_of(c))), float(np.mean(lum_of(c)))))
    for tag, k in (("srcmin", o["argmin"]), ("srcmax", o["argmax"])):
        keep = []
        L.measure_source_frame(subj, k, mlum, bw, cw, km, keep=keep)
        if not keep:
            out.append((tag, k, None, None))
            continue
        wb = keep[0][1]
        c2 = wb[y0:y0 + CROP, x0:x0 + CROP]
        Image.fromarray(disp(c2, scale)).save(
            os.path.join(VDIR, "%s_%s_f%03d_%d_%d.png"
                         % (subj, tag, k, bw[1] + x0, bw[0] + y0)))
        out.append((tag, k, float(np.std(lum_of(c2))), float(np.mean(lum_of(c2)))))
    del mlum
    print("\n%s  window (%d,%d) crop %dx%d at master offset (%d,%d), display "
          "scale p99.5=%.0f DN applied identically to all three"
          % (subj, bw[1], bw[0], CROP, CROP, bw[1] + x0, bw[0] + y0, scale))
    for tag, k, sd, mn in out:
        print("   %-7s %-6s crop std %s DN  mean %s DN"
              % (tag, ("f%d" % k) if k >= 0 else "-",
                 "%8.2f" % sd if sd else "     n/a",
                 "%8.1f" % mn if mn else "    n/a"))
    return out


def main(argv):
    subs = argv
    if not subs:
        t = L.jload(os.path.join(L.OUT, "report", "table.json"))
        v = sorted(t["violations"]["blotch"], key=lambda x: -x[1])[:4]
        subs = [s for s, _ in v]
    print("TRUE 1:1 -- CROP=%d px, slicing only, no resize and no grade" % CROP)
    for s in subs:
        one(s)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
