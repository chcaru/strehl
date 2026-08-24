# M95 arm 8 — the rescale is a step function at the lattice, and the kernel is the lever

`experiments/M95-dose/`, pre-registration in that directory. Every number below
was printed by `y1_dose.py` or `y2_combined.py` in this session.

## 1. Headline

The orchestrator corrected its bar from +0.1301 to ≈ +0.19 dex, revising it
before the fix existed — the only window in which moving a registered bar is
legitimate, and it said so. The corrected bar is still unreachable, and this arm
shows why in a single column of numbers.

The coverage scale acting **alone**, swept across and through unity:

| k | ISO(k) — scale alone | COMP(k) — as shipped |
| --- | --- | --- |
| 0.8000 | +0.1546 | +0.1499 |
| 0.9000 | +0.1603 | +0.1595 |
| **0.9315** | **+0.1836** | **+0.1845** |
| 0.9800 | +0.1805 | +0.1815 |
| **1.0000** | **−0.0000** | **+0.1667** |
| 1.0200 | +0.1765 | +0.1758 |
| 1.1000 | +0.1731 | +0.1689 |
| 1.2500 | +0.0862 | +0.0776 |

Read the ISO column first. At **k = 1.0000 it is −0.0000 dex — exactly free.**
At **k = 0.9800, a 2% scale, it is +0.1805** — that is **98.3%** of what the
full 7.35% enlargement costs at k = 0.9315. The cost does not grow with the
enlargement. It switches on the moment the sample phase leaves the lattice.

**This confirms the orchestrator's own sentence — "a pure crop loses nothing;
reconstructing on a new grid at all is what costs" — precisely.** It is also
exactly why the conclusion drawn from it does not follow.

Now read the COMP column, which is what strehl actually computes. At
**k = 1.0000 — the coverage scale entirely removed — it still costs +0.1667 dex.**
`fit_to_cover` returns `s.then(t)`, one composed mapping and one gather, so
removing `k` leaves each frame's own similarity `(a, b)` in place and the phase
stays off-lattice. Removing the stretch is a move from one point in the
switched-on region to another point in the switched-on region.

**Recovery: +0.0179 dex, 9.7%.** Registered **B13** (orchestrator's model,
recovery ≥ 0.10) does not fire. Registered **B14** (the cost is a gather, not a
scale) fires.

## 2. What does work, measured on the real warps

Since the gather cannot be removed, the question becomes whether it can be made
cheaper. Arm 7 measured lanczos3 beating catmull-rom by +0.1343 dex on synthetic
phases; this crosses the two changes on the shipped mapping so they can be
attributed separately:

| arm | k | kernel | cost (dex) | sem |
| --- | --- | --- | --- | --- |
| TODAY | 0.9315 | catmull-rom | +0.1845 | 0.0049 |
| NOK | 1.0000 | catmull-rom | +0.1667 | 0.0060 |
| KERN | 0.9315 | lanczos3 | +0.0685 | 0.0049 |
| BOTH | 1.0000 | lanczos3 | +0.0564 | 0.0021 |

| change | recovery |
| --- | --- |
| coverage scale removed | **+0.0179 dex** |
| kernel only | **+0.1160 dex** |
| both | **+0.1282 dex** |
| what coverage adds on top of the kernel | **+0.0121 dex** |

**The kernel recovers 6.5× what the coverage fix recovers**, on the same tiles,
the same warps and the same metric. **B17** (both ≥ 0.10) fires. **B18** (kernel
alone ≥ 0.10) fires. Arm 7's synthetic +0.1343 transfers to the real warps at
**+0.1160**, so the registered falsifier of the §7 patch does not fire and the
patch recommendation stands.

**B19 does not fire.** I registered "do not bundle" at extra < 0.01 and the
extra is **+0.0121**, just above it. So the coverage change is not quite
nothing on top of the kernel — but it is **9.4%** of the combined recovery, and
the two must still be landed and attributed separately.

## 3. Three things that went against me, reported because they went against me

**3.1 My own B15 failed.** I registered "COMP(k) is flat across the whole sweep,
max − min < 0.05". The measured spread is **0.1069** and the bar does not fire.
It is driven by the two extreme k values — 0.80 reads +0.1499 and 1.25 reads
+0.0776 — where the resample is far enough from unity that the band-matching
changes regime. Restricted to 0.90 ≤ k ≤ 1.10 the spread is small, but **that
restriction is post-hoc and I am labelling it as post-hoc rather than quietly
re-stating the bar over the range that would have passed.** The claim B15 was
meant to carry is instead carried by the ISO column, which does not need it: a
2% scale costing 98.3% of a 7.35% scale is the whole of "threshold, not dose".

**3.2 I did not reproduce M104's number.** My `ADD` arm — a second gather at
`1.073537` on an already-gathered tile, which is M104's plant — reads
**+0.1000 ± 0.0046 dex**, against M104's **+0.1789 ± 0.0055**. Same operation,
different instruments, and they disagree by more than either standard error.
Plausible causes are the tile set, the source (I gather from
`single-noalign.tif`, a single frame) and the band convention. **I am not
claiming M104 is wrong** — its correction to the round-1 proxy is sound and its
direction is right. But the verdict here does not rest on `ADD`: it rests on
`COMP(1.0) = +0.1667 ± 0.0060`, measured directly, and on `ISO(0.98)` vs
`ISO(0.9315)`, which involve no plant at all.

**3.3 A control passed by luck rather than margin.** K14 required
|ADD − NULL| ≥ 0.10 and measured **0.100058** — it cleared the bar by
**0.000058 dex**. That is not a margin, and had it landed the other side I would
have had to report no arm numbers at all. Recording it because a control that
passes by 6×10⁻⁵ should not be described afterwards as having passed.

## 4. Controls

| control | reading | bar | |
| --- | --- | --- | --- |
| K12 NULL, catmull-rom, identity, k=1 | **−0.000041 dex** | \|c\| < 0.005 | PASS |
| K13 RESPONSE, planted σ = 1.0 px blur | **+2.118865 dex** | ≥ 0.20 | PASS |
| K14 SEPARATION, \|ADD − NULL\| | **0.100058 dex** | ≥ 0.10 | PASS, barely |
| K16 NULL, lanczos3, identity, k=1 | **−0.000041 dex** | \|c\| < 0.005 | PASS |

K12 and K13 together are discipline 594 discharged: the instrument reads
−0.000041 when nothing happened and **+2.118865** when a known σ = 1.0 px blur
was planted, a span of over 2.1 dex. It could have said otherwise, and it did.

K16 matters specifically because lanczos3 is the recommended kernel: reading
−0.000041 at identity phase proves it is interpolating, so the KERN and BOTH
numbers measure its behaviour under motion rather than its own resampling of a
stationary image.

**P13 confirmed.** I predicted ISO would be flat off-lattice rather than
monotone in |k − 1|, reproducing M104's flatness on the isolated scale. It is
**not monotone**. M104's dose-flatness is real and reproduces here.

## 5. What this means for the fix

The native-sampling emit is **not worthless** — it recovers +0.0179 dex alone
and +0.0121 on top of the kernel, and it costs nothing to have, since a pure
crop genuinely is free. It is simply not 48% of the deficit, and no bar set
near +0.19 can be met by it.

Two things follow for scoring, and the second is the one that would otherwise
waste M104's time:

1. **Score the emit change against ≈ +0.017 dex, not ≈ +0.19.** If M104 scores
   it against +0.19 it will read FAIL on a change that did exactly what it
   should.
2. **M104's finding #2 is the reason its own scoring plan needs the third arm it
   named.** On `bee-3-cpl` registration's gain and the resample's loss cancel at
   0.55σ. The ISO column explains the mechanism: the loss is a fixed switch-on
   cost that any registration incurs, so it is constant across the two arms of a
   naive A/B and cancels out of the difference.

## 6. The lever that changes what the owner sees

**The kernel, +0.1160 dex on the real warps**, 6.5× the coverage fix, and it
composes with it for **+0.1282**. The verbatim patch is in
`docs/research/M95-cdiff.md` §7 with its four controls, and
`crates/strehl-cli/examples/m95-lanczos.rs` carries the kernel and asserts them.

It is in `crates/strehl-core/src/align.rs`, which is M86's, so I have not
applied it. **Recommendation unchanged from arm 7: land it as an option, not as
the default, in its own commit.** Lanczos-3 rings ~9.9× harder than Catmull-Rom
at p99.9 and M87 is fighting a halo on the same edges; those two must not be
allowed to collide in a single unattributable change.

## 7. Candidate facts

- **P85.** The coverage scale acting alone costs **−0.0000 dex at k = 1.0000**
  and **+0.1805 dex at k = 0.9800**. A 2% scale costs **98.3%** of what the
  shipped 7.35% enlargement costs. The resampling cost is a step function at the
  sample lattice, not a dose response. `MEASURED`
- **P86.** With the coverage scale entirely removed, strehl's composed mapping
  still costs **+0.1667 ± 0.0060 dex**, because each frame's own similarity keeps
  the phase off-lattice. `MEASURED`
- **P87.** Removing the coverage scale recovers **+0.0179 dex, 9.7%** of the
  gather's cost on the real warps. Registered B13 (≥ 0.10) does not fire; B14
  fires. `MEASURED`
- **P88.** On the real warps, lanczos3 recovers **+0.1160 dex** against
  catmull-rom, **6.5×** what removing the coverage scale recovers. `MEASURED`
- **P89.** Removing the coverage scale and changing the kernel compose to
  **+0.1282 dex**; the coverage change contributes **+0.0121** on top of the
  kernel, **9.4%** of the combined recovery. `MEASURED`
- **P90.** Arm 7's synthetic-phase kernel estimate (+0.1343 dex) transfers to the
  real shipped warps at **+0.1160 dex**, so the synthetic phase average
  over-estimated the real gain by 15.8% while preserving the ordering. `MEASURED`
- **P91.** A second gather at 1.073537 on an already-gathered tile costs
  **+0.1000 ± 0.0046 dex** in this harness, against M104's **+0.1789 ± 0.0055**
  for the same operation. The two instruments disagree by more than either
  standard error and the discrepancy is **unresolved**. `MEASURED`
- **P92.** ISO(k) is **not monotone** in |k − 1|, reproducing M104's dose
  flatness on the isolated scale rather than on the render. `MEASURED`
- **P93.** My registered B15 (COMP spread < 0.05 across the full sweep) **failed**
  at a measured spread of **0.1069**, driven by k = 0.80 and k = 1.25. The
  threshold claim is carried by the ISO column instead. `MEASURED`
- **P94.** Control K14 cleared its 0.10 bar by **0.000058 dex**. It passed, but
  by luck rather than by margin. `MEASURED`

## 8. Scope and falsifiers

- The quarantined `bee-3-cpl` sidecar carries only **8 placed frames**, so the
  COMP column is a smaller warp sample than arm 7's. **The ISO column uses the
  identity frame and is completely independent of the warp set**, and it is the
  ISO column that carries the headline, so the conclusion does not depend on the
  quarantine. The original sidecar being restored would let COMP be re-run at 24
  frames and I would expect the third decimal to move.
- **What would falsify §1:** ISO(k) reading materially above zero at k = 1.0
  exactly, or ISO(0.98) reading materially below ISO(0.9315). Both are one
  `y1_dose.py` run away.
- **What would falsify §2:** KERN failing to beat TODAY on a different stack, or
  K16 reading non-zero, which would mean the lanczos3 in this harness is not
  interpolating.
- **Unresolved and I want it on record:** the `ADD` discrepancy with M104 in
  §3.2. Two instruments priced the same operation and disagreed 2:1. Neither
  side's headline depends on it, but one of the two is wrong about something.
- **Capture request, still outstanding** (`docs/captures-needed.md` is the
  orchestrator's): R, G and B filtered exposures of one static high-detail
  subject, for a CFA-free demosaic ground truth.

## 9. Verification of this report

- `experiments/M95-dose/src/verify_report.py` — **33/33 anchors present, 33/33
  discriminating**, 10 facts / 10 status labels. The discriminate pass perturbs
  one digit of every anchor and requires the perturbed string to be absent, so
  an anchor matching some other row of the document is caught rather than
  counted.
- `experiments/M95-dose/src/verify_negative_control.py` — **green → red, red,
  red → green** across a wrong number in the report, a wrong number in the
  source JSON, and a stripped fact label. Each mutation is anchored on an exact
  full-line string and a miss is a hard error rather than a pass.
- Both instruments' raw stdout is preserved in `out/y1_dose.txt` and
  `out/y2_combined.txt` alongside the JSON.
