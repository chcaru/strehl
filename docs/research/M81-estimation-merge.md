# M81 — estimation merge

**VERDICT — MEASURED: NO SHIP.** The stack-calibrated gate failed the
pre-registered spectral model-sensitivity control on **3/5 stacks**. In the
paired comparison with the shipped `DEFAULT_GATE = 4.0`, it passed **0/5**:
three stacks had invalid stack-specific M80 controls, and each of the two
readable stacks lost the registered detail-to-residual comparison. All five
candidate outputs also retained singleton pixels whose selection penalty is
not priced by the per-pixel sigma model. The automatic gate is therefore
removed from the production CLI and core API; the default remains unchanged.

**ARCHITECTURAL DECISION — ARGUED and IMPLEMENTED: multiple passes, no focus
volume.** M81 used one decode to measure M70's global spectral target and elect
the regularised winner, a second decode to measure the admission-threshold
distribution, and the existing stacker's two decodes to run a paired gate
sweep. The experiment therefore performed **four actual decodes**, not two.
Its per-pixel state is fixed in stack depth; it retains no
`width × height × frames` focus volume. The small spectral record is
`O(24N)`, while the image-sized state is `O(workers × pixels)`.

## M81 §1 — Source findings and the mechanism actually tested

**MEASURED.** M2 §3.2.3, the source of SYNTHESIS fact 19, measured an
**unweighted mean of all 22 frames** at **0.534×** the noise of frame 11 on
`109MSDCF`; it did not measure a noise-gated mean at 0.534×. The same table
measured argmax at 1.253×, a shifted-winner-map placebo at 0.981×, and a
17×17-regularised argmax at 1.075×. The source therefore establishes the noise
value of averaging and the cost of noise-coupled selection, but **0.534× is not
a measured operating point of the shipped gate**.

**MEASURED.** M15 §5.1, the source of SYNTHESIS fact 84, measured the w13
absolute reconstruction error over 30 synthetic cells falling from
**24.79 DN at regulariser width 1 to 15.99 DN at width 17**, a **35.5%**
reduction. M15 also records the scope: this is absolute reconstruction error on
its registered cell corpus, not a five-stack estimate of the full merge.

**MEASURED.** Source history shows that commit `e848b56` had already built both
mechanisms before M81: the 17×17 regularised winner field and the noise-gated
arithmetic mean. M81 did not claim to build them a second time. It built and
tested the missing composition: a gate-free spectral target followed by a
spatial admission solve, then those existing mechanisms at the solved gate.

**MEASURED.** M77's own fact 39 measured gates of 38.534 and 11.642 to match
spectral counts of 4.148 and 4.050 on the sibling `wrapped-text` stacks, a
3.31× gate difference for a 2.4% count difference. M77's own fact 40 measured a
flat ROI freezing while frame-average admission continued to rise. Those
source results reject a portable constant and also warn that a frame-average
target cannot describe local admission.

**MEASURED/ARGUED.** M70 §22 supplied the requested late answer. M70's local
form is measured only down to **128 GQ samples / 255 sensor pixels** with Welch
tile 64; its pure-noise null spans approximately −2.5 to +3.0 even at the
largest window. M70 §22.6 also states that spectral `n_eff` is a count of
informative frames, **not a measured optimal hard-admission target**. M81
therefore retained M70's global 24-textured-patch instrument and treated
`spectral count = mean spatial admission` as the hypothesis under test, not as
an established identity. No local gate was invented.

## M81 §2 — Pre-registration and provenance

**MEASURED.** `experiments/M81-estimation-merge/PREREGISTRATION.md` was
committed at `0bf6e46` before any M81 arm ran. Commit `ff8c166`, also before
measurement, fixed the exact calibration invocation and 7028×4688 analysis
bounds. It registered:

- **ARGUED.** Gate 4 as the control and the solved `T*` as the candidate.
- **ARGUED.** Per-stack acceptance of
  `Q(T*) / Q(4) >= 1.01`, `D(T*) / D(4) >= 0.98`, and a fresh target hit within
  1%.
- **ARGUED.** A mandatory **5/5** result, with any failed control or unreadable
  stack forcing no ship.
- **ARGUED.** The exact five subjects, N values, 256-plane-pixel ROIs,
  M70 spectral geometry, default worker count 6, and every non-default flag.
- **ARGUED.** A three-seed, truth-referenced single-frame floor, plus a gate-zero
  selector required to fail it.

**MEASURED.** The final evidence executable was built from experimental commit
`4b00dd820de38ed5dc4844d906ada64c833c3699` with Rust/Cargo 1.98.0 MSVC and a
private `CARGO_TARGET_DIR`. It is 8,424,448 bytes with SHA-256
`e16fa0d2a4100ba9c534129e781ab869bc93bdf53ff7bc1d7504b7e7ab0aed82`.
`binary.json` and every paired-arm log name that executable and hash.

## M81 §3 — Implementation

**MEASURED/ARGUED.** The experimental core instrument reproduced M70's
configuration exactly: 24 fixed 256×256 GQ patches; 128×128 Welch tiles at 50%
overlap; periodic Hann; the registered low and three mid bands; texture
threshold 10; and `sum(S) / max(S)` with no per-frame clipping. A pure-Rust
radix-2 two-dimensional FFT avoided adding a dependency.

**MEASURED/ARGUED.** Calibration pass one folded the regularised best focus
field and 24 small spectral records per frame. Pass two converted each
frame/pixel focus gap into the gate needed to admit it and folded that value
into a mergeable histogram. The histogram discards 14 low `f32` bits, retaining
the exponent and nine mantissa bits for approximately 0.2% relative threshold
resolution. Its memory is fixed in N.

**MEASURED/ARGUED.** Gate zero admits the tie-broken elected winner and no
other exact-focus ties. An early implementation admitted every tied response,
so the gate-zero control read slightly above one. M81 repaired both the runtime
admission rule and histogram semantics, then added a tie-specific regression
test. The final five-stack controls read exactly 1.000000000 at gate zero and
exactly N beyond the widest finite gap.

**ARGUED.** Conceptually the calibrated production path needs three visits:
measure target/winner, solve admission, and estimate. The isolated experiment
used four because `calibrate-gate` and `stack` were separate commands and M81
did not modify M80-owned `merge_cmd.rs`. Reusing calibration pass one's winner
would remove one decode, but the failed estimator does not justify that
integration work.

## M81 §4 — Spectral and gate controls

**MEASURED.** A fresh Python implementation decoded all five RAW stacks and
recomputed M70's corrected estimator; no old `.npz` target was reused. Rust
agreed within 0.0000841% relative on every nominal target, against the
pre-registered 2% bar.

| Class | Stack | N | Python/Rust relative error | `n_spec` nominal | `T*` | realised mean `n_eff` | fresh G2 relative error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MEASURED | `wrapped-text-1` | 130 | 8.230e-8 | 4.147660 | 38.749996 | 4.148225 | 8.197e-5 |
| MEASURED | `109MSDCF` | 22 | 8.403e-7 | 4.798517 | 3.828125 | 4.798460 | 1.078e-4 |
| MEASURED | `coffee-bean` | 105 | 1.396e-9 | 5.432140 | 1.191406 | 5.434702 | 5.265e-4 |
| MEASURED | `foam` | 100 | 2.912e-8 | 5.499487 | 47.874996 | 5.500630 | 2.752e-4 |
| MEASURED | `bee-1` | 299 | 2.533e-8 | 11.719199 | 1.406250 | 11.723698 | 4.096e-4 |

**MEASURED.** S1, S2, S3, S5, G1, G2, G3, and G4 passed. The N=41 static
spectral plant returned exactly 41.000000; the independent-noise plant returned
−0.071319. Every solve was measured, bracketed, monotone, and within 1% of its
target.

**MEASURED.** Fatal control S4 failed on 3/5 stacks. The table applies M70's
measured photon-transfer variance multipliers, 0.950 and 1.093; the registered
bar was full target span divided by nominal target no greater than 0.20.

| Class | Stack | `n_spec` at 0.950× | nominal | `n_spec` at 1.093× | span / nominal | S4 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| MEASURED | `wrapped-text-1` | 4.726371 | 4.147660 | 3.429687 | 0.312630 | **FAIL** |
| MEASURED | `109MSDCF` | 7.690965 | 4.798517 | −6.125e31 | 1.276e31 | **FAIL** |
| MEASURED | `coffee-bean` | 5.522381 | 5.432140 | 5.389715 | 0.024422 | pass |
| MEASURED | `foam` | 5.591419 | 5.499487 | 5.327484 | 0.047993 | pass |
| MEASURED | `bee-1` | 13.069878 | 11.719199 | 9.256310 | 0.325412 | **FAIL** |

**MEASURED/ARGUED.** The `109MSDCF` denominator approaches zero in one mid
band at 1.093× variance, producing the enormous negative target. This is not a
Rust numerical discrepancy: the fresh Python reference reproduces it. It is
the instability M70 warned an unclipped accumulated noise subtraction can
exhibit. A self-calibration dominated by the known model uncertainty is not
calibrated, so S4 alone forces no ship.

## M81 §5 — Paired gate-4 comparison on all five stacks

**DERIVED.** For each arm, `D = sqrt(q_signal_power)` from M80's repaired
cross-fitted detail instrument, `H` is M77 invariant 1's flat-ROI high-pass SD,
and `Q = D/H`. The ratios below are candidate `T*` divided by gate-4 control.
The shipped, argmax-biased pre-M80 `RETENTION` was not used.

**MEASURED/ARGUED.** M80 §5 validates its global noise null and detail positive
control, while M80 §9 requires a stack's flat control to be flat. M81 therefore
applied M77's pre-registered G0' flat-contamination control as a stack-specific
precondition. `wrapped-text-1`, `109MSDCF`, and `foam` fail it; `foam` also has
detail `STRUCTURE` below M80's positive-control floor in both arms. Their
numbers are reported but not accepted as readable evidence.

| Class | Stack | N | gate 4 mean `n_eff` | `T*` mean `n_eff` | D ratio | H ratio | Q ratio | M77 flat contamination | M80-readable | Registered verdict |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| MEASURED | `wrapped-text-1` | 130 | 1.238 | 4.148 | 0.933770 | 0.502833 | 1.857017 | 2.6339× | no | **UNREADABLE**; D also fails |
| MEASURED | `109MSDCF` | 22 | 4.987 | 4.798 | 1.000196 | 1.028199 | 0.972765 | 1.1399× | no | **UNREADABLE**; Q also fails |
| MEASURED | `coffee-bean` | 105 | 31.614 | 5.435 | 1.006680 | 3.259977 | 0.308800 | 1.0968× | yes | **FAIL Q** |
| MEASURED | `foam` | 100 | 1.359 | 5.501 | 0.515710 | 0.945476 | 0.545449 | 15.8769× | no | **UNREADABLE**; D and Q also fail |
| MEASURED | `bee-1` | 299 | 70.146 | 11.724 | 1.005490 | 1.513470 | 0.664361 | 1.0666× | yes | **FAIL Q** |

**MEASURED.** M77's copied stability controls pass for both ROIs on
`wrapped-text-1`, `109MSDCF`, `foam`, and `bee-1`; both fail on `coffee-bean`.
Its detail-positive control passes on four stacks and fails on `foam`. These
qualifications are recorded in `arms-results.json` rather than silently
discarded.

**MEASURED.** The paired result is **0/5**. Even if the three invalid
stack-specific M80 preconditions were ignored post hoc, every row misses at
least one numerical acceptance clause. The two readable rows are especially
direct: calibrating down from gate 4 to 1.191 on `coffee-bean` increases flat
residual 3.260×, and calibrating down to 1.406 on `bee-1` increases it 1.513×,
without a compensating 1% increase in `Q`.

## M81 §6 — The single-frame floor

**MEASURED.** The pre-registered Rust test used three fixed seeds, known latent
truth, 16 scored 16×16 blocks per seed, and a static N=41 burst whose calibrated
target is all frames. Candidate RMS stayed below pooled single-frame RMS in
every block. Gate zero was the planted selector failure:

| Class | Seed | Candidate worst / single-frame RMS | Selector worst / single-frame RMS | Selector blocks worse than one frame |
| --- | --- | ---: | ---: | ---: |
| MEASURED | `0x4d36340000000001` | 0.319751× | 1.124191× | 7/16 |
| MEASURED | `0xd3014db97f4a7c14` | 0.294348× | 1.055965× | 7/16 |
| MEASURED | `0x9c837e32d192ed02` | 0.301695× | 1.080274× | 9/16 |

**MEASURED.** The same test asserts, for every plant pixel, `n >= 1` and
reported predicted sigma no larger than the model's single-frame sigma. The
negative control proves that the truth-referenced branch can reject a selector.

**MEASURED/ARGUED.** The real candidates nevertheless retain singleton pixels
on every stack: **5.20%** on `wrapped-text-1`, **4.92%** on `109MSDCF`,
**63.64%** on `coffee-bean`, **2.95%** on `foam`, and **46.19%** on `bee-1`.
At a singleton, the current predicted sigma is a single-sample noise value and
does not include the max-over-N selection penalty. M80 repaired a regional
detail-comparison statistic, not this per-pixel uncertainty model. Therefore
the requested everywhere floor is not established on any real stack, and the
pre-registered rule makes all five exposures fatal.

## M81 §7 — Controls made to fail

**MEASURED.** A Python harness replaced the exact unclipped-sum source bytes
with per-frame clipping, read the planted bytes back, and ran one fully
qualified exact Rust test. The mutation changed the independent-noise result
from −0.071319 to **7.446821**, failed S3, and exited 101. A second byte-exact
mutation reversed histogram accumulation; the bracketed solve failed and
exited 101. Both files were restored byte-for-byte.

**MEASURED.** The harness's first version used a shortened Cargo filter with
`--exact`; Cargo selected zero tests and exited zero. M81 rejected that result,
changed the harness to require the complete test path and the literal
`running 1 test`, and reran both controls. This is recorded because it
reproduced the exact silent-control failure the brief warned about.

**MEASURED.** The first real gate-zero control also failed: exact non-winning
focus ties made mean admission slightly exceed one. That failure was retained
until the tie semantics and regression test were repaired; the five final
gate-zero values are exact.

## M81 §8 — Interpretation and boundaries

**ARGUED.** M77 correctly established that a universal gate constant cannot
produce a universal admission target. M81 does not overturn that result. It
shows that the particular replacement tested here is not ready: the M70 count
is model-unstable on 3/5 stacks, is not a measured hard-admission optimum, and
is global while M77 measured admission to be spatially non-uniform.

**ARGUED.** The failed composition does not justify returning to raw argmax.
The existing 17×17 winner regulariser and gated arithmetic mean remain the
production estimator. M81 removes only automatic spectral calibration and
leaves explicit gate 4 as the control/default established before this
milestone.

**ARGUED.** A future attempt needs a target tied to the estimator's actual
loss, not merely an information count. The remaining gap could require
continuous focus-axis weighting and a calibrated singleton selection term.
Those findings do not license M81 to build multi-frame deconvolution, a
depth-posterior object, occlusion unmixing, or an outlier mask.

## M81 §9 — Candidate facts

| M81 namespace | Claim | Label | Evidence |
| --- | --- | --- | --- |
| **M81's own fact 1** | The exact M70 spectral estimator is implementable in Rust without a focus volume; Rust reproduces fresh Python within 8.403e-7 relative on all five stacks. | MEASURED | `reference.json`, `calibration-results.json` |
| **M81's own fact 2** | The proposed calibration is not robust to the already-measured photon-transfer uncertainty: S4 fails on `wrapped-text-1`, `109MSDCF`, and `bee-1`, passing only 2/5. | MEASURED | `calibration.log`, `calibration-results.json` |
| **M81's own fact 3** | The calibrated merge beats gate 4 on 0/5 registered stacks: three comparisons are unreadable under M80's stack-specific flat precondition, and the two readable comparisons fail Q. | MEASURED | `arms-*.log`, `arms-results.json`, M80 §9 |
| **M81's own fact 4** | Every real candidate retains unpriced singleton selection exposure, from 2.95% on `foam` to 63.64% on `coffee-bean`; the everywhere single-frame floor is therefore unproved on 5/5. | MEASURED/ARGUED | `arms-results.json`, M81 §6 |
| **M81's own fact 5** | SYNTHESIS fact 19's source value 0.534× belongs to the unweighted mean of all 22 frames, not to a measured noise-gated operating point. | MEASURED | M2 §3.2.3 |
| **M81's own fact 6** | M70's spectral count can be a global calibration heuristic but is not yet a calibrated admission target: M70 explicitly measured a count, and the M81 composition fails both model sensitivity and paired acceptance. | MEASURED/ARGUED | M70 §22.6; M81 §§4–5 |

## M81 §10 — Reproduction and evidence

**MEASURED.** Durable evidence is under
`experiments/M81-estimation-merge/`:

- **MEASURED.** Frozen design: `PREREGISTRATION.md`.
- **MEASURED.** Fresh independent spectral implementation and values:
  `reference.py`, `reference.json`.
- **MEASURED.** Private binary provenance: `build.log`, `binary.json`.
- **MEASURED.** Five-stack calibration:
  `calibration.log`, `calibration-results.json`,
  `analyse_calibration.py`.
- **MEASURED.** Five paired arms:
  `arms-*.log`, `arms-results.json`, `analyse_arms.py`.
- **MEASURED.** Byte-confirmed red controls:
  `mutation_controls.py`, `mutation-controls.log`.
- **MEASURED.** Spectral and single-frame plants:
  `spectral-plants.log`, `floor.log`.

**MEASURED.** The calibration and floor test code is preserved at experimental
commit `4b00dd8`; it is deliberately absent from the final production tree
because the registered no-ship condition fired.

## M81 §11 — Final disposition and checks

**MEASURED.** `crates/strehl-cli/src/main.rs`,
`crates/strehl-core/src/lib.rs`, and `crates/strehl-core/src/merge.rs` are
byte-equivalent to their state immediately before M81 implementation commit
`885247c`; `crates/strehl-core/src/calibration.rs` is removed. M81 never edited
M80-owned `crates/strehl-cli/src/merge_cmd.rs`.

**MEASURED.** On the restored production tree:

- **MEASURED.** `cargo fmt --all --check` passed.
- **MEASURED.** All **138** `strehl-core` tests passed.
- **MEASURED.** All **22** `merge_cmd::tests` passed.
- **MEASURED.** `cargo clippy --workspace --all-targets -- -D warnings` passed.
- **MEASURED.** All four M81 Python programs compiled, and both result
  analysers reproduced the tables above.
- **MEASURED.** `python scripts\corpus_lint.py` checked 107 Markdown files and
  30 Rust files and reported `OK — no violations`.
