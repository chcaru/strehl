"""Is `tweezers-cpl`'s bump a rim, or is it the gap between the two arms?

`tweezers-cpl` is the only one of ORCH's four HALO subjects with an actual
interior local maximum in its radial profile (band 4, d=32-50, standing 1373.5
DN above its neighbours). The other three are strictly monotone ramps whose
maximum sits in the outermost band, which is a background gradient and not a
rim. So tweezers is the one that has to be explained rather than dismissed.

`halo_profile.py`'s own header already explains it, and says it was checked:

    tweezers-cpl  bump 1573.7 with the non-monotonicity at d=50-80 px. The
                  tweezers are two separate arms and walking outward from the
                  union silhouette crosses the gap between them. Inspected at
                  1:1: the boundary is clean.

That is an argument plus an eye, from a different lane, on a different render.
This script tests it by construction on today's master.

THE TEST
--------
If the bump is produced by crossing the gap between two arms, then it is a
property of the SECOND arm's presence, not of any edge. Remove the second arm
from the picture the distance transform sees and the bump must vanish.

So: label the subject, keep only the largest connected component as the
silhouette, and additionally EXCLUDE from the background every pixel that is
closer to some other component than to the one being measured. What remains is
one arm on open background, which is the regime the instrument was commissioned
in. Re-run the identical profile.

  bump survives  -> a real rim on the largest arm, and ORCH's verdict stands.
  bump vanishes  -> the gap crossing, and the verdict is a segmentation artifact.

COMMISSIONED BOTH WAYS, because "the number went down after I changed something"
is not evidence on its own:

  NEGATIVE CONTROL. Run the same single-component restriction on a subject with
  ONE compact subject (`flower-bud-alone-cpl`). It is already one blob, so the
  restriction must change its profile by ~nothing. If the restriction moves a
  single-blob subject, the restriction itself is doing damage and any change it
  produces on tweezers is uninterpretable.

  POSITIVE CONTROL. Plant a real rim -- a bright annulus hugging the largest
  component's silhouette -- and confirm the restricted profile DETECTS it. A
  test that only ever removes signal would report "bump vanished" for a broken
  instrument exactly as loudly as for a confound. This is the direction that
  matters: it proves the restricted measurement can still see a rim when one
  is there.
"""
import json
import os
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import (binary_closing, binary_dilation, binary_opening,
                           distance_transform_edt, label)

SRC = pathlib.Path(r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful")
OUT = pathlib.Path(r"C:\dev\strehl-out\V-SPEED-HALO")
NEAR = [(2, 6), (6, 12), (12, 20), (20, 32), (32, 50), (50, 80), (80, 120)]
FAR = (400, 900)
SUB = 4


def luma(a):
    if a.ndim == 3:
        return (0.2126 * a[..., 0] + 0.7152 * a[..., 1]
                + 0.0722 * a[..., 2]).astype(np.float32)
    return a.astype(np.float32)


def otsu(v):
    h, edges = np.histogram(v, bins=256)
    h = h.astype(np.float64)
    w0 = np.cumsum(h)
    w1 = w0[-1] - w0
    mids = (edges[:-1] + edges[1:]) / 2.0
    s0 = np.cumsum(h * mids)
    s1 = s0[-1] - s0
    with np.errstate(invalid="ignore", divide="ignore"):
        m0 = s0 / w0
        m1 = s1 / w1
        var = w0 * w1 * (m0 - m1) ** 2
    var[~np.isfinite(var)] = -1
    return float(mids[int(np.argmax(var))])


def segment(y):
    t = otsu(y.ravel())
    s = y < t
    s = binary_opening(s, np.ones((3, 3)))
    s = binary_closing(s, np.ones((5, 5)))
    return s


def prof(y, subj, keep=None):
    """Radial profile relative to the far field.

    `keep` optionally restricts which background pixels may contribute.
    """
    d = distance_transform_edt(~subj) * SUB
    ok = np.ones_like(subj) if keep is None else keep
    far = (d >= FAR[0]) & (d < FAR[1]) & ok
    if int(far.sum()) < 200:
        return None, None, None
    fl = float(np.median(y[far]))
    vals = []
    for lo, hi in NEAR:
        m = (d >= lo) & (d < hi) & ok
        vals.append(float(np.median(y[m])) - fl if int(m.sum()) > 200 else None)
    v = [x for x in vals if x is not None]
    bump = max((v[i] - v[i + 1] for i in range(len(v) - 1)), default=0.0)
    return max(bump, 0.0), max(v), vals


def largest_only(subj):
    """(silhouette of the largest component, background nearer to it than to
    any other component)."""
    lab, n = label(subj)
    if n <= 1:
        return subj, np.ones_like(subj)
    sizes = np.bincount(lab.ravel())[1:]
    big = int(np.argmax(sizes)) + 1
    keepsub = lab == big
    others = subj & ~keepsub
    if not others.any():
        return keepsub, np.ones_like(subj)
    dbig = distance_transform_edt(~keepsub)
    doth = distance_transform_edt(~others)
    return keepsub, dbig < doth


def plant_rim(y, subj, dn, width=8):
    """A bright annulus hugging the silhouette: a real rim, by construction."""
    ring = binary_dilation(subj, np.ones((3, 3)), iterations=width) & ~subj
    out = y.copy()
    out[ring] += dn
    return out


def run(stem, plant=0.0):
    p = SRC / (stem + ".tiff")
    if not p.exists():
        p = SRC / (stem + ".tif")
    y = luma(tifffile.imread(str(p)))[::SUB, ::SUB]
    subj = segment(y)
    lab, n = label(subj)
    big, keep = largest_only(subj)
    if plant:
        y = plant_rim(y, big, plant)
    b0, o0, v0 = prof(y, subj)
    b1, o1, v1 = prof(y, big, keep)
    return {"subject": stem, "components": int(n), "plant_dn": plant,
            "union_bump": b0, "union_over": o0, "union_bands": v0,
            "largest_bump": b1, "largest_over": o1, "largest_bands": v1}


def show(r):
    print("%-30s comps=%-5d plant=%-7.0f" % (r["subject"], r["components"],
                                             r["plant_dn"]))
    print("    union silhouette      bump %9.1f  overshoot %9.1f"
          % (r["union_bump"], r["union_over"]))
    print("    largest arm only      bump %9.1f  overshoot %9.1f"
          % (r["largest_bump"], r["largest_over"]))


def main():
    print(__doc__.split("THE TEST")[0].strip()[:0] or "", end="")
    print("TWEEZERS: does the bump survive removing the second arm?\n")
    res = {}

    res["tweezers"] = run("tweezers-cpl")
    show(res["tweezers"])

    print("\nNEGATIVE CONTROL -- a subject that is already one blob. The")
    print("restriction must do nothing here, or it is not a clean operation.\n")
    res["neg"] = run("flower-bud-alone-cpl")
    show(res["neg"])

    print("\nPOSITIVE CONTROL -- plant a real 3000 DN rim on the largest arm.")
    print("The restricted measurement must SEE it, or 'bump vanished' above")
    print("means only that the measurement stopped working.\n")
    res["pos"] = run("tweezers-cpl", plant=3000.0)
    show(res["pos"])

    t, ng, ps = res["tweezers"], res["neg"], res["pos"]
    print("\n" + "-" * 74)
    fails = []
    drop = t["union_bump"] - t["largest_bump"]
    if ng["union_bump"] is None or abs(ng["largest_bump"] - ng["union_bump"]) > 50:
        fails.append("negative control moved by %.1f DN (limit 50): the "
                     "restriction is not inert on a single blob"
                     % abs(ng["largest_bump"] - ng["union_bump"]))
    if ps["largest_bump"] < 500:
        fails.append("positive control: a planted 3000 DN rim reads bump "
                     "%.1f on the restricted profile -- it cannot see a rim"
                     % ps["largest_bump"])
    for m in fails:
        print("  [COMMISSION FAIL] " + m)
    if fails:
        print("\nCommissioning failed; the tweezers reading is NOT interpretable.")
        return 1
    print("  commission 2/2 PASS: restriction inert on one blob (%.1f DN),"
          % abs(ng["largest_bump"] - ng["union_bump"]))
    print("  and still detects a planted 3000 DN rim (bump %.1f)."
          % ps["largest_bump"])
    print("\n  tweezers bump %.1f -> %.1f on removing the second arm (%.1f DN, %.0f%%)."
          % (t["union_bump"], t["largest_bump"], drop,
             100.0 * drop / t["union_bump"] if t["union_bump"] else 0.0))
    verdict = "GAP-CROSSING ARTIFACT" if t["largest_bump"] < 200 else "REAL RIM"
    print("  VERDICT: %s (threshold 200 DN, the instrument's own)." % verdict)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tweezers.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
