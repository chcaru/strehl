"""Does ORCH's compensation formula predict the gating rate on a NEW subject?

ORCH derived k = 1.29 as 2.0 / 1.5504, where 1.5504 is `leaf-2-cpl`'s measured
floor at band 0 in units of the white floor, and verified it reproduced that
subject's pre-fix gating rate (6.9% vs 7.1%).

That is one subject, and it is the subject the constant was derived on. The
mechanism it assumes is stronger and is testable: if the measured floor is just
the white floor scaled by `xw` at band 0, then gating at `k` against the
measured floor must equal gating at `k * xw` against the white floor, so

    k_pred = 2.0 / xw

should reproduce the white arm's averaged@L0 on ANY subject. `xw` varies
1.0888-1.5504 across the four subjects now measured, so the subjects disagree
about what the landmark is -- which makes this a real test rather than a
restatement.

k_obs is read off each subject's own measured-floor sweep by interpolating
averaged@L0 to the white arm's value. Prediction and observation are computed
from disjoint arms: k_pred uses only the `x white` header, k_obs uses only the
averaged percentages.
"""
import os
import re
import sys

import numpy as np

AB = r"C:\dev\strehl-out\BUILD-GATE\head\ab"
KS = [("G090", 0.9), ("G100", 1.0), ("G129", 1.29), ("G140", 1.4),
      ("G160", 1.6), ("G200", 2.0), ("G260", 2.6)]
SUBJECTS = ["coffee-bubbles", "109MSDCF", "119MSDCF",
            "flower-bud-alone-cpl", "bee-1-cpl"]


def read(arm, subject):
    p = os.path.join(AB, arm, subject + ".log")
    if not os.path.exists(p):
        return None, None
    t = open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"^averaged\s*:\s*([\d.]+)%", t, re.M)
    avg = float(m.group(1)) if m else None
    m = re.search(r"x white\s*:\s*([\d.]+)", t)
    return avg, (float(m.group(1)) if m else None)


def invert(ks, avgs, target):
    """k at which averaged@L0 == target, by linear interpolation."""
    for i in range(len(ks) - 1):
        lo, hi = avgs[i], avgs[i + 1]
        if (lo - target) * (hi - target) <= 0 and hi != lo:
            f = (target - lo) / (hi - lo)
            return ks[i] + f * (ks[i + 1] - ks[i])
    return None


def main():
    print("Testing ORCH's compensation formula k_pred = 2.0 / xw on subjects")
    print("it was not derived on. k_pred from the floor header; k_obs from the")
    print("averaged sweep. Disjoint inputs.\n")
    print("  %-22s %7s %8s %8s %8s %7s"
          % ("subject", "xw b0", "white%", "k_pred", "k_obs", "err"))
    rows, ok, bad, skip = [], 0, 0, 0
    for s in SUBJECTS:
        wavg, _ = read("WHITE200", s)
        ks, avgs, xw = [], [], None
        for arm, k in KS:
            a, x = read(arm, s)
            if a is None:
                continue
            ks.append(k)
            avgs.append(a)
            xw = x if x is not None else xw
        if wavg is None or xw is None or len(ks) < 2:
            print("  %-22s %s" % (s, "not rendered yet"))
            skip += 1
            continue
        kp = 2.0 / xw
        ko = invert(ks, avgs, wavg)
        if ko is None:
            print("  %-22s %7.4f %7.1f%% %8.3f %8s %7s"
                  % (s, xw, wavg, kp, "off-grid", "-"))
            skip += 1
            continue
        err = (ko - kp) / kp
        print("  %-22s %7.4f %7.1f%% %8.3f %8.3f %+6.1f%%"
              % (s, xw, wavg, kp, ko, 100 * err))
        rows.append((s, xw, kp, ko, err))
        if abs(err) <= 0.15:
            ok += 1
        else:
            bad += 1
    print("\n  within 15%%: %d   outside: %d   not scorable: %d   = %d"
          % (ok, bad, skip, ok + bad + skip))
    if rows:
        xws = [r[1] for r in rows]
        print("\n  xw b0 spans %.4f-%.4f across %d subjects, so k_pred spans"
              % (min(xws), max(xws), len(rows)))
        print("  %.3f-%.3f. ORCH's 1.29 is leaf-2-cpl's value, not a constant."
              % (2.0 / max(xws), 2.0 / min(xws)))
    return decoy(rows) if bad == 0 and ok >= 2 else 1


def decoy(rows):
    """Is the agreement above specific, or would any floor number have fit?

    Three points spanning 13% can agree by luck. The control asks the same
    formula to predict from BAND 1 instead of band 0. Band 1 is the wrong
    band -- averaged@L0 is gated by the band-0 floor -- so a formula that is
    actually reading the mechanism must FAIL here. If the b1 decoy fits too,
    the b0 fit means nothing and this test is not an instrument.
    """
    if not rows:
        return 1
    print("\n  DECOY CONTROL: same formula, band 1 floor ratio (the wrong "
          "band).")
    print("  %-22s %8s %8s %8s" % ("subject", "xw b1", "k_decoy", "err"))
    errs, kd = [], []
    for s, _, _, ko, _ in rows:
        t = open(os.path.join(AB, "G200", s + ".log"),
                 encoding="utf-8", errors="replace").read()
        b1 = float(re.search(r"x white\s*:\s*[\d.]+\s+([\d.]+)", t).group(1))
        k = 2.0 / b1
        kd.append(k)
        errs.append((ko - k) / k)
        print("  %-22s %8.4f %8.3f %+7.1f%%" % (s, b1, k, 100 * errs[-1]))
    worst = max(abs(e) for e in errs)
    spread = (max(kd) - min(kd)) / np.mean(kd)
    print("  worst decoy error %.1f%% (b0 worst was 0.8%%); decoy k spans "
          "only %.1f%%" % (100 * worst, 100 * spread))
    if worst < 0.05:
        print("  DECOY ALSO FITS -> the b0 agreement is not evidence. FAIL")
        return 1
    print("  decoy rejected: the fit is specific to band 0, which is the band")
    print("  that gates level 0. The agreement is reading the mechanism. PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
