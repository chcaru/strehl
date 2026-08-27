
## 32. The other half of §30 -- a five-minute Lightroom export, and without it the razor blade will not settle anything either

### Why you are being asked, and why this is not §30 again

§30 asks for a slanted edge because three instruments died on edge width. That
request stands and its analysis is correct. A fourth instrument has now died,
and it died of something §30 does not mention.

The fourth instrument was built specifically to be capable of failing: a
cross-spectrum between two disjoint half-stacks, so that added noise contributes
**zero** to it, commissioned against a real nearest-neighbour gather run through
the actual pipeline, a 0.5x downscale, a known deconvolution improvement, and
flat-versus-detail regions. It did not go blind and it did not go perverse.
It ran, and then this happened:

> A tone curve fitted from **4x4 block averages of strehl's own output** -- a fit
> that has no access to any spatial frequency above 0.125 cyc/px, and therefore
> contains **no information about resolution at all** -- reproduces Zerene's band
> power at 0.25-0.30 cyc/px from strehl's pixels to within **0.02%**
> (0.037147 against 0.037138).

It accounts for **100%** of the apparent gap at 0.25-0.30, **89%** at 0.20-0.25,
and **212%** at 0.30-0.40. And a bare **gamma of 1.25** -- the mildest monotone
curve that exists, which changes no resolution whatsoever -- moves the same
statistic by **+8.5%**.

**So the fine-scale gap that this project has spent weeks trying to measure is a
measurement of Lightroom's contrast slider.** The comparators were fed
Lightroom-developed TIFFs (`Contrast2012=+100` on 113MSDCF) while strehl reads
RAW. That has always been in the README as a caveat sitting beside the result.
It is not a caveat. It is bigger than the result.

**And it does not go away when the razor blade arrives.** A tone curve reshapes
an edge profile, so it moves MTF50 directly. Shooting a perfect knife edge and
then developing one side of the comparison with a contrast curve reproduces the
same defect in a new instrument. **§30 and this are both required. Neither alone
is sufficient.**

### What to do -- no camera, no re-shoot, about five minutes

Re-export the **same developed TIFFs** that Zerene Stacker and the `focus-stack`
fork were fed, from the same Lightroom catalogue, with the development turned
off:

- **Contrast: 0** (this is the one that did the damage)
- **Tone Curve: Linear** -- and check the point curve is actually linear, not
  "Medium Contrast", which is Lightroom's default on some import presets
- **Sharpening: 0** (Amount, Radius, Detail, Masking)
- **Texture: 0, Clarity: 0, Dehaze: 0**
- **Highlights / Shadows / Whites / Blacks: 0**
- **Noise Reduction: 0** (Luminance *and* Colour)
- **Lens Corrections: off**, including the profile and Chromatic Aberration
- **Profile: Adobe Standard or Camera Neutral**, whichever is closer to flat --
  not Adobe Colour, which carries a curve
- Export **16-bit TIFF, ProPhoto or Adobe RGB, no output sharpening, no resize**

Then re-run **both** comparators on those files and drop the outputs anywhere
convenient. If the exports go in a folder next to the existing ones with
`-linear` in the name, nothing else has to be said.

If it is easier: the two subjects that matter are **113MSDCF** and
**coffee-bean**. Everything else can wait.

### While you are in there -- one thing that would help the fork specifically

The fork comparison has a second, unrelated problem, and it is not a quality
problem: **41 of 64 candidate regions could not be registered between strehl's
output and the fork's.** After the best global similarity fit (scale 1.0340,
confirmed as a genuine interior maximum) there is **5.3 px rms** of local
disagreement left over. The two programs align frames with different models, so
co-located crops are not looking at the same part of the scene, and no statistic
computed from them means anything.

Nothing needs shooting for this either. If the fork can be pointed at a **short,
flat subject** -- the same slanted-edge bracket from §30 would do -- the local
warp has nothing to disagree about and the two outputs become directly
comparable.

### What it unblocks

- **The only remaining blocker on a defensible "better than X" claim.** The noise
  win (4.5x) and the clipping win (32% of the frame against 4e-6) are already
  measured and do not depend on any of this. Fine-scale resolution is the last
  open question and this is one of the two things standing in front of it.
- **A re-test of a result that has just moved a long way.** Commit `740e7056`
  raised strehl's *coherent* fine-scale structure by **2.10x at 0.20-0.25**,
  **3.58x at 0.25-0.30** and **3.46x at 0.30-0.40** cyc/output px on 113MSDCF,
  measured on a statistic that noise provably cannot inflate. Every published
  head-to-head number predates that change. Nobody knows where strehl now sits
  relative to Zerene, and this export is what would tell us.
- **Every future comparison, permanently.** This is a one-time export preset. Once
  the comparator inputs are linear, no measurement in this project has to carry
  the "but one side was developed" asterisk again.

### Related

- §30 (slanted edge) -- still needed, for the orthogonal reason given there.
  Shoot it; just do not expect it to decide anything on its own.
- `docs/research/V-HEADTOHEAD2.md` §4.5 has the full derivation, including the
  sensitivity ladder that puts a number on how mild a curve has to be before it
  stops mattering. The answer is: milder than gamma 1.10.
