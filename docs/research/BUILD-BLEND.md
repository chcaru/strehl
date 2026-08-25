# BUILD-BLEND — a Laplacian multi-band merge against the depth-boundary rim

**Verdict, in one line: the multi-band merge removes the cut-out rim on both
polarities, and leaves `couch-fibers-cpl` intact.**

Three things must be true for that sentence to be worth anything, so they are
stated before anything else:

* **It is not blur.** A blurred render has no rim either. The do-no-harm frame,
  `couch-fibers-cpl`, is indistinguishable from the shipped pipeline at full
  frame and a near-match at 1:1 — and the first version of this merge *was*
  visibly soft there, was caught, and was fixed. The softness is what a merge
  like this is supposed to be criticised for, and it is the thing that was
  measured hardest.
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
| flower-bud (bright rim) | `C:\dev\strehl-out\BUILD-BLEND\sxs-flower-bud-with-background-fern-cpl-PAIRED.jpg` | `rim-flower-bud-with-background-fern-cpl-PAIRED.jpg` |
| lavendar (dark rim) | `sxs-lavendar-cpl-PAIRED.jpg` | `rim-lavendar-cpl-PAIRED.jpg` |
| couch-fibers (do-no-harm) | `sxs-couch-fibers-cpl-PAIRED.jpg` | `rim-couch-fibers-cpl-PAIRED.jpg` |

All in `C:\dev\strehl-out\BUILD-BLEND\`. Left panel is the shipped pipeline,
right panel is this merge. Both arms go through the **identical**
`gallery_view.py` recipe — `tifffile`, assert `uint16`, `>> 8`, Lanczos — so a
tone difference cannot be an artefact of the viewer.

**Judge the `-PAIRED` files.** They supersede the earlier `-FINAL` set, which was
confounded — see below. Earlier `sxs-*`, `*-v2` and `*-FINAL` files in the same
directory are intermediate arms kept as the record of how the parameters were
chosen; they are not the result.

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

**I am still deliberately not putting a number on acuity here.** The
statistics available for it — gradient energy, high-pass energy — have both
lied on this project by being satisfied by injected structure, and
`edge_overshoot` gets pinned by a single specular highlight. A number here would
add false confidence to a judgement the pictures already support.

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

This arm worked, and the mechanism debate about *why* the rim exists turned out
not to need resolving in order to remove it — which was the point of running a
structurally different second arm.

Before this goes anywhere near the ship path it needs: photometric normalisation,
clip and outlier handling, an independent verification pass (in this project's
doctrine the author does not verify their own work), and a decision about cost
that rests on a like-for-like re-measurement at equal worker counts on a quiet
machine — my two timing rounds disagree in sign and neither should be trusted.

Acuity on `couch-fibers` should be re-examined by someone who did not build this.
I flagged a residual 1:1 softness in the first round and could not reproduce it
in the second, better-controlled round; that is the kind of claim that most needs
an independent eye, precisely because the person who built the thing is the
person most likely to be relieved when it disappears.

It is also untested on subjects beyond these three. Bees, tweezers and text all
stress different parts of a merge — specular highlights, hard synthetic edges,
and fine periodic detail respectively — and none of them are represented here.
