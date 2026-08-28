# PRE-REGISTRATION -- band qualification of 0.30-0.35 cyc/output px

Written and committed BEFORE any statistic is computed. V-SOFTCHECK.

## The challenge

ORCH, relaying V-LINEAR: a resolution claim must be measured in a band SHOWN to
contain focus-dependent signal. V-LINEAR's `noisefloor.py` reports in-focus /
defocused band power on `--linear-srgb --demosaic` single frames as
**1.015, 1.043, 1.004, 1.138** over 0.20-0.48 cyc/px, against 2.1-3.0 for Lightroom
develops of the same frames. My entire N-invariance finding (+0.0748 dex on bee,
+0.0732 dex on 113MSDCF) is measured at **0.30-0.35 cyc/output px**, inside that
interval. If my band is noise on my data, my finding is a comparison of noise
policies and is void as a resolution claim.

## What is genuinely open, and what is not

V-LINEAR's own banner already withdraws part of this. Per-tile focus selection over
29 tiles on the same develops recovered **R = 2.419** at 0.20-0.25 where whole-frame
pairs read 1.188 -- a factor of 2.0 from tile selection alone -- and 1.387 MARGINAL
at 0.25-0.30, "failing above 0.30". So the pooling defect is already known and fixed,
and my band still failed ON THEIR DATA. I do not get to explain this away by pointing
at pooling.

What is open is the develop path. Their measurement is on `--linear-srgb --demosaic`
SINGLE FRAMES. Mine is `--srgb` with an explicit `--exposure`, on MERGED masters, and
my band is in cyc/OUTPUT px. That lane states the noise-band property is
develop-dependent and demonstrates a range of 1.004 to 3.0 across develops of the
same frames. So the number must be re-taken on my path. I predict nothing.

## Instrument

`bandqual.py`, written by me, not derived from `noisefloor.py`. Same band edges as
every number I have reported (`hcoh.E`, T=128, Hann, FFT), so the qualification is in
the SAME band as the claim rather than a near neighbour.

- Probes: 32 single frames of 113MSDCF via `STREHL_ONLY_FRAME`, step 2 over 63,
  rendered `--srgb --exposure 2.33` -- byte-for-byte the develop path and the gain of
  the N032/N063 arms. Matched gauge; `--auto-exposure` forbidden.
- Per tile: in-focus frame = argmax of a SELECTION band, defocused = argmin.
- Statistic: median over tiles of log10(P_B(best)/P_B(worst)), reported as a linear
  ratio R. Bootstrap CI, 2000 resamples.
- Reported for all 7 bands, not just mine.

## The trap this instrument can fall into, and the control for it

**Selecting the in-focus frame by the SAME band being measured is an order statistic**
-- max over 32 draws of a noise field exceeds min over 32 draws, so a pure noise band
would read R >> 1 and PASS. This is trap 3 from my original brief and it is the defect
that would make me falsely qualify my own headline. Controls, all pre-registered:

1. **Selection band is disjoint from the measured band.** Focus is chosen on
   0.10-0.20; the claim lives at 0.30-0.35. Repeated with 0.05-0.10 as a robustness
   check. If R moves materially with the selection band, selection is driving it.
2. **FLAT-TILE NULL (empirical).** Bottom-two-decile-contrast tiles carry no scene
   detail, so selection there is selection on noise. R_flat must read ~1. This null is
   built from real probes and therefore includes per-frame gain jitter, ISO and dust,
   which a synthetic null would miss.
3. **NOISE-STACK NULL (synthetic).** Pure noise frames, identical pipeline. Must
   return ~1. Proves the instrument CAN return 1 and is not a short-circuit.
4. **BAND-INVARIANT NULL.** Frames whose 0.30-0.35 content is IDENTICAL by
   construction while the selection band varies strongly. True R = 1 exactly. Any
   excess is pure selection inflation, measured rather than assumed.
5. **KNOWN-RATIO POSITIVE CONTROL.** A blur ladder whose true band ratio is computed
   directly without selection. The instrument must recover the known value, so it is
   commissioned for MAGNITUDE and not merely for direction.
6. **SIGNED CONTROL.** A stack where the selection-sharp frame is deliberately the
   band-soft one must return R < 1. A statistic bounded below by 1 would pass every
   qualification ever put to it.

Any control that returns a suspiciously round number will be checked for a
short-circuit before it is believed. This project has now seen that failure twice.

## Decision rule -- fixed now

Primary quantity: **R_top**, median over the top-two-decile-contrast tiles, band
0.30-0.35, selection band 0.10-0.20. Those are the exact tiles the +0.0732 dex
113MSDCF number was measured on.

| outcome | condition | consequence |
|---|---|---|
| **PASS** | R_top >= 2.0 and bootstrap low > 1.5 and R_flat < 1.3 | band carries signal; finding STANDS and is now qualified |
| **FAIL** | R_top < 1.2 or CI includes 1.0 | band is noise; finding VOID as a resolution claim |
| **MARGINAL** | anything between | reported as marginal; finding not quotable as resolution |

**What kills my finding:** R_top < 1.2, or a CI spanning 1.0, or R_flat >= 1.3 (which
would mean my own instrument inflates and the measurement proves nothing either way).

**If it fails I will not simply move the band and re-measure.** I will report the full
7-band ladder, name the lowest-frequency band that qualifies, re-derive the depth
deficit there, and state plainly that +0.0748 / +0.0732 dex are withdrawn and why.

**A failure of control 2, 3 or 4 is a refusal, not a result.** If my own null inflates
by more than the margin between R_top and 1.2, I report UNVERIFIABLE and withdraw
nothing and claim nothing.

## Develop path, stated explicitly as required

`strehl.exe stack <dir> --out <x>.tiff --srgb --exposure 2.33`, pin binary
`44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490`, all `STREHL_*`
cleared except `STREHL_CACHE_DIR`. **No `--auto-exposure`. No `--linear-srgb`. No
Lightroom anywhere in the chain, at any stage, for any arm.** Luma via
`softcheck.load_luma(path,"srgb")`.
