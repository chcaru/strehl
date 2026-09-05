# M176 — Pyramid worker invariance: reproduced mechanism, bounded blast radius

**VERDICT — MEASURED / VERIFIED:** historical Pyramid output is
worker-dependent because the requested worker count changed the logical frame
partition and therefore the order of `f32` reductions.  On the affected source,
W=1 versus W=2 changes 3,430 of 8,241,504 pixels (0.041619%), always by at most
1 DN16; a W=1 repeat is byte-identical.  On the fixed control, W=1 and W=2 are
byte-identical because both use the canonical `[5,5,5,4]` lattice.  This is
quantization-visible floating-point non-associativity, not a structural
merge-decision difference.

**VERDICT — DERIVED FROM THE REVISION-BOUND AUDIT:** the repository-wide claim
that every hash pin was conditional is false.  The historical M139 cross-worker
FAIL, pre-merge checks, estimator-era results, the M117 warp-cache clearance,
and explicitly common-worker scientific A/B conclusions survive.  Absolute
Pyramid hashes without common worker/lattice provenance remain conditional.
M-COVER-BORDER is the one confirmed worker-caused false difference.
V-ENVSURF's equal N=3 W=3/W=1 outputs are a confirmed false-agreement surface
if generalized: equality survives as an observation but is not worker
invariance.  No cancellation of an independent scientific treatment by worker
rounding was measured.  Unsealed stale-render reuse remains a separate material
false-agreement channel.

The technical reproduction is in
`experiments/M176-worker-invariance/out/analysis.json` under `images`,
`comparisons`, and `mechanism_verdict`.  The complete machine-readable blast
audit is `out/claim-audit.json`, especially `claims`,
`material_file_inventory`, `revision_search`, `checkout_stability`,
`status_replacement`, and `uncertainties`.

## 1. Independent reproduction and lineage

**VERIFIED:** the historical affected source
`1a6fd10c94dcb4b780f6af78c46c62a156c39b71` is the sole parent of repair
commit `fc2abb499126a56302de7f21f527de5613be34e7`.  Fixed control
`a97275817c58e164f75c7cd3d80ca99444a2a145` contains that repair.  These
relations are retained in `out/lineage.json` under `repair_parent` and
`repair_is_ancestor_of_fixed`, and are independently rechecked by
`verify.py`'s `git-lineage-identifies-affected-and-fixed` check.

The parent is the exact pre-repair boundary.  With source, input, argv, and all
non-worker environment held fixed, it differs across W=1/W=2 and repeats at
W=1; the fixed descendant is equal across the same W=1/W=2 treatment.  The
source-bound excerpts then identify the changed operation: worker-sized
`par_chunks` in the affected source versus worker-independent canonical chunks
and ordered `absorb` in the fixed source
(`out/source-evidence.json`, `excerpts.affected_*`, `excerpts.fixed_*`, and
`chunking`).  That parent/fixed contrast isolates reduction topology rather
than merely correlating a changed binary with a changed image.  The fixed
control also contains the memory-bounding follow-up, so this report does not
claim that the two binaries differ by only one commit; the matched behavioral
contrast plus the source-anchored topology change is the isolation.

**VERIFIED:** no M139 output artifact was inspected or reused.  The technical
reproduction used only the committed report's lineage statement; the blast
audit separately read the committed report and no artifact.  The reproduction
used fresh, separate source archives, targets, binaries, output paths, and run
records;
`out/provenance.json` records `no_m139_artifact_consumed: true`, while
`out/builds.json` binds both source trees and binary SHA-256 values.

**MEASURED:** the input was the 19-frame development/non-holdout
`coffee-bubbles` stack.  Its read-only recursive before/after manifest remained
identical at SHA-256
`80c16282d9be43a3b3deae5f36141af8bc503717711589ce082888db17eded09`
(`out/input-before.json`, `out/input-after.json`, and
`out/provenance.json`'s `input_manifest_*`).  No holdout was consumed.

## 2. Arms, settings, and raw output hashes

The only behavioral arm variable was `STREHL_PYRAMID_WORKERS`; W=1, W=2, and
the W=1 repeat used the affected binary, then W=1/W=2 used the fixed binary.
`RAYON_NUM_THREADS=2` was common.  No W=3 fallback ran because the affected
W=1/W=2 canonical pixel hashes already differed
(`out/runs.json`, `fallback_w3_used` and `runs[].renderer_environment`).

**VERIFIED settings:** 19 frames; `--merge pyramid`; seven bands; gate `2.0`;
exponent `2.0`; sharpen-per-octave `1.4`; SoftPower selection; plain-mean base;
linear-sRGB, binned RGB16 output; Scale coverage; Catmull-Rom resampling;
alignment off; defect correction off; lateral-CA correction off; restoration
off; halo correction off; input-range hull; significance and weighted coarse
mean both zero; highlight knee `0.60`.  The exact argv and complete renderer
environment are bound in `preregistration.json` under `render` and
`renderer_environment`, and in `out/runs.json` under each `runs[]` record.

**MEASURED raw output hashes** (`out/analysis.json`, `images`; full 64-hex
digests):

| arm | source | W | whole output TIFF SHA-256 | canonical decoded-pixel SHA-256 |
|---|---|---:|---|---|
| affected W1 | `1a6fd10c94dcb4b780f6af78c46c62a156c39b71` | 1 | `cdfc0c589eac96b6c394c9e295d0e25921bf3d625e2d17914cd79369b1cd8c57` | `e4733757eef94b7442f243c805bb624619a28103aad682fef562b2d5221c6a82` |
| affected W2 | `1a6fd10c94dcb4b780f6af78c46c62a156c39b71` | 2 | `1824bde27c5b709600eb8b38a8a2b5796a7b09fb43a69382e3e2714615ffb258` | `ccbcda05920c0d44b4f45c548bea643e905cc927ff5791b68dea38987c0868da` |
| affected W1 repeat | `1a6fd10c94dcb4b780f6af78c46c62a156c39b71` | 1 | `cdfc0c589eac96b6c394c9e295d0e25921bf3d625e2d17914cd79369b1cd8c57` | `e4733757eef94b7442f243c805bb624619a28103aad682fef562b2d5221c6a82` |
| fixed W1 | `a97275817c58e164f75c7cd3d80ca99444a2a145` | 1 | `af6c282e9214d72cd0135b5b7f4a5a6958330910e5bd3a146aa8855ffc7850e3` | `92ff913ee211d74ee5d8dead15ddb4709a9a8ecf49785e4263dd4964d14a2c8c` |
| fixed W2 | `a97275817c58e164f75c7cd3d80ca99444a2a145` | 2 | `af6c282e9214d72cd0135b5b7f4a5a6958330910e5bd3a146aa8855ffc7850e3` | `92ff913ee211d74ee5d8dead15ddb4709a9a8ecf49785e4263dd4964d14a2c8c` |

These are image-file and canonical-pixel hashes.  The
`raw_combined_output_sha256`, `stdout.sha256`, and `stderr.sha256` fields in
`out/runs.json` hash process logs for provenance; they are not output hashes and
are not substituted into this table.

## 3. Magnitude and spatial support

**MEASURED** for affected W2 minus affected W1
(`out/analysis.json`, `comparisons.affected_w1_vs_w2`):

- 3,430 differing pixels of 8,241,504: **0.041619%**.
- 3,437 differing channel samples: R/G/B = **1,855 / 791 / 791**.
- Signed histogram: **−1: 1,657; +1: 1,780**.
- Maximum absolute difference: **1 DN16** =
  `1/65535 = 1.5259021896696422e-05` of full scale.
- Maximum per-sample relative difference: **`1/176` =
  0.005681818181818182**.
- Inclusive `(x0,y0,x1,y1)` bounding box:
  **`[1,0,3515,2343]`**.
- **2,642** changed pixels are at least 256 pixels from every output edge.

**MEASURED:** the affected W1 repeat is identical at both file and canonical
pixel levels.  Fixed W1/W2 is also identical at both levels.

**VERIFIED:** `tifffile` and OpenCV (with explicit BGR-to-RGB normalization)
independently decoded all five images to the same `2344 x 3516 x 3` `uint16`
arrays and canonical hashes (`out/analysis.json`,
`independent_decoder_corroboration` and each image's
`independent_decoders_equal`).

## 4. Mechanism and falsification

**VERIFIED BY SOURCE / MEASURED BY OUTPUT: `REDUCTION_ORDER`.**

1. The affected source makes logical chunks from requested workers: W=1 is
   `[19]`; W=2 is `[10,9]`.
2. SoftPower accumulates `f32` `num`, `usum`, and `den` planes, then
   `BandMerge::absorb` adds those partials.  The explicit anchors are retained
   in `out/source-evidence.json` under `excerpts.soft_power_default`,
   `excerpts.f32_numerator`, and `excerpts.f32_absorb`.
3. Floating-point addition is non-associative, so `[19]` and `[10,9]` round
   along different grouping paths before the final RGB16 quantization.
4. The fixed source chooses a canonical four-chunk lattice from planning bytes
   and frame count.  Both W=1 and W=2 therefore reduce `[5,5,5,4]` in the same
   left-to-right order; requested threads are execution resources, not
   arithmetic grouping.
5. Alignment was off.  The changed pixels span nearly the full output and
   2,642 are deep interior, excluding a coverage/resampling-boundary
   explanation.  SoftPower and the symmetric ±1-only histogram do not support
   a discrete tie/selection change.

The measured defect is therefore **quantization-visible non-associativity**.
It does not establish a different winner, admission set, coverage decision, or
other structural merge decision.

**The preregistered result would have been falsified** if any of these occurred:
the affected W1 repeat changed; affected W1/W2 canonical pixels were equal
(triggering the bounded W3 fallback); fixed W1/W2 still differed; requested
workers did not change affected chunk boundaries; fixed workers changed the
canonical lattice; SoftPower/`f32` absorb was not active; alignment or a
coverage boundary was active; or the spatial/magnitude pattern selected a
boundary or discrete-decision mechanism.  `verify.py`'s
`source-mechanism-preconditions-and-verdict` and the planted improvement,
degradation, and mechanism mutations commission those branches.

## 5. Revision-bound blast-radius audit

**VERIFIED:** the read-only audit is bound to commit
`69bdacafbb4a49a198e9f430590033e8a5ed25a2`, not the moving worktree.
`out/claim-audit.json` contains 30 exactly-once high-stakes IDs, an 82-file
material inventory, 92 exact evidence anchors resolved across 63 unique Git
blobs, declared classification and provenance enums, both false-exposure
directions, and explicit current score/verdict survival.  Every citation is
read from the exact `AUDIT_REVISION:path` blob, decoded as strict UTF-8, and
accepted only when its verbatim anchor occurs exactly once.  Every evidence
path is in the inventory.  M139 evidence remains limited to its committed
report; no M139 output artifact was read.

Legend: **SU** = `SURVIVES_UNCONDITIONALLY`; **SW** =
`SURVIVES_SAME_WORKER_ONLY`; **CU** = `CONDITIONED_UNRECORDED`; **IP** =
`IRRELEVANT_PREMERGE`; **SP** = `SUPERSEDED`; **VD** =
`VOID_AS_DETERMINISM_EVIDENCE`.

### 5.1 Final-render, scored, frozen, and reuse contracts

| ID | worker provenance | classification | disposition and exposure |
|---|---|---|---|
| M8-O | explicit historical W=1 | SP | v1.4 is superseded; v1.5 remains UNMEASURED.  Its rail-projection issue is separate from workers. |
| SHIPPING-SCALE-CATMULL-ROM-BYTE-FREEZE | W=4 recorded, not asserted | SW + VD | `FB76…B084` remains a W=4 Scale + Catmull-Rom witness.  The registry does not prove cross-worker determinism and can false-red at another topology. |
| M130 | **explicit W=2**, Rayon=6 | SW | Every comparable A/B explicitly set W=2.  Code-change equality and Scale geometry survive at W=2.  The separate W=4 registry witness remains separate; the A/B was not a sanitized default. |
| V-MOTE-DUST-OFF | inherited, unrecoverable | CU + SW | The validator/recommendation survives common-worker-only; absolute “zero downside” wording remains conditional. |
| M-COVER-BORDER | mixed history; corrected W=2 | SP | The old mixed `profile-final.json` is invalid; its pinned rerun supersedes it.  This remains the confirmed worker-caused false difference. |
| PINNED-WORKER-PYRAMID-GROUPS | explicit environment or legacy `--chunks` pins | SW | M-FLATNULL, M8-v2, and M142 were W=1; BUILD-RESAMP was W=2; V-ca used `--chunks 5`; V-chroma2 reproduced BUILD-CHROMA at `--chunks 4`.  Their within-pin A/B conclusions survive, not a cross-worker extrapolation. |
| SAME-PROCESS-DEFAULT-AB-GROUPS | one sanitized process/default per pair | SW | M126, BUILD-BLEND, soft-gate/band-floor, and M-COVER-NATIVE A/B conclusions survive within each common topology. |
| DELIVER-V6 | inherited, unrecoverable | CU + VD | Seven equal files remain observations; generalized fixed-binary determinism is withdrawn.  Its existence-only resume also permits stale equality. |
| METADATA-ONLY-EXPOSURE | non-Pyramid semantic case | SP + VD | Different file hashes with 98,898,048 equal pixels remain a confirmed metadata-only false difference and show why whole-file SHA alone is insufficient. |
| SCORED-RUN-MANIFEST-M153 | requested W only; resolved topology absent | CU | No current score is invalidated.  Future scoring requires the normative contract. |
| FINALPASS-CACHE | binary-only `.ok`; image/topology unsealed | CU | Reuse can return a stale TIFF.  `.ok` does not hash the TIFF, canonical pixels, or lattice. |
| M162 | set environment bound; resolved topology absent | CU | The existing UNRESOLVED verdict survives; any future comparison remains conditional. |
| V-ENVSURF-WORKERS | unset W=3 versus explicit W=1 at N=3 | SU + VD | Exact equality survives.  Because 3x1 and 1x3 preserve frame-order arithmetic, it is a **confirmed false-agreement surface if generalized**, not invariance evidence. |
| M-PHASE0-SPLIT | explicit W=1 and Rayon=1 | SW + SP | Split-off/on ordinary TIFF equality survives at W=1.  The KILL/STOP/REMOVE prototype verdict also survives. |
| BUILD-SPEED | declared W=1/2/4/8 treatment; common W=4 controls | SU + SW | The worker-treatment/scaling design survives; repeated common-W=4 hashes survive.  This audit adopts no absolute timing result. |
| ORCH-SHIP-V3-V4 | four workers recorded, not asserted | SW + VD | All 26 equal files remain observations, but SHIP-V3 and SHIP-V4 have different binary pins.  “Two runs of one binary” determinism is withdrawn. |
| V-NEVERWORSE-SHIP-RENDER | common sanitized default; resolved W absent | SW | Shipping-master rerender identity and the corrected verdict survive within the common topology only. |
| SCORECARD-BASELINE | null override; banners record W=4 | SW + CU | W=4 diagnostics survive; the current score remains UNMEASURED.  The manifest has no canonical-pixel hash or lattice identity. |
| UNSEALED-RENDER-RESUME-PATHS | future contract unbound | CU | `render_all.ps1` skips on existence, `gallery-ab.ps1` on a nonempty TIFF, and `finalpass.ps1` on nonempty TIFF + binary-only `.ok`.  These distinct paths are a material stale-equality exposure. |

### 5.2 Pre-merge, worker-treatment, and unit claims

| ID | worker provenance | classification | disposition and exposure |
|---|---|---|---|
| M139 | declared W=1/2/4/8/16 sweep | SU | Historical cross-worker and conjunctive M12 FAIL survive; N=299 M12-D remains UNMEASURED.  W was the treatment. |
| M8-R | explicit W=1; observable is pre-merge | IP | The governing `1.030569%` FAIL survives unchanged. |
| M165 | admitted-input/load boundary | IP | Stage 0M/0C software conclusions survive; campaign/opaque-use limitations remain. |
| M164-WITNESS | checker threads, not renderer workers | IP | Frozen S_1/S_2 witness and licence/Ask-2a rulings survive. |
| M164-FUTURE-CANDIDATE | no candidate exists | CU | Current BLOCKED state survives; an eventual manifest needs requested/resolved worker and lattice fields. |
| M164-BLOCKED-CHECKER | non-render refusal | SU | Blocked-manifest/refusal reproducibility survives; it is not image determinism. |
| M-PHASE0 | declared sweep; queue pairs fixed-W | SU | Worker scaling survives because W is the treatment; queue transparency remains fixed-worker evidence. |
| ESTIMATOR-PREMERGE-GROUPS | Estimator or upstream/copy boundary | SU | Listed claims survive this Pyramid defect; this is not proof for every Estimator input/configuration. |
| WARP-CACHE-M117 | pre-merge placement map | IP + SU | Final-fold workers do not belong in warp-map keys; M117's no-contamination result survives. |
| M175 | external `--threads=1` | SU | The transfer sentinel survives and is neither a Pyramid score nor a quality result. |
| M172-UNIT-WORKER-CONTRACT | explicit W1/W4 unit controls | SU | Spatial work is asserted bit-identical at W1/W4 and worker overrides are asserted not to change canonical partitions.  This is not a final-TIFF ladder or M12 PASS. |

The row-level contracts, evidence paths, semantic anchors, exact provenance
state, classifications, consequences, and booleans behind these summaries are
authoritative in `out/claim-audit.json`, `claims[id=…]`.
The verifier also pins every declared `group_members` array to an explicit
ordered tuple.  For `PINNED-WORKER-PYRAMID-GROUPS`, that tuple is exactly
`[M-FLATNULL, M8-v2, M142, BUILD-RESAMP, V-ca, V-chroma2, BUILD-CHROMA]`.

### 5.3 Exact citation and revision-search coverage

The verifier performs three fixed-commit searches with this exact command
shape:

```text
git grep -Iil -E -e <pattern> 69bdacafbb4a49a198e9f430590033e8a5ed25a2 -- <pathspecs...>
```

The exact patterns are:

```text
STREHL_PYRAMID_WORKERS|--chunks(=|[[:space:]])|worker[- ]count|worker threads?|worker sweep|worker ladder|reduction order|canonical chunks?|logical frame partitions?
(worker|chunks).{0,100}(byte|bit|freeze|hash|TIFF|output|pixel)|(byte|bit|freeze|hash|TIFF|output|pixel).{0,100}(worker|chunks)
(Test-Path|Length|\.ok).{0,120}(tif|output|render)|(tif|output|render).{0,120}(Test-Path|Length|\.ok)
```

The first two search source-like `*.md`, `*.py`, `*.ps1`, and `*.json` below
`docs/research` and `experiments`, `*.rs` and `*.tsv` below
`crates/strehl-cli/tests`, the relevant `merge_cmd.rs`, `stack.rs`, and
`pyramid.rs` sources.  Generated `out`, `results`, `banked`, `artifacts`, and
`logs` trees are excluded, as are all M139 experiment trees.  The third searches
`scripts/*.ps1`.  The literal Git pathspecs, patterns, query names, and sorted
candidate set are in `revision_search`.

The rerun finds 142 candidate paths: 37 are material and 105 carry an explicit
exclusion/disposition.  The 82-file material inventory is exactly the sorted
union of all 63 cited paths and 19 additional material paths.  It includes all
formerly omitted citations and the adversarial resweep paths.  The verifier
requires every inventory path to be a blob at the audit revision and every
search hit to be material or explicitly excluded.

### 5.4 Absolute hashes versus scientific A/B conclusions

**VERIFIED / DERIVED:** exact equal bytes remain an exact observation.  They do
not prove a cross-worker counterfactual.  A scientific A/B conclusion survives
when both arms shared an explicit pin or one sanitized process/default
resolution; only its extrapolation to another worker lattice is disallowed.
An absolute historical Pyramid hash with unrecoverable topology is conditional.

**False difference:** M-COVER-BORDER is confirmed.  V-MOTE, DELIVER-V6, and
unqualified historical absolute Pyramid pins have latent exposure.
`--exposure` is a separate confirmed metadata-only false difference; the
historical warp-cache mechanism was separate and M117 cleared the corpus.

**False agreement:** V-ENVSURF is the confirmed generalization trap: different
worker counts can agree at N=3 without proving invariance.  ORCH's 26 equal
files cannot isolate determinism because the binary pins differ.  No
independent scientific treatment cancellation by worker rounding was measured.
Stale-cache reuse is separate and material across `render_all.ps1`,
`gallery-ab.ps1`, and `finalpass.ps1`.

## 6. Shipping default and the M172 boundary

**VERIFIED BY READING AT THE AUDIT REVISION:** Pyramid is the shipping backend.
`merge_cmd.rs` symbols `canonical_band_chunks`, `band_workers`, and
`run_pyramid` separate logical arithmetic grouping from execution threads:

- canonical chunks are
  `min(frames, max(1, 6 GiB / planning_bytes))`;
- `planning_bytes` follows frame geometry, Pyramid configuration, and build
  constants, not detected RAM or CPU count;
- an explicit `STREHL_PYRAMID_WORKERS=N` resolves execution threads to
  `min(N, frames)`; if unset, execution threads equal the canonical chunk
  count;
- canonical chunks execute in order with one reusable frame worker, while the
  requested pool performs spatial work inside a chunk.

Therefore the **current Pyramid default is not machine-dependent**.  It remains
input/frame-count, planning-byte, build, and configuration dependent.  Older
scripts can still inherit `STREHL_PYRAMID_WORKERS` unless they sanitize it.
There is no `strehl stack --workers` flag; Pyramid's control is the environment
variable.  `RAYON_NUM_THREADS` was an execution-pool cap in historical runs,
not the Pyramid logical-worker request, and current `run_pyramid` constructs its
own pool from the resolved value.

**VERIFIED SEPARATE PATH:** the nonshipping Estimator planner still consults
`std::thread::available_parallelism()` (`merge_cmd.rs`, Estimator planning
block).  M176's current-default conclusion must not be transferred to that
planner.

**VERIFIED UNIT BOUNDARY:** at the audit revision,
`pyramid.rs::spatial_parallelism_is_bit_identical_across_worker_counts`
asserts exact equality between `run(1)` and `run(4)`.
`merge_cmd.rs` separately asserts that explicit execution-thread overrides do
not change `canonical_band_chunks`.  The M172 measurement harness accepts an
explicit worker treatment.  These are powered unit/resolver controls, not a
full final-TIFF ladder.

**Boundary:** before M172, requested workers selected the arithmetic partition;
after M172, a canonical lattice selects it and workers only select execution
resources.  The repair commit was already in the fixed control and in audit
revision `69bdacafbb4a49a198e9f430590033e8a5ed25a2`.  M176 did not land or alter
the repair.  The only post-fix end-to-end result measured here is W=1 versus W=2
on this one 19-frame control.  This is **not** a full post-fix M12
W=1/2/4/8/16 ladder and does not license M12-S PASS.

## 7. Scored-render consequence and normative contract

**DERIVED:** a scored capture, reusable final render, or byte freeze must bind
the arithmetic identity, not merely a requested thread knob.  Requested and
resolved counts can differ; two equal counts can still conceal different frame
partitions after a planner change; and a whole-file hash can differ only in
metadata.  The contract therefore needs requested workers, resolved workers,
the complete versioned reduction lattice, and both file and canonical-pixel
hashes, with fail-closed comparison/reuse.

**Normative requirement (verbatim, one line):**

Every scored, cached, or hash-frozen render MUST bind workers_requested, workers_resolved, and a versioned reduction_lattice_id containing the exact logical frame partitions and ordered reduction topology to both its whole-file and canonical-pixel SHA-256, and MUST refuse comparison or reuse on any mismatch.

This applies prospectively to M153/RUN-MANIFEST scoring, future M164 candidate
packages, M162 render contracts, the byte-freeze registry, and final-render
resume caches.  It does not add irrelevant worker fields to M8-R, M165 admitted
inputs, M164's non-render witness/checker, M175's external single-thread
sentinel, or warp-map cache keys.

## 8. Exact STATUS replacement routed to the orchestrator

**VERIFIED TARGET:** at audit revision
`69bdacafbb4a49a198e9f430590033e8a5ed25a2`,
`docs/STATUS.md` blob `aab1a092cafa4b6768bffbf5627da1dd54d37512`
contains the unique semantic anchor **“Every hash pin in this repository is
therefore …”**.  M176 did not edit STATUS.  The exact proposed replacement,
also machine-bound in `out/claim-audit.json` under `status_replacement`, is:

```text
**M176 narrows the blast radius.** The affected Pyramid backend made final-render bytes depend on its logical worker decomposition, but not every repository hash is a Pyramid final-render hash. The historical M139 cross-worker FAIL; pre-merge M8-R and M165 checks; M164 witness and blocked checker; estimator-era results; M117 warp-cache clearance; and M175 transfer sentinel survive. The shipping Scale + Catmull-Rom freeze and M130 equality at explicit W=2 remain valid at their recorded worker topology, not as cross-worker determinism evidence. V-MOTE's wrong-map/OFF equality and DELIVER-V6's generalized determinism wording must be conditioned on a common worker lattice; M8-O v1.4 and the metadata-only `--exposure` whole-file difference were already superseded. M-COVER-BORDER's mixed-history profile is the one confirmed worker-caused false difference, superseded by its pinned-worker rerun. V-ENVSURF's N=3 W=3/W=1 equality is an exact observation and a confirmed false-agreement surface if generalized, not proof of invariance. M-PHASE0-SPLIT's fixed-W=1 null preserves its KILL verdict; BUILD-SPEED's W=1/2/4/8 treatment is valid without admitting absolute timing; ORCH's 26 equal V3/V4 files do not prove two runs of one binary; and V-NEVERWORSE's shipping-master rerender identity survives only within its common unresolved topology. SCORECARD-BASELINE remains UNMEASURED, render_all/gallery/finalpass resume paths remain unsealed, and M172's unit worker contract is not a full final-TIFF ladder.

Exact equal bytes remain exact observations; they do not prove cross-worker determinism without matching requested/resolved workers and reduction lattice. V-ENVSURF confirms that equal bytes can be a false-agreement surface when generalized, while no cancellation of an independent scientific treatment by worker rounding was measured; stale-render reuse is a separate material false-agreement risk. Every scored, cached, or hash-frozen render MUST bind workers_requested, workers_resolved, and a versioned reduction_lattice_id containing the exact logical frame partitions and ordered reduction topology to both its whole-file and canonical-pixel SHA-256, and MUST refuse comparison or reuse on any mismatch. The M172 repair was already present at audit revision `69bdacafbb4a49a198e9f430590033e8a5ed25a2`; M176 lands no renderer repair.
```

This proposal is routed to the orchestrator; it is not an edit authorization
for this lane.

## 9. Verification, commissioning, and bindings

**VERIFIED without rebuilding or rendering:**

- `out/verification.json` reports **33 checks**: the original **21**
  independently run reproduction checks preserved by their original
  verification SHA-256
  `92072b3eddfe0c2b40b6e6806c67e4b29df1a0ce27f9c05df5bd6b255cecabe4`
  and immutable evidence hashes, **1** historical render-time source-binding
  check, plus **11** newly run claim-audit checks.  The historical production
  source hash map in `provenance.json` remains byte-for-byte bound separately
  from the current LF-normalized integration sources.
- The named claim checks include exact Git-blob citation resolution, the
  revision-bound search rerun, and a private add/commit/clone under
  `core.autocrlf=true`.  All **21** bound M176 experiment paths check out
  byte-identically; the cloned real verifier also reports all 11 claim checks
  green.
- `out/commission.json` reports **56 verifier invocations**: 19 named checks in
  the baseline technical fixture, 11 named checks in the baseline claim audit,
  **24/24** retained technical mutations killed, **28/28** claim-audit
  mutations killed, **1/1** EOL-policy mutation killed, **53/53** total
  substantive mutations killed, and the retained **1/1** inert control
  surviving with byte-identical evidence.
- The added substantive mutations cover all eight new required IDs, a missing
  revision-search hit, a nonexistent evidence path with a nonempty anchor, a
  fabricated nonempty anchor in an existing blob, the retained empty-anchor
  case, corrupted JSON EOL policy, M130's wrong sanitized-default provenance,
  the exact normative requirement, and exact ordered `group_members` contracts
  for every grouped claim.  The new
  `fabricated-pinned-worker-group-member` mutation replaces the real `V-ca`
  line with `FABRICATED-NOT-A-GROUP-MEMBER` and fails specifically with
  `M176-E-CLAIM-GROUP-MEMBERS`; because that replacement also removes `V-ca`,
  the same mutation detects a missing real member.  The original 39
  substantive kills are retained.  Each mutation uses one unique full-line
  block, reports its specifically named red error, and restores its target
  byte-identically
  (`mutation_commission.py`, `CLAIM_AUDIT_MUTATIONS`, and
  `out/commission.json`, `claim_audit_mutations`).

**Evidence SHA-256 bindings after regeneration:**

| artifact | SHA-256 |
|---|---|
| `out/analysis.json` | `69efe9e1c27249ac27cf5622988b5d56592119f48fe705384a83a928bf141b0e` |
| `out/runs.json` | `520ac6b43ac57418dfb3fef8e7184129c7109af19f23df0e1046b845f6d52cb4` |
| `out/source-evidence.json` | `b7ea70c28f8afd54370ee030db04c545f1263cc592065d9ed20d23fb07b6811a` |
| `out/claim-audit.json` | `063314b6aea43db6cd699aa50f49d32e59bc95c78182bda030d467d4ce70a3f4` |
| `out/verification.json` | `ef4d0aea4d8e0778bf8cd0ac3db5d0b11a07d6b396cb902f9e1aa865c11e73d3` |
| `out/commission.json` | `0b807c83797ab1669c3b52b090f3be1f57b297f8b795ec4e5c66ca156afe07d8` |

`out/commission.json`'s `binding.evidence_sha256` binds the claim audit and
regenerated verification alongside every immutable production evidence file.
Its production and sandbox source hashes bind `.gitattributes`, `.gitignore`,
all six Python sources, and `preregistration.json` and match before/after.
The commission document also carries canonical self-excluding payload SHA-256
`280b4586959163f4f05a7c94c31a6903107401407935847507b2de939d87101f`.
The technical fixture, claim audit, and EOL policy were restored
byte-identically after every mutation; STATUS was unchanged during
proposal-only commissioning.

No build or render was rerun for this integration.  No wall-time result is
reported.  M176 made no renderer repair, no STATUS edit, and no protected-path
write.  The read-only capture manifest remains the reproduction's integrity
proof; integration verification did not access capture storage.

## 10. Final disposition

**Survive unconditionally:** M139's historical cross-worker/conjunctive FAIL;
M8-R; M165 Stage 0M/0C within its stated boundary; M164's witness and blocked
checker; M-PHASE0 and BUILD-SPEED's declared worker treatments; estimator and
other pre-merge results against this Pyramid defect; M117's no-contamination
clearance; M175's single-thread transfer sentinel; and M172's unit-level
W1/W4 execution and canonical-partition contract.  BUILD-SPEED contributes no
absolute timing adjudication.

**Survive with fixed/common-worker scope:** the shipping Scale + Catmull-Rom
W=4 freeze; M130's explicit-W=2 non-perturbation result; V-MOTE's scientific
wrong-map/OFF conclusion; explicitly pinned Pyramid groups including V-ca and
V-chroma2/BUILD-CHROMA; same-process/default A/B groups; M-PHASE0-SPLIT's W=1
null; V-NEVERWORSE's common-default rerender; and SCORECARD-BASELINE's W=4
diagnostics.  Their observed equal bytes are not withdrawn; only cross-worker
determinism is unlicensed.  SCORECARD-BASELINE remains UNMEASURED.

**Condition, withdraw, or supersede:** condition V-MOTE's absolute
zero-downside wording and DELIVER-V6's generalized determinism claim; keep the
seven delivered-file identities as observations; supersede the old
M-COVER-BORDER profile with its W=2 rerun; keep M8-O v1.5 UNMEASURED and do not
reuse v1.4 as current; reject the metadata-only `--exposure` whole-file
inference; retain M-PHASE0-SPLIT's KILL verdict; keep ORCH's 26 equal V3/V4
files but withdraw its one-binary determinism interpretation; treat
V-ENVSURF's N=3 equality as a false-agreement surface rather than invariance;
and refuse future M153, M164, M162, byte-freeze, `render_all`, `gallery-ab`, or
`finalpass` comparison/reuse until the normative contract is satisfied.

No existing scored result needs a worker-only rerun merely because it is
pre-merge, non-Pyramid, or a matched fixed-worker A/B.  Any result that seeks
an unconditional absolute Pyramid hash must be rerun under a bound lattice.
A full current M12-S PASS still requires a fresh, explicit post-fix
W=1/2/4/8/16 ladder; M176 measured only W=1/W=2 on one 19-frame development
control.  M172's W1/W4 unit checks do not fill that end-to-end gap.
