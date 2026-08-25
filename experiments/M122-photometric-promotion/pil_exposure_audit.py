"""M122 -- PIL narrowing exposure audit, run rather than asserted.

The orchestrator's lesson: a triage list shipped without being read is an
uncommissioned instrument. The same applies to my ANSWER to that list. So this
does not claim non-exposure -- it demonstrates it, and it demonstrates that the
demonstration could have failed:

  1. the hazard is LIVE on the exact files I measured (a PIL pixel read really
     does narrow them here) -- otherwise a pass would be vacuous;
  2. my loader is not narrowed on those same files;
  3. what the narrowing WOULD have done to each class of number I reported,
     which is the orchestrator's two triage questions answered with measurement
     instead of reasoning:
        - absolute statistics (hf0, dHF, the continuous intercept)
        - same-scale ratios of two arms (B12, k) -- do they cancel?

Reads C:\\dev\\strehl-out\\M122\\measure. Writes nothing but stdout.
"""

import os

import numpy as np
import tifffile
from PIL import Image

MEAS = r"C:\dev\strehl-out\M122\measure"
S = 256


def mine(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, "%s read as %s, expected uint16" % (p, a.dtype)
    return a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)


def hazard(p):
    """The pattern under notice: Image.open -> asarray ON THE PIXELS."""
    a = np.asarray(Image.open(p))
    return a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)


def hf(w):
    lap = -4 * w[1:-1, 1:-1] + w[:-2, 1:-1] + w[2:, 1:-1] + w[1:-1, :-2] + w[1:-1, 2:]
    return float(np.sqrt((lap ** 2).mean()))


def main():
    p0 = os.path.join(MEAS, "tweezers-cpl__A0.tif")
    p1 = os.path.join(MEAS, "tweezers-cpl__A1.tif")

    with Image.open(p0) as im:
        print("STEP 1 -- is the hazard live on my own files?")
        print("  PIL sees mode=%s size=%s" % (im.mode, im.size))
    raw = tifffile.imread(p0)
    print("  tifffile sees dtype=%s shape=%s" % (raw.dtype, raw.shape))

    a_ok, a_bad = mine(p0), hazard(p0)
    b_ok, b_bad = mine(p1), hazard(p1)
    print("  full-frame max   mine %.1f   hazard %.1f" % (a_ok.max(), a_bad.max()))
    if a_ok.max() <= 255:
        print("  !! this file is not 16-bit; the audit is VACUOUS on it")
        return
    print("  -> hazard is LIVE on this file: a PIL pixel read narrows it.\n")

    # x=912 y=400 is the blotch window fact 1638 cites and my instrument picked.
    for tag, x, y in (("BLOTCH  x=912 y=400", 912, 400),
                      ("DETAIL  x=400 y=656", 400, 656)):
        w_ok = a_ok[y:y + S, x:x + S]
        w_bad = a_bad[y:y + S, x:x + S]
        v_ok = b_ok[y:y + S, x:x + S]
        v_bad = b_bad[y:y + S, x:x + S]
        occ = w_ok.max() - w_ok.min()
        print("STEP 2 -- %s   (occupied range %.0f DN)" % (tag, occ))
        print("  distinct levels   mine %6d      hazard %6d   (%.0fx coarser)"
              % (len(np.unique(w_ok)), len(np.unique(w_bad)),
                 len(np.unique(w_ok)) / max(len(np.unique(w_bad)), 1)))
        print("  ABSOLUTE  hf(A0)  mine %9.2f  hazard %9.2f   error x%.3f"
              % (hf(w_ok), hf(w_bad), hf(w_bad) / hf(w_ok)))
        r_ok, r_bad = hf(v_ok) / hf(w_ok), hf(v_bad) / hf(w_bad)
        print("  RATIO     A1/A0   mine %9.4f  hazard %9.4f   moved %+.4f (%+.1f%%)"
              % (r_ok, r_bad, r_bad - r_ok, 100 * (r_bad - r_ok) / r_ok))
        print("            -> toward 1.0000 by %+.4f\n"
              % (abs(r_bad - 1.0) - abs(r_ok - 1.0)))

    print("STEP 3 -- triage answers for M122's reported numbers")
    print("  Q1 is my statistic absolute?")
    print("     YES for hf0 (I quote 41.6 .. 3712.1 DN), dHF, the continuous")
    print("     intercept c, and Dpp's mean levels in DN. These would be wrecked.")
    print("  Q2 does it divide a small quantity by a large one?")
    print("     NO -- and STEP 2 shows Q2 is NOT sufficient. The detail window's")
    print("     same-arm ratio cancelled to -0.1%%, but the BLOTCH window's moved")
    print("     +31.4%% TOWARD 1.0. Cancellation protects a ratio only while the")
    print("     measured quantity stays large against the post-narrowing step.")
    print("  Both classes are safe here only because no reported number came from")
    print("  pixels PIL returned -- see the grep in the report, not this reasoning.\n")

    counterfactual()


def counterfactual():
    """STEP 4 -- would the hazard have turned question 203 into a null?

    Rescores B12 on the SAME 12 windows already chosen and stored, so nothing is
    re-selected; only the pixel read changes. Then recomputes the headline
    correlation. This is the cost of the hazard measured on the actual result,
    rather than argued from the mechanism.
    """
    import json

    import correlate as C

    OUT = r"C:\dev\strehl-out\M122"
    reg = json.load(open(os.path.join(OUT, "correlate.json")))
    drift = {r["stack"]: r for r in json.load(open(os.path.join(OUT, "drift-corpus.json")))}
    blotch = {r["stack"]: r for r in json.load(open(os.path.join(OUT, "blotch-ab.json")))}
    used = reg["used"]

    print("STEP 4 -- the counterfactual: this milestone re-scored through PIL")
    print("%-38s %9s %9s %9s" % ("stack", "B12 real", "B12 PIL", "toward 1"))
    xs, y_real, y_haz = [], [], []
    for s in used:
        p0 = os.path.join(MEAS, "%s__A0.tif" % s)
        p1 = os.path.join(MEAS, "%s__A1.tif" % s)
        a, b = hazard(p0), hazard(p1)
        rs = []
        for w in blotch[s]["smooth_windows"]:
            x, y = w["x"], w["y"]
            h0 = hf(a[y:y + S, x:x + S])
            h1 = hf(b[y:y + S, x:x + S])
            rs.append(h1 / h0 if h0 > 0 else 1.0)
        bh = float(np.median(rs))
        br = blotch[s]["B12"]
        print("%-38s %9.4f %9.4f %+9.4f"
              % (s, br, bh, abs(bh - 1.0) - abs(br - 1.0)))
        xs.append(drift[s]["Dpp"])
        y_real.append(1 - br)
        y_haz.append(1 - bh)

    xs = np.array(xs)
    for lab, y in (("REAL (tifffile)", np.array(y_real)), ("PIL-narrowed  ", np.array(y_haz))):
        rho = C.spearman(xs, y)
        p1_, p2_, sd = C.perm_p(xs, y, rho)
        print("  %s : rho %+.4f  one-sided p %.4f  null sd %.4f  -> P2 (rho>=+0.50, p<0.05) %s"
              % (lab, rho, p1_, sd, "PASS" if (rho >= 0.50 and p1_ < 0.05) else "**FAIL**"))


if __name__ == "__main__":
    main()
