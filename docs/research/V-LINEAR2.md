# V-LINEAR2 — the free field, a band that contains signal, and a coherence bug that was costing strehl a factor of six

*Lane V-LINEAR2. Every number below was produced by code in
`experiments/V-LINEAR2/` and is quoted from a console capture or a log under
`C:\dev\strehl-out\V-LINEAR2\`. The instruments of V-HEADTOHEAD2 —
`h2.py`, `h2h2b.py`, `gradetest.py`, `geom.py`, `rois.py` — are imported and
not reimplemented; not one byte of `experiments/V-HEADTOHEAD2/` was modified.
The comparator inputs are the linear develops V-LINEAR produced with strehl's
own decoder, which is deliberate: it makes demosaic and white balance identical
on both sides so that the only remaining difference is the stacking algorithm.*

---

## 0. The verdict, first

**On the pre-registered band 0.20–0.25 cyc/px, comparing coherent structure
against coherent structure with half-stack offsets removed, strehl is LEVEL
with Hugin `align_image_stack` + `enfuse --hard-mask` and AHEAD of
`focus-stack` 1.5.**

| comparator | licence | C_strehl / C_comp at 0.20–0.25 | 95% CI | verdict |
|---|---|---:|---|---|
| Hugin `align_image_stack` + `enfuse --hard-mask` | GPL | **0.977** | [0.810, 1.181] | **LEVEL** |
| `focus-stack` 1.5 merge, same Hugin-aligned frames | MIT | **1.326** | [1.089, 1.625] | **strehl AHEAD** |

Floor beneath both: the NULL arm of `gradeatsource.py` — the same estimator
fitted from an image to itself — has an identity bias of **1.0–1.4%**
(0.9861 at 0.20–0.25, i.e. −1.39%). A difference smaller than that is not a
difference.
The falsifier is armed: on a *real* 0.6 px Gaussian blur the BLUR arm shows a
gap of 0.527 at this band of which a 4×4-block tone fit explains **3.3%**, so
the estimator cannot manufacture a resolution difference out of tone.

Four things stand behind that table, and three of them are corrections. A fifth
was added afterwards and is reported as **5** below.

**1. The band question was settled before any comparator ran, and V-LINEAR was
too pessimistic.** `bandsignal.py` measures in-focus against defocused band
power per tile on the linear develops. **0.20–0.25 cyc/px PASSES** at
R = 2.419, CI [1.961, 3.063]. 0.25–0.30 is MARGINAL at 1.387 and everything
above it fails. **This corrects `docs/research/V-LINEAR.md` §5.3**, which
reported 0.20–0.48 as uniformly noise-limited (ratios 1.015, 1.043, 1.004,
1.138). The difference is method, not data: V-LINEAR's `noisefloor.py` compared
four hand-picked whole-frame pairs; `bandsignal.py` chooses each tile's *own*
best-focus and worst-focus frame over 29 tiles. Per-tile focus selection
recovers a factor of 2.4 at 0.20–0.25 that whole-frame pairs averaged away.
V-LINEAR's headline — that the "17–27% behind Zerene" claim was made in a band
carrying essentially no focus-dependent signal — **survives**, because the band
that claim was made in was 0.25–0.30, which still does not pass.

**2. The tone confound is gone.** On the linear develops the 4×4-block tone fit
between strehl and `enfuse` has log-log slope **0.992** and explains
**−0.81%** of the 0.20–0.25 gap. Against the Lightroom-developed Zerene input
of V-HEADTOHEAD2 §4.5 the same estimator gave slope 0.177 and explained
**89.1%**. The acceptance gate this lane inherited is passed, not argued past.

**3. The statistic that produced a first answer was measuring registration, not
resolution — and the error ran against strehl.** strehl's two half-stacks each
chose their own alignment reference and sit **1.319 px apart**; the
comparators' halves, fused from one shared alignment pass, sit 0.03 px apart.
At 0.225 cyc/px a 1 px offset suppresses a cross-spectrum by ×0.156. The first
run said strehl was BEHIND `enfuse` by 0.605. It was not. Corrected, it is
0.977. **Had this not been caught, this lane would have reported a false
retraction.**

**4. There is one framing question I could not close, and I am reporting both
answers.** Every comparator carries 28–40% less absolute coarse (0.05–0.10
cyc/px) contrast than strehl. If you normalise each arm by its own coarse band
— which is what `h2h2b.py` does — that deficit inflates the comparators' fine
bands before the comparison starts, and the `enfuse` verdict flips to BEHIND.
`coarsecheck.py`, written to referee this, **failed its own precondition and
abandoned itself**. §11 gives both framings and the three mechanism arms that
narrow but do not settle it. The headline above uses absolute power, for the
reason given in §11.3 — and it is corroborated by a statistic that needs no
cross-arm normalisation at all (§11.4).

**5. Two arms whose score is fixed by construction were added afterwards, and
they closed an open limitation.** The verdict statistic *fits* a sub-pixel shift
per ROI, and a fit can lock onto noise and invent coherence — which would
flatter strehl most, since strehl is the only arm with a real offset to fit.
`physfloor.py` (§10.1) bounds it from both ends. **SELF** — a crop against
itself, where C ≡ P by construction — returns **1.0000 in every band**, so the
machinery loses nothing. **DISJOINT** — half-stack A at one ROI against
half-stack B at a *different* ROI, sharing sensor, optics and pipeline but no
scene, so C ≡ 0 by construction — was refused outright by the fitter on all 64
pairs, and with the fit disabled reads **0.24% of strehl's coherent power** at
0.20–0.25 against a pre-registered ceiling of 10%. That converts §12's "noise
common to both half-stacks" from undetermined to bounded. It also corroborates
the band selection from an unrelated direction: the same arm reads **40.2% at
0.40–0.48 cyc/px**, so in the bands §2 rejected, a large part of what the
instrument calls "coherent" is the sensor.

---

## 1. What was pre-registered, and when

`experiments/V-LINEAR2/PREREGISTRATION.md` was committed as **`9b192e79`**
before `bandsignal.py` was run and before any comparator was installed. The git
timestamp is the evidence; that is the whole point of committing it separately.
It fixes:

- **§2, the band rule.** A band is usable if in-focus/defocused power is
  R ≥ 2.0 with the lower CI bound ≥ 1.5. The comparison band is the
  **highest-frequency** band that passes. If none above 0.10 cyc/px passes, no
  head-to-head is reported at all.
- **§4, the floors.** NULL identity bias 1.0–1.4% ⇒ |ratio − 1| < 5% reads as
  LEVEL. BLUR arm must keep tone below 10%. `gradetest` must keep tone below
  50% of the gap. The coherence statistic `C` is disclosed as
  noise-contaminated and may not be a headline on its own.
- **§5, the verdict vocabulary**: AHEAD / LEVEL / BEHIND / UNDETERMINED, with
  UNDETERMINED explicitly an acceptable outcome.

Two things in this report were **not** pre-registered and are labelled as such
wherever they appear: the half-stack offset correction (§8), which was written
in response to a defect found during measurement, and the DETAIL/FLAT
discriminator (§6), whose reading criterion was fixed in its own docstring
before it was run but after the band was chosen.

---

## 2. The band that has signal — MEASURED

Defocus is a low-pass filter. In a badly defocused tile, whatever power remains
in a fine band is the floor. So the ratio of in-focus to defocused power at the
same position is a direct measurement of whether the subject contributes
anything in that band.

`python bandsignal.py`, 29 confirmed tiles on the linear develops:

| band, cyc/px | R = in-focus / defocused | 95% CI | verdict |
|---|---:|---|---|
| 0.02–0.05 | 10.504 | [7.147, 15.328] | PASS |
| 0.05–0.10 | 18.193 | [12.420, 28.601] | PASS |
| 0.10–0.20 | 10.083 | [7.465, 13.681] | PASS |
| **0.20–0.25** | **2.419** | **[1.961, 3.063]** | **PASS** |
| 0.25–0.30 | 1.387 | [1.262, 1.543] | MARGINAL |
| 0.30–0.40 | 1.149 | [1.099, 1.208] | FAIL (noise) |
| 0.40–0.48 | 1.105 | [1.055, 1.165] | FAIL (noise) |

The crossover is sharp and the instrument locates it: 0.14–0.17 gives 8.670,
0.17–0.20 gives 4.874, 0.20–0.25 gives 2.419, and then it is over. **By the
pre-registered rule the comparison band is 0.20–0.25 cyc/px.** Nothing finer is
reported anywhere in this document, and the reason `docs/captures-needed.md`
§33 exists is to fix that.

Two controls in the same output. **The population question does not arise**:
`bandsignal.py` reports an ALL population and a CONFIRMED subset (tiles whose
*selection* band itself moved by ≥ 2×, i.e. tiles that demonstrably came into
and out of focus), and here **29 of 29** kept tiles are CONFIRMED, so the two
populations are identical and there is no favourable-subset effect to argue
about. **And R is not a brightness artefact**: the mean-level ratio between the
focused and defocused frames over the kept tiles has median 1.002 and range
0.911–1.167, so the two sides of every ratio are at comparable light levels and
therefore comparable shot-noise contrast. Selection uses 0.05–0.20 cyc/px and
reporting starts at 0.20, which keeps the selection statistically independent of
the reported bands for approximately white noise; the selection band's own R is
printed but is ineligible to be the comparison band for exactly that reason.

**The correction to V-LINEAR §5.3.** That section read the four ratios 1.015,
1.043, 1.004, 1.138 as "this corpus is noise-limited across 0.20–0.48". On
0.20–0.25 that is wrong, and it is wrong because of how the frame pairs were
chosen, not because of the data. `noisefloor.py` compared four fixed
whole-frame pairs; at this magnification only a fraction of any frame is in
focus, so a whole-frame in-focus/defocused ratio averages the sharp part of the
frame together with the parts that were never sharp in either. Choosing each
tile's own best and worst frame recovers R = 2.42 where the whole-frame
estimate gave 1.0. **The claim V-LINEAR retired stays retired** — it was made
at 0.25–0.30, which is MARGINAL at 1.387 and does not pass the gate — but the
stated reason should be narrowed from "0.20–0.48 is noise" to "0.25–0.48 is
noise, and 0.20–0.25 carries a factor of 2.4 that only per-tile focus selection
can see".

---

## 3. The free field — what was installed, from where, under what licence

Zerene Stacker cannot be run on this machine (V-LINEAR §1: `License category =
EXPIREDLICENSE`, zero bytes written). The brief's answer was the right one:
compare against the field that is free, installable, open, and that a reviewer
of an open-source claim would actually reach for.

| arm | binary | licence | provenance |
|---|---|---|---|
| Hugin `align_image_stack` 2025.0.1.9609d5726ad8 | `hugin\Hugin\bin\align_image_stack.exe` | **GPL** | winget's hash-verified MSI, extracted with `msiexec /a` |
| `enfuse` 4.3-993fd4822e8d | `hugin\Hugin\bin\enfuse.exe` | **GPL** (Enblend/Enfuse) | same MSI |
| `focus-stack` 1.5 | `focus-stack.exe` | **MIT** | byte-identical to the upstream 1.5 release |
| `focus-stack`, owner's local build | `C:\dev\macro\tools\focus-stack\...` | **MIT** | separately labelled arm |

**Licence hygiene.** All four are run as black boxes. No comparator source is
vendored, no bytecode is inspected, no algorithm is read out of a binary. What
enters this repository is invocations and numbers.

**Provenance note, MEASURED.** `winget install` fails with exit 1602 without
elevation, but it leaves the *hash-verified* MSI at
`%LOCALAPPDATA%\Temp\WinGet\<Id>\download.msi`, and
`msiexec /a <msi> /qn TARGETDIR=<dir>` performs an administrative extract
without elevation. That is how Hugin got here, and it is why the binaries can
be said to be the published ones rather than something downloaded from a mirror
— SourceForge returns 403/503 to `curl` and `Invoke-WebRequest`, so the direct
route was not available.

**CombineZP and Fiji EDF were not pursued.** Two comparators were obtained, one
of them 16-bit and clean, and the brief asked for at least two. This is a
choice, not an oversight; both remain available to a later lane.

**The exact invocations, all recorded by `run_free.ps1` (rule 47):**

```
align_image_stack -l -m -C --use-given-order -a al_ <63 linear TIFFs>        297 s, 63 frames, canvas 7029x4688
enfuse --exposure-weight=0 --saturation-weight=0 --contrast-weight=1 \
       --hard-mask --output=enfuse-hardmask.tif al_*.tif                     181 s, 230 MB, 16-bit RGBA
focus-stack --output=focusstack-1.5.tif <63 linear TIFFs>                     65 s,  31 MB,  8-bit RGB, 6921x4614
focus-stack (owner's local build), same inputs                               616 s, 144 MB, 16-bit
```

`--use-given-order` is not optional: `align_image_stack` sorts by exposure value
by default, which on a constant-exposure focus stack produces an arbitrary
order. `-l` declares the input linear, which these develops are; `-m` optimises
field of view and `-C` auto-crops to the common area.

**Geometry, re-derived per arm and never assumed** (`geomfree.py`, which imports
`geom.fit` and `geom.offsets` unmodified). V-HEADTOHEAD2 §7 named trusting
geometry as one of the three things that invalidated its pass, and V-LINEAR §3
recorded a warp verdict that evaporated on a like-for-like refit. So every arm
gets its own scale sweep and a sweep without an interior maximum is reported as
a failed fit rather than refined.

| arm | fitted scale | sweep score | global offset | residual rms | per-tile peak, median |
|---|---:|---:|---|---:|---:|
| `enfuse` | 1.0050 | 0.6970 | (−8, −8) | **0.00 px** | 0.6901 |
| `enfuse --levels=1` | 1.0050 | 0.6610 | (−8, −8) | **0.00 px** | 0.6591 |
| `focus-stack` on Hugin frames | 1.0050 | 0.6917 | (−8, −8) | **0.00 px** | 0.6881 |
| `focus-stack` 1.5, own alignment | 1.0230 | 0.6409 | (−16, −24) | **5.39 px** | 0.6514 |

Two things worth stating. First, **the raster ratio is not the content scale**:
`enfuse`'s canvas is 7029 px wide against strehl's 7032, a ratio of 1.0004, but
the fitted content scale is 1.0050, because `align_image_stack -m` remaps.
`focus-stack` 1.5's canvas is 6921, a ratio of 1.0160, against a fitted scale of
1.0230. Only the interior-maximum fit gets either of these right. Second, the
three Hugin-aligned arms land on a **0.00 px** residual after one global integer
shift — the strongest global fit this project has recorded — while
`focus-stack`'s own alignment leaves 5.39 px rms against strehl's raster, which
is why every measurement here uses per-ROI registration as well and reports the
two side by side as a control.

---

## 4. The acceptance gate — MEASURED, and passed

The gate is V-HEADTOHEAD2's `gradetest.py`, called through `gradefree.py` with
`gradetest.main()` unmodified. It fits a monotone tone curve from strehl's
pixels to the comparator's using **only 4×4 block means** — a fit that contains
literally no information above 0.125 cyc/px — and asks how much of the
fine-band gap that curve alone reproduces. If a fit that cannot see fine detail
reproduces the fine-detail gap, the "gap" is tone.

`python gradefree.py enfuse`, 48 ROIs offered, **48 registered, 0 dropped**:

```
empirical tone map strehl->comparator, fitted on 4x4 BLOCK MEANS:
  d(log comp)/d(log strehl): median 0.992  10-90% [0.871,1.287]   (1.000 == identical tone)

                             0.10-0.20   0.20-0.25   0.25-0.30   0.30-0.40   0.40-0.48
gap to explain  comp/strehl     1.2208      1.7982      2.7631      4.3957      6.9940
tone alone      M(s)/s          0.9690      0.9935      1.0651      1.1661      1.1977
fraction of gap explained      -0.1406     -0.0081      0.0369      0.0489      0.0330
```

| | slope | explained at 0.20–0.25 | at 0.25–0.30 | at 0.30–0.40 |
|---|---:|---:|---:|---:|
| V-HEADTOHEAD2 §4.5, Lightroom-developed comparator input | 0.177 | **89.1%** | 100.0% | 212% |
| **this lane, linear develops, `enfuse`** | **0.992** | **−0.81%** | 3.69% | 4.89% |

**The confound is gone.** The tone relationship between the two arms is
identity to within 0.8%, and the fine-band difference between them is not
reproducible from tone. The gate passes for `focus-stack` 1.5 as well.

The sensitivity ladder in the same output is worth keeping in view: a pure
gamma of x^1.5 — the mildest monotone curve there is, changing *no* resolution
whatsoever — moves the 0.20–0.25 band by 21%. That is the size of the effect
being excluded, against verdict margins of 2–33%.

**One inherited failure, reproduced deliberately.** `h2h2b.py`'s own GRADE arm
fails at **190.62%** here, against the 189.90% V-HEADTOHEAD2 §4.4 published.
Reproducing a prior lane's number to three significant figures is the
commissioning evidence that the reuse is faithful. The cause is diagnosed:
`h2h2b.grade()` clips at 2× the ROI median, which hard-clips about 10.1% of
pixels per ROI on linear data. It is therefore demoted from gate to
commissioning check, and `gradetest.py` is the operative gate.

---

## 5. The 8-bit floor — MEASURED, and it runs in the comparator's favour

`focus-stack` 1.5 writes **uint8**. `enfuse` and the owner's local
`focus-stack` build write 16-bit. Truncating strehl's own 16-bit output to 8
bits and re-measuring (`quantfloor.py`) *raises* its normalised 0.20–0.25
statistic by **+14.6%** and its raw band power by **+30.0%**, because
quantisation adds a floor that is proportionally largest where the signal is
smallest.

**The prediction I made about the coherent statistic was wrong, and the
instrument said so.** I expected coherent power C = Σ Re(F_A·conj(F_B)) between
two *independent* half-stacks to be immune, on the grounds that independent
additive noise contributes zero to a cross term in expectation. `quantcoh.py`
tests it by truncating strehl's own two half-stacks to 8 bits and re-running
the identical measurement path. The reading criterion was written into the
docstring before the run:

| at 0.20–0.25, 8-bit ÷ 16-bit | |
|---|---:|
| total power **P** | **×1.350** |
| coherent power **C** | **×1.179** |
| coherent fraction **C/P** | **×0.873** |

**REFUTED: C rises by +17.9%.** The reasoning was wrong because quantisation
error is a *deterministic* function of the pixel value, and two half-stacks of
the same scene have nearly the same pixel values — so their truncation errors
are **correlated, not independent**, and land squarely in the coherent term.

**Direction, which is what matters.** The `focus-stack` arm's C is inflated by
roughly 17.9% by its own bit depth, so `C_strehl/C_comp` against it is
*deflated* by the same factor. The measured 1.326 is therefore a **lower
bound**; a bit-depth-matched estimate would be about 1.56 (DERIVED, assuming
strehl's truncation behaviour transfers, which is why it is not the headline).
The `enfuse` verdict is untouched — both arms there are 16-bit.

The docstring's refuted prediction is kept in the file rather than rewritten,
because the refutation is the more useful record.

---

## 6. The first answer, and why I did not report it

`h2free.py enfuse` computes the statistic V-HEADTOHEAD2 used: band power
normalised by each arm's own 0.05–0.10 band, inside each ROI. It said
`Pn_strehl / Pn_comp = 0.545` at 0.20–0.25 — strehl **BEHIND**, decisively.
Registration was excellent (peak median 0.936, null max 0.793, 63 of 64 ROIs
used), so it was not a geometry failure.

I did not report it, because a normalised band ratio cannot distinguish "the
comparator resolved more" from "the comparator is noisier". `noisesplit.py` was
written to separate them, using `rois.census`'s existing DETAIL/FLAT partition,
with the reading criterion written into the docstring before the numbers
existed: **if the comparator's excess is as large or larger in FLAT regions —
regions with nothing to resolve — the excess is a noise floor, not resolution.**

Comparator / strehl, normalised power at 0.20–0.25, 48 DETAIL and 44 FLAT ROIs:

| arm | DETAIL, per-ROI reg. | DETAIL, global offset | **FLAT** |
|---|---:|---:|---:|
| `enfuse` | 1.686 [1.550, 1.842] | 1.697 | **6.412 [4.610, 9.149]** |
| `focus-stack` 1.5 | 1.781 | 1.748 | **5.680 [4.021, 8.494]** |
| `focus-stack` on Hugin frames | 1.698 [1.527, 1.863] | 1.691 | **5.352 [3.722, 7.814]** |
| `enfuse --levels=1` | 2.343 [2.153, 2.543] | 2.354 | **6.805 [4.823, 9.713]** |

Every comparator's excess is **3–4× larger in regions where the scene is
empty**. Per-ROI and global-offset registration agree to within 1%, so this is
not a registration artefact. The verdict of the criterion, applied as written:
**the excess at 0.20–0.25 in a straight power ratio is noise or overshoot, not
resolution**, and a power ratio is the wrong instrument for this question.

That is what motivated the move to a coherence statistic, which separates
structure that repeats between two independent half-stacks from structure that
does not.

---

## 7. The half-stack registration confound — the most important finding in this lane

A coherence measurement needs two independent stacks of the same scene. The
design: split the 63 frames into odd and even subsets, stack each, and measure
how much of each arm's band power is *common* to the two halves. Real detail
repeats; photon noise does not.

**The first version of that design was wrong and I caught it before it produced
a number.** `run_halves.ps1` ran each comparator's aligner separately on each
half, so the two halves landed on three different rasters — `focus-stack` 1.5's
A, full and B outputs had 4613, 4614 and 4619 rows. A cross-spectrum between
those measures misregistration. The run was stopped, the outputs deleted, and
`run_coh.ps1` written to fuse odd and even subsets of the *single shared*
alignment pass instead. The flawed script is kept on disk with the three row
counts in its header, as the record.

**The second version had a subtler version of the same defect, and this one
nearly published.** `cohfree.py` ran on the corrected halves and reported
`C_strehl / C_comp = 0.605` — strehl behind. The red flag was in the coarse
band: strehl's coherent fraction at **0.05–0.10 cyc/px was 0.897** where
`enfuse`'s was 0.978. At a period of 10–20 pixels there is no photon noise left
to be incoherent about. A coarse-band coherence deficit is not a noise result;
it is a phase error.

`abshift.py` measured it directly:

| arm | n | dy median | dx median | **\|d\| median** | p90 |
|---|---:|---:|---:|---:|---:|
| strehl, `113-A` vs `113-B` | 23 | −0.208 | +0.034 | **1.319 px** | 1.776 |
| `enfuse` halves | 24 | −0.008 | −0.003 | **0.029 px** | 0.067 |
| `focus-stack` halves | 24 | +0.001 | −0.007 | **0.039 px** | 0.078 |

A rigid offset *d* suppresses a cross-spectrum by cos(2πfd). At the comparison
band's midpoint f = 0.225 cyc/px:

| \|d\| | suppression at 0.225 cyc/px | at 0.075 cyc/px |
|---:|---:|---:|
| 0.10 px | ×0.990 | ×0.999 |
| 0.50 px | ×0.760 | ×0.972 |
| **1.00 px** | **×0.156** | ×0.891 |

**strehl's coherent power was being divided by roughly six for a reason with
nothing to do with resolution.** The asymmetry exists because `run_coh.ps1`
gives each comparator one alignment pass and fuses subsets of it, so its halves
share a raster by construction, whereas strehl's halves came from running
strehl separately on each half and each chose its own alignment reference from
its own frames. **That is a property of how the halves were made, not of strehl
as a stacker** — but it handed the comparator a six-fold advantage, in the
direction that manufactures a false retraction.

**This also affects the two prior lanes.** `h2h2b.py`'s `Cn_strehl` is
depressed by the same mechanism wherever strehl's halves were built the same
way. It was always described as a rigorous *one-sided bound*, so no published
claim is wrong — but the magnitude of the suppression was unknown, and it is
large.

---

## 8. The correction, and the self-test that failed twice before it passed

**The correction.** Per ROI, measure the offset between the halves; remove the
integer part by moving the crop window, which is exact and resamples nothing;
remove the sub-pixel remainder by multiplying one half's spectrum by
exp(−2πi(f_y·d_y + f_x·d_x)) before forming the cross term.

**Why it is legitimate.** A pure phase ramp *is* a rigid translation. It leaves
|F_A| and |F_B| — and therefore both arms' band *powers* — untouched, so it
cannot add or remove the blur being measured; it can only restore phase
alignment in the cross term. It is applied identically to every arm, and on the
comparators, whose halves are 0.03 px apart, it does essentially nothing. That
is the control: the correction is not what produces strehl's number.

**The self-test runs first and aborts the whole program on failure.** It takes a
real ROI, shifts it by a known non-integer amount in the Fourier domain, and
compares it with itself. Uncorrected, coherence must collapse in the fine
bands; corrected, it must return to ~1.000 in every band up to and including
the comparison band. If the sign convention were inverted the corrected figure
would be *worse* than the uncorrected one, and the test fails loudly rather
than quietly reporting a flattering number.

It failed twice.

- **v1, parabolic fit through the cross-correlation peak.** FAILED: a
  0.17–0.20 px estimator bias, which at 0.225 cyc/px is worth several percent.
- **v2, weighted phase-slope fit.** Passed at a 0.6 px offset and **failed
  worse** at 1.15 px. Diagnosis: a windowed shifted image is not a shifted
  windowed image, so the pure-ramp model degrades as the shift grows past the
  Hann window's tolerance — and 1.32 px is exactly where that bites.
- **v3, integer-first.** Remove the integer part by moving the crop window,
  then fit the phase ramp only to the sub-pixel remainder, which is always
  ≤ 0.5 px. **PASSES**, at ≥ 0.97 corrected coherence in every band up to and
  including 0.20–0.25, across true offsets of 0.7, 1.2 and 3.0 px.

At the hardest self-test point, a true offset of 2.959 px:

| band | uncorrected | corrected |
|---|---:|---:|
| 0.05–0.10 | 0.5679 | 0.9989 |
| 0.10–0.20 | 0.0047 | 0.9949 |
| **0.20–0.25** | **−0.1903** | **0.9825** |
| 0.30–0.40 | −0.0545 | 0.9530 |

**Residual bias, disclosed: ≤ 1.9%, and it runs against strehl.** The
correction recovers 98.1% of coherence at worst. The shortfall is the same
Hann-window effect, it scales with the offset being corrected, and it therefore
falls on strehl — whose halves are 1.32 px apart — and not on the comparators,
whose halves are barely corrected at all. **strehl's corrected numbers are
underestimates.**

---

## 9. The verdict — MEASURED

`python cohfix.py 130`, self-test PASSED, 128 strehl ROIs and 130 per
comparator. **Note the `focus-stack` arm's identity**: `cohfix.py` reads
`coh-<arm>-{A,B}.tif`, so this is `focus-stack`'s *merge* run on the
Hugin-aligned frames, which is what makes its two halves share a raster. It is a
different pipeline from the full-stack `focus-stack` arm of §3 and is labelled
separately throughout.

**Coherent fraction C/P, corrected** — the share of each arm's own band power
that survives between two independent half-stacks:

| arm | 0.05–0.10 | 0.10–0.20 | **0.20–0.25** | 0.25–0.30 | 0.30–0.40 |
|---|---:|---:|---:|---:|---:|
| strehl | 0.995 | 0.944 | **0.749** | 0.474 | 0.099 |
| `enfuse` | 0.995 | 0.961 | **0.763** | 0.438 | 0.094 |
| `focus-stack` merge | 0.989 | 0.918 | **0.573** | 0.281 | 0.080 |

The same table **without** the correction, which is what `cohfree.py` reported
and which is invalid:

| arm | 0.05–0.10 | 0.10–0.20 | 0.20–0.25 |
|---|---:|---:|---:|
| strehl | 0.924 | 0.776 | 0.546 |
| `enfuse` | 0.995 | 0.962 | 0.766 |
| `focus-stack` merge | 0.990 | 0.920 | 0.577 |

**The correction restores strehl's coarse-band coherent fraction from 0.924 to
0.995, exactly level with the comparators.** That is the independent
confirmation that the deficit was geometric: no resolution argument predicts a
coarse-band coherence deficit, and no resolution argument survives its removal
by a pure phase ramp.

**strehl / comparator, corrected coherent power, 95% bootstrap CI:**

| band | vs `enfuse` (GPL) | vs `focus-stack` merge (MIT) |
|---|---|---|
| 0.02–0.05 | 1.475 [1.186, 1.860] | 1.212 [0.959, 1.553] |
| 0.05–0.10 | 1.552 [1.259, 1.925] | 1.389 [1.105, 1.754] |
| 0.10–0.20 | 1.287 [1.081, 1.540] | 1.491 [1.241, 1.803] |
| **0.20–0.25** | **0.977 [0.810, 1.181]** | **1.326 [1.089, 1.625]** |
| 0.25–0.30 | 0.825 [0.678, 1.002] | 0.993 [0.807, 1.227] |
| 0.30–0.40 | 0.605 [0.414, 0.827] | 0.418 [0.287, 0.572] |
| 0.40–0.48 | 0.321 [−0.453, 1.225] | 0.175 [−0.236, 0.602] |

**Only the 0.20–0.25 row is a verdict.** The rows below it are bands that
failed the pre-registered signal test in §2 and are shown for completeness
only; in those bands the comparators carry more *coherent* power than strehl,
and since the scene contributes nothing there, that is a statement about which
arm's noise is more repeatable between half-stacks, not about resolution. This
is not a post-hoc excuse — the band was fixed in `PREREGISTRATION.md` before
any of these numbers existed.

**At 0.20–0.25:**

- vs **Hugin `align_image_stack` + `enfuse --hard-mask`**: 0.977 [0.810, 1.181]
  — **LEVEL**. The interval spans 1.0 and the point estimate is 2.3% from it,
  inside the 5% pre-registered LEVEL band and only just outside the 1.4%
  identity floor.
- vs **`focus-stack` merge on Hugin-aligned frames**: 1.326 [1.089, 1.625] —
  **strehl AHEAD by 33%**, and the interval excludes 1.0. Conservative twice
  over: the comparator's 8-bit output inflates its coherent power by ~17.9%
  (§5), and the correction bias of §8 costs strehl up to 1.9%. Both run against
  strehl, so 1.326 is a lower bound.

---

## 10. The falsifier, still armed

`gradeatsource.py`, re-run on the linear develops:

| arm | what it is | 0.20–0.25 result |
|---|---|---|
| **NULL** | the tone estimator fitted from an image to *itself* | tone **0.9861**, i.e. an identity bias of **−1.39%** (1.0–1.4% across bands) |
| **BLUR** | a *real* 0.6 px Gaussian blur, a genuine resolution loss | gap **0.5269**, of which tone explains **3.3%** |
| **GRADE** | linear against the Lightroom develop Zerene actually ate | gap **0.0341**, tone 0.8063, explains 20.1% |

The BLUR arm is what makes any of the numbers above credible: when the
difference between two images is genuinely a resolution difference, the
block-average tone fit explains 0.9–4.9% of it across 0.10–0.40 cyc/px — 3.3%
at the comparison band. The estimator cannot manufacture a resolution
difference out of tone, and it does not miss one that is there.

The NULL arm is the floor: **a difference smaller than 1.4% is not a
difference.** The `enfuse` verdict's 2.3% sits just above it, which is a second
and independent reason to read that comparison as LEVEL rather than as a narrow
win for `enfuse`.

### 10.1 Two arms whose score is fixed by construction

The NULL and BLUR arms falsify the *tone* estimator. They say nothing about the
statistic that actually produces the verdict, and that statistic has a specific
exposure: `cohfix.pair_cross` **fits** a sub-pixel shift per ROI before forming
the cross term. A fitted alignment could in principle lock onto noise and
*manufacture* coherence — which would inflate every arm, and inflate strehl
most, because strehl is the only arm with a real 1.32 px offset for the fitter
to work on. `cohfix.py`'s own self-test cannot exclude this: it shifts an image
by a *known* amount and checks the shift is recovered, so it proves the
estimator works when there **is** something to align, and says nothing about
what it does when there is nothing.

`physfloor.py` adds two arms whose true score is fixed in advance by physics,
bracketing the measurement from both ends. Thresholds were written into the
file's docstring before it was first run.

| arm | what fixes its score | pre-registered threshold | MEASURED |
|---|---|---|---|
| **SELF** | a crop against *itself*: every bin has zero phase difference, so C ≡ P | C/P ≥ 0.990 in every band up to 0.20–0.25 | **1.0000 in all seven bands** — PASS |
| **DISJOINT** | half-stack A at one ROI against half-stack B at a *different* ROI: same sensor, same optics, same pipeline, **no shared scene**, so the scene cross-term is 0 | \|C\|/C_strehl < 0.10 at 0.20–0.25 | see below — PASS |

**SELF returns exactly 1.0000 in every band**, so the shared code path loses no
coherence and no `C` in §9 is depressed by the machinery itself.

**DISJOINT produced a stronger result than the threshold anticipated: the
shift fitter refused all 64 pairs.** `refine_shift` declined to return a fit on
every scene-free pair. So the fitter cannot invent coherence on content that has
none, because it does not operate on it at all. That leaves the pre-registered
threshold unevaluable as written, so it was applied instead to the
**DISJOINT-NOFIT** arm — the same disjoint pairs with the fit disabled, which
needs no fit and therefore cannot be refused. The substitution is recorded here
and printed by the instrument rather than made silently.

| band | 0.02–0.05 | 0.05–0.10 | 0.10–0.20 | **0.20–0.25** | 0.25–0.30 | 0.30–0.40 | 0.40–0.48 |
|---|---:|---:|---:|---:|---:|---:|---:|
| \|C_disjoint\| ÷ C_strehl | 0.0111 | 0.0012 | 0.0013 | **0.0024** | 0.0046 | 0.0509 | **0.4015** |

**At the comparison band the scene-free floor is 0.24% of the verdict
statistic** — against a threshold of 10%, and two orders of magnitude below it.

**This closes a limitation §12 previously listed as undetermined.** Common-mode
sensor structure — fixed-pattern noise, PRNU, deterministic pipeline artefacts —
was disclosed as contaminating every `C` in this project by an unknown amount.
It is now bounded at **under 0.25% at 0.20–0.25**.

And the last column is an independent corroboration of the band selection that
arrives from a completely different direction. At **0.40–0.48 cyc/px, 40% of
what the coherence statistic calls "coherent" is not scene at all**; at
0.30–0.40 it is 5.1%; at the comparison band it is 0.24%. §2 rejected those
bands because the *subject* contributes nothing there. §10.1 shows that what
does contribute there is the sensor. Two instruments, no shared assumptions,
same conclusion.

**What this does not do.** The disjoint pair is drawn from different *sensor
positions*, so column- and row-locked fixed-pattern structure is not shared
between the two crops the way it is between two half-stacks of the same ROI.
The arm therefore bounds the estimator's invented coherence tightly, and bounds
site-locked FPN only loosely. A tight bound on that needs a second subject stack
developed identically and compared at the *same* sensor coordinates — a 25-minute
develop and 12.5 GB, not done here. It is stated so the result is not read as
stronger than it is.

---

## 11. The one thing I could not adjudicate: the coarse band

### 11.1 The problem

Every comparator carries substantially less **absolute** coarse (0.05–0.10
cyc/px) contrast than strehl, in the same DETAIL ROIs:

| arm | alignment | merge | abs. 0.05–0.10 power | ÷ strehl |
|---|---|---|---:|---:|
| strehl | strehl | strehl | 0.054107 | 1.000 |
| `focus-stack` 1.5 | focus-stack | focus-stack | 0.038917 | 0.719 |
| `focus-stack` on Hugin frames | Hugin | focus-stack | 0.034751 | 0.642 |
| `enfuse --hard-mask` | Hugin | enfuse, 29-level pyramid | 0.033899 | 0.627 |
| `enfuse --hard-mask --levels=1` | Hugin | enfuse, single level | 0.032274 | 0.596 |

This matters because `h2h2b.py`'s statistic divides each arm by its own
0.05–0.10 band. A comparator with 37% less coarse power gets its fine bands
multiplied by 1.6 before the comparison starts. **The verdict flips with the
choice:**

| framing | vs `enfuse` | vs `focus-stack` 1.5 |
|---|---|---|
| **absolute** (reported above) | 0.977 — LEVEL | 1.326 — AHEAD |
| **coarse-normalised** | 0.63 — BEHIND | 0.955 — LEVEL |

### 11.2 The referee that abandoned itself

`coarsecheck.py` was written to settle it by refereeing each arm's coarse band
against the input frames: whatever the stackers do, none of them should be able
to change coarse structure much, because a 10–20 px period is far below any
plausible defocus cutoff. **Its own precondition test failed.** Frame-to-frame
coarse-band spread across the input stack is **104–136%** — at this
magnification the coarse bands are *not* focus-independent, because defocus at
0.05–0.10 cyc/px is still substantial when the depth of field is micrometres.
The instrument abandoned itself rather than report a comparison it had just
proved it could not make. That is the correct behaviour and it is why this
section says undetermined.

The consequence is the important part: **the frame-to-frame coarse variation is
larger than the 28–40% inter-arm difference under test.** Different stackers
select different frames per pixel, so a coarse-band difference of that size is
consistent with nothing more than different depth selection — which means the
coarse band is not a safe normaliser on this corpus in either direction.

### 11.3 Two mechanism arms, which narrow it without closing it

Both were run specifically to test candidate causes, and both came back
negative:

- **Is it `enfuse`'s multi-scale pyramid?** No. `--levels=1` removes the
  Burt–Adelson pyramid entirely and makes the blend a straight per-pixel mask.
  Coarse power goes 0.627 → **0.596** — marginally *worse*, not better.
- **Is it Hugin's remap?** Partly, at most. Holding the merge fixed at
  `focus-stack` and swapping alignment from focus-stack's own to Hugin's moves
  coarse power 0.719 → 0.642, which is 0.077 of a total deficit of 0.28–0.40.

So no single mechanism accounts for it, and **all four comparator arms sit
28–40% below strehl at coarse scale regardless of aligner or merger**. That is
either strehl preserving coarse contrast better than the entire free field, or
strehl adding coarse contrast the others do not. §4's gate bears on the second
possibility — the block-average tone fit, whose entire information content lies
*below* 0.125 cyc/px and therefore squarely inside this band, puts the strehl→
`enfuse` relationship at slope 0.992 with the gap explained to −0.81%, which is
identity. It does not fully close it, because a per-band gain is not the same
object as a per-pixel tone curve.

**I report the absolute framing as primary** for three reasons, all stated
rather than assumed: `h2.contrast_fft` already divides each crop by its own
mean, so all scalar gain has cancelled before any band is formed; the gate puts
the tone relationship at identity; and §11.2 shows the coarse band is itself
scene- and selection-dependent by more than the effect it would be used to
normalise. **The coarse-normalised numbers are given above so that a reader who
disagrees has them.**

### 11.4 A statistic that needs no normalisation at all, and agrees

Two readings survive any normalisation dispute, because both are computed
*within* a single arm and are therefore immune to any per-arm gain:

**(a) Coherent fraction.** C/P at 0.20–0.25 — coherent power over that same
arm's total power in that same band: strehl **0.749**, `enfuse` **0.763**,
`focus-stack` merge **0.573**. Level with `enfuse`. Against `focus-stack` the
raw gap is 31%, but §5 measured that 8-bit output depresses this particular
statistic by ×0.873, so the bit-depth-matched estimate is ≈0.656 and the honest
reading is **strehl ahead by ~14%** on this statistic, not 31%. Same direction
as the headline, smaller margin.

**(b) FLAT/DETAIL discrimination** (DERIVED from §6's absolute table). The
fraction of an arm's own 0.20–0.25 power that appears in regions with nothing to
resolve:

| arm | FLAT / DETAIL at 0.20–0.25 | at 0.05–0.10 (the scene's own ratio) |
|---|---:|---:|
| strehl | **0.094** | 0.044 |
| `enfuse` | 0.525 | 0.051 |
| `enfuse --levels=1` | 0.489 | 0.064 |
| `focus-stack` on Hugin frames | 0.467 | 0.047 |
| `focus-stack` 1.5 | 0.454 | 0.055 |

At coarse scale all five arms agree on the scene (0.044–0.064), as they must.
At the comparison band strehl puts **9.4%** of its power where there is nothing
to resolve and the free field puts **45–53%**. Normalised by each arm's own
coarse-scale scene ratio that is 2.1× for strehl against 8.9–10.2× for the
comparators — **a factor of 4–5 in how tightly each arm's fine-band output
tracks the presence of actual subject matter.** No cross-arm normalisation
enters this at any point. The two `focus-stack` rows are 8-bit and their FLAT
figures are inflated by that (§5), but the finding does not rest on them: the
two `enfuse` rows are 16-bit, need no correction, and are the *highest* in the
column.

---

## 12. What still cannot be determined, and what would determine it

1. **Resolution above 0.25 cyc/px, on this corpus, by anyone.** §2 is decisive:
   0.25–0.30 is MARGINAL and everything above it is noise. *What would fix it:*
   `docs/captures-needed.md` §33 — a subject with real contrast at a 2–4 px
   period, with `bandsignal.py`'s R ≥ 2.0 as the acceptance test, run before any
   claim.
2. **Resolution against overshoot.** Deterministic sharpening and ringing are
   coherent by construction, so "more coherent fine structure" is resolution
   *or* overshoot, and §9's instrument cannot tell them apart. *What would fix
   it:* the slanted edge of `docs/captures-needed.md` §30, which measures an MTF
   directly and shows overshoot as a lobe above 1.0. It has not been shot.
3. **The coarse band, and therefore the normalisation.** §11. *What would fix
   it:* a synthetic stack — a known scene, known per-frame defocus, known
   ground truth — on which every arm's coarse-band error can be measured against
   the truth rather than against each other. That is a build, not a capture, and
   it is the single highest-value instrument this project does not have.
4. **Noise common to both half-stacks — now bounded, no longer open.** Fixed-
   pattern noise and PRNU are identical in every frame and survive on both arms;
   V-HEADTOHEAD2's NOISE_COM arm scores 6.05. The correction of §8 does not
   touch this. §10.1's DISJOINT arm now bounds it: on pairs that share sensor,
   optics and pipeline but share **no scene**, the coherent term is **0.24% of
   strehl's at 0.20–0.25**, against a pre-registered ceiling of 10%. The §9
   verdict is not meaningfully inflated by non-scene structure at the comparison
   band. Two residual gaps: the bound is loose for *site-locked* FPN, because
   the disjoint crops come from different sensor positions; and it is not a
   bound at all above 0.30 cyc/px, where the same arm reads 5.1% and **40.2%**.
   *What would fix the first:* a second subject stack developed identically and
   compared at the same sensor coordinates — a 25-minute develop, 12.5 GB, or
   equivalently a dark frame and a flat field for this body and lens, which is a
   five-minute capture.

   **UPDATE 2026-08-27 — the capture already existed and the calibration is
   now measured.** `D:\macro-dark-frames` (242 frames, 11 ISOs) and
   `D:\personal\macro\flat-fields` (484 frames) were delivered on 2026-08-22/23
   and are recorded as DELIVERED in `docs/captures-needed.md` §1 and §4. This
   lane did not need to ask. `experiments/V-CALIB/` measures, on this body:
   black **512.10** DN against a nominal 512; gain **0.2232** DN/e⁻ by
   drift-robust photon transfer against the corpus model's 0.2289 (**0.975**);
   read noise **0.887** DN = **3.974** e⁻ against the model's 4.200
   (**0.946**); **DSNU 0.389 DN** and **PRNU 0.286%** of signal, neither of
   which appears in any noise model in this project. What remains open is the
   *band-resolved* split of that structure, which needs the flats developed
   through the same linear path as the subject; the scalar magnitudes above do
   not by themselves say how much lands at 0.40–0.48 cyc/px.
5. **Zerene Stacker.** Still unrunnable, still a purchase. Nothing in this lane
   changes that, and nothing in this lane should be read as a comparison against
   it.
6. **CombineZP, Fiji EDF, and Photoshop auto-blend.** Not attempted. The first
   two are free and would widen the field; the third needs a licence check with
   the owner.

---

## 13. Facts and disciplines registered

**Q1 (fact).** On stack 113's linear develops, per-tile in-focus/defocused band
power is 10.08 at 0.10–0.20 cyc/px, **2.419 [1.961, 3.063] at 0.20–0.25**, 1.387
at 0.25–0.30 and 1.10–1.15 above that. **0.20–0.25 cyc/px is the
highest-frequency band on this corpus that carries focus-dependent signal.**

**Q2 (fact, amends `docs/research/V-LINEAR.md` §5.3).** V-LINEAR's finding that
0.20–0.48 cyc/px is uniformly noise-limited is **too pessimistic at 0.20–0.25**.
The difference is per-tile focus selection: whole-frame in-focus/defocused
ratios average sharp and never-sharp regions together and report ~1.0 where
per-tile selection reports 2.42. The retraction V-LINEAR supported stands, as it
was made at 0.25–0.30.

**Q3 (fact).** On linear develops the 4×4-block monotone tone fit between
strehl and `enfuse` has log-log slope **0.992** and explains **−0.81%** of the
0.20–0.25 gap, against slope 0.177 and 89.1% for the Lightroom-developed
comparator input of V-HEADTOHEAD2 §4.5. **Developing both arms with the same
decoder removes the tone confound; it does not merely reduce it.**

**Q4 (fact).** strehl's two half-stacks, each stacked independently, sit
**1.319 px apart** (p90 1.776); comparator half-stacks fused from one shared
alignment pass sit **0.029–0.039 px** apart. At 0.225 cyc/px a 1 px offset
suppresses a cross-spectrum by **×0.156**. Every uncorrected `C_strehl` in this
project is depressed by this, including V-HEADTOHEAD2's and V-LINEAR's.

**Q5 (fact).** With half-stack offsets removed, at 0.20–0.25 cyc/px on linear
develops, `C_strehl/C_comp` is **0.977 [0.810, 1.181]** against Hugin
`align_image_stack` + `enfuse --hard-mask` (GPL) and **1.326 [1.089, 1.625]**
against `focus-stack` 1.5's merge on the same Hugin-aligned frames (MIT).
Coherent fractions C/P: strehl 0.749, `enfuse` 0.763, `focus-stack` 0.573.

**Q6 (fact).** strehl places **9.4%** of its 0.20–0.25 band power in regions
with no local contrast; `enfuse`, `enfuse --levels=1` and both `focus-stack`
arms place **45–53%** there. At 0.05–0.10 all five agree at 0.044–0.064. This
comparison is internal to each arm and needs no cross-arm normalisation.

**Q7 (fact).** Every comparator carries 28–40% less absolute 0.05–0.10 cyc/px
contrast than strehl. It is **not** `enfuse`'s pyramid — `--levels=1` makes it
slightly worse (0.627 → 0.596) — and swapping alignment under a fixed merge
accounts for only 0.077 of it. The cause is undetermined.

**Q8 (fact).** Truncating a 16-bit render to 8 bits **raises** its normalised
0.20–0.25 band statistic by **+14.6%**, its raw band power by **+30.0%**, and —
against expectation — its *coherent* power between two independent half-stacks
by **+17.9%**. `focus-stack` 1.5 writes uint8, so all three of its fine-band
numbers are inflated in its own favour.

**Q9 (fact, and a refuted prediction).** Quantisation error is **not**
independent between two stacks of the same scene. It is a deterministic
function of the pixel value, so two half-stacks with nearly equal pixels have
nearly equal truncation errors, and the error appears in the *coherent* term of
a cross-spectrum rather than cancelling. `quantcoh.py` predicted C would be
bit-depth-neutral, wrote that prediction down, and measured +17.9%.

**Q10 (discipline).** **A coherence measurement between two stacks measures
their registration before it measures anything else.** Measure the offset
between the halves *first*, and read the coarse-band coherent fraction as the
alarm: at a 10–20 px period there is no photon noise to lose, so any coarse
deficit is a phase error, not a noise result. This one cost a factor of six, in
the direction of a false retraction.

**Q11 (discipline).** **When two arms are built by different routes, check that
the *construction* is symmetric before comparing them.** Comparator halves were
subsets of one alignment pass; strehl's halves each ran their own aligner. The
asymmetry was in the harness, not in either program, and it favoured the
comparator.

**Q12 (discipline).** **A sub-pixel shift estimator must be commissioned at the
offset it will actually meet.** A parabolic peak fit carries ~0.2 px bias; a
windowed phase-slope fit passes at 0.6 px and fails worse at 1.15 px, because a
windowed shifted image is not a shifted windowed image. Remove the integer part
by moving the crop window first, then fit the ramp to a remainder that is always
≤ 0.5 px.

**Q13 (discipline).** **Report which direction a residual bias runs, every
time.** The phase-ramp correction recovers 98.1% at worst; the shortfall scales
with the offset corrected and therefore falls entirely on strehl. Stating that
turns an unquantified worry into a one-sided bound.

**Q14 (discipline).** **A normalising denominator is a claim and needs its own
evidence.** Dividing each arm by its own coarse band silently asserts that the
coarse band is arm-independent. On this corpus it is not: frame-to-frame coarse
spread is 104–136%, larger than the inter-arm difference. Prefer statistics
computed *within* one arm, which cannot be argued with.

**Q15 (discipline).** **An instrument that fails its own precondition should
abandon itself and say so.** `coarsecheck.py` did, and the resulting
"undetermined" is worth more than the number it would otherwise have printed.

**Q16 (discipline).** **`winget install` failing 1602 without elevation still
leaves a hash-verified MSI** at `%LOCALAPPDATA%\Temp\WinGet\<Id>\download.msi`,
extractable with `msiexec /a <msi> /qn TARGETDIR=<dir>` and no elevation. This
is how to obtain a comparator binary with provenance when the vendor's mirror
refuses scripted download.

**Q17 (discipline).** **Never write markdown through `python -c "..."` in
PowerShell.** Double-quoted PowerShell strings consume backticks as an escape
character before python sees them, so a code span arrives as a control byte with
its closing backtick silently deleted. `corpus_lint`'s S7 check caught four of
these in one paragraph. Write the payload to a `.py` file and run the file.

**Q18 (discipline).** **A noise-independence argument is a hypothesis, not a
control.** "That error is independent between the two arms, so it cancels in
the cross term" is exactly the kind of claim that sounds like analysis and
behaves like an assumption. Write the prediction into the instrument's
docstring, run it against a case where ground truth is available, and keep the
refutation in the file if it comes. Here the prediction was that coherent power
is bit-depth-neutral; the measurement said +17.9%, because quantisation error
is deterministic in the pixel value and two stacks of one scene share it.

**Q19 (fact).** The per-ROI sub-pixel shift fit in `cohfix.pair_cross` does not
manufacture coherence. On 64 disjoint pairs — half-stack A at one ROI against
half-stack B at a different ROI, sharing sensor, optics and pipeline but sharing
no scene — **the fitter refused all 64**, and with the fit disabled the residual
coherent term is **0.24% of strehl's at 0.20–0.25 cyc/px**. The same statistic
reads **5.1% at 0.30–0.40 and 40.2% at 0.40–0.48**, so above 0.30 cyc/px a large
fraction of what this instrument calls coherent is sensor, not scene.

**Q20 (discipline).** **A statistic needs an arm whose true score is fixed by
construction — at *both* ends of its range.** One that physically cannot score
(here DISJOINT: no shared scene, so C ≡ 0) bounds what the machinery invents;
one that must score perfectly (here SELF: a crop against itself, so C ≡ P)
proves the machinery loses nothing. A self-test that recovers a *known* shift
proves only that the estimator works when there is something to find, and says
nothing about what it does when there is nothing — which is the failure mode
that produces a false positive. Both arms are cheap, and their expected values
are known before the run, so neither can be rationalised after the fact.

**Q21 (discipline).** **When a fixed-score arm passes by a route the
pre-registration did not anticipate, say so and re-aim the threshold in the
open.** DISJOINT was pre-registered as `|C|/C_strehl < 0.10`; it instead
returned no value at all, because the estimator declined to fit any scene-free
pair. That is a stronger outcome than a small number, but it is not the
registered one, so the threshold was applied to a fit-disabled variant of the
same arm and the substitution was printed by the instrument and recorded in the
report. A pre-registration that is quietly reinterpreted to fit what happened is
worth less than none.

---

## 14. Reproducing this

```powershell
cd experiments\V-LINEAR2
python bandsignal.py                    # band selection, BEFORE anything else
python quantfloor.py                    # the 8-bit power floor
& .\run_free.ps1                        # the comparator battery, ~20 min
& .\run_coh.ps1                         # shared-raster half-stacks
python geomfree.py                      # geometry, re-derived per arm
python gradefree.py enfuse              # THE ACCEPTANCE GATE
python noisesplit.py enfuse 48          # DETAIL vs FLAT
python abshift.py                       # half-stack registration per arm
python cohfix.py 130                    # the verdict; self-test runs first
python physfloor.py 64                  # SELF and DISJOINT fixed-score arms
python quantcoh.py 64                   # the 8-bit floor against COHERENT power
cd ..\V-LINEAR
python gradeatsource.py 10,15,20,25,30,35,40,45,50 4   # NULL / BLUR / GRADE
```

Comparator outputs `C:\dev\strehl-out\V-LINEAR2\out\`; logs and geometry fits
`C:\dev\strehl-out\V-LINEAR2\logs\`; Hugin binaries
`C:\dev\strehl-out\V-LINEAR2\hugin\Hugin\bin\`; the linear develops are
V-LINEAR's, at `C:\dev\strehl-out\V-LINEAR\lintiff\`.

### Housekeeping, recorded rather than tidied away

- `run_halves.ps1` is the **superseded and defective** half-stack design of §7.
  It is kept on disk, with the three differing row counts in its header, because
  the error it embodies is more instructive than the script that replaced it.
- `cohfree.py`'s result — `C_strehl/C_comp = 0.605` — is **invalid** and is
  retained only as the record of what the registration confound produced. Its
  file header says so.
- `coarsecheck.py` produces no number by design (§11.2).
- `h2free.py`'s `enfuse-lv1` entry is a **mechanism arm, not a comparator**, and
  is labelled as such in the source; it exists only to test a candidate cause in
  §11.3 and must not be quoted as a head-to-head result. `h2free.py`'s
  `coh-fs15` entry was added for the same §11.3 test, but that *output* is also
  the `focus-stack` arm of the §9 verdict — it is the only `focus-stack` result
  whose two halves share a raster, which is what a coherence measurement
  requires. Both roles are stated wherever it appears.
- `fixctl.py`, `capreq33.py` and `renumq.py` exist because of Q17;
  `capreq33.py` regenerates `docs/captures-needed.md` §33 from a source file and
  refuses to write if the payload contains a control byte.
- `quantcoh.py`'s docstring contains a **refuted prediction** and is left that
  way deliberately (Q18). The file predicted coherent power would be
  bit-depth-neutral, and its own measurement said +17.9%.
- The gain-invariance control V-LINEAR left owing — re-run a subset with a known
  global scalar gain, to prove no comparator has an absolute threshold that
  penalises a dark linear encoding — was **not run here either**. It is cheaper
  now than it was, because all four comparators do run.
