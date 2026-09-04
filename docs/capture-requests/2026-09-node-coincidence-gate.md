# Superseded gate: witness geometry for the former 407-frame protocol

**Status: SUPERSEDED for the current shoot.** The active A7C II automated-
bracketing gate is frozen inside
[`2026-09-319-frame-session.md`](2026-09-319-frame-session.md) under *Frozen
repeatability gate*. This file is retained only as the historical 24-witness
geometry gate for the former 407-frame protocol; do not apply it to the current
443-frame shot list.

This document fixes, in advance, the witness-geometry prerequisite for pass A
and pass B of a given step width. Passing it does **not** by itself make them a
repeat pair: exact command-manifest identity and the separately pre-frozen
pixel-domain ladder-equivalence gate must also pass. It exists because the
alternative — looking at the frames and then deciding what counts as coincident
— is not a measurement.

**Binding: whoever applies this gate did not write it, and whoever wrote it does
not take the reading.** If the reading is taken by the author of this file, the
result is void and must be retaken by another party.

---

## 1. What the witness frames are for

The session carries **24 witness frames**: six locked-focus frames immediately
before each of the four sweep passes (`sw4-A`, `sw4-B`, `sw10-A`, `sw10-B`), all
at the same reset position, all at the same fixed exposure as the sweeps.

They are not sweep data and are never merged. They exist to answer one question
that the sweep frames themselves cannot answer:

> When the rig returned to the reset position to begin pass B, did it return to
> where it was when pass A began?

Focus is **locked** during a witness burst, so any frame-to-frame difference
inside one burst is vibration, air, thermal drift and sensor noise — not focus.
Between bursts, the operator has reset focus, so a difference can come from rig
or subject displacement **or from reset focus/magnification error**. This gate
measures the geometric consequence; it cannot assign the cause or prove that
the complete commanded ladders match.

## 2. Why this gate is needed at all, and what it is not

For final-render FRC alone, the requirement is weaker than "the two passes
visited identical focus positions": separately acquired noise and matched
effective focus support are sufficient. The same capture now also serves
`V-HEADTOHEAD3`, which requires frame `i` of A and B to be independent
same-focus repeats. `docs/research/M-FRC-VIABILITY.md` §1.1 therefore rules that
the stronger frame-indexed contract governs the shared capture.

This gate does **not** certify per-node focus equality. It certifies two
observable geometric conditions:

1. the latent subject did not move between the passes, and
2. the two passes register to each other within the bar the program already
   uses for registration.

**This gate cannot detect a focus-ladder offset that leaves the rig
undisplaced.** That limitation is stated here so it cannot later be presented as
a guarantee this document made. What it detects is displacement, which is the
failure that has actually occurred in this corpus. Passing this gate is
necessary but not sufficient for either consumer; the separate input-only
focus-command/ladder-equivalence gate required by `M-FRC-VIABILITY` must also
pass.

## 3. Provenance of the bar

The bar is not new and is not chosen here. It is the local-geometry bar already
in force, and it already has a measured pass and a measured failure:

| Reading | Value | Outcome |
|---|---:|---|
| Bar | `0.10` native-pixel local RMS | — |
| SPLIT2 bright block | `0.064031` | passed |
| SPLIT2 second block | `0.107703` | **failed** |
| Independent reproduction of the failure | `0.105202` | confirms the failure |

`docs/research/M-FRC-VIABILITY.md` §§1.3 and 6. The independent reproduction
matters: the failing number is not an artifact of one implementation.

Reusing this bar is deliberate. Inventing a second, looser registration bar for
witness frames specifically would be indistinguishable from tuning the gate to
let the data through.

## 4. The frozen predicates

Let a **burst** be one set of six witness frames. For each burst, and for each
pair of bursts, registration is measured with the **same local-geometry
estimator, at the same settings, that produced `0.064031` and `0.107703`**. No
new estimator may be introduced for this gate.

**Registration must use integer-pixel alignment only.** Sub-pixel resampling
adds blur to the quantity being measured, and the whole point of `Crop`-style
native-scale handling in this program is to avoid exactly that.

### G0 — Floor. The instrument must be able to see the bar.

For each burst, compute the within-burst local RMS across its six frames.

> **G0 passes if every burst's within-burst RMS is `<= 0.033` native-pixel
> local RMS**, i.e. at most one third of the bar.

**Rationale, fixed in advance:** a between-burst reading is only interpretable
if the noise floor is well below the bar. At one third, a burst pair sitting
exactly at the floor cannot manufacture a spurious failure, and a genuine
displacement at the bar is separated from the floor by a factor of three. If
G0 fails, the session was too unstable to certify anything and **no pair may be
declared valid**, regardless of what G1 reads. G0 is reported first and
unconditionally.

### G1 — Pairing. The two passes of a repeat pair must coincide.

For each of the two candidate pairs — (`sw4-A`, `sw4-B`) and
(`sw10-A`, `sw10-B`) — compute the between-burst local RMS between the two
bursts that immediately preceded those passes.

> **G1 passes for that pair if the between-burst local RMS is `< 0.10`**
> native-pixel local RMS — strictly less than, matching the existing bar, under
> which `0.107703` failed.

### G2 — Drift. The session must not have walked.

Compute the between-burst RMS for all six burst pairings and report the full
`4x4` matrix, not only the two pairings G1 uses.

> **G2 is diagnostic and does not gate.** It is reported because a monotone
> increase across the session indicates continuous drift rather than a discrete
> disturbance, and that distinction changes what the failure means. Recording it
> costs nothing and cannot be recovered later.

## 5. What failure costs, and what it does not

**The gate is per-pair.** A failure of one pair does not invalidate the other.
This is deliberate: `sw4` and `sw10` are separated in time and by a `sw1`
reference block, and there is no reason a disturbance affecting one must affect
the other.

| Outcome | Consequence |
|---|---|
| G0 fails | No pair passes the witness-geometry gate. Sweeps remain usable for anything not requiring pairing. |
| G0 passes, both G1 pass | Both pairs pass witness geometry and remain eligible only if the separate focus-command and ladder-equivalence gates also pass. |
| G0 passes, one G1 fails | That pair is ineligible. The other passes witness geometry but remains conditional on both focus gates. |
| G0 passes, both G1 fail | No pair passes witness geometry; the rig does not return to position, which is a rig finding worth recording in its own right. |

**In every witness-gate failure case the sweep frames themselves remain fully
usable** for any instrument that does not require A/B pairing — including the
split-half family, which splits odd/even *within* a single dense bracket and
therefore never depends on this gate. The `sw1` block at 91 frames is unaffected
by any outcome here. A failed gate costs the pairing, not the session.

## 6. Prohibited responses to a failure

Fixed in advance, because each of these will be tempting:

- **Do not widen the bar.** `0.10` is inherited, not chosen, and it has a
  measured failure at `0.107703` behind it.
- **Do not substitute a different registration estimator** to obtain a passing
  number. The estimator is pinned to the one with existing provenance.
- **Do not select a subset of the six frames per burst** to lower a reading.
  All six are used, or the burst is reported as unusable with the reason given.
- **Do not use sweep frames in place of witnesses** if a witness burst is
  defective. Sweep frames differ in focus by construction and cannot separate
  displacement from focus, which is the one thing this gate exists to do.
- **Do not treat a G2 pattern as licence to reinterpret a G1 failure.** G2 is
  diagnostic and was declared diagnostic before the data existed.

## 7. Reporting requirement

The reading must report, in this order: G0 per burst (four numbers), the full
G2 matrix (six numbers), then the two G1 verdicts. Reporting G1 first invites
selecting a floor that suits it.

Every number is reported whether or not it passes. A gate that reports only its
passes is not a gate.
