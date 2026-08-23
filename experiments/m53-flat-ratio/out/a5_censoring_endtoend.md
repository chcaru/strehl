# M53 / a5 — `fold_censored` exercised end to end where censoring actually fires

Closes the gap M53 declared open in commit `2b4cff0`: that wiring
`fold_censored` into `merge_cmd.rs:829` had only ever been verified on a stack
with **zero** clipped pixels, so nothing exercised the path that matters.

The full corpus lives at `D:\personal\macro` (READ-ONLY; nothing here writes to
it — file counts were checked before and after each run and were unchanged).

## Method

Two binaries from the same tree, differing in exactly one line:

- **before** — `e.fold(index, &frame, &scratch.reg)`
- **after**  — `e.fold_censored(index, &frame, &scratch.reg, CONTAINER_MAX_DN)`

`merge_cmd.rs` was copied to `%TEMP%` first and restored from there (never
`git checkout --`), `LastWriteTime` bumped after each restore, and each build
confirmed by a real `Compiling strehl-cli` line. After restoring, `git status`
confirmed the file byte-identical to HEAD.

Both outputs are 16-bit linear RGB, 3516 x 2344, one 2x2 quad per pixel.

## Result

| stack | frames | ever clipped | always clipped | changed px | rises | falls |
|---|---|---|---|---|---|---|
| `109MSDCF` | 22 | 0.0000% | 0.0000% | 0 (SHA256 identical) | 0 | 0 |
| `coffee-bubbles` | 19 | 0.5052% (41632) | 0.0088% (724) | 184 (0.0022%) | 185 | 0 |
| `foam` | 100 | 1.1983% (98760) | 0.0000% (0) | 630 (0.0076%) | 638 | 0 |

**MEASURED.** 823 changed samples across two clipping stacks, every one a rise.
M54's "bounded, every change a rise toward the container maximum, bit-exact
no-op where nothing clips" reproduces end to end.

### The direction result is weaker than it looks — state it honestly

`CONTAINER_MAX_DN` is 16383 = 2^14 - 1, the container maximum of a 14-bit
field, and censoring replaces the admitted mean with exactly that value. No
sample can exceed the container ceiling, so the mean it replaces is necessarily
<= 16383 and the substitution can only raise. **The direction is a theorem, not
a contingent measurement, and a run that found no falls could not have found
any.** (DERIVED.)

What the runs *do* have power over is the premise and the wiring:

- a fall would appear if any sample exceeded the container maximum — none did;
- the change could have been inert if the pair were mis-wired — it was not
  (823 samples moved);
- deltas could have exceeded the single-plane bound — none did;
- changed pixels could have escaped the clipped set — they did not.

## Confinement

Changed pixels are a small subset of the ever-clipped set, not a superset:
184 <= 41632 on `coffee-bubbles`, 630 <= 98760 on `foam` (0.64% of it). Nothing
moved that never clipped, which is the property that distinguishes this from
the election-level mask M54 measured and rejected (fact 203), which moved
30-240x more pixels than were clipped and mostly ones that never clipped.

Changed pixels were already bright: minimum before-value 36942/65535 on
`coffee-bubbles` and 31767/65535 on `foam`, the latter sitting at the 98.27th
percentile of an image whose median is 2071. They are scattered specular
points, not one blown highlight — 184 pixels over 164 distinct rows and 138
distinct columns on `coffee-bubbles`.

**Per-channel, the change is almost entirely green**: R 1 / G 184 / B 0 on
`coffee-bubbles`, R 0 / G 628 / B 10 on `foam`. That is mechanical, not
scene-dependent: output green is `(G1 + G2) / 2`, so a pixel is green-changed
if *either* green plane is pinned — twice the exposure of R or B. Every green
delta fell inside the one-plane bound of 65535/2 = 32767.5 (max observed 27712
and 26146), so every change observed was a *single* pinned green plane.

## Size of the bias censoring removes

Undoing the `(G1 + G2) / 2` to recover raw DN, the uncensored merge was
reporting winners whose own sample was pinned as much as **13855 DN below the
pin** — an 85% understatement of a value known to be at or above 16383 DN.
Median 1967 DN. So the correction is rare (0.002-0.008% of pixels) but large
where it applies. (MEASURED.)

## Note on `foam`

`foam` has the corpus's highest clip fraction (1.1983%) yet **zero** pixels
pinned in every frame, where the far less clipped `coffee-bubbles` has 724.
Consistent with `foam` having moved during capture: a scene point that
saturates drifts across the sensor, so it clips in many frames but not the same
pixel in all of them. This is the same stack M52 found cannot reach
`n_eff` = 3 anywhere on the shipped 0.5-4.0 ladder.

## Verification

```
cargo clean -p strehl-cli -p strehl-core
cargo test --workspace
  Compiling strehl-core / strehl-plugin / strehl-raw / strehl-cli
  40 / 127 / 35 / 8 / 1 passed, 0 failed
```
