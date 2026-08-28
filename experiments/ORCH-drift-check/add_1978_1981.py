"""Append facts 1978-1981 to the SYNTHESIS fact table (lane V-DCNULL)."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1977

ROWS = [
    (1978, "V-DCNULL", "MEASURED", (
        "THE PUBLISHED MERGE-VS-BEST-FRAME SOFTNESS NUMBERS ARE CLEAN OF THE DC MECHANISM, and "
        "the orchestrator had named the wrong producer. The seven ratios were NOT produced by "
        "`bandqual.py`/`gnorm` as the tasking assumed; `V-SOFTCHECK-bandqual.md:406` sources "
        "them to `V-SOFTCHECK-nyquist.md`, whose table carries a max63/max32 column that exactly "
        "one file in the tree prints -- `experiments/V-SOFTCHECK/ncommon.py`, computing "
        "median over tiles of ring power of the master divided by the per-band max over frames. "
        "`bandqual.py`'s role is the qualifier, not the producer. On that true producer a "
        "planted DC offset moves the reading by at most 2.320e-07 across six plant arms "
        "(+250 DN, +1000 DN and -250 DN on the master, +250 on all frames, on both sides, and "
        "on even frames only), against a true answer of 1.0000. Quadrupling the offset raises "
        "the residual by 33 percent rather than 4x, which identifies a float32 rounding floor "
        "rather than a mechanism. The cause is structural: `rings()` mean-subtracts each tile "
        "and its annuli start at 0.05 cyc/px, so there is no median rescale and no level "
        "division anywhere between TIFF and ratio. THE ZERO IS A NULL AND NOT A DEAD PROBE, "
        "proven by a purpose-built positive control: the same DC plant pushed through a "
        "deliberately mean-normalised scorer moved the same band from 0.5824 to 0.4086 at "
        "+250 DN and to 0.1852 at +1000 DN."
    )),
    (1979, "V-DCNULL", "MEASURED", (
        "THE REAL EXPOSURE THREAT TO THE SOFTNESS NUMBERS IS GAIN, NOT DC, AND IT IS UNGUARDED. "
        "`ncommon.py`'s statistic is exactly covariant with the square of the level ratio: "
        "measured `r_obs = r_true x (g_master/g_frame)^2` to a relative error of 7.72e-08 at "
        "gain 1.15 and 1.50e-07 at gain 1.0327, with a both-sides control returning 1.0000 "
        "(max deviation 5.453e-06) which confirms the sensitivity is RELATIVE rather than "
        "absolute. A grep of the file for exposure, .log or check_exposure returns EMPTY, so "
        "unlike its siblings `dmeasure.py` and `d113measure.py`, which hard-error on a gain "
        "mismatch, this producer has no exposure audit at all -- and this lane had already "
        "fallen into exactly that trap once, at +2.33 against +0.85 stops. A master-versus-frame "
        "level mismatch of only 2.91 percent would erase the entire published 5.7 percent "
        "shortfall, and a 1 percent mismatch moves the reading by 0.0199. THE CHECK IS NOW "
        "IMPOSSIBLE: `C:\\dev\\strehl-out\\V-SOFTCHECK` no longer exists, so the cache, the "
        "master and the 63 frame TIFFs are purged along with the .log files that recorded the "
        "actual `--exposure` for each side. `softcheck.py`'s claim of no exposure gain is a "
        "DOCSTRING ASSERTION, NOT A MEASUREMENT. Treat the 5.7 percent magnitude as "
        "unfalsifiable until re-rendered with the two exposures recorded."
    )),
    (1980, "V-DCNULL", "MEASURED", (
        "THE SIGN OF THE SOFTNESS RESULT SURVIVES BOTH INSTRUMENT THREATS, and the argument that "
        "saves it is structural rather than a tolerance claim. Against DC the bias is 2.320e-07 "
        "on a 5.7 percent effect, five orders of magnitude too small to flip anything. Against "
        "gain the refutation is stronger and does not depend on any bound: for all seven bands "
        "to be truly 1.0000, the single master-versus-frame level mismatch would have to take "
        "the values 4.87, 9.25, 6.51, -2.91, -14.48, -22.13 and -22.92 percent "
        "simultaneously. ONE SCALAR CANNOT TAKE SEVEN VALUES, LET ALONE VALUES OF OPPOSITE SIGN, "
        "so no exposure error can manufacture the crossover from sharper-at-low-frequency to "
        "softer-at-high-frequency. These figures were independently re-derived by the "
        "orchestrator as sqrt(r)-1 over the seven published ratios and agree with the lane's to "
        "the last digit in MAGNITUDE while carrying the OPPOSITE SIGN, because the lane "
        "expressed the frame-over-master ratio and the re-derivation expressed "
        "master-over-frame; the load-bearing property, that the required mismatch CHANGES SIGN "
        "within the set, holds under both conventions and is what refutes the single-scalar "
        "explanation. The claim that survives is therefore the SHAPE -- that the "
        "merge beats the best single frame below roughly 0.20 cyc/px and loses above it -- while "
        "the specific 5.7 percent shortfall does not inherit that protection."
    )),
    (1981, "V-DCNULL", "MEASURED", (
        "`bandqual.py::gnorm` DOES carry the DC defect class, but bounding it leaves the "
        "qualification verdict standing, which is why the bound was computed rather than the "
        "defect merely reported. Differential DC across frames biases the qualifier ratio R by "
        "4.421e-01, i.e. 44 percent, and uniform DC on a stack with a realistic 4.01 percent "
        "level spread biases it by 1.648e-02 to 3.660e-02. Its GAIN normalisation, by contrast, "
        "is exact at 4.339e-07, so `gnorm` works as designed for the thing it was written to "
        "remove and fails only for the thing it was not. Deflating the published R = 3.3235 and "
        "its CI-low of 2.9495 by the worst measured bias gives 2.3047 and 2.0453 against pass "
        "bars of 2.00 and 1.50, so the PASS survives and BAND SELECTION IS NOT MOVED. The "
        "verifier also declared that its own harness has had NO POLARITY AUDIT -- no arm was "
        "deliberately reversed to confirm the harness would report a failure it was told to "
        "report -- and that the wall-pricing table in nyquist.md running to 0.50 cyc/px is not "
        "`ncommon.py` output, so its producer remains unidentified and unaudited."
    )),
]


def main() -> int:
    src = io.open(PATH, encoding="utf-8").read()
    ids = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", src, re.M)]
    if not ids:
        raise SystemExit("FATAL: no fact rows matched")
    if max(ids) != EXPECTED_TAIL:
        raise SystemExit("FATAL: tail is %d, expected %d" % (max(ids), EXPECTED_TAIL))

    n_before = len(ids)
    cur_tail = EXPECTED_TAIL
    for new_id, lane, kind, body in ROWS:
        if new_id in ids:
            raise SystemExit("FATAL: fact %d already present" % new_id)
        if body.count("*") % 2 != 0:
            raise SystemExit("FATAL: odd '*' count in fact %d" % new_id)
        if "|" in body:
            raise SystemExit("FATAL: '|' in body of fact %d" % new_id)
        anchor = None
        for m in re.finditer(r"^\| %d \|.*$" % cur_tail, src, re.M):
            anchor = m
        if anchor is None:
            raise SystemExit("FATAL: could not locate row %d" % cur_tail)
        src = src[: anchor.end()] + "\n" + ("| %d | %s | %s | %s |" % (new_id, lane, kind, body)) + src[anchor.end():]
        cur_tail = new_id

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(src)

    back = io.open(PATH, encoding="utf-8").read()
    ids2 = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", back, re.M)]
    if max(ids2) != ROWS[-1][0]:
        raise SystemExit("FATAL: post-write tail is %d" % max(ids2))
    if len(ids2) != n_before + len(ROWS):
        raise SystemExit("FATAL: row count went %d -> %d" % (n_before, len(ids2)))
    for new_id, _l, _k, _b in ROWS:
        if new_id not in ids2:
            raise SystemExit("FATAL: fact %d missing after write" % new_id)
    print("OK facts %s appended  rows %d -> %d"
          % (", ".join(str(r[0]) for r in ROWS), n_before, len(ids2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
