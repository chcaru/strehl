"""Insert facts 1808 and 1809 into SYNTHESIS.md after row 1807.

1808 falsifies the orchestrator's own reading in 1807; 1809 records the
per-band knob that the falsification made buildable.

Guarded: exits non-zero if either number already exists or the anchor is not
found exactly once.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

ANCHOR = 1807

ROWS = [
    (
        1808,
        "MEASURED",
        "ORCH",
        "**THE GATE IS NOT DEAD ABOVE LEVEL 0; IT IS OUT-SIGNALLED THERE, AND RAISING THE CONSTANT "
        "REACHES IT -- FACT 1807'S SECOND FINDING IS WITHDRAWN BY ITS OWN AUTHOR.** Same HEAD binary "
        "`AAAF8666B5F08DA5`, same subject `leaf-2-cpl` (182 frames), same recipe `--srgb "
        "--auto-exposure`, one extra knob turned. Fact 1807 concluded from `0.0%` at levels 1-6 that "
        "*\"strehl is a naive pyramid stacker at every scale except the finest\"* and that **\"no `k` "
        "cuts mottle because `k` scales a floor that is never reached\"**. The falsifying arm is one "
        "command: **`--pyramid-gate 8` gives `averaged` = 97.2% 8.1% 4.7% 3.1% 1.3% 0.0% 0.0%, and "
        "`--pyramid-gate 64` gives 100.0% 68.1% 8.8% 4.7% 3.5% 1.9% 0.0%.** Levels 1-5 move off zero "
        "in both. **The coarse bands can gate; at the shipping `k=2.0` they read 0.0% because coarse "
        "Laplacian coefficients clear the floor by a wide margin, which is arithmetically expected "
        "rather than a defect** -- the floor falls ~500x from band 0 to band 3 (1.3795 -> 0.0027) "
        "while signal falls far less. The banner's warning describes near-0% at **every** level "
        "including 0; band 0 reads 54.4%, so the gate is firing where noise actually dominates. "
        "**WHAT SURVIVES OF 1807:** every measured number, the sign correction, and the k=1.29 "
        "landmark. **WHAT DIES:** the `naive pyramid stacker` characterisation and the claim that no "
        "`k` can reach the mottle. **WHY THIS MATTERS MORE THAN THE CORRECTION:** the arms also show "
        "the scalar knob is unusable in the direction wanted -- at `k=8`, band 1 reaches only 8.1% "
        "while band 0 is driven to 97.2% and the fine detail is gone. **One number cannot ask for "
        "less selection at coarse scales and unchanged selection at fine ones, which is exactly what "
        "the blotch-versus-sharpness conflict of facts 1804 and 1806 requires.** The orchestrator's "
        "error was to read one arm at one constant as a structural property; the cost of falsifying "
        "it was two renders.",
    ),
    (
        1809,
        "MEASURED",
        "ORCH",
        "**A PER-BAND NOISE FLOOR DECOUPLES COARSE AVERAGING FROM FINE DETAIL, WHICH `--pyramid-gate` "
        "CANNOT DO BY CONSTRUCTION, AND IT IS COMMISSIONED WITH A BYTE-EXACT NULL.** `--pyramid-gate` "
        "*\"takes a single value by construction\"* (`main.rs:236`), so fact 1808's conflict has no "
        "expressible answer in the shipping flags. Scaling `k` per band and scaling the floor per band "
        "are the same operation, so the knob was added at the cheaper seam: `STREHL_GATE_FLOOR_SCALE`, "
        "a comma-separated per-band multiplier in `gatefloor.rs`, **touching no file any other lane "
        "owns and requiring no change to the merge**. Above the certified range (`CERTIFIED_BANDS = "
        "4`) it extends the floor with the white value **before** scaling, because the merge would "
        "otherwise fall back to white and the multiplier would silently do nothing at exactly the "
        "coarse bands it is aimed at; it is applied in `measure` **after** the debug block, so neither "
        "the per-frame report nor the identity-warp commissioning null ever sees a scaled floor and "
        "reports the knob as probe error. **NULL CONTROL, THE ONE THAT COULD HAVE FAILED:** "
        "`STREHL_GATE_FLOOR_SCALE=1,1,1,1,1,1,1` renders **SHA-256 `171981BC7DC8CD7D...` against the "
        "unset build's `171981BC7DC8CD7D...` -- byte identical**, proving the extension-to-white "
        "reproduces the merge's own fallback exactly rather than approximately. **POTENCY:** "
        "`1,8,8,8,8,8,8` gives `averaged` = **54.4% 19.4% 5.2% 4.0% 2.4% 0.5% 0.0%** against the "
        "default's 54.4% 0.0% x5, a different output hash `FC93F656CD0FA2B1...`, and **band 0 "
        "unchanged to the printed digit** -- the decoupling the scalar knob could not express, where "
        "`--pyramid-gate 8` moved band 0 from 54.4% to 97.2% to buy band 1 only 8.1%. **NOT "
        "ESTABLISHED, AND THIS IS THE WHOLE QUESTION:** `averaged` is a duty cycle, not a quality "
        "metric (fact 1807), so **no claim is made here that coarse averaging cuts blotch or rim**. "
        "The knob makes the experiment possible; it does not report its result. The mechanism worth "
        "falsifying is that mottle and rim are coarse-scale **selection** artifacts -- the argmax "
        "flipping between frames across regions with no coarse structure above noise -- in which case "
        "averaging exactly there is nearly free in sharpness, since low frequencies survive defocus "
        "and differ least between frames. The instrument that can kill it is the rim axis, not the "
        "banner.",
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
