# M86b pre-registration — the warp sidecar

Written and committed **before** `warpmap.rs` or `align_cmd.rs` exist. This
registers what would make the sidecar wrong, not what would make it look right.

Parent: `experiments/M86-alignment/PREREGISTRATION.md` (commit `5205732`) and
`docs/research/M86-alignment.md`.

## 0. What is being built

A **sidecar**: `strehl align <dir> -o <file>` runs the M86 estimator and global
solve over a bracket and writes a per-frame transform table. The merge later
*reads* that table and gathers through it. The solve does not re-run per merge.

Not in scope, explicitly: improving the estimator. M86 measured it as the
bottleneck (`E*` 11.56 px against a 9.07 px cycle floor). Tonight is wiring.

## 1. The semantics being committed to, verified at source first

These were read out of `align.rs` before writing anything, because getting the
direction wrong is silent and is the single most likely defect in this task.

- `AlignEdge.t` is **frame `i` coordinates to frame `j` coordinates**
  (`align.rs:1330` doc).
- `Placement[k]` is **a per-frame transform relative to frame 0**
  (`align.rs:1444` doc). `predict(p,i,j) = relative(p[i], p[j]) =
  p[i]⁻¹ then p[j]`, which is `i → j`, so `p[k]` is **`0 → k`**.
- `gather_into(src, t, ...)`: "`t` maps **reference** coordinates to **source**
  coordinates, so this is a pull" (`align.rs:2383` doc).

**Therefore the registration operation is `gather_into(frame_k, placement[k])`,
with NO inversion.** Reference is frame 0; `p[k]` is reference → frame k, which
is exactly what a pull wants. This is the claim W2 exists to falsify.

## 2. Gates. Each names, in advance, an input that must make it fail.

### W1 — round trip is bit-identical
Write a sidecar, read it back, compare every frame's four transform components
by **exact bit equality** (`f64::to_bits`), not by tolerance.

- **Bar:** all frames bit-identical; refusals still refusals.
- **Must fail on:** flipping one hex digit of one frame's serialised `a_re`.
  If W1 still passes after that, W1 is not reading the file it claims to.
- **Must also fail on:** a file truncated mid-entry — and fail with a typed
  error, never a short map silently missing its tail.

### W2 — a planted warp is actually undone (the one that matters)
On real frames: take frame `k`, apply a known similarity `S` (scale 1.01 about
the plane centre ≈ 21 plane px of corner motion — above the 1 px peak-locking
knee measured in M86 §6.3, inside the ~192 px capture limit of §6.1) to get `W`.
Write a sidecar asserting frame `k`'s placement is `S`. Gather `W` through the
sidecar. The result must match the **original, un-warped** frame `k`.

Scale-free metric, so it cannot be gamed by an overall gain:

    ratio = median |gathered − original|  /  median |warped − original|

over interior pixels only (kernel support inside the plane).

- **Bar:** `ratio <= 0.25`.
- **Must fail on — the inversion control:** gathering with `S.invert()` instead
  of `S`. That doubles the warp rather than removing it, so it must give
  `ratio >= 0.9`. **A round-trip test alone would pass an inverted transform;
  this is the control that catches it.**
- **Must also fail on — the transposition control:** swapping the `x` and `y`
  translation components. Must give `ratio >= 0.9`.
- If the inversion control does **not** fail, W2 is not testing the gather and
  the whole deliverable is unverified.

### W3 — wrong-stack detection fires
A sidecar carries enough identity to detect being pointed at a different
bracket.

- **Bar:** loading a sidecar fitted on stack A against stack B is a typed
  refusal, not a warning and not a silent mis-warp.
- **Must fail on — the hardest available case:** `bee-3-cpl`'s sidecar pointed
  at `bee-2-cpl`. Same subject, same 299 frames, same plane geometry, same
  camera. Identity that only checks frame count or geometry will pass this and
  must therefore be rejected as insufficient.

### W4 — a refused frame is not an identity warp
M86 measured real refusals (bee-3-cpl 20.1% of pairs; frames the solve cannot
place). A frame the solve could not place is a frame the merge must **drop**.

- **Bar:** placed and refused are distinct representable states, and the
  consuming API cannot obtain a transform for a refused frame without
  explicitly handling the refusal. A refusal carries a machine-readable reason.
- **Must fail on:** any code path that lets a refused frame be read as
  identity. Follows M84's discipline 586 — emit a refusal, never a degraded
  artefact.

### W5 — the tilted-subject guard is in the code
M86 §13.4 established a single global similarity is the wrong model for a
subject not normal to the axis.

- **Bar:** `strehl align` refuses `highly-angled-ruler-mm-cpl` with a message
  naming the reason, in code and not only in prose.
- **Must fail on:** the guard being satisfied by a comment.

### W6 — the resampler choice is stated, swappable, and (new) measured
M86 §9 recorded the resampler comparison on real frames as **NOT MEASURED**,
and this dispatch warns against laundering that into a shipped default.

- **Bar:** the resampler is an explicit field in the sidecar and swappable at
  the call site; the report states the evidence for the default.
- **Additionally, and not required by the dispatch:** M23 is recorded as having
  measured a **bilinear** resampler manufacturing `R = 0.372` where truth is
  `1.000` by construction on a zero-defocus self-pair. M86 §6.2 measured
  **0.9997** on exactly that construct using Catmull-Rom. If M23's number
  verifies at source, the default is **evidenced**, and §9's "unevidenced" must
  be corrected rather than repeated. **Verify at source before claiming it.**

## 3. What would mean this does not work

- W2's inversion control passing → the gather is untested; ship nothing.
- W2 `ratio > 0.25` with the correct transform → the gather is wrong.
- W3 failing on the bee-2/bee-3 pair → identity is too weak to be safe.
- Round-trip passing on a corrupted file → the reader is not reading.

Any of these is a **negative result to be reported**, not tuned away.

## 4. Out of scope tonight

Estimator accuracy; merge integration itself (`stack.rs`, `merge.rs`,
`merge_cmd.rs`, `main.rs` belong to other live agents); the uniformity question
(answered in M86 §13 and folded).
