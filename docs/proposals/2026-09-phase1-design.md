# Phase 1 — unified banded-admission merge

Status: PROPOSAL — repository-verified implementation design; W1 is a mandatory go/no-go gate, A2 is closed negative, and the B3 evidence conflict must be resolved before Rust implementation.

Verified 2026-09-02 PDT first against repository HEAD `40b20bef0fe0cdaba7298573095806e580a7ed85`; symbol anchors were refreshed after concurrent HEAD advanced to `986c46535fc082395831724f1d45c33a1d974390`. `crates/strehl-cli/src/merge_cmd.rs` remained under active edit, so volatile CLI locations below are anchored on symbols as well as line numbers.

## 1. Decision and scope

Phase 1 is one default-path pyramid merge composed of A1, A4, B3, B4, and B6, after D9(a) and an aligned-pyramid byte freeze. It retains the seven-band Burt–Adelson Laplacian pyramid, `BaseBand::Mean`, the normalized-input hull, and a single fixed admission constant selected by W1. It replaces the width-confounded soft-power selector with a two-pass, noise-priced band-admission rule; emits a vector confidence product; applies photometric normalization consistently to pixels and their noise model; and uses no replacement selection-inflation constant.

A2 is **not** executable phase-1 scope. `docs/research/M-PHASE0-VEIL2.md` is a final negative report, not a pending one: verdict `NOT ROBUST`, no Rust arm, and the base remains `BaseBand::Mean`. The historical A2 design is retained only in Appendix A. It may not activate without a new, explicit report that supersedes M-PHASE0-VEIL2.

Two constraints are absolute:

1. `docs/STATUS.md` records D8/SPLIT as killed. No split half, FRC, or other subdivision of one stack may choose or adapt `k`, per capture or per tile. Reopening D8 requires the independent repeated-bracket capture its verdict names.
2. No claim above **0.25 cycles/output-pixel** is licensed until the capture requested by `docs/captures-needed.md` §33 exists and passes its own commissioning. Phase-1 measurements must truncate every spatial-frequency statistic at 0.25 cyc/px.

## 2. Verification ledger

### 2.1 Requested citations

| Citation | Result | Repository reading |
|---|---|---|
| `docs/proposals/2026-08-sota-path.md:2074-2083` | **Resolved** | Defines phase 1 as A1/A2/A4/B3/B4/B6, names the aligned-pyramid freeze, requires D9(a) first, and exits with per-band `n_eff` artifacts. Later evidence removes A2. |
| `docs/proposals/2026-08-sota-path.md:459-576` | **Resolved, but provisional** | Contains A1, A2, and the opening of A4. A1's acceptance text still contains literal `[bar]` placeholders, so it is not an executable acceptance specification by itself. |
| `docs/proposals/2026-08-sota-path.md:751-769` | **Resolved, contradicted elsewhere** | Contains B3 and B4. B3 asserts the inverse-square magnification law; current source and M99 dispute that law. B4 is consistent with current `SELECTION_INFLATION = 1.0`. |
| `docs/proposals/2026-08-sota-path.md:815-837` | **Resolved, but provisional** | Contains B6 generalized-Anscombe gating. It also contains a `[level bar]` placeholder and marks a supporting literature citation as remembered rather than verified. |
| `docs/research/M-PHASE0-VEIL2.md:1-7,139-154` | **Resolved; supplied status was wrong** | The report is final, `NOT ROBUST`; it forbids an A2 Rust arm and keeps `BaseBand::Mean`. Calling it “pending” is incorrect. |
| `crates/strehl-core/src/pyramid.rs:1289-1687` | **Partially resolves** | The range contains `BandMerge` and `add_frame_with_gain`, but no longer contains `absorb` or `finish`. Current anchors are approximately `BandMerge` 1310, `add_frame_with_gain` 1614, `absorb` 1914, and `finish` 2185. The composite citation is therefore stale. |
| `crates/strehl-cli/src/merge_cmd.rs:4586-5945` | **Resolved by symbol re-anchor** | Contains the current pyramid fold and `run_pyramid`, now approximately line 5433. Concurrent PIPE edits have shifted this region; use `fn run_pyramid`, `decode_queue::rendezvous`, and `BandWorker::fold` rather than fixed line numbers. |
| `docs/STATUS.md:89-112` | **Resolved** | Decode, not cold storage, is limiting: storage was measured about 4.5× faster than the decoder can consume it. |
| `docs/STATUS.md:156-201` | **Resolved** | D8/SPLIT is killed because subdivisions of one stack are not independent; it may not be used for split-stack tuning. |
| PIPE seam, `merge_cmd.rs:75,4640-4887`; `decode_queue.rs:1-28` | **Resolved by symbol re-anchor; prerequisite currently fails** | `mod decode_queue` is near line 75, `decode_queue::rendezvous` near 4867, and the untracked `decode_queue.rs` defines a zero-capacity rendezvous. At verification time `merge_cmd.rs` was modified and `decode_queue.rs` untracked, so the required cleanliness command did not pass. |

No requested file or named section was absent. The `pyramid.rs` range is the one citation that does not fully resolve the symbols attributed to it; the CLI range resolves only after re-anchoring because its owner is active.

The required PIPE test was deliberately not run during this documentation-only task. W2 must run it after PIPE lands.

### 2.2 Named symbols and current behavior

| Name | Verified state |
|---|---|
| `BandMerge::add_frame_with_gain` | Exists; constructs the luma and variance pyramids, computes smoothed squared Laplacian energy, prices a frame-specific band floor, and accumulates weighted coefficients. |
| `BandMerge::absorb` | Exists outside the cited range; combines partial accumulators. Float reduction order is currently worker-count dependent. |
| `BandMerge::finish` | Exists outside the cited range; reconstructs and applies the configured hull. |
| `run_pyramid` | Exists in `merge_cmd.rs`; owns decode/warp/fold orchestration. |
| `BaseBand::Mean` | Exists and is the default. |
| `DEFAULT_BANDS` | Exists and is `7`. |
| Burt–Adelson kernel | Verified as `[1,4,6,4,1]/16`, separable, non-negative, and unit-DC. |
| `NU_SMOOTH` | Exists as the derived independence approximation `13.37469`; source explicitly says real correlated-band `nu` is lower. |
| `ThroughFocus::subframe_deficit` | Exists and implements the required baseline-subtracted log-parabola deficit. |
| `SELECTION_INFLATION` | Exists as `1.0`; both branches return `1.0`. |
| `Hull::InputRange` | Exists and is the current default. |
| `BandReference` | Does not exist; W3 creates it. |
| `ConfidenceBundle` | Does not exist; W3 creates it. An existing `through_focus::ConfidenceVector` is estimator-oriented and must not be silently duplicated or confused with the pyramid bundle. |
| `confidence.rs` | Does not exist in `strehl-core`; it is a planned W3 file. |

The active CLI working tree also contains an optional `--confidence-map` implementation measuring output centrality in calibrated noise units. It is not the phase-1 confidence vector and currently requires another frame pass after `finish`. W2 must integrate without overwriting or relabelling that work; the phase-1 bundle must be produced from merge sufficient statistics without adding a third decode pass.

### 2.3 Repository-wins discrepancies and blockers

These are not editorial caveats. They are entry conditions or design changes that implementation must respect.

1. **A2 is final-negative, not pending.** It is excluded.
2. **B3 has conflicting repository evidence.** The proposal, README, and `docs/research/BUILD-GHOST.md` support `ln(flux) = -2 ln(scale)` and report up to 5.06× RMS reduction with permutation `p = 0.0025`. Current `crates/strehl-core/src/photometric.rs` and `docs/research/M99-photometric.md` say an aligner-derived inverse-square law was refuted, with fitted exponents from about -0.879 to -6.466. These may be different masks or estimands, but that reconciliation is absent. W4 must reproduce both readings under one scale convention and one pixel mask before landing the law. If it cannot, phase 1 stops.
3. **Scaled noise support is already present.** `photometric::scale_plane_noise` and `scale_noise_model` already implement the correct transform for an applied pixel gain. W4 must reuse and test them, not add a second scaling path.
4. **The uncertainty equation is new design material.** `sigma_E^2 = (2F^2 + 4Fq)/nu_eff` is mathematically consistent with a noncentral Gaussian squared-energy approximation, but no repository report commissions it on real bands.
5. **The original wording mixes domains.** “Generalized-Anscombe decision space” and the supplied linear-energy `F`, `q`, and variance equations do not say whether samples, coefficients, or energies are transformed. Section 4 freezes the intended interpretation: normalize linear samples, apply the generalized Anscombe transform to shared-green samples, then build the decision pyramid; reconstruct from a separate linear-DN pyramid. W1 must commission that exact reading before W3.
6. **Winner semantics were omitted.** Section 4 makes the winner the maximum finite decision-space energy `E`, ties by lower stable frame ordinal, and treats `q_w = 0` as the below-floor case. Changing the winner to `q`, SNR, or a stabilized score is a new preregistered arm, not an implementation detail.
7. **“Below-floor winner means mean” conflicts with unconditional `w = 1/F`.** Section 4 resolves this by using unit weights for every frame in a below-floor band coefficient. Otherwise it would be inverse-variance averaging, not a plain mean.
8. **A global gate has hostile prior evidence.** Existing measurements report about 3.25× sibling dispersion and about 49.5× dispersion across five stacks after scalar correction. W1 is therefore a genuine kill gate, not a calibration ceremony.
9. **The aligned-pyramid freeze is absent.** `byte-freezes.tsv` has one pyramid row, but it has `env_align=0`; no aligned-pyramid row exists.
10. **D9(a)'s performance claim is not supported by the current memory geometry.** The freeze row reports a current worker footprint of about 1328 MiB. From `BandMerge::accumulator_floats`, the 3516×2344, four-plane, seven-band accumulator alone is about 629 MiB: 32 full partials are therefore about 19.6 GiB before workspaces, while eight current concurrent workers are about 10.4 GiB. Four workers already approach the 6 GiB product budget. A fixed reduction lattice can make bytes worker-invariant, but it cannot by itself refund the measured 1.29× four-versus-eight-worker cost under that same budget. The refund needs smaller/tiled partials, spatial cooperation, or spill. W2 must separate the determinism acceptance from the unproven speed claim.
11. **The prescribed W2 ordering conflicts with D9's own prose.** D9 says the aligned row should exist before its freeze event, while W2 says D9 is the first serial commit and the row comes next. Reconciliation: before changing code, W2 must measure and archive the pre-D9 aligned invocation; commit D9 first; then add the post-D9 invariant row, recording both hashes and the intentional transition in the row rationale. If a literal pre-existing registry row is required, the commit order must change.
12. **Residual photometric fitting threatens the two-pass and 2.00× contracts.** A residual estimated from decoded pixels is not available when pass-one decisions are made. A separate calibration decode makes three passes; applying the residual only in pass two makes pass-one winners inconsistent. W4 must demonstrate a no-extra-decode source of the residual, or phase 1 must either drop residual fitting or revise the runtime bar before implementation.
13. **Current D9(a) is not implemented.** The pyramid path still partitions by the selected worker count, so the reduction tree changes with `STREHL_PYRAMID_WORKERS`.
14. **Concurrent ownership is live.** At verification time `merge_cmd.rs` and `byte-freeze.rs` were modified and `merge_cmd/decode_queue.rs` was untracked. W2 must not begin in those files until their owners land and the preconditions in §7.2 pass.
15. **Foam cannot be both W4 calibration and untouched W5 acceptance.** W4's required `<= 0.05`-stop result consumes `foam`, while W5 names it as untouched. W5 may report foam as a regression/stress check after W4, but it is not independent. A genuinely untouched replacement capture must be named before W5 if independent photometric acceptance is required.
16. **“Untouched” is only a phase-1 hold-out claim.** Several W5 captures, especially `coffee-bean` and `foam`, already appear in repository research and freeze work. W5 can keep them out of W1's `k` selection; it cannot represent them as historically unseen.

## 3. Capture manifest

Counts are read-only recursive counts of RAW `.ARW` frames. Nothing under `D:\personal\macro` may be written, renamed, sidecar-updated, or used as a cache destination.

The shorthand `sw4` and `sw10` is ambiguous: both calibration-grid setup 1 and setup 2 contain those sweep widths. Setup 1 is the phase-1 definition because it is the only setup containing the required sw1/sw4/sw10 trio. The setup-2 alternatives remain recorded so the ambiguity cannot be silently rediscovered later.

| Role | Name | Full path | Frames | Diagnostic value |
|---|---|---|---:|---|
| W1 calibration | sw4 | `D:\personal\macro\requests\30-calibration-grid\calibration-grid-1-sw4-cpl` | 55 | Controlled medium-step bracket with grid edges and repeated spatial structure; it anchors the middle of the sampling ladder. |
| W1 calibration | coffee-bubbles | `D:\personal\macro\coffee-bubbles` | 19 | The capture on which flat/detail selection-concentration inversion was measured; it is not a clean fixed-focus null. |
| W1 calibration | 113MSDCF | `D:\personal\macro\113MSDCF` | 63 | Natural fine-detail/MTF bracket and the shorter member of the 112/113 replicate pair. |
| W5 held-out | sw1 | `D:\personal\macro\requests\30-calibration-grid\calibration-grid-1-sw1-cpl` | 91 | Dense focus sampling; tests whether a globally fixed `k` over-admits nearly redundant frames. |
| W5 held-out | sw10 | `D:\personal\macro\requests\30-calibration-grid\calibration-grid-1-sw10-cpl` | 23 | Coarse focus sampling; tests whether the same `k` collapses toward selection when adjacent frames differ strongly. |
| W5 held-out | 112MSDCF | `D:\personal\macro\112MSDCF` | 79 | Same-subject replicate of 113MSDCF with 16 additional frames; separates rule stability from one bracket's depth. |
| W5 held-out | coffee-bean | `D:\personal\macro\coffee-bean` | 105 | Deep rigid stack and the repository's named hull-clamp stress capture; polariser provenance remains unresolved. |
| W4 calibration / W5 regression | foam | `D:\personal\macro\foam` | 100 | Unique measured 0.32-stop local photometric outlier over eight frames and a non-rigid scene; W4 consumes it, so it cannot also be independent W5 hold-out evidence. |
| Excluded ambiguity | alternate sw4 | `D:\personal\macro\requests\30-calibration-grid\calibration-grid-2-sw4-cpl` | 46 | A second setup with the same shorthand; excluded from phase 1 to prevent accidental capture substitution. |
| Excluded ambiguity | alternate sw10 | `D:\personal\macro\requests\30-calibration-grid\calibration-grid-2-sw10-cpl` | 27 | A second setup with the same shorthand; excluded from phase 1 to prevent accidental capture substitution. |

All eight named captures exist. No named capture is missing.

## 4. Merge contract

### 4.1 Fixed topology and notation

- Keep `DEFAULT_BANDS = 7`, the existing Burt–Adelson reduce/expand operators, borders, and linear-DN reconstruction.
- Keep `BaseBand::Mean`; the base residual is always the arithmetic mean of normalized linear-DN base coefficients.
- Keep `mean_coarse = 0` unless a separate measured ladder changes it; phase 1 does not change it.
- A band coefficient is indexed by frame `i`, band `b`, and native band-grid position `p`.
- `N` is frame count. Stable frame ordinal is input order after the CLI has produced its deterministic path list.
- `S_i(p)` is black-subtracted, photometrically normalized shared-green luma: `(G1 + G2)/2` on the aligned quad grid.
- The decision variance is temporal Poisson–Gaussian variance. PRNU is deliberately excluded because the repository noise model documents that fixed pattern cancels in a between-frame decision; it remains relevant to output uncertainty, not admission.

### 4.2 B3 photometric normalization

The proposed deterministic arm is

```text
c_i = (scale_i / scale_ref)^2
X'_i = c_i X_i
```

where `scale_i` and `scale_ref` must use one documented alignment-transform convention. Applying `c_i` to samples requires the noise transform already implemented in `photometric.rs`:

```text
a'_i = c_i a_i
b'_i = c_i^2 b_i
Var[X'_i | X'_i = s'] = a'_i s' + b'_i
```

For `PlaneNoise`, this means scaling `gain_dn_per_e` and white-about-black by `c_i` while keeping `read_noise_e` unchanged; `scale_noise_model` is the canonical implementation. The input hull is accumulated after this normalization.

Residual fitting is permitted only if W4 resolves blocker 2 and blocker 12. The preregistered residual is

```text
r_i = log2(g_measured_i / c_i)          [stops]
```

on one fixed eroded low-detail mask. If every contiguous eight-frame window has peak-to-peak residual `<= 0.10` stop, set residual gain to 1. If any window exceeds `0.10` stop, fit a smooth residual curve and compose it with `c_i`; after fitting, foam's maximum eight-frame peak-to-peak residual must be `<= 0.05` stop. This path may not make pass-one and pass-two normalization differ. If it needs an extra RAW decode, the two-pass/runtime contract has failed and must be explicitly renegotiated rather than hidden.

### 4.3 B6 decision transform

For each normalized frame, form effective shared-green temporal-noise coefficients

```text
a_G = (a_G1 + a_G2) / 4
b_G = (b_G1 + b_G2) / 4
s   = max(S, 0)
A(s; a_G, b_G) = (2 / a_G) * sqrt(max(a_G*s + 3*a_G^2/8 + b_G, 0))
v_A(s) = (a_G*s + b_G) / (a_G*s + 3*a_G^2/8 + b_G)
```

`A` is used only for focus decisions. Linear normalized planes are decomposed separately for accumulation and reconstruction. Under a photometric gain `c`, `s'=cs`, `a'=ca`, and `b'=c^2b`, so `A(s';a',b') = A(s;a,b)` algebraically. W4's gain-invariance test allows maximum absolute floating error `2e-5` over the preregistered signal/gain grid.

The denominator and `v_A` must be finite and positive. Non-finite decision samples never win and are never admitted. Below-black samples use `s=0`, matching `PlaneNoise::variance`.

### 4.4 Pass one: `BandReference`

For every frame, build the generalized-Anscombe shared-green Laplacian pyramid. At every `(b,p)`:

```text
L_i       = LaplacianBand_b(A_i)[p]
E_i       = smooth5(L_i^2)[p]
F_i       = beta_i,b * v_A,i,b[p]
q_i       = max(E_i - F_i, 0)
sigma2_Ei = (2*F_i^2 + 4*F_i*q_i) / nu_eff_b
```

`beta_i,b` is the frame- and warp-specific band-noise gain already represented by `BandGain`/`frame_beta`; no global scalar may replace it. `v_A,i,b` is the variance field propagated down the same Gaussian pyramid. `nu_eff_b` is a W1-commissioned, conservative per-band value validated across the preregistered warp-phase range. Warp interpolation changes correlation as well as energy, so one value is acceptable only if its null coverage holds across those phases. `NU_SMOOTH = 13.37469` is only the analytic independent-sample starting value; it must not be relabelled as a measured correlated-band value.

`BandReference` stores, at native band resolution:

```text
winner_energy: f32      // E_w
winner_floor: f32       // F_w
winner_variance: f32    // sigma2_Ew
winner_frame: u16/u32   // type selected from maximum supported N
below_floor: bit        // q_w == 0
```

The winner is the largest finite `E_i`. Equal bit-pattern energies choose the lower stable frame ordinal. If no finite energy exists, mark the coefficient invalid and fail the merge with coordinates; do not silently emit a mean.

A below-floor winner is one with `q_w = 0`. It routes **all frames with unit weights** to an arithmetic mean for that band coefficient.

### 4.5 Pass two: admission and linear reconstruction

Re-decode and identically normalize/align each frame. Recompute its decision-space `E_i`, `F_i`, `q_i`, and `sigma2_Ei` using the same functions and frozen tables as pass one. For a non-below-floor winner, admit frame `i` iff

```text
E_w - E_i <= k * sqrt(sigma2_Ew + sigma2_Ei)
```

The winner is always admitted. Exactly one fixed global `k`, selected by W1, is compiled as the product default and recorded in provenance. A per-capture value is not an allowed product mode or an acceptance workaround.

Use one shared-green weight for all four CFA planes:

```text
w_i = 1 / F_i                   if admitted and winner is above floor
w_i = 1                         if winner is below floor
w_i = 0                         otherwise
```

Every used `F_i` must be finite and strictly positive; otherwise fail with the frame, band, and coordinates. Do not hide a model failure behind an epsilon. Accumulate at each band coefficient and plane:

```text
sum_wL[c] += w_i * L_linear_i[c]
sum_w     += w_i
sum_w2    += w_i^2
L_out[c]   = sum_wL[c] / sum_w
n_eff      = sum_w^2 / sum_w2
```

`sum_w == 0` is an error because the winner must be admitted. Keep accumulation precision and reduction order fixed by W3/D9; do not introduce atomics whose order is scheduler-dependent.

Accumulate each normalized native CFA plane's `lo`/`hi` before decomposition. Reconstruct each CFA plane from the seven admitted linear bands plus the arithmetic-mean base, then apply the existing normalized-input hull clamp:

```text
d_hull = max(lo - reconstructed, 0, reconstructed - hi)  // pre-clamp, linear DN
output = clamp(reconstructed, lo, hi)
```

### 4.6 B4 output uncertainty

No replacement selection inflation is allowed. Keep the multiplier exactly `1.0`. Where predicted temporal output variance is required, derive it from the actual weights:

```text
Var_out = sum_i(w_i^2 * Var_i) / (sum_i w_i)^2
```

Any fixed multiplier other than 1.0 requires a new independent measurement and proposal.

### 4.7 A4 `ConfidenceBundle`

Add `crates/strehl-core/src/confidence.rs` and export it from `lib.rs`. Reuse `ThroughFocus::subframe_deficit`; do not fork its log-parabola math. The bundle is a vector, never a scalar score:

1. **Per-band Kish participation:** `n_eff_b(p) = sum_w^2/sum_w2` at each band's native resolution.
2. **Sub-frame deficit:** baseline-subtracted log-parabola `1 - f(k*)/f(peak)` at quad resolution, with invalid/boundary state preserved rather than encoded as zero.
3. **Admission width:** per-band winner-referenced `k*sqrt(2*sigma2_Ew)` at native resolution, plus a documented Burt–Adelson expansion to quad resolution for display. The native map is authoritative.
4. **Hull distance:** pre-clamp `d_hull` in linear DN per CFA plane at quad resolution.
5. **Validity/provenance masks:** below-floor, invalid parabola, bracket boundary, and censored state when B2 eventually exists. Phase 1 does not invent B2.

W2 adds `--confidence-bundle <directory>`. The directory contains lossless 32-bit float TIFFs and a JSON manifest naming dimensions, band, units, invalid encoding, input hashes, alignment sidecar hash, noise-model provenance, photometric law and gains, `k`, `nu_eff`, `beta` provenance, frame count/order, reduction-lattice ID, git SHA, and hull policy. Confidence generation must not alter image bytes. It must not require the active centrality map's optional third pass.

## 5. Determinism, orchestration, and freezes

### 5.1 D9(a)

Partition the stable frame list into a fixed chunk lattice independent of worker count. Each chunk processes frames in stable ordinal order. Absorb partials in ascending chunk ID through a fixed tree/order. Record chunk count and lattice version in the run banner and confidence manifest. Worker count may change scheduling only, never grouping or absorb order.

The chunk count must be memory-safe. The proposal's illustrative 32 full-image partials do not fit the present 6 GiB budget. W2 may use fewer chunks for the first determinism landing, but must not claim the 1.29× refund unless a measured smaller/tiled representation or spatial-cooperation design actually permits more concurrent work under the budget.

Acceptance: one release-build aligned-pyramid freeze invocation, forced with `STREHL_PYRAMID_WORKERS=1`, `2`, `4`, and `8`, produces identical SHA-256 and byte count. Peak memory is reported for every arm; an 8-worker hash obtained only by exceeding the product memory budget proves determinism, not a shippable speedup.

### 5.2 PIPE hand-off

`lane-PIPE` exclusively owns `crates/strehl-cli/src/merge_cmd/decode_queue.rs`. W2 consumes `decode_queue::rendezvous` and never edits that file. W2 is blocked from `merge_cmd.rs` until PIPE lands and all commands below hold:

```powershell
git status --short -- crates/strehl-cli/src/merge_cmd.rs crates/strehl-cli/src/merge_cmd/decode_queue.rs
rg "mod decode_queue|decode_queue::rendezvous" crates/strehl-cli/src/merge_cmd.rs
cargo test -p strehl-cli --bin strehl decode_fold_queue
```

The first command must print nothing; the second must find both seam references; the third must exit 0. At this document's verification point the first failed (`merge_cmd.rs` modified, `decode_queue.rs` untracked), the second passed by inspection, and the third was not run. `byte-freeze.rs` was also modified by another lane and must be clean or explicitly handed off before W2 edits it.

Every phase-1 pass uses the same bounded decode-to-fold rendezvous. A producer error closes the queue and reaches the consumer; consumer failure cancels production; no decoded-frame backlog may grow with `N`.

### 5.3 Freeze order

1. Before code changes, render and record the current aligned-pyramid invocation at workers 1/2/4/8 as a pre-D9 measurement.
2. Land D9(a) as W2's first serial commit.
3. Add the aligned-pyramid registry row with its post-D9 worker-invariant hash; record the pre-D9 hashes and the intentional transition in `why`.
4. Land two-pass orchestration and phase-1 default selection.
5. Add phase-1 and legacy control freeze rows, confidence-bundle provenance checks, and teeth plants proving each row can fail.

## 6. Acceptance definitions

All confidence intervals are two-sided 95% block-bootstrap intervals over preregistered, non-overlapping spatial tiles, except an “upper95” or “lower95” bar, which refers to the corresponding one-sided endpoint. Bootstrap seed, tile size, crop coordinates, exclusions, and replicate count are written before scoring. Every frequency-domain metric is restricted to `<= 0.25 cyc/px`.

- **Width match:** for every W1 capture, scored band, and preregistered ROI, `abs(mean_n_eff_candidate / mean_n_eff_legacy_gate4.5 - 1) <= 0.05`. Legacy `n_eff` uses its actual soft weights; zero-weight mean fallback uses unit weights.
- **Detail/MTF retention:** ratio `candidate / legacy-gate-4.5`; the lower 95% bound must be `>= 0.95` on every calibration capture's preregistered detail instrument.
- **Flat power:** ratio of integrated output power in preregistered flat/defocused ROIs over `0.10–0.25 cyc/px`, `candidate / legacy-gate-4.5`; the upper 95% bound must be `<= 0.90` on every applicable calibration capture.
- **Sampled `n_eff` correctness:** maximum absolute error between Rust bundle and independent LibRaw recomputation is `<= 0.02` over a deterministic preregistered sample.
- **Selector census:** fraction of valid coefficients with exactly one admitted frame is `< 0.1%` for every scored band and held-out capture. Count admissions directly; do not infer the census from rounded `n_eff`.
- **Hull:** maximum excess beyond independently recomputed normalized input bounds is `<= 1 DN`, including output quantization.
- **Runtime:** release candidate wall time divided by release legacy gate-4.5 wall time is `<= 2.00` on every held-out capture, same machine and worker setting, alternating order, with the repository timing rule applied. Optional centrality-map time is reported separately; required confidence-bundle time is included.
- **Determinism:** release output hashes are identical at workers 1/2/4/8.
- **W4 VST invariance:** maximum absolute transformed-value difference under consistent sample/noise scaling is `<= 2e-5`.
- **W4 foam residual:** maximum contiguous-eight-frame peak-to-peak residual after permitted fitting is `<= 0.05` stop, and fitting is never engaged when the prefit residual is `<= 0.10` stop.

## 7. Workstreams

| ID | Workstream | Dependencies | Owned files | Completion gate |
|---|---|---|---|---|
| W1 | Preregister and pilot | None | `docs/proposals/2026-09-phase1-design.md`; `experiments/PHASE1-DESIGN/PREREGISTRATION.md`; `reference.py`; `measure.py` | Both exact gate commands exit 0; one fixed global `k`; width match `<=5%`; detail/MTF lower95 `>=0.95`; flat-power upper95 `<=0.90`. “No common k exists” is a successful negative and stops phase 1. |
| W2 | D9 and product integration | W1 GO; PIPE landed; final W3/W4 API at integration | `crates/strehl-cli/src/main.rs`; `merge_cmd.rs`; `tests/byte-freeze.rs`; `tests/byte-freezes.tsv`. Explicitly not `merge_cmd/decode_queue.rs`. | D9 first serial commit; aligned freeze; two-pass queue orchestration; default selector; confidence bundle; provenance; release hashes identical at workers 1/2/4/8. |
| W3 | Core admission and confidence | W1 GO | `crates/strehl-core/src/pyramid.rs`; `through_focus.rs`; new `confidence.rs`; `lib.rs` | Typed pass APIs, commissioned uncertainty/admission, linear reconstruction/hull, vector confidence, and `cargo test -p strehl-core` green. |
| W4 | Photometric law | W1 GO; B3 conflict adjudicated | `crates/strehl-core/src/photometric.rs` | One documented scale convention reconciles BUILD-GHOST and M99; existing noise-scaling path reused; VST error `<=2e-5`; foam residual `<=0.05` stop without violating two-pass/runtime contract. |
| W5 | Independent acceptance | W2 + W3 + W4; independent photometric capture named or foam downgraded to regression | `experiments/PHASE1-VERIFY/PREREGISTRATION.md`; `verify.py` | Phase-1 held-outs; independent LibRaw decode; Pareto bars; `n_eff` error `<=0.02`; selectors `<0.1%`; hull `<=1 DN`; runtime `<=2.00×`; workspace tests and clippy green. |

### 7.1 W1 selection rule

Before looking at candidate outcomes, W1 records crop coordinates, exclusions, bootstrap plan, `nu_eff` commissioning, and the ordered grid

```text
k = 0.00, 0.05, 0.10, ..., 8.00
```

Run every grid value unchanged on all three calibration captures. First discard every value that fails the per-capture/per-band/per-ROI 5% width match. Among survivors, require both Pareto bars on all applicable captures. Select the smallest surviving `k`; the tie-break is fixed in advance and cannot depend on image appearance. If no value survives, report `NO_COMMON_K` and stop. No interpolation, per-capture value, post-hoc crop, or expanded range is allowed without a new preregistration and a fresh untouched calibration set.

### 7.2 W2 integration details

- Preserve an explicit legacy gate-4.5 arm for controls and freeze rows.
- Make banded admission the default only after W1 returns GO and all freeze teeth pass.
- Both passes must call the same frame preparation function for decode, black subtraction, photometric gain, defect handling, warp, crop, luma, variance, and frame-specific `beta`.
- The queue remains bounded and cancellation-safe in both passes.
- Confidence output is opt-in but production-supported; it contains all A4 channels and complete provenance.
- The active centrality `--confidence-map` remains a separately named optional diagnostic.

### 7.3 W5 held-out protocol

W1–W4 may list but must not decode, inspect, crop, or score sw1, sw10, 112MSDCF, or coffee-bean before W5 preregistration is sealed. This means held out from phase-1 parameter selection, not historically unseen by the repository. W4 necessarily scores foam; W5 may include it as a declared regression/stress case, but not as independent evidence. If independent photometric evidence is required, seal a replacement path before W4 opens it.

W5 uses rawpy/LibRaw to decode mosaics independently of the Rust RAW path, consumes the same read-only alignment transforms or independently recreated transforms, and recomputes decisions, weights, `n_eff`, and hull bounds without calling `strehl-core`.

Pareto bars are the W1 bars, evaluated per held-out capture where the instrument applies. The 0.25 cyc/px ceiling remains in force. W5 reports every miss as a result; it does not retune `k`.

## 8. Rejected alternatives and controls

- **Extend soft-power weighting:** rejected because changing its exponent or threshold preserves the width-confounded selector. The repository already shows equal threshold is not equal effective width; any comparison must match Kish `n_eff`.
- **Move to estimator/per-pixel geometry:** rejected because the measured flat-ground winner field becomes patchwork/plateaus. Phase 1 changes admission policy while retaining band geometry.
- **Per-capture `k`:** rejected as a failed global model, not a product feature.
- **Split-stack self-tuning:** prohibited by D8.
- **Replacement selection inflation:** prohibited by B4's negative evidence.

Cheat/control matrix:

| Cheat | Why a headline can look good | Control that must fail it |
|---|---|---|
| Average nearly everything | Suppresses flat noise | Width match and detail/MTF lower95 `>=0.95`. |
| Sharpen output | Raises detail/MTF | Flat-power upper95 `<=0.90`, normalized-input hull `<=1 DN`, and signal-correlated detail instrument. |
| Fabricate/smooth confidence | Makes maps look plausible | Independent LibRaw recomputation, max `n_eff` error `<=0.02`, manifest hashes. |
| Force serial execution | Makes hashes deterministic | Worker 1/2/4/8 hashes plus runtime and peak-memory reports. |
| Tune one `k` per capture | Makes every calibration pass | Manifest equality and the explicit `NO_COMMON_K` rule. |
| Claim fine detail from noise | Raises high-band power | Hard cutoff at 0.25 cyc/px until §33 exists. |

## 9. Risk register and stop conditions

| Risk | Detection | Required response |
|---|---|---|
| No common `k` passes width and Pareto gates | W1 `measure.py --gate` | Successful negative; print `NO_COMMON_K`; stop phase 1. |
| B3 evidence cannot be reconciled | W4 common-mask reproduction | Stop phase 1; do not land inverse-square law. |
| Residual fit needs a third decode | W4 pass accounting/timing | Drop residual arm or revise design and runtime bar before Rust; never hide pass cost. |
| Commissioned `nu_eff` invalidates uncertainty model | Null/positive controls miss their coverage | Stop W3; revise the statistical model in a new preregistration. |
| D9 lattice exceeds memory or gives no speed refund | Peak-memory and worker sweep | Ship determinism only if within product memory; withdraw refund claim or add tiled/spatial design. |
| PIPE seam or freeze files remain dirty | W2 preflight | Do not edit owned integration files. |
| Confidence bundle requires a post-finish frame pass | Pass accounting | Redesign sufficient statistics; required bundle may not create a third decode. |
| Held-out capture viewed early | Access/provenance log | Invalidate held-out set and name replacements before scoring. |
| Foam is presented as untouched after W4 used it | W4/W5 manifests | Label it regression-only and use a sealed replacement for independent photometric acceptance. |
| Any claim needs `>0.25 cyc/px` | Metric manifest | Mark unlicensed; wait for §33. |

Nine negative gates are evidence, not implementation failures. W1 and W4 are allowed—and required—to halt the build.

## Appendix A — A2 archival activation condition

A2's “robust coarse base” is not part of executable phase 1. `M-PHASE0-VEIL2` found it not robust and explicitly forbids a Rust arm. `BaseBand::Mean` remains. This appendix activates only if a later report names M-PHASE0-VEIL2, supplies independent positive evidence and kill bars, and explicitly authorizes Rust. Merely obtaining a visually pleasing base or changing the A1 selector is not a superseding result.

## W1 brief — hand this to an implementer verbatim

Implement W1 only. Do not modify Rust. Create:

- `experiments/PHASE1-DESIGN/PREREGISTRATION.md`
- `experiments/PHASE1-DESIGN/reference.py`
- `experiments/PHASE1-DESIGN/measure.py`

Treat `D:\personal\macro` and everything beneath it as strictly read-only. Put every cache, copied transform, crop, manifest, and result under `experiments\PHASE1-DESIGN\`. Never allow a decoder, aligner, or sidecar writer to choose an input directory as its output directory.

### Capture manifest

Calibration captures—these three and only these three may be decoded or scored in W1:

1. `D:\personal\macro\requests\30-calibration-grid\calibration-grid-1-sw4-cpl` — 55 RAW frames. Controlled medium-step grid bracket; supplies repeatable edges and the middle of the focus-sampling ladder.
2. `D:\personal\macro\coffee-bubbles` — 19 RAW frames. Supplies the measured flat/detail selection-concentration inversion; do not call it a fixed-focus null.
3. `D:\personal\macro\113MSDCF` — 63 RAW frames. Supplies natural fine detail/MTF structure and the shorter side of a replicate pair.

Reserved after W1—record these paths, but do not decode, inspect pixels, choose crops from, or score them in W1:

- `D:\personal\macro\requests\30-calibration-grid\calibration-grid-1-sw1-cpl` — 91 frames; dense-sampling extreme.
- `D:\personal\macro\requests\30-calibration-grid\calibration-grid-1-sw10-cpl` — 23 frames; coarse-sampling extreme.
- `D:\personal\macro\112MSDCF` — 79 frames; same-subject replicate with 16 more frames than 113MSDCF.
- `D:\personal\macro\coffee-bean` — 105 frames; deep hull-clamp stress capture.
- `D:\personal\macro\foam` — 100 frames; 0.32-stop/eight-frame photometric outlier and non-rigid stress capture. W4 is specified to consume it, so it is a W5 regression case rather than untouched evidence unless the workstream assignment changes.

The shorthand `sw4` and `sw10` is ambiguous. Setup-2 alternatives exist at `D:\personal\macro\requests\30-calibration-grid\calibration-grid-2-sw4-cpl` (46 frames) and `D:\personal\macro\requests\30-calibration-grid\calibration-grid-2-sw10-cpl` (27 frames). They are excluded. Use setup 1 exactly.

### Preregister before scoring

In `PREREGISTRATION.md`, before producing candidate metrics, record and hash:

- the complete ordered RAW manifests;
- fixed crop coordinates, flat/detail labels, exclusions, and alignment-transform provenance;
- decoder name/version and linearization/black-level convention;
- bands and frequency bins, never exceeding 0.25 cycles/output-pixel;
- the block-bootstrap tile size, deterministic seed, replicate count, and confidence-interval convention;
- the `nu_eff` commissioning method and frozen per-band values;
- the ordered global grid `k = 0.00, 0.05, ..., 8.00`;
- the exact legacy gate-4.5 equations and fallback behavior;
- the exact candidate equations below;
- the rule that no crop, grid range, metric, exclusion, or tie-break changes after outcomes are visible.

### Commission the independent crop implementation

`reference.py` must decode with an independent LibRaw binding such as rawpy. It may consume read-only alignment transforms, but it must not call or import `strehl-core`, reuse Rust merge output as an intermediate, or copy Rust numerical routines. Candidate and legacy arms must see byte-identical aligned linear samples so the merge policy is the only changed variable.

Implement and commission these equations:

```text
A(s;a,b) = (2/a) sqrt(max(a*max(s,0) + 3a^2/8 + b, 0))
E_i      = smooth5(LaplacianBand(A_i)^2)
F_i      = beta_i,b * v_A,i,b
q_i      = max(E_i - F_i, 0)
sigma2_i = (2F_i^2 + 4F_i q_i) / nu_eff_b
winner    = finite argmax(E_i), stable lower-frame tie-break
admit_i   = winner OR E_w - E_i <= k sqrt(sigma2_w + sigma2_i)
w_i       = 1/F_i for admitted frames; fail if F_i is non-finite or non-positive
n_eff     = (sum w_i)^2 / sum(w_i^2)
```

If `q_w = 0`, admit every frame with unit weight so the result is an arithmetic mean. Accumulate decisions from shared green and apply one weight to all CFA planes; reconstruct in normalized linear DN; retain the normalized-input hull.

Commission before real scoring with all of the following, and make `--commission` fail on any miss:

- hand-calculated tiny arrays for `F`, `q`, `sigma2`, admission, tie-breaking, unit-mean fallback, and Kish `n_eff`;
- constant-field and Poisson–Gaussian nulls with empirical interval coverage matching the preregistered tolerance;
- planted in-focus coefficients whose known admission boundary moves monotonically with `k`;
- frame-order permutations that leave floating results within the preregistered independent-reference tolerance and winner ties deterministic;
- consistent photometric scaling showing generalized-Anscombe error `<=2e-5`;
- identity/positive controls proving the metric code can report both pass and fail;
- measured correlated-band `nu_eff` with null coverage across the preregistered warp phases; do not silently substitute the analytic `13.37469` independence approximation.

### Width match and choose `k`

For each value in `0.00, 0.05, ..., 8.00`, run the unchanged value on all three calibration captures. Compare candidate Kish `n_eff` with the independently implemented legacy pyramid at gate 4.5. A value is width-matched only if, for every preregistered capture, scored band, and ROI,

```text
abs(mean_n_eff_candidate / mean_n_eff_legacy_gate4.5 - 1) <= 0.05
```

Discard every non-matching value. For each survivor, compute:

- detail/MTF ratio `candidate / legacy-gate-4.5`, with lower 95% bound required to be `>= 0.95`;
- flat/defocused power ratio over `0.10–0.25 cyc/px`, `candidate / legacy-gate-4.5`, with upper 95% bound required to be `<= 0.90`.

A value passes only if every applicable preregistered capture passes both its width and Pareto requirements. Select the smallest passing value. Do not interpolate or extend the grid after looking.

**Exactly one fixed global `k` is permitted across calibration-grid-1-sw4-cpl, coffee-bubbles, and 113MSDCF. A per-capture `k` is a failed workstream, not a workaround. Reporting `NO_COMMON_K` / “no common k exists” is a successful outcome of W1 and correctly halts phase 1. Do not tune around that result.**

### Exact gate command and exit criteria

Run exactly:

```powershell
python experiments/PHASE1-DESIGN/reference.py --commission; python experiments/PHASE1-DESIGN/measure.py --gate
```

Both programs must independently exit 0. `measure.py --gate` must refuse to run or exit nonzero if commissioning artifacts are absent, stale, or hash-mismatched.

Exit 0 from `measure.py --gate` means all of the following are true against legacy gate-4.5:

- one and only one fixed global `k` was selected from the preregistered grid;
- Kish `n_eff` width mismatch is at most 5% for every required capture/band/ROI;
- detail/MTF lower 95% bound is at least 0.95;
- flat-power upper 95% bound is at most 0.90;
- no scored frequency exceeds 0.25 cyc/px;
- all manifests, crops, parameters, intervals, and failures are written to the results directory.

If no common value meets those conditions, write the full negative report, print `NO_COMMON_K`, return a distinct nonzero gate code for automation, and stop phase 1. The scientific outcome is successful even though the feature build does not proceed.
