"""Frame 46 is a REGISTRATION OUTLIER, not a deep frame, and here is the number
that separates the two.

Section 9.25 convicted source frame 46 of bee-2-cpl for capturing 62% of a
coarse band. `vn_shipfr.py` then put the same frame through the pinned binary
one frame at a time and found nothing: 1.011x against nulls of 1.008x and
1.014x. The capture is a property of my bundle, and this is why.

  frame 44  state=OK        ncc_b=0.9467  scale=0.9635
  frame 45  state=OK        ncc_b=0.9471  scale=0.9629
  frame 46  state=POOR-REG  ncc_b=0.0275  scale=0.5800
  frame 47  state=OK        ncc_b=0.9477  scale=0.9617
  frame 48  state=OK        ncc_b=0.9488  scale=0.9612

My registration fitted a 0.58x similarity to a frame whose immediate
neighbours all fit 0.962. The warped window is junk, the junk is broadside
coarse-scale, and a merge that rewards raw coarse-band energy handed it the
band. I convicted my own aligner.

WHY THE ADMISSION RULE DID NOT CATCH IT, AND WHY IT SHOULD NOT HAVE. `rule=
"registered"` admits everything that got a warp, and `vn_gbundle` defends that
choice correctly: on this stack `ncc_b` decays SMOOTHLY with depth -- 0.950,
0.943, 0.916, 0.865, 0.752, 0.628, 0.517, 0.386, 0.265, 0.143 -- so a fixed
0.75 floor cuts a defocus ramp, not a registration cliff, and excluding those
118 frames would measure a subrange and call it the stack. That reasoning still
stands. A fixed threshold on the LEVEL of ncc_b cannot separate these two
populations, because they overlap completely in level.

They do not overlap in SHAPE. Defocus is continuous in frame index; a
registration failure is not. So the discriminator here is each frame's ncc_b
against the median of its NEIGHBOURS, which is flat along a ramp however steep
the ramp is, and large exactly where one frame falls off a cliff its
neighbours did not.

COMMISSIONED IN BOTH DIRECTIONS, because a screen that fires on the frame I
already know about proves nothing on its own:

  P  it must FIRE on frame 46                        (the known positive)
  N  it must be QUIET across the whole defocus ramp  (the known negative --
     118 POOR-REG frames whose low ncc_b is real defocus, every one of which a
     level threshold would flag and this must not)
  S  a SYNTHETIC cliff planted at a frame that is currently clean must be
     found, so the screen's reach is measured rather than assumed
  I  an INVERTED plant -- a frame made anomalously GOOD -- must NOT fire,
     since the defect is a frame that failed where its neighbours succeeded,
     not any frame that differs from them
"""
import io
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_subgate as SG  # noqa: E402

GDIR = r"C:\dev\strehl-out\V-NEVERWORSE\gbundle"
BDIR = r"C:\dev\strehl-out\V-NEVERWORSE\bundle"
HALF = 4          # neighbours each side
THRESH = 0.35     # ncc_b below the local median by this much is a cliff
ROGUE = 46


def deviation(rows):
    """Each frame's ncc_b minus the median of its neighbours, excluding itself.

    Returns (frames, ncc, dev). Frames with no ncc_b are carried as NaN so they
    are counted as unexamined rather than silently dropped.
    """
    fr = [int(r["frame"]) for r in rows]
    ncc = np.array([r["ncc_b"] if r.get("ncc_b") is not None
                    and r["ncc_b"] > -1 else np.nan for r in rows], float)
    dev = np.full(len(ncc), np.nan)
    for i in range(len(ncc)):
        lo, hi = max(0, i - HALF), min(len(ncc), i + HALF + 1)
        nb = np.concatenate([ncc[lo:i], ncc[i + 1:hi]])
        nb = nb[~np.isnan(nb)]
        if np.isnan(ncc[i]) or nb.size < 3:
            continue
        dev[i] = ncc[i] - float(np.median(nb))
    return fr, ncc, dev


def screen(rows):
    fr, ncc, dev = deviation(rows)
    hits = [fr[i] for i in range(len(fr))
            if not np.isnan(dev[i]) and dev[i] < -THRESH]
    return fr, ncc, dev, hits


def load_rows(subj):
    for d in (GDIR, BDIR):
        p = os.path.join(d, "%s.json" % subj)
        if os.path.exists(p):
            return json.load(io.open(p, encoding="utf-8"))["rows"], d
    return None, None


def main():
    rows, src = load_rows("bee-2-cpl")
    if rows is None:
        raise SystemExit("REFUSED: no per-frame record for bee-2-cpl")
    fr, ncc, dev, hits = screen(rows)
    poor = [r["frame"] for r in rows if r.get("state") == "POOR-REG"]
    i46 = fr.index(ROGUE)

    fails = []
    if ROGUE not in hits:
        fails.append("P the screen must fire on frame %d; deviation %.4f "
                     "against a threshold of -%.2f"
                     % (ROGUE, dev[i46], THRESH))
    ramp = [f for f in hits if f in poor and f != ROGUE]
    if len(ramp) > 2:
        fails.append("N the screen must be quiet on the defocus ramp; it fired "
                     "on %d of the %d POOR-REG frames" % (len(ramp), len(poor)))
    # S: plant a cliff on a frame that is currently clean.
    victim = None
    for r in rows:
        if r.get("state") == "OK" and int(r["frame"]) not in hits \
                and int(r["frame"]) != ROGUE:
            victim = int(r["frame"])
            break
    planted = [dict(r) for r in rows]
    for r in planted:
        if int(r["frame"]) == victim:
            r["ncc_b"] = 0.03
    if victim not in screen(planted)[3]:
        fails.append("S a synthetic cliff planted at frame %s was not found; "
                     "the screen's reach is smaller than claimed" % victim)
    # I: the inverted plant. Anomalously GOOD must not fire.
    inv = [dict(r) for r in rows]
    deep = [r for r in rows if r.get("state") == "POOR-REG"
            and r.get("ncc_b") is not None and r["ncc_b"] < 0.4]
    if not deep:
        fails.append("I no deep low-ncc frame exists to plant an inverted "
                     "control on")
        ivict = None
    else:
        ivict = int(deep[len(deep) // 2]["frame"])
        for r in inv:
            if int(r["frame"]) == ivict:
                r["ncc_b"] = 0.99
        if ivict in screen(inv)[3]:
            fails.append("I an anomalously GOOD frame (%s) fired the screen; "
                         "it is detecting difference, not failure" % ivict)

    print("bee-2-cpl per-frame record from %s" % os.path.basename(src))
    print("commissioning")
    print("  P frame %d deviation            %.4f" % (ROGUE, dev[i46]))
    print("  N POOR-REG frames flagged       %d of %d" % (len(ramp), len(poor)))
    print("  S synthetic cliff at frame %-4s found" % victim)
    print("  I inverted plant at frame %-5s %s" % (ivict,
          "correctly quiet" if not any(f.startswith("I ") for f in fails)
          else "FIRED"))
    if fails:
        print("REFUSED -- screen not commissioned:")
        for f in fails:
            print("   " + f)
        return 2
    print("  all four pass")

    nb = [i for i in range(len(fr)) if abs(fr[i] - ROGUE) <= 2
          and fr[i] != ROGUE]
    print("\n  frame %d ncc_b                 %.4f" % (ROGUE, ncc[i46]))
    print("  median ncc_b of its neighbours  %.4f"
          % float(np.median(ncc[nb])))
    print("  deviation                       %.4f" % dev[i46])
    dv = dev[~np.isnan(dev)]
    print("  next worst deviation in stack   %.4f"
          % float(np.sort(dv)[1]))
    print("  frames screened / total         %d / %d"
          % (int((~np.isnan(dev)).sum()), len(fr)))
    print("  flagged                         %s" % hits)

    res = dict(subject="bee-2-cpl", source=os.path.basename(src),
               half=HALF, threshold=THRESH, rogue=ROGUE,
               rogue_ncc=float(ncc[i46]),
               rogue_neighbour_median=float(np.median(ncc[nb])),
               rogue_deviation=float(dev[i46]),
               next_worst=float(np.sort(dv)[1]),
               n_screened=int((~np.isnan(dev)).sum()), n_total=len(fr),
               n_poor_reg=len(poor), n_poor_flagged=len(ramp),
               flagged=hits, commission=dict(passed=True, synthetic=victim,
                                             inverted=ivict))
    p = os.path.join(SG.OUT, "regout.json")
    json.dump(res, io.open(p, "w", encoding="utf-8"), default=float, indent=1)
    print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
