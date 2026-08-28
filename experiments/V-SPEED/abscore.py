# Corpus before/after: one row per subject, both arms, every axis.
#
# THE STATISTIC IS DELIBERATELY STRICTER THAN aura.py's. aura.py lets each
# image choose the band pair it scores, which is right for a VERDICT ("does
# this master have a halo?") because the defect is not at the same radius on
# every subject. It is too loose for an A/B, because an arm that merely MOVED
# its ring would be scored at its new position and could read as an
# improvement. So here the peak band and the trough band are chosen ONCE from
# the baseline arm and every arm is then read at THOSE TWO BANDS.
#
# Both statistics are printed. When they disagree, the disagreement is the
# finding: it means the arm moved the ring rather than removing it.
#
# THE OTHER TWO AXES ARE NOT OPTIONAL. Measured on tweezers-cpl, an arm that
# removes 75.0% of the halo (plain mean, --pyramid-exponent 0.001
# --pyramid-sharpen 1.0) destroys 81.4% of the sharpness. That reproduces
# ORCH's independent warning -- "on blotch alone the worst arm wins", 78%
# sharpness loss on a different subject -- and it means a halo table without
# a sharpness column will rank the blurriest arm first. Black level is carried
# for the same reason at low frequency: `stack --help` warns that a shallow
# pyramid trades "grey ink instead of black", which no high-pass statistic can
# see, and on lead-1-cpl bands5 did cost +266.7 DN of black density while
# reading +2.6% on sharpness.

import argparse
import json
import pathlib
import sys

import numpy as np
import tifffile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from aura import (SUB, luma, measure as aura_measure, prominence, segment,  # noqa
                  verdict)
from sharp import sharpness, subject_mask, textured  # noqa

OUT = pathlib.Path(r"C:\dev\strehl-out\V-SPEED-HALO")

# Rendered masters are BULK (10 GB for this sweep) and live on D:, which has
# free space; the scored .txt/.json above are under a megabyte and stay on C:
# where this lane's report cites them.  D: is preferred but not required, so
# the harness still runs on a machine without it.
_D = pathlib.Path(r"D:\strehl-out\V-SPEED-HALO\sweep")
ROOT = _D if _D.is_dir() else pathlib.Path(r"C:\dev\strehl-out\V-SPEED-HALO\sweep")


def band_index(mids, px):
    """Index of the band whose midpoint is `px`, or None."""
    for i, m in enumerate(mids):
        if abs(m - px) < 1e-6:
            return i
    return None


def fixed_at(meds, i_aura, i_rim):
    """PROMINENCE at the baseline's own band indices, in whatever arm.

    Not `meds[peak] - meds[trough]`, which was the first design and is wrong.
    Measured on 109MSDCF, whose trough sits at 36 px and whose peak sits at
    135 px: that difference read 4139.9 DN against a prominence of 1260.3,
    because with the peak OUTSIDE the trough the subtraction measures the
    whole monotone penumbra rise between them rather than any reversal. It
    would have reported a large "halo" for a perfectly smooth ramp.

    prominence() is immune to a monotone trend by construction -- that is the
    property it was built and commissioned for -- so evaluating it at a FIXED
    index gives a fixed-window statistic that still means what aura.py's
    means. The window is fixed to the baseline's bands so that an arm which
    merely MOVED its ring cannot be scored at the ring's new home.
    """
    v = np.asarray(meds, float)
    out = []
    for i, sign in ((i_aura, -1), (i_rim, +1)):
        if i is None:
            out.append(None)
            continue
        p = prominence(v if sign < 0 else -v)
        # Clamped at zero, exactly as aura.py's deficit()/surplus() do.
        # prominence() returns NEGATIVE where the profile is merely monotone
        # -- that is documented in its own docstring -- so an unclamped read
        # reports -1000 DN for a clean ramp and the sign alone would make a
        # smooth image look defective.
        out.append(round(max(0.0, float(p[i])), 1) if np.isfinite(p[i]) else None)
    return out


def score_subject(d, base_tag, arm_tag):
    b = d / (base_tag + ".tiff")
    a = d / (arm_tag + ".tiff")
    if not (b.exists() and a.exists()):
        return None

    yb = luma(tifffile.imread(str(b)))
    sub_full = subject_mask(yb)
    sites = textured(yb, sub_full)
    sub_b = segment(yb[::SUB, ::SUB])
    rb = aura_measure(yb[::SUB, ::SUB], sub_b)
    if rb is None:
        del yb
        return {"subject": d.name, "skip": "too few bands"}
    s_b = sharpness(yb, sites)
    blk_b = float(np.percentile(yb[sub_full], 1.0))
    del yb

    mids = rb["mids"]
    ip = band_index(mids, rb["rim_at_px"])     # bright peak, from BASELINE
    it = band_index(mids, rb["aura_at_px"])    # dark trough, from BASELINE

    ya = luma(tifffile.imread(str(a)))
    ra = aura_measure(ya[::SUB, ::SUB], sub_b)
    s_a = sharpness(ya, sites)
    blk_a = float(np.percentile(ya[sub_full], 1.0))
    del ya

    def fixed(r):
        if r is None:
            return None
        vals = [x for x in fixed_at(r["meds"], it, ip) if x is not None]
        return max(vals) if vals else None

    hb = max(rb["aura_dn"], rb["rim_dn"])
    ha = max(ra["aura_dn"], ra["rim_dn"]) if ra else None
    fb, fa = fixed(rb), fixed(ra)

    def pct(new, old):
        if new is None or old is None or abs(old) < 1e-9:
            return None
        return round(100.0 * (new - old) / abs(old), 1)

    return {
        "subject": d.name,
        "base_verdict": verdict(rb),
        "arm_verdict": verdict(ra) if ra else None,
        "halo_base": hb, "halo_arm": ha,
        "halo_pct": pct(ha, hb),
        "peak_px": rb["rim_at_px"], "trough_px": rb["aura_at_px"],
        "fixed_base": fb, "fixed_arm": fa,
        "fixed_pct": pct(fa, fb),
        "sharp_base": round(s_b, 2), "sharp_arm": round(s_a, 2),
        "sharp_pct": round(100.0 * (s_a / s_b - 1.0), 2),
        "black_delta": round(blk_a - blk_b, 1),
    }


def selftest():
    """Guard the defect that the first version of fixed_at() actually had.

    The first design returned meds[peak] - meds[trough]. On a PURELY MONOTONE
    ramp with no defect at all that returns the full height of the ramp, so
    it would have reported a large halo for a clean image -- and it did:
    109MSDCF read 4139.9 DN against a true prominence of 1260.3. Test 1 is
    that exact case and the old code fails it by construction.
    """
    print("=" * 68)
    print("abscore.py fixed_at() self-test")
    print("=" * 68)
    fails = []

    # A monotone ramp. Trough index inside, peak index outside -- the 109MSDCF
    # geometry that broke the first design.
    #
    # THE SLOPE IS 100 DN/BAND AND THAT IS NOT ARBITRARY. The first version of
    # this self-test used 1000 DN/band with a 700 DN notch, and every plant
    # failed -- correctly, because a 700 DN dip in a 1000 DN/band rise leaves
    # the profile MONOTONE and there is no valley to find. The plant has to be
    # larger than the trend it sits on or it is not the defect it claims to
    # be. Same class as an earlier failure in sharp.py, where a 31 px-period
    # texture made a working blur metric look blind.
    ramp = [100.0 * i for i in range(12)]
    fa, fr = fixed_at(ramp, i_aura=3, i_rim=9)
    got = max(x for x in (fa, fr) if x is not None)
    ok = abs(got) < 1.0
    fails += [] if ok else ["monotone ramp reads %.1f, must be ~0" % got]
    print("[%s] 1 monotone ramp reads %.1f DN (must be ~0; old design gave 600)"
          % ("PASS" if ok else "FAIL", got))

    # Same ramp with a 700 DN notch cut at index 3. The prominence of a notch
    # is its depth below the LOWER of its two shoulders, so the expected value
    # is computed from the plant rather than assumed equal to the cut.
    notch = list(ramp)
    notch[3] -= 700.0
    want = min(max(ramp[:3]), max(ramp[4:])) - notch[3]
    fa, fr = fixed_at(notch, i_aura=3, i_rim=9)
    ok = abs(fa - want) < 1.0
    fails += [] if ok else ["notch reads %.1f, expected %.1f" % (fa, want)]
    print("[%s] 2 planted notch reads %.1f DN (expected %.1f)"
          % ("PASS" if ok else "FAIL", fa, want))

    # And a 700 DN bump, to prove the rim channel is not simply the aura
    # channel under another name.
    bump = list(ramp)
    bump[9] += 700.0
    want_r = bump[9] - max(min(ramp[:9]), min(ramp[10:]))
    fa, fr = fixed_at(bump, i_aura=3, i_rim=9)
    ok = abs(fr - want_r) < 1.0
    fails += [] if ok else ["bump reads %.1f, expected %.1f" % (fr, want_r)]
    print("[%s] 3 planted bump reads %.1f DN (expected %.1f)"
          % ("PASS" if ok else "FAIL", fr, want_r))

    # NEGATIVE CONTROL ON THE WINDOW. A defect at an index the baseline did
    # NOT flag must NOT be picked up, or the window is not fixed and an arm
    # that moved its ring would score as an arm that removed it.
    moved = list(ramp)
    moved[6] -= 700.0
    fa, fr = fixed_at(moved, i_aura=3, i_rim=9)
    got = max(abs(x) for x in (fa, fr) if x is not None)
    ok = got < 1.0
    fails += [] if ok else ["window not fixed: off-index defect read %.1f" % got]
    print("[%s] 4 defect at an UNFLAGGED index reads %.1f DN (window is fixed)"
          % ("PASS" if ok else "FAIL", got))

    print("-" * 68)
    print("%d/4 PASS" % (4 - len(fails)))
    for f in fails:
        print("  FAIL: %s" % f)
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--base", default="baseline")
    ap.add_argument("--arm", default="bands5")
    ap.add_argument("--tag", default="ab")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    root = pathlib.Path(a.root)
    dirs = sorted(p for p in root.iterdir() if p.is_dir())
    rows = []
    print("corpus A/B: '%s' vs '%s'\n" % (a.base, a.arm))
    print("%-28s %10s %10s %8s %9s %9s %8s %8s %8s"
          % ("subject", "halo base", "halo arm", "d halo",
             "fix base", "fix arm", "d fix", "d sharp", "d black"))
    print("-" * 108)
    for d in dirs:
        r = score_subject(d, a.base, a.arm)
        if r is None:
            continue
        if r.get("skip"):
            print("%-28s  SKIP %s" % (r["subject"], r["skip"]))
            continue
        rows.append(r)
        print("%-28s %10.1f %10.1f %7s %9s %9s %7s %+7.2f%% %+8.1f"
              % (r["subject"], r["halo_base"], r["halo_arm"],
                 "%+.1f%%" % r["halo_pct"] if r["halo_pct"] is not None else "-",
                 "%.1f" % r["fixed_base"] if r["fixed_base"] is not None else "-",
                 "%.1f" % r["fixed_arm"] if r["fixed_arm"] is not None else "-",
                 "%+.1f%%" % r["fixed_pct"] if r["fixed_pct"] is not None else "-",
                 r["sharp_pct"], r["black_delta"]))
    print("-" * 108)
    if not rows:
        print("no scorable subjects under %s" % root)
        return 1

    hp = [r["halo_pct"] for r in rows if r["halo_pct"] is not None]
    sp = [r["sharp_pct"] for r in rows]
    bd = [r["black_delta"] for r in rows]
    print("%d subjects.  halo   median %+.1f%%  range %+.1f%% .. %+.1f%%"
          % (len(rows), float(np.median(hp)), min(hp), max(hp)))
    print("%29s sharp  median %+.2f%%  range %+.2f%% .. %+.2f%%"
          % ("", float(np.median(sp)), min(sp), max(sp)))
    print("%29s black  median %+.1f DN  range %+.1f .. %+.1f DN"
          % ("", float(np.median(bd)), min(bd), max(bd)))
    worse = [r["subject"] for r in rows if r["halo_pct"] is not None
             and r["halo_pct"] > 5.0]
    grey = [r["subject"] for r in rows if r["black_delta"] > 200.0]
    soft = [r["subject"] for r in rows if r["sharp_pct"] < -1.0]
    print("\nACCEPTANCE (a fix must not do these):")
    print("  halo worse by >5%%   : %s" % (", ".join(worse) if worse else "NONE"))
    print("  blacks >200 DN grey : %s" % (", ".join(grey) if grey else "NONE"))
    print("  sharpness <-1%%      : %s" % (", ".join(soft) if soft else "NONE"))
    print("\nVERDICT CHANGES:")
    if all(r["base_verdict"] == r["arm_verdict"] for r in rows):
        print("  NONE -- every subject keeps its baseline verdict.")
    else:
        for r in rows:
            if r["base_verdict"] != r["arm_verdict"]:
                print("  %-28s %s -> %s"
                      % (r["subject"], r["base_verdict"], r["arm_verdict"]))

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / ("abscore-%s.json" % a.tag)
    p.write_text(json.dumps(rows, indent=1))
    print("\nwrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
