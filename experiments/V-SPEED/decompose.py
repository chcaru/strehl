# Split each subject's measured halo into the part the merge causes and the
# part the scene contributes, then say how much of the FORMER a candidate fix
# removes.
#
# WHY THIS IS THE RIGHT DENOMINATOR. A raw "halo fell 39.8%" quotes the fix
# against a total that includes structure no merge change can touch. Measured
# on tweezers-cpl, the plain-mean arm -- same frames, same alignment, same
# tone pipeline, NO selection -- still shows 654.9 DN of radial structure. So
# 654.9 DN of that subject's 2621.7 is the scene, and a merge fix that removed
# every trace of selection ringing would still leave it. Dividing by the total
# therefore understates a good fix and, worse, makes subjects with big scene
# gradients look unfixable when in truth they had nothing to fix.
#
# The two gradient subjects make the point at the other extreme: 112MSDCF
# reads 8679.8 DN and flat-on-ruler-cpl 5579.3 DN, the two largest numbers in
# the corpus, and bands5 moves them by 1.8% and 0.2%. Those are lighting
# arches, 65 and 172 px wide, and no selection knob can move a lighting arch.
# Reporting them in the same column as tweezers-cpl's 20 px ring invites the
# reader to average two different things.
#
# INPUTS are two abscore.py runs sharing one baseline:
#   abscore.py --arm bands5    --tag bands5
#   abscore.py --arm plainmean --tag scene
# Both read their band indices from the SAME baseline arm, so `fixed_base`,
# and the two `fixed_arm` values, are all measured in the same window and are
# subtractable. That is the only reason this join is legitimate.

import argparse
import json
import pathlib
import sys

import numpy as np

OUT = pathlib.Path(r"C:\dev\strehl-out\V-SPEED-HALO")


def load(tag):
    p = OUT / ("abscore-%s.json" % tag)
    if not p.exists():
        print("missing %s" % p)
        return None
    return {r["subject"]: r for r in json.loads(p.read_text())}


# A scene floor is only a scene floor if the arm that measured it is the same
# picture at a different selection. It is not, if the arm also moved the tone.
# MEASURED: the plain-mean arm shifts black level by -722 DN on tweezers-cpl
# and +66..+798 DN on 109/112/119MSDCF, but by +4173 DN on flat-on-ruler-cpl
# and +4640 DN on foam. At four thousand DN the arm is a different rendering,
# and subtracting its radial profile from the shipping one is not a
# decomposition, it is a difference of two unlike images. Those subjects get
# their number withheld rather than quietly averaged in.
TONE_LIMIT_DN = 1000.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", default="bands5")
    ap.add_argument("--scene", default="scene")
    ap.add_argument("--tag", default="decompose")
    a = ap.parse_args()

    F, S = load(a.fix), load(a.scene)
    if F is None or S is None:
        return 1

    print("halo decomposition: total = no-selection floor + merge excess\n")
    print("NOTE ON THE NAME. The floor arm removes PER-PIXEL SELECTION and")
    print("nothing else, so what survives it is everything that is not")
    print("selection: veiling glare and lens flare around a dark subject,")
    print("the lighting field, and any residual misregistration, all of which")
    print("are present identically in a plain average. It is NOT evidence")
    print("that the scene alone causes the structure -- only that the merge's")
    print("selection does not.\n")
    print("%-28s %8s %8s %8s %8s %8s %9s %6s"
          % ("subject", "total", "floor", "merge", "fix", "fix-merge",
             "d merge", "tone"))
    print("-" * 100)
    rows = []
    withheld = []
    for s in sorted(F):
        if s not in S:
            continue
        f, sc = F[s], S[s]
        tot = f["fixed_base"]
        scene = sc["fixed_arm"]
        fix = f["fixed_arm"]
        if tot is None or scene is None or fix is None:
            print("%-28s  (not scorable in one arm)" % s)
            continue
        tone = abs(sc["black_delta"])
        if tone > TONE_LIMIT_DN:
            withheld.append((s, sc["black_delta"]))
            print("%-28s %8.1f %8s %8s %8.1f %9s %9s %6.0f  WITHHELD"
                  % (s, tot, "-", "-", fix, "-", "-", tone))
            continue
        # The plain mean is not guaranteed to be BELOW the shipping merge --
        # if it is above, the shipping merge already has less radial structure
        # than a no-selection average and there is no merge excess to remove.
        # That is a real outcome, not an error, and it is printed rather than
        # clipped away.
        m_base = tot - scene
        m_fix = fix - scene
        d = (100.0 * (m_fix - m_base) / m_base) if abs(m_base) > 1e-6 else None
        rows.append({"subject": s, "total": tot, "scene": scene,
                     "merge_base": round(m_base, 1), "fix": fix,
                     "merge_fix": round(m_fix, 1),
                     "merge_pct": round(d, 1) if d is not None else None,
                     "scene_frac": (round(100.0 * scene / tot, 1)
                                    if abs(tot) > 1e-6 else None),
                     "sharp_pct": f["sharp_pct"],
                     "black_delta": f["black_delta"],
                     "scene_tone": sc["black_delta"],
                     "verdict": f["base_verdict"]})
        print("%-28s %8.1f %8.1f %8.1f %8.1f %9.1f %9s %6.0f"
              % (s, tot, scene, m_base, fix, m_fix,
                 "%+.1f%%" % d if d is not None else "-", tone))
    print("-" * 100)
    if withheld:
        print("\nWITHHELD -- the no-selection arm also moved BLACK LEVEL by more")
        print("than %.0f DN on these, so it is not the same picture at a" % TONE_LIMIT_DN)
        print("different selection and its profile is not a scene floor:")
        for s, d in withheld:
            print("  %-28s black %+.1f DN" % (s, d))
    if not rows:
        print("nothing to join")
        return 1

    print("\nhow much of each subject's halo SURVIVES REMOVING SELECTION (and")
    print("so cannot be addressed by any selection knob), and what the fix")
    print("did to the addressable remainder:\n")
    print("%-28s %-12s %9s %11s %9s %9s"
          % ("subject", "verdict", "floor %", "d merge", "d sharp", "d black"))
    print("-" * 84)
    for r in sorted(rows, key=lambda r: -(r["scene_frac"] or 0)):
        print("%-28s %-12s %8s%% %10s %8.2f%% %+8.1f"
              % (r["subject"], r["verdict"],
                 r["scene_frac"] if r["scene_frac"] is not None else "-",
                 "%+.1f%%" % r["merge_pct"] if r["merge_pct"] is not None else "-",
                 r["sharp_pct"], r["black_delta"]))
    print("-" * 84)

    mp = [r["merge_pct"] for r in rows if r["merge_pct"] is not None]
    sf = [r["scene_frac"] for r in rows if r["scene_frac"] is not None]
    if mp:
        print("merge-excess change: median %+.1f%%, range %+.1f%% .. %+.1f%%, n=%d"
              % (float(np.median(mp)), min(mp), max(mp), len(mp)))
    if sf:
        print("no-selection floor : median %.1f%%, range %.1f%% .. %.1f%%, n=%d"
              % (float(np.median(sf)), min(sf), max(sf), len(sf)))
    neg = [r["subject"] for r in rows if r["merge_base"] <= 0]
    if neg:
        print("\nNO MERGE EXCESS TO REMOVE (plain mean is no cleaner than the")
        print("shipping merge on these -- their halo is not selection ringing):")
        print("  %s" % ", ".join(neg))

    p = OUT / ("decompose-%s.json" % a.tag)
    p.write_text(json.dumps(rows, indent=1))
    print("\nwrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
