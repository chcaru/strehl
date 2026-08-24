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
