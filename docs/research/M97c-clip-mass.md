# M97c — gate-weighted clip mass: a producer for the residual magenta highlights

**Status:** landed behind no flag, byte-identical on a real render.
**Commit:** `648cb2b` (`crates/strehl-core/src/merge.rs`, `experiments/M97-warped-merge/src/clipmass_mutctl.py`)
**Consumer:** M109, `crates/strehl-cli/src/merge_cmd.rs` — not written here, not mine.

M109 diagnosed why the shipped highlight clip clears about three quarters of the
defect on `dry-erase-marker-head-cpl` and then stops, leaving 0.5060 % of the
frame visibly pink against LibRaw's 0.0061 %. The guard is a post-merge equality
test, `v_c >= ceil_c`, and clip state is a property of the *frame*, not of the
scene point: a sensel pinned in some frames but not others merges strictly below
the ceiling, so the guard never fires while green stays suppressed. It is a
design limit, not a threshold that needs tuning.

This milestone adds the missing producer — per-pixel, per-plane clip state that
survives the merge — and nothing else. It changes no pixel.

## What was already there, and what was actually missing

The interesting finding is how little was missing.

`Estimator::fold_inner` has detected per-sample pinning since M54. The branch is

```rust
if let Some(level) = censor_level && v >= level {
    self.censor[i] |= 1 << if winner { s } else { s + 4 };
}
```

and it already sits **after** the gate's `continue`, so it already runs over the
contributing set alone. Bits `0..=3` mean the winner's own sample was pinned;
`value()` reads those and returns the container maximum, which is what makes
M109's guard fire at all. Bits `4..=7` mean some *other* admitted frame was
pinned — and **nothing reads them.** They have been computed and discarded.

So the 78.98 % partially-pinned population was already being observed at exactly
the right place in exactly the right set. What was missing was that the record is
a boolean OR, which cannot express *how much* of the average was saturated, and
that it was private.

## Facts

- **C1 (MEASURED).** The clip branch in `fold_inner` sits after the gate's
  `continue`, so the accumulator is over the contributing set structurally, not
  by a convention a future editor must remember. Proved by test
  `clip_mass_counts_the_contributing_set_and_not_the_folded_set`, whose fixture
  folds four frames of which the gate admits three.
- **C2 (MEASURED).** `censor` bits `4..=7` are written and never read. `value()`
  branches only on bits `0..=3`. Grepped and confirmed at `merge.rs:1282-1286`.
- **C3 (MEASURED, defect, corrected here).** The `censor` field doc claimed bits
  `4..=7` meant a sample "has been excluded from the sum". The code sums such
  samples unconditionally, and `has_censored_contributor`'s own doc twelve lines
  below already said "a flag, not a behaviour: such samples are still summed".
  The field doc has been corrected. No behaviour changed; the two docs simply
  disagreed and the wrong one was the one nearer the data.
- **C4 (MEASURED).** Pre-warp saturation detection is unreachable from
  `fold_inner`. `merge_cmd.rs:968` calls `align_cmd::warp_frame_in_place`, which
  mutates the frame **in place**, and `merge_cmd.rs:1928` folds that same frame.
  The pre-warp sensel is not out of scope — it has been overwritten. No change
  confined to `merge.rs` can recover it.
- **C5 (DERIVED from C4).** The post-warp `v >= level` test under-counts at
  partially pinned edges, because Catmull-Rom over a partially pinned
  neighbourhood returns fractionally less than the maximum. The under-count is
  the **safe** direction and is retained deliberately — see §Bias below.
- **C6 (MEASURED).** The accumulator is byte-identical on a real render. The
  byte-freeze corpus suite HOLDS on both frozen hashes,
  `D99F5D82…271C76CA` and `119936E6…22BAD709`, unchanged from before the change.
  The two soft-kernel hashes `4DC0AAD4…A0EE6FCE` and `587AC130…B26EE427` are
  also unmoved, so the soft path is untouched as well.
- **C7 (MEASURED).** 3 of 3 planted defects caught by the new tests; the file was
  restored byte-identically from a TEMP copy and re-verified green afterwards.
  Planted: an unweighted numerator, an unweighted denominator, and collapsing
  "never looked" into "found nothing".
- **C8 (MEASURED).** 335 tests pass, 0 fail (330 before, +5). Clippy reports
  nothing in `merge.rs`; the four `float has excessive precision` errors are
  pre-existing at `softgate.rs:443-446`, which is M111's file at `2ae2944`.
- **C9 (DERIVED).** Memory ratchet: 4 planes x 4 bytes x pixels, allocated only
  when censoring is on. At a 3514 x 2344 quad geometry that is 8,236,816 pixels
  and **125.7 MiB**. It is allocated beside `censor` and on the same condition,
  so an uncensored merge pays nothing.

## The API, and the two choices inside it

```rust
pub fn clipped_weight(&self, p: CfaPlane, i: usize) -> Option<f32>
pub fn contributing_weight(&self, i: usize) -> f32
```

**The denominator is `value()`'s own divisor.** `contributing_weight` returns
`wsum[i]` under a soft kernel and `n[i]` under the top-hat — the same expression
`value()` divides by, not a plausible reconstruction of it. This is the whole
defence against M109's own bar B15, which predicted 74.7 % and measured 21.02 %
because it divided by the frames sampled rather than the ~55 the merge actually
averages. Here the numerator is incremented by the same `wt` on the same branch,
and the denominator is fetched from the same place the value uses. The two cannot
drift apart without a test failing, which is C7's M1 and M2.

**The ratio is deliberately absent.** The threshold at which a pinned fraction
should trigger a correction is the consumer's policy and M109's to defend.
Exposing `w_pinned / Σw` would move that decision into the producer, where
M109's controls cannot reach it.

**`Option`, not `0.0`.** "This estimator is not censoring" and "it is censoring
and found nothing pinned" are different claims. Collapsing them would make an
unwired producer indistinguishable from a clean highlight — a `0.000` that is
equally good evidence for a correct null and a disconnected probe, which is the
failure this project has spent the night learning to refuse.

## Bias: post-warp detection, and why the under-count stays

ORCH's instruction preferred pre-warp detection on the sensel. C4 shows that is
unreachable without a change to a file I do not own, so this takes the post-warp
exact `>=` test, and the edge under-count is recorded here as known, bounded and
directional rather than left to be discovered.

It is worth being clear that the under-count is not merely tolerable, it is the
**correct direction**, and the alternative would have been worse:

- The consumer may only ever lower a channel toward neutral. Under-counting
  therefore reaches fewer pixels than ideal but **can never move a pixel that was
  not pinned**. That is exactly the acceptance property this design was chosen
  for over the more principled alternative.
- Every scheme that transports a pre-warp mask to the output grid by dilation or
  any-touched semantics **over-counts**, and would break that property.
- The principled upgrade is neither: interpolate the clip indicator with the same
  Catmull-Rom kernel the values use, giving a fractional pinned mass with no
  threshold and no epsilon. That requires a change in the warp path, which is not
  my file. Recorded as the successor.

No epsilon is applied to the saturation test. An epsilon would trade a known,
bounded, directional bias for an unknown one.

## Disciplines

- **D1.** A null that holds "by construction" still needs a render hash.
  Construction arguments are claims about the code you believe you wrote. C6 cost
  one command and converts an argument into a measurement.
- **D2.** When a threshold belongs to another agent, expose the numerator and the
  denominator and refuse to expose the ratio. A ratio ships a policy.
- **D3.** Return `Option`, not a sentinel `0.0`, wherever "the feature is off" and
  "the feature is on and found nothing" are both reachable.
- **D4.** When a transported quantity can only be biased one way, pick the
  direction that preserves the acceptance property, then write the bias down.
- **D5.** A mutation control must anchor on a unique full-line string and
  hard-error when the anchor does not land exactly once. A mutation that fails to
  apply produces a GREEN indistinguishable from a passing control.
- **D6 (MEASURED, tooling).** On Windows, `subprocess.run([...], env=env)`
  resolves the executable against the **parent** process PATH, not `env["PATH"]`.
  Passing a doctored PATH in `env` does not make `cargo` findable; name the
  executable absolutely. Cost one failed control run.
- **D7 (MEASURED, tooling).** `cargo` indents its status lines by four spaces, so
  a `Select-String '^Finished'` filter matches nothing and reports an empty
  result for a perfectly successful build. This is the false-zero class in my own
  hands: the exit code was 0 and the filtered output was empty, and only one of
  those two facts was about the build. Anchor on the word, not the line start.

## Reproduction

```powershell
$env:PATH="$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:CARGO_TARGET_DIR="C:\dev\strehl-target-m97"
$env:PYTHONIOENCODING='utf-8'
cd C:\dev\blog\death-of-software\projects\strehl

# the five tests
cargo test --release -p strehl-core merge::tests::clip_mass

# the controls that make them evidence (restores from TEMP, never from git)
python -u experiments\M97-warped-merge\src\clipmass_mutctl.py

# the render-level null
python -u experiments\M97-warped-merge\src\softgate_null.py

# that the commit, not the working tree, builds
python -u experiments\M97-warped-merge\src\verify_commit.py 648cb2b
```
