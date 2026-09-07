# Production synthetic-truth path: read-only prior-art audit

2026-09-07, implementation_audit. Scope: current program step 3. No numbered
milestone, production edit, RAW/holdout access, renderer invocation, or commit.

**VERIFIED by source inspection:** no existing executable inspected here runs
an independently generated CFA focus bracket through the complete current
production Pyramid merge, curved per-frame gather, collapse, and TIFF writer.
The useful pieces already exist. The smallest missing engineering task is a
shared production input seam and a bounded commissioning fixture, not another
Python implementation of the merge or another general-purpose simulator.

## What the existing paths actually exercise

| Path | Actual implementation reached | Missing from the proposed benchmark |
|---|---|---|
| `strehl merge`, `merge_cmd::run` -> `run_pyramid` | Current default backend; four CFA planes, measured warped-noise floor, canonical chunk reduction, collapse, `write_merged`, demosaic/color/output | `main::raw_paths` admits only `.arw`; first-frame prologue and `load_frame` call `strehl_raw::decode` directly. There is no synthetic `FrameSource`/decoder injection seam. |
| `crates/strehl-cli/examples/blend-truth.rs` | `merge_multiband` calls the real `BandMerge::add_frame` and `finish`; `merge_selection` assembles actual `FocusField::compute` and `merge::regularise` primitives | One f32 green-luma plane, no CFA capture, no warp, no production `BandWorker`, no measured floor, no writer. The selection arm is an argmax control, not the complete current estimator and not the default backend. |
| `crates/strehl-cli/examples/build-demosaic-truth.rs` | `#[path]` includes actual `align_cmd.rs`; calls shipped full-resolution/plane warp and demosaic on synthetic `strehl_raw::Frame` | One analytic image and one similarity, no focus bracket or band merge. Default run later reads real captures; it is not a synthetic-only command. |
| `strehl-common-input --exercise-core-merge` | `CommonTiffFrame` identity checks plus one RGB input through three-channel `BandMerge` | Constant variance 1, one frame, no CFA/gather/canonical fold or rendered output. M165 is an identity/entry contract, not a complete common-TIFF production stacker. |
| `experiments/m25-simulator/src/strehl_sim/` | Independent NumPy/SciPy forward capture: per-layer defocus/diffraction, blurred alpha composition, pixel aperture, CFA, Poisson shot and Gaussian read noise | `focus.py` is a Python harness port. It does not call the Rust product. Historical optics/occlusion validation failed and may not be promoted by reuse. |
| `merge_cmd::synthetic_controlled` tests | Generates flat/detail noise for `cross_fitted_detail` and retention decision tests | No frame capture, alignment, merge or output is executed. Synthetic metric commissioning is not synthetic product commissioning. |
| `tests/byte-freeze.rs` | Actual CLI process and TIFF bytes, canonical/environment/placement integrity controls | Requires owner's real RAW inputs. Proves byte lineage, not known-scene reconstruction accuracy. |

Relevant current call graph, verified in the project's own source:

```text
main / raw_paths (.arw only)
  -> merge_cmd::run -> run_pyramid
     -> first decode; Frame metadata; profile::noise_model_for
     -> alignment_for -> WarpMap; cover_or_explain -> pyramid_domain
     -> canonical_band_chunks / band_workers
     -> BandWorker::fold
        -> load_frame -> decode -> optional defect correction
                      -> warp_frame_in_place -> gatefloor::Probe::measure
                      -> extract_planes [R,G1,G2,B] -> green luma
        -> luma_variance -> BandMerge::add_frame_with_gain
     -> absorb/reset canonical chunks -> BandMerge::finish
     -> write_merged(Merged::Bands) -> delivered TIFF
```

`load_frame` is deliberately shared with confidence passes. Injecting frames
only into a newly copied fold would miss this existing consistency guarantee.
`run_pyramid` also intentionally does not run estimator-only photometric gain,
clip census, outlier rejection, occlusion correction, or through-focus stages.
A benchmark must name the Pyramid consumer rather than claim all those paths.

Source lineage inspected: `merge_cmd.rs` last changed at
`a97275817c58e164f75c7cd3d80ca99444a2a145`; `blend-truth.rs` at
`74640d7d1f081bdfc83d3b564daafa73e5298985`; `build-demosaic-truth.rs` at
`5db5ac09e2aa7be6bbe1b4832cac552733f0aee9`. These are file-history references,
not claims that current binaries were rebuilt or run during this audit.

## Existing findings constrain reuse

1. **M25 is model-scoped, not a validated camera twin for every use.** Read
   `docs/research/M25-simulator-measured.md` opening verdict and SYNTHESIS
   facts 540–552. Its noise/selection validation can miss deleting diffraction
   entirely, and its occlusion mechanism failed its own gate. Source reuse can
   provide a declared synthetic forward model and catch software defects. It
   cannot establish real-camera optical accuracy or real occlusion fidelity.
   Do not call a wrapper around M25 an independent replication of M25.

2. **The Rust occlusion fixture already failed commissioning.**
   `BUILD-BLEND.md`, “The synthetic two-layer ground truth, and why its rim rows
   are inadmissible,” records a weak scene after three corrections: out-of-
   bracket background, smooth background null, and row-varying foreground
   depth. `blend-truth::run_scene` checks `potency < 20.0`, but only prints
   `SCENE NOT COMMISSIONED`; the rows were already printed, and it returns
  `Ok(())`. Thus a process-success gate cannot enforce this refusal. Preserve
  the historical finding. A future structured commissioning result must make
  the unadmitted scope impossible to mistake for a successful scene.
   The separate `roadmap_audit` agent independently inspected this branch and
   the one-channel `merge_multiband` call on 2026-09-07 and confirmed both
   limitations, without running the harness. In particular, the report's
   wording “refuses to report its edge rows” is not what the executable does.

3. **Do not mistake an oracle selector for an attainable pixel target.** The
   same BUILD-BLEND section says the depth oracle can be worse near the edge
   because no single frame contains both the desired sharp matte and the best
   background. `occluding_scene` builds a hybrid target from sharp foreground
   and least-blurred background. Report ideal latent reconstruction error and
   attainable control results separately; do not normalize by an unproved
   oracle floor or reinterpret a failed foreground/background regime as a win.

4. **Noise constants have drifted across harnesses.** M25's `config.Sensor`
   still defaults `read_noise_e_high=1.47`; production `profile::A7C2` uses
   `1.2392`. `blend-truth::synthetic_noise` hardcodes gain `0.62`, read noise
   `3.4`, ISO 200; that is a synthetic regime, not the production ISO-200
   profile. Its `render_frame` draws Gaussian noise with the injected green-
   luma sigma and clamps at zero, rather than independently exposing four CFA
   photosites with Poisson/read noise, black pedestal, white clipping and u16
   quantization. Freeze explicit producer parameters and production metadata;
   do not copy a stale “camera-like” claim. A plant sharing parameters with
   its gate tests the operator, never real sensor calibration (rule 34).

5. **M25 already accepts a curved scale series.**
   `render.render_stack(..., scale_series=...)` accepts every frame's scale;
   its linear default is expressly a convenience. `Breathing` supports a
   per-stack center and fixed translation/rotation; only scale is a per-frame
   series in this API. No new curved-scale renderer is needed. M103's
   `data/truth-dense.json` exists (8,491 bytes) and `src/curvature.py` describes
   its 39-rung curve. It diagnoses track curvature downstream of registration;
   it is not itself a scene renderer. Reuse that measured curve as declared
   shape input, with an explicit scale conversion for a small fixture; do not
   claim a scaled-down plant reproduced native placement severity. Every
   placement check needs the merge's per-frame gauge and an interior curvature
   check, not only equal endpoints.

6. **Forward truth still needs a coordinate/output adapter.** M25's
   `ground_truth` emits unwarped scene radiance and an ideal geometric-alpha
   target; it does not receive `scale_series`. Calling it “frame-0 geometry”
   requires an actual identity frame-0 transform or an explicit truth mapping.
   Its truth is not automatically a camera-linear or linear-sRGB TIFF target:
   producer channel scales, exposure, CFA sites, WB, crop origin and writer
   normalization must be accounted for. `RenderConfig.channels="green"`
   copies green into R/B and is explicitly invalid for demosaic; use `rgb`.

7. **Known useful controls should be retained.** BUILD-DEMOSAIC's analytic
   waves, non-unity WB, flat/noise, real chroma, planted false chroma, identity,
   and byte-identical re-gather control expose mistakes that gradient magnitude
   misses. M87 records an occlusion correction that improves its ISO metric
   while increasing truth error. M135/M164/M166 explain why a physical truth
   reference needs verified information advantage and external bindings; this
   development fixture does not replace that requirement. M63's bimodality
   refusal and M6's defocus residual interpretation also prohibit equating a
   low alignment residual or low edge statistic with correct reconstruction.

## Smallest next implementation, proposed rather than built

**ARGUED recommendation:** first add a private decoded-frame source seam to the
existing Pyramid path and one test-only synthetic fixture bridge. Keep the
ordinary RAW route as the default source. Do not implement a fake ARW encoder,
disguise a different container as ARW, or treat the common-TIFF identity binary
as the missing renderer.

Concrete candidate interfaces (names provisional):

```rust
trait PyramidFrameSource {
    fn len(&self) -> usize;
    fn decode(&self, index: usize) -> anyhow::Result<strehl_raw::Frame>;
}
// Shared production body after normal input/configuration preparation.
fn run_pyramid_prepared(
    opts: &MergeOptions,
    prepared: PreparedPyramid, // metadata/noise/domain/placements, explicitly bound
    source: &impl PyramidFrameSource,
) -> anyhow::Result<()>;
```

`merge_cmd.rs::run_pyramid` remains the production wrapper: resolve file list,
first-frame metadata, injected `NoiseModel`, alignment, defect plan and domain
once; pass a disk source into the shared body. Route `load_frame` and
`BandWorker::fold` through the source, retaining the existing post-decode
correction/gather/variance/floor logic, canonical chunk boundaries, collapse,
and `write_merged`. Any confidence pass supported by the new seam must use the
same source. Refuse unimplemented test modes rather than silently substituting
disk reads. This is a source substitution, not a second merge algorithm.

A `#[cfg(test)]` child module under
`crates/strehl-cli/src/merge_cmd/production_truth.rs` can access private stages
without turning the entire CLI into a library or shipping a new user flag.
Its source reads frozen, plainly identified u16 CFA fixtures or regenerates one
frame from explicit fixture data at a time, and constructs `Frame` using the
existing public struct. `WarpMap::new` already accepts per-frame
`FrameWarp::Placed(Similarity)` and explicit provenance/reference. The fixture
can therefore exercise known placement/gather and the current output path while
clearly excluding live registration and the RAW decoder from its claim.

Keep the producer outside production math: import existing M25
`scene`/`render`/`sensor` modules through a small prospective wrapper, supply a
frozen curved `scale_series`, full RGB/CFA rendering, explicit noise parameters
and independently chosen scene seeds. Reuse the BUILD-DEMOSAIC analytic flat and
color controls where they are cheaper than a full scene. Preserve old files and
their failed gates. If M25's optics or occlusion commissioning cannot support
a requested scope, narrow the benchmark to the declared forward model and leave
that physical scope unmeasured; do not claim the old refusal disappeared.

Proposed first size is a small non-square sensor grid and a short bracket with
several distinct best-focus regions, both occlusion polarities, texture, and
true flat tiles. Freeze exact dimensions/seeds/levels/transforms/regions and
admission bars before any candidate admission change. The known-curvature
track must visibly depart its chord on this grid. Do not run a native 299-frame
scene merely to establish this software seam.

## Falsifiable commissioning required before candidate tuning

- **Actual-path control:** a disk-source delegation and its source-seam
  equivalent must deliver byte-identical TIFFs and identical frame counts,
  domain, environment and reduction metadata. For synthetic inputs, change one
  upstream frame, placement, or output setting and require a visible output
  hash change; a constant-output or discarded-input wrapper must fail. A
  later authorized real byte-freeze checks the refactor's native lineage; this
  audit does not authorize or run that corpus check.
- **Flat first:** use fixed latent flat regions across independent sensor-noise
  realizations. Report output bias and per-site temporal variance, not spatial
  sd. Zero-noise control must show its quantization/demosaic floor; adding
  independent noise must increase temporal variance. Change only the emitter's
  gain/read-noise law while leaving the production model fixed and require a
  mismatch diagnostic. This validates simulated data flow, not camera gain.
- **Fidelity and gaming controls:** report delivered linear RGB reconstruction
  error, boundary-band error and flat temporal noise separately. Inject output
  blur, directional sharpening, false chroma, boundary flattening, and noise
  amplification; a score cannot trade lower flat noise for invented detail or
  boundary loss. Known truth substitution supplies the positive control, but
  an ideal target is never silently called an attainable estimator.
- **Geometry control:** correct per-frame transforms, identity, an interior
  curved-track perturbation with unchanged endpoints, and a constant wrong
  crop origin. Check all admitted sites in the writer's gauge. The curved
  perturbation and crop error must increase matched truth error; if they do
  not, the stimulus lacks power. The planted inverse transform must come from
  explicit coordinate algebra, not from running the production interpolator
  backwards to create its own inputs.
- **Forward-model control:** freeze blur-before-composite and pixel integration
  order. Compare a small independently calculated PSF/alpha case and sample
  convergence before relying on boundary truth. Deleting diffraction or
  swapping compositing order must fail the declared forward-model check, even
  if a merge-noise statistic stays unchanged. M25 already proved that the
  latter statistic cannot commission optics.
- **Scope and evidence control:** exact input/producer/product/manifest hashes,
  all invocation/environment settings, every registered repeat and refusal,
  machine-readable failure status, and an independent reviewer who re-chooses
  scene aspect ratio, color/geometry, noise seed and failure plant. Keep v1
  renderer warnings/refusals in the record; none may become a “PASS” merely
  because a process exited zero.

These are proposed kill conditions, not acceptance results. Their quantitative
bars and the fixture must be registered and commissioned before comparing one
production admission change. No new SOTA axis follows from passing them.

## Commands and scope of this audit

Run successfully:

```powershell
python experiments/ORCH-drift-check/prior_art.py production synthetic truth defocus occlusion
git log -1 --format="%H %s" -- crates/strehl-cli/examples/blend-truth.rs
git log -1 --format="%H %s" -- crates/strehl-cli/examples/build-demosaic-truth.rs
git log -1 --format="%H %s" -- crates/strehl-cli/src/merge_cmd.rs
```

`rg` inventories and `Get-Content` inspected the files/symbols named above.
The prior-art command surfaced M87, M63, M79, M135, M6, BUILD-DEMOSAIC, M164,
M166, M84b and M136, with M25/BUILD-ELECT/BUILD-SHARP also listed. This audit
followed the reports relevant to the implementation seam and recorded their
prior refusals; it did not rerun their claims.

Existing documented commands, **inspected but not run here**:

```powershell
cargo run --release -p strehl-cli --example blend-truth
cargo run --release -p strehl-cli --example build-demosaic-truth
cargo test -p strehl-cli --test byte-freeze
```

The second command includes real-capture stages with default external paths;
the third is a real-RAW integration test. The first prints a failed-scene warning
without failing the process. None is the requested commissioned complete
synthetic production benchmark today. No compilation, timing, image-quality or
render-memory result is claimed from this read-only audit.

## Root continuation: producer channel scope

**MEASURED exploratory API control, 2026-09-07:**
`python -B experiments/review-production-truth/producer-scope.py` exits zero
with the expected four dispositions in `producer-scope.json`. A 9x13 scalar
scene works with identity and scale1.01. A spatial RGB array passes the early
identity return but fails scale1.01 with `ValueError: too many values to unpack`.
`similarity_warp` unpacks two dimensions; `render_stack` then applies its fixed
`channel_scale` to the same radiance array at three wavelengths. Thus selecting
`channels="rgb"` does not establish arbitrary spatial RGB scene support.

The fixture's three channels are deliberately distinct. An identity-only API
test would miss this failure. This is an exploratory compatibility observation,
not optical or full-renderer commissioning. Reuse the current producer only
within its scalar-radiance scene scope, add separately commissioned chromatic
controls, or explicitly implement and verify a prospective channel extension.
Do not silently promote the `Layer` docstring's advertised 3D shape into an
executed RGB-bracket capability. The frozen M25 source remains unchanged.

**VERIFIED separately by directional_detail:**
`python -B experiments/review-production-truth/independent-producer-scope.py`
re-chooses 17x26 dimensions, spatially distinct RGB channels, a different centre,
linear interpolation, translation and rotation. Scalar nonidentity controls
produce finite changed outputs; the translated ramp has its independently
predicted interior value. Both nonidentity RGB calls raise the same dimension
error; identity returns the supplied array. The independent JSON retains all
dispositions and unchanged M25 source hashes. This corroborates API scope only.
