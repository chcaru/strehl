"""Does the HEAD --auto-exposure clipping regression reach MY measurement sites?

ORCH measured that `strehl stack --srgb --auto-exposure` at HEAD blows
highlights on 11 of 18 corpus masters (109MSDCF 92.03% of pixels clipped,
119MSDCF 84.67%, flower-bud-alone-cpl 78.58%, bee-1-cpl ~56-60%). Every master
in the per-band scale sweep was rendered with that recipe, so by ORCH's
case 2 the sweep's numbers are suspect.

But no statistic in this lane reads a whole master. Blotch and grain are read
at flat 560px sites chosen by `blotch.pick_flat_sites`, and sharpness at
textured sites chosen by `ceiling.pick_sites`. BOTH pickers already reject
clipped candidates -- `(c >= 65000).mean() > 0.001` and `clipf > SITE_CLIP_MAX`
respectively. So the question is not whether the master is blown. It is
whether the sites the numbers were actually computed on are blown.

That is an empirical question and this answers it, reporting three things per
subject that a global clip fraction cannot distinguish:

  - the global clip fraction, to confirm the regression is present here at all;
  - how many candidate sites the clip guard REJECTED, because a guard that
    never fires is not evidence that it worked -- it is evidence it was never
    tested;
  - the worst clip fraction among the ACCEPTED sites, which is the number the
    measurements actually depend on.

A guard under no pressure on a blown master would be the alarming finding: it
would mean the picker is choosing from clipped regions and calling them flat.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blotch as bl                                               # noqa: E402
import tifffile                                                   # noqa: E402
from ceiling import pick_sites                                    # noqa: E402
import scale_score as S                                           # noqa: E402

CLIP = 65000


def probe(subject):
    ref = S.arm_path("NULL", subject)
    a = tifffile.imread(ref)[..., :3].astype(np.float64)
    gclip = float((a >= CLIP).mean())
    gmed = float(np.median(a))

    flat, rej, _ = bl.pick_flat_sites(ref)
    fclip = [float((a[y:y + bl.CROP, x:x + bl.CROP, :] >= CLIP).mean())
             for (y, x) in flat]
    tex, trej = pick_sites(a)
    tclip = [float((a[y:y + bl.CROP, x:x + bl.CROP, :] >= CLIP).mean())
             for (y, x) in tex]
    nrejclip = sum(1 for r in trej if "clipped" in r[2])
    return gclip, gmed, flat, rej, fclip, tex, nrejclip, tclip


def main():
    print("Clipping audit of the per-band scale sweep's MEASUREMENT SITES.")
    print("Masters rendered at HEAD with `--srgb --auto-exposure` (ORCH case "
          "2).")
    print("A site counts as clipped if pixels >= %d.\n" % CLIP)
    worst = 0.0
    for s in S.SUBJECTS:
        if not os.path.exists(S.arm_path("NULL", s)):
            continue
        g, gmed, flat, rej, fclip, tex, nrejclip, tclip = probe(s)
        print("%s" % s)
        print("  master        : %.2f%% of pixels clipped, median %.0f"
              % (100 * g, gmed))
        print("  flat sites    : %d accepted, %d rejected for clipping"
              % (len(flat), rej.get("clip", 0)))
        print("                  worst accepted site: %.4f%% clipped"
              % (100 * max(fclip, default=0.0)))
        print("  textured sites: %d accepted, %d rejected for clipping"
              % (len(tex), nrejclip))
        print("                  worst accepted site: %.4f%% clipped"
              % (100 * max(tclip, default=0.0)))
        worst = max(worst, max(fclip, default=0.0), max(tclip, default=0.0))
        print()
    print("Worst clip fraction across every ACCEPTED site, all subjects: "
          "%.4f%%" % (100 * worst))
    if worst > 0.01:
        print("VERDICT: sites are contaminated -- the sweep must be "
              "re-rendered without --auto-exposure.")
        return 1
    print("VERDICT: every accepted site is clean. The blown highlights lie "
          "outside the pixels these statistics read.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
