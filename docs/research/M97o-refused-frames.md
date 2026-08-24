# M97o — a refused frame is dropped, not fatal

Status: SHIPPED. Milestone M97, defect 2 of the warp-gather audit.

## 1. The defect

`strehl align` can **refuse** a frame: the solve could not connect it to the
rest of the bracket, so its placement is unknown. `warpmap.rs` models this as
`FrameWarp::Refused(why)` and is explicit that a refused frame is *not* a frame
with an identity warp.

The merge did not honour that. `Ctx::field_for` in `merge_cmd.rs` reached
`Ok(FrameWarp::Refused(why))` and called `bail!`, so **one unplaceable frame
aborted the entire render**. On the owner's 299-frame bracket that is a total
loss of the run, and the alternative the code offered was no alternative at
all: merging the frame unregistered would put known-bad geometry into the
election, which is the exact defect alignment exists to remove.

## 2. Honesty first: this changes no pixels on real data

**MEASURED.** Every real sidecar in the repository refuses nothing:

| sidecar | frames | refused |
| --- | ---: | ---: |
| `warpmap-bee-3-cpl.txt` (the owner's stack) | 299 | 0 |
| `warpmap-foam.txt` | — | 0 |
| `warpmap-109MSDCF.txt` | — | 0 |
| `warpmap-ruler.txt` | 79 | 0 |

Live runs agree, reporting `299 placed / 0 refused` and `79 placed / 0 refused`.
Frame-level refusal has never fired on real frames; M86's recorded refusal
rates of 0.0 / 13.2 / 16.2 % are at the **edge** level, not the frame level.

So this is **robustness, not image quality**. It converts a crash into graceful
degradation. It does not address the owner's "those stacks don't look too good
yet" complaint and must not be reported as if it did.

That is also why the bars below are built the way they are: a fix that changes
nothing on real data is indistinguishable from a fix that never ran, unless a
plant proves the measurement can move.

## 3. The change

`crates/strehl-cli/src/merge_cmd.rs` only.

- `Ctx::is_refused(index)` — one predicate, asked by every pass.
- A census before pass one computes the refused set once, prints the dropped
  frame indices, and `ensure!`s that at least one frame survives.
- **Three** call sites skip: pass one, pass two, and the halo pass. All three
  matter. Pass two's noise gate is only meaningful if the winner field it
  compares against was built from the same set of frames, so an asymmetric skip
  would silently corrupt the gate rather than fail.
- Both frame-count assertions now compare against the surviving count.
- The `bail!` in `field_for` is kept, reworded as an invariant: reaching it now
  means a pass forgot its skip.

## 4. Pre-registered bars, and the results

Bars were written before any run (`prereg-D.txt`), including the named
falsification input: *if the frozen bytes move, the fix is wrong and must be
reverted, because dropping zero frames must be a no-op.*

| bar | claim | result |
| --- | --- | --- |
| D1 | frozen renders still produce recorded bytes | **PASS** — 5/5, both rows hold |
| D1b | PLANT for D1: a refusal run must hash differently | **PASS** — `DE0825B75294864E` vs `9AB8BC3AE9F52DDE` |
| D2 | 8 refused of 79 → exit 0 and an image | **PASS** — `EXIT=0`, 49 505 882 B |
| D2b | RED: skips removed → the pre-fix abort returns | **PASS** — `EXIT=1`, "reached field_for" |
| D3 | neither frame-count assertion fires; drops named | **PASS** — "DROPPING 8 of 79 … 0, 10, 20, 30, 40, 50, 60, 70" |
| D4 | all 79 refused → clean refusal, not a garbage image | **PASS** — `EXIT=1`, "refused all 79 frames" |

D1's evidence is the strong form: `coffee-bean-20-gate2-sidecar`, an
**aligned** frozen row, reproduces `119936E6…` with `20 placed / 0 refused`.
Zero refusals in, zero bytes changed.

### Facts

- **T1 (MEASURED).** Frame-level refusal does not occur on any capture in this
  corpus: four sidecars, 0 refused lines each.
- **T2 (MEASURED).** Pre-fix, a sidecar with 8 refused frames aborted the run
  with exit 1 and wrote no file. Post-fix the same input renders 71 frames and
  exits 0.
- **T3 (MEASURED).** Dropping is byte-exact on refusal-free data: the aligned
  byte-freeze row is unchanged.
- **T4 (MEASURED).** Dropping 8 of 79 frames moved mean n_eff 1.154 → 1.131 and
  the coverage scale 0.9708 → 0.9710, so the drop is visible to the merge's own
  statistics and to the coverage solve, not merely to the frame counter.
- **T5 (DERIVED).** Because T1 holds, this ships zero pixel change on the
  owner's stacks. Its value is that a 299-frame render can no longer be lost to
  a single unplaceable frame.

## 5. Method note — the RED control had to mutate the subject

There was no pre-fix binary left to A/B against, and the corpus rule is that a
null must be proven with a plant on the same wiring. The control therefore
removes the three skips from the source, rebuilds, and asserts the failure
returns.

Two safeguards, both of which have burned this project before:

- The original is copied to `$env:TEMP` and restored from **that copy**.
  `git checkout -- <path>` reverts to HEAD and would destroy other agents'
  uncommitted work in a shared tree.
- The mutation asserts its own occurrence counts (2 blocks at one indent, 1 at
  another) and hard-errors with `MUTATION TARGET NOT FOUND` on a miss. A
  `replace` that quietly matches nothing yields a green control that proves the
  opposite of what it claims.

The restore is in a `finally` block, so a mid-run failure cannot leave the
shared working tree mutated.

## 6. What this does not do

- It does not make refusal *more* likely to be correct. If the solve refuses a
  frame it should not have, the frame is now silently dropped instead of loudly
  crashing — arguably a worse failure mode for a solver bug. The stderr line
  names every dropped index precisely so that this stays visible.
- It does not fit a per-frame gain, deconvolve, or change the election.
- It is not a quality improvement. See §2.
