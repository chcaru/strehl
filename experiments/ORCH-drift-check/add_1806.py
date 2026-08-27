"""Insert fact 1806 into SYNTHESIS.md after row 1805.

Guarded: exits non-zero if the number already exists or the anchor is not
found exactly once.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

NUM = 1806
KIND = "MEASURED"
LANE = "BUILD-PLUGIN"
BODY = (
    "**THE ADMISSION GATE IS A GRAIN KNOB, NOT A MOTTLE KNOB, AND IT HAS NO AUTHORITY OVER THE DEPTH "
    "COLLAPSE -- TWO ELIMINATIONS THAT COST THE MECHANISM SPACE MORE THAN A TUNING WIN WOULD HAVE.** "
    "Two-column sweep over `--pyramid-gate k` on five subjects, knee defined as the largest blotch cut "
    "whose CI excludes 1.0 among arms whose sharpness CI does not exclude 0: best knee is "
    "`bee-1-cpl` **-3.57%** [-7.02, -1.34] against the **-58.8%** needed to undo the convicted 2.43x, "
    "i.e. **6.1% of the requirement** -- and that share is an over-estimate because 2.43x is itself a "
    "floor. `coffee-bubbles` (19) and `109MSDCF` (22) have **no knee at all**. Over the same arms grain "
    "moves **2.5-11.9x** while blotch moves **1.9-14.9%**: **mottle survives removing three quarters of "
    "the grain, so per-pixel admission is not what makes it.** On depth: the whole range `k=1->4` moves "
    "textured sharpness **1.20%** on the 299-frame stack, and Spearman(N, gate authority) = **-0.30**, "
    "non-monotone (169% at N=22, 70.9% at N=19, 1.20% at N=299) -- **the lane declined to separate N "
    "from regime across five confounded subjects rather than report a trend it could not defend.** "
    "**METHOD CORRECTION THE LANE ISSUED AGAINST ITS OWN INSTRUCTION, now binding on every lane: "
    "\"quote a sharpness number on the same pixels as the blotch number\" is UNSATISFIABLE as stated, "
    "because on sites chosen for having no detail the sharpness column correlates 0.985-0.997 with "
    "grain and IS a second noise column.** Amended to: sharpness must be read on **textured** sites and "
    "the correlation between the sharpness and grain columns must be quoted, so a grain move cannot be "
    "sold as a sharpness move. `bee-1-cpl` G400 is the demonstration -- `r(sharp/tex, grain) = 0.60` "
    "there against 0.976-0.999 elsewhere, the only subject where the axes decouple, delivering "
    "**-91.6% grain at -0.84% sharpness** (CI includes 0) on a column commissioned responsive on that "
    "subject (blur 0.0166x, sharpen 4.0002x); **reported, not recommended**, since G400 costs -59% to "
    "-87% on the other four. Commissioning 4/4 both ways, negative control **8/8 caught / 0 missed**, "
    "verifier 53 checks / 0 failed / 0 skipped; two earlier commissioning failures were traced to the "
    "lane's own **plant** (a difference-of-boxes stopband leaking +4.79% into the sharpness column) and "
    "**reported rather than papered over**. **OPEN AND UNRESOLVED, flagged because it may describe a "
    "live shipping regression:** the same report prices a \"§9 floor fix\" at the shipped `k` as costing "
    "**-9.9% to -39.9% sharpness on three subjects**, and it is not yet established whether that is "
    "`gatefloor.rs` (`78fed9a1`, ON by default, fact 1805) or a separate change. If it is the same fix, "
    "the sign is backwards from theory -- a less-strict gate should select more and soften less -- and "
    "the leading candidate reconciliation is that `k = 2.0` was implicitly tuned against the **wrong** "
    "floor, making a fix priced at the shipped `k` a measurement of the mismatch rather than of the fix."
)


def main() -> int:
    text = io.open(PATH, encoding="utf-8").read()

    if re.search(r"^\| %d \|" % NUM, text, re.M):
        print("REFUSED: fact %d already exists" % NUM)
        return 2

    anchor_hits = re.findall(r"^\| 1805 \|.*$", text, re.M)
    if len(anchor_hits) != 1:
        print("REFUSED: anchor row 1805 found %d times, expected 1" % len(anchor_hits))
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
