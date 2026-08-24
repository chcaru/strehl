# M98 — PRE-REGISTRATION

**Written and committed BEFORE any number in this milestone existed** (rule 12).
Nothing below was chosen after seeing a result. Where a later section of the
report departs from this document, the departure is stated in the report as a
departure, with the reason.

**HEAD at pre-registration:** `45ba18ba6ed71daa21802b9d45274ee49abe7892`
**Working tree at pre-registration is NOT clean.** Other agents hold uncommitted
edits to `crates/strehl-core/src/robust.rs` and four `crates/strehl-cli/examples/*`.
My binary is built from that tree. `robust.rs` is not on the default merge path;
I record the state so the build is attributable rather than assumed.

**Binary:** `.cargo-target-m98\release\strehl.exe`, `cargo build --release`,
own `CARGO_TARGET_DIR`.

---

## 0. The question, restated so it can fail

`DEFAULT_GATE = 4.0` (`merge.rs:297`). Two milestones disagree about what raising
the gate costs:

- **M85 / fact 1196:** gate 0 → gate 4 on `bee-3-cpl`, mean `n_eff` 1.000 → 60.860
  (61×), high-frequency amplitude on the eye facets **0.985×**, on the
  demosaic-free path **0.997×**; defocused background **0.151×**. Conclusion: the
  gate is nearly free.
- **M92 / fact 1245:** gate 0.99 vs gate 0.50, **−0.61753 px** (`112MSDCF`, 28.19σ),
  −0.31755 px (`wrapped-text-1`), −0.39077 px (`109MSDCF`), 66 of 70 ROIs.
  Conclusion: the near-selector is much sharper.

**Two things I assert about the two milestones, from reading their source, and
which I will re-verify in the report rather than leave as assertion:**

1. **They are not on the same axis.** `experiments/m57-shape-metric/src/m57lib.py:510`
   `merge_subset(..., gate=0.5)` computes `acc = cf >= (gate * peak)` — a
   **fractional peak-height** gate. The shipped gate (`merge.rs:319` `Gate::admits`)
   thresholds on `T * sqrt(2) * FOCUS_NOISE_SD`, in calibrated-noise units. M92's
   report calls 0.50 "the shipped gate"; the shipped gate is 4.0 on a different
   axis. `strehl stack --gate --help` already carries this caveat verbatim; fact
   1245's phrasing does not.
2. **M92's half-merges are unregistered.** `merge_subset` gathers `cube[idx]` with
   no warp. Alignment became default-ON in the shipped merge at `885e9f7`,
   *after* both milestones. Averaging more frames of an unregistered bracket
   blurs by the drift spread — a mechanism that reads exactly like a gate cost.

Both of those are *mechanisms that would produce M92's sign without the gate
being at fault*, and both are testable. They are hypotheses, not findings.

---

## 1. Hypotheses, pre-registered with falsifiers

| # | Hypothesis | What would falsify it |
|---|---|---|
| **H1** | M85's gate ladder was measured on unregistered frames, so part of the measured cost of raising the gate was misregistration. With alignment ON the sharpness-vs-gate curve is **flatter** (smaller cost per decade of `n_eff`) than with registration removed. | The aligned arm's gate contrast is **equal to or larger than** the FOV-matched unaligned arm's, on the top detail tercile, on `bee-3-cpl`. |
| **H2** | M92's −0.62 px is largely axis-mismatch plus missing registration. Measured on the **shipped** `--gate` axis with the **shipped binary** and alignment ON, the gate-0 → gate-4 edge-width contrast on `112MSDCF` is **smaller than 0.31 px** (half of M92's 0.61753). | It is ≥ 0.31 px. |
| **H3** | The gate's cost is **not one number**. Mean `n_eff` is a global average dominated by low-detail regions, so "61 frames averaged per pixel" does not describe what happens where detail lives: local `n_eff` in the top detail tercile at gate 4 is **below one third** of the global mean. | Top-tercile local `n_eff` at gate 4 ≥ ⅓ of the reported global mean `n_eff`. |
| **H4** | On a subject with **a priori known** structure (a millimetre ruler), raising the gate 0 → 4 costs **less than 10%** of the modulation at the tick-comb frequency. | Comb modulation falls by ≥ 10%. |

I expect to be wrong about at least one of these. H1 is the one I most expect to
survive; H4 is the one I have least basis for.

---

## 2. Stacks, arms and renders — fixed here

| stack | frames | role |
|---|---:|---|
| `D:\personal\macro\bee-3-cpl` | 299 | primary; M85's stack; the owner's photograph |
| `D:\personal\macro\112MSDCF` | 79 | M92's strongest cell (28.19σ); H2 |
| `D:\personal\macro\highly-angled-ruler-mm-cpl` | 299 | external ground-truth anchor (D2); **the aligner refuses it** (`align_cmd.rs:38` `TILTED_SUBJECTS`), so it renders unregistered by design |

**`D:\personal\macro` and `D:\macro-dark-frames` are read-only and are never
written to.** The shipped merge caches a solved sidecar at `<dir>/warpmap.txt`
(`align_cmd.rs:788`), which would be a write into the read-only tree. Every run
therefore operates on **copies** under `C:\dev\strehl-out\M98\frames\`, never on
the corpus directory.

**Gate ladder:** `T ∈ {0, 0.5, 1, 2, 4}` — M85's ladder exactly, so the two are
comparable row for row. `DEFAULT_GATE` is **not** modified; `--gate` is passed.

**Alignment arms.** Two, and the unaligned one is `STREHL_ALIGN=zoom`, **not**
`STREHL_ALIGN=0`: `zoom` is field-of-view- and resampler-matched, so the ROI
grids are co-located and magnification cannot read as sharpness (discipline 606,
and it fooled the orchestrator by eye tonight).

| arm | env | what differs |
|---|---|---|
| `ALN` | (default) | registration applied |
| `ZOOM` | `STREHL_ALIGN=zoom` | same FOV, same resampler, registration discarded |

**Half-merges.** Every metric here is a **cross-power between two renders with
independent noise**, because the gate changes the noise by ~6.6× and a
single-render band-power metric cannot tell signal from noise. Halves are
**parity splits** of the frame list (even index → half A, odd index → half B),
which is `m57lib.splits()`'s `parity` rule. Each half is aligned by its own
solve; the two solves are the same for every gate within an arm, so a common
decorrelation cancels in a gate *contrast*.

**Output file.** The **binned, linear, camera-native** default — the byte-frozen
measurement file. `--srgb` and `--demosaic` are used **only** for the owner-facing
artefact (D4) and **no number is measured on them** (M85 §5, `stack --help`).

---

## 3. Metrics — exact, with their failure direction (rule 18)

Everything is computed on the **green plane** `G = (G1+G2)/2` as emitted, over
512×512 ROIs, using `experiments/m57-shape-metric/src/m57lib.py` unmodified:
`RingStats(a, b)` (mean-removed, symmetric Hann, unnormalised `fft2`, 64 radial
rings, 16 angular sectors) and `dsig(rs1, rs2)`.

| symbol | definition | can be fooled by |
|---|---|---|
| `C_T(f)` | ring-mean real cross-power `Re(A·conj(B))` of the two half-merges at gate `T`. **Noise-free in expectation**: independent noise has zero mean cross-power. | *variance* of the cross-power biases `log C`; `m57lib`'s `c_var()` Jensen correction is applied by `dsig` and is the reason `dsig` is used rather than a bare log-ratio |
| `A_hf(T)` | `mean(C_T)` over `f ∈ [0.15, 0.2762]` cyc/px, band-integrated. **M85's quantity, made noise-free.** Reported as the ratio `A_hf(4)/A_hf(0)`. | rises if a merge *manufactures* correlated detail in both halves (e.g. a shared resampling ringing); admissible against collapse, inadmissible as proof of quality |
| `dsig(T_a → T_b)` | `m57lib.dsig(RingStats(a_Ta,b_Ta), RingStats(a_Tb,b_Tb))`, equivalent-Gaussian-blur difference in px over `f ∈ [0.05, 0.2762]`. **M92's quantity.** Positive = configuration 2 is blurrier. | returns `NaN` where the band has no signal; censoring rate is reported per stack, and a stack censoring > 25% of ROIs is reported as an instrument test, not a scene test (M92's ruling on `109MSDCF`) |
| `n_eff_loc(T)` | mean `n_eff` inside the ROI. Requires a per-pixel `n_eff` map. If the shipped binary does not emit one, `n_eff_loc` is dropped and H3 is tested with a `--flat-roi`/`--detail-roi` pair instead, and the substitution is declared. | — |
| `hp_sd` | sd of the ROI after a 3×3 Laplacian, on the **gate-0 `ALN`** render only, so the stratification map is fixed once and is not a function of the arm being compared (rule 17). | — |
| `sigma_flat` | sd of `(a − b)/2` on a ROI — the **temporal** noise of the merge, never a spatial sd (rule 10). | — |
| `M_comb` | ruler only: modulation at the tick-comb line, taken as the spectral peak within ±10% of the a-priori comb frequency **minus the median of the two adjacent sidebands**, so the local noise floor is removed. | a comb that is not resolved at any gate makes this inert — see the **inertness gate** below |

### Stratification (discipline 603), declared before the numbers

ROIs are split into **detail terciles by `hp_sd`** measured on the gate-0 `ALN`
render. Every headline is reported per tercile as well as pooled. **A conclusion
that holds on the top tercile and reverses on the bottom is reported as two
conclusions, not one.**

### ROI grid, defined procedurally so it cannot be chosen after the fact

24 ROIs of 512×512 on a 6×4 lattice: centre `(x,y) = (W(2i+1)/12, H(2j+1)/8)`
for `i ∈ 0..5`, `j ∈ 0..3`, clamped so the ROI lies inside the frame. `W, H` are
the emitted dimensions of that arm.

---

## 4. Controls, each with the input that makes it fail (rule 20, rule 39)

| # | control | bar, at an **exact** value | the input that makes it fail |
|---|---|---|---|
| **EQ** | Two invocations, identical arguments, identical frames → identical output. | **`100.000000%` of pixels equal** and SHA-256 equal. Not "~100%", not ">99.99%" (fact 1231). | **NC1** below |
| **NC1** | *The negative control made to go red.* Take the EQ pair and flip **exactly one** pixel of one file by **exactly 1 LSB**. | EQ must read **`99.999996%`** (1 changed pixel of `W·H·3`) and **RED**. If EQ still reads `100.000000%`, the comparison is not reading the file and every equality claim in this milestone is void. | by construction |
| **PC** | *Power control.* Plant a Gaussian blur of **σ = 0.30 px** into both halves of the gate-4 `ALN` render and re-measure `dsig(gate4 → gate4+blur)`. | recovered `dsig ∈ [0.25, 0.35] px`. | if it reads `< 0.25 px` the instrument cannot see an effect the size M92 reports, and **no null result in this milestone means anything**. Registered as fatal to the milestone, not to the gate. |
| **PL1** | *Placebo.* Re-render the same gate twice and measure `dsig` between the two pairs. | **exactly `0.000000` px**, and `A_hf` ratio exactly `1.000000`. | a non-zero reading means the instrument is reading run-to-run state, not sharpness |
| **PL2** | *Placebo.* Swap the half labels A↔B at every gate. | every `dsig` unchanged to **`< 1e-9` px**; `RingStats` is symmetric in its two arguments for the real cross-power, so any change is a bug in my harness | — |
| **FLAT** | *Rule 9, run FIRST, not as a closing check.* On the lowest-`hp_sd` ROI: `sigma_flat` must **fall** monotonically with gate, and `A_hf` must **not rise**. | `sigma_flat(4)/sigma_flat(0) ≤ 0.5`, and `A_hf(4)/A_hf(0) ≤ 1.05` on that ROI. | a metric that credits a defocused background with **gaining** detail is M38's defect and kills every number computed with it |
| **INERT** | *Rule 13 / rule 20 — can the stimulus express the failure?* Before any ruler number is read: the tick comb must be **visible above its own sidebands by ≥ 3×** in at least one gate. | `M_comb / sideband ≥ 3.0` at some gate | if no gate resolves the comb, the ruler measurement is **inert** and is reported as no evidence, not as a null |
| **AXIS** | Re-verify, on the shipped binary, that M92's `gate=0.50` is not the shipped gate: report the achieved `mean n_eff` at shipped `--gate 0.5` against M92's measured 4.66–6.71 at its own `gate=0.50`. | — | if they coincide the axis-mismatch claim is withdrawn |

`corpus_lint.py` must exit 0 before the milestone closes, run as its own call and
never chained to a commit (discipline 556).

---

## 5. Decision rule — the numbers, fixed in advance

The recommendation concerns `DEFAULT_GATE`. **I may not change it** (question 90 is
open and is the orchestrator's). I state a recommendation and the evidence.

All three read the **top detail tercile** of `bee-3-cpl`, arm `ALN`, and require
**PC, PL1, PL2, FLAT and NC1 all green**.

- **R-KEEP — "the shipped default is correct."**
  `A_hf(4)/A_hf(0) ≥ 0.95` **and** `|dsig(0 → 4)| ≤ 0.10 px`
  **and** `sigma_flat(4)/sigma_flat(0) ≤ 0.5`.
  0.10 px is one unit of fact 1243's corrected single-ROI real-dark null
  (0.08906–0.09442 px), so this says the gate's cost is at or under the noise
  floor of the sharpest instrument the project has.
  **This is the pre-registered outcome that exonerates the gate, and its failing
  value is `|dsig(0 → 4)| > 0.10 px` or `A_hf(4)/A_hf(0) < 0.95`.**

- **R-LOWER — "the default is too high."**
  `|dsig(0 → 4)| ≥ 0.20 px` (2 null units) at `|mean|/SE ≥ 3.0` across the
  tercile's ROIs, **and** a knee gate `T*` exists on the ladder with
  `|dsig(0 → T*)| ≤ 0.05 px` while `sigma_flat(T*)/sigma_flat(0) ≤ 0.5`.
  The recommendation is then `T*`, reported with what it costs in noise.

- **R-INCONCLUSIVE** — anything else, or any control red. Reported as such.
  **A clean negative result is an acceptable outcome and will not be dressed up.**

**Registered wrong predictions, to be scored in the report** (so that being wrong
is visible rather than quietly dropped):

| # | prediction |
|---|---|
| (a) | `dsig(0 → 4)` on `bee-3-cpl` `ALN`, top tercile, lands in `[0.00, 0.15]` px |
| (b) | the `ZOOM` arm's `dsig(0 → 4)` is at least 1.5× the `ALN` arm's |
| (c) | top-tercile local `n_eff` at gate 4 is under 20, against the global 60.86 |
| (d) | `A_hf(4)/A_hf(0)` reproduces M85's 0.985× to within ±0.03 on the `ZOOM` arm |
| (e) | the ruler comb survives gate 4 with ≥ 0.90 of its gate-0 modulation |

---

## 6. What I will not do

- Not change `DEFAULT_GATE`, `merge.rs`, `through_focus.rs`, `align.rs`,
  `warpmap.rs`, `robust.rs`, `noise.rs`, `profile.rs`, `merge_cmd.rs`,
  `align_cmd.rs`, `lib.rs` or `main.rs`.
- Not use whole-frame gradient-energy sharpness (Tenengrad) as a bar: it ranks a
  visibly-sharper registered render as 0.979× because misregistration
  manufactures gradient energy. Measured-blind on this rig.
- Not quote M57's S5/S6/S7 nulls on `109MSDCF` or `foam`: fact 1243 corrected
  the 0.34310 px bound to 0.089–0.094 px, and the old figure carried
  1.7587× too much injected noise from a hard-coded `ISO = 500` on an ISO-160
  stack.
- Not judge any pair of renders by eye without a field-of-view check.
