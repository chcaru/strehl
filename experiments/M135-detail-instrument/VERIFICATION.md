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

Status: **SELF-TESTED 25/25; PHYSICAL BINDING UNAVAILABLE; SEPARATE-AUTHOR
REVIEW PENDING**

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
passed the same 25 checks:

- one request emitted valid `DETAIL_PASS → true` and
  `DETAIL_FAIL → false` decisions;
- a flat detailed ROI and a missing-flat payload each emitted
  `INSTRUMENT_INVALID` with no Boolean;
- an unregistered capture emitted no Boolean;
- repeated evaluation and commissioning output was byte-identical;
- the physical null, pre-noise blur, and planted pre-noise optical improvement
  controls all moved in their registered directions;
- missing-flat and artifact-hash mutation controls both refused;
- wrong artifact hashes, supplied Booleans, and duplicate capture IDs exited
  nonzero with no standard output; and
- the unbound runtime exited nonzero with explicit `INSTRUMENT_UNBOUND` and no
  standard output.

`m138-adapter-verification.json` is the machine-readable 25/25 result;
`m138-adapter-verification-run2-failed.json` preserves the 24/25 run.
`m138-adapter-verification-run3-pre-bootstrap.json` preserves the
pre-bootstrap-hardening 25/25 run.
`m138-adapter-verification-run4-pre-source-loader.json` preserves the
pre-source-loader-hardening 25/25 run.
An immediate full replay reproduced the final verification artifact
byte-for-byte.
`m138-adapter-bootstrap-verification.json` records an additional 10/10
bootstrap test. It first built a timestamp-eligible poisoned `.pyc` and proved
that a conventional source loader executed its sentinel while the adapter
ignored it and emitted a valid description from the registered source. It then
replaced `comparison_checker.py` with a second sentinel under the stale bundle;
the adapter returned a machine-readable hash-mismatch refusal with empty
standard output, and that sentinel did not exist. The earlier 5/5
pre-source-loader artifact is also retained.
`m138-adapter-description.json` separately exercises production bundle and
environment verification and reports:

- adapter
  `6d4366533b2b12fc1e03c44d96faa1af3d7e89e6c6f35ed5420dd33b8e5e6290`;
- bundle
  `fa3f5135693766114aed6db58bfa74197236e5a51b454a421951f645cdcb27ea`;
- environment
  `c4b60a7988e31ab21d60958b7e3ef58279595b9f2ef53d1d4d794c316b6b9cc4`;
- comparison rule
  `88741cec6756392d5e8f892f8be8e6be299f55de1d6525dff08718eb19dedc4f`;
  and
- binding state `UNBOUND`.

This verifies the adapter's executable and fail-closed interface. It does not
constitute the rule-12 separate-author review and does not commission physical
extraction, physical nuisance allowances, or a claim-bearing M1 decision.

M138's own current adjudicator self-test also passed. Its independently
maintained consumer path reported `M135-null-state=INSTRUMENT_INVALID`,
`M135-valid-fail=REFUTED`, `M135-improvement-missing=RED`, and
`M135-unbound=BLOCKED`. That confirms the consumer preserves the adapter's
state distinctions; it is not a separate execution of M135's estimator.
