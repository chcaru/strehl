# M194g milestone rule evidence inventory — draft

2026-09-07, implementation_audit. **Author evidence inventory, not independent
verification.** This maps the current AGENTS.md's 50 rule items: rules 1–49 plus
the separately numbered 31b. There is no invented rule 50. The inspected rule
file is SHA256 d8d2218b41fccfbc63a30a2fa26e55fa7de74676369b3882ac0154f8afbb4abe.
Root checkpointed the reconciled allocation/status prose at `1cc5e963`.

This task only read existing source, commands and retained JSON/text metadata.
It ran no generator, image decoder, metric, control or scientific calculation.
No new quality number is asserted here. MEASURED below points to an existing
executed record; source inspection alone is labeled as such. A recorded PASS
has the scope of its own schema, not all the scopes downstream of it.

## Evidence key and current boundary

The exact invocation is in each linked release's `commands` and its result's
actual `invocation`/`orig_argv`. Source maps, file lengths, snapshots, runtime
and final closures remain in those records; this shorthand does not replace
them with an abbreviated command to rerun.

| Key | Actual command/result and relevant source |
| --- | --- |
| P | [Original preregister][P]; mechanical prior-art output [PA]. Initial preregistration commit `a59a1c47c2d5ab57a9e2397d3589190aa35c7d23` predates geometry implementation. Root's later phase releases expand the staged work; the original exclusions remain historical. |
| G | [Cost release 2][G-release], [cost result 2][G]. `geometry.py::ExactSelector`, `preflight.py::count_geometry` and the pinned loader; independent geometry/preflight/budget controls are bound upstream. Cost admission is not radiance admission. |
| C | [Numerical implementation release][C-release], [component verification 3][C]. `hybrid.py::render_cell`, analytic transfer and frozen fallback; independent spatial reference and changed/restored component paths. Numerical implementation release was committed at `9b5ca1dc98c80717657e5f7e168dba9b2f621665`. |
| F | [Complete-array reader release][F-release], [complete-array result][F] and its actual float commission. Separately read all declared author/reference arms; current scopes and independent whole/band/refinement bars are in that record. Full admission checkpoint `561f58f3b4e17f92d87eb14dcd3e9e4bfe37bb5e`. |
| N | [Private software-noise command][N-release], [private result][N]. `software-noise.py::sample_frame`/`encode_dn`; independent reader `Temporal`, `PairMoments`, `fault_power`, `cross_frame`, `rounded_normal_oracle`, `run_reader_controls`. Private commission checkpoint `458818e00a9b16bab4e27e02d1bd0d124a94f46c`. |
| E | [Intended 90 command][E-release], [generation result][E], [independent file-reader release][E-read-release] and [noise admission][E-gate]. Intended saved-file reading has a different scope from the private retained-intermediate noise law. |
| B | [Build 2 release][B-release], [build 2 result][B], compiler/list/copied executable children. `noise-pupil-bridge.rs::Source`, `plan`, `run_source` call the existing prepared production consumer. [Private tests][B-tests] and [private RGB read][B-private] are separate executed results. |
| A | [Intended 12 independent-read release 2][A-release], [actual 59 control child][A-controls], [actual 12 read][A] and [bridge gate][A-gate]. `independent-quality-adapter.py::read_entry`; `independent-quality-adapter-controls.py::run_controls`; root wrapper `context_and_rows`. Checkpoint `877386aa9f1906f065d864d337dd38cc1adab35c` preserves the first failed read and the scoped repair. |
| I | [Private 69 command][I-release], [private 69 result][I]. `independent-quality-instruments.py::metric_controls`/`tiff_controls`; actual full 18-row private reductions are additional controls in A, not silently included in 69. |
| T | [K0 target command][T-release], [target][T], [separate 10-cell command][T-read-release], [separate 10-cell result][T-read]. `independent-quality-target.py::Target.cell` uses frozen polygon primitives; `independent-k0-target.py::integrate_cell` independently integrates x then split y. |
| M | [Actual 38 command][M-release], [actual 38 index][M]. `production-matrix.py` and the source-bound launcher; all plan/launch/render associations are retained. Release checkpoint `614525474d121f664f6716c9ecd5472154115395`. |
| Q | [Score command][Q-release], [score result][Q], [flat readout][Q-flat], [textured readout][Q-textured]. `independent-quality-score.py::main`, `independent-quality-readout.py::scene_readout` and `independent-quality-metrics.py`. Source/command checkpoint `9a8259360dff6aecbff7839274a8ed846f86d8b6`. |

Q reports `COMPLETE_FIXED_QUALITY_DIAGNOSTICS`, with 38 admitted entry FileRefs,
108 actual TIFF decodes, two scene readouts, null error and no finalization
errors. Its result hash is 7477f1553ac53dc87d554cee04117c536f7e5d3476b97ce9fde8f5d3b42b95df.
This is the author's completed diagnostic pipeline. Socrates' separate
numerical verification was pending when this inventory was drafted. The root
mathematical source review and Socrates' metadata source review are different
evidence from that forthcoming executed verification.

## All rule items

“Recorded” means the named existing evidence addresses this rule within the
stated scope. “Limited” names a boundary that must remain in the report.
“Not applicable” is not a waiver for a different future experiment.

| Rule | Applicability and actual evidence | Limit or publication obligation |
| --- | --- | --- |
| 1 | **Recorded with an explicit numerical-reference exception.** E persists headerless u16 CFA; `Source::decode` supplies u16 production frames and the existing prepared consumer uses f32 arithmetic. High-precision expected-electron references/analysis use declared f64 NPY arrays under P/F/T. | Those f64 references are generator/scorer artifacts, not a change to production storage/arithmetic. No f16 source or claim was introduced. |
| 2 | **Recorded.** B's `run_source` reaches existing `run_pyramid_prepared` through `PyramidFrameSource`; Source opens/decode-at-consumption. Q's `scene_readout` streams matched repeats and reopens delete-one pairs. | No aligned RGB frame volume is created. The limited reference/mean/M2 arrays are named in the budget; this is not an RSS claim. |
| 3 | **Recorded.** `noise-pupil-bridge.rs::noise`/`run_source` supply fixed noise coefficients; A checks every injected-noise/sensor field. N independently tests the consuming Poisson/read/gain order. | No calibration is inferred from those same supplied coefficients. The existing measured gate-floor probe is retained and its actual banner/count is bound, not replaced by a private noise estimate. |
| 4 | **Recorded.** M/A/Q pin SoftPower/Mean and each actual admission mode; `scene_readout` uses the fixed K0 target and separate endpoints, never a per-pixel best-frame argmax. | HardFloor stays the default. No index-map speckle, selection regularization or alignment assertion is used to justify the result. |
| 5 | **Not an alignment-fit experiment.** P fixes identity geometry in native reference 2; B/A check that exact supplied placement. | Synthetic known geometry does not satisfy or replace real runtime geometry fitting. No transfer to measured capture geometry is claimed. |
| 6 | **Not applicable to an alignment solve; gauge discipline applies.** A/Q validate original/local/probe indices, native crop and reference 2. There is no chained or fixed-reference registration fit. | All coordinate statements must keep native/reference 2 and crop origin. Neither endpoint is selected because its fit or error is favorable. |
| 7 | **Recorded within synthetic storage.** E files have an exact declared 320×240 extent and no inactive rawler padding; A/Q derive the actual delivered domain from plans and TIFFs. | “Whole” in Q means the complete delivered RGB output, not an unseen physical sensor area. This milestone does not inspect a rawler decoded buffer. |
| 8 | **Recorded, not extended.** G–Q each have actual releases, invocations, terminal records and source bindings. Q separates complete diagnostics from a quality PASS. | Report every quality figure as MEASURED on the fixed software population, then identify the independent verification scope. Resource times are completion observations, not comparative speed claims. |
| 9 | **Recorded.** I's constant flat wave controls run before textured wave controls; A exercises the full flat reducer with half-noise, bias and spike inputs. M/Q process the flat scene before textured. | A larger fitted amplitude alone is not detail preservation. Keep the flat temporal/control evidence beside any wave/detail statement. |
| 10 | **Recorded.** `independent-quality-metrics.py::Temporal` accumulates corresponding pixels across eight repeats; `scene_readout` separately retains structure-bearing target errors. I includes temporal-versus-spatial controls. N independently tests per-parity temporal moments. | Do not rename spatial residual RMS or scene structure as temporal noise sigma. No physical camera model fit is inferred. |
| 11 | **Recorded with final verification pending.** C/N/A/I pair active faults with restored/null companions. A's executed 59 includes the actual full 18-row reducer, literal variance/MSE/bias oracles and consumed outside-window spike. Q is the same reduction path. | Headline claims must cite those particular controls and the separately executed final numerical verifier when available. The full score has run; this inventory does not independently verify it. |
| 12 | **Limited, explicitly separated.** Independent geometry/reference/array/noise/bridge readers have distinct owners, and root reviewed the quality mathematics while Socrates reviewed its metadata. | This checklist is authored by the hybrid/noise/quality implementation lane. It cannot verify those implementations. Final quality numerical verification remains a separate pending task; no author self-PASS should be published as that verdict. |
| 13 | **Not a parameter optimization.** P fixes foci/fields/cases; M fixes two modes, all noise states and endpoints before pixels. No gate/weight/focus-count sweep is selected using Q. | The endpoints are separately named observations, not endpoint optima. Any future sweep needs its own powered interior-failure plant. |
| 14 | **No capture-corpus census claimed.** The new paths and B's no-RAW source are synthetic; the input ledgers authenticate only named files. | No assertion that the entire external corpus stayed unchanged is made from these ledgers, and no new corpus census was run for this inventory. |
| 15 | **Terminology requirement recorded in P/quality design.** The model concerns a depth-boundary/occlusion mechanism; the 74-native support guard is separately a local kernel-support condition. | Say “occlusion halo” for an artifact and “plugin halo” for support expansion. A local support guard does not establish global measured-beta/domain invariance. |
| 16 | **Not a timing comparison.** M alternates mode order by the fixed global state ordinal but does not derive a performance ranking. G/N/Q report fixed resource limits and actual terminal readings. | No per-setting minimum/thermal attribution is claimed. Profiling attribution was not recovered from the failed profiling schedule; do not turn budget timing into a speed result. |
| 17 | **Recorded.** `metrics::regions` uses only preregistered native coordinates, the half-plane equation and fixed window. Q does not derive masks from focus winners, output errors or fitted coefficients. | The fixed scene masks support this fixture only. All whole-output and window results remain present; masks cannot be moved to avoid costs. |
| 18 | **Recorded.** Q retains bias, MSE/RMSE, temporal variance, complex wave errors, phase, residual/full-signal error and sparse signed costs. I powers amplitude inflation, phase change, extra/projected residual and flat controls. | MSE can reward blur, bias can cancel, amplitude can reward manufactured contrast. The three review flags are descriptive and their absence never proves quality or general linear-filter immunity. |
| 19 | **Recorded for new owned files.** New g sources, outputs and this document use kebab-case names. Existing Rust crate names remain strehl-*. | Historical directory names are not renamed to manufacture compliance or disturb evidence paths. |
| 20 | **Recorded per staged protocol.** P/C register branch/radius/transfer/ULP faults; N registers stream/order/rail faults; A/I register typed association and real consumer destroyers before their runs. | Source-traced prospective final-scorer failure cases are not mislabeled newly executed private tests. Keep the actual controls separate from planned ones. |
| 21 | **Recorded with model boundary.** C/T use separately derived constant/affine/transfer integrals; N compares actual samples to the declared distribution with explicit wrong-law faults. | The same planted coefficients cannot validate a real sensor. Neither fitting a sharpness coefficient nor inversion of a fitted quantity supplies a physical-model gate. |
| 22 | **This draft is the requested mechanical inventory.** All 50 current rule items are listed individually with evidence or explicit limits. | The inventory does not convert a citation into a test result. Root must resolve remaining publication items and independently verify headline quantities. |
| 23 | **No non-spatial Sobel path in this scorer.** `scene_readout` consumes individual 2D channel planes, joint fixed-wave fits and Temporal states; it creates no frame-axis Sobel cube. | This is source inspection of the declared scorer path, not a blanket claim about all library filters. |
| 24 | **Recorded in independent choices.** Geometry re-chooses tangent/ULP/nonidentity cases; spatial reference avoids the author's Bessel/polar calculation; T re-chooses x-antiderivative/split-y integration; root TIFF/readout controls re-choose colours, strips and faults. | The ten T cells are not a second integration of every target cell. Re-reading Q's saved arithmetic is not the pending independent numerical quality verification. |
| 25 | **Not applicable to a fold.** P expressly assigns no SYNTHESIS number block, and this inventory introduces no proposed facts or disciplines. | A future fold requires its own namespace allocation/collision and content checks; do not infer that a free number means material is new. |
| 26 | **Recorded where claimed.** C includes analytic/fallback observer and reordered-traversal payload identities; N includes off/count/placebo and replay checks; A's actual intended off/count/placebo outputs use ordinals 6/8/9 with identical file and independent pixel hashes. | The failed counter-profile schedule did not complete its observer commission and grants no such claim. Q's read-only scorer is not a new production observer. |
| 27 | **Recorded failure/completion behavior.** G and numerical controllers keep partial counters and explicit limit/refusal records; later runs use new releases/directories. Root-owned process completion supplies terminal status. | No lane declares a run dead from missing output or an unchanged progress sample. No comparative liveness/timing inference is introduced here. |
| 28 | **Not applicable to a fold.** No M194g SYNTHESIS fold is supplied or claimed. Historical M194b–f results are identified as prior work in P. | Before any later fold, match content against existing SYNTHESIS rows; do not use the report's proposed numbering as authority. |
| 29 | **Limited source/edit evidence.** Root retained earlier source snapshots and scoped corrections; the adapter build-string repair changes only the plan literal, and entry packaging preserves every entry. This task only creates this new file. | This inventory did not re-audit every historical patch's deletion/heading counts. Root reports exact heading-preservation and allocation pipe-count checks for the reconciliation committed at `1cc5e963`. |
| 30 | **Recorded refusal history, no carve-out.** Original CPU/refusal, profile JSON-comparison failure, reference quadrature warning and first bridge-read version failure remain separately retained. Reference normalization is a prospectively released method correction, not warning suppression. | No failed site/arm is removed or an accuracy bar relaxed after seeing it fail. A tolerated physical-model limitation is stated as limited scope, not silently removed from a test. |
| 31 | **Not applicable to a fold; source chronology recorded.** P/C/F/N/A/M/Q give preregistration, source and command checkpoints; Q's command is frozen at 9a825936 before execution. | No SYNTHESIS insertion or report fold occurred in this task. Future folding must cite the actually committed report revision, not the newest draft. |
| 31b | **Not applicable.** No fold script or SYNTHESIS edit exists in this task, so fold_check was not run or claimed. | The mechanical fold check and qualifier read remain mandatory if root later commissions a fold. |
| 32 | **Not applicable to rawpy lifetime.** This path reads strict saved synthetic CFA and TIFF bytes, not a RawPy context or LibRaw view. `Reads.array` parses the hashed NPY buffer; source readers own their bounded decoded data. | It does not independently re-decode real RAW or certify unrelated rawpy code. |
| 33 | **Recorded.** B preserves the first cargo compile failure; replacement build 2 retains an actual Compiling strehl-cli message, exact compiler artifact/copy identity and test listing. Private tests and output commands use that immutable copied executable. | Python source controls do not substitute for compilation. No additional full CLI-suite claim is inferred from the scoped six bridge tests. |
| 34 | **Explicit software-only limit.** N/E inject and test the same declared software sensor coefficients; the private moment/stream/encoding checks have wrong-law destroyers. | This commissions software behavior, not physical gain/read calibration, diffraction, a lens model or real-capture noise. The report must carry that qualification beside noise conclusions. |
| 35 | **Recorded controls with independent terms.** A/I literal temporal/bias/spike oracles test consumed arrays; C/T analytic predictions and independent spatial methods supply separate terms; N wrong-law controls reach actual moments/correlations. | The finite-repeat decomposition and saved-discrepancy recomputation are arithmetic consistency checks, explicitly not independent corroboration. |
| 36 | **Recorded.** C records real branch/defocus/transfer/hook use; N records actual component draws and fault activation; A records nonzero count/placebo hooks and the actual sparse spike; T requires mixed visibility in selected controls. | Mode names or configured parameters alone are not path evidence. The complete populations in deciding results must remain attached to any claim. |
| 37 | **Not applicable.** No SYNTHESIS edit is performed or claimed. | A future insertion must use section/item structure, table escaping and trailing-newline checks; do not inherit an exemption from this no-fold task. |
| 38 | **Recorded citation form.** This table cites source symbols and actual result/release records, not mutable line numbers alone. Build-stamp rationale distinguishes crate::SOFTWARE from image_out::MEASUREMENT_SOFTWARE. | This inventory quotes no new corpus fact figure. A final report must read complete supporting rows and keep their model/target qualifications. |
| 39 | **Recorded for stochastic quality quantities, limited elsewhere.** Q retains all eight paired MSE differences with SD/SE and matched delete-one variance/jackknife rows. Flat/off/restored nulls and active faults are in A/I/N. | Deterministic hash identity has no sampling SE. Engineering moment/correlation tolerances and tiny numerical discrepancies are not probability/confidence claims. Do not present them as universal confirmation or a calibrated sigma statement. |
| 40 | **Recorded original prior art.** PA retains the actual mechanical search, and P names M194e/f/b/d and the larger-fixture design lineage; the quality design explicitly carries M194d's prior tradeoff. | This inventory did not rerun prior_art or establish absence of other literature. Its scope is the existing dispatch evidence, not a new novelty search. |
| 41 | **Recorded allocation, reconciled status.** The current AGENTS M194g row names larger expected arrays, software noise and the production comparison through separate root releases. The updated report opening marks completed diagnostics and pending verification. | Earlier phase exclusions remain historical. Root checkpointed the ledger/report reconciliation at `1cc5e963`; that status still distinguishes completed diagnostics from pending numerical verification. |
| 42 | **Limited to recorded ownership/commits.** Root owns all commits and immutable source releases; this lane made no Git mutation. The checkpoints above resolve in Git and retained releases name their source sets. | This inventory does not certify every Git invocation was path-scoped merely because its resulting tree is clean. Root's owned-path commit audit remains the authority. No history rewrite is requested. |
| 43 | **Recorded scope wording.** P and the quality design cite the prior stages and explicitly distinguish absent authority from absent phenomena. Report/status staleness has been routed to root and reconciled without erasing history. | Do not replace “not tested here” with “nobody has measured” or a broad assertion that evidence does not exist. No new absence claim is made. |
| 44 | **Not applicable to a fold.** This is a new inventory, not a repeat of numerical facts for SYNTHESIS insertion. Earlier failed results and existing supporting records stay resolvable. | A future fold must use only the new delta and retain amended rows as possible duplicate targets. No new fold exemption is introduced. |
| 45 | **No registration sidecar path used.** B calls prepared synthetic identity state directly; plans/launches retain the actual isolated environment and no RAW stack directory is opened. A rejects unregistered active overrides. | No shared warpmap write/cache/solve is claimed. This does not certify the production alignment CLI's sidecar behavior or a gather-kernel sweep. |
| 46 | **Recorded invocation boundary.** Build and production launchers retain complete logs and explicit process return codes before metadata publication; Python gates preserve terminal errors and finalization failures. Q parses complete hashed JSON before display summaries. | This draft's selective display of already parsed metadata is not a fresh gate execution. A truncated console excerpt alone is not the source of any PASS in this table. |
| 47 | **Recorded actual commands and environment.** Every key above points to original interpreter/test argv, external input hashes, actual selected frame identities, explicit fixed config and relevant removed/active overrides. Q uses a fresh cache and records Python/NumPy/SciPy/thread environment. | These are declared dependency/environment closures, not a hermetic OS/credential inventory. Use original recorded commands, not current defaults, when reproducing. |
| 48 | **Not applicable to a visual verdict.** Q performs native decoded-pixel analysis; this task does not view, resize or rate an image. | No aesthetic/visual defect claim follows from a thumbnail or the numerical PASS. A future visual verdict needs the commissioned viewer and stated identical display transform. |
| 49 | **Recorded orchestration boundary.** Root issued the staged source/run releases and owns actual launches. This lane inspected and authored files, reported findings, and did not terminate another lane's process. | Root source holds protect evidence; no peer-created scheduling authority, host lock or timing quarantine is asserted. Resource timings are not defended as comparative benchmarks. |

## Items root must keep explicit

1. **Final numerical quality verification is still separate.** The executed
   score and upstream commissions do not self-verify the author's final quality
   quantities. Add the independent executed verdict when it exists; until then
   retain “diagnostics complete; independent numerical verification pending.”
2. **Target authority is limited.** T creates a full array and checks its full
   file/layout/finite-value integrity, but the separate method integrates only
   ten fixed cells. The complete F comparison of defocused expected arrays is
   a different population, not an all-cell K0 target verification.
3. **Software/model/consumer scopes remain distinct.** Private retained noise
   intermediates commission the specified law. Intended 90-file reading checks
   actual CFAs/audits; it does not reconstruct unretained random intermediates.
   K0 is an ideal geometric target; actual endpoints are local observations.
   No physical calibration, real alignment, SOTA or default promotion follows.
4. **Scope/status reconciliation is checkpointed.** Root committed the
   report opening and allocation updates at `1cc5e963`, preserving earlier
   phase restrictions/refusals as history. Root also recorded exact heading
   preservation and allocation pipe-count checks. No authority/gate/source
   mutation is requested by this inventory.
5. **No SYNTHESIS fold is performed by this inventory.** A later root-owned
   fold must satisfy rules 25/28/31/31b/37/44. HardFloor remains the production
   default; review flags do not constitute GO authority.

[P]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/preregister.md
[PA]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194f-production-bridge/next-larger-prior-art.log
[G-release]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/cost-release-2.json
[G]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/preflight-2/result.json
[C-release]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/numerical-implementation-release-1.json
[C]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-component-verification-3/result.json
[F-release]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-full-array-reader-release-1.json
[F]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-full-array-verification-1/result.json
[N-release]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/software-noise-commission-release-1.json
[N]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/software-noise-commission-1/result.json
[E-release]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/software-noise-intended-release-1.json
[E]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/software-noise-intended-1/result.json
[E-read-release]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-noise-files-release-1.json
[E-gate]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-noise-files-1/noise-admission.json
[B-release]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/bridge-build-release-2.json
[B]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/bridge-build-2/result.json
[B-tests]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/production-private-controls-1/result.json
[B-private]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-private-bridge-read-1/result.json
[A-release]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-production-bridge-read-release-2.json
[A-controls]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-production-bridge-read-2/adapter-controls.json
[A]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-production-bridge-read-2/result.json
[A-gate]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-production-bridge-read-2/bridge-commission.json
[I-release]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-quality-instruments-release-1.json
[I]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-quality-instruments-1/result.json
[T-release]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-quality-target-release-1.json
[T]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-quality-target-1/target.json
[T-read-release]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-k0-target-release-1.json
[T-read]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-k0-target-1/result.json
[M-release]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/production-matrix-release-1.json
[M]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/production-matrix-1/run-index.json
[Q-release]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-quality-score-release-1.json
[Q]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-quality-score-1/result.json
[Q-flat]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-quality-score-1/flat-readout.json
[Q-textured]: C:/dev/blog/death-of-software/projects/strehl/experiments/m194g-larger-pupil/independent-quality-score-1/textured-readout.json
