# M160 — durable capture-request citations

## Change

- Converted all six scorecard references in
  `docs/capture-requests/2026-09-319-frame-session.md` from mutable line ranges
  to named source structure.
- Citation convention:
  ``(`path.md`, "Section / Clause" clause)`` or
  ``(`path.md`, "Section" section)``.
- `verify_capture_request.py` now resolves the path literally, requires one
  named anchor, strips Markdown `>` prefixes per line, collapses whitespace,
  and requires the registered quotation to occur exactly once inside that
  anchored region. Each required citation is also bound to one unique nearby
  claim in the capture request, so swapping two valid citations cannot pass.
- Replaced `truth.holdout-lines-345-349` with the stronger
  `truth.holdout-content-anchor`, and `xref.ranges-in-bounds` with
  `xref.anchors-unique`. Added explicit M5 quotation checks, a ban on legacy
  line citations, and an aggregate substantive-content check.
- `xref.count` now enforces required semantic references as minima rather than
  an exact total. A seventh valid citation is accepted and checked.
- Added `--scorecard` so commissioning can mutate a source copy in
  `$env:TEMP`; `--commission` runs `nc_capreq.py`.

## Coverage

Before: **136 checks, RED (129 pass / 7 fail)**.

After: **141 checks, GREEN (141 pass / 0 fail / 0 skipped; accounted 141)**.
No check was dropped without a stronger replacement.

The pre-existing 47-line M5 addition was copied before editing. A byte-level
no-index diff from that copy to the final capture request shows exactly the six
citation-line substitutions and no substantive change. Its repository diff
moved from `47/0` to `51/4`, accounting for four replacements outside the new
section and two replacements inside it.

## Commissioning

`nc_capreq.py` ran every mutation on fresh copies below `$env:TEMP`. Every
anchor was a unique full line; a missing or duplicate anchor is a hard error.

| control | anchor found | exit code | expected check failed | verdict |
| --- | --- | ---: | --- | --- |
| arithmetic-block-count | yes | 1 | yes: `arith.physical.TC0-sw10-B`, `arith.physical-sum`, `arith.stated-total` | RED / PASS |
| arithmetic-stated-total | yes | 1 | yes: `arith.stated-total`, `arith.total-expression` | RED / PASS |
| stale-603-wrapped | yes | 1 | yes: `numbers.603-only-historical` | RED / PASS |
| stale-duration-budget | yes | 1 | yes: `numbers.duration.bracket-frames` | RED / PASS |
| mwork-silent-default | yes | 1 | yes: `mwork.settings-placeholder`, `mwork.no-concrete-instruction` | RED / PASS |
| converter-every-frame-wrapped | yes | 1 | yes: `converter.no-all-frame-instruction`, `converter.keep-off-tc0` | RED / PASS |
| stop-banner-removed | yes | 1 | yes: `stop.exact-banner` | RED / PASS |
| stop-condition-softened | yes | 1 | yes: `stop.removal-condition`, `stop.not-softened` | RED / PASS |
| control-row-in-scored-table | yes | 1 | yes: `controls.no-scored-table-row`, `arith.physical-row-order`, `internal.no-unknown-block-identifiers` | RED / PASS |
| unknown-block-reference | yes | 1 | yes: `internal.no-unknown-block-identifiers` | RED / PASS |
| missing-block-purpose | yes | 1 | yes: `internal.all-block-purposes-present` | RED / PASS |
| inert-owner-metadata | yes | 0 | n/a; GREEN required | GREEN / PASS |
| missing-required-citation | yes | 1 | yes: `xref.count`, `xref.holdout-rule` | RED / PASS |
| legacy-line-citation | yes | 1 | yes: `xref.no-line-number-citations` | RED / PASS |
| nonliteral-citation-path | yes | 1 | yes: `xref.paths-resolve-literally` | RED / PASS |
| unknown-citation-anchor | yes | 1 | yes: `xref.anchors-unique` | RED / PASS |
| misbound-citation-count-preserved | yes | 1 | yes: `xref.citations-bound-to-claims`, `xref.commission-quote` | RED / PASS |
| commission-source-wording | yes | 1 | yes: `xref.commission-quote`, `xref.all-citations-substantive` | RED / PASS |
| commission-source-duplicate | yes | 1 | yes: `xref.commission-quote`, `xref.all-citations-substantive` | RED / PASS |
| frequency-source-wording | yes | 1 | yes: `xref.frequency-quote`, `xref.all-citations-substantive` | RED / PASS |
| holdout-source-wording | yes | 1 | yes: `truth.holdout-content-anchor`, `xref.holdout-rule`, `xref.all-citations-substantive` | RED / PASS |
| m5-wilson-source-wording | yes | 1 | yes: `xref.m5-wilson-quote`, `xref.all-citations-substantive` | RED / PASS |
| m5-input-source-wording | yes | 1 | yes: `xref.m5-eligibility-floor`, `xref.all-citations-substantive` | RED / PASS |
| blockquote-lines-benign | yes | 0 | n/a; GREEN required | GREEN / PASS |
| source-line-shift-benign | yes | 0 | n/a; GREEN required | GREEN / PASS |
| seventh-citation-benign | yes | 0 | n/a; GREEN required with `xref.count: citations=7` | GREEN / PASS |

Summary: **26/26 controls passed; 22/22 defects produced RED on their named
checks; 4/4 benign changes remained GREEN.**

## Outside-owned defects

None found.
