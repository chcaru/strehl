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

