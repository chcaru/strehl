"""Insert fact 1807 into SYNTHESIS.md after row 1806.

Guarded: exits non-zero if the number already exists or the anchor is not
found exactly once.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

NUM = 1807
KIND = "MEASURED"
LANE = "ORCH"
BODY = (
    "**THE SHIPPING DEFAULT AVERAGES 7.7x MORE OF THE FINEST BAND THAN THE PRE-FIX BUILD DID, THE "
    "COMPENSATION IS ONE STALE CONSTANT, AND THE GATE HAS NEVER FIRED ABOVE LEVEL 0 UNDER ANY FLOOR "
    "OR ANY CONSTANT.** HEAD build `AAAF8666B5F08DA5` (clean `cargo build --release`, 26.69 s; "
    "distinct from the pin's `44C2F2CD2E5B2894`), subject `leaf-2-cpl` (182 frames, worst rim in the "
    "corpus at +37.07%), SHIP-V4's exact recipe `--srgb --auto-exposure` recovered from `RUN.txt`. "
    "The gate's own `averaged` diagnostic at level 0 -- coefficients where no frame cleared the floor, "
    "so the merge averaged instead of selecting: **shipping default (measured floor, k=2.0) 54.4%; "
    "pre-fix control (`STREHL_GATE_FLOOR=white`, k=2.0) 7.1%; measured floor at k=1.29 6.9%; measured "
    "floor at k=0.9 0.0%.** **FIRST CORRECTION -- THE SIGN WAS BACKWARDS AND THE ORCHESTRATOR HAD "
    "RELAYED IT TO TWO LANES:** the banner reads `measured floor 1.3795 0.0566 0.0112 0.0027 / x white "
    "1.5504 1.0693 1.1132 1.1386`, **every entry ABOVE 1.0**, so on real frames the white constant "
    "UNDER-states the noise and the landed fix makes the gate **stricter**. BUILD-GATE's "
    "`beta_actual/beta_white` of **0.3432 ... 0.9981, all below 1.0**, is not wrong -- it measures "
    "**warping alone**. Two effects compose and oppose: warping correlates neighbours and lowers "
    "band-0 power; **demosaic correlates them far more and raises coarse-band power**, exactly as "
    "`merge_cmd.rs:402-407` states, and the demosaic term dominates. **A ratio measured on a synthetic "
    "warp does not survive contact with a demosaiced frame.** This vindicates BUILD-PLUGIN's measured "
    "-9.9% to -39.9% sharpness cost against the orchestrator's theory (fact 1806's open item, now "
    "closed): a stricter gate averages more and softens more. **THE COMPENSATION IS ONE CONSTANT:** "
    "predicting `2.0 / 1.5504 = 1.29` restores the pre-fix rate gives **6.9% against 7.1%**, within "
    "0.2 pp; confirmed on decoded pixels (`headcheck_cmp.py`, identity control exactly 0) where "
    "`white-k2.0` vs `measured-k1.29` is **25.47 DN** mean absolute against **339.62 DN** for the "
    "shipping default -- **13x closer**. The floor also costs **~1.9x runtime** (65.1 s vs 34.3 s), "
    "since it probes every frame. **NOT ESTABLISHED, AND THE EASY OVER-READ:** `averaged` is a "
    "diagnostic, not a quality metric -- `k=0.9` drives it to **0.0%**, which is naive argmax and "
    "certainly worse -- so **k=1.29 is a landmark, not a recommendation**. Restoring the pre-fix rate "
    "is not obviously right either, because the old `k=2.0` was demanding 2.0 against an under-stated "
    "floor, i.e. an effective **1.29x the true noise**: **`k` has never been chosen against a correct "
    "floor.** **SECOND FINDING, STRUCTURAL: levels 1 through 6 read `0.0%` averaged in EVERY arm, "
    "including `k=0.9`** -- by the banner's own criterion (*\"Near 0% everywhere would mean the gate is "
    "not gating and this is a naive pyramid stacker\"*), **strehl is a naive pyramid stacker at every "
    "scale except the finest.** This mechanistically explains fact 1806: no `k` cuts mottle because "
    "`k` scales a floor that is never reached above level 0, so sweeping `k` cannot fix a gate that "
    "does not fire where the mottle is."
)


def main() -> int:
    text = io.open(PATH, encoding="utf-8").read()

    if re.search(r"^\| %d \|" % NUM, text, re.M):
        print("REFUSED: fact %d already exists" % NUM)
        return 2

    anchor_hits = re.findall(r"^\| 1806 \|.*$", text, re.M)
    if len(anchor_hits) != 1:
        print("REFUSED: anchor row 1806 found %d times, expected 1" % len(anchor_hits))
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
