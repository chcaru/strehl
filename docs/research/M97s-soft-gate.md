# M97s — wiring the soft admission gate, and pricing the kernel it should use

**Status: shipped behind a flag at `4247607`. Not self-verified.**

M111 measured the "waxy blob" artefact to the merge's admission gate being a
**top-hat**: `Gate::admits` is a hard boolean cutoff on the focus-response gap,
so a pixel one hair either side of the threshold contributes fully or not at
all. Across a smooth region the admitted-set membership flips discontinuously
from pixel to pixel and the output acquires plateaus with hard edges. M111 built
the replacement in `softgate.rs` at `2ae2944` and deliberately stopped there,
because `merge.rs` is a different lane. This milestone is the hand-off: the
integration, its null, and the kernel comparison M111 declined to make and ORCH
handed over rather than deciding.

## 1. What shipped

`crates/strehl-core/src/merge.rs`, behind `STREHL_SOFT_GATE`, default off.

The flag names the **kernel**, not a boolean. `unset` / `""` / `0` / `off` /
`false` are off; `gaussian` and `exponential` select; `1`, `true`, `on` and any
typo are **refused loudly with the bad value named**. Truthy is refused for the
same reason `optics.rs` refuses it: there are two kernels, and "on" does not say
which. Both run on the **same calibrated temperature** the hard gate already
uses, `tolerance() = threshold · √2 · FOCUS_NOISE_SD`; only the shape varies.

`Estimator::new` resolves the env var itself, mirroring `optics::active_profile`.
This is a behaviour change to a constructor with 37 call sites and is worth
knowing about: `merge_cmd.rs` holds the single `Estimator::new` on the real
pass-two render path and belonged to another agent, so this is how the flag
reaches `strehl stack` with **zero edits to that file**. `new_soft` stays
env-free, so parallel tests never mutate global state — the same split
`optics.rs` makes for the same reason.

## 2. The three judgment calls ORCH escalated

**The winner is pinned to weight 1.0** by an explicit `.max(1.0)`. Its gap is
zero so the kernel already returns 1.0; the point is that the invariant no
longer rests on `best_focus[i]` being bit-equal to the winner's response.

**Row 3, the subtle one.** `disagreement()` divides `luma_sum` by `n`. Weighting
the numerator and not the divisor would silently change what the noise
diagnostic *means*, and that diagnostic is load-bearing elsewhere. Both are
weighted, with the reliability-weighted unbiased form
`s² = (Σw·x² − wsum·mean²) / (wsum − wsq/wsum)`. On 0/1 weights `wsum = wsq = n`
and the denominator is exactly `n − 1`, so it reduces **bit-for-bit** to today's
arithmetic. A test asserts exactly that against the hard path.

**`n_eff()` keeps its `&[u16]` return type**; the Kish count arrives as a second
accessor, `soft_n_eff()`. Decided by measurement rather than taste: `n_eff` has
**49 call sites across 10 files**, including `merge_cmd.rs`, eight examples owned
by other milestones, a `u16` dump format, and `assert_eq!` exact-equality
determinism tests. Changing the type ripples outside this lane and breaks the
dump format.

One addition **beyond** §15.6's table, flagged as such: `predicted_sigma` now
divides by the Kish `n_eff` when soft. σ of a weighted mean falls as
`1/√n_eff`, and leaving it on the boolean count would make the predicted noise
disagree with the noise the merge actually produces.

## 3. Facts

**S1 — MEASURED. The null is byte-identical and the switch is proved live on
the same wiring.** Six arms of the corpus byte-freeze suite, each gated on
`subprocess.returncode`:

| arm | `STREHL_SOFT_GATE` | result |
| --- | --- | --- |
| unset | — | exit 0, 5/5 freezes hold, both corpus hashes unchanged |
| off | `off` | exit 0, hashes identical to unset |
| zero | `0` | exit 0, hashes identical to unset |
| gaussian | `gaussian` | freeze moves, `4DC0AAD4…A0EE6FCE` |
| exponential | `exponential` | freeze moves, `587AC130…B26EE427` |
| typo | `gausian` | refused, message names the bad value |

The three off-arms are the null; the three on-arms are the plant that proves the
null was a live probe rather than a disconnected one. The two kernels differ
from each other, so neither is silently falling through to the other.

**S2 — DERIVED. The byte-identical null holds by construction, not by luck.**
`wsum`/`wsq` are left **empty** when the feature is off, exactly as `censor` and
`luma_sum` encode their own features being off, so `value()` takes the original
integer divide and no weighted arithmetic exists on that path.

**S3 — MEASURED. The two kernels are exactly equal at z = 0 and z = 2.**
`−0.5z² = −z` has those two roots, so both read `0.135335283237` at two
tolerances, identical to machine precision. **A comparison anchored at z = 2
measures the anchor, not the kernels.** Inside `z < 2` the **Gaussian** is the
heavier of the two; only beyond `z = 2` is the exponential heavier. That is the
opposite of the intuition "the exponential has the fat tail, so it is heavier",
and it falsified one of my own directional assertions in a test before this was
understood. Pinned as a test.

**S4 — DERIVED. The cutoffs match in weight, not in distance.** Both truncate at
`WEIGHT_FLOOR = 2⁻¹⁶`: the Gaussian at `√(32 ln 2) = 4.7096` tolerances, the
exponential at `16 ln 2 = 11.0904`. Truncating both at one *distance* would
silently turn a comparison of shapes into a comparison of supports.

**S5 — MEASURED. A soft render is reproducible for a fixed chunk length, not
across chunk lengths.** f32 addition is not associative, so `1.0 + (w1 + w2)`
differs from `(1.0 + w1) + w2`; the Kish count drifts by **5.890e-8 relative**,
about 1 ULP, between a whole fold and a two-chunk absorb. The boolean path never
faced this because `n` is an integer. The test measures the drift rather than
asserting bit-equality — which is what its first version did, wrongly.

**S6 — MEASURED. On M111's published 14-rung ladder the Gaussian's prediction
HOLDS and the exponential's is UNRESOLVED — and that is not a verdict on the
exponential.** Separations (seam_lo − texture_hi): Gaussian **+0.299**,
exponential **−0.228**. M111's script says explicitly that overlap is the
ladder's resolution and must not be reported as a refutation. The exponential's
bounds were strictly wider on both populations, which is the signature of a
ladder too coarse for its support: M111 built its rungs for a kernel that is
zero beyond z = 4.71 and stated so, while `z = gate/4` puts the exponential's
cutoff at **gate 44.36**, so the whole of `z = 4 … 16` was one bin across which
the kernel falls by a factor of ~1200. **That is the same defect M111 diagnosed
in its own first run** (one bin spanning a factor of 1800, which "bounded
nothing").

**S7 — MEASURED, and it refuted my own first refinement.** Eight new rungs at
gates 18, 20, 24, 28, 32, 36, 40, 44 tightened the exponential from −0.228 to
−0.084 and left it still unresolved. Decomposing the bound width by bin showed
those eight rungs carry **0.0%** of it, and the **first bin alone carries
100.0%**, in both populations.

**S8 — DERIVED, and it is the reason.** A textured pixel is sharp in one frame,
that frame is the winner, and the winner sits at gap exactly 0 where both
kernels read exactly 1.0 — but the ladder cannot see that it sits at 0 rather
than at 0.0625. Across that first stretch the exponential falls by **0.0606**
against the Gaussian's **0.0020**: **31x looser on identical bins and identical
counts**, entirely because `exp(−z)` has a **cusp** at the origin
(`d/dz = −1`) where `exp(−0.5z²)` is **flat** (`d/dz = 0`).

**S9 — MEASURED. With three rungs at the origin the exponential resolves, and
both kernels HOLD.** On the 25-rung ladder:

| kernel | seam ratio | texture ratio | separation | verdict |
| --- | --- | --- | --- | --- |
| gaussian | 1.60 – 2.13 | 1.07 – 1.29 | **+0.310** | HELD (disjoint) |
| exponential | 1.53 – 1.98 | 1.15 – 1.34 | **+0.191** | HELD (disjoint) |

**The Gaussian wins on both sides of the trade at once**: it raises `n_eff` more
at seams (1.60–2.13 against 1.53–1.98), which is the fix working, and less in
texture (1.07–1.29 against 1.15–1.34), which is the fix averaging in-focus
detail with out-of-focus detail. Raising `n_eff` in texture is blur, and it is
the direction that made `--gate 1e5` destroy the photograph.

**S10 — MEASURED. Every refined interval nests inside its coarse one.** Both
kernels, both populations, all four checks NESTED. Refining tightened the bounds
without moving the estimand, which is the check that my rungs and M111's sample
**one** gap distribution — the failure that would occur if the new rungs had
come from a different binary. Ladder monotonicity: **0 violations of
172,973,136**.

**S11 — DERIVED. The exponential's un-measurability and its blur risk are the
same property.** A kernel that puts weight on frames far from the winner needs a
finer ladder to bound to equal precision. "Puts weight on frames far from the
winner" is exactly the property that risks averaging out-of-focus detail into
sharp pixels. The kernel that was hard to measure was hard to measure *because*
it reaches far.

## 4. What this milestone does NOT claim

- It does **not** claim the soft gate improves the photograph. It claims the
  `n_eff` prediction holds and the flag is live and inert when off. The visible
  outcome is M110's sheet to measure, not mine.
- It does **not** claim the exponential is wrong. Both kernels **HOLD** the
  prediction on a ladder that resolves both. The Gaussian is better on this
  metric by 0.310 against 0.191; that is a margin, not a disqualification.
- The comparison is on **one stack** (`dry-erase-marker-head-cpl`) and one
  metric. It is not a claim about every stack.
- The soft path is **not** default, so no byte-freeze is at risk and the
  regression net is intact.
- `predicted_sigma`'s Kish generalisation is mine, not M111's, and is untested
  against a rendered noise measurement.

## 5. Disciplines

**D1 — An overlap is a statement about your ladder, not about the thing you are
measuring.** Reporting "the Gaussian wins because the exponential is unresolved"
would have been reporting an instrument's blind spot as a property of the world.
The exponential was fine; it needed three rungs at the origin. The Gaussian
still wins, but for a measured reason instead of a fake one.

**D2 — When a refinement finds nothing, that is a measurement, and it belongs in
the record.** Eight renders aimed at the tail carried 0.0% of the width. Keeping
them and saying so is what makes the low-rung result interpretable.

**D3 — Measure where the error lives before spending compute on it.** The width
decomposition is arithmetic on maps already on disk and cost nothing; it
redirected the second refinement from the wrong end of the ladder to the right
one, and three renders then settled what eight had not.

**D4 — Compare by substituting exactly one thing into the other party's
instrument.** The masks, bins, Kish estimator and verdict logic are M111's,
imported and unedited on disk; only `KERNEL` differs. Re-deriving the arithmetic
would have put my code on one side of the scale and M111's on the other, and any
difference could then have been either the kernel or me.

**D5 — Relabel a borrowed artefact before it is cited.** M111's writer tags every
non-top-hat run `gauss`, so an exponential arm writes a file labelled as the
Gaussian's. A mislabelled artefact is how a number ends up attributed to the
wrong thing, and this project has already lost twenty minutes to a phantom agent
for exactly that reason.

**D6 — A checker that reads a correct result as a failure is the same class of
defect as one that reads a broken result as a pass.** The null harness's first
run reported the gaussian arm as "reproducing a default hash". It was counting
every 64-hex string in the output as a hash the render had *produced*, and the
freeze failure report prints the **expected** hash beside the actual one. Fixed
to parse `actual sha256 :` and the HOLDS lines only, and recorded rather than
quietly corrected.

**D7 — A failing test can be the result.** Two of the twelve new tests failed on
first run and both were the test being wrong, not the code. One asserted the
wrong direction across the z = 2 crossing; the other demanded bit-exactness
across a chunked reduction and so discovered S5.

**D8 — Reproduce an `old_str` in full inside the `new_str`.** One edit dropped
the loop's closing braces and `self.frames += 1; Ok(())`. Caught by viewing the
region immediately after editing rather than by trusting the tool's success.

**D9 — A spec's variable names are not free of the target's namespace.** §15.6
uses `w` for the weight; `w` is already the plane width in `fold_inner`.

## 6. Reproduction

```
python experiments/M97-warped-merge/src/softgate_null.py
python experiments/M97-warped-merge/src/refine_for_exponential.py tail
python experiments/M97-warped-merge/src/refine_for_exponential.py low
python experiments/M97-warped-merge/src/width_decomp.py
python experiments/M97-warped-merge/src/kernel_price.py
python experiments/M97-warped-merge/src/verify_commit.py 4247607
```

`cargo test --release -p strehl-core` — 330 passed, 0 failed.
`cargo clippy --release -p strehl-core --lib --all-targets -- -D warnings` —
nothing in `merge.rs`; the four remaining errors are `softgate.rs:443-446`,
committed at `2ae2944` in another lane.
`cargo check --workspace --all-targets` at commit `4247607`, built in a detached
worktree rather than the working tree — exit 0.
