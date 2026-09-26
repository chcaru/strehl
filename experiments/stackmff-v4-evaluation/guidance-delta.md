# Learned guidance: possible API, weak architectural delta

2026-09-25. **ARGUED: do not implement another guided-fusion arm now.** The
learned evidence is new; the obvious native consumer is an already-rejected
source-prior operator. This is not proof that learned guidance cannot work.
No model/RAW execution or source edit was performed for this assessment.

Mechanical searches executed with `prior_art.py StackMFF learned source prior`
and the narrower `prior_art.py StackMFF`. The latter identifies
[`B-algorithms-sota.md`](../../docs/research/B-algorithms-sota.md), especially
sections3.5–3.6: learned deterministic selection versus diffusion was already
known, as was the need to average common information instead of selecting one
noise realization. [`M70`](../../docs/research/M70-through-focus-spectrum.md)
sections0.1–0.3 and18 found useful off-peak mid-band information; the corrected
matched-filter comparison is2.38%, not its superseded0.23%. Those older corpus
measurements do not quantify this marigold, but reject the premise that one
focus label contains every useful contribution.

**Exact available seam.** Pinned V4 evaluates finite logits `[1,N,H,W]` at
`focus_map_creation` before softmax/argmax. Capture there under `eval()`; do not
switch to training mode to obtain logits because that changes normalization.
It supplies one source distribution per native pixel, not separate frequency-
band responses or calibrated radiance/noise probabilities. At the native Rust
consumer, `rb-own-guide::canonical_fields` yields existing per-band weights,
and `add_fields` can consume altered weights with the actual gathered four CFA
planes, existing coefficients, injected variance/beta, mean base and input
hull. Thus the mechanics are straightforward, but preserving those objects
does not prove preservation of their information in the reconstructed image.

**What changes, and what does not.** Hard membership shared across all AC
repeats the source-ownership assumption in
[`shared-source-field`](../shared-source-field/charter.md), whose generated
controls lost detail and whose complete chip observation produced colour islands
([result](../chip-shared-source-observation/results.md)). A soft learned
distribution q, averaged onto CFA quads and reduced with the existing pyramid,
would naturally give `w'[i,k]=w[i,k]*G^k(q[i])`. This is the same multiplication
used by [`cross-scale-source-prior`](../cross-scale-source-prior/design.md),
with learned RGB evidence replacing normalized finest-band evidence. Keeping
band0 unchanged does not protect far/coarse structure: that prior reduced the
separately measured far component from roughly0.77 to0.22. Its complete chip
had limited contact benefit, while the unchanged complete488 marigold and ore
transfer had no useful repair
([generated](../cross-scale-source-prior/results.md),
[photographs](../full-stack-source-prior/photographic-review-september25.md)).
The independent same-band harmonic alternative also gave no useful complete
chip gain ([result](../band-source-agreement/results.md)).

V4's learned spatial context and joint stack attention are a genuinely different
evidence generator; no prior result measures that generator inside the RAW
consumer. Nevertheless, a near-zero learned probability can still veto real
coarse information from another depth. The pilot's independently observed
switching islands establish a direct-output failure, not evidence that its
unexported probabilities will fix this. Its N3 maps also have no entries for
the other485 sources. Inferring their membership or temporal neighbourhood from
three labels would be a new, unsupported algorithm. Do not smooth, threshold,
retune or relabel the direct-output failure as success.

**Cheapest meaningful falsifier if root later reopens this evidence substitution:**
reuse the existing five-source flat, near-fine/far-coarse and glint fixtures at
ISO100 with actual BandWorker gathering and injected noise. Develop each source
identically, replicate-pad its native290x250 image to384 without resampling for
the frozen network, then unpad its softmax distribution and apply exactly the
coarse-only formula above. No temperature, strength, threshold or kernel sweep.
Compare actual final CFA/MHC images, using existing5% error/98% component guards;
keep flat first, both uncapped depth components and the existing wrong-depth
destroyer. Off/uniform guidance must use a literal canonical branch, with
observer identity.
This small test can reject starvation/noise damage before a photograph; passing
would establish only this new evidence-generator delta, not calibrate Sony noise
or validate learned confidence. Given the current visible seams and the repeated
consumer-family failures, this is a conditional falsifier, not the recommended
next implementation or a full-stack route.
