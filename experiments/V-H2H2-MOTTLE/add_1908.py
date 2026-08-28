import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ANCHOR = "| 1907 |"

ROWS = [
    "| 1908 | MEASURED | V-H2H2 | **THE DERIVED SIGNIFICANCE FLOOR IS TOO SMALL TO MATTER, AND BAND 0 IS OUT OF "
    "REACH OF ANY WEIGHTING CHANGE AT ALL.** `p_eff` (fact 1812) is built and lands at `da23605a`: `select_weight` "
    "replaces `r` with `hypot(r, r_floor)`, exactly `p_eff = p*f(z)`, `f(z) = ln(1+z^2)/(2 ln z)`, with `NU_SMOOTH = "
    "13.37469` DERIVED from `KERNEL` (a test recomputes it and caught a digit transposition, 13.37619, in my own "
    "arithmetic). MEASURED on `coffee-bean` 20 frames, `--merge pyramid`, ONE binary `6A9FABB7`, three arms differing "
    "only in `STREHL_PYRAMID_SIGNIFICANCE`. Concentration `max_i(w_i)/sum_i(w_i)`, flat/detail by local SD -- FLAT "
    "off/x1/x1000 then DETAIL off/x1/x1000: band 0 `1.0000 1.0000 1.0000` / `0.9999 0.9990 0.5000`; band 1 `0.8997 "
    "0.8444 0.1667` / `0.8340 0.8106 0.0958`; band 2 `0.6440 0.6325 0.0909` / `0.6917 0.6876 0.2802`; band 3 `0.3074 "
    "0.3071 0.0556` / `0.3955 0.3953 0.3244`; band 6 `0.0583 0.0583 0.0582` / `0.0567 0.0567 0.0565`. **At the derived "
    "strength the flat/detail inversion does NOT collapse** -- it narrows at band 1 (gap 0.0657 -> 0.0338) and moves "
    "bands 2-6 by under 0.2%. At 1000x it collapses and REVERSES to the correct polarity at bands 2-4, so the "
    "mechanism is real and the derived scale is simply far too small to reach it; reaching it needs a fitted "
    "multiplier, the exact constant the design existed to avoid. **BAND 0 IS ARITHMETICALLY UNREACHABLE:** `conc = "
    "1.0000` EXACTLY means every other frame's weight is exactly zero, and `select_weight` returns 0 on `excess <= 0` "
    "BEFORE it looks at the floor -- one frame cleared the gate and the rest did not. That is a decision of the GATE, "
    "upstream of the weight, which is why the refused fractions (0.6176 flat, 0.4958 detail) are identical in all "
    "three arms. **THEREFORE `p_eff` DOES NOT SUBSUME `STREHL_GATE_FLOOR_SCALE`** (ORCH's explicit question): they act "
    "on different mechanisms and at the band where the inversion is worst only the gate-side knob can act. Defaulted "
    "OFF -- it moves every byte of a shipping render (three arms, three distinct hashes) while failing its criterion. "
    "NULL ARM PROVEN ON A REAL RENDER across two binaries: explicit `=0` under `6A9FABB7` and the unset default under "
    "`B1524C8C` both give `89CB2998...`, distinct from arm 1 `17C43D1F`. The variable is a MULTIPLIER, not a flag, and "
    "that is what made the potency arm possible -- arms 0 and 1 alone cannot distinguish \"too small to matter\" from "
    "\"never executed\", because both render identical bytes. |\n",

    "| 1909 | MEASURED | V-H2H2 | **THE BYTE-FREEZE SUITE HAS ZERO COVERAGE OF THE BACKEND THAT SHIPS.** "
    "`crates/strehl-cli/tests/byte-freeze.rs:574-575` hardcodes `\"--merge\", \"estimator\"` into every row's argv, "
    "while `crates/strehl-cli/src/merge_cmd.rs:429` sets `DEFAULT_MERGE_BACKEND = MergeBackend::Pyramid`. So the "
    "project's strongest anti-regression instrument exercises only the non-default merge, and the comment at "
    "`byte-freeze.rs:564` still asserts \"The estimator is still the default\" -- stale, and the same class of error as "
    "the rounded-constant docstring ORCH ruled must be fixed on sight. The file predicts its own gap at :572: \"The day "
    "a pyramid row is added this must become a registry column.\" HOW IT WAS FOUND, and the lesson: a three-arm A/B of "
    "`STREHL_PYRAMID_SIGNIFICANCE` (0 / 1 / **1000**) over both frozen rows returned BYTE-IDENTICAL output on all three "
    "arms. A 1000x floor is `r_floor = 3.02` and would be catastrophic if it ran at all, so the potency arm converted a "
    "plausible-looking \"the fix is inert\" into the true reading, \"the harness cannot see this code\". Arms 0 and 1 "
    "alone would have reported inertness and been believed. |\n",

    "| 1910 | MEASURED | V-H2H2 | **`coffee-bean-20-gate2-sidecar` HAS MOVED AND IT IS NOT V-H2H2'S; DO NOT "
    "RE-BASELINE IT.** The row expects `52517FF8...`; binary `6A9FABB7` renders `E600A506...` at 49450019 bytes "
    "(unchanged geometry, pixel VALUES moved). It is not the significance fix: arm `STREHL_PYRAMID_SIGNIFICANCE=0` "
    "restores the shipping weight bit for bit (unit-tested on `to_bits()`, and confirmed on a real render) and STILL "
    "renders `E600A506`. It cannot be the significance fix for a second, independent reason -- fact 1909: every freeze "
    "row runs `--merge estimator` and the variable exists only on the pyramid backend. The suspect surface is the "
    "estimator path; ~36 lines of BUILD-SOFTGATE's `preflight_soft_kernel()` were sitting uncommitted in "
    "`merge_cmd.rs` throughout (fact 1907). Attribution belongs to whoever owns that path, by re-rendering the row's "
    "OWN recorded invocation, per the standard the registry itself sets. Recorded because the harness's failure banner "
    "invites the next lane who runs the suite to re-baseline it, and that lane would be signing for a change that is "
    "not theirs. |\n",
]


def main():
    with io.open(PATH, encoding="utf-8") as fh:
        lines = fh.readlines()

    idx = [i for i, l in enumerate(lines) if l.startswith(ANCHOR)]
    if len(idx) != 1:
        sys.exit("anchor %r matched %d lines, expected exactly 1" % (ANCHOR, len(idx)))
    at = idx[0] + 1

    for n in (1908, 1909, 1910):
        if any(l.startswith("| %d |" % n) for l in lines):
            sys.exit("fact %d already present" % n)

    lines[at:at] = ROWS
    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.writelines(lines)

    with io.open(PATH, encoding="utf-8") as fh:
        after = fh.readlines()
    for n in (1908, 1909, 1910):
        hits = [l for l in after if l.startswith("| %d |" % n)]
        if len(hits) != 1:
            sys.exit("fact %d landed %d times" % (n, len(hits)))
        if hits[0].count("|") < 5:
            sys.exit("fact %d has too few cells" % n)
    print("inserted 1908-1910 after line %d; file now %d lines" % (idx[0] + 1, len(after)))


main()
