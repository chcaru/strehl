"""Insert facts 1811 and 1812 into SYNTHESIS.md after row 1810.

Guarded: exits non-zero if either number already exists or the anchor is not
found exactly once.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

ANCHOR = 1810

ROWS = [
    (
        1811,
        "MEASURED",
        "V-H2H2",
        "**THE MERGE CONCENTRATES ITS SELECTION MORE STRONGLY WHERE THERE IS NOTHING TO SELECT ON: "
        "FLAT-REGION CONCENTRATION EXCEEDS DETAIL-REGION CONCENTRATION AT EVERY BAND, AND THE "
        "RESULTING PLATEAUS LAND INSIDE THE CONVICTED 20-60 px MOTTLE SCALE.** `coffee-bubbles`, 19 "
        "frames, matched flat/detail arm because a mid-band statistic without one charges for subject "
        "structure. Scale anchored by two references measured in the same instrument: **a plain mean "
        "reads 0.0526 and winner-take-all reads 1.0.** Concentration, flat against detail: band 0 "
        "**1.0000 / 0.8214**; band 1 **0.9997 / 0.4909**; band 2 **0.7837 / 0.2989**; band 3 0.4025 / "
        "0.1467; band 4 0.2311 / 0.0965; band 5 0.1198 / 0.0857. **At bands 0-2 one frame in 19 owns "
        "essentially the entire coefficient in regions with no structure to choose on -- backwards for "
        "a merge that is supposed to select on signal, and it is the mottle mechanism stated "
        "arithmetically.** The spatial consequence is measured, not inferred: the merge runs "
        "3516x2344 into a 7032x4688 output so band *k* spans 2^(k+1) output px, giving **band 3 "
        "plateaus of 26.1 px against 17.1 px by chance and band 4 plateaus of 46.2 px against 33.9 "
        "px** -- both inside the convicted 20-60 px window -- with adjacent coefficients sharing a "
        "winner **57-61% of the time in flat regions against ~6% chance, i.e. 9-11x over chance and "
        "higher than the detail arm's 4-6x**. **THREE CORRECTIONS TO THE ORCHESTRATOR'S READING OF "
        "THE SAME FILE:** `DEFAULT_BANDS = 7` (`pyramid.rs:136`), not 6, so the whole exponent ladder "
        "was quoted shifted one index -- actual coarse-to-fine `2.000, 2.800, 3.920, 5.488, 7.683, "
        "8.000, 8.000`, the last two capped from 10.756 and 15.059; **the file's own doc comment "
        "states that ladder as `2 3 4 5 8 8 8`, wrong by up to 0.488 and repeated in two places**, "
        "which is precisely how a wrong premise gets inherited; and `SNR_REF = 64.0` **cancels in "
        "`w_i / sum w_j`** -- max share difference **1.431e-06** across `SNR_REF` in {1, 64, 1024} over "
        "1926 trials -- so it is an overflow guard, not a threshold, and not the mechanism. The "
        "diagnostic is proven inert: dump off, dump on, and the commissioning null all render to "
        "SHA-256 `08A559B3F21B12E0`. All source quotes read as bytes via `subprocess`, because "
        "`git show > file` re-encodes on Windows.",
    ),
    (
        1812,
        "MEASURED",
        "V-H2H2",
        "**WINNER COHERENCE IS PROVABLY BLIND TO THE EXPONENT AND MUST NOT BE USED AS AN ACCEPTANCE "
        "METRIC FOR ANY EXPONENT-SHAPED FIX -- IT WOULD HAVE REPORTED `NO CHANGE` HOWEVER LARGE THE "
        "CHANGE WAS.** The weight is `r_i^p` with the **same** `p` for every frame, so `argmax(r_i^p) "
        "= argmax(r_i)` for all `p > 0`: the winner identity is a strictly monotone transform of the "
        "energy and is exactly invariant to the exponent. **Measured worst-case disagreement 0.49%, "
        "all of it where the `[-80, 80]` clamp newly binds.** Confirmed empirically before it was "
        "explained: commissioning both directions on real renders -- `--pyramid-exponent 0.5` and "
        "`6.0` -- moved band-4 flat concentration **0.2311 -> 0.0827** and **0.2311 -> 0.4828**, while "
        "**the coherence table printed identical numbers on all three arms.** **This is the failure "
        "the improvement arm exists to catch (fact 1801's discipline generalised): a metric that "
        "cannot respond to a planted improvement will certify any fix as neutral.** Concentration "
        "moves in both directions and is therefore commissioned; coherence cannot and is therefore "
        "struck for this class of change, in every lane. **COROLLARY THAT CONSTRAINS THE FIX:** an "
        "exponent change cannot *move* a plateau boundary, only **dilute** it -- at `p -> 0` the merge "
        "is the plain mean and the patchwork is gone, but dilution is exactly what costs sharpness. "
        "**A GLOBAL EXPONENT IS THEREFORE THE WRONG SHAPE OF KNOB**, which is what motivates the "
        "per-coefficient significance design `z = excess / (floor/gate * sqrt(2/nu))`, `p_eff = p * "
        "f(z)`: one-pass and `absorb`-safe (the merge is a streaming fold, so cross-frame spread does "
        "not exist at weight-computation time and two-pass would require re-warping), and derived "
        "from the calibrated noise model rather than fitted, so it introduces no new constant and "
        "dilutes **only where the noise model says there is nothing to select on**.",
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
