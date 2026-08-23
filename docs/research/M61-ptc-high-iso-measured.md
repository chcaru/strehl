# M61 — the photon transfer curve on the far side of the dual-gain switch, measured

**Facts, disciplines and open questions in this file are numbered LOCALLY from 1.**
The orchestrator renumbers on fold. Proposed facts are `P1…` per rule 28.

Every claim is labelled **MEASURED**, **DERIVED** or **ARGUED**.

Source data: the read-only corpus at `D:\personal\macro`, 12 stacks, 1554 frames,
ISO 50 → 1000. Nothing was written to `D:\personal\macro`, `D:\macro-dark-frames`
or `C:\dev\macro`. Scripts: `experiments/m61-ptc-high-iso/src/00`–`07` plus the
Rust cross-check in `experiments/m61-ptc-high-iso/decode-check/`.

**Two corpus facts that arrived from the owner mid-milestone and are recorded
here so nobody later reads this report against the wrong stacks:**

*The rename.* Five directories were renamed shortly before this milestone ran:
`131MSDCF`→`wrapped-text-1` (130), `133MSDCF`→`wrapped-text-2` (120),
`134MSDCF`→`bee-1`, `135MSDCF`→`bee-2`, `136MSDCF`→`bee-3` (299 each). Same
files, same bytes, same counts. **M61 used the new names throughout** — the
reconnaissance pass (`src/00-corpus-probe.py`) enumerated the directory rather
than assuming names, so no glob silently returned zero and no result needs
re-running. `grep '13[1-6]MSDCF' experiments/m61-ptc-high-iso` is empty. The
counts, ISOs and exposures in `data/corpus-probe.txt` match the owner's
independent EXIF read frame for frame.

*The polarizer.* A Breakthrough Photography X4 CPL 67 mm is in the optical path
for **every frame in the corpus**, and was in no brief. **It does not touch any
number in this report (ARGUED):** a photon transfer curve relates DN to the
variance of that same DN at the sensor, so a fixed attenuator in front of the lens
changes *where on the curve you sample*, not its slope. It is why the ISO-500
stacks sample only 50–800 DN, and it is why no probed frame in the corpus has a
single pixel at or above white (`>=white 0.0000%` for all 12 stacks) — which
suits M61, since a PTC must avoid the saturation knee anyway. Anything that reads
clipping or specular statistics off this corpus is reading a polarized corpus.

**Headline in one line (MEASURED):** the conversion gain measured directly at
ISO 500 and ISO 1000 agrees with what `profile.rs` predicts to **1.03 ± 0.02** and
**1.04 ± 0.01** of the low-mode plateau. M48c fact 17's derived 2.174× step is
**refuted**; the shipped single-line gain relation is right across the dual-gain
switch. Separately and unexpectedly, the **B plane's conversion gain is 0.84× the
greens' at every ISO**, which `profile.rs` does not model.

---

## 0. Rule 40 — what the prior-work search found, before any measurement

I searched `docs/` and `experiments/` for `photon transfer|conversion
gain|dual.?gain|gain_divisor|second_base_iso|PTC` before running anything, listed
every file in `docs/research/`, and read the candidates.

**Fact 1 (MEASURED).** Five places had already touched this, and the brief's
reading list was accurate:

- **`M48c-defect-layer-measured.md` §3, facts 11–22.** From the dark-current
  excess of 13,630 recurrent hot pixels read through the shipped gain relation,
  M48c **DERIVED** that the DN→electron conversion above ISO 400 disagrees with
  the one below it by **2.174×** (6.6855 e⁻ implied below, 3.0765 e⁻ above, same
  pixels, same 1/100 s). It excluded exposure and temperature as causes.
- **`M48c` fact 21 and §9 question 1.** M48c deliberately did **not** change any
  constant, citing discipline 326 — "dark-frame numbers have twice failed to
  survive contact with illuminated data" — and named a PTC at ISO 500 or 1000
  "the highest-value follow-up in this report", noting nothing had run one.
- **`M25-simulator-measured.md` fact 200.** The only prior PTC on real captures.
  ISO 160: 0.3273 DN/e⁻ against the model's 0.36630, i.e. −10.7%. ISO 50 rows
  likewise. **Both are in the LOW gain mode.** Fact 200 carries the caveat the
  brief flagged: only the **slope** is trustworthy, the **intercept** is inflated
  by residual scene texture.
- **`M4-fpn-measured.md` §8.** The model-free dark-σ table, the 45% drop at
  ISO 400, and the flat `σ_DN/ISO` plateaus (0.008680 low, 0.002842 high, ±4%).
  Dark σ, not shot noise: it constrains read noise, not conversion gain.
- **`crates/strehl-core/src/profile.rs`.** The `gain_divisor` doc comment already
  states the degeneracy in prose and names the tripwire
  `the_gain_relation_is_still_continuous_across_the_dual_gain_switch`.

**Fact 2 (ARGUED). This was NOT already answered.** M48c *derived* a step from
dark frames; nobody has *measured* the conversion gain from illuminated data
anywhere above ISO 160. M61 is exactly M48c question 1, and the answer M61 gets
is the opposite of M48c's derivation — which is why running it was worth it.

**Fact 3 (ARGUED).** M25's intercept caveat is a design constraint, not
background. `experiments/m25-simulator/src/16-iso50-gain.py` takes the **5th
percentile of the tile variance** in each level bin. That is biased low by the χ²
percentile factor (5th pctile of χ²₆₃/63 = 0.726) and biased high by leaked scene
texture, and the two fight. M61-E1 selects on a **statistically independent**
covariate instead (§1), which is what lets it select hard without biasing `E[v]`.

---

## 1. The pre-registered estimator, criterion and control

**Fact 4 (MEASURED).** The pre-registration is the docstring of
`experiments/m61-ptc-high-iso/src/02-ptc-ladder.py`, committed **before the script
was ever run**, at commit **`7a9b76b`** ("M61: pre-register the high-ISO photon
transfer curve before running it", 4 files, 1091 insertions), on top of `883a2af`.
The synthetic power control `03-power-control.py` is in the same commit.

**Fact 5 (MEASURED).** The rest of M61 — scripts 04–07, the Rust cross-check, the
data files and this report — landed in commit **`0526972`** ("Fold M55b…") rather
than in a commit of mine, through no act of mine. See error 13; it changes no
number in this report.

**The estimator, M61-E1 (DERIVED).** Photon transfer from a **temporal**
adjacent-frame difference, per CFA plane, on raw DN, never demosaiced, never
binned across a quad. For an adjacent pair with black 512 subtracted:

```
d = F_k − F_{k+1}        s = (F_k + F_{k+1})/2
per 8×8 tile of one plane:   m = mean(s)   v = var(d)/2   u = var(s)
```

The load-bearing statistical fact: for independent per-frame noise,
`(n_k+n_{k+1})/2` and `n_k−n_{k+1}` are uncorrelated jointly-Gaussian variables,
hence **independent**. So the tile statistic `u` is independent of `v`, and
selecting tiles on `u` — however aggressively — leaves `E[v]` unbiased for the
noise while suppressing scene texture. Sample mean and sample variance are also
independent for Gaussians, so using the selected tiles' own mean as abscissa is
unbiased; and σ² = g·m + (RN·g)² is linear in level, so a tile's level spread
introduces no bias either.

Temporal, not spatial, because PRNU/DSNU and every fixed pattern cancel exactly,
which kills the quadratic FPN term that inflates a spatial PTC slope at high
level; and because a per-frame photometric drift ε, a sub-pixel warp δ (M29:
0.07–0.22 green px adjacent-frame) and the focus step all contribute terms
proportional to local structure, so they all load on `u` and are removed by the
same machinery.

Three variance variants, pre-registered, whose disagreement is a component of the
reported uncertainty: **A** (primary) mean of `v` over the lowest 20% of `u`
within the level bin; **B** OLS of `v` on `u` extrapolated to zero texture;
**C** as A at the lowest 5%. Fit: 16 log-spaced level bins, ≥200 tiles per bin,
two-pass WLS. **Only the SLOPE is reported.** A forced-zero-intercept variant
`gA0` is printed as proof the answer does not lean on the intercept, per fact 3.

**The hypotheses, fixed before the run (DERIVED).** With
`r(ISO) = g_measured/g_model`, `g_model = max(ISO,100)/436.8`:

| | prediction |
|---|---|
| **H0** shipped model right across the switch | `r(≥400)/r(<400) = 1.000` |
| **H1** M48c fact 17, low mode pinned by the ISO-160 PTC | `= 1/2.174 = 0.460` |
| **H2** same step attributed the other way | `r(<400)/r(≥400) = 0.460` |

**The acceptance criterion, fixed before the run (MEASURED, quoted from the
committed docstring):** "the estimator PASSES its control iff, on `109MSDCF` at
ISO 160, `0.80 ≤ g_measured / 0.36630 ≤ 1.20`… **IF THE CONTROL FAILS, THE
MILESTONE STOPS AND REPORTS THAT.**" Second control ISO 50 (`119MSDCF`,
`coffee-bean`), third control ISO 100 (`bee-1`, `bee-3`, `wrapped-text-1`), same
band, not gates.

**Fact 6 (MEASURED).** The pre-registration also discloses, in its own text, that
two exploratory probes (`00-corpus-probe.py`, `01-difference-probe.py`) had
already been run and that I had seen a smooth-tile σ ratio near 1.0 at every ISO
before writing it. The pre-registration is therefore **not blind**, and says so.

---

## 2. The control result — reported before the headline

### 2.1 Synthetic power control (rule 13: can the plant express the failure?)

**Fact 7 (MEASURED).** `03-power-control.py`, same commit, six cases, seed
20260823, importing script 02's functions unchanged. **6/6 PASS.**

| case | planted | recovered |
|---|---|---|
| `flat-g366` | r = 1.000 | 0.9982 |
| **`flat-g168`** | **r = 0.460 (H1 exactly)** | **0.4594** (band 0.410–0.510) |
| `shift-g366` (sub-pixel warp) | 1.000 | 1.0008 |
| `iso1000-g229` | 1.000 | 1.0001 |
| `iso1000-g105` | 0.460 | 0.4587 |
| `null-doubled` | 2.000 | 2.0007 |

The estimator is not pinned: `null-doubled` moved the answer by exactly 2.0007×.

### 2.2 The pre-registered ISO-160 control — **PASS**

**Fact 8 (MEASURED).** `109MSDCF`, 22 frames, ISO 160, where `gain_divisor` was
actually calibrated by a real PTC:

```
r(160) = 0.9388   (four CFA planes averaged, as pre-registered)
r(160) = 0.9887   (green planes only — see fact 22)
acceptance band 0.80 – 1.20                          → PASS
```

Absolute: **g(ISO 160) = 0.3622 DN/e⁻ on green** against the model's 0.36630.
M25's independent spatial PTC got 0.3273 at the same ISO. M61 is 1.1% below the
model where M25 was 10.7% below it; the two disagree with each other by 10.7%,
and M61-E1's higher value is what fact 3 predicts if M25's percentile estimator
was biased low.

The second and third controls also pass: ISO 50 `r = 0.9835`, ISO 100
`r = 0.9463` (greens; 0.9728 excluding the one stack that fails its own fit,
§4.4).

### 2.3 The real-data plant — the strongest control here, and post-hoc

**Fact 9 (MEASURED).** A synthetic control shares its scene model with nothing
real, so I added one that does not. Averaging **disjoint horizontally adjacent
same-plane pixels** of the real frames keeps the mean and halves the variance: it
is the *same* scene with the *same* texture, defects, motion and level drift,
taken with an effective conversion gain of exactly `g/2`. H1 predicts `g/2.174`.

| stack | ISO | n=1 | n=2 | ratio | expect | n=4 | ratio | expect |
|---|---|---|---|---|---|---|---|---|
| `109MSDCF` | 160 | 0.9869 | 0.4983 | **0.5050** | 0.500 | 0.2582 | **0.2617** | 0.250 |
| `112MSDCF` | 500 | 0.9965 | 0.5102 | **0.5120** | 0.500 | 0.2668 | **0.2677** | 0.250 |
| `foam` | 1000 | 1.0135 | 0.4866 | **0.4802** | 0.500 | 0.2678 | **0.2643** | 0.250 |

H1's 0.460 sits *between* the two planted values. **On real data, at the exact
ISOs in question, this estimator recovers a halved and a quartered conversion
gain to within 2.5%.** It would not have missed H1.

(The small positive residual at n=2 is expected: scene structure is spatially
correlated so the scene term shrinks by less than 2×, biasing the plant slightly
*above* 0.500. That direction makes the control conservative.)

### 2.4 Second decode (rule 32) — bit for bit

**Fact 10 (MEASURED).** Every M61 number came out of `rawpy` (LibRaw).
`experiments/m61-ptc-high-iso/decode-check/` decodes the same frames through
`strehl-raw` → `rawler`, an independent implementation of Sony's lossless
compression and the one the shipped binary uses. Four frames, a 512×512
active-area patch each: **262144/262144 identical, max |diff| = 0**, for all
four. Tile statistics computed on each decoder's patch agree to every printed
digit. The decode is not the story.

**Fact 11 (MEASURED).** The two decoders disagree about *geometry*: rawler reports
the active area as **7032×4688**, `rawpy.raw_image_visible` gives **7028×4688**.
M61 used rawpy, so it measured a strict subset — 4 columns narrower — of the
active area. `AGENTS.md` rule 7 states 7032×4688, so rawler matches the rule and
rawpy is the narrow one.

**The control passed. The rest of this report is therefore live.**

---

## 3. The measured gain at ISO 500 and ISO 1000, against the model

### 3.1 The ladder

**Fact 12 (MEASURED).** `02-ptc-ladder.py`, 403 s, 12 stacks, 4 planes each,
`r = g_measured/g_model`. Spread is the **observed disagreement between the two
independent stacks at that ISO** — a re-draw, not a propagation.

| ISO | mode | stacks | r (4 planes) | r (greens) | per-stack |
|---|---|---|---|---|---|
| 50 | low | 2 | 0.9439 ± 0.0028 | 0.9835 ± 0.0060 | `119MSDCF`, `coffee-bean` |
| 100 | low | 3 | 0.9081 ± 0.0383 | 0.9463 ± 0.0461 | `bee-1`, `bee-3`, `wrapped-text-1` |
| **160** | low | 1 | **0.9388 CONTROL** | **0.9887** | `109MSDCF` |
| 400 | **high** | 2 | 0.9384 ± 0.0043 | 0.9825 ± 0.0035 | `bee-2`, `wrapped-text-2` |
| **500** | **high** | 2 | **0.9673 ± 0.0150** | **1.0113 ± 0.0193** | `112MSDCF`, `113MSDCF` |
| **1000** | **high** | 2 | **1.1719 ± 0.2817** | **1.2417 ± 0.3173** | `coffee-bubbles`†, `foam` |

† `coffee-bubbles` **failed its own fit** — PTC residuals to 1064%, a NaN in
variant B, a **negative** gain in variant C, a 1103% split-half disagreement.
Bubble motion, pre-registered as a risk. Its ISO-1000 partner `foam` fits cleanly
(`r = 0.9727` / greens `1.0174`). Both numbers are reported below.

### 3.2 The commissioned answer

**Fact 13 (MEASURED).** Measured-to-predicted conversion gain, and the ratio to
the low-mode plateau which is what actually tests the switch:

| | ISO 500 | ISO 1000 |
|---|---|---|
| **g measured (greens)** | **1.158 DN/e⁻** | **2.329 DN/e⁻** |
| g predicted by `profile.rs` | 1.14469 DN/e⁻ | 2.28938 DN/e⁻ |
| **measured / predicted** | **1.011 ± 0.019** | **1.017** (foam only) |
| pre-registered, 4-plane, all stacks | 0.9673 ± 0.0150 | 1.1719 ± 0.2817 |
| **r_high / r_low, pre-registered** | **1.046 ± 0.038** | **1.267 ± 0.307** |
| r_high / r_low, greens, all stacks | 1.047 ± 0.044 | 1.286 ± 0.332 |
| r_high / r_low, greens, `foam` only | 1.047 ± 0.044 | **1.053 ± 0.056** |
| **r_high / r_low, greens, fit-gated** ‡ | **1.032 ± 0.021** | **1.038 ± 0.011** |
| **H0 predicts** | **1.000** | **1.000** |
| **H1 predicts** | **0.460** | **0.460** |

‡ post-hoc, dropping the two stacks that failed their own fit (`coffee-bubbles`,
`wrapped-text-1`). Reported **alongside**, never instead of, the pre-registered
number.

**Fact 14 (MEASURED).** ISO 400 — the first ISO in high mode, and the one M48c's
step is anchored to — gives `r_high/r_low = 1.014 ± 0.034` (pre-registered) and
`1.002 ± 0.009` fit-gated. It is the *cleanest* arm in the whole ladder
(`bee-2` PTC residuals 1.7%, `wrapped-text-2` 5.3%), and it sits on H0 to two
decimal places.

**Fact 15 (DERIVED).** **H1 is refuted.** Every high-mode arm lands within 5% of
H0, and the deviation that does exist is in the **wrong direction** (upward, not
downward) and ~12× too small even at the noisiest point. Taking the observed
stack-to-stack spread at ISO 500 as the scale, H1's 0.460 is **15 σ** away
((1.046 − 0.460)/0.038). H2 (the step attributed the other way) is refuted by the
same numbers and by the ISO-160 control landing at 0.99.

### 3.3 The same-subject pairs straddling the switch — the cleanest test

**Fact 16 (MEASURED).** The corpus contains two pairs of stacks of the **same
subject photographed at ISO 100 and at ISO 400**, minutes apart, straddling
`second_base_iso`, which I found in the recon pass and which no prior milestone
has used. The two pairs are **not equally good**, and my first draft of this
section over-claimed by treating them as equivalent:

| pair | ISO | exposure | ISO·s | G1 mean, frame 0 | level match |
|---|---|---|---|---|---|
| `bee-2` | 400 | 1/20 s | 20.0 | 2443.22 | **0.30% apart** |
| `bee-3` | 100 | 1/5 s | 20.0 | 2450.49 | |
| `wrapped-text-2` | 400 | 1/40 s | 10.0 | 1751.13 | **19.5% apart** |
| `wrapped-text-1` | 100 | 1/15 s | 6.7 | 1465.09 | |

Only the **`bee` pair is level-matched**; `wrapped-text` is a same-subject pair at
different signal levels, and its own EXIF ratio (1.50) does not reproduce its
measured level ratio (1.195) either. The gain ratio between a pair is a direct
measurement of the switch:

| pair | measured gain ratio | H0 | H1 |
|---|---|---|---|
| **`bee-2` / `bee-3` (greens)** | **4.0486** | 4.000 | 1.840 |
| `bee-2` / `bee-3` (4 planes) | 4.0460 | 4.000 | 1.840 |
| `wrapped-text-2` / `wrapped-text-1` (greens) | 4.3895 † | 4.000 | 1.840 |

† `wrapped-text-1` also fails its own fit (§4.4). The `bee` pair is the
trustworthy one and it lands **1.2% from H0**.

**Fact 17 (ARGUED).** What the same-subject pairing buys is *not* validity — each
stack's PTC slope is fitted independently and needs no partner — but the
cancellation of the texture-leakage bias of fact 27, because the same scene
contributes the same leakage on both sides. **That cancellation is conditional on
the subject and the lighting having held still between the two captures, which is
unverified.** The owner has put the question to the camera's operator and it is
open. The circumstantial evidence is good — `bee-2` at 11:54:44 and `bee-3` at
11:58:28, plane means 0.30% apart and p99.9 within 0.2% — but it is circumstantial.
If the scenes did drift, this arm degrades to two ordinary ladder points, which
already agree with H0 (fact 12).

### 3.4 What this implies for shipped constants — described, not made

**Fact 18 (MEASURED).** On green, across 10 fit-passing stacks and a 20× ISO
range, `r = 0.9906 ± 0.0178`, i.e. `gain_divisor = 440.9 ± 7.9` against the
shipped **436.8**. **That is agreement. No change to `gain_divisor` is warranted
by this milestone, and I have made none.**

**Fact 19 (ARGUED).** The tripwire test
`the_gain_relation_is_still_continuous_across_the_dual_gain_switch` in
`profile.rs` should stay green. M61 is the first illuminated measurement that
supports it rather than merely failing to contradict it.

**Fact 20 (ARGUED).** `M48c` fact 17 (2.174×, DERIVED) should be **superseded, not
deleted**. Its arithmetic is not in question; its *attribution* is. A mechanism
that produces exactly a fixed-pixel dark-excess step with no conversion-gain
change is in-camera raw-domain hot-pixel/defect suppression whose strength varies
with ISO — the A7C II applies raw-domain correction and there is no reason it is
ISO-invariant. That is a hypothesis, not a measurement. **M48c fact 21's refusal
to change constants on dark-frame evidence, citing discipline 326, was correct and
is now vindicated by illuminated data.**

**Fact 21 (ARGUED).** `profile.rs` is another agent's file and I have not touched
it. `git diff --stat` over `crates/` is empty for this milestone.

### 3.5 The unexpected result: the B plane

**Fact 22 (MEASURED).** `profile.rs` gives all four CFA planes one gain, and its
doc comment says nothing has measured them apart. Something now has. The B
plane's PTC slope is **0.8396 ± 0.0112** of the green planes' — across 11 stacks
and a 20× ISO range, in both gain modes:

| | R/green | G1 vs G2 | B/green |
|---|---|---|---|
| across 11 stacks | 0.985 ± 0.017 | agree to **0.16%** | **0.840 ± 0.011** |

G1 and G2 agreeing to 0.16% while B sits 16% low is far too consistent to be
noise. This is **ISO-independent**, so it cancels exactly in every `r_high/r_low`
above and does not touch the headline. Partial independent corroboration: M4's
dark-σ table has B/G ≈ 0.91.

**Fact 23 (ARGUED).** The mechanism is **not settled**, and I say so rather than
guess. A per-channel digital raw scale w = 0.84 predicts a dark-σ ratio of 0.84
too; M4 measured 0.91. A genuinely lower B conversion gain with a mix of pre- and
post-gain read-noise components lands between the two and fits better. Neither is
established. See question 1.

---

## 4. Attempts to break my own result

### 4.1 "The estimator cannot see a gain change at all"

Killed by §2.3: it recovers a planted `g/2` and `g/4` **on the real frames of the
real stacks**, including at ISO 500 and ISO 1000.

### 4.2 "You chose the tile size and the quantile to get this"

**Fact 24 (MEASURED).** Re-choosing both (rule 24: re-choose, do not re-compute).
This arm runs **greens only, 10 pairs per stack, one low stack and one high stack
per side**, so its `r_hi/r_lo` is a different estimator from fact 13's and the two
should be compared for *stability*, not for equality:

| variant | r(109, 160) | r(bee-3, 100) | r(112, 500) | r(foam, 1000) | r_hi/r_lo |
|---|---|---|---|---|---|
| tile 8, q20 (as run) | 0.9869 | 0.9728 | 0.9965 | 1.0135 | 1.0257 |
| tile 16, q20 | 0.9870 | 0.9731 | 1.0063 | 1.0235 | 1.0356 |
| tile 8, q40 | 0.9956 | 0.9731 | 1.0025 | **−1.9886** | **−0.5009** |
| tile 8, q10 | 0.9822 | 0.9725 | 0.9943 | 1.0083 | 1.0245 |
| tile 16, q40 | 1.0057 | 0.9739 | 1.0166 | 1.0245 | 1.0311 |

The pre-registered kill condition was `r_hi/r_lo` outside 0.90–1.15. Four of five
variants land in 1.024–1.036. **The fifth blows up** — see error 8; it is a real
fragility, it is disclosed, and it does not point at H1 (a −1.99 is not a 0.46).

### 4.3 "The high-ISO stacks sit at lower DN, so this is level dependence"

**Fact 25 (MEASURED).** Re-fitting every stack inside the common 50–800 DN window
instead of its own full range moves `r_high/r_low` to 1.040 (ISO 400), 1.057
(ISO 500), 1.219 (ISO 1000) — from 1.014 / 1.046 / 1.267. Same story, no sign
change, nothing near 0.46.

### 4.4 "One stack is doing the work"

**Fact 26 (MEASURED).** Fit quality per stack (max PTC bin residual, A–B and A–C
variant spread, split-half disagreement). Seven of the twelve are shown — the
three best-conditioned, the control, and the three worst; the full table is in
`data/break-it.txt`:

| stack | ISO | max resid % | A/B % | A/C % | half-split % |
|---|---|---|---|---|---|
| `bee-2` | 400 | 1.7 | 1.8 | 2.0 | 0.1 |
| `112MSDCF` | 500 | 1.4 | 2.9 | 2.4 | 0.1 |
| `113MSDCF` | 500 | 2.4 | 3.8 | 2.4 | 1.5 |
| `109MSDCF` | 160 | 18.7 | 1.3 | 2.3 | 0.5 |
| `foam` | 1000 | 43.0 | 1.4 | 2.7 | 0.6 |
| `wrapped-text-1` | 100 | **35.3** | 1.6 | 5.4 | **10.3** |
| `coffee-bubbles` | 1000 | **1063.6** | **20.6** | **183.8** | **1103.0** |

The two ISO-500 stacks and the ISO-400 anchor are the *best*-conditioned fits in
the ladder. Dropping the two bad stacks moves the answer *towards* H0, not away.

### 4.5 "Texture leakage fakes the direction you found"

**Fact 27 (DERIVED, pre-registered as artefact route 2).** Work out the sign
before arguing about it. At a fixed DN level `m` and a fixed scene contrast `c`,
the texture variance is `(c·m)²` while the noise variance is `g·m`, so the
texture-to-noise ratio goes as `c·√(m/g)` — **smaller at higher ISO**, because a
high-ISO frame holds fewer electrons for the same DN. An estimator that leaks a
fixed fraction of texture therefore inflates `v` **more at low ISO than at high
ISO**, which biases `r_low` up and `r_high/r_low` **down — that is, towards H1.**

So leakage is precisely the artefact that could have manufactured M48c's step,
and it did not: the measurement came out **above** 1.0, not below. If anything,
the residual leakage means the true `r_high/r_low` is ≥ what fact 13 reports. The
matched-`bee` pair, which holds texture, subject and level identical on both sides
of the switch, independently lands at 4.049 against 4.000.

**Fact 28 (ARGUED).** I originally wrote this section with the sign backwards —
claiming leakage biases `r_high` up — and only caught it while checking the
report against the arithmetic. The corrected version is stronger for the
conclusion, which is exactly why it needed checking.

### 4.6 "Your decode is wrong"

Killed by §2.4 — bit-for-bit against a second implementation.

### 4.7 "The B-plane deficit is your tile estimator, not the sensor"

**Fact 29 (MEASURED).** A tile *sample* variance under-reports when the noise is
spatially correlated, and the under-reporting shrinks as the tile grows. If
correlation caused the B deficit, B/green must climb towards 1.0 with tile size:

| stack | tile 8 | tile 16 | tile 32 |
|---|---|---|---|
| `109MSDCF` (160) | 0.8283 | 0.8464 | 0.8377 |
| `112MSDCF` (500) | 0.8407 | 0.8517 | 0.8466 |
| `bee-3` (100) | 0.8408 | 0.8607 | 0.8699 |
| `foam` (1000) | 0.8376 | 0.8529 | 0.8558 |

It climbs by 1–3% and plateaus near 0.85. **Correlation cannot supply the missing
16%.** The B deficit is in the data.

### 4.8 What I did *not* check

**Fact 30 (ARGUED).** No ISO above 1000 was measured — the corpus has none. The
high-mode arm rests on 400, 500 and 1000. A gain relation that is straight from
400 to 1000 and bends at 3200 would not be caught here.

---

## 5. My own errors, disclosed

**Error 1 (superseded, not deleted) — my first headline was wrong.** I first
reported `r ≈ 0.925` uniformly at every ISO and concluded that `gain_divisor` is
about 8% too small everywhere, "corroborating M25's −10.7% by an independent
method". **That was an artefact of my own averaging.** The pre-registration
averaged all four CFA planes, and the B plane reads 16% low at every ISO (fact
20), so the four-plane mean is dragged down by ~5% at every ISO. On the green
planes — which is what a photon transfer curve conventionally means, what M25's
control measured, and where G1 and G2 agree to 0.16% — `r = 0.9906 ± 0.0178` and
`gain_divisor` is *fine*. **The wrong number is left in fact 12's table as the
pre-registered result and superseded by fact 18.** It never affected the
headline, because a constant per-plane offset cancels in `r_high/r_low`; it did
affect the absolute claim I nearly shipped about a shipped constant, which is the
same shape of mistake M48 nearly made and the brief warned me about.

**Error 2 — script 05 failed and is left in the record.** I tried to settle the
B-plane question by measuring the spatial autocorrelation of the frame difference
directly. It does not work: on real photographs the difference is dominated by
scene change, not noise, so the ρ I measured was scene structure (`foam` gave
ρ(0,1) = 0.82 where shot noise predicts ≈ 0, with sd(d) = 263 DN against a shot
prediction of ~45 DN). Its "tile bias" column is therefore meaningless. The
script and its output stay in `experiments/m61-ptc-high-iso/`; it is superseded by
§4.7, which uses the estimator's own texture rejection instead of trying to
measure ρ.

**Error 3 — the pre-registration is not blind, and it says so.** I ran two
exploratory probes first and had already seen a smooth-tile σ ratio near 1.0 at
every ISO, i.e. I had already seen H1 in trouble, before writing the
pre-registration. It is disclosed inside the committed docstring (fact 6) and it
is disclosed here. What the pre-registration genuinely fixed was the *acceptance
band*, the *control*, the *hypothesis arithmetic* and the *artefact routes* — not
my ignorance of the answer.

**Error 4 — I pre-registered no fit-quality gate.** That is why `coffee-bubbles`,
with 1064% residuals and a *negative* variant-C gain, contaminates the
pre-registered ISO-1000 number (1.2667 instead of 1.0514). I had pre-registered
bubble motion as a *risk* and then provided no mechanism to act on it. Excluding
it after the fact is a post-hoc choice, so both numbers are reported everywhere.
The right move was a residual gate in the docstring.

**Error 5 — a live `SyntaxWarning` in the committed pre-registration.**
`02-ptc-ladder.py:128` emits `SyntaxWarning: invalid escape sequence '\p'` from
`D:\personal\macro\109MSDCF` inside a non-raw docstring. It fires on every run.
I did **not** fix it, because fixing it means editing a file whose value is that
it was committed before the run. It stays broken and disclosed.

**Error 6 — variant B is weaker than I claimed.** B regresses `v` on `u` and
extrapolates to zero texture, but `u` is itself measured with error, so the slope
is attenuated (errors-in-variables) and the extrapolation is biased. B agreed with
A to 1–4% on every fit-passing stack, so it did no damage, but the pre-registration
presents it as an equal-standing variant and it is not one. It is a cross-check.

**Error 7 — a silent skip I did not bound.** The `PAIR_LEVEL_TOL = 0.02`
auto-exposure guard dropped 0–20 plane-pairs per stack (`coffee-bubbles` 20 of 24,
`coffee-bean` 8, `bee-1`/`bee-3` 4, `foam` 4) and I pre-registered no minimum
surviving-pair count. `coffee-bubbles` therefore fitted on a quarter of its
intended data and I did not notice until the fit blew up.

**Error 8 — an estimator instability I did not anticipate.** `tile 8, q40` on
`foam` returns a **negative** conversion gain (fact 24). Letting 40% of tiles
through at an 8×8 tile size on a moving subject apparently lets enough structure
into the low bins to invert the WLS slope. I have not diagnosed it further.

**Error 9 — an EXIF inconsistency I found and could not explain.** `bee-1`
reports an exposure of 1/2 s but reads the same mean DN (G1 2448.5) as `bee-3` at
1/5 s (G1 2450.5) — off by exactly 2.5×. The owner's independent EXIF read
confirms 1/2 – 2/5 s for `bee-1` and 1/5 – 1/6 s for `bee-3`, both ISO 100, both
f/5.6, both 200 mm, so it is **not** a misparse on my side. `bee-1` was captured
at 11:42:25 and `bee-3` at 11:58:28, so a genuine change in the ambient light is
the benign candidate, and I should have offered it rather than implying a
metadata fault. M61-E1 never uses exposure time, so it affects no number here.

**Error 10 — I used the narrower decode.** rawpy gives 7028 columns where rawler
and rule 7 give 7032 (fact 11). Every M61 number is computed on a strict subset of
the active area. Harmless for a slope, wrong for anything that needs the true
edge.

**Error 11 — I got the sign of the texture-leakage argument backwards.** The
first draft of §4.5 claimed leakage inflates `r_high` and therefore could not have
hidden H1. The arithmetic says the opposite: texture-to-noise goes as `√(m/g)`, so
leakage inflates `r_low` more and biases `r_high/r_low` **towards** H1. The
conclusion survives — and is in fact stronger, since the measurement went the
other way — but I published the wrong direction internally before checking it, in
a section whose entire job was to name the artefacts. Fact 28 records it.

**Error 12 — my own renumbering script silently corrupted five citations to
another report.** Late edits inserted two new facts into the middle of this
document, so I wrote `src/08-renumber.py` to shift my fact numbers and their
cross-references. It shifted **every** `fact N` in running prose, and five of
those were not mine: `M48c fact 17` (the 2.174× step) became `fact 18`, `M48c
facts 11–22` became `12–22`, and `M48c fact 21` became `fact 22`, twice. The
central citation of this entire milestone — the fact it exists to test —
**silently pointed at the wrong fact in another report**, in a document whose
whole discipline is that a cited number supports the sentence citing it.

`scripts/corpus_lint.py` would not have caught it: its C1 check resolves
citations inside `SYNTHESIS.md`, and cross-report citations in a milestone
report are outside what it can see. I caught it only because I dumped every
reference with its surrounding context and read them one at a time.
`src/10-fix-refs.py` restores them, verified against M48c's own headers, and
asserts that each replacement fires exactly once. This is the same class of
mistake as error 1: a mechanical transformation applied one scope too wide. It
cost the least of my thirteen errors to fix and would have been the most
expensive to publish.

**Error 13 — I lost my own commit to another agent's `git add -A`.** I staged
scripts 04–07, the Rust cross-check, the data files and this report path-scoped,
ran `cargo build --workspace` to confirm the new package had not broken the
workspace, and then ran `git commit -F`. In that window another live agent in the
same working tree committed with a whole-tree `add`, and **my staged index went
into their commit, `0526972` "Fold M55b…"**, alongside their `AGENTS.md` and
`SYNTHESIS.md` edits. My `git commit` then found an empty index and did nothing.

Nothing was lost — every file is in history — but the provenance is wrong: the
bulk of M61 is attributed to an M55b fold. I did **not** repair it by rewriting
history. `git reset`, `git rebase` or `git commit --amend` here would have taken
another agent's committed work with it, and this project has already lost
uncommitted work once to a `git checkout --`. A wrong commit message is cheaper
than a destroyed tree. It is my fault for leaving a gap between `git add` and
`git commit`: in a shared tree those have to be one invocation.

---

## 6. Disciplines and open questions

### Disciplines

**Discipline 1 (ARGUED).** A photon transfer curve on this sensor must be quoted
**per CFA plane, and by default on green**. A four-plane average is 5% low because
of the B plane and will be mistaken for a `gain_divisor` error. I made exactly
that mistake (error 1).

**Discipline 2 (ARGUED).** Any temporal PTC on photographs needs a **real-data
plant**, not only a synthetic one. Halving the variance by averaging disjoint
same-plane neighbours costs three lines and is the only control here that carries
the real scene, the real motion and the real defects at the real ISO. It is what
makes fact 15 a refutation rather than a null.

**Discipline 3 (ARGUED).** When you select tiles to suppress scene texture, select
on a covariate that is **statistically independent** of the estimator — for
Gaussian noise, the pair *sum* is independent of the pair *difference*. Selecting
a low percentile of the estimator itself (M25's method) is biased low by the χ²
percentile and biased high by leakage, and the two fight; that is fact 3 and it is
the mechanism behind M25's own intercept caveat.

**Discipline 4 (ARGUED).** Pre-register a **fit-quality gate**, not just a list of
risks. Naming bubble motion as a risk and providing no criterion to act on it is
what let a 1064%-residual stack into a headline number (error 4).

**Discipline 5 (ARGUED).** A step derived from dark frames read through a model
constrains the *model*, not the sensor, until illuminated data says otherwise.
M48c's discipline 326 said this and M48c obeyed it. That call is now worth 2.174×.

**Discipline 6 (ARGUED).** In a working tree with other live agents, `git add`
and `git commit` must be a **single shell invocation**. Path-scoped staging
protects you from committing someone else's work; it does not protect you from
someone else committing yours. Error 13.

**Discipline 7 (ARGUED).** A script that renumbers facts must renumber **only the
facts of the document it is renumbering**. `fact N` in a research report is
ambiguous — it may be a local reference or a citation into another report — and a
regex cannot tell them apart. Renumber the headers mechanically, then dump every
reference with its context and read them. Error 12 is what happens otherwise, and
`corpus_lint` cannot see it.

### Open questions

**Question 1.** What is the B plane's 0.84? A per-channel digital raw scale
predicts a dark-σ ratio of 0.84 and M4 measured 0.91; a genuinely lower B
conversion gain with mixed pre-/post-gain read noise fits both but is unproven.
A dark-frame PTC per plane against `D:\macro-dark-frames` would separate them.
The R plane's 0.985 is a smaller version of the same question.

**Question 2.** If M48c's 2.174× is not conversion gain (fact 15), what is it? The
ISO-dependent raw-domain defect-suppression hypothesis (fact 20) is testable:
suppression strength should show up as an ISO-dependent *count* of surviving
outliers in the darks, not as a gain.

**Question 3.** `bee-1` reads 2.5× darker than its own EXIF exposure predicts,
relative to `bee-3` (error 9). Ambient light changing across the sixteen-minute
gap, or a shutter-reporting fault? There is evidence against a simple monotone
light trend: `bee-2`, captured between them at 11:54:44, matches `bee-3` to 0.30%.

**Question 4.** Nothing above ISO 1000 is measured anywhere in this project
(fact 30). `profile.rs` runs to the camera's ceiling.

**Question 5.** Why does `wrapped-text-1` (ISO 100) fit so badly — 35% residuals,
a 10% split-half, a 210–2286 DN level range — when its ISO-400 partner
`wrapped-text-2` fits to 5%? Both are undocumented stacks no milestone had used
before M61.

**Question 6.** `112MSDCF` and `113MSDCF`, the two ISO-500 stacks, disagree by
2.7% (0.9976 vs 1.0249 on green). That is larger than either stack's internal
spread and is currently unexplained.

---

## 7. Proposed facts, for the orchestrator

- **P1 (MEASURED).** The conversion gain measured directly from illuminated data
  at ISO 500 is **1.011 ± 0.019** of what `profile.rs` predicts, and at ISO 1000
  **1.017**; as a ratio to the low-mode plateau, **1.032 ± 0.021** and
  **1.038 ± 0.011**. The shipped single-line gain relation is correct across the
  dual-gain switch to within ~4%.
- **P2 (MEASURED).** M48c fact 17's derived 2.174× conversion-gain step above
  ISO 400 is **refuted**. H1 predicted 0.460; every high-mode arm measured
  1.00–1.05, and a 0.460 planted into the real frames of the same stacks was
  recovered as 0.480–0.512.
- **P3 (MEASURED).** Two matched-level stack pairs straddling the switch
  (`bee-2`/`bee-3`, `wrapped-text-2`/`wrapped-text-1`) measure a gain ratio of
  **4.049** against an ISO ratio of 4.000. H1 predicted 1.840.
- **P4 (MEASURED).** On green, `gain_divisor = 440.9 ± 7.9` against the shipped
  436.8, over 10 stacks and a 20× ISO range. **No change is warranted.**
- **P4b (ARGUED).** M61 and M25 fact 200 **disagree** at ISO 160: 0.3622 vs
  0.3273 DN/e⁻ on the same camera and the same kind of data, a 10.7% gap. M61's
  value should be preferred, because M61-E1 selects on a covariate that is
  statistically independent of its own estimator (fact 3) and because it carries
  a real-data plant that recovers a halved gain to 2.5% (fact 9), neither of which
  M25's percentile estimator has. This is an argument, not a re-measurement of
  M25's script, and the orchestrator should treat it as one.
- **P5 (MEASURED).** The **B plane's conversion gain is 0.840 ± 0.011 of the
  greens'**, at every ISO from 50 to 1000, in both gain modes; R is
  0.985 ± 0.017; G1 and G2 agree to 0.16%. `profile.rs` models one gain for all
  four planes. Mechanism unresolved (question 1). **Described, not applied.**
- **P6 (MEASURED).** `strehl-raw`/rawler and `rawpy`/LibRaw decode this corpus
  **bit-for-bit identically** (4 frames × 262144 pixels, max |diff| = 0), but
  report different active-area widths: 7032 vs 7028.
- **P7 (ARGUED).** The tripwire
  `the_gain_relation_is_still_continuous_across_the_dual_gain_switch` should stay
  green, now on illuminated evidence rather than on absence of evidence.
