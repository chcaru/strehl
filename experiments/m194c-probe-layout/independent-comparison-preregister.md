# M194c independent comparison preregistration

2026-09-07, before candidate outputs or root comparison results. Owner
`roadmap_audit`. Read AGENTS allocation, M194b final report and retained
independent results, M194c author preregistration and the frozen M194b reader.
M194b is committed at `444eb759be0358cda25e97d4375f977a039efe6a`.
Zeno independently owns sampler/probe/production-layout semantics; this review
owns the candidate comparison and controller, not duplicate product tests.

## Fixed scope and choices

The baseline is M194b's complete 40-TIFF package, index SHA-256
`37f99736bd32dfb4891bd8fa2b033cacc2c58e9265515fa53cb5921dd80d9c08`,
read through explicit reader v3 SHA-256
`f8740c75c5d65842d8b1993807ad99b27e988c7fb659e6f52fcd3848a6f65f00`.
The candidate reuses the actual same 20 manifests/180 active-CFA inputs,
original frame-4 gauge, curved geometry, crop, 21,504-pixel canonical ROI,
injected coefficients, complete configuration, producer and final M194b
scoring functions. No RAW, sealed capture, parameter search, reference fit,
new scene, physical-camera claim, performance bar or SOTA admission occurs.

The intended product outcome is removal of unused-storage dependence. A
changed deterministic probe realization can move absolute output bytes and
quality components. Do not require cross-version identity for padded inputs;
do require a complete, untuned account of every fixed comparison. Retain both
ideal and optical-observation targets and the single-input comparator. The
existing local-index probe seed convention remains visible: original frame4
is seed-index4 in full9 and local-index0 in single4.

## Independent acceptance and falsifiers

1. **Actual input/source/build identity.** Read actual candidate source snapshots,
   build log, compiler artifact and pinned executable, not booleans alone.
   Compare the production source delta with committed M194b: only allocated
   gatefloor traversal/helper/comments may change. M194b producer, consumer,
   controller and scorer bytes must remain unchanged. Discover the new
   out-of-crate Rust test includes from their explicit source declarations;
   require every compiler input in the build and run snapshot maps. In
   particular, a build whose normal tracked sources are complete but whose
   external test source is omitted must fail this independent check. Distinct
   author target directories do not satisfy the M194b reader's fixed build
   argv: the candidate's scored build must have that exact argv and recorded
   compilation. No baseline executable or artifact may be overwritten.

2. **Complete matched actual outputs.** Independently read all 40 candidate
   TIFFs and all 40 baseline TIFFs, pairing by `(scene, repeat, arm)` rather
   than row position or filename order. Require the fixed twenty-case matrix,
   two arms each, eight named paired repetitions on each scalar scene,
   identical source manifest hashes, actual geometry/configuration and score
   masks. Missing/duplicated/mislabeled cases, changed input/model, wrong crop
   or target convention must refuse comparison even when record checksums
   are coherently updated. Treat valid reordering/byte-copy as inert only if
   the declared interface allows it; otherwise label an interface refusal.

3. **Independent numerical difference read.** Use direct TIFF decoding and
   literal native ROI offsets, independent cell/pupil integration and direct
   complex wave projection as in M194b's separate readout. Compute delivered
   candidate-minus-baseline bias, MSE, RMSE, wave amplitude and phase from the
   arrays. Both target conventions and all RGB channels remain. Use streaming
   Welford accumulation for per-photosite temporal variance. Match repeats
   across versions; independently derive per-repeat MSE differences and
   their whole-image SEM, plus leave-one-repeat-out variance-difference
   uncertainty if reported. Pixel count is not an independent sample count.
   Numerical agreement tolerances are arithmetic verification tolerances:
   0.001 DN for independently integrated RMSE, 1e-8 DN for wave readout and
   1e-8 DN² for same-array temporal variance. They are not promotion bars.

4. **Live and inert comparator controls.** Before trusting a reported zero or
   direction, compare an unchanged array/package with itself and require
   exact zero differences. On separately labelled diagnostic copies of an
   actual retained TIFF ROI, a constant +20 DN changes bias by +20 DN;
   spatial-only Gaussian blur sigma0.6 changes the registered wave amplitude;
   a channel permutation changes color error; added independent repeat noise
   changes temporal variance. Keep the flat/no-op blur control. Same-mean
   mismatched model or a changed-input binding must be refused by the
   comparison's provenance checks, not silently scored as the same candidate.
   These diagnostic arrays never replace a baseline or candidate artifact.
   Existing M194b model/blur controls may be cited where the comparison reuses
   their exact implementation, but new difference formulas need a live check.

5. **Direction and numerical scope.** Negative candidate-minus-baseline MSE
   favors the candidate only on that named target/component. Blur can reduce
   noisy MSE and also remove detail; wave and noise-off rows expose this.
   Neither in-focus observation nor actual single-frame output is a universal
   attainable error floor. The twice-refinement-difference policy is an
   engineering refusal rule, not a propagated error bound for arbitrary
   nonlinear metrics. Since actual producer samples are identical across
   versions, shared approximation errors need not cause an output difference;
   this does not license sub-budget claims of physical accuracy.

6. **Disposition and evidence.** A verified layout repair with small mixed
   quality movements is not a universal quality improvement. Report adverse,
   negligible and target-dependent movement without tuning. The independent
   semantics lane must establish actual padding/odd-tail/packed legacy
   invariants; these cannot be inferred from this comparison's standard
   layout alone. Preserve failed attempts, exact source/index/revision
   digests, commands, raw logs and content bindings. No modification of the
   frozen M194b artifacts or scorecard is allowed.

Root may expose its comparison API and candidate paths after this document;
those names can be recorded without changing these choices. The review may
finish with a supported repair and no directional quality claim.

## Controller API clarification, before implementation/results

The unchanged M194b driver requires its exact `sources()` map on every call.
Root therefore retains that evidence unchanged and adds a separate M194c
supplementary source attestation around build, the complete render and scoring.
The union of the original source map and this external attestation must cover
the actual compiler inputs; item1 does not require rewriting M194b's map.
The supplement must bind the included external Rust files, its controller and
preregistration, exact before/after source sets and hashes, snapshots and the
build/run/score digests. An omitted included test, renamed or added source-set
member, changed supplemental bytes or a supplement for a different run must
fail. No candidate outputs have been read at this clarification.
