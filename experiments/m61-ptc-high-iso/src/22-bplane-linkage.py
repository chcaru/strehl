"""M61 step 22 -- the attempt to break step 21's D2 result.

WHAT STEP 21 CONCLUDED, and why it is worth attacking rather than banking.
D2 found B pixels at 16383 in `foam` and `coffee-bubbles`, the same ceiling
the greens reach. A digital per-channel scale of 0.84 applied AFTER the ADC
caps that plane at 0.84 * 16383 = 13761 and can never emit 16383, so D2
refuted the post-ADC-scale hypothesis. D1 independently found no comb.

THE ALTERNATIVE EXPLANATION THAT WOULD VOID IT, and it is not exotic. Many
cameras implement HIGHLIGHT LINKAGE: when any channel saturates, the raw
writer stamps ALL channels of that pixel at container maximum, so the
demosaic does not produce a coloured fringe in a blown highlight. Under
that behaviour a B value of 16383 is a FLAG, not a measured value, and it
would appear whether or not B is digitally scaled. D2 would then be void
and would have looked clean.

I did not think of this before running step 21. I am recording that: the
alternative surfaced from looking at the output, not from the
pre-registration, and it is exactly the kind of thing a pre-registration is
supposed to catch in advance.

--------------------------------------------------------------------------
THE OBSERVABLE THAT SEPARATES THEM, pre-registered before running
--------------------------------------------------------------------------
The two explanations differ in the SHAPE of the B histogram just below the
ceiling, not in whether the ceiling is reached.

  If B is genuinely unscaled and simply saturates, its values approach 16383
  CONTINUOUSLY: the population between 13761 and 16383 is filled in.

  If B is digitally scaled by 0.84 and 16383 is a linkage flag, B can hold
  no real value above 13761. The histogram then shows a POPULATED region up
  to about 13761, a DEAD ZONE from there to 16383, and an isolated SPIKE at
  16383.

So:
  occupancy in (13761, 16383) is substantial     -> D2 stands, H-B refuted
  occupancy in (13761, 16383) is ~zero while
     16383 itself is heavily populated           -> D2 is VOID, linkage
                                                    explains it, and the
                                                    B-plane question
                                                    reverts to open

ACCEPTANCE, fixed now: I call the dead zone real only if the count strictly
between 13761 and 16383 is less than 1% of the count AT 16383. Otherwise
the region is populated and D2 survives. Numbers reported either way.

SECOND, INDEPENDENT ARM -- linkage is testable directly. If the writer
stamps all channels together, then every pixel QUAD containing a 16383 in
any plane has 16383 in ALL FOUR planes. That is a strong, cheap prediction:
  fraction of quads with a saturated plane that are saturated in all four
    near 1.0  -> linkage is operating, D2 void
    well below 1.0 -> planes saturate independently, D2 stands
This arm does not depend on my 13761 threshold at all, so it is a genuine
cross-check rather than a restatement.

--------------------------------------------------------------------------
AND A SEPARATE ERROR IN STEP 21 THAT THIS SCRIPT ALSO SETTLES
--------------------------------------------------------------------------
Step 21's D5 counted pixels above 15360, the white level given in my brief,
and read the existence of values above it as evidence of a multiplicative
step above unity somewhere in the chain. But step 21's own D3' printed the
file's declared `white_level` and it is 16383, NOT 15360. Values between
15360 and 16383 are therefore inside the sensor's declared range and are
not evidence of anything. D5's reading is VOID and I withdraw it.

That leaves a real and separate question, which this script records rather
than resolves: the project constant says white 15360 while the file says
16383. Both can be defensible -- 15360 as a conservative linearity limit,
16383 as the container -- but they are not the same number and anything
that thresholds on saturation is choosing between them. This is M54's
territory, not mine, and I do not touch it.
"""
import glob
import os
import sys

import numpy as np

CORPUS = r"D:\personal\macro"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "data", "bplane-linkage.txt")
CONTAINER = 16383
CAP = int(0.84 * CONTAINER)          # 13761 -- where a 0.84 scale would stop
PL = ("R", "G1", "G2", "B")
LINES = []


def say(s=""):
    print(s)
    LINES.append(s)


def planes(path):
    import rawpy
    with rawpy.imread(path) as r:
        a = r.raw_image_visible.astype(np.int32)
    return {"R": a[0::2, 0::2], "G1": a[0::2, 1::2],
            "G2": a[1::2, 0::2], "B": a[1::2, 1::2]}


def main() -> int:
    say("=" * 78)
    say("M61 step 22 -- breaking step 21's D2: is B's 16383 real, or a")
    say("               highlight-linkage flag?")
    say("=" * 78)
    say()
    say(f"  A 0.84 post-ADC scale would cap a plane at {CAP}.")
    say(f"  Dead zone under test: ({CAP}, {CONTAINER}).")
    say()

    # Only stacks where step 21 saw B at the ceiling can test this.
    picks = ["foam", "coffee-bubbles"]
    frames = []
    for st in picks:
        fs = sorted(glob.glob(os.path.join(CORPUS, st, "*.ARW")))
        for f in (fs[0], fs[len(fs) // 2], fs[-1]):
            frames.append((st, f))

    say("-" * 78)
    say("ARM 1 -- is the region below the ceiling populated in B?")
    say("-" * 78)
    say(f"  {'stack':<16}{'frame':<14}{'plane':>6}"
        f"{'n in zone':>12}{'n at 16383':>12}{'zone/ceil':>11}")
    arm1 = []
    cache = {}
    for st, f in frames:
        pl = planes(f)
        cache[(st, f)] = pl
        for p in ("G1", "B"):
            v = pl[p]
            nz = int(((v > CAP) & (v < CONTAINER)).sum())
            nc = int((v == CONTAINER).sum())
            rat = nz / nc if nc else float("nan")
            say(f"  {st:<16}{os.path.basename(f)[:12]:<14}{p:>6}"
                f"{nz:>12}{nc:>12}{rat:>11.4f}")
            if p == "B" and nc:
                arm1.append(rat)
    say()
    if arm1:
        m = float(np.mean(arm1))
        dead = m < 0.01
        say(f"  B mean zone/ceiling ratio = {m:.4f}   "
            f"(acceptance: dead zone iff < 0.0100)")
        if dead:
            say("  -> DEAD ZONE PRESENT. B holds no real value above the cap.")
            say("     Step 21's D2 is VOID; the 16383s are linkage flags.")
        else:
            say(f"  -> REGION POPULATED. B carries real values above {CAP},")
            say("     which a 0.84 post-ADC scale could not produce.")
            say("     Step 21's D2 SURVIVES this attack.")
    else:
        say("  ARM 1 UNAVAILABLE -- no ceiling pixels found.")
    say()

    say("-" * 78)
    say("ARM 2 -- do planes saturate together?  (independent of the cap)")
    say("-" * 78)
    say("  If the writer stamps all channels when any saturates, every quad")
    say("  with one saturated plane has all four saturated.")
    say()
    say(f"  {'stack':<16}{'frame':<14}{'quads any sat':>15}{'all four':>11}"
        f"{'frac':>9}")
    arm2 = []
    for st, f in frames:
        pl = cache[(st, f)]
        h = min(pl[p].shape[0] for p in PL)
        w = min(pl[p].shape[1] for p in PL)
        sat = {p: (pl[p][:h, :w] == CONTAINER) for p in PL}
        anys = sat["R"] | sat["G1"] | sat["G2"] | sat["B"]
        alls = sat["R"] & sat["G1"] & sat["G2"] & sat["B"]
        na, nl = int(anys.sum()), int(alls.sum())
        fr = nl / na if na else float("nan")
        say(f"  {st:<16}{os.path.basename(f)[:12]:<14}{na:>15}{nl:>11}"
            f"{fr:>9.4f}")
        if na:
            arm2.append(fr)
    say()
    if arm2:
        m2 = float(np.mean(arm2))
        say(f"  mean all-four fraction = {m2:.4f}")
        if m2 > 0.90:
            say("  -> LINKAGE OPERATING. Saturation is stamped across planes,")
            say("     so a B value of 16383 says nothing about B's scale.")
            say("     Step 21's D2 is VOID.")
        else:
            say("  -> planes saturate INDEPENDENTLY. No linkage. A B pixel at")
            say("     16383 is a measured saturation, and a 0.84 post-ADC")
            say("     scale could not produce it. D2 SURVIVES.")
    else:
        say("  ARM 2 UNAVAILABLE.")
    say()

    say("-" * 78)
    say("D5 WITHDRAWN (step 21)")
    say("-" * 78)
    say("  Step 21 counted pixels above 15360 -- the white level from my")
    say("  brief -- and read their existence as evidence of a multiplicative")
    say("  step above unity. The file's own declared white_level is 16383,")
    say("  printed by step 21 itself in the D3' block. Values between 15360")
    say("  and 16383 are inside the declared range and evidence nothing.")
    say("  D5's reading is VOID and withdrawn. The discrepancy between the")
    say("  project's 15360 and the file's 16383 is real and is M54's, not")
    say("  mine; recorded, not touched.")
    say()
    say("=" * 78)

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"\n[wrote {OUT}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
