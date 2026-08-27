"""Where a master touches the ends of the tone scale, and which channel does it.

WHAT THIS ADDS TO `orch_printready.py`

That gate reports two numbers per master: `clip` = mean(rgb >= 65500) and
`crush` = mean(rgb <= 35), both taken over the FLATTENED three-channel array.
A single number over three channels cannot distinguish the two mechanisms that
produce it, and they need completely different responses:

  * a NEUTRAL highlight -- all three channels at the ceiling together -- is a
    specular or a blown white. If it is in the capture, no renderer can fix it.
  * a ONE-CHANNEL pin is a colour event. `image_out::gamut_map` blends an
    out-of-gamut triple toward the neutral of the same luminance and takes the
    SMALLEST blend that works, which places the offending channel at EXACTLY
    the boundary -- 65535 or 0. So every out-of-gamut pixel contributes at
    least one channel to `clip` or `crush` BY CONSTRUCTION, without any
    highlight or shadow being blown at all.

So this counts the channels separately and reports the joint pattern. The
distinction it is built to expose is `all three` versus `exactly one`, and the
direction it can be fooled in is stated: it is a count of VALUES, so it cannot
tell a pin the merge manufactured from a pin the scene delivered. That is what
`clip_source.py` is for; this decides which subjects are worth taking there.

Usage:  python clip_census.py <dir-of-masters> [glob]
"""

import pathlib
import sys

import numpy as np
import tifffile

HI = 65500     # orch_printready.py's threshold, reused verbatim
LO = 35        # ditto


def census(path):
    a = tifffile.imread(str(path))
    if a.ndim != 3 or a.shape[2] < 3:
        return None
    rgb = a[:, :, :3]
    n = rgb.shape[0] * rgb.shape[1]

    hi = rgb >= HI
    lo = rgb <= LO
    hi_n = hi.sum(axis=2)          # 0..3 channels at the top, per pixel
    lo_n = lo.sum(axis=2)

    out = {
        "clip_ch": float(hi.mean()),          # matches orch_printready `clip`
        "crush_ch": float(lo.mean()),         # matches orch_printready `crush`
        "clip_px_any": float((hi_n > 0).mean()),
        "clip_px_all3": float((hi_n == 3).mean()),
        "clip_px_one": float((hi_n == 1).mean()),
        "crush_px_any": float((lo_n > 0).mean()),
        "crush_px_all3": float((lo_n == 3).mean()),
        "crush_px_one": float((lo_n == 1).mean()),
        "n_px": n,
    }
    for c, name in enumerate("RGB"):
        out["clip_" + name] = float(hi[:, :, c].mean())
        out["crush_" + name] = float(lo[:, :, c].mean())
        # EXACT boundary hits. gamut_map lands on 65535/0 exactly; a scene
        # highlight that merely got bright lands near them but not on them.
        out["exact_hi_" + name] = float((rgb[:, :, c] == 65535).mean())
        out["exact_lo_" + name] = float((rgb[:, :, c] == 0).mean())
    return out


def main(argv):
    root = pathlib.Path(argv[1])
    pat = argv[2] if len(argv) > 2 else "*.tiff"
    paths = sorted(root.glob(pat))
    if not paths:
        raise SystemExit("no masters matching %s in %s" % (pat, root))
    print("clip = channel samples >= %d, crush = channel samples <= %d, "
          "as %% of all samples or all pixels" % (HI, LO))
    print("%-38s %8s %8s %8s %8s | %8s %8s %8s %8s" % (
        "subject", "clipCH", "clipALL3", "clipONE", "clip=R/G/B",
        "crushCH", "crushALL3", "crushONE", "crush=R/G/B"))
    print("-" * 150)
    rows = []
    for p in paths:
        r = census(p)
        if r is None:
            print("%-38s  (not 3-channel)" % p.stem[:38])
            continue
        rows.append((p.stem, r))
        print("%-38s %7.4f%% %7.4f%% %7.4f%% %5.3f/%5.3f/%5.3f | "
              "%7.4f%% %7.4f%% %7.4f%% %5.3f/%5.3f/%5.3f" % (
                  p.stem[:38],
                  r["clip_ch"] * 100, r["clip_px_all3"] * 100,
                  r["clip_px_one"] * 100,
                  r["clip_R"] * 100, r["clip_G"] * 100, r["clip_B"] * 100,
                  r["crush_ch"] * 100, r["crush_px_all3"] * 100,
                  r["crush_px_one"] * 100,
                  r["crush_R"] * 100, r["crush_G"] * 100, r["crush_B"] * 100))
    print("-" * 150)
    print("exact-boundary hits (== 65535 / == 0), the gamut_map signature:")
    print("%-38s %10s %10s %10s | %10s %10s %10s" % (
        "subject", "R==65535", "G==65535", "B==65535",
        "R==0", "G==0", "B==0"))
    for name, r in rows:
        print("%-38s %9.4f%% %9.4f%% %9.4f%% | %9.4f%% %9.4f%% %9.4f%%" % (
            name[:38],
            r["exact_hi_R"] * 100, r["exact_hi_G"] * 100, r["exact_hi_B"] * 100,
            r["exact_lo_R"] * 100, r["exact_lo_G"] * 100, r["exact_lo_B"] * 100))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
