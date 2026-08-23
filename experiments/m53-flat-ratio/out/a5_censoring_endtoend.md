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

## Caveat corrected: the polarizer was NOT universal, and three of these stacks are bare-lens

**Superseded disclosure.** An earlier version of this section said a
*Breakthrough Photography X4 CPL 67 mm* (Schott B270, MRC16) was in the optical
path for **every frame in the corpus**, and hedged every number below as a
lower bound. **That was wrong.** The orchestrator circulated the universal claim
to five agents before it had been checked; the owner has since confirmed the
filter was fitted for only part of the corpus. The split follows EXIF capture
date cleanly:

| stack | captured | CPL | used in a5 |
|---|---|---|---|
| `109MSDCF` | 17 May | **off** | **yes** |
| `119MSDCF` | 9 May | off | no (see below) |
| `112MSDCF` / `113MSDCF` | 7 May | off | no |
| `coffee-bean` | 10 May | **unknown** — owner cannot recall | no (see below) |
| `coffee-bubbles` | 25 May | **on** | **yes** |
| `foam` | 25 May | **probably on** — owner: *"probably. i doubt i would've removed it. but don't recall specifically"* | **yes** |
| `wrapped-text-1/2`, `bee-1/2/3` | 25 May on | on | no |

`coffee-bean` sits on the off side of the 17-May/25-May boundary but is
**unknown, not off** — the owner does not recall it specifically. `foam` sits
6.5 minutes after `coffee-bubbles` in one session, which is why it is probable
rather than confirmed.

### What survives, and what it applies to

**The one-sided argument itself is unchanged and correct**: suppressing
speculars can only *reduce* the population of pinned samples, so where a
polarizer was fitted the effect sizes are lower bounds. What was wrong is the
**population it was applied to**. Per headline:

| headline | stack | CPL | reading |
|---|---|---|---|
| 0.0000% clipped, SHA256 identical | `109MSDCF` | **off** | **bare lens. No hedge. See below — this one gets stronger.** |
| 0.5052% ever clipped (41632) | `coffee-bubbles` | on | lower bound |
| 1.1983% ever clipped (98760) | `foam` | probably on | lower bound, conditional on `foam` |
| 184 changed px, R1/G184/B0 | `coffee-bubbles` | on | lower bound |
| 630 changed px, R0/G628/B10 | `foam` | probably on | lower bound, conditional |
| min before-value 36942/65535 | `coffee-bubbles` | on | lower bound |
| 98.27th percentile, 31767/65535, median 2071 | `foam` | probably on | lower bound, conditional |
| 13855 DN worst case, median 1967, 0.002–0.008% | `coffee-bubbles` + `foam` | **both on** | lower bound; **does not mix optical paths** |
| 823 changed samples, 0 falls | `coffee-bubbles` + `foam` | both on | direction is a theorem regardless |

**No a5 headline pools across the CPL boundary.** Every effect size comes from
the two on-side stacks; `109MSDCF` contributed exactly zero changed pixels and
so enters no pooled magnitude. The 0.002–0.008% range spans `coffee-bubbles`
and `foam` only, both on the same side.

**The `109MSDCF` result is strengthened, not weakened, by this correction.**
It was shot bare-lens on 17 May, so its 0.0000% clip census **cannot be
attributed to specular suppression**. The bit-exact no-op there is a property
of a genuinely clip-free stack under an unfiltered lens, which is a cleaner
control than the superseded disclosure allowed it to be. (MEASURED; the
re-reading is DERIVED from the capture date, and nothing was re-run.)

The qualitative conclusions were never at risk and are not now: that the change
is confined to the ever-clipped set, that every change is a rise (a theorem),
and that the bias removed reaches 13855 DN, all depend on *which* pixels clip,
not how many.

### Question 194 — is a5 exposed to `coffee-bean`'s unresolvable provenance?

**No. (DERIVED.)** Two independent reasons, and it is worth being precise
because the milestone-wide stack list below is easy to misread:

1. **`coffee-bean` contributes no measurement to a5 — or to M53 at all.** Its
   name occurs in three M53 logs, and in every case inside a canned diagnostic
   block the binary *prints*, quoting M24's photometric-drift survey
   (`a0_before.log:57-58`: "coffee-bean 11.70% -> 2.21"). **M53 never opened a
   `coffee-bean` frame.** a5's runs are `109MSDCF`, `coffee-bubbles` and
   `foam` — the three rows of the result table — and nothing else. This was
   checked by searching every `.md`/`.log`/`.py`/`.rs` under
   `experiments/m53-flat-ratio/`, not assumed from the result table.
2. **The one thing a5 inherits from `coffee-bean` is optics-independent.** a5
   consumes `CONTAINER_MAX_DN`, which M54 established partly on `coffee-bean`
   (`M54-clip-mask-measured.md`: "15360 is not a clip point on `coffee-bean`;
   16383 is"). But `clip.rs:33` declares 16383 as **the 14-bit container
   maximum**, i.e. 2^14 − 1 — an algebraic property of the container, not a
   fitted optical measurement. **A polarizer cannot move 2^14 − 1.** The
   confound therefore does not propagate.

Where a5 *would* be exposed is any headline pooling `coffee-bean` into an
effect size, and there is none.

Nobody has measured the filter's transmission or uniformity, and this milestone
did not either. (Disclosed, not measured.)

## Corpus rename, mid-milestone

The owner renamed five directories in `D:\personal\macro` while this milestone
was running: `131MSDCF` -> `wrapped-text-1`, `133MSDCF` -> `wrapped-text-2`,
`134/135/136MSDCF` -> `bee-1/2/3`. Same files, same counts.

**No stack used anywhere in M53 was renamed.** All five the *milestone* touched
— `109MSDCF`, `119MSDCF`, `coffee-bean`, `coffee-bubbles`, `foam` — keep their
names, and no renamed name appears in any M53 file. **This is the milestone-wide
list, not a5's**: a5 itself measured only `109MSDCF`, `coffee-bubbles` and
`foam`, the three rows of the result table. `119MSDCF` was measured elsewhere in
M53 (the negative control's ISO-50 arm and the kernel sweep) but contributes no
number here. **`coffee-bean` was never measured by M53 at all** — every
occurrence of the name in an M53 log sits inside a canned diagnostic block the
binary *prints*, quoting M24's photometric-drift survey (`a0_before.log:57-58`).
Nothing here was re-run or relabelled. Recorded so a later reader does not
mistake the rename for a change of subject — or this list for a5's measurement
set.

## Verification

```
cargo clean -p strehl-cli -p strehl-core
cargo test --workspace
  Compiling strehl-core / strehl-plugin / strehl-raw / strehl-cli
  40 / 127 / 35 / 8 / 1 passed, 0 failed
```
