# M78 — blur-equalised and phase-shifted short alignment edges

**MEASURED — status.** Neither arm ships. Arm A makes the registered conservation defect nearly
vanish but worsens its best admissible held-out row from 7.241426 to 7.266073 plane px. Arm B moves
the same conservation statistic less far and worsens its best admissible held-out row from
7.241426 to 7.244330 px. Both remain above the strict 6.758 px gate.

**MEASURED — pre-registration.** The binding pre-registration was committed before any M78
outcome measurement as
`3cc682e334802522d233a4c5e256eab66fb5d959` (`3cc682e`). The commit contains only
`experiments/m78-blur-eq/`; `git show --name-only 3cc682e` lists the fork, README, and
`PREREGISTRATION.md`.

**ARGUED — answer in one sentence.** A lowpass can make short-edge scale conservation look right
without making the edges more predictive: Gaussian cross-blur moves `coffee-bean` from 3.260389
to 1.073795 and a bilinear half-shift moves it to 2.493648, yet neither arm beats even its paired
untreated held-out row.

---

## 1. Question, predecessor, and registered rulings

**MEASURED — inherited problem.** The inherited `coffee-bean` span-1 conservation ratio is
3.260389 in M78's recomputation. The predecessor's fixed held-out baseline is 6.758 px; M78
reproduces it as 6.758243 px on `S4-poly6` trained on `span >= 32`.
`docs/research/M23-metacalibrated-edges-measured.md` §7, under “GATE (c),” identifies that row and
states that it contains no repaired short edge.

**MEASURED — inherited gap.** M23 §10, bullet “R5 (blur-equalised edges) was not attempted,” leaves
R5 explicitly untested. M23's proposed open question 25 asks for the integer-plus-half-pixel
probe that Arm B implements here.

**MEASURED — inherited trap.** `docs/research/M23-metacalibrated-edges-measured.md` §6, fact 172,
reports that the bilinear plant is a lowpass: its zero-defocus self-pair reads response 0.3719,
while the point-sampled field with no interpolator reads 0.9645. M78 therefore treats every added
filter as a possible instrument effect rather than evidence for defocus.

**ARGUED — Arm A hypothesis.** If unequal defocus PSFs cause some of the short-edge scale loss,
cross-convolving each tile by the other frame's estimated PSF should remove the asymmetry by
construction.

**ARGUED — Arm B hypothesis.** If sampling phase causes some of the short-edge scale loss, a known
integer-plus-half-pixel offset followed by exact analytic removal should change the short-edge
observable; a same-direction move from mirrored offsets would identify a phase-sensitive repair
class.

**ARGUED — common ship gate.** A repaired arm must pass its controls, move the fixed conservation
statistic toward 1 by at least 0.15 without crossing below 0.85, and produce an admissible
short-edge-inclusive held-out row strictly below 6.758 px. Equality fails. The older M23
`<= 6.358 px` margin is printed separately and is not substituted for this brief's gate.

---

## 2. Provenance and implementation

### 2.1 Fixed inputs

**MEASURED.** The three fixed input hashes are:

| classification | input | SHA-256 |
|---|---|---|
| **MEASURED** | inherited M10 `coffee-bean` edge table | `E242A64A6367FBE2C1A52D679D85CAA40BD091529E2FCE0D477EDB94FAC801A6` |
| **MEASURED** | inherited M12 `112MSDCF` edge table | `045995EFA2CFF6804D0391274EB51E2919432BBC869F1983C853E9F036D943FF` |
| **MEASURED** | copied M6 `coffee-bean` ring-focus table | `C5533D43654CC84E7CD4FA95ACFE87F72236B81D6C585484811017DC2D6FF8D4` |

**MEASURED.** The focus table contains one case, 96 tile IDs, 105 frames, and exactly one row per
tile/frame pair. `src/main.rs::load_focus_w` implements the same argmax, three-point parabolic
offset, and `[-1,1]` offset clamp as `experiments/m6-residual-halo/m6_lib.py::winner_index`.
The resulting `w_t` range is 1.837 to 104.000 frames; median ring peakiness is 0.9302.

**MEASURED.** The read-only inventory is identical before and after all real-data measurements:

| classification | root | before and after |
|---|---|---|
| **MEASURED** | `C:\dev\macro` | 18,530 files; 286,893,514,060 bytes |
| **MEASURED** | `D:\macro-dark-frames` | 242 files; 8,179,392,512 bytes |
| **MEASURED** | `D:\personal\macro` | 2,263 files; 94,751,309,426 bytes |

**MEASURED.** The checkable records are
`experiments/m78-blur-eq/out/capture-before.txt` and `capture-after.txt`.

### 2.2 What changed relative to M23

**MEASURED.** The Rust and Python estimator sources were byte-identical to M23 when forked; only
the crate rename, initial README, copied inherited edge tables, and pre-registration existed in
commit `3cc682e`.

**MEASURED.** `src/align.rs::gaussian_kernel` builds a unit-normalised circular Gaussian's
separable one-dimensional kernel with radius `ceil(3*sigma)`.
`src/align.rs::gaussian_region` filters only the requested tile or moving search rectangle and
uses clamped boundary extension.

**MEASURED.** `src/align.rs::align_with_blur` retains the inherited unfiltered coarse pyramid and
calls `fit_stage_blurred_at` only for the final 128×128 correlations. The baseline
`src/align.rs::align_with` was not routed through the new filter.

**MEASURED.** `src/field.rs::Field::at_blurred` multiplies each continuous sinusoid by
`exp(-2*pi^2*sigma^2*nu^2)` before point sampling. `Field::render_blurred` therefore plants native
Gaussian mismatch without raster resampling.

**MEASURED.** `src/main.rs::run_blur_eq` applies, for pair `(i,j)` and tile `t`, added sigmas
`q*abs(j-w_t)` to the reference and `q*abs(i-w_t)` to the moving search patch.
`src/main.rs::run_phase` makes one bilinear or exact integer shift and then calls
`remove_known_transform`; that helper composes the measured similarity with the exact inverse
rather than subtracting translations approximately.

**MEASURED.** `src/main.rs::run_field_probe` uses the same continuous field with independent
sensor-noise seeds on both sides. Its phase treatment samples the field directly at the composed
transform, so no geometric interpolator appears in that control.

**MEASURED.** A forced release build printed `Compiling m78-blur-eq`. Three release tests pass:
the local separable Gaussian agrees with direct two-dimensional convolution; zero-sigma
correlation dispatches to and agrees exactly with the inherited correlation; and exact removal of both mirrored
phase plants recovers the original similarity.

---

## 3. Arm A — R5 blur equalisation

### 3.1 Registered method

**DERIVED.** The primary rate is `q = 1/6 = 0.1666667` plane-pixel sigma per frame, derived in
`PREREGISTRATION.md` §2.1 from the fixed focus-step geometry. It is not fit to `coffee-bean`.

**ARGUED.** The non-selectable sensitivity ladder is
`q={1/12,1/6,1/3,2/3}`. Only `q=1/6` can decide the outcome.

**ARGUED.** A Gaussian approximation makes the two total model sigmas equal:
the reference carries its native `sigma_i` plus added `sigma_j`, and the moving tile carries
native `sigma_j` plus added `sigma_i`; both totals are
`sqrt(sigma_i^2+sigma_j^2)`.

### 3.2 Controls

**MEASURED.** All fatal Arm A instrument controls pass:

| classification | control | statistic | registered limit | verdict |
|---|---|---|---|---|
| **MEASURED** | A-C0, 52 real self-pairs | median 0.009812 px; p95 0.021414 px; max 0.023055 px | median <=0.05; p95 <=0.19 | PASS |
| **MEASURED** | A-C1, native sigmas 0.5/1.5 | treated median-Q range 0.006704 | every median in [0.90,1.10]; range <=0.15 | PASS |
| **MEASURED** | A-C1p, native sigmas 1.0/1.0 | treated median-Q range 0.005753 | every median in [0.90,1.10]; range <=0.15 | PASS |

**MEASURED.** The 12-field amplitude ladder is:

| classification | probe `g` | A-C1 raw median Q | A-C1 treated median Q | A-C1p treated median Q |
|---|---:|---:|---:|---:|
| **MEASURED** | `1e-4` | 0.987588 | 0.992008 | 0.993221 |
| **MEASURED** | `2e-4` | 1.000946 | 0.995982 | 0.997904 |
| **MEASURED** | `4e-4` | 1.000447 | 0.998712 | 0.998974 |
| **MEASURED** | `8e-4` | 0.998267 | 0.996837 | 0.996927 |

**MEASURED.** The A-C1 treated-minus-raw median-Q differences range from -0.004963 to +0.004420.
The A-C1p differences range from -0.002201 to +0.000372.

**MEASURED — positive mechanism probe.** The untreated mismatched field reads
`Q(1e-4)=0.987588`, only 0.012412 from unity. The registered A-P firing threshold is 0.10, so the
proposed Gaussian blur-asymmetry mechanism does **not** fire.

**ARGUED.** A-C1 shows that the R5 implementation does not invent a scale-response failure on this
band-limited field; A-P says more importantly that the controlled native blur mismatch does not
reproduce the real short-edge defect. A real-data movement cannot therefore be attributed to the
registered blur-asymmetry mechanism.

### 3.3 Real-data observable

**MEASURED.** `m78_analyze.py::conservation` recomputes the fixed inherited statistic as
`C_0=3.260389`. At the primary rate, Arm A reads `C_A=1.073795`, a movement of -2.186595 and an
improvement in distance from unity of 2.186595. It passes the registered A-S1 threshold and does
not overshoot below 0.85.

**MEASURED.** The complete non-selectable rate ladder is:

| classification | q | fixed `C(0..48)` | denominator multiplier | width-48 median | local telescoping median |
|---|---:|---:|---:|---:|---:|
| **MEASURED** | `1/12` | 1.210415 | 2.693612 | 1.260290 | 0.992372 |
| **MEASURED** | `1/6` primary | 1.073795 | 3.036325 | 1.105110 | 1.006946 |
| **MEASURED** | `1/3` | 0.988850 | 3.297151 | 0.999053 | 1.004822 |
| **MEASURED** | `2/3` | 0.941080 | 3.464517 | 0.968732 | 0.997338 |

**DERIVED.** “Denominator multiplier” is the treated sum of 48 adjacent log-scales divided by its
untreated value, equivalently `C_0/C_A`; at the primary rate the filter makes that aggregate
3.036325 times as large.

**MEASURED.** Over all 48 available width-48 windows, the untreated median is 2.835638 and the
primary Arm A median is 1.105110. The per-triple local telescoping median moves from 1.181637 to
1.006946.

**MEASURED.** The filter raises the median accepted-tile count from 90 to 92 and the median NCC
peak from 0.935340 to 0.995640, while worsening the median fitted displacement-field RMS from
0.535793 to 0.694374 px.

**ARGUED.** The rate ladder is a warning, not an optimum search: progressively stronger lowpass
smoothly steers the conservation ratio through unity. A statistic that can be tuned through its
target by filter strength does not establish that the physical PSFs were equalised correctly.

### 3.4 Held-out gate and decision

**MEASURED.** `m78_heldout.py::admissible` requires at least one replaced span-1/2 edge, positive
cycle rank, and 105/105 solved frames. The fixed test contains 125 inherited direct edges with
span at least 40 and at least 12 accepted tiles; no treated edge is in the test.

**MEASURED.** The best of 72 admissible Arm A rows is `S4-poly2` on `all measurable`:

| classification | E* | paired untreated E* | delta | train edges | treated edges | cycle rank |
|---|---:|---:|---:|---:|---:|---:|
| **MEASURED** | 7.266073 px | 7.241426 px | +0.024647 px | 1,336 | 207 | 1,232 |

**MEASURED.** The row has 105/105 coverage; over the 125-edge test its ordinary median is
7.435801 px, p90 is 13.966347 px, maximum is 24.191797 px, and the robust `E*` tail contains 35
edges.

**MEASURED — Arm A verdict.** `7.266073` is not below `6.758`; it also does not meet the separately
printed historical `6.358` margin. Arm A fails A-S2 and ships nothing.

**ARGUED — what killed it.** The acceptance gate, not a harness control, kills R5. The stronger
mechanistic result is that A-P never expressed the hypothesised defect: Gaussian mismatch was
already recovered at Q approximately 1 before equalisation. The real conservation movement is an
effect of adding a lowpass to real content, but this experiment cannot call it removal of
defocus-induced bias.

**ARGUED — implication.** Do not re-admit the R5 short edges. Do not choose a larger `q` because it
lands nearer 1; the primary physical rate was fixed before measurement, and every ladder value
fails to supply held-out evidence.

---

## 4. Arm B — integer-plus-half-pixel phase probe

### 4.1 Registered method

**MEASURED.** The primary moving-frame plant is `(+4.5,-3.5)` plane px through one bilinear
`warp_known`; the mirror is `(-4.5,+3.5)`. The integer placebo is an exact point-copy by
`(+4,-3)`. `src/main.rs::remove_known_transform` removes each plant in exact similarity algebra
after fitting.

**ARGUED.** The integer terms put the estimator away from the near-zero operating point; the 0.5
fractions interrogate a fixed sampling phase. The mirror was fixed before measurement and was not
chosen by its result.

### 4.2 Controls

**MEASURED.** All registered Arm B instrument controls pass:

| classification | control | statistic | registered limit | verdict |
|---|---|---|---|---|
| **MEASURED** | B-C0, 52 real self-pairs | median 0.017547 px; p95 0.032370 px; max 0.044042 px | median <=0.05; p95 <=0.19 | PASS |
| **MEASURED** | B-C1, exact integer placebo | `C=3.260389`; movement +0.000000 | movement <=0.05 | PASS |
| **MEASURED** | B-C2, `112MSDCF` | 1.048162 to 1.042335; movement -0.005827 | movement <0.10 | PASS |
| **MEASURED** | B-C3, exact-render field | treated median-Q range 0.012158 | every median in [0.90,1.10]; range <=0.15 | PASS |

**MEASURED.** The B-C3 12-field amplitude ladder is:

| classification | probe `g` | raw median Q | exact-phase median Q | treated minus raw |
|---|---:|---:|---:|---:|
| **MEASURED** | `1e-4` | 0.984663 | 1.008315 | +0.023651 |
| **MEASURED** | `2e-4` | 1.001003 | 0.996156 | -0.004847 |
| **MEASURED** | `4e-4` | 1.001433 | 0.999999 | -0.001434 |
| **MEASURED** | `8e-4` | 0.999052 | 1.001365 | +0.002313 |

**MEASURED.** The exact phase deltas change sign over probe amplitude while every treated median
remains within 0.008315 of unity. The response is flat enough to use, but it does not reproduce a
stable under-response analogous to the real conservation defect.

**MEASURED.** Across 104 integer-placebo edges, the median corner difference from the inherited
fit is 0 and the maximum is 0.000002113 px. The control therefore tests an actual point-copy and
analytic composition rather than another interpolator.

### 4.3 Real-data observable and attribution

**MEASURED.** Both primary and mirror offsets move the fixed statistic from 3.260389 to 2.493648,
a -0.766741 movement toward unity. Both exceed the registered 0.15 effect and repair thresholds
without overshooting below 0.85, so B-S1 passes.

**MEASURED.** The two half-shift arms have the same conservation value to six decimals. Across
their 207 corresponding transforms, median and p95 corner difference are zero; the maximum is
0.056648 px.

**DERIVED.** The adjacent-log-scale denominator grows by a factor of 1.307478 under either
half-shift. The integer point-copy grows it by exactly 1.000000.

**MEASURED.** The half-shift raises the median NCC peak from 0.935340 to 0.945860 while leaving the
median fit RMS nearly unchanged, 0.535793 to 0.533319 px.

**ARGUED — mechanism.** A positive or negative half-pixel bilinear shift applies the same
two-tap half-sample lowpass in the image interior. The identical primary/mirror conservation
reading, exact integer null, and near-unity point-sampled field response jointly attribute the
large real-data movement to that lowpass/content interaction, not to the sign of sampling phase.
This is the same class of confound that M23 fact 172 exposed.

**ARGUED — scope of attribution.** The exact-render field does show small Q differences, including
+0.023651 at the smallest probe, so M78 does not claim sampling phase has mathematically zero
effect. It claims that those sign-changing differences do not explain the stable -0.766741
real-data conservation movement.

### 4.4 Held-out gate and decision

**MEASURED.** The best of 72 admissible Arm B rows is `S4-poly2` on `all measurable`:

| classification | E* | paired untreated E* | delta | train edges | treated edges | cycle rank |
|---|---:|---:|---:|---:|---:|---:|
| **MEASURED** | 7.244330 px | 7.241426 px | +0.002904 px | 1,336 | 207 | 1,232 |

**MEASURED.** The row has 105/105 coverage; over the fixed test its ordinary median is 7.473442
px, p90 is 13.953907 px, maximum is 24.225761 px, and the robust tail contains 35 edges.

**MEASURED — Arm B verdict.** `7.244330` is not below `6.758`; it also misses `6.358`. Arm B fails
B-S2 and ships nothing.

**ARGUED — what killed it.** The strict held-out gate kills the repair even though B-S1 and every
control pass. Its nearly unchanged paired score says the lowpass-induced conservation movement
does not carry useful long-baseline predictive information.

**ARGUED — implication.** Do not add a bilinear phase dither to alignment. The exact-render control
leaves open a genuinely different upsampled-correlation-peak estimator, but M78 supplies no
positive evidence that such an estimator would rescue the short edges.

---

## 5. Cross-arm result

**MEASURED.** Arm A and Arm B remain separately attributable: no edge table combines their
measurements, and `m78_heldout.py::main` replaces the inherited short edges with one arm at a time.

**MEASURED.** Their outcomes align despite different operators:

| classification | arm | fixed conservation | movement from 3.260389 | best admissible E* | paired delta |
|---|---|---:|---:|---:|---:|
| **MEASURED** | A, Gaussian cross-blur | 1.073795 | -2.186595 | 7.266073 px | +0.024647 px |
| **MEASURED** | B, bilinear half-shift | 2.493648 | -0.766741 | 7.244330 px | +0.002904 px |

**ARGUED.** Conservation is sensitive to lowpass filtering in exactly the failure direction: a
filter increases the aggregate measured adjacent scale and drives `C` toward 1. Held-out
prediction does not reward that movement. The conservation statistic remains a diagnostic
observable, not an acceptance metric by itself.

**ARGUED.** Fact 47's planning implication survives: deep alignment remains bounded by the edge
measurements, and neither proposed manipulation turns short edges into useful constraints.

---

## 6. What ships

**MEASURED.** No production Rust file under `crates/` changed.

**MEASURED.** Arm A ships no estimator, no `q`, and no repaired edge policy.

**MEASURED.** Arm B ships no dither, no resampler, and no repaired edge policy.

**ARGUED.** The alignment plan should retain the current exclusion of short edges. A future
candidate must improve the fixed held-out test rather than merely repair conservation.

---

## 7. Limits

**ARGUED.** The decisive held-out result uses one deep scene, `coffee-bean`. `112MSDCF` is a
no-defect placebo, not a second scene with a large conservation failure.

**ARGUED.** Arm A tests a Gaussian PSF model and a geometry-derived blur rate. Real defocus is not
exactly Gaussian, and M6's 56 px focus-grid margin differs from M10's 96 px alignment-grid margin;
both limitations were declared before measurement.

**ARGUED.** A-P is a controlled Gaussian mismatch, not a complete model of real through-focus
content changes. Its failure refutes the registered mechanism plant, not every conceivable
content-dependent blur mechanism.

**ARGUED.** Arm B's real half-shift intentionally contains bilinear interpolation because that is
the registered probe. The exact-render field and integer point-copy identify its confounds, but
M78 does not test a Fourier shift or an upsampled NCC peak.

**ARGUED.** The 6.758 px test is held out by edge span within the same stack, not by subject.
Passing it would have been necessary, not sufficient, for production.

**ARGUED.** The `q` ladder is sensitivity analysis only. Reporting its nearer-to-unity rows as a
selected result would violate the pre-registration.

---

## 8. Proposed SYNTHESIS facts

**ARGUED.** The orchestrator owns numbering and folding; the following are proposed facts, not
edits to `SYNTHESIS.md`.

1. **MEASURED — proposed fact F1.** R5's instrument controls pass: real self-pairs read median
   0.009812 px and p95 0.021414 px, while its interpolator-free treated Q medians span only
   0.006704 over an 8× probe ladder. But the untreated native-blur mismatch reads
   `Q(1e-4)=0.987588`, only 0.012412 from unity, so the registered positive blur-asymmetry
   mechanism does not fire. Check
   `experiments/m78-blur-eq/out/analysis.txt`, sections “SELF-PAIR” and
   “A-C1 native sigmas 0.5/1.5,” generated by `m78_analyze.py::show_self` and `show_field`.

2. **MEASURED — proposed fact F2.** Primary R5 moves `coffee-bean` conservation from 3.260389 to
   1.073795 but worsens the best admissible held-out row from 7.241426 to 7.266073 px; it fails
   the strict 6.758 px gate and ships nothing. Check `out/analysis.txt` under “CONSERVATION” and
   `out/heldout.txt` under “ARM A,” generated by `m78_analyze.py::show_conservation` and
   `m78_heldout.py::show_best`.

3. **MEASURED — proposed fact F3.** Mirrored bilinear half-shifts both move conservation to
   2.493648, while the exact integer point-copy leaves it at 3.260389 and the point-sampled phase
   field retains Q in `[0.996156,1.008315]`. The stable real movement belongs to the bilinear
   lowpass/content interaction rather than phase sign. Check `out/analysis.txt`, sections
   “B-C3,” “CONSERVATION,” and “PHASE-ARM TRANSFORM COMPARISONS”; implementation sites are
   `src/main.rs::warp_integer`, `run_phase`, and `run_field_probe`.

4. **MEASURED — proposed fact F4.** The bilinear half-shift's best admissible held-out row is
   7.244330 px against 7.241426 paired untreated and 6.758243 unrestricted baseline; it fails the
   gate and ships nothing. Check `out/heldout.txt` under “ARM B,” generated by
   `m78_heldout.py::admissible` and `show_best`.

5. **DERIVED — proposed fact F5.** Two independently attributable lowpasses repair the
   conservation observable without improving held-out prediction: Gaussian R5 moves it by
   -2.186595 and worsens paired E* by +0.024647 px; the bilinear half-shift moves it by -0.766741
   and worsens paired E* by +0.002904 px. Check the two rows in this report §5 against
   `out/analysis.txt` and `out/heldout.txt`.

**ARGUED — open question 26.** Answer “no on the registered candidate”: R5 is now tested and fails
the held-out ship gate.

**ARGUED — open question 25.** Answer the registered bilinear probe “not as a repair”: it changes
the observable through a lowpass and does not improve held-out error. Keep only the narrower
question of an interpolator-free upsampled peak open.

---

## 9. Reproduction and falsifiers

**MEASURED.** The complete invocation is:

```powershell
Set-Location C:\dev\blog\death-of-software\projects\strehl\experiments\m78-blur-eq
.\run-m78.ps1
```

**MEASURED.** `run-m78.ps1` validates all three fixed input hashes, inventories all three read-only
roots, forces release tests and a release executable build, runs every registered control and real
arm, runs both analysis scripts with UTF-8 Python output, and verifies the final inventory.

**MEASURED.** Principal machine-readable artifacts are:

| classification | artifact | content |
|---|---|---|
| **MEASURED** | `data/a-mismatch-field.csv`, `a-equal-field.csv`, `b-phase-field.csv` | all 8× Q ladders, raw and treated |
| **MEASURED** | `data/a-self-edges.csv`, `b-self-edges.csv` | fatal real-content self-pairs |
| **MEASURED** | `data/a-primary-edges.csv`, `a-q*-edges.csv` | Arm A primary and sensitivity edges |
| **MEASURED** | `data/b-primary-edges.csv`, `b-mirror-edges.csv`, `b-integer-edges.csv`, `b-112-edges.csv` | Arm B treatment and placebos |
| **MEASURED** | `data/heldout-candidates.csv` | all 408 baseline/Arm A/Arm B solver rows |
| **MEASURED** | `out/analysis.txt`, `out/heldout.txt` | concise registered decisions |

**ARGUED — falsifier F1.** Proposed fact F1 dies if recomputing the field CSVs puts any treated
median Q outside `[0.90,1.10]`, makes its across-amplitude range exceed 0.15, or moves untreated
A-C1 `Q(1e-4)` at least 0.10 from unity.

**ARGUED — falsifier F2.** Proposed fact F2 dies if
`m78_heldout.py::replacement_rows` does not replace all 207 inherited short edges, if any replaced
edge enters the 125-edge test, or if an admissible Arm A row scores below 6.758 px.

**ARGUED — falsifier F3.** Proposed fact F3 dies if the exact integer placebo moves conservation
by more than 0.05, if the `112MSDCF` placebo moves by at least 0.10, or if the exact-render field
fails its Q accuracy/flatness bands.

**ARGUED — falsifier F4.** Proposed fact F4 dies if an admissible Arm B row scores below 6.758 px
on the same fixed test.

**ARGUED — whole-report falsifier.** The comparison dies if the inherited edge hashes or focus
hash differ, if the unrestricted baseline no longer reproduces 6.758 within 0.01 px, or if the
capture inventories differ before and after.
