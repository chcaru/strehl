# Research and corpus workflow

Read this before commissioning experiments, publishing measurements or folding
results. Detailed examples retain their original rule numbers in the
[engineering ledger](engineering-ledger.md). Commands run from the repository root.

## Before dispatch

1. Use the [research guide and topic indexes](../research/README.md) to locate
   reports and experiment results. Run the unified search **and** the mechanical
   prior-art check, which also surfaces source-code test names and refusals:

   ```powershell
   python scripts/research.py search <subject words>
   python experiments/ORCH-drift-check/prior_art.py <subject words>
   ```

   Search the question **and supporting assertions**, including claims of
   absence. Also inspect retained experiment results; the historical index is
   not exhaustive. Name prior work in the brief. "Already answered, nothing to
   add" is valid. Reopening a rejected branch needs new evidence and a precise
   changed question (original rules 40 and 43).
2. Allocate a unique identifier, question, owned paths, owner and state in the
   [milestone ledger](milestone-ledger.md) **before dispatch**, covering reports
   and experiments. Suffix genuine continuations; never reuse an identity.
3. Keep current scope, resource bounds and stopping conditions in the experiment's
   own brief. The [dispatch history](experiment-history.md) preserves earlier
   constraints and the October 17 pause; it is not a queue of authorized jobs.
4. Name the consumer, its actual input quantity and gauge, a failing input for
   each gate, a placebo/null and a known-real positive control. Identify shared
   estimators, fitted constants and circular paths. A plant validates an
   operator, not a calibration constant it supplies itself.

## Execute and review

- Establish that controls reject a wrong answer **before** using the metric.
  Run flat-ROI controls first for sharpness; state failure direction. Gradient
  energy can reject collapse but cannot establish quality. Report the null and
  its standard error beside a claimed separation, ratio or confirmation.
- Assert that fixtures exercise the interesting case. Assert tolerated model
  disagreement at its expected wrong value instead of excluding it. Give each
  headline a regression on its producing code path and a causal placebo.
- Break shared-data circularity with an independent scale, spatial shift or
  appropriate permutation, paired with a positive control. Compare temporal
  sigma with like quantities and sanity-check it against the injected model;
  spatial standard deviation includes scene structure.
- Before a sweep, show the stimulus can express the proposed failure/turnover.
  An endpoint minimum is "no turnover found within the sweep," not an optimum.
  Alternate timing direction, take per-setting minima, record host load, and
  describe near-flat results as bounds.
- Freeze the exact command, resolved defaults, input order/range and identity,
  relevant environment, worker count, code/build identity, output bytes and hash.
  Reproduce the original baseline before extending a harness, stratifying on
  every original column. Byte identity is consistency, not independent evidence.
  Replay a broken freeze in its own recorded environment before blaming code.
- Prove diagnostic non-perturbation by output hash with it on/off, including its
  placebo. Preserve completed experiment sources, builds and receipts.
- Independent verification must **re-choose**, not just recompute: challenge
  nuisance estimator, reference, arm, null and library defaults with different
  defensible choices. Author-run tests do not replace independent verification
  of research conclusions.
- Inspect complete photographs before choosing native witnesses. Use identical
  display transforms and unresampled crops within a commissioned viewer's limit
  (historically about 400 px). Record coordinates. Resized overviews are for
  orientation; do not base defect verdicts on them.
- Label claims MEASURED / VERIFIED / DERIVED / ARGUED / UNVERIFIED and attach the
  command actually run. Before publishing, name the code line/command discharging
  each applicable rule and explain those that do not apply.

## Fold into SYNTHESIS

1. Fold only a **committed** report revision; cite its SHA in the source column.
   Read the folded row itself before describing a correction. Cite symbols and
   content, not line numbers alone. Read the full source column and prohibitions.
2. Check existing folds **by content before number**. Match roughly the first
   70 characters of each proposed fact against all of section 4. All matches
   means the fold is done: record its actual mapping. For partial matches,
   reconcile and fold only the new delta. Keep duplicates marked in place so
   citations resolve; do not fold restated findings as corroboration.
3. Reports propose `P1`, `P2`, etc.; the fold owner allocates absolute numbers.
   Claim and programmatically collision-check blocks **per namespace** using
   existing checks in `experiments/*/fold-*.py` and other fold scripts. Facts,
   disciplines and questions are separate namespaces. Shift a colliding block
   together and record the mapping in the fold and report.
4. Slice the destination section first; insert after the **whole item**, including
   continuation lines. Section 4 is a four-column table; sections 5 and 10 are
   numbered lists. Re-emit consumed anchors, count every deletion, re-list
   headings, check unescaped pipes across **all** table rows, and preserve one
   final newline. Do not widen a table to silence misplaced-item diagnostics.
5. Propagate amendments to citing code: search `crates/` for the fact number and
   fix affected consumers in the same scoped change.
6. Run the fold checker, **read its qualifier bucket**, then run the corpus linter:

   ```powershell
   python experiments/ORCH-drift-check/fold_check.py <fold.py> <report.md> docs/research/SYNTHESIS.md
   python scripts/corpus_lint.py
   ```

   Capture complete output and exit code before display filtering; assert the
   exact expected code, including for red controls. The fold checker supports
   `--commission` to exercise its planted failures. Green checks do not establish
   semantic fidelity (original rule 31b).

## Maintaining these instructions

Keep `AGENTS.md` short and action-oriented. Put rationale/incidents in the
engineering ledger, allocations in the milestone ledger, and detailed briefs
beside experiments. Preserve old identifiers for corpus/source citations.
Historical scripts that edit the former root ledger need adaptation before reuse.

When moving guidance, check content preservation and links, not just line count.
`scripts/corpus_lint.py` reads rules from `engineering-ledger.md`, allocations
from `milestone-ledger.md`, and checks Markdown under `docs/agents/`. Keep this
integration and its regression tests working.
