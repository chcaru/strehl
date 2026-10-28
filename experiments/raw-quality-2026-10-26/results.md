# RAW quality continuation: current evidence

2026-10-26/27. Active program. Independent complete-image review finds a modest weevil hair-fringe improvement from disabling the applied CA profile, but the same intervention visibly worsens another complete insect stack. This is not a general repair or a solution to softness. The user prioritizes generally applicable insect quality; weevil107 is the first complete acceptance stack. Flower, mineral and diagnostic transfer remain required. Prepared marigold visibility work is held while insect evidence is resolved.

## Baseline and source identity

VERIFIED latest remote main was fetched and pulled into the isolated `codex/raw-quality-october26` worktree at `4813e46bdc9aaf5f9220115911df5cd5aa3fd808`. The original shared checkout was preserved. The complete299-source weevil107 baseline has a6896x4596 RGB16 sRGB master, a pre-tone RGB32-float master and the complete original-source manifest. Commands, map, environment, build/executable identity and all-source before/after hashes are under `../../outputs/raw-quality-2026-10-26/weevil-107-baseline/`.

MEASURED command:

```text
python -X faulthandler experiments/raw-quality-2026-10-26/render-cpu.py --input D:/personal/macro/insects/bug-3/107MSDCF --out outputs/raw-quality-2026-10-26/weevil-107-baseline --exe target/release/strehl.exe --sha256 89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388
```

All299 frames placed, reference149, Catmull-Rom, native full-resolution gather, four workers. Alignment128.266s and rendering322.453s are operational receipts, not isolated speed comparisons: build/check work overlapped part of rendering. Held-out alignment residual3.3588px does not measure true per-frame placement accuracy. Master SHA256 `ecfae13e937f44445f3fe2a83a2e72861c4cd6cd9f56f02139f3f5e3dc0f9665`.

Independent baseline review freezes ten native384x384 witnesses after complete-image orientation. See `photo-review/baseline-review.md`. The first three source frames (0,149,298) do not establish erased genuine scale structure; the ends are defocused at these sites and149 only partly focuses the upper leg. This is insufficient evidence about source availability elsewhere in the299-frame bracket, not a capture ceiling.

## Fixed direct-CFA recipe rejected

The experimental original-CFA sampler uses same-color cubic R/B lattices and both greens on their quincunx lattice, immutable u16 source storage, f32 arithmetic and the existing geometry/CA/writeback. It remains opt-in and defaults are unchanged. The independent generated suite preserves integer samples, active-area bounds and noise transport but exposes substantial fine neutral detail loss. Passing implementation tests is not acceptance of its quality.

Exact execution commands, exit0:

```text
cargo test --locked --offline -p strehl-core cfa_lattice -- --nocapture
cargo check --locked --offline -p strehl-cli --lib --features direct-cfa-gather
cargo test --locked --offline --release -p strehl-cli --features direct-cfa-gather --lib cfa_lattice_independent_suite -- --nocapture --test-threads=1
cargo test --locked --offline --release -p strehl-cli --features direct-cfa-gather --lib unchanged_green_residual_falsifier -- --nocapture --test-threads=1
cargo test --locked --offline --release -p strehl-cli --features direct-cfa-gather --lib cfa_integration_tests -- --nocapture --test-threads=1
```

Fresh Compiling/Checking appears in the corresponding `../../outputs/raw-quality-2026-10-26/cfa-*.log` records. Build workers8. Integration tests used unset STREHL_FIX_CA and STREHL_WARP_WRITEBACK; the latter resolves parallel. Three actual-warp/writeback controls pass, including a nonzero active origin, colored padding, below-black samples, fractional similarity, CA, immutable greens and missing-domain refusals. The file-identity-to-CA lookup is source-reviewed, not independently exercised by injected metadata. Existing unrelated test-only dead-code warnings remain.

MEASURED flat controls ran first: aggregate empirical/independent expected noise variance ratios1.013393 and1.014309 at DC1000/4096. These are generated injected-model controls, not sensor calibration. Neutral gratings at0.18 and0.30 native cycles/pixel lose detail despite some pure-color gains. No full candidate photograph was rendered from this failed recipe.

A single changed residual question was then closed. Giving the recipe perfect R/B values cannot repair its unchanged measured-green sites: the frozen0.30cyc/px,73degree fixture has baseline green RMS35.0052795DN, direct67.0886701DN, and perfect-R/B67.0886701DN. This rejects that unchanged-green extension, not every joint RAW reconstruction or color-difference method. See `cfa-residual/results.md`.

## Competitive workflow

MEASURED two retained developed TIFFs were submitted to installed Helicon8.3.11. The sandboxed process exited1 with no output; normal application-data access succeeded with exit0 and a7032x4688 RGB16 TIFF. The complete orientation view shows no obvious promotional overlay. This is a compatibility witness only. Source TIFF hashes remain unchanged. It does not establish RAW decoding support or a quality result.

```text
python -X faulthandler experiments/raw-quality-2026-10-26/comparator/helicon-witness.py
python -X faulthandler experiments/raw-quality-2026-10-26/comparator/helicon-witness.py helicon-witness-app-access
```

The latter child process ran with normal application-data access. Its log identifies a valid trial and absent Adobe DNG Converter; no install, purchase, licensing reset or activation was performed. The complete weevil comparison is being prepared using all299 RAW sources, the product decoder/MHC/developer, fixed WB and common logged tone. Premerge development and external alignment/CA differences must accompany any comparison. Full workflow costs include development; vendor merge-only time is not compared with native total time.

### Completed competitive workflows and source attribution

The complete299-source exporter and both vendor arms subsequently completed. Each produces a7020x4676 RGB16 master with the same ICC as native. Application logs enumerate all299 intended TIFF filenames: B has598 processing rows across forward/reverse passes; C has299 ascending rows. Invocation arguments are retained; the opaque vendor does not expose an independent internal-method trace. Corresponding native crops are original unresampled pixels; subject scale differs by about2percent. See `comparator/photo-review/independent-results.md` for the complete outputs and all ten comparisons.

Independent review finds local hair-separation advantages in B with persistent colored contour fringes and similar rounded scales. C adds bright glint spill and colored angular/diagonal dark-background traces. Neither is a clean SOTA target. These comparisons do not isolate merge algorithms because CA, placement and premerge tone differ.

Operational child-process wall times/peak Job commitment: native alignment128.266s/9.44GiB; native merge322.453s/2.71GiB; source development211.109s/0.39GiB; vendor B46.703s/33.26GiB; vendor C35.329s/31.26GiB. Vendor processing excludes the required development and about55GiB of prepared TIFF storage. Development plus vendor child work totals257.812s(B) and246.438s(C); verification/wrapper work adds cost. Different worker counts, host overlap and cache state prohibit an isolated speed ranking. Commands:

```text
cargo build --locked --offline --release -p strehl-cli --example weevil-batch-develop
python -X faulthandler experiments/raw-quality-2026-10-26/comparator/run-weevil.py develop --exe target/release/examples/weevil-batch-develop.exe --sha256 fdf14eebef1164c59362c503f73c0506fa2a263055516f4e0f2272935721ebdf --build-log outputs/raw-quality-2026-10-26/weevil-export-build.log
python -X faulthandler experiments/raw-quality-2026-10-26/comparator/run-weevil.py b
python -X faulthandler experiments/raw-quality-2026-10-26/comparator/run-weevil.py c
```

The full-source locator identifies contiguous focus neighborhoods, then inspects persistent structures across neighboring native source views. It does not create an argmax reference image or establish a source-detail ceiling. See `photo-review/source-neighborhood-results.md`.

Actual source149 gather capture then isolates added colored hair separation before merging. Its separate CA-off control returns all31,694,016 delivered CFA sites exactly unchanged from the original; the CA-on capture changed R/B. The stored anchor transform retains tiny gauge roundoff; an initial exact-identity assertion failed before decoding and was replaced by an exact frozen-bit check, never by changing the transform. This establishes the applied profile's role in the one-source fringe change, not an optimal optical coefficient.

VERIFIED by independent complete-image and ten frozen native-witness review: the complete299-source CA-off ablation modestly reduces orange/blue separation along some weevil hairs while preserving visible strands. Soft scales, hard glints, pale occlusion contours and background specks remain. Same frozen executable/map/input order/crop; original hashes remain unchanged. Original master SHA256 `5dc571cce0d9e310f1f06b6e7f3c78faae8fb4ee4f12c94ff76d1d0c0e3fb655`,6896x4596. The review uses both linear masters through fixed gain3.434 and the same sRGB transfer, avoiding the different automatic tone placements. Complete common-display masters and JPEGs are under `photo-review/ca-off-review/{baseline-ca-on,ca-off}/`; see its `review.md`, `visual-review.json` and `common-display-receipt.json`.

The separate complete299-source bug2/100 transfer pair uses the same frozen executable and one map, delivered6566x4376. Independent review froze ten baseline witnesses and gain4.993 before reading the candidate. CA-off increases red/cyan splitting on pale flecks and fibres on both sides of the frame. Orange networks remain soft/hazy, and seam/occlusion contours and background streaks persist. This rejects a blanket default change despite the local weevil benefit; it does not establish an optimal CA model. Full pairs and receipts are under `photo-review/bug2-transfer/`. Commands actually run:

```text
python -X faulthandler experiments/raw-quality-2026-10-26/render-ca-off.py --input D:/personal/macro/insects/bug-3/107MSDCF --out outputs/raw-quality-2026-10-26/weevil-107-ca-off --exe outputs/raw-quality-2026-10-26/baseline-strehl.exe --sha256 89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388 --warp-map outputs/raw-quality-2026-10-26/weevil-107-ca-off-alignment.txt
python -X faulthandler experiments/raw-quality-2026-10-26/render-cpu.py --input D:/personal/macro/insects/bug-2/100MSDCF --out outputs/raw-quality-2026-10-26/bug2-100-baseline --exe outputs/raw-quality-2026-10-26/baseline-strehl.exe --sha256 89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388
python -X faulthandler experiments/raw-quality-2026-10-26/render-ca-off.py --input D:/personal/macro/insects/bug-2/100MSDCF --out outputs/raw-quality-2026-10-26/bug2-100-ca-off --exe outputs/raw-quality-2026-10-26/baseline-strehl.exe --sha256 89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388 --warp-map outputs/raw-quality-2026-10-26/bug2-100-ca-off-alignment.txt
```

### Insect placement attribution and next consumer

MEASURED the fixed two-gap observation completed its flat, translated-boundary, stationary-defocus and changed-glint controls, then refused every nominated actual green profile. Three original sources104/105/106 were independently staged as u16; source105 agrees exactly with the retained second decoder. A cached four-phase inspection shows the nominated centers lie on bead flanks/bright beads rather than the prescribed dark gaps. Green structure is strong. There is no displacement estimate, no evidence of zero misplacement, and no evidence of color-only structure from this observation. No warp follows. See `insect-placement/results.md`; root commands were `python -B -X faulthandler experiments/raw-quality-2026-10-26/execute-placement.py controls`, `stage`, and `measure`.

The separately prepared shared-color focus guide changes the current Laplacian consumer's common weight to normalized R/G/B evidence while retaining the original CFA coefficients and reconstruction. This is a general prospective hypothesis, not an established cause of weevil softness. Independent source review added a noiseless color companion to distinguish deterministic false green from the loss of green noise averaging caused by shared color-driven weights. Numeric guards remain unchanged. See `insect-color/independent-review.md` and `root-observation-policy.md`; a generated screen cannot complete the photographic objective.

MEASURED / independently reviewed: that screen now completes and rejects the exact recipe for a full299-source observation. Flat RGB error is approximately0.94 times canonical and the fixed neutral/crossing guards pass. The cofocused color positive improves visibly, but the ISO400 different-source adverse loses blue recovery from0.52125 to0.40710 while strengthening red. This21.9% loss of previously retained structure is beyond the prospective green-noise tradeoff exception. The noiseless joint green error is1.595 times canonical but close to its identified focused-source witness; do not label it newly invented merge false-green or explain it as noise alone. All generated complete views and the independent conclusion are in `insect-color/independent-results.md`. The source-only full-cost adapter remains uncompiled, unrun and held. No full candidate photograph or product-default change follows.

Actual commands were `python -B -X faulthandler experiments/raw-quality-2026-10-26/execute-color.py build`, then `execute-color-observed.py`, then `execute-color-post-cleanup.py`. Cargo freshly compiled core/CLI/GPU dependencies and emitted a completed test artifact after4m20s. The first build wrapper nevertheless reached its900second bound while draining one owned descendant after Cargo exit0/pipe EOF, then terminated that descendant. Its wall time is not a build-performance result. A separately recorded cached Cargo invocation exited0 and retained the same executable SHA256 `b122a2c720de6880ceece6ae59eb95e5bdea4b0fc3d3ac269753690540476109`. After the cleanup boundary, the entire screen ran again in a fresh owned job, exit0,4.344s and400,412,672bytes peak job commitment; all66 generated float outputs are byte-identical to the independently inspected first screen. See the post-cleanup `replay-equivalence.json`. Test-process success remains distinct from the false quality-admission flag.

Root changes the next research question to continuous thin-structure visibility, under `ribbon-visibility/brief.md`. This is source preparation for a bounded original-CFA forward/inference prototype with independent truth, not a new photographic result. The objective remains substantial gains on complete real stacks; no tested change yet solves the main softness, glare, ghosting or occlusion-halo defects.

That bounded prototype subsequently completed through `python -B -X faulthandler experiments/raw-quality-2026-10-26/execute-ribbon.py`: exit0,13.172s,2,741,702,656bytes peak job commitment. The GPU consumer preserves original-u16 observations, f32 arithmetic and shared pupil/footprint first-hit visibility. Independent generated truth and a73-evaluation conditional fit retain both thin structures and their crossing; held prediction RMS1.150sigma and dense independent64-query held RMS1.157sigma qualify this small model. Fitted widths still trade with radiance, flat validation is forward-only, and automatic topology/mismatch refusal remain absent. The independent review withdrew the proposed marigold transfer because two constant-color capsules cannot represent its broad curved surfaces. No original-photo fit or halo-repair claim follows. See `ribbon-visibility/results.md`, complete generated float masters and matched full-domain previews.

Root's additional native header observation finds substantially different Sony CA tables in current weevil149 and bug2-149 despite matching camera/lens/TC, aperture, ISO and correction-setting code. The exact command is retained in `../../outputs/raw-quality-2026-10-26/bug2-anchor-native-metadata-receipt.json`; the original source hash is unchanged. A bounded prior audit recovers bee-3 calibration-source header identities resembling bug2's state, but not the historical per-tile coefficient archives. The next header-only domain observation is specified in `ca-metadata/brief.md`; it must check all six named calibration stacks before inferring that weevil is outside observed states. No table-unit interpretation, physical-CA attribution or correction is activated. An effective chromatic registration may be useful without isolating its optical cause, but must preserve actual colored structures across held focus/field and complete photographs.

One small secondary GPU diagnostic was released while insect source work proceeded. The saved-alpha observation stopped before its intervention at a mechanical positive-control tolerance: expected500DN, actual mean499.958618DN, maximum error0.041748DN versus the declared0.02DN bound. A separate logging-only source reproduced the failure; all17 assertions stayed identical and inputs stayed unchanged. This is a numerical control refusal, not a test or rejection of structured visibility, and no quality gain follows. Root commands were `python -B -X faulthandler experiments/raw-quality-2026-10-26/execute-visibility.py` and `execute-visibility-record.py`, both exit1. The prepared diagnostic remains incomplete; no optimizer or RAW decode ran. See `structured-visibility/control-failure-review.md`.

### Metadata domain and exact consumer observation

MEASURED / independently reviewed: `python -B -X faulthandler experiments/raw-quality-2026-10-26/execute-header-domain.py` completed144 native header inspections,24 uniformly selected sources from each of six historical calibration stacks. All source bytes/metadata and inventories remain unchanged. This replays the current selection recipe; it does not recover the missing historical coefficient dataset. Weevil's code86 and exact32-value table are absent from these sampled sources (codes56 through66). Bug2's exact code/table occurs in four stacks; only tweezers also matches the complete recorded camera, firmware, lens, focal length, aperture, ISO and setting tuple. These are metadata distinctions, not calibrated table units, a correction policy or a photographic gain. See `ca-metadata/header-domain-results.md` and `../../outputs/raw-quality-2026-10-26/ca-header-domain-1/receipt.json`. The root wrapper took12.078seconds with24,727,552bytes peak job commitment.

VERIFIED exact complete observer: the frozen executable replayed all299 weevil sources with only `--sensor-master` added. Both RGB16 and float-linear master TIFFs are byte-identical to the prior CA-off output. The sensor TIFF is6896x4596 single-channel f32 CFA before WB, MHC and highlight processing, SHA256 `fa5825b834121b28547fc6e2154623740a24acc4e1616915c1c197bc90be2b02`. Its sidecar SHA256 is `e22ad2fad5ac7307a4560ccee4b0ad232edf1dc9449fdce7057022bff9341f21`. This observer is needed because the nominal linear RGB master already carries nonlinear highlight processing and is not globally invertible to the original CFA merge. All original hashes and the private map remain unchanged. This is an observation, not an image-quality change.

```text
python -B -X faulthandler experiments/raw-quality-2026-10-26/render-sensor-observer.py --input D:/personal/macro/insects/bug-3/107MSDCF --out outputs/raw-quality-2026-10-26/weevil-107-sensor-ca-off --exe outputs/raw-quality-2026-10-26/baseline-strehl.exe --sha256 89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388 --warp-map outputs/raw-quality-2026-10-26/weevil-107-sensor-ca-off-alignment.txt
```

The source143 companion was captured through the actual production CA-off gather under the held299 map. `execute-gather143.py` completed its exact ignored library test and then independently decoded the original with RawPy0.27, copying the active CFA inside its context. All31,694,016 original delivered-crop sensels agree, including all four phases; originals/map/order remain unchanged. The first attempted Cargo target was `--bin strehl` and ran zero tests; its log is retained and is not evidence of a capture. Corrected `--lib --no-run` freshly compiled in1m28s, and the bounded actual test ran once in0.906s. Commands/logs are retained in `source143-lib-build.*` and `source143-gather-job-1/` under the campaign outputs.

MEASURED / independently reviewed: `python -B -X faulthandler experiments/raw-quality-2026-10-26/execute-consumer-spread.py` completed in0.640seconds with63,688,704bytes peak job commitment. Generated controls and the dark-background check preceded the one frozen bristle. The actual149 green gather null is exact. All four final-stack transfer fits (G1/G2, source143/149) refuse held prediction: source143 residual64.48--64.52DN and source149 residual24.81--29.15DN. The fitted zero spread is not a zero-blur result. A pure0.5px shift creates1.091px apparent spread in this small sampled kernel family; the sharpening placebo is admitted as gain/offset with zero spread. Literal saved sections have a taller, more concentrated final peak than source143, so the surrounding focused context did not make143 a sharp reference for this particular bristle. Close the instrument without retuning. See `insect-consumer-spread/results.md` and `independent-results.md`; no restoration or placement change is inferred.

The next fixed experiment is `green-phase-guide/brief.md`: retain G1/G2 separately through ordinary finest-two-band energy, then share one noise-gated weight across all original CFA coefficients. It preserves coarse fields/base and adds no R/B evidence. This differs from the rejected original-green difference high-pass and shared RGB guide. Its complete299-source baseline/matched-mean/candidate route is prepared alongside the small generated controls, so a numerical screen cannot become a substitute for the decisive photograph. No default or quality result is yet claimed.

### Green-phase full-photograph observation

MEASURED / independently reviewed: build4 freshly compiled in236.859seconds, executable SHA256 `d89b20091cd425ea546da3234657ed3c99de85781cc4d0cdad19132c68ec67f6`. Its generated screen completed in3.453seconds and reproduces all56 build3 float payloads and all scientific outcomes exactly. Build4 changes only the bounded TIFF float-payload readback allowance after cost1 exceeded the decoder's default buffer limit; the failed cost1 evidence remains intact. The screen retains both thin depths and has no severe new guard failure, but low-frequency error rises about26%, moderate diagonal detail is unchanged and glint streaks remain. This is permission for an observational photograph, not a quality improvement. See `green-phase-guide/independent-results.md`.

MEASURED cost2: the one-source full-resolution run completes in15.031seconds with6,567,747,584bytes peak job commitment; source149 processing takes8.008seconds. All three CFA/RGB16/RGB32 outputs agree exactly under the one-source hull. Its2475-second full299 projection is an extrapolation, not competitive full-workflow timing. This prototype pays for16 source-space noise probes per photograph. Root has started the bounded complete299-source baseline/matched-mean/phase-energy comparison, with14GiB commitment and3600-second wall limits, four workers and actual GPU gather. Its receipt and complete baseline pixel identity are pending. Source/output manifests bind the unchanged build; no product default is altered.

Commands actually run:

```text
python -B -X faulthandler experiments/raw-quality-2026-10-26/run-green-phase.py build 4
python -B -X faulthandler experiments/raw-quality-2026-10-26/run-green-phase.py screen 4
python -B -X faulthandler experiments/raw-quality-2026-10-26/run-green-phase-photo.py cost 4 2
python -B -X faulthandler experiments/raw-quality-2026-10-26/run-green-phase-photo.py full 4 2
```

### Highlight locality and broader diagnostic baseline

MEASURED / independently reviewed: `python -B -X faulthandler experiments/raw-quality-2026-10-26/highlight-location/observe.py` completed in0.203seconds after its flat, strict-threshold, exact13-tap-support and wrong-location controls. This reads the retained exact final sensor TIFF, not original RAWs. Bright-wing-rim has24 in-crop CFA samples above the14848-DN working white (26 including the2-pixel expansion) and13 above15871DN; upper-occlusion has7 and5. The final MHC RGB dependency unions cover248/149 and37/30 native sites respectively. These are possible dependencies, not artifact-pixel counts or calibrated saturation evidence. Independent whole-image/native-map review locates sparse compact glints, not the broad pale wing contour; one small upper-occlusion cluster touches a bright point near its contour. Close the proposed exceptional-final-maxima explanation for the broad halos without a new299-source provenance trace. This does not exclude attenuated original clipping, sub-white ringing or other reconstruction errors. See `highlight-location/independent-results.md` and `photographic-location-review.md`.

Root also starts the complete60-source flat1s slide baseline with the same frozen normal executable, its own fresh isolated map and matching profile. This independent baseline is useful regardless of the weevil candidate's outcome; no flat candidate is released. Native optical headers from first/middle/last sources were inspected in0.219seconds with source hashes unchanged, before rendering. All three report the Sony100mm+2X lens identity,200mm,f/5.6, ISO100,1-second exposure and coarse focus code57. Those headers do not by themselves establish shutter/stabilization/illumination state. Four CPU workers overlap the running four-worker weevil trial on the32-logical-CPU host; neither run's operational time is a clean competitive benchmark. See `flat-baseline/brief.md`.

```text
python -B -X faulthandler experiments/raw-quality-2026-10-26/flat-baseline/inspect-headers.py
python -B -X faulthandler experiments/raw-quality-2026-10-26/render-cpu.py --input D:/personal/macro/requests/misc-diagnostic/high-res-calibration-slide-cpl/flat-sw4-cpl/flat-et1s-sw4-cpl --out outputs/raw-quality-2026-10-26/flat-1s-baseline --exe outputs/raw-quality-2026-10-26/baseline-strehl.exe --sha256 89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388
```

The flat baseline subsequently completed:60/60 placed, reference30, delivered6932x4620 at active origin(50,34), RGB16 master SHA256 `01e576315fdf8242b9d008c06a0ad9b52f837f84d8d28e05d59d13b97379dbdc`. All60 originals match their pre-run hashes and metadata. Operational alignment/render times are30.031/67.172seconds, peak commitment2,316,210,176/2,928,582,656bytes during the stated weevil overlap. The independent receipt audit records that the unchanged runner checks source hashes after rendering, not between its phases, and that the original completion omits the float binding. The separately verified crop-export receipt closes the latter gap: linear master SHA256 `51fd1f3e281c10def359af38a2064055de11b8788ff5ce7c0428d9e5a9e417ab`, single-page RGB32,6932x4620. No source mutation or incomplete file was found.

VERIFIED independent complete-image and eight frozen384-square witness review: this flat baseline has soft fine bars, merged lower radial spokes and cyan/red edge separation. The broad gray and dark dot regions contain visible texture/marks whose origins are not established. No placement, noise, optics or saturation cause is inferred from appearance. Exact RGB16 crops and ICC were verified, with no new display fit; original product DisplayBaseline `[0.008842854,0.36849296,0.55,1]` is retained for a later matched comparison. Full photograph and both masters are linked from `flat-baseline/baseline-review.md`. This is a current baseline, not an improved output.

### Complete green-phase rejection and flat full-workflow comparison

VERIFIED complete photographic result: the full299 green-phase observation finished, with canonical CFA and RGB pixels exactly reproducing the held baseline. Its2261.063-second run used7,961,710,592bytes peak Job commitment under the stated overlap. Root and an independent reviewer viewed all three complete outputs and all30 frozen native witnesses. Both changed arms strengthen colored background curves; neither provides convincing new scale/hair detail or relief of broad pale contours. Reject the exact recipe, with no optimization, default promotion or transfer render. Full photographs, RGB16 masters, float-linear masters and sensor payloads remain linked in [green-phase results](green-phase-guide/results.md). The earlier pending paragraphs describe the launch state, now superseded by this completed negative result.

MEASURED / independently audited: the flat60 exporter freshly built and processed all60 originals using the exact native baseline tone and fixed first-source WB; no source WB differed. All source hashes and metadata stayed unchanged. The existing native development golden passed exactly. Complete Helicon B/C runs then succeeded with identical exported inputs. B's full7032x4688RGB16 master SHA256 is `054ff371ff7c3fe4e0fd32d568d635c204b702a64c16ba94a8999e293bfc62ac`, C's is `ecdb2622995ef290fd65c9b7edb77c8e2019a728cd4604694a0797d1ed7c20d4`. An earlier sandbox B startup stalled before ingestion and was safely stopped as an exact owned child; its timing and stale copied application log are excluded. Fresh desktop-context runs used40GiB Job limits, with measured peaks about18.2GB for B and14.2GB for C. The successful runs' actual TIFF readback and fresh source logs establish completeness despite the absent vendor saved-output-list file. See [independent workflow audit](flat-comparator/independent-review.md).

```text
python -B -X faulthandler experiments/raw-quality-2026-10-26/flat-comparator/build-exporter.py
python -B -X faulthandler experiments/raw-quality-2026-10-26/flat-comparator/run-flat.py develop --exe outputs/raw-quality-2026-10-26/flat-export-build-1/flat-batch-develop.exe --sha256 203f20d75e8b9624d18fc9a6912b8372248826a92fddfaa93cbfc4dbc3c1e9c7 --build-log outputs/raw-quality-2026-10-26/flat-export-build-1/build.log
python -B -X faulthandler experiments/raw-quality-2026-10-26/flat-comparator/run-flat.py b
python -B -X faulthandler experiments/raw-quality-2026-10-26/flat-comparator/run-flat-desktop.py b
python -B -X faulthandler experiments/raw-quality-2026-10-26/flat-comparator/run-flat-desktop.py c
python -B -X faulthandler experiments/raw-quality-2026-10-26/flat-comparator/photographic-review/export-mapped-crops.py
```

VERIFIED photographic comparison: root and independent reviewer inspected the three whole flat outputs and all eight corresponding384-pixel native triplets. B makes existing QR blocks, circles and upper radial wedges clearer, without resolving the smallest central bars or lower radial convergence. B/C carry stronger red/cyan fringes, and C adds broad luminous shoulders. Native CA-on versus no-CA TIFF input and premerge/postmerge development are material confounds; no isolated cause or overall vendor superiority is asserted. [The complete comparative report](flat-comparator/photographic-review/independent-results.md) contains all three full images/masters and exact unresampled witness bindings. This is a practical edge-definition gap, not a native improvement or a new-resolution claim.

The proposed [camera-domain edge transport](../raw-quality-2026-10-27/cfa-edge-transport/brief.md) was subsequently refused before implementation or execution. Producer and independent reviewer derived a tangential-color counterexample: ideal diagonal coordinate transport preserves that component, whereas the proposed same-phase bilinear sampling attenuates it. The loss can occur below CFA Nyquist and survive a common-gradient-sign guard. No photograph was changed and no optical family is ruled out; see [the exact design objection](../raw-quality-2026-10-27/cfa-edge-transport/design.md).

VERIFIED independent source observation: five complete cached source-TIFF views preceded the fixed selection of indices15 and30. Eight native384 crops then showed that source30/reference30 already contains the clearer QR corners, dot contours and upper wedges seen in B. Smaller bar groups did not improve beyond the stack, and some are clearer in native/B than either source nominee. Root separately viewed the complete source30 and all four of its crops and concurs. This is source support for existing contours, not a resolution ceiling or a cause attribution; CA and development order still differ. [The source-support report](flat-comparator/source-support/results.md) retains all complete views/masters, mappings and unchanged-input receipts.

Root next allocates [native pixel fusion](../raw-quality-2026-10-27/native-pixel-fusion/brief.md): one direct shared-CFA weighted average from the actual current finest-band noise-gated weights, with the normal Pyramid baseline alongside the same prepared gathers. This changes reconstruction order, not the guide, sampling or optical model. Far/coarse loss and noise selection are explicit adverse controls. Source preparation includes a real reference30 checkpoint and complete flat60 pair before any complete weevil trial. This is experimental and unpromoted. The main insect/detail/halo quality goal remains unresolved.

### Native pixel fusion: complete photographic rejection

MEASURED / independently reviewed: the fixed direct whole-CFA tuple average completed its generated controls, source30 checkpoint and full60 flat comparison. Root commands were `python -B -X faulthandler experiments/raw-quality-2026-10-27/native-pixel-fusion/run.py build 1`, then the same wrapper with `screen 1`, `cost 1`, and `full 1`. The fresh build produced executable SHA256 `2dad4b2ef2a6a5a03781f2fcfeccd2ef1cc42c1102002893ceafadcbf223b403`. The generated screen mechanically passed but its quality qualification failed: fine near-depth recovery rose while broader far-depth recovery fell from0.765--0.784 to0.216. Different-source blue recovery and glint errors also worsened. A bounded full-flat diagnostic was explicitly released despite this known general failure; no general promotion was implied.

VERIFIED: the actual source30 checkpoint reproduces gathered CFA exactly through candidate and canonical single-source paths, and independently matches ordinary pre-tone RGB32 development. The complete60 run preserves every original and map, with canonical RGB16/RGB32 pixels exactly reproducing the held normal baseline. It completes in57.016seconds with3,999,551,488bytes peak Job commitment, four workers and GPU gather. These are operational figures, not a clean competitive benchmark. Full6932x4620 sensor, RGB16 and float RGB masters are retained; the shared fixed-display export is bound in `native-pixel-flat-views-1/receipt.json`.

VERIFIED complete photographic rejection: root and independent reviewer inspected both complete outputs before all eight frozen384-pixel native pairs. Firmer contours carry pervasive new purple inset bands, triangular corner shading, wedge-like interior marks and mottled dot/bar interiors. No convincing new smallest-bar separation or lower radial convergence appears. Actual source30 and Helicon B retain compact contours without these new interior structures, although their color fringes remain. The exact recipe is rejected, with no weevil run or default change. [Independent generated review](../raw-quality-2026-10-27/native-pixel-fusion/independent-results.md) and [complete photographic review](../raw-quality-2026-10-27/native-pixel-fusion/photographic-review.md) retain the controls, entire images and full-resolution masters. This does not reject all shared-CFA or spatially coherent reconstruction.

### Product checks

The original-CFA Gaussian-relative-blur prototype completes its first bounded screen without photographic admission. A first run exits1 before fitting on a NumPy-scalar JSON serialization defect; the exact failed source is retained and only serialization is repaired. The second root command, `python -B -X faulthandler experiments/raw-quality-2026-10-27/raw-blur-compatibility/run-bounded.py --iteration 2`, exits0 in8.172seconds with3,536,044,032bytes peak Job commitment. Known-X phase, footprint, forward/adjoint and detail controls pass. The neutral-flat returned image has lower RGB/chroma noise and passes held prediction, but reaches64iterations with maximum parameter gradient0.00052035 against1e-6. Scientific status remains NUMERICAL_REFUSAL; coloured/structured/adverse fits were skipped. This neither rejects the physical model nor validates it. One separately allocated fixed-work coloured-flat/compatible-detail diagnostic retains every numerical/quality guard and cannot authorize a photograph.

The two subsequent unchanged-budget original-CFA diagnostics also finish without admission. `python -B -X faulthandler experiments/raw-quality-2026-10-27/raw-blur-compatibility/finite-diagnostic/run-bounded.py --iteration 1` completes in7.359seconds/3,545,792,512bytes. Its colored flat passes noise/image and held guards, but unidentifiable calibrated variances choose the256 ceiling and stop progression. The separately allocated `run-compatible-bounded.py --iteration 1` completes in7.125seconds/3,544,018,944bytes. Root and independent review inspect complete truth, returned image and initialization: fine colored modulation is visibly weakened. Recoveries are0.837 near-fine,0.871 blue diagonal,0.829 weak-green crossing and0.724 red third harmonic. RGB/chroma error64.21/65.83DN exceeds45.81/37.83, and one held view fails at1.330sigma. The fit remains nonstationary; underestimated blur and softened radiance co-occur without isolating causality. See [compatible review](../raw-quality-2026-10-27/raw-blur-compatibility/finite-diagnostic/compatible-results.md). No RAW/photo run follows.

A single count-additive likelihood comparison is prospectively allocated in [its brief](../raw-quality-2026-10-27/raw-blur-compatibility/counted-likelihood/brief.md). Independent source/math review shows that the inherited per-view average plus fixed image prior is equivalent to five image penalties for five equal views. The changed objective counts independent original training sensels and one unchanged prior, retaining all image/held guards and fixed work. It is not a calibrated prior or a demonstrated photographic improvement.

The count-additive diagnostic executes with `python -B -X faulthandler experiments/raw-quality-2026-10-27/raw-blur-compatibility/counted-likelihood/run-bounded.py --iteration 1` in11.312seconds/3,583,225,856bytes, preserving all21 originals. Unequal-partition objective/gradient controls pass and reject equal-group averaging. Fine generated component recovery improves, but neutral/color flat errors roughly double relative to the stronger prior. All fixed flat guards and both structured held views pass; overall RGB/chroma52.56/58.30DN and thin red/near-blue detail still fail. [Independent counted review](../raw-quality-2026-10-27/raw-blur-compatibility/counted-likelihood/independent-results.md) records this mixed result.

The final conditional test supplies only the five independently generated training blur values and optimizes radiance with unchanged prior/work. `python -B -X faulthandler experiments/raw-quality-2026-10-27/raw-blur-compatibility/known-variance/run-bounded.py --iteration 1` completes in8.703seconds/3,560,591,360bytes; all14 originals and all receipt/master bindings remain exact. All named component/channel guards now pass, but overall RGB/chroma53.77/60.98DN still fail45.81/37.83. Both held views and flat guards pass; gradient nonconvergence remains. Root and independent complete-panel review close this fixed free-RGB/Cauchy/Gaussian recipe without a full-size adapter, blur-calibration lane or solver rescue. This does not establish an exact CFA null space or reject inverse reconstruction generally. See [independent conditional review](../raw-quality-2026-10-27/raw-blur-compatibility/known-variance/independent-results.md).

Root now allocates a [complete flat60 photographic observation](../raw-quality-2026-10-27/reconstruction-photo-observation/brief.md) of the unchanged finite coefficient-consistency result. This explicitly changes only the old experiment's no-render-on-numerical-refusal policy, not its32step solver,0.02DN admission bar, generated harms or defaults. The objective is a complete paired photographic verdict; all numerical failures stay recorded and admission remainsfalse. The actual current hull and canonical writer must be replayed, so cached chip coefficients alone are insufficient.

The fixed reconstruction residual-restart trial is also closed without a candidate photograph. Fresh build1 produces executable SHA256 `37453389c452631a8d511712e4a9d13a04361a9e01b256cb9dea6a8196b64503`; five independent controls pass in2.375seconds/449,060,864bytes peak Job commitment. The actual one-iteration solve refuses, dense reference RMS is0.001287714DN, and a single source remains bit-exact through CFA/hull/RGB. Existing generated glint/far-detail failures remain. The exact cached full-chip old/new comparison completes in32.750seconds/582,062,080bytes, reproduces old results, and exercises one restart at8 in each green plane. Both still refuse at32iterations:0.023784833/0.024252882DN versus0.02. All bound inputs remain unchanged. Commands were `python -B -X faulthandler experiments/raw-quality-2026-10-27/reconstruction-restart/run.py build 1`, then `screen 1`, then `cache 1`. [Independent cache review](../raw-quality-2026-10-27/reconstruction-restart/independent-cache-results.md) retains the distinction between a completed numerical experiment and photographic progress. No full-flat run or threshold/cap sweep follows.

The additional complete weevil Helicon B4/S4 comparison also finishes without substantial photographic improvement over B8. Root and independent review cover all three entire outputs and all30 frozen native witnesses. All299 developed TIFFs remain unchanged; the successful45.344-second vendor run peaks at34,698,645,504bytes under a38GiB Job. A first49GiB available-memory preflight refused before application launch and is excluded from performance evidence. [Full comparison results](../raw-quality-2026-10-27/weevil-fine-comparator/results.md) retain masters, exact commands, resource bounds and development/gauge limitations. Native softness, glints and pale contours remain unresolved.

Tracked diff whitespace check passed after removing an extra ledger EOF blank line. Corpus lint exits1 with16 existing violations in unchanged historical reports (seven table-width, seven unescaped code-pipe and two missing-final-newline findings). No historical tables were rewritten during this quality program. Git metadata access prevented the linter's committed-line-ending checks; this is not a complete corpus-lint pass. Test-only existing warnings remain. Full product checks and independent transfer are required before any production promotion.

MEASURED full core test command `cargo test --locked --offline -p strehl-core` freshly compiled the affected crate and passed591 tests with3 ignored, plus the sampler-boundary integration test. `cargo clippy --locked --offline -p strehl-core --all-targets --no-deps -- -D warnings` exits101 on existing warnings in unchanged historical paths; no finding is in the added CFA sampler. `cargo fmt -p strehl-core -- --check` exits1 on existing formatting differences; scoped new sources pass rustfmt. These are qualified checks, not a clean whole-repository validation. Logs are retained under the campaign output directory.
## Complete reconstruction observation, October27

VERIFIED no useful photographic gain: the unchanged coefficient-consistency solver rendered all60 flat sources in53.547s/3.574GB peak job commitment. Baseline pixels/material metadata reproduce exactly; all four solves meet their original numerical bar. Root and independent whole-image plus eight-native-pair review find persistent softness/unresolved fine structures without a substantial improvement. Both complete outputs and RGB16 masters were shown; the [scoped report](../raw-quality-2026-10-27/reconstruction-photo-observation/results.md) retains exact commands, build, audits and full outputs. No automatic weevil transfer or default promotion. The independently allocated native-restoration question returns to current complete weevil photographic acutance without claiming new information or calibrated optics.

## Complete native restoration observation, October27

VERIFIED mixed photographic effect: the fixed bounded same-phase correction makes existing weevil and chart contours firmer, but hardens stippling/glints and some stepped contours without resolving soft insect hairs, pale occlusion rims or finest chart patterns. Root and independent review cover both complete pairs and all18 frozen native witnesses. Both full-image pairs and RGB16 masters were shown. Seven of eight generated quality guards fail and remain false; exact no-op full pixels/material metadata, input preservation and complete masters pass independent audit. [Scoped results](../raw-quality-2026-10-27/native-restoration/results.md) retain commands, hashes and costs. The4.547/4.640s observations are saved-CFA reconstruction/writer costs, not end-to-end stack performance or a competitive win. No default promotion or resolution claim.

The [denser source-support observation](../raw-quality-2026-10-27/weevil-through-focus-support/results.md) then inspects31cached complete source views and five fixed focus timelines. Focused thorax and scale observations improve on the earlier sparse sampling, but root and independent review find no unambiguous omitted structure. No finer interval or weight census follows; this is no optical ceiling or proof of correct placement. A separately allocated six-direction dual-tree design changes the reconstruction representation, with the prior full separable-wavelet photographic rejection explicitly retained.

## Six-direction transform checkpoint, October 27

MEASURED: the genuine six-direction CFA transform passes signed reconstruction,
angular separation and actual gathered singleton checks. Six of eight generated
quality guards pass; weak-green and glint failures remain. A full-size original
weevil source with all sixteen probes takes 44.696869 seconds in the source
phase and 10.4336388 seconds to finish, with 8.17 GiB peak job commit. The fixed
projection is 13,494.8 seconds for 299 frames, so root declines the CPU full run
and allocates an unchanged GPU port. This is a cost finding, with no complete
stack candidate or photographic improvement. [The scoped report](../raw-quality-2026-10-27/dual-tree-cfa/results.md)
retains commands, actual output identities, independent review and known harms.

## Complete GPU dual-tree weevil: photographic rejection

MEASURED: the unchanged ordered-FIR GPU method completes all299 original weevil
frames and4784 probes in3554.016seconds, peak host job commitment15,233,900,544bytes.
The original1200second/14GiB practical limits remain failed; the separately
allocated4800second/16GiB observation bounds pass. Baseline pixels/material
metadata, input preservation and actual pre-hull nulls pass. RGB16 container
Software and strip offsets differ, so pixel identity is not file-byte identity.

VERIFIED by root and independent complete-image plus all-ten-native-witness
reviews: reject the candidate. Broad teal/green glow increases around insect
contours and dark gaps, without convincing newly resolved hairs/scales or a
softness/glare/occlusion repair. Complete images, all full-resolution masters,
commands and retained Helicon B8/B4/C context are in the
[photographic result](../raw-quality-2026-10-27/dual-tree-cfa-gpu/photographic-observation/results.md).
No default promotion, strength sweep, automatic other-stack transfer or GPU
gather optimization follows this fixed recipe.

The same audit makes the architectural limitation explicit: the current
full-resolution consumer reconstructs MHC per source, interpolates and
requantizes to CFA before merging and final development. CFA-domain fusion and
original-u16 storage do not satisfy literal original-CFA/demosaic-once. The
architecture document is corrected. After rejecting scalar full-value admission's
depth-preservation counterexample, the original-CFA band-residual prototype was
tested on a complete generated flat and rejected for severe colored striping.
The [saved original-sample error budget](../raw-quality-2026-10-27/joint-cfa-local-fit/band-residual/results.md)
found significant measured residual despite numerical acceptance. A separately
allocated [exact constant-deflation test](../raw-quality-2026-10-27/joint-cfa-local-fit/constant-deflation/results.md)
removed that catastrophic bias but still failed the actual-product RGB/chroma
guards and64-step normal criterion. Neither recipe proceeds to a photograph.
No photographic improvement is claimed; the user's broad quality goal remains open.

The [complete insect alignment observation](../raw-quality-2026-10-27/insect-placement-observer/results.md)
now retains the actual299-source matcher population without changing any map
bits:2340 pairs and224640 attempted fine tiles,139.25s and about9.44GiB peak
commitment. Generated producing-path controls and591 ordinary core tests pass.
Conditional anchor-footprint transport and independent source photographs
support one bounded held measured-field stability test, but do not identify a
physical placement error or justify a new warp. This is diagnostic progress,
not a photographic gain; the complete weevil baseline and its defects remain.

The [fixed field follow-up](../raw-quality-2026-10-27/insect-field-stability/results.md)
is now complete and negative. Generated controls pass, but ten of12 complete
held site/span cells fail the frozen stability criterion; all six replication
cells worsen the zero null. Scoring takes2.328seconds and23,658,496bytes peak
job commitment. Two independent reviews agree that the exact per-step model
is closed without a warp, physical explanation or photographic improvement.
The subsequent [current StackMFF V3 comparison](../raw-quality-2026-10-27/stackmff-v3-current/brief.md)
uses a materially redesigned October2026 release, distinct from the rejected
old three-source V4 hard-selection pilot. It is an external developed-image
comparator and cannot substitute for the native RAW reconstruction contract.
