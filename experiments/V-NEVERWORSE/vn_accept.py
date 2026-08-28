"""The N-invariance acceptance criterion, derived from the corrected ladder.

ORCH asked for N-invariance as a first-class acceptance test alongside blotch
and sharpness, with the caution that it must not be winnable by blurring. The
corrected ladder says the criterion has to be stated on TWO terms, because each
alone is trivially gameable:

  SCENE.  Doubling N must not reduce the noise-subtracted scene power at
          0.30-0.35 or 0.40-0.45 cyc/px. An arm can pass any noise test by
          averaging the detail away; this is what refuses it.

  NOISE.  Doubling N must not INCREASE the noise term. The ideal for an
          unweighted average of independent frames is a ratio of exactly 0.5
          per doubling, and that ideal is achievable -- the plain-mean arm
          measures it, and this file prints what it measured rather than
          asserting a number. Any value above 0.5 is frames being spent to
          make the picture noisier.

`noise efficiency` below is the measured noise ratio divided by 0.5, so 1.00 is
the theoretical ideal.

This file only reads artifacts written by vn_ninv2.py. Every number it prints
is parsed out of the JSON; none of the values it compares against are written
here. The one constant it does contain, 0.5, is a derivation (var/N for N
independent samples) and the plain-mean arm measures it as a check.
"""
import io
import json
import os
import sys

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\ninv2"
IDEAL = 0.5


def load(subj):
    with io.open(os.path.join(OUT, "%s.json" % subj), encoding="utf-8") as f:
        return json.load(f)


def rungs(d):
    ks = d["ks"]
    return [(ks[i], ks[i + 1]) for i in range(len(ks) - 1)]


def report(subj):
    d = load(subj)
    rows = {(r["arm"], r["N"]): r for r in d["rows"]}
    arms = []
    for r in d["rows"]:
        if r["arm"] not in arms:
            arms.append(r["arm"])
    print("\n================ %s  (n=%d, %s) ================"
          % (subj, d["n"], "full window" if not d["crop"]
             else "%dpx crop" % d["crop"]))
    nz = d["noise"]
    print("noise gauge: incumbent sigma %.3f DN (gain %.4g) vs paired %.3f DN "
          "(gain %.4g) -- variance over-stated %.3fx"
          % (nz["incumbent_sigma"], nz["incumbent_gain"], nz["paired_sigma"],
             nz["paired_gain"],
             (nz["incumbent_sigma"] / max(nz["paired_sigma"], 1e-9)) ** 2))
    c = d["counts"]
    print("cells: %d examined = %d measured + %d refused"
          % (c["examined"], c["measured"], c["refused"]))

    print("\n  per-doubling behaviour, at matched focus range")
    print("  %-11s %-10s %9s %9s %9s %9s  %s"
          % ("arm", "rungs", "scene mid", "scene fin", "noise", "noise eff",
             "verdict"))
    out = {}
    for a in arms:
        for hi, lo in rungs(d):
            rh, rl = rows[(a, hi)], rows[(a, lo)]
            if rh["degenerate"] or rl["degenerate"]:
                print("  %-11s %-10s %9s"
                      % (a, "%d<-%d" % (hi, lo), "REFUSED"))
                continue
            sm = rh["scene_mid"] / rl["scene_mid"]
            sf = rh["scene_fine"] / rl["scene_fine"]
            nr = rh["noise_mid"] / rl["noise_mid"]
            # The rungs are not always an exact doubling, so normalise the
            # noise ratio to a per-doubling figure before comparing it to the
            # ideal. Without this a 19<-9 rung and a 79<-39 rung are not
            # comparable and the "efficiency" column would rank stack depth.
            import math
            oct_ = math.log(hi / float(lo), 2.0)
            nr_dbl = nr ** (1.0 / oct_)
            eff = nr_dbl / IDEAL
            bad = []
            if sm < 1.0:
                bad.append("loses mid scene")
            if sf < 1.0:
                bad.append("loses fine scene")
            if nr_dbl > IDEAL:
                bad.append("gains noise")
            print("  %-11s %-10s %9.4f %9.4f %9.4f %9.2f  %s"
                  % (a, "%d<-%d" % (hi, lo), sm, sf, nr_dbl, eff,
                     "; ".join(bad) if bad else "PASSES"))
            out.setdefault(a, []).append(
                dict(hi=hi, lo=lo, scene_mid=sm, scene_fine=sf,
                     noise=nr_dbl, eff=eff))
    if "mean" in rows_by_arm(d):
        import math
        got = []
        for hi, lo in rungs(d):
            rh, rl = rows[("mean", hi)], rows[("mean", lo)]
            nr = rh["noise_mid"] / rl["noise_mid"]
            got.append(nr ** (1.0 / math.log(hi / float(lo), 2.0)))
        print("  the 0.5 ideal is not asserted: the plain-mean arm measures "
              "%s per doubling on this subject"
              % ", ".join("%.4f" % g for g in got))
    return d, out


def rows_by_arm(d):
    return set(r["arm"] for r in d["rows"])


def ceiling(out):
    """How much of the N-noise defect does the confidence fix remove?

    Stated as a fraction of the EXCESS over the achievable ideal, not of the
    raw ratio: an arm at 1.69 against an ideal of 0.5 has an excess of 1.19,
    and a fix that moves it to 1.62 has removed 5.8% of the defect, not 4.1%
    of the number.
    """
    if "shipping" not in out or "confidence" not in out:
        return
    print("\n  the fix's ceiling on the N-noise defect")
    print("  %-10s %10s %10s %10s   %s"
          % ("rungs", "ship exc", "fix exc", "removed", "cost in fine scene"))
    for s, c in zip(out["shipping"], out["confidence"]):
        es = s["noise"] - IDEAL
        ec = c["noise"] - IDEAL
        rem = 100.0 * (es - ec) / es if es > 0 else float("nan")
        cost = 100.0 * (c["scene_fine"] / s["scene_fine"] - 1.0)
        print("  %-10s %10.4f %10.4f %9.1f%%   %+.1f%% fine scene retained "
              "per doubling vs shipping"
              % ("%d<-%d" % (s["hi"], s["lo"]), es, ec, rem, cost))


def absolute(d):
    """Ratios alone can be won by an arm that is worse everywhere.

    An arm whose noise merely fails to GROW with N has passed the N-invariance
    test while sitting at twice the noise of an arm that grows. So the levels
    at full depth are printed next to the ratios, and a sharpness term
    (SCENE fine, on the same pixels as the noise term, from the same
    decomposition of the same reconstruction) is carried beside every noise
    number. This is the column that refuses a fix which buys quiet with blur.
    """
    deep = max(d["ks"])
    rows = {r["arm"]: r for r in d["rows"] if r["N"] == deep}
    ship = rows.get("shipping")
    if ship is None:
        return
    print("\n  absolute levels at full depth N=%d, all arms on the SAME pixels"
          % deep)
    print("  %-11s %10s %10s %8s %10s %8s %9s"
          % ("arm", "scene fine", "noise mid", "fine/noi", "scene 20-50",
             "20-50/n", "blotch"))
    for a, r in rows.items():
        if r["degenerate"]:
            print("  %-11s %10s" % (a, "REFUSED"))
            continue
        print("  %-11s %10.4g %10.4g %8.3f %10.4g %8.1f %9.5f"
              % (a, r["scene_fine"], r["noise_mid"],
                 r["scene_fine"] / r["noise_mid"],
                 r["scene_mot"], r["scene_mot"] / r["noise_mot"],
                 r["blotch"]))
    for a, r in rows.items():
        if a == "shipping" or r["degenerate"]:
            continue
        print("    %-11s retains %.1f%% of shipping's fine scene while "
              "carrying %.1f%% of its mid-band noise"
              % (a, 100.0 * r["scene_fine"] / ship["scene_fine"],
                 100.0 * r["noise_mid"] / ship["noise_mid"]))


def selectivity(d, out):
    """Is the noise growth ordered by how selective the arm is?

    The competing explanations for noise rising with N are share dilution
    (which predicts the LEAST selective arm suffers most) and a maximum-of-N
    selection premium (which predicts the MOST selective arm suffers most).
    They disagree in sign, so ranking the arms by winner's share and by noise
    growth settles it without a further experiment.
    """
    deep = max(d["ks"])
    share = {r["arm"]: r["share"] for r in d["rows"] if r["N"] == deep}
    have = [a for a in out if a in share and out[a]]
    if len(have) < 2:
        return
    have.sort(key=lambda a: -share[a])
    print("\n  arms ranked by selectivity at N=%d" % deep)
    print("  %-11s %14s %12s" % ("arm", "winner share", "noise/doubling"))
    for a in have:
        print("  %-11s %14.4f %12.4f" % (a, share[a], out[a][0]["noise"]))
    ns = [out[a][0]["noise"] for a in have]
    mono = all(ns[i] >= ns[i + 1] for i in range(len(ns) - 1))
    print("  noise growth is %sMONOTONE in selectivity across %d arms: "
          "%s -- %s"
          % ("" if mono else "NOT ", len(have),
             " > ".join("%.4f" % x for x in ns),
             "consistent with a maximum-of-N selection premium and against "
             "share dilution, which predicts the opposite order" if mono
             else "neither mechanism is supported by the ordering"))


def main():
    subjects = sys.argv[1:] or ["coffee-bubbles"]
    for s in subjects:
        if not os.path.exists(os.path.join(OUT, "%s.json" % s)):
            print("\n%s: NO ARTIFACT -- not measured, and no claim is made "
                  "about it" % s)
            continue
        d, out = report(s)
        absolute(d)
        selectivity(d, out)
        ceiling(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

