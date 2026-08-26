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

> **Status: the pyramid merge is the default path and runs end to end.**
> `strehl stack` produces print-worthy 16-bit masters from real RAW files —
> four subjects verified by eye at true 1:1, with the occlusion halo gone
> (see *Looking at the output* below). The naive per-pixel argmax lives at
> `strehl argmax-baseline`, kept deliberately as the reference artifact every
> quality claim is measured against.
>
> **Two corrections to what this paragraph used to say**, both material enough
> to belong here rather than in a footnote. It claimed the *estimation* merge
> was the default: it is not. The default is `--merge pyramid`; the estimator is
> selected with `--merge estimator`. This line used to say the estimator
> **"currently exits rc=1 out of the box"**; that is now false and is retracted —
> see the correction below.
> It also claimed "per-pixel confidence as outputs": the only per-pixel trust
> artifact in the tree is `--n-eff-map`, which is one of nine flags the CLI
> refuses on the default backend. The default emits an image and nothing else.
> Closing that is the top build priority; see the comparison table below.
>
> **Measured end to end on the reference rig:** 299 frames of 33 MP Sony ARW to
> a 7032 x 4688 16-bit sRGB TIFF in **51.6 s** — decode, align, focus, elect,
> merge, demosaic and write (Ryzen 9 9950X3D, warm cache, best of 3). That
> figure was **23.1 s** before alignment was wired into the merge; registration
> is what the extra ~28 s buys. Full sensor resolution is **free**: the binned
> render measures 51.4 s, inside the run-to-run spread of the full one.
>
> **Read that number with its caveat.** "Elect" is an estimator stage, so 51.6 s
> was measured on the path that is no longer the default. The **shipping
> pyramid path's end-to-end time has not been re-measured** since it became the
> default, and a speed claim about a path nobody timed is not a speed claim.
> Treat 51.6 s as evidence that the architecture is fast at 299 frames and 33 MP
> — not as the current default's number.
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


## Looking at the output

Before anything else, look at pictures. Build a self-contained gallery of every
current stack — each subject's full frame paired with a **true 1:1 crop** of its
most detailed region:

```console
$ python experiments/ORCH-drift-check/build_gallery.py
$ python experiments/ORCH-drift-check/verify_gallery.py   # checks the page, not the log
```

Then open `C:\dev\strehl-out\VIEW\index.html`.

The 1:1 crop is the point. **A reduced image cannot support a verdict about
print quality** — it hides softness and it also hides the fine structure that
separates a genuinely sharp low-contrast subject from a blurred one. Three
separate wrong conclusions in this project came from judging pictures at
thumbnail scale, including one that had already been sent to two contributors as
an instruction before it was retracted.

Judged that way, **every one of the 26 subjects has now been opened at 1:1, and
no subject anywhere in the corpus shows a merge defect.** Twenty-four are
print-worthy. Two are limited by the capture rather than by the stacker, which
is a different verdict and is recorded as one below rather than folded into a
pass rate.

> **Scope, and it is a real limitation of this survey: these masters were not
> rendered at the shipping default.** Every image in the gallery, and therefore
> every judgement in this section, was produced with `--pyramid-gate 4.5`. The
> compiled default is **2.0**. This was found *after* the survey finished, by
> two agents independently, and established by byte-identity rather than by
> inference: `SHIP-V1\bee-3-cpl.tiff` and `SHIP-V1\109MSDCF.tiff` each reproduce
> **exactly** — same SHA-256 — when re-rendered at gate 4.5 through the pinned
> binary, and do not reproduce at the default.
>
> On the one subject where both have been measured the two gates give the **same
> detail** (detail-ROI ratio 0.9945) and differ in flat regions, where the
> default carries **7.8x the gradient energy**; on noise against a single
> unstacked frame the default reads **0.915x** where 4.5 reads **0.746x**.
>
> **The gap has since been rendered and looked at, and it is not small.** Both
> gates of `109MSDCF`, same pinned binary, same source, nothing else changed:
> **97.359% of samples differ**, peak difference **21.1% of full scale**, rms
> **0.41%**. Taking the 256-px block where they disagree most (x=3056, y=3888),
> cropping that same box from both at 800x800 with no resampling, and opening it
> at 1:1: **gate 4.5 is visibly cleaner, and the shipped default is visibly
> grainier** — plain grain across flat fields, no pixel-peeping required. Within
> that crop **16.0% of samples differ by more than 0.5% of full scale**. Two
> instruments that share no code now order the two gates the same way. So the
> gallery **flatters the shipping product**, which is the direction that matters:
> it is the one that makes this survey read better than the binary a reader runs.
>
> One caution against over-reading that crop. It was selected by *total*
> disagreement, and total disagreement selects **flat** regions — so it can
> establish that the gap is material and it cannot say what the gate does to
> detail. **Cleaner is not better if it costs resolution.** Given the fine-detail
> deficit in *Measured against other stackers* below, smoothing our way out of a
> sharpness problem would register as a win on every noise metric this project
> owns, which is exactly why the noise numbers cannot decide this.
>
> **So the split was measured, with a control — and the first attempt at it was
> wrong, so read the retraction before the table.**
>
> <b>RETRACTED.</b> The first version of this measurement reported detail ratios
> of 0.9864–1.0086 across every band and concluded the higher gate cost no
> detail at all. **It was measured on the `--srgb` render**, which this tool's
> own `--help` says twice not to do: *"Do not measure either file"*, and of the
> full-resolution demosaic, *"Do not measure resolution on it."* The output
> banner said so explicitly — `sRGB (BT.709 primaries, D65, sRGB transfer) — for
> looking at, Malvar-He-Cutler demosaic` — and I did not read it before
> measuring. The likely mechanism is exactly the one the warning exists for: the
> Malvar demosaic **interpolates** high-frequency content, and the interpolated
> content is common to both arms, so it dilutes the difference and pushes every
> ratio toward 1. The numbers below replace it, measured on the linear,
> camera-native, binned output that the corpus is measured on.
>
> Design: two 512-px crops from the same pinned pair of `109MSDCF` — the block
> with the most gradient energy and the block with the least — both selected on
> the *mean* of the two arms so the choice cannot favour the arm being judged,
> then the radially averaged power spectrum of each. The control is what makes it
> readable: in the flat crop, any high-frequency difference is **noise by
> construction**, because there is no structure there to lose. Crop separation
> was **4.5x** in gradient energy.
>
> | band (cyc/px) | detail ratio 4.5/2.0 | flat ratio 4.5/2.0 |
> |---|---|---|
> | 0.05–0.10 | 0.9972 | 0.9483 |
> | 0.10–0.20 | 0.9802 | 0.7806 |
> | 0.20–0.30 | 0.8470 | 0.4849 |
> | 0.30–0.40 | 0.4865 | 0.2262 |
> | 0.40–0.50 (to Nyquist) | 0.2159 | 0.1267 |
>
> The honest reading: **gate 4.5 removes a great deal of high-frequency power,
> and it removes consistently more of it from flat regions than from detailed
> ones** — 0.2159 against 0.1267 in the top band, 0.4865 against 0.2262 below
> that. Structure is preferentially retained. **That is not the same as "no
> detail is lost", and the earlier claim that nothing was lost is withdrawn.**
>
> **The instrument was then rebuilt to settle it, and it does.** Two defects in
> the version above: the detail block was chosen by *gradient* energy, which
> favours one strong edge over fine texture (an edge has a 1/f spectrum, so its
> top bands are noise-dominated for trivial reasons); and a pairwise ratio cannot
> say whether a band held real signal in the first place. The rebuild selects the
> detail block by **high-frequency energy** — the quantity actually in question —
> and adds the rung that makes it decisive: **gate 0, ungated**, all detail and
> all noise, against which every other rung is measured.
>
> `detail kept` is high-frequency power in the detail crop relative to gate 0;
> `noise kept` is the same in the flat crop; **FoM = detail kept / noise kept.**
> The construction is self-checking: if a band's "detail" were really just noise,
> the two would fall together and **FoM would read 1.0**. Crop separation was
> **15.4x**, and the script aborts below 3x rather than report an
> indistinguishable pair.
>
> | band (cyc/px) | arm | detail kept | noise kept | **FoM** |
> |---|---|---|---|---|
> | 0.10–0.20 | gate 2.0 **(ships)** | 0.9870 | 0.7328 | **1.35** |
> | | gate 4.5 (gallery) | 0.9674 | 0.4630 | **2.09** |
> | | gate 8.0 | 0.9513 | 0.3383 | **2.81** |
> | 0.20–0.30 | gate 2.0 **(ships)** | 0.8401 | 0.5153 | **1.63** |
> | | gate 4.5 (gallery) | 0.7116 | 0.1492 | **4.77** |
> | | gate 8.0 | 0.6826 | 0.1274 | **5.36** |
> | 0.30–0.40 | gate 2.0 **(ships)** | 0.5781 | 0.4433 | **1.30** |
> | | gate 4.5 (gallery) | 0.2813 | 0.0591 | **4.76** |
> | 0.40–0.50 | gate 2.0 **(ships)** | 0.4719 | 0.4433 | **1.06** |
> | | gate 4.5 (gallery) | 0.1019 | 0.0354 | **2.87** |
>
> **The shipped default is the weakest operating point on the curve.** At
> 0.40–0.50 cyc/px gate 2.0 scores **1.06** — it discards detail and noise in
> almost exactly equal proportion, which is what an indiscriminate blur does.
> Gate 4.5 scores **2.87–4.77** across the same bands. Gate 8.0 is marginally
> better again but buys very little over 4.5 (0.0975 vs 0.1019 detail kept in the
> top band), so the curve has flattened by then.
>
> And the pixels agree, which is the part a trade curve cannot supply: at 1:1 all
> four rungs are **near-indistinguishable** — the paper striations and the
> dendritic fingers on the ink edge survive in every one. So the 72% of
> high-frequency power that gate 4.5 discards above 0.3 cyc/px **is not visible
> as detail loss**, which is consistent with that band sitting above this rig's
> measured optical cutoff, where there is little real signal to lose. The
> print-relevant detail lives at 0.1–0.3 cyc/px, and there gate 4.5 keeps
> **71–97%** of it while removing **54–85%** of the noise.
>
> That is a well-supported case that **2.0 is the wrong default**. It is still
> one subject. A higher gate admits **more frames** into the average — that is
> why it denoises — and the failure mode is admitting frames that are genuinely
> out of focus, which depends on focus step against depth of field. A 22-frame
> stack cannot answer that for a deep stack with coarse steps, and that sweep is
> in flight.
>
> **None of that rescues the scoping.** A survey of 26 subjects that describes a
> configuration the user does not get by typing `strehl stack` is scoped to that
> configuration, and saying so is cheaper than arguing the gap is small. Either
> the default moves to 4.5 or the gallery is re-rendered at 2.0 and re-surveyed.
> That decision is in flight, and this notice comes down when the two agree.

The twenty-four: `bee-1-cpl`, `bee-2-cpl`, `bee-3-cpl`, `leaf-2-cpl`,
`tweezers-cpl`, `coffee-bean`, `112MSDCF`,
`flower-bud-with-background-fern-cpl`, `119MSDCF`, `109MSDCF`,
`wrapped-text-1`, `foam`, `highly-angled-ruler-mm-cpl`, `113MSDCF`,
`lavendar-cpl`, `pencil-steep-angle-cpl`, `pencil-flatter-angle-cpl`,
`dry-erase-marker-head-cpl`, `flower-inner-edge-cpl`, `flat-on-ruler-cpl`,
`coffee-bubbles`, `couch-fibers-cpl`, `flower-bud-alone-cpl` and
`wrapped-text-2`. Individual compound-eye facets, plumose hair barbules
including their branched side-structure, chloroplast speckle, brushed-metal
striations, porous cellular texture, graphite striations over resolved paper
tooth, individual toner particles sitting on individual substrate grains, and
crystal dendrites to near single-pixel width all resolve.

The two that are not: `lead-1-cpl` is **uniformly** soft — no localised defect,
no halo, no patchwork, which is the signature of a capture limit rather than a
merge failure; the cause is not attributable by eye and is not attributed here.
`flowers-cpl` is **capture-limited** in regions that fall outside the bracket
entirely, where the merge correctly renders smooth natural defocus. Neither is
a merge defect, and neither is called a pass.

**The occlusion halo is gone.** Not only where pale hairs cross a dark
defocused compound eye, but in `flower-bud-with-background-fern-cpl` — a dense
multi-layer tangle of overlapping trichomes, bracts and pollen grains at many
depths, where individual hairs resolve *where they cross each other* and no
crossing shows a rim. That is a far harder test than the single-boundary case,
and it is the geometry that rims in every other stacker. `tweezers-cpl` is the
complementary check: dark grooves on bright metal is the classic ringing
geometry, and there is no bright rim along them. `coffee-bean` is the third —
V-HULLCOST found it needs the hull clamp more than any other subject, so it is
also the test that the clamp is not costing detail. It is not.

**One residual, named rather than folded into that verdict.** A separate
edge-profile measurement of the shipping blend finds the hard rim genuinely
gone — the excess at ~21 px, where a rim would sit, is **below 1%** — but the
same measurement finds a **1.24% interior peak at d = 275 px**, far inside the
silhouette and far broader than any rim. Two acceptance criteria had been
written for this and they disagree: it **passes** *"the ring at ~21 px is below
1%"* and **fails** *"no interior peak above 1%"*. Choosing between them after
seeing the number is precisely the error this document keeps catching
elsewhere, so neither is chosen here. What is measured is stated instead: the
hard white rim tracing the silhouette — the thing that was actually complained
about — is gone, and a broad, low-amplitude interior feature at 1.24% is not.
They are different features at different scales. The second has **not** yet
been looked at by eye at 1:1, and that, rather than another statistic, is the
next thing that should happen to it.

The hardest case of all is `highly-angled-ruler-mm-cpl`: a steel rule crossing
the frame at a steep angle, so a hard occluding edge runs diagonally through it
with the background surface behind, and the steep angle forces the deepest
bracket in the corpus — the most frames, and the most chances to get the
boundary wrong. The millimetre graduations terminate crisply at that edge with
**no rim brightening on either side**. The only dark band below the rule is the
rule's own shadow.

The category "not individually judged at 1:1" — which existed precisely so that
a subject nobody looked at and a subject that passed would not print the same
way — is now **empty**, because the survey finished rather than because the
standard moved. The distinction was worth keeping while it had members.

**All 26 subjects have now been opened at 1:1 and none shows a merge defect.**
Two of them were my own *worst*-ranked: I had labelled `119MSDCF` and
`109MSDCF` "genuinely under-resolved, last of 26" on a contrast-normalised
detail ranking. Opening them refutes it — the olive band in `109MSDCF` resolves
hundreds of individual bubbles as crisp high-contrast points, and `119MSDCF`
keeps dust specks as points and shows no chromatic rim on saturated-colour
edges. Both are retracted, which leaves the *under-resolved* category with **no
members at all**.

That empty category deserves the same suspicion as the zero above, and more,
because the two verdicts are not independent — mine by eye, TRIAGE's numerical,
but both formed by parties who expected the merge to be fine. Two methods that
could have disagreed did not; neither has yet been shown able to return the
other answer on this corpus.

And the zero is now **complete**, which makes it a stronger claim resting on
weaker evidence per subject, not a stronger one. Twenty-six inspections by a
single non-blind observer who expected to find nothing is the exact shape of a
result that should be distrusted. What would settle it is a second party opening
the same 26 tiles without seeing these verdicts, or a defect deliberately
planted in a render to establish that this survey can return a defect at all.
**Neither has been done.** Until one is, read this section as "one careful person
found nothing", which is worth something but is not the same as "there is
nothing".

Three of my "soft" findings have now been retracted on inspection
(`flowers-cpl`, `flower-inner-edge-cpl`, and this pair). All three came from a
detail-ranking statistic, and all three turned out to be subjects with little
structure rather than outputs with little sharpness. **The statistic was
measuring the subject.**

The cure is not a better statistic. It is an **in-frame control** — a feature in
the same picture you already know should be sharp. `wrapped-text-1` is the clean
demonstration: printed lettering whose ink edges are visibly soft, sitting on a
surface whose speckles are individually crisp. Both came out of the same frames
through the same estimator, so the soft edges are the ink bleeding into the
texture, not the stacker. That takes seconds to see and needs no calibration,
and it is the check the detail ranking was standing in for.

One observation that was open and is now settled, and it ended somewhere none of
the three candidate explanations expected. `foam` is dark cellular plastic with
blown specular highlights — maximum contrast at a hard edge — and its highlight
rims carry visible orange, cyan and magenta. Three explanations were live:
lateral chromatic aberration, thin-film iridescence (foam has thin films, and
iridescence is a real optical effect), and clipping. All three were eliminated
or confirmed by measurement rather than argument.

**It is not lateral CA.** Rendering `foam` twice from one binary with the
correction on and off, and measuring edge colour in six radial bands with the
edge mask found on *green* so it cannot be manufactured by the colour being
measured, gives a clean radial signature in red — `1.003x` at the centre, which
is a perfect null since lateral CA is zero on axis, falling to `0.758x` at the
corner. But blue is barely touched at all: `0.988x` at the same corner, on the
same edges. Something non-radial was surviving the correction.

**It is not iridescence, and it is not demosaic error.** Among hot edge pixels
`B−G` is positive on **88.9%** of them; thin-film interference cycles hue
through both signs and cannot produce a one-sided excess. Demosaic error would
stay radius-dependent, and at matched level the blue edge colour is **flat
across the whole field** (0.0671 centre against 0.0692 corner).

**It is a channel-asymmetric highlight-saturation defect, and it is ours.** In
the rendered master **green's ceiling is 38921 while blue's is 52239**, so as a
highlight brightens green pins first and the pixel acquires a one-sided blue
excess. `B/G` climbs monotonically **1.0257 → 1.2903 across all nine level
deciles** — which a fixed white-balance gain cannot do, because a gain makes
`B/G` a constant multiple independent of level. Dropping the top 0.76% of
luminance collapses the corner/centre ratio from **1.878 → 1.031**, about 96% of
the effect, while removing *the same number* of pixels at random leaves it at
**1.856 ± 0.088** — a 7.6 sd separation, so it is *which* pixels were removed
and not how many.

**The apparent radial pattern was composition, not optics**: the corner band is
51.99% bright highlights against the centre's 0.68%. Chasing it as a field
effect was chasing a sampling artifact, and two of us did.

Because the defect is a function of **level rather than field position, it will
affect any subject with blown speculars** — wet surfaces, dew, chitin, glass,
metal — not just this one. A fix is in progress.

This paragraph previously ended by saying `STREHL_FIX_CA` is **off** in the
shipping render. **That was false and is retracted.** The correction is default
**on** whenever the EXIF gear guard matches, which it does for this rig; the
pinned shipping binary prints `lateral CA : CORRECTING, profile
"a7c2-fe100gm-2xtc-x4cpl" (gear matched; default on)`. The claim came from
reading a command line instead of running the program, which is the error the
rest of this section exists to avoid.

### Two verdicts per subject: retouch this, or reshoot this

Each subject in the gallery carries **two** tags, and they answer different
questions. The first is the 1:1 verdict above — *can you print the detail that
was examined*. The second is a whole-frame capture verdict — *was anything
anywhere in this frame limited by the capture rather than by the stacker*.

Three subjects are **print-worthy where I looked and capture-limited somewhere
else**: `tweezers-cpl`, `leaf-2-cpl` and `flower-bud-with-background-fern-cpl`.
That is not a contradiction; it is the distinction the tool exists to draw. A
gallery that showed only one of the two tags would be hiding it.

Across all 26 subjects and **51 distinct evidence-bearing sites**, zero were
limited by the merge. All 14 defective subjects are capture-limited — 10 by a
bracket that ran out of focus travel before covering the subject, 4 by a subject
that moved. The remedy for those is a different capture, not different software,
and the gallery now says which and by how much (`13/24 blocks, all far` tells
you the bracket needed to extend further, and in which direction).

**That count used to read 64 and it was inflated by double-counting.** An
independent re-test found 13 of the 64 were one block counted twice under two
labels — `bee-1-cpl`'s DETAIL and SOURCE-BEST are the identical measurement,
8463.3 and 8925.9 DN/px, listed as two sites. 51 is the number of distinct
`(subject, block)` pairs.

**The zero has now survived the test it needed, and the test says less than the
sentence above sounds like.** A count of zero reads identically whether nothing
was wrong or the detector cannot fire, so a merge defect was planted — Gaussian
blur applied to the merged master alone, sources untouched, hash-verified per
rung — and the classifier does flip:

| subject | flips to MERGE-LIMITED at |
| --- | --- |
| `109MSDCF` (worst site already near parity) | **0.4 px** |
| `bee-3-cpl` (merge starts 1.81x ahead at DETAIL) | **1.8 px** |

The two thresholds differ because the flip point measures *subject headroom*,
not detector floor: a plant must first erase the lead the merge already has. On
a subject at parity the detector fires between 0.3 and 0.4 px. **The detector is
potent and the zero is a real measurement.**

Three things the same re-test found wrong, all of which narrow the claim:

- **The margin is 7%, not 39%.** The headline paired the maximum of one
  statistic with the threshold of another. The classifier tests
  `blur_equiv_px`; the corpus maximum is **0.746 px** against a 0.80 px
  threshold. Three subjects sit within a factor of 1.63 of it. Fragile at the
  top, robust below — 19 of 26 subjects read exactly 0.000.
- **The 0.80 px threshold was never pre-registered.** `git log -S` over all
  refs finds it in a single commit, and the classifier's mtime is later than
  every measurement it judges. It is a post-hoc threshold, which is not the same
  as a wrong one, but it may not be quoted as a prediction that held.
- **The scope is narrower than "the merge is never the bottleneck."** Only
  Gaussian blur was planted, and the statistic behind the verdict is a p99.5
  gradient percentile. A *pedestal-shaped* defect — a veil, a tone shift, a DC
  offset — does not change local slope and would score 0.00 px at every one of
  the sites. So the honest claim is **no merge defect of a resolution
  character**, and the veil described below is precisely the class the
  instrument cannot see.

One risk remains open and unmeasured, and it is the largest: the capture-limited
verdicts are adjudicated *before* the merge test runs, so a false coverage-gap
or motion call would mask a merge verdict underneath it. Three subjects
(`lead-1-cpl`, `dry-erase-marker-head-cpl`, `flowers-cpl`) carry 1.41–3.00 px
merge deficits at sites that the earlier rules route away. Nobody has yet shown
those routings are correct.

What is not fixed: a *veil* at occlusion boundaries. Its mechanism is measured
rather than guessed — the merge selects the right frame, and the veiled detail
is present at 0.85 correlation with the frame that resolved it, but the
pyramid's base band is a plain unweighted mean across every frame, so at an
occluded pixel it averages in the ~290 frames showing the defocused foreground
and lifts the pedestal. Correct detail, wrong brightness. See §59.3 of
[`ORCH-veiling.md`](docs/research/ORCH-veiling.md).

`verify_gallery.py` exists because the generator's "nothing missing" line is
printed from the same variables it used to build the page. The verifier re-reads
the written HTML, resolves every `src` against the filesystem, and checks that
each crop labelled 1:1 is actually large enough to be one — the failure a link
checker passes.


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

**In practice, on this corpus — and this has now been measured rather than
argued.** All 26 reference renders were produced on this path, and the question
of whether any of them *needed* those two stages was put to three independent
tests.

*Motion.* Twenty-two crops at 1:1 across fifteen subjects, examined as
pictures: **zero visible ghosting**, including the hardest geometries in the
set — bee setae against white, and printed text. The other eleven subjects were
**not viewed** (15 viewed + 11 not viewed = 26, stated as a partition so an
unexamined subject cannot read as a clean one; they are the subjects with no
hot cluster worth cropping). Numerically, 10 of 26 subjects show any
inter-frame displacement clearing a floor measured on a subject that physically
cannot move, and the largest detection anywhere in the corpus clears that floor
by only 1.90x. Nothing in the corpus needed outlier rejection.

*Exposure.* This one corrected the reason, not just the claim. Several subjects
show flux ramps across a bracket that look alarming — up to half a stop
end-to-end — and the obvious reading is exposure drift. It is mostly not.
It is **magnification**: as focus breathing changes the scale, flux follows
`ln flux = -2 ln scale` with no free parameter, which reduces the ramp RMS by
up to 5.06x and survives a permutation null at p=0.0025. Between *adjacent*
frames the residual is 0.003-0.006 stops, which is nothing. So the gate is not
being fed drift on most of this corpus, and the earlier phrasing here —
"if your exposure held steady" — was giving the right advice for the wrong
reason.

*The exception.* `foam` is a genuine photometric outlier: **0.32 stops within
8 frames**, with inconsistent EXIF. One subject in twenty-six does need the
stage that does not exist. The blanket "none of them needed those stages"
that stood here before was wrong, and this is what replaced it.

**The estimator backend runs again — this paragraph used to say it did not, and
that is retracted.** A reachability audit once found that `--merge estimator`
exited non-zero with `U3 the eroded low-detail region keeps only 0 px` unless
`STREHL_PHOTOMETRIC=off` was set in the environment. That finding was true when
made and is now stale: photometric normalisation became **opt-in**, and the
stage prints `STATUS: NO per-frame gain term is fitted or applied`. Measured on
the pinned shipping binary, `strehl stack <DIR> --merge estimator` **exits 0**,
banner `merge backend : estimator (--merge)` — the binary's own words are
*"reachable, NOT the default"*. Two further full runs by a separate campaign
also exited 0. The `U3` string still exists at `photometric.rs:371`; it is
simply no longer reached. **It is still not a fallback to reach for**, for
different reasons than the ones given here before: it is *slower* than the
default (320.9 s against 229.7 s at comparable load), and it loses to the
pyramid on acuity and microcontrast on all three subjects in the comparison
table below. The audit's other finding stands unchanged — four of the five
stages the banner lists as "not applied" are fully written and reachable only
from that path, so the capability exists and has never run on a delivered
image, and the shipping default remains the less capable of the two backends.

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

**Shadows are not crushed by the merge.** A pyramid merge can leave the
output above or below the range of every input that fed it, which shows up as
punched-out white or crushed black along high-contrast edges. The delivered
renders carry **zero** exact-zero RGB pixels on subjects where an unclamped
merge produces 0.371% and 1.048%. Dark is subject, not clipping.

That paragraph used to be headed *"Highlights are not clipped by the merge"*.
**Retracted, and the reason is worth stating plainly: every number in it is a
count of exact-ZERO pixels.** It measured the shadow end and claimed the
highlight end, and the claim stood for as long as it did because the heading and
the evidence were read by the same people at the same time. The shadow result is
real and is kept above; the highlight half was never measured.

Measurement since then points the *other* way. On the pyramid arm, pixels pinned
at the container maximum run **4.65% frame-wide against the estimator's 1.87%**,
and **20.48% against 0.0952% inside one 47–93 px band** — with p90 already at
65522 and everything above p95 pinned flat. Two caveats, both real: that
comparison came from an A/B whose arms are now known to differ by more than the
merge, so the *ratio* is not cleanly attributable; and the two arms carry a
global affine difference of +2.3% gain and −359 DN offset. The *absolute* count
on the shipping arm is a direct census of a delivered render and does not depend
on either.

**And the tool cannot presently see this on the path that ships.** The clip
census is described in the source as *"always reported, not hidden behind
`--stats`, because a clipped pixel is a correctness question rather than a
diagnostic one"* — and the pyramid backend does not run it, which it discloses
honestly in both its doc comment and its runtime banner (`not applied :
photometric gain, clip census, ...`). Skipping photometric normalisation and
outlier rejection on a merge that is not an estimator is defensible. Skipping a
*counter* is a different thing: counting what you pinned is not an estimation
stage. So the one measurement this codebase singles out as a correctness
question is the one the default path does not make. That is being fixed, and
until it is, **treat highlight behaviour on the default backend as unmeasured
rather than as passing.**

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
| Output | an image | an image (**see the caveat below — the confidence map is not on the default path**) |
| Capture geometry | one hardcoded assumption | fitted per stack, not baked from one rig |

**The per-pixel confidence map is designed, built, and not reachable on the
backend that ships.** This row previously claimed it as a shipped differentiator
and that was an overclaim. What is true: `--n-eff-map` writes a genuine
per-pixel map of how many frames were effectively averaged
(`merge_cmd.rs:2636`), and it is one of **nine** flags the CLI refuses on the
default pyramid backend — along with `--index-map`, `--stats`, `--gate`,
`--target-n-eff`, `--photometric`, `--flat-roi` and `--detail-roi`. They belong
to the estimator. The estimator does run (the claim that it did not is retracted
above), but it is not the default and is slower, so in practice the default path
emits an image and nothing else, and a user cannot presently ask this tool which
parts of its output to trust.

That is the single largest gap between what this project is *for* and what it
currently *does*. Confidence as an output is the thesis, not a feature: a
stacker that cannot separate "retouch this" from "reshoot this" is a bug report
rather than an instrument. Closing it is the top priority after the merge
itself.

No existing tool is RAW-native. Zerene states plainly that "no stacking software
really works directly with raw files"; Helicon's RAW workflow demosaics via
Adobe DNG Converter before it aligns anything.

v1 targets **in-camera focus bracketing**. Focus-rail capture is a designed-for
seam but is deferred until there is hardware to test it against.

## The honest performance claim

Not "N times less noise". The gain depends entirely on how many frames actually
see a given point in focus.

> **Scope, stated before the numbers: every `gate` row below is an ESTIMATOR
> measurement, and the estimator is not what ships.** `--gate` is one of the nine
> flags the default pyramid backend refuses outright — `strehl merge --merge
> pyramid --gate 2` exits 1 with *"--gate belongs to the estimator merge, and
> --merge selected pyramid."* The pyramid's own knob is `--pyramid-gate`, and the
> binary is explicit that it is **a different quantity**: a multiple of the
> modelled band-noise power, where `--gate` is a multiple of the focus-response
> SD. *The number does not carry over.* This notice used to say that the table
> had no row for the backend that ships, that the shipping path's noise was
> therefore **unquantified**, and that the notice would come down when the row
> landed and not before. **The row has landed** — the last two rows of the table
> are the default backend, measured by a separate campaign
> ([`docs/research/BUILD-PYRNOISE.md`](docs/research/BUILD-PYRNOISE.md)) on the
> same ROI, the same bracket and the same single unstacked frame. Two things
> support joining the two campaigns in one table: that campaign re-measured the
> **estimator** at gate 2 with its own instrument and read **0.888x** against
> this table's **0.890x** — a 0.2% agreement between instruments built weeks
> apart and never cross-checked before — and its positive control, a planted
> known σ, recovered `sqrt(σ0²+σa²)` to a worst error of **0.157%** against a
> 1.0% bar. Note also the inference trap that produced the original gap: passing
> an estimator-only flag *without* `--merge` silently
> selects the estimator — measured, `--gate 2` alone prints `merge backend :
> estimator (inferred from --gate)`. Any harness quoting numbers below may have
> been on the estimator without meaning to be.

Measured on the 22-frame reference bracket, over a
low-detail region, against a single unstacked frame:

| gate | mean `n_eff` | flat-ROI noise | |
| --- | --- | --- | --- |
| 0.0 | 1.000 | **1.074x** | selection — *worse than not stacking* |
| 0.5 | 1.414 | 1.027x | still worse |
| 1.0 | 1.884 | **0.973x** | first gate that beats one frame |
| 2.0 | 2.891 | 0.890x | |
| 4.0 | 4.987 | 0.788x | |
| — | — | **1.068x** | the argmax `strehl argmax-baseline` ships |
| — | *N* | 0.534x | a plain mean — the floor, and it destroys 58% of detail |
| — | not computed | **0.915x** | **`--merge pyramid` at its default `--pyramid-gate 2.0` — this is what you actually get** |
| — | not computed | **0.746x** | `--merge pyramid --pyramid-gate 4.5` |

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

**On a whole photograph, measured — and then substantially retracted.** This
paragraph used to report `leaf-2-cpl`, 182 frames, with noise falling
**0.006381 → 0.000987** in a 200x200 flat patch: a ratio of **0.1546x**,
quoted as *"equivalent to averaging 41.8 frames"*. It was the most persuasive
number in this file. Three things are wrong with it and only the first was
suspected.

**It measures a backend that no longer ships.** Both arms were selected with
`--gate`, which chooses the estimator merge. The shipping default is the pyramid
merge. Whatever this paragraph established, it did not establish it about the
code a user runs.

**It does not reproduce on the current binary.** Re-run on the shipping pin, the
same script re-chooses its patch and reports **0.6196x** and **2.61 frames** —
against 0.1546x and 41.8. Mean `n_eff` falls **15.077 → 5.229**, with 62.57% of
pixels at `n_eff` = 1, and `--gate 0`'s "1.000 with 100.00% of pixels" now reads
1.006 / 99.37%. Two pinned conditions agree with each other, so the merge
changed, not the measurement.

**The figure was mostly a choice of patch.** Holding the *inherited* ROI fixed
on that same pin gives **0.1408x** and 50.4 frames — corroborated to 3.3% by the
binary's own `--n-eff-map`. Re-choosing the patch by the same script on the same
binary gives 0.6196x. **A 4.4x spread on one subject, one binary, one merge,
decided entirely by which flat patch the search lands on.** The number was never
a property of the merge alone.

The honest whole-plane figure, which is the one a photograph actually receives,
is the tool's own **0.8556x** predicted sigma gain. **"41.8 frames" is withdrawn
as a framing**, not merely as a value: it is a best case by roughly fifty-fold
against the plane, and quoting a best case beside the caveat that it is one
turned out not to be enough, because the caveat travelled and the number was
what people remembered.

Measured and adjudicated by BUILD-PYRNOISE, whose admission test first flagged
this subject for the *wrong* reason and who said so — see
`docs/research/BUILD-PYRNOISE-ADJUDICATION.md`. I argued to them that a
non-stationary subject would inflate an arm-versus-arm ratio. **They measured it
and I was wrong**: the inflation is 1.02x, and thirteen windows that fail their
admission test predict the measured ratio to under 3% (correlation between
admission score and error: −0.002). The mechanism cancels between two merges of
one bracket because both elect the same frames through the same spatially
coherent winner field. The paragraph did not die of the disease I diagnosed.

On resolved detail the expected gain was **`ARGUED` at ~1.2-1.8x** — the
reasoning being that at a sane focus step only about 1.3 to 1.5 frames have any
given depth inside their depth of field. **That figure has now been measured,
and it is not observed.** Six subjects rendered twice from one binary — the
shipping pyramid merge and the shipping `argmax-baseline` selector — and
compared green plane, camera-linear, at 36 matched sites chosen on the mean of
both arms, come out **indistinguishable**.

**The direction survives independent re-measurement; the number did not.** A
verifier built a separate instrument sharing no code with the first — a spectral
blur-match, commissioned to identity at +0.0000 and to a pure-scale pair at
−0.002 — and over its own 109-tile grid reports pooled **−0.183 px, 95% CI
[−0.249, +0.076]**: no merge gain on any of six subjects. But the published
**"0.5 px" is an artifact of a truncated ladder**, not a floor: a relative
deficit of 1e-6 inverts to 0.155–0.184 px through that ladder and to **exactly
0.000** through an exact Gaussian. **The claim that the noise gap was "also 0.5
px" is therefore withdrawn** — it was never a physical coincidence, but two
small relative differences pushed through one compressive nonlinearity. Measured
with a noise-corrected instrument, the arms' pure noise difference is **+0.04 to
+0.09 px** on five of six subjects.

The form of this result that needs no ladder, no inversion and no Gaussian model
is the raw half-energy frequency: **`f50_merge / f50_argmax` = 0.900 to 1.010**,
against the 1.20–1.80 that was argued. Those are the units the claim should
always have been in. Selection wins outright on one subject,
`flat-on-ruler-cpl`.

The tie is also **backend-invariant**, which closes a trap rather than opening
one: the same comparison run against the estimator backend gives margins that
agree with the pyramid's. There is no hidden win on the other path.

That it is the *shipping* backend was checked from the runs' own banners rather
than assumed from their command lines, because the two can disagree: passing any
estimator-only flag without `--merge` silently selects the estimator, and the
binary reports that this caught 338 call sites in 185 files. All six headline
arms print `merge backend : pyramid (default)`; the only estimator banners in
the tree read `estimator (--merge)`, stated rather than inferred; and the string
`inferred from` does not occur anywhere in it.

**The merge's advantage on this corpus is noise and the absence of invented
structure, not fineness.** That is a narrower claim than the one this paragraph
used to make, and it is the one the measurement supports.

**And the null is more favourable than it sounds, because of what the losing
arm is doing while it ties.** Per-pixel selection has no correct value to choose
in genuinely out-of-focus ground — no frame contains one — so adjacent pixels
elect different source frames and the region shatters into piecewise-constant
plateaus with hard polygonal edges. A detail statistic scores those manufactured
edges *as detail*. Measured on the two arms' own crops, as gradient kurtosis
inside low-detail regions chosen on the mean of both arms (higher = more flat
plateaus punctuated by hard steps):

> **WITHDRAWN, 2026-08-26.** A six-row gradient-kurtosis table stood here, with
> ratios from 2.79x down to 1.01x, and a geometric story that read them against
> subject depth. **I asked the verifier to attack it and it did not survive.**
> Four defects, any one of which is disqualifying at the precision I quoted:
>
> - **It was measured through a tone curve.** The crops were written as
>   `(v ** (1/2.2) * 255)` and read back through a luma channel mix. This
>   project's own standing rule is that nothing is measured on a gamma-encoded
>   path, and I broke it in the README.
> - **The statistic rises 2.313x on a pure blur plant and 1.302x on pure
>   noise** — the confounds are the size of the effect it was reporting.
> - **`frac = 0.35` was load-bearing and was never varied.** At `frac = 0.10`
>   the top subject reads **0.90**, below unity, reversing its sign.
> - **Three implementations disagree**: `bee-3-cpl` reads 2.79 / 3.58 / 2.26.
>
> And the correction destroys the narrative rather than shifting it.
> Recomputed camera-linear the *median* effect strengthens, but `tweezers-cpl`
> moves from **1.17x to between 1.86x and 4.20x** — and tweezers has the
> highest absolute kurtosis of any subject in the set. It was the near-planar
> anchor of the "selection is well-posed on flat subjects" story, and it no
> longer sits where that story needs it. Only `flat-on-ruler-cpl` survives as
> an exception.
>
> **What survives is the direction and nothing quantitative**: per-pixel
> selection has no correct value to choose in genuinely out-of-focus ground,
> because no frame contains one, so adjacent pixels elect different source
> frames and the region breaks into piecewise-constant plateaus with hard
> polygonal edges — which a detail statistic scores *as detail*. That mechanism
> is real, visible, and is why the merge should be preferred on a detail tie.
> The size of it is unmeasured and the table that claimed to measure it is gone.
>
> I wrote to the verifier that if the table was an artifact I had put an
> artifact in the README and needed to know that night. It was, and this is the
> consequence. **A statistic that has never been shown to fail is not evidence
> — and I published one that had only ever been shown to succeed.**

Two caveats, because this is the kind of result that gets overstated. The
per-subject cut above was made *after* seeing the per-tile numbers, so it is
descriptive rather than a pre-registered test, and anything built on it needs
its own run. And the crop labels were checked before publication rather than
assumed: on 31 of 35 tiles the argmax-labelled panel is the noisier one in flat
regions, as selection physics requires, and the four exceptions are all
high-detail tiles where the flat-mask catches real subject content
(`experiments/ORCH-drift-check/labelcheck.py`).

Two candidate detail statistics were killed by their own commissioning before
they could vote — both *rise* on blur, by 5.1x and 12.6x on a ground-truth
chirp. A third, which I supplied, failed a noise null it had never been given:
it moves +33% under 15% added noise and reports −0.34 to −0.49 px on a pure
noise difference, which accounts for its entire apparent result on five of the
six subjects. A statistic that has never been shown to fail is not evidence.

**That verification has now landed, and it found defects** — the truncated-
ladder floor, the refuted noise-gap equivalence, and the withdrawn table above.
The direction was confirmed independently and the numbers were not, which is the
outcome the labelling existed for: a negative is as capable of being an
instrument artifact as a positive, and this one was load bearing enough that it
should not have been believed on one agent's word — including when that agent
was arguing against the project's own headline. The noise column
above is unaffected, and was never a result on its own: a plain mean wins it
outright while collapsing detail, which is why `merge` refuses to report it
without a `--detail-roi`.

**Speed — the shipping default, measured end to end.** On the 299-frame, 33 MP
reference stack (11.3 GB of Sony ARW), `strehl stack <DIR> --out <PATH>` — which
is `--merge pyramid` — writes a 7032 x 4688 16-bit TIFF in **116.9 s warm, best
of 3** (96.8 MB/s, 0.391 s per frame, 5.7 GB peak resident), and **327.4 s on a
cold cache**, of which 73.4 s is a one-time registration solve every later run
reads from a sidecar. The fold is **98.5% of the run**: decode, registration
lookup, collapse and the 198 MB write together cost 1.8 s. Cost is linear in
frame count — `wall = 1.1 s + 0.77 s x N`, R² 0.998 — with a **one-second
intercept**, so a small stack pays no fixed setup. Memory is flat at 5.6-5.8 GB
from 20 frames to 299, a 3.2% spread across a 14.9x range of N: the O(workers)
claim holding under measurement rather than being asserted.

> **These are upper bounds, and the machine was the confound.** They were taken
> on a box shared with a dozen concurrent agents. Twelve runs producing
> byte-identical output spanned **116.9 s to 240.2 s**, tracking the machine's
> busy fraction at R² 0.88; child CPU-seconds are not load-invariant either, 510
> to 904 for identical work. The same subject rendered in **102.2 s** on a quiet
> box, for output this build reproduces byte for byte. A worker sweep shows the
> memory-derived 4-worker cap costs **1.29x** against 8 workers on a 16-core
> part — the cap is deliberate, because float addition is non-associative and a
> host-dependent worker count would change the shipped bytes. Commit
> `b9b6921e`, binary SHA-256 `88782BBC…2916`; every timed run exited zero and
> was checked for geometry, dtype, non-degeneracy and detail-in-family against
> the shipped master, with a flat-region control alongside.

**The 22-frame figure is a different measurement, and is scoped as one.** That
stack *merges* in **3.19 s** end to end (1.15 s pass one, 2.04 s pass two) at
**262 MB/s** over 836 MB of RAW, on a Ryzen 9 9950X3D — but that is the `merge`
subcommand on the **estimator** path at an older commit, not `strehl stack` on
the default backend. The two are not comparable and should not be quoted
against each other. Peak memory is bounded at 5 in-flight frames — **never
O(N)** — and decode alone is 1.78 s cold, 0.91 s warm. See
[`M1`](docs/research/M1-decode-measured.md).

## Measured against other stackers

**This is the section that decides whether the project's ambition has been met,
and today it has not been.** An independent verification pass compared strehl
against two external comparators on identical frame sets
([`V-HEADTOHEAD`](docs/research/V-HEADTOHEAD.md)): the patched `focus-stack`
fork this project's owner used before, and **Zerene Stacker PMax**. Frame-set
equivalence was confirmed for both subjects (105 and 63 identical exposures),
and every comparison below has the tone grade removed. Without that step the
numbers are meaningless — the first attempt at them read 0.349 where the correct
answer was 0.735, and a naive microcontrast comparison would have handed the win
to the wrong arm outright.

Contrast ratios by spatial frequency, strehl over comparator, **grade-removed**,
626 ROIs against the fork and 576 against Zerene. **Below 1.0 means strehl is
behind:**

| band (cyc/px) | feature size | vs the fork | vs Zerene PMax |
| --- | --- | ---: | ---: |
| 0.05-0.10 | ~10-20 px | 1.063 | 1.007 |
| 0.10-0.20 | ~5-10 px | 1.079 | 0.936 |
| **0.20-0.30** | **~3-5 px** | **0.833** | **0.735** |
| **0.30-0.40** | **~2-3 px** | **0.766** | **0.843** |
| 0.40-0.48 | ~2 px | 1.060 | 1.511 |

**strehl is at parity or ahead at coarse scales and 17-27% behind at 3-5 pixel
features — against both comparators independently, on two subjects, with tight
confidence intervals.** The 0.40-0.48 band is noise-dominated in both
comparisons and is not evidence of resolution; do not read 1.511 as a win. The
verifier tried to explain the deficit away and could not: it is **not** capture
sharpening, because both subjects' XMP sidecars read `crs:Sharpness="0"`, and it
is not an artifact of the grade, because removing the grade properly is what
produced these numbers. About **half** is attributable to strehl's own 3.5%
coverage upscale; the rest sits in the merge and the gather kernel, where strehl
uses Catmull-Rom against the fork's `cv::INTER_LANCZOS4`. Work to close it is in
flight.

**What strehl wins, and these are not close:**

- **Noise.** On flat defocused ground, high-pass rms **0.5025% → 0.1125%** — a
  **4.5x** reduction against the fork, of which at least **2.4x** survives a
  worst-case grade correction. The fork's residual is grain; strehl's is real
  structure. This is estimation-not-selection doing the thing it was built for.
- **Clipping.** The fork clips **32% of the frame** on one subject; strehl
  clips **4e-6** of it.
- **Occlusion halos.** strehl is lower on **all four** rim measures, and
  neither arm's median edge profile exceeds 1.0. Bounded honestly: the
  instrument only resolves rims above roughly strong-unsharp-mask strength.

**So "state of the art" is not a defensible claim for this tool today, and is
not made anywhere in this document.** What the measurements support is that
strehl is competitive with both comparators, decisively better on noise and on
clipping, and measurably behind on fine microcontrast. Three caveats bound even
that: both subjects were Lightroom-developed for the comparators and RAW for
strehl, a confound that cannot be removed without abandoning the comparator the
owner actually uses; Zerene's **DMap** mode never rendered, so this is only
against PMax, its contrast-and-noise-raising mode, which flatters it on exactly
the axis strehl loses; and two subjects against two comparators is a floor under
*competitive*, not a foundation for *state of the art*.

The same pass reported that **three of its own instruments failed their
controls** — a 10-90% rise metric with no power, and two rim measures reading
+428% on a clean image and +0.02% on a real unsharp mask. They are recorded in
the report rather than quietly dropped. The numbers above are the ones that
survived commissioning.

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
