# Production reconstruction consumer review, checkpoint 01

Independent source review; no CLI/core source edits or RAW/engine jobs by this reviewer. This is not photographic validation. The root is building release12 from this checkpoint and will fix the confirmed graph defect after the snapshot. Exact source identities are below.

## Findings requiring implementation or controls

1. **Confirmed graph coverage defect** (`session-reconstruction-consumer.rs`, pair construction near lines123–126). A star plus adjacent original source indices does not guarantee a triangle for every leaf. With four sources and anchor1, edges01,12,13,23 leave source0 without a triangle. Only3 sources qualify, while native-size red/blue reconstruction requires4 acquisitions; every otherwise-good pixel consequently falls back. With3 sources and anchor1 there is no triangle at all. Root confirmed the defect. Connect neighboring non-anchor leaves and exercise all anchors for source counts3,4 and larger. Do not relax the triangle or per-channel acquisition gate to hide this failure.

2. **Retained report memory is not explicitly bounded** (`session-reconstruction-consumer.rs`, `reports` and final `tiles.json`). The numerical phase budgets account native output buffers, caches and per-worker scratch conservatively, and merge workspaces are explicitly dropped before reconstruction. However, a Vec of full JSON tile reports retains up to64 per-source certificates per tile. Dense depth boundaries can force32-by32 native tiles while leaving50–64 candidates in each accepted tile. These variable-size JSON trees can exceed the fixed512MiB metadata allowance plus the small unused fraction of128bytes/quad. Stream the tile array with a bounded buffered writer, or derive and reserve a checked bound for all tile/source certificates before allocation. Also account the retained tile plan. A concrete negative control should force many small tiles with maximum source lists under a deliberately tight memory budget.

3. **Local work currently traverses complete source planes** (`process`, both NativeSampler gathers). The guide and motion fields need only a tile plus halo, but each gather converts all four full original planes. Roughly4,000 tiles times8 sources times8million quads gives order10^12 full-plane operations. This is a performance risk, not evidence that the photographs are wrong. Measure a representative cohort before dispatching a full scene; a local original-sample gather can preserve exact coordinates, clipping stencils and interpolation while eliminating unrelated full-plane conversion. Keep an exact current-versus-local numerical control.

4. **Focus-summary coordinate binding should be explicit** (`session-reconstruction-plan.rs`, `FocusSummary::from_evidence`). Original ordinal/global-index binding is retained and sources are not compacted. The summary drops geometry, however, and the planner checks only vector lengths. The current compute_pass caller supplies the same domain, so this is a defensive API gap rather than a demonstrated wrong output. Carry/check the SamplingDomain and exercise equal-length maps with a different crop origin or dimensions.

## Checked behavior and remaining scope

- Current window_fits duplicates the original-patch boundary calculation, including per-color site offset and full-grid center. Unsupported edge windows are skipped and can retain native output; they do not currently propagate the active-area error as a whole-image failure.
- The graph's consuming_color_pulls currently equal the saved, directly qualified pulls. Motion sampling on the saved map is therefore in the same gauge. A future local correction must update the actual sampling fields too.
- The guide acquisition set is outside the complete tile target union. It is chosen before candidate evaluation. This avoids reusing target photons as precision predictors, but focus/motion admission remains adaptive, guide blur is only an expected-signal approximation, and no unconditional delivered variance is established.
- Guide validity is the intersection of complete unclipped original support after the blur/derivative halo. Target validity likewise requires complete all-color support before a candidate is allowed. The original-CFA kernel checks its own actual raw samples and per-color acquisition/phase criteria.
- Native RGB is developed once. Refused pixels are never round-tripped through the inverse normalization: the output loop writes only coherent all-RGB successes into the original camera-RGB buffer. Matrix/highlight/tone remain common, and tone is frozen from the unchanged native mosaic. The None branch continues through the existing writer.
- Explicit primary selects a preferred local anchor and retains native output where a qualified primary has no supported local source. This is a support rule, not an independent guarantee that changed content preserves primary appearance; a translated/occluded secondary-content control remains necessary.
- Support is a native-size Gray32Float0/1 map. Fallback codes describe the first refusing color or an outer refusal. registration_supported_tiles counts a geometric tile qualification and does not imply that every pixel in that tile was replaced. No resolution or native-relative noise-gain claim follows from these counts.
- Partial failures cannot create a completed render: maps and geometry precede the photograph/master and render report, and final binding/completion remains the caller's job. The new reconstruction source files are included in renderer_source_sha256.

## UI/schema checks actually run

The concrete schema fixture is [reconstruction-contract-example.json](reconstruction-contract-example.json). Its map receipts refer to actual tiny synthetic TIFFs under outputs/multi-stack/completion/reconstruction-schema-example, explicitly marked example_only. It is not a completed render or quality result. Current consumer field names, native canvas origin/step, local receipt filenames, geometry SHA, reason labels and counts match the UI reader.

Commands actually run from the active worktree:

```powershell
python -X utf8 experiments/multi-stack-2026-10-28/run-command.py --receipt outputs/multi-stack/completion/ui-reconstruction-session-controls-03 --cwd . -- cargo test --locked -p strehl-ui session_ -- --nocapture
python -X utf8 experiments/multi-stack-2026-10-28/run-command.py --receipt outputs/multi-stack/completion/ui-reconstruction-saved-controls-01 --cwd . -- cargo test --locked -p strehl-ui saved_ -- --nocapture
```

VERIFIED: session controls43passed, saved controls34passed, both exit0 and both logs contain fresh Compiling strehl-ui. Session run also compiled CLI; saved run rebuilt core/raw/plugin/CLI/UI. The earlier session-controls01 compile error in the reviewer's SHA formatting and session-controls02 missing in-progress CLI module are retained; neither is reported as passing. Controls include incompatible modes before catalog mutation, immutable flags, checksum/schema/gauge/census refusals, support labels, actual egui overlay clipping/navigator exclusion, and identical cyan/orange trace/label colors. New wording explicitly says overlay colors are sampled for display while hover/click reads the exact saved cell. Actual GPU verification of these new changes awaits the next released binary.

## Reviewed source SHA256

- `crates/strehl-cli/src/session-reconstruction-plan.rs`: `d3c578f69c7ba5de479db9d8f8e315de47785e3f0a8810cf53092044946b040d`
- `crates/strehl-cli/src/session-reconstruction-consumer.rs`: `99ce052f0f61e46cb763f446c7ba170293874549f9a34926cf0701f42b22bed8`
- `crates/strehl-cli/src/session-reconstruction-output.rs`: `6908b816878e9d5979cb80e7351d3f59a9429b565f680f37e9b01b78bff2c2e7`
- `crates/strehl-cli/src/session-consumer.rs`: `130144155501bdc00c3a8fc45fb8ae0b568cd9a81f0b8c5772f493f66688b124`
- `crates/strehl-cli/src/merge_cmd.rs`: `7a498413de8e2911c73aa3a06df7e642bd50d60f45ba44b8e81434eca60703ef`
- `crates/strehl-cli/src/session-cmd.rs`: `7712f227b9d175949ec8057be9ea2c9f43edca0cb91a976fe156be174b26e836`
- `crates/strehl-core/src/reconstruction.rs`: `d7392a43d71cb04feb77269de2ff47e1cbcf7c9c822e472c820b520d4484a6ea`
- `crates/strehl-core/src/reconstruction-registration-graph.rs`: `1576c15f2bdae3b44b3cfb41f6e03ee64a49235190cfe428eca8cb64520f05b4`
