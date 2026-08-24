# M81 — estimation merge

**VERDICT — MEASURED/ARGUED: NO SHIP; THE FOCUS-NOISE UNIT HYPOTHESIS IS
REFUTED.** On the two `wrapped-text` sibling stacks whose through-focus
responses M70 P34 measures agreeing within 4.7%, a fresh common-target ladder
requires raw gates 37.5 and 11.5, a 3.25× span. M81's primary
texture-qualified `FOCUS_NOISE_SD` correction changes those to 40.0 and 11.0
corrected units, a **3.63× span**, beyond the pre-registered 2× falsification
line and farther apart than before correction. Across all five required M77
stacks, the corrected constants span **49.54×**. M69's two published
stack-level estimators independently give sibling spans **4.09×** and
**3.57×** and five-stack spans **49.54×** and **50.49×**. The result does not
depend on which of the three estimators is used.

**VERDICT — MEASURED/ARGUED: THE CORRECTED GATE ALSO FAILS THE PRODUCT
CONTROL.** Re-expressing shipped corrected-unit gate 4 as raw gate `4*rho`
beats the shipped raw gate 4 on **0/5** required stacks. M77's registered flat
control makes three comparisons unreadable; the two readable stacks both miss
the pre-registered detail-to-residual bar. Every candidate leaves unpriced
singleton selection exposure, from **3.93% to 82.11%**, so the requested
"never worse than a single frame" floor is not established anywhere.

**ARCHITECTURAL DECISION — ARGUED and IMPLEMENTED IN THE EXPERIMENT:
multiple passes, no focus volume.** The production merge remains its existing
two-pass design: pass one elects the 17×17-regularised winner and pass two
folds every admitted RAW sample into the arithmetic mean. The unit experiment
uses M70's compact full-stack texture record, then one middle RAW frame and
32 synthetic replicates per accepted 512×512 tile, folded with Welford state.
Its memory is fixed in stack depth. M69 says real response noise requires a
textured static burst; because that capture does not exist, this instrument was
never eligible to become a production calibration path even if the unit
hypothesis had survived.

**FOLLOW-UP VERDICT — ARGUED: M80'S RISK BUDGET IS A VALID ABSTENTION
TEMPLATE, NOT YET A VALID MERGE GATE.** The existing gate is already
algebraically a normal-quantile rule under a fixed-pair Gaussian
approximation. That approximation does not describe a winner selected as the
maximum of N responses, and an alpha budget for rejecting a true tie does not
price the opposite error: admitting a defocused frame. A shippable
probabilistic gate still needs a selected-winner null, a spatially valid
response standard error, and a truth-linked non-inferiority margin. M80
explicitly leaves its analogous product margin unclaimed. M81 therefore does
not rename the failed threshold, add `--gate-alpha`, or ship an adaptive arm
merely because it adapts.

**FOLLOW-UP BUILD STATUS — MEASURED: STRICT CLIPPY IS GREEN.** The transient
M81-owned blocker was `clippy::too_many_arguments` on the experimental
`CalibrationScratch::compute` in `main.rs`: eight arguments against Clippy's
default limit of seven. Commit `bcde55e` removed that failed calibration path
when M81 restored the production source for NO SHIP. A fresh
workspace/all-targets run at commit `76b7f76` exits zero, so no speculative
source edit is made.

## M81 §1 — The redirection, and whether M81 agrees

**ARGUED.** M81 agrees with the redirection as a falsification. Testing whether
the unit restores one portable constant is simpler and better identified than
assuming that M70's informative-frame count is the count a hard gate should
admit. M70 §22.6 explicitly withdraws that identification: its spectral
`n_eff` is an information count, not a measured admission optimum.

**ARGUED.** M81 disagrees with one premise, not with the experiment. M69's
4.062× result is not a measured per-stack scalar dispersion. M69 fact 18
measures it across correlation lengths on a controlled texture plant. M69
fact 17's P2-derived stack scalars span 1.186×, while M69 fact 56's direct
synthetic-replicate stack scalars span 2.104× and explicitly conflict with the
P2 values. M69 §6 then says true response noise on moving-focus real data is
not identifiable without a textured static burst. The correction therefore
tests a strong hypothesis with imperfect scalar estimators; it does not
pretend M69 already supplied the missing real calibration.

**MEASURED.** M70 P34 is the decisive clean control. `wrapped-text-1` and
`wrapped-text-2` agree within 4.7% on M70's gate-free equal-average
through-focus ladder, and their spectral counts agree within 2.4%. M70 P35
places the local spectral floor at 255 sensor pixels. M70 P36 measures flat
tiles as unusable nulls rather than zero targets. M70 P37 shows why a global
moving-patch response must not be silently read as local physics.

**MEASURED.** M69's source also predicts that a scalar correction is small
relative to the gate disparity. Its Part-I P2 values on the six stacks used
here are 0.9285–1.1009; its Part-II direct B3 values are 0.8116–1.2281. Neither
source contains a per-stack correction remotely as large as the raw
common-target gate spread.

## M81 §2 — What was already built

**MEASURED.** M2 §3.2.3, the source of SYNTHESIS fact 19, measures the
unweighted mean of all 22 `109MSDCF` frames at **0.534×** the noise of frame
11. It does not measure a noise-gated operating point at 0.534×. The same
source measures argmax at 1.253×, its shifted-winner placebo at 0.981×, and a
17×17-regularised selector at 1.075×.

**MEASURED.** M15 §5.1, the source of SYNTHESIS fact 84, measures absolute
reconstruction error falling from 24.79 DN without spatial support to 15.99 DN
at regulariser width 17 over its 30 registered synthetic cells, a 35.5%
reduction.

**MEASURED.** Commit `e848b56` had already put both mechanisms in the shipped
path before M81: the 17×17 regularised winner field and the noise-gated
arithmetic mean. M81 did not duplicate them. It tested whether either proposed
automatic gate calibration made those existing mechanisms acceptable.

## M81 §3 — Frozen design and provenance

**MEASURED.** The original spectral arm was pre-registered at commits
`0bf6e46` and `ff8c166`, measured, parked, and reported NO SHIP at `bcde55e`.
After M70 §22 arrived, the corrected unit arm was separately frozen in
`PREREGISTRATION-UNIT.md` at commit `ea8e4ad` before its new calibration,
ladder, or paired result ran.

**MEASURED.** The amendment disclosed that the qualitative direction was not
blind: M69's published `rho` values, M77's coarse ladders, and the parked M81
solve already existed. It therefore fixed a fresh diagnostic target,
`mean n_eff = 4.000`, rather than reusing M70's count, and made no optimality
claim for that target.

**ARGUED.** The binary decision was fixed at corrected sibling and five-stack
spans no larger than 2×. The exact ladder was gates
`0, 0.25, 0.5, 1, 2, 4, 8, 16, 24, 32, 40, 48, 64, 96, 128`; the solve used
log-gate/log-`n_eff` interpolation between positive bracketing rungs and
forbade extrapolation.

**MEASURED.** The six-stack ladder and five paired runs used a private release
binary built from commit
`97dc93d9a2417085bf40fa8ac576a3eccdb381bc`. It is 8,278,016 bytes with
SHA-256
`925a83fa70205dc4cd23f78c03ddeb16c6e0ebb9eb1ce3268bdf5ac9cce4a2cd`.
Every run log repeats the commit and hash. The merge has no `--tile` flag.
The only non-default ladder flag was `--gate`; paired runs additionally named
the frozen 256-plane-pixel flat and detail ROIs.

**MEASURED.** The texture-calibration log names repository baseline
`178cfb1cd92e3ea7da9a7f84e9cffe2b3892c1a8`. The only intervening change before
the binary's `97dc93d` baseline normalised an M80 evidence log; the core,
`main.rs`, and `merge_cmd.rs` trees are byte-identical between the two commits.

| Class | Stack / subject | N | paired flat ROI | paired detail ROI |
| --- | --- | ---: | --- | --- |
| MEASURED | `wrapped-text-1` / wrapped label text | 130 | `32,1312,256,256` | `2208,672,256,256` |
| MEASURED | `wrapped-text-2` / wrapped label text | 120 | portability only | portability only |
| MEASURED | `109MSDCF` / acrylic paint | 22 | `1440,416,256,256` | `1952,1056,256,256` |
| MEASURED | `coffee-bean` / coffee bean | 105 | `32,416,256,256` | `1312,416,256,256` |
| MEASURED | `foam` / coffee foam | 100 | `1312,288,256,256` | `160,1952,256,256` |
| MEASURED | `bee-1` / bee anatomy | 299 | `2720,1568,256,256` | `1952,672,256,256` |

## M81 §4 — Texture-qualified response-noise calibration

**ARGUED/MEASURED.** The primary estimator applies M69 B3's synthetic-replicate
response measurement only to M70-qualified texture. It reads M70's exact 24
fixed patches, each 256 green-quincunx samples or 511 sensor pixels, with Welch
`--tile` **128**, periodic Hann, 50% overlap, and low-band
`peak signal / median model variance >= 10`. A passing centre contributes a
512×512 raw tile from the middle frame; a flat centre contributes nothing.

**ARGUED/MEASURED.** Each accepted tile receives 32 deterministic
photon-transfer-model noise replicates. The independent Python operator is
green luma, 3×3 Sobel, 27×27 box, noise normalisation, and the shipped 17×17
regulariser. Welford state retains no replicate cube. M69 B3's frozen-latent
debias is applied, and the stack scalar is the median accepted-patch mean.

**MEASURED.** The zero-signal temporal control returns `rho = 1.003112`,
inside the pre-registered `[0.98, 1.02]` interval. Every stack has at least 16
textured patches, and every within-stack patch-mean span is below the
pre-registered 2× scalar-readability line.

| Class | Stack | N | textured / flat patches | primary `rho` | patch min–max | patch span | calibration |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| MEASURED | `wrapped-text-1` | 130 | 24 / 0 | 0.936807 | 0.738264–1.190659 | 1.612783× | pass |
| MEASURED | `wrapped-text-2` | 120 | 24 / 0 | 1.044503 | 0.898421–1.368982 | 1.523764× | pass |
| MEASURED | `109MSDCF` | 22 | 22 / 2 | 1.115148 | 0.939996–1.204208 | 1.281077× | pass |
| MEASURED | `coffee-bean` | 105 | 16 / 8 | 0.865784 | 0.722109–1.147850 | 1.589579× | pass |
| MEASURED | `foam` | 100 | 24 / 0 | 1.196133 | 1.027628–1.568268 | 1.526105× | pass |
| MEASURED | `bee-1` | 299 | 16 / 8 | 0.932787 | 0.653345–1.107243 | 1.694730× | pass |

**ARGUED.** Passing these controls makes the scalar falsification readable; it
does not turn modeled synthetic noise into real measured response noise.
M69 fact 56 shows B3 and P2 disagree, and M69 §6 names the absent static burst
as the needed measurement.

## M81 §5 — Fresh common-target ladder: primary verdict

**MEASURED/DERIVED.** All six 15-rung admission ladders are non-decreasing and
bracket mean `n_eff = 4.000`. The solver's power-law plant recovers its known
gate within 0.1%, and substituting every solved gate back into its measured
interpolation segment recovers the target within 1%. Values below carry more
digits only to reproduce that interpolation; the CLI prints `n_eff` to three
decimals and the comparison does not support five-significant-figure physics.

| Class | Stack | N | raw gate at mean `n_eff = 4` | primary `T/rho` | M69 B3 `T/rho` | M69 P2 `T/rho` |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| MEASURED/DERIVED | `wrapped-text-1` | 130 | 37.518 | 40.049 | 39.921 | 37.342 |
| MEASURED/DERIVED | `wrapped-text-2` | 120 | 11.528 | 11.037 | 9.763 | 10.472 |
| MEASURED/DERIVED | `109MSDCF` | 22 | 3.022 | 2.710 | 2.880 | 3.052 |
| MEASURED/DERIVED | `coffee-bean` | 105 | 0.984 | 1.137 | 1.213 | 1.060 |
| MEASURED/DERIVED | `foam` | 100 | 32.987 | 27.578 | 26.861 | 32.143 |
| MEASURED/DERIVED | `bee-1` | 299 | 0.754 | 0.808 | 0.806 | 0.740 |

**MEASURED/DERIVED.** Before correction, the sibling gates span 3.254×. The
primary correction worsens that to **3.629×**; source B3 gives **4.089×** and
source P2 gives **3.566×**. All exceed the frozen 2× line, so U1 refutes the
unit hypothesis on the pair for which M70 supplies the common-physics control.

**MEASURED/DERIVED.** Across the five mandatory M77 stacks, raw target gates
span 49.752×. Primary, source B3, and source P2 corrected constants span
**49.538×**, **49.543×**, and **50.490×**, respectively. U2 also fails by more
than an order of magnitude. The correction changes the unit but does not
explain the admission geometry.

**ARGUED.** This result rejects a **per-stack scalar** repair. It does not
establish which non-scalar mechanism is sufficient. M69's own within-stack
texture dependence and M77's within-image non-uniform admission are compatible
with a local unit, but M70 P36 says flat regions supply no spectral calibration
target and the available corpus supplies no real static-noise measurement.
M81 therefore records the need and does not build a local profile.

## M81 §6 — Shipped gate 4 versus corrected-unit gate 4

**DERIVED.** `Gate::tolerance` is linear in `FOCUS_NOISE_SD`; corrected-unit
gate 4 is therefore emulated without production changes by raw gate `4*rho`.
The five candidate gates are 3.747, 4.461, 3.463, 4.785, and 3.731 in table
order below.

**MEASURED/DERIVED.** `D = sqrt(q_signal_power)` uses M80's final cross-fitted
resolved-detail statistic, `H` is the flat-ROI high-pass SD, and `Q = D/H`.
Every selector detail target is measurable under M80's final one-sided
control. M77's independently registered flat-contamination precondition fails
on `wrapped-text-1`, `109MSDCF`, and `foam`, so those rows remain unreadable
rather than being promoted from their numerical signs.

| Class | Stack | N | candidate gate | control / candidate mean `n_eff` | D ratio | H ratio | Q ratio | M77 flat precondition | candidate singleton | verdict |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| MEASURED | `wrapped-text-1` | 130 | 3.747 | 1.238 / 1.224 | 1.000419 | 1.003562 | 0.996868 | fail | 82.11% | **UNREADABLE** |
| MEASURED | `109MSDCF` | 22 | 4.461 | 4.987 / 5.500 | 0.998514 | 0.935434 | 1.067435 | fail | 3.93% | **UNREADABLE** |
| MEASURED | `coffee-bean` | 105 | 3.463 | 31.614 / 29.608 | 1.000692 | 1.020718 | 0.980380 | pass | 56.55% | **FAIL Q** |
| MEASURED | `foam` | 100 | 4.785 | 1.359 / 1.431 | 0.983929 | 0.998973 | 0.984941 | fail | 66.53% | **UNREADABLE** |
| MEASURED | `bee-1` | 299 | 3.731 | 70.146 / 67.434 | 1.000548 | 1.001347 | 0.999203 | pass | 31.87% | **FAIL Q** |

**MEASURED.** The paired result is **0/5**. `109MSDCF` is the only numerical
row to clear both `D >= 0.98` and `Q >= 1.01`, but its flat control fails and
the row is unreadable. The two readable rows both preserve D and lose Q. No
post-hoc relaxation converts this into the required 5/5 win.

## M81 §7 — The single-frame floor

**MEASURED.** Candidate model-predicted sigma gains are 0.9444, 0.4698,
0.6724, 0.8920, and 0.5518 across the five stacks, all no larger than the
single-frame model value. The estimator structurally admits its elected winner
at every pixel, and the existing core test
`averaging_beats_one_frame_and_selection_does_not` checks the two branches.

**MEASURED/ARGUED.** That model is deliberately incomplete at `n = 1`.
`merge.rs` records the reopened gap: singleton selection is correlated with
the same noise that elected it, while `SELECTION_INFLATION` has no surviving
measured price. The unit candidate leaves singleton exposure on **5/5** stacks:
82.11%, 3.93%, 56.55%, 66.53%, and 31.87%. The requested everywhere floor is
therefore **not established**, which independently forces no ship.

**MEASURED.** M81's earlier truth-referenced static-burst test proved its
parked high-admission candidate below pooled single-frame RMS on all 48 scored
blocks and made its gate-zero selector fail on 23/48. That is a valid
instrument control preserved in `floor.log`, not evidence for these five
new scalar-unit candidates; M81 does not transfer the result.

## M81 §8 — The parked spectral-count arm

**MEASURED.** Before M70 §22, M81 implemented the dispatched
`spectral n_eff -> mean admission` composition. Rust reproduced a fresh Python
M70 estimator within 8.403e-7 relative on all five stacks and solved a
gate with fixed-in-N memory.

**MEASURED.** Its pre-registered photon-transfer sensitivity control failed on
3/5 stacks, its gate-4 paired arm passed 0/5, and every real candidate retained
singleton exposure. Commit `bcde55e` removed its production integration and
recorded NO SHIP. M70 §22 later supplied the more fundamental objection: the
target identity itself had never been measured.

**ARGUED.** The implementation remains useful evidence that a global spectral
measurement and spatial admission histogram can be computed without a focus
volume. It is not a fallback product arm and none of its target values choose
the corrected-unit experiment.

## M81 §9 — Controls made to fail

**MEASURED.** The corrected-unit algebra plant uses
`rho = [0.5, 1, 2]`, raw target gates `[2, 4, 8]`, and must recover constants
`[4, 4, 4]` by division. `unit_mutation_control.py` constructs the exact byte
mutation from division to multiplication, writes it, verifies the planted
bytes by read-back, and invokes exactly two declared self-tests. The mutation
produces `[1, 4, 16]`, exits nonzero, and the harness restores the source
byte-for-byte.

**MEASURED.** The zero-signal temporal calibration control was also capable of
failure and read `rho = 1.003112` against its ±2% bar. All ladder processes and
all paired processes exited zero, and every log records the frozen binary
hash. M80 independently validates the detail statistic's noise null,
detectability transition, retained-detail control, and byte-planted negative
control in M80 §§5–6.

## M81 §10 — Candidate facts

| M81 namespace | Claim | Label | Evidence |
| --- | --- | --- | --- |
| **M81's own fact 1** | The exact M70 spectral estimator is implementable in Rust without a focus volume; its parked implementation reproduced fresh Python within 8.403e-7 relative on all five original stacks. | MEASURED | `reference.json`, `calibration-results.json` |
| **M81's own fact 2** | The parked spectral calibration is not robust to measured photon-transfer uncertainty: its registered sensitivity control failed on `wrapped-text-1`, `109MSDCF`, and `bee-1`. | MEASURED | `calibration-results.json` |
| **M81's own fact 3** | The parked spectral candidate beat gate 4 on 0/5 registered stacks. | MEASURED | `arms-results.json` |
| **M81's own fact 4** | The parked spectral candidates left unpriced singleton exposure from 2.95% to 63.64%, so their everywhere floor was unproved. | MEASURED/ARGUED | `arms-results.json` |
| **M81's own fact 5** | SYNTHESIS fact 19's source value 0.534× is the unweighted mean of all 22 frames, not a measured noise-gated operating point. | MEASURED | M2 §3.2.3 |
| **M81's own fact 6** | M70's spectral count is not a measured optimal hard-admission target; M81's attempted composition also failed model sensitivity and paired acceptance. | MEASURED/ARGUED | M70 §22.6; M81 §8 |
| **M81's own fact 7** | M69's 4.062× result is a controlled texture-form sweep, not a per-stack scalar spread; M69's competing stack-level estimators span 1.186× and 2.104×. | MEASURED | M69 facts 17, 18, and 56 |
| **M81's own fact 8** | The texture-qualified unit calibration is readable on all six stacks: 16–24 accepted 511-sensor-pixel patches per stack, flat control `rho = 1.003112`, and patch-mean spans 1.281–1.695×. | MEASURED | `unit-calibration.json` |
| **M81's own fact 9** | Per-stack `FOCUS_NOISE_SD` correction does not restore a sibling constant: corrected `wrapped-text-1/2` spans are 3.629× primary, 4.089× B3, and 3.566× P2 against the frozen 2× line. | MEASURED/DERIVED | `unit-results.json` |
| **M81's own fact 10** | Across all five M77 stacks, corrected common-target constants span 49.538× primary, 49.543× B3, and 50.490× P2. | MEASURED/DERIVED | `unit-results.json` |
| **M81's own fact 11** | Corrected-unit gate 4 beats shipped raw gate 4 on 0/5: three rows are unreadable under the registered flat control, and both readable rows fail Q. | MEASURED | `unit-arms-results.json` |
| **M81's own fact 12** | Every corrected-unit candidate retains unpriced singleton exposure, from 3.93% on `109MSDCF` to 82.11% on `wrapped-text-1`; the everywhere single-frame floor remains unproved. | MEASURED/ARGUED | `unit-arms-results.json` |
| **M81's own fact 13** | Under a preselected independent-pair Gaussian approximation, the shipped gate threshold is already a z-like risk number; its actual reference is a maximum selected over N, so a per-comparison alpha does not transfer. | DERIVED/ARGUED | M81 §12.2; `merge.rs` |
| **M81's own fact 14** | A false-rejection budget for tied focus responses does not bound defocus admitted by a low-power test. A risk-based gate additionally requires a selected-winner null, a local response standard error, and a truth-linked non-inferiority margin. | ARGUED | M81 §12.2–§12.3; M80 §§8–9 |
| **M81's own fact 15** | The transient `main.rs` blocker was an eight-argument `CalibrationScratch::compute`; removing the failed experimental path at `bcde55e` cleared it, and strict workspace/all-targets Clippy passes at `76b7f76`. | MEASURED | `risk-budget-main-clippy.log`, `risk-budget-current-clippy.log` |

## M81 §11 — Reproduction and final disposition

**MEASURED.** Durable evidence is under
`experiments/M81-estimation-merge/`:

- **MEASURED.** Frozen designs: `PREREGISTRATION.md` and
  `PREREGISTRATION-UNIT.md`.
- **MEASURED.** Texture calibration: `unit_calibration.py`,
  `unit-calibration.log`, and `unit-calibration.json`.
- **MEASURED.** Six fresh ladders: `run_unit_ladders.ps1`,
  `unit-ladder-*.log`, `analyse_unit.py`, and `unit-results.json`.
- **MEASURED.** Five paired arms: `run_unit_arms.ps1`,
  `unit-arms-*.log`, `analyse_unit_arms.py`, and
  `unit-arms-results.json`.
- **MEASURED.** Frozen executable provenance: `unit-build.log` and
  `unit-binary.json`.
- **MEASURED.** Negative control: `unit_mutation_control.py` and
  `unit-mutation-control.log`.
- **MEASURED.** Parked-arm evidence remains in the same directory under its
  original names.

**MEASURED.** M81 makes no production change. It does not modify M80-owned
`crates/strehl-cli/src/merge_cmd.rs`, does not change `DEFAULT_GATE`, and does
not add multi-frame deconvolution, a depth posterior, occlusion unmixing, or an
outlier mask.

**ARGUED.** The scalar unit hypothesis was the right redirection and the result
is useful precisely because it failed cleanly. The next evidence must identify
the spatially local response-noise unit on real texture or choose a gate by a
truth-linked estimator loss. M69's requested textured static burst is the
minimum capture for the former. M81 does not infer either solution from the
negative.

**MEASURED.** Rust and Cargo are 1.98.0 MSVC. All **138** `strehl-core` tests
and all **25** selected `merge_cmd::tests` pass. Strict
`cargo clippy --workspace --all-targets -- -D warnings` and
`cargo fmt --all --check` pass. All four new Python programs compile; both
reducers reproduce byte-identical JSON; the byte-restoring negative control
passes; and corpus lint checks 107 Markdown files and 30 Rust files and reports
`OK — no violations`. Exact outputs are preserved in `unit-*-tests.log`,
`unit-clippy.log`, `unit-fmt.log`, `unit-python-checks.log`,
`unit-toolchain.log`, and `unit-corpus-lint.log`.

## M81 §12 — M80 risk-budget and lint follow-up

### M81 §12.1 — What M80's alpha establishes

**DERIVED/ARGUED.** M80's own §4 derives the null variance of its signed
cross-fitted detail power and allows the acceptance instrument to answer only
when

\[
Q_0 > 2.326347874\,\operatorname{SE}(Q_0).
\]

M80 identifies `2.326347874` as the one-sided standard-normal 99% quantile and
pre-registers M80 alpha = 0.01 as the sole policy choice. The statistic has a
defined noise null; the remaining DN threshold follows from the calibrated
gradient covariance, ROI geometry, and invocation rather than tuning.

**MEASURED/DERIVED.** M80's own §5 validates that decision on 1,000 synthetic
null draws at each of M80 N = 22, M80 N = 130, and M80 N = 299: it reports 16,
8, and 10 false answers against its frozen ceiling of 18. All three tested
depths first answer on the discrete contrast ladder at M80's 8-DN rung. That
does not establish one exact portable 8-DN boundary: M80's continuously
derived crossings are 4.746507, 5.764350, and 6.200540 DN, and M80 accepts the
observations within a pre-registered factor-of-two rung. The result validates
the refusal rule over those synthetic configurations, not a universal
real-scene DN constant.

**ARGUED.** M81 adopts the design principle where it fits: an instrument
should abstain unless a declared false-answer budget permits it to answer.
That is why M81 respects M80's `NO TARGET` state and does not treat a
detail-free region as zero detail. M81's paired arm also does not use M80's
`DETAIL_COLLAPSE_FLOOR = 0.90` as acceptance evidence. M80's own §8 leaves
that product tolerance unclaimed; M81 instead used its separately
pre-registered D and Q ratios.

### M81 §12.2 — Why alpha alone does not define admission

**DERIVED.** The shipped rule is

\[
\widehat F_{\max}-\widehat F_i
 \le T\sqrt{2}\,\mathtt{FOCUS\_NOISE\_SD}.
\]

If the two responses were independent, Gaussian, equally noisy, and chosen
before observing them, setting \(T=z_{1-\alpha}\) would expose a one-sided
false-rejection rate for a truly tied pair. In that restricted model the
current `T` is already the proposed risk coordinate; replacing shipped
`DEFAULT_GATE = 4.0` with an alpha spelling changes no admission geometry.

**ARGUED.** The shipped comparison does not meet that model. The reference is
the observed maximum over M81 N = 22–299 frames. Its selection offset and tail
therefore depend on N and on the joint response distribution; `merge.rs`
already records this winner's curse. M69 further shows that the response-noise
scale changes with texture, while M81's own fact 8 measures within-stack
patch-mean spans of 1.281–1.695×. M81's own facts 9–11 then show that a scalar
unit correction neither restores portability nor beats the control. A
per-comparison normal quantile cannot repair an unmeasured local standard error
or a selected maximum.

**ARGUED.** More fundamentally, this is the wrong error budget for the product
decision. The rule above admits a frame when it fails to demonstrate that the
frame is worse. Alpha can bound exclusion of a genuinely tied frame under a
calibrated null; it cannot bound admission of a defocused frame when the test
has low power. Turning non-rejection into evidence of equivalence requires a
non-inferiority margin: the largest true response or reconstruction loss that
may safely enter the mean. Noise determines the uncertainty around that
margin, but it cannot choose the margin. M80's own §§8–9 draw the same boundary
for the repaired instrument: the noise-derived refusal rule does not select
its unclaimed product floor and does not choose an operating gate.

### M81 §12.3 — What would make a risk gate testable

**ARGUED.** A later risk-gate milestone can become decidable by
pre-registering all of:

1. a local response standard-error and covariance estimator validated on
   M69's requested textured static burst;
2. the selected-winner distribution over the registered stack-depth range,
   including a simultaneous rather than preselected-pair error budget;
3. a non-inferiority margin tied to truth-referenced reconstruction or
   resolution loss; and
4. separate observable costs for false admission and false exclusion, so the
   blur-bias/noise-variance trade is explicit.

**ARGUED.** An N-aware multiple-comparison correction could address part of
item 2, but it would not supply items 1, 3, or 4. Shipping one now would merely
replace an exposed gate constant with an exposed alpha plus a hidden,
unmeasured equivalence margin. The corrected-unit candidate already
demonstrates that adaptation by itself is not acceptance: it adapts on every
stack and records M81's own fact 11's 0/5 result against shipped gate 4.

### M81 §12.4 — The `main.rs` blocker

**MEASURED.** `risk-budget-main-clippy.log` reconstructs M81 commit `885247c`,
where the parked spectral calibration still existed. Strict
`cargo clippy --workspace --all-targets -- -D warnings` identifies
`CalibrationScratch::compute` at historical `main.rs:366` as an
eight-argument function against Clippy's seven-argument limit. That historical
snapshot also predates M80's repair and therefore contains M80's separate
then-live `merge_cmd.rs` warning; it is not attributed to M81.

**MEASURED.** M81's NO SHIP commit `bcde55e` removed
`CalibrationScratch`, `calibrate-gate`, and the experimental core module rather
than preserving a product path that failed its registered controls. M80's own
§7 subsequently reports strict Clippy passing. The fresh evidence in
`risk-budget-current-clippy.log` records commit `76b7f76`, the exact
workspace/all-targets command, and exit 0. `crates/strehl-cli/src/main.rs`
therefore needs no further change and remains byte-unchanged in this follow-up.

**MEASURED.** `risk-budget-corpus-lint.log` records all repository corpus
checks reporting `OK — no violations` after this amendment.
