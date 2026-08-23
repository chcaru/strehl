"""M61 step 19 -- inter-stack gaps, and what they say about the matched pairs.

Arm A of script 18 turned up something the brief did not mention: the
CPL-ON population is NOT one session. `coffee-bubbles` and `foam` are
25 May 2026; `wrapped-text-1/2` and `bee-1/2/3` are 23 August 2026 --
ninety days later, and a few hours before this milestone read them.

Two consequences, both pre-registered here before this script runs:

A. THE BRACKET TEST GAINS A THIRD CONFOUND. Script 18 arm D found a dip at
   ISO 100. Its ISO-100 stacks are all from the August session, while its
   ISO-50 and ISO-160 stacks are all from May. So the dip is confounded
   with subject (registered in script 18) AND with a ninety-day gap in
   time, equipment handling and technique. Report it as three-way
   confounded, which is weaker than script 18 concluded.

B. THE GAPS ARE AN INDEPENDENT CHECK ON THE OWNER'S MATCHED-PAIR
   CORRECTION -- the correction I acted on in section 3.3 purely on his
   say-so. He reported that `bee-2`/`bee-3` ARE matched, that `bee-1` is a
   different angle and depth, and that `wrapped-text-1`/`-2` are slightly
   different angles.

   Prediction, fixed before running: if that is true, the gap between
   `bee-2` and `bee-3` should be SHORT -- no time to reposition -- and the
   gaps around `bee-1` and between the two `wrapped-text` stacks should be
   LONGER, because moving a camera and refocusing on a new depth takes
   time. I pre-register the direction and NOT a threshold, because I have
   no calibration for how long the owner takes to reposition a macro rig.

   This can corroborate or contradict. It cannot prove framing identity --
   a short gap is consistent with an unmoved camera, not proof of one --
   and I will not report it as more than corroboration.

   If the gaps come out the other way round, the owner's correction and my
   section 3.3 are both in question, and that is what I would report.
"""
import glob
import os
import sys
from datetime import datetime

CORPUS = r"D:\personal\macro"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "data", "stack-gaps.txt")
AUG = ["wrapped-text-1", "wrapped-text-2", "bee-1", "bee-2", "bee-3"]
LINES = []


def say(s=""):
    print(s)
    LINES.append(s)


def dt_of(path):
    import exifread
    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False,
                                  stop_tag="EXIF DateTimeOriginal")
    for k in ("EXIF DateTimeOriginal", "Image DateTime"):
        if k in t:
            return datetime.strptime(str(t[k]), "%Y:%m:%d %H:%M:%S")
    return None


def main() -> int:
    say("=" * 72)
    say("M61 step 19 -- inter-stack gaps in the August session")
    say("=" * 72)
    say()

    span = {}
    for s in AUG:
        fs = sorted(glob.glob(os.path.join(CORPUS, s, "*.ARW")))
        span[s] = (dt_of(fs[0]), dt_of(fs[-1]), len(fs))

    order = sorted(AUG, key=lambda s: span[s][0])
    say(f"  {'stack':<16}{'n':>5}  {'start':<9}{'end':<9}{'dur':>8}"
        f"{'gap from prev':>16}")
    prev_end = None
    gaps = {}
    for s in order:
        a, b, n = span[s]
        dur = (b - a).total_seconds()
        gap = (a - prev_end).total_seconds() if prev_end else None
        gaps[s] = gap
        gs = f"{gap/60:.1f} min" if gap is not None else "--"
        say(f"  {s:<16}{n:>5}  {a:%H:%M:%S} {b:%H:%M:%S} {dur:>6.0f}s"
            f"{gs:>16}")
        prev_end = b
    say()

    say("-" * 72)
    say("THE OWNER'S MATCHED-PAIR CORRECTION, checked against the clock")
    say("-" * 72)
    say("  claim: bee-2 / bee-3 ARE matched (same subject, angle, depth)")
    say("         bee-1 is a DIFFERENT angle and depth")
    say("         wrapped-text-1 / -2 are slightly different angles/depth")
    say()
    g_b3 = gaps.get("bee-3")
    g_b2 = gaps.get("bee-2")
    g_wt2 = gaps.get("wrapped-text-2")
    for lab, g in (("bee-2 -> bee-3 (claimed MATCHED)", g_b3),
                   ("bee-1 -> bee-2 (claimed DIFFERENT)", g_b2),
                   ("wrapped-text-1 -> -2 (claimed DIFFERENT)", g_wt2)):
        say(f"  {lab:<42}{g/60:>7.1f} min" if g is not None else
            f"  {lab:<42}    n/a")
    say()
    ok = (g_b3 is not None and g_b2 is not None and g_wt2 is not None
          and g_b3 < g_b2 and g_b3 < g_wt2)
    say(f"  matched gap is the SHORTEST of the three -> "
        f"{'YES, corroborates' if ok else 'NO, CONTRADICTS'}")
    say()
    say("  A short gap is consistent with an unmoved camera. It is NOT proof")
    say("  of identical framing, and this is corroboration of the owner's")
    say("  statement, not an independent measurement of it. The direction was")
    say("  pre-registered; no threshold was.")
    say()

    say("-" * 72)
    say("THE SESSION SPLIT INSIDE THE CPL-ON POPULATION")
    say("-" * 72)
    say("  25 May 2026   coffee-bubbles, foam            (ISO 1000)")
    say("  23 Aug 2026   wrapped-text-1/2, bee-1/2/3     (ISO 100, 400)")
    say("  ninety days apart. The brief describes both as '25 May onward',")
    say("  which is true and hides that these are two sessions, not one.")
    say()
    say("  Consequence for script 18 arm D: its ISO-100 group is entirely")
    say("  August and its ISO-50/160 groups are entirely May, so the dip at")
    say("  ISO 100 is confounded with SUBJECT, with SESSION, and with ninety")
    say("  days of anything else. Three confounds, not one.")
    say()
    say("  Consequence for 'no intentional rotation between shoots': that")
    say("  assumption now spans ninety days and an unknown number of lens")
    say("  mounts, rather than a single afternoon.")
    say("=" * 72)

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"\n[wrote {OUT}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
