# Capture request: the 407-frame session that unblocks M1, M5 and M9

Status: REQUESTED — awaiting owner
Owner of this file: orchestrator
Raised: 2026-09
Amended: 2026-09 (supersedes the 319-frame and witness-only versions)

---

## AMENDED — read this before shooting

**This request was reviewed and found insufficient as written.** The mechanical
core was right and is unchanged: **stabilisation off, fixed exposure, coplanar
nonperiodic patch, paired A/B passes.** Four things were missing, and the first
fix was later tightened when a second consumer required frame-for-frame
same-focus repeats.

| # | Change | Why |
| --- | --- | --- |
| 1 | **Frame-indexed focus equality required; witnesses retained as a geometry sentinel** | Witnesses alone cannot prove that `A[i]` and `B[i]` share a focus command |
| 2 | **Patch must be physically large enough** for 64 sites | Frame count is not site count |
| 3 | **Flats and darks doubled**, one independent set per pass | One calibration master applied to both passes correlates them |
| 4 | **Explicit settling delay** after each focus move | "1 s interval" is not a settling specification |

**Frame budget: 383 image frames + 24 witness frames = 407 total.** The
319 — 383 step is the calibration doubling and is already approved. The 24
witness frames are short and still useful, but they do **not** by themselves
make the A/B pairing defensible.

**The frame budget is unchanged; the focus-control procedure is not.** If you
have already started, stop and read *Focus nodes and witness frames*. A
different focus ladder cannot be repaired afterwards.

**Before the first frame:** choose one valid focus-control method from *Focus
nodes and witness frames*, record its command state, and take the single test
exposure described in *Before you shoot*. The exposure is fixed for all 407
frames, so getting it wrong spoils the session.

## Why this exists

Three scorecard axes — M1 (detail), M5, M9 — are blocked on captures, not on
code. Two lanes arrived at the required session independently and from
different requirements, and they specified the same 319 frames. That figure was
later reviewed and found insufficient; the session is now **407 frames** (see
*AMENDED* above). This document is the single consolidated request. It is
written to be followed at the bench.

**What is wrong with every capture we currently hold:** in-body stabilisation
was on. IBIS introduces a small per-frame geometric change that is not a rigid
translation, which defeats the local nontranslation gate (measured `0.107703`,
reproduced `0.105202`) and therefore defeats every repeat-pair instrument the
detail axis could be built on. Nothing else about the existing captures is
unsound. **IBIS off is the single defect this session exists to fix.**

## What this session is, and the discipline it requires

The scorecard states that the burned grid and the development-only
high-resolution slide *"may commission a new instrument but may never provide
its scored value"* (`docs/proposals/2026-09-sota-scorecard.md:462-463`).

So the division of labour is:

- **Existing development captures commission the instrument.** They are already
  in hand and already classified development.
- **This session provides the scored value. It is HOLDOUT.**

**Therefore this session must be sealed on arrival and never used for
development, tuning, threshold selection, or debugging.** If any lane renders
it while an instrument is still being tuned, the holdout is burned and the
session has to be shot again. A holdout unit is subject plus uninterrupted
session (`2026-09-sota-scorecard.md:276-295`), so it cannot be partly spent.

## No certified target is needed

An earlier draft of this request specified a certified 10-µm clear-film grid
with a fabricated nonperiodic microdot field. **That is withdrawn.** M1 caps its
claims in **native pixel** units — the registered constraint is *"no frequency
above `0.25 cyc/native px`"* (`2026-09-sota-scorecard.md:465-467`) — and SOTA
here is a *relative* comparator-leading claim against Zerene and Helicon on
identical input. Absolute physical scale is consumed only when converting to
cycles/mm or physical feature size, which is M10's problem, not M1's.

Certification is therefore deferred to a later, much smaller M10 session. A
Pyser-SGI S8 or equivalent 10-µm stage micrometer is the right artifact for
that, and it is a poor M1 target on its own because its narrow repetitive field
carries very little nonperiodic information.

## The target: existing grid plus a coplanar nonperiodic patch

Two things must be in the frame, **in the same plane**:

1. **The microscope grid you already have** — it supplies controlled, regular
   depth structure across the focus sweep.
2. **A fresh nonperiodic patch, coplanar with the grid** — it supplies content
   whose identity the stacker cannot guess. This is the part that matters, and
   it is the part that is currently missing.

The scorecard names the failure this defends against directly: *"a periodic
checker can carry its own answer."* A pure grid is predictable, so a program can
score well on it without resolving anything.

**Anything stable, fine and irregular works.** In rough order of convenience:

- fine matte paper or fabric fibres;
- a dried natural specimen — an insect wing is ideal;
- a DIC-style random-speckle decal, if you happen to have one.

It must not shift between passes, and it must sit in the same plane as the grid
rather than behind it.

**Optional, not required:** an Imatest sinusoidal Siemens star (~$340–630) or a
Thorlabs R1DS1P USAF 1951 target would add a clean frequency ladder. Neither
replaces the nonperiodic patch — the star's radial pattern is deterministic and
the USAF bars are sparse and repeated, so both risk carrying their own answer.

## Frame counts — 407 total

| Block | Frames | Purpose |
| --- | ---: | --- |
| witness 1 | 6 | locked focus at the reset position, immediately before `sw4-A` |
| `sw4-A` | 55 | step width 4, pass A |
| witness 2 | 6 | locked focus at the reset position, immediately before `sw4-B` |
| `sw4-B` | 55 | step width 4, pass B — independent repeat of A |
| `sw1` checker-only | 91 | dense reference. **Never feed this to a stacker.** |
| witness 3 | 6 | locked focus at the reset position, immediately before `sw10-A` |
| `sw10-A` | 27 | step width 10, pass A |
| witness 4 | 6 | locked focus at the reset position, immediately before `sw10-B` |
| `sw10-B` | 27 | step width 10, pass B — independent repeat of A |
| flats A | 32 | calibration for the A passes only |
| flats B | 32 | calibration for the B passes only — **diffuser moved or rotated between the two groups** |
| darks A | 32 | calibration for the A passes only |
| darks B | 32 | calibration for the B passes only |
| **image frames** | **383** | |
| **witness frames** | **24** | |
| **total** | **407** | |

The A/B pairs are the point: two independent passes over identical geometry and
exposure are what make a repeat-pair instrument possible at all.

## Focus nodes and witness frames — frame `i` must match frame `i`

**The problem.** `sw4-A` and `sw4-B` are two complete focus sweeps. Starting both
from an "identical near-focus reset" does **not** guarantee they land on the same
focus positions: focus motor state, magnification and sweep phase can all differ
slightly. If they do, A and B are resolving **different material**, and that
mismatch would look exactly like independent noise to every instrument we would
build on this session. It bites hardest on `sw10`, where the steps are widest.

The capture has two consumers. Repeat-pair FRC needs matched effective focus
support. `V-HEADTOHEAD3` needs the stronger form: frame `i` of A and frame `i`
of B must be independent exposures at the **same commanded focus position**.
The stronger requirement governs this shared capture.

**Witness frames do not prove that.** They can expose displacement, vibration,
reset-focus change and focus breathing at the start, but they do not observe
every command in the bracket. `FocusPosition2`/`FocusDistance2` are too coarse
to certify a fine ladder.

**Choose one valid focus-control method before shooting:**

1. **Preferred: indexed lens-focus control.** Use a controller that can issue
   and record one ordered list of **absolute** lens-focus commands. Run that
   list for A, restore the same approach state, then replay the identical list
   for B. The existing block order, frame budget and registered sw4/sw10
   ladders do not change. Do not substitute a camera rail: translating the
   camera is a different optical/geometry experiment.
2. **Whole-pass camera bracketing, only if demonstrably repeatable.** The camera
   must restore an exact starting focus command—not an approximate visual
   reset—and use identical start command, step width, frame count, direction,
   lens state and frame index in A and B. Record that command state. No
   result-time re-indexing is allowed.

If neither method is available, **do not shoot the A/B sweeps as a claim-bearing
repeat capture**. More witnesses do not repair an unobserved focus command.

**What to shoot:** immediately before each of the four sweep passes, with the
camera at the near-focus reset position and **focus locked** (no bracketing, do
not touch focus), take **6 frames**. Same exposure, same everything, rig
untouched. That is 24 frames total.

**What the witnesses establish:** their within-burst floor and between-burst
geometry are a necessary stability check. Their spatial focus profiles also
feed the separate focus-ladder equality gate. They remain necessary, but neither
their registration nor a matching reset image proves that all later nodes match.

**Do this too, and it costs nothing:**

- **Approach every reset from the same direction.** Always arrive at the reset
  position travelling the same way, so mechanical backlash lands the same way.
- **Do not touch the rig between a witness burst and the pass that follows it.**
  The witness geometry reading applies to that pass only if nothing changed in
  between.

**Input contract, frozen before any new RAW is read:** the command manifests
must match exactly, and a separately commissioned pixel-domain gate must compare
the A/B per-site through-focus response curves and reject systematic
frame-index/peak-position offsets. The witness geometry gate is necessary and
not sufficient. Failure of either focus or geometry invalidates that A/B pair,
although the passes remain ordinary stacks and `sw1` remains a valid dense
reference.

## The patch must be physically large enough

**Frame count is not site count.** 55 frames give one output pair; they do not
give the independent measurement sites an uncertainty estimate needs. The
registered floor is **at least 64 independent, non-overlapping sites**.

**What that means at the bench:** at a 256-pixel tile, 64 sites is an **8 by 8
lattice, roughly 2048 by 2048 pixels of usable patch**, before guard margins.

**So, before you shoot:** frame it, take one test exposure, and check that the
**nonperiodic patch alone** — not the grid, not the background — fills a region of
that order in the frame. If it does not, use a bigger patch or move in. A patch
that is too small will pass a whole-frame check and still leave the session
underpowered.

The patch must also sit where the focus peak is **interior to both sweeps** — it
should come into focus somewhere in the middle of the travel, not at either end.

## Calibration: two independent sets, not one

**Why doubled.** If one flat master and one dark master are applied to both A and
B, they inject **identical** structure into both outputs. Every repeat-pair
instrument works by treating A and B as independent; shared calibration breaks
exactly that assumption, and the residual correlation is indistinguishable from
real detail.

**Flats — 32 for A, 32 for B:**

- Same RAW exposure settings as the session.
- **Defocused or integrating field, not resolved paper.** Paper fibre texture is
  confounded with sensor response and cannot be separated afterwards. Use a
  diffuser, an opal/flat panel, or heavy defocus so the field carries no
  resolvable structure.
- Comfortably **below saturation** at the bright end, but well up the range.
- **Move or rotate the diffuser between the A group and the B group** so the two
  masters do not share the same residual texture.

**Darks — 32 for A, 32 for B:**

- **1 s, ISO 100**, matching the session exposure.
- Shot at the **warmed-up session temperature**, not from cold.
- **Discard the first two frames of each group** — they settle.
- Lens cap on, and no light leaks.

## Settings

**The two that this session exists for:**

- **Body SteadyShot: OFF**
- **Lens OSS: OFF**

**Body and lens:** A7C II, FE 100mm Macro GM with 2× teleconverter at 200 mm.

**Exposure:** M mode, ISO 100, 1 s, f/5.6. Identical for every frame in every
block, including both passes.

**File:** 14-bit lossless compressed RAW. Fixed white balance — pick a value,
do not use auto. EFCS on.

**All off:** DRO, HDR, long-exposure NR, high-ISO NR, pixel shift, AF, and
in-camera auto lens corrections.

**Rig:** tripod, remote or self-timer release. Nothing touching the rig during a
pass.

**Lighting:** flicker-free diffused LED, warmed up at least 15 minutes before
the first frame so output has stabilised. Source polariser plus crossed CPL on
the lens. Matte-white backing behind the target. Tilt the target roughly 1° so
the focus sweep has something to resolve through.

**Sweep:** focus bracket, direction `0 → +`. Use the focus-control method chosen
above. A and B must replay the same absolute command list or the same exact
recorded start and bracket state; an approximate visual near-focus reset is not
enough. **Approach every restored start from the same direction.**

**Settling:** the `1 s` shooting interval is an exposure cadence, **not a
settling specification**. Allow the rig to come to rest after each focus move
before the shutter opens. If the camera exposes immediately on arriving at a
node, use the longest interval the bracketing menu offers rather than the
shortest. Vibration during exposure is indistinguishable from a focus error in
the result.

## What this unlocks, and what it does not

**Unlocks:** M1's replacement statistic, M5, M9, and the commissioning of a
repeat-pair detail instrument on data whose geometry is actually rigid.

**Does not unlock:** M10 depth accuracy, or any claim in cycles/mm or physical
units. Those need the certified scale artifact and a separate small session.

## Interim option, and why it is not recommended

A minimal immediate re-shoot — two 32-frame fixed-focus ISO-100 blocks at two
light levels, plus 32 flats and 32 darks, IBIS off — would reopen fixed-focus
repeat-FRC geometry and null commissioning. **It would not license focus-stack
M1, M5, M9, or the leading candidate instrument.**

Since certification turned out not to be needed, the full 407-frame session
buys much more than the interim shoot. **Shoot the full session only after a
valid replayable focus-control method is selected and the input gate is
frozen.**

## Before you shoot: one test exposure

With the crossed polarisers in place, take a single test frame and check the
`1 s` setting is **neither clipped nor photon-starved**. Crossed polarisers cost
a lot of light, and the exposure is fixed for the whole session — if it is wrong,
every frame is wrong. Check the histogram, not the rear-screen brightness.

While you are there, confirm the nonperiodic patch fills enough of the frame
(see *The patch must be physically large enough*).

## Checks on arrival

All of these are **input-only**: they read RAW frames and never a render, so they
spend none of the holdout.

1. **Frame-indexed focus equality.** Confirm the recorded bracket state and
   start command match exactly for A and B. Apply the separately frozen
   pixel-domain ladder-equivalence gate to the per-site through-focus curves.
   Any systematic frame-index/peak-position offset invalidates that pair.
2. **Witness geometry.** Register witness burst 1 against witness burst 2, and 3
   against 4. This is necessary but does not certify focus-node equality.
   **The threshold is already frozen**, before this session was shot, in
   [`2026-09-node-coincidence-gate.md`](2026-09-node-coincidence-gate.md) — read
   it before taking any reading, and do not restate its bars from memory.
   Precedent: an
   earlier session died at a registration residual of `0.107703` against a `0.10`
   native-pixel bar, so this is a real failure mode, not a formality.
3. **Spectral eligibility, per site.** Confirm the patch carries power out to
   `0.25 cyc/native px` — measured **per site**, not as a frame average, and
   measured as **cross-power attributable to the subject** rather than raw
   single-frame power, which sensor pattern and noise can satisfy on their own.
4. **Site count.** Confirm at least **64 guarded, non-overlapping eligible
   sites** survive. Freeze the site manifest before any render exists.
5. **Clipping and focus.** Reject clipped sites, and verify each retained site
   has a through-focus peak **interior** to both the A and B sweeps.

If the patch is too smooth, or too few sites survive, the session is still fine
for everything else, but the detail axis would need the patch replaced and those
blocks reshot.
