# V-NOISE — pre-registration

Committed **before** any statistic in this lane was computed. The git timestamp
is the evidence, which is the only reason to commit it separately.

Lane: the noise half of the free-field head-to-head. The sharpness half is
`docs/research/V-LINEAR2.md` §9: level with `enfuse` (0.977, CI [0.810, 1.181]),
ahead of `focus-stack` 1.5 (1.326, CI [1.089, 1.625]), at 0.20–0.25 cyc/px.
Against those two comparators **sharpness is the whole of what has been
measured**. Every noise, clipping and rim advantage this project holds is
against its own predecessor or against single input frames, not against
`enfuse` or `focus-stack`.

---

## 0. Disclosure — this pre-registration is NOT blind, and here is exactly how

I have already seen one statistic that bears on the outcome.
`experiments/V-LINEAR2/noisesplit.py` reported a within-arm FLAT/DETAIL power
ratio at 0.20–0.25 cyc/px of **strehl 0.094, `enfuse` 0.525, `enfuse --levels=1`
0.489, `focus-stack`-on-Hugin-frames 0.467, `focus-stack` 1.5 0.454**. Those
numbers were produced for a different purpose — to establish that strehl's
fine-band advantage was not concentrated in featureless regions — and I read
them at the time.

A ratio of 0.094 against 0.525 is a fivefold difference in the direction that
flatters strehl. **So I know the likely sign of the result before registering
the test, and this document cannot claim otherwise.** What it can still do, and
what it is for:

- fix the **ROI rule**, the **statistic**, the **floors** and the **success
  criterion** before any of them is computed on this question;
- fix the **commissioning arms** before their outcome is known;
- commit me to reporting an unflattering result, which is the part that is
  actually at risk when the sign is already suspected.

Anyone weighing the result should discount it accordingly and lean on §4's
commissioning arms, whose outcomes I genuinely do not know.

---

## 1. Inputs, and why they are the right ones

All arms are built from **strehl's own linear TIFFs** — `--linear-srgb
--demosaic`, pinned binary sha256 `15EA7346…82A7B0`. Demosaic and white balance
are therefore identical on every side and the only remaining difference is the
stacking algorithm. This is the same property that makes the sharpness table
trustworthy, and it costs nothing to reuse.

| arm | file | licence |
|---|---|---|
| strehl | `C:\dev\strehl-out\V-H2H2\lin\113-full-g1.tiff` | this project |
| `enfuse --hard-mask` | `C:\dev\strehl-out\V-LINEAR2\out\enfuse-hardmask.tif` | GPL |
| `focus-stack` 1.5 | `…\out\focusstack-1.5.tif` | MIT |

Half-stacks (`113-A-g1`/`113-B-g1`, `coh-enfuse-A/B`, `coh-fs15-A/B`) are used
only for the §3.2 cross-check.

`C:\dev\strehl-out\SHIP-V2\` is **never** read by this lane.

---

## 2. The ROI rule — fixed here, computed from the SOURCE, never from an output

Selecting flat regions by looking at a stacker's output would be selecting on
the thing being measured. So:

1. Candidate ROIs are a fixed grid of 256×256 tiles at stride 256 on the
   registered common canvas, with a 128 px margin excluded (breathing shrinks
   the field).
2. For each tile, detail energy is computed **on the source linear TIFFs** as
   the maximum over frames of the high-pass variance. Maximum over frames, not
   mean, so a tile counts as detailed if *any* frame could have resolved detail
   there — the conservative direction.
3. **FLAT = the bottom quartile of that per-tile maximum.** Fixed at 25%; not
   tuned.
4. A tile is dropped if any arm clips it: max ≥ 0.98 of range, or min ≤ 0.02,
   in any channel.
5. The resulting tile list is **identical for every arm**, written to disk
   before any arm is scored, and reported with its count.

## 3. The statistic

### 3.1 Primary — residual sigma in flat ROIs

Per ROI, per channel: subtract a local mean (uniform filter, 9 px) and take the
standard deviation of the residual. This is what a print reviewer sees: grain
on a featureless surface.

**Luma and chroma are reported separately**, in a linear opponent basis:

- `Y  = 0.2126 R + 0.7152 G + 0.0722 B` (Rec.709 linear luma)
- `C1 = R − Y`, `C2 = B − Y`

Chroma is reported because stackers differ far more in chroma speckle than in
luma sigma, and chroma speckle is disproportionately visible in a print.

Each arm's sigma is **normalised by its own ROI mean level** before comparison,
so an exposure difference between arms cannot masquerade as noise. The reported
quantity is `sigma_arm / sigma_strehl`; **>1 means the comparator is noisier.**

### 3.2 Cross-check — half-stack difference

`0.5·Var(A − B)` over the same ROIs, where A and B are two half-stacks of the
same scene. The scene cancels; what remains is noise. strehl's halves sit
**1.319 px apart** (V-LINEAR2 §7) and the comparators' 0.03 px, so the
integer-shift-then-phase-ramp correction of `cohfix.pair_cross` **must** be
applied first or this statistic measures misregistration. If the two estimators
disagree in sign, the result is reported as UNDETERMINED and no winner is
declared.

### 3.3 Band treatment, stated explicitly

Noise is reported **broadband** (primary) and per band. **For this question the
0.30–0.48 cyc/px region is treated as SIGNAL, not contamination.** V-LINEAR2 §2
rejected those bands for *sharpness* because the subject contributes nothing
there, and §10.1 measured that 40.2% of "coherent" power at 0.40–0.48 is
non-scene. That is precisely where noise lives, so for a noise question it is
the most informative region, not the least. The same fact carries opposite
meaning for the two questions and this lane says so rather than reusing the
earlier verdict unexamined.

## 4. Commissioning — the arms whose outcome I do not know

The instrument does not get to report a number until all three pass.

- **NULL (identity floor).** Statistic computed on an image against itself.
  Must return **1.000 ± 0.005**. Any difference smaller than the observed floor
  is not a difference, and will be described that way in the report.
- **POTENCY (planted noise).** Gaussian noise of known sigma added to one side.
  The statistic must move by the predicted `sqrt(sigma0² + sigma_added²)`,
  agreeing to **within 10%**, at two levels (0.5× and 2× the measured noise).
  *A noise metric that cannot detect planted noise cannot certify its absence.*
  If POTENCY fails, this lane reports no comparison at all.
- **TONE (the confound).** The 4×4-block monotone tone fit
  (`gradetest.fit_map`/`apply_map`) is fitted between arms and applied, and the
  statistic recomputed. **If the tone fit reproduces ≥50% of the noise ratio,
  the comparison is declared a tone measurement and withdrawn**, exactly as
  V-HEADTOHEAD2's fine-scale table was. A tone curve that lifts shadows raises
  measured noise without anything real having changed.

## 5. Success criterion and verdict vocabulary

Fixed now:

- **CLEANER / NOISIER** — the ratio's 95% CI (bootstrap over ROIs, 2000
  resamples) excludes 1.0 **and** |ratio − 1| exceeds the NULL floor.
- **LEVEL** — CI includes 1.0, or |ratio − 1| is below the NULL floor.
- **UNDETERMINED** — §3.1 and §3.2 disagree in sign, or any §4 arm fails.

The result is reported **whichever way it falls**. A measured loss to `enfuse`
on noise is worth more to the owner than an unmeasured win, and is exactly the
kind of finding that must not first surface after publication.
