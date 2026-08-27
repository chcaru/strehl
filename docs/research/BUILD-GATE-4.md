# BUILD-GATE-4 — the gate sweep: both axes, both regimes, and what should ship

Status: measurement complete. One decision is owed to ORCH and is named in §9.

This is the report ORCH asked for: fix the floor, then **sweep the gate across a
range that spans both sides of today's value** and score sharpness and noise at
every point, stratified by merge regime, with a default recommended in headroom
terms rather than in gate-ratio terms.

It also scores my own pre-registration (`BUILD-GATE-3.md` §4) against the
result, including the three predictions that failed, and **retracts** one
conclusion from `BUILD-GATE-2` §4 that was an artifact of a blind instrument.

---

## 0. The result in one paragraph

The gate is a near-linear dial between sharpness and noise, and **today's HEAD
is standing on the wrong end of it.** The floor fix (`78fed9a1`) is correct and
is already the default; but it was landed without moving the gate constant, and
that combination costs **6.4–20.1% of the master's fine detail** on four of five
subjects relative to the masters the owner has actually seen. The product's
*effective* gate before the fix was not its nominal `k=2.0` but **`k=1.731`
(measured, two independent axes, ±0.103)**, because the floor underneath it was
`1.1787×` too low. Correcting the floor without re-pointing `k` therefore moved
the product to an operating point nobody chose. **The floor fix and the gate
constant are one decision, not two.** Shipping the corrected floor at `k≈1.7`
holds the product within ±6% sharpness and ±10% noise of the approved masters
while putting a *measured* floor underneath it. That is the recommendation.

---

## 1. What was swept, and why these values

`MergeConfig::gate` (`pyramid.rs:1081`, default `2.0`) is documented as a
false-positive control: the band-energy statistic is a smoothed mean of ~13
squared samples fluctuating ~39% of its mean under pure noise, so gate `k` sits
`(k-1)/0.39` standard deviations above the noise expectation. The sweep is
therefore **a sweep in sigma**, not in round numbers:

| arm | k | sigma | what it is |
|---|---:|---:|---|
| `G100` | 1.0 | 0.00 | gate exactly at the noise floor: maximum selection |
| `G140` | 1.4 | 1.03 | |
| `G170` | 1.7 | 1.79 | **prices** the pre-fix shipping operating point (2.0/1.1787) |
| `G200` | 2.0 | 2.56 | **today's default, and what HEAD ships** |
| `G300` | 3.0 | 5.13 | |
| `G400` | 4.0 | 7.69 | maximum averaging |
| `WHITE200` | 2.0 | — | `STREHL_GATE_FLOOR=white`: the **pre-fix** shipping build |

`G170` **prices** the old operating point; it does not **reproduce** it. Fact 631
established that rescaling a gate does not reproduce another configuration's
decisions, and `beta` is per-frame and per-band while `k` is global, so no single
`k` can undo a per-frame error. §5 measures how close the approximation gets, and
the answer is *near but not exact*, which is what fact 631 requires.

**Seven arms x five subjects, one pinned binary** (SHA256 `8E397B01…`), every
render at **complete bracket depth**, no subsampling. A 13-frame reference once
made the merge look 1.25x–16.5x better than its input, and that was pure sampling
artifact.

**The pin is HEAD on the merge path, and this was proved rather than argued.**
The pin was built at 08:30:50 and HEAD is later, so:
`git log --since=08:25 -- crates/strehl-core/src/pyramid.rs crates/strehl-cli/src/merge_cmd.rs crates/strehl-cli/src/merge_cmd/ crates/strehl-core/src/focus.rs`
returns **empty**. That is necessary but not sufficient: the pin reports itself
as `42e2d95ec94c-dirty`, i.e. built from a tree with uncommitted changes, so it
might correspond to no commit at all. The check that settles it is direct
reproduction — a clean release build at HEAD (`0832dfc12b2f`, `crates/` verified
clean) re-rendered the `G200` arm:

```
pixels differing : 0.0000%     max |diff| : 0     mean ratio 1.000000
ceiling score    : 1.0924 vs 1.0924, per-site 1.035 1.103 1.111 both
```

The **file hashes differ** and the pixels do not, because the build identifier is
embedded in the TIFF metadata — the same mechanism behind the registry's
`ImageDescription` re-baseline, and the same reason `SHIP-V4` and `WHITE200`
differ by 11 bytes in §3 while being pixel-identical. **`G200` is what
`strehl stack` does today**, and a `-dirty` pin turned out to be harmless here
only because it was checked.

---

## 2. The instrument, and the four ways it was commissioned

The numerator is **ORCH's**, imported and never reimplemented: `ceiling.py`
takes `luma`, `detail`, `register`, `best_site`, `patch_gain` and every constant
from `experiments/ORCH-drift-check/orch_sharp1to1.py`. The denominator is a
**complete per-site focus ceiling**: for every tile, the sharpest value any frame
in the bracket achieves at that tile.

**C1 — agreement with ORCH's own harness.** Two sites scored by both paths:
`1.116853 vs 1.116853` and `1.203802 vs 1.203802`, **IDENTICAL**. My statistic
*is* `patch_gain`; any disagreement with another lane is therefore not in this
number.

**C2–C5 — response to planted change, including a planted improvement.** ORCH
required the improvement arm specifically, because a metric that only ever sees
things get worse passes a damage-only test trivially:

```
C2 identity (byte copy)      +0.00%  vs    0.00%  PASS
C3 softened (5-tap blur)    -64.96%  vs  -65.05%  PASS
C4 gain x1.05               +5.00%  vs   +5.00%  PASS
C5 SHARPENED (unsharp mask) +62.23%  vs  +61.90%  PASS   <- the IMPROVEMENT
```

**The ceiling is computed once per subject and held fixed across all seven
arms.** The sources are identical across arms, so this is not an optimisation —
it is what makes the comparison **paired** and what cancels the order-statistic
inflation *exactly* rather than approximately. Sites and registration shifts are
also taken once, from a named reference arm, so no arm can move the statistic by
moving the selection.

**An instrument bug its own control caught, recorded rather than hidden.** The
first commissioning predictor summed tile detail across sites and compared that
to a **median** of per-tile ratios. Different aggregations disagree on any
non-uniform change — a blur costs a fine-texture tile a larger *fraction* of its
gradient than a high-contrast edge tile — so it read `-64.96` measured against
`-44.23` predicted and **failed two arms that had in fact moved correctly**.
Fixed to `median(per-tile factor)`, still computed from the master alone so it
remains an independent prediction.

**Registration was replaced and the replacement was proved, not trusted.**
`register_fft` (`regcheck.py`) computes the same argmax via one rFFT
cross-correlation plus integral images. Validated three ways: **12/12 identical
shifts**, **108.1x faster** (8.570 s → 0.079 s), and a **full ceiling rebuild
that is bit-identical, `max abs diff 0.0`**. `build_ceiling` re-validates on 3
evenly-spaced frames **per build** and hard-exits on disagreement: a speedup
validated once elsewhere is an assumption; validated per build it is a control.

**The renders are reproducible.** 23 arms were re-rendered from the pin and
hashed against the arms already on disk: **determinism mismatches = 0**
(`banner_capture.ps1`, covering all seven arms on the three shallow subjects and
the stratification arm on both deep ones). That re-render also recovered the
`averaged` banner, because the stratification variable had otherwise survived
only in a console transcript, and a number transcribed from a transcript has no
provenance.

**A bug in that harness, found because it was backgrounded.** `banner_capture.ps1`
originally set `$ErrorActionPreference = "Stop"`. `strehl` writes its banner to
**stderr**, and `2>&1` on a native command turns stderr into a PowerShell error
record, which under `Stop` is terminating. The in-session run completed all 21
arms; the backgrounded run via `Start-Process powershell -File` died on the
first render and wrote **zero** logs while leaving a `NativeCommandError` in its
stderr. A script that works when watched and fails when backgrounded is worse
than one that always fails. Fixed, and the render is now judged by its **output**
— the hash comparison — rather than by the absence of an error record.

---

## 3. The baseline is the shipped product, measured not assumed

`WHITE200` is not a stand-in for the shipping build. It **is** it:

```
SHIP-V4 vs WHITE200 : pixels identical = True   max|d| = 0
SHIP-V4 vs G200     : pixels identical = False  max|d| = 4328,  91.87% of pixels differ
```

So every delta below is measured against the exact pixels the owner has
approved, and the floor fix is not cosmetic — it moves 91.87% of the frame.

Two incidental findings from that check, both worth someone's attention:
`SHIP-V3` and `SHIP-V4` are **byte-identical** (`ABA490AA…`, same size), so they
are one render under two names; and the shipping masters are **pre-fix**, i.e.
they predate `78fed9a1`.

---

## 4. THE PRIMARY RESULT — both axes, all five subjects

Sharpness is the per-site ceiling ratio (higher is better). Noise is flat-tile
high-pass rms (lower is better). Both are deltas against `WHITE200` = the
shipped master. The two axes deliberately share **no tiles**: sharpness is read
on the three most textured sites where detail lives, noise on the flattest
decile where noise lives.

### Sharpness, Δ% vs the shipped master

| subject | avg@ship | regime | G100 | G140 | **G170** | **G200 = HEAD** | G300 | G400 |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| `bee-1-cpl` | 0.4% | SELECTION | −0.33 | −0.17 | **+0.17** | **−0.31** | −0.69 | −1.40 |
| `flower-bud-alone-cpl` | 12.5% | averaging | −11.11 | −2.37 | **+0.21** | **−11.62** | −29.84 | −29.95 |
| `119MSDCF` | 15.5% | averaging | +8.70 | +10.59 | **+0.53** | **−11.19** | −28.25 | −33.74 |
| `coffee-bubbles` | 26.1% | averaging | +10.43 | +12.97 | **+5.57** | **−6.38** | −38.26 | −51.37 |
| `109MSDCF` | 52.5% | averaging | +42.15 | +21.74 | **−6.02** | **−20.09** | −36.51 | −45.22 |

### Noise, Δ% vs the shipped master

| subject | G100 | G140 | **G170** | **G200 = HEAD** | G300 | G400 |
|---|---:|---:|---:|---:|---:|---:|
| `bee-1-cpl` | −18.64 | −7.19 | **+0.36** | **−4.48** | −74.18 | −86.56 |
| `flower-bud-alone-cpl` | −0.68 | +9.53 | **+2.61** | **−24.76** | −71.17 | −73.78 |
| `119MSDCF` | −2.08 | +4.68 | **+0.59** | **−15.22** | −64.15 | −78.57 |
| `coffee-bubbles` | +12.72 | +15.47 | **+6.74** | **−9.16** | −52.52 | −68.85 |
| `109MSDCF` | +47.58 | +28.37 | **−9.85** | **−40.16** | −69.73 | −71.39 |

### Three things this table says

**(a) HEAD is soft on every subject.** `G200` — the floor fix at the unchanged
default — is negative on sharpness for **all five**: `−0.31, −11.62, −11.19,
−6.38, −20.09`. There is no subject on which shipping the fix at `k=2.0` is free.

**(b) `G170` is the only arm neutral on both axes everywhere.** Sharpness
`+0.17, +0.22, +0.53, +5.58, −6.02` — four within ±6%, `109MSDCF` marginally
outside at **−6.02%**, so the honest band is **±6.1%**. Noise `+0.36, +2.61,
+0.59, +6.74, −9.85`, all within ±10%. No other arm is uniformly small on both.
(The draft of this line said "all within ±6%". The §10 verifier failed it on
`109MSDCF` at −6.02% and the band was widened to the measured value rather than
the claim being kept. A tolerance quietly loosened to fit a number is how a
measurement becomes a benchmark.)

**(c) There is no free lunch, and the exchange rate is remarkably stable.** On
`coffee-bubbles` the ratio of Δsharpness to Δnoise is `+0.82, +0.84, +0.83,
+0.70, +0.73, +0.75` across the entire sweep — the gate buys about **0.8% of
sharpness per 1% of noise**, in both directions, over a range where the ceiling
ratio itself moves **2.3x** (`0.5674 → 1.3182`).

---

## 5. The regime stratification, and the threshold I used

**Stratification variable:** the measured `averaged` fraction at band 0 under the
**shipping** configuration, taken from the render banner (provenance:
`banner_capture.ps1`, logs under `.../BUILD-GATE/banner/`). I used the directly
measured causal quantity rather than V-EYES' `avg_index`, whose definition I do
not have.

**Threshold, stated as ORCH required: `< 5%` = selection-dominated, `>= 5%` =
averaging-dominated.** That places `bee-1-cpl` (0.4%) alone in the selection
stratum and the other four (12.5–52.5%) in the averaging stratum.

**The threshold is not arbitrary — the response splits exactly there.** Total
sharpness range across the whole sweep, k=1.0 to k=4.0:

| subject | regime | sharpness range across the sweep |
|---|---|---:|
| `bee-1-cpl` | SELECTION | **1.6%** |
| `flower-bud-alone-cpl` | averaging | 30.1% |
| `119MSDCF` | averaging | 40.1% |
| `coffee-bubbles` | averaging | 57.0% |
| `109MSDCF` | averaging | 61.5% |

**On a selection-dominated subject the gate is nearly free.** `bee-1-cpl` gives
up **1.40%** of sharpness for an **86.56%** noise reduction between `k=1.0` and
`k=4.0`. On averaging-dominated subjects the same move costs 30–61%. ORCH was
right that a corpus mean would have averaged these into a null: the mean of
`−1.40` and `−45.22` is a number describing no subject in the corpus.

**The sharpness-optimal `k` FALLS as the averaging fraction rises.** Peak arm by
subject: `109MSDCF` (52.5% averaged) peaks at `k=1.0`; `coffee-bubbles` (26.1%)
and `119MSDCF` (15.5%) at `k=1.4`; `flower-bud` (12.5%) at `k=1.7`; `bee-1`
(0.4%) is flat to 1.6% with a nominal peak at `k=1.7`. The direction is the
physically sensible one and it is worth stating plainly: **a subject that is
already averaging heavily is the one being hurt by averaging, so it wants a
LOWER gate, not a higher one.** **There is no single optimal gate** — the
optimum is a property of the subject's averaging regime, and that is itself a
publishable result.

(I wrote this sentence backwards in draft — "rises" — and the verification
script in §10 caught it against my own table. Recorded because a report whose
arithmetic is checked only when it disagrees with expectation is not checked.)

---

## 6. The convergence check that could have failed and did not

The floor arithmetic (WS4) says the shipping band-0 floor was `1.1787x` too low,
so the *effective* gate was `2.0/1.1787 = 1.697`. That is an inference from the
floor, not from pixels. `keff.py` tests it against the sweep, which knows nothing
about `beta`: interpolate the measured curves to find the `k` whose **sharpness**
equals the shipping arm's, and independently the `k` whose **noise** does.

```
subject                k_eff(sharp) k_eff(noise)     spread
coffee-bubbles              1.840      1.827      0.013
109MSDCF                    1.635      1.623      0.012
119MSDCF                    1.714      1.711      0.002   AMBIGUOUS: 1/2 crossings - EXCLUDED

mean k_eff over 4 unambiguous estimates = 1.731  (sd 0.103)
predicted 1.697 -> discrepancy +2.0%
```

**The two axes share no tiles, no reference and no physics, and they agree to
within 0.013 in `k` on every subject.** A common `k` is not built into the
construction; it had to be measured. And the agreement with the floor arithmetic
is **+2.0% — near but not exact**, which is precisely what fact 631 demands. An
exact hit would have been evidence of a book-keeping error, not of success.

**`invert` was fixed mid-analysis and the fix is recorded.** It originally
returned the *first* crossing, which is a silent lie on a non-monotone curve:
`119MSDCF`'s noise curve genuinely has two roots because `G100` reads *below* the
shipping arm. It now returns the crossing count and the caller **excludes**
ambiguous subjects from the mean rather than folding an artifact into it.

**This is the independent confirmation of the WS4 floor finding**, obtained from
delivered pixels rather than from the floor computation, and it is the reason
`k≈1.7` is not a tuned number: it is the operating point the product already had.

---

## 7. Scoring my own pre-registration, including what failed

`BUILD-GATE-3.md` §4 registered P1–P6 before any of this was measured.

**P1 — every subject's ratio FALLS on the shipping arm. CONFIRMED, 5/5.**
`−0.31, −11.62, −11.19, −6.38, −20.09`. This was the primary prediction and it
was **against** what ORCH expected when the brief was written.

**P2 — the plane arm rises. NOT TESTED.** The sweep did not include a
`STREHL_FULLRES_GATHER=0` arm. This was the discriminating two-arm test that
would have separated the mechanism from "the new code just softens things", and
I did not run it. It remains owed.

**P3 — magnitude 19.9–36.1%. REFUTED.** Measured falls are `0.31–20.09%`; only
`109MSDCF` reaches the bottom of the predicted band. The prediction was
extrapolated from `acuity.py`'s sharp-tile statistic, which §8 now shows is
nearly blind to this variable. The regime-split half of P3 survives; the
magnitude half does not.

**P4 — fall size monotone in Δ`averaged`(band 0); `bee-1` smallest,
`flower-bud` largest. HALF CONFIRMED.** `bee-1` smallest: correct. Monotone:
Spearman **rho = 0.90**, 4 of 5 in order. `flower-bud` largest: **wrong** — it
has the largest Δ`averaged` (+24.8 pp) but only the third largest fall; the
largest fall is `109MSDCF`. The prediction was directionally right and specific
in the wrong place.

**P5 — noise falls 15–35%, and noise and sharpness move together to within 10
pp. BOTH PARTIALLY REFUTED, and the failure is the interesting part.** The level:
only 2 of 5 land inside 15–35% (`−4.48, −24.76, −15.22, −9.16, −40.16`). The
coupling: 3 of 5 within 10 pp (`bee` 4.2, `119` 4.0, `coffee` 2.8), but
`flower-bud` 13.1 pp and `109MSDCF` **20.1 pp**. The two that break it are the
two that average most, and they break it in the *favourable* direction — on
`109MSDCF` noise falls **twice as fast** as sharpness. So the band-0 gate is
close to a non-selective attenuator on lightly-averaged subjects and becomes
genuinely **noise-selective** on heavily-averaged ones.

**P6 — the align-refused placebo moves exactly 0.000. NOT TESTED** in this sweep.

Three predictions confirmed or half-confirmed, two refuted, two untested. The
refutations are recorded here because a pre-registration that is only cited when
it succeeds is not a pre-registration.

---

## 8. RETRACTION: BUILD-GATE-2 §4's Q1 answer was instrument-limited

`BUILD-GATE-2` §4 answered ORCH's Q1 — *is the 94.1% `averaged` / 13.06x removal
noise removal, or signal averaged away?* — using `acuity.py`'s sharp-tile
statistic, and concluded the band-0 gate was close to a **non-selective
attenuator**.

**That instrument cannot see this variable.** Across the full sweep, over which
the per-site ceiling ratio moves **2.3x** (`0.5674 → 1.3182` on
`coffee-bubbles`), `acuity.py`'s `sharp` moves by **at most 0.16%**:

| arm | ceiling ratio | acuity `sharp` Δ |
|---|---:|---:|
| G100 | 1.2885 | −0.08% |
| G140 | 1.3182 | −0.00% |
| G200 | 1.0924 | −0.05% |
| G400 | 0.5674 | −0.08% |

A statistic that reads `−0.08%` where the better instrument reads `−51.37%` is
not measuring the quantity. **I retract the "non-selective attenuator"
conclusion as an artifact of that blindness**, and I note that BUILD-GATE-2's
own `−19.9…−36.1%` readings on `foam`/`tweezers`/`couch` may still be real —
sensitivity is strongly subject-dependent — but they cannot support a general
claim. `acuity.py` remains sound for the **noise** axis, which is what it is used
for above and what it was commissioned against; its `sharp` output should not be
used for sharpness verdicts on the gate.

**ORCH's Q1, answered with the instrument that can see it:** it is **both, never
purely noise, and the mix is a function of regime.** On `109MSDCF` noise falls
`40.16%` for `20.09%` of sharpness — 2:1, mostly denoising. On `coffee-bubbles`
it is `9.16%` for `6.38%` — 1.4:1, substantially signal. **On no subject
measured is it free.** The live hypothesis ORCH raised — signal averaged away —
is confirmed as a real component on every subject.

---

## 9. Recommendation, in headroom terms

The product is **1.54–1.76x cleaner than `enfuse` on chroma noise** and **0.977
on sharpness**. Large noise headroom; **zero** sharpness headroom.

**Recommended: ship the floor fix, and move the default gate `2.0 → 1.7` in the
same change.**

- **HEAD today is unshippable on the sharpness axis.** The floor fix at `k=2.0`
  costs `6.4–20.1%` on four of five subjects against the approved masters. That
  spends the one currency at zero headroom.
- **`k=1.7` is neutral on both axes on all five subjects** (±6.1% sharpness,
  ±10% noise) — and it is not a fitted number. It is the product's own measured
  effective operating point, `k_eff = 1.731 ± 0.103`, arrived at independently
  in §6. Correcting the floor and re-pointing `k` to `1.7` keeps the delivered
  image where it is while putting a **measured** floor underneath it.
- This maps to **ORCH's decision-rule branch 3** — *neutral on both, ship it on
  as pure correctness*. At `k=2.0` the same fix falls under **branch 2** and
  would have to ship defaulted **off**.

**On branch 1 (sharper at equal-or-better noise → becomes the default): no arm
qualifies corpus-wide.** `119MSDCF`'s `G100` does (`+8.70%` sharper at `−2.08%`
noise) and `bee-1`'s `G100` nearly does, but the same arm is `−11.11%` on
`flower-bud`. I am **not** recommending it.

**`k=1.4` is the aggressive option and I am reporting it rather than
recommending it.** It is the sharpness optimum on two subjects (`+12.97%`,
`+10.59%`), positive on three of five, and costs `−2.37%` on `flower-bud`. It
buys sharpness with noise, which given the headroom asymmetry is the *right
direction* of trade. But the translation is not mine to make: the `enfuse`
head-to-head is another lane's instrument on different tiles, and I **cannot**
multiply `0.977` by my ratio and claim a number. **If ORCH wants `k=1.4`
considered, the head-to-head must be re-run at that setting.** I did not tune
`k` against the softness ratio and I did not treat it as a target.

**A byte-freeze question that answers itself.** My recommendation changes a
default, so the freezes were checked rather than assumed. Every freeze row runs
**`--merge estimator`** (hardcoded, `byte-freeze.rs:544-545`) and passes
`--gate`, the estimator's threshold — a different quantity on a different scale.
The pyramid gate is not merely inert there, it is **refused**:

```
strehl stack ... --merge estimator --gate 2.0 --pyramid-gate 1.7
  -> Refused rather than ignored because a flag that silently does nothing
     looks exactly like one that works.
```

So changing `MergeConfig::default().gate` **cannot move a byte freeze**. I have
still not made the change: it touches `crates/strehl-core/src/pyramid.rs:1081`
and I have not been sequenced for it. **That is the one decision owed to ORCH.**

---

## 10. Verification

```
cargo test --workspace          712 passed; 0 failed; 1 ignored      exit 0
  (includes the 5-test byte-freeze suite, 509.45s, 0 failed)
cargo clippy --workspace --all-targets                               exit 0
  warnings only, all pre-existing; crates/ untouched this session
python scripts/corpus_lint.py --root .                               exit 0
python experiments/BUILD-GATE/src/verify_tables.py                   exit 0
  ALL CLAIMS VERIFIED -- re-derives every ratio, range, peak arm, rank
  correlation and exchange rate in sections 4 and 5 from the measured arms
```

**The verifier earned its place twice.** It failed the draft on §5's claim that
the optimal `k` *rises* with the averaging fraction (it falls), and again on
§4(b)'s "within ±6%" when `109MSDCF` reads `−6.02%`. Both were corrected in the
text rather than absorbed by loosening a tolerance, and both corrections are
recorded at the point of the claim.

Determinism control: 21 arms re-rendered from the pin and hashed against the
arms already on disk — **mismatches = 0**.

`byte-freezes.tsv` is **byte-identical at HEAD and at the pre-fix parent**
(`78fed9a1~1`) — 0 diff-body lines in `78fed9a1`. **Nothing was re-baselined.**

## 11. Open, and honestly so

- **The absolute levels disagree with V-EYES. §12.3 RETIRES THIS ITEM'S
  DIAGNOSIS AND WITHDRAWS THE NUMBERS BELOW.** V-EYES
  reads `coffee-bubbles 0.9018 / 109MSDCF 0.8855 / 119MSDCF 0.8147`; I read
  `1.1668 / 2.8206 / 1.8590` **on the same pixels** (§3 proves `WHITE200` is
  `SHIP-V4` byte for byte) with a statistic C1 proves is `patch_gain` exactly.
  So the difference is **neither the master nor a transcription error — it is
  the two lanes' instruments.** The guess recorded here was population:
  `patch_gain` scores the three most textured 560px sites; V-EYES appears to
  tile the whole frame, which includes flat regions where a merge cannot beat
  its best frame. **That guess was wrong.** §12.3 measures the actual cause — a
  0.59×–3.31× brightness mismatch between the master and the ceiling frames, to
  which `patch_gain` is exactly linearly sensitive — and withdraws the absolute
  levels. **The rankings agree** — `bee-1` most beats its ceiling in both lanes —
  and my comparison is paired, so every delta here is valid regardless.
- **P2 and P6 remain untested** (§7).
- The noise axis uses one statistic on one tile class. It is commissioned, but a
  second independent noise instrument would strengthen §4.
- `bee-1-cpl` and `flower-bud-alone-cpl` resolved **2 sites**, not 3, and
  `bee-1` refused 3 of 299 registrations at one site. Both are recorded in the
  ceiling artifacts.

## 12. ORCH's three added requirements: complying, and what complying changed

ORCH added three requirements after §0–§11 were written: score against a
per-site ceiling, use a selection-immune construction or commission a forced
null and refuse on high leak, and confine the reported band to ≤0.25 cyc/px.
Requirement 1 was already met. Requirements 2 and 3 were **not**, and meeting
them changed several numbers and retired one open item. New instrument:
`experiments/BUILD-GATE/src/bandceiling.py`, driven by `bandsweep.py`, with
intervals from `bandboot.py`.

### 12.1 The requirements are violated by ORCH's own numerator

Both violations are in `orch_sharp1to1.patch_gain`, which is the numerator every
number in §4 was computed with. This is a property of the shared instrument, not
a defect in this lane's use of it.

- **REQ 2.** `patch_gain` computes `sf = max((detail(c[sl])[0] for _, c in reg))`
  — a max taken directly over the reported quantity. That is the inflated
  construction ORCH now asks to replace.
- **REQ 3.** `patch_gain` reports `detail(...)[0]`, a full-resolution first
  difference whose power response `4 sin²(πf)` rises monotonically to Nyquist.

**REQ 3, measured rather than assumed.** For white input the analytic fraction of
that statistic's energy above 0.25 cyc/px is 0.8183. I quoted that figure as my
expectation. On real tiles it is **much lower**, because real spectra fall:

| subject | fraction of `fine` energy above 0.25 cyc/px |
|---|---:|
| `bee-1-cpl` | 0.1199 |
| `119MSDCF` | 0.1858 |
| `109MSDCF` | 0.3209 |
| `flower-bud-alone-cpl` | 0.3614 |
| `coffee-bubbles` | 0.4931 |

Mean 0.2962. **My analytic expectation over-predicted by 2.76×** and is
withdrawn.
The honest statement is that 12–49% of §4's statistic sits in withdrawn
territory, and that the contamination varies **4× across subjects**, so it is not
a constant that cancels in cross-subject comparison.

### 12.2 The disjoint construction, and its commissioning

Select the reference frame per tile on band A (0.05–0.20); report band B
(0.20–0.25) from that frame; never take a max over B. The bands share no Fourier
bins, so the noise that wins the selection is independent of what is reported.
Tiles are Hann-windowed first — without it the tile edge is a discontinuity
whose spectrum contaminates every band.

Immunity by construction is still a claim, so it is commissioned with a forced
null: n = 24 statistically identical noised copies of the master, true ratio
1.000 by construction, so any departure is the construction's own leak.

| subject | null `max` | null `disj` | leak `max` | leak `disj` | verdict at 2% |
|---|---:|---:|---:|---:|---|
| `bee-1-cpl` | 0.9892 | 0.9961 | 1.08% | 0.39% | both OK |
| `flower-bud-alone-cpl` | 0.9722 | 0.9876 | 2.78% | 1.24% | **REFUSE `max`** |
| `119MSDCF` | 0.9855 | 0.9994 | 1.45% | 0.06% | both OK |
| `coffee-bubbles` | 0.9726 | 0.9858 | 2.74% | 1.42% | **REFUSE `max`** |
| `109MSDCF` | 0.9755 | 0.9893 | 2.45% | 1.07% | **REFUSE `max`** |

**The max construction is refused on 3 of 5 subjects.** `disj` passes on all
five. Adopting ORCH's refusal discipline therefore withdraws the construction
`patch_gain` uses, on the majority of this corpus.

The leak also behaves the way immunity predicts. Doubling the planted noise
scales `max`'s leak roughly linearly (119MSDCF: 0.72% → 1.45% → 2.89% at
0.5×/1×/2×) while `disj`'s stays flat (0.05% → 0.06% → 0.14%). A leak
proportional to noise power is selection inflation; a leak that ignores it is
not.

**One attempted fix was tested and rejected.** A gain-invariant variant
(`share` = band-B's share of band-W, which cancels any exposure gain exactly)
leaked **1.46–1.80%** and in the *opposite* direction, above 1.000 — dividing by
W reintroduces the selection through the denominator. It buys gain invariance by
giving back selection immunity, and it leaks in strehl's favour, which is the
dangerous direction. Not used.

### 12.3 The absolute levels are confounded, and §11's open item is retired

§11 recorded that my absolute levels disagreed with V-EYES and guessed the cause
was tile population. **That guess was wrong.** The cause is a brightness
mismatch between the master and the ceiling frames:

| subject | median luma, master | median luma, frame | gain |
|---|---:|---:|---:|
| `coffee-bubbles` | 3819.7 | 6439.0 | **0.5932** |
| `119MSDCF` | 19058.8 | 10091.0 | **1.8887** |
| `109MSDCF` | 18673.7 | 5640.6 | **3.3106** |

A planted gain establishes the sensitivity exactly. Multiplying only the master
crop by g moves the band ratio by precisely g² (1.5 → 2.250, 2.0 → 4.000) and
ORCH's `fine` by precisely g¹ (1.500, 2.000), on all three subjects. So
**`patch_gain` is exactly linearly sensitive to a mismatch measured here at
0.59×–3.31×** — enough to move a subject across the 1.0 threshold its docstring
uses to separate "the merge SELECTS" from "the merge RECONSTRUCTS, that is this
project's actual claim".

Correcting §11's numbers by the measured gain:

| subject | §11 | gain | corrected | V-EYES | ratio |
|---|---:|---:|---:|---:|---:|
| `coffee-bubbles` | 1.1668 | 0.5932 | 1.9670 | 0.9018 | 2.181 |
| `119MSDCF` | 1.8590 | 1.8887 | **0.9843** | 0.8147 | 1.208 |
| `109MSDCF` | 2.8206 | 3.3106 | **0.8520** | 0.8855 | **0.962** |

Two of three move from "reconstructs" to V-EYES' side of 1.0, one to within
3.8%. `coffee-bubbles` does not. **So the confound is a major contributor and
not a complete explanation, and I do not claim reconciliation.**

**I attributed the mismatch to `--auto-exposure` and an intervention refuted
that.** Re-rendering the three masters with the flag removed and nothing else
changed gave a median-luma ratio of **1.0000** and ratios identical to four
decimals (`coffee-bubbles` 1.7065 both ways). Auto-exposure is a no-op on these
subjects. The mismatch is structural to comparing a strehl `--srgb` master
against `rawpy.postprocess(gamma=(2.222,4.5), no_auto_bright=True,
use_camera_wb=True)` frames — and **`orch_sharp1to1.py:394` develops its frames
with byte-identical parameters**, so the confound is shared.

**Consequence: the absolute ceiling ratios in §4 and §11 are withdrawn.** The
arm-to-arm deltas are not, and that is measured rather than argued: across-arm
master luma varies by ≤0.4% on `119MSDCF` and `109MSDCF` and ≤3.4% on
`coffee-bubbles`' most extreme arm, i.e. ≤1% in energy except G400 at ≤6.8%,
against deltas of 5–80%. The ceiling is built once per subject and held fixed
across all seven arms, so it is a common denominator that cancels in every
delta. This is the argument made in BUILD-GATE-3 §3 against my own interest,
now measured.

### 12.4 The sweep re-scored on the compliant statistic, with intervals

Paired tile bootstrap, 2000 resamples, resampling tiles because tiles are the
replicated unit. `*` marks a 95% CI excluding zero. Δ% against `WHITE200`, the
arm the product actually ships.

| subject | G100 | G140 | G170 | G200 | G300 | G400 |
|---|---:|---:|---:|---:|---:|---:|
| `bee-1-cpl` | −0.02 | −0.00 | +0.01 | −0.71 | −1.19 | −0.84 |
| `flower-bud-alone-cpl` | −12.43\* | −2.24 | +1.82 | −17.41\* | −79.98\* | −87.30\* |
| `119MSDCF` | +9.68\* | +16.57\* | +0.97 | −26.79\* | −55.52\* | −69.12\* |
| `coffee-bubbles` | +7.46\* | +11.74\* | +6.47\* | −9.87\* | −46.65\* | −59.20\* |
| `109MSDCF` | +87.27\* | +43.80\* | −10.52\* | −39.93\* | −70.13\* | −82.02\* |

**What survives, what changes:**

- **`bee-1-cpl` is null across the entire sweep — not one arm on either
  construction has a CI excluding zero.** The pooled point estimate read −7.32%
  at G100; the paired median is −0.02% with CI [−7.06, +0.18]. That difference
  is the disjoint statistic's noise floor: band B is a thin annulus holding ~2.7×
  fewer Fourier bins than band W, so on a 2-site/128-tile subject its floor is
  ±7–14%. **Any single-subject `disj` delta smaller than that is not a
  measurement**, which is why §12.4 is reported with intervals and §4 should
  not be read without them.
- **The ranking is unchanged** from §4 on all five subjects, and **the direction
  of every significant arm agrees** with §4. The conclusion does not depend on
  the non-compliant instrument.
- **The losses at high gate are systematically larger** on the compliant
  statistic: `119MSDCF` G200 −26.79% vs §4's −11.19%, `109MSDCF` G400 −82.02%
  vs −45.22%. Restricting to the supportable band makes the gate look **worse**,
  not better, because averaging destroys the finest supportable detail first and
  the wideband statistic dilutes that with Nyquist energy the merge barely
  touches.
- **G200, the nominal default, is significantly worse than what ships today on 4
  of 5 subjects** (−17.41, −26.79, −9.87, −39.93, all CIs excluding zero; bee-1
  null). This is the §9 recommendation's central claim and it is now
  significant rather than merely pointwise.
- **G170 is indistinguishable from the shipped arm on 3 of 5** (bee-1
  [−0.29,+0.26], flower-bud [−1.09,+3.64], 119MSDCF [−1.23,+3.25]),
  significantly **better** on `coffee-bubbles` (+6.47 [+2.94,+10.21]) and
  significantly **worse** on `109MSDCF` (−10.52 [−15.82,−3.70]).

**§4(b)'s "G170 is neutral within ±6% on all five" is corrected: on the
compliant statistic it is −10.52% on `109MSDCF`, and that CI excludes zero.**
The recommendation survives because the comparison that matters is against G200,
not against zero — but the cost is larger than §4 stated and is stated here.

### 12.5 The recommendation under ORCH's pre-registered rule, unchanged

- **Branch 1 (sharper at equal-or-better noise on averaging-dominated subjects)
  qualifies on no arm.** `coffee-bubbles` G170 is +6.47% sharper but +6.74%
  noisier; G100 is +7.46% sharper but +12.72% noisier. The exchange rate
  reported in §5 holds on the compliant statistic. **There is no free lunch in
  this parameter**, and that is a real result rather than a failure to find one.
- **Branch 2 (correct but costs sharpness) is what the floor fix is, if shipped
  at the nominal gate.** G200 is significantly softer than today's product on
  4 of 5 subjects.
- Therefore §9's recommendation stands and is now better evidenced: **ship the
  floor fix and 2.0 → 1.7 as one change.** Shipping the fix alone is a
  significant, measured sharpness regression on 4 of 5 subjects. `k = 1.7` is
  not fitted to these data — it equals the independently measured `k_eff =
  1.731` of §6.

## 13. Does the admission gate fix the mid-scale mottle? No.

ORCH asked for a two-column sweep -- blotch and sharpness in every row, never
one -- on artifacts already on disk, and for the depth question. Both are below.
No re-render was needed; all seven arms and five subjects were already rendered.

**The answer in one line: the largest blotch reduction available at no
measurable sharpness cost is -3.57%, and undoing the convicted 2.43x excess
needs -58.8%.** The knob delivers at most 6.1% of the required reduction, on
one subject of five, and on two subjects it delivers nothing at all. The
admission gate is not the mechanism that manufactures the mottle.

### 13.1 The instrument, and why it is ORCH's

`sigma_mid` is imported from `experiments/ORCH-drift-check/orch_eye_check.py`,
not reimplemented. It is `std(boxblur(p,10) - boxblur(p,30))`: box widths 21
and 61 px, which is exactly the 20-60 px band the convictions live in. The
earlier caveat in section 12 -- that the band cache starts at 0.05 cyc/px and
so covers only the fine end of mottle scale -- applies to `tile_bands`, not to
this statistic. `sigma_mid` covers the conviction band in full.

**Textured sites cannot measure mottle, and this was measured rather than
argued.** `sigma_mid` on a textured `pick_sites` crop of `coffee-bubbles` reads
**25.34 codes**; on the flat sites it reads **0.12-1.30 codes**. A textured
reading is therefore ~99% subject structure, and a 2-code plant on it is a 0.3%
change -- unresolvable. This is the failure mode that refuted ORCH's own
mid-band statistic when it lit up on a leaf's vein network. `pick_flat_sites`
scans a 280-px grid of 560-px candidates, rejects clipped and near-black crops
and overlaps, and keeps the three lowest fine-band-energy sites. Rejection
counts are reported separately and never folded into the accepted count.

The matched arm is what makes the absolute level irrelevant. Every arm is the
same subject, the same frames, the same registration, one pinned binary,
differing only in `k`. Subject structure is numerically identical across arms
and cancels exactly in an arm-to-arm ratio. Only ratios are quoted.

### 13.2 Commissioning, both ways, and two failures that were mine

ORCH made both-way commissioning a condition. The statistic was commissioned on
`coffee-bubbles`, four arms, all passing:

| arm | what it plants | result |
|---|---|---|
| C1 | blotch at 0.25/0.5/1.0/2.0x baseline | rises 1.006/1.017/1.103/1.284x, within 3% of quadrature |
| C2 | an improvement, strength 0.25-1.0 | falls 0.835/0.675/0.523/**0.390**x |
| C3 | a 20-60px plant, read on the sharpness column | **-0.000%** |
| C4 | a real blur, read on the sharpness column | 0.214x at r=1, 0.007x at r=2 |

C2 is the arm a blind gauge fails. C4 exists because without it C3 is
trivially satisfied by a sharpness column that never moves at all.

**Two earlier commissioning runs failed, and both failures were in my plant,
not in the statistic.** The plant was first built as
`boxblur(w,10) - boxblur(w,30)`, a difference of boxes, whose stopband
rejection is poor: it leaked into 0.20-0.25 cyc/px and moved the sharpness
column **+4.79%**, failing C3. Passing that plant through the same band filter
a second time inside `sigma_mid` then attenuated it below quadrature, failing
C1 at f >= 1.0 (0.9411 measured against 1.1387 predicted). The fix was a
brick-wall FFT bandpass at `1/60 <= f <= 1/20`, and C1 now predicts from the
plant's own measured `sigma_mid` rather than from its amplitude.

The bootstrap was commissioned separately. It resamples per-block sufficient
statistics rather than pixels; the pooled sigma so computed was checked against
a direct sigma over the same pixels on real data at **rel 1.4e-16**. The
obvious implementation -- gathering `(2000, 108, 80, 80)` -- asks for 11 GB and
was measured to hang for 17 minutes before being killed.

### 13.3 The sharpness column is commissioned per subject

`bee-1-cpl`'s sharpness column spans **1.20%** across a knob that moves its
grain by **12x**. From the number alone that is indistinguishable from a column
that cannot move on this subject -- the frozen probe -- and it is the most
expensive way to be wrong here, because it would license a default change on a
subject where the instrument is blind. So every subject's column was
commissioned on its own sites, in both directions:

| subject | planted blur r=1 | planted sharpen 1.0 | verdict |
|---|---:|---:|---|
| `coffee-bubbles` | 0.0157x | 4.0006x | responsive |
| `109MSDCF` | 0.0129x | 4.0013x | responsive |
| `119MSDCF` | 0.0150x | 4.0015x | responsive |
| `flower-bud-alone-cpl` | 0.0151x | 4.0003x | responsive |
| `bee-1-cpl` | **0.0166x** | **4.0002x** | responsive |

`bee-1-cpl`'s null is therefore real: the gate genuinely does nothing to its
textured sharpness. No row was refused.

### 13.4 The two-column sweep

`blotch` is `sigma_mid` as a ratio to the shipped arm with a 95% CI from a
paired 108-block bootstrap; `*` marks a CI excluding 1.0. `sharp` is the
compliant selection-immune `disj` statistic of section 12, confined to
0.20-0.25 cyc/px, as a delta with `*` marking a CI excluding 0. `grain` is
ORCH's `sigma_hp` on the same pixels.

`WHITE200` is k=2.0 with the pre-fix white-noise floor and was measured
pixel-identical to the shipped master. **`G200` is therefore not a sweep point:
it is the section 9 floor fix priced at the shipped k.**

| subject | N | arm | k | blotch x [95% CI] | sharp | grain x |
|---|---:|---|---:|---|---:|---:|
| `bee-1-cpl` | 299 | WHITE200 | 2.0 ship | 1.0000 | +0.00% | 1.0000 |
| | | G100 | 1.0 | 0.9858 [0.9692, 0.9954] * | -0.02% | 0.8098 |
| | | G140 | 1.4 | 0.9955 [0.9889, 0.9990] * | -0.00% | 0.9261 |
| | | G170 | 1.7 | 1.0021 [1.0006, 1.0043] * | +0.01% | 1.0039 |
| | | G200 | 2.0 | 1.0014 [0.9989, 1.0048] | -0.71% | 0.9638 |
| | | G300 | 3.0 | 0.9800 [0.9575, 0.9968] * | -1.19% | 0.2440 |
| | | G400 | 4.0 | **0.9643 [0.9298, 0.9866]** * | -0.84% | **0.0842** |
| `flower-bud-alone-cpl` | 205 | WHITE200 | 2.0 ship | 1.0000 | +0.00% | 1.0000 |
| | | G100 | 1.0 | 0.9504 [0.9299, 0.9677] * | -12.43% * | 0.8998 |
| | | G140 | 1.4 | **0.9792 [0.9686, 0.9875]** * | -2.24% | 0.9894 |
| | | G170 | 1.7 | 0.9925 [0.9893, 0.9951] * | +1.82% | 1.0073 |
| | | G200 | 2.0 | 0.9669 [0.9552, 0.9754] * | -17.41% * | 0.8676 |
| | | G300 | 3.0 | 0.8980 [0.8618, 0.9262] * | -79.98% * | 0.3105 |
| | | G400 | 4.0 | 0.8506 [0.7905, 0.8963] * | -87.30% * | 0.2384 |
| `119MSDCF` | 33 | WHITE200 | 2.0 ship | 1.0000 | +0.00% | 1.0000 |
| | | G100 | 1.0 | **0.9988 [0.9977, 0.9999]** * | +9.68% * | 0.9565 |
| | | G140 | 1.4 | 1.0000 [0.9989, 1.0012] | +16.57% * | 1.0264 |
| | | G170 | 1.7 | 0.9999 [0.9996, 1.0001] | +0.97% | 1.0045 |
| | | G200 | 2.0 | 0.9977 [0.9965, 0.9989] * | -26.79% * | 0.8697 |
| | | G300 | 3.0 | 0.9882 [0.9854, 0.9908] * | -55.52% * | 0.4009 |
| | | G400 | 4.0 | 0.9811 [0.9778, 0.9843] * | -69.12% * | 0.2502 |
| `coffee-bubbles` | 19 | WHITE200 | 2.0 ship | 1.0000 | +0.00% | 1.0000 |
| | | G100 | 1.0 | 1.0066 [1.0029, 1.0104] * | +7.46% * | 1.0832 |
| | | G140 | 1.4 | 1.0041 [1.0004, 1.0079] * | +11.74% * | 1.1125 |
| | | G170 | 1.7 | 1.0020 [1.0004, 1.0039] * | +6.47% * | 1.0513 |
| | | G200 | 2.0 | 0.9982 [0.9970, 0.9993] * | -9.87% * | 0.9283 |
| | | G300 | 3.0 | 0.9851 [0.9810, 0.9888] * | -46.65% * | 0.5811 |
| | | G400 | 4.0 | 0.9852 [0.9803, 0.9897] * | -59.20% * | 0.4490 |
| `109MSDCF` | 22 | WHITE200 | 2.0 ship | 1.0000 | +0.00% | 1.0000 |
| | | G100 | 1.0 | 1.0082 [1.0045, 1.0126] * | +87.27% * | 1.4420 |
| | | G140 | 1.4 | 1.0057 [1.0031, 1.0087] * | +43.80% * | 1.2697 |
| | | G170 | 1.7 | 0.9953 [0.9938, 0.9967] * | -10.52% * | 0.9060 |
| | | G200 | 2.0 | 0.9836 [0.9803, 0.9867] * | -39.93% * | 0.6159 |
| | | G300 | 3.0 | 0.9710 [0.9655, 0.9766] * | -70.13% * | 0.3160 |
| | | G400 | 4.0 | 0.9699 [0.9639, 0.9762] * | -82.02% * | 0.2969 |

### 13.5 The knee, and why it does not pay

The knee is the largest real blotch reduction (CI excluding 1.0) among arms
that cost no measurable sharpness (`disj` CI not excluding 0 on the low side).

| subject | N | knee | blotch | sharpness | share of the -58.8% needed |
|---|---:|---|---:|---:|---:|
| `bee-1-cpl` | 299 | G400 | **-3.57%** [-7.02, -1.34] | -0.84% null | **6.1%** |
| `flower-bud-alone-cpl` | 205 | G140 | -2.08% [-3.14, -1.25] | -2.24% null | 3.5% |
| `119MSDCF` | 33 | G100 | -0.12% [-0.23, -0.01] | +9.68% better | 0.2% |
| `coffee-bubbles` | 19 | none | -- | -- | 0% |
| `109MSDCF` | 22 | none | -- | -- | 0% |

A knee exists on three subjects of five and is worth 0.12% to 3.57%. **This
knob cannot fix the mottle.** Two subjects have no knee at all: on
`coffee-bubbles` and `109MSDCF` every arm that cuts blotch costs sharpness at a
CI that excludes zero.

**And 6.1% is an over-estimate.** ORCH's note that a subsampled minimum is a
denominator makes 2.43x a floor on the excess, so the true reduction required
is larger than 58.8% and the knob's share is smaller than 6.1%. My own
arm-to-arm ratios contain no minimum and are not lower bounds; the target they
are measured against is.

### 13.6 What the gate actually is: a grain knob

The same seven arms move the two columns by wildly different amounts:

| subject | blotch span | grain span |
|---|---:|---:|
| `bee-1-cpl` | 3.78% | **11.9x** |
| `flower-bud-alone-cpl` | 14.94% | 4.2x |
| `119MSDCF` | 1.89% | 4.1x |
| `coffee-bubbles` | 2.15% | 2.5x |
| `109MSDCF` | 3.83% | 4.9x |

On the three shallow subjects blotch moves under 4% while grain moves 2.5-4.9x.
The admission gate has authority over fine noise and almost none over mid-scale
structure. That is a mechanism statement, not a correlation: mottle at 20-60 px
survives a change that removes three quarters of the grain, so whatever creates
it is not per-pixel frame admission.

**One arm is worth ORCH's attention on the noise axis rather than the mottle
axis.** On `bee-1-cpl`, G400 buys **-91.6% grain** for a sharpness change of
-0.84% whose CI includes zero, with the column commissioned responsive on that
subject (0.0166x to a blur, 4.0002x to a sharpen). This is not the
blur-to-win failure ORCH warned about, and there is an internal check that
says so: if `bee-1-cpl`'s textured band energy were noise-dominated it would
have tracked grain down, and it did not. `r(sharp/tex, grain)` is **0.60** on
`bee-1-cpl` against 0.976-0.999 on the other four -- the only subject where the
two axes decouple. Against a 1.62x noise deficit this is the largest free move
found anywhere in this sweep. **It is one subject, and G400 is catastrophic on
the other four (-59% to -87% sharpness), so this is reported, not recommended.**

### 13.7 ORCH's "same pixels" requirement is unsatisfiable as stated

ORCH required the sharpness column on the same pixels as the blotch. It was
computed, and it is degenerate. Pearson r between the flat-site sharpness
column and grain, across the seven arms:

| subject | r(sharp/flat, grain) | r(sharp/tex, grain) |
|---|---:|---:|
| `coffee-bubbles` | 0.9956 | 0.9992 |
| `109MSDCF` | 0.9855 | 0.9880 |
| `119MSDCF` | 0.9964 | 0.9759 |
| `flower-bud-alone-cpl` | 0.9966 | 0.9921 |
| `bee-1-cpl` | 0.9922 | **0.6011** |

At r = 0.985-0.997 the flat-site sharpness column carries no information the
grain column does not. The reason is structural: a site selected **for having
no detail** has no detail to lose, so its band energy at 0.20-0.25 cyc/px is
noise, and a column reading it is a second noise column wearing a sharpness
label. The requirement cannot be met on the pixels where mottle is measurable.
The sharpness column in section 13.4 is therefore read on textured sites, and
the flat-site column is reported here only to show why it was not used.

### 13.8 The depth question: no N-dependence these five subjects can establish

| subject | N | sharpness authority | knee |
|---|---:|---:|---|
| `bee-1-cpl` | 299 | 1.20% | G400 |
| `flower-bud-alone-cpl` | 205 | 89.12% | G140 |
| `119MSDCF` | 33 | 85.69% | G100 |
| `109MSDCF` | 22 | 169.29% | none |
| `coffee-bubbles` | 19 | 70.94% | none |

`Spearman(N, sharpness authority) = -0.30` over five subjects. **Not monotone
and not significant.** Authority is highest at N=22 and lowest at N=299, but
it is 70.94% at N=19 and 89.12% at N=205, so the ordering is not depth.

The knee column looks monotone in N and must not be read that way. **N and
regime are confounded across these five subjects**: `bee-1-cpl` (N=299) is the
most selection-dominated and `109MSDCF` (N=22) the most averaging-dominated, so
any statistic ordered by regime will appear ordered by N. With five subjects
the two cannot be separated, and I am not separating them.

What can be said without separating them is the part that bears on the depth
collapse: **on the 299-frame subject, the entire gate range 1.0 to 4.0 moves
textured sharpness by 1.20% total**, with the instrument commissioned
responsive on that subject. Whatever costs `bee-1-cpl` its detail against a
comparator, the admission gate has no authority over it. This does not
exonerate the merge; it exonerates this knob.

### 13.9 What this is not

- Not a per-site-ceiling number. The sharpness column here is arm-to-arm, so it
  prices the knob, not the product. The per-site-ceiling ratios are section 12.
- Not a claim about absolute blotch level. Section 12.3's gain confound is
  unresolved and absolute levels remain withdrawn; across-arm luma varies
  <= 0.4% (<= 3.4% on `coffee-bubbles` G400), so arm-to-arm deltas are clean.
- Not a recommendation to change the default. Section 9's recommendation stays
  held, and `pyramid.rs` is closed to this lane.
- Still owed from the original pre-registration: P2 (plane arm) and P6
  (align-refused placebo).
