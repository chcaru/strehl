# V-SOFTCHECK: is the merge deficit a tuning deficit or a Nyquist deficit?

Status: Measured. Pin `9b05d0b7`, binary sha256 `44C2F2CD2E5B2894...`, the same
binary named by every `SHIP-V4.tiff.ok`. Every number below is from that pin.

## Verdict

**It is a tuning deficit. The Nyquist wall is real, but it was already removed
before the deficit was measured, and removing it recovered less than a third of
the gap.**

`BUILD-SHARP.md:4665-4669` is **stale**. It describes a merge that gathers on
four phase planes at half the output dimensions, band-limiting everything to
0.25 cycles per output pixel. That path exists, but it is no longer the default:
`align_cmd.rs:938-1010` documents `STREHL_FULLRES_GATHER`, states the same
mechanism verbatim, and then records "It shipped off while the trade was
unpriced. **It is now on.**" `byte-freezes.tsv` dates the flip to `4c99cc40`,
2026-08-26. My own A/B confirms it on the shipping pin: the master I measured is
**byte-identical to the full-resolution-gather arm**.

So the deficit is measured *after* the wall came down, and it survives.

## Pricing the wall

Same pin, same bracket, same registration, gather as the only variable. Both
arms re-rendered end to end -- master **and** all 33 single-frame references,
because the single-frame path also runs `warp_frame_in_place` and is not
invariant under the flag. Charged against each arm's own band-limited null.

| band (cyc/output px) | plane gather (the wall) | full-res gather (shipped) | recovered |
|---|---:|---:|---:|
| 0.05-0.10 | 0.8795 | 0.8845 | 1.006x |
| 0.10-0.15 | 0.8378 | 0.8644 | 1.032x |
| 0.15-0.20 | 0.7643 | 0.8239 | 1.078x |
| **0.20-0.25** | **0.6894** | **0.7540** | **1.094x** |
| 0.25-0.30 | 0.6431 | 0.6648 | 1.034x |
| 0.30-0.35 | 0.5947 | 0.6435 | 1.082x |
| 0.35-0.40 | 0.5578 | 0.6454 | 1.157x |
| 0.40-0.45 | 0.5465 | 0.6605 | 1.208x |
| 0.45-0.50 | 0.5505 | 0.7368 | 1.338x |

The wall's signature is unmistakable and it is exactly where the doc says it is:
the recovery is negligible below 0.15 and climbs monotonically above 0.25,
reaching 1.338x at 0.45-0.50. Removing it was worth **9.4%** in the headline
0.20-0.25 band.

**And 0.7540 is still a 25% deficit.** The wall was roughly a third of the
0.20-0.25 gap. Two thirds of it is not Nyquist and is still there.

The measured recovery understates the wall's absolute cost, because in the plane
arm the single-frame reference pays the wall too, so it partly cancels in the
ratio. That cancellation is also why the pre-registered cliff test could not
decide -- see below.

## Shape: smooth, not a cliff

Pre-registered in `experiments/V-SOFTCHECK/PREREG-nyquist.md`, committed at
`c15422e5` **before** measuring. Discriminator: `W/D_drop > 0.40` = cliff,
`< 0.20` = smooth.

Measured: 119MSDCF **0.363 (ambiguous)**, 109MSDCF **0.084 (smooth)**. No cliff
at 0.25.

**The registered test was structurally incapable of finding one.** Above 0.25
cyc/output px both the master *and* the single-frame reference are interpolated
from half-resolution planes, so any wall attenuates numerator and denominator
alike and cancels in the ratio. I discovered this only after running it. The
result is reported as it came out; the intervention A/B above is what actually
settled the question.

Pre-committed ceiling, stated in advance and unchanged: the shipping test
`lanczos3_is_not_meaningfully_sharper` bounds Lanczos-3 against Catmull-Rom
below 1.15x amplitude everywhere up to plane Nyquist, so **no kernel change can
buy more than ~1.32x in power.** `gather_mtf` was re-derived independently in
Python from the kernel definition and validated against all four pinned values
(0.94024 / 0.82113 / 0.74255 / 0.62506).

## Signal above 0.25 cyc/px

The master is not empty above 0.25 -- but it is systematically short of a single
frame there, reading 0.64-0.74 of the per-site best frame. Critically, in the
shipped full-res arm that deficit **stops deepening and turns back up**
(0.6435 at 0.30-0.35 to 0.7368 at 0.45-0.50), whereas in the walled arm it falls
monotonically (0.5947 to 0.5505). A wall produces monotone collapse. The shipped
path does not show one.

## The N hypothesis: killed as an explanation, replaced by a worse finding

113MSDCF, two arms at **matched focus range** and different N: all 63 frames, vs
every 2nd frame (32 frames, first `DSC00001` and last `DSC00063` both preserved
-- density subsampled, range not). Single-frame renders were verified
byte-identical across the two source directories at matched exposure, so the
reference is literally the same files.

Both masters divided by the **same** denominator, the per-site max over all 63
frames, so the denominator is identical between arms and every difference is the
merge. This is conservative: arm B is charged against sharp frames its merge was
never given.

| band | merge of 63 | merge of 32 | difference |
|---|---:|---:|---:|
| 0.05-0.10 | 1.0997 | 1.0730 | -0.0267 ns |
| 0.10-0.15 | 1.1936 | 1.1295 | -0.0641 ns |
| 0.15-0.20 | 1.1345 | 1.0846 | -0.0499 ns |
| 0.20-0.25 | 0.9426 | 0.9547 | +0.0121 ns |
| 0.25-0.30 | 0.7314 | **0.8107** | **+0.0793 sig** |
| 0.30-0.35 | 0.6063 | **0.7203** | **+0.1140 sig** |
| 0.35-0.40 | 0.5942 | **0.7022** | **+0.1080 sig** |

**Killed:** the >1 low-band readings are not an N artifact. Halving N moves
0.10-0.15 from 1.1936 to 1.1295 -- still far above 1. There is a genuine but
small N effect in the numerator, worth about a third of the excess; it cannot
account for it. Whatever makes deep stacks read sharp below 0.20 is unidentified
and remains open.

**Found instead, and it matters more:** above 0.25 cyc/px **the merge gets
softer the more frames it is given.** Folding 63 frames instead of 32, over the
same focus range, against a literally identical reference, costs 0.114 at
0.30-0.35 -- a 16% relative loss. Fewer and less optimal input frames produced a
*sharper* master. A Nyquist wall is N-independent by construction, so this
cannot be one. It is a merge defect that scales with bracket depth, and it is
addressable.

## A number I checked before reporting

The diagnostic column `max63/max32` read **exactly 1.0000** at all seven bands.
That is the predicted reading, not a bug: 32 of 63 argmax positions survive in
the even subset, so P(a site's max is retained) = 0.508 > 0.5, and just over half
of all sites tie exactly, pinning the median to 1.0. Simulation with no image
data reproduces it (median 1.0000, fraction exactly 1.0 = 0.507, mean 1.124).
The order statistic is real but lives in the upper half of the distribution.
`experiments/V-SOFTCHECK/medmask.py`.

## Disposition of `flower-bud-alone-cpl`

**Stays REFUSED.** The band limit does not explain it, because the band limit was
not in effect for the renders in question. It is the deepest stack in the corpus
at N=205, and the N-scaling defect above is now a *named candidate* mechanism
consistent with its behaviour -- but naming a candidate is not measuring one, and
it was not measured here. It remains refused, not explained.

## A trap I fell into myself

Arm A of the N test had been rendered at `--exposure +2.33` and my first arm B
render used `+0.85`. Exposure is one multiply in linear light and the statistic
is linear in gain, so that comparison was worthless. It surfaced as "single-frame
renders are not directory-independent"; at matched exposure they are
byte-identical (`1AD1F0D9CC2A02A6`). This is trap 1, the mismatched gauge,
reproducing itself in the hands of the lane sent to check for it.

## Partition

Attempted 2 = measured 2 (119MSDCF wall pricing, 113MSDCF N test) + refused 0 +
failed 0. `flower-bud-alone-cpl` carries its prior REFUSED disposition from the
softness measurement and was not re-attempted here.

## What this retires and what it opens

Retired: "fix the gather / change the kernel / raise the plane resolution" as a
route to the 0.20-0.25 deficit. The gather fix already shipped, it bought 9.4%,
and any kernel change is bounded at 1.32x in power by a test in the tree.

Opened: the merge's fold loses high-frequency content in proportion to how many
frames it folds. That is where the remaining 25% lives, and unlike the wall it
is a tuning surface.
