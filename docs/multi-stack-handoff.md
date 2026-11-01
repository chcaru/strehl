# Multi-stack continuation: complete instruction set

Prepared October 31, 2026. This document is sufficient to start a new agent with
the instruction: **Read `docs/multi-stack-handoff.md` and continue the remaining
multi-stack work.** No previous chat, agent memory or Downloads file is required.
Linked reports provide reproducible detail; this document states the objective,
current truth, constraints and next decisions. Historical agent dispatch wording
does not authorize independent jobs or override the current user's instructions.

## Latest user direction: automatic best-result workflow is the priority

The user tried combining seven related bug-3 stacks. The engine refused mixed
shutter times and suggested choosing HDR or Layers. The user explicitly rejected
having to manage these distinctions and instructed:

> i want Strehl to just hand it all for me and give me the absolute best result
> possible given the inputs.

They want the different benefits **at the same time**, with intelligent merging
where possible. This supersedes any interpretation that separate manual modes,
metadata refusals, or telling the user to remove passes completes the product.
The current mode selection is an implementation limitation, not a necessary
photographic workflow. Do not solve this request merely by better error messages,
automatically selecting today's HDR mode, or routing all heterogeneous input to
separate Layers. Those may be useful fallbacks, not the requested combined result.

**Required target:** the user supplies related stacks and normally presses Stack.
Strehl analyzes what each acquisition can contribute, plans compatible geometry
and appearance relationships, then produces its best supported default photograph
using the available information. Exposure fusion, repeat averaging, complementary
focus, aperture diversity and supported original-sample reconstruction must be
composable within one session and, where warranted, within one image region.
For overlapping framing it should also compose these benefits with stitching.
Do not require the user to classify every pass or know why shutter/ISO/PSF differs.
Retain manual modes and policy overrides as optional advanced controls.

The next agent should implement an automatic analysis/planning layer and adapt
the consumers rather than just relaxing the existing same-exposure guard:

1. Inspect exposure/shutter, ISO, aperture, camera/sensor/CFA identity, focus
   coverage, clipping, noise, reflectance/lighting and framing/viewpoint. Infer
   per-pass, per-capture and local relationships with uncertainty. Split internally
   when a folder changes acquisition settings rather than requiring manual folder
   classification. Metadata is useful evidence, not proof of optical equivalence.
2. Fit geometry and calibrated per-source photometry/noise in appropriate common
   coordinates. Different shutter times should trigger normalization and local
   usable-signal reasoning, not an immediate whole-session rejection. ISO, PSF and
   aperture differences need their actual response/noise/support treatment, not
   unconditional pooling. Do not average genuine reflection or illumination
   changes into invented common radiance.
3. Choose contribution locally: recover supported unclipped highlights, improve
   supported shadows/repeat noise, fill missing focus, retain the best supported
   fine structure and use sampling diversity only where it delivers a demonstrated
   benefit. Coverage, calibration and optical eligibility are separate evidence.
   Contribution should reflect information delivered, not a requirement that every
   input affect every pixel. Avoid blur, ghosts, seams and color drift.
4. Provide local fallback when an acquisition or hypothesis is unhelpful. Preserve
   a coherent supported result rather than failing the whole session on one bad
   relationship. Genuinely unrelated viewpoints cannot safely become one 2-D photo;
   detect and explain that case, retain useful views, and keep diagnostics/optional
   alternative outputs available without making them the default user's burden.
5. Preserve the optional primary target for simple same-subject multi-stack work;
   it is a framing/appearance preference, not a prerequisite. It still does not
   apply to stitching. Automatic planning must retain immutable source identities,
   deduplication/independence accounting, recipes/cache bindings, cancellation,
   memory planning, progress and reopening. Explain material exclusions succinctly
   after processing; avoid making internal algorithm choices mandatory setup.
6. Establish the automatic default through complete-image comparisons against the
   best credible individual/manual results, not merely successful execution.
   Include mixed-exposure repeat/interleave cases and compatible aperture/lighting
   cases together, positive/negative controls, ordinary no-regression and independent
   full/native review. "Best possible" is the user's quality objective; it is not a
   claim of a universal optimizer or permission to fabricate unsupported detail.

First concrete regression case: the exact seven-pass manifest at
`C:/Users/chris/Pictures/Strehl/strehl-1793474770086-32624-1/session-manifest.json`;
its ordered pass folders are bug-3 107/106/105/104/103/102/100 under
`D:/personal/macro/insects`, with optional primary 107. Source directories remain
read-only. The census records 1.6 s for 103--107 and 2 s for 100/102; verify current
metadata rather than assuming all differences are shutter-only. Start with bounded
analysis and controlled subsets; do not blindly launch a costly all-source render
or claim all these passes are mutually mergeable before measuring them.

**October 31 continuation status.** A first planner slice exists: `SessionMode::Auto`
("Best result", the new desktop default) plans each pass against the anchor,
combines equal settings, admits shutter differences only through held-out
calibrated photometry, and excludes unsupported passes with stated reasons instead
of failing. Equal-setting Auto output is bit-identical to Combine on a real
107+106 control. Measured on bounded subsets, the regression case is **not
primarily HDR**: all seven passes share ISO/aperture/lens; 100/102 are roughly
2.5--3x close-ups of the elytra, and 103--105 differ from 107 by translation and
magnification. Every cross probe from 107 except to 106 fails at the coarse
stage, so Auto currently uses 107+106 only. The calibrated-exposure path has not
yet run on real aligned data. A wide-baseline initializer (`strehl-core` `align_global`, seeds confirmed by
direct refinement) now joins 103--105 (x1.22--1.24, about -2 deg), but review and
residual fields showed a **pose change**: fusing them ghosted. A cross/intra
tile-support gate (compatible 1.17, pose-changed 0.15--0.28, bar 0.5) excludes
them in Auto and refuses them in fused manual modes. The complete seven-pass
manifest now completes in Auto (43.6 min, 10.8 GiB peak): 107+106 fused cleanly,
five passes excluded with reasons; close-ups 100/102 are not found by the global
search. Next candidates: locally deformable cross-pass registration (to use
pose-changed passes), close-up detail insertion, cross-ISO/aperture treatment and
in-pass setting splits. Evidence, commands and limits:
[first-slice-2026-10-31.md](../experiments/multi-stack-2026-10-28/completion/auto-plan/first-slice-2026-10-31.md).
The complete automatic best-result workflow remains required future work.

**Third slice (bug-4, five passes, 1,231 frames).** All frames now place in one
component (identity-seed retry for intra-pass pairs the coarse ladder refuses;
exposure-relative contrast floor). Per-frame brightness is solved jointly over
geometry-confirmed overlaps (residual 0.0004 ln over 11,042 overlaps), replacing
per-pass gains, so in-pass lighting drift and shutter differences combine without
manual classification. A direct post-placement residual check replaces the support
proxy as the pose gate (relit 104/105: 1.0/1.4 guide px, consistent). Bug-4's
other four passes are lit differently in *shape* (cross spread 0.27--0.35 vs
about 0.01 within a pass); they become `lighting_layer` roles. Four blends of
separately merged lighting groups were measured against the anchor's developed
photograph and **none beat it** (haze, glow, seams; then dark holes at speculars
and softer grain). Lighting layers are therefore reported but not consumed by
default; `--lighting-fusion` enables the experimental detail-only blend. Default
Auto on bug-4 is bit-identical to the anchor-only render. Next: brightness-matched
detail transfer for lighting layers, locally deformable registration, close-up
insertion.

**Fourth slice (light superposition, pose layers).** Superseding the above:
lighting layers are now consumed by default through equal-weight light
superposition after a lighting-independent defocus gate, coarse-to-fine dense
residual registration and a relit coverage fill; pose-changed passes become
pose layers, superposed only where they match the relit anchor. On bug-4 this is
the first combination that beats the anchor alone (background noise -23%,
detail intact, no seams or holes). On bug-3 the gate drops the blurry merges of
103/105 and uses 104 where it agrees; the close-ups 100/102 are still unplaced.
`--anchor-lighting-only` opts out. Next: close-up detail insertion (100/102),
why some separately merged passes come out blurry (bug-3 103/105, bug-4 105),
and desktop surfacing of layer outcomes.

**Fifth slice (local sharpness, desktop).** Layers are gated per pixel by local
sharpness, so a short pass contributes where it is in focus. The blurry merges
above are short or off-focus passes (bug-3 103: 22 frames; bug-4 105: 55), not a
merge defect. The desktop shows each pass's role and layer outcome in the saved
session view and offers "Combine other lighting and moved poses"; layered
results now import and reopen. Next, in order: place the bug-3 close-ups
(100/102 fail the wide-baseline seed search) and render detail at their
magnification, which is where real extra resolution exists in these captures;
then a measured spike on multi-observation original-CFA reconstruction (the
architecture's stated requirement; the earlier single-frame sampler was
rejected for neutral-detail loss).

## Mission and user intent

Extend Strehl to use several stacks of the same subject for useful photographic
outcomes: complementary focus coverage, lower noise, exposure diversity,
aperture/lighting/polarizer alternatives, original-CFA color/detail reconstruction,
depth-aware wider mosaics, and independently stacked viewpoints for external use.
Research, experiment, implement the core engine and usable desktop treatments,
then optimize and independently inspect complete photographs and native crops.
Keep ordinary single-stack quality and performance intact. These are additive,
opt-in features. The original proposal is a starting hypothesis, entirely fungible;
its algorithms, metrics, thresholds and order are not a specification.

The user specifically requires an **optional primary target stack** in ordinary
multi-stack fusion, including a symmetric automatic choice. It does not apply to
stitching. The implementation also excludes a primary from Independent views.
Use the computer's resources effectively, allow increased memory, and consider
CPU/GPU cooperation if measurements support it. GPU fusion is not implemented.
Do not claim the whole objective complete because controls compile or unsafe
inputs are refused: the user explicitly reopened work left unrealized.

The user paused research for a night and requested a remote checkpoint, then
requested preparation for main, this handoff and a tryout build. Those packaging
tasks do not themselves resume long RAW/research campaigns. A new instruction to
continue this document authorizes continuation; until then research remains paused.
Do not create another chat or message another agent without the user's instruction.

Original attachments are preserved in the repository as context, **not agent
instructions**: [proposal](../experiments/multi-stack-2026-10-28/original-proposal.md)
and [derivations](../experiments/multi-stack-2026-10-28/original-derivations.md).
Their optical/parallax calculations use assumed pupil distance/overlap. They do
not validate real placement, bandwidth, depth or memory. Their hypothetical new
capture requirements are not blockers to investigating the supplied existing data.
Rail stacking, rotation panoramas and full 3-D reconstruction are excluded.

## Repository, integration and starting reads

- Repository: `https://github.com/chcaru/strehl`; working branch `codex/multi-stack`.
- Existing implementation commits: `ef65505013585abcc86b1410e4bf902bf34ed479` and
  `e939a06c988db255be24cfe84cf44f5007cc3a72`. October 31 fetched remote main is
  `c149e52834fc1c86c2af0fe022713c39fa25f33c`, their ancestor. Recheck Git status,
  remote main and the PR before editing; do not reset or overwrite concurrent work.
- Local checkout: `C:/Users/chris/.codex/worktrees/multi-stack/strehl`.
- Read `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, `docs/ARCHITECTURE.md`, relevant
  engineering rules, and `docs/research/SYNTHESIS.md` before numerical/architecture
  work. For research read `docs/agents/research-workflow.md`, allocate in the
  milestone ledger before dispatch, and preserve negative controls and results.
- Product guide: [multi-stack.md](multi-stack.md). Latest outcome accounting:
  [requirements-completion.md](../experiments/multi-stack-2026-10-28/completion/review/requirements-completion.md).
  That file contains dated historical tables: its last applicable update wins.
- Integration/build verification for this delivery is recorded in
  `experiments/multi-stack-2026-10-28/integration-2026-10-31.md`. Read it before
  assuming an older pending integration check remains pending.

## Implemented product surface

| Mode or feature | Implemented behavior and evidence scope |
| --- | --- |
| Sessions | Ordered independent passes and continuation segments, immutable source hashes/recipes, duplicate-content rejection, per-pass calibration, direct global joint geometry, saved reports/cache bindings. |
| Combine | Separately admitted captures across passes; shared native photograph and linear master. |
| Interleave | Explicit mode; real pitch32/offset16 test used 6+6 distinct originals from a 182-frame sweep and recovered complementary recognizable content. This is a controlled artificial split, not an independently captured half-step experiment. |
| Repeat | Noise-gated compatible coefficient means; optional predicted-noise weighting using separate guides. Wrong focus, motion, PSF and unequal-noise foils remain relevant. |
| Exposure range | Different shutter times, bounded photometric normalization, clipping-aware admission. Useful simultaneous highlight/shadow superiority remains unproved. |
| Aligned layers | Separate appearances on a shared canvas. Complete 117-source f5.6/f8 razor pair showed useful aperture selection; complete 598-source insect pair showed localized green/blue appearance choice. Actual desktop selection, reopen and export were exercised. No universal aperture ranking or calibrated polarimetric decomposition. |
| Independent views | Separate native coordinates, photographs/masters, focus/support/geometry/source bundles, explicitly unknown relative pose. Two complete 299-source views reviewed; actual desktop selection/export and relocated 103-file bundle import verified. No metric depth or 3-D mesh. |
| Mosaic | Union canvas, coverage/alpha, bounded tiles, focus/overlap/placement and support machinery. No qualified real extended-field photograph/master yet. |
| Original-CFA reconstruction | Direct original-sample reconstruction, phase/focus/geometry/appearance guards and exact native fallback, native output size, support/refusal overlays. Full chart replacement covered 0.468%; recognizable color/detail/alias improvement is unproved. |
| Evidence | Actual source/group influence by band, focus ordinals/support/ambiguity, two-pass reproducible-detail/disagreement maps and curves, strict completed-output bindings. Correlation is not resolution; focus ordinal is not distance. |
| Desktop | Session composition, options/guards, optional primary, memory/thread settings, pass timeline, layer/view selection, diagnostics/raw samples/curves, saved recipes, import/reopen/export. GPU viewer exercised in recorded product12/15/16 reviews. |
| Native sensor export | Contribution diagnostics additionally export exact signed f32 CFA merge before demosaic/WB/display/reconstruction. Strict typed optional fourth output and CLI/UI tamper/reopen controls implemented. Final real-binary checks are in the integration report. |

Primary selection anchors framing and prefers supported primary content on
disagreement; unmatched other focus captures can still contribute. Layers keep
their own appearance. Mosaic/Independent views clear primary. Session rendering
is full resolution; temporal smoothing, source repair, frame limits, ordinary
coverage controls and automatic exposure are unavailable rather than silently
applied. Existing saved recipes default new experimental options off.

## What improved, what has not been established

**VERIFIED bounded positives:** interleave coverage, aperture/appearance selection,
independent-view bundle workflow, diagnostic inspection, and conditional precision
arithmetic. In a fixed-guide same-photon 48-trial control, weighting lowered
injected temporal variance about 11.6% while matching the equal arm's clean transfer
to roundoff. That does not establish unconditional developed-camera SNR.

**MEASURED/independently reviewed repeat evidence:** real paired CFA operators
improved conditional reference agreement on the fixed bee protocol. Full product17
bee photographs compare legacy 4-pair, broader 16-pair and 32-singleton grouping
with the same 32 originals, geometry and development. Complete scenes, 27 frozen
native witnesses and both single-pass controls showed no conspicuous new seam,
color break or hair/facet loss. A baseline-only fixed shadow display showed lower
fine color grain in both preselected backgrounds with broader grouping. This is a
useful appearance result; it is not independent temporal output noise or proven
PSF equivalence. The broader `--uncertainty-repeat-proposals` option is hidden
research functionality, not a promoted desktop/default matcher.

**Still active:** generalized real repeat/HDR improvement without suppressed
detail; improved per-frame consumer placement from cross-pass constraints; useful
color/alias/detail gain from original-CFA reconstruction; qualified real mosaics
with added field and acceptable depth seams; final optimization of those outcomes.
Refusal machinery is useful safety behavior, not the positive result.

**Compatibility/performance:** product16's complete ordinary 299-source photograph,
linear master and sensor pixels were identical to the original baseline, over
7032x4688. Product17 legacy repeat photo/master pixels matched product16. Cache,
prefetch, buffered reports and bounded region gathering have scoped measured gains
and equality controls. A 24.9% cold-transfer pilot improvement is not a whole-mode
speed guarantee; cold/warm total comparisons are not isolated speedups. CPU does
fusion; GPU draws the workspace. RAM budget defaults to 16 GiB and is configurable.

## Exact pending work and recommended sequence on continuation

1. **Establish the delivered build state.** Read the integration report and run
   only missing checks. Before that report, product17 was the last archived release;
   final native export and omission source had unit tests but no new release.
   Do not confuse archived binaries with current source. Keep their source/library
   bindings intact when rebuilding. Exercise actual completed-result import/reopen
   for any changed producer and refresh ordinary equality after numerical changes.
2. **Bridge the repeat photo positive to a properly scoped held-source comparison.**
   Read `completion/review/repeat-proposal-withheld-plan.md`,
   `research-cohort-exclusion-review.md`, `native-sensor-export-review.md`,
   `repeat-proposals-17-photographic-review.md` and
   `noise-bee-commission-independent-audit.md` under the experiment root.
   Hidden repeated `--omit-acquisition` uses saved alignment, exactly two bounded
   Repeat passes, no RAW decode, retained cached pixels only, declared-original
   identity checks and poisoned-cache controls. Omit globals
   **17,18,21,22,25,26,29,30**: retained cohort is **16A+8B**, not 12+12. Leaders
   0/16 remain. Maximum eight cross-pass pairs. The proposed 24-source photographic
   comparison has not run. The shared map used all 32 originals: report conditional
   agreement, not unbiased 24/32 risk. Reference photons already occur in the old
   full32 photograph; the earlier observer cannot independently validate that image.
   Preserve per-target/color outcomes and adverse PSF/unequal-noise controls.
3. **Mosaic: diagnose underfit using saved measurements before new pixels.** Read
   `completion/mosaic/checkpoint-2026-10-29-night.md`, `dense-fit-protocol.md` and
   `spatial-independence.md`. Latest 772-source marigold focused-FIT replay used
   zero RAW decode, 603 nominations/289 accepted original pairs. Mixed/focused/
   augmented models all failed current placement/coverage bars (maximum held error
   roughly 6 quad pixels; zero qualified cells). Dense-FIT controls compiled but
   their six tests and real replay have not run. Verify frozen source/library
   identity, review complete-footprint fold purging, and execute controls first.
   Nine predeclared models are spacing 512/256/128 times smoothness 2/.2/.02.
   Five-fold FIT-only CV must retain all folds, training-only weights/coherence/
   seeds and native backward placement scoring. Correlated FIT rows cannot inflate
   independent evidence. Diagnose model capacity before new native queries;
   qualification needs fresh held islands, unchanged hull/reciprocal/Jacobian
   guards, a full added-field output and independent seam/detail review.
4. **SR: validate the original-sampling model before admitting real detail.** Read
   `completion/sr/repeat-forward-results.md` and
   `completion/review/sr-next-instrument-review.md`. Failed spline v1/v2 and cosine
   v3 hypotheses are preserved. Cosine v3 ran 21 synthetic cases, 25 fixed patches,
   held-photon isolation and aperture quadrature controls. Ideal geometry gave
   3/8 fully consistent seeds; recorded bee geometry gave 0/8 under variance cap 4.
   It has read no new real pixels and grants no product admission. Model mismatch
   is not proof of PSF disagreement. Before actual pixels bind four CFA-site noise/
   levels, source/guide identities, negative-tap dependencies, prediction variance,
   conditioning, exact consuming footprints and covariance scope. Do not pick a
   basis/subset or loosen thresholds after reading held values. Repeat plateaus
   need honest evidence distinct from a fabricated sweep peak/metric depth.
5. **Close useful complete photographic outcomes, then optimize.** HDR must show
   highlight preservation and useful shadows together against both singles;
   reconstruction must show actual supported color/alias/detail benefit; mosaic
   must add field with acceptable overlap. Keep native fallback outside supported
   regions. Review full masters and native crops with identical frozen transforms.
   Run isolated alternating timing/memory arms with output/evidence equality after
   the final mode works. Do not substitute a microbenchmark for whole-mode results.

## Code map and invariants

- `crates/strehl-core/src/session*.rs`: session types, global tracks, bounded
  coefficient fusion, statistics and attribution. `precision-mean.rs`,
  `repeat-evidence*.rs`, `focus-evidence.rs`, `reproducibility*.rs`,
  `reconstruction*.rs`, `mosaic*.rs` contain related primitives/controls.
- `crates/strehl-cli/src/session-cmd.rs`: CLI/options; `session-input.rs`:
  original census/calibration; `session-align.rs`: direct joint geometry;
  `session-consumer.rs`: native fusion; `session-sampling.rs` and mapped sampling:
  gather/cache; `session-repeat-proposals.rs`: hidden geometry proposals;
  `session-research-cohort.rs`: cache-only omission adapter;
  `session-reproducibility.rs`: publication/bindings. Reconstruction/mosaic and
  independent-view modules have explicit `session-` prefixes.
- `crates/strehl-ui/src/session*.rs`, `jobs-session.rs`, `process-session*.rs`,
  `app-session*.rs`: composition/options/import/control/history/inspection.
  `crates/strehl-edit`: shared saved recipe and export model.
- Keep stored originals u16 CFA, arithmetic f32, one injected noise model,
  runtime-fit geometry and one consumer gather; no aligned-frame volume or f16.
  Retain averaging/noise gates, active-area statistics and camera-profile boundaries.
- Never chain deep-stack alignment or transfer scene-fitted corrections. Evaluate
  placement at the consumer with gauge/scale stated. No raw bandwise argmax baseline.
- Observe AGENTS source-license prohibitions, including GPL implementations and
  rawler/dnglab source; do not open those to research algorithms. Use source-inclusive
  packaging/relink route and notices for binaries, not a lone static executable.

## Data, preserved outputs and safe execution

All supplied captures under `D:/personal/macro` are read-only. User-nominated roots:

```text
D:/personal/macro/requests/7-aperture-pairs
D:/personal/macro/requests/30-calibration-grid
D:/personal/macro/requests/misc-diagnostic/high-res-calibration-slide-cpl
D:/personal/macro/insects
D:/personal/macro/flower-marigold-cpl
D:/personal/macro/minerals/peacock-ore
D:/personal/macro/requests/8-tilted-planar
D:/personal/macro/requests/19-razor-edge
```

Inventory and scene IDs: `experiments/multi-stack-2026-10-28/corpus/report.md` and
`inventory-table.md`. b17/b18 are appearance views, b16/b18 independent angles,
b46/b47 the razor aperture pair; inspect saved manifests for exact folders.
Do not touch the sealed 407-frame holdout or infer capture roles from folder names.

All following paths are relative to this checkout unless absolute:

| Location | Contents / importance |
| --- | --- |
| `experiments/multi-stack-2026-10-28/` | Versioned source, protocols, compact receipts, reviews and failed hypotheses; keep in Git. |
| `outputs/multi-stack/completion/` | Ignored local artifacts: full outputs, source snapshots, run/resource logs, maps, caches. A clone does not contain them. |
| `outputs/multi-stack/completion/noise-bee-repeat-01/` | 32 original input copies/stamps, frozen protocol/manifests, saved alignment, source cache, old equal/precision/native witnesses. Keep copied-input identity/stamps. |
| `outputs/multi-stack/overflow/repeat-proposals-17/` | Complete three-arm photographs/masters/maps, full/native/shadow review images and receipts. |
| `outputs/multi-stack/completion/mosaic-marigold-2-3-prepared-01/` | Bound 772-source pass maps, compact guides and focus evidence; reuse only with exact identities. |
| `outputs/multi-stack/completion/mosaic-focused-fit-02/` | All preserved native measurements and negative mixed/focused/augmented outcomes. |
| `outputs/multi-stack/completion/mosaic-dense-fit-controls-build-01/` | Compiled, unexecuted controls and exact source/library hashes. |
| `outputs/multi-stack/completion/repeat-forward-v1-source/`, `-v2-source/`, `-v3-source/` | Frozen failed/current forward model source identities and results. |
| `outputs/multi-stack/completion/product-17/` | Old release executable/source archive/build identities; do not overwrite. |
| `outputs/multi-stack/completion/ordinary-regression-readback-16.json` | Complete ordinary pixel-equality receipt; actual images in `ordinary-regression-16/`. |

`outputs/multi-stack/overflow` is a junction to
`D:/codex-work/multi-stack-2026-10-28`. The 85.3 GB mosaic cache is separately
relocated there as `mosaic-source-cache`, with a junction at its old
`outputs/multi-stack/completion/mosaic-source-cache` path. All 1,298 copied files
were SHA256-verified before removing the C: copy. Cleanup receipts are versioned
at `completion/night-cleanup-receipt.json`; 96.17 GiB was reclaimed on C:.
Four obsolete prefetch caches and `target/debug/incremental` were deleted.
Do not rerun that one-shot cleanup or recursively follow/delete junctions.
Keep primary source caches, original copies/stamps, native masters, failed results,
prepared maps/guides, release libraries and frozen source snapshots.

This host was measured as 16 physical/32 logical CPUs and about 64 GiB RAM.
Read current free memory/load/disk space; no permanent exclusivity is implied.
Use bounded worker counts and resource receipts; root alone schedules shared
lanes, ignores peer locks and never kills an unowned process. For Windows atomic
TIFF/cache writes or Git metadata, the managed sandbox may require escalation;
record real failures rather than treating sandbox I/O failure as algorithm failure.

## Commands and verification discipline

PowerShell cwd is the checkout above. Use explicit paths and `login:false` for
tool commands. `GIT_WORK_TREE` may need that absolute checkout in this managed
worktree. Never repurpose HOME/CODEX_HOME, use bare shared-index commits, write
capture sidecars, or run Cargo with `-q` for evidence.

```powershell
$env:GIT_WORK_TREE = 'C:/Users/chris/.codex/worktrees/multi-stack/strehl'
$env:CARGO_BUILD_JOBS = '4'
cargo test --locked -p strehl-core -- --test-threads=4
cargo test --locked -p strehl-cli -p strehl-ui session -- --test-threads=4
cargo test --locked -p strehl-ui -p strehl-edit -- --test-threads=2
cargo clippy --locked -p strehl-core --all-targets --no-deps -- -D warnings
cargo clippy --locked -p strehl-cli --all-targets --no-deps -- -D warnings
cargo clippy --locked -p strehl-ui -p strehl-edit --all-targets --no-deps -- -D warnings
cargo fmt -p strehl-core -p strehl-cli -p strehl-ui -p strehl-edit -- --check
```

The pre-handoff final focused run freshly compiled and passed 160 CLI +64 UI
session tests; core passed 955/4 ignored. Strict CLI clippy failed with 30 unchanged
main diagnostics and one prior multi-stack diagnostic; core retained 43 main
diagnostics. UI had an unchanged unused function and an incremental hardlink
warning. Broad formatting also has recorded older failures. Do not claim clean
strict checks without actual new results. Corpus lint has 16 unchanged main-doc
violations. Broad CLI/workspace tests have private-corpus exceptions; read
CONTRIBUTING before claiming workspace-wide results. Check integration report for
the new delivery's refreshed tests and CI.

Every native command must preserve full output and exact exit immediately. The
runner below records command, environment, executable identity, elapsed time,
sampled private memory and host load. Use a fresh receipt/output directory:

```powershell
python experiments/multi-stack-2026-10-28/run-command.py --receipt outputs/multi-stack/NEW-run-01 --cwd . --env RAYON_NUM_THREADS=8 -- <executable> <arguments>
./scripts/package-desktop.ps1 -Destination ./outputs/NEW-desktop -TargetDirectory ./target
```

A source-inclusive local package includes `Strehl.exe`, `strehl-cli.exe`, notices,
hashed source snapshot, `strehl-source.zip` and rebuild instructions. Public
releases need the stronger official offline-vendored release workflow. Build from
committed source and confirm the changed crates actually Compile/Check; cached
output is not evidence of edited code. Preserve source/rebuild notices with any
distribution. Generated packages/RAW/cache/large photos stay outside Git.

For actual desktop exercise use `scripts/strehl-control.py` and
`docs/desktop-control.md`, **not Computer Use**. Isolate catalog, output and grants.
Use the helper's `screenshot` command for native egui/wgpu offscreen checks.
Headless option tests do not establish layout/GPU behavior. Shutdown only owned
workers and never present a partial/cancelled run as completed output.

For CLI alignment always set an isolated `STREHL_WARPMAP`; `--out` alone does not
isolate sidecars. Saved maps bind source identities, operator and implementation;
never edit a report hash to bypass mismatch. `session-align.rs` was deliberately
kept byte-identical to archived17 (SHA256
`a805c794a2b2dc40b4b25721ca2302b4582512ad20c6f42f1ff7c6b4a857c4f7`);
the retained-cohort adapter instead checks full-cohort parity before filtering.
Changing this source invalidates old map bindings and needs a fresh controlled map.

## Completion standard

Label claims MEASURED / VERIFIED / DERIVED / ARGUED / UNVERIFIED. Commission each
metric with inputs that make it fail; flat-ROI controls precede sharpness claims.
Independent review must challenge estimator/reference/arm/null/defaults as well
as arithmetic. Complete photographs/masters plus identical native display checks
are required for photographic conclusions. Preserve negative cases and scope.
Finish engine, usable UI, positive and negative evidence, ordinary regression and
appropriate optimization for every intended outcome, or obtain an explicit user
scope change. A new agent should advance the pending work above rather than
relabeling the implemented controls as completion.

## October 31 delivery verification

The tryout is now built from committed `9f81063231b78b9244874ccfa4bb939b60517ef5`,
build ID `desktop-129ddfd67a3f75a5`, at
`outputs/strehl-multi-stack-2026-10-31/Strehl.exe` with its source/relink package.
PR https://github.com/chcaru/strehl/pull/3 prepares integration into main; verify
its live state/checks before choosing the next base.

Fresh local verification passed 1,034 UI and 140 edit tests (15 UI tests ignored),
desktop/edit strict clippy and formatting, and 12 source-package controls.
The actual packaged CLI's complete ordinary photograph/master/sensor pixels match
the previously baseline-equal product16. Full 32-source photo/master bits match
with native sensor export off/on and match product17 legacy. A completed-output-
only UI grant successfully imported the new four-output result, saved/reopened
it and rendered an inspected actual GPU screenshot. These close the previously
pending native-export release/UI checks. The 24-source held comparison remains
unrun; new photographic HDR/SR/mosaic outcomes remain open. See the integration
report for exact commands, hashes, resource receipts and initial failures/fixes.
