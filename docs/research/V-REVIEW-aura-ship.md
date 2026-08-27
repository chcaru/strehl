# Aura on the shipping pin

Adjudicated by the V-REVIEW lane. Re-measures the README's aura / veiling entry
on `9b05d0b7`, the binary that rendered the 26 SHIP-V4 masters.

## Verdict for the owner

**The aura is not in the shipping product. Strike the entry, or re-scope it to
the non-default `--merge estimator` backend.**

The veil is real, it is large, and it is visible: a plateau of roughly 18
display levels holding from 30 px out to 150 px around the subject. It belongs
to `--merge estimator`. The shipping default is `--merge pyramid`, and on the
same frames its ground recovers monotonically to within one display level of
its own far field. Re-measured on the shipping pin, the difference the README
quotes has the **opposite** sign to the one the entry implies: the arm that
shipped is the cleaner of the two, by up to 14.72 display levels.

## Gauge

Pin **derived** from the corpus seal rather than declared, using the guard
hardened in the previous task: 26 sealed masters name `44C2F2CD...F490`, which
selects `9b05d0b7`, and the binary hashes to that seal.

**Space.** Encoded sRGB, deliberately. The question is what a viewer sees on a
print, and the encoded file is what the print receives. **No ratios are taken
anywhere below** -- the transfer curve moves ratios, so only DN differences and
display levels are quoted. One display level is 257 DN.

**Band.** Every statistic here is spatial: distance-transform annuli over
medians. **No frequency transform is taken at any point**, so the formally
withdrawn statistic above 0.30 cyc/px does not apply to any number in this
document.

## Controls

The strongest one first: the comparison arm was required to reproduce the
shipped master **byte for byte**, not merely to resemble it.

| control | arm | result |
|---|---|---|
| A1 byte-exact | pyramid render vs `flower-bud-alone-cpl` master | `D9B88743...B8FD` both, IDENTICAL |
| A2 byte-exact | pyramid render vs `coffee-bean` master | `41153A82...C721` both, IDENTICAL |
| B null | same pixels differenced against themselves | `+0.000000` DN |
| C plant | smooth aura of 1.0 level planted | recovered `+0.50` levels, expected `+0.53` |
| C plant | smooth aura of 4.0 levels planted | recovered `+2.03` levels, expected `+2.13` |
| K3 cannot-fire | sham surround differenced against other shams | `z = -1.09` |

Control A is what makes the rest admissible: because the pyramid arm is
bit-identical to the delivered file, the estimator arm differs from what the
owner has by the named switch and by nothing else -- not by exposure, not by
environment, not by build.

## The measurement

Fine radial profile on `flower-bud-alone-cpl`, 5 px bins, display levels
relative to each arm's own far field. Positive is brighter than far field.

| distance from subject | shipping pyramid | estimator |
|---|---|---|
| 0-5 px | `-78.51` | `-77.11` |
| 25-30 px | `-5.42` | `-15.55` |
| 45-50 px | `-2.84` | `-16.96` |
| 80-85 px | `-1.05` | `-18.76` |
| 115-120 px | `-0.27` | `-18.98` |
| 120-150 px | `+0.07` | `-18.07` |
| 270-300 px | `+1.26` | `-2.56` |

The two arms separate completely. The shipping arm decays monotonically and is
back inside one display level by 80 px. The estimator does not decay: it falls
to about 15 levels by 25 px and then **deepens** to a plateau near 19 levels
that holds out past 150 px. That plateau is the aura.

The estimator is also slightly **brighter** than the shipping arm in the first
5 px, by 1.40 levels, before turning darker from 5 px outward. A bright
overshoot at the edge with a dark undershoot beyond it is a halo, and it is
what the 1:1 crop shows.

## Excess over a far baseline

An aura grows toward the subject. A level difference between two merges does
not. Subtracting each subject's most distant band removes any common-mode
offset by construction:

| subject | 20-50 px | 50-80 px | 80-200 px | shape |
|---|---|---|---|---|
| flower-bud-alone-cpl | `+9.81` | `+13.59` | `+14.72` | radial, real |
| bee-1-cpl | `-3.10` | `+2.20` | `+1.13` | radial, real |
| 112MSDCF | `-0.98` | `-0.52` | `-0.33` | flat, level offset |
| 113MSDCF | `-0.72` | `-0.31` | `-0.18` | flat, level offset |

Positive means the shipping arm is brighter, so the veil is the estimator's.

## Visual call, made at 1:1

Crops are 400x400 at native resolution, written from the encoded master. No
decimation and no stretch, because a visual verdict above roughly 400 px is not
admissible in this project.

On `flower-bud-alone-cpl` the estimator crop carries an obvious white rim
hugging the subject boundary with a greyed background beyond it. The shipping
master has neither. On `bee-1-cpl` the estimator crop shows hard polygonal
patches where the selection switched frames; the shipping master is continuous.
Both visual readings agree with the numbers, and neither shows an aura on the
delivered file.

## What this corpus cannot see

The whole-frame statistic was **underpowered and is not counted as evidence in
either direction**. Measured across the masters it ran from `-71.83` to
`+58.87` display levels, because the far field at 800-2000 px sits toward the
vignetted corners while the near band contains the subject's own shadow. A
statistic with a spread of 130 levels cannot bound an effect of a few.

Pricing that floor with a sham surround -- the real subject's own mask
translated to a place where no merge aura can exist -- gives: 17 subjects
measured, 9 refused for an unpriceable null, summing to the 26 masters. The
detection floor, taken as the median sham spread, is 10.65 levels at 20-50 px,
10.07 at 50-80 px and 8.92 at 80-200 px.

**The z-scores from that null must not be read as significance.** They reach
`-23.3`, so the null is fat-tailed and the scale is not calibrated. No positive
excursion in this corpus is a detection, and the two that came closest are
disposed of in the table above.

## Corrections to my own work in this task

1. **My first pass reported ten subjects as VISIBLE, the largest at `+57.40`
   display levels.** All of it was unmasked subject, the subject's physical
   shadow, and lens vignetting. The texture guard did not fire on cases the
   same script's commissioning block had labelled contaminated. **Withdrawn in
   full.**
2. **I used a single frame as the zero-aura reference. It is not one.** A
   single frame has the subject defocused, so its dark edge spreads outward and
   it carries the *largest* skirt of any arm. Measured as frames accumulate:
   `+29.98`, `+28.86`, `+23.18`, `-0.05` levels for 1, 5, 25 and 205 frames,
   monotonically shrinking, which is the prediction the mechanism makes. **That
   differential is withdrawn.**
3. **A verdict line in `va_cand.py` fired on an invented threshold.** It
   declared a genuine pyramid aura whenever the difference beat 1.0 display
   levels in any band beyond 20 px. The difference on those subjects is flat
   with distance, including at 400-800 px where no aura reaches. Corrected by
   the far-baseline excess above, it is under one display level. **That printed
   verdict is withdrawn**; the corrected number stands.

The first and third are the same defect twice: a threshold or a guard that was
written down rather than commissioned. The second was caught only because the
number surprised me and the mechanism was checked before it was reported.

## Uncertainty

The residual on the shipping arm is bounded at under one display level beyond
80 px on subjects whose ground is uniform enough to support the fine radial
profile. It is **not** bounded that tightly corpus-wide: on subjects with
structured grounds the whole-frame floor stands at roughly 9 to 11 display
levels, and an aura hiding under that would not be found by anything in this
document. What can be said corpus-wide is narrower and is enough for the
decision: no subject shows a radial darkening profile on the shipping arm that
survives its own null, and every subject rendered both ways shows the veil on
the estimator rather than on the default.

## Related

- `docs/research/V-REVIEW-aura.md` -- the estimator-versus-pyramid work this
  supersedes for the purpose of the README entry.
- `docs/research/V-REVIEW-merge-rim.md` -- the rim statistic and why a
  resampler that cannot ring read worse than the shipping default.

## Addendum: the three binary claims, audited

Raised as an urgent addendum to this task. Adjudicated rather than accepted.

### The missing build is not missing

**REFUTED.** `066A87ABF8C4D337539ADBA17A9453ABE93728360816700C43E6852099F0437B`
is present at `C:\dev\strehl-out\V-REVIEW\bin\strehl-pinned.exe`, 9,716,736
bytes. The original aura renders **are** reproducible, and the README caveat
should not be strengthened to say otherwise.

The absence report is an artifact of the search, not of the filesystem, and the
mechanism is measured rather than supposed:

| search pattern | paths | distinct builds |
|---|---|---|
| exact name `strehl.exe` | 159 | 63 |
| any `strehl*.exe` | 301 | 165 |

An exact-name search cannot reach 102 of the builds on this machine, including
this one, because the file is named `strehl-pinned.exe`. Twenty-six distinct
filenames carry builds it cannot see, among them `strehl-base.exe`,
`strehl-pre.exe`, `strehl-post.exe` and every Cargo hash-suffixed artifact.

> **A search narrower than the thing it is looking for returns the same empty
> result as a search that looked everywhere.** "Not found" is a statement about
> the query until the query's reach has been measured.

Nothing in the aura verdict depends on this. The re-measurement was made on the
shipping pin, which is a stronger footing than the build it replaces.

### The mislabelled pin is real

**CONFIRMED.** `C:\dev\strehl-out\PIN-V3\strehl.exe` hashes
`B50EABC12D16B29095AAE82240698F3D51BFB64482D4993725437B4CE11A7C99` and appears
in no seal of any corpus, at exactly 9,568,768 bytes.

### The pin directory is mostly not pins, and the size collision is worse

**CONFIRMED, with the count corrected upward.** Sealed corpora and their seals:
`PINTEST` and `SHIP-V3` both name `15EA7346`, `SHIP-V4` names `44C2F2CD`.
Against those, `acceptance-pins` partitions as 2 sealed and 3 unsealed, summing
to the 5 pins present.

| build | size | standing |
|---|---|---|
| `15EA7346` | 9,568,768 | seals PINTEST and SHIP-V3 |
| `44C2F2CD` | 9,568,768 | seals SHIP-V4 |
| `B50EABC1` | 9,568,768 | unsealed, sitting under a directory named for a pin |
| `F663B703` | 9,568,768 | unsealed |

**Four distinct builds share that byte count, not three.** The fourth,
`F663B703AA685129`, was not in the addendum.

### My own renders

Every artifact produced for this task carries a seal and a provenance file
written at render time, and every seal matches the pin the corpus names:
12 sealed and correct, 0 otherwise, summing to the 12 artifacts rendered.

The earlier `geom` and `halo2` renders still carry no seal, deliberately. That
refusal is now doubly vindicated: a guessed hash would have been a certificate
for a build I could not identify. Since that build turns out to still exist,
those renders can be re-made and sealed honestly rather than stamped.
