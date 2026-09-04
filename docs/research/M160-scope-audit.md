# M160 scope audit — independent review of `6b966d8c`

Status: **COMPLETE — SCOPE, FORK PROVENANCE, AND M8-O ACHIEVABILITY RECONCILED**

## M136 M8-O achievability correction

The v1.4 M8-O result did not show strehl failing a demanding but attainable
standard. The construction was impossible for every normalized-`u16`
implementation at `977,684` required census coordinates where
`lo - tolerance > 1`. The scorecard now carries this exact disposition:

> **M8-O v1.4 superseded figure:** `1.326144%` was read against the v1.4 bar, which has been shown impossible as written; see `docs/research/M136-m8o-bar.md` (commit `7befe55c`).

The M8 axis nevertheless remains **`FAIL`** on its own merits: M8-R is
`1.030569%` against an achievable exact-zero bar. The blocker table, metric card,
and results table now say that M8-R is the only produced-and-read score against an
achievable bar.

M8-O v1.5 remains `UNMEASURED`. Its replacement checker was corrected at
`e5489d64` but has not been independently recommissioned, so no candidate score
exists. The scorecard does not contain or promote the diagnostic Catmull-Rom count.
It does record the valid discriminating control from
`experiments/M136-m8o-bar/analysis.json`: clean bilinear is exactly
`0/74,173,536`, independently zero in R, G, and B. This demonstrates that the
repaired predicate has a clean pass construction while distinguishing the shipping
kernel; it is evidence about the bar, not a promoted candidate result.

`experiments/M160-scope-audit/verify_m136_m8o.py` reads M136 at `7befe55c`, M166
at `02014c6e`, the analysis artifact at `6712449e`, the corrected checker's commit
subject at `e5489d64`, and the accepted scorecard baseline at `7bee3738`.

```text
GROUP_SUM discrimination total=7 passed=7 failed=0
GROUP_SUM integrity total=48 passed=48 failed=0
GROUP_SUM m8 total=16 passed=16 failed=0
GROUP_SUM source total=11 passed=11 failed=0
SUMMARY total=82 passed=82 failed=0 skipped=0 accounted=82
VERDICT GREEN
```

Only scorecard sections 3, 4, and 6 changed. Every other top-level section is
byte-identical to `7bee3738`; every non-M8 metric card and result row is
byte-identical; M8-R's definition is byte-identical; all twelve fork blocker cells
remain; and the F4/F14 joint row still occurs exactly once with `Q_flat<=1.00`.

| Control | Anchor found | Exit | Expected named result | Result |
| --- | --- | ---: | --- | --- |
| soften-m8-axis-verdict | yes | 1 | RED `m8.axis-fail` | PASS |
| make-readiness-v15-pass | yes | 1 | RED `m8.v15-unmeasured-readiness` | PASS |
| make-result-v15-fail | yes | 1 | RED `m8.v15-unmeasured-result` | PASS |
| restore-v14-failure | yes | 1 | RED `m8.superseded-line` | PASS |
| claim-v15-recommissioned | yes | 1 | RED `m8.v15-unmeasured-card` | PASS |
| promote-diagnostic-count | yes | 1 | RED `m8.no-diagnostic-count` | PASS |
| break-bilinear-zero | yes | 1 | RED `m8.bilinear-zero-card` | PASS |
| erase-channel-independence | yes | 1 | RED `m8.bilinear-channels-card` | PASS |
| restore-only-axis-claim | yes | 1 | RED `m8.only-r-produced-read-card`, `m8.no-old-only-axis-claim` | PASS |
| erase-impossibility-population | yes | 1 | RED `m8.v14-impossibility-count` | PASS |
| status-reflow-benign | yes | 0 | GREEN | PASS |
| bilinear-reflow-benign | yes | 0 | GREEN | PASS |

Result: **12/12 controls passed: 10 named RED controls and two benign GREEN
controls.**

## M162 fork-provenance correction

M162 establishes that the archived fork result is a byte-pinned output, not a
reproducible build. It consumed `105` Lightroom-developed TIFFs; no producing source
revision or executable is cryptographically bound to it; the retained May 17
executable postdates the render by six days and is not its producer. The fork and
strehl repositories also have unrelated histories, so no cross-project bisect exists
(`docs/research/M162-noise-regression.md`, "Correction to the premise" and
"DELIVER-V6 ground truth" clauses).

The scorecard now applies that provenance:

- The archived output is labelled **HISTORICAL /
  `PRODUCT_NATIVE_END_TO_END` DIAGNOSTIC ONLY**. It is inadmissible for common merge
  and does not satisfy the current product-native scoring contract.
- The required fork comparator is a fresh rebuild from the best-known retained source
  revision, pinned by commit before scoring. Its source tree,
  toolchain/dependency lock, compiler flags, executable SHA-256, settings, and exact
  common-input TIFFs are frozen before rendering.
- The first retained commit,
  `4bc7f95e448cf20ee2bdd758403ec43e2612a1c6`, is recorded only as proof that a source
  pin exists; the scorecard does not claim it builds.
- Every one of the twelve fork result cells now reads
  **`UNMEASURED — blocker (d)`**. The status clears only after the commit-pinned
  rebuild exists, its executable hash is frozen before rendering, and it consumes
  the exact common-input TIFF bytes.
- M159's `1.515208x` / `0 of 12` comparison is retained as an adverse historical
  product-native diagnostic, never promoted into a common-merge comparator value.

`experiments/M160-scope-audit/verify_m162_fork.py` reads M162's source evidence from
commit `ed5fa20b` and independently compares the `7648d360` scorecard blob with the
corrected result at `7bee3738`. The verifier and its controls now default to that
immutable result so the accepted checkpoint remains reproducible after M136:

```text
GROUP_SUM fork total=8 passed=8 failed=0
GROUP_SUM integrity total=46 passed=46 failed=0
GROUP_SUM position total=2 passed=2 failed=0
GROUP_SUM rebuild total=13 passed=13 failed=0
GROUP_SUM source total=6 passed=6 failed=0
GROUP_SUM table total=8 passed=8 failed=0
SUMMARY total=83 passed=83 failed=0 skipped=0 accounted=83
VERDICT GREEN
```

Its integrity checks keep all twelve at-a-glance rows and all twelve metric-card
success blocks unchanged, preserve every non-fork scoreboard field except M2's
required provenance qualification, and leave sections 2 and 5 byte-identical. M8
remained `FAIL` at that checkpoint. M136 now supersedes the M8-O v1.4 figure;
M8-R remains `FAIL` at `1.030569%` against its achievable `0.0000%` bar. The
F4/F14 joint row still occurs exactly once with `Q_flat<=1.00` intact.

| Control | Anchor found | Exit | Expected named result | Result |
| --- | --- | ---: | --- | --- |
| admit-archive-to-common-merge | yes | 1 | RED `fork.archive-common-inadmissible` | PASS |
| drop-source-commit-pin | yes | 1 | RED `fork.rebuild-required-set` | PASS |
| freeze-executable-after-render | yes | 1 | RED `fork.rebuild-executable-pre-frozen` | PASS |
| blank-one-fork-cell | yes | 1 | RED `fork.column-status-count`, `fork.column-no-blank` | PASS |
| erase-developed-input-defect | yes | 1 | RED `fork.archive-developed-input` | PASS |
| claim-bound-producer | yes | 1 | RED `fork.archive-no-bound-producer` | PASS |
| mark-fork-cell-pass | yes | 1 | RED `fork.column-status-count`, `fork.column-status-token` | PASS |
| erase-m8-fail | yes | 1 | RED `integrity.m8-fail` | PASS |
| lower-m2-bar | yes | 1 | RED `integrity.m2-glance-row` | PASS |
| commit-pin-reflow-benign | yes | 0 | GREEN | PASS |
| archive-reason-reflow-benign | yes | 0 | GREEN | PASS |

Result: **11/11 controls passed: nine named RED controls and two benign GREEN
controls.**

## F5/F6/F14 follow-on reconciliation

### F5 — two non-spliceable tracks

The scorecard now defines two frozen contracts:

- **Common merge** is the sole evidence path for the owner's SOTA sentence and all
  seven publication gates. Strehl, licensed Zerene PMax, licensed Zerene DMap, and
  a fresh commit-pinned rebuild of the best-known retained fork source receive
  byte-identical linear TIFFs; Helicon receives the same bytes when obtainable.
- **Product native** starts from one frozen ARW manifest, lets each arm use its
  frozen native stack path, and is labelled `PRODUCT_NATIVE_END_TO_END`. It must be
  reported honestly and in full, but it cannot establish a competitive detail,
  noise, clipping, or colour win or satisfy, rescue, veto, or alter an owner gate.

Every result names its track, and no value, setting, or verdict may be spliced
between them. M11's unchanged native CPU, hybrid, cold, live, and baseline bars
remain product evidence; only the common-merge `>=2.00x` result and its retained
cross-worker identity component gate publication. Full M12 remains a registered
product-native disclosure, so it enters only all-axis measurement accounting and
the `PASS` / `DISCLOSURE MISS` split, never an owner gate.

### F6 — conditional high-frequency admission

The permanent ban above `0.25 cyc/native px` is replaced by a conditional gate. A
claim requires input-verified real contrast, an independently commissioned
scene/alias/interpolation/sharpening/noise discriminator, and a stated physical
optical/sampling ceiling. Commissioning must contain all three directions: a
planted improvement that is rewarded, an untuned null that is not rewarded, and a
planted degradation that is penalized.

No licensed high-frequency instrument exists in v1.7. Consequently every current
above-`0.25 cyc/native px` reading remains `UNLICENSED_GT_0.25`; M1 and M9 remain
`UNMEASURED`. This changes future eligibility, not a present result.

### F14 — independent M2 verdict and honest present status

M2 is renamed **flat/defocused-ground noise**. M2, M4, and M8 retain independent
axis verdicts: an M4 or M8 failure is published beside M2 but does not convert M2
to `FAIL` or `UNMEASURED`, while an M2 pass excuses neither failure and licenses no
detail claim. The already accepted same-output median-`Q_flat<=1.00` guard remains
only as the narrow M4-derived anti-cheat component of the owner's M1/M2/M8 gate.

The rename does not manufacture an instrument or a pass. M2 remains
**INSTRUMENT VOID / UNMEASURED**. The scorecard preserves M159's adverse
product-native diagnostic: DELIVER-V6 is `1.515208x` the historical archived fork
output's fractional box9 residual, with `0 of 12` sites below one, while blur improves
the existing statistic to `0.571215x`. That archived output is not an admissible
common-merge arm. The `98%` natural-detail qualification also remains unchanged.

### F4/F14 overlap

F4 and F14 targeted the same joint row. Commit `513ea3fe` had already replaced that
row for the retained M4 anti-cheat ruling, so M158's shared replacement was not
applied a second time and was not copied verbatim. The row was merged once: F14's
independent M2/M4/M8 verdict language was added without discarding the accepted
same-output `Q_flat` guard. The verifier requires exactly one merged row.

### Forward verification

`experiments/M160-scope-audit/verify_f5_f6_f14.py` reads the `513ea3fe` baseline
and an optional committed result as raw `git show` bytes, decodes UTF-8 itself, and
compares wrapped prose after per-line blockquote stripping and whitespace
normalisation. Its result is:

```text
GROUP_SUM frequency total=16 passed=16 failed=0
GROUP_SUM integrity total=36 passed=36 failed=0
GROUP_SUM m2 total=24 passed=24 failed=0
GROUP_SUM source total=6 passed=6 failed=0
GROUP_SUM track total=26 passed=26 failed=0
SUMMARY total=108 passed=108 failed=0 skipped=0 accounted=108
VERDICT GREEN
```

The integrity group independently compares the two scorecard blobs. Changed
top-level sections are exactly 0, 1, 3, 4, 6, 7, and 8; sections 2 and 5 are
byte-identical. Every pre-existing results-table `FAIL` row remains byte-identical,
all twelve at-a-glance rows and all twelve detailed success blocks retain their
baseline numeric tokens, and M8 remains `FAIL` at M8-R `1.030569%` and M8-O
`1.326144%` against exactly `0.0000%` at that historical checkpoint. M136 now
supersedes only the M8-O v1.4 classification; M8-R remains the current
`1.030569%` failure against an achievable exact-zero bar.

The historical reconciliation verifier and controls now default to the immutable
`513ea3fe` blob, so their accepted 51-check / 12-control result remains reproducible
after this follow-on amendment. The F5/F6/F14 verifier and controls likewise default
to immutable commit `7648d360`, preserving their 108-check / 12-control result after
the later M162 correction.

### Commissioning

Every mutation uses a unique exact full-line anchor, hard-errors unless it occurs
once, verifies that the candidate differs, and runs only on a UTF-8 copy below
`%TEMP%`.

| Control | Anchor found | Exit | Expected named result | Result |
| --- | --- | ---: | --- | --- |
| product-native-satisfies-sota | yes | 1 | RED `track.sota-common-only` | PASS |
| high-frequency-without-instrument | yes | 1 | RED `frequency.unlicensed-stays-unlicensed` | PASS |
| m4-m8-converts-m2 | yes | 1 | RED `m2.disposition-independent` | PASS |
| delete-improvement-control | yes | 1 | RED `frequency.improvement-control` | PASS |
| allow-cross-track-splicing | yes | 1 | RED `track.scope-no-splicing` | PASS |
| erase-m2-instrument-void | yes | 1 | RED `m2.instrument-void-card` | PASS |
| hide-adverse-m2-reading | yes | 1 | RED `m2.adverse-residual` | PASS |
| drop-retained-qflat | yes | 1 | RED `m2.disposition-qflat` | PASS |
| erase-m8-fail | yes | 1 | RED `integrity.m8-fail` | PASS |
| lower-m2-bar | yes | 1 | RED `m2.target` | PASS |
| scope-reflow-benign | yes | 0 | GREEN | PASS |
| frequency-reflow-benign | yes | 0 | GREEN | PASS |

Result: **12/12 controls passed: 10 named RED controls and two benign GREEN
controls.**

### Judgment

I found no evidence that any ruling is wrong. I did find and correct one wording
collision while applying F5: saying that no product-native result could alter any
top-level verdict contradicted the already accepted requirement to measure full M12
as a product-native mandatory disclosure. The operative text now states the narrower
and consistent rule: product-native evidence can never affect an **owner gate**;
registered full-M12 evidence affects only disclosure completeness and the clean-pass
versus `DISCLOSURE MISS` distinction. That is bookkeeping required by the earlier
gate/disclosure decision, not a relaxation or a new gate.

## Reconciliation applied

The scorecard now implements the owner's three decisions in operative text rather
than only in amendment prose.

### Publication states

- The owner gates are exactly `M1`, `M2`, `M3`, `M8`, `M9`, `M10`, and `M11`.
- `M4`, `M5`, `M6`, `M7`, and `M12` are mandatory disclosures. Every one must be
  measured and published, and every miss must be stated prominently.
- `PASS — SOTA under scorecard v1.7` is reserved for a clean result: all seven owner
  gates pass, including their two retained anti-cheat components, and all five
  disclosure axes pass.
- `DISCLOSURE MISS — owner's seven-axis SOTA claim supported` is the distinct state
  for seven passing owner gates plus a full-axis disclosure miss. It is explicitly
  neither `PASS` nor `FAIL`, and its headline must name every miss, value, and bar.
- `FAIL` is limited to a missed owner gate or retained anti-cheat component.
- `UNMEASURED` applies when required evidence is incomplete. All twelve axes remain
  mandatory measurements; optional Helicon absence or invalidity is non-fatal.

### Retained anti-cheat components

The full M4 and M12 axes remain disclosures. Two narrower components protect claims
the owner actually made:

1. The same output bytes and settings used for M1/M2/M8 must have median
   `Q_flat<=1.00`. M4's failed-site, ghost-ratio, and comparator bars do not gate the
   owner's verdict.
2. The fixed-width outputs at 1/2/4/8/16 workers must be mutually byte-identical, and
   the 16-worker output must meet M11. M12's fixed-worker-repeat, memory, N-scaling,
   and N-mod-4 bars do not gate the owner's verdict.

The document now states why this split is necessary: dropping the components permits
a named claim to be bought by a cheat, while retaining either full axis contradicts
the seven-axis scope.

### Comparator contract

The required comparator set is now consistently:

- licensed Zerene Stacker PMax;
- licensed Zerene Stacker DMap;
- a fresh fork rebuild from the best-known retained source revision, pinned by
  commit before scoring, with its executable hash frozen before rendering.

The fork settings entry requires its source commit, source-tree hash, toolchain and
dependency lock, compiler flags, binary SHA-256, and complete frozen settings
manifest. M162 subsequently proved that the old archived output cannot fill this
arm; its developed input and unbound producer make it historical/product-native-only
diagnostic evidence. The common-input rule, readiness blocker, speed qualification,
results schema, and public sentence all require the fresh rebuild. Helicon is
qualified `when obtainable` throughout operative text; its absence or invalidity is
recorded and excluded rather than made fatal.

### Forward verification

`experiments/M160-scope-audit/verify_reconciliation.py` reads the predecessor and
reconciled scorecard blobs as bytes through `git show` and decodes UTF-8 itself when
run with `--after-rev`. Its reconciled result is:

```text
CHECKS total=51 passed=51 failed=0 skipped=0 accounted=51
GROUP source total=3 passed=3 failed=0
GROUP gate total=13 passed=13 failed=0
GROUP anti total=11 passed=11 failed=0
GROUP comparator total=15 passed=15 failed=0
GROUP integrity total=9 passed=9 failed=0
VERDICT GREEN
```

The integrity group confirms:

- changed top-level sections are exactly 0, 1, 3, 4, 6, 7, and 8;
- the preamble and sections 2 and 5 are byte-identical;
- §§1.1, 1.3, 1.5, 1.6, and 3.2 are byte-identical;
- the complete M1, M2, M3, M9, and M10 cards are byte-identical;
- all twelve at-a-glance registered-bar rows and all twelve detailed `Success`
  blocks are byte-identical;
- every pre-existing scoreboard value and standing is preserved while the fork
  column is added; and
- At that historical checkpoint M8 remained `FAIL` on M8-R `1.030569%` and M8-O
  `1.326144%` against `0.0000%`. M136 now supersedes the M8-O v1.4 figure while
  leaving the M8-R failure intact.

### Reconciliation commissioning

All mutations use unique exact full-line anchors, hard-error unless the anchor occurs
exactly once, verify that the candidate differs from the baseline, and run only on
UTF-8 copies below `%TEMP%`.

| Control | Anchor found | Expected result | Result |
| --- | --- | --- | --- |
| remandate-unnamed-axis | yes | RED `gate.disclosure-split` | PASS |
| delete-m4-anti-cheat-component | yes | RED `anti.m4-flat-power-component` | PASS |
| delete-m12-anti-cheat-component | yes | RED `anti.m12-cross-worker-component` | PASS |
| drop-fork-from-common-input | yes | RED `comparator.common-input-required-set` | PASS |
| make-helicon-mandatory | yes | RED `gate.helicon-not-unmeasured` | PASS |
| drop-fork-binary-hash | yes | RED `comparator.fork-freeze-protocol` | PASS |
| drop-fork-scoreboard-column | yes | RED `comparator.scoreboard-schema` | PASS |
| collapse-disclosure-miss-into-pass | yes | RED `gate.disclosure-miss-distinct` | PASS |
| retract-m8-fail | yes | RED `integrity.m8-fail-preserved` | PASS |
| lower-m2-comparator-bar | yes | RED `integrity.at-glance-bars-unchanged` | PASS |
| benign-required-set-rewrap | yes | GREEN | PASS |
| benign-disclosure-role-paragraph-break | yes | GREEN | PASS |

Result: **12/12 controls passed: 10 named RED controls and 2 benign GREEN
controls.**

### Judgment check

I found no evidence that any of the three decisions is wrong. The required
clarification was not a fourth decision: a disclosure axis must be measured before a
run verdict can issue, but a measured disclosure miss changes the verdict to
`DISCLOSURE MISS` rather than negating the owner's sentence. This preserves mandatory
measurement without silently restoring the five full axes as owner gates.

The remainder of this report records the independent audit of predecessor commit
`6b966d8c` that motivated the reconciliation.

## Verdicts

| Claim | Verdict | Basis |
| --- | --- | --- |
| A — seven axes, five unnamed | **CONFIRMED** | The plan's printable sentence contains six top-level clauses and seven distinct axis predicates because its compound output clause names both certificate calibration and physical depth. |
| B — Helicon optional; Zerene-only purchase; fork required | **CONFIRMED** | The plan says `Helicon if obtainable`, pins the fork at its best-known build, and gives the owner only a Zerene purchase at Prosumer/Professional prices. |
| C — no bar or FAIL weakened beyond the stated scope change | **CONFIRMED** | Only sections 0 and 8 changed; the pre-existing decision rules and sections 1–7 are byte-identical; section 8 is append-only; the M8 row is unchanged and remains FAIL at M8-R `1.030569%`. |
| D — amended scorecard internally consistent | **REFUTED** | Fourteen operative checks still encode all-primary/all-quality gating or a mandatory Zerene+Helicon comparator set that omits the newly required fork. |

The independent checker reports:

```text
CHECKS total=36 passed=22 failed=14 skipped=0 accounted=36
CLAIM A CONFIRMED
CLAIM B CONFIRMED
CLAIM C CONFIRMED
CLAIM D REFUTED
AUDIT_VERDICT REFUTED
```

## Method

`experiments/M160-scope-audit/verify_scope_audit.py` reads the plan directly.
It reads the parent and target scorecard blobs as bytes via `git show`, decodes
UTF-8 itself, and compares content by named sections and unique single-line
anchors. Wrapped quotations are compared after stripping Markdown blockquote
prefixes per line and collapsing whitespace.

The withdrawn mandatory-Helicon wording occurs exactly once in the amended
scorecard, inside the amendment block and nowhere outside it. This is a
position-aware check, not a global presence/absence test.

## Claim A — clause enumeration

Source block anchor in `docs/proposals/2026-08-sota-path.md`:
`licensing instrument in parentheses:`.

| Predicate in the printable sentence | Named instrument | Axis | Confidence | Reason |
| --- | --- | --- | --- | --- |
| `resolves detail at or beyond the best shipping comparator` | `D1: FRC + slant-edge`, licensed Zerene PMax and DMap | M1 | High, 0.99 | M1 is sharpening-safe resolved information. |
| `at strictly lower noise` | `existing flat-ROI instrument` | M2 | High, 0.99 | M2 is noise efficiency. |
| `with zero invented structure` | `hull census, stamped per file` | M8 | High, 1.00 | M8 is explicitly the independent source-hull census. |
| `no occlusion veil above [bar]` | `halo instrument at full reach` | M3 | High, 0.99 | M3 is occlusion halo and broad veil. |
| `per-pixel certified acuity, n_eff` | D2 model channel plus D8 empirical channel | M9 | High, 0.98 | M9 is explicitly acuity / `n_eff` certificate calibration. |
| `depth in physical units` | A5 depth field plus C5 metric conversion | M10 | High, 0.98 | M10 is the physical-depth product. |
| `[X] s per frame on CPU` | `existing harness` | M11 | High, 1.00 | M11 is wall-clock throughput. |

The sentence contains no predicate for:

- M4 non-edge artifact rate. `zero invented structure` is disambiguated by its
  explicit `hull census` instrument, which is M8.
- M5 depth-of-field coverage. A5 contributes to the emitted depth product, but
  the sentence claims physical depth, not eligible-tile coverage or failed-run
  length.
- M6 highlight/shadow retention.
- M7 colour fidelity.
- M12 memory, determinism, or scaling invariance. The sentence names CPU
  seconds per frame, which is M11.

## Claim B — comparator and purchase source

The plan's D1 section is explicit:

- Anchor `speed quote against it), Helicon if obtainable. Every scorecard run archives hashes`
  makes Helicon optional.
- Anchor `the fork rebuilt at its best-known build (2.4× is the honest`
  makes the fork a pinned comparator.
- Anchor `pinned and priced: licensed Zerene (PMax *and* DMap — DMap has never rendered here and`
  requires both Zerene modes.

The owner's purchase list is equally explicit:

- Anchor `session has room. *Owner (purchase):* the Zerene licence — D1 is blocked on it and`
  names Zerene only.
- Anchor `we need, *Save Adjusted Input Images*, is licensed only to **Prosumer`
  and anchor `($189)** or **Professional ($289)**. This is an owner purchase, not a build.`
  establish the two price points.

The later plan shorthand `unavailable common-input Zerene/Helicon output`
describes the then-current scorecard blocker table, but the same amendment's
concrete purchase action remains Zerene-only. It does not override D1's
`Helicon if obtainable`.

## Claim C — amendment integrity

The parent is `c30c93b0`; the reviewed commit is `6b966d8c`.

- Top-level changed sections are exactly `0` and `8`.
- The complete text from anchor `### 0.1 Decision rule` through the start of
  section 8 is byte-identical before and after. No metric card, numeric bar,
  control, readiness row, or scoreboard row changed.
- Section 8's former content is an exact prefix of its amended content.
- Every pre-existing line containing `FAIL` remains.
- The M8 scoreboard row is byte-identical and still says
  ``**FAIL** — M8-R `1.030569%```.
- The old mandatory wording beginning
  `passes every primary bar below against licensed Zerene Stacker and Helicon Focus`
  occurs once, between the amendment anchor
  `> **AMENDMENT — publication scope corrected to the owner's sentence, and Helicon`
  and `### 0.1 Decision rule`; it occurs zero times outside that interval.

I found no easier metric threshold, erased failure, or changed axis result.
The only semantic relaxation in the diff is the stated publication-scope and
Helicon change.

## Claim D — contradictory operative text

These are not historical quotations. Each anchor occurs exactly once in
operative text.

### Publication scope still gates unnamed axes

1. Anchor:
   `1. Every primary metric is a hard gate. No win compensates for a loss.`

   All twelve rows are still labelled primary metrics, so this makes M4, M5,
   M6, M7 and M12 fatal despite the amendment.

2. Anchor:
   ``| M1 information + M2 noise + M4 flat power + M8 hull | Harder averaging can lower noise by losing information; sharpening can flatter transfer while increasing flat power or leaving the source hull. | M1 presently has no admissible statistic. When it is replaced, publish the replacement detail value with `(eta, Q_flat, M8-R, M8-O)` from the same output and pass every bar simultaneously. Until then neither a noise-only nor a detail claim is valid. |``

   This keeps the unnamed M4 bar as a prerequisite for the named M1, M2 and M8
   claims.

3. Anchor:
   `| M11 runtime + M12 determinism/scaling invariance/memory | Serial execution can make fixed-worker runs deterministic by abandoning the speed claim. | The primary CPU result is the 16-worker output; it must meet M11, reproduce at fixed width, and be byte-identical to 1/2/4/8-worker outputs while meeting M12. |`

   This keeps the unnamed M12 axis as a prerequisite for named M11.

4. Anchor:
   `is the fastest mode that passes the complete quality scorecard. This is intentionally`

   The comparator-speed definition still gates M11 on all quality axes.

5. Anchor:
   `7. Comparator speed uses the fastest mode that passes all quality gates at identical`

   M11's own computation repeats the same all-quality prerequisite.

6. Anchor:
   ``- `FAIL`, when any commissioned primary gate misses;``

   An M4/M5/M6/M7/M12 miss still forces the only `FAIL` verdict, contradicting
   the section 8 amendment's statement that such a miss does not determine the
   owner's verdict.

### Helicon remains mandatory and the fork remains unwired

7. Anchor:
   `   Zerene PMax, Zerene DMap, and Helicon Methods A, B, and C, each at its frozen`

   The operative comparator envelope includes Helicon without an optional
   qualifier and omits the required fork.

8. Anchor:
   `5. Zerene, Helicon, and strehl must receive the exact same TIFF bytes. A strehl TIFF`

   The common-input contract still requires Helicon and does not require the
   fork.

9. Anchor:
   `### 1.4 Comparator settings`

   This complete section has Zerene, Helicon and strehl bullets, but no fork
   bullet. The required fork therefore has no version, hash or frozen-setting
   protocol.

10. Anchor:
    `- **Helicon Focus:** licensed current shipping build; Methods A, B, and C at factory`

    The Helicon settings bullet has no `when obtainable` qualification.

11. Anchor:
    `exclude that mode. If either product cannot produce a linear output that passes §1.3,`

    In the two-product settings section, failure by either Zerene or Helicon
    leaves the named-comparator requirement unmet.

12. Anchor:
    `Zerene/Helicon output, and **(e)** scientifically measurable now. An **(e)** does not`

    Readiness blocker `(d)` still requires Zerene/Helicon and omits the required
    fork.

13. Anchor:
    `| ID | Metric | strehl | Zerene Stacker | Helicon Focus | Current standing |`

    The result schema has no column for the required fork and presents optional
    Helicon as the sole second comparator.

14. Anchor:
    `> **strehl’s competitive position against Zerene Stacker and Helicon Focus is`

    The only permitted public sentence omits the required fork and presents
    optional Helicon as part of the core comparator statement.

## Required reconciliation (applied)

The predecessor amendment could not be made internally consistent by one more
disclaimer. The reconciliation above applies these required changes:

1. Replace “every primary metric” and “any commissioned primary gate” with the
   explicit owner-required set M1, M2, M3, M8, M9, M10 and M11; retain the other
   five as mandatory disclosures.
2. Decide whether the M4 and M12 joint constraints are true anti-cheat
   components of named axes or independent axis prerequisites. If the former,
   state the narrower component requirement; if the latter, the amendment's
   seven-axis claim is false.
3. Replace the comparator set everywhere with licensed Zerene PMax/DMap plus a fresh
   rebuild of the best-known retained fork source, pinned by commit before scoring
   with its executable hash frozen before rendering, and qualify Helicon with `when
   obtainable`. M162 superseded the earlier "frozen best-known build" shorthand
   after proving that the archive has no bound producer.
4. Add separate comparator-settings entries for the required fresh best-known-source
   fork rebuild and the historical/product-native-only archive, plus a fork result
   column whose cells remain explicitly `UNMEASURED — blocker (d)` until the rebuild
   exists.
5. Change both speed-selection clauses from `complete/all quality scorecard`
   to the owner-required quality subset, while still publishing added-axis
   failures.
6. Rewrite the public unknown-position sentence around Zerene plus the required
   commit-pinned best-known-source fork rebuild; state its current `UNMEASURED`
   blocker, and mention the archived fork and optional Helicon separately.

## Why the predecessor author's verifier passed

`experiments/ORCH-verify/v-scope.ps1` reports 35/35 because it checks that the
new amendment says the intended things, not whether operative text elsewhere
still contradicts them.

Its position check is also incomplete. The unique anchor
`Chk 'old text sits INSIDE the amendment' (($amendIdx -ge 0) -and ($oldIdx -gt $amendIdx))`
tests only that the old wording occurs after the amendment starts; it never
checks that the occurrence precedes the amendment's end. The commissioned
counterexample moves the sole occurrence below `### 0.1 Decision rule`.
The author's verifier remains **35/35 GREEN** while the independent
`C.withdrawn-old-text-position` check turns RED.

`experiments/ORCH-verify/nc-scope.ps1` also accepts duplicate mutation anchors:
its unique anchor is
`if ($count -lt 1) { throw "MUTATION TARGET NOT FOUND: $($c.n) -- anchor '$($c.a)'" }`.
It should require `$count -eq 1`; `.Replace()` currently mutates every duplicate.

## Commissioning

All controls used fresh copies below `$env:TEMP`.

| Control | Anchor found | Expected transition | Result |
| --- | --- | --- | --- |
| plan-detail-instrument-wording | yes | `A.map-M1` PASS→FAIL | PASS |
| plan-helicon-made-mandatory | yes | `B.helicon-optional` PASS→FAIL | PASS |
| plan-purchase-adds-helicon | yes | `B.owner-purchase-zerene-only` PASS→FAIL | PASS |
| m8-fail-retracted | yes | both M8-preservation checks PASS→FAIL | PASS |
| withdrawn-wording-outside-block | yes | position check PASS→FAIL | PASS |
| author-position-counterexample | yes | independent position check FAIL; author verifier remains GREEN | PASS |
| repair-primary-gate-scope | yes | named D check FAIL→PASS | PASS |
| repair-required-fork-settings | yes | named D check FAIL→PASS | PASS |
| repair-helicon-optional-settings | yes | named D check FAIL→PASS | PASS |
| benign-scorecard-line-shift | yes | identical failure set | PASS |
| benign-plan-quote-rewrap | yes | identical failure set | PASS |

Result: **11/11 controls passed**.
