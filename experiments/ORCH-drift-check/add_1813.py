"""Insert facts 1813 and 1814 into SYNTHESIS.md after row 1812.

Guarded: exits non-zero if either number already exists or the anchor is not
found exactly once.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

ANCHOR = 1812

ROWS = [
    (
        1813,
        "MEASURED",
        "V-LINEAR",
        "**IN THE CONVICTED BAND OUR MERGE'S HALVES DISAGREE 12.4x MORE THAN `enfuse`'s, AND ONLY WHERE "
        "SCENE STRUCTURE EXISTS -- A SECOND, INDEPENDENT SIGHTING OF THE SELECTION DEFECT.** Subject "
        "`119MSDCF`, split halves, `phi = P_d/P_m` with both terms band-limited to the same annulus, "
        "per-band commissioning passed in both bands, pre-registration `2ada7413` landed **before** the "
        "instrument existed. **THE BAND CHANGES WHAT THE LANE'S EARLIER VERDICT MEANT, SO IT GOES "
        "FIRST:** the convicted plateau is 20-60 px = **0.017-0.050 cyc/px**, while this lane's prior "
        "LEVEL verdict sat at **0.20-0.25 cyc/px** -- an order of magnitude apart, so **the lane had "
        "never measured the convicted band.** Measured now: COARSE/DETAIL strehl 0.00357 vs `enfuse` "
        "0.00029, **R = 12.424 [6.067, 19.468]**; COARSE/FLAT 1.062; FINE/DETAIL 1.355 [1.010, 2.252]; "
        "FINE/FLAT 1.051. **THE CONTROL THAT MAKES IT A FINDING (C4): FLAT tiles agree to 6% while "
        "DETAIL reads 12.4x, so the excess appears only where structure exists -- which kills \"strehl "
        "is simply noisier\".** C1 pre-empts the obvious rebuttal: `enfuse`'s halves genuinely differ, "
        "and differ **more in absolute terms** (0.01141 vs 0.00451, zero bit-identical tiles) while "
        "carrying 12x **less** coarse disagreement, so this is not a build artifact. C2 rebuts "
        "perversity off the lane's own `PERVERSE` arm -- slope 1.05 predicts 0.905 from the -9.1% "
        "amplitude gap against an observed 0.0805, so **perversity accounts for 10.3%**. C3: n=110, "
        "2000 bootstraps, both CIs exclude 1.0, **no tiles dropped in either arm**. Two earlier "
        "sections are reconciled by an independently built statistic: FINE coherent-only amplitude "
        "**1.651** against published `C` 2.017 and total 1.003, and the gap between 1.651 and 1.003 "
        "**is** the incoherent detail, now measured rather than hypothesised. **NOT ESTABLISHED, AND "
        "ENFORCED AS A QUOTATION BAN: that the 12.4x is the missing 43% of blotch.** What was measured "
        "is selection **instability**, not blotch; the link is ARGUED. **Neither 57% nor 12.4% nor "
        "12.4x may be quoted as a share of the blotch.** One subject, one comparator; `bee` at N=299 -- "
        "where the effect should be strongest -- has not been run. **ALSO UNDETERMINED AND PRINTED AS "
        "SUCH: alignment-versus-selection attribution.** The lane's signature separator failed twice "
        "and said so rather than reporting a number: v1 gave `SHIFT` +0.490 and `BLOTCH` +0.426 around "
        "a baseline of **+0.457**, so the calibration arms straddled what they bracket; v2's "
        "concentration ratio spans only 0.86x and reverses the prediction, because blur-blend perturbs "
        "edges too.",
    ),
    (
        1814,
        "MEASURED",
        "V-LINEAR",
        "**A STATISTIC COMMISSIONED IN ONE BAND IS NOT COMMISSIONED IN ANOTHER: A FIXED PLANT AMPLITUDE "
        "IS WRONG BY CONSTRUCTION ACROSS BANDS.** The COARSE annulus captures **10x less white noise** "
        "than FINE -- area fractions **0.00698 against 0.0707** -- so a plant sized for one band "
        "arrives at a tenth of its intended strength in the other. Measured consequence: the "
        "`NOISE-INC` commissioning arm **failed at +4.7%**, not because the statistic was blind but "
        "because the plant was too weak to be seen there. Repaired by deriving the plant amplitude per "
        "band: **beta = 0.1389 against 0.0124, 11x apart.** This is the mirror image of the same "
        "lane's earlier too-potent plant, and together they bracket the general rule: **a commissioning "
        "plant must be sized in the units of the band it is planted in, and a commissioning result "
        "does not transfer across bands any more than a fitted constant transfers across scenes.** "
        "Generalises past this lane -- every per-band instrument in the project (the noise floor's "
        "`beta[k]`, the exponent ladder, the concentration table, the per-band floor multiplier) is "
        "exposed to exactly this error.",
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
