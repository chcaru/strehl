# Capture request: 383 claim frames + 60 witnesses + 160 reference = 603 for M1, M5 and M9

Status: REQUESTED — awaiting owner
Owner of this file: orchestrator
Raised: 2026-09
Amended: 2026-09 (Sony A7C II automated-bracketing protocol)
Amended: 2026-09 (truth-reference block; main sweeps pinned to 1.30× reproduction)

---

## AMENDED — read this before shooting

**Do not use the earlier paired-node instructions.** The Sony A7C II cannot
take A and B at one focus node before advancing; Focus Bracket drives a complete
ladder automatically. The whole-pass sequence below replaces every earlier
version of this request.

| # | Change | Why |
| --- | --- | --- |
| 1 | **Two complete automated A/B brackets, with fixed-focus start/end sentinels** | Per-node A/B interleaving is unavailable on this body |
| 2 | **Patch must be physically large enough** for 64 guarded sites | Frame count is not site count |
| 3 | **Use separate 32-flat/32-dark groups for A and B** | Shared calibration structure correlates the two realizations |
| 4 | **Use a 3 s bracket interval and freeze the repeatability gate before shooting** | The old 1 s interval did not provide a settling margin or a defensible node test |
| 5 | **Shoot the main sweeps at 1.30× effective reproduction — NOT at maximum magnification** | The truth reference must out-sample the main sweeps. At maximum magnification the ratio is 1.0× and the whole detail axis is an automatic no-go |
| 6 | **Keep the 2× teleconverter installed for every frame in the session, main and reference alike** | Comparing a bare-lens reference against a teleconverter main sweep compares two different optical paths, not two samplings of one |
| 7 | **Add a 160-frame truth-reference block at the end** | This is the only block that can make the detail axis measurable at all; without it M1 stays `UNMEASURED` no matter how good the sweeps are |

**The detail axis is the reason this session exists, and it is the one thing the
previous version of this request could not have delivered.** Six candidate
detail statistics have failed because no single-image measurement separates
resolved detail from sharpening. The escape is an independently sampled,
higher-magnification image of the same patch — that is the 160-frame block, and
it can only be shot while this rig is standing.

**The claim-frame budget changed from 319 to 383.** The focus data remain 255
frames. The old plan allowed four 16-frame calibration groups; this request
uses four 32-frame groups instead, adding 64 frames and leaving reserve after
dark-frame settling discards:

- **383 claim/calibration frames:** 255 focus + 128 calibration.
- **60 fixed-focus witness frames:** 12 reset pre-flight + 48 start/end
  sentinels around the four automated passes.
- **443 acquired session frames total.**
- One throwaway histogram exposure comes first and is not part of the 443.

The four discarded settling darks are still counted among the 443 shutter
releases. The owner-approved 319 -> 383 amendment is the calibration increase;
the additional 60 are the evidence needed to decide whether two automated
ladders may be paired.

**Before the first session frame:** confirm the G0-G3 reader has passed its
development-data dry run without changing the bars below. Then take the
throwaway test exposure, run the 12-frame reset pre-flight, and read its frozen
gate. Do not begin `sw4-A` unless that pre-flight passes.

## Why this exists

Three scorecard axes — M1 (detail), M5, M9 — are blocked on captures, not on
code. Two lanes arrived at the required session independently and from
different requirements, and they specified the same 319 claim frames. Review
retained their 255 focus frames but doubled the four calibration groups, making
**383 claim/calibration frames**. Automated-bracket eligibility adds 60 fixed
witnesses, for 443 session frames. This document is the single consolidated
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

## Frame counts — 383 claim/calibration + 60 witness + 160 reference = 603

| Block | Frames | Purpose |
| --- | ---: | --- |
| reset pre-flight P0 | 6 | fixed focus at the recorded near-focus reset |
| reset pre-flight P1 | 6 | same reset after moving away and returning by the recorded approach |
| start `sw4-A` | 6 | fixed-focus sentinel immediately before A |
| `sw4-A` | 55 | automated Focus Bracket, step width 4 |
| end `sw4-A` | 6 | fixed-focus sentinel at A's untouched final position |
| start `sw4-B` | 6 | fixed-focus sentinel after the repeated reset |
| `sw4-B` | 55 | identical automated repeat of A |
| end `sw4-B` | 6 | fixed-focus sentinel at B's untouched final position |
| start `sw10-A` | 6 | fixed-focus sentinel immediately before A |
| `sw10-A` | 27 | automated Focus Bracket, step width 10 |
| end `sw10-A` | 6 | fixed-focus sentinel at A's untouched final position |
| start `sw10-B` | 6 | fixed-focus sentinel after the repeated reset |
| `sw10-B` | 27 | identical automated repeat of A |
| end `sw10-B` | 6 | fixed-focus sentinel at B's untouched final position |
| `sw1` checker-only | 91 | dense reference. **Never feed this to a stacker.** |
| flats A | 32 | calibration for the complete A passes |
| flats B | 32 | calibration for the complete B passes; **move or rotate the diffuser first** |
| darks A | 32 | calibration for the complete A passes |
| darks B | 32 | calibration for the complete B passes |
| **claim/calibration** | **383** | |
| **fixed-focus witnesses** | **60** | |
| reference near | 32 | fixed focus, **Focus Bracket OFF**, at maximum reproduction |
| reference middle | 32 | fixed focus at the middle depth of the same patch |
| reference far | 32 | fixed focus at the far depth of the same patch |
| reference flats | 32 | **independently repositioned** diffuser; reference-only masters |
| reference darks | 32 | warmed, matching the reference exposure |
| **truth reference block** | **160** | |
| **session total** | **603** | |

## Literal shooting order

### 1. Reset pre-flight — do this before any bracket

1. Establish the near-focus reset. Record exactly how you approached it.
2. Lock the lens at that position without turning the focus ring or issuing
   another AF command. Take six RAWs: `P0`.
3. Move focus well away, then return to the reset using the same direction and
   method. Lock it the same way. Take six RAWs: `P1`.
4. Run the pre-flight gate below. If it fails, **stop without shooting any
   bracket**. Correct the reset/rig problem and begin a new pre-flight.

### 2. `sw4` pair — gate it before continuing

1. Return to the reset by the recorded approach. Lock focus and take six
   `S4-A` frames.
2. Without refocusing, set Focus Bracket to step width 4, 55 shots, order
   `0 -> +`, and 3 s interval. Run `sw4-A`.
3. At the untouched final focus position, lock focus and take six `E4-A`
   frames. Do not reset first.
4. Return to the reset by the identical approach. Lock focus and take six
   `S4-B` frames.
5. Without refocusing or changing a setting, run `sw4-B`.
6. At the untouched final focus position, lock focus and take six `E4-B`
   frames.
7. Run the frozen witness and node gate. Do not continue if it fails.

### 3. `sw10` pair — repeat the same pattern

Repeat the seven steps above using `S10-A`, `sw10-A` (27 shots, step width 10),
`E10-A`, `S10-B`, `sw10-B`, and `E10-B`. Keep order `0 -> +`, interval 3 s,
and every other camera/lens setting unchanged. Gate the pair before continuing.

### 4. Finish the main session

After both A/B pairs pass their input-only gates, shoot the 91-frame `sw1`
checker-only bracket, then the four 32-frame calibration groups.

### 5. Truth-reference block — 160 frames, last, and do not skip it

Everything above measures the stacker against itself. **This block is the only
part of the session that can tell us whether the stacker resolves real detail
rather than merely adding contrast**, so if bench time runs short, cut
something else rather than this.

1. **Do not touch the subject, the lighting or the tripod position.** The
   reference must show the same patch under the same illumination. Moving the
   target invalidates the block.
2. **Leave the 2× teleconverter on.** Do not swap to the bare lens.
3. **Turn Focus Bracket OFF.** Every frame in this block is fixed focus.
4. **Increase magnification to the lens's maximum** — target **≥ 2.70×**
   effective reproduction, versus the 1.30× used for the sweeps. Refocus and
   reframe onto the same patch as needed; the framing may differ, but the same
   physical detail and at least some of the same fiducial marks must be visible
   so the two can be registered.
5. Pick **three depths** across the patch — near, middle, far — matching the
   depth range the sweeps covered. At each, lock focus and take **32 frames**
   without touching anything. That is 96 frames.
6. **32 reference flats.** Move or rotate the diffuser first, exactly as you did
   between flats A and B. These must not reuse the main session's flats.
7. **32 reference darks**, warmed, at the same exposure as the reference frames.
8. Keep every frame in this block in its own folder, clearly separated from the
   main sweeps.

**If the maximum reproduction you can reach is below about 2.0× while the main
sweeps are at 1.30×, stop and tell me the number before shooting the block** —
below that ratio the reference cannot serve as truth and those 160 frames would
be wasted.

For every six-frame fixed-focus burst, use the same lock method. Switching
between the lock and Focus Bracket must not move focus. If it does, this setup
cannot support the gate and the session must not be used as paired data.

## Frozen repeatability gate — both parts must pass

**A fixed-focus witness-only proof of the complete ladder is impossible.**
Start and endpoint frames cannot see an interior motor error that later catches
up. A sacrificial duplicate bracket would prove only that duplicate, not the
later claim run. This request therefore freezes two complementary tests:

1. the 60 fixed-focus frames gate reset, endpoint, stability, and focus profile;
2. the actual A/B bracket RAWs gate every corresponding node before any stack
   is rendered.

Both are input-only eligibility tests. Neither may inspect a merged image or a
competitor result, and neither permits result-time re-indexing.

### G0 — every fixed-focus burst must be stable

For each six-frame burst, compute the within-burst local-registration RMS using
the existing four-quadrant estimator.

> **Pass only if every burst is `<= 0.033` native-pixel local RMS.**

Run this first on P0 and P1. If either fails, do not shoot a bracket.

### G1 — reset and endpoint geometry must repeat

Average the six RAWs in each burst after black subtraction. For each pair
P0/P1, S4-A/S4-B, E4-A/E4-B, S10-A/S10-B, and E10-A/E10-B, estimate one global
translation and four quadrant translations. The statistic is

```text
R = 2 * sqrt(mean_q(||shift_q - shift_global||^2))
```

in native pixels.

> **Pass only if every `R < 0.10` native pixel.**

This is the same family of statistic and the same strict bar under which
SPLIT2 passed at `0.064031` and failed at `0.107703` (independently reproduced
at `0.105202`). Use one common integer shift and crop for comparison. Measuring
a fractional residual is allowed; applying sub-pixel resampling, scale,
rotation, or local warp is not.

### G2 — fixed-focus spectral profile must repeat

On each of at least 64 predeclared 256-pixel patch sites, compute

```text
q = log(P[0.18, 0.35] / P[0.05, 0.15])
```

from each six-frame burst mean. For the same five burst pairs used by G1,
compute the RMS of the per-site A/B differences.

> **Pass only if every spectral-profile RMS is `< 0.10` log-ratio unit.**

The `q` statistic and `0.10` stability bar have existing commissioning
precedent. Their cross-burst, per-site use here is a new frozen application and
must be dry-run on development data before any frame from this session is read.
It catches a reset or endpoint that registers geometrically but has a different
focus profile.

### G3 — the actual A/B ladder nodes must match

For each step width, compare A frame `i` only with B frame `i`; do not shift the
index. On every corresponding pair:

- require the G1 local-geometry statistic to remain `< 0.10` native pixel;
- compute the per-site `q` curves across frame index;
- require each retained site's A/B curve correlation to have a unique maximum
  at integer lag zero; and
- require the RMS of all same-index A/B `q` differences to be `< 0.10`
  log-ratio unit.

At least 64 guarded sites must survive clipping, texture, and interior-peak
eligibility in both A and B. The gate and all bars are frozen by this document
before the RAWs exist. G3 must likewise be dry-run on development data without
changing these bars before it reads this session.

> **A step width passes only if G0, G1, G2, and G3 all pass.**

### Failure action

- **P0/P1 failure:** stop before any bracket. Correct the rig or reset method,
  then restart the pre-flight from P0.
- **Any later failure:** stop the session. The affected A/B pair is not
  same-node repeat data, and the shared claim session is unusable. Do not
  re-index, choose a favorable subset, widen a bar, or replace one failed node.
  Reshoot the complete session after correcting the cause.
- Failed brackets remain ordinary stacks for work that does not require paired
  realizations; they may not provide the claim-bearing pair.

Keep the rig and subject untouched while each gate is read.

## Why automated in-camera bracketing helps

The camera, not a human, issues every focus move. With the same starting state,
step width, count, direction, aperture, interval, and lens state, it replays the
same command program and removes manual per-node placement error. Record those
settings before A and confirm them again before B. G1/G2 check the program's
start and accumulated endpoint; G3 checks the actual interior nodes.

That determinism is useful, but it is not permission to ignore a failed gate.
Sony's step width is relative to the initial focus and shooting conditions.
Step width 10 does not make an offset harmless; it must pass separately.

**Do not shoot one finer bracket and split odd/even files.** Odd and even files
are adjacent commanded focus positions, one minimum step apart. A smaller
offset is still not an independent exposure at the same node, so those two
sub-stacks cannot serve either repeat consumer.

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
count, leaving 30 darks per realization. Apply A calibration to the complete
named A passes and B calibration to the complete named B passes. Never build
one master and apply it to both.

## Settings

**Required stabilisation settings:**

- **Body SteadyShot: OFF**
- **Lens OSS: OFF**

**Body and lens:** A7C II, FE 100mm Macro GM with 2× teleconverter at 200 mm.
**Keep the teleconverter installed for every frame in the session**, including
the reference block.

**Reproduction ratio — this is new and it matters more than it looks:**

- **Main sweeps and all witnesses: 1.30× effective reproduction** at the
  near-focus reset, verified from the grid as pixels per period. Do **not**
  shoot these at the lens's maximum magnification.
- **Truth-reference block only: maximum available reproduction, target ≥ 2.70×.**

The reference must out-sample the main sweeps by at least 2×; 1.30× against
2.70× gives 2.078×, with margin. If the main sweeps are shot at maximum
magnification instead, the ratio collapses to 1.0×, the reference is
disqualified before it is taken, and the detail axis cannot be measured from
this session at any later date.

**Exposure:** M mode, ISO 100, 1 s, f/5.6. Identical for every session frame.

**File:** 14-bit lossless compressed RAW. Fixed white balance — pick a value,
do not use auto. EFCS on.

**All off:** DRO, HDR, long-exposure NR, high-ISO NR, pixel shift, Pre-AF,
continuous/tracking AF, and in-camera auto lens corrections. Use the focus mode
required by Focus Bracket, unchanged between A and B; do not issue a new
autofocus command after establishing the reset.

**Rig:** tripod, remote or self-timer release. Nothing touching the rig during
an automated pass or fixed-focus burst.

**Lighting:** flicker-free diffused LED, warmed up at least 15 minutes before
the first frame so output has stabilised. Source polariser plus crossed CPL on
the lens. Matte-white backing behind the target. Tilt the target roughly 1° so
the focus sweep has something to resolve through.

**Sweep:** automated Focus Bracket, direction `0 → +`. Use step width 4 / 55
shots for each `sw4` pass, step width 10 / 27 shots for each `sw10` pass, and
step width 1 / 91 shots for `sw1`. Approach every near-focus reset from the
same recorded direction.

**Settling:** set Focus Bracket **Shooting Interval to 3 s** for every automated
pass. If the menu does not offer 3 s, choose the next longer value; never use
the old 1 s interval. After manually moving to a reset or endpoint witness
position, wait at least 3 s after lens motion stops before the first fixed-focus
witness.

## What this unlocks, and what it does not

**Unlocks if every frozen gate passes:** the independent same-focus evidence
needed by the head-to-head physical-detail question, M5, M9, and any future M1
instrument that requires paired realizations.

**Does not by itself provide:** an admitted M1 detail statistic, M10 depth
accuracy, or any claim in cycles/mm or physical units. Physical scale needs the
certified artifact and a separate small session.

## Interim option, and why it is not recommended

A minimal fixed-focus repeat would not answer the focus-stack question or
provide the through-focus pairs this session exists to collect. The automated
whole-pass protocol above is the only approved acquisition on this body.

## Before you shoot: one test exposure

With the crossed polarisers in place, take a single test frame at **ISO 100,
1 s, f/5.6** and check that it is **neither clipped nor photon-starved**.
Crossed polarisers cost a lot of light, and the exposure is fixed for the whole
session — if it is wrong, every frame is wrong. Check the histogram, not the
rear-screen brightness.

While you are there, confirm the nonperiodic patch fills enough of the frame
(see *The patch must be physically large enough*). This test exposure is not
one of the 443 acquired session frames. After it passes, run P0/P1 and obtain
the pre-flight verdict before starting `sw4-A`.

## Checks on arrival

All of these are **input-only**: they read RAW frames and never a render, so they
spend none of the holdout.

1. **Manifest.** Confirm the named file ranges contain P0/P1, all eight
   start/end bursts of six, `sw4-A/B` at 55 each, `sw10-A/B` at 27 each,
   `sw1` at 91, four calibration groups at 32 each, and the five reference
   groups at 32 each (near, middle, far, reference flats, reference darks).
   Confirm A and B used identical bracket settings and the recorded reset
   approach, and that the reference groups carry **no** Focus Bracket metadata.
2. **Reference eligibility — do this early, because it is the one thing that
   cannot be fixed later.** Measure effective reproduction on both the main
   sweeps and the reference block from the grid, as pixels per period, and
   compute the ratio. It must be **≥ 2.0×**; below `1.25×` the block is an
   automatic no-go. Confirm the reference is unclipped, that its two disjoint
   16-frame halves agree, and that it carries genuine power in every band the
   detail claim will use. A failed gate makes M1 `UNMEASURED`; it never
   produces a lower score.
3. **Repeatability.** Run G0 through G3 exactly as frozen above. Compare only
   A frame `i` with B frame `i`; no re-indexing, fractional resampling, scale,
   rotation, warp, or favorable subset.
4. **Spectral eligibility, per site.** Confirm the patch carries power out to
   `0.25 cyc/native px` — measured **per site**, not as a frame average, and
   measured as **cross-power attributable to the subject** rather than raw
   single-frame power, which sensor pattern and noise can satisfy on their own.
5. **Site count.** Confirm at least **64 guarded, non-overlapping eligible
   sites** survive. Freeze the site manifest before any render exists.
6. **Clipping and focus.** Reject clipping per site. Verify every retained site
   has a through-focus peak **interior** to both complete named A and B passes.

If the patch is too smooth, or too few sites survive, the session is still fine
for everything else, but the detail axis would need the patch replaced and those
blocks reshot.
