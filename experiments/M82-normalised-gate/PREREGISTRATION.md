# M82 — pre-registration: outcome-normalised gate

**Frozen before any M82 ladder, solved-gate confirmation, sharpness merge,
flat-control rescan, or portability score was run.**

**MEASURED disclosure.** This is not blind to the earlier corpus. M77 published
coarse gate ladders and its flat-contamination control; M81 published denser
ladders; M57 published the resolution instrument and its failures; and M70
published the wrapped-text sibling control. Those reports choose the design
below. No M82 outcome exists at the time of this commit.

## 0. Source corrections and question

**MEASURED.** The shipped path in `crates/strehl-core/src/merge.rs` elects the
maximum 17×17-regularised focus response, then admits the winner
unconditionally and every frame satisfying
`best - focus <= T * sqrt(2) * FOCUS_NOISE_SD`. The admitted native samples are
averaged arithmetically. `DEFAULT_GATE` is 4.0 and `FOCUS_NOISE_SD` is 0.015214.

**MEASURED.** M69 facts 17, 18 and 56 do not say that
`FOCUS_NOISE_SD` varies 4.06× across stacks. They report a 1.186× P2 per-stack
span, a 4.062× controlled texture-form span, and a 2.104× B3 per-stack span,
respectively. M81's scalar correction therefore tested a different and
narrower hypothesis than the one here.

**MEASURED.** M2 §3.2.3 reports 0.534× single-frame spatial noise for the plain
22-frame mean, 1.253× for naive argmax, and 0.981× for its shifted-winner
placebo. The 0.534× value is not a gated operating point.

**MEASURED.** M57's 0.496–0.740 px result used a fractional peak-height gate,
not the shipped absolute-noise gate. M64 §6.1 identifies the direction and unit
mismatch explicitly. M57's spectral method can compare new outputs, but its old
gate values cannot be transferred.

**MEASURED.** M70 P34 reports that the two wrapped-text captures' frame-domain
through-focus responses agree within 4.7% at every rung and that their spectral
counts agree within 2.4%. Owner question 48, folded as SYNTHESIS fact 848,
chooses one exposed noise-versus-sharpness continuum rather than two hidden
modes.

**ARGUED hypothesis H.** A request expressed as model-predicted merged sigma
relative to one frame has one meaning across stacks even when the raw gate does
not. H survives only if the sharpness price of a fixed request is portable,
first on the wrapped-text siblings and then across all five M77 stacks.

## 1. The coordinate

**ARGUED primary coordinate.** For gate `T`, use the shipped
`Estimator::mean_predicted_sigma_gain`:

```text
S(T) = mean_pixels(predicted merged sigma / predicted single-frame sigma).
```

This is the mean of the per-pixel ratios, not
`1 / sqrt(mean n_eff)`. The latter is Jensen-wrong when admission is spatially
heterogeneous. The registered requests are `S = 0.90`, `0.70`, and `0.50`;
`0.70` is the primary decision point. The other two rungs show the local shape
of any price list and are not substitutes for a failed primary result.

**ARGUED naming limit.** `S` is a **model-predicted sigma gain**, not measured
temporal noise. `selection_inflation` remains 1.0 in the shipped model, so no
result may shorten “model-predicted 0.70×” to “0.70× noise” or claim a
single-frame floor.

**ARGUED alternatives rejected.**

1. Mean `n_eff` loses the distribution and does not map to noise through
   `1/sqrt(mean n_eff)`.
2. `n_eff/N` additionally changes its meaning with bracket length.
3. M70's spectral `n_eff` is an information count; M70 §22.6 did not validate
   it as a hard-admission target.
4. Measured flat-ROI noise cannot define a whole-image knob because M77 fact 5
   found no qualifying flat ROI on three of five required stacks.

**DERIVED capability check.** Admission count is non-decreasing in `T`, so
`S(T)` is non-increasing. Gate 0 begins at the selector end and an open gate
approaches `1/sqrt(N)`. Every registered stack has `N >= 22`, so all three
requests lie above its full-mean endpoint. M81 §5 independently reports all six
15-rung admission ladders as non-decreasing and target-bracketing.

## 2. Locked data, ROIs and invocations

**MEASURED.** RAW inputs are read-only under `D:\personal\macro`, filename
sorted. The stack identities, counts, ISOs, subjects and original 256² plane
ROIs come from M77's committed ROI records and M81 pre-registration B2.

| stack / subject | N | ISO | M77 flat ROI | M77 detail ROI | role |
| --- | ---: | ---: | --- | --- | --- |
| `wrapped-text-1` / wrapped label text | 130 | 100 | `32,1312,256,256` | `2208,672,256,256` | sibling + five-stack |
| `wrapped-text-2` / wrapped label text | 120 | 400 | `32,672,256,256` | `3104,160,256,256` | sibling |
| `109MSDCF` / acrylic paint strokes | 22 | 160 | `1440,416,256,256` | `1952,1056,256,256` | five-stack |
| `coffee-bean` / coffee bean | 105 | 50 | `32,416,256,256` | `1312,416,256,256` | five-stack |
| `foam` / coffee foam | 100 | 1000 | `1312,288,256,256` | `160,1952,256,256` | five-stack |
| `bee-1` / bee anatomy | 299 | 100 | `2720,1568,256,256` | `1952,672,256,256` | five-stack |

**ARGUED sharpness ROIs.** M57 calibrated its spectral contrast on 512²
regions. Each M77 ROI is therefore expanded around its centre to 512² and
clamped to leave the exact 32-pixel extraction pad inside the 3514×2344 plane.
The coordinates are frozen here:

| stack | 512² flat ROI, run first | 512² detail ROI |
| --- | --- | --- |
| `wrapped-text-1` | `32,1184,512,512` | `2080,544,512,512` |
| `wrapped-text-2` | `32,544,512,512` | `2970,32,512,512` |
| `109MSDCF` | `1312,288,512,512` | `1824,928,512,512` |
| `coffee-bean` | `32,288,512,512` | `1184,288,512,512` |
| `foam` | `1184,160,512,512` | `32,1800,512,512` |
| `bee-1` | `2592,1440,512,512` | `1824,544,512,512` |

**ARGUED CLI flags.** The fresh ladder is exactly:

```text
--gate 0 0.25 0.5 1 2 4 8 16 24 32 40 48 64 96 128
```

The confirmation invocation supplies the three solved gates in request order
and the original M77 ROIs:

```powershell
strehl stack D:\personal\macro\<stack> `
  --gate <T_0.90> <T_0.70> <T_0.50> `
  --flat-roi <M77-flat> --detail-roi <M77-detail>
```

No `--limit`, `--stats`, `--stats-placebo`, `--srgb`, `--out`, or non-default
memory flag is used. The Python sharpness arm uses all sorted frames, a
32-plane-pixel pad, and even/odd filename-index halves.

## 3. Solving the requested outcome

**ARGUED solve.** For each request, locate adjacent positive ladder rungs
`(T0,S0)` and `(T1,S1)` with `S0 >= request >= S1`, then interpolate linearly
in log gate and log sigma gain:

```text
f = log(request / S0) / log(S1 / S0)
T = exp(log(T0) + f * log(T1 / T0)).
```

Extrapolation is forbidden. A confirmation run measures `S(T)`. Absolute error
must be at most 0.005. If it is larger, the confirmation point is added to the
bracket and the same interpolation is repeated, with at most two updates. Every
attempt remains in the log. Failure to confirm after two updates makes that
stack/request unreadable.

**ARGUED solver controls.**

1. Every measured `S(T)` ladder must be non-increasing.
2. All three requests must be bracketed without extrapolation.
3. Feeding a solved gate through its interpolation segment must reconstruct the
   request within 0.1%.
4. A synthetic power-law ladder must recover its analytic gate within 0.1%.
5. The confirmation must meet the 0.005 absolute bar.

## 4. Primary sharpness instrument

**ARGUED instrument choice.** Reuse M57's `dsig` method, but not its old
outputs or old fractional gate. For each stack and requested gate, independently
merge the even and odd frame halves through a source-level reproduction of the
current shipped focus field, 17×17 regulariser and absolute gate. Compare the
target pair against the gate-0 pair:

```text
C = dsig(RingStats(selector_even, selector_odd),
         RingStats(target_even, target_odd)).
```

Positive `C` means the requested outcome is blurrier than the selector by the
equivalent Gaussian sigma in pixels; negative means sharper. M57's frozen
settings remain unchanged: symmetric Hann, 64 rings, 16 angular sectors, and
`[0.05, 0.2762]` cycles/pixel. A non-positive common-power ring returns `NaN`
and remains `N/A`.

**MEASURED limitation carried forward.** M57 P5–P7 report a worst independent
noise-null displacement of 0.343 px and sector-jackknife errors that are
anti-conservative by 1.29–3.09×. M57's verdict says `dsig` is a research
contrast, not a shippable detail metric.

**ARGUED readability rule.** Multiply every jackknife standard error by the
worst measured factor, 3.09. A primary price is readable only if it is finite,
`abs(C) > 0.343 px`, and `abs(C) / (3.09 * se_jack) >= 2`. A smaller or
non-finite result is an abstention, not zero cost. The 512² flat ROI is run
first and reported beside the detail ROI; it never replaces or corrects the
detail value.

**ARGUED implementation validation.** The independent Python path must:

1. parse sensor and gate constants from current Rust source rather than retype
   them;
2. reproduce the private Rust CLI's whole-plane mean `n_eff` on
   `109MSDCF`, gate 2, within 1%;
3. reproduce each CLI confirmation row's 256² detail `raw rms` from the local
   full-stack merge within 1%;
4. report any raw container pin in a 512² sharpness ROI and make that row
   unreadable rather than silently differ from `fold_censored`.

M52 §4.1's independent implementation, which agrees with the shipped binary
within 0.09% on seven stacks, is the source template. It is not accepted as a
substitute for the fresh checks above.

## 5. Companion controls

**ARGUED M80 companion.** The confirmation CLI also runs M80's repaired,
cross-fitted resolved-detail statistic on the original M77 ROIs. `N/A / NO
TARGET` remains an abstention. A rise is not evidence of sharpness because M80
states that the statistic is one-sided against collapse.

**ARGUED flat-contamination control.** Recompute M77's all-frame
`max contamination < 1.10` precondition on every original 256² flat ROI,
including a fresh all-frame scan for `wrapped-text-2`. Any M80 row whose flat
precondition fails is labelled **UNREADABLE**, and its numerical sign cannot
enter the decision or a candidate fact. The primary `dsig` contrast does not
transfer a flat-derived noise scale, so the M77 failure does not silently veto
it; its own flat cell, null bound and readability rule do.

**ARGUED singleton control.** At every solved request report whole-plane mean
`n_eff`, `n_eff/N`, singleton percentage, boundary percentage and confirmed
model-predicted sigma gain. Any singleton percentage above zero is explicitly
unpriced selection exposure. It does not by itself answer H, but it forbids an
actual-noise floor claim.

**ARGUED curve control.** Within a stack, the central equivalent-blur price
should not fall as the requested sigma falls from 0.90 to 0.70 to 0.50. A
reversal is fatal only when the two conservative intervals
`C +/- 2 * 3.09 * se_jack` do not overlap; ordinary noisy crossings are
reported without promotion.

## 6. Frozen portability decision

**ARGUED sibling bar S.** At the primary 0.70 request, both wrapped-text detail
prices must be readable, positive, and satisfy
`max(C)/min(C) <= 1.50`. M70 P34's physical mismatch is only 4.7%; a 50%
allowance is deliberately more than ten times larger. A span above 1.50
refutes H on its easiest case.

**ARGUED five-stack bar F.** At the primary 0.70 request, all five M77 detail
prices must be readable, positive, and satisfy
`max(C)/min(C) <= 2.00`. A span above 2.00 refutes the portable-price-list
hypothesis. This is a product-scale tolerance, not an estimate of instrument
precision.

**ARGUED sign and abstention rules.**

- A readable positive price on one stack and readable negative price on another
  refutes a common positive price list.
- A `NaN`, unresolved value, failed merge validation, or inaccessible request
  yields **NO SHIP / NOT ESTABLISHED**, not a fabricated span.
- S or F failure yields **NO SHIP / REFUTED**.
- H survives only if S, F, all solver controls, and the curve control pass.
  Survival is not proof beyond these six captures.

**ARGUED product consequence.** Only a surviving result may add a production
solver. The proposed named requests are **detail** (`S = 0.90`) and **quiet**
(`S = 0.50`), always described as model-predicted. A failed or unresolved
result changes no production code.

## 7. Negative control, provenance and reporting

**ARGUED mutation control.** A Python byte-level mutation reverses the core
admission comparison from `gap <= tolerance` to `gap >= tolerance`. The
control must find exactly one byte sequence, write the mutation, verify it by
read-back, run an announced self-test that exits nonzero, and restore the source
byte-for-byte in `finally`. A zero-test success or failed restoration fails the
experiment.

**ARGUED provenance.** Build Rust 1.98.0 MSVC with Cargo located explicitly
under the user profile and a private M82 `CARGO_TARGET_DIR`. Record the source
commit, dirty-path audit, executable byte length and SHA-256, Python and package
versions, input evidence hashes, every command, timestamps and exit codes.

**ARGUED reporting rule.** Every result claim is labelled MEASURED, DERIVED or
ARGUED. Prior numbers retain their milestone namespace. Mechanism diagnostics
may report local admission-count quantiles and accepted frame-index distance,
but they cannot relax S or F after the result is visible.
