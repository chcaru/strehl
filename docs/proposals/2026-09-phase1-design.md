# Phase 1 — unified banded-admission merge

> **REFUTED — DO NOT IMPLEMENT. This design is retained as history only.**
>
> The W1 go/no-go gate below **fired against this design** and it did not survive.
> The result was `NO_COMMON_K`: of 42 predicates, 16 pass at some `k` and 26 pass
> at none, and critically **no predicate in bands 4–6 passes at any `k` in
> `[0,8]`**. The two ends of the band range require opposite values of the single
> constant this design has on offer, so the gap cannot be closed by choosing `k`
> better. **The design is refuted, not untuned**, and it must not be revived by
> adjusting a constant.
>
> The verdict was challenged on four separate grounds by the program orchestrator
> and survived all four; the numbers were then independently re-verified. See
> `docs/STATUS.md` §2.8 for the challenge and its outcome.
>
> Everything below this banner is the design *as written before the gate fired*.
> Its capture manifest, its repository citation audit, its A2/B3 archival
> evidence, and its correction that `119MSDCF` is not a scorecard systems arm
> remain independently factual and may be cited. **The merge design itself may
> not.**

Status: **REFUTED by the W1 gate.** Originally: PROPOSAL — repository-verified implementation design; W1 is a mandatory go/no-go gate. A2 and B3 are excluded from executable phase 1 by repository evidence. The executable spine is A1/A4/B4/B6 behind the aligned-pyramid freeze and D9(a).

Verified 2026-09-02 PDT first against repository HEAD `40b20bef0fe0cdaba7298573095806e580a7ed85`; symbol anchors were refreshed at `986c46535fc082395831724f1d45c33a1d974390`, and this replacement was rechecked against current HEAD `a3d4ba30e2a1f4ba64a4192ff89742d9947d7618`. `crates/strehl-cli/src/merge_cmd.rs` remained under active edit, so volatile CLI locations below are anchored on symbols rather than depending on line numbers.

## 1. Decision and scope

The governing proposal literally defines phase 1 as one merge containing A1, A2, A4, B3, B4, and B6, after an aligned-pyramid byte freeze and D9(a) (`docs/proposals/2026-08-sota-path.md` §9, “Phase 1 — one merge”). Subsequent repository evidence removes two arms:

- A2 is `NOT ROBUST`; `M-PHASE0-VEIL2` forbids its Rust arm and retains `BaseBand::Mean`.
- B3 is not supported as a product law. `M99-photometric` directly tests the alignment sidecar’s scale ladder and refutes the fixed inverse-square predictor; `BUILD-GHOST` measures a different, independently refitted pairwise scale and does not validate the sidecar predictor. B3 is archived in Appendix B.

Executable phase 1 is therefore **A1/A4/B4/B6**. It retains the seven-band Burt–Adelson Laplacian pyramid, `BaseBand::Mean`, and `Hull::InputRange`; replaces soft-power selection with a two-pass band-admission rule; emits a vector confidence product; and introduces no replacement selection-inflation constant. It applies no per-frame photometric gain: phase-1 gains are identically one.

D9(a) is a determinism prerequisite, not a promised speedup. Its fixed lattice must fit within the scorecard’s 6-GiB process-tree ceiling. The proposal’s claimed 1.29× refund is withdrawn for the current full-image accumulator geometry unless a separately measured memory-reducing design earns it.

Three constraints are absolute:

1. D8/SPLIT is killed. No subdivision of one bracket may choose or adapt `k`.
2. No claim above **0.25 cycles/output-pixel** is licensed until the §33 capture exists and passes its own commissioning.
3. A capture family used to choose `k`, a metric, a crop, a threshold, or an implementation response is development data and cannot provide primary W5 or SOTA-scorecard evidence for that version.

## 2. Verification ledger

### 2.1 Requested citations

| Citation | Result | Repository reading |
|---|---|---|
| `docs/proposals/2026-08-sota-path.md:2074-2083` | **Resolved; superseded in part by later evidence** | Defines literal phase 1 as A1/A2/A4/B3/B4/B6, requires the aligned-pyramid freeze and D9(a), and exits with per-band `n_eff` artifacts. Later repository evidence removes A2 and B3 from the executable spine. |
| `docs/proposals/2026-08-sota-path.md:459-576` | **Resolved, but provisional** | Contains A1, A2, and the opening of A4. A1's acceptance text still contains literal `[bar]` placeholders, so it is not an executable acceptance specification by itself. |
| `docs/proposals/2026-08-sota-path.md:751-769` | **Resolved; B3 rejected, B4 retained** | Contains B3 and B4. B3’s alignment-scale law is contradicted by the direct `WarpMap`-scale test in `M99-photometric`; `BUILD-GHOST` measures independently refitted pairwise scales and does not overturn that product result. B4 agrees with current `SELECTION_INFLATION = 1.0`. |
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

### 2.3 Repository-wins resolutions

1. **A2 is excluded.** `BaseBand::Mean` remains.
2. **B3 is excluded.** `M99-photometric` tests the scale ladder the product actually holds. Relative to the no-law residual, fixed `-2A` reads 3.96×, 0.722×, 1.277×, and 5.72× on its four decks; fitted exponents are -4.740, -6.466, -0.879, and -3.045. This fails its registered predictor.
3. **`BUILD-GHOST` does not rescue B3.** Its scale is independently refitted pairwise rather than read from the shipping `WarpMap`; its median subject slope is 0.365 against the fixed prediction 1.0. Its `p=0.0025` establishes informative pairing, not unit slope. Six large-ramp subjects obtain 2.07×–5.06× RMS reduction, but the report recommends not porting photometric normalization and explicitly says foam’s output benefit was not measured.
4. **The merge is strictly two-pass.** There is no residual-gain fit, calibration decode, or pass-dependent normalization. Passes one and two consume the same black-subtracted aligned samples. Required confidence statistics are retained during those passes.
5. **Foam is no longer calibration data.** With B3 removed, W1–W3 do not inspect it; W5 may use it as sealed phase-1 stress evidence. It remains historically studied, not historically unseen.
6. **Capture independence is by family, not spelling.** `112MSDCF` and `113MSDCF` are one subject family; because W1 uses 113, 112 is regression-only. All five calibration-grid sweeps form one target family and remain sealed from W1–W3 and phase-1 adaptation. `coffee-bubbles` and `coffee-bean` are distinct subjects with 19 and 105 ARWs and no shared frames.
7. **The uncertainty equation remains uncommissioned design material.** `sigma_E^2=(2F^2+4Fq)/nu_eff` must pass W1’s real-band null and positive controls before W3.
8. **Winner and fallback semantics are fixed.** Winner is finite argmax `E`, ties choose the lower stable frame ordinal, and `q_w=0` routes every frame through unit-weight arithmetic mean.
9. **The global-width prior is hostile.** Existing reports show large cross-stack dispersion. `NO_COMMON_K` is therefore an expected successful negative, not an invitation to tune by capture.
10. **The aligned-pyramid freeze is absent.** The registry’s current pyramid row has alignment disabled. An executable aligned row must be committed before D9 changes reduction behavior.
11. **D9 does not buy speed under current memory geometry.** The registry reports 1328 MiB per current worker: four are about 5312 MiB, eight about 10624 MiB. `BandMerge::accumulator_floats` implies about 629 MiB per full accumulator; 32 alone are about 19.6 GiB before workspaces. D9 may establish determinism, but no 1.29× refund is claimed.
12. **PIPE ownership remains exclusive.** W2 never edits `merge_cmd/decode_queue.rs` and does not enter `merge_cmd.rs` or the freeze harness until their current owners commit and hand off clean files.

## 3. Capture manifest and leakage boundary

Nothing under `D:\personal\macro` may be written, renamed, or used as a cache destination.

A capture is **consumed** when its pixels or candidate outcomes influence `k`, `nu_eff`, crop selection, exclusions, a threshold, a model choice, or a code response. Listing paths, counting files, and reading metadata for inventory do not consume it. Captures from the same physical target/session family are not promoted to independent subjects merely because they are separate directories.

| Role | Capture | Full path | ARWs | Diagnostic value |
|---|---|---|---:|---|
| W1 development | flat-on-ruler | `D:\personal\macro\flat-on-ruler-cpl` | 79 | Rigid planar null: printed card fixed to a steel ruler, sharp markings and paper fibre, with flat and structured regions. Use coherent detail; use MTF only if the input-only line-locus qualifier passes. |
| W1 development | coffee-bubbles | `D:\personal\macro\coffee-bubbles` | 19 | Known flat/detail concentration inversion; development-only in the SOTA scorecard. |
| W1 development | 113MSDCF | `D:\personal\macro\113MSDCF` | 63 | Natural detail through 0.25 cyc/px; already a historical regression sentinel, not a primary scorecard acuity capture. |
| W5 sealed reference | grid-1 sw1 | `D:\personal\macro\requests\30-calibration-grid\calibration-grid-1-sw1-cpl` | 91 | Dense independent grid reference; never a scored repeat. |
| W5 sealed primary | grid-1 sw4 | `D:\personal\macro\requests\30-calibration-grid\calibration-grid-1-sw4-cpl` | 55 | Scorecard repeat A. |
| W5 sealed primary | grid-2 sw4 | `D:\personal\macro\requests\30-calibration-grid\calibration-grid-2-sw4-cpl` | 46 | Scorecard repeat B from a separate setup. |
| W5 sealed stress | grid-1 sw10 | `D:\personal\macro\requests\30-calibration-grid\calibration-grid-1-sw10-cpl` | 23 | Sparse-step stress A. |
| W5 sealed stress | grid-2 sw10 | `D:\personal\macro\requests\30-calibration-grid\calibration-grid-2-sw10-cpl` | 27 | Sparse-step stress B. |
| W5 sealed primary | coffee-bean | `D:\personal\macro\coffee-bean` | 105 | Distinct from coffee-bubbles; rigid deep-stack hull and medium-N systems stress. |
| W5 sealed primary | foam | `D:\personal\macro\foam` | 100 | Non-rigid, specular and exposure-irregular stress. It tests robustness of the no-B3 product; it does not establish a photometric correction benefit. |
| Sealed reserve | 119MSDCF | `D:\personal\macro\119MSDCF` | 33 | Not assigned by the current scorecard; kept unopened by W1–W3 pending a future role. |
| W5 systems | bee-1-cpl | `D:\personal\macro\bee-1-cpl` | 299 | Scorecard N=33, N=100, and N=299 wall-clock and memory arms. |
| Regression only | 112MSDCF | `D:\personal\macro\112MSDCF` | 79 | Same subject and sweep as W1’s 113MSDCF; cannot be independent evidence after 113 is used. |

> **Disputed prescribed claim — corrected, not applied as written:** the replacement labelled `119MSDCF` the scorecard short-stack systems arm. The current scorecard does not mention `119MSDCF`; M11/M12 use the first 33 frames of `bee-1-cpl`. The row above keeps `119MSDCF` sealed but does not attribute a scorecard role to it.

All grid captures remain sealed from W1–W3 and phase-1 outcome-driven adaptation until W5 candidate scoring. An independently preregistered scorecard lane may measure its frozen baseline on the grid family, but its sites or outcomes must not cross into W1–W3. W5 freezes all input-derived sites before rendering candidate output and reports the grid family hierarchically by setup/capture rather than pretending five sweeps are five subjects. If implementation changes after a W5 miss, every opened W5 capture becomes development data for that revision and fresh validation captures are required.

If the already-launched W1 has exposed candidate results from grid-1 sw4, that capture is consumed and may not remain scorecard repeat A. If no candidate result or outcome-dependent crop was seen, quarantine the abandoned W1 artifacts, record the aborted access, amend the preregistration, and restart with flat-on-ruler.

## 4. Merge contract

### 4.1 Fixed topology and notation

- Keep `DEFAULT_BANDS = 7`, existing Burt–Adelson reduce/expand operators, replicated borders, and linear-DN reconstruction.
- Keep `BaseBand::Mean`; the base is the arithmetic mean of black-subtracted aligned linear-DN base coefficients.
- Keep `mean_coarse = 0` unless a separate measured ladder changes it.
- Keep `Hull::InputRange`, evaluated against the aligned, black-subtracted phase-1 inputs.
- A coefficient is indexed by frame `i`, band `b`, and native band position `p`.
- Stable frame ordinal is deterministic input order after CLI path resolution.
- `S_i(p)=(G1+G2)/2` on the aligned quad grid. Phase 1 applies no per-frame photometric gain.
- PRNU is excluded from between-frame admission variance, consistent with the current noise-model contract; it remains relevant to output uncertainty.

### 4.2 B3 — excluded from executable phase 1

Phase 1 does not derive gain from alignment scale, fit gain from frame pixels, or compose a residual curve. Every per-frame gain is exactly one. Existing `photometric::PhotometricMap`, `PhotometricMap::from_flux`, `scale_plane_noise`, and `scale_noise_model` remain available to the estimator/reference path but are not changed or newly invoked by the phase-1 pyramid.

This decision keeps the merge at two RAW decodes. It also prevents pass one from electing under one photometric state and pass two from estimating under another.

Appendix B records the evidence and reopening requirements. B3 may return only through a separate preregistered milestone; it is not a latent phase-1 flag.

### 4.3 B6 decision transform

For each frame, form effective shared-green temporal-noise coefficients:

```text
a_G = (a_G1 + a_G2) / 4
b_G = (b_G1 + b_G2) / 4
s   = max(S, 0)
A(s; a_G, b_G) = (2 / a_G) * sqrt(max(a_G*s + 3*a_G^2/8 + b_G, 0))
v_A(s) = (a_G*s + b_G) / (a_G*s + 3*a_G^2/8 + b_G)
```

`A` is used only for focus decisions. A separate linear-DN pyramid supplies the estimate and hull. Denominators and propagated variances must be finite and positive; non-finite decision samples neither win nor enter admission.

The algebraic covariance control remains mandatory even though the product applies no gain: for synthetic `s'=c*s`, `a'=c*a`, and `b'=c^2*b`, the implementation must satisfy `A(s';a',b')=A(s;a,b)` to maximum absolute error `2e-5` over the preregistered grid. This commissions B6 arithmetic; it does not license B3.

### 4.4 Pass one: `BandReference`

For every frame, build the generalized-Anscombe shared-green Laplacian decision pyramid. At every `(b,p)`:

```text
L_i       = LaplacianBand_b(A_i)[p]
E_i       = smooth5(L_i^2)[p]
F_i       = beta_i,b * v_A,i,b[p]
q_i       = max(E_i - F_i, 0)
sigma2_Ei = (2*F_i^2 + 4*F_i*q_i) / nu_eff_b
```

`beta_i,b` is the frame- and warp-specific band-noise transfer represented by `BandGain` and `frame_beta`. `v_A,i,b` follows the existing Gaussian variance pyramid. `NU_SMOOTH = 13.37469` is only the independent-sample starting value; W1 must commission conservative per-band `nu_eff_b` values against real correlated bands and the preregistered warp phases.

`BandReference` stores at native band resolution:

```text
winner_energy: f32
winner_floor: f32
winner_variance: f32
winner_frame: u16/u32
below_floor: bit
```

Winner is the maximum finite `E_i`; equal bit-pattern energies choose the lower stable frame ordinal. `below_floor` means `q_w=0`. No finite winner is a merge error with band and coordinates, not a silent fallback.

### 4.5 Pass two: admission and linear reconstruction

Re-decode each frame and repeat the same black subtraction, defect handling, alignment, crop, shared-green construction, variance propagation, and frame-specific `beta` calculation. No state estimated from pass one changes the input samples or noise model in pass two.

For an above-floor winner, admit frame `i` iff:

```text
E_w - E_i <= k * sqrt(sigma2_Ew + sigma2_Ei)
```

The winner is always admitted. Exactly one fixed global `k`, selected by W1, is the product default and is recorded in provenance. A per-capture value is forbidden.

Use one shared-green weight for all four CFA planes:

```text
w_i = 1/F_i   if admitted and winner is above floor
w_i = 1       if winner is below floor
w_i = 0       otherwise
```

A used `F_i` must be finite and strictly positive. Accumulate:

```text
sum_wL[c] += w_i * L_linear_i[c]
sum_w     += w_i
sum_w2    += w_i^2
L_out[c]   = sum_wL[c] / sum_w
n_eff      = sum_w^2 / sum_w2
```

For a below-floor winner, every valid frame receives unit weight, yielding an arithmetic mean. `sum_w==0` is an error.

During this same pass, retain the minimum decision response and the responses at `winner_frame-1`, `winner_frame`, and `winner_frame+1` needed for the baseline-subtracted log-parabola. Do not decode frames after `BandMerge::finish`.

Accumulate each aligned native CFA plane’s `lo`/`hi`, reconstruct the seven linear bands plus arithmetic-mean base, and apply:

```text
d_hull = max(lo - reconstructed, 0, reconstructed - hi)
output = clamp(reconstructed, lo, hi)
```

### 4.6 B4 output uncertainty

No replacement selection inflation is allowed. Keep the multiplier exactly `1.0`. Where temporal output variance is required:

```text
Var_out = sum_i(w_i^2 * Var_i) / (sum_i w_i)^2
```

A fixed multiplier other than 1.0 requires a new independent measurement.

### 4.7 A4 `ConfidenceBundle`

Add `crates/strehl-core/src/confidence.rs` and export it from `lib.rs`. Reuse the baseline-subtracted log-parabola semantics of `ThroughFocus::subframe_deficit`; do not create a competing formula.

The bundle contains:

1. Per-band Kish `n_eff` at native band resolution.
2. Baseline-subtracted sub-frame deficit, preserving boundary/invalid state.
3. Native per-band admission width `k*sqrt(2*sigma2_Ew)` plus a documented display expansion; native values are authoritative.
4. Pre-clamp hull distance in linear DN per CFA plane.
5. Below-floor, invalid-parabola, bracket-boundary, and future-censoring validity masks.

`--confidence-bundle <directory>` writes lossless float TIFFs and a manifest naming dimensions, units, invalid encoding, input hashes, alignment hash, noise provenance, `photometric_policy=none`, `k`, `nu_eff`, `beta` provenance, frame order, lattice ID, git SHA, and hull policy. Confidence generation must not alter image bytes or require a post-`finish` decode. The existing centrality `--confidence-map` remains separately named and optional.

## 5. Determinism, orchestration, and freezes

### 5.1 D9(a): determinism without a speed claim

Use lattice ID `cpu-v1-c4-ceil`. For `N` frames:

```text
logical_chunks = min(N, 4)
chunk_size     = ceil(N / 4)
chunk j        = [j*chunk_size, min((j+1)*chunk_size, N))
```

Omit empty chunks. This matches the current four-worker contiguous partition. Every chunk folds frames in stable ordinal order. `BandMerge::absorb` consumes partials in ascending chunk ID. Requested worker count changes only scheduling; it never changes frame grouping or reduction order.

Concurrency is separately capped by the measured process-tree memory model. If four concurrent phase-1 partials do not fit, run the same four logical chunks in smaller batches; do not change chunk boundaries or lattice ID. The banner reports requested workers, effective concurrent chunks, logical chunk count, per-pass memory estimate, and measured peak.

The current baseline geometry predicts:

- 1328 MiB × 4 workers = 5312 MiB before unmodelled process-tree headroom;
- 1328 MiB × 8 workers = 10624 MiB, above 6 GiB;
- about 629 MiB per full accumulator;
- 32 full accumulators ≈19.6 GiB before workspaces.

Therefore D9 claims **worker-count-invariant bytes only**. It does not claim the proposal’s 1.29× speed refund. A scorecard speed pass remains unmeasured and may fail even when D9 succeeds.

Acceptance is byte-identical output at requested workers 1/2/4/8/16, with process-tree peak committed memory `<=6 GiB` in every arm. The 16-worker arm must meet the scorecard runtime bar before any SOTA speed claim; an effective cap of four is reported, not disguised.

### 5.2 PIPE hand-off

`lane-PIPE` exclusively owns `crates/strehl-cli/src/merge_cmd/decode_queue.rs`. W2 consumes `decode_queue::rendezvous` and never edits that file.

Before W2 touches integration or freeze files, all commands must pass:

```powershell
git status --short -- crates/strehl-cli/src/merge_cmd.rs crates/strehl-cli/src/merge_cmd/decode_queue.rs crates/strehl-cli/tests/byte-freeze.rs crates/strehl-cli/tests/byte-freezes.tsv
rg "mod decode_queue|decode_queue::rendezvous" crates/strehl-cli/src/merge_cmd.rs
cargo test -p strehl-cli --bin strehl decode_fold_queue
```

The first command must print nothing; the second must find both seam references; the test must exit 0. If PIPE does not land that seam, W2 is blocked pending a revised orchestration design.

Both phase-1 passes use the landed bounded rendezvous. Producer failure reaches the consumer, consumer failure cancels production, and decoded-frame backlog remains constant in stack depth.

### 5.3 Correct freeze order

1. **Wait for PIPE and the freeze owner to land.**
2. **Commit the pre-D9 aligned freeze first.** Extend the registry so the invocation records an explicit pyramid selector, `STREHL_PYRAMID_WORKERS`, and PIPE queue mode. Add an aligned sidecar row using the committed `coffee-bean-20.warpmap.txt`, `--merge pyramid`, `--pyramid-select soft`, `--pyramid-gate 2.0`, `--limit 20`, workers `4`, and an explicit queue mode. Independently measure the hash, then prove the row’s teeth with a pyramid-path plant.
3. **Land D9 as the first behavior-changing W2 commit.** `cpu-v1-c4-ceil` must reproduce the pre-D9 workers=4 hash unchanged, because it preserves that exact partition and absorb order. Workers 1/2/4/8/16 must then reproduce that same hash.
4. If the workers=4 hash moves, stop before re-baselining. Attribute the movement independently; a post-D9 hash generated and accepted by the same change is not a freeze.
5. After W1 GO and W3 completion, integrate admission. Keep the pre-D9/D9 row explicitly on `soft`; add a separate explicit `admission` row carrying the fixed `k`. Only then flip the product default.

The old ordering—implement D9 and add the first aligned row afterwards—tests only that D9 can reproduce its own answer. It loses the executable pre-change predicate, cannot distinguish intended reduction movement from unrelated aligned-path movement, and recreates generator/checker cancellation.

## 6. Acceptance definitions

All intervals are 95% block-bootstrap intervals over preregistered non-overlapping physical sites. Seeds, tiles, crops, exclusions, and replicate counts are frozen before candidate output. No scored frequency exceeds 0.25 cyc/px.

- **Width match:** on flat-on-ruler, coffee-bubbles, and 113MSDCF, for every applicable band and frozen ROI, `abs(mean_n_eff_candidate/mean_n_eff_legacy_gate4.5 - 1) <= 0.05`.
- **Detail/MTF retention:** candidate/legacy-gate-4.5 lower95 `>=0.95` on each applicable W1 development capture and later on every applicable W5 capture. MTF is permitted only after its input-only line-locus qualification; otherwise use the preregistered coherent-detail instrument.
- **Flat power:** candidate/legacy-gate-4.5 integrated over `0.10–0.25 cyc/px`; upper95 `<=0.90` on every applicable flat/defocused ROI.
- **Sampled `n_eff`:** maximum absolute Rust-versus-independent-LibRaw error `<=0.02`.
- **Selector census:** coefficients admitting exactly one frame `<0.1%` in every scored band/capture. Count admissions directly.
- **Hull:** maximum output excess beyond independently recomputed aligned-input bounds `<=1 DN`, including quantization.
- **Runtime:** release candidate/post-D9 legacy-gate-4.5 warm-wall ratio `<=2.00` on every timed held-out capture, with the same lattice ID, requested worker setting, queue policy, registration, write, and required confidence bundle. No D9 refund is subtracted.
- **Memory:** peak native-RAW process-tree committed bytes `<=6 GiB`; `peak_N299/peak_N33<=1.10`. Record working set, child processes, page faults, and temporary bytes.
- **Determinism:** highest-precision delivered image bytes are identical at requested workers 1/2/4/8/16 while remaining within the memory bar.
- **B6 covariance:** maximum generalized-Anscombe error under consistently scaled synthetic sample/noise parameters `<=2e-5`.
- **Pass count:** exactly two RAW decodes per accepted frame. Required confidence output adds none.
- **Data separation:** all grid captures, coffee-bean, foam, 119MSDCF, and bee-1 remain unopened by W1–W3. `112MSDCF` is regression-only because W1 consumes its same-subject partner, 113MSDCF.

There is no phase-1 photometric-residual or foam-correction acceptance criterion because B3 is not executable scope.

## 7. Workstreams

| ID | Workstream | Parallel-safe | Dependencies | Owned files | Completion gate |
|---|---|---|---|---|---|
| W1 | Independent admission pilot | Yes | None | `experiments/PHASE1-DESIGN/PREREGISTRATION.md`; `reference.py`; `measure.py` | One fixed global `k`; width mismatch `<=5%`; detail/MTF lower95 `>=0.95`; flat-power upper95 `<=0.90`. `NO_COMMON_K` is a successful negative and stops integration. |
| W2 | Freeze, D9, and CLI integration | Yes relative to W1/W3; internally serial | PIPE and freeze-owner hand-off for pre-freeze/D9; W1 GO and W3 API before integration | `crates/strehl-cli/src/main.rs`; `crates/strehl-cli/src/merge_cmd.rs`; `crates/strehl-cli/tests/byte-freeze.rs`; `crates/strehl-cli/tests/byte-freezes.tsv`. Never `merge_cmd/decode_queue.rs`. | Pre-D9 aligned row committed and commissioned; D9 preserves its workers=4 hash; 1/2/4/8/16 hashes match under 6 GiB; two-pass orchestration, confidence bundle, provenance, and explicit soft/admission rows land. |
| W3 | Core admission, B6, and A4 | Yes | W1 GO | `crates/strehl-core/src/pyramid.rs`; `through_focus.rs`; new `confidence.rs`; `lib.rs` | Typed pass APIs; commissioned energy uncertainty; linear reconstruction/hull; vector confidence; `cargo test -p strehl-core` green. |
| W5 | Independent acceptance | No | W2 + W3 | `experiments/PHASE1-VERIFY/PREREGISTRATION.md`; `verify.py` | Sealed-capture Pareto, confidence, selector, hull, two-pass, runtime, memory, and determinism bars pass; workspace tests and clippy pass. |

W4 is retired from phase 1 rather than silently repurposed: it was the B3 workstream, and B3 is archived.

### 7.1 W1 selection rule

Before outcomes, W1 freezes crops, exclusions, bootstrap plan, `nu_eff`, and:

```text
k = 0.00, 0.05, 0.10, ..., 8.00
```

Run every value unchanged on flat-on-ruler, coffee-bubbles, and 113MSDCF. Discard any value missing a required 5% width match. Among survivors, require every applicable Pareto bar on all three captures. Select the smallest survivor. No interpolation, expanded grid, per-capture value, or post-outcome crop is permitted.

No common value means `NO_COMMON_K`, a successful W1 result that halts W3 and W2 integration.

### 7.2 W2 details

- W2 may perform the pre-freeze and D9 milestones while W1 runs, after PIPE and freeze-file hand-off.
- D9 is the first behavior-changing W2 commit; the pre-D9 freeze instrumentation commit necessarily precedes it.
- Preserve explicit legacy soft/gate-4.5 controls.
- Both passes call the same frame preparation seam for decode, black subtraction, defects, warp, crop, luma, variance, and `beta`.
- Apply no phase-1 photometric gain.
- Use the landed bounded queue in both passes.
- Produce `ConfidenceBundle` from pass sufficient statistics, not another frame traversal.
- Flip the default only after W1 GO and all freeze teeth pass.

### 7.3 W5 protocol

Before any W5 candidate render, seal input-derived site manifests for the full grid family, coffee-bean, foam, and the `bee-1-cpl` N=33/100/299 systems arms. Grid sw1 is reference-only; grid-1/grid-2 sw4 are primary repeats; both sw10 captures are sparse-step stress. Treat setup and capture as hierarchy levels. `119MSDCF` remains an unassigned sealed reserve, not current scorecard evidence.

`112MSDCF` may be reported only as same-subject regression after W1’s use of 113MSDCF. It cannot rescue a failed independent capture.

Decode independently with rawpy/LibRaw and do not call `strehl-core` when recomputing decisions, weights, `n_eff`, or hulls. W5 never retunes `k`. A miss either stops this phase-1 version or forces a new preregistration and fresh validation captures.

### 7.4 Sequencing and critical path

W1’s synthetic commissioning may run immediately. Its real-capture phase must use the corrected development set. PIPE proceeds independently. After PIPE and freeze-file hand-off, W2 may commit the pre-D9 row and D9 while W1 runs. W3 starts only on W1 GO. W2 integration waits for both W1 GO and W3. W5 follows integration.

The joined critical path is:

```text
W1 GO -> W3 --------------------\
                                  -> W2 integration -> W5
PIPE -> pre-D9 freeze -> D9 ----/
```

## 8. Rejected alternatives and controls

- **Extend soft-power weighting:** preserves the width-confounded selector.
- **Move to estimator/per-pixel geometry:** restores measured flat-ground patchwork.
- **Per-capture `k`:** a failed global model, not a product feature.
- **Split-stack tuning:** prohibited by D8.
- **Replacement selection inflation:** contradicted by B4 evidence.
- **B3 alignment-scale gain:** rejected because the shipping `WarpMap` predictor fails M99; independently refitted pairwise scale is not a substitute.
- **Residual gain in phase 1:** rejected because a pixel-derived fit is unavailable before pass one and creates a third decode.
- **D9 speed refund:** rejected under the current 1328-MiB worker geometry; determinism is retained.

| Cheat | Misleading result | Control |
|---|---|---|
| Average nearly everything | Low flat noise | Width match and detail lower95 `>=0.95`. |
| Sharpen output | High detail/MTF | Flat-power upper95 `<=0.90`, input hull `<=1 DN`, and coherent-detail control. |
| Fabricate confidence | Plausible maps | Independent LibRaw recomputation; `n_eff` error `<=0.02`; manifest hashes. |
| Force serial execution | Stable hashes | 1/2/4/8/16 hashes jointly reported with runtime and 6-GiB memory. |
| Tune `k` by capture | Every development capture passes | One manifest-global value and explicit `NO_COMMON_K`. |
| Tune on a score capture | Good apparent generalization | Capture-family ledger; all grid captures sealed from phase-1 development until W5 candidate scoring. |
| Hide a third pass | Better-looking algorithm description | Decode census and complete process timing. |
| Claim D9 refund outside budget | Fast non-product arm | Process-tree peak `<=6 GiB`; requested and effective concurrency both printed. |
| Claim high-frequency detail from noise | Attractive band power | Hard 0.25-cyc/px ceiling until §33. |

## 9. Risk register and stop conditions

| Risk | Detection | Required response |
|---|---|---|
| No common `k` | W1 gate | Report `NO_COMMON_K`; stop phase-1 integration. |
| W1 consumes a scorecard grid capture | Access/result ledger | Halt and retarget before outcomes; if outcomes were visible, invalidate that capture as holdout. |
| `nu_eff` model misses real-band coverage | W1 null/positive controls | Stop W3 and revise under a new preregistration. |
| Two-pass candidate exceeds `2.00×` | W5 complete warm-wall timing | Fail phase 1; do not subtract decode or claim a D9 refund. |
| D9 exceeds 6 GiB | Process-tree monitor | Reduce scheduling concurrency without changing `cpu-v1-c4-ceil`; if still over, D9 fails. |
| D9 gives no speed improvement | Worker sweep | Publish determinism only; SOTA speed remains unmeasured/failed. |
| Pre-D9 aligned row is added after D9 | Commit/freeze audit | Reject the freeze and recreate an executable pre-change predicate before proceeding. |
| PIPE or freeze files remain dirty | W2 preflight | Do not edit them. |
| Confidence requires another decode | Decode census | Redesign sufficient statistics; required confidence may not create pass three. |
| W5 capture influences a repair | Outcome/code chronology | Mark the family development and require fresh validation. |
| Any metric needs `>0.25 cyc/px` | Metric manifest | Emit `UNLICENSED_GT_0.25`; wait for §33. |

Negative W1 or W5 outcomes are successful measurements. No workstream is tasked with making phase 1 pass.

## Appendix A — A2 archival activation condition

A2's “robust coarse base” is not part of executable phase 1. `M-PHASE0-VEIL2` found it not robust and explicitly forbids a Rust arm. `BaseBand::Mean` remains. This appendix activates only if a later report names M-PHASE0-VEIL2, supplies independent positive evidence and kill bars, and explicitly authorizes Rust. Merely obtaining a visually pleasing base or changing the A1 selector is not a superseding result.

## Appendix B — B3 archival evidence and reopening condition

B3 is not executable phase-1 scope.

`M99-photometric` directly evaluates `ln(flux/flux_ref)=-2 ln(a/a_ref)` using the alignment scale the shipping merge holds. The fixed predictor is worse than the null by 3.96×, 1.277×, and 5.72× on three decks and improves the fourth only to 0.722×, missing its registered bar. Free exponents span -0.879 to -6.466. `PhotometricMap::from_flux`, rather than an alignment-law constructor, reflects that result.

`BUILD-GHOST` later finds physically informative pairing between flux and independently refitted pairwise similarity scale (`p=0.0025`) and six large-ramp subjects with 2.07×–5.06× RMS reduction. That estimator is not the product `WarpMap`; the median slope is 0.365 rather than the fixed 1.0; and the report recommends deferring the port. Foam’s 0.3165-stop eight-frame excursion is real, but improvement of its merged output was explicitly not measured.

Reopening B3 requires all of:

1. one documented scale convention connecting the shipping `WarpMap` to independently measured pairwise magnification;
2. a shuffled/interleaved-focus capture separating scale from elapsed time and illumination;
3. a held-out predictor whose fixed slope includes 1.0 and whose correction beats the no-law residual under preregistered bars;
4. measured final-image benefit, not flux-fit benefit alone;
5. a gain available before pass one without an extra RAW decode, or a separately approved pass/runtime design.

Existing `scale_noise_model` remains the required propagation if a future arm earns activation.

## W1 brief — hand this to an implementer verbatim

Implement W1 only. Do not modify Rust. Create:

- `experiments/PHASE1-DESIGN/PREREGISTRATION.md`
- `experiments/PHASE1-DESIGN/reference.py`
- `experiments/PHASE1-DESIGN/measure.py`

Treat `D:\personal\macro` and all descendants as strictly read-only. Write caches, manifests, transforms, crops, and results only beneath `experiments\PHASE1-DESIGN\`.

Do not decode or score any calibration-grid capture in W1. The committed SOTA scorecard reserves that family for later reference and scored repeats.

### Development captures

These three and only these three may influence W1:

1. `D:\personal\macro\flat-on-ruler-cpl` — **79 ARWs**. A rigid planar null: printed card fixed to a steel ruler, with sharp markings, paper fibre, and flat regions. Use coherent detail over 0.10–0.25 cyc/px. Use an MTF statistic only if an input-only line-locus qualification is frozen first and passes.
2. `D:\personal\macro\coffee-bubbles` — **19 ARWs**. The known flat/detail selection-concentration inversion and a scorecard development-only subject.
3. `D:\personal\macro\113MSDCF` — **63 ARWs**. Natural fine detail with usable signal only through 0.25 cyc/px; a development/regression subject, not primary scorecard acuity evidence.

The following are sealed from W1:

- all five directories under `D:\personal\macro\requests\30-calibration-grid\`;
- `D:\personal\macro\coffee-bean`;
- `D:\personal\macro\foam`;
- `D:\personal\macro\119MSDCF` (sealed reserve; not a current scorecard systems arm);
- `D:\personal\macro\bee-1-cpl`;
- `D:\personal\macro\112MSDCF`.

`112MSDCF` is the same subject/sweep family as 113MSDCF and can later be regression-only, not independent validation.

If a previous W1 attempt has already shown candidate results from grid-1 sw4, stop and report that access immediately; do not conceal it by restarting. If only inventory was read and no candidate outcome or outcome-dependent crop was seen, quarantine the aborted artifacts, record the aborted invocation, and restart under this brief.

### Preregister before real scoring

Record and hash:

- complete ordered RAW manifests;
- fixed crops, flat/detail labels, exclusions, and alignment provenance;
- decoder/version and black-level convention;
- bands and bins, all `<=0.25 cyc/px`;
- bootstrap site unit, tile size, seed, replicates, and interval convention;
- commissioned per-band `nu_eff`;
- `k=0.00,0.05,...,8.00`;
- exact legacy gate-4.5 equations and fallback;
- exact candidate equations;
- the rule that outcomes cannot change captures, crops, metrics, exclusions, grid, or tie-breaks.

Phase 1 applies no per-frame photometric gain. Candidate and legacy arms must consume byte-identical black-subtracted aligned samples.

### Commission the independent crop implementation

Decode through an independent LibRaw binding such as rawpy. Do not import or call `strehl-core`, and do not use Rust merge output as an intermediate.

Implement:

```text
A(s;a,b) = (2/a) sqrt(max(a*max(s,0) + 3a^2/8 + b, 0))
E_i      = smooth5(LaplacianBand(A_i)^2)
F_i      = beta_i,b * v_A,i,b
q_i      = max(E_i - F_i, 0)
sigma2_i = (2F_i^2 + 4F_i*q_i) / nu_eff_b
winner   = finite argmax(E_i), lower-frame tie-break
admit_i  = winner OR E_w-E_i <= k*sqrt(sigma2_w+sigma2_i)
w_i      = 1/F_i when admitted
n_eff    = (sum w_i)^2 / sum(w_i^2)
```

If `q_w=0`, admit every valid frame with unit weight and emit the arithmetic mean. Use shared green for decisions and one weight for all CFA planes. Reconstruct from a separate linear-DN pyramid and retain the aligned-input hull.

`--commission` must fail unless all of these pass:

- hand-calculated arrays for `F`, `q`, `sigma2`, admission, tie-breaking, mean fallback, and Kish `n_eff`;
- Poisson–Gaussian and constant-field null coverage;
- planted focus coefficients whose boundary moves monotonically with `k`;
- deterministic winner ties under frame-order scheduling changes;
- generalized-Anscombe synthetic covariance error `<=2e-5`;
- controls capable of producing both pass and fail;
- real correlated-band `nu_eff` coverage across preregistered warp phases, without relabelling `NU_SMOOTH=13.37469` as measured.

The synthetic scaling control commissions B6 arithmetic only. It does not apply or license B3.

### Width-match and select `k`

Run every grid value unchanged on all three development captures. A value survives width matching only if every applicable capture, band, and frozen ROI satisfies:

```text
abs(mean_n_eff_candidate/mean_n_eff_legacy_gate4.5 - 1) <= 0.05
```

Each survivor must then satisfy:

```text
detail or qualified-MTF lower95(candidate/legacy_gate4.5) >= 0.95
flat-power upper95(candidate/legacy_gate4.5)              <= 0.90
```

Flat power is integrated over 0.10–0.25 cyc/px. Select the smallest passing `k`.

Exactly one value must serve flat-on-ruler, coffee-bubbles, and 113MSDCF. Per-capture values, interpolation, a wider post-outcome grid, or replacement crops are failures, not repairs.

### Exact command and STOP result

Run:

```powershell
python experiments/PHASE1-DESIGN/reference.py --commission; python experiments/PHASE1-DESIGN/measure.py --gate
```

Both commands exit 0 only when one fixed global `k` passes all width and Pareto bars. `measure.py` must refuse stale or hash-mismatched commissioning artifacts.

If no common value exists:

1. write every arm and failed criterion;
2. print `NO_COMMON_K`;
3. return a distinct nonzero gate code;
4. report W1 as a successful negative;
5. stop W3 and phase-1 integration.

Do not tune around `NO_COMMON_K`.
