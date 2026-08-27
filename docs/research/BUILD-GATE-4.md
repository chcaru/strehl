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

- **The absolute levels disagree with V-EYES and this is unresolved.** V-EYES
  reads `coffee-bubbles 0.9018 / 109MSDCF 0.8855 / 119MSDCF 0.8147`; I read
  `1.1668 / 2.8206 / 1.8590` **on the same pixels** (§3 proves `WHITE200` is
  `SHIP-V4` byte for byte) with a statistic C1 proves is `patch_gain` exactly.
  So the difference is **neither the master nor a transcription error — it is
  the two lanes' instruments.** The likeliest cause is population: `patch_gain`
  scores the three most textured 560px sites; V-EYES appears to tile the whole
  frame, which includes flat regions where a merge cannot beat its best frame.
  **The rankings agree** — `bee-1` most beats its ceiling in both lanes — and my
  comparison is paired, so every delta here is valid regardless. But **the two
  absolute numbers must not be quoted side by side until this is reconciled.**
- **P2 and P6 remain untested** (§7).
- The noise axis uses one statistic on one tile class. It is commissioned, but a
  second independent noise instrument would strengthen §4.
- `bee-1-cpl` and `flower-bud-alone-cpl` resolved **2 sites**, not 3, and
  `bee-1` refused 3 of 299 registrations at one site. Both are recorded in the
  ceiling artifacts.
