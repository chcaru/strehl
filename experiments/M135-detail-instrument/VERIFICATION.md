# M135 independent verification

Status: **VERIFIED — final pass reports no defects**

Read-only `ultracode:ultra-verifier` passes independently inspected the M135
report, source, freeze history, generated artifacts, and D8 adjudication.

The original verification:

- reran all 22 frozen estimator gates;
- reproduced postfilter invariance at machine precision;
- exercised all missing-lineage paths;
- confirmed all 32 permutation maps were distinct derangements;
- checked the freeze commits were path-scoped;
- checked the historical and current FRC rulings;
- compared `RESULTS.md` with `commission.json`; and
- sampled more than 15 verbatim quotations and every citation range.

The D8 update verification independently:

- matched all four historical source blobs;
- reproduced blur `0.9938215871-0.9973982082`, normalized-SNR movement
  `0.537785071%`, RMS-gradient gain `8.2513656688x`, and the power identity;
- reproduced common-filter scaling/invariance to at worst `3.553e-15`;
- confirmed the failed historical null, common-mode FRC `0.972099`, phase-0
  `STOP_REMOVE_RUST` verdict, SPLIT2's held-out tuner-leakage RED, and its
  second-repeat geometry failure;
- regenerated `d8-audit.json` and `audit.json` byte-for-byte in memory; and
- confirmed all 87 citation tokens and 104 individual ranges are valid.

The D8 verifier passes found and caused correction of several audit defects:
a citation checker that ignored second comma-separated ranges; one range
extending three lines past EOF; wording that overstated exact cancellation and
bounded residuals for finite Hann/ring aggregates; a no-result check that
covered only one SPLIT2 output path; and wording that wrongly credited repeated
brackets with temporal-noise independence already present in the odd/even
split. The final verifier reported **PASS with no remaining defects**.

This verifies the mathematical and synthetic estimator work. It does not
replace physical reference/extraction commissioning or produce an M1 score.

## Amendment 4/5 verification

Status: **VERIFIED by a separate implementation path; not an independent
author**

`flat_verify.py` does not import `commission.py`. It independently:

- checked that `commission.json` passes all 25 gates;
- compared every pre-amendment information, transfer, residual, tone,
  sample-size, permutation, checker, averaging, and C0-C21 result against
  `commission-run4-pre-flat-null.json`;
- verified every uncontaminated arm's maximum flat/detail information,
  reference-repeatability, and output-repeatability ratios against the frozen
  `0.10 / 0.25 / 0.10` bars;
- checked common-artifact rejection in 128/128 populations, structured-flat
  rejection at ratios `1/1/1`, and missing-flat rejection in 128/128;
- checked the four frozen squared noise gains, q95 information ratio below
  `0.90`, and zero promotions;
- read M137's retained JSON directly and matched its detailed gap, flat gap,
  ratio, failed S7 gate, preserved old gates, and final failure; and
- generated a fresh 128-site independent probe. Baseline was `OK`; the
  high-band noise plant reduced `J_TR` from `3.9841138452442353` to
  `2.6334749277223413` (`0.6609938947567657x`); its flat information ratio
  remained `0`; structured and common-artifact flats failed; and omission
  returned `MISSING_FLAT_CONTROL`;
- exercised a malformed primary bundle and confirmed typed `INVALID_SHAPE`
  rather than an indexing error; and
- confirmed amendment 6's replacement campaign is byte-identical to the
  pre-shape-guard artifact.

All 20 checks passed. The machine-readable result is
`flat-verification.json`.

## M138 consumer-interface verification

Status: **SELF-TESTED; PHYSICAL BINDING UNAVAILABLE**

The comparison checker was committed before its self-test ran. Its frozen
synthetic battery passed all 14 controls:

- default binding returns `INSTRUMENT_UNBOUND`;
- an unregistered capture returns `NOT_APPLICABLE`;
- exact null and genuine improvement return `DETAIL_PASS`;
- information, one-cell transfer, and unexplained-repeatability defects return
  `DETAIL_FAIL`;
- candidate and legacy flat-null failures return `INSTRUMENT_INVALID`;
- missing, short, non-finite, wrong-seed, unpaired, wrong-frequency,
  wrong-angle, wrong-hash, Boolean/numeric-string draw, Boolean-count, and
  producer-Boolean payloads are invalid;
- exact threshold values pass and one floating-point step beyond each
  threshold fails; and
- every decision exposes the contract and checker hashes while non-decisions
  keep `detail_pass=null`.

`comparison-rule-manifest.json` records the frozen hashes.
`comparison-binding.json` remains `UNBOUND`; this test therefore verifies only
the deterministic consumer interface, not a physical detail decision. M138
still requires the pre-output physical binding amendment and its referenced
capture, generator, preregistration, environment, and commissioning artifacts.

## M138 executable-adapter verification

Status: **SELF-TESTED 56/56; LOCAL MUTATIONS 27/27; REANCHORED M149
MUTATIONS 31/31 APPLIED AND KILLED, 0 UNAPPLIED; REPLACEMENT-RACE BATTERY
7/7; PHYSICAL BINDING UNAVAILABLE; SECOND M149 SEND BACK REPAIRED, RE-REVIEW
PENDING**

The adapter preregistration and source were committed before behavioral
execution. The first invocation failed at startup because ordinary sibling
imports are unavailable under this host's `python -I`; amendment 1 replaced
that import with an exact path-bound import before any request or statistic
ran. The amendment-1 battery then passed 24/25. Its sole miss was in the
self-test fixture: an unbound binding's explicit JSON `null` was copied into a
request hash field instead of selecting the intended valid dummy digest.
Amendment 2 changed only that fixture and preserved the 24/25 artifact.

The complete amendment-2 rerun passed all 25 predeclared checks. A subsequent
source audit found that the adapter executed its local core before performing
its own bundle check. M138's outer adjudicator already verified the bundle
before process launch, but amendment 3 made the standalone order truthful:
bundle and environment verification now precede local core and NumPy imports.
The pre-hardening 25/25 artifact was preserved, and the complete amendment-3
rerun passed the same 25 checks. A further source review found that the
standard loader could still execute an unbound cached `.pyc`. Amendment 4
removed that loader and now compiles the already-verified core source bytes
directly. The amendment-3 outputs were preserved, and the amendment-4 rerun
passed the same 25 checks.

M149's independent fixture-based review then found two CRITICAL, one HIGH, and
two MEDIUM defects. The adapter hashed each artifact and the core source, closed
the file, and later reopened the path for parsing or execution. A concurrent
replacement could therefore turn a registered `INSTRUMENT_INVALID` payload into
`DETAIL_FAIL → false`, or execute unregistered core bytes while reporting the
registered bundle hash. The 25-check suite also counted outcomes without proving
that its individual guards were capable of failing.

Amendment 5 changed the substrate, not the scientific contract. Every request,
artifact, bundle manifest, and bundle member is now read exactly once into an
immutable byte snapshot. The adapter hashes that snapshot, parses or compiles
only that snapshot, and never reopens the verified path. The core's own JSON and
hash helpers are rebound to the verified bundle snapshots. Thus a replacement
before the read is rejected by its digest, while a replacement after the read
cannot affect the consumed bytes. This is a structural guarantee, not an
empirical timing assumption.

The amendment-5 ordinary battery had 51 named checks. It retained the original
behavior checks and added direct probes for every formerly uncovered predicate:

- valid `DETAIL_PASS → true` and `DETAIL_FAIL → false` decisions;
- flat, missing-flat, and other internal-invalid states with no Boolean;
- unregistered capture handling and request-level empty-stdout refusal;
- nested supplied-decision rejection, exact environment equality, both request
  binding-hash comparisons, and the canonical terminal newline;
- positive and negative arms for all 20 commissioning predicates; and
- byte-identical replay.

`m138-adapter-verification-run6-pre-threshold-fix.json` preserves that 51/51
result.
`m138-adapter-verification-run5-pre-m149.json` preserves the final pre-review
25/25 result;
`m138-adapter-verification-run2-failed.json` preserves the 24/25 run.
`m138-adapter-verification-run3-pre-bootstrap.json` preserves the
pre-bootstrap-hardening 25/25 run.
`m138-adapter-verification-run4-pre-source-loader.json` preserves the
pre-source-loader-hardening 25/25 run.
`m138-adapter-bootstrap-verification-run2-pre-m149.json` preserves the
pre-review 10/10 bytecode/source bootstrap result, and the earlier 5/5
pre-source-loader artifact remains retained.

The pre-threshold `m138_adapter_mutation.py` independently neutralized 25
guards one at a time.
Every substantive mutant made its registered named check fail, and one inert
docstring mutation left all probes green. The result is 25/25 substantive
mutations killed with the inert control surviving. Amendment 6 records the
first harness failure: raw CRLF source did not match frozen LF anchors.
Amendment 7 records the second: the initial hash-error mutant raised through an
unrelated `None` dereference rather than turning the named check red. Both
harness defects were frozen before repair; that mutation artifact is preserved
as `m138-adapter-mutation-verification-run1-pre-threshold-fix.json`.

The pre-threshold `m138_adapter_race.py` artifact reproduced both M149
replacement mechanisms. Stable
registered missing-flat input remains `INSTRUMENT_INVALID` without a Boolean;
stable registered fail input remains `DETAIL_FAIL → false`; stable replaced
artifact and core inputs refuse nonzero with empty standard output, and the
core sentinel never executes. Across 16 concurrent artifact attempts there were
5 refusals and 11 registered-invalid decisions, with zero unsafe conclusions.
Across 16 concurrent core attempts there were 8 refusals and 8 registered-core
decisions, with zero sentinel executions or unsafe reports. All 7 named race
checks passed.

M149 re-attacked those repairs at commit `714f38c6`. Its positive controls
reproduced both old races, while 512 repaired attempts per race exercised both
exit paths without an unsafe result. It independently reproduced the local
25/25 mutation result and 7/7 race result. The two CRITICAL races are therefore
closed.

That re-attack returned a second `SEND BACK` for threshold coverage. Both
contract-key substitutions applied cleanly and passed all 51 checks. On
discriminating controls, blur q95 `0.95` incorrectly passed the strict `<0.90`
bar when wired to `1.10`, and improvement q05 `1.00` incorrectly passed the
strict `>1.10` bar when wired to `0.90`. Nineteen additional entries in M149's
32-entry manifest did not apply because the read-once refactor had moved their
anchors.

Amendment 8 names both contract-key selectors, directly probes their exact
values, and adds public-CLI marginal fixtures requiring both commissioning
Booleans to stay false. It also adds a stale bundle-member refusal check. The
current ordinary battery passes 56/56. The local helper mutation suite now
kills 27/27 substantive mutations with its inert mutation green.

`m149-mutation-manifest-reanchored.json` maps every one of M149's 19 stale
anchors to a present current predicate; none is classified gone. M149's
unchanged mutation harness applied all 32 entries from that manifest: all
31/31 applied substantive mutations went red, zero entries were unapplied, and
the inert control remained green. The two threshold mutants each failed both
their exact-key probe and their marginal public-CLI control.

M149's own race programs were then rerun control-first. The vulnerable
artifact race reproduced at attempt 5/120 and the vulnerable source race,
including sentinel execution, at attempt 8/120. Against amendment 8, 128
artifact attempts split 63 registered snapshots and 65 refusals; 128 source
attempts split 58 registered snapshots and 70 refusals. No repaired attempt
converted invalidity into `DETAIL_FAIL`, and no replacement source executed.
The current M135 race harness also passed 7/7 with 128 attempts per race.
This is a direct replay of the reviewer's mechanisms, not a substitute for
M149's next independent review.

`m138-adapter-description.json` separately exercises production bundle and
environment verification and reports:

- adapter
  `daa8a24531343bf2ec75c31f1dbabd3b5594b88e792f4e6f3005cbc9cd5302d2`;
- bundle
  `72951c1924d577c7a08d69d5ffcfc1c52816240068767e54cf67e4f4c5137593`;
- environment
  `c4b60a7988e31ab21d60958b7e3ef58279595b9f2ef53d1d4d794c316b6b9cc4`;
- comparison rule
  `88741cec6756392d5e8f892f8be8e6be299f55de1d6525dff08718eb19dedc4f`;
  and
- binding state `UNBOUND`.

This verifies the adapter's executable and fail-closed interface locally. It
does not close M149's separate-author review: the second `SEND BACK` has been
repaired and awaits re-attack. It also does not commission physical
extraction, physical nuisance allowances, or a claim-bearing M1 decision.

M138's own current adjudicator self-test also passed. Its independently
maintained consumer path reported `M135-null-state=INSTRUMENT_INVALID`,
`M135-valid-fail=REFUTED`, `M135-improvement-missing=RED`, and
`M135-unbound=BLOCKED`. That confirms the consumer preserves the adapter's
state distinctions; it is not a separate execution of M135's estimator.
