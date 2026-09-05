# ORCH-clamp-default-decision — should clamped Catmull-Rom become the shipping default?

**Status: REGISTERED, UNRESOLVED. Prospective.**
**Owner: root orchestrator. Executing lanes report results here; they do not edit
sections 4-8 of this document.**

Registered before the deciding evidence exists. No arm of this decision has been
read at the time of writing. That is the point: `ORCH-kernel-decision.md`
Amendment 3 recorded, as discipline 890, that a decision record which tracks only
*feasibility* gates converges on GO as engineering lands, because every gate it
tracks is work someone is being paid to finish. **The gate that should have
failed was never written.** This document exists to write that gate first.

---

## 1. The decision

`crates/strehl-cli/src/align_cmd.rs:59` sets `DEFAULT_RESAMPLER_NAME` to
`"catmull-rom"`. M172 landed `Resampler::ClampedCatmullRom` **opt-in**: an exact
same-support limiter that constrains each gathered sample to the local hull of
the source values it was gathered from.

The question is whether that clamp should become the shipping default.

## 2. Why this decision is live, and the trap attached to it

M8 fails. `docs/proposals/2026-09-sota-scorecard.md:2109` records M8-R at
`1.030569%` against a bar of exactly `0.0000%`, and records that the failure is
**100% attributable to the Catmull-Rom gather**. The underlying count,
`63,191,176 / 6,131,678,976 = 1.030569%`, is transcribed at
`docs/research/M136-m8-passability.md:553`.
`docs/research/M136-m8-passability.md` §3 proves that M172's clamp forces
`V_R = 0` as a mathematical consequence, not a statistical hope.

**So a default flip would turn a red axis green, and that is precisely why this
document must not be resolved on that fact.** M136 §4.3 already ruled that a
default change justified only by M8-R becoming zero is *"metric gaming and an
unearned product pass"*. I adopt that ruling without reservation. Section 2.1
below goes further and shows the flip cannot score M8 at all right now.

**Binding anti-Goodhart clause.** This decision is to be made as though M8 did
not exist. Any GO must be defensible in a release note that never mentions M8. If
the only sentence available to justify the change is "it makes a scorecard axis
pass", the answer is NO-GO regardless of every other gate below.

### 2.1 The scorecard already anticipated this move, and it bites

This section was added after sections 1-2 were drafted, on checking a citation
that turned out not to say what it was cited for. The scorecard does not merely
fail to license a clamped default — **it registered a control against it in
advance**:

> `docs/proposals/2026-09-sota-scorecard.md:1629-1631` — **"Known defeat.** Final
> clamping can erase M8-O evidence; ... and **destructive clipping can force a
> zero rate."**

> `docs/proposals/2026-09-sota-scorecard.md:1639-1642` — **"A future M1 and the
> retained M4 flat-power-plus-transfer component are the owner-gate controls
> against buying the hull result through sharpening, attenuation, or
> clamping.** ... While M1 is absent, **M8 may prove only this internal
> invariant, not SOTA.**"

The registered control against buying an M8 zero by clamping is **conjunctive: a
future M1 _and_ the retained M4 flat-power-plus-transfer component.** M1 is
blocker `(a)` — the missing admissible detail instrument. The control is
therefore *unavailable*, by name, for exactly this intervention.

**Note for whoever executes this.** M136 §4.2 paraphrases that clause as "M1's
detail and flat-power-plus-transfer component", which silently drops M4 and reads
as though the control were M1 alone. The literal text names **two** controls, and
M4 is described as *retained* — i.e. it may already exist. **Whether M4's
flat-power-plus-transfer component is presently runnable is an open question I am
not answering here**, and it matters: if M4 is available, then half of a
conjunctive control is already in hand and only M1 is missing. Do not assume
either way without reading M4's own status.

**Consequence, and it is the most important sentence in this document:**

> **A clamped shipping default is NOT a route to an M8 PASS while M1 is absent.**
> The product decision and the axis score are separable, and only the first is
> available now. A blind by-eye read (section 5) can license a *product* change
> on ringing grounds. It is **not** the registered control and must never be
> presented as discharging it. Any M8 score taken under a clamped default before
> M1 exists is defeated in advance by the scorecard's own clause.

I record that I found this route while looking for movement on M8, drafted a
document aimed at it, and only located the disqualifying clause when verifying my
own citation. The anti-Goodhart clause above worked on its author. That is the
intended function and it should be left in place for the next person.

## 3. Why this is not a re-run of the Lanczos-3 decision

`ORCH-kernel-decision.md` was suspended NO-GO because its two terms went
asymmetric in the worst way: a **measured** cost bought with a **withdrawn**
benefit. This decision is the mirror image, and the mirroring is the reason it
needs its own gates rather than the old ones.

| Term | Lanczos-3 (suspended NO-GO) | Clamped Catmull-Rom (this decision) |
| --- | --- | --- |
| Benefit | `+0.116 dex` sharpness — a **statistic**, later withdrawn as 12.8% subject detail and 87.2% noise | Exact same-support hull containment — a **proved structural invariant**. Not a statistic and not withdrawable. |
| Cost | `2.5x-3.5x` warp time — **measured** | Loss of restoration — **certain**. Loss of resolved detail — **unmeasured**. |

Two consequences follow, and they are the whole design of section 4.

1. The benefit side cannot collapse the way M85's did, because it is a theorem
   about the gather, not a measurement through a noisy band. The Amendment 3
   failure mode does not threaten this decision from that direction.
2. **The unwritten gate is therefore on the cost side.** Lanczos-3's premise was
   withdrawn when its benefit evaporated. This decision's premise evaporates if
   the clamp is shown to destroy real image content. That is the gate that must
   be able to go red, and section 5 writes it.

## 4. What the clamp actually buys, stated without reference to any metric

Overshoot outside the local source hull is not an abstraction. It is the
mechanism of **ringing and dark rims at occluding silhouettes** — the signature
artifact of focus stacking, and the one a macro stacker is most often judged on.

`ORCH-kernel-decision.md` §5 already holds, as its **N1** clause, that visible
ringing on occluding silhouettes *"is fact 1374's real concern and **it outranks
any metric**"*. That precedent was written against a different kernel and in the
NO-GO direction, but the principle is symmetric and I am applying it in the
direction it points: **if by-eye ringing outranks any metric when it argues
against a kernel, it outranks any metric when it argues for one.**

A clamped default would make strehl a stacker that provably never emits a value
its source neighbourhood did not contain. That is a real product position and it
is legible without a scorecard.

## 5. GO criteria — ALL required

- **G1. Blind, non-author, by-eye read at 1:1.** Both arms rendered from the same
  stacks at the same commit, differing only in `--resampler`. Output files named
  by a digest so the reader cannot tell which arm is which, and the mapping
  sealed before the read. The reader must not be the lane that built either arm.
- **G2. Ringing improves or is unchanged on occluding silhouettes.** At least
  three subjects with genuine occluding edges against a distant background.
- **G3. Specular highlights are not visibly flattened.** The clamp is a nonlinear
  limiter and flattening real extrema is its characteristic failure. Subjects
  must include specular content; this is the arm most likely to go red.
- **G4. Restoration remains reachable.** `crates/strehl-core/src/restore.rs:127`
  makes `restoration_supported()` false for `ClampedCatmullRom`, for the honest
  reason that a content-dependent limiter has no shift-invariant tap response to
  invert. A default flip therefore removes a shipped feature from the default
  path. **G4 is met only if restoration remains available under an explicit
  opt-in linear resampler, and the release note states the trade in the form
  "the default never invents a value; restoration requires `--resampler
  catmull-rom` and accepts overshoot".** Silently losing restoration is NO-GO.
- **G5. The cost is stated, not buried** — in the release note and in `README`.
- **G6. Byte-freeze fixtures updated prospectively.** `crates/strehl-cli/tests/
  byte-freezes.tsv` pins the current default. A default change must update it in
  the same commit, with the old fixture retained as history.

## 6. NO-GO if ANY of

- **N1. Any subject shows visible loss of real detail or flattened extrema** in
  the blind read. Structural containment does not license destroying content.
- **N2. The blind read is not blind** — if the reader can identify the arms by
  filename, order, metadata, or by having seen either arm before, the read is
  void and must be re-run, not repaired.
- **N3. The only available justification references M8**, a scorecard axis, or
  any census. See the anti-Goodhart clause in section 2.
- **N4. Clamping changes already-in-hull values.** M136 §4.1 records that M172
  leaves in-hull Catmull-Rom values bit-identical. If that is false in the
  shipping path, the clamp is doing something other than containment and this
  decision is void pending re-analysis.
- **N5. An M8 score is taken under a clamped default while M1 is absent.** This
  is prohibited outright by §2.1, not merely discouraged. A GO here changes the
  product; it does not touch the M8 row. If a GO lands, the M8 row must continue
  to report the admitted historical `1.030569%` M8-R failure until M1 exists and
  the registered control at `:1639-1642` can actually be run. **A lane that
  reports a clamped M8 zero as an axis pass has produced a defeated number, and
  the defeat is already written down.**

## 7. Explicitly NOT criteria

- **M8, M8-R, M8-O, or any scorecard row.** Binding; see section 2.
- **The withdrawn `99.7587%` detail-retention figure.**
  `experiments/M134-kernel-frontier/M137-clamped-detail.md:200-290` withdrew its
  resolved-detail interpretation after the flat-ROI null failed — flat regions
  showed a *larger* Catmull-over-bilinear band gap than detailed regions. **That
  number must not be cited in favour of this change by anyone.** It is recorded
  here so that it cannot be quietly reintroduced.
- **Any statistic from the detail-instrument graveyard** — D8, CAND1, CAND2,
  ring-FRC / M-FRC, S25/razor. All killed or barred; see
  `docs/proposals/2026-09-sota-scorecard.md` Revision 1.10 and
  `docs/research/M-PHASE0-SPLIT.md`.
- **Speed.** The clamp is a scalar min/max on an existing gather. If it measurably
  costs throughput that is worth knowing, but M11 throughput is a separate axis
  and must not be traded against containment inside this document.

## 8. What a GO licenses, and what it does not

A GO licenses exactly one sentence: **the shipping default gather never emits a
sample outside the local hull of the source values it gathered from.**

A GO does **not** license: preserved resolved detail, perceptual superiority,
restored-kernel equivalence, a whole-axis M8 claim, or SOTA. M136 §4.4 states
this, and `docs/proposals/2026-09-sota-scorecard.md:1642` states that while M1 is
absent, **M8 may prove only this internal invariant, not SOTA.** Any downstream
document that upgrades this licence is defective.

**Citation correction.** M136 §4.4 cites
`docs/proposals/2026-09-sota-scorecard.md:1573-1582` for this limitation. I read
those lines in the live tree and they are the M8-O v1.5 legitimacy ruling, not
the licence limitation. The correct anchors are `:1631` (known defeat) and
`:1639-1642` (the M1 control and the SOTA limit). M136's substantive claim is
correct; only its line reference is wrong. Routed to M136 as a defect in its own
document, and recorded here so the wrong anchor is not propagated further.

## 9. What would make me wrong

- **The clamp's benefit may be structurally real but perceptually absent.** If
  Catmull-Rom's overshoot at real macro edges is already below the quantisation
  floor of a 16-bit output, then containment is a guarantee about nothing
  visible, and I would be trading a shipped feature for a certificate. **The
  blind read in G1-G3 is the check, and a "no visible difference in any arm"
  result should be read as evidence for this concern, not as a clean pass.**
- **I may be reasoning toward the axis without noticing.** I found this route
  while looking for movement on M8 and I am the one who benefits from a green
  square. Section 2's clause is written against my own incentive and G1's
  non-author requirement exists because I should not be the reader.
- **Three subjects may be too few** for a nonlinear, content-dependent operator
  whose failure is content-dependent by construction.
- **`n_eff` is small in flat regions** (M111 measured it collapsing to `1.6`).
  Clamping interacts with the merge's phase averaging, and the flat regions where
  the waxy-blob artefact lives are exactly where the averaging argument is
  weakest. If the clamp misbehaves anywhere it should misbehave there, and no
  arm below currently targets it. **Recorded as the weakest point in the GO case
  before any data is taken.**

## 10. Result

**UNRESOLVED.** No arm has been read. Executing lanes append findings below this
line under their own lane heading and do not modify sections 1-9.
