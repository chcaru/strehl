# PRE-REGISTRATION -- silhouette discriminator, n=2 -> n=6

Written BEFORE any of the four new subjects was rendered or measured. The two
existing subjects are the ones that generated the hypothesis and cannot test it.

## The claim under test

Section 22.7 measured, on the sharpest reference-amplitude quintile, clip-free
tiles only, the mid-band (0.2-0.7 f/Nyq) amplitude ratio pyramid/legacy:

    flower-bud-alone-cpl   0.6719     has a silhouette
    couch-fibers-cpl       1.1081     has no silhouette

and ARGUED that the discriminator is whether the subject presents an occluding
outline against a defocused background -- BUILD-HALO's veil mechanism, in which
the election is drawn to the coherent constant-gradient ramp a defocused
foreground lays over the backdrop.

n=2 is one subject per arm. This corpus has been burned by two-subject
conclusions before. The hypothesis is cheap to falsify and is falsified here.

## Classification, fixed in advance

Assigned from what the subject IS, before any measurement:

| subject | frames | class | why |
| --- | ---: | --- | --- |
| tweezers-cpl | 100 | SILHOUETTE | metal tips against open background |
| dry-erase-marker-head-cpl | 299 | SILHOUETTE | marker tip against open background; also the known clipper, 45.19% drift / 1.29% clip |
| wrapped-text-1 | 130 | NO SILHOUETTE | printed surface filling the frame |
| flat-on-ruler-cpl | 79 | NO SILHOUETTE | a plane, by construction |

Held from section 22 as the generating pair, not counted as evidence:
flower-bud-alone-cpl (SILHOUETTE), couch-fibers-cpl (NO SILHOUETTE).

## Predictions

1. PRIMARY. The two SILHOUETTE subjects show a clip-free sharp-quintile
   mid-band ratio materially below 1.0. The two NO-SILHOUETTE subjects do not.
   Threshold fixed now: SILHOUETTE < 0.90, NO SILHOUETTE >= 0.95.

2. The four subjects separate on class with no overlap. If any NO-SILHOUETTE
   subject falls below any SILHOUETTE subject, the discriminator is refuted as
   stated.

3. SECONDARY, weaker, stated so it cannot be claimed afterwards: black-rail
   clipping is confined to SILHOUETTE subjects, because the dark pedestal that
   lets a photometric excursion cross zero is what a defocused background
   supplies. Predicted but NOT load-bearing -- section 19's cross-subject
   result already showed drift alone does not predict clipping.

## What would refute it

- Any NO-SILHOUETTE subject below 0.90 -> the deficit is not about occlusion.
- Both SILHOUETTE subjects at or above 0.95 -> flower-bud is idiosyncratic and
  section 22.7's target for BUILD-HALO is aimed at the wrong thing.
- No separation at all -> the mid-band deficit tracks something else entirely
  (frame count, subject distance, magnification) and the veil story is wrong.

## What is NOT being claimed

That the classification is objective. "Has a silhouette" was assigned by
judgement from the subject description, not measured. A cleaner future test
would derive it from the depth map's bimodality, which is what the posterior
would supply. Recorded as a known weakness of this test.

## Protocol

Identical to section 21.3 and 22: pin tree-lin-0d9fd28, both arms
camera-linear, STREHL_FIX_CA and STREHL_PHOTOMETRIC unset in both, --gate 4,
matched full resolution (7040x4688), scored by accept2.py, which refuses to
print a verdict until every arm scores exactly 1.0000 against itself.

Known caveat, carried forward honestly: both arms are Malvar-He-Cutler
demosaiced and the shipped log itself warns "Interpolated -- do not measure
resolution on it." The demosaic is common-mode across the two arms, so the
RATIO is defensible where an absolute resolution number would not be. Stated
because it is a real limitation of every number in sections 22 and this test.
