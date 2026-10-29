# Multi-stack continuation: active implementation and evidence

This continuation remains active. The earlier `results.md` and packaged
candidate7 describe a narrower checkpoint, not completion of the user's full
request. See [the independent requirements audit](review/requirements-completion.md)
for outstanding outcomes. Proposals are hypotheses and the implementation may
change; passing mechanics or a refusal-only experiment does not close an outcome.

VERIFIED: core focus evidence retains per-pass acquisition order, complete
support, local shape, competing modes and source identities. Focus width is not
metric depth or calibrated uncertainty. Exports now include all eight retained
modes, their heights/boundary flags, four source ranks, support counts and flags.
The first 14 focus controls and the expanded core suite passed (659 tests plus
sampler and then-current reconstruction controls); later module changes have
separate receipts and still require a final integrated check.

VERIFIED: optional coefficient attribution preserves image bits while reporting
normalized effective contributors, primary/group fractions, conditional variance
and missing/saturated kinds. Frozen-guide precision uses a distinct acquisition
and refuses guide reuse within its own averaging group. Thirty fusion controls
passed. This is conditional coefficient information before collapse/demosaic,
not final-pixel uncertainty or proof of a real HDR benefit.

VERIFIED: the integrated CLI session suite passed 70 tests in
`outputs/multi-stack/completion/cli-expanded-02`; 14 revised mosaic controls
passed in `mosaic-consumer-controls-02`. These include the original-CFA mapped
consumer, union coverage, whole/tiled phase equivalence, conflicting-view
fallback and continuity across a change in overlap qualification. Failed local
mesh cells remain unsupported. Real extended-view photographic validation is
still required. Alpha export retains RGB16 values, ICC and print metadata and
uses a conservative demosaic-support mask. Tone measurements exclude missing
union storage. Filesystem publication tests required execution outside the
Windows sandbox with temporary files kept inside this worktree.

VERIFIED: 26 desktop session tests passed in `ui-session-controls-01`. New saved
options default off, follow the immutable job snapshot, and reject incompatible
mode combinations. Mosaic has no primary target. Coverage and saved diagnostic
viewers are still being integrated; these tests are not an actual GPU UI exercise.

MEASURED: `binary-04/strehl.exe session compare` compared the complete existing
299-frame insect pass masters on their identical measured geometry. It produced
7,597 nonoverlapping 64-sensor-pixel patches with ring curves, correlation,
relative disagreement and amplitude ratios. The run took 24.813 seconds and
sampled 1.255 GB private memory while another cache experiment ran. Every patch
is explicitly focus-unverified because no focus evidence was supplied; the
values are descriptive repeated structure, not resolution or noise estimates.
`insect-reproducibility-run-01/receipt.json` contains the exact command and build.
The first three file-name fields serialized a Windows OsStr object rather than
a string; source was corrected and this artifact needs regeneration before UI
acceptance. Actual CLI publication/shared-photon/gauge-refusal controls passed
in `reproducibility-cli-controls-01`.

MEASURED, REJECTED photographic candidate: `sr-roi-run-03` completed the
192×192-sensor-pixel insect ROI from cached original CFA after the historical
decoder binding was independently audited. It used no RAW decode, took 89.05 s,
and sampled 1.211 GB private memory. Complete 299-frame focus evidence was read
twice per pass. Scalar reconstruction took 0.04231 s and parallel tiles 0.006867 s
with identical bits; this is a tiny-kernel timing, not whole-feature speedup.
Only 2 red, 748 green and 3 blue pixels reconstructed. All nonlinear-highlight
and whole-native fallback pixels retained exact native float bits. Native-size
inspection nevertheless found purple pits from isolated green substitutions.
The fixed target frame neighborhood also missed the measured local focus peak;
tiny common focus weights could normalize back into apparent phase support.
Neither result is accepted as useful reconstruction. Follow-up requires an
absolute mode-neighborhood admission, coherent RGB fallback, measured local
geometry and an evidence-selected source neighborhood, without lowering phase
or focus gates to obtain a favorable picture.

MEASURED: the first HDR source-flat observer accepted no tiles before opening
measurement frames. It cannot establish benefit or absence of usable evidence;
its exact qualification null still needs commissioning. See
[the observer record](review/hdr-temporal-observer-results.md). Controlled
incremental-noise experiments on real signal and full precision/HDR photographs
remain required, along with signal-transfer witnesses and independent review.

Prepared real data, all outside the read-only capture corpus: 182 byte-verified
tilted-chart originals split into even/odd ordered passes; and 34 byte-verified
marigold center/offcenter pilot originals retaining continuation segments and
the three previously nominated focus pairs. Their plan/preparation JSON files
bind original/copy hashes. Full 827-frame marigold data remain the final mosaic
photographic test. Full interleave, HDR, reconstruction and mosaic campaigns,
optimization, ordinary-stack regression and final source-inclusive packaging
are still in progress.

## Continuation checkpoint after binary 08 (goal remains active)

MEASURED: full interleave-02 completed182 originals in760.093s with8.138GB sampled private memory. Both91-frame reconstructions, focus/contribution maps and descriptive reproducibility curves were exported. The ordinary182 reference completed in96.049s with7.375GB private memory. Complete-photo/native-witness review found no recognizable gain from this densely sampled split. The stronger predeclared pitch8/offset4 causal partition completed46 originals in203.547s with8.108GB private memory; its two23-frame controls and combined photograph now await frozen-control review. These are artificial partitions of one sweep, not independent repeated acquisitions.

MEASURED: hdr-precision-01 completed126 originals in516.390s with9.611GB sampled private memory. Full photograph/native-witness review confirms the option executes and found no new obvious seam/color break, but no recognizable improvement over equal HDR; some edges remain softer than short-only. Source-contribution maps locate precision mostly in supported midtones rather than clipped boundaries. No actual photographic SNR gain is claimed.

MEASURED: the off-center SR census used1196 historical-cache reads and zero RAW decodes for three regions in165.838s,1.301GB private. A sealed import reused those exact focus fields in sr-roi-04:18cache reads,2.682s,1.202GB private,2265 of36864 pixels reconstructed coherently in RGB. All other native and nonlinear fallback bits remain exact. Root and independent inspection found the earlier partial-channel purple-hole artifact absent, but no defensible detail gain. Local-registration-01 measured72 RGB edges and certified no source: current raw-NCC geometry remains inadequate at the unchanged0.15sensor-pixel criterion. Measured-trajectory and alias/estimator controls precede further geometry work.

MEASURED, refused: marigold pilot01 failed at coarse descriptor nomination despite real overlap. Source-feature pooling and scale-aware descriptors passed causal geometry controls; pilot02 improved nomination to three reciprocal matches but still failed before native measurement. Neither run publishes a photograph or constitutes a useful mosaic. Work continues on original-source untrusted seeds and distributed native validation; no geometry acceptance threshold was widened.

VERIFIED: 83 CLI session tests passed in cli-expanded-10 (fresh compile, elevated filesystem publication);34 UI session/import/diagnostic controls passed in ui-expanded-controls-02 using the freshly compiled test executable. The preceding session-expanded-08 failed compilation at a large JSON macro and was repaired by moving nested serialization outside it. session-expanded-09 exposed two real detector-positive failures plus12 sandbox filesystem failures; all were subsequently resolved or rerun with correct filesystem permissions. The four importer controls distinguish renderer-bound results from explicitly labelled legacy current-file identities. Actual GPU inspection is in progress through the prescribed local helper.

VERIFIED: output bindings now hash each photograph/master/render report plus its full session/census/alignment, and final completion hashes those per-output receipts. Comparison refuses replaced masters and retains complete focus ordinals when originals are unplaced. Standalone focus export now checks per-pass header calibration consistency and records resolved noise, optical, filter and policy parameters. Existing unbound results remain historical evidence, not silently upgraded certificates.

VERIFIED: the additive reconstruction writer seam produces byte-identical native photograph/master files when no candidate is substituted. A single changed camera-RGB pixel is developed once without a second demosaic; every other master pixel remains exact. It preserves normalization and white balance before the native MHC step, freezes tone from native CFA, and reuses its one final RGB buffer for the master. The ordinary writer is unchanged.

MEASURED, conditional simulation only: noise-transfer-02 runs the actual production coefficient consumer with48 independent synthetic noise realizations on fixed original-CFA signal. A frozen noisy withheld guide reduced temporal variance about12.6% on flat and13.1% on the textured fixture versus equal averaging. Missing guides reproduce equal-weight outputs bit for bit. The common unblurred fixture observer also detected loss of midband signal transfer: green gain0.87745 for equal versus0.85735 for the noisy-guide precision arm, and clean RMSE151.12 versus161.78DN. This is a real tradeoff, not a free quality gain or camera-model validation. An explicit causal arm now separates precision delivery from equal-observation cross-group focus weights; it is not yet selected by the product.

Pending: useful original-CFA reconstruction and extended-view photographs, their full-scene independent review, strong interleave outcome review, precision-feedback isolation and review, actual GPU controls, final optimization/regression/checks and updated source-inclusive distribution. No completion claim or merge is authorized by this checkpoint.

## Follow-up to binary 08

MEASURED, conditional simulation only: noise-transfer-03 exercises explicit equal-observation focus weights while retaining precision delivery. Across48 independent noise realizations, noisy-guide temporal variance is0.88319–0.88402 of equal averaging (sigma0.93978–0.94022). Clean outputs differ from the equal baseline by only3.19e-5–1.02e-4DN RMS, at most0.00293DN. The equal baseline's existing signal transfer is retained; this does not recover the unblurred truth or validate real-camera noise/geometry. The independent observer audit agrees. CLI precision now selects this reference; precision-off and the ordinary consumer retain their old calls. Thirty-one session-fusion controls pass in precision-focus-control-02. A complete HDR photograph and review remain required.

VERIFIED: cli-expanded-11 passes86 session tests, including actual coarse/native mosaic-search controls, cross-view spatial-role leakage refusal, and insufficient-native-evidence refusal. ui-expanded-controls-03 passes36 tests after correcting imported-result capture readiness: saved source counts no longer enqueue unavailable RAW thumbnails. Actual GPU screenshots remain required. Imported renderer-bound pitch8 output and legacy labelled outputs both passed mailbox controls in desktop08.

MEASURED: the pitch8 full photographs and36 native crops showed no clear gain over both halves. Dense focus-map widths are about5.6 original frames at the median, larger than that partition's nearest missed step. A predeclared pitch32/offset16 partition now has12 byte-verified originals and six focus-only witnesses selected before viewing its output. Local curve width is a shape approximation, not a calibrated focus probability.

MEASURED: the reproducibility ABBA benchmark with1/16/16/1workers gives23.633/22.620/22.607/23.615s end-to-end. Independent patch compute falls from0.715s to0.056–0.060s, with identical map hashes and tile curves; the whole operation improves only about4percent. Per-stage timers were added to locate the remaining cost before further optimization. Timings include a concurrent light UI control lane and are recorded in repro-benchmark-run-1 through-4.

VERIFIED photographic positive: pitch32/offset16 completed12 originals in77.616s with6.751GB sampled private memory. Independent review of four complete photographs and24 native384 crops confirms complementary focus gaps filled in both directions: paired bars/digits from even32 and radial spokes/labels from offset16 remain recognizable in the combined6788x4524 output. Root independently viewed the two decisive native boards and agrees. No superiority over the dense182 reference, independent-repeat noise reduction or resolution beyond captured support is claimed. Selection and exact saved-map gauge transfer preceded candidate viewing. See [the full review](review/pitch32-photographic-review.md).

MEASURED: hdr-precision-03 rendered126 sources in187.455s,9.624GB sampled private memory, reusing exactly bound geometry and original cache at8workers. The complete equal-observation-focus precision output is awaiting the same12-witness independent review. Attempt02 at16workers correctly refused a mismatch with the saved alignment's settings before decoding; neither its failed directory nor its timing is presented as a result.

VERIFIED: session-expanded-12 passes87 CLI tests. A new UI Mosaic binding positive initially failed because its direct-helper fixture supplied a noncanonical root, unlike the production loader. Correcting only that fixture gives38 UI session tests passing in ui-expanded-controls-04; the actual egui mesh overlay test passes too. GPU09 captures succeeded and exposed the overlay's screen/UV mapping bug; the corrected mapping still awaits GPU10 verification. New Mosaic receipts bind their real geometry and all visibility/owner artifacts, never a fabricated ordinary alignment.

## Continuation through binary13: still active

VERIFIED: the production original-CFA option is connected from immutable UI job settings through CLI preflight, complete-track focus maps, bounded original-handle cohorts, direct-anchor/cycle registration, coherent RGB replacement, common final development, and receipt-bound support/fallback maps. It remains opt-in for combine/repeat/interleave/HDR; Layers/Mosaic/binned combinations refuse. Exact native RGB survives every rejected pixel without a normalization round trip. Independent review found and prompted corrections to interior-anchor triangle connectivity, retained report/plan memory, refused-vector capacity, small-remainder subdivision reservation, and explicit focus-domain binding. No complete-scene reconstruction photographic success is claimed yet.

VERIFIED: session-integration-controls-13 passed106 CLI session tests after fresh compilation. sr-consumer-controls-05 passed12 reconstruction/sampling/writer/plan controls. The actual cropped merged-writer seam retains complete native photograph/master bytes when its callback makes no substitutions. The regional sampler matches full-plane arithmetic and masks for all six kernels and checked optics/crop/boundary cases.

MEASURED: original region preparation is77.74–79.52times faster than the full-plane gather in the three actual-RAW placement arms, with identical values/masks and97,600–98,325bytes of region buffer reservation versus41,280,480bytes. This is a small-window preparation result, not a whole-session speedup. Exact ABBA commands, input, source/library bindings and scope are in [region-preparation-results.md](sr/region-preparation-results.md). Reproducibility JSON buffering separately reduced an approximately22.2second publication-dominated operation to2.08–2.28seconds with identical maps/curves/non-timing report values; its earlier worker-only result understated the avoidable output cost.

VERIFIED: UI12 completed23 real product-control commands and six GPU screenshots. Reconstruction preference survives draft reopening; automatic and explicit primary choices work; unsupported mode changes refuse atomically. Overlay navigation, continuous/categorical legends and trace colors were inspected at1x/8x. The future completed-reconstruction outcome panel still requires an actual producer result. See [UI12 review](review/ui12-actual-gpu-review.md).

VERIFIED photographic scope: the complete hdr-precision-03 output and60 frozen native crops preserve the coherent HDR result but show no additional visible gain over equal/short controls. Conditional simulation variance improvement remains distinct from actual photographic SNR. The earlier pitch32/offset16 complementary-focus photographic positive remains verified.

MEASURED, refused: full827 marigold completed internal alignment/focus preparation in1675.04seconds,18.28GB sampled private memory, but no cross-view graph or photograph. Dense input exposed redundant source nomination. Exact cached guide reconstruction reproduced both intensity bits and source-witness hashes in46.36seconds, with zero RAW decodes. Bounded spatial diversity, stronger descriptor pooling and focus-ordinal-conditioned coarse proposals now replay from those bound artifacts. At the latest checkpoint, native evidence still refuses; local-footprint diagnostics and independent controls continue. Nomination counts are not quality or placement evidence.

MEASURED, still under investigation: sealed chart census02 read252 current cached originals with zero RAW decodes in33.40seconds,1.273GB sampled private memory, retaining the three predetermined odd sensor-coordinate witnesses. Chart ROI registration initially certified no source. A continuous, fixed-patch photometric refinement plus a separately tested wider independent footprint now passes chart-level known-geometry/noise controls at the unchanged0.15sensor-pixel bar, but independent seed/bias review and the real photographic arm remain required before promotion. The original low-DN commissioning failure is preserved.

VERIFIED with unresolved checks: broad core validation passed710 library tests (4ignored) and the preceding examples, then failed the newly registered low-DN signal-commissioning positive already identified above. Strict lint audits distinguish40 new completion diagnostics from74 inherited findings across core/CLI; scoped new-code cleanup is in progress, with exact unchanged-source mappings retained in [broad-validation-01.md](review/broad-validation-01.md). No green full-suite claim, final ordinary299 regression, final source-inclusive distribution, or completion declaration is made at this checkpoint.
