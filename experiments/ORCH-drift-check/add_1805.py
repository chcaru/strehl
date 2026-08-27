"""Insert fact 1805 into SYNTHESIS.md after row 1804.

Guarded: exits non-zero if the number already exists or the anchor is not
found exactly once.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

NUM = 1805
KIND = "MEASURED"
LANE = "ORCH"
BODY = (
    "**EVERY QUALITY VERDICT IN THIS CAMPAIGN WAS PRONOUNCED ON A BINARY 12,637 LINES OUT OF DATE, "
    "AND TWO OF THE MISSING COMMITS TARGET THE EXACT AXES BEING FAILED.** `git log 9b05d0b7..HEAD -- "
    "crates/` returns **13 commits, 26 files, +12,637 / -538**, separating the pin the 26 SHIP-V4 "
    "masters were rendered from and the tree. Verified, not inferred: "
    "`crates/strehl-cli/src/merge_cmd/gatefloor.rs` **does not exist at the pin** (`git cat-file -e` "
    "fails; its adding commit `78fed9a1` is not an ancestor of `9b05d0b7`), and it is **ON by "
    "default** (`gatefloor::enabled()` returns `true` unless `STREHL_GATE_FLOOR=white`). What it "
    "corrects: `BandGain` derives the gate's floor by pushing **white** noise through the pyramid, "
    "which is the noise transfer of an **unwarped** frame; a resampled frame's noise is correlated by "
    "the interpolation kernel, its band-0 power falls, and the white floor **over-states** the true "
    "one -- *\"so the gate averages pixels it should have let select.\"* BUILD-GATE measured "
    "`beta_actual / beta_white` in **0.3432 ... 0.9981** over eight representative warps, **every "
    "entry below 1.0**, so `gate = 2.0` was demanding **up to 3.7x the true noise power**. It is not "
    "a constant and no scalar can fix it: the two gather arms are different *periodic functions* of "
    "sub-pixel warp phase, with periods of one plane-pixel and one full-res pixel, **and their curves "
    "cross**. The pin also lacks `5db5ac09` (*\"the chroma excess is RESTORED -- and the double "
    "demosaic is not innocent, it is invisible\"*), which bears directly on the chroma term the blotch "
    "axis reads. **CONSEQUENCE: fact 1804's `rim 13 FAIL / blotch 8 FAIL / 1 of 26 clean` is a verdict "
    "at pin `9b05d0b7` and NOT a statement about what the tool now produces; a softening fix and a "
    "chroma fix both landed, defaulted on, after every master under judgement was rendered.** "
    "**PROCESS CAUSE, and it was written down in this repository before it happened:** `merge_cmd.rs` "
    "already warns, of its own backend table, *\"Comparing a new treatment against an old control is "
    "how a corpus drifts without anyone deciding to move it\"* -- and the orchestrator ran the gate, "
    "read the warning's own file twice the same night, and relayed the verdict to five lanes without "
    "asking how old the masters were. **The pin was created to make comparisons stable and instead "
    "made them stale: a frozen control is only a control while the treatment is also frozen, and "
    "eleven lanes were committing to `crates/` the whole time.** DISCIPLINE 34 -- **a verdict inherits "
    "the date of the artefact it was measured on, so every quality claim must carry the commit it was "
    "rendered at, and a control must be re-cut whenever the tree it stands against has moved.** Note "
    "the instrument findings are untouched by this: a sign inversion, a NaN reading as PASS and a "
    "kernel refutation are properties of the gauge and hold against any masters."
)


def main() -> int:
    text = io.open(PATH, encoding="utf-8").read()

    if re.search(r"^\| %d \|" % NUM, text, re.M):
        print("REFUSED: fact %d already exists" % NUM)
        return 2

    anchor_hits = re.findall(r"^\| 1804 \|.*$", text, re.M)
    if len(anchor_hits) != 1:
        print("REFUSED: anchor row 1804 found %d times, expected 1" % len(anchor_hits))
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
