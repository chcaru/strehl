# M56 — citation-content audit — SOURCE REPORT MISSING

**Status: DISCLOSURE STUB. This is not M56's report. M56's report was never committed
and is unrecoverable.**

## What happened

M56 audited every `§4 fact NNN` citation in `crates/**` for *content* — not whether the
number resolves to a row, but whether the row says what the citing code claims. It
reported 260 citation instances, 77 distinct fact numbers across 18 files, and 11
defects, 5 of them user-visible.

Its findings were folded into `SYNTHESIS.md` as **facts 713–723, disciplines 343–347 and
questions 168–171**, all carrying provenance `M56 (MEASURED)`.

**The fold cited a source that does not exist in any commit.** Rule 31 requires every
folded claim to name a committed source. The orchestrator folded from the agent's
returned report text without requiring the agent to commit it, and that text is now gone.
This is recorded as SYNTHESIS **fact 765**.

## What survives, and what does not

**Evidence — committed alongside this file**, under `experiments/M56-citations/`:
the extraction and grouping scripts, the citation inventory, the per-file context dumps,
and the `cargo test` capture. These are the inputs the audit ran on. They are sufficient
to re-run the audit; they are not the audit's reasoning.

**Independent verification.** M58 could not check the eleven rows for fidelity — there was
nothing to compare them against — so it verified them directly against `crates/` instead:

| Row | Result |
| --- | --- |
| 714 (the invented regularised-Tenengrad speckle) | **Confirmed exactly.** Independently re-confirmed a third time by M53 from three sources (fact 752). |
| 715 (`~1.7 ms` quoted at five sites, including in the example that measured its refutation) | **Confirmed exactly.** |
| 718 (`--stats` help said 494 MB, binary printed 527 MB) | **Confirmed exactly.** Fixed. |
| 720 (a green test with two of three assertions false) | **Confirmed exactly.** |
| 721 (`LADDERS` stale on 8 of 20 rungs) | **Confirmed exactly.** |
| 717 (`stack.rs` prints "fact 200a" every run) | Confirmed with **narrower scope** — the string is in one `match` arm, not every run. |
| 719 (`profile.rs` has four mis-cited sites) | **Partly refuted.** The count of four is right, but "all cite `M25 fact 200`" is false: `:92` cites `200a`. The count came from a substring match. Corrected in place; see fact 763. |

**What is unrecoverable:** M56's scope statements, its method, its own uncertainty
qualifications, and any finding it made that the orchestrator did not fold. Facts 713,
716, 722 and 723 have no committed source and no independent re-verification.

## The rule this violated, stated plainly

A fold whose source is not committed is **unauditable by construction**. Code
verification can confirm a claim about code; it cannot confirm that the fold reported the
source faithfully, preserved its scope, or omitted nothing. Question 179 asks whether
provenance cells should carry the source commit sha, which would make this omission
impossible to complete rather than merely against the rules.
