# ORCH — pre-registration: should `strehl stack` default to Lanczos-3?

**Status: NO-GO as of 2026-08-25. The decision is SUSPENDED, not merely
unresolved — see AMENDMENT 3 at the foot of this document.** The last gate (G3)
was met on 2026-08-24, and on the same night the measurement that motivated the
whole question was **withdrawn by its own author**. The cost of the change is
still measured; the benefit no longer is. Do not read "all gates met" as "go".

**Status (original):** PRE-REGISTERED. Written **before** the combined comparison sheet exists.
**Author:** ORCH (orchestrator). **Decision owner:** ORCH.
**Written at:** `c1da5ab`, with M107 wiring chromatic aberration, M109 holding
`merge_cmd.rs`/`align_cmd.rs`, M110 preparing the sheet, M111 building the soft gate.

---

## 1. Why this document exists

Every milestone in this project is required to register its bars before it looks
at its data. I have never done that for a decision of my own, and I am about to
make one on evidence I commissioned, about a change I have already told four
agents I expect to make. **That is the exact circumstance in which a bar written
afterwards is worthless.**

I have also, tonight, been wrong three times about the state of the tree (facts
1453, 1460, 1476) and twice broadcast a diagnosis I had not run (facts 1454, and
the M111 election-map correction). My judgement is not the reliable instrument
here. The bars are.

**Fact 1464 records my own by-eye read and states plainly that I am not an
independent judge of it: I re-prioritised three agents on the strength of fact
1420 and then went looking at its output hoping to see a win.** This document is
the guard on that.

## 2. The decision

`align_cmd.rs::merge_config` returns `Resampler::CatmullRom` as a literal. The
question is whether it should return `Resampler::Lanczos3`.

This is **not** the question of whether Lanczos-3 is a better interpolator. That
is settled well past the standard this project uses for anything else.

## 3. What is already established, and by whom

| finding | value | source | independent? |
| --- | --- | --- | --- |
| synthetic accuracy gain | **+0.1366 dex** (M95: +0.1343) | M113 own route, 3 instruments, 117 tiles | yes — re-derived |
| **end-to-end** gain through the shipped merge | **+0.083 to +0.099 dex**, sem 0.0010-0.0031 | M113, two 299-frame merges | yes |
| gain where the election held still | **+0.0968** vs **+0.0604** where it did not | M113 stratified | yes |
| excess local extrema in the merge | **1.00x** (0.9924 / 0.9938 / 1.0039 / 1.0048) — **SUPERSEDED, see §8.2: 1.21x at edges** | M113 reference-free census | yes |
| edge overshoot end-to-end | **<= 1.47/255, sign-changed** | M110, different route | yes — uncorrelated |
| by-eye, real hairs and text | **better, no visible ringing** | M113, M110, ORCH | 3 uncorrelated reads |
| wall-clock cost | **2.478x** (bee, 299 fr) / **3.529x** (text) | M110, flagged unpriced by M113 | yes |
| ringing mechanism | mean `n_eff` **55.3**; ringing is phase-dependent and averages down, passband gain does not | M113 | yes |

**The objection that gated this for weeks — fact 1374's 9.902x overshoot — has
been explained rather than contradicted.** *(**§8.1: the 9.902x figure was
retired by its own author; the real value is 1.78x.** The explanation below
stands, but it was explaining a number 5.6x too large.)* It was measured on a
*single frame at
a half-pixel phase*. A 299-frame merge is a different object and the quantity
does not transfer across that boundary. Both M110 and M113 drew that distinction
independently and both refused to let their result be read as refuting 1374.

## 4. The live objection, which is not about ringing

**M110, unprompted, having never seen M107's work:** the dominant artefact at x6
is **lateral chromatic aberration**, not sharpness and not ringing — *"every
spicule carries a cyan/red pair"* — and **Lanczos-3 makes it more conspicuous by
sharpening the fringes.**

I saw the same thing independently before reading that sentence (fact 1464).
Fact 1452 predicted the mechanism: **Catmull-Rom has been buying CA suppression
with blur.** Removing the blur does not create the fringes — they are optical,
and they are equally present in the shipped default — but it does stop hiding
them.

**So a Lanczos-3 render shipped today would be sharper AND more visibly fringed,
and the owner has told me his stacks "don't look too good yet."** Shipping it
alone is a defensible engineering decision and an indefensible product one.

## 5. Pre-registered criteria

### GO requires ALL of:

- **G1.** The chromatic aberration correction is **wired, landed, and demonstrably
  reaching rendered pixels** — not merely present in `optics.rs`. The check is a
  render that differs with the correction on, plus a **byte-identical null** with
  it off. *(Until tonight `OpticalProfile` had zero consumers outside its own
  file; a "CA arm" would have been a silent no-op.)*
- **G2.** On a 1:1 comparison sheet at HEAD, the **combined arm (CA + Lanczos-3)**
  is judged better than the shipped default by **at least one agent that authored
  neither the kernel claim nor the CA correction.** My own eye does not count
  toward this, by fact 1464.
- **G3.** A **`--resampler` flag exists on `strehl stack`**, so the change is
  declinable. A 2.5x-3.5x cost imposed with no way to opt out is not acceptable
  under a brief that says *"high-performance (speed **and** quality)"*.
- **G4.** The **cost is stated in the release note and in `README`**, in the form
  "N x wall-clock for +X dex", not buried.

### NO-GO if ANY of:

- **N1.** Visible ringing or a dark rim appears on **occluding silhouettes** in the
  combined arm at 1:1. This is fact 1374's real concern and it outranks any metric.
- **N2.** The CA correction makes the **corners** visibly worse. M107's fit is
  supported only to **r = 0.788**; at r = 1.0 the correction is 2.98 sensels of
  which **0.63 is extrapolated from the model's shape**. The sheet includes a
  corner crop precisely to test this.
- **N3.** The **red-only correction looks worse than no correction** on a red/cyan
  fringe. `eps_b` is `None` — blue was never fitted — so at most half of each
  fringe is addressed, and a half-corrected fringe may read worse than a
  symmetric one.
- **N4.** The election-agreement stratification **reverses** on a second subject —
  i.e. gain becomes *larger* where the election disagrees. That would mean the
  measured gain is a reshuffled election rather than better interpolation.

### Explicitly NOT criteria

- **The metric alone.** M113 showed the discriminating control C4 is an unbounded
  ordering on passband gain that **ranks a 137 %-overshoot kernel first**. A
  metric that prefers more ringing cannot license a kernel.
- **My own by-eye read** (fact 1464), for the reason stated in section 1.
- **Cost as a veto.** Given G3 and G4, I am willing to trade 2.5x-3.5x warp time
  for +0.085 dex **as a default**, because quality is the harder thing to recover
  later and the flag makes it declinable. **Lanczos-3 is separable and the
  current path is a scalar gather, so this cost is a target, not a constant.**

## 6. What would make me wrong

- **The three by-eye reads are not as independent as I am treating them.** All
  three looked at crops chosen by the same harness, on two subjects, and two of
  the three knew the hypothesis. The corner and specular crops were near-useless
  discriminators in my own read. *Mitigation: G2 requires a non-author, and M110
  is adding subjects with specular highlights and corner content.*
- **The gain may be concentrated where nobody looks.** +0.085 dex is a whole-frame
  aggregate; the central-half figure is markedly higher than the whole-frame one
  (+0.0887 vs +0.0299 at 64 px), which means the border contributes little. If the
  gain lives mostly in already-sharp regions, the visible improvement is smaller
  than the number suggests.
- **`n_eff` = 55.3 is a mean.** Fact 1141 already warns that a whole-image mean
  cannot answer a per-pixel question, and M111 measured `n_eff` collapsing to
  **1.6** in exactly the flat regions where the waxy-blob artefact lives. **Where
  `n_eff` is small, the phase-averaging argument that kills ringing does not
  apply.** If ringing appears anywhere, it should appear there — and that is a
  specific, checkable prediction that no one has yet tested. **This is the single
  weakest point in the GO case and I am recording it as such before the data
  arrives.**

## 7. Sequencing consequence

The soft gate (fact 1470) raises `n_eff` in precisely the low-`n_eff` regions
named above. **If it lands first, it strengthens the anti-ringing argument
structurally rather than empirically.** That is an argument for kernel-after-gate
ordering, and I am recording it now so that if the order ends up that way it is
visibly a plan and not a rationalisation.

## 8. AMENDMENT 2026-08-24 — the weakest point was real, and the threat number was stale

*Added after M113 reported, before the comparison sheet exists. Criteria in §5
are unchanged; this section corrects two factual inputs to them and records the
outcome of the prediction in §6.*

**8.1 The 9.902x figure in §3 above is retired and must not be quoted again.**
Its own author withdrew it: `M95-kernel.md` §22.4 states plainly *"The 9.902x
ringing figure is stale, and it is still being quoted,"* and P95 gives **1.78x**.
The 9.9x reproduces at 9.06x only on an ungated population that is **99.87%
noise**. M113's independent positive control measures **1.793x**. So the sentence
in §3 — *"the objection that gated this for weeks"* — was gating on a number that
had already been withdrawn by the person who measured it. **Read 1.78x wherever
this document says 9.902x.** The explanation offered in §3 still stands; it was
explaining a figure 5.6x larger than the real one.

**8.2 My stated weakest point in §6 was a genuine weakness. Ringing does survive
where `n_eff` is small.** M113 stratified its census by `n_eff` using an
independent third arm's map (discipline 752) rather than either arm under test.
Over the clean stratum of 2 605 077 quads: **1.143x** overall, **1.206x** at
edges, **1.450x** at the sharpest 1% of gradients, with **73.1%** of the
single-resample excess surviving the merge. **The 1.00x row in §3's table is
therefore too strong** — it used a blunt extrema census over unrestricted ROIs,
which diluted an edge-only effect to invisibility. I folded that row as a
structural result and it was not one.

**8.3 But the ratio does not climb toward 9.9x. The measured ceiling is 1.425x.**
So the `n_eff`-dependent kernel I speculated about in the brief is **not**
licensed: the span is 1.02x to 1.21x, the whole effect is under two display
levels, and a per-pixel kernel switch would buy a spatial discontinuity worth
more than it removes. Recorded so that the idea is visibly rejected on evidence
rather than quietly dropped.

**8.4 The premise underneath §6's prediction was itself wrong, in my favour.**
I wrote that `n_eff` collapses *"in exactly the flat regions where the waxy-blob
artefact lives."* On `bee-3-cpl` the opposite holds: median 5x5 range is **1654
DN** where `n_eff == 1` versus **46 DN** where `n_eff >= 129`, a factor of
**36**. **Low `n_eff` is where the detail is, not where the flat regions are.**
That makes §7's sequencing argument weaker than written — the soft gate raises
`n_eff` somewhere, but not demonstrably in the regions this document assumed.

**8.5 Net effect on the decision: GO survives, on a repaired argument.** The
whole ringing effect measures **1.67/255** against catmull-rom and **0.6/255**
against un-interpolated nearest, over 32 115 edge profiles — independently
matching M110's `<= 1.47/255` by a different route. Decisively, **lanczos3 sits
closer to the un-resampled reference than catmull-rom does** (45.61 vs 51.70 per
255): a kernel that rang would move *away* from truth, not toward it. The GO case
no longer rests on "ringing does not survive the merge," which is false. It rests
on "the ringing that survives is 1.2x, under two display levels, and points
toward the reference rather than away from it."

**8.6 What this changes about §5.** Nothing. No criterion is added, removed or
loosened. G2's non-author by-eye requirement is now carrying more weight than
when written, because the numerical anti-ringing argument is weaker than §3
claimed.

---

## 9. AMENDMENT 3, 2026-08-25 — NO-GO. The last gate opened and the reason to walk through it closed on the same night.

**Decision: NO-GO. This pre-registration is SUSPENDED and must not be resolved
on its current evidence.**

### What changed, in the order it happened

1. **G3 was met.** M124 landed `--resampler` on `strehl stack` with five kernels,
   the default unmoved and pinned byte-for-byte to a committed freeze fixture
   (`crates/strehl-cli/tests/byte-freezes.tsv`). That was the last outstanding
   GO gate, and it is genuine work: it makes the change **cheap and reversible**.
2. **On the same night, the benefit was withdrawn.** M85 retracted its own
   `+0.1160 dex` sharpness headline — the number this entire document was
   written to act on. Its band, **0.30-0.48 cyc/px**, was measured to be
   **12.8 % subject detail (CI 12.2-13.4 %) and 87.2 % noise**. The retraction
   is not a doubt, it is a placebo result: **a dark frame containing no
   photograph at all** was scored through the identical channel and read
   essentially the same gain, **1.0006**. The defocus null read **+0.0033**.

### Why this is a NO-GO rather than a "wait"

The two terms of the trade have become asymmetric in the worst possible way:

| Term | Status |
| --- | --- |
| **Cost** of Lanczos-3 by default | **Still measured**, 2.5x-3.5x warp time |
| **Benefit** of Lanczos-3 by default | **No longer measured** — the supporting statistic was withdrawn by its author |

§5 was explicit that "cost as a veto" was *not* a criterion, on the reasoning
that a measured sharpness gain justified a measured time cost. **That reasoning
required the gain.** With the gain withdrawn, the document's own logic inverts:
what remains is a real cost purchased with an unmeasured benefit. Proceeding
would not be a close call made carefully, it would be a trade whose favourable
side no longer exists.

### The failure mode this document came within one night of demonstrating

A decision record that tracks **feasibility** gates converges on GO as
engineering lands, because every gate it tracks is a piece of work someone is
being paid to complete. Nothing in the original §5 would have gone red when the
motivating measurement was retracted — **G1-G4 are all still met.** The gate
that should have failed was never written, because the possibility that the
premise would be withdrawn was not on the list of ways to be wrong (§6).

**Generalisation, recorded as discipline 890:** `cheaper to do` and `justified
to do` are different gates, and a decision record must say which one moved. A
retraction does not travel to the decisions that depend on it by itself; the
retracting party must name the decision document, and the decision owner must
carry a live pointer back to the measurement the decision rests on.

### What would reopen this

A sharpness comparison scored in a band **demonstrated in advance** to carry
subject detail, with the dark-frame placebo run first and required to read null.
Not the previous band, and not by-eye alone: G2's non-author eye check was
designed as a *guard* on a quantitative result, and it cannot be promoted to
the evidence itself. Until then the default stays where it is, which is the
outcome the freeze fixture now protects for free.

**Sources:** `M95-kernel.md` (retraction, band composition, dark-frame placebo);
M124's report (flag, freeze fixture, G3); SYNTHESIS facts 1726-1730 (M124),
1736 (retraction), disciplines 884, 890.
