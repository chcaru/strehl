# AGENTS.md — Strehl

Noise-aware RAW focus stacking in Rust, with a CLI and desktop workspace.
Keep storage as u16 CFA and arithmetic as f32; gather aligned samples at the
consumer and demosaic once. Camera/sensor calibration belongs in data profiles;
fit stack-dependent geometry at runtime.

## Read what the task needs

Start with [README.md](README.md) and [CONTRIBUTING.md](CONTRIBUTING.md) for current
builds and normal product behavior. Read
[the decision record](docs/research/SYNTHESIS.md) before architectural changes;
it records rejected approaches as well as decisions.

| Task | Additional reading |
| --- | --- |
| Pipeline, RAW, noise or alignment | [Architecture](docs/ARCHITECTURE.md); relevant [engineering rules](docs/agents/engineering-ledger.md) |
| Experiment, measurement or research review | [Research workflow](docs/agents/research-workflow.md); relevant engineering rules |
| Research lookup or milestone allocation | [Research guide and topic indexes](docs/research/README.md); [milestone ledger](docs/agents/milestone-ledger.md) |
| Continuing a recorded experiment | Its actual brief/results; [dispatch history](docs/agents/experiment-history.md) |
| Capture data, sensor levels or new capture request | [Capture reference](docs/agents/capture-reference.md); [captures needed](docs/captures-needed.md) |
| Desktop or binary distribution | [Desktop README](crates/strehl-ui/README.md); [build guide](docs/desktop-build.md); [release checklist](docs/public-release.md) |
| Pinned native research renderer | [Native workflow](docs/native-rendering.md); separate from normal CLI/desktop builds |

Historical citations to **AGENTS rule N** resolve to
[engineering-ledger.md](docs/agents/engineering-ledger.md) at `#rule-N`, including
`#rule-31b`. Original numbers, amendments and retractions remain there. Read the
entries applicable to your task; do not load every historical brief by default.

## Source-license restrictions — before opening another repository

Strehl is **MIT OR Apache-2.0**. Project policy prohibits consulting or copying
these implementations, including when researching an algorithm:

| Do not open/read/browse/copy source | License |
| --- | --- |
| enfuse / enblend; `align_image_stack` / Hugin | GPL-2.0 |
| EPFL Extended Depth of Field; ChimpStackr | GPL-3.0 |
| darktable, including `exif.cc`; RawTherapee; ART; Filmulator | GPL-3.0 |
| `librtprocess`; ExifTool Perl source | GPL-3.0 |
| `rawler` / `dnglab` source (link only) | LGPL-2.1 |

Safe to read: PetteriAimonen/focus-stack, z-stackr, stackaroni and `rawkit`
(MIT/Apache-2.0). Do not link AGPL `dssim`; use `ssimulacra2` and `butteraugli`.
ExifTool tag-table pages are generated from GPL source: tag IDs, offsets and
enum values may be used as facts; do not copy their surrounding prose or read
Perl source.

For `rawler` distribution, use dynamic linking or provide the required object
files/reproducible rebuild route and corresponding source/notices described in
[the decoder notice](docs/raw-decoder-notice.md). Do not distribute a lone
statically linked executable. Use the source-inclusive packaging workflow.

## Engineering invariants

- **Storage u16 CFA; arithmetic f32.** Never store f16. Never materialize an
  aligned-frame volume: gather inside each consuming kernel.
- **Inject one noise model.** Do not derive private per-stage estimates. Compute
  statistics only over the decoded active area, never synthetic buffer padding.
- **A regularized selector is still a selector.** Do not use raw per-band argmax
  as a merge reference or an unquestioned "best frame" analysis baseline. Keep
  the noise-gated averaging requirement; do not justify a value-admission gate
  with index-map speckle or claim argmax always flees clipping (ledger rule 4).
- **Fit geometry at runtime.** Do not bake scale drift or its center into a
  profile. Do not chain alignment edges or rely on one fixed reference for a
  deep stack. Solve direct pairwise fits globally in the anchor's connected
  component; report unplaced frames and check cycle rank before comparing with
  a chain. Do not transfer a fitted shrinkage correction across scenes.
- **Score alignment where the merge consumes it:** per-frame placement, with
  gauge/reference and pixel scale stated. End-to-end improvement does not
  establish placement improvement. Short edges are biased but load-bearing;
  span discard is a known-harmful stopgap, not a result to generalize. Synthetic
  alignment plants must carry measured curvature (rule 6 and its M103 amendment).
- **Keep capture corpora read-only.** Put outputs, caches and maps outside them.
  Isolate CLI alignment with `STREHL_WARPMAP`; `align --out` alone is insufficient.
  A map pins its resampler too: for kernel comparisons use a fresh isolated map
  per arm or an isolated input copy; never write a shared capture sidecar.
- In Python RAW loaders, copy `raw_image_visible` **inside** the `RawPy` context;
  make decoding checkable against an independent decode. Use
  `python -X faulthandler` for native crashes. Apply spatial filters to 2-D planes
  explicitly: separable filters on a frame cube can smooth the frame axis.
- Use **plugin halo** for filter rectangle expansion and **occlusion halo** for
  edge artifacts. Use kebab-case for new files/directories and `strehl-*` crates;
  preserve existing historical names and references.

## Evidence and verification

- Every quality/performance claim needs the command actually run. Label claims
  **MEASURED / VERIFIED / DERIVED / ARGUED / UNVERIFIED**; record input identity,
  resolved flags/defaults, relevant environment, worker count and build identity.
- Before using a gate or metric, specify an input that makes it fail and exercise
  it. Run flat-ROI controls **first** for sharpness. State the direction a metric
  can be fooled; gradient energy alone cannot establish quality. Use a causal
  placebo and test the code path producing each headline.
- Compare temporal sigma with like quantities; spatial standard deviation carries
  scene structure. Check sigma against the injected model. A fitted constant
  cannot validate its own model, and a plant cannot validate its own calibration.
- Independent research verification must challenge choices of estimator,
  reference, arm, null and defaults, not only repeat arithmetic. Author-run
  implementation checks do not replace independent review of conclusions.
- Inspect complete outputs and native crops with identical display transforms.
  Commission the viewer; historically crops of about 400 px or smaller avoided
  resampling. Record origins/sizes; resized overviews are orientation only.
- Follow [the research workflow](docs/agents/research-workflow.md) before dispatch,
  publication or a SYNTHESIS fold. It covers prior-art search, allocation,
  falsifiable controls, numbering/content checks and mandatory fold checks.

## Build, test and shared-work hygiene

Run checks appropriate to the changed path. For example, for an engine change:

```powershell
cargo test --locked -p strehl-core
cargo clippy --locked -p strehl-core --all-targets --no-deps -- -D warnings
cargo fmt -p strehl-core -- --check
```

Select the affected crate; desktop work also needs actual UI exercise. See
CONTRIBUTING for private-corpus test limitations. Documentation-only changes
need link/content/structure checks; do not run RAW campaigns for them.

- Never use Cargo `-q` for evidence. After edits/restores, ensure affected code
  rebuilds; refresh restored mtimes or force a targeted rebuild if needed.
  Look for **Compiling** on build/test/run, **Checking** on check/clippy, and
  **Documenting** on doc. Do not mistake cached results for the edited code.
- Capture native output and `$LASTEXITCODE` immediately, **before** piping output
  through `Select-Object -First` or other display filters. Assert the exact
  expected exit code, including for intentional failures.
- Preserve unrelated work. In a shared tree, scope commits with
  `git commit -- <paths>`, never a bare commit of the shared index or `git add -A`.
  Audit with `git show --name-only`; do not rewrite history to repair a sweep.
- Only the root orchestrator schedules lanes. Ignore/report peer holds or locks;
  never terminate a process you did not start. Before declaring a run dead,
  state how a healthy run would differ at that instant. After a kill boundary,
  discard and rerun affected measurements; check artifact completeness, not just
  parseability. Record host load for timings.
- When editing structured Markdown, account for deletions, preserve anchors and
  headings, check all table rows, and leave exactly one final newline.

## Repository map and instruction maintenance

| Path | Purpose |
| --- | --- |
| `crates/strehl-core/` | Noise, geometry, focus and merge types/operators |
| `crates/strehl-raw/` | RAW decoding behind the linked decoder |
| `crates/strehl-plugin/` | Focus-measure extension and host calibration surface |
| `crates/strehl-cli/` | CLI and engine orchestration |
| `crates/strehl-edit/` | Shared editing and development model |
| `crates/strehl-ui/` | Desktop workspace |
| `docs/research/`, `experiments/` | Decision record, reports, scoped experiment sources/results |
| `docs/agents/` | Detailed engineering rules, reference indexes and allocation history |

Keep this file a concise working contract. Put new rationale/incidents in the
engineering ledger, allocate identities in the milestone ledger before dispatch,
and keep detailed briefs/results with their experiments. Preserve rule numbers
for existing citations. Historical assignments do not authorize new work; the
October 17 pause/deferred scopes are recorded in the dispatch history.
