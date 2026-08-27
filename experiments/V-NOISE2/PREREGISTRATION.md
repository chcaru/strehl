# V-NOISE2 — PRE-REGISTRATION: does the noise advantage generalise across subjects?

**Written and committed BEFORE any of the three new subjects had been
developed, stacked, or measured. The git timestamp on this file, and the
absence of any output for `bee-1-cpl`, `119MSDCF` or `flower-bud-alone-cpl`
under `C:\dev\strehl-out\` at that commit, are the evidence.**

Continuation of `docs/research/M127-noise-head-to-head.md`. That milestone
measured strehl against `enfuse` and `focus-stack` on noise and found strehl
**1.54–1.76× cleaner on chroma** with **more** scene content in the same tiles.
It named its own binding limitation: **one scene**. This document fixes, in
advance, everything needed to test whether that number is a property of
`strehl` or a property of that one subject.

---

## 0. Blindness status — DISCLOSED, and it is partial

M127's §0 disclosed that its registration was not blind. The same honesty is
owed here, and the situation is different in kind:

- **I have seen the result on the existing subject.** 1.540 luma / 1.763 /
  1.538 chroma against `enfuse`. So I know the sign I am hoping for, and the
  hypothesis under test is one I have an interest in.
- **I have seen nothing on the three new subjects.** No frame of `bee-1-cpl`,
  `119MSDCF` or `flower-bud-alone-cpl` has been developed. No comparator arm
  exists for any of them. No statistic has been computed. `Get-ChildItem
  C:\dev\strehl-out` at the time of writing contains no directory for this
  lane's new work beyond a one-frame timing probe.
- **The one number I did take before writing this is a timing probe** — a
  single frame of `119MSDCF` developed to measure seconds-per-develop (1.5 s,
  197 798 923 bytes) so that the subject list could be chosen for regime
  coverage rather than silently for cheapness. It is a cost measurement and
  carries no information about noise.

So: not blind to the hypothesis, blind to the data. That is the strongest
available position given that the lane which measured M127 is the lane asked to
generalise it, and it is the reason the subject list below is frozen here
rather than assembled as results arrive.

---

## 1. THE SUBJECT LIST — FIXED IN ADVANCE, IN FULL

**Four subjects. Three new, plus the one already measured. This list is closed.**

| # | subject | N frames | depth | merge regime | why this one, decided *a priori* |
| --- | --- | ---: | --- | --- | --- |
| 1 | `113MSDCF` | 63 | mid | mid | **Already measured (M127).** Carried in unchanged; not re-run, not re-tuned. |
| 2 | `bee-1-cpl` | 299 | **deep** | **selection** (`avg_index` **0.06**) | Mandated by the commission. The most selection-dominated subject in the corpus (`V-EYES.md` §5.6). |
| 3 | `119MSDCF` | 33 | **shallow** | **averaging** | The **largest** measured softness deficit in the corpus, 0.8110 at a complete 33/33 bracket (`V-EYES.md` §5.5), and one of the three subjects V-EYES identified as averaging most. |
| 4 | `flower-bud-alone-cpl` | 205 | **deep** | **averaging** (`avg_index` 1.80) | **Breaks the collinearity.** See below — this is the only reason a fourth subject is on the list. |

**Why subject 4 exists and is not padding.** With only `bee-1-cpl` (deep +
selecting) and `119MSDCF` (shallow + averaging), *depth* and *regime* are
perfectly confounded: any split I found could equally be a stack-depth effect.
`V-EYES.md` §5.6 names exactly this as the corpus's structural gap and had to
spend a full 299-frame bracket to break it for a different statistic.
`flower-bud-alone-cpl` is **deep and averaging**, which separates the two axes:

| | averaging | selecting |
| --- | --- | --- |
| **shallow** | `119MSDCF` (33) | *— no subject; declared gap* |
| **mid** | `113MSDCF` (63) | |
| **deep** | `flower-bud-alone-cpl` (205) | `bee-1-cpl` (299) |

**The empty cell is declared now, not discovered later.** There is no shallow
selection-dominated subject on this list, so if a split appears along the
regime axis it will be supported by three cells, not four, and I will say so.

**Rules on the list, binding:**

1. **No subject may be added after the first noise number is seen.** A
   flattering fifth subject is the obvious failure mode of a multi-subject
   study and it is foreclosed here.
2. **No subject may be dropped for its result.** A subject may only be
   withdrawn for a **mechanical** failure — a pipeline exit code, a failed
   geometry fit, a missing output — and the failure must be reported with the
   command and the error, in a partition that sums to four.
3. **The regime labels above are fixed now** and are taken from `V-EYES.md`,
   a document written for a different purpose by a different lane. I will
   additionally *measure* `avg_index` for each subject from strehl's own stack
   log and report it, but the labels used to interpret a split are these.

---

## 2. Pipeline — identical to M127's, per subject, no substitutions

Every arm is built from **strehl's own linear develops**, which is the property
that makes the comparison mean anything: demosaic, white balance, black level,
colour matrix and CA correction are then the same operation on both sides, and
the only remaining difference is the stacking algorithm.

Per subject, with the pinned binary
`C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe`
(sha256 `15EA…A7B0`):

1. **Develop** every frame individually: `stack <one-frame-dir> --merge pyramid
   --pyramid-gate 4.5 --linear-srgb --demosaic`, `STREHL_ALIGN=0`,
   `STREHL_FULLRES_GATHER=1`. No `--srgb`, no `--exposure`.
2. **Shared raster**: `align_image_stack -l -m -C --use-given-order` over
   **all N** developed frames **once**. This is `run_coh.ps1`'s correction and
   it is not optional — aligning halves separately anchors them on different
   reference frames at different magnification, which is a registration error
   that runs **in strehl's favour**.
3. **Comparator halves** from even/odd subsets of that one aligned set:
   `enfuse --exposure-weight=0 --saturation-weight=0 --contrast-weight=1
   --hard-mask`, and `focus-stack --no-align`.
4. **strehl halves** from the ARW frames: `strehl align` then `strehl stack
   --merge pyramid --pyramid-gate 4.5 --linear-srgb --demosaic` on each half
   directory, with that half's own warpmap.
5. **Geometry re-derived per subject** by the scale sweep in
   `V-LINEAR2/geomfree.py`, imported unmodified. **A sweep without an interior
   maximum is a FAILED FIT and that subject is reported as failed, not
   refined.** Scale is not carried across subjects: it depends on which frame
   the aligner anchored on.

**Frame budget and the only permitted deviation.** Full brackets are the
intent. If an intermediate would exceed free disk, the bracket is subsampled
**uniformly**, by a stated factor, **applied identically to all three arms**,
and the factor is reported per subject. Uniform subsampling changes the
absolute noise level but not the ratio between arms on identical inputs; it is
still a deviation and is reported as one. Free space is checked and recorded
before each subject starts.

`D:\` is read-only. Frames are copied to `C:\dev\strehl-out\V-NOISE2\` and the
copies are what is decoded.

---

## 3. The statistic — M127's surviving one, unchanged

**The half-stack difference estimator, `halfdiff.py`.** `0.5·Var(A−B)` over two
disjoint half-stacks of the same scene: the scene cancels by construction, so
this needs no assumption that a tile is featureless. Reported per channel in
opponent space — **luma Y, chroma R−Y, chroma B−Y** — as a median over FLAT
tiles, with a bootstrap 95% CI on the ratio comparator/strehl. `>1` means the
comparator is noisier.

M127's pre-registered *primary* — flat-ROI residual σ — is **not** used as a
noise statistic here. M127 withdrew it after measuring it to be 84.6% scene,
and a withdrawn statistic does not get quietly reinstated on new data.

**FLAT tiles are selected from the source develops, never from a stacker
output**, by `census_src.py`'s rule: max-over-frames high-pass variance, bottom
quartile. Selecting ROIs on an output would let the choice of ROI encode the
result.

**Integer-shift corrected is primary; RAW is reported beside it**, as in M127,
because strehl's halves are known to sit further apart than the comparators'
and misregistration inflates `Var(A−B)` — a bias **against** strehl.

**Band treatment.** Where a frequency-domain number is quoted, 0.30–0.48 cyc/px
is treated as **signal**, not contamination: that band is where sensor noise
lives, which is the quantity under test here. This is M127 §3.3 restated and
unchanged.

---

## 4. Commissioning — RE-RUN ON EVERY SUBJECT, NOT CARRIED ACROSS

A floor is a property of the image as much as of the estimator. Each of the
three new subjects gets its own full commissioning, and **a subject whose
commissioning fails is reported as failed rather than having its number
reported with a caveat.**

| arm | what it does | pass criterion, fixed now |
| --- | --- | --- |
| **NULL** | the estimator on an image against itself | returns the identity floor; a ratio below the floor is not a difference |
| **POTENCY** | plant Gaussian noise of known σ at **three levels spanning ≥8×**, on that subject's own tiles | measured/predicted within **±10%** at every level. `half_sigma` applies no high-pass, so the prediction carries **no `KVAR` factor** |
| **QUANT8** | requantise strehl's halves to 8 bits | must be **strictly >1** in all three channels. An exact 1.000 is impossible here and means a defect — this is the arm that caught M127's rebound-loop bug |
| **TONE** | fit a 4×4-block tone map from one arm to the other and re-measure | if applying it explains most of the ratio, the result is a **tone measurement** and is withdrawn for that subject |

---

## 5. Verdict vocabulary — fixed before the data

Decided per subject on the **chroma** channels (M127's headline lives there),
with luma reported alongside:

- **CLEANER** — ratio CI entirely above 1.0.
- **LEVEL** — CI spans 1.0.
- **NOISIER** — CI entirely below 1.0. *This is a permitted outcome and will be
  reported as the headline if it occurs.*
- **UNDETERMINED** — commissioning fails, or the TONE arm explains the ratio.
- **FAILED** — mechanical failure; reported with the command and exit code.

Across the four subjects:

- **GENERALISES** — ≥3 of 4 subjects **CLEANER** on both chroma channels, none
  **NOISIER**, and the pooled CI above 1.0.
- **REGIME-DEPENDENT** — the outcome splits along the averaging/selection axis.
  **This is a finding, not a failure**, and is reported as the headline if it
  occurs. Another lane has already shown these two regimes behaving oppositely
  on a related statistic, so it is a live hypothesis rather than an excuse.
- **DOES NOT GENERALISE** — 2 or more subjects **LEVEL** or **NOISIER**. If
  this happens, **M127's README claim must be narrowed to one scene**, and I
  will say so in those words.

---

## 6. Pooling — the rule, and the test that must precede it

**Pooling is not the default. It is conditional, and the condition is tested
before the pooled number is computed.**

1. Compute the four per-subject ratios and their CIs.
2. **Split test, decided now:** the per-subject estimates are declared
   heterogeneous if the highest and lowest point estimates have
   **non-overlapping 95% CIs**, or if the rank order of the four ratios matches
   the rank order of `avg_index` (a regime trend) with all four subjects
   agreeing in direction.
3. **If heterogeneous → pooling is declared ILLEGITIMATE** and no pooled number
   is reported as the headline. Per-subject numbers and the regime split are
   the result. A pooled figure may still be shown, explicitly labelled as
   descriptive only.
4. **If homogeneous → pool** as the unweighted median of the per-subject
   medians, with a bootstrap resampling **subjects and tiles** so the CI
   carries between-subject variance rather than pretending four scenes are one
   large sample. Unweighted, so a 299-frame subject does not outvote a 33-frame
   one on tile count.

**Stated in advance because it is the obvious place a flattering answer can
enter**: a pooled mean weighted by tile count would let the deepest stack carry
the verdict, and the deepest stack is the one I expect to win.

---

## 7. What would falsify M127's headline

Named now so it cannot be renamed later:

- **≥2 of the 4 subjects reading LEVEL or NOISIER on chroma** falsifies
  "strehl is cleaner than `enfuse`" as a general claim. The README headline
  would have to be narrowed to the subject it was measured on.
- **A TONE arm that explains the ratio on any subject** withdraws that
  subject's number outright, exactly as M127's `CHROMAGAIN` arm withdrew its
  own flat-ROI chroma headline.
- **A QUANT8 arm returning exactly 1.000** on any subject is a defect in the
  instrument, not a result, and blocks that subject until diagnosed.

---

## 8. A naming correction carried in

M127's subject is `D:\personal\macro\113MSDCF`, 63 frames. It has been referred
to in dispatch as `coffee-bubbles`; that is a **different** subject on disk
(`D:\personal\macro\coffee-bubbles`, 19 frames) with a different regime
(V-EYES 13-frame scan: `113MSDCF` 1.651, `coffee-bubbles` 0.922). The M127
result is `113MSDCF` and is labelled that way throughout this lane.

---

## 9. Route 1 — the full-render detail reading (added 2026-08-27, before `fullhp.py` was run)

This section is written and committed **before** the statistic has been
evaluated on any real pair. Its purpose is that the branch cannot be chosen
after the number is seen.

**The question.** On `119MSDCF`, the half-stack coherence statistic `C` reads
`enfuse` at **2.017x** strehl's detail amplitude at 0.20–0.25 cyc/px. `C` counts
only structure correlated across the two half-stacks. Detail that a
selection-dominated merge delivers incoherently across its halves is therefore
charged as absent. Route 1 removes the half-split entirely and reads total band
amplitude on the **full** merges.

**The statistic**, with every term's bandwidth stated before any two are
combined, because this lane has already shipped one statistic that subtracted a
full-band term from a high-pass total. Let `B = [0.20, 0.25)` cyc/px.

| term | definition | bandwidth |
| --- | --- | --- |
| `D_X` | median band power over DETAIL tiles | **band-limited to `B`** |
| `F_X` | median band power over FLAT tiles | **band-limited to `B`** |
| `S_X` | `D_X − F_X` | **band-limited to `B`** |
| reported | `sqrt(S_enfuse / S_strehl)` | amplitude ratio |

No full-band quantity appears anywhere in it, and no half-stack is read.

**Pre-registered branches.** Fixed now:

- **LEVEL** — corrected ratio in `[0.90, 1.11]` **and** its 95% CI contains 1.0.
  Reading: the 2.017 is not visible without the half-split, so it is half-stack
  incoherence and the detail is present in the delivered image.
- **CONFIRMED** — corrected ratio `>= 1.5`. Reading: the detail is genuinely
  absent; the incoherence story is dead and the project is behind `enfuse` here.
- **PARTIAL** — anything else. Reading: a real gap, smaller than `C` reports.

**LEVEL is the branch that flatters this project**, so it carries an extra
obligation that is registered here rather than invented afterwards: the
**uncorrected** ratio is reported alongside the corrected one in every case, and
if the correction carries most of the movement then the verdict rests on
assumption A1 (noise power equal in the two tile populations) and must say so in
those words.

**Commissioning, all answers fixed in advance.** `IDENT-BITWISE` (1.000,
determinism only, discounted); `IDENT-PATH` (1.000, potency proven on the
`k != 1` rungs); `SCALE` (1.000, isolates the tile-size asymmetry); `k = 1.30`
**sharper**, must return `> 1` so a parity-bounded statistic cannot pass
trivially; `k = 0.95, 0.85, 0.70, 0.50` must recover `k`; **`NOISE-PROP`** —
the arm ORCH required — plants Gaussian noise with **no** detail change, and the
**corrected** statistic must not rise while the **uncorrected** one must, or the
plant is inert and the arm proves nothing; `NOISE-ABS` violates A1 on purpose
and is checked against a computed prediction; `NOISE+DETAIL` must still recover
0.70. **A commissioning failure blocks the verdict** — `fullhp.py` returns 1 and
prints no reading.
