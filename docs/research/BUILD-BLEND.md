# BUILD-BLEND — a Laplacian multi-band merge against the depth-boundary rim

**Verdict, in one line: the multi-band merge removes the cut-out rim on both
polarities and does not soften `couch-fibers-cpl` — but it is 12.3% noisier
there, and that price is real.**

The rim result is strong and I will defend it. The do-no-harm result is a
*qualified* pass, not a clean one, and the qualification is measured rather
than hedged: this arm does not pay for the rim in sharpness, which is the way
BUILD-HALO's arm currently pays, but it does pay in noise. Both numbers are in
"The price this arm pays" below and neither is buried.

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
| flower-bud (bright rim) | `C:\dev\strehl-out\BUILD-BLEND\sxs-flower-bud-CA.jpg` | `rim-flower-bud-CA.jpg` |
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

## The price this arm pays

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

| | removes the rim | softens `couch-fibers` | noisier on `couch-fibers` |
|---|---|---|---|
| BUILD-HALO's selection fix | reduced, not removed | **yes — their stated blocker** | not reported here |
| this arm | **yes, both polarities** | **no — no band is softer** | **yes, +12.3%** |

Both arms pay on the do-no-harm control. They pay in different currencies.
Which is preferable is the owner's call, not mine — but noise is recoverable by
averaging more frames and lost acuity is not recoverable at all, which is the
one thing I would put on the scale.

## Where the two arms differ, by distance from the silhouette

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

This arm worked on the defect it was built for. The rim is gone on both
polarities, the hard-edged patch artefact is gone with it, and the mechanism
debate about *why* the rim exists turned out not to need resolving in order to
remove it — which was the point of running a structurally different second arm.

It is not free, and the bill is now measured rather than assumed:

* **+12.3% noise in flat regions on `couch-fibers`.** Real, against this
  project's more valuable crown jewel, and the first thing to attack. The
  mechanism is that per-band exponents of 2–8 concentrate weight on too few
  frames; lowering the fine-band exponents and widening the gate trades along
  exactly that axis.
* **A ~2% backdrop difference on `flower-bud` outside the 20 px rim zone**,
  which ORCH's instruction says must not be there. The leading explanation is
  this arm's missing photometric normalisation interacting with depth-dependent
  frame selection, but that is *not established*, and until it is, it stands as
  an open charge.
* `lavendar` shows the correct shape — confined inside 20 px, ~0 beyond — so the
  `flower-bud` result is not a property of the method as such.

Before this goes anywhere near the ship path it needs: photometric normalisation
(which would also test the backdrop explanation above), clip and outlier
handling, a fine-band exponent sweep against the flat-region noise number, and
an independent verification pass — in this project's doctrine the author does
not verify their own work, and that applies to every number in this document.

Cost remains unmeasured. My two timing rounds disagree in *sign*, on a machine
running five other agents, and a third informal round agreed with neither
convincingly. I am claiming nothing about speed. A like-for-like re-measurement
at equal worker counts on a quiet machine is the only thing that would settle it.

It is also untested on subjects beyond these three. Bees, tweezers and text all
stress different parts of a merge — specular highlights, hard synthetic edges,
and fine periodic detail respectively — and none of them are represented here.
