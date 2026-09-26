# Independent interpretation of the fixed marigold trace

Status: independently interpreted and observer-admitted, 2026-09-25. Root ran
the separately reviewed saved-pair verifier successfully; evidence is retained
in saved-pair-verification-1/comparison.json. The same-build observer-on/off
complete TIFF bytes and all complete merged planes are identical. Historical
decoded RGB16, ICC and encoded pixel strips also match; the only cross-build
file differences are 12 bytes inside Software tag305's build string. Both
original wrappers remain recorded as refusing literal cross-build TIFF identity;
no completion was written back to them and no RAW render was repeated. This is
an explicit metadata-only exception, not a relaxed pixel or same-build observer
gate. No treatment or photographic improvement was made by this experiment.

**Decision: the independently frozen near/far centres do not establish a stable
captured hair contrast that the merge loses. Do not run the proposed 80-168
coarse-support restriction, recenter these profiles or search another donor
from this result.** The accounting remains useful, but it has not selected a
causal quality intervention.

The complete five-point gathered-source profiles are decisive. The fixed near
centre's G1 contrast is +65, -11 and -67.5 DN at sources 108, 112 and 116. Its
prescribed source 112 has the five samples [1630,1665,1704,1792,1800] DN: a rising
profile, not a centred bright hair. The output G1 contrast is -31.420166015625
DN, but comparing it only with source 108 would manufacture a loss claim by
choosing the convenient source after the fact. The R/G2/B contrast signs and
profile shapes also differ; no colour-phase-independent stable ridge was
established.

The far centre's G1 contrast is -55.5, +7.5 and +26.5 DN at sources 148, 152 and
156. Prescribed source 152 has [1966,2152,1887,1845,1793] DN: the larger inner
sample is at offset -4 native pixels, not the frozen centre. The output's G1
profile [2096.5703125,2280.85888671875,2031.4002685546875,1951.046142578125,
1902.1868896484375] retains that displaced-profile character. A scalar centre
contrast of +32.02166748046875 DN cannot tell whether the photograph preserves
the real long hair, creates texture, changes blur or shifts correspondence.
Recentring onto the more convenient sample is expressly excluded by the plan.

These findings limit this particular sample choice, not the existence of real
near/far hairs demonstrated in the earlier complete-source images. They also
do not establish an alignment defect: defocus, visibility, distinct structures,
sampling phase and noise can change these five samples. The actual output is
still visibly unsatisfactory. An inadequate local witness is not a capture
limit or proof that the merge is correct.

The final input-range clamp contributes exactly zero at both fan profiles and
the fan-context profile. One blue rim-control profile has a nonzero clamp
contrast contribution of +10.824295043945312 DN. This proves why clamp accounting
must remain separate; it does not turn the distant rim control into a new
target or explain the fan haze. No temporal-sigma, flat-noise or sharpness
quality claim is made from these textured locations.

The offline accounting's largest f64-to-actual-pre-hull discrepancy is about
0.000475194 DN, below its declared 0.02 DN numerical bar. The producer reports
exact sampled canonical accumulator, chunk absorption and final-CFA replay.
These verify numerical attribution only. Large source weights or distant
absolute contributions are not automatically harmful: opposing AC terms can
cancel captured defocus and coexist with the deliberately averaged terminal
base. Without a stable protected spatial witness, choosing a negative term to
remove would be another ungrounded treatment.

Run by the independent reviewer:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/real-source-contributions/independent-interpret.py --attribution experiments/real-source-contributions/analysis-1/attribution.json --contributions experiments/real-source-contributions/analysis-1/source-contributions.npz --out experiments/real-source-contributions/analysis-1/independent-interpretation.json
```

The interpretation aid binds its inputs and its own source, shows every fixed
five-point profile and each natural-order signed band/bin contribution, and
does not rank sources. Its 108/112/116, 148/152/156 and 316/320/324 neighbourhoods
were frozen before actual trace values were read. Direct tabulation of those
saved profiles produced the numbers above; no RAW decode or new render was run
by this reviewer.

The program then returned to the separately observed complete-chip quality gap
versus HeliconB. The one stock ramp1.4-to1.0, exponent2 comparison is a distinct
whole-image observation, with seven preserved native regions, complete outputs
and an explicit independent-tone limitation. Its later independent review also
rejects it: smoothing did not restore useful contact separation. See
../chip-stock-selectivity/independent-photographic-review.md. This marigold trace
never proved that selectivity caused the chip gap or predicted that the stock
comparison would improve it. Neither negative result authorizes a generic plant,
source interval, donor, mask or ramp/exponent sweep.
