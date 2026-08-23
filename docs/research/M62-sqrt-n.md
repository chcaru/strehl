# M62 — The √N acceptance harness: a merge problem whose answer is arithmetic

**Verdict.** The harness works, it is calibrated across the whole range, and **it
fails selectors** — which is the only property that made it worth building. On a
30-frame static burst the shipped `strehl merge` reaches **5.4778× noise
reduction against an arithmetic truth of √30 = 5.4772** (+0.008 %), while the
shipped `strehl stack` selector scores **0.7690×** — a 1.30× noise *increase* —
and the same merge binary configured to admit exactly one frame scores
**0.9768×**. The separation between estimator and selector under this statistic
is **5.61×**. Under the invariant the CLI ships today it is **1.039×**.

**This is `strehl`'s first acceptance test with a known correct answer.**
Everything else in the corpus compares one merge against another, or against a
model. This compares a merge against arithmetic.

**Nothing here validates the sensor model.** Arm A's noise is drawn from the same
`g` and `RN_e` the merge gates with, so it measures the estimator's *efficiency*
and is circular with respect to the calibration (rule 34). Only the owner's real
§12 burst tests calibration. §8 says exactly which is which and why it matters.

Pre-registration: `experiments/M62-sqrt-n/PREREGISTRATION.md`, committed
**`906688c`**, before any arm was scored. Arm D's, `PREREGISTRATION-D.md`,
committed **`dea34ad`**, before Arm D was run. Both are quoted below and one of
them was violated; §7.3 says which and why.

Binary: `strehl` built from **`c37a790`** (HEAD at start of work), exported with
`git archive` into `experiments/M62-sqrt-n/build-head/`. The working tree did not
compile — another agent has `merge.rs` mid-edit — and I did not touch it (§11).

---

## 1. Why a static burst is different from every other capture in the corpus

In a focus stack every frame differs in **both** noise and focus, and separating
the two requires a model — which is the thing under test. In a **static repeat
burst** the focus never moves, so every frame is a sample of the *same* latent.
Two consequences follow, and they are the whole point:

- the true merged output **is the scene**, so truth is available; and
- the true noise reduction for an estimator that averages `N` samples is
  **exactly √N**, by arithmetic, not by estimate.

That gives a **pass mark that no one chose**. It also gives a zero point: a
selector that copies one frame's pixel achieves **1.0×**, because one sample is
one sample, no matter how cleverly it was picked. The gap between 1.0 and 5.4772
is the estimator/selector distinction made numerical.

**ARGUED.** No existing check in this corpus spans that gap. `M55b`'s battery is
about *detail*, not noise; `M24`'s drift work and fact 19's 0.534× are
merge-against-merge comparisons with no external truth. Discipline 250 records
three shipped checks that could not fail. §7 is the evidence that this is not a
fourth.

---

## 2. What was built

`experiments/M62-sqrt-n/`, Python driving the shipped Rust CLI. No crate file was
modified.

| file | what it is |
| --- | --- |
| `src/dngwrite.py` | a minimal uncompressed CFA DNG writer. The CLI selects a decoder by file *content* but requires a `.arw` extension, so the harness writes DNG bytes into `.arw` names. This is what made "use the shipped CLI" possible at all |
| `src/harness.py` | constants (parsed out of the crate, never retyped), burst generation, the truth-referenced statistic, block bootstrap, CLI runner |
| `src/01-pick-latent.py` | picks the latent frame and crop |
| `src/02-fidelity.py` | three fidelity checks run **before** any result was believed |
| `src/04-arms.py` | the deciding run: A0, A1, B1a, B1b, B2, B3, three seeds |
| `src/05-trap-audit.py` | the shared-noise prediction checked against the CLI's own printed instrument |
| `src/06-armD.py` | Arm D — the same harness on real sensor noise |
| `src/07-real-burst.py` | **Arm C — the real-capture path. Written; the real branch is not run because no real burst exists.** `--smoke` exercises the identical code |
| `src/08-flat-selector.py` | the selector penalty measured against scene structure |
| `src/09-diagnostic-hash.py` | rule 26 — the `--flat-roi` diagnostic proved not to perturb the output, by hash |

`out/*.json` and `out/*.log` hold every number and every CLI transcript quoted
below. `build-head/` and `data/` are gitignored; §12 says how to regenerate them.

---

## 3. The plant, and the constants — read from the crate, not retyped

**Latent.** `D:\personal\macro\109MSDCF\DSC00020.ARW`, frame 11 of 22, ISO 160,
17 May — **before** the 25 May circular polariser of fact 845. A 2048×2048
RGGB-phased crop at (y=1024, x=4096). Chosen by a rule fixed in advance: maximise
texture subject to mid-tone and unclipped. Max 2731 DN against white 15360;
**zero saturated pixels**. Binned green sits at **1229.90 DN of signal**
(MEASURED, `out/01-latent-provenance.json`).

The corpus file count was asserted against `AGENTS.md`'s table before anything
was computed — 22/79/63/33/105/19/100/299/299/299/130/120 = **1568** `.ARW`, and
242 darks in 11 groups of 22 (MEASURED). Discipline 388 exists because a glob
over a missing directory returns zero files and raises nothing.

**Constants.** `harness.constants()` parses them at run time from the built
tree's `crates/strehl-core/src/profile.rs`, `const A7C2: CameraProfile`:

| constant | value | source |
| --- | --- | --- |
| `gain_divisor` | 436.8 | `profile.rs:229` |
| `base_iso` | 100.0 | `profile.rs:230` |
| `read_noise_e_low` | 4.20 | `profile.rs:231` |
| `read_noise_e_high` | 1.2392 | `profile.rs:232` |
| `second_base_iso` | 400.0 | `profile.rs:233` |
| black / white | 512 / 15360 | `noise.rs`, asserted present at parse time |

At ISO 160: `g = max(160, 100)/436.8 = 0.36630037` DN/e, `RN_e = 4.20 e` (160 <
400), `RN·g = 1.53846` DN, so **`σ²(S) = 0.36630037·S + 2.36686` DN²** (DERIVED).
Binned green over the ROI: **σ = 15.0479 DN** (DERIVED).

**Independent confirmation the parse is right:** the CLI, computing from its own
compiled constants, printed `model predicts : sigma 15.048 DN` at `mean 1229.91
DN` against the harness's 15.04793 DN at 1229.902 DN (MEASURED,
`out/04-merge-s0-g8.0.log`). Two code paths, five digits.

**Facts 783–808 cannot bite here.** The 2.174× dark-signal step at ISO 400 is a
labelling failure in the gain/read-noise split, not an arithmetic error, and it
moves **no DN-domain prediction**. Every number in this report is in DN, and the
plant is at ISO 160, below `second_base_iso` in any case. Stated explicitly
rather than assumed away.

**Everything is per CFA plane.** R at (even, even), G1 at (even, odd), G2 at
(odd, even), B at (odd, odd), matching `CfaPlane::rggb_offset`. The scored
quantity is binned green `(G1+G2)/2` in raw DN, exactly what
`Estimator::green_mean` produces. Arm D additionally reports all four planes
separately.

### 3.1 Fidelity, checked before anything was believed

| check | result |
| --- | --- |
| **F1** CLI decode round-trip: `merge --limit 1` vs the written array | max abs **0.1133 DN**, exactly **half** the TIFF quantisation step (0.22657 DN); RMS 0.0654 = step/√12. MEASURED |
| **F2** the CLI read the plant as intended | `iso: 160`, `PROVENANCE=Profile` — not the fallback model. MEASURED |
| **F3** does the burst carry the σ it was told to? | empirical pooled temporal RMS **18.7046 DN** vs model **18.7002 DN**, ratio **1.00024**. MEASURED |
| **F4** does the `--flat-roi` diagnostic perturb the merged output? | **byte-identical SHA-256** with it on and off, at gate 0 *and* gate 16 (rule 26). MEASURED, `out/09-diagnostic-hash.json` |

Had F1 failed, nothing downstream would have run. `out/02-fidelity.json`.

---

## 4. The shared-noise trap, and why it does not touch this statistic

The latent is a real frame, so `L = T + η`: the noise-free scene plus **one
frozen realisation** of sensor noise. All `N` synthetic frames carry that same
`η`, and a shared term does not average away.

**I took option (b): keep it, and do the algebra.** The resolution is a choice of
reference. Score against **`L`**, the latent as defined — not against `T`:

```
Y_i − L  =  ε_i                        Var = v
Ô  − L  =  (1/n) Σ_{i∈A} ε_i           Var = v/n
```

`η` appears in **neither** residual. It is inside the definition of truth, so it
cancels **identically**, not approximately. The expected ratio of pooled RMS
residuals is **exactly √N** — no ceiling, no correction term. (DERIVED.)

The trap is real and it lands on **every other reference choice**:

| reference | expected ratio at N=30 |
| --- | --- |
| `L`, the defined latent — **this harness** | **√30 = 5.4772** |
| `T`, the noise-free scene | `√[(v_T+v)/(v_T+v/N)] = √(2N/(N+1))` = **1.3912** |
| box high-pass sd on a flat ROI — **the invariant the CLI ships** | `√[(h²+G²v)/(h²+G²v/N)]` ≤ **1.3912** |

with `G = 0.99381 = √(1−1/81)` (`flat_ratio.rs::HP_NOISE_GAIN`) and `h` the
high-passed true scene. **A merge achieving 5.4772 would be scored 1.39 or less
by a truth-free statistic.** That is a fact about instruments, not about merges,
and it is the reason this harness needed building.

### 4.1 The prediction, and the CLI's own instrument agreeing with it

Pre-registered at `906688c` §3, from the latent's measured high-pass sd
(59.9909 DN) and the model variance: the CLI's flat-ROI invariant would read
**1.0295** on a merge in fact achieving 5.4772.

**Convention flip, stated rather than performed quietly:** the pre-registered
1.0295 is a *reduction factor* (reference ÷ merged). **The CLI prints the
reciprocal** (merged ÷ reference, lower is better). `1/1.0295 = 0.97131`.

| quantity | predicted | CLI printed | agreement |
| --- | --- | --- | --- |
| reference high-pass sd | 61.8268 DN | **61.827** | 0.0003 % |
| merged high-pass sd (N=30) | 60.0530 DN | **60.056** | 0.005 % |
| the printed ratio | 0.97131 | **0.971** | 0.03 % |

MEASURED, `out/05-trap-audit.json`, `out/04-merge-s0-g8.0.log`. The algebra
predicted the shipped instrument's reading to three significant figures before
the run.

### 4.2 A refinement the pre-registration did not anticipate

On this crop the compression of the high-pass statistic is dominated by **scene
structure**, not by the frozen `η`. The CLI itself prints the diagnostic:
`STRUCTURE FLOOR: median hp sd is 4.1343× the model's per-sample sigma` — that
is `hp_sd / (HP_NOISE_GAIN · model_sigma)`, `flat_ratio.rs:216`.

Decomposing `hp_L² = h² + G²·v_T` gives `h² = 3598.9 − 223.6 = 3375.3`
(DERIVED). On a **real** burst of the same crop — no shared `η` — the same
statistic would read `√(3598.9/3382.8) = 1.0315` (CLI 0.9695) against the
1.0295/0.9713 measured here.

**So the frozen-`η` trap is severe on a genuinely flat ROI (1.3912 against
5.4772, a 3.94× cost) and nearly invisible on a textured one (0.2 %).** Both
halves belong in the record: the trap was worth handling and, on this plant, it
was not what limited the instrument. Structure was.

---

## 5. The statistic

Pooled mean-square residual against `L`, merged over **all** `N` frames in the
denominator — never one privileged frame, because fact 441 measured a 1.60×
swing from that choice.

```
R = sqrt( mean_pixels mean_frames (Y_i − L)² / mean_pixels (Ô − L)² )
```

ROI: the plane interior inset 32 px (selection window radius 13, regulariser
radius 8, so 21 would suffice), giving **944×944 = 891 136 plane pixels**.
Uncertainty is a **64×64 block bootstrap, 2000 draws**, plus the spread over
**three independent noise seeds** reported beside it.

Only **green** is scored. `write_merged` encodes `clamp((raw−black)·gain/range,
0, 1)` with white balance applied (R ×2.861, B ×1.482); green's gain is exactly
1.0, so green and only green inverts cleanly back to raw DN.

---

## 6. Arm A — the estimator, and the ladder

### 6.1 Pre-registered (`906688c` §4)

> **A0-k** — Python mean of the first `k` frames, `k ∈ {1,2,3,5,10,20,30}` —
> **exactly √k**: 1.0000, 1.4142, 1.7321, 2.2361, 3.1623, 4.4721, 5.4772.
> **A1-t** — `strehl merge` at gate `t` — `≤ √(mean n_eff)` printed by the same
> run, and `→ 5.4772` as `n_eff → 30`.

### 6.2 Measured

`out/04-arms.json`. Three seeds, N=30. "sd" is between-seed; "SE" is the block
bootstrap on seed 0.

| arm | expected | measured | sd | SE | error |
| --- | --- | --- | --- | --- | --- |
| A0-1 | 1.0000 | 1.00069 | 0.00139 | 0.00089 | +0.069 % |
| A0-2 | 1.41421 | 1.41524 | 0.00056 | 0.00125 | +0.072 % |
| A0-3 | 1.73205 | 1.73266 | 0.00136 | 0.00167 | +0.035 % |
| A0-5 | 2.23607 | 2.23788 | 0.00198 | 0.00209 | +0.081 % |
| A0-10 | 3.16228 | 3.16320 | 0.00210 | 0.00258 | +0.029 % |
| A0-20 | 4.47214 | 4.47232 | 0.00256 | 0.00394 | +0.004 % |
| **A0-30** | **5.47723** | **5.47913** | 0.00674 | 0.00440 | +0.035 % |

**The harness is calibrated across the whole range, not merely able to tell two
extremes apart** (MEASURED). Worst rung is 0.081 % off; the pre-registered
tolerance was 1 %.

`strehl merge`, the shipped estimator, gate ladder:

| gate | measured `R` | mean `n_eff` | `√(mean n_eff)` | efficiency | `n_eff=1` % | CLI hp ratio |
| --- | --- | --- | --- | --- | --- | --- |
| 0.0 | 0.97682 | 1.000 | 1.0000 | 0.9773 | 100.00 % | 1.009 |
| 0.5 | 1.35937 | 2.966 | 1.7222 | 0.7906 | 26.50 % | 0.993 |
| 1.0 | 1.96845 | 6.804 | 2.6084 | 0.7556 | 5.69 % | 0.983 |
| 2.0 | 3.77637 | 18.434 | 4.2935 | 0.8760 | 0.20 % | 0.975 |
| 4.0 | 5.43162 | 29.539 | 5.4350 | 1.0001 | 0.00 % | 0.971 |
| **8.0** | **5.47768 ± 0.0044** | 30.000 | 5.4772 | **1.0014** | 0.00 % | 0.971 |
| 16.0 | 5.47768 ± 0.0044 | 30.000 | 5.4772 | 1.0014 | 0.00 % | 0.971 |

**P1 (MEASURED).** Given a static burst of 30 frames and a gate that admits all
of them, `strehl merge` at `c37a790` achieves **5.4778× noise reduction against
an arithmetic truth of 5.4772**, +0.008 %, block-bootstrap SE 0.0044,
between-seed sd 0.0067. **The merge is an estimator, at the arithmetic limit,
when the gate lets it be one.**

**P2 (MEASURED).** The 0.026 % shortfall of the CLI merge (5.47768) against the
pure Python mean (5.47913) is **entirely TIFF output quantisation**: merged
residual sd 15.048/√30 = 2.7474 DN, quantisation sd 0.06540 DN, predicted ratio
`1/√(1+q²/σ²) = 0.999717` against a measured 0.999735 (`out/05-trap-audit.json`).
The merge itself loses nothing.

**P3 (MEASURED).** The CLI's own model-based prediction at gate 8, `pred sigma
gain 0.1826×`, matches the truth-referenced `1/5.47768 = 0.18256×` to 0.02 %.
Its self-report is honest *on data drawn from its own model* — which is exactly
the circularity §8 is about.

---

## 7. Arm B — the negative control. **This is the harness's power.**

### 7.1 Pre-registered (`906688c` §4–5)

> **B1a** constant selector (copy frame 0) — **exactly 1.0000**.
> **B1b** random per-pixel selector — **exactly 1.0000**.
> **B2** `strehl stack`, the shipped unregularised argmax — **≤ 1.0**.
> **B3** `strehl merge --gate 0`, the shipped estimator configured as a selector
> — **≤ 1.0**.
>
> The harness is **BROKEN** if: B1a/B1b outside 1.0000 ± 0.005; **B2 or B3 ≥
> 1.05**; any A0-k off √k by more than 1 %; A1 above √(mean n_eff) by more than
> the bootstrap SE. *"Failure of 1, 2 or 3 is reported as the finding, in the
> headline, ahead of any number about the merge."*

### 7.2 Measured — the selector scores

| arm | what it is | expected | **measured** | sd | SE |
| --- | --- | --- | --- | --- | --- |
| **B2** | **`strehl stack` — the shipped argmax selector** | ≤ 1.0 | **0.76903** | 0.00022 | 0.01205 |
| **B3** | **`strehl merge --gate 0` — same binary, one frame admitted** | ≤ 1.0 | **0.97682** | 0.00066 | 0.00089 |
| B1a | copy frame 0 everywhere | 1.0000 | 1.00069 | 0.00139 | 0.00089 |
| B1b | random frame per pixel | 1.0000 | 0.99961 | 0.00062 | 0.00088 |
| **B4** | `merge --gate 0` on a **structure-free** field | ≤ 1.0 | **0.95162** | 0.00058 | 0.00060 |

**B4 was not pre-registered.** It was added *after* Arm D tripped its bound, to
turn an explanation into a measurement. It is post-hoc and is labelled so
wherever it is used; it tests a mechanism, not the headline, and no number in
§6 or §7.2's first four rows depends on it.

**Every pre-registered break criterion passed. None tripped.** The harness is not
a fourth un-failable check.

**P4 (MEASURED).** `strehl stack` — the merge path the project's thesis calls a
selector — scores **0.7690×** on a problem where the correct answer is 5.4772×.
It does not merely fail to reduce noise; it **increases** it by **1.300×**, and
the three seeds agree to 0.0002. Handed thirty samples of the same scene, the
shipped selector returns an image noisier than any one of them.

**P5 (MEASURED).** The strongest control is one parameter of one binary. `strehl
merge --gate 0` sets `tolerance = 0·√2·FOCUS_NOISE_SD = 0`, and `Gate::admits`
(`best − focus ≤ tolerance`) then admits **only the winner**: the CLI itself
prints `mean n_eff 1.000, n_eff=1 100.00%`. Same code, same crop, same frames —
**0.9768 as a selector, 5.4778 as an estimator, a 5.61× separation.** No
re-implementation, no straw man.

**P6 (MEASURED).** Trivial selectors land on the arithmetic zero point: 1.00069
and 0.99961, both inside the pre-registered ±0.005. The statistic's zero is
where arithmetic says it is.

**P7 (MEASURED).** The selector penalty is ordered by how much scene structure
the argmax has to work with, and the order is monotone:

| latent | structure floor | `merge --gate 0` | noise penalty |
| --- | --- | --- | --- |
| textured crop (Arm A) | 4.13× model σ | 0.97682 | 1.0237× |
| **constant field, zero structure (B4)** | 1.0 | **0.95162** | **1.0508×** |
| real dark field (Arm D) | ~1.0 | **0.92772** | **1.0779×** |

The mechanism: the argmax returns the frame with the largest regularised focus
response, and that response is structure plus noise. Where structure decides the
winner, the pick is nearly independent of the pixel's noise; where structure is
absent, **the noise decides the winner**, so the selector systematically returns
the sample whose noise pointed the right way. B4 removes structure and nothing
else, and the penalty **doubles** — 2.37 % → 5.08 % (MEASURED). The dark field's
further excess (7.79 %) is ARGUED to be the deliberate σ mismatch of §9.

**P8 (MEASURED, cross-check).** Regularisation costs the selector ~10× less than
no regularisation: 1.0238× (`merge --gate 0`) against 1.3004× (`strehl stack`).
Rule 4 records raw argmax at 1.95–2.61× single-frame noise; this is the same
direction and comparable ground, but a **different operator and a different
statistic**, so it is reported as *consistent with*, not as *equal to*.

### 7.3 The dynamic-range argument, which is the case for the capture

**P9 (MEASURED).** Selector against estimator, same data, same merges:

| statistic | selector | estimator | **separation** |
| --- | --- | --- | --- |
| the invariant `strehl merge` ships today (flat-ROI high-pass) | 1.009 | 0.971 | **1.039×**, i.e. 3.9 % |
| **this harness (truth-referenced)** | 0.9768 | 5.4778 | **5.61×** |

A 3.9 % separation is inside the range where drift, ROI choice and structure
argue about the answer. A 5.61× separation is not. **ARGUED:** this is why the
static burst is worth a capture slot — it is the only configuration in which the
project's central claim about itself becomes a measurement with a 5.6× lever
instead of a 4 % one.

### 7.4 What the harness cannot separate, stated because it matters

The pooled-RMS ratio is `1/√(E[1/n])`. The CLI prints `E[n]` (`mean n_eff`) and
`E[1/√n]` (`mean_predicted_sigma_gain`, `merge.rs:920`) but **not** `E[1/n]`, and
Jensen makes both printed quantities loose bounds. Consequently:

- **gate 0**: `n ≡ 1` exactly, so `E[1/n] = 1` and the no-bias value is exactly
  1.0000. The whole 2.32 % ± 0.07 % shortfall is **selection bias**, isolated
  (DERIVED from MEASURED).
- **gate ≥ 8**: `n ≡ 30`, no selection at all, no-bias value √30, efficiency
  1.0014 — **no bias** (MEASURED).
- **intermediate gates**: the 0.76–0.88 efficiency deficit is Jensen *and*
  selection bias mixed, and **this harness cannot separate them.**

**P10 (ARGUED, actionable).** To make the intermediate gates diagnosable the
merge should emit `E[1/n]` — or the per-pixel `n_eff` map — alongside the
existing `mean n_eff`. One extra accumulator turns an unresolvable deficit into
two named terms. I did not implement it: `merge.rs` is another agent's.

---

## 8. Arm C — what the real capture tests that Arm A cannot

**This is the sentence the rest of the report exists to support.**

> **Arm A's noise is generated from the same `g` and `RN_e` the estimator gates
> with, so it measures the estimator's *efficiency* and is *circular with respect
> to the model's calibration* — it cannot validate the sensor model. The real
> burst's noise comes from the sensor, so it tests *calibration*: whether the
> measured `g` and read noise actually describe reality at working exposure.**

Concretely, and stated as limits rather than caveats:

| question | Arm A | real §12 burst |
| --- | --- | --- |
| does the merge average what it admits? | **yes** — 5.4778 vs 5.4772 | yes |
| is the gate ladder calibrated? | **yes** | yes |
| does a selector fail this test? | **yes** — 0.7690 | yes |
| is `σ²(S) = g·S + (RN·g)²` true of the sensor at 1/8–2.5 s? | **no. Assumed, then recovered.** | **yes** |
| is `g = 0.36630` DN/e right at working exposure? | **no** — it is the input | **yes** |
| how many defects exist at working exposure? | **no** — synthetic noise has none | **yes** |
| is the sensor's noise independent frame to frame? | **no** — drawn independent by construction | yes (and Arm D, §9) |

Rule 34 is not escapable by care here. It is escapable only by a different
capture.

### 8.1 The path, written and not run

`src/07-real-burst.py`. The real branch requires a burst that does not exist; the
`--smoke` branch runs the identical code over a synthetic Arm A burst and **is**
run, so the path is demonstrated to execute rather than asserted to.

```
python src/07-real-burst.py D:\personal\macro\<burst-dir> --n 30
```

Three measurements, of which only the first is one Arm A can also make:

- **C1 — noise reduction against held-out truth.** A real burst has no known `L`,
  so truth must be the mean of a held-out half, which carries `v/M` of its own
  noise; the statistic subtracts it, and the TIFF quantisation term, explicitly.
  Expected **√(N/2) = √15 = 3.8730**.
- **C2 — in-situ photon transfer at working exposure.** The static burst gives a
  per-pixel temporal variance and a per-pixel mean over a scene spanning a real
  signal range, with fixed-pattern noise, defects and structure all held
  constant. So `var = g·S + (RN·g)²` can be **regressed**, per plane, in DN. This
  is the measurement that closes fact 808: the shipped `g` and read noise were
  fitted at 1/100 s in the dark, and this checks them at 1/8–2.5 s on a scene.
- **C3 — defect census at working exposure.** Pixels whose temporal variance
  exceeds the model, per plane — the population fact 808 says the 1/100 s dark
  map misses (~5 of ~839). Reported per plane because of the 68× odd/even
  asymmetry (R 101, G1 98, G2 7757, B 5674).

### 8.2 Smoke result — the fitter recovers a known answer

`out/07-armC-smoke.json`, N=30 synthetic, ISO 160. **Circular by construction and
labelled so**: on synthetic data the fitter *must* recover `g` and `RN`, because
`g` and `RN` generated the data. Its value is that a fitter which cannot recover
a known answer cannot be trusted with an unknown one.

| plane | `ĝ/g` | `R̂N·g / RN·g` | `R̂N_e` (profile: 4.20) |
| --- | --- | --- | --- |
| R | 0.99953 | 0.99923 | 4.199 |
| G1 | 0.99970 | 0.96801 | 4.067 |
| G2 | 1.00019 | 0.95718 | 4.019 |
| B | 0.99908 | 0.98540 | 4.142 |

**P11 (MEASURED).** The photon-transfer fitter recovers a known gain to within
**0.2 %** and a known read noise to within **4.3 %** from 30 frames over a
37–2086 DN signal span. The read-noise intercept is the weaker of the two, as
expected from extrapolating to `S = 0`; **ARGUED:** the real burst should be shot
with as much shadow as the frame allows, or the intercept will be the loose term.

**P12 (MEASURED).** C1's held-out-truth variant — the only variant a real burst
can use — is calibrated: **3.8701 against √15 = 3.8730**, −0.075 %, with the
Python ladder at 0.99979 / 1.41353 / 2.23565 / 3.87004 for k = 1/2/5/15. The
`v/M` and quantisation corrections are correct.

**P13 (MEASURED, null).** C3 finds **zero** excess-variance pixels in 921 600 per
plane on synthetic data, median `var/model` 0.978. Synthetic noise has no
defects, so the census does not manufacture them.

---

## 9. Arm D — the same harness on noise the sensor actually made

**The corpus already contains real static repeat bursts.** `D:\macro-dark-frames`
is 11 ISO groups of 22 frames; within a group nothing moves and nothing
refocuses. The latent is the dark field and the exposure is 1/100 s — so this is
**not** the §12 capture and **does not** close fact 808 — but the noise is the
sensor's, not the model's.

Group `118MSDCF`, **ISO 100** (`base_iso`, low-gain mode, so `read_noise_e_low`
governs and no part of facts 783–808 is in play). First 2 frames discarded; set
**A** = 10 merged, set **B** = 10 held-out truth. Pre-registered at `dea34ad`.

**P14 (MEASURED).** The latent is static: per-frame mean over the crop spans
**0.079 DN** across 20 frames with a slope of 0.0015 DN/frame, against a
per-sample σ near 1 DN. No dark-current drift.

**P15 (MEASURED).** On real sensor noise the ideal mean reaches √N, per plane:

| plane | temporal σ (DN) | model `RN·g` | measured/model | **D1-10** vs √10 = 3.16228 |
| --- | --- | --- | --- | --- |
| R | 1.00643 | 0.96154 | 1.047 | 3.19412 (+1.01 %) |
| G1 | 0.99346 | 0.96154 | 1.033 | 3.16561 (+0.11 %) |
| G2 | 0.99905 | 0.96154 | 1.039 | 3.13826 (−0.76 %) |
| B | 0.91900 | 0.96154 | 0.956 | 3.18786 (+0.81 %) |
| green | 0.72959 | 0.67991 | 1.073 | 3.15696 (−0.17 %) |

**The sensor's temporal noise is independent frame to frame** to within 1 %.
Correlated read-out, supply ripple or dark-current drift would have shown here
and Arm A is structurally incapable of showing it, because Arm A's noise is drawn
independent by construction.

**P16 (MEASURED, replication).** The four-plane mean dark σ is **0.9795 DN**
against M4 §8.2's 0.9845–0.9866 DN at ISO 50/100 — an independent replication
through a different code path, 0.5–0.7 % apart. The profile's `RN·g = 0.96154 DN`
is **2–5 % low** for R/G1/G2 and **4 % high** for B. The raw data's own 1 DN
quantisation contributes up to 1/12 DN² of the measured variance and biases these
ratios upward; the direction of the correction is down.

**P17 (MEASURED, new).** G1 and G2 are **temporally correlated within a frame**:
`var(green) = 0.53229` against `(var G1 + var G2)/4 = 0.49626` if independent, so
`cov = 0.0721` and **ρ = +0.073**. This is why green's measured/model ratio
(1.073) exceeds its planes' (1.033, 1.039). It does **not** damage √N averaging —
spatial correlation of temporally independent noise still averages down, and
D1-10 on green confirms it at −0.17 %. **ARGUED:** it does mean that any
noise-propagation algebra treating the two greens as independent will
underestimate green-luma variance by about 7 %.

**P18 (MEASURED).** G2 is the low rung of the ladder (−0.76 %, the only negative
of the four planes) — the plane carrying 7757 of the corpus's defects against
G1's 98. Consistent with the 68× odd/even architectural asymmetry; too small a
deviation to be more than a flag.

**P19 (MEASURED).** The shipped merge on real sensor noise: **`--gate 16` scores
3.1375 against √10 = 3.1623** (−0.79 %), with the CLI reporting `mean n_eff
10.000, pred sigma gain 0.3162×`. **`--gate 0` scores 0.9277** — the selector
fails on real noise too, harder than on synthetic.

### 9.1 A pre-registration violation, disclosed

`PREREGISTRATION-D.md` declared Arm D broken if **`D2-g0` fell outside 1.00 ±
0.05**. It measured **0.9277**. **The criterion tripped.**

It is reported as a **mis-specified criterion, not a broken harness**, and the
reasoning is available for the reader to reject:

1. The direction is the safe one. A broken harness reports *noise reduction* for
   a selector; this reports a 7.8 % *penalty*. The failure mode the criterion
   existed to catch is the opposite sign.
2. The bound was written for a scene and applied to a **dark field**, where there
   is no structure and the argmax is therefore decided entirely by noise. §7.2's
   B4 — run afterwards, for this reason, and labelled post-hoc — measures exactly
   that effect in isolation: remove structure from a synthetic latent and the
   penalty goes 2.37 % → 5.08 %. **±0.05 was never wide enough for a structureless
   latent**, and that is a defect in my criterion, written before I had thought
   about what "structure" does to an argmax.
3. The remaining gap (5.08 % → 7.79 %) is **ARGUED** to be the deliberate σ
   mismatch below, and is not separately measured.

**Disclosed deliberate mismatch.** `write_merged` encodes `(raw−black).max(0)`,
and a dark frame sits *on* black, so half its samples would clamp to zero. Arm D
adds a **constant +1230 DN pedestal**, identical in every frame, which moves no
temporal statistic. It puts the level where the profile predicts a green-luma σ
of **15.05 DN** against a sensor delivering **0.68 DN** — a **22× overstatement**
that makes the gate admit everything. This is *not* a calibration test; it is
what a merge looks like when the calibration is 22× wrong, and it is the reason
Arm D's `--gate 16` number is quoted with its mechanism attached.

**Asymmetry worth flagging (ARGUED):** `roi_green` (single frame, via
`plane.rs::green_luma`) clamps at black while `roi_green_merged`
(`merge_cmd.rs:346`) does not. On near-black data the CLI's own single-frame and
merged ROI statistics are not computed on the same footing.

---

## 10. Claim ledger

| # | claim | label |
| --- | --- | --- |
| P1 | merge reaches 5.4778 against √30 = 5.4772 at gate ≥ 8 | MEASURED |
| P2 | the 0.026 % CLI/Python gap is TIFF quantisation, predicted 0.999717 vs measured 0.999735 | MEASURED |
| P3 | the CLI's own `pred sigma gain` matches truth to 0.02 % on its own model's data | MEASURED |
| P4 | `strehl stack` scores 0.7690 — a 1.300× noise increase | MEASURED |
| P5 | `merge --gate 0` is a pure selector (`n_eff ≡ 1`) and scores 0.9768; separation 5.61× | MEASURED |
| P6 | trivial selectors land at 1.00069 / 0.99961 | MEASURED |
| P7 | the selector penalty is ordered by scene structure: 2.37 % / 5.08 % / 7.79 % | MEASURED (B4 arm is **post-hoc**) |
| P8 | regularisation cuts the selector penalty ~10× (1.0238× vs 1.3004×) | MEASURED |
| P9 | the shipped flat-ROI invariant separates selector from estimator by 1.039×; this harness by 5.61× | MEASURED |
| P10 | the merge should emit `E[1/n]`; without it, intermediate gates cannot be diagnosed | ARGUED |
| P11 | the PTC fitter recovers a known `g` to 0.2 %, known `RN` to 4.3 % | MEASURED |
| P12 | the held-out-truth variant is calibrated: 3.8701 vs √15 = 3.8730 | MEASURED |
| P13 | the defect census returns zero on synthetic data | MEASURED |
| P14 | the dark group's latent is static to 0.079 DN over 20 frames | MEASURED |
| P15 | real sensor noise averages as √N to within 1 % on all four planes | MEASURED |
| P16 | dark σ replicates M4 to 0.5–0.7 %; the profile's `RN·g` is 2–5 % low on R/G1/G2, 4 % high on B | MEASURED |
| P17 | G1 and G2 are temporally correlated within a frame, ρ = +0.073 | MEASURED (ρ DERIVED from measured variances) |
| P18 | G2 is the low rung of the real ladder, consistent with the odd/even defect asymmetry | MEASURED |
| P19 | on real noise, merge scores 3.1375 vs √10; the selector scores 0.9277 | MEASURED |
| — | the frozen `η` cancels identically when scoring against `L` | DERIVED |
| — | the three-reference table (5.4772 / 1.3912 / ≤1.3912) | DERIVED |
| — | the flat-ROI prediction matching the CLI to 0.03 % | MEASURED against a DERIVED prediction |
| — | Arm A is circular w.r.t. calibration; only a real burst tests it | ARGUED |
| — | Arm D's tripped criterion is mis-specification, not breakage | ARGUED |

---

## 11. Limits, disclosures, and what I did not do

- **`109MSDCF` is the corpus's easiest stack.** One of four with no saturation,
  and the quietest photometrically (M24: 0.91 % drift). The CLI prints this
  itself. A clean result here is **systematically weaker evidence than it looks**,
  and the §12 capture should not be shot to match it.
- **Fact 845 / discipline 409 — checked, unaffected.** `109MSDCF` is 17 May, on
  the **bare-lens** side of the 25 May boundary, so its numbers stand unqualified.
  No claim here is hedged on the filter: the word "specular" does not appear in
  this report or its code, no number is called a lower bound, and the one caveat
  attached to this stack (bullet above) rests on **M24's measured drift and the
  measured absence of saturation**, not on optics. Under the corrected rule that
  caveat is *stronger*, not weaker — the stack's clean highlights are a property
  of the subject and the exposure, with no filter available to explain them away.
  `coffee-bean` is not used anywhere in this work.
- **Fact 800** — the merge is blind to sensor defects, `D_defect/D_control = 1.00
  ± 0.08` — is untouched by this work. This harness measures *noise*, and
  averaging thirty samples of a hot pixel yields a well-averaged hot pixel. Arm
  C's C3 is the path that would give the defect layer a working-exposure
  population; nothing here does.
- **Fact 19** — the gated mean measures 0.534× noise relative to the argmax
  baseline, verified, **not built into the shipped binary**. This report is
  consistent with it in direction and does not re-measure it: the statistics are
  different (truth-referenced vs argmax-referenced) and the gates are different.
- **Fact 808 is not closed.** Arm D is 1/100 s in the dark. Only the §12 capture
  at 1/8–2.5 s on a scene closes it, and §8.1's C2 is the code that will.
- **One latent, one crop, one ISO.** N=30 with three seeds; the whole of Arm A is
  a single scene at ISO 160. Arm D adds ISO 100 on a dark field. Nothing here
  says anything about ISO 400+, where facts 783–808's labelling failure lives.
- **Green only** through the CLI, because white balance clips R and B in
  `write_merged`. Arm D's Python path covers all four planes; the CLI path
  cannot.
- **I did not modify** `SYNTHESIS.md`, `merge.rs`, `focus.rs`, `plane.rs`,
  `stack.rs`, `through_focus.rs`, `strehl-plugin/**`, or any of
  `strehl-cli/src/{lib,stack,merge_cmd,main}.rs`. The working tree's `merge.rs`
  does not compile (`E0425: cannot find value 'black_dn'`, `merge.rs:686`) — an
  agent has it mid-edit — so the binary was built from a `git archive` of
  `c37a790` in a scratch tree. Nothing under `D:\` or `C:\dev\macro` was written.
- **Rule 40 discharged:** `docs/research/M*.md` contains no prior report on a
  static or repeat burst. `M55-acceptance-spec.md` is a *detail* battery, not a
  noise one.

---

## 12. Reproduction

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cd experiments\M62-sqrt-n
git archive HEAD | tar -x -C build-head          # working tree may not compile
cd build-head; cargo build --release; cd ..
$env:PYTHONIOENCODING='utf-8'
python src\01-pick-latent.py
python src\02-fidelity.py        # must pass before anything else is believed
python src\04-arms.py            # the deciding run, ~8 s per seed
python src\05-trap-audit.py
python src\06-armD.py
python src\07-real-burst.py --smoke
python src\08-flat-selector.py
python src\09-diagnostic-hash.py  # rule 26; needs 06-armD.py to have run
```

`build-head/` and `data/` are gitignored — the first is a build tree, the second
holds synthetic frames (8 MB each, 30 per burst, deleted between seeds). Every
result is in `out/`.

**When the §12 burst lands:**
`python src\07-real-burst.py D:\personal\macro\<dir> --n 30`, which asserts the
frame count first (discipline 388) and writes `out/07-armC-real.json`. The
numbers to read, in order: **C2's `g_ratio` per plane** — that is the one Arm A
could not produce.

---

## 13. Rule walk (rule 22)

Agreeing with a rule does not execute it. Per rule, the line or command that
discharges it.

| rule | discharged by |
| --- | --- |
| 1 storage u16, arithmetic f32 | frames written as `<u2`; every statistic in `float64`. `harness.make_burst` |
| 2 never materialise aligned frames | nothing is aligned — a static burst has no alignment stage |
| 3 noise model injected, never re-derived | `harness.constants()` **parses** `profile.rs`; no constant is retyped anywhere in the harness |
| 4 never let a merge reference be a raw argmax | the reference is `L`, the defined latent. Raw argmax appears only as **arm B2**, as the thing being failed |
| 5 fit geometry at runtime | no geometry is used |
| 6 never chain alignments | n/a |
| 7 never compute statistics over the full decoded buffer | every statistic is on `H.roi()`, the plane interior inset 32 px |
| 8 every claim needs a command that was run | every number cites `out/*.json` or `out/*.log`; §12 lists the commands; every claim is labelled in §10 |
| 9 pair every sharpness metric with a flat-ROI control | no sharpness metric is used; the flat-ROI **statistic** appears as the instrument under audit in §4.1, and **B4** is a literally flat plant |
| 10 never compare a spatial sd to a temporal sigma | the harness statistic is **temporal-residual throughout**. §4.1's high-pass numbers are *spatial* and are compared only to a spatial prediction, never to the temporal ratio. Arm D's `measured/model` compares a **temporal** sd to `RN·g` |
| 11 every defect needs a placebo, every headline a regression on its own code path | the headline (P1) is regressed on its own code path by **B3** — same binary, one parameter — and by **B1a/B1b/B2/B4** |
| **12 the author never verifies their own work** | **not discharged, and cannot be by me.** See below |
| 13 check the plant can express the failure first | the gate ladder spans `n_eff` 1.000 → 30.000 on this plant (MEASURED, §6.2), so both ends are expressible |
| 14 `Get-ChildItem -Force` for the read-only guarantee | nothing under `D:\` was opened for write; every access is `rawpy.imread` or `glob` |
| 15 never the bare word "halo" | it does not appear |
| 16 alternate sweep direction when timing | no timing claim is made |
| 17 what map are you binning against | Arm C's C2 bins temporal variance against **per-pixel mean signal**, named at the call site |
| 18 say which direction each metric can be fooled | §4 (the reference choice compresses toward 1.39), §7.3 (the shipped invariant under-separates), §7.4 (Jensen bounds are loose in a known direction) |
| 19 kebab-case | `experiments/M62-sqrt-n/`, `docs/research/M62-sqrt-n.md` |
| 20 write the input down before running the gate | `PREREGISTRATION.md` at `906688c`, `PREREGISTRATION-D.md` at `dea34ad` |
| 21 a fitted constant cannot gate the model it was fitted to | **this is the whole of §8.** Stated as the report's central limit, not a footnote |
| 22 walk the list | this table |
| 23 `scipy.ndimage.sobel` smooths every axis but `k` | `sobel` is not used. `uniform_filter` is used only on 2-D arrays |
| 24 verification re-chooses, not re-computes | for the verifier; §13.1 names what to re-choose |
| 25 claim a number block before using it | proposed numbers are `P1…P19`, **local to this report**. No `SYNTHESIS` namespace was claimed or written |
| 26 prove the diagnostic does not perturb output, by hash | **F4** — byte-identical SHA-256 with `--flat-roi` on and off, both gates. `out/09-diagnostic-hash.json` |
| 27 what a healthy long-running process looks like | merges run in ~8 s; nothing was declared dead |
| 28 facts live in the fold, not in proposed numbers | `SYNTHESIS.md` **untouched**; `P` numbering is relative |
| 29 a string-anchored edit deletes its anchor | the `AGENTS.md` row re-emits its anchor; verified **1 insertion, 0 deletions**, 78 → 79 rows, pipe count 3 matching neighbours |
| 30 tolerated disagreements are asserted against, not carved out | Arm D's 22× σ mismatch is **stated and quantified** in §9.1, not excluded from the assertion; the tripped criterion is reported rather than relaxed |
| 31 fold from a committed revision, record the sha | pre-registrations committed **before** the runs that test them; binary sha `c37a790` recorded in the header |
| 32 `raw_image_visible` is a view | `.astype(np.float64)` on the same line, inside the `with`, in `01-pick-latent.py`, `06-armD.py` and `07-real-burst.py` |
| 33 no `Compiling` line, no evidence | `cargo build --release` in `build-head/` emitted `Compiling strehl-core` and `Compiling strehl-cli`, 1 m 02 s |
| **34 a plant supplying its own noise constant cannot detect that constant** | **conceded in the verdict, in §8, and in the pre-registration §6.** It is the reason Arm C exists and the reason Arm D was run |
| 35 a test whose subject and object are the same value has no power | the pass mark is **√30, arithmetic**, not any quantity the merge produces. The five selector arms demonstrate the power rather than asserting it |
| 36 show the fixture exercises the property | **F3** — the burst carries the σ it was told to, to 0.024 % |
| 37 insert into SYNTHESIS at the end of an ITEM | `SYNTHESIS.md` not touched |
| 38 cite by symbol and content, never line number alone | `const A7C2` with values; `Estimator::mean_predicted_sigma_gain`; `roi_green_merged`; `HP_NOISE_GAIN = 0.993_807_989_999_906_5`; `Gate::admits` |
| 39 report the null with its standard error | every arm carries a block-bootstrap SE **and** a between-seed sd; every separation in §7.3 is quoted against its null (1.0000 for selectors, √k for the ladder) |
| 40 search `docs/research/` before commissioning | done: no prior report on a static or repeat burst. `M55-acceptance-spec.md` is a detail battery |

### 13.1 Rule 12 — what an independent verifier should re-choose

I wrote this and I cannot verify it. The three things most worth **re-choosing**
rather than re-computing:

1. **A different latent.** `109MSDCF` is the corpus's quietest, unsaturated
   stack, and the estimator result may be flattered by it. Re-run Arm A at a
   high ISO — `coffee-bubbles` or `foam`, both ISO 1000 — and on a **saturated**
   crop, where clipping breaks the Gaussian noise assumption the plant is built
   on. **Filter state matters for the second choice and not the first.** A
   polariser suppresses speculars, so a CPL-side stack is poor hunting ground
   for clipped pixels, and both ISO-1000 stacks are on that side (`coffee-bubbles`
   confirmed, `foam` probable). `coffee-bean` — the obvious large low-ISO
   alternative at 105 frames — has an **unresolved** filter state (10 May, owner
   cannot recall) and would import a confound nobody can settle. For a
   saturation probe prefer `112MSDCF`, `113MSDCF` or `119MSDCF`: bare-lens,
   dated, unambiguous.
2. **A different reference.** The whole of §4 turns on defining truth as `L`. A
   verifier who instead denoises `L` and scores against `T` — option (a), which I
   declined — should land on the 1.3912 of the three-reference table, and the
   fact that they *disagree* by 3.94× is the check that the algebra is right.
3. **A different statistic.** The ratio is pooled RMS. A per-pixel median ratio,
   or a variance-of-differences estimator, should reproduce √30 to within the
   bootstrap SE. If it does not, the pooling is doing work it should not.

Most likely place for a defect, stated so it can be looked for first: the DNG
writer. It is 200 lines of hand-rolled IFD arithmetic, it already produced one
silent failure (ISO read as `UNKNOWN`, which would have forced the fallback noise
model and been invisible in the ratio), and **F1/F2 exist because of it**.
