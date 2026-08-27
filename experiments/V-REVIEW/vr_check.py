r"""Look at it. Register a source render to the master and DUMP THE PAIR.

The project's own record is that five instruments were wrong in one night and
every one was caught by rendering the thing, never by the statistic. This dumps
the master's analysis window beside the same window pulled out of the source
render, at one shared display gain, so a claim that the two arms are looking at
the same piece of the subject can be checked by eye.
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402
import vr_reg2 as R                                           # noqa: E402


def tone(a, lo, hi):
    return np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)


def main():
    subj = sys.argv[1]
    frames = [int(a) for a in sys.argv[2:]] or [0]
    with open(os.path.join(V.OUT, "master_stats.json")) as f:
        ms = json.load(f)[subj]
    y, x = ms["blotch"]["y"], ms["blotch"]["x"]
    km = R.master_cover(subj)
    mrgb = V.read_rgb(V.master_path(subj))
    mlum = V.lum_of(mrgb)
    mw = mrgb[y:y + V.BWIN, x:x + V.BWIN]
    lo, hi = np.percentile(V.lum_of(mw), [1, 99])
    tiles = [(mw, "MASTER blotch win (%d,%d)  contrast %.5f" % (y, x, ms["blotch"]["contrast"]))]
    del mrgb
    for k in frames:
        tif = os.path.join(V.OUT, "%s--f%04d.tiff" % (subj, k))
        if not os.path.exists(tif):
            log = V.render_frame(subj, k, tif)
            ks = R.cover_of_log(log)
        else:
            ks = 0.9974
        srgb = V.read_rgb(tif)
        slum = V.lum_of(srgb)
        for how in ("orb", "model"):
            if how == "orb":
                A, d = V.register(mlum, slum)
                if A is None or d.get("inliers", 0) < 40:
                    print("frame %d ORB   no fit (%r)" % (k, d))
                    continue
            else:
                A, d = R.register_model(mlum, slum, km / (ks or 0.9974))
            n = R.context_ncc(mlum, slum, A, y, x, V.BWIN)
            w = V.warp_window(srgb, A, y, x, V.BWIN)
            r = V.blotch_ratio(V.lum_of(w))[0] if w is not None else float("nan")
            print("frame %3d %-6s scale %.4f  ecc %.4f  ncc %.4f  blotch %.5f"
                  % (k, how, d.get("scale", np.nan), d.get("ecc", np.nan), n, r))
            if w is not None:
                tiles.append((w, "f%d %s ncc %.3f blotch %.5f" % (k, how, n, r)))
        del srgb, slum
    ncol = min(4, len(tiles))
    nrow = (len(tiles) + ncol - 1) // ncol
    S = 450
    canvas = np.zeros((nrow * (S + 18), ncol * S, 3), np.uint8)
    for i, (img, lab) in enumerate(tiles):
        t = cv2.resize(img, (S, S), interpolation=cv2.INTER_AREA)
        t = (np.stack([tone(t[..., c], lo, hi) for c in range(3)], -1) * 255).astype(np.uint8)
        ry, rx = divmod(i, ncol)
        canvas[ry * (S + 18):ry * (S + 18) + S, rx * S:(rx + 1) * S] = t
        cv2.putText(canvas, lab[:52], (rx * S + 3, ry * (S + 18) + S + 13),
                    cv2.FONT_HERSHEY_PLAIN, 0.85, (255, 255, 255), 1)
    out = os.path.join(V.OUT, "check-%s.png" % subj)
    cv2.imwrite(out, canvas[:, :, ::-1])
    print("wrote %s   (shared display window %.0f-%.0f DN)" % (out, lo, hi))


if __name__ == "__main__":
    main()
