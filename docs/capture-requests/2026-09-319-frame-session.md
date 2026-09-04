# Capture request: inverted M1, M5 and M9 scored session

> # ⛔ STOP — THIS DOCUMENT IS NOT SAFE TO SHOOT FROM
>
> **Raised by the orchestrator, 2026-09-04, after the M135 sampling ruling.
> The scored block table was reconciled by lane M150 on 2026-09-04.**
>
> **DO NOT SHOOT.** The scored frame and release totals, block layout and
> converter inversion are reconciled in the body. The working magnification
> parameter `M_work` remains unset, M147's in-field preflight has not been
> delivered or rehearsed, and the non-holdout rehearsal required by blockers 1
> and 2 has not been completed. Clearing any subset of those open items does
> **not** make this document shootable.
>
> **Superseded totals, 2026-09-07 (lane M166, commit `a195bc63`).** The
> `T_session` arithmetic in the body is stale. M164's frozen witness contract
> ruled that a fixed-focus burst is inadmissible as the dominance witness when
> the renderer receives a focus stack, and M166 re-derived the session on that
> basis: **`891 + 32 + 164 + 128 = 1,215` registered frames**, plus a `1,092`-frame
> exact-configuration rehearsal in front of it. Both are **STOP at zero frames**
> until the hash-bound production dominance manifest exists.
>
> **⚠ Do not double-count `96` or `164`.** Those two numerals appear *twice* in
> this program with different meanings, because the same `55/55/27/27`
> focus-stack budgets recur. In the body table below, `96` is the **converter-on
> reference subject** and `164` is the **TC0 scored focus** block — both already
> inside the base `891`. M166's corrections are *additions on top of* `891`: a
> `+32` fourth reference strip, a `+164` physical `S_1/S_2` witness that replaces
> a previously proposed `+96` converter-off witness, and `+128` held-out
> calibration. The base blocks and the additions are different frames.
>
> **Why.** The design requires the truth reference to oversample the TC0 state by
> `2.0x`. **Only conditionally, if M147 sets `M_work = 1.33x`,** the conservative
> geometry is `2.7015 / 1.33 = 2.0312x`, leaving a margin of `0.0312x`, or
> **1.54%**. That conditional calculation is not permission to enter `1.33x` on
> the bench sheet. Magnification is set by hand on the focus ring, and M84b's
> `0.188%` / `~0.36%` figures measure **recovery, not placement** — they describe
> how precisely a ratio can be *read back* from frames, not how precisely it can
> be *dialled in*. M141 established that reproduction ratio is
> metadata-recoverable for **0 of 68** existing stacks, so a session shot below
> the required ratio would announce nothing and would be discovered only after
> the fact, burning the whole sitting.
>
> **What is settled and carries forward:** the unchanged 443-frame session and
> the 448-frame inverted block shown in the block table; the converter **on**
> for the existing session and the reference frames, then **off** for the TC0
> scored sweeps, their witnesses and their calibration; stabilisation **off**;
> the 603-frame request **superseded**; and no M135 control frames in the scored
> sitting.
>
> **What is not settled:** `M_work`, supplied by the M147 preflight. It must not
> be inferred from this document or dialled from a provisional value.
>
> **What unblocks it.** Lane **M147** is building an in-field magnification
> preflight so the achieved ratio can be confirmed *before* the session rather
> than discovered after it. The measurement is tractable because both optical
> states image one coplanar grid, which makes the gate a **ratio** — grid pitch,
> pixel pitch and EXIF all cancel, so no absolute calibration is required.
>
> M135 has ruled that the mandatory physical control arms belong to the
> already-required **non-holdout rehearsal**, not this scored sitting. They may
> not be shot or read here; the control rule is recorded below the block table.
>
> **This banner is removed only after M147's preflight has been delivered and
> rehearsed and the exact-configuration non-holdout rehearsal has closed
> blockers 1 and 2, including the physical control arms. DO NOT SHOOT until the
> orchestrator removes this banner.**

Status: **BLOCKED — DO NOT SHOOT (M147 and non-holdout rehearsal pending)**
Superseded: the 603-frame design, on 2026-09-04
Reconciled: 2026-09-04 to the derived scored block table
Owning lane: **lane-FRC**
Approver: **orchestrator**
Raised: 2026-09
Session length: **PROVISIONAL DURATION; one uninterrupted session; do not
promise 45 minutes.** The fixed scored blocks include 419 automated-bracket
frames in nine passes, hence 410 three-second intervals, and 472 non-bracket
exposures. Their acquisition floor is **28.5–35.4 minutes**:
`(410 × 3 s + 472 × 1 s + 9 terminal bracket exposures × 1 s) / 60 = 28.52 min`
if the camera's interval includes each bracket exposure, or
`(410 × 3 s + 419 × 1 s + 472 × 1 s) / 60 = 35.35 min` if it is additive.
That leaves only 9.6–16.5 minutes inside a 45-minute sitting for gates, resets,
converter removal, reframing, calibration changes and three reference focus
settings.
**The former 45–60-minute estimate is no longer a safe planning assumption:
45 minutes is not credible, and completion within 60 minutes is conditional on
the exact-configuration rehearsal. It may run longer. Splitting it across two
sittings still invalidates the same-session requirement.**
Amended: 2026-09 (Sony A7C II automated-bracketing protocol)
Superseded amendment: 2026-09 (160-frame truth reference and 1.30× main setting)
Frozen: 2026-09-03
Amended: 2026-09-04 (reference block made physically executable; three pre-shoot blockers raised)
Reconciled: 2026-09-04 (448-frame inverted block; `M_work` left unset)
Resolved: 2026-09-04 (M135 controls assigned to non-holdout rehearsal; no scored frames)

## DO NOT SHOOT YET — FOUR TRACKED ITEMS; 1, 2 AND 4 REMAIN OPEN

Raised by lane-FRC on review of the truth-reference integration, 2026-09-04.
Item 4 was raised separately by the orchestrator on the M135 sampling ruling and
is the superseding blocker; see the stop banner at the top. Item 3 is closed.
The reconciled procedure remains blocked by items 1, 2 and 4. **Settle every
open item before the holdout acquisition begins.** The non-holdout rehearsal
for items 1 and 2 also owns the M135 physical control arms recorded below.

| # | Blocker | Why it can ruin the session | What settles it |
| --- | --- | --- | --- |
| 1 | **TC0 `sw4` / `sw10` step widths are unverified at `M_work`** | The widths were frozen without a documented bare-lens reproduction ratio. Sony's step width is *relative* and depends on aperture and initial focus, so depth-of-field per step changes with magnification. If they are wrong, the ladders have gaps and the sweeps do not sample what the gates assume. | After M147 supplies `M_work`, a non-holdout rehearsal with the **converter off**, at `M_work` and marked f/5.6, proving 55 frames at width 4 and 27 at width 10 give **gap-free coverage with interior peaks at 64 eligible sites**. **Verify this from image data, not from EXIF — see the note below.** Do not derive replacement widths from holdout data. |
| 2 | **G2 and G3 are not commissioned for bare-lens TC0 at `M_work`** | G2 is a fixed-focus spectral repeat and G3 a ladder-node match. Their thresholds (`< 0.10` log-ratio, unique zero-lag maximum, `< 0.10` geometry) were frozen at a different configuration and there is no justified magnification-adjusted threshold. | The same exact-configuration, converter-off development rehearsal as item 1. G0 (`≤ 0.033`) and G1 (`< 0.10` native pixel) are unaffected and remain valid. |
| 3 | ~~Converter identity is unresolved~~ **CLOSED 2026-09-04 — it is a 2× Viltrox, and every existing focus-bracket capture was shot on it** | The concern was that repository Focus-Bracket evidence might have been obtained on different hardware from the session, leaving mode availability, 55/27-shot completion and endpoint repeatability unverified on the converter actually used. | **Settled by the owner directly:** the rig is a **Sony A7C II + Sony FE 100mm F2.8 GM + 2× Viltrox teleconverter**, and **all stacks in the corpus are focus bracketed.** So the Viltrox is not a new variable — it is the converter every existing capture was taken through, including the 182-, 92- and 197-frame bracket ladders on the 2026-09-02 calibration slide, which completed at 200 mm f/5.6. Focus Bracket is therefore demonstrated on this exact hardware. |
| 4 | **`M_work` is unset; the conditional 1.54% margin cannot be dialled in by assumption** | **This is the blocker that superseded the design.** The reference must oversample TC0 by `2.0x`. Only if `M_work = 1.33x` does the conservative geometry give `2.7015 / 1.33 = 2.0312x`, a margin of `0.0312x` = **1.54%**. That is a conditional calculation, not the selected setting. The owner sets magnification on the focus ring by hand, and M84b's `0.188%` / `~0.36%` figures measure **recovery, not placement**. M141 found reproduction ratio metadata-recoverable for **0 of 68** existing stacks, so a session shot fractionally under the ratio announces nothing at the time and is discovered only in analysis — after the sitting is gone. | **M147's in-field magnification preflight, followed by an exact-configuration rehearsal.** It must supply the accepted value of `M_work` and prove the ratio at the bench before any session frame. Both optical states image one coplanar grid, so the gate is a **ratio** and grid pitch, pixel pitch and EXIF all cancel — no absolute calibration is required. Do not substitute a provisional value. |

**Blockers 1, 2 and 4 converge on the M147 preflight plus one
exact-configuration rehearsal. Blocker 3 is closed.**

### Do not try to identify the teleconverter from EXIF

**EXIF cannot distinguish this converter and an earlier revision of this
document was wrong because it tried.** Every one of the **68** distinct stack
directories under `D:\personal\macro` reports, in `LensModel` and in the Sony
maker note `LensType3` alike:

`Sony FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`

The physical converter is a **Viltrox**. It reports over the electronic
protocol as a Sony 2× so the body meters and records correctly, and the maker
note is written from that protocol rather than from the physical part. A
verifier that compares EXIF strings will confirm this string on every frame and
still be reading the wrong hardware. **Converter identity is owner testimony,
not metadata.**

### Why coverage must be verified from image data, not EXIF

`FocusPosition2` is far too coarsely quantised to verify per-node coverage.
Measured on the 2026-09-02 calibration slide:

| stack | frames | `FocusPosition2` histogram | frames per encoder unit |
| --- | ---: | --- | ---: |
| `tilted-sw4-cpl` | 182 | `57`×76, `58`×80, `59`×26 | ~78 |
| `tilted-sw10-cpl` | 92 | `57`×38, `58`×40, `59`×14 | ~40 |
| `very-tilted-all-axis-sw10-cpl` | 197 | `56`×10, `57`×40, `58`×40, `59`×41, `60`×40, `61`×26 | ~40 |

One encoder unit spans roughly **40 frames at step width 10** and **78 at step
width 4**. A ladder of 55 or 27 frames therefore lives almost entirely inside a
*single* encoder value, so EXIF cannot show whether the ladder covered the depth
range without gaps. **Gap-free coverage and the 64 interior peaks must be
demonstrated from the rendered focus response per site.**

The same table yields a useful free measurement: across the two `tilted` stacks
the per-bucket frame ratios are `76/38 = 2.000` and `80/40 = 2.000`, so **step
width 10 advances focus almost exactly twice as far as step width 4** at that
configuration. The truncated final bucket, `26/14 = 1.857`, shows the two
sweeps stopped at slightly different points inside encoder value `59`.

## STANDING EQUIPMENT CONSTRAINT — OWNER-SUPPLIED — DO NOT REOPEN

The owner directly confirmed that macro captures use **in-camera Focus Bracket
on the Sony A7C II**. The camera drives each complete focus ladder and fires
one exposure per node. It cannot expose A and B back-to-back at one node before
advancing. Per-node A/B pairing was proposed twice during review; it is
unavailable on this body and must not be proposed again.

The executable protocol is therefore the automated whole-pass procedure below.
No lane may change frame counts, shot order, settings, or gates without explicit
orchestrator authorisation. A newly discovered invalidating defect must be
reported, not silently edited.

## Frame-count changelog

| Version | Count | Disposition |
| --- | ---: | --- |
| Original request | 319 | 255 focus frames + four 16-frame calibration groups; insufficient calibration reserve |
| Witness-first amendment | 407 | 383 claim/calibration frames + 24 reset witnesses; witnesses could not observe endpoints or interior nodes |
| Paired-node proposal | 383 | Removed witnesses by interleaving A/B at every node; withdrawn because the A7C II cannot execute it |
| Automated-bracket amendment | 443 | Restored complete A/B passes and added 60 reset/start/end witnesses |
| Superseded frozen request | 603 | 443-frame automated-bracket session + 160-frame truth-reference block |
| **Current scored request** | **see block table** | Derived fixed total; M135 control arms are excluded from the scored sitting |

---

## AMENDED — read this before shooting

**Do not use the earlier paired-node instructions.** The Sony A7C II cannot
take A and B at one focus node before advancing; Focus Bracket drives a complete
ladder automatically. The whole-pass sequence below replaces every earlier
version of this request.

| # | Change | Why |
| --- | --- | --- |
| 1 | **Two complete automated A/B pairs in each optical state, with fixed-focus start/end sentinels** | Per-node A/B interleaving is unavailable on this body; both the converter-on block and TC0 therefore use whole-pass repeats |
| 2 | **Patch must be physically large enough** for 64 guarded sites | Frame count is not site count |
| 3 | **Use separate 32-flat/32-dark groups for A and B in each optical state** | Shared A/B calibration correlates the realizations, and sharing across converter states imports the wrong flat field |
| 4 | **Use a 3 s bracket interval and freeze the repeatability gate before shooting** | The old 1 s interval did not provide a settling margin or a defensible node test |
| 5 | **Keep the existing 443-frame block converter-on at maximum reproduction** | It remains the M5/M9 session and supplies the optical state and A/B calibration masters for the fixed-focus truth reference; it is not the M1 scored input |
| 6 | **Invert the M1 design: reference converter-on, scored TC0 converter-off** | The 96 reference frames preserve the existing maximum-reproduction framing; the TC0 sweeps, their 60 witnesses and all 128 TC0 calibration frames use the bare lens |
| 7 | **Replace the superseded 160-frame reference block with the 448-frame inverted block** | The replacement adds the independently calibrated bare-lens scored passes; appending it to the old reference block would be wrong |
| 8 | **Leave `M_work` unset until M147 supplies it** | A provisional magnification printed as an instruction would defeat the preflight and can burn the session |
| 9 | **Keep both M135 physical control arms in the non-holdout rehearsal** | Acquiring or reading either control in this sitting burns the same holdout unit used for the score |

**The detail axis is the reason this session exists, and it is the one thing the
previous version of this request could not have delivered.** Six candidate
detail statistics have failed. Under the current output-only observation
contract, none has separated resolved detail from sharpening without an
external model, prior, or reference. The current usable route supplies that
external information with an independently sampled, higher-magnification image
of the same patch. The replacement 448-frame block
contains that 96-frame reference plus the independently calibrated TC0 scored
passes, and it can only be shot while this rig is standing.

**The complete arithmetic now lives in the frame table below.** Its currently
named rows preserve the 383 claim/calibration frames and 60 original witnesses,
and replace the superseded 160-frame reference with the decomposed 448-frame
inverted block. M135's two physical control arms are deliberately excluded from
the scored manifest and assigned to the non-holdout rehearsal.

The eight discarded settling darks — two from each of four named dark groups —
remain registered frames. One throwaway histogram exposure comes first and is
not a registered session frame. The exact frame and release derivation appears
once, immediately below the block table.

**Before the first session frame:** M147's preflight must have supplied
`M_work`; the non-holdout rehearsal must have closed blockers 1 and 2 and
acquired and read both M135 physical control arms; and the G0-G3 reader must
have passed its development-data dry run without changing the bars below. Then
take the one throwaway test exposure, run the converter-on 12-frame reset
pre-flight, and read its frozen gate. Do not begin `sw4-A` unless that gate
passes.

## Why this exists

Three scorecard axes — M1 (detail), M5, M9 — are blocked on captures, not on
code. Two lanes arrived at the required session independently and from
different requirements, and they specified the same 319 claim frames. Review
retained their 255 focus frames but doubled the four calibration groups, making
**383 claim/calibration frames**. Automated-bracket eligibility adds 60 fixed
witnesses. The replacement inverted block is decomposed in the frame table.
M135's physical controls are commissioned outside this holdout and add no
scored frames. This document is the single consolidated request, but it remains
blocked by the stop banner.

**What is wrong with every capture we currently hold:** in-body stabilisation
was on, and there are no calibrated frame-for-frame same-focus repeats. IBIS
introduces a small per-frame geometric change that is not a rigid translation
(measured `0.107703`, reproduced `0.105202`). This session fixes both defects:
stabilisation is off, and every claim-bearing focus node has two exposures.

## What this session is, and the discipline it requires

The scorecard states that the burned grid and the development-only
high-resolution slide *"may commission a new instrument but may never provide
its scored value"* (`docs/proposals/2026-09-sota-scorecard.md`, "M1 / Input needed by a future replacement" clause).

So the division of labour is:

- **Existing development captures commission the instrument.** They are already
  in hand and already classified development.
- **This session provides the scored value. It is HOLDOUT.**

**Therefore this session must be sealed on arrival and never used for
development, tuning, threshold selection, or debugging.** If any lane renders
it while an instrument is still being tuned, the holdout is burned and the
session has to be shot again. A holdout unit is subject plus uninterrupted
session (`docs/proposals/2026-09-sota-scorecard.md`, "2.3 Holdout units and burn log" section), so it cannot be
partly spent.

## No certified target is needed

An earlier draft of this request specified a certified 10-µm clear-film grid
with a fabricated nonperiodic microdot field. **That is withdrawn.** M1 caps its
claims in **native pixel** units — the registered constraint is *"no frequency
above `0.25 cyc/native px`"*
(`docs/proposals/2026-09-sota-scorecard.md`, "M1 / Exact computation" clause) — and SOTA here is a
*relative* comparator-leading claim against Zerene and Helicon on identical
input. Absolute physical scale is consumed only when converting to
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

## Frame counts — scored total derived from named blocks

| Block | Frames | Purpose |
| --- | ---: | --- |
| reset pre-flight `P0` | 6 | converter on, fixed focus at the existing maximum-reproduction reset |
| reset pre-flight `P1` | 6 | converter on, same reset after moving away and returning by the recorded approach |
| start `S4-A` | 6 | converter-on fixed-focus sentinel immediately before A |
| `sw4-A` | 55 | converter-on automated Focus Bracket, step width 4 |
| end `E4-A` | 6 | converter-on fixed-focus sentinel at A's untouched final position |
| start `S4-B` | 6 | converter-on fixed-focus sentinel after the repeated reset |
| `sw4-B` | 55 | identical converter-on automated repeat of A |
| end `E4-B` | 6 | converter-on fixed-focus sentinel at B's untouched final position |
| start `S10-A` | 6 | converter-on fixed-focus sentinel immediately before A |
| `sw10-A` | 27 | converter-on automated Focus Bracket, step width 10 |
| end `E10-A` | 6 | converter-on fixed-focus sentinel at A's untouched final position |
| start `S10-B` | 6 | converter-on fixed-focus sentinel after the repeated reset |
| `sw10-B` | 27 | identical converter-on automated repeat of A |
| end `E10-B` | 6 | converter-on fixed-focus sentinel at B's untouched final position |
| `sw1` checker-only | 91 | converter-on dense checker. **Never feed this to a stacker.** |
| `TR-REF-NEAR` | 32 | converter on, fixed focus, existing maximum reproduction and framing |
| `TR-REF-MID` | 32 | converter on, same framing, fixed focus in the middle third |
| `TR-REF-FAR` | 32 | converter on, same framing, fixed focus in the far third |
| flats A | 32 | converter-on calibration for the complete A passes and odd reference halves |
| flats B | 32 | converter-on calibration for the complete B passes and even reference halves; **move or rotate the diffuser first** |
| darks A | 32 | converter-on calibration for the complete A passes and odd reference halves |
| darks B | 32 | converter-on calibration for the complete B passes and even reference halves |
| `TC0-P0` | 6 | converter off, fixed focus at the recorded `M_work` near-focus reset |
| `TC0-P1` | 6 | same reset after moving away and returning by the recorded approach |
| `TC0-S4-A` | 6 | fixed-focus sentinel immediately before `TC0-sw4-A` |
| `TC0-sw4-A` | 55 | bare-lens automated Focus Bracket, step width 4, pass A |
| `TC0-E4-A` | 6 | fixed-focus sentinel at A's untouched final position |
| `TC0-S4-B` | 6 | fixed-focus sentinel after the repeated reset |
| `TC0-sw4-B` | 55 | identical independent repeat of `TC0-sw4-A` |
| `TC0-E4-B` | 6 | fixed-focus sentinel at B's untouched final position |
| `TC0-S10-A` | 6 | fixed-focus sentinel immediately before `TC0-sw10-A` |
| `TC0-sw10-A` | 27 | bare-lens automated Focus Bracket, step width 10, pass A |
| `TC0-E10-A` | 6 | fixed-focus sentinel at A's untouched final position |
| `TC0-S10-B` | 6 | fixed-focus sentinel after the repeated reset |
| `TC0-sw10-B` | 27 | identical independent repeat of `TC0-sw10-A` |
| `TC0-E10-B` | 6 | fixed-focus sentinel at B's untouched final position |
| `TC0-FLAT-A` | 32 | bare-lens calibration for the complete TC0 A passes |
| `TC0-FLAT-B` | 32 | independent bare-lens B flat; **move or rotate the diffuser first** |
| `TC0-DARK-A` | 32 | bare-lens A dark at the scored exposure |
| `TC0-DARK-B` | 32 | independent bare-lens B dark at the scored exposure |
| **existing claim/calibration** | **383** | 255 converter-on focus + 128 converter-on calibration |
| **existing fixed-focus witnesses** | **60** | converter-on reset, start and endpoint eligibility |
| **reference subject** | **96** | three converter-on fixed-focus truth bursts |
| **TC0 scored focus** | **164** | two bare-lens `sw4` plus two bare-lens `sw10` passes |
| **TC0 fixed-focus witnesses** | **60** | bare-lens reset, start and endpoint eligibility |
| **TC0 calibration** | **128** | two independent bare-lens flat/dark pairs |
| **replacement inverted M1 block** | **448** | `96 + 164 + 60 + 128` |
| **scored session total `T_session`** | **891** | `383 + 60 + 96 + 164 + 60 + 128` |

One throwaway histogram exposure precedes the scored session and is not in
`T_session`: **`R_session = 891 + 1 = 892` shutter releases.**

## Physical control arms for the detail instrument — NON-HOLDOUT REHEARSAL ONLY

> **⛔ DO NOT ACQUIRE OR READ THESE CONTROLS IN THE SCORED SESSION.**

The detail instrument requires two mandatory **physical** control arms: a
pre-noise blur arm with information-ratio `Q95 < 0.90`, and a genuine pre-noise
optical-improvement arm with `Q05 > 1.10`.

These arms must be acquired and read in the non-holdout rehearsal already
required by blockers 1 and 2. Their rehearsal frame count is intentionally not
specified here. They are measured against a converter-on `R1/R2` reference,
and the scored value depends on that same reference channel. The holdout unit
is the subject plus the uninterrupted capture session; reading an outcome on
any member burns every member
(`docs/proposals/2026-09-sota-scorecard.md`, "2.3 Holdout units and burn log" section). Reading either control
against this session's reference would therefore burn the scored session.

- **Do not select the blur arm after the fact from this session's
  `sw4`/`sw10` ladder frames.** That is outcome-dependent selection.
- **Do not use the converter-on truth reference measured against the TC0 scored
  block as the improvement arm.** That uses the reference as both truth and
  improved output and is circular.
- **Do not add either control to the scored block table.** Complete and read
  both in the non-holdout rehearsal before the holdout sitting begins.

## M5 eligibility gate — REHEARSAL EXIT CONDITION, zero extra frames

> **This gate decides whether the 891-frame scored session is worth shooting
> at all.** It is measured on the non-holdout rehearsal, so reading it burns
> nothing.

**Why this exists.** M5 requires a Wilson lower bound `>= 98%`
(`docs/proposals/2026-09-sota-scorecard.md`, "M5 / Success" clause). For an all-successes sample
the bound is `n / (n + z^2)` with `z = 1.6448536269514722`, so
`z^2 = 2.705543454`. That gives `n=128 -> 0.979300` and `n=132 -> 0.979915`,
both short, while `n=133 -> 0.980063` clears it. **133 eligible tiles is the
smallest sample that can satisfy M5 at all**, and it was independently
re-derived twice before being written here.

**The population is not small.** At the RAW-visible active area of
`7028 x 4688`, one frame affords
`floor(7028/128) * floor(4688/128) = 54 * 36 = 1,944` complete non-overlapping
`128 x 128` tiles, leaving `116 px` unused at right and `80 px` at bottom. An
earlier reading of `13/64` was an `8x8` grid **subsample**, not the population,
and reporting it as though `64` were all there is understated eligibility by
roughly thirty-fold.

**The gate can fail, which is the point.** Measured on the full population, the
burned calibration grid yields `0/1,944` eligible at `sw4/55` and `0/1,944` at
`sw10/27`, while the best exact 27-frame tilted window reaches `275/1,944`
eligible from `328` point-qualified, an all-success `LCB95` of `0.990258`. So
`133` is demonstrably attainable at this geometry **and** demonstrably not
automatic.

**The gate.** For each step width, average the complete A/B block cross-powers
**before** election and bootstrap, then require all three:

1. pass-averaged `sw4` manifest: **`>= 133` eligible tiles**
2. pass-averaged `sw10` manifest: **`>= 133` eligible tiles**
3. physical-coordinate intersection across `sw4`/`sw10`: **`>= 133` eligible
   tiles**

**Any failure is a STOP before the 891-frame session.**

**Two things this gate is not.** A/B halves and step widths must **not** be
counted as independent populations — that would manufacture the sample rather
than measure it. And this converter-off rehearsal gate is a **feasibility
check, not the converter-on M5 score**; the separate scorecard floor of "500
eligible tiles overall and 50 per capture"
(`docs/proposals/2026-09-sota-scorecard.md`, "M5 / Input" clause) still governs the complete
registered M5 capture set.

## Literal shooting order

### 0. M147 and non-holdout rehearsal gates — before the session

Do not begin the session until M147's preflight has supplied `M_work`, the
exact converter-off setup has been rehearsed, blockers 1 and 2 have closed, both
M135 physical control arms have been acquired and read in that non-holdout
rehearsal, and the orchestrator has removed the stop banner. Copy the supplied
`M_work` value onto the live bench sheet; do not fill it from a provisional
value in another document.

### 1. Converter-on reset pre-flight — do this before any bracket

1. Install the 2× Viltrox and establish the existing maximum-reproduction
   near-focus reset. Record exactly how you approached it.
2. Lock the lens at that position without turning the focus ring or issuing
   another AF command. Take six RAWs: `P0`.
3. Move focus well away, then return to the reset using the same direction and
   method. Lock it the same way. Take six RAWs: `P1`.
4. Run the pre-flight gate below. If it fails, **stop without shooting any
   bracket**. Correct the reset/rig problem and begin a new pre-flight.

### 2. Converter-on `sw4` pair — gate it before continuing

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

### 3. Converter-on `sw10` pair — repeat the same pattern

Repeat the seven steps above using `S10-A`, `sw10-A` (27 shots, step width 10),
`E10-A`, `S10-B`, `sw10-B`, and `E10-B`. Keep order `0 -> +`, interval 3 s,
and every other camera/lens setting unchanged. Gate the pair before continuing.

### 4. Finish the converter-on brackets

After both A/B pairs pass their input-only gates, shoot the 91-frame `sw1`
checker-only bracket. Do not remove the converter, move the target, change
framing or disturb the lighting.

### 5. Converter-on truth reference — 96 frames, and do not skip it

The bracket pairs above measure the stacker against itself. **These three bursts
are the only part of the session that can tell us whether the TC0 stacker
resolves real detail rather than merely adding contrast.** Do not substitute
the superseded reference-flat/reference-dark design.

1. **Do not touch the subject or the lighting.** The reference must show the
   same patch under the same illumination. Moving or relighting the target
   invalidates the block.
2. **Leave the 2× teleconverter on and leave the existing
   maximum-reproduction framing untouched.**
3. **Turn Focus Bracket OFF.** These are fixed-focus bursts, not a stack.
4. Use the **same three physical near / middle / far regions**. Approach each
   focus position from the same recorded direction, lock focus, and take
   **32 frames** without touching anything: `TR-REF-NEAR`, `TR-REF-MID` and
   `TR-REF-FAR`, 96 frames total.
5. Keep the three bursts in separate, clearly named folders. Record the three
   focus positions and at least four common grid or fiducial intersections.

For every six-frame fixed-focus burst, use the same lock method. Switching
between the lock and Focus Bracket must not move focus. If it does, this setup
cannot support the gate and the session must not be used as paired data.

### 6. Converter-on calibration — four groups

Shoot the existing 32-frame flats A/B and 32-frame darks A/B at the unchanged
converter-on exposure. Move or rotate the diffuser between flat groups. Split
each 32-frame truth burst odd/even: the 16 odd frames use the A flat/dark
masters and the 16 even frames use the B masters.

**Do not add reference-only flats or darks.** The truth bursts share the
converter-on optical state and exposure of these existing masters. If their
exposure changed, stop: the named blocks no longer supply matching independent
reference calibration.

### 7. Invert to TC0 and prove the live ratio

Only after every converter-on subject and calibration frame is complete:

1. Remove the converter. Do not move the target, target tilt, lighting,
   polarizers, camera roll or camera yaw.
2. Reframe the same physical patch by axial camera motion only, preserving roll
   and yaw and retaining at least four common fiducials.
3. Set the near-focus reset to the M147-supplied `M_work` using the common grid,
   not a lens label or EXIF.
4. Measure the converter-on reference sampling `M_ref` and the live TC0
   sampling from pixels per common grid period. **Do not take `TC0-P0` unless
   `M_ref / M_work >= 2.0` and the M147 preflight accepts the live placement.**
   If either gate fails, stop; do not substitute another magnification.
5. Record `M_ref`, the measured `M_work`, their ratio, converter removal,
   working distance, reset approach and fiducial coordinates.

### 8. TC0 scored pairs and witnesses — 224 frames

With the converter off, repeat sections 1–3 under the TC0-prefixed names:
`TC0-P0/P1`, `TC0-S4-A`, `TC0-sw4-A`, `TC0-E4-A`, through
`TC0-S10-B`, `TC0-sw10-B`, `TC0-E10-B`. Use the same counts, direction,
three-second interval, reset approach and G0–G3 procedure. Keep ISO 100,
marked f/5.6, 1 s, fixed white balance, EFCS, IBIS off and OSS off. These four
bare-lens brackets, and not the converter-on brackets, are the M1 scored focus
inputs.

### 9. TC0 calibration — 128 frames

Finish with `TC0-FLAT-A/B` and `TC0-DARK-A/B`, 32 frames in each group. Move or
rotate the diffuser between the TC0 flat groups. These bare-lens masters are
disjoint from the converter-on masters and may not calibrate the truth
reference.

## Frozen repeatability gate — both parts must pass

**A fixed-focus witness-only proof of the complete ladder is impossible.**
Start and endpoint frames cannot see an interior motor error that later catches
up. A sacrificial duplicate bracket would prove only that duplicate, not the
later claim run. This request therefore freezes two complementary tests:

1. each 60-frame fixed-focus witness set gates reset, endpoint, stability, and
   focus profile — 60 converter-on frames and 60 TC0 frames;
2. the A/B bracket RAWs in each optical state gate every corresponding node
   before any stack is rendered.

Both are input-only eligibility tests. Neither may inspect a merged image or a
competitor result, and neither permits result-time re-indexing.

### G0 — every fixed-focus burst must be stable

For each six-frame burst, compute the within-burst local-registration RMS using
the existing four-quadrant estimator.

> **Pass only if every burst is `<= 0.033` native-pixel local RMS.**

Run this first on `P0/P1` in the converter-on phase and again on
`TC0-P0/P1` after converter removal. If either pair fails, do not shoot that
phase's bracket.

### G1 — reset and endpoint geometry must repeat

Average the six RAWs in each burst after black subtraction. Within each optical
state, use the five pairs `P0/P1`, `S4-A/S4-B`, `E4-A/E4-B`,
`S10-A/S10-B`, and `E10-A/E10-B`; use the same names with the `TC0-`
prefix for the bare-lens phase. Never compare a converter-on witness with a
TC0 witness. For each pair, estimate one global translation and four quadrant
translations. The statistic is

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

from each six-frame burst mean. For the same five burst pairs in each optical
state used by G1, compute the RMS of the per-site A/B differences.

> **Pass only if every spectral-profile RMS is `< 0.10` log-ratio unit.**

The `q` statistic and `0.10` stability bar have existing commissioning
precedent. Their cross-burst, per-site use here is a new frozen application and
must be dry-run on development data before any frame from this session is read.
It catches a reset or endpoint that registers geometrically but has a different
focus profile.

### G3 — the actual A/B ladder nodes must match

For each step width within each optical state, compare A frame `i` only with B
frame `i`; do not shift the index and do not compare across converter states.
On every corresponding pair:

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

- **`P0/P1` or `TC0-P0/P1` failure:** stop before that phase's bracket. Correct
  the rig or reset method, then restart the phase's pre-flight from P0.
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
that order in both optical states. If it does not, use a bigger patch during
the rehearsal. **Do not move either live camera position away from the
M147-accepted geometry merely to enlarge the patch.** A patch that is too small
will pass a whole-frame check and still leave the session underpowered.

The patch must also sit where the focus peak is **interior to both sweeps** — it
should come into focus somewhere in the middle of the travel, not at either end.

## Calibration: independent A/B sets in each optical state

**Why doubled.** If one flat master and one dark master are applied to both A and
B, they inject **identical** structure into both outputs. Every repeat-pair
instrument works by treating A and B as independent; shared calibration breaks
exactly that assumption, and the residual correlation is indistinguishable from
real detail. Converter removal also changes the flat field, so converter-on and
TC0 masters may never be shared.

**Flats — 32 for A and 32 for B in each optical state, 128 total:**

- Same RAW exposure settings as the session.
- **Defocused or integrating field, not resolved paper.** Paper fibre texture is
  confounded with sensor response and cannot be separated afterwards. Use a
  diffuser, an opal/flat panel, or heavy defocus so the field carries no
  resolvable structure.
- Comfortably **below saturation** at the bright end, but well up the range.
- **Move or rotate the diffuser between the A group and the B group** so the two
  masters do not share the same residual texture.

**Darks — 32 for A and 32 for B in each optical state, 128 total:**

- **1 s, ISO 100**, matching the session exposure.
- Shot at the **warmed-up session temperature**, not from cold.
- **Discard the first two frames of each group** — they settle.
- Lens cap on, and no light leaks.

Capture all 32 frames in each group; the first-two discard is included in that
count, leaving 30 darks per realization. Within each optical state, apply A
calibration to the complete named A passes and B calibration to the complete
named B passes. For each truth burst, apply the converter-on A masters to the
16 odd frames and the converter-on B masters to the 16 even frames. Never
share a master across A/B or converter states.

## Settings

**Required stabilisation settings:**

- **Body SteadyShot: OFF**
- **Lens OSS: OFF**

**Body and lens:** Sony A7C II and Sony FE 100mm F2.8 GM. Install the **2×
Viltrox teleconverter** for the existing 443-frame block and the three truth
bursts; the body reports that phase at 200 mm. **Remove the converter only
after all converter-on subject and calibration frames are complete.** Keep it
off for every TC0 sweep, TC0 witness, TC0 flat and TC0 dark. This is an optical
state boundary, not a mid-block option.

**Reproduction ratio — this is new and it matters more than it looks:**

- **Converter-on phase:** keep the existing maximum-reproduction setting and
  framing for `P0` through `sw1` and all three truth bursts. Measure and record
  its common-grid sampling as `M_ref`.
- **TC0 phase:** use the bare lens at **`M_work`**, an explicitly unset
  parameter supplied by M147. Verify it from pixels per common grid period
  after converter removal. Do not infer it from the focus ring, a nominal lens
  maximum, EXIF or this document.
- **Live eligibility:** require `M_ref / M_work >= 2.0` before `TC0-P0`.

The `2.7015 / 1.33 = 2.0312x` geometry in the stop banner applies only under
the stated condition `M_work = 1.33x`; it does not select that value.

**Exposure:** M mode, ISO 100, 1 s, marked f/5.6. Identical for every session
frame and both optical states.

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
shots for each converter-on and TC0 `sw4` pass, and step width 10 / 27 shots
for each converter-on and TC0 `sw10` pass. The step width 1 / 91-shot `sw1`
exists only in the converter-on phase. Approach every near-focus reset from
the same recorded direction.

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
part of `T_session`; it is the one throwaway already included in the release
derivation below the block table. After it passes, run `P0/P1` and obtain the
converter-on reset-gate verdict before starting `sw4-A`. This histogram check
does not replace the M147 magnification preflight required by the stop banner.

## Checks on arrival

All of these are **input-only**: they read RAW frames and never a render, so they
spend none of the holdout.

1. **Manifest.** Recompute `T_session` from the block table and confirm every
   row. The scored rows are converter-on `P0/P1`, eight converter-on
   start/end bursts of six, `sw4-A/B` at 55 each, `sw10-A/B` at 27 each,
   `sw1` at 91, and four converter-on calibration groups at 32 each;
   `TR-REF-NEAR/MID/FAR` at 32 each; TC0 `P0/P1`, eight TC0 start/end bursts of
   six, `TC0-sw4-A/B` at 55 each, `TC0-sw10-A/B` at 27 each, and four TC0
   calibration groups at 32 each. Confirm no M135 control frame entered this
   manifest. Confirm A and B used identical bracket settings and the recorded
   reset approach within each optical state. Confirm all three truth bursts
   carry **no** Focus Bracket metadata and that no reference-only calibration
   groups were added.
2. **Reference eligibility — do this early, because it is the one thing that
   cannot be fixed later.** Measure effective reproduction on both the TC0
   scored sweeps and the converter-on reference from the grid, as pixels per
   period, and compute the ratio, then apply exactly three bands so there is no
   ambiguity:
   **≥ 2.0× is eligible**; **1.25× to 2.0× is degraded** — record it and do not
   use it for a scored detail claim without an explicit ruling; **below 1.25×
   is an automatic no-go** and the block is dead. Confirm the reference is
   unclipped, that its two disjoint
   16-frame halves agree, and that it carries genuine power in every band the
   detail claim will use. A failed gate makes M1 `UNMEASURED`; it never
   produces a lower score.
3. **Repeatability.** Run G0 through G3 exactly as frozen above in both optical
   states. Compare only A frame `i` with B frame `i` from the same state; no
   cross-state pairing, re-indexing, fractional resampling, scale, rotation,
   warp, or favorable subset.
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
