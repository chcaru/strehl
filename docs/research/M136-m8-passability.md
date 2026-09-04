# M136 — M8 passability after the clamped Catmull-Rom landing

**INFERRED BY READING — RULING:** `M8 PASSABLE BUT ILLEGITIMATE` **at
present**: M172's exact
same-support clamp makes M8-R integer zero a mathematical consequence, but
promoting that opt-in nonlinear limiter to the shipping default solely to turn
the failed axis green is not licensed by the available product-quality evidence.
M8 also lacks a scoreable M8-O v1.5 target census, a scoreable identity result,
and a verifier that satisfies the required single-read rule.

**INFERRED BY READING — scope:** This is a ruling about the evidence now
available. It does not say that a
clamped default can never be legitimate. It says that the current repository
has not earned that product decision, and an opt-in result cannot be reported as
the shipping default's score.

## 1. Evidence boundary and identities

**VERIFIED BY RUNNING:** The historical result and its producer are unchanged
from evidence commit
`76b3d9cc8b5185735d6c19d4339ce74d29e333e2`:

| Evidence | Immutable identity |
|---|---|
| `experiments/M8-overshoot/results.json` | git blob `f5287faa0d830eff2d6e9ebffb6d32f1cd3a05c0`; raw SHA-256 `D310ABB387A7EE7F9F9C4BB5A4484ACE8A864F34E4C90EE026BFA97AC5236241` |
| `experiments/M8-overshoot/run.ps1` | git blob `e3036876269dc53867a33c774738835880ec18d6` |
| `experiments/M8-overshoot/checker.py` | git blob `dc1b931cabaaf42a1356e875f9fd4f148fde5dd3` |
| `experiments/M8-overshoot/summarize.py` | git blob `7336e00621df310bc4d277ae894618866106b33d` |

**VERIFIED BY RUNNING:** `391cdd33` resolves to
`391cdd33bd2defcd6562b0df64f1a67740d26409`. A path-scoped
`git diff --quiet 391cdd33..HEAD` returned clean for the six production source
files changed by M172. This report therefore reads the landed implementation,
not a later transcription. The relevant blobs at `391cdd33` are:

| File | git blob |
|---|---|
| `crates/strehl-core/src/align.rs` | `806f6226eb3f28d220ac0e1c071df56a30e57730` |
| `crates/strehl-core/src/restore.rs` | `38180c50757334b46bedf75b476f31ee522624de` |
| `crates/strehl-core/src/warpmap.rs` | `908b97b85ab154f926f35a8a38fc3a008b4ce30e` |
| `crates/strehl-cli/src/align_cmd.rs` | `be3de1abe67dfe7fd57c134e648b6161342c112e` |
| `crates/strehl-cli/src/main.rs` | `4ab4005ff79f78774e197ec224a7797fb96523d7` |
| `crates/strehl-cli/src/merge_cmd.rs` | `081406ae3de079820eb4e134594cd75e72f187fd` |

**VERIFIED BY RUNNING:** The scorecard bytes read here have git blob
`819215ff3673d8a53a6264886f1bdd8328178a5d` and raw SHA-256
`D72160F57494ED1B3A07807EA0D7D6451B5E50D4630E0E6EEB093CED7D74CB28`.

## 2. The current M8-R number

### 2.1 What the artifact says

**VERIFIED BY RUNNING:** I parsed the integer fields in
`experiments/M8-overshoot/results.json:15-24`, rather than copying the rounded
scorecard text:

```text
V = 63,191,176
N = 6,131,678,976
V/N = 7,898,897 / 766,459,872
100*V/N = 1.030568890630715...%
```

**VERIFIED BY RUNNING:** The displayed `1.030569%` is correct rounding. The split is
`32,634,423` lower and `30,556,753` upper violations, which sums exactly to
`63,191,176`.

### 2.2 What produced it

**INFERRED BY READING:** The historical runner copied the then-current workspace
into a private source snapshot, injected a value-only trace hook, and built the
instrumented CLI (`experiments/M8-overshoot/run.ps1:105-124`). It generated
Catmull-Rom maps explicitly
(`experiments/M8-overshoot/run.ps1:127-142`) and rendered the three
development flat stacks through Pyramid, `cover=scale`
(`experiments/M8-overshoot/run.ps1:144-175`,
`experiments/M8-overshoot/run.ps1:224-229`).

**INFERRED BY READING:** The independent checker reconstructed source support
from the source planes and placements; the summarizer then required the exact
frame/site counts, no coordinate-validity mismatch, no unconsumed block, and
manifest row counts equal to the reported violation count
(`experiments/M8-overshoot/summarize.py:37-89`). It summed integer counts across
the three arms (`experiments/M8-overshoot/summarize.py:124-154`,
`experiments/M8-overshoot/summarize.py:211-248`) only after
requiring commissioning and checker independence
(`experiments/M8-overshoot/summarize.py:159-179`,
`experiments/M8-overshoot/summarize.py:250-310`).

**INFERRED BY READING:** The commissioning was bidirectional enough to establish
that the historical checker was live: Catmull hard step `28/252`, explicit
high/low plant `2/252`, copy `0/252`, and bilinear `0/300`
(`experiments/M8-overshoot/results.json:27-61`).

### 2.3 Current or stale?

**INFERRED BY READING:** It is the **current admitted M8-R score** because the
governing scorecard still names it as the reason M8 remains `FAIL` and calls it
the only produced-and-read score against an achievable bar
(`docs/proposals/2026-09-sota-scorecard.md:1512-1516`).

**INFERRED BY READING:** It is **stale as a measurement of M172 or current
HEAD**. It measured the historical Scale/Catmull candidate, not commit
`391cdd33`, and no M172 binary/trace/census is bound into that artifact. The
shipping defaults still select ordinary Catmull-Rom
(`crates/strehl-cli/src/align_cmd.rs:50-59`) and Scale
(`crates/strehl-cli/src/align_cmd.rs:978-1008`), so the failed mechanism remains
on the default path; that does not make the old percentage a fresh HEAD
measurement.

## 3. Does M172 force M8-R to integer zero?

### 3.1 Proof

**INFERRED BY READING:** Yes, for every admitted finite source support, if the
trace records the value M172 actually returns.

**INFERRED BY READING:** M172 evaluates ordinary Catmull-Rom in the same
operation order while collecting
the minimum and maximum of the exact 16 consumed source taps. It returns `lo`
for a NaN accumulator, `lo` below the hull, `hi` above it, and the unchanged
accumulator otherwise
(`crates/strehl-core/src/align.rs:2694-2754`). Its dispatch selects that function
for `Resampler::ClampedCatmullRom`; its support is exactly Catmull-Rom's `2.0`,
and `sample_checked` applies the same valid-domain predicate
(`crates/strehl-core/src/align.rs:2894-2950`).

**INFERRED BY READING:** This is the same hull the prepared M142 checker tests:
it independently accepts coordinates from `1.5` through `width/height-2.5`,
applies the same floor rule, and reduces the `(-1,0,1,2) x
(-1,0,1,2)` source rectangle
(`experiments/M142-m8o-execute/checker_m136.py:2667-2694`). It does not compare
the gather to a different merge-stage or all-frame hull.

**INFERRED BY READING:** The scorecard's phrase “pre-merge and pre-clamp”
cannot license tracing M172's hidden raw cubic accumulator while the merge
consumes its clamped return value. The same sentence requires the **actual
gathered value**, and a clamp constitutive of the registered resampler defines
that value. “Pre-clamp” distinguishes the gather from later pedestal,
container, or output-rail clamps
(`docs/research/M136-m8-census-groundtruth.md:100-105`). Instrumentation that
records the raw accumulator but sends the clamped value to the merge, or the
reverse, is a mismatched trace and makes the run `UNMEASURED`.

**INFERRED BY READING:** Let the checker reconstruct the same finite support
`S={s_1,...,s_16}`, with `lo=min(S)`, `hi=max(S)`. M172 returns

```text
r = lo                  if the cubic accumulator is NaN or below lo
    hi                  if the cubic accumulator is above hi
    cubic accumulator   otherwise
```

**INFERRED BY READING:** Therefore `lo <= r <= hi`. M8-R counts only
`r < lo - tau_R` or `r > hi + tau_R`, and `tau_R >= 0`
(`docs/proposals/2026-09-sota-scorecard.md:1462-1478`). Neither predicate can
be true. The integer violation count is therefore exactly zero, not merely a
small expected rate.

**INFERRED BY READING:** The merge, Pyramid reconstruction, output gain,
quantisation, and serialization cannot add an M8-R violation because M8-R's
observed value is the actual per-frame gather at the pre-merge boundary
(`docs/proposals/2026-09-sota-scorecard.md:1462-1466`). They can affect M8-O,
which is why this proof does not prove the axis.

### 3.2 Executed checks

**VERIFIED BY RUNNING:** In an isolated
`experiments/M136-m8-passability/target`, using `--locked --offline`, the
following landed tests passed:

- four `clamped_catmull_rom` core tests: exact `4x4` hull containment,
  bit-identity while ordinary Catmull-Rom is already in hull, exact
  integer/constant identity, and unchanged support/checked domain
  (`crates/strehl-core/src/align.rs:3605-3736`);
- the widened-clamp negative control, which restores violations and therefore
  proves the containment guard can fail
  (`crates/strehl-core/src/align.rs:3738-3763`);
- the core and CLI fail-closed restoration tests
  (`crates/strehl-core/src/restore.rs:122-136`,
  `crates/strehl-core/src/restore.rs:839-862`,
  `crates/strehl-cli/src/merge_cmd.rs:2441-2445`,
  `crates/strehl-cli/src/merge_cmd.rs:7655-7664`);
- the resampler-name round trip, including `clamped-catmull`
  (`crates/strehl-core/src/warpmap.rs:957-987`);
- the CLI default guard, which still resolves to ordinary Catmull-Rom
  (`crates/strehl-cli/src/align_cmd.rs:2664-2684`).

**VERIFIED BY RUNNING:** The command results were nine passing tests, zero
failures. The isolated target directory was removed after the checks; no build
output is part of this report.

**VERIFIED BY RUNNING — corroboration, not a M172 score:** I reparsed the three
existing M134 clamped-census files. They contain
`0/1,977,960,960`, `0/2,010,926,976`, and `0/2,142,791,040`, with zero coverage
mismatches, for exactly `0/6,131,678,976`. Their SHA-256 values remain
`7FBCCC57...CC3F7`, `5BE981BA...BD59`, and `E4425625...23C70`, as recorded in
`docs/research/M136-m8-census-groundtruth.md:26-31` and
`docs/research/M136-m8-census-groundtruth.md:107-120`.

**VERIFIED BY RUNNING:** A repository search under `docs/` and `experiments/`
for the short or full `391cdd33` commit identity, excluding this report and
build-target directories, found no result artifact naming that candidate.

**COULD NOT VERIFY:** No frozen M8-R census produced by a binary built from
`391cdd33` exists in the evidence handed to M136. The proof determines what a
correctly bound census must read; the targeted tests and M134 artifacts
corroborate it. They do not substitute for source/binary/trace binding on the
scored commit.

## 4. Is adopting the clamp legitimate?

### 4.1 The strongest case that it is legitimate

**INFERRED BY READING:** Changing implementation after a failed metric is not,
by itself, moving the goalposts. The M8-R population, source support, tolerance,
denominator rule, and exact-zero threshold would remain unchanged. M172 changes
the operation that violated the preregistered invariant and leaves already
in-hull Catmull-Rom values bit-identical. That is the normal shape of fixing a
failed regression test, not weakening one.

**INFERRED BY READING:** The proposed counterfactual — “would it have been
chosen if M8 did not exist?” — is useful against Goodharting but too strict as a
general rule. A valid instrument is supposed to reveal defects and influence
engineering. The better test is:

> With the numerical score hidden, does the intervention directly satisfy the
> predeclared semantic requirement, preserve the measured population, survive
> controls that distinguish it from a no-op or a destructive substitute, and
> have its product costs accepted on independent evidence?

**INFERRED BY READING:** M172 clears the first three parts for M8-R. Its mechanism is exactly local
source-hull containment; it does not shrink support or validity; and the
in-hull, widened-clamp, registration, and restoration controls discriminate it.

### 4.2 The strongest case that it is not legitimate now

**INFERRED BY READING:** The fourth part — independent acceptance of product
costs — is not met.

1. M172 deliberately landed the kernel **opt-in**. The default constant remains
   `"catmull-rom"` (`crates/strehl-cli/src/align_cmd.rs:50-59`), and the CLI
   describes clamped Catmull-Rom as a nonlinear, content-dependent limiter that
   can flatten extrema or alter harmonics
   (`crates/strehl-cli/src/main.rs:682-700`).
2. Restoration refuses it because there is no shift-invariant MTF to invert
   (`crates/strehl-core/src/restore.rs:122-136`). A default flip therefore also
   changes which product features are admissible.
3. The apparent evidence that clamping retained `99.7587%` of Catmull-Rom
   “detail” failed its flat-ROI null. Flat regions showed a slightly larger
   Catmull-over-bilinear band gap than detailed regions, so the report withdrew
   the resolved-detail interpretation
   (`experiments/M134-kernel-frontier/M137-clamped-detail.md:200-290`).
4. The repository's prospective kernel-decision precedent says a kernel metric
   alone cannot license a default, and later suspended a GO when the motivating
   benefit was withdrawn
   (`docs/research/ORCH-kernel-decision.md:100-139`,
   `docs/research/ORCH-kernel-decision.md:214-252`).
5. The scorecard itself names destructive clipping as a known way to buy zero
   and limits a current M8 pass to the internal invariant while independent
   detail/transfer controls are absent
   (`docs/proposals/2026-09-sota-scorecard.md:1564-1582`).

### 4.3 Ruling

**INFERRED BY READING — ruling:** A default change now, justified only by
M8-R becoming zero, would be **metric gaming and an unearned product pass**. It
would not literally move the bar; it would move the product into a
metric-enforcing mode whose independent quality case has not been established.
That distinction matters: the census could be numerically true while the claim
that this is the shipping product's justified default would be false.

**INFERRED BY READING:** A future pass can become legitimate in either of two
ways:

1. an independent, prospectively governed product decision establishes that
   clamped Catmull-Rom is the preferred default after accounting for spatial
   fidelity and loss of restoration; or
2. the owner explicitly elevates same-support hull containment to a
   non-negotiable product invariant, accepts the documented quality/function
   trade, and makes that policy prospective rather than presenting M8 alone as
   evidence of overall quality.

**INFERRED BY READING:** Only after one of those decisions may a
shipping-default clamped run score M8.
Leaving the kernel opt-in is a valid product outcome, but its zero would license
only that opt-in configuration.

### 4.4 What a pass licenses

| State | Legitimate licence |
|---|---|
| Historical/default Catmull-Rom M8-R failure | No claim that every gathered sample remains in its exact source-support hull. |
| Opt-in clamped M8-R zero | The named opt-in gather enforces same-support scalar containment. It says nothing about the shipping default. |
| Shipping-default clamped M8-R zero, without M8-O | The default gather enforces the local scalar invariant. It does not license a final-output or whole-axis claim. |
| Full M8 pass | On the frozen scored candidate and population: every eligible per-frame gather is inside its reconstructed support hull, every final serialized code is inside the representable all-frame output hull, and the crop/reference identity arm is exact within the registered tolerances. |

**INFERRED BY READING:** No M8 pass licenses preserved resolved detail,
perceptual superiority, restored-kernel equivalence, or SOTA. The scorecard says
that explicitly while M1 is absent
(`docs/proposals/2026-09-sota-scorecard.md:1573-1582`).

## 5. Why M8 does not pass now

**INFERRED BY READING:** The following gates are conjunctive.

### 5.1 Scored configuration

**INFERRED BY READING — BLOCKED:** The scorecard requires strehl's shipping
default at the scored commit, with no experimental quality flags
(`docs/proposals/2026-09-sota-scorecard.md:468-469`). Current defaults are
Pyramid, Scale, ordinary Catmull-Rom, and — on matching registered gear —
lateral-CA correction on
(`crates/strehl-cli/src/merge_cmd.rs:433-438`,
`crates/strehl-cli/src/align_cmd.rs:978-1008`,
`crates/strehl-cli/src/align_cmd.rs:50-59`,
`crates/strehl-cli/src/merge_cmd.rs:5482-5518`).

**INFERRED BY READING — BLOCKED:** The current M142 target command instead
forces Pyramid, Crop, clamped Catmull-Rom, and `--fix-ca off`
(`experiments/M142-m8o-execute/run-clamped-m8o.ps1:942-952`). Thus even a clean
M142 development result would not certify the present shipping default. A
scoreable campaign must use one exact default configuration; it may not splice
M8-R from Scale/Catmull, M8-O from Crop/clamped/no-CA, and identity from another
arm.

### 5.2 M8-R

**INFERRED BY READING — MATHEMATICALLY CLOSED, FORMALLY UNMEASURED:** M172's
implementation forces `V_R=0` by the proof in §3, but a formal score still
requires the complete trace population from the exact scored binary, the
independently reconstructed support/validity, and integer-zero counts per
capture and aggregate. No such M172 artifact has been produced.

### 5.3 M8-O v1.5

**INFERRED BY READING — UNMEASURED:** M8-O is not implied by M8-R. It compares
the final serialized output after the declared intermediate integer,
black/pedestal, gain, merge, projection, and quantisation path
(`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:71-87`).
The preregistered rule is `V=0` for every capture and aggregate; one violation
fails
(`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:88-104`). No
target v1.5 census exists.

### 5.4 Crop/reference identity

**INFERRED BY READING — UNMEASURED FOR THE NEW CANDIDATE:** The combined
decision independently requires crop/reference identity `V=0`
(`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:88-104`). Historical
identity controls and unit tests do not bind this arm to the scored M172 binary.

### 5.5 Population

**INFERRED BY READING — NOT YET SCORED:** The three flat stacks are the
development commissioning population; M8's scorecard input is every scored
quality capture
(`docs/proposals/2026-09-sota-scorecard.md:1456-1460`). The preregistration
itself says a flat-corpus pass does not replace the later score on every scored
quality capture
(`experiments/M136-m8o-bar/clamped-m8o-preregistration.json:88-104`).
A development-flat zero can establish achievability and commission the
instrument. It cannot alone establish the axis pass.

### 5.6 Current M142 freeze

**VERIFIED BY RUNNING — NOT FROZEN:** At inspection, the top-level M142 output
contained only `source-manifest.json`, `source-patch.json`,
`source-snapshot/`, and `patched-snapshot/`. There was no build receipt, test
receipt, commissioning directory, instrument freeze, target capture, verifier
report, or summary.

**VERIFIED BY RUNNING:** The prepared source patch has SHA-256
`01D85CE5C8757F1CC551BE64E4E5175435BB38D39687B52A6F385E29BE0F685A`
and records base commit
`248178b921f98ec1f13ea4c07d30fa68ace787a0`
(`experiments/M142-m8o-execute/out/source-patch.json:137-151`). The runner
requires that old commit
(`experiments/M142-m8o-execute/run-clamped-m8o.ps1:17-21`).
Exact git-blob comparison found that all six overlapping production files in
that private patched candidate differ from M172's `391cdd33` files. A future
M142 result under the current freeze would certify its private candidate, not
the landed M172 implementation.

### 5.7 Commissioning status

**VERIFIED BY RUNNING — CORRECTION TO THE SCORECARD:** The statement that the
corrected M136 verifier “has not been independently recommissioned”
(`docs/proposals/2026-09-sota-scorecard.md:1548-1557`) is stale.
`experiments/M136-m8o-bar/verifier-recommission-e5489d64-result.json:1-12`
records `PASS`, exit `0`, and commission SHA-256
`5FEC854466CC31C215458C16C9868EBFDE6A46E05D1839EE85FB3BD15EDA9865`;
the recommission was committed at `9dbfedbd`.

**INFERRED BY READING:** That correction does not create a target score. M142
must still freshly commission its checker/fixture, bind that commissioning into
the freeze, and run the target. Any verifier change made to close §5.8 must
itself be recommissioned again before target evidence is accepted.

### 5.8 Single-read / TOCTOU

**VERIFIED BY RUNNING:** The current verifier has raw SHA-256
`2AA3789060D9885A63EC9DF16CC8933492466185EF549241F69BA852A85CC9F7`.

**INFERRED BY READING — HARD VERDICT GATE:** It hashes paths and later reopens
them. `frozen_file` retains a path and digest
(`experiments/M136-m8o-bar/verifier_m136.py:350-445`); JSON consumers reopen
the path (`experiments/M136-m8o-bar/verifier_m136.py:1414-1418`); and
`parse_trace` hashes and closes a trace before later path-based header reads and
memory maps (`experiments/M136-m8o-bar/verifier_m136.py:334-349`,
`experiments/M136-m8o-bar/verifier_m136.py:458-524`). A transient
substitution followed by restoration can therefore feed bytes other than the
bytes whose digest was approved. End-of-run rehashing does not close that gap.

**INFERRED BY READING:** No M8 verdict may be promoted through this verifier
unchanged. Metadata must be
hashed and parsed from the same in-memory bytes; large traces must be parsed
from the same sealed handle or immutable snapshot that was hashed. This is not
an advisory hardening item: it gates the verdict under the assigned verification
standard.

## 6. Complete path to a defensible M8 PASS

**INFERRED BY READING:** All of the following are required:

1. **Legitimate product decision.** Select a scored shipping-default
   configuration on independent product grounds. An opt-in flag is not the
   default.
2. **Prospective configuration registration.** Register the active default
   cover, resampler, CA behavior, backend, and numeric path before reading any
   target output. If the default remains Scale, the current Crop-specific M142
   target protocol must be revised prospectively and recommissioned; the
   crop/reference identity arm remains a separate mandatory control.
3. **Exact source/build binding.** Freeze the full scored commit, source tree,
   lockfile/toolchain, deterministic environment, instrumentation-only patch,
   reproducible build, candidate executable, maps, and capture identities.
4. **Single-read verifier repair.** Close §5.8, commission both directions, and
   freeze the repaired verifier before target bytes are opened.
5. **Live commissioning.** Require Catmull and explicit high/low defects to go
   red; copy, clamped-copy, convex bilinear, and correct-rail cases to go green;
   widened-clamp and one-code-off-rail plants to go red. Every source mutation
   must match one unique full line or hard-error.
6. **Complete trace census.** Require every expected frame/site exactly once,
   independently reconstruct validity/support/crop, reject any missing or
   duplicate block, and use at least 64-bit integer aggregation.
7. **M8-R integer zero.** `V_R(c)=0` for every scored capture and
   `sum_c V_R(c)=0`. A formatted `0.0000%` with nonzero `V_R` fails.
8. **M8-O v1.5 integer zero.** `V_O(c)=0` for every scored capture and
   `sum_c V_O(c)=0`, using the exact representable-domain interval path and
   fixed `q=1/131070`. A nonzero floor is forbidden.
9. **Identity integer zero.** The separately registered crop/reference copy arm
   has `V=0`, with independently reconciled crop origin and dimensions.
10. **Mandatory disclosures.** Keep every eligible rail coordinate in the
    denominator and report high/low, at-rail/off-rail excursions separately;
    report exact per-capture and aggregate denominators and every violation.
11. **One-run provenance.** The same frozen binary and configuration must
    produce the values entering M8-R, M8-O, and the TIFF. No cross-arm or
    cross-commit splice is admissible.
12. **Full score population.** After development commissioning, run every
    frozen scored quality capture. Flat-only success is not a score.
13. **Independent promotion.** M136, or another non-author verifier, must
    generatively recompute the verdict from sealed evidence. Artifact
    consistency alone is insufficient.

**INFERRED BY READING:** The axis passes only under the conjunction:

```text
all scored captures: V_R = 0 and V_O = 0
aggregate:           V_R = 0 and V_O = 0
identity arm:        V = 0
all provenance, population, commissioning and single-read gates: PASS
```

## 7. Who must run what

**INFERRED BY READING:** M142 owns the freeze/census runner. M136 must not run or
edit that lane's apparatus. After the product decision, scored commit, target
configuration, population, and single-read verifier are resolved, M142 must run
the following sequence against the **same full commit**:

```powershell
$Commit = '<full scored shipping-default commit>'
powershell -NoProfile -ExecutionPolicy Bypass -File .\experiments\M142-m8o-execute\run-clamped-m8o.ps1 -Mode Prepare -SourceCommit $Commit
powershell -NoProfile -ExecutionPolicy Bypass -File .\experiments\M142-m8o-execute\run-clamped-m8o.ps1 -Mode Commission -SourceCommit $Commit
powershell -NoProfile -ExecutionPolicy Bypass -File .\experiments\M142-m8o-execute\run-clamped-m8o.ps1 -Mode Freeze -SourceCommit $Commit
powershell -NoProfile -ExecutionPolicy Bypass -File .\experiments\M142-m8o-execute\run-clamped-m8o.ps1 -Mode Census -Capture All -SourceCommit $Commit
powershell -NoProfile -ExecutionPolicy Bypass -File .\experiments\M142-m8o-execute\run-clamped-m8o.ps1 -Mode Verify -SourceCommit $Commit
powershell -NoProfile -ExecutionPolicy Bypass -File .\experiments\M142-m8o-execute\run-clamped-m8o.ps1 -Mode Summarize -SourceCommit $Commit
```

**INFERRED BY READING:** Those commands are not ready to run as written today:
the runner rejects commits other than `248178b9`, targets a private patched
candidate, uses a non-default configuration, and covers only the development
flat set. Running it now would create diagnostic evidence, not an M8 score.

## 8. Exact owner-facing scorecard correction

**INFERRED BY READING:** Replace the stale status paragraph at
`docs/proposals/2026-09-sota-scorecard.md:1548-1557` with:

> **Status: `UNMEASURED` for M8-O v1.5; the M8 axis remains `FAIL` on
> M8-R.** The corrected M136 verifier was independently recommissioned PASS at
> `9dbfedbd`, with `verifier-commission.json` SHA-256
> `5FEC854466CC31C215458C16C9868EBFDE6A46E05D1839EE85FB3BD15EDA9865`.
> No frozen target v1.5 census exists. M142 has not completed a
> Prepare→Commission→Freeze→Census→Verify→Summarize campaign for a scored
> shipping-default commit, and verifier SHA-256
> `2AA3789060D9885A63EC9DF16CC8933492466185EF549241F69BA852A85CC9F7`
> reopens hash-checked paths. That single-read/TOCTOU defect blocks promotion
> until it is repaired and the repaired verifier is recommissioned. The admitted
> M8-R result remains `63,191,176 / 6,131,678,976 = 1.030569%`; it is the
> governing score but not a fresh measurement of M172.

## 9. Final answer

**INFERRED BY READING:** M172 answers the narrow technical question: an exact
M8-R zero is achievable without changing M8-R's bar, support, validity, or
denominator rule. The existing M134 artifacts show the expected integer zero,
and M172's landed implementation makes that outcome a proof obligation rather
than a statistical hope.

**INFERRED BY READING:** M8 nevertheless does not pass now. The shipping
default still fails on the admitted historical result; the clamped kernel is
opt-in; its promotion lacks independent product-quality license; M8-O v1.5,
identity, and the scored capture population are unmeasured; M142 is not frozen
to M172 or to the default configuration; and the independent verifier's
single-read defect is a hard promotion blocker.
