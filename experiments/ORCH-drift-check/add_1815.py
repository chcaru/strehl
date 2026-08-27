"""Insert facts 1815-1817 into SYNTHESIS.md after row 1814.

Guarded: exits non-zero if any number already exists or the anchor is not
found exactly once.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

ANCHOR = 1814

ROWS = [
    (
        1815,
        "MEASURED",
        "ORCH",
        "**THE SHIPPING RECIPE BLEW 11 OF 18 MASTERS TO A WHITE MEDIAN AT HEAD, AND THE ACCEPTANCE PIN "
        "PROVES IT IS A REGRESSION RATHER THAN A STANDING CONDITION.** Instrument "
        "`experiments/ORCH-drift-check/clipcheck.py` (clip% = share of pixels whose max channel is "
        "65535). Three arms on `109MSDCF`, 22 frames, HEAD binary sha `82EA1F96DA4550F6`: `--srgb "
        "--auto-exposure` **92.03% clipped, median 65535**; `--srgb` alone **0.00% clipped, median "
        "61063**; `--srgb --exposure=0` identical to the latter. Corpus sweep of 18 HEAD masters "
        "rendered with the SHIP-V4 recipe: **11 BLOWN (>25%)** -- `couch-fibers-cpl` 92.13, "
        "`109MSDCF` 92.03, `119MSDCF` 84.67, `flower-bud-alone-cpl` 78.58, `flowers-cpl` 75.15, "
        "`flower-bud-with-background-fern-cpl` 68.90, `bee-1/2/3-cpl` 59.70/56.39/58.59, "
        "`flat-on-ruler-cpl` 56.99, `112MSDCF` 35.57 -- against 4 clean (`coffee-bean`, "
        "`coffee-bubbles`, `dry-erase-marker-head-cpl`, `foam`). **THE CONTROL THAT MAKES IT A "
        "REGRESSION AND NOT A DISCOVERY: the delivered `acceptance/SHIP-V4/` masters, rendered by pin "
        "`9b05d0b7` with the SAME recipe, clip 0.00-0.09% with sane medians.** So every verdict taken "
        "on the delivered set stands; only HEAD renders taken with `--auto-exposure` are affected. "
        "**NOT ESTABLISHED: that clipping causes the rim, `pinned_to_hull` or manufactured-detail "
        "readings.** It is a live alternative explanation for all three and their attribution is "
        "hereby unproven, not withdrawn.",
    ),
    (
        1816,
        "MEASURED",
        "ORCH",
        "**THE GAIN WAS NEVER THE BUG -- THE BASELINE IT MULTIPLIES WAS -- AND THE FIX WAS ALREADY "
        "WRITTEN IN THE FILE THE SHIPPING COMMAND DOES NOT USE.** Pin `9b05d0b7` (sha "
        "`44C2F2CD2E5B2894`) given the identical recipe chooses **+2.60 stops / 6.063x** and clips "
        "**0.00%** (median 60918); HEAD chooses **+2.61 stops / 6.105x** and clips **92.03%**. The "
        "chosen gains agree to 0.7%, so the difference is not the chooser. **Pin+auto (median 60918) "
        "and HEAD-without-auto (median 61063) land in the same place**, which identifies the "
        "mechanism: a tone stage added since the pin now performs the normalisation `--auto-exposure` "
        "used to perform, so HEAD applies the same rule twice. `stack.rs:1644-1683` states the "
        "identity outright -- `AUTO_EXPOSURE_PERCENTILE` 99.9 = `TONE_WHITE_PCT` 99.9, "
        "`AUTO_EXPOSURE_TARGET` 0.90 = `TONE_WHITE_TARGET` 0.90 -- **predicts this failure at this "
        "exact magnitude (\"blow every highlight by its own chosen gain -- 6.105x on the corpus\") and "
        "guards against it.** But `strehl stack` dispatches to `merge_cmd::run` (`main.rs:1084`), not "
        "`stack::run` (`main.rs:856`), and the guard was never ported. **THE GENERAL LESSON, WHICH IS "
        "THE REASON THIS IS A ROW AND NOT A COMMIT MESSAGE: a correct fix in a sibling module is not a "
        "fix. Two entry points implementing one pipeline will diverge, and the one carrying the "
        "written-down argument is not necessarily the one the user runs.** Repaired by porting the "
        "supersede into `merge_cmd.rs`, gated on `srgb` so that linear renders -- which have no tone "
        "placement -- keep `--auto-exposure` load-bearing.",
    ),
    (
        1817,
        "DISCIPLINE",
        "ORCH",
        "**EVERY PRINT-GATE AXIS IS STRUCTURAL, AND A SATURATED REGION HAS NO STRUCTURE, SO A MASTER "
        "CAN READ CLEAN ON ALL FOUR WHILE BEING A WHITE SHEET.** Rim, sharpness, dust and cert all "
        "score relationships between neighbouring pixel values; when 92% of pixels are pinned at the "
        "same value those relationships are gone, and their absence scores as their being in order. "
        "This is why an 11-of-18 blowout survived a gate that was passing 17 subjects. **THE RULE: any "
        "gate built on differences between pixels must carry a companion check on the pixels "
        "themselves -- level, clip fraction, black fraction, median -- because a degenerate image is "
        "the quietest possible input to a difference operator.** Corollary for attribution, and it "
        "cuts against three of this project's own findings: clipping manufactures infinitely sharp "
        "edges (candidate cause of \"master exceeds its own focus ceiling\" on 13/19 subjects), pins "
        "pixels at `hi` (which is definitionally what `pinned_to_hull` counts), and places a blown "
        "highlight beside a dark edge (which reads as large overshoot, i.e. rim). Those three "
        "measurements were taken on the delivered pin masters, which are **not** blown, so they are "
        "not withdrawn -- but any future re-measurement at HEAD must state its clip fraction beside "
        "its verdict or the verdict is uninterpretable.",
    ),
]


def main() -> int:
    text = io.open(PATH, encoding="utf-8").read()

    for num, _, _, _ in ROWS:
        if re.search(r"^\| %d \|" % num, text, re.M):
            print("REFUSED: fact %d already exists" % num)
            return 2

    anchor_hits = re.findall(r"^\| %d \|.*$" % ANCHOR, text, re.M)
    if len(anchor_hits) != 1:
        print("REFUSED: anchor row %d found %d times, expected 1" % (ANCHOR, len(anchor_hits)))
        return 3
    anchor = anchor_hits[0]

    block = anchor
    for num, kind, lane, body in ROWS:
        block += "\n| %d | %s | %s | %s |" % (num, kind, lane, body)

    out = text.replace(anchor, block, 1)
    if out == text:
        print("REFUSED: replacement did not land")
        return 4

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(out)

    after = io.open(PATH, encoding="utf-8").read()
    for num, _, _, _ in ROWS:
        if not re.search(r"^\| %d \|" % num, after, re.M):
            print("FAILED: fact %d not present after write" % num)
            return 5
    print("OK: inserted facts %s" % ", ".join(str(n) for n, _, _, _ in ROWS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
