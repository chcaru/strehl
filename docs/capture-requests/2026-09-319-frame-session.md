# Capture request: the 319-frame session that unblocks M1, M5 and M9

Status: REQUESTED — awaiting owner
Owner of this file: orchestrator
Raised: 2026-09

---

## Why this exists

Three scorecard axes — M1 (detail), M5, M9 — are blocked on captures, not on
code. Two lanes arrived at the required session independently and from
different requirements, and they specified the same 319 frames. This document
is the single consolidated request. It is written to be followed at the bench.

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

## Frame counts — 319 total

| Block | Frames | Purpose |
| --- | ---: | --- |
| `sw4-A` | 55 | step width 4, pass A |
| `sw4-B` | 55 | step width 4, pass B — independent repeat of A |
| `sw1` checker-only | 91 | dense reference. **Never feed this to a stacker.** |
| `sw10-A` | 27 | step width 10, pass A |
| `sw10-B` | 27 | step width 10, pass B — independent repeat of A |
| flats | 32 | |
| darks | 32 | |
| **total** | **319** | |

The A/B pairs are the point: two independent passes over identical geometry and
exposure are what make a repeat-pair instrument possible at all.

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

**Sweep:** focus bracket, direction `0 → +`, 1 s interval. **Return to an
identical near-focus reset before each pass** — the A and B passes must start
from the same place or they are not repeats.

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

Since certification turned out not to be needed, the full 319-frame session is
executable now with equipment already on hand, so the interim shoot buys a
fraction of the value for most of the effort. **Shoot the full session.**

## One check on arrival

Before the session is sealed and scored, run an **input-only** spectral
eligibility check: confirm the nonperiodic patch actually carries power out to
`0.25 cyc/native px`. Input-only means it reads the RAW frames and never a
render, so it spends none of the holdout.

If the patch is too smooth, the session is still fine for everything else, but
the detail axis would need the patch replaced and those blocks reshot.
