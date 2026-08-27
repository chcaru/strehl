# V-DRIFT — alignment accumulation is not what is destroying deep stacks

Lane V-DRIFT. All numbers quoted against `91150f56`, measured with the pinned
acceptance binary `C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe`
(SHA-256 verified to begin `44C2F2CD2E5B2894` before every run that produced a
number here). Source quoted from `git show 9b05d0b7:<path>`.

**Follow-on.** [`V-SELECT.md`](V-SELECT.md) tests the competing hypothesis on the
same two subjects and finds one thing this document did not: registration between
two *independently solved halves* of `bee-3-cpl` diverges 1.90× with depth. That
is not the accumulation refuted below — it is solve-to-solve divergence, and §8
of that document holds it.

---

## Verdict

**The alignment-accumulation hypothesis is refuted for the shipped solve.** Four
independent geometric strands say the same thing, and one of them is a natural
control I did not expect to find. The merge-dilution work in flight is aimed at
the right target.

That is the answer to the question asked. Three further findings are, I think,
worth more to you than the verdict itself, because two of them say the fleet is
reasoning from broken numbers:

1. **The number that justified this lane is a gauge error.** "Deep-stack
   alignment is on record as usable-not-solved at 6.76 px" — 6.76 px is a
   *`coffee-bean`* number (105 frames), and `heldout-px` is not the shipped
   solve's accuracy in the first place. It is the error of a *deliberately
   handicapped* solve trained on short spans only. Quoting it as strehl's
   registration error overstates the error of the thing that actually ships.
2. **Registration difficulty on a deep stack is worst at the START, not the
   end** — the opposite of what an accumulation story predicts, and a genuinely
   new fact about this corpus.
3. **A band-amplitude detail statistic reads a deliberately misregistered merge
   as *sharper*, not softer** — I measured 1.82× on bee-3-cpl. If the scene-ratio
   evidence now being used to indict the merge is band-amplitude-shaped, part of
   it may be an artifact. I did not measure the other lanes' instrument and I am
   not claiming their result is wrong; I am saying this failure mode is live on
   this corpus and I hit it tonight.

**REFUSED:** I could not honestly complete the link from registration geometry
to merge detail. §8 states exactly where the instrument failed and why I am not
reporting the number I have.

---

## What I measured vs what I assumed

**Measured.** Every geometric quantity below: held-out error, cycle floor, total
corner drift, refusal rate, per-window local disagreement, accumulation
exponents, and the determinism control. The warp-sidecar geometry is
independently re-implemented (`wm.py`) and agrees with the product's own printed
figure to +0.0001 px. The dose arms are real merges of real frames through
deliberately corrupted sidecars.

**Assumed.**

- That `cycle_floor` is a fair proxy for "how hard is this frame pair to
  measure". It is the self-inconsistency of the raw pairwise measurements with
  no solver involved, which is the best available bound, but it is a bound and
  not ground truth.
- That the isolated window solves in §6 are good enough to serve as a reference
  for the full solve. They are not perfect. The mitigation is that every window
  is the same size, so *variation across position* still isolates a
  position-dependent effect even if every window carries the same bias.
- That a merge combines, at any output pixel, a contiguous run of neighbouring
  frame indices. This is the argument in §7 and it is an argument, not a
  measurement. I did not instrument the merge's per-pixel frame support.
- I did **not** measure the other lanes' scene-ratio or noise instruments. §8's
  caution is about a failure mode I reproduced on my own arms, not an audit of
  theirs.

---

## 1. Commissioning

Nothing below is trusted before its instrument is shown to be able to fail.

**1.1 The geometry (`wm.py`).** An independent re-implementation of the sidecar
format and the corner-error geometry, deliberately sharing no code with its
subject. It reproduces strehl's own printed `total corner drift` on bee-3-cpl:

| | value |
|---|---|
| strehl printed | 185.266 px |
| `wm.py` independently | 185.266 px |
| delta | **+0.0001 px** |

This took three attempts and the two failures were load-bearing. A naive reading
gave 195.300 px and a second gave 132.508 px. The definition that reconciles is
that `total_drift` is the max over placed frames of the corner error of
`rel(0→i)` against identity, computed on placements referenced to **frame 0
before the re-reference to the middle frame** — despite the CLI printing the
label "frame 0 -> 298". A by-product: the middle reference is worth a measured
**1.40×** (132.508 px worst drift from the middle against 185.266 px from
frame 0).

**1.2 The accumulation detector.** A statistic that cannot see accumulation
cannot report its absence. Forced into a chain by truncating the span ladder to
`--spans 1`, the same detector reads, on bee-3-cpl at N=299:

> log-log slope **0.433**, r² **0.984** — a textbook random walk, growing to
> 118.90 px at separation d=298.

The detector sees accumulation cleanly when accumulation is present. `classify()`
refuses to name a power law at all when r² < 0.5, so a bad fit cannot pass as a
verdict.

**1.3 The plant (`commission_plant.py`).** Three checks, all PASS:

| check | result |
|---|---|
| identity round-trip (shape=none) | worst corner delta **exactly 0** over 299 frames |
| dose recovery, `iid`/`walk` at 0.5 / 4 / 20 px | recovered max within **3.6e-15 px** of request |
| shape separation at matched 20 px envelope | `iid` carries **17.2×** the local error of `walk` at sep 1 |

Dose recovery is measured back out through `wm.py`'s corner geometry, which does
not share a line of code with the writer.

**1.4 The detail metric, both ways.** Required explicitly: a planted degradation
must be detected *and* a planted improvement must score as an improvement. On
d0.tif, 12 sites, 256 px tiles:

| plant | band high vs ref | edge_slope vs ref |
|---|---:|---:|
| blur σ=0.5 | 0.673 | 0.944 |
| blur σ=1.0 | 0.137 | 0.769 |
| blur σ=2.0 | 0.001 | 0.481 |
| blur σ=4.0 | 0.000 | 0.248 |
| sharpen a=0.25 | 1.219 | 1.061 |
| sharpen a=0.5 | 1.439 | 1.112 |
| sharpen a=1.0 | 1.878 | 1.247 |
| sharpen a=2.0 | 2.756 | 1.522 |

Both metrics are monotone **down** the blur ladder and monotone **up** the
sharpen ladder. Both PASS. **This is exactly why §8 is a refusal and not a
result:** the metric is correctly signed and sensitive for real blur and real
sharpening, and it still cannot see misregistration. A single-direction
commissioning would have licensed the number.

**1.5 Determinism.** Two repeats of the shipped ladder on bee-3-cpl returned
bit-identical held-out (13.353 px), cycle floor (2.908 px) and drift
(185.266 px). Unlike V-SPEED, nothing in this lane is a wall-clock quantity, so
the nine other agents saturating this box cannot move these numbers. No
interleaving policy is needed and none was used.

**1.6 The write-up itself.** `verify.py` re-derives every table row in this
document from the raw JSONL, comparing numerically rather than by string match,
with each check pinned to one canonical table row located by a prefix that must
match exactly once inside a named section. It reads **75 checks passed, 0
failed — GREEN**. `verify.py --commission` plants two defects and requires the
verifier to notice both:

| planted defect | required | result |
|---|---|---|
| window 236–298 cycle floor 0.451 → 0.462 | RED | **PASS** |
| iid20 crop factor k 0.9256 → 0.9456 | RED | **PASS** |
| unmutated document | GREEN | **PASS** |

The plants hard-error with `MUTATION TARGET NOT FOUND` if their anchor does not
land, so a green control cannot be produced by a mutation that silently missed.

---

## 2. The shipped solve is not chain-like, which is the whole point

`strehl align` fits a **similarity ladder** over spans `1 2 4 8 16 32 64 96 128`
against the **middle** frame. That is precisely the design that prevents chain
accumulation. `align_image_stack` — the comparator whose sequential pairwise
alignment I blamed for the depth-dependent *speed* gap in V-SPEED §7.4 — is
chain-like. **strehl is not, and the two must not be reasoned about as if they
were the same shape.**

Truncating the ladder shows what the long spans buy. bee-3-cpl, N=299:

| spans | held-out px | cycle floor px | drift px | refused % |
|---|---:|---:|---:|---:|
| 1 (pure chain) | – | – | 66.4 | 0.0 |
| 1,2,4 | – | 0.264 | 112.1 | 0.0 |
| 1..16 | – | 0.638 | 228.8 | 0.1 |
| 1..32 | – | 1.158 | 256.8 | 2.7 |
| 1..64 | 11.687 | 1.756 | 237.2 | 7.8 |
| **full 1..128 (shipped)** | **13.353** | **2.908** | **185.3** | **16.2** |

And the accumulation shape, measured as corner error against the base frame as a
function of separation d:

| spans | d=1 | d=149 | d=298 | slope | r² | verdict |
|---|---:|---:|---:|---:|---:|---|
| [1] | 10.52 | 95.83 | 118.90 | **0.433** | 0.984 | RANDOM WALK |
| [1,2,4] | 8.08 | 63.19 | 79.52 | 0.504 | 0.937 | RANDOM WALK |
| [1..16] | 6.77 | 28.62 | 43.68 | 0.753 | 0.780 | SYSTEMATIC DRIFT |
| [1..64] | 5.05 | 36.63 | 51.97 | 0.829 | 0.800 | SYSTEMATIC DRIFT |

> **Careful with `cycle_floor` across these rows.** It is *not* a subject
> constant. It rises as longer and harder spans are added to the measured edge
> set (0.264 px with spans 1–4 against 2.908 px with the full ladder), because
> the ladder is being asked harder questions, not because the subject moved.
> Only compare cycle floors between runs with the **same span set**.

---

## 3. Error tracks measurement difficulty, not chain length

bee-3-cpl, shipped ladder, varying only `--limit` — same subject, same optics,
same reference strategy, only the chain gets longer:

| limit | held-out px | cycle floor px | drift px | refused % | wall s |
|---:|---:|---:|---:|---:|---:|
| 33 | – | 1.116 | 42.2 | 0.7 | 6.5 |
| 63 | – | 2.033 | 76.5 | 7.0 | 12.3 |
| 105 | – | 2.658 | 109.8 | 11.7 | 18.4 |
| 150 | 11.545 | 2.535 | 131.5 | 15.1 | 23.3 |
| 205 | 12.190 | 2.884 | 165.7 | 15.9 | 41.8 |
| 250 | 12.078 | 2.992 | 179.5 | 15.8 | 78.1 |
| 299 | 13.353 | 2.908 | 185.3 | 16.2 | 52.6 |

Held-out error grows **+15.7%** from L=150 to L=299. The cycle floor — the
noise floor of the raw measurements, with no solver involved — grows **+14.7%**
over the same range. The ratio between them is flat:

| limit | held-out / cycle floor |
|---:|---:|
| 150 | 4.554 |
| 205 | 4.226 |
| 250 | 4.037 |
| 299 | **4.592** |

**P1. Held-out error on bee-3-cpl is riding the measurement noise floor, not
accumulating on top of it.** Nearly all of the growth with depth is growth in
how hard the frames are to measure at all. (bee-3-cpl, N=150→299, shipped
ladder.)

`heldout` is `None` below L≈150 on this subject: too few surviving edges with
span ≥ 40 and `used ≥ 12`. That is a property of the metric, not a failure.

---

## 4. The second subject settles it

`flower-bud-alone-cpl`, 205 frames, shipped ladder, same sweep:

| limit | held-out px | cycle floor px | **drift px** | refused % |
|---:|---:|---:|---:|---:|
| 33 | – | 0.166 | 0.795 | 0.0 |
| 63 | – | 0.153 | 0.778 | 0.0 |
| 105 | 0.150 | 0.131 | 0.636 | 0.0 |
| 150 | 0.155 | 0.103 | 0.737 | 0.1 |
| 205 | 0.352 | 0.052 | 0.715 | 0.1 |

**P2. `flower-bud-alone-cpl` is a 205-frame stack whose total corner drift is
0.715 px — sub-pixel — and flat across depth (0.636–0.795 px from L=33 to
L=205).** Against bee-3-cpl's 185.3 px that is a **260× spread in the alignment
variable across two deep stacks from the same corpus.**

This is the strongest single result in the lane, and it is a natural control I
did not have to build. If registration accumulation were what makes deep merges
soft, then a 205-frame stack with essentially no registration error should not
be soft. **Any depth-dependent quality loss measured on `flower-bud-alone-cpl`
cannot be alignment, because there is no alignment error there to blame.** That
is a cheap, decisive test and it is now available to whoever owns the quality
instrument — it needs no new tooling, only the existing scene-ratio measurement
pointed at this subject at two depths.

The cycle floor *falls* with depth here (0.166 → 0.052 px), which is the
signature of a stack shot without meaningful focus breathing: more frames, more
mutually consistent evidence, a better-conditioned solve.

**4.1 An attempt at the depth test on this subject, reported with its confound.**
Since `flower-bud-alone-cpl` has no alignment error to blame, a depth comparison
on it should isolate the merge. I merged it at N=32 and N=205 — and the coverage
crop came out at k=0.9969 and k=0.9971, a 0.02% difference, so the two are very
nearly a matched-crop pair.

| sites chosen on | arm | band high | edge slope | mean DN |
|---|---|---:|---:|---:|
| fl32 mid band | fl32 (N=32) | 1.000 | 1.000 | 13951 |
| fl32 mid band | fl205 (N=205) | **1.364** | **1.404** | 15474 |
| fl205 mid band | fl32 (N=32) | 0.576 | 0.083 | 13951 |
| fl205 mid band | fl205 (N=205) | 1.000 | 1.000 | 15474 |

**This is not a clean test of merge dilution and I am not offering it as one.**
Two confounds, both in the open: N=32 covers roughly a sixth of the focus travel,
so the reverse-selection row is reading focus coverage rather than merge
behaviour; and the two arms differ in mean level by 1.109×, which scales band
amplitude directly. Normalising for level still leaves the deeper merge ahead at
the shallower merge's own sites (1.23× band high, 1.27× edge slope).

All it says is the weak, honest thing: **on this subject, at sites the 32-frame
merge covers, the 205-frame merge is not softer.** It does not contradict the
63-against-32 result, which used a matched focus range and a different
denominator — a design mine does not reproduce.

**The clean version is cheap and I did not have time for it.** Merge a contiguous
64-frame window, then merge every second frame of that *same* window (N=32,
identical focus range, identical coverage, no k difference). That is depth with
coverage held constant, and on `flower-bud-alone-cpl` it is depth with alignment
held constant too, because §4 has already measured alignment error there at
0.715 px. It is two merges and it isolates dilution from everything else.

---

## 5. Difficulty is strongly non-uniform, and inverted from the hypothesis

Five isolated 63-frame window solves at five positions in bee-3-cpl:

| window (global frames) | cycle floor px | local drift px | refused % |
|---|---:|---:|---:|
| 0–62 | **2.033** | 76.5 | **7.0** |
| 59–121 | 1.295 | 59.4 | 0.0 |
| 118–180 | 1.077 | 61.9 | 0.0 |
| 177–239 | 0.641 | 42.8 | 0.6 |
| 236–298 | **0.451** | 21.0 | 2.5 |

**P3. The start of a deep stack is 4.51× harder to register than the end**
(cycle floor 2.033 px against 0.451 px; local drift 76.5 px against 21.0 px over
63 frames each). (bee-3-cpl, N=299, 63-frame windows, shipped ladder.)

This separates *accumulation* from *difficulty*, which was the second thing you
asked for. The near-focus end of a focus bracket changes magnification fastest
per frame, so its frames are the hardest to relate. An accumulation story
predicts error growing *along* the chain; what is actually there is a difficulty
gradient running the *other* way.

---

## 6. The decisive measurement

Median disagreement, in plane pixels, between the **full 299-frame solve** and an
**isolated local solve** of the same frames, for frame pairs separated by `sep`
indices. This compares geometry to geometry and never touches image sharpness,
so it has none of the focus-coverage confound discussed in §7.

| window (global) | cycle | sep 1 | sep 2 | sep 4 | sep 8 | sep 16 | sep 32 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0–62 | 2.033 | **0.552** | 0.891 | 1.854 | **3.704** | 7.296 | 14.265 |
| 59–121 | 1.295 | 0.447 | 0.808 | 1.592 | 3.223 | 6.627 | 12.470 |
| 118–180 | 1.077 | 0.366 | 0.588 | 1.078 | 2.260 | 4.592 | 9.213 |
| 177–239 | 0.641 | 0.422 | 0.637 | 1.140 | 2.049 | 4.079 | 8.855 |
| 236–298 | 0.451 | **0.325** | 0.522 | 0.715 | 1.267 | 2.671 | 5.317 |

The reference frame is 149, at the centre. **Windows 0–62 and 236–298 are
equidistant from it — both 118 frames away, identical registration path
length.** Accumulation predicts they should be equally bad, and symmetric about
the middle window.

They are not. They differ by **2.92×** at sep 8 (3.704 px against 1.267 px), and
the column is **monotone decreasing across the stack, not symmetric**. It tracks
the cycle floor (4.51× spread), which is difficulty, and not the distance from
the reference, which is path length.

**P4. At matched registration path length, local geometric disagreement in the
shipped solve differs by 2.92× between the two ends of bee-3-cpl, and tracks
measurement difficulty rather than distance along the chain.** (bee-3-cpl,
N=299, 63-frame windows, sep=8, shipped ladder.)

This is the refutation. Path length is held constant and the effect survives at
full strength, driven by something else.

---

## 7. Why accumulation could not have blurred the merge anyway

This is an argument, flagged as one, and it is why §6 measures what it measures.

At any output pixel a merge combines only the frames in which that pixel is in
focus — a contiguous run of neighbouring indices. So the quantity a merge is
exposed to is **relative misregistration between frames close together in
index**, not absolute placement error.

A slowly accumulating error moves neighbouring frames *together*. It is a smooth,
low-frequency warp: it displaces the output, it does not blur it. Only local
relative error can blur. Accumulation and blur are therefore not the same
currency, and the 185.3 px of "total drift" on bee-3-cpl — the number that looks
alarming — is almost entirely the harmless kind. The harmful kind is the sep 1–8
columns in §6, and those are **0.33–3.70 px**.

> **A note on the experiment you proposed.** Contiguous-32 against spanning-32 at
> matched N has a confound: a contiguous window covers ~1/9 of the depth, so it
> is sharp in one thin slice while the spanning set is sharp everywhere but
> sparsely. A global sharpness measure would be reading focus coverage, not
> registration path length. If it is run, the metric must be restricted to a
> region both arms cover. §6 avoids the confound entirely by comparing geometry
> to geometry, and §8 attacks the same question by planting known misregistration
> into a real merge.

---

## 8. REFUSED — the dose-response from geometry to detail

I built this and I am not reporting the headline number from it, because the
instrument failed its positive control at maximum dose.

**The design.** Merge bee-3-cpl five times through deliberately corrupted warp
sidecars, in matched pairs. `walk` is a random walk in translation — large
*absolute* excursion, tiny *local* error, i.e. what pure accumulation looks
like. `iid` is independent per-frame translation — the same absolute envelope,
so the same coverage crop, but large local error. Translation-only, so the dose
is exactly `|db|` in plane pixels with no dependence on which corner is asked.
Each arm got its own `STREHL_CACHE_DIR`, because the shared cache at
`%LOCALAPPDATA%\strehl\warpmaps` is what `strehl stack` reads by default and
nine other lanes are running on this machine. All arms `--linear-srgb
--demosaic`, per BUILD-TRIAGE.

**What the arms actually were, and whether they could be measured at all:**

| arm | shape | abs max px | local sep 1 px | local sep 8 px | k | NCC vs d0 | peaks at wall |
|---|---|---:|---:|---:|---:|---:|---:|
| d0 | shipped | 0.00 | – | – | 0.9321 | 1.000 | – |
| iid2 | iid | 2.00 | 0.610 | 0.642 | 0.9314 | 0.982 | 0/24 |
| walk20 | walk | 20.00 | 1.350 | 3.928 | 0.9281 | 0.812 | 0/24 |
| iid20 | iid | 20.00 | 6.095 | 6.425 | 0.9256 | 0.728 | 0/24 |
| walk60 | walk | 60.00 | 4.051 | 11.785 | 0.9155 | 0.628 | **6/24** |
| noalign | alignment off | 232.70 | – | – | 1.0000 | 0.484 | **13/24** |

**Why the refusal.** The detail statistic, commissioned and passing in both
directions on known blur and known sharpening (§1.4), reads planted
misregistration like this:

| arm | band high vs d0 | edge_slope vs d0 |
|---|---:|---:|
| iid2 (0.61 px local) | **1.159** | 0.981 |
| walk20 (1.35 px local) | **1.654** | 0.937 |
| iid20 (6.10 px local) | **1.825** | 0.964 |
| noalign (232.7 px, unregistered) | **0.992** | **0.982** |

Two things are wrong and either alone is disqualifying.

1. **The sign is inverted.** Planting 20 px of misregistration *raised* high-band
   amplitude to 1.82× the undamaged merge. Misregistration doubles edges and
   stops the merge cancelling noise; both add high-frequency energy. BUILD-TRIAGE
   names this failure in advance and quantifies it at 2.05× from broadband noise
   alone. A metric that rises under damage cannot be used to argue damage is
   small — the sign is wrong before the magnitude is read.
2. **The positive control at maximum dose is not a control.** `noalign` combines
   299 frames with 232.7 px of drift and no registration at all — an output that
   must be destroyed — and reads 0.982 of the good merge on edge slope. The
   reason is in the last column: **13 of 24 of its correlation peaks sit against
   the wall of the 64 px search box.** The partner window was never found, so
   that row is the difference between two different pieces of scene, not a
   measurement of damage. `walk60` is compromised the same way at 6/24. I am
   reporting them struck out rather than deleting them, because the fact that a
   maximum-dose control could not be matched is the finding.

**What does survive.** `walk20` and `iid20` are both cleanly matched (0/24 at
wall) at an identical 20 px absolute envelope and differ 4.5× in local error.
That is the matched pair the whole design was for:

**P5. At an identical 20 px absolute displacement envelope on bee-3-cpl (N=299),
the arm with 4.5× more *local* relative error is the more damaged one — NCC 0.728
against 0.812, and higher ghosting energy, 1.82× against 1.65× band high.**
Absolute drift is held constant; local error moves the damage. This is one
matched pair, on one subject, and I am calling it directional support for §7's
argument and not a dose-response curve.

**What I therefore cannot tell you:** the number of plane pixels of local
registration error at which detail retention falls to the `bee` figure of 0.180.
Building that needs a detail statistic that can see ghosting, which neither band
amplitude nor edge slope can. A structural measure — the NCC column above is
already behaving like one, monotone from 0.982 down to 0.484 across the whole
dose range — is the obvious candidate and I did not have time to commission it.

**The caution this raises for tonight.** I have measured, on this corpus and this
merge, a **1.82× false high-band gain produced by pure geometric damage**, and a
catastrophically misregistered merge reading **0.99** of a good one. If the
scene-ratio evidence indicting the pyramid merge is band-amplitude-shaped, then
the direction of its bias is worth checking before the merge fix is credited:
strehl reading *low* on such a statistic against a comparator is consistent with
strehl being *smoother* — which is also what an 11.9–15.6× noise win means. I
have not measured that instrument and I am not claiming the result is wrong. I am
saying this exact failure mode is live on this corpus, I walked into it tonight,
and it takes one both-ways commissioning to rule out.

---

## 9. Corrections to the premises this lane was launched on

**C1. 6.76 px is a `coffee-bean` number, not a deep-stack number.** The
bee-3-cpl figure is **13.353 px** (measured here) / 13.578 px (M110). Already
flagged in `BUILD-DEFECT.md:2114` and `M110-track-jitter.md:33`.

**C2. `heldout-px` is not the shipped solve's registration accuracy.** Per
`align_cmd.rs:618`, `heldout_error` trains on spans < 40 and tests on held-out
spans ≥ 40. It is the error of a *deliberately handicapped, chain-like* solve —
exactly the failure mode the shipped ladder exists to avoid. The shipped solve
uses all spans to 128 and is better than its own held-out figure. **Quoting
6.76 px or 13.353 px as "strehl's alignment error" is a gauge error, and it is
the number that motivated this lane.**

**C3. M110's `smooth` claim is stale at this pin.** M110 records that the track
prior "defaults to 0.0 and no product path sets it". At `9b05d0b7` the prior is
**ON by default at lambda=1.0** since BUILD-SHARP; `STREHL_SMOOTH=0` restores the
free solve bit-exactly, and `STREHL_SMOOTH_HUBER` defaults to 1.0 px. Every solve
in this document is therefore the shipped default. I verified no `STREHL_*`
variables were set in my environment.

**C4. M110 does not already answer this question.** Its B6 "INVISIBLE" result
concerns **jitter**: its roughness prior explicitly *preserves* low-frequency
modes (H≈0.93 at a 10-frame period). Accumulation is a low-frequency mode. M110
tested the high-frequency component and left this one open.

**C5. A frame-count discrepancy, noted not resolved.** The brief gives
`113MSDCF` as 33 frames; on disk it holds **63** `.ARW` files (`119MSDCF` holds
33). If the quality lane subset it, fine — but per §127 a ratio names its frame
count, and these two do not currently agree.

---

## 10. What would change my mind

- A merge whose per-pixel frame support is *not* a contiguous run of indices
  would break §7's argument and put absolute drift back in play. I did not
  instrument this.
- A deep subject with a flat cycle floor *and* growing held-out error would
  separate accumulation from difficulty in the direction I did not find. Neither
  bee-3-cpl nor flower-bud-alone-cpl is one.
- A commissioned structural detail metric showing that 0.33–0.55 px of local
  disagreement costs the detail the `bee` scene ratio says is missing. §8 is
  where that work stops, and it is the honest boundary of this lane.

---

## Reproducing

```
python experiments/V-DRIFT/wm.py                  # geometry commissioning, +0.0001 px
python experiments/V-DRIFT/commission_plant.py    # plant commissioning, 3 checks
python experiments/V-DRIFT/commission_detail.py   # detail metric, both ways
python experiments/V-DRIFT/sweep.py   --subject bee-3-cpl --dir D:\personal\macro\bee-3-cpl \
                                      --limits 33 63 105 150 205 250 299 --tag depth  <out.jsonl>
python experiments/V-DRIFT/window.py  --subject bee-3-cpl --dir D:\personal\macro\bee-3-cpl \
                                      --count 63 --starts 0 59 118 177 236           <out.jsonl>
python experiments/V-DRIFT/wincmp.py  <full.warpmap.txt> <windows.jsonl>   # §6, the decisive one
python experiments/V-DRIFT/dose.py    --keep-baseline                      # §8 merges
python experiments/V-DRIFT/matchcheck.py                                   # §8 wall-peak check
python experiments/V-DRIFT/detail.py
python experiments/V-DRIFT/verify.py                # 75 checks, re-derived from raw JSONL
python experiments/V-DRIFT/verify.py --commission   # plant defects, require RED
```

`sweep.py` hashes the binary and refuses to run unless SHA-256 begins
`44C2F2CD2E5B2894`. `--spans` takes **one value per occurrence**
(`--spans 1 --spans 2 --spans 4`); a space-separated list exits 2. Always pass
`--out` to `strehl align`, or it writes into the shared warpmap cache that
`strehl stack` reads and poisons every other lane on the box.
