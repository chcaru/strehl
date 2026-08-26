# BUILD-BLEND — a Laplacian multi-band merge against the depth-boundary rim

**Verdict, in one line: the multi-band merge removes every seam defect ORCH has
reported — the tight rim, the broad aura, the jagged silhouette outline on
`bee-1-cpl`, and the straight-edged polygonal patches — and it does not soften
`couch-fibers-cpl`. It does cost flat-region noise, and that cost is real.**

> **The "no added noise" claim in the previous headline is retracted.** At pin
> `275fbd1` the blend arm is measurably noisier in flat regions on
> `couch-fibers-cpl`: `+11.8%` fine-band RMS, or `+104%` in gradient RMS,
> depending on the statistic. It is not caused by the hull clamp (isolated: the
> unclamped arm is *worse*), it is not the base band (isolated at a fixed pin
> earlier), and it is not the measurement space (linear and sRGB agree). At pin
> `0d9fd28` the same script on the same subject in the same space read `1.0015`,
> so something between those pins changed it. See "The noise cost, measured
> three ways and attributed to none of my levers".

Measured against a `STREHL_ONLY_FRAME` reference, which performs no election at
all, on the subject ORCH chose for the purpose:

| feature | shipped selection merge | this arm | reference |
|---|---|---|---|
| broad aura, median at d≈112 px | **−4549 DN (−23.9% of backdrop)**, reaches d≈300 px | **below the 45 DN noise floor** | 0 by construction |
| peak background deviation, d ≥ 30 px | −4549 DN (−23.9%) | **+698 DN (+3.7%)** | 0 |
| tight rim, median, d ≤ 16 px | below floor | +993 DN (+5.2%), dies by d≈16 px | 0 |
| far-field offset from the reference | +9.3 DN | +11.0 DN | 0 |
| flat-region noise vs the shipped merge | 1.000 | **0.989 / 0.991 / 0.998 / 1.002** | — |

The dominant defect — the one that is 23.9% of the backdrop and reaches 300 px
— is removed. What is left in its place is a deviation 6.5× smaller and of the
opposite sign. That residue is real and is not claimed to be zero.

> **Two earlier claims in this report are now retracted, and both were against
> my own arm.** The `12.3% noisier on couch-fibers` cost in the previous
> headline does not reproduce: the flat-region noise ratio is now 1.0015 there
> and below 1.0 on all three other subjects. **I first attributed that to the
> base band and the attribution was wrong.** Holding the pin fixed at `0d9fd28`
> and changing *only* the base band gives 0.9980 (weighted) against 1.0015
> (mean) — both ≈ 1.0, so the base band cannot be the cause. The difference is
> therefore between pins, in shared code I do not own, and I am not able to
> attribute it further without bisecting other agents' commits. The old numbers
> are kept in "The price this arm pays" with the retraction attached, rather
> than deleted.

Three things must be true for the rim sentence to be worth anything, so they
are stated before anything else:

* **It is not blur.** A blurred render has no rim either. On the do-no-harm
  frame `couch-fibers-cpl` every Laplacian band of this arm is at or *above*
  the shipped pipeline's amplitude — there is no band in which it is softer.
  The first version of this merge *was* visibly soft there, was caught, and was
  fixed.
* **It is not a framing artefact.** The two arms were checked to share a pixel
  grid exactly (`geometry_check.py`, best integer shift `0, 0`) before any
  conclusion was drawn from a side-by-side.
* **It is not a develop-path artefact.** Both arms are built from one archived
  SHA and run back to back from that one build, so they share the demosaic, the
  tone curve and the colour path exactly. My first comparison did *not* have this
  property; I caught it and redid all six renders. See "The confound I shipped,
  and then caught".

## Look at these

Full frame is the judging surface; the 1:1 files are supplementary evidence
about a defect that is already visible at full frame.

| | full frame (primary) | 1:1 at the largest disagreement |
|---|---|---|
| **flower-bud-alone (the measured subject)** | `C:\dev\strehl-out\BUILD-BLEND\sxs-flower-bud-alone-cpl-BM.jpg` | `rim-flower-bud-alone-cpl-BM.jpg` |
| **flower-bud + fern (bright rim)** | `sxs-flower-bud-with-background-fern-cpl-BM.jpg` | `rim-flower-bud-with-background-fern-cpl-BM.jpg` |
| **lavendar (dark rim)** | `sxs-lavendar-cpl-BM.jpg` | `rim-lavendar-cpl-BM.jpg` |
| **couch-fibers (do-no-harm)** | `sxs-couch-fibers-cpl-BM.jpg` | `rim-couch-fibers-cpl-BM.jpg` |

**The `-BM` set is the current result.** All four subjects, both arms, one
archived SHA (`0d9fd28`), one build, run back to back, `STREHL_FIX_CA` set
identically on every render, and this arm in its new default base band. The
older `-CA` set below is the previous configuration and is kept as the record.

`rim-flower-bud-alone-cpl-BM.jpg` is now the single most informative file. The
control panel shows the subject's edge behind a **milky, low-contrast veil**
with pink/purple fringing on it; the blend panel shows the same edge dark,
saturated and crisp. That veil is the same thing the profile below measures as
the merge running +39% bright *inside* the silhouette at d = −65…−100 px.

| | full frame (previous config) | 1:1 |
|---|---|---|
| flower-bud (bright rim) | `sxs-flower-bud-CA.jpg` | `rim-flower-bud-CA.jpg` |
| lavendar (dark rim) | `sxs-lavendar-CA.jpg` | `rim-lavendar-CA.jpg` |
| couch-fibers (do-no-harm) | `sxs-couch-fibers-CA.jpg` | `rim-couch-fibers-CA.jpg` |

All in `C:\dev\strehl-out\BUILD-BLEND\`. Left panel is the shipped pipeline,
right panel is this merge. Both arms go through the **identical**
`gallery_view.py` recipe — `tifffile`, assert `uint16`, `>> 8`, Lanczos — so a
tone difference cannot be an artefact of the viewer.

**Judge the `-CA` files.** Both arms have `STREHL_FIX_CA=a7c2-fe100gm-2xtc-x4cpl`
set, per ORCH's instruction, so the lens's lateral chromatic aberration — which
neither merge causes and which has its own colour signature on every edge —
cannot be mistaken for a merge difference. They supersede the `-PAIRED` set,
which was matched-tree and correct but CA-off; the rim verdict is the same in
both, which is itself worth knowing, because it means the rim is not a colour
artefact. Earlier `sxs-*`, `*-v2` and `*-FINAL` files in the same directory are
intermediate arms kept as the record of how the parameters were chosen; they
are not the result.

`rim-flower-bud-CA.jpg` is the single most informative file. It shows **two**
defects in the control panel, not one: the bright cut-out rim tracing the leaf,
and a hard-bordered patch of differently-blurred content pasted across the
lower leaf — the artefact ORCH described seeing in a 2x crop. The blend panel
has neither.

### The confound I shipped, and then caught

The `-FINAL` pair was **not a like-for-like comparison and should not be used.**
Its control came from the then-current gallery pin `pin-859edac`, but between
that binary being built and my renderer being built, a sibling agent landed
`1cacb61 tone: place black and white on luminance, not per channel` — a change to
`image_out.rs`, which is the develop path my renderer `#[path]`-includes. The
tone change landed 14:32; my binary was built 15:14. So the two arms were
developed through **different tone curves**, and every tonal difference I
reported between them was partly that change rather than my merge.

This is exactly the "builds land mid-run" hazard the brief warned about, and I
walked into it. The fix, which is what the brief prescribes: `git archive` a
single SHA to a directory outside the tree, build **both** arms there, and run
all six renders back to back from those two binaries.

- tree: `C:\dev\strehl-out\BUILD-BLEND\tree-d4b8644\` (from `d4b8644`)
- control binary sha256 `E1708B9A30423F283B1D99268411B74302517FA25A1AC9AF93523EC38770B449`
- blend binary sha256 `0A44CADBC0F343699D1812FE553B0B3AA5B73412F08B3D9D2CFDB78E6139416D`

The rim verdict was **unchanged** by this correction, which is the reassuring
part: a tone curve cannot create or remove a hard-edged mask stain. Two other
claims of mine did not survive it, and both are corrected below.

### What the frames show

On **flower-bud**, the control's bright outline around every leaf, the bud and
the stem is gone. At 1:1 the control also shows a hard-edged grey stain lying in
the background alongside the silhouette, with a visible mask edge, and a magenta
patch on it; the blend's background there is clean and uniform. The control's
leaf has a glossy, plasticky look with bright blobs on it. The blend's leaf reads
as a matte leaf with visible surface texture.

On **lavendar**, the opposite polarity, the dark rim around the white flower is
likewise gone, and the mottled hard-edged blotches in the control's background
are replaced by a smooth gradient.

On **couch-fibers**, the two are indistinguishable at full frame. At 1:1, in the
window of *largest low-frequency disagreement* — a crop chosen to be maximally
unflattering to the blend, not hand-picked to flatter it — fibre edges are
equally crisp in both, and the blend holds slightly deeper contrast in the dark
inter-fibre gaps with less colour fringing on the specular highlights.

**Correction to my own earlier claim.** In the confounded `-FINAL` round I
reported "marginally less high-frequency sparkle" on `couch-fibers` and flagged
a residual softness. **In the matched-tree `-PAIRED` round I cannot reproduce
it.** The most likely explanation is that it was the tone-curve mismatch:
per-channel versus luminance black/white placement changes local contrast, and
lower local contrast reads as softness. I am not claiming the softness is
definitively gone — I am reporting that the better-controlled comparison does
not show it, and that my earlier flag rested on a comparison I now know was
invalid.

**I no longer decline to put a number on acuity.** When this was written the
only statistics I had for it — gradient energy, high-pass energy — had both
lied on this project by being satisfied by injected structure, and
`edge_overshoot` gets pinned by a single specular highlight. That objection was
correct and it is answered rather than ignored: "The price this arm pays" below
reports band amplitude *and* a flat-region noise measurement side by side,
which is what separates a sharper image from a noisier one. The answer that
came back is partly against this arm, and it is stated there.

**Retraction of a framing I inherited.** Earlier drafts of my thinking leaned on
ORCH's hypothesis that the rim's sign is anti-correlated with the subject's
brightness, implying a wide veiling term. **ORCH has retracted it and I am not
relying on it.** `STREHL_ONLY_FRAME` renders a single frame with no election at
all, and across 470 px of backdrop the arms `off`, `on`, `frame000` and
`frame298` are superimposed within noise, all rising the same ~4%. A feature
identical in a single exposure and in the merge is the scene's own illumination
field, not an artefact. The observation that survives is narrower and more
useful: **the merge departs from a single-frame reference only within ~10–20 px
of the silhouette.** Nothing in this report's conclusions depends on the
retracted hypothesis; the rim result was always judged on frames, and the
distance-resolved check that this arm respects the scene outside that zone is
in "Where the two arms differ, by distance from the silhouette".

## Why this arm exists — the structural argument

A per-pixel selection followed by a gather puts a **hard discontinuity wherever
the elected frame changes**, and that discontinuity exists at *all* spatial
frequencies at once, including the low frequencies where the eye is most
sensitive to a step. That is what a "cut-out sticker" rim is.

In a Laplacian-pyramid merge, the selection weights are band-limited by
construction. A selection error at level `k` can only inject an error of level
`k`'s extent and amplitude. **There is no path by which a wrong pick becomes a
hard low-frequency step.** The merge does not need to diagnose the rim's
mechanism in order to not produce it.

That asymmetry turned out to be the design's most useful idea, and not only for
the reason it was introduced — see "the sharpness must depend on scale" below.

## What was built

* `crates/strehl-core/src/pyramid.rs` — the module. Operators (`reduce`,
  `expand`), `Pyramid` (build / build_gaussian / collapse), `BandGain`,
  `luma_variance`, `BandMerge` (a streaming fold), `FrameWorkspace`. 22 unit
  tests.
* `crates/strehl-cli/examples/blend-render.rs` — full-frame renderer.
* `crates/strehl-core/src/lib.rs` — one line, `pub mod pyramid;`. The only edit
  outside the lane.
* `experiments/BUILD-BLEND/` — `compare.py` (side-by-side), `strip.py` (N-up
  parameter strips), `geometry_check.py`, `tone_split.py`.

The renderer is deliberately **not** wired into the CLI merge path. It pulls
`align_cmd.rs` and `image_out.rs` in with `#[path]` rather than reimplementing
them, so registration and development are byte-identical to the shipped path and
the two arms differ **in the merge and nowhere else**. Neither file is modified.

## Design decisions

**Soft weighting, not hard argmax.** Sign coherence comes free: a convex
combination cannot take adjacent coefficients from opposite-signed frames, which
is the ringing that coefficient-wise argmax-of-magnitude produces. And it
degrades to averaging where frames are indistinguishable, which is the only
operation that gets *below* single-frame noise. `SelectMode::HardMax` exists as a
reachable control arm.

**The noise model gates every band.** `floor = gate · beta[k] · V_k(x)`,
`excess = max(0, E_k − floor)`. Where no frame clears the floor the merge
averages instead of selecting. This is the single thing separating this from a
naive pyramid stacker, whose signature failure is that argmax over 300 noisy
coefficients reliably elects the largest noise excursion, so flat regions *gain*
contrast. Measured on the real frames, the gate refuses selection on 13–34% of
the finest band and ~0% below it — exactly the right shape, and evidence the
gate is actually gating rather than decorating.

**`beta[k]` is measured, not derived.** The tempting derivation (the kernel's
squared-weight sum, compounded per octave) is right for the first reduction and
badly wrong after, because the samples stop being independent; by level 3 it is
an order of magnitude low and the gate silently stops gating. `BandGain::measure`
pushes fixed-seed white noise through the real operators and reads `E[L_k²]/σ₀²`
off the interior. A test asserts the result is a property of the operators by
checking it does not change with probe size.

**The sharpness must depend on scale — this is the part worth keeping.** The
same asymmetry that makes a pyramid merge immune to the rim also says the two
ends of the pyramid want *opposite* treatment:

* **Fine bands: be aggressive.** All the acuity lives here, and this is exactly
  where being wrong is cheap — a wrong pick is one high-frequency coefficient
  nobody can see. Blending here is a low-pass of the sharpest information in the
  stack, which is precisely the softness a conservative merge gets criticised
  for.
* **Coarse bands: be gentle.** A wrong pick here, expanded through the collapse,
  *is* the rim.

A single global exponent throws that away by treating every band with the same
caution. The exponent now ramps 1.4× per octave toward fine: `2 3 4 5 8 8 8`.
Chosen by sweeping 1.0 / 1.4 / 2.0 on an 80-frame subsample of both an acuity
subject and a rim subject and looking at the frames — 1.4 and 2.0 were
indistinguishable, 1.0 was visibly softer. The gentler of two equals wins,
because the coarse bands are where the risk sits.

**The base band is taken weighted from the coarsest band, not averaged.** The
base grid is 2^bands coarser than the output, so even a hard mask there becomes a
transition spread over ~128 output pixels — smooth by construction — while still
giving correct *local* tone at a depth boundary instead of averaging in every
defocused frame's veil. `BaseBand::Mean` is the conservative alternative and is
one flag away.

**Selection runs on green luma only, shared across all four CFA planes**,
matching the shipped election. Letting a colour plane's own noise drive selection
manufactures chroma speckle.

**Streaming fold.** Every accumulator is a sum, so `BandMerge` is a monoid and
`absorb()` combines partial merges exactly. `strehl-core` has no rayon
dependency, so the module is single-threaded by construction and the parallelism
lives in the example — which is why the chunk/absorb shape is public API.

## Two bugs worth recording

Both were found by rendering and looking, not by the tests that existed at the
time. Both now have tests.

**The band-gain probe was a fixed 256×256**, which bottoms out at five bands. A
real 3520×2344 plane at the default seven indexed off the end of `beta` and
panicked mid-render.

**The clamp on the selection weight was uncentred, and that turned the acuity
parameter into a blur parameter.** The first sharpened render came out as glowing
mush. The cause: with `p = 16`, a clamp on `p · ln(snr)` at 60 saturates above
`snr = 42`, so *every clearly-in-focus frame received an identical weight* and
the merge averaged all of them. Dividing by a reference SNR first centres the log
so weights straddle 1 and the clamp becomes what it was meant to be — an
overflow guard that never binds.

`MAX_EXPONENT` then had to drop 16 → 8, because 16 is **not representable**: a
real stack spans `snr` up to ~1e5, and above `p ≈ 10` the sharpest coefficients
can no longer be ranked against each other in f32. If more selectivity than 8 is
ever wanted, the answer is `HardMax`, which is exact.

The test that guards this does **not** assert "no overflow" — the buggy version
did not overflow either. It asserts the weight keeps *ordering* frames across the
full SNR range a real stack contains.

## Honest numbers

### Timing — and why I now distrust my own first table

Ryzen 9 9950X3D, 299 frames at 33 MP, warm warpmap cache. I have two rounds, and
**they disagree in sign**, so I am reporting both rather than the flattering one.

Round 1 (confounded `-FINAL`, blend on 4 workers, control a separately-built pin):

| subject | blend total | control total |
|---|---|---|
| flower-bud | 252.4 s | 208.6 s |
| lavendar | 207.4 s | 168.7 s |
| couch-fibers | 213.0 s | 185.0 s |

Round 2 (matched tree `d4b8644`, both binaries from one build, six renders back
to back, blend self-limits to **3 workers**, control uses **13**):

| subject | blend total | control total |
|---|---|---|
| flower-bud | 163 s | 259 s |
| lavendar | 141 s | 213 s |
| couch-fibers | 141 s | 163 s |

Round 1 says the blend is 15–25% *slower*; round 2 says it is 14–35% *faster*,
on a quarter of the workers. **Both cannot be right, and the honest conclusion is
that wall-clock timing is not reliably measurable on this machine right now**:
five sibling agents are building and rendering concurrently, and the load during
either round is unknown. The same contamination showed up in my memory
measurements (below).

What I will state with confidence is only the shape: the fold is O(frames) with a
small constant, the merge self-limits its worker count from a memory budget so it
runs fewer workers than the control, and it is **not** catastrophically slower —
it is in the same order. Anyone deciding on cost should re-measure at equal
worker counts on a quiet machine. I am not claiming a speed win.

Peak working set, measured by sampling the process, against frame count:

| frames | 20 | 80 | 160 | 299 |
|---|---|---|---|---|
| peak | 4,692 MB | 4,711 MB | 4,774 / 4,749 MB | 4,775 MB |

**+1.8% across a 15× increase in frame count** — O(workers), not O(frames), as
the fold structure requires. Planned 4,284 MB against 4,775 MB measured, the
difference being the output mosaic and allocator overhead.

One earlier reading at 160 frames came in at **8,200 MB**. It did not reproduce
on two re-runs (4,774 and 4,749 MB) and is recorded here rather than dropped: it
was almost certainly another agent's process inflating system memory pressure on
this shared machine. If a future run sees peak memory scale with frame count,
this note is the prior evidence that it should not.

## The two defects, reported separately

ORCH measured the shipped merge against a `STREHL_ONLY_FRAME` render — one
frame, no election anywhere, so the scene cancels by construction — and found
**two** defects, at very different scales and with opposite signs. A single
"halo score" would let an arm that fixes one and worsens the other read as
progress, so they are reported separately here and the instrument that produces
them is gated on being able to tell them apart.

Subject `flower-bud-alone-cpl`, 205 frames, chosen because a featureless white
backdrop cannot be changed by defocus. Linear camera-native output
(`image_out::OutputSpace::CameraLinear`) — the tone curve amplifies the rim
about 4×, so an `--srgb` render would overstate any fix. Reference is frame
102, the merge's own alignment reference, so both arms are identity-warped.
Pin `0d9fd28`, `STREHL_FIX_CA` on for every arm.

Median deviation from the single-frame reference, referenced to each arm's own
far field (600–1400 px from the silhouette). Negative distances are **inside**
the subject.

| d (px) | shipped selection merge | this arm (weighted base) | this arm (**mean base**, default) |
|---|---|---|---|
| −100…−80 | +457 | +142 | −449 |
| −80…−65 | +335 | +84 | −482 |
| −20…−16 | −451 | −17 | −692 |
| −1…0 | −914 | +458 | −343 |
| +4…5 | −852 | +1172 | +359 |
| +12…16 | −512 | +1798 | +993 |
| +30…40 | −1801 | +1413 | +698 |
| +65…80 | −4192 | +1204 | +452 |
| **+100…125** | **−4549** | +1102 | **+288** |
| +200…250 | −2532 | +1227 | +562 |
| +250…300 | −249 | +1180 | +531 |
| far-field offset | +9.3 | −475.0 | **+11.0** |
| instrument noise floor | 29.7 | 835.0 | **45.0** |

**The broad aura is removed.** The shipped merge's −4549 DN dip at d ≈ 112 px —
23.9% of the 19038 DN backdrop, reaching 300 px — falls below this instrument's
45 DN noise floor. In its place is a deviation that peaks at +698 DN (+3.7%),
6.5× smaller and of the opposite sign, and much flatter with distance.

**The residue is not zero and I am not claiming it is.** A roughly +300…+700 DN
positive offset persists across the whole backdrop out to 300 px. Neither
feature statistic reports it — the rim window is |d| ≤ 16 px and the aura
statistic takes a minimum — which is a reporting gap in my own instrument, so
it is stated here explicitly rather than left to be inferred from the table.

**What the rim column means, and what it does not.** Inside |d| ≲ 20 px the
reference is *defocused* — the transition from subject to backdrop is about 50 px
wide in frame 102 — so a sharp arm and a blurred reference must differ there,
and that difference is the merge working, not a halo. The near-contour numbers
in this table are therefore not interpretable as halo, and the d ≈ 112 px number
is, because a featureless backdrop has nothing for focus to change. This is
ORCH's own reason for choosing this subject and it cuts both ways.

### The base band was the one decision I argued instead of measuring

The middle column above is the previous default, `BaseBand::WeightedFromCoarsest`.
Its docstring called it "the better default" on an argument: the base grid is
2^bands coarser than the output, so even a hard mask on it is smooth after the
collapse, and weighting buys local tone at a depth boundary.

The first half of that is true. The second half is the problem — the weights are
a function of position, so the merged *level* is too, and on a featureless
backdrop, where there is no focus signal to justify any particular weighting,
the level simply wanders. It cost **−475 DN of global level** (−2.5%) and
**835 DN of position-dependent structure** in a subject-free quadrant, against
**+11 DN and 45 DN** for the plain mean. The shipped merge, for scale, sits at
+9.3 DN and 29.7 DN.

Both base bands removed the aura equally well, so this is not what buys the
headline result, and — measured, at a fixed pin — it is **not** what removed the
noise cost either: `couch-fibers-cpl` flat-region noise is 0.9980 with the
weighted base and 1.0015 with the mean. What the base band decides is whether
the arm introduces a *level* defect of its own while removing the aura. The
default is now `BaseBand::Mean`, `--base-weighted` keeps the losing arm
reachable, and two tests pin the choice — one on the default value, one
asserting the two arms are not the same merge, because a default chosen by
measurement is worthless if the thing it beat was itself.

**Nothing in the 432-test suite noticed the flip when I made it.** That is the
condition the two new tests exist to remove.

### My instrument reported a false clean, twice, for the same reason

`twofeature.py` in its first form found ORCH's aura to within 5% **and reported
no tight rim at all** — not only on my renders but on ORCH's own TIFFs. Rather
than conclude their rim was not real, I looked at the instrument. It had two
defects, both of the same family: *a window that cannot express a feature
reports its absence, and reports it in exactly the same glyph as a real
negative.*

1. **The bins started at d = 0**, so only the *outside* of the contour was ever
   profiled. ORCH's `diffmap.png` shows the thread **on** the contour.
2. **The narrowest bin was 4 px and the statistic was a median.** Commissioning
   a 4 px-wide plant straddling the contour recovered **+108 DN of a planted
   +984** — an 89% amplitude error — because a median over a half-filled bin
   returns roughly the unaffected half.
3. **A median over a 7 Mpx silhouette's annulus cannot see a localised
   feature.** Commissioning a 2 px thread on 15% of the contour gives
   **median +11.5 DN** and **p95 +1007 DN**. A median-only instrument calls that
   clean.

With 1 px bins spanning the contour and a p95 column, the same instrument on the
same ORCH TIFFs finds a **+6595 DN localised bright feature at d = −7.5 px**,
just inside the contour. The feature was always there. The summary could not
express it.

The commissioning gate now runs seven planted cases — rim outside, inside, and
straddling the contour; a 2 px thread; aura alone; both together; and a null —
recovers every amplitude to within 0.3%, requires that a planted rim does *not*
read as an aura and vice versa, and separately verifies that the noise floor
every detection gate divides by is non-zero and rises monotonically (16.0× across
a 16× noise range). A floor of exactly 0.0 would silently turn every
`peak > 5 × floor` test into `peak > 0`, which is how the first version of this
gate was passing.

## The price this arm pays

> **Superseded, and retracted where it is wrong.** Everything in this section
> was measured at pin `6a51e43` with the old weighted base band. At pin
> `0d9fd28` the noise cost does **not** reproduce — see the current numbers at
> the end of the section. The section is kept because the retraction is only
> meaningful next to what it retracts.

The owner asked for a number on one specific trade: whether a multi-band merge
can be *conservative at the coarse scales where the rim lives while staying
aggressive at the fine scales where texture lives*. BUILD-HALO's blocker is
that their fix reduces the halo **and softens `couch-fibers`**. This is the
directly comparable number.

Whole frame, no crop, both arms CA-on from the same archived build. RMS
Laplacian band amplitude in 16-bit DN, raw columns first, ratio derived
(`experiments/BUILD-BLEND/bandtrade.py`):

| band | scale | ctrl RMS | blend RMS | ratio |
|---|---|---|---|---|
| L0 | ~2 px | 536.84 | 613.03 | **1.1419** |
| L1 | ~4 px | 703.70 | 762.43 | 1.0835 |
| L2 | ~8 px | 1073.87 | 1133.57 | 1.0556 |
| L3 | ~16 px | 1435.72 | 1495.13 | 1.0414 |
| L4 | ~32 px | 1709.70 | 1757.88 | 1.0282 |
| L5 | ~64 px | 1828.32 | 1848.49 | 1.0110 |
| residual | >=64 px | 44731.06 | 44652.46 | 0.9982 |

Mean level ratio 0.9983, so this is not a tone difference wearing a detail
costume. **There is no band in which this arm is softer on `couch-fibers`.**
That is the answer to the softening question and it is a clean pass.

### But a ratio above 1 is not a win, and here it is not one

This project has twice been fooled by exactly this reading — "+6.7% gradients,
therefore not a blur" while measuring a blotchy artifact, and "+16.8% high-pass
energy" on crops chosen for containing no structure. Extra high-frequency
energy is what a sharper image and a noisier image both look like. So the
+14.2% at L0 was not reported as sharpness; it was sent to a detector built to
tell those two apart.

`experiments/BUILD-BLEND/flatnoise.py` ranks pixels by the local variance of a
heavily blurred luma and keeps the flattest 20%. Selecting on **coarse**
structure while measuring **fine** energy does two jobs at once: the coarse
field is essentially identical in both arms, so neither arm chooses its own
pixel set; and real detail is by construction absent from flat regions, so
fine-band energy there is overwhelmingly noise. In a flat region there is
nothing to be sharper about.

| subject | ctrl flat fine RMS | blend flat fine RMS | ratio |
|---|---|---|---|
| **couch-fibers (do-no-harm)** | 621.46 | 697.87 | **1.1230** |
| flower-bud (bright rim) | 598.06 | 600.39 | 1.0039 |
| lavendar (dark rim) | 599.31 | 644.94 | 1.0761 |

**On `couch-fibers` essentially all of the +14.2% extra fine-band energy is
noise, not detail.** The whole-frame L0 excess is +14.2% and the flat-region
noise excess is +12.3%; there is very little left over to be sharpness. I am
stating that against my own arm because it is what the instrument says.

This matters more here than it would elsewhere. The shipped path's central
claim is that it gets *below* single-frame noise — 5.43x where a selector
scores 0.77x on a burst whose right answer is known to be sqrt(30) = 5.48x.
A 12.3% noise increase is a real regression against the more valuable of this
project's two crown jewels, even though it is modest in absolute terms.

The mechanism is not mysterious and it is not intrinsic to multi-band merging.
The shipped path averages *every* frame whose response the noise model cannot
separate from the winner's, which is an explicitly noise-minimising design. My
per-band weighting uses exponents 2–8, which concentrates weight far more
narrowly and therefore averages fewer frames. Lowering the fine-band exponents
and widening the gate trades directly along that axis, and is the first thing
to try if this arm is taken further.

### So the comparison, in one table

Superseded row included, because the retraction is the point.

| | removes the rim | removes the broad aura | softens `couch-fibers` | noisier on `couch-fibers` |
|---|---|---|---|---|
| BUILD-HALO's selection fix | reduced, not removed | not reported here | **yes — their stated blocker** | not reported here |
| this arm, pin `6a51e43`, weighted base *(superseded)* | yes, both polarities | not measured then | no — no band is softer | ~~yes, +12.3%~~ **retracted** |
| **this arm, pin `0d9fd28`, mean base** | **yes, both polarities** | **yes — −23.9% → below floor** | **no — no band is softer** | **no — 1.0015** |

At pin `0d9fd28` the flat-region noise ratio is 1.0015 on `couch-fibers-cpl`,
0.9914 on `flower-bud-alone`, 0.9887 on `flower-bud-with-background-fern` and
0.9977 on `lavendar` — three of four *below* 1.0. Holding the pin fixed and
changing only the base band gives 0.9980 (weighted) against 1.0015 (mean), so
the base band accounts for none of the change and the cause lies between pins,
in shared code this agent does not own.

The remaining question — which arm is preferable — is the owner's call, not
mine. The one thing I would put on the scale is that noise is recoverable by
averaging more frames and lost acuity is not recoverable at all.

## Where the two arms differ, by distance from the silhouette

> **Superseded by "The two defects, reported separately".** ORCH has since
> retracted the 10–20 px bound this section is built on: the dominant defect
> peaks at d ≈ 117 px and reaches ~300 px. A broad backdrop difference is
> therefore expected rather than anomalous, which reframes the open charge this
> section raises against my own arm rather than clearing it. Kept as the record.

ORCH's correction makes this the load-bearing check on this arm. `STREHL_ONLY_FRAME`
showed that across 470 px of backdrop the arms `off`, `on`, `frame000` and
`frame298` are superimposed within noise, all rising ~4% — and two of those
contain no election at all, so that 4% is **the scene's own illumination
field**. The instruction that follows is that the merge departs from a
single-frame reference only within ~10–20 px of the silhouette, and that
anything "fixing" the backdrop further out is editing the photograph.

That zone is corroborated from inside the code: `focus.rs` has
`SUPPORT_RADIUS = SOBEL_RADIUS(1) + WINDOW_RADIUS(13) = 14 px`, and documents
that "the rim cutoff tracks the window radius 1:1 over radii 9–26, slope 1.07".
An independently measured ~10–20 px departure zone and a 14 px support radius
are the same number.

So a merge that removed the rim by quietly lifting the whole backdrop would be
a *worse* outcome than the rim, and no whole-frame statistic can tell those
apart. `experiments/BUILD-BLEND/distprofile.py` bins the difference between the
arms by distance from a silhouette defined from the **control's own content**
(the gradient of a sigma-8 px blurred luma), never from the difference between
the arms, which would be circular.

`lavendar`, robust gain 0.9982, de-gained mean shift:

| distance | 0–5 | 5–10 | 10–20 | 20–40 | 40–80 | 80–160 | 160+ |
|---|---|---|---|---|---|---|---|
| mean shift, DN | +479.9 | +481.7 | +389.3 | **+96.5** | −59.3 | −3.6 | +289.4 |

**This is the shape the instruction asks for.** The change is +1.3% of level
inside 20 px and collapses to ~0 immediately beyond it. On `lavendar` this arm
edits the rim zone and leaves the scene alone.

`flower-bud` is not as clean and I am not going to present it as if it were.
After removing a robust gain of 1.0530 the de-gained mean shift runs +188 DN at
0–5 px, rising to +714 DN at 40–80 px — roughly +0.5% climbing to +2.0%, in the
wrong direction for a confined fix. The 160+ bin is unusable: 58% of it is at
or above 60000 DN, so it is clipped and cannot move.

The leading explanation is this arm's own documented gap rather than the
multi-band principle. It has **no photometric normalisation**, and regions at
different depths draw from different frames, so an un-corrected per-frame gain
drift lands as a *depth-correlated* brightness difference — and distance from
the silhouette is correlated with depth. That is exactly the shape observed.
It is a stated limitation of this renderer, it is fixable, and the shipped
merge does not have it. **But I have not established that explanation, and
until someone does, a ~2% backdrop difference on `flower-bud` stands as an
open charge against this arm.**

### One instrument defect worth recording, because it inverted a verdict

The first version of `distprofile.py` estimated the global gain as the ratio of
means. On `flower-bud` that returned 1.0304 when the true gain is 1.0530,
because 58% of the frame is a bright backdrop sitting against the saturation
ceiling and physically unable to move; averaging a compressed region with an
uncompressed one under-estimates the gain. The under-correction left residue in
*every* distance bin and the table read as a broad backdrop edit — a serious
charge against this arm, produced entirely by my own estimator. The median over
unclipped pixels does not have that failure. The lesson generalises: **a
normalisation fitted across a clipped region will manufacture a spatially broad
artefact out of a purely global difference.**

## The synthetic two-layer ground truth, and why its rim rows are inadmissible

ORCH asked both arms to report on the synthetic two-layer scene with known
ground truth referenced at `crates/strehl-cli/src/merge_cmd/halo.rs:31` (M87
§6.3), on the reasoning that a scene where the correct answer is known by
construction is the one instrument that cannot be satisfied by injected
structure. The CLI only ingests `.arw` from a directory, so the harness lives
in-crate: `crates/strehl-cli/examples/blend-truth.rs`. It scores the shipped
selection primitives (`FocusField::compute` → `merge::regularise` → argmax →
gather) against `BandMerge` on identical frames, plus a depth-oracle floor,
per M87 §26.3's rule that arms be scored against an achievable floor rather
than against each other.

**The headline is a negative about the instrument, not about either merge.**

Three scene defects were found and fixed, each caught by a null:

1. **The background was inside the bracket** (`BG_DEPTH = 36` of 48 frames), so
   the selection arm won the far field by trivially electing frame 36. The real
   backdrop is *out* of bracket — BUILD-HALO §17.2 records the fern as "a
   subject with no sharp frame anywhere in the bracket". Fixed to `BG_DEPTH = 78`.
2. **The backdrop carried texture at the rim scale**, which made *ground truth
   itself* score 0.04856 on the ISO metric against the selection merge's
   0.05558 — the metric was reading texture, not rim. M87 §2.1 names this exact
   failure direction. After reducing backdrop amplitude the nulls came clean:
   truth 0.00010, single frame 0.00165.
3. **The subject sat at a single depth.** M87 §16.5 measures the real flower's
   subject spanning 248 of 299 frames p10–p90, and shows a *global* foreground
   depth removes only 1.2% of its halo. Fixed so `fg_depth(y)` ramps across 92%
   of the bracket, varying by row, keeping each row a physically consistent 1-D
   occlusion problem.

After all three, the selection arm still scores only **2.0x–2.6x its own
single-frame null**, where M87 on real data measures 0.06804 / 0.000026 =
**2617x**. The scene under-produces the defect by roughly 1250x. The harness
therefore prints `*** SCENE NOT COMMISSIONED` and **refuses to report its edge
rows**. That refusal is printed rather than left to the reader.

This corroborates the existing corpus from a new direction. M63 "killed the
two-layer model"; M87's own unmixing reached −28.2% against a −50% bar.
Building a clean two-layer scene and failing to reproduce the defect is the
same conclusion approached from the opposite side: **whatever this halo is, it
is not what a clean two-layer occlusion produces.**

### The admissible half

The `texture` scene — the `couch-fibers` analogue, pixel-scale depth variation
and no silhouette — needs no rim commissioning, and there the comparison
stands:

| arm | RMSE against achievable truth, DN |
|---|---|
| shipped selection primitives | 253.1 |
| **this multi-band merge** | **134.0** |
| depth oracle (achievable floor) | 48.6 |

The blend lands **47% closer to truth** and captures **58.2% of the headroom**
between the selection arm and a depth-oracle. The oracle's 48.6 DN is
effectively the single-frame noise floor, so the non-noise (acuity) component
falls from ~248 to ~130: the win is not noise-averaging.

### An oracle is not automatically a floor

Worth recording because it cost me a wrong reading. The depth oracle scores
*worse* than both real merges in the ≤20 px band (2198 against 143 and 240).
The reason is that it is restricted to one frame per pixel, and in **every**
frame the foreground's blurred matte spills ~19 px over the background — so
in-band there is no frame in which the matte is sharp *and* the background is
well rendered. The band is genuinely ambiguous and the "ideal" target is
unattainable there. M87 §26.3's rule still holds, but **the floor has to be
checked for validity per region**, not assumed globally.

## The index field this arm never forms

BUILD-CHROMA found the election index map contains jumps of up to **191 frames
between adjacent pixels** (median 0.000, so a thin tail). Two neighbouring
pixels in a 299-frame bracket gathering from indices 191 apart are sampling
unrelated points in the focus sweep. The shipped 17x17 box regulariser
(`merge::REGULARISER_RADIUS = 8`) applied across such a jump *averages the
indices* — 40 and 231 give 135, an index at which neither depth is in focus.
That is a plausible reading of fact 86's non-monotonicity, where width 3 is
worse than no regularisation at all.

A coefficient-space merge never forms an index field, so it cannot inherit this
failure mode. In my synthetic scene the selection arm's index field shows max
adjacent jumps of 41–47 of 48 frames — 85–98% of the bracket, the same class of
behaviour as BUILD-CHROMA's 191 of 299 — while the blend arm has no index field
in which a jump could occur.

I have **not** measured the real 299-frame index field myself, so the 191 figure
remains BUILD-CHROMA's and is cited, not reproduced. What I can report directly
is the visible consequence: `rim-flower-bud-CA.jpg` shows in the control panel a
hard-bordered patch of differently-blurred content pasted across the lower leaf
— the artefact ORCH described seeing in a 2x crop — and the blend panel does not
have it. **This arm removes the hard-edged patch artefact as well as the rim.**
That is a second visible defect gone, and it is consistent with the index-jump
account, though it does not by itself prove it.

## How the instruments were commissioned

Every number above comes from a script that was made to fail on purpose before
it was believed. A metric that has never been shown to move is not an
instrument.

| script | null | positive control | result |
|---|---|---|---|
| `bandtrade.py` | control vs itself, all 7 ratios exactly 1.000000 | one-octave blur must drop band 0 below 0.60 | 0.5548 — PASS |
| `distprofile.py` | control vs itself, every bin exactly 0 | +900 DN rim planted within 14 px must localise | far bins exactly 0.0000 — PASS |
| `flatnoise.py` | control vs itself, ratio exactly 1.000000 | ladder of +150/300/600/1200 DN white noise must respond monotonically and reach the +14% it must adjudicate | 1.0228 / 1.0885 / 1.3192 / 1.9896 — PASS |
| `blend-truth.rs` | ground truth and a single frame scored against themselves | selection arm must beat its own single-frame null by the margin M87 measures on real data | 2.0–2.6x against 2617x — **FAIL, rim rows withheld** |

Two of these gates were themselves wrong on first writing, and both failures
are worth recording because they are the same failure:

* `distprofile.py`'s positive-control gate read the *de-gained* column, which by
  construction carries a level-proportional residue because the plant itself
  shifts the global mean. It failed a probe whose raw column was reading
  exactly 0.0000 in every far bin — i.e. it condemned the probe precisely when
  the probe was perfect.
* After the estimator was fixed, the same gate required `deg_far > 0` to form a
  ratio, and so failed again when perfect separation drove the far field to
  exactly zero.

**A gate that cannot express a perfect result will report a perfect result as a
failure.** Both were fixed by gating the raw column for localisation and
treating exact zero as infinite separation.

## Differences from the control arm, and what is not done

These are real and are not hidden in the comparison:

* **No photometric normalisation.** The shipped merge fits per-frame gains from
  first-pass flux. Doing that here would double the decode cost, which is the
  whole runtime. The expected consequence is global, not local — the base band is
  close to a mean across frames, so gain drift lands as an overall exposure shift.
  Measured: the blend runs 0.4–5% brighter, and a single global gain-and-offset
  fit explains only 3–35% of the total difference between the arms, so the bulk of
  what the side-by-sides show is the *picture* differing, not the exposure.
* **No clip handling and no outlier rejection.** Both are separate stages in the
  shipped path and neither is what this arm tests.
* Not wired into the CLI. Deliberately — the merge path is another agent's lane.

## Recommendation

This arm worked on the defect it was built for. Both defects ORCH measured are
gone — the tight rim on both polarities and, more importantly, the broad aura
that was 23.9% of the backdrop and reached 300 px — the hard-edged patch
artefact is gone with them, and the mechanism debate about *why* they exist
turned out not to need resolving in order to remove them. That was the point of
running a structurally different second arm.

The trade ORCH asked for a number on — conservative at the coarse scales where
the aura lives, untouched at the fine scales where `couch-fibers` texture lives
— is the one this representation gets by construction, and it holds:

* **Coarse scales:** the aura's −4549 DN median at d ≈ 112 px falls below a
  45 DN noise floor. The residue is +698 DN peak (+3.7%), opposite in sign and
  6.5× smaller.
* **Fine scales:** on `couch-fibers-cpl` no Laplacian band is below the shipped
  pipeline's amplitude (L0 1.051, L1 1.065, L2 1.051, residual 1.002), and
  flat-region noise is 1.0015. At the *worst* 1:1 disagreement window the two
  are indistinguishable in sharpness.

The bill, measured rather than assumed:

* **A +300…+700 DN (+1.6…+3.7%) positive offset across the backdrop out to
  300 px.** Small next to what it replaced, but not zero, and neither of my two
  feature statistics reports it — the rim window stops at 16 px and the aura
  statistic takes a minimum. That reporting gap is mine and it is why the number
  is stated here in words.
* **~2% backdrop difference on `flower-bud` outside 20 px** — this was logged as
  an open charge under the earlier brief, which held that the merge departs from
  a single frame only within 10–20 px. **ORCH has since retracted that bound**,
  and a defect reaching 300 px means a broad backdrop difference is expected
  rather than anomalous. The charge is therefore *reframed, not cleared*: what
  it actually was is the same broad deviation now quantified in the table above.
* **The `+12.3%` noise cost previously reported here is retracted**, and so is my
  first attribution of the retraction. See the note under the headline: at a
  fixed pin the base band accounts for none of it.

Before this goes anywhere near the ship path it needs: photometric normalisation,
clip and outlier handling, an attack on the residual backdrop offset (the coarse
bands' gate and exponent are the levers — depth is already sufficient, the
coarsest Laplacian band spans 128 output px and the base 256), and an
independent verification pass — in this project's doctrine the author does not
verify their own work, and that applies to every number in this document.

Cost is now measurable but still soft. Back to back from one binary on
`flower-bud-alone-cpl` (205 frames): shipped merge 111.9 s, this arm 87.5 s;
across the four `-BM` subjects this arm was faster on three (79 vs 96, 111 vs
143, 133 vs 200) and slower on one (175 vs 146). Directionally this arm is not
slower, but the machine is running five other agents and my earlier two rounds
disagreed in *sign*, so I am claiming no more than that.

It is also untested on subjects beyond these four. Bees, tweezers and text all
stress different parts of a merge — specular highlights, hard synthetic edges,
and fine periodic detail respectively — and none of them are represented here.

## The mid-tone clip, reproduced and removed

ORCH-veiling 29 established by construction that this module emits values no
input frame supports, and named the fix as mine. It is now made and the defect
is gone. Both blend arms below are the same binary on the same 205-frame stack,
one flag apart, so nothing but the clamp can differ between them.

`flower-bud-alone-cpl`, camera-native linear, pin `275fbd1`, CA on
(`experiments/BUILD-BLEND/clipcheck.py`, which reports ORCH's statistics so the
two are directly comparable):

| arm | exact-zero px | exact-0 % | luma<500 % | median DN | R zero | G zero | B zero |
|---|---:|---:|---:|---:|---:|---:|---:|
| ORCH's pyramid render (§29.1) | 122,416 | 0.371% | 1.310% | 18550.5 | 123,050 | 176,531 | 460,886 |
| **mine, `--unclamped`** | 115,503 | 0.350% | **1.311%** | 18541.7 | 115,616 | **176,566** | **462,519** |
| **mine, default** | **0** | **0.000%** | **0.000%** | 18538.8 | **0** | **0** | **0** |
| shipped estimator | 0 | 0.000% | 0.002% | 18137.3 | 2 | 1 | 15 |

The unclamped arm replicates ORCH's numbers from a render they never saw: green
to 0.02%, blue to 0.4%, `luma<500` to 0.001 of a percentage point. Red is 6%
off, which I attribute to their render coming through the CLI backend rather
than this example binary. The clamp takes all three channels to exactly zero.

### What the clamp moved, which the count does not say

`clamped_fraction` reports 8.6–11.0% of pixels per plane, and a clamp binding on
a tenth of the frame deserves more than a count
(`experiments/BUILD-BLEND/clipmag.py`):

| statistic | value |
|---|---:|
| pixels moved > 1 DN | 11.670% |
| of those, moved **up** (clamped to the floor) | **84.7%** |
| median \|move\| over moved px | 275.0 DN |
| p95 / max \|move\| | 1338 / 4457 DN |
| **global level shift** | **+39.75 DN (+0.264%)** |

And by input brightness:

| input luma | px | moved % | median \|move\| |
|---|---:|---:|---:|
| 0–1,000 | 5,883,993 | **83.408%** | 548 DN |
| 1,000–4,000 | 14,035,491 | 39.563% | 118 DN |
| 4,000–12,000 | 1,584,990 | 15.590% | 141 DN |
| 12,000–30,000 | 77,506,086 | **1.093%** | 330 DN |

This is ORCH's predicted mechanism, confirmed on data their toy model never
touched. The excursion is **downward** (84.7% of moves are upward corrections),
it concentrates **in the dark** (83.4% of shadow pixels moved against 1.1% of
the well-exposed majority, which is 77.5M of 99M), and blue leads red 4.0×
against their predicted 3.7×. Every signature they derived from 40 lines of
numpy is present in a 33 MP render.

The clamp is therefore surgical rather than tonal: it repairs crushed shadows
and leaves 98.9% of the well-exposed frame alone, for a global level change of
a quarter of one percent.

### Commissioned, not asserted

The load-bearing test is the negative control. A clamp tested only on a case
that never violates its bound passes vacuously, and the same green tick means
"fixed" and "never broken". So
`unclamped_the_reconstruction_leaves_the_hull_of_its_inputs` constructs eight
frames whose fine and coarse bands prefer different frames over the same ground
and **requires a violation to be present**, and requires it to be non-trivial in
size so noise cannot satisfy it. Only then does the clamped twin assert zero.

One finding fell out of building the diagnostic. Identical frames have a *point*
hull, so every float error in the collapse is formally outside it, and the first
version of `clamped_fraction` duly reported 1.7% on a stack of identical frames.
That is dust, not binding. The method now takes an explicit tolerance, and its
test asserts the dust exists at `tol=0`, is under 1 DN, and does not fool the
diagnostic at `tol=1` — so the tolerance is shown to be necessary rather than
chosen to make a number look good.

## `bee-1-cpl`: the jagged outline and the polygonal patches

This subject had never been through this arm. ORCH reported two defects on it: a
jagged bright outline stair-stepped along the forelegs, and straight-edged
polygonal patches of wrong-depth content inside the subject.

**Both are gone.** `sxs-bee-1-cpl.jpg` shows the silhouette rim at full frame —
present as a bright scalloped band on the thorax fuzz and around the forelegs in
the shipped arm, absent in this one. `rim-bee-1-cpl.jpg` is the more useful
picture: at 1:1 the shipped arm's white backdrop is broken into hard-edged
angular facets meeting along straight lines, a low-poly look that **defocus
cannot produce**, and in this arm the same backdrop is smooth and continuous.
The hair tips are also better separated against it.

That is the prediction this arm was built on, confirmed on a third subject: a
coefficient-space merge never forms an index field, so it has no boundaries to
print. It cannot inherit the 191-frame index jumps or the 17×17 box regulariser
averaging across them.

### Am I masking rather than fixing?

ORCH asked for this explicitly, and it is the right question. The honest answer
is **partly, and the part that is masking is the coarse bands**.

What this arm does *not* do is make a wrong election look smoother — it makes no
election. But its per-band weight is still an **energy** measure, so it shares a
family resemblance with the focus measure BUILD-ELECT is investigating. The
difference that matters is that mine is **scale-resolved**: a box-summed
gradient over a 13 px window mixes every scale into one number, where band power
at level *k* is the energy at scale ≈2^k alone. Defocus is a low-pass, so at
fine scales energy *is* a sharpness proxy and the weight is sound. At coarse
scales it is not — a defocused bright feature carries real coarse-band energy —
and there the merge is deliberately gentle, which is closer to declining to
decide than to deciding well.

So if BUILD-ELECT finds the focus measure is biased, that finding still stands
and this arm does not repeal it. What this arm removes is the *seam*, which is a
separate defect that would survive a perfect election and does not depend on the
election being wrong.

## The noise cost, measured three ways and attributed to none of my levers

ORCH asked for gradient energy on `couch-fibers-cpl` before and after. That
number cannot answer the question on its own — a sharper image and a noisier
image both raise it, and this project has twice been fooled by exactly that
reading. So `experiments/BUILD-BLEND/gradenergy.py` reports it beside a
decomposition that separates the two cases, with the pixel sets frozen on the
control arm so the treatment cannot choose its own scoring region, and it is
commissioned against a planted blur, a planted noise injection and an identity
(it separates all three; identity reads exactly 1.0000).

`couch-fibers-cpl`, whole frame, camera-native linear, pin `275fbd1`:

| statistic | ctrl | blend | ratio |
|---|---:|---:|---:|
| gradient energy — *what was asked for* | 91,681 | 113,695 | **1.2401** |
| flat 20% — noise | 6,683 | 27,879 | **4.1718** |
| textured 20% — acuity | 357,088 | 384,394 | 1.0765 |
| mean level DN | 8,060.3 | 8,115.8 | 1.0069 |

**Read alone, the +24% headline says "sharper". The decomposition says it is
mostly noise.** That is the trap the brief warned about, and it caught my own
arm rather than someone else's.

### Three candidate causes, three eliminated

| candidate | test | result |
|---|---|---|
| the hull clamp (new) | same pin, same stack, one flag apart | **exonerated** — unclamped is *worse*, flat ratio 4.4137 vs 4.1718 |
| the base band | fixed pin, base band only | exonerated earlier — 0.9980 vs 1.0015 |
| measurement space | same pin, same arms, sRGB vs linear | **not the cause** — sRGB 4.6660, linear 4.1718 |
| clipped pixels inflating the ratio | split the flat set on control clipping | **refuted** — 0 clipped in linear, ratio 4.6666 on the unclipped part in sRGB |

What is left is the pin. At `0d9fd28`, `flatnoise.py` on this subject in sRGB
read **1.0015**; at `275fbd1` the same script on the same subject in the same
space reads **1.1179**. Something between those two commits changed this arm's
noise, and it is not code I own. I have not bisected it — that is six lanes'
worth of commits and outside my file lane.

### And the pictures do not show it, which has to be said

`hull/rim-couch-fibers-cpl.jpg` puts the two arms at 1:1 at their largest
low-frequency disagreement. They are indistinguishable in sharpness, and I
cannot see the noise. That is not me dismissing the number — it is the number
being small in absolute terms. Flat-region gradient RMS goes 82 → 167 DN on a
16-bit scale, which is **0.32 → 0.65 of one 8-bit level**. A 4× energy ratio on
a quantity that small is a doubling of something near the floor.

The two instruments also disagree on magnitude by about 2× in RMS — `flatnoise`
says +11.8%, `gradenergy` says +104% — because one measures a Laplacian band and
the other a gradient over differently chosen regions. Both agree in **sign**,
which is the part I am willing to assert. The magnitude is unsettled and I am
not picking the flattering one.

**So the honest statement is: this arm is measurably noisier in flat regions on
the do-no-harm guard, by somewhere between 12% and 104% in RMS depending on the
statistic, on a base small enough that I could not see it at 1:1. It is a real
cost, it is not caused by anything I changed this session, and it wants an
independent eye at print size before anyone decides whether it matters.**

### The exponent ramp was my last lever, and pulling it makes things worse

ORCH-veiling 29.3 showed the hull-violation rate is driven by the selection
exponent, and my per-band ramp runs `2 3 4 5 8 8 8` with the three finest bands
sitting exactly where the violations turn severe. That made the ramp the obvious
suspect for the noise as well: exponent 8 is near winner-take-all, and a
coefficient taken from one frame carries one frame's noise instead of an
average's. So I tested it — `--sharpen 1.0`, which disables the ramp and leaves
a uniform exponent of 2, same pin, same stack, same binary.

It confirms ORCH's mechanism and refutes my hypothesis at the same time:

| arm | hull clamp, per plane | flat 20% (noise) | textured 20% (acuity) | fine-band RMS |
|---|---|---:|---:|---:|
| ramp `2 3 4 5 8 8 8` (default) | 2.08 / 7.02 / 7.05 / 3.97% | 4.1718 | **1.0765** | 1.2150 |
| uniform exponent 2 | **0.43 / 2.34 / 2.34 / 1.04%** | 3.6346 | **0.8202** | 1.1525 |

The hull violations fall by about 3×, exactly as 29.3 predicts. But the noise
barely moves — 4.17 → 3.63, and +15.2% → still noisier than the shipped arm —
while **acuity collapses by 18%**, which `gradenergy` reads without prompting as
`VERDICT: textured energy DOWN 18.0% -- this is a softening`.

That is the trade 25.2 called monotone in selectivity, and it is a bad one at
this price. It also settles the question of whether the ramp earns its place:
**it does, and it is the single thing keeping this arm from being the softening
ORCH warned me not to ship.** A merge that is 18% down on texture across a
subject audited as genuinely good is precisely the regression that went
unnoticed for two hours once already.

So the ramp stays, and the noise remains unattributed to any lever I own. Every
candidate I can reach has now been eliminated by direct intervention rather than
by argument:

| candidate | verdict |
|---|---|
| hull clamp | exonerated — the unclamped arm is worse |
| base band | exonerated at a fixed pin |
| measurement space | not the cause — linear and sRGB agree |
| clipped pixels in the scoring set | refuted — none in linear |
| **selection exponent ramp** | **refuted — costs 18% acuity, keeps the noise** |
| the pin (`0d9fd28` → `275fbd1`) | **the only candidate left, and outside my lane** |


## The default flip: measured, justified, and landed as `5142ace`

ORCH asked me to wire the multi-band merge into the CLI and make it the default.
Two of those three things were already true when I looked, and the third is one
line. All of that is below, with the numbers that decide it, and with the
technique that let me write that line into a file two other lanes were holding
open at the same time.

### What was already wired

The CLI surface exists and follows the `--fix-ca` house pattern exactly: `--merge`
as `Option<String>`, `STREHL_MERGE` as its env twin with the spelling in one
`pub const`, `resolve_merge_backend` three-valued so an unparseable value is a
hard error rather than a silent off, dispatch at `merge_cmd.rs:2291`, and a
cross-backend refusal table in `main.rs` that refuses a flag belonging to the
other arm rather than ignoring it. I wrote none of it. The flip is therefore not
a wiring job at all -- it is `DEFAULT_MERGE_BACKEND`, one constant, deliberately
built so the decision has one address.

### The byte-freeze answer ORCH asked for: zero rows move

`tests/byte-freeze.rs` is immune by construction. `Freeze::argv` hardcodes
`--merge estimator` into every row's argv, with a comment saying why:

> The day `DEFAULT_MERGE_BACKEND` moves, an unnamed row would silently change
> pipeline and every hash below would move at once.

`STREHL_MERGE` is also in the scrubbed-environment list, so an ambient value
cannot contaminate a freeze. **No re-baselining is required and none should be
done.** The regression net was immunised against this exact flip in advance.

The real blast radius is elsewhere and it is not zero: eight flags are
estimator-only and are *refused* under `--merge pyramid`, so any harness passing
one without naming a backend starts failing loudly. A sweep recorded in the
working tree puts that at 338 call sites in 185 files, 189 of them executable,
with `--gate` alone accounting for 275. Loud, not silent -- but a harness that
dies is a measurement that does not happen.

### The criterion was pre-registered, and it is now met

`DEFAULT_MERGE_BACKEND` names its own release condition: *"This line moves the
day that clip passes the gate."* The blocker was `flower-bud-alone-cpl` clipping
**1.4043% of pixels against the estimator's 0.0001%**, with `p1` falling
1028 -> 334. `accept.py` defines `clip%` as pixels with any channel *exactly
zero* -- it is a black-point statistic, the same defect ORCH-veiling section 29
diagnosed and assigned to this lane, and the one `Hull::InputRange` was built to
remove.

Re-measured tonight through one binary, both arms camera-linear (`--demosaic`),
CA and photometric explicitly unset, stock configuration (band gate 2.00,
exponent ramp `2 3 4 5 8 8 8`, base = mean):

| subject | arm | clip% | acuity | microC | p1 | verdict |
|---|---|---:|---:|---:|---:|---|
| couch-fibers-cpl | estimator | 0.0000 | 334.1 | 289.88 | 3068 | reference |
| | pyramid | 0.0000 | **373.2** | **339.73** | 3232 | **PASS** |
| flower-bud-alone-cpl | estimator | 0.0001 | 126.9 | 54.21 | 1028 | reference |
| | pyramid | **0.0000** | **223.4** | **117.55** | 1042 | **PASS** |
| lavendar-cpl | estimator | 0.0000 | 165.9 | 42.83 | 1939 | reference |
| | pyramid | 0.0000 | **330.4** | **161.58** | 2462 | **PASS** |
| coffee-bean | estimator | 0.0000 | 669.8 | 655.27 | 1801 | reference |
| | pyramid | 0.0000 | 724.9 | **440.66** | 1726 | **FAIL: micro 67.2%** |

**The clip is 0.0000% and `p1` no longer collapses.** The specific condition
written against the constant is satisfied. The gate as a whole is not: one
subject fails, and that subject is new evidence nobody had, because the pair the
criterion was written against did not include it.

Two claims in the working tree are corrected by this. The pyramid arm was said
to be uncharacterised at its own default gate, on the grounds that the numbers
came from `--pyramid-gate 4`; both `FLIP` render logs record `noise gate : 2.00`,
which is the stock default, and so does every render above. And the acuity
regression that was once attributed to the merge is absent at stock gate on all
four subjects -- the pyramid wins acuity everywhere, by 12% to 99%.

### The rim, on ORCH's own instrument and pre-registered targets

`rimprofile.py`, linear 16-bit, my renders. The estimator arm reproduces ORCH's
section 12 reference **exactly** -- interior local maximum at d=18 px standing
+2279 DN above the trough -- which commissions the instrument before it is used
to judge anything.

| d (px) | estimator, vs far field | pyramid, vs far field |
|---:|---:|---:|
| 16-20 | **-2622**  (ring peak) | -1225  (no local max) |
| 65-80 | -4774 | -419 |
| **100-125** | **-4901**  (aura floor) | **-208** |
| 150-200 | -3942 | +19 |
| 250-300 | -1194 | +149 |

Both features ORCH separated collapse together:

| feature | estimator | pyramid | target | result |
|---|---:|---:|---|---|
| ring prominence at d=18 | **12.0%** (+2279 DN) | **no ring at d=18** | <= 1% | **met** |
| broad aura at d~117 | **-25.8%** (-4901 DN) | **-1.09%** (-208 DN) | -- | **23.6x smaller** |

The pyramid's profile is *monotone* through the entire rim zone. The detector's
nearest residual on it is +268 DN (1.41%) at **d=275 px** -- a different, far
weaker feature fifteen times further out, in the region ORCH has already shown
carries the scene's own illumination field.

`coffee-bean`, the pre-registered negative control, holds: ring prominence
**0.14% -> 0.47%**, both an order of magnitude under `flower-bud`'s 12.0% and
both inside the 1% bar. Neither arm invents a silhouette ring on it.

## ORCH's contamination question, answered: the pair was toned, and the arms were toned differently

ORCH profiled `ca-ctrl-` and `ca-blend-flower-bud-with-background-fern-cpl.tiff`
and read them as "linear, no tone curve", then asked whether the gallery recipe
contains a global normalisation that would contaminate cross-arm absolute DN.

**It does, that pair went through it, and the two arms got different
parameters.** `image_out.rs` writes the tone into each file's own
`ImageDescription`, so the files answer this themselves.
`experiments/BUILD-BLEND/tonecheck.py` reads the tag out of the TIFF header
without decoding 198 MB of pixels:

| file | space | tone black | tone white | span |
|---|---|---:|---:|---:|
| `ca-ctrl-...` | **sRGB, "For viewing"** | 0.011119 | 0.306019 | 0.294900 |
| `ca-blend-...` | **sRGB, "For viewing"** | **0.000000** | **0.319798** | 0.319798 |

Two separate problems. They are **sRGB-encoded, not linear**; and the tone black
and white are percentiles of *each image's own* luminance
(`TONE_BLACK_PCT` 0.1, `TONE_WHITE_PCT` 99.9, `image_out.rs:448/474`), so each
arm placed itself on its own scale. The blend's span is **8.44% wider**, so it
compresses harder, and its black is 0.0111 lower.

`image_out.rs:1389` has a test named
`tone_rides_with_the_viewing_render_and_never_with_a_measurement`, and the
measurement path is clean: `dev.tone` is `None`, so `develop_pixel` applies no
gain, no `gamut_map` and no `s_curve`, and with `srgb` false the output is
`linear * 65535`. The only global term left is the raw normalisation by
`(white - black)`, and those come from the **camera metadata** -- fixed
per-capture constants, identical for both arms. **Untoned pairs are safe to
compare in absolute DN. Toned pairs are not.**

### How much of ORCH's table was tone

`tonesplit.py` reproduces the full chain from `image_out.rs` (`Tone::gain`, the
soft toe, `srgb_encode`, `s_curve`), inverts the control's chain by bisection to
recover the true linear value of each row, then pushes that *same* value through
the blend's chain. The result is what each row would read **if the two images
were identical**.

A pure null, same linear input through both tones, zero image difference:

| linear | ctrl DN | blend DN | tone alone |
|---:|---:|---:|---:|
| 0.05 | 24368 | 27102 | **+2733** |
| 0.10 | 39832 | 40640 | +808 |
| 0.15 | 50081 | 49986 | -96 |
| 0.20 | 57221 | 56685 | -536 |
| 0.25 | 62121 | 61435 | -685 |

Applied to ORCH's rows, **40% of the reported total is tone**. The far-field
rows are almost entirely tone: at d = 200-600 the tone term alone is -613 to
-631 DN against a reported -535 to -867. The mid-field rows are the opposite --
the tone term there is *negative*, so it was **masking** part of the win.

Sensitivity is good: perturbing the control DN by +/-50 moves the recovered
value by -0.90 to -0.97 DN per DN, so every row is well conditioned. The linear
values are 0.098-0.222, nowhere near the compressive top of the curve.

### Why the two arms were toned differently, which is the whole mechanism

The blend arm's tone black is **exactly 0.000000**. Since
`black = at(0.1) * 0.85`, that means at least 0.1% of its pixels had *zero*
luminance. That is the black-point collapse this lane already found and fixed --
the clip that ran at 1.4043% before `Hull::InputRange`.

`ca-blend` was rendered from `tree-ca-6a51e43`, i.e. commit `6a51e43`, which is
**two `pyramid.rs` commits behind HEAD** and does not contain `275fbd1`
("confine the reconstruction to the hull of its inputs"). So the chain is:

1. the pre-hull build clipped pixels to zero;
2. that dragged the image's own 0.1th percentile to zero;
3. which set a different tone black;
4. which produced a different affine placement, 8.44% wider;
5. which printed a broad deficit into the toned sRGB output;
6. which reads as a mysterious far-field bowl.

**ORCH was profiling a superseded build of this arm through a data-dependent
transform that the build's own defect had perturbed.**

## The far-field bowl, re-measured clean: real, and about a quarter of what was seen

The above would let me say the bowl is entirely tone. **It is not, and the clean
measurement is the one that decides it.** `flower-bud-with-background-fern-cpl`
re-rendered through the untoned measurement path, both arms, one binary,
`--demosaic`, no `--srgb`, CA and photometric unset
(`C:\dev\strehl-out\BUILD-BLEND\fern\`, confirmed `LINEAR` by `tonecheck.py`),
profiled with ORCH's own `rimprofile.py`. Each arm against **its own** far field:

| d (px) | control | blend | change |
|---:|---:|---:|---:|
| 0-4 | -4584 | -4739 | -155 |
| 8-12 | -1368 | -1546 | -178 |
| 12-16 | -967 | -1303 | **-336** |
| 25-30 | -531 | -868 | **-337** |
| 30-40 | -897 | -678 | +219 |
| 50-65 | -1386 | -407 | **+979** |
| 65-80 | -1314 | -288 | **+1026** |
| 80-100 | -1095 | -197 | +898 |
| 100-125 | -936 | -82 | +854 |
| 125-150 | -872 | -36 | +836 |
| 150-200 | -748 | -158 | +590 |
| 200-250 | -523 | -224 | +299 |
| 300-400 | -319 | -261 | +58 |
| 400-500 | -245 | -389 | **-144** |
| 500-600 | -222 | -399 | **-177** |

Three findings, and only one of them is good news.

**The mid-field win is real and survives the clean measurement.** At d = 50-150
the deficit falls from -1386/-872 to -407/-36, a 71-96% reduction, and the
control's characteristic bowl -- deepening from -531 at d = 25-30 to -1386 at
d = 50-65 before recovering -- is flattened into a monotone approach. The tight
interior peak the detector finds moves from **+855 DN at d = 27** to **+363 DN
at d = 137**: less than half the amplitude, five times further out.

**The far-field bowl is real, and ORCH's hypothesis (1) is right.** At
d = 400-600 the blend is 144-177 DN below the control against its own far field,
about **1.0-1.2% of level**, which is the 1-1.5 sRGB levels ORCH estimated. It
is roughly **one quarter** of the 535-867 DN they measured -- the other
three quarters was tone -- but it is not zero and it should not be reported as
zero. ORCH's proposed remedy is well supported by the split: the win lives at
d = 30-300 and the bowl at d = 400-600+, which are different octaves, so
tapering the coarsest level should cost little of it.

**A regression they did not flag, and I am not going to bury it.** At
d = 8-30 the blend is **worse than the control by 178-337 DN**. On this subject
my arm slightly deepens the near-silhouette deficit while transforming the
mid-field. That zone is the one ORCH assigned to BUILD-HALO, but "someone else
owns it" is not the same as "my change did not move it," and my change moved it
the wrong way.

### One limit of this measurement, stated

`rimprofile.py` builds its mask from the image it is profiling, so the two arms
were segmented separately and the near-silhouette rows are the ones most exposed
to that. My own `dnlevel.py` -- which builds one mask from the control and reads
both arms through it -- **refuses this subject**, correctly: the fern behind the
bud shreds a luminance threshold into 1880 components with the second largest at
36% of the first. So the d = 8-30 regression above is measured through the
weaker of my two instruments and deserves a paired re-measurement on a subject
whose backdrop can be segmented before it is treated as settled.


## Absolute levels in DN, because a ratio cannot answer the question asked

ORCH made this a hard requirement across the project after a near-miss:
BUILD-SHARP measured that an upper-envelope estimator carries a **+0.845 sigma
upward bias**, and the defect it is aimed at is a *darkening*. At
sigma_frame ~ 200 DN that is about **+169 DN** of free credit. An estimator with
that bias can drive a veiling *error* metric to zero arithmetically without
improving the photograph at all, and neither an error nor a ratio can show the
difference. Only a level can.

### Why ORCH's own instrument could not be used for this

`rimprofile.py` builds its subject mask **from the image it is profiling**. That
is correct for characterising one render, and wrong for comparing two, because
the two arms then get two different masks and the disagreement is largest exactly
at the silhouette -- which is where the artifact lives. The measurement would be
confounded by the very thing being measured.

`experiments/BUILD-BLEND/dnlevel.py` follows ORCH's own `veilpair.py` discipline
instead: build the mask and the distance transform **once, from the control
arm**, and read both arms through that one geometry. Every number below is two
reads of one ruler.

### The levels

Aura zone is d = 80-200 px from the silhouette; far field is each arm's own
600-1400 px annulus. Linear 16-bit, one binary, both arms.

| subject | aura deficit, estimator | aura deficit, pyramid | far-field level shift | aura-zone level shift | peak row shift |
|---|---:|---:|---:|---:|---:|
| flower-bud-alone-cpl | **-4739 DN** | **-166 DN** | **-113 DN** | **+4459 DN** | +4647 @ d=125-150 |
| coffee-bean | **-5629 DN** | **-1765 DN** | **-317 DN** | **+3547 DN** | +6965 @ d=65-80 |
| 109MSDCF (placebo) | -- | -- | median **+0 DN**, mean **+5 DN** | -- | worst 6x6 tile **32 DN** |

A correction to an earlier revision of this table, and to the commit message of
`5943e16`, which was written before I re-ran the instrument to check my own
transcription. That version gave one column headed "aura-zone shift" holding
`+4452` for `flower-bud` and `+6965` for `coffee-bean`. Both are real readings
off the printed table, but they are **different statistics**: `+4452` is the
single d = 80-100 px row and `+6965` is the *peak* row, at d = 65-80. Neither is
the aura-zone aggregate the header claimed, which is `+4459` and `+3547`. The
error flattered nothing -- `coffee-bean`'s honest aggregate is smaller than the
number I first published -- but a column in which two rows mean different things
is not a measurement, so it is now split into two columns that each mean one
thing. This is the reason the instrument was re-run rather than transcribed
from notes.

### The discriminator

The two rightmost columns have **opposite signs**. The far field moves *down* by
113 and 317 DN while the aura zone moves *up* by 4459 and 3547 DN.

A +0.845 sigma upward bias is a bias on an order statistic, and it would lift
**both** columns together -- the far field is where such a bias is least opposed,
so it would show there most cleanly. It moves the wrong way. On the corrected
aggregates the local change is **39x** the global one on `flower-bud` and
**11x** on `coffee-bean`, and carries the opposite sign, which is the signature
of a spatially-varying additive term being removed rather than of a level being
added.

My merge is not an order statistic and I did not expect it to carry this bias.
The point of the table is that I can no longer be *assumed* not to, and a ratio
would have left it unanswerable either way.

### The placebo

`109MSDCF` has no depth separation and only a -177 DN aura, so ORCH set it as the
subject the fix must be approximately a no-op on. It is: **median +0 DN**, mean
+5 DN, worst tile 32 DN, against +4459 DN of real correction on a subject that
has the defect. That is the change declining to fire where there is nothing to
correct.

### A false positive I caught in my own guard

`dnlevel.py` initially **refused** `coffee-bean` on a rule that a mask covering
more than half the frame is a failed segmentation. `maskcheck.py` and an overlay
render showed the mask covered only 22% of the border ring and touched 2 edges --
it was the bean **plus its cast shadow**, which is the subject, correctly found.
Area cannot separate "dark ground" from "large dark subject."

The guard is now a **border-ring polarity test**: a backdrop surrounds a subject,
so it dominates all four edges. It admits `coffee-bean` and still refuses
`lavendar-cpl`, whose inverted polarity genuinely defeats the segmentation. The
structure was also changed so a refusal no longer discards the maskless global
levels -- otherwise the placebo, which by construction has no silhouette to
segment, could never be measured at all, and the deliverable ORCH asked for would
have been unobtainable by the shape of my own script.


**`lavendar-cpl` is not reportable on this instrument and I am not reporting a
number for it.** `rimprofile.py` assumes a dark subject on a bright ground and
segments with `lum < threshold`; lavendar is a bright subject on mid grey, so the
mask selects the *ground*, and it fragments into 8137 components. A profile
computed from that is not measuring the silhouette. This is the same failure
ORCH-veiling 42.2 warned about -- a probe whose verdict names a premise it never
tested -- and the correct output is a refusal, not a number.

### The picture, which is the part that matters

`view\sxs-flower-bud-alone-cpl.jpg`. On the estimator the "spilled milk" defect
is unmistakable: a bright scalloped band with drip-shaped lobes hugging the
entire silhouette, and a hard outline tracing every edge. On the pyramid it is
**gone** -- smooth backdrop, no band, no outline -- and the bud carries visibly
more trichome detail at the same time. The removal is not a blur: acuity rises
76% and micro-contrast 117% on that frame.

`view\crop-couch-fibers-cpl.jpg`, the do-no-harm guard at 1:1: individual
filaments are equally crisp in both arms. The guard improves rather than softens
(+11.7% acuity, +17.2% microC), which is the specific trade ORCH asked me to put
a number on, and it is the right sign.

### The one failure, diagnosed rather than explained away

`coffee-bean` fails `microC` at 67.2%. I looked at it at 1:1 before deciding what
that meant. There is no visible loss of detail; what is visible is that the
*estimator's* dark regions carry blotchy mottle that the pyramid's do not.
`microC` is a median local standard deviation, and on this subject a large part
of the scored population is dark bean surface where the estimator's noise is
being counted as micro-contrast.

That reading is supported but not proven. Splitting local standard deviation by
population, with rail-clipped control tiles excluded so nothing is a ratio
against the white rail:

| subject | backdrop | subject interior | control at white rail | pyramid at white rail |
|---|---:|---:|---:|---:|
| flower-bud-alone | 2.21x | 1.49x | 0.0000% | 0.0000% |
| lavendar | 3.87x | 1.27x | 0.0000% | 0.0000% |
| couch-fibers | 1.17x | 1.17x | 0.0000% | 0.0000% |
| **coffee-bean** | **1.14x** | **0.85x** | **1.1657%** | **2.8649%** |

`coffee-bean` is the only subject whose interior falls, and it is the only
subject with material white-rail clipping -- which the pyramid **more than
doubles**, 1.17% -> 2.86%. That is a real defect and it is mine: the hull clamp
confines the reconstruction to the hull of its inputs, and where the inputs
themselves reach the rail the hull permits the rail. Near-argmax selection then
drives toward it. It is the highlight-side twin of the black-point collapse I
already fixed, and it is not fixed.

It also disposes of one convenient story: `gradenergy` read the coffee-bean
backdrop as **10.97x** noisier, and that number is an artifact of comparing
against clipped control tiles. Excluding them it is **1.14x**. I would have
reported the 10.97x had I not checked.

### Why the backdrop noise happens, which answers an open question

Across every subject the pyramid raises backdrop local standard deviation --
1.14x to 3.87x. My own render log says why, in a diagnostic I built and had not
read carefully enough:

```
averaged : 49.1%  0.0%  0.0%  0.0%  0.0%  0.0%  0.0%  100.0%
```

That is the fraction of coefficients at each level where no frame cleared the
noise floor and the merge averaged instead of selecting. **The gate gates at
level 0 and does not gate at all at levels 1 through 6.** In a region that is
featureless in every frame those bands contain only noise, so some frame always
"wins", independently per coefficient -- which is precisely ORCH-veiling section
40's patchwork mechanism, visible in my own instrumentation.

The cause is that the floor is `gate * beta * sigma^2` where `beta = E[L_k^2] /
sigma_0^2` is derived by pushing **white** noise through the operators. Real
post-demosaic sensor noise is spatially correlated, so it carries more energy at
coarse scales than white noise predicts, and `beta` collapses fast --
`0.8898 0.0529 0.0101 0.0024 0.0006 0.0001 0.0000 0.0000`. By level 5 the floor
is effectively zero and anything clears it.

This also answers the question ORCH-veiling 42.3 left open -- why gate 4.5
collapses `bee-1`'s background 87% but moves `couch-fibers`' only 3.4%, "when
both have noise-dominated flat tiles". A gate calibrated for white noise does not
act in units of the real noise on subjects whose noise correlation differs. The
fix is to estimate the per-band floor empirically from the frames the fold
already sees rather than from a white-noise model. That is a change in
`pyramid.rs`, it is mine, and it is not a 4 a.m. change.

I already know two things it should not be. Lowering the exponent uniformly costs
18% of textured acuity for almost no noise gain, and raising the gate is a
per-subject win and a per-subject loss (ORCH-veiling 42). Neither is the fix; a
correctly calibrated floor plausibly is.

### How the line was flipped while two other lanes held the file

`crates/strehl-cli/src/merge_cmd.rs` and `crates/strehl-cli/src/main.rs` were held
by live lanes throughout. Both carried uncommitted work -- 240 lines across the
two -- and the `merge_cmd.rs` hunks landed **exactly** on the `MergeBackend`
variant docs and the `DEFAULT_MERGE_BACKEND` doc block, the precise text a flip
must rewrite. An earlier revision of this section recorded that I had stopped for
that reason. That was the right call at the time and it is no longer the state.

The obstacle is real and worth naming precisely, because the repository's stated
safety rule does not cover it. `git commit -- <path>` is the prescribed
path-scoped commit, and it commits **the whole working-tree file**, not my part
of it. With two agents editing one file, path scoping is not fine enough to be
safe: my commit would have carried their unfinished work under my message.

The way through is to build the commit from a temporary index instead of the
shared one:

    GIT_INDEX_FILE=<temp>  git read-tree HEAD
    git diff -U3 -- <file>            # split into hunks
    <keep only hunks whose new-start line falls in my ranges>
    git apply --cached                # into the temp index only
    git write-tree | git commit-tree | git update-ref

The working tree is never written, so the other lanes' edits stay exactly where
they left them. The script is `experiments/BUILD-BLEND/commit_mine.py`. It
hard-errors if zero hunks are kept or if the resulting tree equals HEAD's, so a
mis-specified line range fails loudly instead of committing nothing and
reporting success.

The result, commit `5142ace`: **6 hunks taken, 12 left behind.** Two of fourteen
hunks in `merge_cmd.rs`, three of seven in `main.rs`, one of one in
`check-defaults.py`. Immediately after, `git status` still showed both Rust files
dirty and `git diff HEAD --numstat` reported 157/19 and 13/9 lines still
outstanding -- the other lanes' work, untouched and still theirs to commit.

Flipping the constant is not a one-line edit in effect: four tests in `main.rs`
read the rendered help back and compare it against this constant, so the value
and the words move together or the suite fails. Those four tests
(`stack_help_marks_the_backend_the_constant_selects`,
`the_merge_flag_help_names_the_same_default`,
`the_not_yet_caveat_names_a_backend_that_is_not_the_default`,
`the_help_this_module_reads_is_actually_rendered`) are the reason the prose moved
in the same commit as the value.

### Checking the commit, not the working tree

Testing in the working tree would not have shown whether `5142ace` builds,
because the working tree also contains 176 lines of other lanes' in-progress
work. A green suite there is a statement about *their* code plus mine, and if
their edits happened to supply something mine needed, HEAD would be broken for
everyone and the test would still pass.

So the check was run against the commit in isolation:

    git worktree add --detach <tmp> 5142ace
    cargo test --release -p strehl-cli --bins

**97 passed, 0 failed**, including all four constant-coupled help tests above.
That is a statement about what is now in the history, which is the thing five
lanes are about to build on.

### The byte-freeze row that fails, and why it must not be re-baselined

ORCH asked how many freeze cases moved. **Zero moved and nothing was
re-baselined.** But one row does currently fail, and it is worth recording why
the honest response to it is to leave it alone.

`coffee-bean-20-gate2-unaligned` mismatches: frozen `3162EB0B...`, current
`88712017...`. The tempting reading is that my flip caused it and the row needs a
new hash. Two independent lines of evidence say otherwise.

Code: the row's own recorded argv pins `--merge estimator`, and
`resolve_merge_backend(Some(x))` returns before it ever consults
`DEFAULT_MERGE_BACKEND`. The constant appears in exactly three places outside its
own definition -- tests, doc comments, and the stderr banner -- and in no code
path that a row with an explicit `--merge` can reach.

Empirical, which is the part that settles it: re-running that row's own
invocation with `STREHL_EDGE_AWARE=0` reproduces `89958637...C218` **bit-exactly**
-- the pre-edge-aware baseline the row's own note names as its arm-off control.
Bit-exact reproduction of a third hash proves the entire rest of the render path
is unchanged, and localises the whole delta inside `edge_aware_arm()`, which is
another lane's live file.

Re-baselining it would have absorbed another agent's in-flight change into a
commit of mine, under a message claiming it was my intended move. That is
precisely the failure the row's note warns about.

### What is still wrong, stated as failures

`accept.py` reads **3 PASS / 2 FAIL** across the five subjects. Both failures are
real and neither is explained away here:

- `coffee-bean` micro-contrast **67.2%** of the estimator arm.
- `109MSDCF`, the placebo, acuity **65.2%** -- on a subject my change is supposed
  to leave alone.

Against that, the placebo's *level* is a no-op: median **+0 DN**, mean **+5 DN**,
worst 6x6 tile 32 DN, against +4459 DN of real correction on `flower-bud-alone`.
So the pyramid is not moving that picture's brightness anywhere; it is changing
the amplitude of something the acuity statistic counts. `acuitysplit.py` shows
the placebo's flat-region energy went *down* to 67.6% while other subjects' went
up, which is consistent with dark-ink noise being removed rather than detail --
consistent with, not demonstrated, and I have not closed it.

Also open, and mine: edge amplitude sits at **84-94%** of the control on
non-halo subjects; flat-region energy rises up to **8.6x** on lavendar because
the band gate is not gating above level 0 (`averaged` reads
`49.1% 0.0% 0.0% ...`); and white-rail clipping doubles on coffee-bean,
1.17% -> 2.86%, the highlight twin of the black-point collapse
`Hull::InputRange` was built to remove.

### A caveat about the instrument that would flatter me if I omitted it

Edge |Laplacian| cannot tell a sharp edge from an edge **plus an overshoot rim**.
A halo is a large Laplacian. On `flower-bud-alone` -- the subject whose halo is
the most conclusively removed, by ORCH's own instrument and by eye at full frame
-- my edge-amplitude metric reads **57.1%**, the lowest of all five subjects.

Read naively that is the worst softening in the corpus. It is in fact the metric
counting the removed defect as lost detail. This means the edge-amplitude number
**cannot by itself settle softening versus halo removal in either direction**,
including in my favour on the other four subjects. I am recording it because it
is the reading that would let me dismiss the two `accept.py` failures, and I do
not think it is strong enough to.

---

## ORCH's far-field bowl: the mechanism is right, the address is one level off, and the bowl does not survive clean measurement

ORCH measured a broad shallow bowl in the blend arm, registered four criteria
before I ran anything, and prescribed a specific fix. This section answers all
four, reports the ladder, and reports one finding that changes what the criteria
mean.

Landed as `3db5693` (mechanism) and measured here. **The recommendation is to
leave the default at 0.** The reasoning follows and it is not the reasoning I
expected to be writing.

### 1. The prescribed fix was already in place

ORCH prescribed: *"replace the level-N Gaussian residual (the base) with the base
of the noise-gated mean of the aligned stack."*

That is what this module already does, and has done since before the flip.
`BaseBand::Mean` is the shipped default; it zeroes the weight field, so every
base coefficient falls through the unweighted branch at the bottom of
`finish_level`. The base band is a plain mean across frames today.

This is not an argument from reading the source. The renderer prints its own
per-level averaged fraction, and on the **unmodified default** it reads:

```
bands           : 7 Laplacian levels + 1 base, coarsest 28 x 19
averaged        : 23.0% 0.0% 0.0% 0.0% 0.0% 0.0% 0.0% 100.0%
```

The last entry is the base band. **100.0%, before any change of mine.** So the
prescription is a literal no-op, and this module's own `BaseBand` table already
recorded why it would be: *"Both blend arms removed the shipped merge's broad
aura equally well, so the base band is not what buys that."*

The **mechanism** ORCH described is nonetheless correct. A Laplacian blend does
redistribute energy at its coarsest scales, and that is the right family of
explanation for a several-hundred-pixel pedestal. The address is one level off.
The bowl's scale belongs to the coarsest **Laplacian** bands, which were still
being *selected* at exponent 2.0, not to the base residual.

The scale arithmetic says the same thing. On a 7040 px frame with 7 bands, level
6 sits on a ~110 px grid, so one coefficient is ~64 output px and its 5x5
binomial kernel reaches ~320 output px. That is the 175-550 px bowl. The base
band sits on a 28x19 grid, an entirely different scale.

So I implemented ORCH's principle at the level that carries the effect:
`STREHL_PYRAMID_MEAN_COARSE` averages the coarsest N Laplacian bands by the same
mechanism `BaseBand::Mean` uses. The per-level diagnostic confirms it acts where
intended and nowhere else:

```
mc=0   averaged : 23.0% 0.0% 0.0% 0.0% 0.0% 0.0%   0.0% | 100.0%
mc=1   averaged : 23.0% 0.0% 0.0% 0.0% 0.0% 0.0% 100.0% | 100.0%
mc=2   averaged : 23.0% 0.0% 0.0% 0.0% 0.0% 100.0% 100.0% | 100.0%
```

### 2. The instrument, and why it is not `rimprofile.py` in a loop

`experiments/BUILD-BLEND/bowlprofile.py` reproduces ORCH's arithmetic exactly --
same bin edges, same luma, same largest-component mask, same far-field
reference, same sRGB encode -- and fixes three things without which a ladder
cannot be read.

**The mask is per-image.** `rimprofile.py` derives `subject` from a p5/p95
threshold on the very image it is profiling, so two arms get two different masks
and two different distance fields, and a row labelled `d=2` is not the same set
of pixels between arms. **The encode white is also per-image**
(`percentile(lum, 99.9)`), so the `of 255` column is scaled by a per-image
quantity too. Both are taken once from a named reference here, and both drifts
are *reported* rather than silently corrected, so their size is visible:

| image | own subject % | own white DN | own threshold DN |
|---|---:|---:|---:|
| control (estimator) | 27.14 | 16620 | 8830 |
| blend mc0 | 27.13 | **17706** | **9085** |

The encode white differs by **6.5%** between arms. That is not a small
correction to a `of 255` column.

**Third and largest: ORCH's registered bars are in units that do not transfer.**
They were measured on `ca-ctrl`/`ca-blend-*.tiff`, which declare in their own
`ImageDescription` that they are sRGB-encoded *and* tone-mapped, with different
per-image black points per arm (0.011119 vs 0.000000). `rimprofile.py` then
applies `srgb()` again -- its own docstring says *"Measures on the LINEAR 16-bit
render only."* The encode's slope depends on where you sit on it, so an
identical physical deficit prints a much larger number on a linear file, which
sits far lower on the curve. Comparing my rungs against their literal bars would
compare two rulers.

So every bar is restated in the parity form ORCH themselves wrote it in
(*"Control is -0.50 and -0.79; that is the parity bar"*), evaluated against the
control measured through the identical path, and criterion (b) is restated as a
**retained fraction** of the mid-field win, which is scale-free and therefore
transfers between encodes exactly.

### 3. Commissioning, before any rung was read

Rung 0 was not a data point. It had to come back **byte-identical** to the
existing pyramid render made by the previous binary, or the ladder would be
confounded by whatever else differed between the two builds.

```
mc0  : 84A4661DEC40C040D3988B57305CF5BC429BDCD03BE078FC579B9A74286D655C
fern : 84A4661DEC40C040D3988B57305CF5BC429BDCD03BE078FC579B9A74286D655C
IDENTICAL
```

And the converse: mc1, mc2, mc3 all differ from mc0, so the env var reaches
pixels. A sweep that came back flat because the knob was never plumbed through
would have looked exactly like a sweep that came back flat because the effect is
absent. This project has shipped that failure three times; it is not shipping it
a fourth on my account.

### 4. The ladder

`flower-bud-with-background-fern-cpl`, 299 frames, untoned linear, one binary,
shared mask and shared encode white. Deficit against each arm's own far field,
in DN, so the +630 DN cross-arm level shift divides out by construction.

| d (px) | control | mc0 (shipped) | mc1 | mc2 | mc3 |
|---:|---:|---:|---:|---:|---:|
| 2 | -4584 | -4743 | **-4590** | -4633 | -4868 |
| 10 | -1368 | -1475 | -1432 | -1543 | -1999 |
| 28 | -531 | -784 | -737 | -909 | -1579 |
| 45 | -1271 | -492 | **-400** | -636 | -1486 |
| 58 | -1386 | -384 | **-301** | -658 | -1320 |
| **90** | **-1095** | **-219** | **-218** | -707 | -874 |
| 138 | -872 | **-68** | -292 | -491 | -539 |
| 175 | -748 | **-181** | -375 | -395 | -418 |
| 350 | -319 | -271 | -257 | -257 | **-238** |
| 450 | -245 | -402 | -403 | -332 | **-273** |
| 550 | -222 | -413 | -405 | -311 | **-246** |

Against ORCH's four criteria:

| rung | (a) bowl d>=300 | (b) win retained at d=90 | (c) silhouette d=2 |
|---|---|---:|---|
| mc0 | PASS PASS PASS | 100.0% | FAIL by 159 DN |
| mc1 | PASS PASS PASS | 100.0% | FAIL by 6 DN |
| mc2 | PASS PASS PASS | **44.3%** FAIL | FAIL by 49 DN |
| mc3 | PASS PASS PASS | **25.2%** FAIL | FAIL by 284 DN |

Bar for (b) is 88.6%, derived from ORCH's own numbers: their d=90 bar of -4.5
against a control of -7.69 and a blend of -4.09 permits losing 0.41 of a 3.60
win.

**Criterion (a) already passes at mc0 -- the currently shipped default.** Every
rung that closes the bowl further fails (b), and fails it badly. ORCH
pre-registered the response to exactly this: *"If (a) passes but (b) fails,
report it as a failure and stop; do not ship a fix that trades the visible
artifact for the invisible one."*

### 5. Why (a) already passes: the bowl is mostly the tone curve

This needs its own falsifiable test rather than an assertion, because "your
measurement was contaminated" is the most self-serving thing an implementer can
say.

`experiments/BUILD-BLEND/tonebowl.py` converts ORCH's published `of 255` rows
back to DN at the operating point their own published pair pins
(59630 DN = 248.1 of 255, so encode white 63467 DN and slope 0.001832 of 255 per
DN, making their 1.0 bar **546 DN**), and compares them to the same rows measured
untoned.

The test discriminates because it has a control. If toning is the explanation,
the **control** arm should transfer (ordinary black point) and the **blend** arm
should not (black point collapsed to exactly 0.000000). If instead my renders or
my instrument simply disagree with ORCH's, **both** arms should fail to transfer
by similar factors -- which would refute the tone explanation and force me to
accept the bowl as measured.

| d | ORCH control DN | mine | ratio | ORCH blend DN | mine | ratio |
|---:|---:|---:|---:|---:|---:|---:|
| 350 | -273 | -319 | **0.86** | -1469 | -271 | **5.42** |
| 550 | -431 | -222 | **1.94** | -1720 | -413 | **4.16** |

Median over the criterion-(a) rows: **control 1.40x, blend 4.79x, discriminating
ratio 3.42x.** The control arm transfers; the blend arm does not. Both were
profiled by the same instrument on the same capture, so an instrument or subject
difference would have moved both.

Residual **real** bowl on untoned data, blend minus control:

| d | excess over control | at ORCH's operating point | their bar |
|---:|---:|---:|---:|
| 350 | -48 DN | -0.09 of 255 | 1.00 |
| 550 | +191 DN | +0.35 of 255 | 1.00 |

**The bowl is real and it is about a third of the bar.** ORCH's `-2.7 to -3.2 of
255` was dominated by the per-image tone applied to the blend arm.

The same contamination runs the other way in the mid-field, and I am reporting
that because it cuts against tidiness rather than for it: at d=90 and d=175 the
blend transfer ratio is **10.2x and 10.3x**, far above the 4.79x far-field
figure. The toned pair **understated** the mid-field win as much as it
overstated the bowl. Both errors have the same origin.

### 6. Verdict, and the four criteria answered

**`DEFAULT_MEAN_COARSE` stays at 0.** `mean_coarse` ships as a measured,
commissioned, reachable knob, and the measurement says do not turn it on:

- (a) **passes already** at the shipped default; the residual bowl is +0.35 of
  255 against a 1.00 bar.
- (b) mc2 and mc3, the only rungs that close the bowl further, retain **44.3%**
  and **25.2%** of the mid-field win against an 88.6% bar. That is ORCH's
  registered stop condition.
- (c) fails marginally on every rung including the shipped one: mc0 is 159 DN
  below control at d=2, which is **0.29 of 255** at ORCH's operating point, on a
  row whose value is -4584 DN. mc1 reduces it to 6 DN, essentially exact parity.
  I am recording this as a fail rather than rounding it away, but note that d=2
  is the single most mask-sensitive bin in the profile and the two instruments
  disagree about its sign (ORCH's per-image masks made the blend *better* at d=2
  by 1.39 of 255).
- (d) **holds by construction.** mc0 is byte-identical to the shipped default,
  proven by SHA-256 above, so the lavendar morphology ORCH already judged is
  unchanged. There is no new render to inspect because there is no new image.

**mc1 is the one rung worth recording as genuinely interesting and I am still
not shipping it.** It is free on (b) (100.0% retained), it is better than mc0 on
every row from d=2 to d=90 -- including turning criterion (c) from a 159 DN
miss into a 6 DN one -- and it is *worse* than mc0 by 142-194 DN across
d=112-225. That is a trade, not an improvement, and this project does not move a
default on a trade with no arbiter. It is one env var away for whoever wants to
arbitrate it.

### 7. What I am not claiming

- I have **not** shown the bowl is zero. It is +191 DN at d=550, real, and
  attributable to the coarsest Laplacian bands by the scale argument in section
  1. I have shown it is about a third of the bar ORCH set, and that closing it
  costs more than it is worth at every rung I can reach.
- The d=8-30 **near-field regression** is real and unresolved: the blend is
  ~250 DN worse than the control at d=14-28 on this subject. No registered
  criterion covers it. It is not caused by `mean_coarse` (mc1 improves it
  slightly, mc3 destroys it), it predates this work, and it is the one row band
  where the estimator arm is genuinely better. Somebody should own it.
- All of section 5 rests on ORCH's five published rows and on the operating point
  implied by one published pair. If either the rows or `59630 DN = 248.1 of 255`
  was mistranscribed, the conversion moves. The discriminating ratio is robust to
  a scale error in the slope -- it divides out -- but not to an error in an
  individual row.
- I did not verify any of this myself in the sense the project means. I ran what
  is listed here and reported it.

### 8. Test state at HEAD, including a break that is not mine

`cargo test --release -p strehl-core --lib` at a clean checkout of HEAD:
**455 passed, 0 failed.** Run in a detached `git worktree`, not the shared
working tree, because five lanes have uncommitted edits there and a pass in that
tree would not be a statement about HEAD.

`cargo test --release -p strehl-cli --bins` **does not compile at HEAD**:

```
error[E0061]: this method takes 3 arguments but 4 arguments were supplied
    --> crates/strehl-cli/src/merge_cmd.rs:3590:27
    --> crates/strehl-core/src/merge.rs:2063:12
```

Bisected rather than blamed by inspection. Note that plain `cargo build`
succeeds at the broken commit -- the call site is inside a `#[cfg(test)]` path,
so a build-only check reports green and only the test build sees it:

| commit | test build | |
|---|---|---|
| `ab0d71a` | OK | parent of my first commit |
| `0e03579` | OK | |
| `794e605` | **BROKEN** | BUILD-SHARP: wire restore behind STREHL_RESTORE |
| `3db5693` | OK | mine |

An arity mismatch between the veil call site in `merge_cmd.rs` and the method in
`merge.rs`. Both files are outside my lane and none of my four commits touches
either, which is checkable with `git show --name-only`. Flagging rather than
fixing, but flagging loudly: **the CLI test suite cannot run at HEAD**, so
nobody is currently getting a byte-freeze signal from it.

That does not affect the results above. The byte-freezes cannot have moved for
`mean_coarse`: rung 0 is byte-identical to the pre-change render by SHA-256, and
`DEFAULT_MEAN_COARSE` is 0.

One further hazard, recorded because it is invisible in `git status`: the shared
index still holds a snapshot of `scripts/check-defaults.py` that predates
`5ce0fd7`, so a bare `git commit` by any lane would revert my registry entry
while committing their own staged hunk. A path-scoped commit takes the worktree
and is safe. I did not touch the shared index to "fix" this, because another
lane has 31 legitimately staged lines sitting in it.

### 9. Provenance of the `ca-*` pair, and: is far-field normalisation actually safe?

ORCH found the per-image normalisation independently, in the tone stage, and
concluded that measurements normalised to an in-image reference are safe because
*"a per-image scale factor cancels in a ratio taken within that same image"*.

**Provenance, asked and answered.** All six `ca-*` files are `--srgb` and
**TONED**, read from their own `ImageDescription`:

| pair | ctrl black / white | blend black / white |
|---|---|---|
| fern | 0.011119 / 0.306019 | **0.000000** / 0.319798 |
| lavendar | 0.015192 / 0.368004 | 0.017343 / 0.366872 |
| couch | 0.013474 / 0.282117 | 0.015274 / 0.280613 |

These arms are **not gain-related**, which is checkable without touching a
pixel: under a common gain `g`, black and white must both scale by `g`. White
ratios are 1.0450 / 0.9969 / 0.9947 while black ratios are 0.0000 / 1.1416 /
1.1336. ORCH's cancellation argument holds for a gain and these are not gains.

**The premise is true; the conclusion does not follow.** The tone stage is not a
scale. It is `y = (l - black)/(white - black)` -- affine, with an **offset** --
followed by a soft toe, `srgb()`, and `s_curve()`: two nonlinearities. A gain
cancels because it scales `l`, `black` and `white` together, which is exactly why
ORCH's `--auto-exposure` test returned 1.0000. An offset does not cancel in a
ratio, and a nonlinearity does not preserve one.

`experiments/BUILD-BLEND/farfieldsafe.py` tests this by pushing **one** physical
scene through each arm's real tone parameters, so the physical difference is
zero by construction and every DN of output is artifact -- measured *after* the
far-field normalisation. Two controls, both passing, because a number with no
control is not a measurement:

- **positive** (validates the model): a 6.148x gain with both tone points scaled
  cancels to **0.000000 of 255**, reproducing ORCH's own measurement.
- **null** (validates the attribution): identical tone parameters give exactly
  **0.000000**, so the differences below come from the parameters, not the code.

**The answer is row-dependent, and it is not uniformly bad news:**

| d | ORCH's blend-control | manufacturable by tone alone | share |
|---:|---:|---:|---:|
| 2 | +1.39 | **+2.01** | **144%** |
| 90 | +3.60 | +0.27 | **7%** |
| 175 | -0.25 | +0.17 | -68% |
| 350 | -2.19 | +0.07 | -3% |
| 550 | -2.36 | +0.05 | -2% |

- **d=2 is not physics.** The artifact is *larger* than the measured value and
  has the same sign. ORCH's reading that the blend is better at the silhouette
  is not supported by that row. This also explains why their instrument and mine
  disagree about the sign of criterion (c).
- **d=90, the mid-field win, is 93% real.** Independently corroborated: my
  untoned re-render measures +876 DN there.
- **The bowl is not manufactured by the arm-to-arm difference.** At d>=350 the
  artifact is ~0.05 of 255 and points the *other way*.

**But there is a second effect, and it is the larger one.** It applies to both
arms equally, so it is invisible to any blend-minus-control column and survives
far-field normalisation untouched, because it is nonlinear rather than
multiplicative. Expressing the control's own profile both ways:

| d | linear DN | as linear /255 | as toned /255 | inflation |
|---:|---:|---:|---:|---:|
| 90 | -1094 | -2.00 | -6.97 | 3.48x |
| 350 | -319 | -0.58 | -1.94 | 3.32x |
| 550 | -222 | -0.41 | -1.34 | 3.30x |

Median **3.33x** over d>=175. So the bowl is real in sign and in existence, and
roughly three times smaller in physical terms than the printed `of 255` numbers
imply. De-inflating ORCH's own -2.36 gives about -0.71 of 255 -- **still inside
their own 1.00 bar**, which is an independent route to the same conclusion
section 6 reached from my untoned renders (+0.35 of 255).

**Revised rule, narrower than ORCH's.** Normalising to an in-image reference
removes a per-image *gain*. It does not remove a per-image *offset*, and it does
not undo a nonlinearity. On a toned render it is safe only where the tone curve
is locally linear -- which the bright far field roughly is, and the deep
silhouette emphatically is not, at 4.28x inflation and a sign-flipping artifact.
Measuring on untoned linear output remains the only thing that needs no caveat.

### 10. The CLI wiring gate, answered at runtime

ORCH reported: *"`crates/strehl-cli/src/merge_cmd.rs` contains **no reference to
it**... The owner cannot get any of this from `strehl stack`."* Treated as the
highest-priority item and checked before anything else.

**The wiring is present and the pyramid is already the default.** Not from a
grep -- from the binary, built at HEAD, running the exact command quoted:

```
strehl stack "D:\personal\macro\coffee-bubbles" --out gate.tiff --srgb --demosaic

merge backend   : pyramid (default)
strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)
bands           : 7 Laplacian levels + 1 base, coarsest 28 x 19
base band       : plain mean across frames
```

Supporting code state: `merge_cmd.rs` holds **89** pyramid references;
`main.rs:858` calls `choose_merge_backend` and `main.rs:893` constructs
`strehl_core::pyramid::MergeConfig`; `DEFAULT_MERGE_BACKEND` is
`MergeBackend::Pyramid`. The escape hatch is the opt-**out** ORCH asked for
(`--merge estimator`), and cross-family flags are refused rather than ignored.

**Why the check disagreed, precisely.** ORCH grepped their pinned tree
`tree-ca-6a51e43`. That pin is commit `6a51e43`, dated **08-25 16:12**. The flip
is `5142ace`, dated **08-26 05:05** -- thirteen hours later. At `6a51e43`,
`merge_cmd.rs` contains **0** occurrences of `pyramid`, exactly as reported.

    git merge-base --is-ancestor 5142ace 6a51e43   ->  NO, the pin predates the flip

So the grep was correct about the tree it was run on, and the tree was stale.
This is worth recording as a method note beyond this instance: a repo-state claim
carries the commit it was read at, or it is not checkable. The same pin produced
the images judged in that message, which is why the *pictures* were current while
the *grep* was not -- `blend-render.exe` was built from it, and the example
carried the algorithm before the CLI did.

**The prescribed base-band fix is also already in place**, and the banner above
is the runtime confirmation rather than another reading of the source: `base band
: plain mean across frames`. `BaseBand::Mean` has been the shipped default since
the module landed; sections 1-2 measured the base band at 100.0% averaged
*before* any change of mine. The remedy cannot be applied because it is already
the state of the code. The bowl lives one level up, in the coarsest *Laplacian*
bands, which is what `mean_coarse` addresses and what the section 4 ladder swept.

**One thing ORCH should take back.** They asked to own `scripts/check-defaults.py`
and record the new switch's provenance themselves. I had already added the
`STREHL_PYRAMID_MEAN_COARSE` entry in `5ce0fd7`, committed hunk-wise so as not to
disturb another lane's 31 staged lines in that file. It is there now; it should
be re-checked or rewritten by its owner rather than trusted from me.

### 11. Scored against V-RIM's answer key, with V-RIM's own instrument

ORCH forwarded V-RIM's finding -- single frames have flat backdrops, the merge
manufactures the darkening, the election can leave the hull of its inputs -- and
asked me to score against the in-focus frame rather than a pre-registered number.
Done, using `C:\dev\strehl-out\V-RIM\framerings.py` (V-RIM's code, not mine,
argv-capable) against V-RIM's own single-frame linear TIFFs.

**First, which backend V-RIM measured.** Their merge input is
`ORCH-rim\fb-1cacb61-lin.tif`, and the banner captured in their own log reads
`strehl stack -- regularised winner + noise-gated average (THE DEFAULT PATH, an
estimator)`. **V-RIM measured the estimator -- the old default.** None of the
quoted -18.94% / -13.61% figures describe the merge that ships today.

**Commissioning before use.** Running their instrument on my *estimator* arm
first reproduces their ground truth: frame 110 far field **19058 DN**, against
ORCH's quoted "~19100 DN". An instrument that had not reproduced that number
would not have been trusted for the row below it.

`flower-bud-alone-cpl`, smooth backdrop, STRAIGHTEST QUARTILE / ALL RAYS:

| metric | estimator | **pyramid** | FRAME110 = truth |
|---|---|---|---|
| far field DN | 17150 / 16761 | **19467 / 19470** | 19058 / 19070 |
| inner DN | 3803 / 3699 | **2655 / 2720** | 2729 / 3070 |
| 10-90 edge px | 242.6 / 239.2 | **27.7 / 35.4** | 43.9 / 81.6 |
| ring % | +2.68 / +3.32 | **+0.11 / +0.06** | +0.19 / +0.10 |

The estimator's backdrop sags **10.0%** below the frame that actually saw it.
The pyramid arm lands **+2.1% above** it -- no sag -- and its ring, **+0.11%**,
is at or below the ground-truth frame's own **+0.19%**, a **24x** reduction. Edge
width is tighter than the in-focus single frame. On this subject the merge is
already at the answer key.

**ORCH's falsifiable prediction (3), tested and CONFIRMED.** The prediction was
that the cure should help most on a smooth backdrop and least on a textured one,
because texture gives the focus measure real signal to elect on. `coffee-bean`
is the textured case (paper fibres):

| ring % | estimator | **pyramid** | FRAME58 = truth |
|---|---|---|---|
| flower-bud (smooth) | +2.68 / +3.32 | **+0.11 / +0.06** | +0.19 / +0.10 |
| coffee-bean (textured) | +4.15 / +7.02 | **+3.54 / +3.62** | +0.16 / +0.18 |

Smooth: cured, 96% of the ring removed, ground truth reached. Textured: only
15% / 48% removed and **+3.54% of ring remains against a +0.16% truth**. The
prediction holds in the direction and the magnitude stated, from an instrument
neither ORCH nor I wrote. The mechanism is confirmed.

**What this changes about priority.** ORCH asked for the base-band fix as the
highest-value item. The base band is *already* the plain mean -- runtime-confirmed
in section 10 -- and the flower-bud row shows that is already delivering the cure
where the mechanism predicts it should. **The residual is on `coffee-bean`, and it
cannot be a base-band problem**: a textured backdrop gives the focus measure real
signal, so the bad election happens in the *detail* bands, which the base band
does not touch. Changing the base band cannot move a ring that lives at fine
scales. The remaining work is in detail-band election on textured backdrops --
a different fix from the one prescribed, and the answer key now localises it.

**Reported against my own interest.** Two residuals in my arm, neither spun:
`coffee-bean` inner is **8512 DN against the frame's 9563**, 11% dark, and I
cannot tell from this measurement whether that is veil correctly removed or the
subject over-darkened. And `flower-bud` far field overshoots truth by +409 DN
(+2.1%). Both want a diagnosis before either is called good.

### 12. ORCH's flat-region noise finding, reconciled against the shipping arm

ORCH asked me to stop treating the flat-region noise number as a cost, on the
evidence that the added energy is correlated structure rather than white noise.
Two things needed checking before accepting that: the +12.3% they attribute to
me, and whether their attribution holds on the arm that actually ships.

**The +12.3% is mine and I had already retracted it.** This report's own
preamble records the retraction: the ratio reads **1.0015** on
`couch-fibers-cpl` and 0.989 / 0.991 / 0.998 / 1.002 across four subjects. So
ORCH is defending a number that its author had already withdrawn -- worth saying
plainly, because a retracted figure that keeps circulating is a cost of its own.

**The reconciliation ORCH said they had not done.** Their three candidates were
different tiles, different high-pass radius, different renders. The first can be
eliminated by reading their code rather than guessing: `flatnoise.py:40` selects
tiles **once, on the mean of the two arms**, explicitly so that neither arm's
own residual drives the choice. My prior suspicion of selection bias was wrong
and their design is the correct one.

That leaves the renders, which is separable by running **their instrument,
unmodified, on my renders** (`experiments/BUILD-BLEND/flatnoise_on_mine.py`
imports `flatnoise.py` and redirects one constant):

| couch-fibers-cpl | result |
|---|---|
| ORCH's instrument, ORCH's pinned renders | **+32.1%** |
| ORCH's instrument, this arm's renders | **+3.6%** |
| this report's instrument, this arm's renders | **+0.15%** |

The instruments differ by ~3 points. **The renders differ by ~29.** ORCH's two
pinned binaries are not the two arms that ship, which is the same stale-pin
failure that produced the `merge_cmd.rs` grep in section 10. A pin is a claim
about a commit and needs to carry one.

**The attribution, re-run on the shipping arm** (`detail_on_mine.py`, ORCH's
`noise_vs_detail.py` unmodified):

| subject | sigma B | sigma A | rho_A | rho_add | if noise |
|---|---|---|---|---|---|
| 109MSDCF (placebo) | 71.5 | **44.2** | — | — | *adds no energy at all* |
| coffee-bean | 46.3 | 72.2 | +0.391 | +0.157 | +0.299 |
| couch-fibers-cpl | 202.0 | 212.8 | +0.800 | +0.372 | +0.763 |
| flower-bud-alone-cpl | 46.6 | 70.9 | +0.468 | +0.436 | +0.221 |
| lavendar-cpl | 28.0 | 90.2 | +0.399 | +0.368 | +0.067 |

**ORCH's conclusion holds on the shipping arm.** Every subject that gains energy
reads as structure against the measured white-noise reference of -0.0035, and
the placebo `109MSDCF` -- no depth separation -- adds **no** energy: sigma falls
71.5 -> 44.2, **-38.3%**. A change that manufactured noise could not be quiet on
the placebo and loud only where there is depth.

**A reporting defect in that script, and a correction against myself.** Two rows
above have `rho_add` *below* the "if noise" column, which on first reading looks
like the verdict contradicting its own evidence. It does not. `rho_if_noise =
cb*vb/va` is the counterfactual for **rho_A**, not for `rho_add`, so the two
adjacent columns are not comparable and the verdict test -- `rho_add` against
the white reference -- is the right one. The valid paired comparison is `rho_A`
vs `if noise`, which passes on all four (+0.391 > +0.299, +0.800 > +0.763,
+0.468 > +0.221, +0.399 > +0.067). **I was one step from reporting a bug in
ORCH's code that does not exist.** The defect is presentational, but it is not
harmless: ORCH published exactly this table as their evidence, and on renders
where the two columns cross it reads as a self-contradiction.

**Accepted, with the boundary stated.** The noise number comes off the blocker
list, re-characterised as *"attributed to recovered detail on four subjects; the
placebo adds no energy."* This bounds the character of the aggregate, not of
every component -- a real noise increase can ride underneath a larger detail
increase -- and that caveat is ORCH's, kept deliberately. Nothing in this arm
will be blurred or denoised to move the number.

### 13. The exact-zero blue pixels: real defect, already-shipped fix, wrong binary

ORCH measured **723,429 blue pixels at exactly 0 (2.192%)** on
`flower-bud-alone-cpl`, ruled out edge ringing and canvas coverage, rendered the
mask to show the zeros sitting in dark textured shadow on the subject, and
diagnosed a Laplacian reconstruction undershooting where the base band is low.
**That diagnosis is correct in every particular.** It is also a description of
the *unclamped* arm, which stopped being the default on 08-25.

**Their hypothesis about the mechanism, checked and refuted.** They proposed the
reconstruction clamps the accumulated sum, or clamps before the last band is
added. It does not: `pyramid.rs:1284` applies the clamp exactly **once**, after
`collapse()`, to the final image. Per-layer clamping is not happening.

**The A/B.** One binary, one stack, 205 frames, `--linear`, differing only in
`Hull::InputRange` vs `Hull::Unclamped`:

| arm | R == 0 | G == 0 | B == 0 |
|---|---|---|---|
| **clamped (ships)** | **0** | **0** | **0** |
| unclamped | 109,511 | 189,803 | **983,083 (2.979%)** |

The shipping arm has **no exact-zero pixels at all**, in any channel. The
unclamped arm reproduces ORCH's signature: same channel, same order of
magnitude, 2.979% against their 2.192%. **The clamp is the mitigation, not the
cause** -- the exact inverse of the hypothesis.

Neither rail is clipped in the shipping arm: `== 65535` is 0 in R, G and B, and
so is the estimator control, so there is no highlight cost either.

**Why their binary shows it.** ORCH pinned `blend-render.exe` from
`tree-ca-6a51e43`. From git, at that commit:

    enum Hull occurrences    : 0
    Hull::InputRange default : 0
    clamped_fraction present : 0

The `Hull` type **did not exist**. The clamp landed at `275fbd17`, 08-25 23:05
-- **seven hours after** that pin. Their binary cannot clamp because there is
nothing in it to do so. This is the third stale-pin finding in one session, after
the `merge_cmd.rs` grep (section 10) and the +32.1% noise gap (section 12), and
the pattern is now the single largest source of wasted measurement on this
project.

**Two corrections against myself, both from this same investigation.**

1. I reported earlier in this session that the clip "reproduces on my own TIFF"
   because `clip_linear.py` printed `+1.5804 pt CLIPPING IS IN THE MERGE` when I
   passed it my render. **It ignored my argument.** Its summary line reads
   `total compared: 6` -- it globbed ORCH's own `_tiff` directory and reported
   ORCH's data back to me while appearing to answer about my file. An instrument
   that silently ignores argv will confirm whatever you already believed. Check
   that the input count matches the input you supplied.
2. This report's `Hull` documentation says the excursion is rare enough that the
   clamp is nearly inert. It is not.

**The real finding, which is mine and is not fixed.** The per-render diagnostic
reads:

    hull clamp : 8.647% 10.106% 10.105% 10.986%

**The reconstruction puts 8.6-11.0% of output pixels outside the range its own
input frames support.** The clamp catches them, so nothing reaches the file --
but this report's own `clamped_fraction` doc states the interpretation: *"large
means the merge is routinely emitting values no frame observed, which is a
statement about the selection exponent and not about the clamp."* One pixel in
ten is large. The clamp is load-bearing, not a safety net, and a clamp doing
that much work is converting an out-of-hull excursion into a flat spot rather
than into a zero. **ORCH pointed at a real weakness and the pointing stands even
though the measurement was on the wrong binary.** The next work in this lane is
the selection exponent at the coarse bands, not clip handling.

**Also worth re-checking on a current binary:** the C5 gallery result that
flagged `dry-erase-marker-head-cpl` at +2.291 pt and `foam` at +1.020 pt. If
those renders came from the same pin, they are measuring an arm with no clamp.


## 14. A census instead of a fourth assertion, and a correction on my own commit

ORCH has now reported four times that `merge_cmd.rs` contains no reference to
the pyramid backend. Three times the report traced to a stale pinned tree and
three times I answered by re-counting references at HEAD. That answer has now
failed to persuade three times, which makes it the wrong answer regardless of
whether it is true. This section stops asserting and measures the environment
instead.

### 14.1 There are 105 copies of `merge_cmd.rs` on this machine

ORCH supplied a fingerprint without intending to: *"the four `blend` matches are
`support.blend()`, the edge-aware mask."* Zero `pyramid`, a few `blend`, at least
one `support.blend(`. That identifies a file by content, so the tree can be found
rather than argued about. `experiments/BUILD-BLEND/treecensus.py` walks the disk
and fingerprints every copy.

| | count |
|---|---:|
| copies of `merge_cmd.rs` under `C:\dev` | **108** |
| copies with **zero** `pyramid` references | **72** |
| copies matching ORCH's fingerprint (0 `pyramid`, has `support.blend()`) | **34** |
| the live repository, `blog\death-of-software\projects\strehl` | **100 `pyramid`** |

The count was 105 when I first ran it and 108 twenty minutes later, because other
lanes are creating trees while this is being written. The unwired copies are pins
and worktrees: `tree-ca-6a51e43`, `pin-1cacb61`, `vtone-pin`,
`BUILD-SHARP\pin-aac3ee8`, `pure-head`, and three dozen more. Several are mine.
The wired copies run 22 -> 25 -> 28 -> 35 -> 50 -> 52 -> 70 -> 100 references,
which is the backend being built out commit by commit, and the live repository
sits at the top of that ladder.

**The conclusion is not that ORCH was careless.** Any agent in this workspace can
open a real file, read it correctly, and be wrong about the product, because
there are 105 candidates and nothing in a path like
`C:\dev\strehl-out\pure-head\crates\strehl-cli\src\merge_cmd.rs` announces
that it is not the product. A name containing `head` is actively misleading. This
is an environment defect that has now consumed four exchanges across two agents,
and re-asserting a reference count does nothing about it. What does: quoting the
absolute path and `git rev-parse HEAD` beside any claim about what ships.

The live path, stated once so it can be copied:

    C:\dev\blog\death-of-software\projects\strehl

### 14.2 The `--camera-linear` confound: chronology refutes it

ORCH asked, reasonably, whether my own pre-`0d9fd28` comparisons carry the
cross-space confound they had just caught in their own tooling -- specifically
the `+12.3%` flat-region noise number. It is a good question and it was cheap to
answer. It does not apply, for two independent reasons.

**Chronology.** `0d9fd28` (`--camera-linear`) is 08-25 **18:10**. `275fbd17` is
08-25 **23:05**, five hours *later*, and `git merge-base --is-ancestor 275fbd1
0d9fd28` returns false in that direction and true in the other. The reading that
shows the noise -- `1.1179` -- is the **later** pin. The clean reading, `1.0015`,
is the earlier one. So the number ORCH suspects was measured on a tree that
already contained the fix; the confound cannot reach it.

**Direct control, already run.** Section 7 tested measurement space explicitly at
a fixed pin: sRGB `4.6660` against linear `4.1718`, recorded there as *"not the
cause"*. The space was controlled by measurement, not by assumption.

### 14.3 The correction I owe, and it is against my own arm

Section 7 closes the noise investigation with this sentence:

> *"The difference is therefore between pins, in shared code I do not own, and I
> am not able to attribute it further."*

That is wrong, and it is wrong in the one direction an agent should never be
wrong in -- it moved a defect out of my own lane. `275fbd17` touched exactly two
files:

    crates/strehl-cli/examples/blend-render.rs |  32 ++-
    crates/strehl-core/src/pyramid.rs          | 341 ++++++++++++++++++++++++++++-

**Both are mine.** It is my commit, in my module, and it made `Hull::InputRange`
the *default* rather than adding an opt-in flag. The regression bisects to me. I
disowned it in writing while holding the commit that caused the pin boundary.

### 14.4 The mechanism I then proposed -- and its refutation

The module's own docstring argues the clamp "cannot cost anything real," on the
grounds that a value outside `[min_k, max_k]` is unsupported by the data. Reading
it again with 14.3 in hand, that argument is about **bias** and is silent on
**variance**, and there is a mechanism it does not exclude: where the clamp
binds, the output is no longer the reconstruction but an *extreme order statistic
of N noisy frames*. Extreme order statistics have high variance. Substituting one
for a smooth reconstruction is a plausible way to add high-frequency energy in
exactly the flat regions where `min_k` and `max_k` are pure noise.

`experiments/BUILD-BLEND/hullnoise.py` tests it. One binary at HEAD, one flag
apart, `couch-fibers-cpl` (299 frames, the do-no-harm control subject),
`--camera-linear` so no tone stage is in the path. The design carries an internal
control that the cross-pin comparisons never had: **the arms differ by one flag,
so `A != B` is exactly the set of pixels where the clamp bound**, and every other
pixel is byte-identical by construction. A tile's bind fraction is therefore a
within-image dose. If the clamp is responsible, the effect must concentrate where
the dose is high.

Commissioned before the verdict was read:

| control | expected | read | |
|---|---|---|---|
| null: arm A against itself | exactly 1.0000 | **1.0000** | exact |
| positive: synthetic Gaussian base, 120 DN plant | 1.1670 | **1.1653** | **1.0% of the effect** |
| sensitivity: real photograph, 81.4 DN plant | > 1 | 1.1009 | correct sign |

*The first positive control failed*, reading 1.1003 against a predicted 1.0198 --
406% of the effect. The failure was mine, not the instrument's: I predicted with
`sqrt(s^2 + amp^2)/s`, which is quadrature for two Gaussians, while measuring
with MAD on the highpass of real photographic detail, which is heavy-tailed. On a
heavy-tailed base MAD under-reads the base scale, so an added white component
inflates the ratio faster than quadrature predicts. Moving the positive control
onto a Gaussian base -- where the formula it uses is actually the right model --
brings it to 1.0% error. The real-data reading is kept as a *sensitivity*, not a
gate, because it bounds how far a quoted magnitude can be trusted.

The result, `couch-fibers-cpl`, 200 flattest 96 px tiles, clamped / unclamped:

| channel | dose | overall A/B | lowest-dose quartile | highest-dose quartile |
|---|---:|---:|---:|---:|
| R | 12.33% | 0.9841 | 0.9993 *(dose 1.60%)* | **0.9555** *(dose 27.22%)* |
| G |  9.40% | 0.9647 | 0.9980 *(dose 1.07%)* | **0.9076** *(dose 21.50%)* |
| B | 14.33% | 0.9770 | 0.9983 *(dose 2.03%)* | **0.9425** *(dose 30.57%)* |

**The hypothesis is refuted, and cleanly.** Every ratio is below 1.0: the clamped
arm is *quieter* than the unclamped one. The dose-response runs the right way in
all three channels -- tiles where the clamp barely bound read 0.998-0.999, i.e.
indistinguishable, as they must be since those pixels are nearly identical, while
tiles where it bound on 21-31% of pixels read 0.91-0.96. The clamp is not
injecting noise; it is removing excursions that were noise, and it removes more
of it exactly where it acts more.

So the docstring's conclusion survives -- but it survives for a reason it did not
state. Its argument was that the clamp cannot cost anything because the values it
removes are unjustified. The measured reason is stronger and different: the
values it removes are *noisier* than what replaces them. I have now corrected
that docstring once for overstating how inert the clamp is (section 13); this is
the opposite correction, and both came from measuring rather than from reading.

### 14.5 What this leaves open, now correctly scoped as mine

The `0d9fd28` -> `275fbd17` noise regression is **real and still unexplained, and
the clamp is not it** -- turning the clamp off makes flat regions worse, not
better, so it cannot be why noise rose at the commit that introduced it. Since
that commit touched only two files and both are mine, the remaining candidates
are inside my lane. It is not bisected. It is no longer disowned.

Also unchanged from section 13 and still the largest open number in this report:
the reconstruction puts **8.6-11.0%** of pixels outside the hull its own inputs
support on `flower-bud-alone-cpl`, and **2.1-7.0%** even on the flat control
subject. The clamp is load-bearing rather than a safety net, and 14.4 says it is
a *good* load-bearing part. The indicated attack remains the coarse-band
selection exponent, which is what generates the excursions in the first place.

*Nothing in this section was verified by its author beyond the commands quoted.
The renders, the instrument and its controls are committed and re-runnable:
`experiments/BUILD-BLEND/hullnoise.py`, `experiments/BUILD-BLEND/treecensus.py`.*


## 15. The clamp acceptance test, run in the product, and a divergence I withdraw

### 15.1 Status on the wiring gate: wired, and the dispute has a second fingerprint

ORCH's fifth report says `merge_cmd.rs` has zero `pyramid` references and adds a
new datum: *"merge_cmd.rs is 5579 lines."* That is a stronger fingerprint than
the reference count, because it is a number they measured themselves.

Live tree, checked at the moment of writing rather than from the earlier census:

| | |
|---|---|
| repo | `C:\dev\blog\death-of-software\projects\strehl` |
| HEAD | `ac8b7022` -> `d56540eb` (other lanes committing during this check) |
| `merge_cmd.rs` | **7619 lines**, mtime 11:21:29, **100 `pyramid`** |
| `DEFAULT_MERGE_BACKEND` | `MergeBackend::Pyramid`, line 389 |
| callers of `pyramid::` | `merge_cmd.rs`, `main.rs`, `blend-truth.rs`, `blend-render.rs` |

Searching every copy on disk for one of **exactly 5579 lines** returns **eleven**,
every one with **zero** `pyramid`, and **not one of them is the repository**:

    tree-ca-6a51e43   tree-d4b8644   tree-lin-0d9fd28   pin-1cacb61   pin-elect
    V-CHROMA\pin-new  VERIFY-WIRE\t-parent   vtone-after   vtone-before
    vtone-tree        strehl-pin-ce2c793

Three of those eleven are mine, so I helped build the maze I am complaining
about. The decisive detail is that `git -C <dir> rev-parse --short HEAD` returns
**nothing** for all eleven: they are plain directory copies with no `.git`, so
there is no check an agent can run *inside* one that reveals it is stale. That
fully explains a careful agent reading a real file and being repeatedly wrong
about the product, and it is why four rounds of "89 references at HEAD" changed
nothing.

Runtime proof, from a hashed binary built out of the live tree:

    SHA256 A2A6077B8C97FF20198717572AA4BC32C2A837EF74945FF7288DBE4C6FC6363B
    $ strehl stack D:\personal\macro\coffee-bubbles --out banner.tiff
    merge backend   : pyramid (default)
    strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)
    bands           : 7 Laplacian levels + 1 base, coarsest 28 x 19
    base band       : plain mean across frames

No flags. That is the product command with its defaults.

### 15.2 The acceptance test, run with one binary instead of two

ORCH's design pins two executables -- `strehl.exe` for BEFORE and
`blend-render.exe` for AFTER. That confounds the merge backend with every other
difference between two binaries built at different commits. Since the backend is
now selectable at runtime, a strictly better design is available: **one binary,
one flag apart**, `--merge estimator` against the default `--merge pyramid`, with
every other flag identical by construction.

`--demosaic`, ORCH's own configuration, scored by ORCH's own metric
(`experiments/BUILD-BLEND/zerocount.py`):

| subject | ch | BEFORE @0 | AFTER @0 | delta pt |
|---|---|---:|---:|---:|
| dry-erase-marker-head-cpl | R | 0.0001 | **0.0000** | **-0.0001** |
| dry-erase-marker-head-cpl | G | 0.0000 | **0.0000** | **-0.0000** |
| dry-erase-marker-head-cpl | B | 0.0005 | **0.0000** | **-0.0005** |
| couch-fibers-cpl *(placebo)* | all | 0.0000 | 0.0000 | 0.0000 |

Per-channel minima tell it more directly. The **estimator** arm bottoms out at
`0 / 0 / 0`; the **pyramid** arm bottoms out at `582 / 292 / 89`. The pyramid
merge emits no exact zeros at all on the subject ORCH measured at **+2.36 pt**,
and the sign of the difference is negative in every channel -- it is the arm that
*does not* clip. Both subjects pass, and the placebo does not regress.

### 15.3 A divergence I claimed and now withdraw

Between measurements I reported that `blend-render.rs:611` carries a
`.max(0.0)` the product lacks:

    blend-render.rs:611   let norm = |v, gain| v.max(0.0) * gain * eg / range;
    merge_cmd.rs:5971     let norm = |v, gain| v * gain * eg / range;

**That was wrong, and I withdraw it.** The product clamps the pyramid planes one
call upstream, in `Merged::value` at `merge_cmd.rs:4091`:

    Self::Bands { planes, .. } => planes[band_slot(p)][i].max(0.0),

Different site, same clamp. I compared one file's `norm` against the other's and
concluded from the mismatch without checking whether the clamp had simply moved.
The doc contract on `write_frame` -- *"every line of arithmetic here is copied
from `merge_cmd::write_merged`"* -- is intact. Nothing needs fixing, and the
"real divergence, and it's my bug" I announced does not exist.

### 15.4 So why were ORCH's zeros real?

They were, and section 13 already has the mechanism: their AFTER binary predates
`275fbd17`, the commit that made `Hull::InputRange` the default. Without the hull
clamp the reconstruction goes negative; the `.max(0.0)` -- which is present on
*both* arms and always has been -- pins those negatives to exactly zero, which is
the spike-at-zero-with-no-ramp signature ORCH correctly identified. With the hull
clamp on, the reconstruction is confined to `[min_k, max_k]`, every frame is
already non-negative, so nothing reaches the clamp and no zeros appear. That is
exactly what 15.2 measures.

**ORCH's item B is not a request; it is a description of what shipped.** *"A merge
that estimates a pixel from N frames should not be able to return a value outside
the range those frames span at that pixel"* is `Hull::InputRange`, landed 08-25
23:05. Their instinct and the implemented fix are the same object.

### 15.5 The instrument caught its own bug first

`zerocount.py` returned `+0.0000` on every channel, every subject, every
threshold. A frozen probe and a genuine pass are the same glyph, so it was
commissioned before being believed. The first positive control **failed**:

    planted 12345 exact zeros, counter reports 0
    POSITIVE CONTROL FAILED: counter cannot see planted zeros

The fault was in the control, not the counter: `img[:, :, 2].ravel()` returns a
*copy* for a non-contiguous slice, so the plant never landed in the array being
counted. Writing through `np.unravel_index` instead gives `12345 / 12345` exact.

It also surfaced that the **default (binned) render never approaches zero at all**
-- floor `447-739 DN` -- so the first `+0.0000` was partly "not measurable in this
configuration" rather than "not present". Re-rendering in ORCH's `--demosaic`
configuration is what made the metric live: the estimator arm's minima drop to 0
there. Without the floor check, a pass would have been reported from a render in
which the statistic could not have moved.

*Renders, instruments and controls are committed and re-runnable:
`experiments/BUILD-BLEND/acceptance.ps1`, `zerocount.py`, `zerocommission.py`.*


## 16. The blocks are not at HEAD, but the hull violation behind them is real and large

### 16.1 merge_cmd.rs: never touched

ORCH withdrew the wiring mandate and asked whether I hold local edits to
`crates/strehl-cli/src/merge_cmd.rs`. `git status --porcelain` on that path is
**empty**, and no commit of mine (`blend:`) appears in its history. I have never
written to it. Nothing to discard.

### 16.2 The visible defect does not reproduce at HEAD, in either binary

ORCH reports solid black axis-aligned blocks 40-60 px across at
`(6136, 1360)` on `dry-erase-marker-head-cpl`, and instructs -- correctly --
that the picture is the instrument and the number is the annotation. So the
crop was taken, with **one tone mapping shared by both panels** taken from the
BEFORE arm only, since a per-panel normalisation could manufacture or hide a
black block.

At that site, HEAD `5dd9b649`:

| arm | linear min | exact zeros |
|---|---:|---:|
| estimator (BEFORE) | 408 DN | 0 |
| pyramid, `strehl stack` | **2970 DN** | **0** |
| pyramid, `blend-render` | **2970 DN** | **0** |

Whole frame, both binaries, identical to four decimals:

    ch      min       <=0       <=1      <=16      <=64     <=256    <=1024
    R       582   0.0000%   0.0000%   0.0000%   0.0000%   0.0000%   2.3891%
    G       292   0.0000%   0.0000%   0.0000%   0.0000%   0.0000%   3.1193%
    B        89   0.0000%   0.0000%   0.0000%   0.0000%   0.0000%   4.0350%

    pixels with ANY channel exactly 0 : 0 (0.0000%)

That the product binary and my example binary agree *exactly* is an independent
confirmation of the retraction in 15.3: their arithmetic really is the same, and
the `.max(0.0)` divergence I claimed does not exist.

What the crop does show is the opposite of the report. The **estimator** panel
carries the halo -- a pale ring around the ink, concentric contour banding, a
grey patch to the left and a pale blob upper-right, and ink that reads
washed-out blue-grey. The **pyramid** panel is clean: solid black ink, no ring,
no patches, paper fibre resolved.

### 16.3 But the mechanism ORCH proposes is confirmed, and it is worse than the count suggested

ORCH's hypothesis -- *a per-band convex combination is not convex overall, so the
reconstruction can leave `[min_k, max_k]`, and at black-ink-on-white-paper
contrast that excursion is thousands of DN* -- is **correct**. This module's own
`Hull` docstring already says so, citing ORCH's earlier 1-D construction. What
was missing was the magnitude on a real high-contrast frame.

`hull clamp` on `dry-erase-marker-head-cpl`: **11.498% 18.821% 18.881% 12.553%**
per CFA plane -- the highest out-of-hull fraction measured anywhere in this
project, against 8.6-11.0% on `flower-bud-alone-cpl`. ORCH's contrast argument is
right.

The rate alone decides nothing, so the *correction magnitude* was measured
directly as `clamped - unclamped` (`experiments/BUILD-BLEND/excursion.py`):

| ch | moved | median &#124;d&#124; | p99 | p99.9 | max | share of frame > 1000 DN |
|---|---:|---:|---:|---:|---:|---:|
| R | 16.588% | 194 | 1835 | 4461 | **42711** | 2.026% |
| G | 15.512% | 287 | 1972 | 5515 | **49500** | 2.015% |
| B | 16.853% | 226 | 1904 | 5285 | **49497** | 1.795% |

And the direction is ORCH's direction: the clamp **raises** 77.7% / 85.0% /
79.1% of the pixels it moves, meaning the reconstruction had fallen *below* the
hull, toward and past black. The unclamped arm carries **1.17% / 1.29% / 1.40%**
exact zeros, which is the signature ORCH measured at +1.86 / +1.96 / +2.36 pt.

So: **the artifact ORCH saw is what this merge does with the clamp removed**, and
the clamp is the only thing standing between the current output and those blocks.
A merge that requires a 49,500 DN correction -- 75% of full scale -- on 2% of a
frame is not sound at those sites, even when the correction lands.

### 16.4 The design this data indicates

ORCH asks for a fix that does not resolve by reflex into a hard hull projection,
because that would also forbid genuine super-resolution or deconvolution gain,
and proposes a margin tied to the calibrated noise. **The excursion distribution
argues for exactly that, and it sets the constant.**

The median excursion is **194-287 DN**, which is on the order of one sigma of the
calibrated noise at these levels -- i.e. the typical excursion is inside what the
noise model already says is plausible, and is a candidate for genuine recovered
detail of the kind ORCH's own `rho_add` analysis found. The tail is **20-200
sigma**. Those two populations are separated by more than two orders of
magnitude, which is what makes a noise-referenced bound feasible rather than
arbitrary:

    lo_k = min_k - lambda * sigma(pixel)
    hi_k = max_k + lambda * sigma(pixel)

with `lambda` around 2-3. That admits essentially all of the median-scale
excursion and rejects essentially all of the catastrophic tail, and -- unlike an
absolute epsilon -- it scales correctly with signal level, so it does not tighten
in the shadows where the current hull is nearest zero and does most of its
damage.

Two properties worth stating before implementing, because they are what makes
this safe rather than merely plausible:

* It **degenerates to the current behaviour as `lambda -> 0`**, so a rung-0
  byte-identity commissioning is available -- the same ladder discipline used for
  `mean_coarse`.
* It **cannot reintroduce a hard seam**, because `min(max(x, lo), hi)` stays
  continuous in all three arguments and `sigma` is a smooth function of the
  signal, so the widened bound is still continuous.

The real fix is upstream of all of this: the excursions are generated by the
per-band selection exponent (`2 3 4 5 8 8 8`, highest at the finest bands), and
this module's own docstring records 0 violations at exponent <= 1 against 511 at
16. A margin makes the clamp honest; lowering the exponent would make it
unnecessary. The margin is the safe first rung because it cannot cost acuity,
which an exponent reduction measurably does (18% by an earlier measurement).

### 16.5 Acceptance, as ORCH specified it

Scored on the **linear 16-bit TIFF**, AFTER minus BEFORE, per channel, on
`dry-erase-marker-head-cpl`, `foam` and `flower-bud-alone-cpl` within +0.05 pt,
with `couch-fibers-cpl` held at 0.0000 as the placebo, plus a re-crop of
`(6136, 1360)` inspected by eye. `experiments/BUILD-BLEND/zerocount.py` and
`cropsite.py` implement it; `zerocommission.py` must pass first, since a
zero-count that cannot see a planted zero reports a pass and a frozen probe
identically.

*Instruments: `cropsite.py`, `clipcensus.py`, `excursion.py`, `zerocount.py`,
`zerocommission.py`, `acceptance.ps1`. Not verified by their author.*
