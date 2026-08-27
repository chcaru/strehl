# V-LINEAR — closing Blocker 1: the licence, the linear inputs, and the band that has no signal in it

*Lane V-LINEAR. Every number below was produced by code in
`experiments/V-LINEAR/` and is quoted from a log or a console capture under
`C:\dev\strehl-out\V-LINEAR\`. Nothing is carried over from V-HEADTOHEAD2
except its instruments, which are imported and not reimplemented, and its
strehl-arm renders, which are not used for any number here.*

---

> ## ⚠ PARTIALLY SUPERSEDED — read this before §0.3, §5.3 or P7
>
> **`docs/research/V-LINEAR2.md` §1 overturns this document's reading of the
> 0.20–0.25 cyc/px band, and this file's title restates the superseded
> version.** The four ratios below — **1.015, 1.043, 1.004, 1.138** — come from
> four hand-picked **whole-frame** pairs. Letting each of 29 tiles choose its
> *own* best-focus and worst-focus frame, on these same linear develops, gives
> **R = 2.419, CI [1.961, 3.063]** at 0.20–0.25 cyc/px; **1.387 MARGINAL** at
> 0.25–0.30; and failing above 0.30. Whole-frame pairs average sharp and
> never-sharp regions together and report ~1.0 where per-tile selection
> recovers a factor of 2.4.
>
> **What is withdrawn:** the conclusion that 0.20–0.48 cyc/px is uniformly a
> noise band, *for 0.20–0.25 only*. It stands at 0.25–0.30 and above.
>
> **What survives, and it is this lane's headline:** the "17–27% behind Zerene"
> claim was made in a band with no focus-dependent signal. That claim was made
> at **0.25–0.30**, which still does not pass. The retraction this lane
> supported is unaffected.
>
> **Every original number is retained below, unedited.** The measurement is
> reproducible and the correction is auditable; nothing here is deleted.
>
> **Known dependency, not fixed here.** `docs/research/V-HEADTOHEAD2.md` §3b
> imports these whole-frame ratios and uses them *against its own* headline
> result. That lane is still running and is being routed separately, so this
> lane has deliberately not edited it. Whoever picks it up should start there.

---

## 0. The verdict, first

I was sent to close V-HEADTOHEAD2 §7's Blocker 1 — re-develop the comparator's
inputs without a grade, re-run Zerene, and put the fine-scale question to a
measurement for the first time. Three findings, and the third is the one that
matters.

**1. Zerene Stacker cannot be run on this machine at all. Its trial licence
expired on 2026-06-06 and it refuses to save output.** `License category =
EXPIREDLICENSE`. It is not watermarking and not degrading: it loads the frames,
aligns them, runs PMax to completion — 138.6 s of CPU across 6 frames — and then
puts up a dialog reading *"Trial expired: cannot save output image: Aborting
batch run."* and writes **zero bytes**. The brief asked me to check the licence
state before trusting a single pixel of its output. There are no pixels to
trust. This is a purchase, not a bug, and no amount of engineering closes it.

**2. Blocker 1's fix is not free, and the reason is not the licence.** §7 asked
for the same TIFFs re-exported "with zero contrast, zero curve, zero clarity,
zero texture, zero sharpening, and a linear tone response". I produced exactly
that with strehl's own decoder, 63 frames. Comparing them against the graded
TIFFs Zerene actually ate: the graded files carry **2.61× more** coarse
(0.02–0.05 cyc/px) contrast and **49× less** fine (0.25–0.30 cyc/px) contrast,
coarse-normalised — and a 4×4-block monotone tone fit, the estimator that
explained 89–212% of the *output-side* gap, explains only **17.2%** of this.
A tone curve cannot move a fine band by 49×. **Something other than tone
dominates the difference between the comparator's inputs and a linear
develop**, so re-developing linearly does not isolate the stacking algorithm;
it trades one confound for another.

**3. The band the whole dispute lives in contains no focus-dependent signal on
this corpus.** *(Superseded in part — see the banner at the head of this file.
Per-tile focus selection recovers R = 2.419 at 0.20–0.25 cyc/px; this finding
stands at 0.25–0.30, which is where the retracted claim was made, so the
conclusion drawn from it below is unaffected.)* Defocus is a low-pass filter, so in a badly defocused tile
whatever fine-band power remains is the noise floor. In strehl's linear
develops, a tile that is *in focus* has the same 0.20–0.48 cyc/px power as the
same tile 20 frames out of focus: ratio **1.015, 1.004, 1.043, 1.138** across
four independent frame pairs. Focusing the lens does not measurably change the
fine bands. **The 0.25–0.30 cyc/px comparison that produced "17–27% behind
Zerene" was conducted in a band where these frames carry essentially nothing
but noise.** That is a third, independent reason the retracted claim was not a
resolution measurement — and unlike the first two it is not fixed by a licence,
a re-export, or a better comparator. It is fixed by different data.

**So: the question cannot be answered, and it is now clear that it could not
have been answered even if Zerene had run.** I did not produce a band table,
because the gate that licenses one could not be run and the data underneath it
would not have supported one.

---

## 1. Zerene's licence state — measured, and it is the blocker

The brief flagged this as a must-check-first. It was right to.

**Installed:** `C:\Program Files\ZereneStacker\`, **Zerene Stacker 1.04 Build
T2026-05-04-0750**, bundled Zulu OpenJDK 25.0.1 JRE. `%APPDATA%\ZereneStacker\
LicenseKey.txt` **does not exist**.

From the console of a real batch launch (`zerene-welcome` capture,
`experiments/V-LINEAR/capture_dialog.ps1`), MEASURED:

```
0.438: trial.info=1.0,1778210014628,9b39f19827d162b7a3dc867110f8777a
0.479: license 83ced522295099724b84c81abbb79f3199726fd7 expires on Sat Jun 06 20:13:34 PDT 2026
0.480: now = Thu Aug 27 02:40:05 PDT 2026
0.480: relevant = false
0.481: Using default license key
0.481: License category = EXPIREDLICENSE
```

The May 2026 session that produced the existing comparator TIFF logged
`License category = TRIAL` — i.e. **the comparator now in the repository was
made under a then-valid trial that has since lapsed.**

The application stops on a modal dialog (`logs\zerene-welcome.png`) reading:

> **THE FREE TRIAL PERIOD FOR THIS SOFTWARE HAS EXPIRED.**
> You will not be able to save images or projects until a valid license key is
> installed.
> `[Visit Website] [Install License Key] [Continue as Expired] [Exit Immediately]`

I took **Continue as Expired** — a path the vendor offers to the user — to find
out whether the claim was literal or whether output would instead be
watermarked or degraded, which would have been a worse confound than the one I
was sent to remove. It is literal. Zerene loaded the six frames, registered
them, ran PMax to completion (138.6 s CPU, 6,048 MB working set at the moment
the dialog appeared), and then:

> **Cannot save images with an expired trial**
> Trial expired: cannot save output image: Aborting batch run.

`logs\zerene-cannot-save.png`. Output folder afterwards: **EMPTY — zero files
written**; source folder unchanged.

**Licence hygiene.** Nothing here inspects, patches, decompiles or bypasses
anything. `ZereneStacker.jar` was never opened. The licence check ran, reached
its own conclusion, and I recorded it. The system clock was not touched. The
owner's `zerenstk.cfg` was backed up before the first launch and verified
byte-identical afterwards (sha256 `22293EC5CEBB…` both times).

### The invocation, for whoever runs this with a licence

This is not the flag the brief guessed. Zerene's Batch API documents
**`-batchScript path/foo.xml`**; `-runBatchScript` does not exist. The rest of
the command line must be taken verbatim from `%APPDATA%\ZereneStacker\
zerenstk.launchcmd`, which Zerene writes itself:

```
C:\Program Files\ZereneStacker\jre\bin\java.exe
  -Dsun.java2d.opengl=false -Dsun.java2d.d3d=false -Dsun.java2d.xrender=false
  -Dsun.java2d.metal=false -Dsun.java2d.noddraw=true
  -Xmx56516m
  -XX:ErrorFile=C:\Users\chris\AppData\Roaming\ZereneStacker\hs_err_pid%p.log
  -DjavaBits=64bitJava
  -Dlaunchcmddir=C:\Users\chris\AppData\Roaming\ZereneStacker
  -classpath "C:\Program Files\ZereneStacker\ZereneStacker.jar;C:\Program Files\ZereneStacker\JREextensions\*"
  com.zerenesystems.stacker.gui.MainFrame
  -noSplashScreen -exitOnBatchScriptCompletion -runMinimized
  -batchScript <path.xml>
```

`java.exe`, not `javaw.exe` — the vendor's own note says javaw runs silently and
produces no console output. `experiments/V-LINEAR/run_zerene.ps1` builds this
from the launchcmd rather than hard-coding it, and
`experiments/V-LINEAR/make_batch.py` emits the XML with its schema provenance
recorded per element (vendor documentation for the document shape,
`ProjectDispositionCode=101`, `OutputImageDispositionCode=2`, the naming
template and `TaskIndicatorCode=1`=PMax; named third-party repositories for
`TaskIndicatorCode=2`=DMap and `OutputImageDispositionCode=5` +
`OutputImagesDesignatedFolder`). **PMax reached the save step and DMap was
never run**, because there was no point running a second method against the
same refusal.

**Both of these were verified to work up to the licence wall**: the XML parsed,
the sources loaded, alignment and stacking ran to completion. The only untested
element is `OutputImageDispositionCode=5`, which Zerene never reached.

### Two failures of my own, recorded because they are the interesting kind

- **A GUI-hosted batch tool does not fail with an exit code. It hangs.** My
  first launcher tokenised the launchcmd with `'"[^"]*"|\S+'` plus
  `Trim('"')`, which mangles `-Dlaunchcmddir="C:\path\with\no\spaces"` into
  `-Dlaunchcmddir="C:\path…` — a stray leading quote. Zerene put up *"Problem
  with application data directory"* and sat there: process **Responding**, 2.03
  s of CPU in nine minutes, no output, no exit, forever. `run_zerene.ps1` now
  carries a watchdog that enumerates the process's visible top-level windows and
  aborts on any that is not on a known-benign list. It is what caught the
  licence dialog too, in 15 s instead of never.
- **`Start-Process -ArgumentList` does not quote its arguments.** It joins the
  array with spaces, which split `-classpath "C:\Program Files\…"` and produced
  `Could not find or load main class Files\ZereneStacker\ZereneStacker.jar`. Use
  `ProcessStartInfo.ArgumentList`, which applies the Win32 quoting rules per
  element.

---

## 2. The linear inputs — produced, and delivered regardless

63 frames, `D:\personal\macro\113MSDCF\*.ARW` → `C:\dev\strehl-out\V-LINEAR\
lintiff\DSC000NN.tif`, 7032×4688 u16, **197,798,923 bytes each**, all exit 0.
`experiments/V-LINEAR/develop_frames.ps1`, full rule-47 header (binary path and
sha256, every flag including those left at default, every environment
variable).

**Why strehl's own decoder, deliberately.** The brief asked me to preserve this
and it is worth stating why: developing both arms' input with the same decoder
makes demosaic, white balance, black level, colour matrix and CA correction
**bit-identical across the two arms**. Whatever error those stages carry, both
arms carry the same one, and it cancels. The only thing left different between
the arms is the stacking algorithm, which is the thing under test. Developing
the comparator's input with *any* other program — including a "neutral"
Lightroom export — reintroduces exactly the class of difference this lane
exists to remove.

Two decisions inside the develop, both measured rather than assumed:

- **`STREHL_ALIGN=0`.** With alignment on, even a one-frame `stack` reports
  `coverage: field of view scaled to 0.9974 … then upsampled` — a CatmullRom
  resample. Disabling it gives `alignment: OFF`, so the Zerene arm would carry
  exactly one registration resample (Zerene's own) rather than two.
- **The develop is dark and does not clip**: median ≈1150/65535 (1.75%), p99
  ≈6000, max 17660, zero clipped samples. At 14 bits, 1 raw DN ≈ 4.4 u16
  counts, so there is no quantisation loss. This is what linear looks like; it
  is also, as §5 shows, what makes the noise floor visible.

**ICC, measured** (`icc_dump.py`, parsing the published ICC.1:2010 layout):
strehl's TIFFs carry a 696-byte profile, `desc` = "strehl linear sRGB (BT.709-6
primaries, D65, gamma 1.0)", rTRC/gTRC/bTRC = `curv` count 0 = identity. The
Lightroom TIFFs Zerene ate carry Adobe's 516-byte **"Adobe RGB (1998) (Linear
RGB Profile)"**, TRC gamma **1.0000**, 32-bit float. So both are gamma-1.0
encoded and the *encoding* was never the confound — the grade is baked into the
values. The arms differ in primaries (BT.709 vs Adobe RGB), which is a linear
3×3: it cannot generate harmonics and cannot fake a tone confound.

---

## 3. Geometry, re-derived not trusted — and a wrong verdict I caught

§7 warned that geometry must be re-derived. It must, and it nearly cost me a
false headline.

`geomgrid.py`, 30 tiles of 384 px on frame 32, `h2.integer_shift` (the prior
lane's own primitive), gated at correlation peak ≥ 0.70:

| model | residual rms | max |
|---|---|---|
| pure translation | 4.73 px | 11.73 px |
| affine (translation + scale + rotation + shear) | 2.87 px | 9.33 px |
| affine, robust set (26 of 28) | **1.97 px** | — |
| affine + radial `k1,k2`, same robust set | 1.73 px | — |

Fitted scale LIN/LR **y 1.00189, x 1.00166** (pixel-count ratio 1.00342, so it
is a scale *and* a differing crop).

**The wrong verdict.** The `dx` column marches monotonically from −6 px at the
left edge to +5 px at the right, which looks exactly like a lens-distortion
correction applied by Lightroom and not by strehl. My first version of this
script printed *"VERDICT: NON-LINEAR RADIAL WARP"* — and it was comparing a
**robust** affine+radial fit against a **non-robust** affine fit. The
improvement it was crediting to the radial term came from dropping three
outlier tiles. Fitted on the same tiles, the radial term buys 12% of the
residual and its coefficients are `k1 = −0.0023 px`, `k2 = −0.0009 px` — i.e.
nothing. **There is no warp.** The geometry is affine to ~2 px rms and the
residual is registration scatter on single, largely defocused frames.

That is the correct answer and it is duller than the one I nearly published.

---

## 4. The gate: pre-registered, and why no number is reported against it

**Pre-registration, written before any Zerene run and unchanged since.**
V-HEADTOHEAD2's `gradetest.py` on the graded pair (48/48 ROIs) returned
tone-alone ratios **1.934 / 2.354 / 1.899** and fractions of gap explained
**89.1% / 100.0% / 212%** at 0.20–0.25 / 0.25–0.30 / 0.30–0.40 cyc/px, with
median `d(log comp)/d(log strehl)` = 0.177. On genuinely linear inputs the gate
passes only if **all** of:

- **Primary:** |tone − 1| ≤ 0.10 in each of the three fine bands;
- **Secondary:** fraction of gap explained by tone < 0.5 in every fine band
  where a gap exists;
- **Tertiary:** median `d(log comp)/d(log strehl)` within [0.90, 1.10];
- `gradetest.py`'s own verdict strings read "tone does NOT explain the gap".

Failure ⇒ report the failure and report **no band numbers**.

**The gate was not run, because its second input does not exist.** `gradetest.py`
requires a comparator render of the linear inputs. Zerene wrote zero bytes. I
am recording the pre-registration anyway, unchanged, so that whoever finishes
this cannot choose the criterion after seeing the result.

**What I did not do:** repoint `h2h2b.COMP` at the *old graded* Zerene output
and report those bands as if they were the linear comparison. They are not, and
a tone map cannot be inverted after the fact — Zerene made its selection
decisions on contrast-boosted gradients, and no post-hoc curve undoes a
decision.

---

## 5. What could be measured without a licence

Both developments of the same 63 exposures now exist. That makes the *input*
side of §7's claim measurable for the first time, with no stacker in the loop —
and it turns out to be where the story is.

### 5.1 The instrument, commissioned two-sidedly

`gradeatsource.py` runs three arms through identical code, importing
`gradetest.fit_map` / `apply_map` and `h2h2b.band_power` / `coarse` rather than
reimplementing them. Tiles are 256 px with 32 px pad, registered per-tile,
gated at peak ≥ 0.70, and admitted only where **this** frame is a local maximum
of fine-band power against frames ±4 away — the interior-maximum rule from
`geom.py`, applied to focus. 20 tiles survive from 9 frames.

| arm | 0.20–0.25 | 0.25–0.30 | 0.30–0.40 |
|---|---|---|---|
| **NULL** LIN vs LIN — tone M/A | 0.9861 | 0.9898 | 0.9932 |
| **BLUR** LIN vs blur(LIN, σ=0.6 px) — gap B/A | 0.5269 | 0.3718 | 0.1993 |
| **BLUR** — tone M/A | 0.9845 | 0.9892 | 0.9924 |
| **BLUR** — *explained by tone* | **3.3%** | **1.7%** | **0.9%** |

Two things follow, and the second is the important one.

- **The tone-application step has a small identity bias.** Fitting a map from
  an image to *itself* and applying it loses ~1–1.4% of fine-band power
  (NULL row). `fit_map` is a 256-knot quantile interpolation and interpolation
  between knots is mildly smoothing. It is small against V-HEADTOHEAD2's
  headline but it is a real bias in the direction of *understating* tone, and it
  had not been measured.
- **The falsifier passes, and it commissions V-HEADTOHEAD2's method.** A 4×4
  block-mean tone fit contains no information above 0.125 cyc/px, so it should
  be unable to reproduce a pure blur. It explains **0.9–3.3%** of a 0.6 px
  Gaussian — and most of even that is the identity bias just measured. **The
  technique genuinely cannot manufacture a resolution difference out of tone.**
  V-HEADTOHEAD2's 89–212% is therefore not an artefact of its estimator. That
  is a positive result for the prior lane, obtained by an arm it did not run.

### 5.2 The grade at its source, and the 49× that is not tone

Same instrument, arm **GRADE**: strehl's linear develop vs the Lightroom TIFF
of the same RAW frame — the actual file Zerene consumed.

| band | gap LR/LIN | tone M/A | explained by tone |
|---|---|---|---|
| 0.02–0.05 | **2.6148** | 1.0585 | 3.6% |
| 0.05–0.10 | 1.0000 (reference) | 1.0000 | — |
| 0.10–0.20 | 0.1636 | 0.8547 | 17.4% |
| 0.20–0.25 | 0.0341 | 0.8063 | 20.1% |
| 0.25–0.30 | **0.0206** | 0.8312 | **17.2%** |
| 0.30–0.40 | 0.0160 | 0.8309 | 17.2% |
| 0.40–0.48 | 0.0206 | 0.8623 | 14.1% |

MEASURED: the graded input has 2.61× more coarse contrast and **1/49th** the
fine contrast of the linear develop, coarse-normalised. DERIVED: a monotone
tone map fitted on block means accounts for at most a fifth of that, and no
monotone curve can move a band by 49× while the falsifier above shows the
estimator would have detected it if one had.

**Disclosure.** This arm is not purely tone: LIN and LR also differ by demosaic
algorithm, by the 1.0018 scale and crop of §3, and by primaries. So it bounds
the tone contribution from *above* and its honest reading is "a block-average
tone fit accounts for this fraction of the whole input-side difference".

### 5.3 Why: the fine bands of a linear frame are noise

> **SUPERSEDED IN PART by `docs/research/V-LINEAR2.md` §1.** The per-band table
> and the four aggregate ratios below are from **whole-frame** pairs. Per-tile
> focus selection over 29 tiles on the same develops gives **R = 2.419**,
> CI [1.961, 3.063], at 0.20–0.25 cyc/px — so **the 0.20–0.25 row below is
> withdrawn**. 0.25–0.30 (1.387, MARGINAL) and everything above 0.30 stand, and
> with them this section's use in §6. Numbers retained unedited; see the banner
> at the head of this file for the full statement and for the
> `V-HEADTOHEAD2.md` §3b dependency.

`noisefloor.py`. Defocus is a low-pass filter, so a badly defocused tile
contains no real detail at fine scale and whatever power is there is the noise
floor. Compare, at the same position, an in-focus frame against one 20 frames
away:

| band | strehl linear, in/defocused | Lightroom, in/defocused |
|---|---|---|
| 0.02–0.05 | 6.826 | 2.896 |
| 0.05–0.10 | 8.128 | 5.453 |
| 0.10–0.20 | 2.741 | 4.768 |
| 0.20–0.25 | **1.188** | 2.977 |
| 0.25–0.30 | **1.011** | 2.506 |
| 0.30–0.40 | **0.962** | 2.137 |
| 0.40–0.48 | **0.950** | 2.150 |

Aggregate over 0.20–0.48, four independent frame pairs (35/15, 25/5, 50/30,
45/15): strehl linear **1.015, 1.043, 1.004, 1.138**. Lightroom **2.744, 619,
1.134, 171** — wildly unstable, because its denominator is a *denoised*
defocused tile with almost nothing left in it, which is itself the finding.

MEASURED: **in a single linear-developed frame, focusing the lens does not
measurably change the 0.20–0.48 cyc/px band.** DERIVED: per-frame fine-band
signal power is ≲15% of noise power at 0.25–0.30. ARGUED: a stacker that
*selects* rather than averages cannot improve that at all, and one that averages
the K frames in focus at a given point improves power SNR by at most K; with
K ≈ 5–10 here, stacked fine-band SNR stays of order 1. **The band the dispute
lives in is a noise band on this corpus.**

This also explains §5.2 without appeal to anything exotic: Lightroom's pipeline
removes the noise floor, strehl's linear develop does not, and 49× is the size
of that floor.

### 5.4 The trap this avoided

Had the licence been valid, the "free fix" would have fed Zerene 63 frames
whose fine bands are noise, and PMax — which selects maximum local contrast —
would have been selecting noise. The comparator would have come out worse, and
the natural reading of that table would have been *"strehl beats Zerene at fine
scale on tone-matched inputs"*. That number would have been wrong, it would
have been in strehl's favour, and it would have been the third retraction.

---

## 6. The question, answered

**On tone-matched linear inputs, does strehl out-resolve, match, or trail
Zerene Stacker at fine scale?**

**Still cannot be determined.** Two reasons, of very different weight:

1. **Proximate:** Zerene will not save output on this machine (§1). This is a
   purchase.
2. **Fundamental, and it survives the purchase:** at 0.25–0.30 cyc/px this
   corpus carries no measurable focus-dependent signal in a linear development
   (§5.3). Buying a licence and re-running would produce a table, and the table
   would be a comparison of two programs' noise handling wearing the word
   "resolution".

The one thing I can say in strehl's favour is procedural, not performance:
V-HEADTOHEAD2's retraction of the "17–27% behind" claim is now supported by a
third independent line of evidence, and its estimator has been commissioned
against a falsifier it did not itself run (§5.1). The claim was correctly
retracted. It should not be re-asserted in either direction.

---

## 7. What still cannot be determined, and exactly what would determine it

- **Zerene's behaviour on linear input.** Needs a licence key
  (`%APPDATA%\ZereneStacker\LicenseKey.txt`). Everything else is built and
  tested up to the wall: `run_zerene.ps1` + `make_batch.py` will run PMax and
  DMap unattended the moment one exists. Cost: one purchase, plus compute
  extrapolated from the pilot at roughly 23 s of CPU per frame per method.
- **Whether `OutputImageDispositionCode=5` is honoured on build
  T2026-05-04-0750.** Zerene aborted before the save step. Fallback is the
  vendor-documented `2` (save in source folder) plus a move.
- **A fine-scale resolution comparison of any two stackers.** Needs *different
  data*, not a different comparator: a subject with real contrast above 0.20
  cyc/px, exposed so that a linear development is not noise-limited there —
  lower ISO, brighter subject, or many more frames per focus step. The
  diagnostic is `noisefloor.py`; a usable stack is one whose in-focus/defocused
  ratio at 0.25–0.30 is comfortably above ~2, as Lightroom's denoised files are
  and strehl's linear ones are not. **This should be added to
  `docs/captures-needed.md`.**
- **Whether the 49× is noise reduction specifically**, as opposed to demosaic
  smoothing or a Process-Version difference. I have bounded it (not tone, ≤20%)
  but not attributed it. Determined by re-exporting one frame from Lightroom
  with NR explicitly at zero and re-running `gradeatsource.py` — which needs the
  owner and Lightroom, and is the *only* part of this lane that does.
- **The disclosed weakness in `C`** (V-HEADTOHEAD2's NOISE_COM arm scoring
  6.05, coherence inflated by noise common to both half-stacks) is untouched by
  this lane — and §5.3 makes it materially worse than it looked, since the noise
  common to both half-stacks is now measured to *dominate* the fine bands.

---

## 8. Proposed facts and disciplines

Numbered per rule 28 as proposals; the orchestrator allocates absolute numbers.

**P1 (fact).** Zerene Stacker 1.04 Build T2026-05-04-0750 on this machine runs
as `License category = EXPIREDLICENSE` (default key, expired 2026-06-06). It
performs alignment and stacking to completion and then refuses to write output:
*"Trial expired: cannot save output image: Aborting batch run."* Zero bytes
written. The Zerene comparator in this repository is **not reproducible** here.

**P2 (fact).** Zerene's batch option is `-batchScript <path.xml>`, not
`-runBatchScript`, and the rest of the command line must be taken from
`%APPDATA%\ZereneStacker\zerenstk.launchcmd` with `javaw.exe` replaced by
`java.exe` to obtain console output.

**P3 (fact).** strehl's linear develop and Lightroom's export of the same RAW
differ geometrically by an **affine** transform (scale y 1.00189, x 1.00166)
to 1.97 px rms. A two-parameter radial term buys 12% of that with coefficients
of −0.002 px: there is **no lens-distortion warp** between them.

**P4 (fact).** A 4×4-block monotone tone fit — `gradetest.fit_map` +
`apply_map` — explains **0.9–3.3%** of a pure 0.6 px Gaussian blur in the
0.20–0.40 cyc/px bands. The estimator cannot manufacture a resolution
difference out of tone, which commissions V-HEADTOHEAD2 §4.5.

**P5 (fact).** The same estimator has an identity bias: fitted from an image to
itself, it loses 1.0–1.4% of fine-band power. Small, but signed, and in the
direction of understating tone.

**P6 (fact).** The graded TIFFs fed to the comparators carry **2.61×** the
coarse (0.02–0.05) and **1/49th** the fine (0.25–0.30) coarse-normalised
contrast of a linear develop of the same RAW. A block-average tone fit explains
**17.2%** of the fine-band difference. **The dominant input-side difference
between graded and linear is not tone.**

**P7 (fact).** In single linear-developed frames of stack 113, fine-band
(0.20–0.48 cyc/px) contrast power is unchanged by focus: in-focus/defocused =
1.015, 1.043, 1.004, 1.138 over four frame pairs, against 2.1–3.0 per band for
the Lightroom development of the same frames. **This corpus is noise-limited in
the band every strehl-versus-anything fine-scale claim has been made in.**

> **P7 IS AMENDED by `docs/research/V-LINEAR2.md` §1 / Q2.** The four ratios
> are whole-frame; per-tile selection gives **R = 2.419 [1.961, 3.063]** at
> 0.20–0.25 cyc/px. **P7 should be registered for 0.25–0.48 cyc/px only.** The
> sentence in bold is true as written for 0.25–0.48 and false at 0.20–0.25.
> Because every fine-scale claim it refers to was made at 0.25–0.30, the
> consequence P7 was registered to support is unchanged.

**P8 (discipline).** A GUI-hosted batch application fails by **hanging on a
modal dialog**, not by exiting non-zero. Any harness that drives one must poll
the process's visible top-level windows against an allow-list and abort on
anything else. Exit code is not a liveness signal. (Cost of learning this: nine
minutes of a process at 2.03 s CPU, Responding, producing nothing.)

**P9 (discipline).** When comparing two models to decide whether the richer one
is needed, fit both on the **same** rows, and choose the outlier-rejection set
with the **simpler** model's residual. Comparing a robust fit of the rich model
against a non-robust fit of the simple one credits the extra parameters with
the outlier rejection. This produced a confident "NON-LINEAR RADIAL WARP"
verdict from coefficients of 0.002 px.

**P10 (discipline).** Before comparing two renders in a frequency band, measure
whether that band contains signal, by comparing in-focus against defocused
power at the same position. A band whose in-focus/defocused ratio is ~1 is a
noise band, and every ratio computed in it is a comparison of noise policies.
This is one script and it should run *before* the head-to-head, not after.

**P11 (discipline).** `Start-Process -ArgumentList` joins its array with spaces
and does not quote members containing spaces. Use
`ProcessStartInfo.ArgumentList`, which applies the Win32 quoting rules per
element.

**P12 (discipline).** **A correction that only points backwards is invisible
from the place where the error is read.** A successor document that opens by
naming the section it corrects is necessary and not sufficient: the superseded
section has no idea anything came after it, and a reader arriving there
directly — by citation, by search, or by following a link from a third
document — has no way to discover the correction short of noticing a later
directory entry. **The retraction has to live where the mistake is, not only
where the fix is.** Cost of learning this: §5.3's whole-frame ratios were read
as current after `V-LINEAR2.md` §1 had already overturned them, and were
published to the owner-facing README and sent to two working lanes as grounds
to doubt their instruments. Forward banners are cheap; the original numbers
stay, unedited, so the file remains reproducible and the correction auditable.
The banner must also name any **third-party dependants** it knows of — here
`V-HEADTOHEAD2.md` §3b — because the agent who can fix the dependant is
usually not the agent who owns the corrected file.

---

## 9. Reproducing this

```powershell
cd experiments\V-LINEAR
& .\develop_frames.ps1                      # 63 linear TIFFs, ~25 min, 12.5 GB
python geomgrid.py 32                       # geometry, re-derived
python gradeatsource.py 10,15,20,25,30,35,40,45,50 4   # NULL / BLUR / GRADE
python noisefloor.py 35 20                  # the band-has-no-signal test
& .\capture_dialog.ps1                      # licence state, from the dialog

# with a licence installed, and only then:
& .\run_zerene.ps1 -Source C:\dev\strehl-out\V-LINEAR\lintiff `
    -OutDir C:\dev\strehl-out\V-LINEAR\zerene -Method PMax -Name full-PMax
```

Logs, batch XML and dialog captures: `C:\dev\strehl-out\V-LINEAR\logs\`.
Linear develops: `C:\dev\strehl-out\V-LINEAR\lintiff\`. Zerene config backup:
`C:\dev\strehl-out\V-LINEAR\zerenstk.cfg.backup-before-V-LINEAR`.

### Housekeeping, recorded rather than tidied away

- `geomprobe.py` is the **superseded** 5-position first version of §3. Kept
  because its 26 px `dy` spread is what prompted the grid version, and one of
  its five positions was a mis-registration at correlation peak 0.59 — an
  argument for the peak gate, made by the instrument against itself.
- `make_batch.py`'s DMap preferences set
  `UseFixedContrastThresholdPercentile=true` at the owner's own 12.4, rather
  than the absolute `DepthMapControl.ContrastThresholdLevel=8.177664E-6` in
  `zerenstk.cfg`, because that absolute threshold was calibrated on bright
  graded frames and the linear develops are ~50× darker. **Untested** — DMap
  never ran.
- The planned gain-invariance control (re-run a subset with a known global
  scalar gain, to prove Zerene has no absolute threshold that penalises a dark
  linear encoding) was **not run**, because it requires Zerene to save output.
  It remains the right control and `make_batch.py` is set up for it.
- `commission_develop.py`, promised in `develop_frames.ps1`'s header as an
  assertion that a one-frame pyramid `stack` is a passthrough, was **not
  written**. The develops are used here only as *inputs* to a differential
  measurement in which the same decoder appears on both sides of every
  comparison except §5.2, and §5.2's conclusion is a lower bound that a
  passthrough defect could only strengthen. It is still owed before any
  absolute claim rests on them.
