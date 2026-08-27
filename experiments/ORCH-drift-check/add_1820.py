"""Insert facts 1820-1822 into SYNTHESIS.md after row 1819.

Guarded: exits non-zero if any number already exists or the anchor is not
found exactly once.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

ANCHOR = 1819

ROWS = [
    (
        1820,
        "MEASURED",
        "V-H2H2",
        "**DEEPENING A STACK MAKES FLAT FIELDS 17% NOISIER, BECAUSE IN FLAT REGIONS THE MERGE RUNS "
        "WINNER-TAKE-ALL ON NOISE -- AND THE ORCHESTRATOR'S DILUTION HYPOTHESIS IS REFUTED IN THE "
        "SAME ARMS.** `113MSDCF`, N=63 against N=32, **matched focus range by decimation** (`--limit` "
        "was rejected because it shortens the bracket and confounds frame count with depth of field), "
        "both arms staged as copies on one volume through one binary, `--linear-srgb` so neither arm "
        "**can** carry an exposure gain, robust to mask choice to three decimals. **THE REFUTATION "
        "FIRST:** the prediction was that the reconstruction drifts toward an average as N grows, "
        "which requires `n_eff/N` to RISE; measured, it is constant to within 2% at bands 1-6 and "
        "**FALLS 22% at band 0** (0.0490 -> 0.0381), so the merge becomes relatively **more** selective "
        "with depth. The raw `n_eff` ratio 1.97-2.01x against N's 1.969x **is the null**, not a "
        "finding. **THE MECHANISM FOUND INSTEAD:** flat-region band-0 `n_eff` is **1.008 at N=63** and "
        "1.004 at N=32 -- one frame chosen out of sixty-three, where there is no signal to choose on. "
        "The output is therefore the largest of N noisy candidates, and `E[max of N] ~ sigma*sqrt(2 ln "
        "N)` predicts **x1.0934** against a measured **x1.1697** grain ratio: same direction, same "
        "order, and 7% above a prediction it could have missed. Detail sites move oppositely (grain "
        "x0.9645, sharpness x0.9879), so this is not a global noise increase. **THIS EXPLAINS WHY THE "
        "PRINT GATE'S REFUSALS ARE THE DEEP SUBJECTS** -- `flower-bud-alone-cpl` at N=205 and the bee "
        "at N=299. **THE ACCEPTANCE CRITERION IS REPLACED ON THE LANE'S OWN ARGUMENT:** N-invariance "
        "of `n_eff/N` is already satisfied and therefore cannot drive a fix; the criterion is now "
        "*deepening a stack at matched focus range must not raise flat-field grain*, which today reads "
        "**x1.1697 and must read <= 1.0** -- a criterion the merge currently FAILS.",
    ),
    (
        1821,
        "DISCIPLINE",
        "V-H2H2",
        "**TWO GAUGE FAILURES CAUGHT BY THEIR AUTHOR, BOTH OF WHICH WOULD HAVE READ AS RESULTS.** "
        "(1) **f32 IS THE WRONG TYPE FOR A PARTICIPATION RATIO, AND IT FAILS HARDEST EXACTLY WHERE THE "
        "PHENOMENON LIVES.** Weights at the `exp(-80) = 1.8e-35` clamp floor square to `3.2e-70`, "
        "below `f32::MIN_POSITIVE`, and flush to zero -- so `sum(w^2) = 0` while `sum(w) > 0` and "
        "`n_eff` went NaN on **965,647 coefficients, precisely the MOST COMPLETELY AVERAGED ones**, "
        "which are the population the statistic exists to describe. It corrupted survivors too: band 3 "
        "read **6.221 in f32 against 6.502 in f64**. (2) **A SUMMARY LINE MUST NOT BE ABLE TO PRINT A "
        "VERDICT THE UNDERLYING GAUGE DECLINED TO GIVE.** `bandlib.display()` takes a linear gain and "
        "was passed `0.0`, multiplying the image by zero; every band read 0.000 and the summary "
        "printed **\"n63 SOFTER by 100.00%\"** -- the gauge itself had refused both sites, and only the "
        "summary claimed a result. Repaired by deriving the gain from the reference arm and making a "
        "zero-signal reference a hard error. **GENERALISES: the reporting layer is an instrument too, "
        "and it needs its own refusal path.** Also recorded: the lane rejected `concentration` for "
        "this question on the ground that its null value is `1/N`, so it falls with N for a merge that "
        "behaves identically, randomly, or as hypothesised -- **reporting that it fell would have "
        "confirmed the hypothesis by arithmetic.**",
    ),
    (
        1822,
        "OPEN",
        "V-H2H2",
        "**THE MERGE APPEARS TO DECIDE ON A 3516x2344 GRID WHILE WRITING A 7032x4688 OUTPUT, WHICH "
        "WOULD MEAN NO SELECTION DECISION EXISTS AT THE FINEST OUTPUT OCTAVE AT ALL.** Raised by the "
        "lane against the softness lane's operating band of 0.30-0.35 cyc/output px, which sits "
        "**above that grid's 0.25 Nyquist**. If confirmed, the pipeline is choosing what is sharp "
        "using a proxy that cannot see the frequencies its sharpness is judged at -- a candidate root "
        "cause for the softness observed by direct 1:1 inspection on textured subjects, and "
        "architectural rather than a tuning knob. **NOT ESTABLISHED AND EXPLICITLY NOT ACTED ON:** the "
        "grid may be FORCED rather than incidental, because a CFA plane is genuinely half-resolution "
        "per channel and a per-quad decision may be inherent to the CFA-native design the project "
        "chose deliberately. The open question is (a) forced or incidental, (b) if forced, what it "
        "costs in cyc/output px and whether the finest octave is therefore selected on interpolated "
        "evidence. Orchestrator direction on the record: **measure it, do not rewrite the merge for "
        "it** -- a change at that layer needs its own verification pass, and a known limitation ships "
        "better than an unverified rewrite.",
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
