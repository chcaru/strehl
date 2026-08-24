"""Sharpen fact 1449: the merge HAS photometric and disagreement machinery, and
both are deliberately diagnostic-only."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1451,
     "**THE MERGE MEASURES PER-FRAME PHOTOMETRIC DRIFT AND FRAME DISAGREEMENT, AND ACTS ON NEITHER -- BY "
     "DESIGN, IN WRITING.** This sharpens fact 1449 against its most obvious rebuttal, which is that "
     "`merge.rs` does mention photometry. It does, and the docstring on "
     "`Estimator::fold_censored_probing_photometry` (merge.rs:653) says the correction is *\"applied to "
     "the disagreement accumulator only... The four `sum` planes, `n_eff`, the gate and the censoring "
     "bits are all untouched, so **this cannot change the merged image**.\"* It exists *\"to price rival "
     "explanations for disagreement.\"* The same file records that **M24 measured real per-frame drift of "
     "0.91% peak-to-peak on `109MSDCF` and 11.70% on `coffee-bean`, and that EXIF does not predict it, "
     "so the correction must be fitted from the data.** Separately, `Estimator::track_disagreement` "
     "accumulates noise-normalised disagreement among the frames a pixel actually averaged -- and "
     "nothing rejects on it; the only admission test is the focus gate.",
     "**So the situation is not that the forward model is missing: it is that it is fully instrumented "
     "and deliberately disconnected from the output.** An 11.70% peak-to-peak gain drift entering a "
     "gated average uncorrected means the gate reads an exposure change as a signal change, which is "
     "exactly the failure the calibrated noise model exists to prevent. And tracked-but-unused "
     "disagreement is the reviewer's *\"one twitching antenna poisons both reference and average with no "
     "defence\"*, measured and then not spent. **Note that nothing here is dishonest** -- the code says "
     "precisely what it does and does not do, and the probe's diagnostic-only scope is a deliberate, "
     "well-argued choice for pricing a hypothesis. **The defect is that the loop was never closed, and "
     "no instrument was asking whether it had been** (facts 1449-1450, discipline 732).",
     "ORCH, read directly from `merge.rs:653-693` and its cited M24/M28 measurements (MEASURED)"),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1450 \|", l))

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        r = f"| {fid} | {claim} | {interp} | {src} |"
        k = r.count("|") - r.count("\\|")
        assert k == 5, f"fact {fid}: {k} unescaped pipes"
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
        rows.append(r)

    out = lines[:]
    out[fact_idx + 1:fact_idx + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print("folded fact 1451")


if __name__ == "__main__":
    main()
