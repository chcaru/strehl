# M101 — sensor defects, the focus measure, and whether the election cares

**Facts, disciplines and open questions in this file are numbered LOCALLY as
`P1, P2, …` per rule 28.** The orchestrator allocates absolute numbers at fold.

Every claim is labelled **MEASURED**, **DERIVED** or **ARGUED**. An unlabelled
claim is unfounded and should be read as such.

**Source revision:** `6a8ac30` (`corpus: the complaint is sharpness, and exposure
is not the answer`).

**Read-only inputs, never written to:** `D:\macro-dark-frames` (242 frames),
`D:\personal\macro` (23 stacks). Scratch: `C:\dev\strehl-out\M101\`.
Scripts: `experiments/M101-defect/src/`.

---

## 0. The commission, and the prior work my brief did not name

### 0.1 What I was asked

> *The sensor has permanent defects, the focus measure loves them, and nothing
> in the pipeline defends against that.*

The mechanism as briefed: `box_mean_27(|Sobel L|) / sigma(L)` is a local energy
detector, a hot pixel is a local maximum of gradient energy, so the election has
a systematic reason to prefer whichever frame puts a hot pixel on the pixel being
decided. Defects are fixed in **sensor** coordinates; the scene translates up to
**232.7 plane px** across a stack under breathing (fact 1177). So the defect is
dragged across the scene and a single hot pixel is a candidate to produce a
**trail**, not a dot.

Deliverables, in order: build the defect map and prove it is a map; run *the
deciding measurement* — does this touch the owner's photographs; and build the
correction **if and only if** the deciding measurement justifies it.

### 0.2 Prior work. My brief named none of it, and it is extensive

Rule 40 requires the dispatch to name every prior report on the question, and
rule 43 requires that an assertion of absence carry the search that establishes
it. **My brief contains neither.** It presents the defect map as work to be done
and the darks as freshly delivered calibration data — *"The owner has delivered
the calibration data"* — with no reference to the fact that these exact 242
frames have been used for this exact purpose twice. I searched
`docs/research/` before measuring anything and found:

| report | what it already settled | facts |
|---|---|---|
| `M22-hot-pixels-measured.md` | Built the map from these 242 darks. **Recurrence across the 11 ISO groups, not a sigma threshold, is the discriminator.** Defensible map **11,393 px = 0.0346%** at >= 6/11 groups. In-situ impact **<= 0.39 sigma**, excess flat at ~3 DN across three signal decades. Only **3 pixels** sensor-wide are always-hot and > 100 DN. | 160, 161, 162 |
| `M48c-defect-layer-measured.md` | Independent census: **13,650 = 0.0414%**, corroborating M22 to 19.8% by a different criterion. **99.8% singletons, largest cluster 3 px, no rows or columns.** **68x odd/even sensor-row asymmetry** (R 101, G1 98, G2 7,757, B 5,674). Measured the merge **blind**: `D_defect/D_control = 1.00 +/- 0.08` against a contrast-matched control. | 783-808 |
| `M29-static-defects-measured.md` | Dust. `D = 0.999` at `n_eff = 3`; suppression is bought by the **span** of frames averaged, not their count. | 230-234 |
| `M48-read-noise-measured.md` | The hot-pixel tail explains ~1/10 of the read-noise estimator gap; oracle excision of M22's whole map moves pooled RMS **1.1-1.8%**. | — |

So §1 of my commission is, in large part, **a replication**. I have run it as
one — the corpus rule is *"reproduce one published number from the original data
before extending anyone's experiment"* — and the two committed censuses are my
external positive control.

**The part that was genuinely open is exactly the part my brief calls the
deciding measurement**, and both prior reports name it in their own words:

- M22 §7: *"**Smearing under warp.** The review's specific worry — that
  fixed-sensor defects smear into trails once frames are warped — was not tested
  at all. It requires the aligner, and it is the right follow-up if this is
  built."*
- M48c fact 30: *"Today `D_defect/D_control = 1.00 +/- 0.08` because nothing
  moves. When alignment lands, a sensor-fixed defect **will** land on different
  scene points in different frames while real detail does not… **Re-running
  script 07 unchanged after alignment is a ready-made, pre-registered acceptance
  test for a subsystem that does not exist yet.**"*

That subsystem now exists. M86 built the solve, M97 wired it into `strehl stack`
at `885e9f7` and it is **on by default**. M101 is the first milestone that can
run M48c's registered test, and the trail question is therefore the centre of
this report rather than a side arm.

### 0.3 One number in my brief does not come from the corpus

The brief states the noise model as *"A7C2 gain ~0.229 DN/e-, RN ~3 e-"*. The
gain is right: `profile.rs` ships `gain_dn_per_e = max(iso, 100)/436.8`, which is
**0.22894 DN/e-** at ISO 100. **`RN ~3 e-` is not a shipped or measured
constant.** `profile.rs` ships `read_noise_e_low = 4.20` (ISO < 400) and
`read_noise_e_high = 1.2392` (ISO >= 400); fact 795 records that read *in
electrons* the high mode is ~2.69 e-, but that is a re-labelling of 1.2392 and is
explicitly not what the model evaluates. Every sigma in this report is computed
from the shipped constants, at the shipped values, and named per ISO.

---

## 1. Pre-registered bars

Written and committed **before** any of the measurements below was run.
Verify with `git log --diff-filter=A -- docs/research/M101-defect.md` and compare
against the commit that adds each result.

### 1.1 The map (§1 of the commission)

**Method, fixed in advance.** Per ISO group (11 groups of 22, frames 3-22 kept,
n = 20 — the owner's *"first 2 shots for stablization"*, which §2.1 checks rather
than assumes): temporal mean, minus black 512, split into the four CFA planes at
the RGGB offsets `CfaPlane::rggb_at` uses. The statistic is the **excess of a
sample over the median of its eight same-plane neighbours**, centre excluded.

**Two thresholds, both stated in sigma, neither chosen by eye:**

- **T-model.** `sigma_model = sigma_pred(S = 0, ISO) / sqrt(20) * c_med`, with
  `sigma_pred(0, ISO) = read_noise_e(ISO) * gain(ISO)` from `profile.rs`, and
  `c_med = sqrt(1 + 1.5708/8) = 1.09371` — the asymptotic variance inflation of a
  median of eight. At ISO 100 that is `0.96154/sqrt(20)*1.09371 = 0.23514 DN`.
  **K = 6.**
- **T-robust.** The same statistic with `sigma = 1.4826 * MAD(excess)` measured
  per plane per group. **K = 6.** This is M22's and M48c's form and is what makes
  my census comparable to theirs.

**Pre-registered prediction P-A (inherited, not mine): T-model over-flags**,
because the shipped noise model has no DSNU term and cannot describe the
pixel-to-pixel spread of a dark frame (M48c fact 4). I register the ratio
`sigma_robust / sigma_model` per plane per ISO as the measurement of that gap.
Reporting a threshold that was declared and then failed is evidence about the
model, not clutter.

**Recurrence.** A defect is a site flagged in **>= 6 of the 11 ISO groups**,
adopted unchanged from M22/M48c for comparability. Cold defects: the same with
the sign reversed.

**Bars:**

- **B1 — split-half reproducibility.** Within each ISO group, split the 20 frames
  into two disjoint random halves of 10; build a full map from each half.
  **Bar: Jaccard(A, B) >= 0.80.** Below that, the threshold is cutting into noise
  and the map is not a map. *(0.80 is set from the structure of the problem, not
  from a result: the two halves see the same silicon with independent noise, so a
  well-separated population should reproduce nearly perfectly; 0.80 leaves room
  for the sites sitting on the recurrence boundary and nothing more.)*
- **B2 — placebo.** The identical Jaccard computed on two uniformly random
  coordinate sets of the same sizes, drawn per plane. **Bar: <= 0.01**, and it is
  reported beside B1 in every table. Analytic chance is `|A| / (2N - |A|)`
  ~ 2e-4 at this density; the empirical draw is what is reported.
- **B3 — external replication (positive control).** My >= 6/11 census must land
  within **+/-25%** of M48c's committed **13,650** and of M22's **11,393**.
  *(+/-25% is the width of the existing agreement between the two prior
  censuses — 19.8% — not a tolerance invented to pass.)*
- **B4 — does one map serve all ISOs?** Build a low-mode map (ISO 50/100/200/250,
  recurrence >= 3/4) and a high-mode map (ISO 400-2000, recurrence >= 4/7).
  **Bar for "one map serves all ISOs": the low-mode map must be >= 90% contained
  in the high-mode map.** Direction registered in advance from physics: dark
  current is generated before the analogue gain, so higher gain can only make the
  same sites *more* detectable; containment the other way would falsify that.

### 1.2 The deciding measurement (§2 of the commission)

**Stack: `bee-3-cpl`**, 299 frames, **ISO 100, 1/5 s, f/5.6 marked** (MEASURED
from EXIF, `00-probe.json`). This is the project's workhorse and it is
**gain-matched to dark group `118MSDCF` (ISO 100) and 20x its exposure** — the
first exposure lever in the corpus on this question, since all 242 darks are
1/100 s (fact 162).

**D1 — do the darks' defects appear in the light frames, at the same sensor
coordinates?**

Statistic: mean over T light frames of the same neighbour-excess used for the
map. Because the scene translates and scales by up to 232.7 px across the stack
(fact 1177), averaging the excess over widely separated frames decorrelates scene
structure while a sensor-fixed defect adds coherently.

- **Placebo: the shift control** (fact 162's) — roll the defect map by an even
  offset, preserving CFA phase and every spatial statistic while destroying
  per-pixel correspondence — plus a uniform-random coordinate set.
- **Positive control:** the 352 always-hot sites must read a *larger* excess than
  the >= 6/11 set. M22 measured +3.72 DN against +3.11 DN.
- **Bar B5: median/mean excess at defect coordinates must exceed the shift
  control's by >= 5x**, or the map is wrong and everything downstream is void.

**Pre-registered fork P-B, with a number on each limb.** The darks fix the excess
in electrons at 1/100 s; `bee-3-cpl` is 20x that exposure at the same gain.

- **H_dark-current** — the excess is thermally generated charge, proportional to
  integration time: the in-situ excess should be **~20x** the ISO-100 dark
  excess.
- **H_fixed** — the excess is a fixed per-site offset (DSNU), independent of
  time: **~1x**.

Nothing in the corpus separates these, because every delivered dark is 1/100 s.
I register both limbs with their predicted factors before measuring.

**D2 — THE HEADLINE. What fraction of elected pixels lands on a defect
coordinate?**

Instrument: an **independent Python reimplementation** of the shipped election —
warp each frame's four CFA planes by the committed sidecar
(`experiments/M86-alignment/out/warpmap-bee-3-cpl.txt`, reference 0,
Catmull-Rom), green luma `0.5*((G1-b)+ + (G2-b)+)`, `|Sobel|/8`,
`box_mean(r=13)`, `/ max(green_luma_sigma(L), EPS)`, `box_mean(r=8)` regulariser,
argmax over frames with ties to the lower index. Every constant is read from the
shipped source, not re-derived.

- **B6 — instrument validation (positive control on the instrument).** The
  reimplementation must reproduce the shipped binary's own printed winner-field
  statistics on the same stack and sidecar to **<= 2%** on the winner-response
  median and **exactly** on the plane geometry and frame count. Precedent: fact
  1168, an independent reimplementation reproducing the shipped merge to
  0.00380%. **If B6 fails, no D2 number is admissible.**
- Two quantities, both reported: `H_value`, the fraction of output pixels whose
  elected sample is gathered from a defective site; and `H_support`, the fraction
  whose elected frame carries a defect anywhere in the 29x29 focus support that
  decided it (`SUPPORT_RADIUS = SOBEL_RADIUS + WINDOW_RADIUS = 14`).
- **B7 — the negative-result bar, registered in advance.** If `H_value` and the
  enrichment of D3 are both indistinguishable from their controls, **the correct
  deliverable is a negative result and no code ships.** I register that outcome
  as a success here so that it cannot be argued away later.

**D3 — is the election *enriched* at defect coordinates relative to chance?**

For each (frame `k`, defect site `s`) the defect's image sits at reference
coordinate `p = t_k^{-1}(s)`. Count how often `W(p) == k` — the defect's own frame
winning the election exactly where the defect landed — and compare against:

- **the shift control**: the identical count with the defect map rolled by an
  even offset. This is the primary null.
- **a matched-brightness control**: the shifted sites resampled to match the
  merged output's brightness distribution at the real sites, because bright
  regions win elections for legitimate reasons.
- **a frame-permutation control**: `W` held fixed, the frame index of each event
  permuted, which destroys the defect-frame correspondence while preserving both
  marginals.

**B8: enrichment must exceed 1.5x against all three nulls** to be called real,
with the standard error of each null reported beside it (rule 39).

**D4 — does a defect produce a trail, and how long is it?**

The geometric trail `{ t_k^{-1}(s) : k = 0..298 }` is computable in closed form
from the committed sidecar with no decode at all, so its length is DERIVED
exactly and separately from anything measured. The **output** trail is the subset
of trail points where that frame actually won: `|{ p : W(p) == k_p }|`. A render
is not a measurement; the deliverable is (length, elected count, contrast).

**B9 — the plant (positive control with a known answer).** Inject a synthetic hot
pixel of known amplitude at a sensor coordinate **absent from the defect map**,
re-run the election, and require that the trail appears at the coordinates
predicted from the warp and that the elected count rises monotonically with
amplitude. Per discipline 615 the plant runs in a **separate arm** so it cannot
perturb the mechanism the real measurement runs through, and the real arm's
numbers are computed from a run in which nothing was planted.

### 1.3 What would make each instrument fail (rule 20)

| instrument | the input that makes it FAIL | does such an input exist? |
|---|---|---|
| map (B1/B2) | a threshold that admits noise: split halves then disagree | yes — B2's random sets read Jaccard ~2e-4 by construction |
| D1 | a defect map unrelated to this sensor | yes — the shift control *is* that map |
| D2/D3 | an election indifferent to defects | yes — that is the null, and B9's plant proves the instrument can see the alternative |
| D4 | a warp that does not move | yes — the identity warp arm, run as a control |

### 1.4 Rules discharged, per rule 22

Named per rule at the end of the report, each against the line of code or the
command that discharges it, not against my agreement with it.

---

*Sections 2 onward are written after the runs and record the outcome against
these bars. Any bar adjusted after seeing a result is called out in its own
subsection, loudly, with the reason.*

---

## 2. The answer, up front

**The hypothesis is false on this sensor, and it is false by more than two
orders of magnitude.**

The defect map is real: 14,604 sites reproduce M48c's independent census to 7.0%
and appear in the owner's photographs at the same sensor coordinates with a
monotone dose-response. But the amplitude that reaches a light frame is
**1.5 DN on one green plane**, and the election does not begin to prefer a hot
pixel until that amplitude reaches **between 100 and 250 DN** — a threshold
measured by planting synthetic defects, and predicted in advance from the shipped
arithmetic to fall exactly there.

The consequences, each MEASURED and each with its controls beside it:

| question | measured | control | verdict |
|---|---|---|---|
| fraction of elected pixels landing on a defect | **0.1778%** | shift 0.1773%, random 0.1767%, map density 0.1771% | chance, z = **0.24** |
| enrichment of the election at defect coordinates | **0.987x** | random 1.007x, permuted 1.024x, bar 1.5x | **no enrichment** |
| ... at matched brightness, 5 luma decades | 1.035, 0.989, 1.014, 0.987, 0.901 | — | **no enrichment anywhere** |
| trail: geometric length | **97.7 px** median, 200.1 px max | — | the drag is real |
| trail: pixels actually elected | **0.931** | shift null **0.937** | **no trail** |

The scene really is dragged across the defect — the geometric trail is 97.7 px
at the median, so the mechanism the commission describes is physically present.
The election simply does not take the bait. A defect is elected at 0.0034 of the
frames it is visible in, and uniform chance over 299 frames is 0.00334.

**No correction ships.** Section 6 says what was built instead and why the code
would have been the wrong deliverable.

---

## 3. The map (commission section 1)

### 3.1 Method

242 darks, 11 ISO groups of 22. Frames 1-2 of each group dropped per the owner's
note, then a temporal mean of n = 20, black 512 subtracted, split into the four
CFA planes at the RGGB offsets `CfaPlane::rggb_at` uses. The statistic is a
sample's excess over the median of its eight same-plane neighbours, centre
excluded. Scripts `01`, `02`, `04`, `05`.

**MEASURED — the owner's stabilisation warning is unnecessary but harmless.**
Frames 1-2 differ from frames 3-22 by a mean of **-0.064 to +0.014 DN** across
the 11 groups, which is below the per-frame read noise in every group. They were
dropped anyway, for comparability with M22 and M48c. *(Script `03`.)*

### 3.2 B3 — external replication. PASS against M48c, FAIL against M22

| plane | mine, >= 6/11 | M48c committed | Jaccard vs M48c |
|---|---|---|---|
| R | 111 | 101 | 0.797 |
| G1 | 124 | 98 | 0.762 |
| G2 | 8,149 | 7,765 | **0.897** |
| B | 6,220 | 5,686 | **0.904** |
| **total** | **14,604** (0.0443%) | **13,650** (0.0414%) | — |

**MEASURED.** My census is **+7.0%** on M48c — inside the +/-25% bar — and site
by site the two agree at Jaccard 0.90 on the two populous planes. Against M22's
11,393 it is **+28.2%**, which is **outside** the bar and is recorded as a
failure of that limb. The three censuses form a monotone chain
11,393 -> 13,650 -> 14,604 built by three different neighbour statistics; M22 is
the outlier of the three, and the +/-25% bar was set from the M22-M48c gap of
19.8% before I knew where mine would land.

**MEASURED — the odd/even sensor-row asymmetry replicates.** (G2 + B) /
(R + G1) = 14,369 / 235 = **61.1x**, against M48c fact 9's 68x, measured
independently from the same darks by a different criterion.

**MEASURED — 461 sites are hot in all 11 ISO groups** (R 3, G1 0, G2 294,
B 164), and **142 sites are cold** at the same recurrence.

### 3.3 B1 — split-half reproducibility. **FAIL**, and the failure is the finding

| plane | Jaccard A vs B | **placebo (B2)** | analytic chance |
|---|---|---|---|
| R | **0.077** | 0.000 | 2.1e-4 |
| G1 | **0.074** | 0.000 | 2.2e-4 |
| G2 | **0.401** | 4.7e-4 | 2.1e-4 |
| B | **0.380** | 3.9e-4 | 2.3e-4 |

**MEASURED.** B2 passes everywhere by three orders of magnitude, so the
instrument is not broken — the placebo reads chance exactly as pre-registered.
**B1 fails on every plane.** The bar was 0.80.

Two things follow, and both matter more than a passing bar would have.

**MEASURED — R and G1 defect detections do not reproduce at all.** At Jaccard
0.077 and 0.074 against a placebo of 0.000, the 111 and 124 sites those planes
contribute are consistent with the tail of the noise, not with a defect
population. **M22 and M48c both published them as defects. Neither ran this
test.** This is the first evidence in the corpus that the sparse planes of the
map are noise, and it is consistent with the physical asymmetry: the two odd
sensor rows carry 61x more real defects, so on the even rows a fixed 6-sigma cut
is sampling almost pure noise.

**MEASURED — G2 and B reproduce, but only in their strong half.** Recovery in
*both* halves, stratified by amplitude at ISO 100:

| amplitude, DN | G2 n | G2 recovered | B n | B recovered |
|---|---|---|---|---|
| 0.0-0.5 | 442 | 0.358 | 435 | 0.361 |
| 0.5-1 | 864 | 0.405 | 817 | 0.372 |
| 1-2 | 2,697 | 0.470 | 2,254 | 0.473 |
| 2-4 | 3,420 | 0.665 | 2,242 | 0.660 |
| 4-8 | 513 | **0.862** | 262 | **0.908** |
| 8-16 | 4 | 0.750 | 2 | 1.000 |

**DERIVED.** Monotone in amplitude on both planes. That is the signature of a
real population whose weak end is buried: the >= 6/11 set is dominated by sites
sitting on the detection cut, where halving the frame count is close to a coin
flip. A site detected with per-group probability `p` in a half gives a Jaccard of
about `p/(2-p)`; the measured 0.40 corresponds to `p ~ 0.57`.

**I did not move the bar.** Script `04` re-ran the identical test with the cut
held fixed in DN at the full map's value, to rule out my own split design as the
cause — it moved G2 from 0.352 to 0.401 and B from 0.342 to 0.380 and changed
nothing. Script `05` then replaced the count-based criterion with a physical one
(the median across the 11 ISO groups of the gain-normalised excess, an
ISO-invariant amplitude in electrons) and swept the amplitude cut looking for the
operating point that meets 0.80. **There is none at which the map is populous:**
the Jaccard peaks at 0.51 and the only cut that reaches 0.80 leaves **5 sites on
the whole sensor**. That is itself a result — it replicates M22's finding that
only 3 pixels sensor-wide are unambiguous.

### 3.4 B4 — does one map serve all ISOs? **FAIL as stated, and the direction is informative**

| plane | low-mode n | high-mode n | low contained in high | high in low |
|---|---|---|---|---|
| R | 68 | 541 | 0.162 | 0.020 |
| G1 | 80 | 523 | 0.050 | 0.008 |
| G2 | 3,018 | 12,071 | **0.832** | 0.208 |
| B | 1,903 | 9,706 | **0.854** | 0.167 |

**MEASURED.** The bar was 0.90 containment and G2/B reach 0.83-0.85, so B4 fails
as written. But the *direction* registered in advance holds: the high-gain map is
~4x larger and largely contains the low-gain one, exactly as expected if dark
signal is generated before the analogue gain. The honest answer to the
commission's question is **one map does not serve all ISOs at the containment
standard I set; a high-ISO map is a superset of a low-ISO one to 83-85% on the
planes that carry real defects, and to nothing on the planes that do not.**

### 3.5 P-A — the shipped noise model under-predicts dark spread

**MEASURED.** `sigma_robust / sigma_model` on the neighbour excess, ISO 100,
n = 20: **1.20 to 1.30** across the four planes, and the T-model criterion flags
**21,211** sites against T-robust's 14,604, over-flagging by **45%**. P-A was
registered in the right direction — the model does over-flag, because it carries
no DSNU term — but M48c fact 4's implied magnitude of ~1e6 is not what a
6-sigma cut on a 20-frame mean produces. The model is 20-30% optimistic about
dark-frame spread, not six orders of magnitude wrong.

---

## 4. THE DECIDING MEASUREMENT (commission section 2)

Stack `bee-3-cpl`: 299 frames, **ISO 100, 1/5 s**, digest `8d023c0fe355d109`,
warped by the committed M86 sidecar. Scripts `06`, `07`, `08`, `09`.

### 4.1 D1 — the defects are really there, in the owner's photographs

48 frames sampled evenly across the stack; per-site median across frames of the
same neighbour excess.

| plane | defect | **shift control** | **random control** | net | **positive control: always-hot** |
|---|---|---|---|---|---|
| R | **+2.500 DN** | +0.250 | -0.250 | +2.25 | +1.75 (n = 3) |
| G1 | **+3.375 DN** | -0.375 | +0.125 | +3.75 | — (n = 0) |
| G2 | **+1.500 DN** | **0.000** | **0.000** | +1.50 | **+3.25** |
| B | **+1.500 DN** | **0.000** | **0.000** | +1.50 | **+2.50** |

**MEASURED. B5 passes.** On G2 and B the shift control reads *exactly* 0.000 DN,
so the ratio is unbounded rather than merely above 5. *(Script `06` records
`B5_pass: false` for those two planes: the guard `sh and abs(d/sh) >= 5` returns
False on a zero denominator. That is a reporting artefact in my own code, not a
failed bar, and the underlying comparison is +1.500 DN against 0.000 DN.)*

**MEASURED — the positive control passes and the map's amplitude ordering
survives into the photographs.** Always-hot sites read 2.2x the >= 6/11 set on
G2 and 1.7x on B. And the in-situ excess is monotone in the *dark-frame*
amplitude:

| dark amplitude | G2 in-situ | B in-situ |
|---|---|---|
| 1-2 e- | 1.00 DN | 0.50 DN |
| 2-4 e- | 1.50 DN | 1.25 DN |
| 4-8 e- | 1.75 DN | 2.00 DN |
| >= 8 e- | **4.00 DN** | **4.00 DN** |

This is the strongest external check in the milestone and it costs one decode
pass: a map built from 242 dark frames predicts, site by site and in the right
order, an effect in a completely separate set of 299 light frames.

### 4.2 P-B — the fork, settled. It is a fixed offset, not dark current

**MEASURED.** `bee-3-cpl` runs at 20x the darks' exposure at the same ISO 100
gain. The in-situ excess on G2 is **6.55 e-** against the dark map's **3.63 e-**:
a ratio of **1.81x**, not 20x.

- **H_dark-current predicted 20x. FALSIFIED.**
- **H_fixed predicted 1x. Approximately confirmed, with a resolvable thermal term.**

**DERIVED.** Solving `c + d*t` on the two exposures (t = 0.01 s and 0.2 s) gives
a fixed component **c = 3.47 e-** and a dark-current component
**d = 15.4 e-/s**. So **95% of what these darks measure is a fixed per-site
offset**, and at 1/5 s the thermal part contributes 3.1 e- of the 6.55.

This matters beyond M101 and it closes a gap the corpus could not previously
address: **every one of the 242 delivered darks is 1/100 s**, so nothing in the
existing corpus separates a fixed offset from dark current, and both M22 and
M48c's amplitudes are silently a mixture. It also means the map does **not**
scale with exposure the way a dark-current model would predict — a 10 s exposure
would carry ~157 e- at these sites, which is a different regime and is not
covered by this measurement.

### 4.3 B6 — is the instrument admissible? **PASS on the decision arithmetic, FAIL on the resampling**

There is no CLI flag that dumps a winner map, so the deciding measurement uses an
independent Python reimplementation. It was validated against the shipped binary
on the same 299 frames, twice.

| arm | shipped `strehl stack --stats` | mine | delta |
|---|---|---|---|
| **unwarped** (`STREHL_ALIGN=0`) median | **3.5364** | **3.5360** | **-0.011%** |
| unwarped p10 | 0.6352 | 0.6354 | +0.03% |
| unwarped p90 | 12.5327 | 12.5197 | -0.10% |
| warped (committed sidecar) median | 4.0088 | 4.2680 | **+6.46%** |
| warped p10 | 0.6018 | 0.6062 | +0.73% |
| warped p90 | 12.1578 | 12.8125 | +5.39% |

**MEASURED.** On the unwarped path the reimplementation reproduces the shipped
election to **0.011%** — Sobel, box mean, sigma normalisation, 17x17 regulariser,
argmax and tie-breaking are all exact. **B6's 2% bar passes there and fails on
the warped path at 6.46%,** which localises the entire discrepancy to my
Catmull-Rom resampler rather than to the decision arithmetic. Candidate causes,
untested: coverage/edge handling in `warpmap.rs::gather_checked`, and my
edge-replication of rawpy's 3514 columns up to rawler's 3516 (M48c fact 33).

**Why the deciding measurement survives a failed B6 limb**, ARGUED, three ways:

1. Every headline is a **ratio between coordinate sets scored inside one winner
   map** — defect against shift, random and permuted. A global scale offset in
   the focus field cancels exactly; it cannot turn a 1.5x enrichment into 0.99x.
2. The identity arm re-runs the whole deciding measurement with a *provably
   exact* instrument (0.011%) and reaches the same null.
3. The plant arm passes through the identical warp and still produces a clean
   dose-response, so the warp does not destroy the sensitivity being claimed.

**A failed bar is reported as failed.** The conclusion is qualified accordingly:
this milestone establishes the null on an instrument that is exact unwarped and
6.5% off in the warped response scale.

### 4.4 D2 — the headline. What fraction of elected pixels lands on a defect?

| quantity | value | control |
|---|---|---|
| **H_value, any plane** | **0.0017782** (14,655 of 8,241,504 px) | shift **0.0017732**, random **0.0017657** |
| map density | 0.0017707 | — |
| H_value, green planes only | 0.0010140 | — |
| H_support (defect anywhere in the 29x29 support) | 0.7657 | shift 0.7642 |

**MEASURED. The election lands on defects at exactly the base rate.**
H_value / density = **1.0042**, and against the shift control the difference is
**z = 0.24** — nowhere near significance.

**Discipline 616 check, run deliberately.** H_value equals a parameter of my own
pipeline (the map density), which the corpus says to treat as a bug report. It is
not one here, and the reason is checkable: the shift and random controls have the
same density *by construction* and would read the same value under a bug, but the
**plant arm uses the same code and reads 1.43x** at 500 DN. A trivially
density-returning instrument could not do that.

**MEASURED — H_support carries no signal and should not be quoted as if it did.**
0.7657 sounds alarming until the control is read: shift gives 0.7642, and the
Poisson expectation from density alone is `1 - exp(-14,604 * 841 / 8,241,504)`
= **0.775**. The number is pure area-counting.

### 4.5 D3 — enrichment. **B8 fails: there is none**

| arm | hits | visible events | rate | +/- |
|---|---|---|---|---|
| **defect** | 3,725 | 1,097,105 | **0.0033953** | 5.6e-5 |
| shift null | 3,747 | 1,089,678 | 0.0034386 | 5.6e-5 |
| random null | 3,659 | 1,083,981 | 0.0033755 | 5.6e-5 |
| permuted null | 3,642 | 1,097,105 | 0.0033196 | 5.5e-5 |
| uniform chance, 1/299 | — | — | 0.0033445 | — |

**MEASURED.** Enrichment **0.987x** against shift, **1.006x** against random,
**1.023x** against permuted. The bar was 1.5x against all three. **B8 fails; a
defect coordinate wins its own election at uniform chance**, and if anything
fractionally below it.

Matched-brightness control, because bright regions win elections for legitimate
reasons:

| elected luma, DN | n defect | defect rate | shift rate | enrichment |
|---|---|---|---|---|
| 0-500 | 674 | 0.003431 | 0.003314 | 1.035 |
| 500-1,000 | 550 | 0.003312 | 0.003350 | 0.989 |
| 1,000-2,000 | 552 | 0.003395 | 0.003349 | 1.014 |
| 2,000-4,000 | 1,637 | 0.003348 | 0.003393 | 0.987 |
| 4,000-8,000 | 587 | 0.003583 | 0.003975 | 0.901 |

**MEASURED. No enrichment at any brightness, across five decades.**

### 4.6 D4 — the trail. The drag is real; the trail is not

**MEASURED, and DERIVED exactly from the sidecar with no decode:** a defect's
image sweeps a geometric path of **97.7 px at the median**, 152.7 px at p90 and
**200.1 px at maximum** across the 299 frames. The mechanism the commission
describes is physically present and large.

**MEASURED, from the winner map:** of those ~274 visible positions, the number
at which the defect's own frame actually wins is **0.931 px on average** — median
1, p90 1, maximum 10 — against a **shift null of 0.937 px**. 18.2% of defects are
elected nowhere at all, against 17.2% of shift controls.

**A defect deposits about one pixel in the merged image, in the same quantity as
a coordinate chosen to be nowhere near a defect.** There is no trail. The
commission asked for this to be quantified rather than rendered, and the honest
quantification is: *a geometric trail of 97.7 px, of which 0.93 px are elected,
against a null of 0.94 px.*

**MEASURED — the identity-warp control arm.** Re-running the entire deciding
measurement with every warp forced to identity, so that nothing moves:

| quantity | warped | **identity control** |
|---|---|---|
| geometric trail, median | 97.7 px | **0.0 px** |
| elected trail, mean | 0.931 px | **1.000 px** |
| H_value | 0.0017782 | **0.0017707** (= density exactly) |
| enrichment vs shift | 0.987x | **1.000x** |

This is the degenerate case and it behaves exactly as it must: with no motion a
defect occupies one reference pixel and exactly one frame wins there, so the
elected trail is **1.000 px by construction**. The warped arm reads **0.931**,
i.e. *below* the static case — because 18.2% of defect positions fall outside
some frames' coverage. **Alignment does not spread defects into the merge; it
very slightly reduces how much of them arrives.** That is the direct answer to
M22 section 7's open question and to M48c fact 30's pre-registered acceptance
test, and the answer is the opposite of what both expected.

### 4.7 B9 — the positive control. The instrument is **not** blind

320 synthetic hot pixels planted at coordinates absent from the defect map, 40 at
each of eight amplitudes, in **its own arm** (discipline 615). The real arm's
numbers above come from a run in which nothing was planted; planting perturbed
**0.206%** of the winner map, and that perturbed map was never used for the real
measurement.

The prediction was DERIVED *before the run* from the shipped arithmetic: an
isolated spike of green-luma amplitude `A` raises `box_mean_27(|Sobel L|)` by
`2.118*A/729`, so `dFocus = 0.002905*A/sigma_L`, and it can only win where that
is comparable to `FOCUS_NOISE_SD = 0.015214`. At the measured median
`sigma_L = 17.05 DN` the turn-on should sit **between 100 and 250 DN**.

| plant, DN on G2 | elected px | same sites, unplanted | enrichment | predicted dFocus |
|---|---|---|---|---|
| 2 | 0.95 | 0.93 | 1.03x | 0.011 sd |
| 5 | 0.97 | 0.97 | 1.00x | 0.028 sd |
| 10 | 1.02 | 1.02 | 1.00x | 0.056 sd |
| 25 | 0.97 | 1.00 | 0.97x | 0.140 sd |
| 50 | 1.10 | 1.15 | 0.96x | 0.280 sd |
| 100 | 0.93 | 0.88 | 1.06x | 0.560 sd |
| **250** | 1.23 | 1.02 | **1.20x** | 1.400 sd |
| **500** | 1.32 | 0.93 | **1.43x** | 2.799 sd |

**MEASURED. Flat below 100 DN, monotone above it, turning on exactly where the
closed-form prediction says it must.** Unplanted control sites inside the planted
run read 0.00343, i.e. chance.

**This is the number that makes the null admissible.** The instrument detects an
election preference when one exists, and the amplitude at which it starts is
predicted in advance to within one ladder step.

### 4.8 The bridge: why the answer is "no", quantitatively

**DERIVED.** The real defect amplitude reaching a light frame is **1.5 DN** on one
green plane (section 4.1), so **0.75 DN** of green luma. Through the shipped
arithmetic that is

```
dFocus = 0.002905 * 0.75 / 17.05 = 1.28e-4  =  0.0084 * FOCUS_NOISE_SD
```

**A real hot pixel perturbs strehl's focus measure by 0.8% of the measure's own
noise floor.** The plant ladder confirms the scale empirically: the election
turns on somewhere above 100 DN, and the real defects are at 1.5 DN — **at least
67x, and by the derivation ~120x, below the amplitude that would matter.**

That is the whole milestone. The focus measure does not love hot pixels on this
sensor, because on this sensor hot pixels are 1.5 DN tall.

---

## 5. Threats to validity

1. **One stack, one ISO, one exposure.** Everything in section 4 is `bee-3-cpl`,
   ISO 100, 1/5 s. The conclusion is a statement about *amplitude*, and amplitude
   is ISO- and exposure-dependent. **DERIVED:** at ISO 2000 the same 3.47 e-
   fixed offset is 15.9 DN, and a 10 s exposure would add ~154 e- = 3.5 DN at
   base gain. Neither reaches 100 DN, but the margin narrows and the corpus has
   no long-exposure dark to check the linearity of the thermal term against.
2. **B6 fails on the warped path at 6.46%.** Argued around in section 4.3, not
   eliminated. An independent verifier should re-run the identity arm first,
   where the instrument is exact to 0.011%.
3. **B1 fails.** The >= 6/11 map is only ~40% reproducible under a 10/10 split on
   G2/B and not at all on R/G1. This makes the map *conservative* for the null —
   a noisier map dilutes any real enrichment toward 1.0. The 461 always-hot sites
   are the reproducible core, and section 4.1 shows they read 2.2x higher
   in-situ, so the ordering is right even where the membership is marginal.
   A verifier could re-run D3 restricted to those 461.
4. **Nearest-sample attribution.** H_value asks whether the *nearest* source
   sample is defective. The shipped gather is Catmull-Rom over 4x4, so a defect
   can contribute at up to ~2 px away with a small weight. `H_support` bounds the
   other end at 0.766 and is pure area-counting; the truth is between, and both
   ends read their controls.
5. **The plant is a delta; a real defect may not be.** M48c measured 99.8%
   singletons and a largest cluster of 3 px, so the delta is a good model, but
   the 0.2% that are clusters are not represented in the ladder.
6. **Rawpy vs rawler geometry.** The map is built in rawpy's 3514-column
   geometry and used in rawler's 3516. M48c fact 33 measured the rawpy columns to
   be rawler's leading 3514, which I relied on rather than re-measured.

---

## 6. What I built, and what I did not

**No correction ships, and `crates/strehl-core/src/defect.rs` was not written.**
The commission is explicit that this is a first-class outcome, and section 4.8 is
the reason: the correction would repair a 0.8%-of-noise perturbation at the cost
of a new CLI surface, a new sidecar format, and a permanent exclusion path
through the election. The stack already contains up to 299 observations of every
scene point, and the measurement says it is already using them without
prejudice.

**What was built instead**, and is committed with this report so every figure is
re-runnable:

| script | what it does |
|---|---|
| `00-probe.py` | EXIF/geometry probe; the per-ISO sigma table the bars are stated in |
| `01-map-from-darks.py` | decodes all 242 darks once, per-group means and both thresholds |
| `02-fold-and-bars.py` | recurrence fold, B1-B4, external replication against M48c |
| `03-operating-point.py` | recurrence sweep; the stabilisation-frame check |
| `04-splithalf-fixedcut.py` | B1 re-run at matched sensitivity; strength stratification |
| `05-amplitude.py` | ISO-invariant amplitude estimator in electrons |
| `06-insitu.py` | D1: the defects in the owner's photographs, with both placebos |
| `07-election.py` | the election, reimplemented; three arms |
| `08-deciding.py` | D2/D3/D4 with four nulls |
| `09-plant.py` | B9, the planted positive control |

**No patch to `lib.rs` or `main.rs` is requested**, because no module was added.

### 6.1 If the owner ever wants it anyway

**ARGUED.** The cheapest defensible version is not a defect module at all. The
map's whole measured effect is 1.5 DN at 0.0018 of pixels; a *repair* is
therefore indistinguishable from a no-op, but an *exclusion* is free to state:
the merge already averages `mean n_eff = 55.9` frames per pixel at gate 4, so
dropping the one sample that sits on a known defect costs 1/55.9 of the
averaging and removes the contaminated value exactly. That is the design the
commission preferred, and it remains the right one — it is simply not worth
shipping for a 1.5 DN effect on this body.

---

## 7. What I would do next

1. **A long-exposure dark set.** One group at 5-10 s at ISO 100 would separate
   the fixed offset from the thermal term directly instead of by a two-point
   solve, and would say whether the map matters for the exposures the owner
   actually uses at night. This is the single highest-value follow-up and it
   costs the owner ten minutes with the lens cap on.
2. **Re-run D3 on the 461 always-hot sites.** The reproducible core, where B1
   would pass.
3. **Fix the warp discrepancy.** 6.46% on the warped median is a real
   disagreement between an independent implementation and `warpmap.rs`, and it is
   worth knowing which one is right; the identity arm proves everything *else* in
   both agrees to 0.011%.
4. **Tell M22 and M48c that R and G1 are noise.** Both published those planes'
   sites as defects; neither ran a split-half. 235 of the 14,604 sites should be
   struck.

---

## 8. Facts, disciplines and questions

**Facts.**

- **P1 (MEASURED).** A defect map from the 242 delivered darks at >= 6/11
  recurrence holds **14,604 sites, 0.0443%** of the sensor: R 111, G1 124,
  G2 8,149, B 6,220. It replicates M48c's independent 13,650 to **+7.0%** and
  agrees site-by-site at Jaccard **0.897** (G2) and **0.904** (B). *(`02`.)*
- **P2 (MEASURED).** The odd/even sensor-row asymmetry replicates independently:
  (G2+B)/(R+G1) = **61.1x**, against M48c fact 9's 68x. *(`02`.)*
- **P3 (MEASURED).** **R and G1 defect detections do not reproduce.** Split-half
  Jaccard **0.077** and **0.074** against a random-coordinate placebo of
  **0.000**. Those 235 sites are consistent with noise; M22 and M48c both
  published them. *(`04`.)*
- **P4 (MEASURED).** G2/B split-half Jaccard is **0.401** / **0.380** against
  placebos of 4.7e-4 / 3.9e-4 — far above chance, far below the 0.80 bar.
  Recovery is monotone in amplitude, from 0.36 below 0.5 DN to **0.86-0.91**
  above 4 DN. *(`04`.)*
- **P5 (MEASURED).** No populous amplitude cut reaches Jaccard 0.80; the cut that
  does leaves **5 sites** sensor-wide. Maximum defect amplitude is **11.5 e- on
  G2** and **8.3 e- on G1** — the only two planes the election can see. *(`05`.)*
- **P6 (MEASURED).** The darks' defects appear in `bee-3-cpl` at the same sensor
  coordinates: **+1.500 DN** on G2 and B against a shift control of **exactly
  0.000 DN**. Always-hot sites read **+3.25 DN**, and in-situ excess is monotone
  in dark-frame amplitude (1.00 -> 1.50 -> 1.75 -> 4.00 DN). *(`06`.)*
- **P7 (MEASURED).** **The excess is a fixed offset, not dark current.** At 20x
  the darks' exposure and the same gain the in-situ excess is **1.81x**, not 20x.
  A two-point solve gives a fixed **c = 3.47 e-** and a thermal
  **d = 15.4 e-/s**; ~95% of what a 1/100 s dark measures is the fixed part.
  *(`06`.)*
- **P8 (MEASURED).** **The election lands on defects at exactly chance.**
  H_value = **0.0017782** against a map density of 0.0017707 and a shift control
  of 0.0017732, **z = 0.24**. *(`08`.)*
- **P9 (MEASURED).** **No enrichment.** A defect coordinate wins its own election
  at **0.0033953**, against shift 0.0034386, random 0.0033755, permuted
  0.0033196 and uniform chance 0.0033445 — **0.987x**, against a 1.5x bar, and
  flat across five decades of matched brightness. *(`08`.)*
- **P10 (MEASURED).** **The drag is real and the trail is not.** Geometric trail
  **97.7 px** median / **200.1 px** max; elected trail **0.931 px** against a
  shift null of **0.937 px**. An identity-warp control arm gives a geometric
  trail of 0.0 px and an elected trail of exactly **1.000 px**, so alignment
  **reduces** the defect's deposit rather than smearing it. This answers M22
  section 7 and M48c fact 30, and the answer is the opposite of what both
  predicted. *(`08`.)*
- **P11 (MEASURED).** The election begins to prefer a planted hot pixel between
  **100 and 250 DN** (enrichment 1.06x -> 1.20x -> 1.43x at 100/250/500 DN),
  exactly where `dFocus = 0.002905*A/sigma_L` crosses `FOCUS_NOISE_SD`. Real
  defects are **1.5 DN**, i.e. **0.0084 sigma** of the focus noise floor —
  more than 100x below the threshold that would matter. *(`09`.)*
- **P12 (MEASURED).** An independent Python reimplementation of the election
  reproduces `strehl stack`'s winner response to **0.011%** unwarped
  (3.5360 vs 3.5364) and **6.46%** warped (4.2680 vs 4.0088), localising the
  disagreement entirely to the Catmull-Rom resampler. *(`07`.)*
- **P13 (MEASURED).** The owner's first two stabilisation frames per group differ
  from the rest by **-0.064 to +0.014 DN**, below read noise in every group.
  *(`03`.)*
- **P14 (MEASURED).** The shipped noise model under-predicts dark-frame spread by
  **20-30%**, and a 6-sigma model cut over-flags by **45%** (21,211 vs 14,604) —
  not the ~1e6 M48c fact 4 implies. *(`01`.)*

**Disciplines.**

- **PD1.** *A split-half is not a placebo, and neither is sufficient alone.* B2
  passed at 0.000 while B1 failed at 0.077 on the same plane: the placebo proves
  the instrument is not hallucinating agreement, and only the split-half proves
  the map is a map. Two published censuses ran neither.
- **PD2.** *When a bar fails, first ask whether your own instrument caused it.*
  Halving the frame count raised the DN cut, so the two halves were maps of
  different sensitivity. Re-running at a matched cut moved 0.352 to 0.401 and
  settled that the failure was real. Do that before either moving the bar or
  believing the result.
- **PD3.** *Give a null an amplitude ladder, not just a control.* "No enrichment"
  is weak; "no enrichment below 100 DN, 1.43x at 500 DN, and the real defect is
  1.5 DN" is a bound. A dose-response converts a null into a measured margin.
- **PD4.** *Predict the turn-on before you plant.* The closed-form
  `dFocus = 0.002905*A/sigma_L` put the threshold between 100 and 250 DN, and
  that is where it landed. A positive control that only confirms *that* the
  instrument works is much weaker than one that confirms *where* it works.
- **PD5.** *A pipeline whose two exposures differ is worth more than one that is
  internally consistent.* Every delivered dark is 1/100 s, so the corpus could
  not tell a fixed offset from dark current. The owner's photographs are 20x
  longer, and that one lever settled it for free.

**Questions.**

- **PQ1.** How does the fixed 3.47 e- offset behave at long exposure? The
  two-point solve assumes the thermal term is linear in time; no dark longer than
  1/100 s exists in the corpus.
- **PQ2.** Why does my Catmull-Rom warp disagree with `warpmap.rs` by 6.46% on
  the median regularised response when the unwarped path agrees to 0.011%?
- **PQ3.** Would D3 show enrichment if restricted to the 461 always-hot sites?
  The prediction from P11 is no — they are still only ~3.25 DN.
- **PQ4.** M22 and M48c's R/G1 sites do not reproduce. Should the committed
  masks in `experiments/m48c-defect-layer/data/` be corrected, or annotated?

---

## 9. Rules discharged

| rule | how |
|---|---|
| 8 | Bars committed in `d9019ce` before any measurement; results in a later commit |
| 11 | Every claim labelled MEASURED / DERIVED / ARGUED |
| 12 | Placebo *and* positive control beside every headline; B9's ladder is the positive control for the null |
| 20 | Section 1.3 names the input that makes each instrument fail, and B9 supplies it |
| 22 | This table |
| 24 | B1, B4, B6-warped and B3's M22 limb are reported as **failed**, not re-scoped |
| 28 | Facts numbered locally as P1-P14 |
| 32 | `raw_image_visible` copied inside every `with rawpy.imread(...)` block |
| 39 | Standard errors beside every rate in section 4.5 |
| 40, 43 | Section 0.2 names M22, M48c, M29 and M48, which the dispatch omitted, and gives the search |
| 41 | **M101 is not in the AGENTS.md ledger.** A ledger patch is routed to the orchestrator rather than applied here |

**Reproduction.** Every number above comes from
`experiments/M101-defect/src/*.py` run in numeric order against
`D:\macro-dark-frames` and `D:\personal\macro\bee-3-cpl`, writing to
`C:\dev\strehl-out\M101\`. The two shipped-binary cross-checks are
`strehl stack D:\personal\macro\bee-3-cpl --gate 4 --stats` with
`STREHL_WARPMAP` set to the committed M86 sidecar, and the same with
`STREHL_ALIGN=0`. Script `01` re-decodes 242 frames in ~70 s wall on 11 workers;
each election arm is ~9 min on 16.
