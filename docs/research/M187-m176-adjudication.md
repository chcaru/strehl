# M187 — independent adjudication of M176's worker-invariance claims

**Lane:** M187
**Date:** 2026-09-05
**Disposition:** both route claims are overclaims; the rewrite is an
unadjudicated silent drop.

## 1. Evidence contract

I re-derived the boundaries from Rust and the governing documents. I did not use
M176's account of itself as proof. Git-hosted text cited below was obtained as
bytes from `git show <revision>:<path>` and decoded as UTF-8; no shell redirection
or checkout representation was used as a Git-blob surrogate.

The committed M176 baseline is commit
`5270e0ee0a319e59f6efb90f9e7f27f3a4117bb3a`, whose LF-normalized report blob is
`d712f86ac912eddfbe4ed018787c54742b957e21`. The report presently in the working
tree is not committed: its clean-filter candidate object ID is
`8e70eab7b70d7dd8a944efa3a69ac4a77b8d050d`; its raw CRLF checkout hashes as Git
blob `10b5eb6962d6add147f4c36e7af9d5b7733db22e` and SHA-256
`3D7E71F1A67810CDD2967CB7CE1983FDE3F285E0F052C8CF6FC8A2C146052F88`.
The candidate audit is also uncommitted: its clean-filter candidate object ID is
`9381307d38dd8a629899bdb1bd047a49658a63fa`; its raw CRLF checkout hashes as Git
blob `010c940782e8496b9c7533a858acec2ab5f93216` and SHA-256
`AD689F6525CA046827292D08F0974FE0141516945A185CBA527C56C2127F5CCF`.
The committed audit at `HEAD` is instead blob
`918c31044fccf86016c20fe2ca5b720e9d30429c`. I quote neither audit as
authority.

Unless a different revision is written inline, governing-document citations
refer to evidence snapshot `2b14eb0399bbe682b4b83910f941ca5c63cf2a0d`:
`docs/STATUS.md` is LF blob
`c03b7f33287a1b99a73ffb91e20b2cc02c3c4b27`, the scorecard is LF blob
`908b21d8d01554c205b68711c80fe855466f0924`, and M172's closure report is LF
blob `f268c8e08fea8eae9c88001f133288c175aafc08`.

The current report candidate differs from the committed report by 86 inserted
lines and 431 deleted lines. All findings classified as absent in §5 were
checked against the whitespace-collapsed candidate text, not by single-line
grep.

## 2. Canonical rulings

**M187-R1 — UPHELD: the statement that every repository hash pin is conditioned on worker count is false; D9 can condition Pyramid final-render identities downstream of the merge reduction, but M8-R and M165 hash state upstream of that boundary.**

**M187-R2 — UPHELD: landing D9 does not retroactively make hash pins unconditional; an affected pin sheds its worker condition only inside a frozen D9 lineage covered by an accepted end-to-end certificate whose own gate has fired red on the unrepaired lineage.**

**M187-R3 — UPHELD: the current M176 rewrite removes prior findings without withdrawing or superseding them, and its bare notice that material was dropped does not satisfy the program's visible-retraction rule.**

Each sentence above is the sole canonical site for its ruling.

## 3. Route 1 — the Rust boundary

### 3.1 M8-R is before merge accumulation

At M8's source revision `76b3d9cc8b5185735d6c19d4339ce74d29e333e2`,
the Catmull-Rom loop calls `sample_checked` into `scratch.dst`
(`crates/strehl-cli/src/align_cmd.rs:2108-2120`). Inverse white-balance gain does
not begin until `:2122-2125`, and conversion to rounded/clamped integer output
begins at `:2127-2133`.

The committed injector uses `let inv = 1.0 / gain[ci]` as its exact anchor and
replaces it with the trace call followed by the same inverse-gain line, thereby
placing `trace_site(..., &scratch.dst)` after the gather
(`experiments/M8-overshoot/inject_trace.py:15-30`). The trace serializer writes
the source sample set and gathered floating-point result
(`experiments/M8-overshoot/m8_trace.rs:116-122`). Thus the M8-R hash sees the
gathered `f32` value before inverse gain, integer rounding, frame accumulation,
partial-merge absorption, and final rendering.

The production call chain confirms the separation. A frame is fully decoded and
warped by `load_frame` before `add_frame_with_gain` is invoked
(`fc2abb49:crates/strehl-cli/src/merge_cmd.rs:4829-4885`). Therefore no choice
made later by the D9 reduction can flow backward into the M8-R trace.

### 3.2 M165 is an input identity, not an output identity

At M165's source revision `6e50d201001748bf64c3ccc46046860ab31e0c3d`,
`strehl-common-input` reads and verifies the TIFF, constructs the exact
merge-facing planes, and hashes them before any optional core-merge exercise
(`crates/strehl-cli/src/bin/strehl-common-input.rs:45-58`). The implementation
hashes the whole file and TIFF payload
(`crates/strehl-raw/src/common_tiff.rs:323-325,341-345`), decoded `u16` samples
and merge-facing floating-point planes (`:380-432`).

The optional smoke merge later calls one-frame `add_frame` and `finish`, but it
checks only geometry and finiteness; it never hashes that rendered result
(`crates/strehl-cli/src/bin/strehl-common-input.rs:135-159`). M165's pins
therefore cannot depend on the CLI's multi-part reduction order.

### 3.3 What D9 actually changes

Before D9, `STREHL_PYRAMID_WORKERS` selected a worker-sized `per_chunk`;
`par_chunks(per_chunk)` produced partial `BandWorker`s that were then absorbed
(`1a6fd10c:crates/strehl-cli/src/merge_cmd.rs:5786-5842`). The merge arithmetic
itself warns that SoftPower sums are mathematically associative but not
bit-associative (`fc2abb49:crates/strehl-core/src/pyramid.rs:1936-1946`).

D9 makes the arithmetic grouping canonical for a fixed build and input (the
19-frame control's lattice is `[5, 5, 5, 4]`), lets Rayon schedule those fixed
groups, collects indexed results, and absorbs them left-to-right
(`fc2abb49:crates/strehl-cli/src/merge_cmd.rs:5468-5491,5802-5866`). The final
render follows `finish` at `:5950-5952`.

The sound scope is consequently narrow: worker provenance is required for
Pyramid final-render byte/hash claims made by a pre-D9 executable, or by a D9
executable not yet certified end to end. It is not a blanket property of hashes
whose bytes were fixed before `add_frame_with_gain` or of unrelated input
identities.

## 4. Route 2 — certificate and retirement rule

The scorecard defines the registered certificate, not the existence of a source
patch:

- M12-D requires “exactly one distinct hash in every fixed-worker six-run cell,”
  while M12-S requires “exactly one distinct hash across all five worker counts
  at every N” (`docs/proposals/2026-09-sota-scorecard.md:2016-2029`).
- The registered run covers N=33/105/299 and workers 1/2/4/8/16, with one
  warm-up and six alternating-order scored repetitions per cell
  (`:2056-2062`).
- The common-merge outputs must agree in both complete-file and canonical
  decoded-pixel SHA-256 identity (`:2181-2184`).
- The repaired observations must come from one hash-bound binary. M172 states
  that its evidence covers only N33, one run per worker, and that the registered
  certificate still requires every worker at every registered N from one
  hash-bound repaired binary
  (`docs/research/M172-m12s-closure.md:121-137`).

M172's committed N33 evidence is strong but deliberately narrower than the
certificate: its final pixel identity is
`6EFC261E892DCDB5D492AD3FD79BDC7E5A208D93D0227A41B258FB3B900F9B89`,
its final TIFF identity is
`9CCF896743B08E68AB08E4437EC4E3EAF2AAD8D37884170E95067577C80286B5`,
and its pre-quantization identity is
`A38952442C2F4FF206A49DBE75808717`
(`docs/research/M172-m12s-closure.md:71-83`).

N7 adds a causal qualification: “a repair may not be cashed on the sub-property
it repairs until the certifying test has been seen to go **red** on the
unrepaired artifact” (`docs/STATUS.md:8025-8028`). The certificate must
therefore bind the repaired executable and its D9 ancestry, cover the full
registered output matrix and both identity representations, and use the same
certifying gate that rejected a genuinely unrepaired executable.

Nothing in that rule rewrites history. The program separately records that
evidence collected from different binaries cannot be combined into a score
(`docs/STATUS.md:7493-7501`) and that a previously ungrounded number “does not
become grounded retroactively because a different number later landed nearby”
(`:8021-8023`). A pre-D9 render pin remains a fact about the producing
executable. A later certificate may establish a new unconditional pin for its
own frozen lineage; it cannot repair provenance that the old pin never had.

## 5. Route 3 — findings deleted rather than retracted

`git log --follow -- docs/research/M176-worker-invariance.md` yields one
committed version, the baseline identified in §1. Comparing that blob with the
current uncommitted candidate establishes the following complete claim-level
drop inventory. Repeated summaries in the old §§8 and 10 are not counted twice;
every distinct old finding absent from the candidate appears below.

1. **M187-DP01 — headline result and causal classification.** The earlier report
   said the mechanism was independently reproduced, localized to dynamic
   Rayon-sized chunking plus ordered fold, and classified as a false-difference
   source rather than algorithmic nondeterminism
   (`5270e0ee:docs/research/M176-worker-invariance.md:3-10`).
2. **M187-DP02 — lineage and isolation.** It bound the examined source commit,
   executable, dirty-tree paths, replacement instrument, and isolation from the
   earlier M139 executable (`:33-52`).
3. **M187-DP03 — independent-run integrity.** It recorded a fresh execution,
   no reuse of M139 output, and read-only input integrity findings (`:54-67`).
4. **M187-DP04 — treatment and render settings.** It defined the single-factor
   five-arm treatment, recorded why the bounded W3 fallback did not run, and
   bound the exact rendering controls held constant (`:71-84`).
5. **M187-DP05 — complete output matrix.** It published the five-arm output-hash
   table and distinguished output identity from log identity (`:86-100`).
6. **M187-DP06 — magnitude, spatial distribution, and independent decoding.**
   It reported 3,430 changed pixels out of 8,241,504 (`0.041619%`), 3,437
   changed channel samples split 1,855/791/791 across R/G/B, a -1/+1 histogram
   of 1,657/1,780, a maximum magnitude of one 16-bit code
   (`1/65535 = 1.5259021896696422e-05` of full scale), a maximum per-sample
   relative difference of `1/176 = 0.005681818181818182`, inclusive bounding
   box `[1,0,3515,2343]`, 2,642 changed pixels at least 256 pixels from an edge,
   and agreement between `tifffile` and OpenCV on `2344 x 3516 x 3` `uint16`
   geometry (`:104-125`).
7. **M187-DP07 — mechanism and preregistered falsifiers.** It tied the effect to
   floating-point regrouping in worker-sized partial merges and recorded the
   falsifiers that did not fire (`:129-160`).
8. **M187-DP08 — audit population and coverage.** It bound a prior current-text
   population of 30 exactly-once high-stakes IDs, an 82-file material
   inventory, and 92 exact evidence anchors across 63 Git blobs. Its
   fixed-revision resweep found 142 candidate paths, classified 37 as material
   and 105 with explicit dispositions, and described the inventory as the union
   of 63 cited and 19 additional paths. The exact search forms, path classes,
   exclusions, candidate mapping, and line-ending-invariant report/audit result
   were part of that finding (`:164-173,227-257`).
9. **M187-DP09 — rows omitted wholesale.** The rewrite drops the old rulings for
   M8-O v1.4, FINALPASS-CACHE, M162, the unsealed paths, WARP M117, and the M172
   unit-test claim (`:184,194-195,202,216,218`).
10. **M187-DP10 — detail stripped from retained rows.** It removes the old
    group-membership and pin details for the shipping freeze and grouped
    comparisons; DELIVER's seven-file observation; the exact metadata-equal
    pixel count; V-ENVSURF's frame-order mechanism; M-PHASE0-SPLIT's retained
    KILL/STOP/REMOVE verdict; ORCH's 26-file observation and mixed-binary
    limitation; the baseline's missing canonical hash/lattice fields; M139's
    N299 qualification; M8-R's governing measured failure value; M165's
    campaign/opaque-use limitations; the limits on generalizing Estimator
    results; and M164's future-manifest requirements
    (`:184-225`).
11. **M187-DP11 — false-difference and false-agreement conclusions.** It removes
    the confirmed worker-caused M-COVER-BORDER false difference, the general
    distinction between exact equality and a cross-worker counterfactual, the
    finding that equal unrecorded-worker hashes cannot prove reproducibility,
    the finding that no independent treatment cancellation was measured, and
    the separate stale-cache false-agreement channel (`:261-277`).
12. **M187-DP12 — shipping-default, estimator, and unit-boundary findings.** It
    removes the implementation-level finding that the shipping Pyramid default
    uses a deterministic canonical-lattice resolver rather than machine
    parallelism, the separate nonshipping Estimator dependence on
    `available_parallelism()`, the distinct roles of the Pyramid and Rayon
    environment controls, the absence of a `strehl stack --workers` flag, and
    the limit that M172's unit/resolver checks were not a final-output ladder
    (`:281-322`).
13. **M187-DP13 — normative provenance contract.** It removes the proposed
    fail-closed render-identity contract, its requested/resolved worker,
    versioned-lattice, file-hash, and pixel-hash fields, and its explicit
    applicability and non-applicability boundaries (`:326-342`).
14. **M187-DP14 — verification, commissioning, and evidence bindings.** It
    removes the prior result of 33 checks split into 21 reproduction, one
    source-binding, and 11 claim-audit checks; the 56-invocation commission
    result, including 24/24 technical kills, 28/28 claim-audit kills, 1/1 EOL
    kill, 53/53 substantive kills, and a surviving 1/1 inert control; the
    mutation-specific red/error findings; six evidence-file SHA-256 bindings
    and the commission's self-excluding binding; and the limitations that no
    build, render, wall-time measurement, protected-path write, or capture
    access occurred (`:364-425`).
15. **M187-DP15 — end-to-end scope limit.** It removes the measurement-specific
    conclusion that M176's repaired control covered only W1/W2 on one 19-frame
    input, not the registered full final-output campaign, and that M172's unit
    checks did not fill that gap (`:456-461`).

The candidate's replacement-history note acknowledges that reproduction and
localization were removed (current uncommitted checkout, line 116, raw
representation identified in §1), but it neither declares those findings false
nor supplies superseding evidence. Program policy is explicit: a false claim is
“withdrawn visibly rather than deleted,” because silent removal erases the fact
that anyone was misled (`docs/STATUS.md:5301-5303`). A rewrite may condense or
supersede findings only if it preserves a visible disposition and provenance;
it may not convert live claims into absence.

## 6. Exact STATUS replacements

These quotations and counts cover LF Git blob
`c03b7f33287a1b99a73ffb91e20b2cc02c3c4b27` at
`2b14eb0399bbe682b4b83910f941ca5c63cf2a0d`. The raw CRLF checkout of the same
clean content hashes as Git blob `3ab29749a7c02e21c0c24ab39c01d0c9c5b14a26`
and SHA-256
`8F5340E3BCE286520F09053D9B33A5E395F4C3411189EC9A1EE7EF41D5697F68`.

### 6.1 Route 1

**Anchor:** `**Every hash pin in this repository is therefore`
**Occurrences in the cited current STATUS blob:** 1

**Current text, verbatim:**

> **Every hash pin in this repository is therefore
> conditioned on a worker count that was, in most cases, never recorded** — the
> common-input byte-identity check, the dominance manifest, the shipping-default
> byte-freeze, the dust-correction "a wrong map renders byte-identical to OFF"
> downside bound.

**Replacement, verbatim:**

> **Only Pyramid final-render byte/hash claims from pre-D9 executables—or from D9 executables not yet covered by an accepted end-to-end certificate—require a common-worker condition.** M8-R and M165 stop before that boundary, M8-O v1.5 is unmeasured, and M164 has no candidate render. The shipping Scale + Catmull-Rom freeze remains a recorded W=4 witness; V-MOTE's WRONGMAP/OFF identity is conditional because its worker count was not recorded.

### 6.2 Route 2

**Anchor:** `repairs one of M12's two bars and simultaneously makes every hash pin in the`
**Occurrences in the cited current STATUS blob:** 1

**Current text, verbatim:**

> Landing it
> repairs one of M12's two bars and simultaneously makes every hash pin in the
> repository unconditional.

**Replacement, verbatim:**

> Landing D9 does not by itself make any hash pin unconditional. For an affected Pyramid final-render pin, the same-worker condition retires only for a frozen executable lineage proven to contain D9 by an accepted, N7-qualified end-to-end certificate covering the registered worker/N matrix with complete-file and canonical decoded-pixel identity. Historical pre-D9 hashes are not repaired retroactively; non-render hashes were never conditioned on D9.
