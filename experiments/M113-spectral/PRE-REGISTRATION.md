# M113-spectral: pre-registration

Written and timestamped BEFORE any stack beyond bee-3-cpl and couch-fibers-cpl
was rendered. Nothing below was chosen after seeing a result.

## The claim under test

My own fact 8 / corpus fact 1570: `needed` differs 23.6 % between bee-3-cpl
(529.9 ppm) and couch-fibers-cpl (654.9 ppm), attributed to SCENE SPECTRUM --
a channel's effective wavelength being its passband centroid weighted by the
scene's spectral radiance. ORCH has already rewritten the owner's #1 capture
request on the strength of that attribution. It was ARGUED, never tested.

## What EXIF already settles, before any measurement

Read from frame 0 and frame n/2 of every candidate stack:

- **Aperture is constant** at f/5.6 across every `-cpl` stack. Only coffee-bean
  and foam differ (f/8) and both are excluded as non-CPL anyway.
- **The optical path is constant**: every stack reports
  `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter` at 200 mm.
- **Focus distance is NOT constant** at the reference frame: 0.2738 (tweezers),
  0.2771 (leaf-2), 0.2841 (bee-1, couch-fibers, lavendar, dry-erase-marker-head,
  flower-bud-with-background-fern), 0.2917 (bee-2, bee-3).

So rivals 1 (aperture) and 3 (teleconverter) are dead on the metadata alone, and
rival 2 (magnification) is the live one.

## The natural experiment this creates

**bee-1-cpl is the crux.** It is the SAME SUBJECT as bee-2/bee-3, so the
spectral hypothesis predicts it needs what they need. It is at the SAME FOCUS
DISTANCE as couch-fibers-cpl, so the magnification hypothesis predicts it needs
what couch needs. Those predictions are 529.9 and 654.9 ppm, 23.6 % apart, and
one render decides between them.

Two further groupings do work for free:

- **Within 0.2841 m**: bee-1, couch-fibers, lavendar, dry-erase-marker-head.
  Magnification is held constant by construction across four different subjects.
- **bee-2 vs bee-3 at 0.2917 m**: same subject, same distance -- a pure
  repeatability replicate that bounds the noise on `needed`.

## Bars

**S0 -- instrument check, per stack, discipline 810.** `applied / eps_r` must lie
in **[0.90, 1.02]**. A stack outside that band is reported as UNDETERMINED and is
EXCLUDED from every correlation below. Registered because I established 0.94-0.98
on two stacks and have no right to assume it holds on a third.

**S1 -- replicate bound.** |needed(bee-2) - needed(bee-3)| defines the
repeatability floor. If it exceeds **60 ppm** (half the 125 ppm bee-3/couch gap),
then the instrument cannot resolve between-stack differences at all and the whole
question is UNDETERMINED.

**S2 -- the crux, and the explicit falsifier.** Let `d = needed(bee-1)`.
- If `d` is within **60 ppm of the bee-2/bee-3 mean** and more than 60 ppm from
  couch, the variation tracks SUBJECT: spectral SUPPORTED, magnification refuted.
- If `d` is within **60 ppm of couch** and more than 60 ppm from the bee mean,
  the variation tracks FOCUS DISTANCE: **spectral REFUTED**, magnification is the
  explanation, and the owner should shoot an aperture/magnification ladder rather
  than gels.
- Anything else: UNDETERMINED.

**S3 -- constant-magnification group.** Across the four stacks at 0.2841 m, let
`R` be the range of `needed`. If `R <= 60 ppm`, magnification alone accounts for
the between-stack variation and **spectral is REFUTED**. If `R >= 125 ppm` (the
original bee-3/couch gap) with magnification held fixed, spectrum or some other
scene property is real.

**S4 -- dispersion ratio, a free second discriminator.** Measure `needed_B`
(blue against green) on the same windows as `needed_R`. A pure magnification or
alignment change scales the whole image, so it multiplies eps_R and eps_B by the
SAME factor and leaves `needed_B / needed_R` invariant. A change in effective
wavelength moves the two independently. Falsifier: if the coefficient of
variation of `needed_B / needed_R` across stacks is **below 10 %** while `needed_R`
itself varies by more than 20 %, the between-stack variation is a COMMON SCALE
and is not spectral.

**S5 -- alignment, my own outstanding Gap.** Render the reference frame ALONE
with `STREHL_ALIGN=0` and no merge, by copying that single ARW to a scratch
directory on C:. Measure `needed_R` on it and compare with the aligned merged
value for the same stack. Bar: agreement within **60 ppm** means align and merge
contribute nothing to `needed` and it is optical. A larger difference means part
of `needed` is manufactured by the pipeline.

**S6 -- colour proxy.** Spearman rank correlation between `needed_R` and scene
R/G, over all stacks passing S0. The physical argument predicts a redder scene
needs a LARGER correction, so the correlation must be **positive**. A negative or
null correlation does not by itself refute the spectral hypothesis, because a
three-channel ratio cannot see within-passband weighting -- and that limitation
is registered HERE, in advance, as a reason this bar is weak evidence either way.

## Stated in advance: what this design cannot do

Three-channel data cannot measure the spectral radiance INSIDE a channel's
passband. If S2 and S3 point at subject rather than magnification, that
establishes a scene-dependent effect but does NOT establish that the mechanism is
spectral -- subject colour, subject radial structure and subject material all
covary. The honest ceiling of this experiment is therefore:
REFUTE the spectral attribution, or narrow it to "scene-dependent, mechanism not
yet identified". It cannot confirm it.