# BUILD-BLEND — a Laplacian multi-band merge against the depth-boundary rim

**Verdict, in one line: the multi-band merge removes the cut-out rim on both
polarities, and leaves `couch-fibers-cpl` intact.**

Two things must be true for that sentence to be worth anything, so they are
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

## Look at these

Full frame is the judging surface; the 1:1 files are supplementary evidence
about a defect that is already visible at full frame.

| | full frame (primary) | 1:1 at the largest disagreement |
|---|---|---|
| flower-bud (bright rim) | `C:\dev\strehl-out\BUILD-BLEND\sxs-flower-bud-with-background-fern-cpl-FINAL.jpg` | `rim-flower-bud-with-background-fern-cpl-FINAL.jpg` |
| lavendar (dark rim) | `sxs-lavendar-cpl-FINAL.jpg` | `rim-lavendar-cpl-FINAL.jpg` |
| couch-fibers (do-no-harm) | `sxs-couch-fibers-cpl-FINAL.jpg` | `rim-couch-fibers-cpl-FINAL.jpg` |

All in `C:\dev\strehl-out\BUILD-BLEND\`. Left panel is the shipped pipeline,
right panel is this merge. Both arms go through the **identical**
`gallery_view.py` recipe — `tifffile`, assert `uint16`, `>> 8`, Lanczos — so a
tone difference cannot be an artefact of the viewer.

The `-FINAL` files are the ones to judge. Earlier `sxs-*` and `*-v2` files in the
same directory are intermediate arms, kept as the record of how the parameters
were chosen; they are not the result.

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

On **couch-fibers**, the two are indistinguishable at full frame. At 1:1 I can
still see marginally less high-frequency sparkle in the specular highlights of
the blend, offset by noticeably less colour fringing on fibre edges.

**I am deliberately not putting a number on that residual softness.** The
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

Ryzen 9 9950X3D, 299 frames at 33 MP, four workers, warm warpmap cache. Renders
made from a binary pinned outside the tree (sha256
`CA8C1F91FAE1EF294F5A2A85D669DFADBDF93DCB96E5E471B678C502B3A41C59`), because
builds land mid-run on this shared tree.

| subject | blend fold | blend total | control total |
|---|---|---|---|
| flower-bud | 248.4 s | 252.4 s | 208.6 s |
| lavendar | 205.4 s | 207.4 s | 168.7 s |
| couch-fibers | 210.7 s | 213.0 s | 185.0 s |

**This merge is 15–25% slower than the shipped one, and it is doing that on four
workers against the control's thirteen.** Per-frame cost is 0.69–0.83 s wall at
four workers. The control is not a like-for-like comparison of algorithmic cost
and I am not claiming it is.

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
doctrine the author does not verify their own work), and a decision about the
15–25% cost. The residual 1:1 softness on `couch-fibers` should be re-examined by
someone who did not build this.
