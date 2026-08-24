"""Correct fact 1339 in place and fold what M100 actually shipped.
Facts 1346-1347, discipline 668.

Fact 1339's headline was wrong: the exposure correction IS in the binary, in
strehl-core::color, fully implemented and tested by M100. What is missing is
the command-line wiring, and M100 supplied that as a verbatim patch that has
been sitting unapplied.

My grep covered crates/strehl-cli/src only. I asserted a negative from a
search that could not have found the thing.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

AMENDMENTS = [
    ("**THE MEASURED EXPOSURE CORRECTION IS NOT IN THE BINARY; IT LIVES ONLY IN AN EXPERIMENT SCRIPT.**",
     "**THE MEASURED EXPOSURE CORRECTION IS NOT WIRED TO THE COMMAND LINE.** *(Headline corrected: the original "
     "read \"is not in the binary; it lives only in an experiment script\", which is **false** -- see fact 1346. "
     "The grep below is accurate but was scoped to one crate of two.)*"),
    ("ORCH (MEASURED, grep of the shipped CLI + read of `gallery.py`); dispatched to M105",
     "ORCH (MEASURED, grep of `strehl-cli` only + read of `gallery.py`); **headline corrected by fact 1346**; "
     "dispatched to M105, whose brief was corrected in flight"),
]

FACTS = [
    (1346, "**THE EXPOSURE MACHINERY IS SHIPPED, TESTED AND UNWIRED, AND M100's PATCH FOR THE WIRING HAS BEEN "
           "SITTING UNAPPLIED.** `crates/strehl-core/src/color.rs` holds the whole of it: `AUTO_EXPOSURE_PERCENTILE "
           "= 99.9`, `AUTO_EXPOSURE_TARGET = 0.90`, `AUTO_EXPOSURE_MAX_STOPS = 6.0`, "
           "`AUTO_EXPOSURE_STEPS_PER_STOP = 100.0`, a `nearest_rank_index` deliberately matching "
           "`numpy.percentile(method=\"inverted_cdf\")` to the bit, `Exposure::resolve` refusing an exposure "
           "without `--srgb` and refusing both flags at once, `choose_exposure`, and `AppliedExposure` with a "
           "round-trip token -- under a test module whose bars are named against M100's pre-registration. **A grep "
           "of `strehl-cli` for `exposure` finds no use of any of it.**",
     "**M100 could not wire it because it may not edit `main.rs` or `merge_cmd.rs`, so it supplied verbatim patches "
     "in its §4 and routed them to the orchestrator, who did not apply them.** Re-running M100's own "
     "`patchcheck.py` at current HEAD gives **22 blocks located exactly once, 2 not** -- all nine `merge_cmd.rs` "
     "blocks clean, and **both failures in `main.rs`, caused by the orchestrator's own later application of M95's "
     "patch at `56bd846`**, which invalidated M100's note that neither file had been touched. The corpus-safety "
     "property is already designed in and stronger than a check: the gain folds into the existing normalisation "
     "closure, so `image_out.rs` needs no patch and the byte-frozen branch is *textually* unchanged.",
     "ORCH (MEASURED: `patchcheck.py` at HEAD, + read of `color.rs` and M100 §4); M100's patch, unapplied"),

    (1347, "**THE ORCHESTRATOR ASSERTED A NEGATIVE FROM A SEARCH THAT COULD NOT HAVE FOUND THE THING, AND PUT IT "
           "IN A BRIEF AS A LOAD-BEARING PREMISE.** The brief dispatching M105 stated *there is no exposure logic in "
           "the CLI at all* and instructed the agent to write `crates/strehl-cli/src/exposure.rs` from scratch. The "
           "grep behind it covered `crates/strehl-cli/src`; the logic is in `crates/strehl-core/src/color.rs`, the "
           "crate M100's own ledger row names as its property. **The brief did not state its search scope**, so "
           "nothing in it flagged the claim as scope-limited.",
     "**A negative claim is exactly as strong as the scope of the search that produced it, and a brief that omits "
     "the scope launders a narrow search into a general fact.** Caught 20 minutes after dispatch, by reading the "
     "ledger row that named the other crate -- the same row the orchestrator had written by hand an hour earlier. "
     "M105 was redirected before it built anything. This is the second time tonight the ledger repair paid for "
     "itself and the fifth error of the confirm-in-general-never-check-the-instance class, after facts 1297, 1304, "
     "1324 and 1341.",
     "ORCH (self-disclosed); brief corrected in flight, nothing built against it"),
]

DISCIPLINES = [
    (668, "**State the scope of any search that produces a negative claim, in the same sentence as the claim.** The "
          "orchestrator briefed a milestone on *there is no exposure logic in the CLI at all*, from a grep of one "
          "crate, when the logic sat fully implemented and tested in the other -- and instructed the agent to "
          "rebuild it. *\"A grep of `crates/strehl-cli/src` finds none\"* would have carried its own limitation and "
          "invited the check; *\"there is none\"* did not. **Absence of evidence is a fact about the search, and a "
          "brief that omits where you looked converts it into a fact about the repository.** Facts 1346, 1347."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    for anchor, repl in AMENDMENTS:
        n = text.count(anchor)
        if n != 1:
            raise SystemExit(f"AMENDMENT TARGET NOT UNIQUE ({n}): {anchor[:70]!r}")
        text = text.replace(anchor, repl, 1)

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1345 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^667\. ", l))
    assert disc_idx > fact_idx, f"fact {fact_idx}, disc {disc_idx}"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        row = f"| {fid} | {claim} | {interp} | {src} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes, need 5"
        rows.append(row)

    drows = [f"{did}. {body}" for did, body in DISCIPLINES]

    for fid, *_ in FACTS:
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
    for did, _ in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"amended fact 1339 in place; folded facts 1346-1347 after line {fact_idx}, "
          f"discipline 668 after line {disc_idx}")


if __name__ == "__main__":
    main()
