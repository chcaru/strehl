# Capture request: the 383-frame session for M1, M5 and M9

Status: REQUESTED — awaiting owner
Owner of this file: orchestrator
Raised: 2026-09
Amended: 2026-09 (supersedes the 319-frame and interim 407-frame versions)

---

## AMENDED — read this before shooting

**The 319-frame request was reviewed and found insufficient.** The mechanical
core was right and is unchanged: **stabilisation off, fixed exposure, and a
coplanar nonperiodic patch.** The acquisition and calibration instructions below
replace the version already sent.

| # | Change | Why |
| --- | --- | --- |
| 1 | **Take A and B back-to-back at every focus node** | This guarantees that `A[i]` and `B[i]` share one focus command |
| 2 | **Patch must be physically large enough** for 64 guarded sites | Frame count is not site count |
| 3 | **Use separate 32-flat/32-dark groups for A and B** | Shared calibration structure correlates the two realizations |
| 4 | **Wait after every focus move before exposing** | A 1 s shooting interval is not a settling delay |

**Frame budget changed from 319 to 383.** The focus data remain 255 frames.
The old plan allowed four 16-frame calibration groups; this request uses four
32-frame groups instead, adding 64 frames and leaving reserve after dark-frame
settling discards. The primary paired-node protocol needs no witness frames:
**255 focus frames + 128 calibration frames = 383 acquired session frames.**
The four discarded settling darks remain part of that acquired-frame total.

If the body cannot take two exposures at one focus node before advancing, use
the frozen whole-pass fallback described below. That fallback adds 24 witness
frames and is **407 total**, not 383.

**Before the first session frame:** confirm how you will take two exposures
without moving focus, then take the throwaway test exposure described in
*Before you shoot*. Do not start and improvise the pairing halfway through.

## Why this exists

Three scorecard axes — M1 (detail), M5, M9 — are blocked on captures, not on
code. Two lanes arrived at the required session independently and from
different requirements, and they specified the same 319 frames. Review retained
their 255 focus frames but doubled the four calibration groups, making the
primary session **383 frames**. This document is the single consolidated
request. It is written to be followed at the bench.

**What is wrong with every capture we currently hold:** in-body stabilisation
was on, and there are no calibrated frame-for-frame same-focus repeats. IBIS
introduces a small per-frame geometric change that is not a rigid translation
(measured `0.107703`, reproduced `0.105202`). This session fixes both defects:
stabilisation is off, and every claim-bearing focus node has two exposures.

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

It must not shift at any point in the session, especially between A and B at a
node, and it must sit in the same plane as the grid rather than behind it.

**Optional, not required:** an Imatest sinusoidal Siemens star (~$340–630) or a
Thorlabs R1DS1P USAF 1951 target would add a clean frequency ladder. Neither
replaces the nonperiodic patch — the star's radial pattern is deterministic and
the USAF bars are sparse and repeated, so both risk carrying their own answer.

## Frame counts — 383 total

| Block | Frames | Purpose |
| --- | ---: | --- |
| `sw4` paired A/B | 110 | 55 focus nodes, two back-to-back exposures at each node |
| `sw1` checker-only | 91 | dense reference. **Never feed this to a stacker.** |
| `sw10` paired A/B | 54 | 27 focus nodes, two back-to-back exposures at each node |
| flats A | 32 | calibration for every A exposure |
| flats B | 32 | calibration for every B exposure; **move or rotate the diffuser first** |
| darks A | 32 | calibration for every A exposure |
| darks B | 32 | calibration for every B exposure |
| **total** | **383** | |

Within each paired block, the file order is
`A1, B1, A2, B2, ...`. Build stack A from the odd exposures and stack B from
the even exposures. Do not reorder by measured sharpness or metadata.

## Focus nodes — take the pair before advancing

For each of the 55 `sw4` nodes and each of the 27 `sw10` nodes:

1. Move to the next focus position in direction `0 -> +`.
2. After focus motion has stopped, wait **at least 2 full seconds** before
   the next exposure. If the controller offers 1 s or 3 s, choose 3 s.
3. Take exposure A.
4. Without moving focus, refocusing, or touching the rig, take exposure B.
5. Only then advance to the next focus position.

The second exposure does not need another settling delay because focus has not
moved. Keep AF off. Before each ladder, approach the near-focus reset from the
same direction so backlash is taken up the same way. Use a tethered controller,
indexed lens-focus control, or a manual sequence that can hold one focus command
for both exposures. Do not substitute a camera rail.

### Fallback only if paired-node capture is impossible

If the body cannot take A and B before advancing focus, stop and use four whole
passes: `sw4-A` 55, `sw4-B` 55, `sw10-A` 27, and `sw10-B` 27. Approach every
reset from the same direction and repeat the exact start command, step width,
frame count, direction, and lens state. No result-time re-indexing.

Immediately before each fallback pass, lock focus at the reset and take six
witness frames. Follow
[`2026-09-node-coincidence-gate.md`](2026-09-node-coincidence-gate.md) and the
input-only ladder-equivalence check below. The 24 witnesses make the fallback
**407 frames total**. A witness pass alone does not prove node equality; if
either frozen gate fails, that A/B pair is not usable as a repeat pair.

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

Capture all 32 frames in each group; the first-two discard is included in that
count, leaving 30 darks per realization. In the primary paired-node protocol,
apply the A flat and dark only to odd-numbered exposures and the B flat and dark
only to even-numbered exposures. In the fallback, apply A calibration to the
complete named A passes and B calibration to the complete named B passes. Never
build one master and apply it to both.

## Settings

**Required stabilisation settings:**

- **Body SteadyShot: OFF**
- **Lens OSS: OFF**

**Body and lens:** A7C II, FE 100mm Macro GM with 2× teleconverter at 200 mm.

**Exposure:** M mode, ISO 100, 1 s, f/5.6. Identical for every session frame.

**File:** 14-bit lossless compressed RAW. Fixed white balance — pick a value,
do not use auto. EFCS on.

**All off:** DRO, HDR, long-exposure NR, high-ISO NR, pixel shift, AF, and
in-camera auto lens corrections.

**Rig:** tripod, remote or self-timer release. Nothing touching the rig during
a paired block or fallback pass.

**Lighting:** flicker-free diffused LED, warmed up at least 15 minutes before
the first frame so output has stabilised. Source polariser plus crossed CPL on
the lens. Matte-white backing behind the target. Tilt the target roughly 1° so
the focus sweep has something to resolve through.

**Sweep:** direction `0 → +`. For `sw4` and `sw10`, take A then B at every node
before advancing, exactly as described in *Focus nodes*. For `sw1`, take one
exposure per node. Approach every near-focus reset from the same direction.

**Settling:** after every focus move, wait at least **2 full seconds after lens
motion stops before the next exposure**. This applies to each `sw1` frame, each
frame in a fallback whole pass, and the first witness after moving to reset. If
the controller offers 1 s or 3 s, choose 3 s. The old 1 s shooting interval is
not a substitute. Paired-node exposure B needs no second delay because focus
did not move after A.

## What this unlocks, and what it does not

**Unlocks:** the independent same-focus evidence needed by the head-to-head
physical-detail question, M5, M9, and any future M1 instrument that requires
paired realizations.

**Does not by itself provide:** an admitted M1 detail statistic, M10 depth
accuracy, or any claim in cycles/mm or physical units. Physical scale needs the
certified artifact and a separate small session.

## Interim option, and why it is not recommended

A minimal fixed-focus repeat would not answer the focus-stack question or
provide the through-focus pairs this session exists to collect. **Shoot the
383-frame paired-node session.** Use the 407-frame fallback only if the body
cannot hold focus for the second exposure at a node.

## Before you shoot: one test exposure

With the crossed polarisers in place, take a single test frame at **ISO 100,
1 s, f/5.6** and check that it is **neither clipped nor photon-starved**.
Crossed polarisers cost a lot of light, and the exposure is fixed for the whole
session — if it is wrong, every frame is wrong. Check the histogram, not the
rear-screen brightness.

While you are there, confirm the nonperiodic patch fills enough of the frame
(see *The patch must be physically large enough*). This test exposure is not
one of the 383 acquired session frames.

## Checks on arrival

All of these are **input-only**: they read RAW frames and never a render, so they
spend none of the holdout.

1. **Pairing manifest.** For the primary protocol, confirm `sw4` contains 110
   files and `sw10` contains 54, with no focus command between each odd/even
   pair. Build A from odd files and B from even files.
2. **Fallback only: node repeat.** Confirm exact A/B bracket state and start
   command, apply the frozen pixel-domain ladder-equivalence gate, and apply
   [`2026-09-node-coincidence-gate.md`](2026-09-node-coincidence-gate.md) to
   the four witness bursts. Failure of either gate invalidates that pair.
3. **Spectral eligibility, per site.** Confirm the patch carries power out to
   `0.25 cyc/native px` — measured **per site**, not as a frame average, and
   measured as **cross-power attributable to the subject** rather than raw
   single-frame power, which sensor pattern and noise can satisfy on their own.
4. **Site count.** Confirm at least **64 guarded, non-overlapping eligible
   sites** survive. Freeze the site manifest before any render exists.
5. **Clipping and focus.** Reject clipping per site. Verify every retained site
   has a through-focus peak **interior** to both A and B: the odd/even stacks in
   the primary protocol, or the two complete named passes in the fallback.

If the patch is too smooth, or too few sites survive, the session is still fine
for everything else, but the detail axis would need the patch replaced and those
blocks reshot.
