# M120b pre-registration — mechanism of the background patchwork

Written **before** any M120b measurement was run. Existence is settled by ORCH
(facts 1616–1620) and is not re-litigated here. This is about **mechanism only**.

Commit this file before running `14_*.py` onward.

---

## ORCH's hypothesis (to be killed or confirmed)

> Where the background is defocused in every frame, the through-focus response is flat,
> so the data term is at the noise floor. The **spatial regulariser** then dominates
> completely, and a smoothness term with a vanishing data term produces large flat regions
> with arbitrary hard boundaries.

Supporting argument ORCH gives: *"raw argmax noise would be pixel-scale salt-and-pepper,
not blobs tens of pixels across. Something is imposing spatial coherence. The regulariser
is the only thing in the pipeline that does that."*

## The structural objection, stated before measuring (ARGUED)

The last sentence is **false as a matter of code**, and this is checkable without any
pixels. The chain in `crates/strehl-core/src/focus.rs` + `merge.rs` is:

| stage | operator | support | source |
| --- | --- | --- | --- |
| 1 | Sobel 3×3, squared (Tenengrad) | 3 px | `SOBEL_RADIUS = 1` |
| 2 | **box sum over the focus window** | **27 × 27** | `WINDOW_RADIUS = 13`, 729 taps (`focus.rs:899`) |
| 3 | `regularise` = `box_mean` | 17 × 17 | `REGULARISER_RADIUS = 8` (`merge.rs:93,194`) |
| 4 | argmax over frames | — | |

There are **two** spatial-coherence operators, and the one applied *first* is **larger**
(27 px) than the regulariser (17 px). Argmax of a field that has already been box-summed
over 27 px cannot be salt-and-pepper: the field's correlation length is 27 px, so its
argmax is coherent over ~that scale by construction. **The regulariser is therefore not
necessary for blobs, and may be a minor contributor.**

This predicts a specific, falsifiable outcome, registered as M1.

---

## Pre-registered tests, predictions and decision rules

Notation: `A(x)` = mean area of connected components of constant elected index over the
background ROI, in px. "Shipped" = window ON + regulariser ON.

### M1 — the operator-isolation test (decisive; M120b's own, not on ORCH's list)

Recompute the elected-index field from the raw 299-frame luma cube, replicating the
shipped chain exactly, and **toggle stage 3 and stage 2 independently**:

| arm | stage 2 window | stage 3 regulariser | |
| --- | --- | --- | --- |
| **C** | 27×27 | 17×17 | shipped |
| **B** | 27×27 | **OFF** | the decisive arm |
| **A** | **OFF (1×1)** | OFF | positive control for salt-and-pepper |
| **A′** | OFF (1×1) | 17×17 | regulariser acting alone |

**Pre-registered predictions.**

- *ORCH's hypothesis predicts* arm **B** collapses toward pixel scale: `A(B) < 0.10 × A(C)`.
- *M120b predicts* arm **B** retains most of the blob size: **`A(B) > 0.50 × A(C)`**.
- Both predict arm **A** is near pixel scale: `A(A) < 5 px`. **If arm A is not near pixel
  scale the instrument is broken and no other arm may be reported.** (Positive control for
  the *ability to show* salt-and-pepper — without it, "B has blobs" is unfalsifiable.)

**Decision rule.** `A(B) > 0.50 × A(C)` ⇒ ORCH's mechanism **REFUTED**: the regulariser is
not necessary. `A(B) < 0.10 × A(C)` ⇒ ORCH's mechanism **CONFIRMED**. Between the two ⇒
**partial**, report the fraction and claim nothing stronger.

### M2 — the scale prediction

If the window sets the scale, blob diameter should sit near 27 px, not near 17 px, and
**not** at the 43 px composite. Pre-registered: equivalent diameter `√(4A/π)` for arm C in
**20–45 px**; for arm B in **20–35 px**. A result far outside these ranges falsifies the
window-scale account and I must say so.

### P1 (ORCH) — do render blobs coincide with elected-index boundaries?

Predicted **YES** (M120 already measured ρ = +0.5465 against a +0.0077 shift-null at gate 0).
Registered as a **replication on independent data** (M96's Rust-produced `elected-index.tif`,
which M120 has never touched). Decision: edge-coincidence ratio > 3× the shifted null ⇒
constant-index regions confirmed as the blobs. **< 1.5× ⇒ ORCH's mechanism dead outright**
and M120's own earlier coincidence number is thereby impeached too.

### P2 (ORCH) — is the margin at the noise floor in the background?

**This test must separate two quantities ORCH's wording conflates**, and the separation is
the crux:

- **response level** (the data term itself). M120 measured this at **15.0× the pure-noise
  ceiling** in the background — the data term does **not** vanish. Predicted to replicate:
  background response ≫ noise floor.
- **margin** (winner minus runner-up). M120 measured 0.216 gate units. Predicted **small**,
  i.e. at or below ~1 noise unit.

**Predicted outcome: margin IS at the noise floor while response is NOT.** That combination
falsifies "the data term vanishes" while leaving "the election is degenerate" standing.
Decision: if background *response* is also at the noise floor, M120's earlier R1a refutation
was wrong and I must retract it.

### P3 (ORCH) — regress blob size against local margin

ORCH predicts blob size grows as margin falls (`ρ < −0.3`, monotone across margin deciles).

**M120b predicts a weak or absent relationship** (`|ρ| < 0.2`) with blob size **pinned near
the window scale across all margin deciles**, because the correlation length of the argmax
is set by the box supports and not by how close the contest was.

Decision rule, registered in the direction that can embarrass me: **if blob size rises
monotonically across margin deciles with `ρ < −0.3`, ORCH is right and I am wrong**, and I
will report that as the headline.

### P4 (ORCH) — subject-region negative control

Predicted: subject ROI shows **higher margin** and **smaller** constant-index components.
Decision: if the subject region is indistinguishable from the background on both, then
nothing measured here is specific to the flat-response case and **every P1–P3 result must
be withdrawn**.

---

## Controls that must pass before any headline

1. **Positive control (M1 arm A)** — the component metric must be able to read ~1 px.
2. **Null (shift)** — P1's coincidence must be computed against a large-offset shift of one map.
3. **Null (iid)** — M96 ships `elected-index-null-iid.tif`; its component sizes must be near
   pixel scale. If the *null* field also shows blobs, the component metric is measuring the
   operator and not the data, and P1/P3 are void.
4. **Reference choice (discipline 829)** — where a set of references exists, use the one that
   argues **against** the conclusion I expect. For M1 that means comparing arm B against the
   **largest** plausible `A(C)`.

## Reader discipline (discipline 828)

Every `.tif` read via `tifffile.imread` followed by an explicit `assert` on dtype. No PIL
read of any TIFF. PIL is permitted only for `.save()` of PNG previews.

## Scope limits stated in advance

- Blob *size* is measured on the elected-index field, not on the render; the render's steps
  are a consequence of index changes, and M120 already tied the two together at gate 0.
- Everything here is `bee-3-cpl` plus whatever M96 stacks are read for P1–P4. Generalisation
  beyond those stacks is not claimed.
- **No render A/B.** `STREHL_SOFT_GATE` belongs to M116.
