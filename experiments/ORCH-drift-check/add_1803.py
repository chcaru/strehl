"""Insert fact 1803 into SYNTHESIS.md after row 1802.

Guarded: exits non-zero if the number already exists or the anchor is not
found exactly once.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

NUM = 1803
KIND = "ARGUED"
LANE = "ORCH"
BODY = (
    "**A LEVEL-0 CLAMP CANNOT PRODUCE A HULL VIOLATION AND CAN STILL MANUFACTURE DETAIL, WHICH "
    "RECONCILES A ZERO AND A 13-OF-19 THAT LOOKED CONTRADICTORY -- AND THE CANDIDATE FIX IS BUILT, "
    "TESTED AND UNREACHABLE.** `pyramid.rs` defines `Hull::Unclamped`, `Hull::InputRange` and "
    "`Hull::PerLevel`; the default is `InputRange` (`:1143`, asserted at `:3404`) and "
    "`the_reconstruction_never_leaves_the_hull_of_its_inputs` reads **`bad == 0`**. Yet V-GATHER "
    "measured the shipped master exceeding its own focus ceiling on **13 of 19 subjects** (fact 1799). "
    "**The two are not in conflict because they measure different things: a hull violation is an "
    "output VALUE outside the range of input values; ceiling excess is output LOCAL CONTRAST "
    "exceeding the sharpest contributing frame. Clamping values does not clamp gradients.** A band "
    "excursion born at a coarse level and guillotined at level 0 leaves a run of pixels pinned flat "
    "at `lo` and `hi` -- a squared-off edge carrying more local contrast than any input, sitting "
    "entirely inside the value hull. A cut-out sticker rim is what a level-0 clamp looks like from "
    "the outside, and the mechanism **requires no ringing**, which is why V-GATHER's kernel refutation "
    "came out as it did (`nearest` has no negative lobes and reads *more* overshoot). The file already "
    "names the gap: `PerLevel` is *\"a strict tightening of `InputRange`\"* whose claim is that *\"the "
    "excursion is caught at the coarse level where it is born, so that by the time the reconstruction "
    "reaches level 0 there is far less for the last clamp to do,\"* and it carries a negative control, "
    "a do-no-harm test (inert when every frame agrees) and `per_level_leaves_the_final_clamp_less_to_do`. "
    "**It has never been run on a real subject: `Hull` is absent from `main.rs` and `merge_cmd.rs` "
    "except one doc mention, so `strehl stack` cannot reach it**; only `examples/blend-render.rs` "
    "exposes it, as `--per-level`. **INSTRUMENT CONSEQUENCE, and the reason this is not merely a "
    "candidate fix: `hull_violations` is SATURATED AT ZERO under the shipping default and therefore "
    "blind to the defect it appears to police.** The live statistic is `pinned_to_hull` -- *\"a pixel "
    "pinned exactly at `lo` or `hi` is one the last clamp rescued\"* -- and the acceptance gate on the "
    "merge rebuild was amended from the violation count to the pinned count for exactly this reason. "
    "**A gate reading zero for every arm is not a gate that is being passed; it is a gate that is not "
    "being asked.** Falsifiable: `--unclamped` must raise ceiling excess (potency, run first), "
    "`--per-level` must lower it on the 13, and must be **inert** on subjects already within ceiling; "
    "a `PerLevel` that improves a subject with no excess is doing something other than what it claims. "
    "The paired A/B is valid inside `blend-render` despite its two declared gaps -- no photometric "
    "normalisation, no clip handling -- **because both arms are missing the same two stages and the "
    "gaps cancel in the difference, which is true only within that binary and never across to "
    "`strehl stack`.**"
)


def main() -> int:
    text = io.open(PATH, encoding="utf-8").read()

    if re.search(r"^\| %d \|" % NUM, text, re.M):
        print("REFUSED: fact %d already exists" % NUM)
        return 2

    anchor_hits = re.findall(r"^\| 1802 \|.*$", text, re.M)
    if len(anchor_hits) != 1:
        print("REFUSED: anchor row 1802 found %d times, expected 1" % len(anchor_hits))
        return 3
    anchor = anchor_hits[0]

    row = "| %d | %s | %s | %s |" % (NUM, KIND, LANE, BODY)
    out = text.replace(anchor, anchor + "\n" + row, 1)
    if out == text:
        print("REFUSED: replacement did not land")
        return 4

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(out)

    if not re.search(r"^\| %d \|" % NUM, io.open(PATH, encoding="utf-8").read(), re.M):
        print("FAILED: fact %d not present after write" % NUM)
        return 5
    print("OK: inserted fact %d" % NUM)
    return 0


if __name__ == "__main__":
    sys.exit(main())
