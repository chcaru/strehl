# M97e — wiring the robust election into pass one

Status: **LANDED BEHIND A FLAG, DEFAULT OFF, AND THE FLAG SHOULD STAY OFF.**

The mandate was to connect `robust.rs` — dead code since M89 — to the pass-one
election in `merge.rs`, on the strength of fact 1189: masking the *election*
removes 100 % of the motion-elected pixels where masking the *average* recovers
6.0 %, a 16.7× difference between stages.

The wiring is done, tested, controlled, and null-proven. **The statistic it
carries does not survive its trap.** This document leads with that, because it
is the finding.

---

## 1. The headline: the trap fires 21× harder than the plant

ORCH registered the bar before the build: the plant is a stack with measured
motion (`foam`, the stack fact 1189 was measured on); the **trap** is a
stationary stack where a frame legitimately disagrees because it is *the only
frame that resolves that pixel*. **A gate that fires on the trap is worse than
no gate.**

| arm | stack | frames | pixels whose elected frame changed | output pixels whose value changed |
| --- | --- | ---: | ---: | ---: |
| **TRAP** | `coffee-bean` (stationary, tripod) | 105 | **7.3723 %** | **6.874 %** |
| **PLANT** | `foam` (measured motion) | 100 | **0.3431 %** | **0.314 %** |

**MEASURED.** Both arms rendered back-to-back from one pinned binary with
command lines identical but for the environment variable. The gate moves
**21.5× more of the stationary stack than of the stack it was built for.**

That is not a motion gate. It is not a marginal miss, a threshold that wants
tuning, or a bar that wants narrowing. The quantity is aimed at the wrong thing.

### Two independent instruments agree

The `moved` counter is computed **inside one process**, comparing the gated
election against the ungated election on the same focus fields, so it cannot be
confounded by anything that changes between runs. The changed-pixel fraction is
computed **across two processes** by differencing the two TIFFs. They agree to
within half a percentage point on both stacks (7.37 / 6.87 and 0.34 / 0.31).

That agreement is the evidence that no dependency drifted between the baseline
render and the gated render — which matters, because ten agents share this
working tree. A within-process counter and a cross-process image diff cannot
both be wrong in the same direction by accident.

### The image says the same thing, and says why

`C:\dev\strehl-out\M97e\crops\trap-coffee-bean.png` and `plant-foam.png` —
OFF | SOFT | |diff|×8, 1:1, no resampling, both arms toned by a single scale
derived from the **baseline only** so that the gated arm never gets its own
normalisation.

The crop window is **not hand-picked**. On a change that alters 0.3–7 % of
pixels you can find a flattering crop and a damning crop in the same render, so
the script takes the window of maximum absolute difference by box filter, and
the same rule runs on both stacks.

On the **trap**, the difference is **dense speckle covering the entire textured
subject and exactly zero on the smooth background**. On the **plant** it is a
sparse scatter of isolated specks.

**DERIVED, from that spatial pattern:** the gate is keyed to **fine texture**,
not to displacement. Its firing rate tracks how much resolvable high-frequency
detail a pixel has, which is why the busiest stack in the corpus lights up and
the moving stack does not. This is `robust.rs`'s own central warning, arriving
exactly as its author predicted:

> *"A frame can disagree with its neighbours because it moved **or because it is
> the only frame that resolves that pixel**. A gate that cannot tell those apart
> destroys the product."*

`Arm::Soft` was chosen as default precisely to survive this — it demotes by
weight rather than excluding. It is not enough. Soft weighting still moves 7.4 %
of a stationary stack's elections, and it moves them **on the subject**, which
is the only part of the frame anyone looks at.

### What this does *not* say

It does not refute fact 1189. 1189 measured that motion wins the election; that
remains the diagnosis. What M97e measures is that **the leave-one-out residual
z is not a sufficient statistic for "this frame moved"**, because it cannot
separate a displaced edge from a uniquely-resolved one. The cure was aimed at
the right *stage* (discipline 804) and built on the wrong *discriminant*.

---

## 2. The null

`Arm::Ungated` is the strong null: it runs the entire ring, kernel, z
computation and election machinery and withholds **only** the weight. It
separates "the gate changed the picture" from "the new plumbing changed the
picture".

Unset / `off` / `0` / `ungated` all render **byte-identical to HEAD** across 5
runs, at the registry hashes:

```
119936E656CD4E844F8345F23D8196B6B282C883C4B828318BADC6E222BAD709
D99F5D82337AA2F093202D12677FBD1DE6D78A94761C0DE250020085271C76CA
```

**The null is non-vacuous, and proving that took a second instrument.**
`arm_from_setting` refuses an unknown key, so the harness carries a **typo arm**:
it renders with `STREHL_ROBUST_ELECTION=sotf` and requires the run to **fail**.
A render that *succeeds* with a garbage value is positive proof that nothing
read the variable. On the first pass it succeeded — the null was real and
meaningless at the same time, and I reported it as vacuous rather than bank it.
With the `merge_cmd` seam applied, `sotf` exits 101 and the null means something.

Determinism, measured separately: three identical `foam --limit 100 soft` runs
produced identical `moved`, identical `zmax`, identical `mean|z|`, and
byte-identical SHA-256
`A3D7DA6B7A4668B90BCD18F2F71B5D44A2CDBCF2DE8AB151486BAD121E7FC80C`.

---

## 3. The silent-inertness defect — the most actionable finding here

**This is the part worth keeping regardless of what happens to the gate.**

`z` needs a centred 5-frame window. A merge chunk shorter than `Z_WINDOW` never
produces a centred frame, so **every** frame in it is elected with `z = 0`, the
gate does nothing whatsoever, and the run reports every frame elected, emits no
warning, and produces a perfectly good photograph — the shipped argmax.

`merge_cmd.rs:785` sets `chunk_len = frames.div_ceil(workers)` from a **memory**
budget that knows nothing about this statistic. **MEASURED:**

| run | workers | `chunk_len` | times `z` was scored |
| --- | ---: | ---: | ---: |
| `foam --limit 40` | 13 | 3 | **0** |
| `109MSDCF --limit 22` | 11 | 2 | **0** |
| `foam --limit 100` | 13 | 8 | 395,592,192 |

The first two rendered byte-identical to HEAD. **I very nearly reported that as
"the gate is correctly quiet on a stationary stack."** It was not quiet. It was
disconnected. This is discipline 598 — a control reading exactly `0.000` is as
likely to be a disconnected probe as a correct null — reproduced from the inside
on the first day the code existed.

Fixed at `2cfd8ed`: `RobustPassOne` counts every frame elected from a starved
window, `absorb` sums it across chunks, and `FocusStats::window_starved_frames()`
exposes it. A healthy run reports `2 * Z_HALF * chunks`; a run where the counter
equals `frames_folded` scored nothing. Test
`a_chunk_shorter_than_the_window_gates_nothing_and_says_so` pins it at every
chunk length `n = 1..=12`.

**Any future claim about what this gate did must quote that counter beside it.**

---

## 4. A withdrawn number, and why it is here

An earlier unpaired run reported `foam` at **4.5392 %** moved, which corroborated
fact 1189's independently measured 4.78 % almost exactly. It was extremely
tempting.

**It does not reproduce and I am withdrawing it.** The paired, thrice-repeated,
byte-identical figure is **0.3431 %**. The earlier run's `zn` matches the current
one exactly, so the chunking was identical; its `zmax` (74.21 vs 25.77) and
`mean|z|` (0.940 vs 0.664) do not, so the *inputs* to `z` differed — most likely
the `foam` warp sidecar was regenerated by a sibling agent between the two runs.
I did not hash the dependency tree on that run, so I cannot prove which.

The lesson is the one already in the corpus and I paid for it anyway: **in a
shared tree, a number without a hashed dependency set is an anecdote.** It is
recorded here rather than deleted because a 4.54 % that matched a published 4.78 %
is exactly the kind of agreeable result that gets banked without a second run.

Similarly withdrawn: an earlier `coffee-bean` figure of 10.67 %, from the same
unpaired batch. The paired figure is 7.3723 %. **Both withdrawn numbers pointed
at the same conclusion as the reproducible ones — the trap failing harder than
the plant — which is the only reason the error was survivable.**

---

## 5. What landed

`e028113` (wiring, 5 files) and `2cfd8ed` (starvation counter, 2 files).

- `merge.rs`: `ROBUST_ENV` / `arm_from_setting` / `active_arm`; `RobustPassOne`
  ring; `FocusStats::new_robust`, `new_robust_with` (env-free, so parallel tests
  never mutate process globals), `arm()`, `robust_frames_elected()`,
  `robust_fallbacks()`, `ungated_winners()`, `window_starved_frames()`,
  `fold_with_luma()`, `finish_chunk()`, robust-aware `absorb`, and a loud
  `assert!` in `fold()` when the robust path is active and the caller used the
  wrong entry point.
- `robust.rs`: the z producer — `loo_residual_kernel`, `ResidualOp`, `AffineVar`.
  It was dead because `RobustElection::fold` needs a per-frame `z` and
  `loo_residual_kernel` existed only as two duplicated copies inside
  `crates/strehl-cli/examples/`. Nothing in the library could produce one.
- 11 integration tests (350 → 351 in `strehl-core`; **485 workspace-wide, 0
  failed**), a 4-mutation control at **4/4 RED** with byte-identical restore, and
  the null harness with its typo arm.

The `merge_cmd.rs` seam is **not** applied to the shared tree — that file is
M109's. It is a 3-hunk diff at
`experiments/M97-warped-merge/out/M97e-merge_cmd-seam.diff.txt`, applied and
exercised only in an isolated worktree.

### Two things the seam's owner must know before applying it

1. **Floor `chunk_len` at `Z_WINDOW` when the feature is active, or refuse the
   run.** See §3. `chunk_len` is computed in `merge_cmd.rs`, not in my file.
2. **The pass-one memory planner at `merge_cmd.rs:738` is wrong when the feature
   is on.** The ring holds 10 planes × 4 B × pixels ≈ **330 MB per worker** at
   full geometry, which the planner does not know about. Reducible to 8 planes —
   the regularised ring only needs depth `Z_HALF + 1`.

---

## 6. Recommendation

**Do not ship this on.** Do not ship it on for a subset of stacks either; the
trap and the plant are not distinguishable a priori by anything the merge knows.

Keep the wiring. It is the only path in the library that can carry a per-frame
statistic into the election, and the election is the stage worth 16.7× the
average (fact 1189, discipline 804). What it needs is a **discriminant that
separates a displaced edge from a uniquely-resolved one** — which the LOO
residual demonstrably is not.

The obvious candidate is the one thing the residual throws away: **direction**.
A displaced edge moves *coherently* with its neighbours across the frame; a
uniquely-resolved detail does not. `outlier.rs`'s Schur-complement displacement
detector is a spatially-coherent quantity and is the natural next thing to try
here — not as fact 1189's 6 %-of-the-benefit average-time mask, but as the
election-time discriminant this milestone found missing.

**UNMEASURED, disclosed:** whether the trap's over-firing is driven by
`coffee-bean`'s 11.70 % peak-to-peak exposure drift (M24, the largest in the
corpus) rather than by texture. `--photometric` refuses on `foam` — *"the eroded
photometric region keeps only 622 px (minimum 1024)"* — so the discriminator
cannot be run on the plant, and on `coffee-bean` it returned figures identical to
16 digits, which I could not distinguish from a cache hit. The texture
explanation is favoured because the difference map is spatially locked to the
subject and blank on the background, which an exposure wobble would not be. That
is an argument from a picture, not a measurement.

**Also disclosed:** `pass1_var` is computed once from the *unscaled* noise model,
while under `--photometric` each frame carries its own scaled model. Second
order, but a real inconsistency in the z normalisation.
