# strehl

**Noise-aware RAW focus stacking for macro photography.**

Every shipping focus stacker is a *selector*. It decides, per pixel or per
frequency band, which frame is sharpest, and copies it. That one decision is the
root cause of the field's entire catalogue of known defects — halos, the
"stacking sparkle" of amplified noise, index-map speckle, and output that in
flat regions is measurably **worse than not stacking at all**.

`strehl` treats stacking as **estimation** instead. It works in the sensor's
native colour-filter-array domain, carries a calibrated per-channel noise model
through every stage, selects only where the difference between frames genuinely
exceeds the noise floor, averages everywhere else, and tells you per pixel how
much it trusts its own answer.

The name is the Strehl ratio: how close a real optical system comes to the
diffraction-limited ideal.

> **Status: the estimation merge is the default path and runs end to end.**
> `strehl stack` implements the thesis on real RAW files: a 17x17-regularised
> winner field in pass one, a noise-gated average in pass two, with `n_eff`,
> boundary flags and per-pixel confidence as outputs. The naive per-pixel argmax
> now lives at `strehl argmax-baseline`, kept deliberately as the reference
> artifact every quality claim is measured against.
>
> **Measured end to end on the reference rig:** 299 frames of 33 MP Sony ARW to
> a 7032 x 4688 16-bit sRGB TIFF in **51.6 s** — decode, align, focus, elect,
> merge, demosaic and write (Ryzen 9 9950X3D, warm cache, best of 3). That
> figure was **23.1 s** before alignment was wired into the merge; registration
> is what the extra ~28 s buys. Full sensor resolution is **free**: the binned
> render measures 51.4 s, inside the run-to-run spread of the full one.
>
> **Measured and refused, not pending.** Two items previously listed here as
> "not yet built" have since been built, measured against the merge that already
> ships, and declined:
>
> - **Multi-frame deconvolution.** `R_SNR = 1.0014`, CI **[0.965, 1.038]** — the
>   interval excludes a useful effect rather than merely failing to find one.
>   The apparent sharpening was **2.51x** contrast bought with **2.03x** noise,
>   and **29.5-36.4%** of output pixels fell outside the convex hull of their own
>   sources (invented values) against **exactly 0.0000%** for every convex arm.
>   The proposed safety guard — self-calibrating the OTF from the through-focus
>   curve — is separately **refuted**. See
>   [`M115`](docs/research/M115-deconv-headroom.md).
> - **Outlier rejection.** Built or specified and refused **four independent
>   times**. Most recently it fired on **29.55%** of a *stationary* subject and
>   **4.3x less** on the moving one. See
>   [`M123`](docs/research/M123-robustness-mask.md).
>
> **Still open, and correctly attributed:** occlusion modelling — a bright veil
> along the subject silhouette, present at `--gate 0`, surviving alignment, with
> **no established mechanism** (the three obvious explanations are each measured
> and each refuted, `crates/strehl-cli/src/merge_cmd/halo.rs`).
>
> **The polygonal patchwork is closed, and the cause was the backend.** It was
> first *proved* rather than observed: in a ROI where all 299 input frames are
> featureless, the estimator's render carries **3.4x more fine structure than any
> spatially constant convex weighting can produce**, so the cause is the *spatial
> variation* of the merge weights ([`M120`](docs/research/M120-patchwork.md)).
> It has since been seen directly and localised to one component. On the same
> pinned binary, the same 299-frame subject and the same 1:1 crop — the crop site
> chosen independently in each arm by a stated gradient rule, and landing on the
> same coordinates in both — the **estimator** backend draws hard-edged grey
> polygons across the defocused background and smears hair detail, and the
> **pyramid** backend draws neither, at gate 4.5 *and* at its own default gate of
> 2.0, while also resolving hairs and pollen more crisply. So the patchwork is a
> property of the per-pixel winner field rather than of the noise gate, and the
> fix is the backend rather than a tuning parameter. **`--merge pyramid` is now
> the compiled-in default**, so this needs nothing from you; the gate does — see
> the quickstart.
>
> **The honest consequence:** there is currently **no measured route to resolving
> detail beyond the sharpest captured frame.** The claim this project defends is
> narrower and testable — that estimating from all frames under a calibrated
> noise model degrades what was captured less than selection does.
> The research corpus is in [`docs/research/`](docs/research/), and
> [`SYNTHESIS.md`](docs/research/SYNTHESIS.md) is the decision record.

### Lateral chromatic aberration correction — on by default, certified corpus-wide

The one defect visible at 1:1 on otherwise clean renders was lateral CA: red/cyan
fringing along high-contrast edges, worst toward the frame corners, which is what
a radial per-channel scale error looks like. Correction is now **on by default**.

It was measured on **all 26 subjects** in the corpus, both arms rendered by the
same pinned binary with the correction as the only difference, and scored as the
ratio of edge chroma spread after to before — so **lower is better and 1.0 is no
change**. The crop and the edge set were chosen on the **mean of the two arms**,
so neither arm picked its own ground.

```
compared 26, skipped 0, total 26
edge R-G: improved 25, worsened 0, unchanged 1   (sums to 26)
median edge R-G 0.6533   R-B 0.7480   B-G 0.9452
```

**Zero subjects worsened.** The single unchanged row is
`highly-angled-ruler-mm-cpl`, which reads exactly `1.0000` on all three channels
— a subject where the correction is a measured no-op, and a better built-in
control than anything that would have been designed on purpose.

The flat-region placebo on this test does **not** read 1.0, and that is reported
rather than buried: correcting CA resamples R and B, interpolation low-passes
noise, and in a region that is pure noise a spread ratio reads that as
improvement. The effect is confirmed in closed form against the interpolation
kernel's own taps, it explains the observed channel ordering, and deconfounding
for it moves the median by **-0.0273** — the noise floor was *diluting* the
measured win, not inflating it. See §46 of
[`ORCH-veiling.md`](docs/research/ORCH-veiling.md).


## Quickstart

```console
$ cargo build --release -p strehl-cli

# Look at what the decoder found before stacking anything.
$ strehl probe <DIR>

# Stack, and render something you can actually look at.
$ strehl stack <DIR> --merge pyramid --pyramid-gate 4.5 --srgb --auto-exposure -o out.tif
```

**`--merge pyramid` is now the compiled-in default.** The flag in the line above
is redundant and is written out only so the command reads the same whichever
build you have. It is the backend the measurement above singles out: same binary,
same subject, same crop, polygons in the old default arm and none in this one.
Verified on this build — a bare `strehl stack <DIR> --srgb --auto-exposure`
reports `LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)`.

**`--pyramid-gate 4.5` is NOT redundant, and you should keep it.** The compiled
default is still `2.0`. Those two values do not produce the same picture: run at
`4.5` and at the default on the same subject with the same binary and the outputs
differ (`C085A056…` against `6980D447…`, same 197,798,531 bytes). Every reference
render in the gallery, and every quality claim made about them, was produced at
`4.5`. Drop the flag and you get a render nobody has certified.

The patchwork is absent at *both* values, so this is not a defect workaround — a
higher gate averages more frames per band, which lowers noise. The corpus-wide
sweep that would justify moving the compiled default is open, and until it lands
this line is the honest one: **what ships by default is not what was measured**,
and the flag is how you get the measured thing.

### What the default backend does not do

The pyramid merge is the merge and nothing else. It prints this itself on every
run, and it is worth reading rather than scrolling past:

```
not applied     : photometric gain, clip census, outlier rejection, halo correction,
                  through-focus statistics. Those are the --merge estimator path's
                  stages; this arm is the merge only.
```

Two of those matter on real captures, and you will meet them by accident rather
than on purpose:

- **No outlier rejection.** If something in your scene *moved* between frames — an
  antenna, a leg, a bubble, a leaf in a draught — nothing defends the merge
  against it. You get the ghost.
- **No photometric normalisation.** If exposure drifted across the bracket, the
  gate reads the drift as signal rather than as gain.

These are refused rather than ignored, which is the behaviour you want:

```
$ strehl stack <DIR> --photometric on
Error: --photometric belongs to the estimator merge, and --merge selected pyramid.
  what to do  : NOT YET IMPLEMENTED on this backend, rather than inapplicable. [...]
  or          : pass --merge estimator to use --photometric as it stands.
Refused rather than ignored because a flag that silently does nothing looks
exactly like one that works.
```

The obstacle is the pass structure, not the backend: fitting a per-frame gain
needs every frame's flux *before* the first frame is folded, and the pyramid
folds in a single pass. The gain itself would apply unchanged. This is a known
gap with a known fix, not a design position.

**In practice, on this corpus:** all 26 reference renders were produced on this
path and none of them needed those stages. If your subject held still and your
exposure held steady, neither will yours.

**Do not take the estimator backend as a working fallback.** A reachability
audit of the whole binary found that `--merge estimator` fails out of the box:
it exits non-zero with `U3 the eroded low-detail region keeps only 0 px` unless
`STREHL_PHOTOMETRIC=off` is set in the environment. The advice to fall back to
it was wrong and is withdrawn until that is fixed. The same audit found that
four of the five stages the banner lists as "not applied" are fully written and
reachable only from that broken path — so the capability exists, has never run
on a delivered image, and the shipping default is the less capable of the two
backends. Porting what is worth porting into the pyramid is in progress.

**There is no hot-pixel or defect-pixel correction anywhere in either crate.**
Not disabled, not stubbed — absent. Every apparent reference in the source is
prose. On long exposures at high ISO you will keep your sensor's hot pixels, and
because they are fixed in sensor coordinates while the frames are warped into
alignment, they smear into short trails rather than staying points. Dark frames
sufficient to identify them have been captured; the correction has not been
built.

`--srgb` applies the camera's colour matrix and the sRGB transfer curve, and
since M95 it emits at **full sensor resolution by default** — pass `--binned`
for the old half-resolution render. **None of this is on by default**, because
the default output is the binned linear camera-native file that every number in
the corpus was measured on.

`--srgb` alone is *faithful*, not *flattering*: it reproduces the capture, and
these captures run 1.1–3.2 stops under. `--auto-exposure` picks a gain by
putting the 99.9th percentile of linear-sRGB luminance at 0.90 and **prints the
`--exposure=N` that reproduces the file byte for byte**; `--exposure <STOPS>`
sets it yourself. Both are one multiply in linear light before the transfer
curve — no tone curve, no saturation, no roll-off — and both refuse to run
without `--srgb`, because the linear output is the measurement output. Use the
flags to look, drop them to measure.

### What the output actually looks like

Four things are worth stating plainly: two are defects this class of tool is
notorious for, one is the positive result, and the last is what is actually
still open.

**The halo is gone on this path, and that is measured rather than asserted.**
The classic focus-stacking artifact is a bright or dark band tracing every
silhouette, left behind where the merge picked a defocused frame's veiling glow
over the background it should have kept. Profiled by signed distance from the
silhouette on `flower-bud`, both arms rendered camera-linear from a single
binary so nothing is compared across a tone curve: the older estimator backend
shows an interior peak of **+12.65% at 21 px**, and the pyramid backend that
ships by default is **monotonic from 1 px to 275 px with no interior maximum at
all**. It also survives the harder test, which is looking at it: at 1:1 across a
dark hairy stem against a blown-white backdrop, the backdrop stays clean to the
edge and the individual hairs resolve against it.

**Highlights are not clipped by the merge.** A pyramid merge can leave the
output above or below the range of every input that fed it, which shows up as
punched-out white or crushed black along high-contrast edges. The delivered
renders carry **zero** exact-zero RGB pixels on subjects where an unclamped
merge produces 0.371% and 1.048%. Dark is subject, not clipping.

**On a good capture the result is print-worthy, and that judgement was made by
looking at pixels rather than at a metric.** Three subjects were pulled to true
1:1 out of the delivered masters, through a single display curve derived once
per master so no two crops are graded differently: `bee-3-cpl` resolves
individual plumose hair barbules, including the branched side-structure that
makes bee hair feathery rather than smooth; `leaf-2-cpl` resolves vein structure
at three scales plus cell-level texture and chloroplast speckle; `112MSDCF`
resolves crystal dendrites down to near single-pixel branch width. None of the
three shows a halo. `leaf-2-cpl` is the searching case of that set, because long
straight high-contrast veins are the geometry a Laplacian pyramid rings against
most readily.

**What is still open is sharpness, and it is uneven.** The tool is not uniformly
soft — it is *inconsistent*, which is worse, because a contact sheet that mixes
both gives you no way to tell which is which. Resolved-detail score at each
subject's own sharpest site spans an order of magnitude across the corpus, from
`flat-on-ruler-cpl` at **0.0503** down to `flowers-cpl` at **0.0045**, which
reads as mush at the same magnification the top of that range reads as a print.
Some of that spread is capture — depth coverage, aperture, subject motion — and
some of it is the merge. Telling those two apart per subject is in progress, and
until it is settled the honest summary is that this tool will hand you a
print-worthy file on some stacks and a soft one on others, and does not yet tell
you which you are holding. Making it tell you is the point of the confidence
map, and it is the difference between a defect report and an instrument.

## What is actually different

| | Every shipping stacker | `strehl` |
| --- | --- | --- |
| Core operation | select the sharpest frame | estimate from all frames, gated by measured noise |
| Colour domain | demosaic first, then stack | **CFA-native**; the merge emits RGB directly |
| Noise | not modelled | calibrated `sigma^2(S, ISO)` injected into every stage |
| Output | an image | an image **plus a per-pixel confidence map** |
| Capture geometry | one hardcoded assumption | fitted per stack, not baked from one rig |

No existing tool is RAW-native. Zerene states plainly that "no stacking software
really works directly with raw files"; Helicon's RAW workflow demosaics via
Adobe DNG Converter before it aligns anything.

v1 targets **in-camera focus bracketing**. Focus-rail capture is a designed-for
seam but is deferred until there is hardware to test it against.

## The honest performance claim

Not "N times less noise". The gain depends entirely on how many frames actually
see a given point in focus. Measured on the 22-frame reference bracket, over a
low-detail region, against a single unstacked frame:

| gate | mean `n_eff` | flat-ROI noise | |
| --- | --- | --- | --- |
| 0.0 | 1.000 | **1.074x** | selection — *worse than not stacking* |
| 0.5 | 1.414 | 1.027x | still worse |
| 1.0 | 1.884 | **0.973x** | first gate that beats one frame |
| 2.0 | 2.891 | 0.890x | |
| 4.0 | 4.987 | 0.788x | |
| — | — | 1.253x | the argmax `strehl argmax-baseline` ships |
| — | *N* | 0.534x | a plain mean — the floor, and it destroys 58% of detail |

Read the first row carefully, because it is the whole argument. **At `n_eff` = 1
the merge is doing exactly what every other stacker does — selecting — and it is
measurably 7.4% noisier than the single frame it selected from.** Selection is
not free. That is why the gate exists, and it is why gate 0 is a diagnostic
rather than a shipping configuration.

It is also a correction. This README previously claimed *"never worse than a
single frame anywhere — Wiener shrinkage cannot amplify"*. That is false, the
project's own guard test asserted it for four days, and the test passed only
because the noise model was blind in precisely the place the invariant could be
violated. Both were fixed; see facts 428-431 in
[`SYNTHESIS.md`](docs/research/SYNTHESIS.md).

The honest claim is narrower: **averaging two or more frames is strictly better
than one, and the gate is what decides when that is safe.**

**On a whole photograph, measured.** `leaf-2-cpl`, 182 frames, both arms at a
fixed `--exposure=3.19` so the merge is the only difference between them.
`--gate 0` reports mean `n_eff` 1.000 with 100.00% of pixels at `n_eff` = 1 —
pure selection, every output pixel exactly one frame's pixel. `--gate 2` reports
mean `n_eff` 15.077. In a 200x200 flat patch chosen on the *mean of both arms*,
so neither arm selected the view, noise falls **0.006381 → 0.000987**, a ratio
of **0.1546x** — equivalent to averaging **41.8 frames** — and the matched
detail crop is **visually indistinguishable**. That flat-patch figure is a best
case and is quoted as one: the tool's own model predicts **0.4439x** image-wide
at this gate, because 21.95% of pixels still average nothing. Both numbers are
right; they describe different regions.

On resolved detail the expected gain is **~1.2-1.8x** — at a sane focus step only
about 1.3 to 1.5 frames have any given depth inside their depth of field — but
that figure is `ARGUED`, not measured, and the noise column above is not a
result on its own: a plain mean wins it outright while collapsing detail, which
is why `merge` refuses to report it without a `--detail-roi`.

**Speed.** The same 22-frame 33 MP stack merges in **3.19 s** end to end
(1.15 s pass one, 2.04 s pass two) at **262 MB/s** over 836 MB of RAW, on a
Ryzen 9 9950X3D. Peak memory is bounded at 5 in-flight frames — **never O(N)** —
and decode alone is 1.78 s cold, 0.91 s warm. See
[`M1`](docs/research/M1-decode-measured.md).

## Usage

```
strehl probe <DIR> [--limit N]     # sensor geometry, levels, ISO, white balance
strehl stack <DIR> [--out <PATH>]  # THE THESIS: noise-gated estimation
                   [--merge pyramid|estimator]   # default: pyramid
                   [--gate T...] [--target-n-eff N] [--limit N]     # estimator only
                   [--pyramid-gate G] [--pyramid-bands N]           # pyramid only
                   [--srgb] [--demosaic] [--binned]
                   [--exposure <STOPS>] [--auto-exposure]
                   [--flat-roi X,Y,W,H] [--detail-roi X,Y,W,H]      # estimator only
                   [--stats] [--stats-placebo] [--confidence-tail Q] # estimator only
strehl argmax-baseline <DIR> --out <PATH>   # the naive argmax, for comparison
                   [--srgb] [--index-map <PATH>] [--flat-roi X,Y,W,H]
                   [--memory-model <MODEL>]
```

### `stack` — the estimation path

**`stack` runs the pyramid merge by default.** Everything in this section
describes the *estimator*, which is now selected with `--merge estimator`.
The flags below belong to it and are **refused, not ignored**, if you leave
them on a pyramid run — the error names the pyramid counterpart, or says
plainly that there isn't one.

```console
$ strehl stack C:\dev\macro\test\109MSDCF --merge estimator --target-n-eff 3 --out merged.tif \
      --flat-roi 2272,1344,256,256 --detail-roi <X,Y,W,H>
```

Two passes over the frames. Pass one elects a winner per pixel from a
17x17-regularised focus field; pass two averages every frame whose regularised
response the calibrated noise model **cannot separate** from that winner. Where
one frame is unambiguously sharpest it degenerates to selection; where several
are indistinguishable it averages them, which is the only operation that goes
below single-frame noise.

**Set `--target-n-eff`, not `--gate`.** A fixed gate is not a calibration: at
gate 2.0 the achieved `n_eff` spans 2.26-7.42 across five stacks, and reaching
`n_eff` = 3 needs gates from 1.1 to 2.9. `--gate` is repeatable and the whole
ladder folds in one pass two, so a sweep costs one decode budget, not one per
value — that is how the table above was produced.

`--stats` opts into the per-pixel through-focus sufficient statistics (sub-frame
peak by parabola fit, top-4 frames, a bimodality statistic) at a **5-pixel**
window rather than the 27-pixel selection window, because occlusion bimodality
is *depleted* at the selection scale. Fixed 60 B/px, constant in frame count. It
costs 494 MB per worker and **cannot change the merged image** — that is
asserted by byte-identical hash, not by argument.

### `argmax-baseline` — the baseline it has to beat

```console
$ strehl argmax-baseline C:\dev\macro\test\109MSDCF --out baseline.tif \
      --index-map baseline-index.tif --flat-roi 2272,1344,256,256
```

`argmax-baseline` streams the directory's RAW frames through a bounded rayon
fold — it
never materialises the focus volume, so peak memory is O(threads), not
O(frames) — computes a noise-normalised bandpass focus measure per CFA plane,
and takes the per-pixel argmax. It does **not** align, denoise, regularise the
winner map, or blend frames. That is the point: it is the naive baseline, and
it is what later work has to beat.

**What it writes.** `--out` is a **3516 x 2344 16-bit RGB TIFF**: one output
pixel per physical 2x2 CFA quad, with `R` = R, `G` = (G1+G2)/2, `B` = B taken
from the winning frame. It is **binned, not demosaiced** — there is no
interpolation, and therefore no demosaic artifact in the baseline. The cost is
half linear resolution. White balance is applied as a green-normalised gain; no
colour matrix is applied, so the output is camera RGB, not colorimetric sRGB.

**Default output is linear** and will look dark in a normal viewer. That is
correct: it is what measurement needs. `--srgb` applies the sRGB transfer curve
to produce something viewable — use it for looking at, never for measuring. If
`--srgb` still looks dark, that is the capture rather than the render, and
`--auto-exposure` will say so with a number: it prints the gain it chose and the
`--exposure=N` that reproduces the file exactly.

**`--index-map`** writes the winner map as a 16-bit grayscale TIFF holding the
literal frame index (0..N-1) per pixel, so it needs autoscaling to view. It is
the primary diagnostic: real depth is piecewise smooth, so coherent bands are
genuine focus structure and salt-and-pepper speckle is the argmax defect made
visible.

**`--flat-roi X,Y,W,H`** (in plane coordinates) prints the **spatial** standard
deviation of the stacked green channel over that ROI next to the same ROI in a
single unstacked frame, and their ratio. **A ratio above 1.0 means the stack is
noisier than one unstacked frame.** On the reference bracket it is 1.253x, and
~1.48x once shared scene structure is removed.
Pick a genuinely low-detail region: scene structure is common to both sigmas and
biases the ratio toward 1.0. Note that both are *spatial* sds over many pixels,
while the noise model's prediction on the line below them is a *temporal*
per-sample sigma — they are different quantities and are not expected to match.

`stack` also prints throughput, the enforced in-flight frame bound, the winner
distribution, index-map speckle, and an explicit provenance line stating whether
the noise model came from calibration or a fallback guess.

## Design

Read [`docs/research/SYNTHESIS.md`](docs/research/SYNTHESIS.md) first — it is the
decision record, including what lost and why. It has been revised once already in
response to [`docs/research/REVIEW.md`](docs/research/REVIEW.md), an adversarial
review that found and corrected four design-changing errors.

The six background reports (`A`–`F`) are the underlying research: the prior-art
corpus, the algorithmic state of the art, the competitive and licensing
landscape, the Rust and hardware envelope, the plugin architecture, and the
optical modelling of the reference rig.

Measurement milestones are recorded separately and label every claim `MEASURED`,
`VERIFIED`, `DERIVED`, `ARGUED` or `UNVERIFIED`. There are forty-odd of them;
[`AGENTS.md`](AGENTS.md) carries the index. Entry points:
[`M1`](docs/research/M1-decode-measured.md) (decode throughput and sensor
constants), [`M2`](docs/research/M2-baseline-skeleton.md) (the argmax defect
measured on real files), [`M3`](docs/research/M3-alignment-measured.md)
(alignment), [`M18`](docs/research/M18-merge-implemented.md) (the merge and its
sufficient-statistics seam), and
[`G-edof`](docs/research/G-edof-deconvolution.md) (the EDOF/microscopy survey).

**Findings that lost are kept, and marked.** Withdrawn rows stay in the table
with the reason attached rather than being deleted — fact 242 was refuted by an
independent verification of the project's own work, and fact 341 was a defect in
shipped Rust found the same way. Four independent verifications have run over
fourteen milestones; **not one defect they found was arithmetic.** Every one was
a *choice* — of estimator, reference, arm, or null. That is why verification
here is required to re-choose rather than re-compute, and why the author of a
result never verifies it.

## Contributing

Focus measures, merge strategies, alignment models, and camera/lens optical
profiles are all designed to be replaceable and contributable. The architecture
deliberately does **not** pre-build seams it has not needed yet; see
`SYNTHESIS.md` §9 for what was cut and why.

Before contributing, read [`AGENTS.md`](AGENTS.md) — in particular the
**do-not-read list**. This project is MIT/Apache-2.0 licensed and several
prominent tools in this space are GPL. Reading their source would contaminate
the project.

## Licence

MIT OR Apache-2.0, at your option.

Note that the RAW decoder (`rawler`) is LGPL-2.1. That is fine for a permissive
project, but it carries one real obligation: anyone we ship a binary to must be
able to relink it against a modified `rawler`. See `AGENTS.md`.
