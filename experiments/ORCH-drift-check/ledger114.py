"""Append the M114-M124 rows to the AGENTS.md milestone allocation ledger.

Rule 41 says the ledger is written at DISPATCH. It has been ten stems stale, and
tonight that staleness had a measured cost: M105 was dispatched onto a question
four prior reports had already closed, and I came within one command of doing it
again with the resampler flag. `prior_art.py` reads docs/research/*.md and so
partially covers the gap, but the ledger is what agents actually read first.

Rows are inserted after the M113 row, keeping the table's rough chronology.

Every row here is written from a primary source I read: the report's own headline
or verdict line, or -- for the live stems -- the brief I dispatched. Nothing is
summarised from memory, because discipline 849 says my summaries have a
systematic sign.
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

AGENTS = Path(__file__).resolve().parents[2] / "AGENTS.md"

ROWS = [
    (
        "M114",
        "**Allocated but never dispatched.** The stem was reserved during the "
        "deconvolution planning burst and the work it was reserved for became "
        "`M115`. Recorded so the number is not reissued -- rule 41 exists because "
        "the `M60` collision was three-way.",
        "--",
        "**retired unused.** Do not reallocate.",
    ),
    (
        "M115",
        "**PRICE THE REVIEWER'S CENTRAL THESIS BEFORE BUILDING IT.** The external "
        "review argued that at this rig's magnification selection cannot produce a "
        "sharp image and only reconstruction can, and proposed making the merge "
        "itself a multi-frame Wiener deconvolution across the focus axis. That "
        "thesis had shaped the roadmap, `captures-needed.md` section 17.5 and section 18, and the "
        "project's own account of what it was for. Measure the headroom against "
        "**the gated average that already ships**, not against a single frame.",
        "`docs/research/M115-deconv-headroom.md`",
        "**COMPLETE. THE THESIS IS DEAD, AND THIS IS THE MOST CONSEQUENTIAL "
        "REFUSAL IN THE PROGRAM.** `R_SNR = 1.0014`, CI **[0.965, 1.038]** -- "
        "against the shipping merge, deconvolution buys **nothing**, and the CI is "
        "tight enough to exclude the effect rather than merely fail to find it. "
        "The apparent win decomposes: contrast **2.51x** bought with noise "
        "**2.03x**. **29.5-36.4%** of output pixels land outside the convex hull of "
        "their own sources -- invented values -- against **exactly 0.0000%** for "
        "every convex arm, and halo energy rises **70.7%** in the 8-16 px shell. "
        "The reviewer's proposed safety guard, **OTF self-calibration from the "
        "through-focus curve, is REFUTED** by direct measurement. And its "
        "pre-registered primary channel **failed its own null in the direction of "
        "its hypothesis** -- SNR **84.9** on a scene-free capture -- so the "
        "instrument was caught before the claim was. Consequence I then had to "
        "sweep: two capture requests were still justified in the owner's brief by "
        "this thesis, and I withdrew the justifications while keeping the captures "
        "(commit `cf382d0`).",
    ),
    (
        "M116",
        "**FOUR QUALITY INSTRUMENTS ARE BUILT, MEASURED, AND OFF BY DEFAULT.** The "
        "project had accumulated switches -- photometric normalisation, smoothing, "
        "halo correction, the soft gate -- each built by a milestone that measured "
        "it and then declined to promote it. Ask the promotion question **once, "
        "across all of them, on real captures, against pre-registered bars**, "
        "rather than leaving four separate deferred decisions.",
        "`docs/research/M116-promotion.md`",
        "**COMPLETE. \"None of the four instruments clears its pre-registered "
        "promotion bar.\"** Its second headline is the one that bears on the "
        "owner's actual complaint and is why the milestone was worth running even "
        "though it promoted nothing. Independently re-verified by `V-M116`.",
    ),
    (
        "M117",
        "**IS THE CORPUS CONTAMINATED BY AN UNKEYED WARP CACHE?** A cache whose key "
        "omits a parameter it depends on will serve one arm's warp to another arm, "
        "and this project's A/B measurements are almost all file-mutation arms over "
        "a shared tree. If true, an unknown number of published facts are "
        "comparisons of a thing against itself.",
        "`docs/research/M117-cache-audit.md`",
        "**COMPLETE. Verdict: the corpus is trustworthy** -- and it got there by "
        "**refuting the premise of its own brief in its first result**, which is "
        "the outcome I most wanted and least expected. A clean negative on a "
        "contamination question is worth more than most positive findings, because "
        "everything downstream inherits it.",
    ),
    (
        "M118",
        "**DOES THE MERGE'S RESAMPLING KERNEL COST THE OWNER VISIBLE SHARPNESS?** "
        "`M95` landed Lanczos-3 switchable on `align` and deliberately did not move "
        "the default. Re-ask at **merge** time, on real captures, with a non-author "
        "eye read as a required deliverable alongside the metric.",
        "`docs/research/M118-resampler.md`",
        "**COMPLETE, folded as facts 1670-1674 and disciplines 852-853.** It "
        "answered the question and then **dismantled the instrument it had just "
        "used to answer it**: a closed form derived from `align.rs`'s own filter "
        "weights, run with **no photograph at all**, predicts its own per-cell "
        "headline to **0.0155 dex against a 0.1300 dex effect** -- the metric is "
        "**88% the kernel's datasheet**. Corroborated from the other side by "
        "`nearest` **topping** the band metric exactly as pre-registered. Rule 9's "
        "flat-decile control **fails on all three subjects**. And yet by eye it "
        "**is** better. **The compositional finding is the one that matters**: "
        "Lanczos-3 makes lateral-CA fringing **more conspicuous**, a second "
        "independent sighting of fact 1452's prediction that the shipped "
        "Catmull-Rom has been **hiding that fringing with blur** -- so the CA "
        "correction is a **prerequisite** for a sharper kernel, not an independent "
        "tidy-up. Declined to promote because **`strehl stack` has no "
        "`--resampler` flag**, so a 2.91-3.92x cost cannot be declined; handed over "
        "an `align_cmd.rs` diff rather than editing across an ownership boundary. "
        "Separately: it was **not** PIL-exposed, re-ran the question anyway, and "
        "found that had it used PIL, **rule 9's control would have sign-reversed**.",
    ),
    (
        "M119",
        "**BUILD CAMERA/LENS IDENTITY EXTRACTION.** The optical profile system was "
        "shipped with 287 passing tests and **zero consumers** (fact 1444's class): "
        "nothing in the pipeline can tell which body and lens took a frame, so a "
        "gear-specific correction cannot be applied safely to anyone's captures but "
        "by hand. Extract identity from maker notes and make it the key that "
        "profiles are looked up by.",
        "`crates/**`, `docs/research/M119-gear-identity.md`",
        "**live (`d9762866`, `claude-opus-5`).** This is the unblock for turning "
        "any gear-specific correction on by default rather than behind a "
        "case-sensitive string the owner has to type.",
    ),
    (
        "M120",
        "**THE BACKGROUND PATCHWORK THE OWNER CAN SEE.** Smooth out-of-focus "
        "background renders in visible patches rather than continuously. Diagnose "
        "the mechanism and, per discipline 572, **deliver the metric first** -- a "
        "visual impression is a hypothesis with a milestone attached.",
        "`experiments/M120-patchwork/`, `docs/research/M120-patchwork.md`",
        "**live (`2f2a7434`, `claude-opus-5`); report already written.** Its "
        "opening line is *\"ORCH's fact 1604 is wrong in two of its three limbs. "
        "But fact 1603 is right, and it is\"* -- **a fifth orchestrator folding "
        "error, found by a subordinate**, and it lands on the same night as "
        "discipline 849. **Not yet folded; the correction to 1604 is owed.** "
        "Warning attached to this stem: its `patchwork_16bit.py` derives its "
        "ceiling via `np.iinfo(a.dtype).max` on 8-bit data, giving **255 rather "
        "than 65535**.",
    ),
    (
        "M121",
        "**THE HALO IS THE PROJECT'S NUMBER ONE DEFECT AND HAS NO FIX.** `M87` "
        "built a correction, measured it, and recommended against it (erases the "
        "bee's abdomen hairs while its own metric reports a 72.9% improvement); "
        "`M111`'s claims were audited; deconvolution is now **measured dead** by "
        "`M115` and so is not the route either. Test the **polarity mechanism** -- "
        "which side of the occluding edge the excess energy sits on, and whether "
        "that is consistent with the two-layer veiling model the corpus has assumed "
        "but never confirmed directionally.",
        "`experiments/M121-halo/`, `docs/research/M121-halo-polarity.md`",
        "**live (`7d8eb5c3`, `claude-opus-5`). Still the #1 visible defect with no "
        "shippable fix**, and after `M115` there is no known route to "
        "out-resolving the sharpest frame the owner shot -- remaining work is about "
        "not degrading what he captured.",
    ),
    (
        "M122",
        "**DOES THE BLOTCH DEFECT TRACK MEASURED LEVEL DRIFT?** `STREHL_PHOTOMETRIC` "
        "is built and off. Rather than re-running the promotion bar `M116` already "
        "failed it against, ask the **mechanistic** question across the whole "
        "corpus: if the blotch is caused by exposure drift between frames, its "
        "severity must correlate with independently measured per-frame level drift.",
        "`docs/research/M122-photometric-promotion.md`",
        "**live (`1db793fa`, `claude-opus-5`); report already written and "
        "NOT YET FOLDED.** *\"Answer: yes -- rho = +0.70, one-sided permutation "
        "p = 0.0035, n = 14 stacks.\"* **The mechanism is confirmed and the default "
        "still does not move: verdict KEEP-OFF.** Registration frozen per subject "
        "so the correlation is not confounded by the solve. **This is the first "
        "confirmed mechanism for a defect the owner can actually see**, and it is "
        "owed both a fold and a line in his brief.",
    ),
    (
        "M123",
        "**THE OUTLIER MASK MEETS REAL CAPTURES.** `M89` built the noise-normalised "
        "robustness weight and rejected it on five registered bars; the external "
        "review named it as one of the unglamorous layers SOTA dies without. Re-ask "
        "against real captures with a **stationary subject as the null** and a "
        "moving one as the positive control.",
        "`docs/research/M123-robustness-mask.md`",
        "**COMPLETE, folded as facts 1666-1669 and disciplines 850-851. Flat "
        "refusal: do not ship the mask, do not wire it.** It fires on **29.55%** of "
        "a **stationary** subject and **4.3x less** on the moving one -- the "
        "instrument is **anti-correlated with the thing it exists to detect**. Four "
        "of six pre-registered criteria fail; no response below 1.0 px; separation "
        "**2.12x** where displacement separates 0.96x. Its null **passes on the "
        "mean (1.038) and fails on the spread (0.1247 against a predicted 0.0442, "
        "2.82x)** -- a mean-only null would have passed it. **Fourth independent "
        "refusal of this component** (M28, M60, M89, M97r). **Consequence: I had "
        "already promised the owner this fix was being wired in tonight, and had to "
        "withdraw it** (commit `8e2d9eb`).",
    ),
    (
        "M124",
        "**A QUALITY CHANGE THAT CANNOT BE DECLINED IS A TAX, NOT A DEFAULT** "
        "(discipline 853). `M118` measured Lanczos-3 as visibly better and refused "
        "to promote it because `strehl stack` exposes no `--resampler` flag, "
        "leaving the shipped `lanczos2` variant **unreachable from any command "
        "line**. Plumb the **existing** enum and parser through to the merge path. "
        "**Explicitly barred from moving the default**, which is pre-registered in "
        "`ORCH-kernel-decision.md`. Required proof is by **hash, not by reading "
        "the code**: byte-identical with no flag and with the explicit default, "
        "and provably different for `lanczos3` and `nearest` -- because a flag that "
        "parses and is then ignored is exactly fact 1444's failure and "
        "`STREHL_FIX_CA`'s silent no-op under `STREHL_ALIGN=0`.",
        "`crates/strehl-cli/**`, `docs/research/M124-resampler-flag.md`",
        "**live (`eb0fd6e1`, `claude-opus-5`).** Dispatched **after** running "
        "`prior_art.py`, which surfaced `M95`'s *\"Lanczos-3 lands switchable\"* "
        "and the pre-registered GO/NO-GO -- **the check changed the brief before it "
        "was sent**, narrowing it from *add a kernel* to *expose the one that is "
        "already there*.",
    ),
]


def main() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    lines = text.split("\n")

    anchors = [i for i, ln in enumerate(lines) if ln.startswith("| `M113` |")]
    assert len(anchors) == 1, f"expected exactly one M113 ledger row, found {len(anchors)}"
    at = anchors[0]

    for stem, _, _, _ in ROWS:
        pat = re.compile(r"^\| `" + stem + r"` \|", re.M)
        hits = pat.findall(text)
        assert not hits, f"{stem} already has a ledger row -- refusing to duplicate"

    block = []
    for stem, asked, writes, state in ROWS:
        row = f"| `{stem}` | {asked} | {writes} | {state} |"
        assert row.count("|") == 5, f"{stem}: pipe count {row.count('|')} != 5"
        # `crates/**` is a glob inside a code span, not an opening bold marker.
        # Strip code spans before counting, or the checker convicts valid rows.
        bare = re.sub(r"`[^`]*`", "", row)
        assert bare.count("**") % 2 == 0, f"{stem}: unbalanced bold"
        assert "\n" not in row, f"{stem}: embedded newline"
        for ch in row:
            assert ch == "\t" or ord(ch) >= 32, f"{stem}: control char {ord(ch)}"
        block.append(row)

    lines[at + 1 : at + 1] = block
    out = "\n".join(lines)

    for stem, _, _, _ in ROWS:
        assert len(re.compile(r"^\| `" + stem + r"` \|", re.M).findall(out)) == 1, stem
    assert out.count("| `M113` |") == 1

    AGENTS.write_text(out, encoding="utf-8")
    print(f"inserted {len(block)} ledger rows after line {at + 1} (the M113 row)")
    for stem, _, _, _ in ROWS:
        print(f"  {stem}")


if __name__ == "__main__":
    main()
