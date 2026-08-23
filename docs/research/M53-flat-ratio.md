# M53 — replacing ACCEPTANCE INVARIANT 1's flat-ROI statistic

Milestone report for SYNTHESIS facts 733–757. **This file is late**, which is
question 192 / fact 843. Read section 0 before using any F-number in it.

Companion artifacts, all committed:

| artifact | commit | what it holds |
| --- | --- | --- |
| `experiments/m53-flat-ratio/` | `d48e659` | code, logs, the negative control |
| `docs/research/M53-flat-roi-statistic.md` | `9e1674f` | question 183 in full |
| `experiments/m53-flat-ratio/out/a5_censoring_endtoend.md` | `217b2ce` | `fold_censored` end to end |

---

## 0. The F-numbering, and what is actually being reconstructed

**No M53 artifact has ever contained an F-number.** The milestone's brief said
"number them LOCALLY from 1 — I renumber on fold", so findings were numbered
1..N *per turn*, restarting each turn, and delivered in the turn's report. The
`F1`…`F10` labels exist only in the orchestrator's fold.

That has a consequence which must be stated plainly, because getting it wrong
would make twenty-five rows quietly wrong instead of loudly unsourced:

**The mapping below is recovered from the fold's own citation column, not from
the author's memory of what it numbered.** Every row of §1 was obtained by
reading what fact *N* cites and what fact *N* claims, then matching that claim
to a committed artifact. Where the fold cites an F-number, that F-number is
authoritative and this file adopts it. **Where no fact cites an F-number, the
finding behind it is not recoverable and is marked so rather than invented.**

The fold uses **four separate namespaces**, which is why "F1" appears more than
once and why a flat F1–F10 list would have been wrong:

- bare `M53 Fn` — turn 1 (the main deliverable)
- `M53 turn-2 Fn`, `M53 turn-3 Fn`, `M53 turn-4 Fn`
- three facts cite a commit hash instead of an F-number

**Audit timing.** `M58c` (`74ac38f`, 14:13:48) reported no `docs/research/M53-*.md`
in any commit. That was true when it ran. `M53-flat-roi-statistic.md` landed at
14:21:44 in `9e1674f`, eight minutes later. The audit was correct and is now
stale on that one point; the F-numbering and index-row findings stand and are
what this file repairs.

---

## 1. Fact → finding map

| fact | cites | recovered |
| --- | --- | --- |
| 735 | `M53 F1` | yes |
| — | `M53 F2` | **UNRECOVERABLE — no fact cites it** |
| 733 | `M53 F3` | yes |
| 734 | `M53 F4` | yes |
| 736 | `M53 F5` | yes |
| 737 | `M53 F6` | yes |
| 757 | `M53 F7` | yes |
| — | `M53 F8` | **UNRECOVERABLE — no fact cites it** |
| 745 | `M53 F9` | yes |
| 743 | `M53 F10` | yes |
| 739 | `M53 turn-2 F1/F2` | yes |
| 740 | `M53 turn-2 F3` | yes |
| — | `M53 turn-2 F4` | **UNRECOVERABLE — no fact cites it** |
| 741 | `M53 turn-2 F5` | yes |
| 738 | `M53 turn-2 self-refutation` | yes |
| 746 | `M53 turn-3 F1` | yes |
| 747 | `M53 turn-3 F2/F3` | yes |
| 749 | `M53 turn-3 F4` | yes |
| 751 | `M53 turn-3 F5` | yes |
| 748 | `M53 turn-3 near-miss` | yes |
| 752 | `M53 turn-4 F1` | yes |
| 755 | `M53 turn-4 F2` | yes |
| 753 | `M53 turn-4 F3` | yes |
| 754 | `M53 turn-4 F4` | yes |
| 742 | `M47 -> M53 55b6b0d` | yes |
| 744 | `M53 4a5c270` | yes |
| 750 | `M53 9168b19` | yes |

**Nothing is at risk from the three unrecoverable slots**: no folded fact cites
`F2`, `F8` or `turn-2 F4`. Either they were reported and not folded, or the
fold's numbering skipped. **I do not know which, and I am not going to supply
findings for them.** Discipline 384.

---

## 2. Turn 1 — the main deliverable (`d48e659`)

**F1 — the replacement kernel reconciles with fact 469's to 0.0038 %.
(MEASURED + DERIVED.)** `x - box9(x)` on `109MSDCF` frame 11, the exact input
behind fact 469's denominator. Raw spatial sd **76.2716 DN** (M41 published
76.272). M41's `hp_sd` (reflect, full) reads **11.7696 DN** against its
published **11.770**. M53 ships **valid-interior** instead (11.1181 DN),
because only there does the white-noise closed form `sd = sigma*sqrt(1-1/w^2)`
hold exactly — **reflect padding duplicates samples and manufactures an edge
one radius in, inflating the residual 5.5 % on this real ROI**. Gain 0.993808
(theory) against 0.994397 ± 0.000938 (M41) and 0.994481 ± 0.001109 (M53).
Fact 469's published 6.3x reconciles as 76.272/11.770 = 6.48 ÷ arm E's own
1.0218 = **6.34**. Source: `src/a1_reconcile.py`, `out/a1_reconcile.log`.

**F2 — UNRECOVERABLE.** See §1.

**F3 — the old statistic reads a planted 10x explosion as 1.513x. (MEASURED.)**
On the 22 real `109MSDCF` flat ROIs at fact 469's own ROI, with `K` solved from
the calibrated model so the truth comes from neither statistic under test:

| K true | OLD reports | NEW reports |
| --- | --- | --- |
| 1.000 | 0.990x | 0.973x |
| 2.000 | 1.010x | 1.842x |
| 5.000 | 1.139x | 4.529x |
| 10.000 | **1.513x** | **9.036x** |
| 22.767 | 2.796x | 20.559x |
| 144.391 | 16.631x | 130.368x |

Source: `src/a3_negative_control.rs`, `out/a3_negative_control.log`
**as that log stood at `d48e659`**. The file at HEAD is *not* this table:
`53d06f5` rewrote the control into the two-arm form of §3, and in doing so
dropped the two `under-reports` columns as withdrawn (see turn-2
self-refutation). The table above is quoted with those columns removed for that
reason. **A bare citation to the path at HEAD would not support this finding**
— which is a fourth instance of F10's failure mode, found in this repair.

**F4 — UNPLANTED, and the finding nobody asked for. (MEASURED.)** On the
shipped pipeline, real frames, no plant:

| merge | LEGACY raw ratio | NEW hp ratio |
| --- | --- | --- |
| `strehl stack`, unregularised argmax | 0.985x | **1.208x** `[0.962 .. 1.306]` |
| `strehl merge --gate 2.0`, regularised | 0.997x | **0.980x** `[0.780 .. 1.059]` |

**The legacy statistic ranks unregularised argmax — the defect the project
exists to remove — as the BETTER of the two, and passes a 21 % noise
increase.** Source: `out/a5_stack.log`, `out/a4_after.log`.

**F5 — fact 441's privileged denominator reproduces live and is now
unrepresentable. (MEASURED.)** Over 22 `109MSDCF` frames the high-pass sd
spread is **1.3575x** (min 8.929 frame 21, max 12.121 frame 9), and the
previously privileged frame 11 sits at **11.118 — near the top, not typical**.
On the shipped default ROI the statistic reads **0.980x** against the median
and **0.850x** against frame 11, a live 1.15x reproduction. `FlatReference`
now has **no single-frame accessor at all**.

**F6 — `boxfilter::horizontal_sums` accumulates row sums in f32.
(MEASURED, pre-existing.)** About **2.2e-4 DN** of box-mean rounding:
negligible on real data (41:1 pedestal-to-residual) but 2.5e-5 relative on a
hostile 353:1 fixture. **Pre-existing, not introduced here, deliberately not
fixed** — a bound was derived and the test strengthened to pin both absolute
sds against their closed form instead.

**F7 — `w = 9` ships although the sweep prefers `w = 3`. (ARGUED.)** Flat-ROI
structure contamination **1.0234x** at `w=3` against **1.2756x** at `w=9` on
`109MSDCF`. Shipped `w=9` to reconcile with M41's kernel, on the argument that
*deleting a statistic for being an unmeasured choice and replacing it with a
different unmeasured choice repeats the error*. Now question 174, and §2 of
`M53-flat-roi-statistic.md` adds independent support for revisiting it: M2's
Immerkaer 3x3 high-pass reads 1.011x of model sigma where the shipped `box9`
reads 1.198x on the same frame and ROI.

**F8 — UNRECOVERABLE.** See §1.

**F9 — fact 441's spread is invariant to any change in the numerator.
(DERIVED.)** Ratios of the form `max_i(N/D_i) / min_i(N/D_i)` cancel `N`
identically, so pre- and post-gain-fix figures for fact 441 **are** comparable
— unlike almost every other pre/post pair on an ISO-50 stack.

**F10 — three independent instances of one failure mode. (ARGUED.)** A
measured correction lands in one artifact and not in its siblings: (a) fact
550's PTC landed in `profile.rs`'s doc and not in `stack.rs`'s user-facing
string; (b) M53's own `flat_ratio.rs` estimate against its committed sweep log;
(c) `profile.rs`'s `read_noise_e_high` doc names the same thing a third time.

**A fourth instance was found while writing this report**, in M53's own work:
`out/a3_negative_control.log` was rewritten by `53d06f5`, so a citation to that
path at HEAD no longer supports the F3 table it was written for. Recorded here
rather than folded, since F10 is already folded as fact 743 with three.

---

## 3. Turn 2 — hardening the control (`53d06f5`)

**turn-2 F1/F2 — the replacement verification is sigma-free and holds across
the gain fix. (MEASURED.)** ARM 1 predicts `g*raw_mid/hp_med` from quadrature
and measures it on real structured ROIs: `109MSDCF` (ISO 160) predicted
7.8531x, measured **7.8491x** (−0.051 %); `119MSDCF` (ISO 50) predicted
12.0815x, measured **12.0649x** (−0.137 %). Quadrature holds to ≤0.02 % over a
512x plant sweep on both.

**turn-2 F3 — the statistic under test contains no calibrated constant.
(DERIVED.)** `hp(merged) / median_i hp(F_i)` is a ratio of measurements, so
unlike M40's null plant it is **not** blind to a wrong noise model. Only the
plant's *label* (`K`) needs sigma. This is why fact 599 does not sink the
milestone.

**turn-2 F4 — UNRECOVERABLE.** See §1.

**turn-2 F5 — a tolerance 168x looser than the achievable margin is
decoration. (MEASURED.)** The first high-pass assertion used 2 % against a real
agreement of **0.0119 %**; a gain-less implementation errs 0.63 % and **would
have passed**. Tightened to 0.2 % and then verified by substituting gain 1.0,
where predicted 87.6622 against measured 87.1143 makes the assertion fail.

**turn-2 self-refutation — the milestone refuted its own headline and withdrew
it. (DERIVED.)** The control plants `p = sigma*sqrt(K^2 - 1/n)`, so as `K`
grows `K/OLD -> raw_mid/sigma` and `K/NEW -> hp_med/(g*sigma)` — **the same
expressions the "prediction" was computed from.** The claim that the prediction
was "met to three decimal places" was arithmetic, and is withdrawn. What
survives is their *ratio*, 7.8531x, with sigma cancelled.

---

## 4. Turn 3 — the fact-324 test (`9168b19`)

**turn-3 F1 — FOUR of five fixture rows were stale, not two, and a second
commit is responsible. (MEASURED.)** `113MSDCF` and `112MSDCF` moved under
`f95f6f4`'s read-noise change, not only the two ISO-50 rows under `2a4f5c5`.
The brief's "the three that reproduced are ISO 160" was wrong: they are ISO
**160, 500, 500**.

**turn-3 F2/F3 — one-sidedness, not freshness, is what survived recalibration.
(MEASURED + DERIVED.)** In the same test over the same recalibration:
`hi/lo > 2.4` (one-sided) stayed true as the measured ratio moved
**2.7215x -> 28.8703x**, while `lo in [1.0,1.2)` and `hi in [2.7,3.1)` both
went false. Solved gates moved lo 1.1064 -> **0.7618**, hi 3.0111 -> **21.9934**.
The generalisable rule: *a claim of the form "X is large" must be asserted as a
one-sided bound, and the bound set from where the claim stops meaning anything,
never from the current measurement.*

**turn-3 F4 — `109MSDCF`'s solved gate is invariant to four decimals.
(MEASURED.)** 2.0963 pre-fix against 2.0964 post-fix, because ISO 160 sits
outside both `2a4f5c5` and `f95f6f4`. This is the in-run control that made the
ISO-50 movement a diagnosis rather than an assertion.

**turn-3 F5 — a unit test in `merge_cmd.rs` can never verify "the gate does not
transfer across stacks". (ARGUED.)** That is a claim about seven image stacks
and the test has no images. The irreducible residue is a snapshot; what is
controllable is whether recalibration makes the surviving assertions *more*
true or **quietly false**.

**turn-3 near-miss — the author reintroduced the defect being removed.
(MEASURED.)** The first one-sided floors were set at 5.0 and 2.0 **from M52's
current numbers**, which fail on pre-fix data — one-sided clothing on the same
defect. Caught by testing the candidate floors against *both* epochs, and
corrected to 2.4 and 1.5, which pass both.

---

## 5. Turn 4 — citation repairs and `fold_censored` (`2b4cff0`)

**turn-4 F1 — fact 714 independently confirmed from three sources. (MEASURED.)**
The corpus publishes ring-unregularised speckle (34.381 %), ring-**regularised**
(0.868 %) and Tenengrad-**unregularised** (1.010 %), and **no**
regularised-Tenengrad row. Sources: `M2-verification.md:150-154` and `:205`;
`M14-tenengrad-implemented.md:77-83` column headers; fact 71. Two code sites had
invented the fourth cell by mislabelling the second.

**turn-4 F2 — `fold_censored` is a bit-exact no-op end to end on a clean stack.
(MEASURED.)** Wired at `merge_cmd.rs:829`, signature checked at `merge.rs:496`
rather than assumed. `109MSDCF` (0 of 8241504 clipped) hashes
`DF6C3DE2…C815EE` before and after. Extended in `217b2ce` — see
`out/a5_censoring_endtoend.md`.

**turn-4 F3 — a refuted derived quantity does not implicate its inputs.
(DERIVED.)** `FINE_FOCUS_NOISE_SD = 0.090400` is **correct as consumed** — the
fine field is deliberately unregularised and `bimodality_sigma` divides by
`sqrt(2)*FINE_FOCUS_NOISE_SD`. Only its quotient with `FOCUS_NOISE_SD` and the
inference drawn from it were wrong. Fixing this by changing a constant would
have broken a correct consumer.

**turn-4 F4 — fact 500's second sentence was a causal claim with a confound.
(ARGUED.)** "The fine field is 5.94x noisier than the selection field, so its
argmax moves" attributes to noise a movement with **two** causes — a smaller
operator window **and** no regulariser. Substituting 1.815 would have left the
confound intact; the sentence needed rewriting, not a number swap.

---

## 6. Findings folded against a commit hash

- **fact 742** (`55b6b0d`) — `stack.rs`'s `Provenance::Profile` string told
  every user the gain was "not a photon-transfer measurement", which `2a4f5c5`
  had made false. Fixed against `profile.rs`'s doc comments at HEAD.
- **fact 744** (`4a5c270`) — `a2_kernel_sweep.py` used M41's stale ISO-50 gain
  with the confound disclosed only verbally in the report, not in the committed
  artifact. This is instance (b) of F10, found in the author's own work.
- **fact 750** (`9168b19`) — the stale fixture was **removed** rather than
  refreshed, because refreshing was not available without inventing data: M52
  publishes gate-2.0 values, not four-rung ladders.

---

## 7. Later work, not yet F-numbered

Delivered after the fold and cited by commit in this file rather than by
F-number, to avoid colliding with a numbering the orchestrator owns:

- **`217b2ce`** — `fold_censored` exercised where censoring fires:
  `coffee-bubbles` 184 changed px, `foam` 630, **823 rises, 0 falls**, all
  confined to the ever-clipped set. Also the DERIVED result that the *direction*
  is a theorem (`CONTAINER_MAX_DN = 2^14-1`), so a run finding no falls could
  not have found any.
- **`9e1674f`** — question 183. Facts 19 and 734 were never measured on the
  same ROI (`2272,1344,256,256` against `1356,32,512,512`). On M2's own ROI
  today's binary reproduces M2's denominator **exactly** (28.201 DN), legacy
  reads 1.068x where the high-pass reads **1.223x**, and the regularised merge
  crosses 1.0 like for like (1.075x -> 0.890x).
- **`c37a790`** — 494 MB and 527 MB are 60 B/px and 64 B/px of the same plane,
  not an allocator figure. See §8.
- **`4c02816`** — a circular polarizer is in the optical path for the whole
  corpus, so every clip statistic in `a5` is a **lower bound**.

  > **[Editorial note, added later — the quoted claim above is REFUTED.]** The
  > universal quantifier ("the whole corpus") was the orchestrator's
  > generalisation, circulated to five agents before it had been checked, and
  > `4c02816` repeated it in good faith. EXIF capture dates refute it: the
  > filter was fitted from **25 May** onward only. Of twelve stacks, **seven are
  > on-side** (`coffee-bubbles`, `foam`, `wrapped-text-1/2`, `bee-1/2/3`),
  > **four are bare-lens** (`109MSDCF` 17 May, `119MSDCF` 9 May, `112MSDCF` and
  > `113MSDCF` 7 May), and **one is unknown** (`coffee-bean`, 10 May — the
  > owner cannot recall it; unknown, not off). The commit text is left standing
  > because falsifying a quoted historical record is worse than a stale claim.
  > Corrected in `ceb9a99`; the date rule and a per-headline scoping table are
  > in `out/a5_censoring_endtoend.md`. **`109MSDCF`'s 0.0000% clip census and
  > bit-exact no-op are bare-lens and need no hedge at all** — the hedge above
  > made that control look weaker than it is. (Facts 877-880, discipline 409.)

---

## 8. The 494 / 527 MB help strings

Resolved in `c37a790`. **Both numbers are correct and they measure different
things; neither is stale, and it is not an allocator figure.** Verified against
what the code allocates:

```
merge_cmd.rs:393  stats_bytes = px * (FINE_FIELD_PER_PX + gathers * ThroughFocus::bytes_per_pixel())
FINE_FIELD_PER_PX = 4   (merge_cmd.rs:376)
bytes_per_pixel() = 2 + 4 + 12 + 4 + TOP_K*(4+2) + 4 + 2 + 8 = 60   (TOP_K = 4)

60 B/px * 8241504 = 494.5 MB  -- ThroughFocus ALONE, the struct's payload
64 B/px * 8241504 = 527.5 MB  -- what setting the flag COSTS
```

A real `--stats` run prints `of which stats: 527 MB/worker`, so the binary
agrees with the 64 B/px reading. The 6.7 % is the fine focus plane the flag
forces into every pass-two worker, not allocator overhead.

**Neither string was changed to match the other.** Each now names its quantity.
Two corrections to the brief that raised it:

1. **`MergeOptions` is not clap-derived** — it is a plain struct — so the
   `merge_cmd.rs` doc was never user-visible. `strehl merge --help` prints
   `main.rs`'s text and none of it.
2. **`main.rs` needed no repair and was not touched.** It already carried the
   correct 527 figure *and* the diagnosis. Only the internal copy was stale.

Also recorded: **527 MB is a floor, not a constant.** `gathers = 1 +
usize::from(opts.stats_placebo)`, so `--stats --stats-placebo` gives 124 B/px
≈ 1022 MB/worker. Not observed, derived from the allocation expression.

---

## 9. What this milestone did not verify

- **M41's arm E `144.391x` was never regenerated.** The kernel is reconciled
  through fact 469's *denominator* (11.770 DN, reproduced to 0.0038 %) plus a
  derivation, not by re-running M41's RIF arm.
- **M2's placebo A (0.981x) was not reproduced** — it needs a half-ROI shifted
  winner map and the retired `ring(1,3)` operator. It is the control that
  proved causation for fact 19.
- **Operator and window could not be separated** in question 183; `ring(1,3)`
  has no implementation left in the shipped crates.
- **The control plants white noise only.** A 9x9 box high-pass is blind to a
  very-low-frequency explosion. Documented, untested.
- **`generated_ladders()` shape coverage is argued, not measured.**
- **Three F-slots are unrecoverable** (§1), and no fact depends on them.

---

## 10. Exposure to M55b's contiguous-split null

M55b established that a **contiguous** half-stack split yields two half-merges
whose ring cross-power is statistically indistinguishable from two unrelated
images, on 6 of 6 real cells, detail ROIs as well as flat. Facts 641 and 702
were therefore read inside the null and fact 707's mechanism dissolves. This
section names which M53 quantities are exposed. Asked for as a list, answered
from the files rather than from memory.

**Nothing M53 measured rests on a half-stack split of any kind.** Checked by
searching every `.py`/`.rs`/`.log`/`.md` under `experiments/m53-flat-ratio/`
and both owned source files for `half-stack`, `halves`, `contiguous`, `parity`,
`cross-power`, `split-half`, `even/odd frames`. One hit, and it is a false
positive: `a2_kernel_sweep.py:79` says `(G1+G2)/2` "halves the variance",
which is **intra-frame Bayer green averaging**, not a stack split.
(`splitmix64` in `flat_ratio.rs` is a PRNG.)

| quantity | construction | exposed? |
|---|---|---|
| the shipped statistic `hp(merged)/median_i hp(F_i)` | one merged image against the per-frame distribution, **all** frames | **no** |
| negative control arms 1 and 2 | plant into merged output, compare statistics | **no** |
| a5 `fold_censored` before/after | two binaries, same full stack | **no** |
| q183 legacy-vs-HP on M2's ROI | merges over the full stack | **no** |
| kernel sweep `w = 3..15` | high-pass sd, single images | **no** |
| fact 441 spread (1.3575x) | per-frame sds, no pairing | **no** |
| speckle 34.381 / 0.868 / 1.010 % (fact 752) | `speckle_fraction(best_index, geom, tol)` at `merge_cmd.rs:1286` — **spatial** neighbour comparison on one winner map | **no** |

The statistic is structurally immune: it never forms a cross-quantity between
two subsets of frames, which is the object M55b showed to be null. Its
denominator is a **median over every frame**, which is the opposite of a split.

**Two where I am not certain, flagged rather than guessed:**

1. **`n_eff` = 3 on `foam`** (quoted from M52 at `a5_censoring_endtoend.md:89`,
   used only as context for why `foam` is the corpus's hardest stack). I read
   `n_eff` as an effective-sample-size over the merge weights, not a split
   statistic — `merge_cmd.rs:82` discusses it as a gate target — but **I did
   not verify M52's construction** and this is not my number. If it is
   weight-based it is unexposed; I am not asserting that.
2. **M2's placebo A (0.981x)**, named in `M53-flat-roi-statistic.md` as the one
   thing q183 could **not** reproduce. I recall it as a half-**ROI** shifted
   winner map — a *spatial* rearrangement, a different object from a half-
   *stack* split — but **I never reconstructed it**, which is exactly why it is
   listed there as an open hole. **If placebo A in fact split the stack, it is
   exposed and my inability to reproduce it becomes more interesting, not
   less.** Someone who can read M2's construction should check it.

No M53 conclusion changes if both turn out exposed: neither feeds the
statistic, the control, or any acceptance number. (MEASURED for the table,
ARGUED for the immunity claim, explicitly UNVERIFIED for the two flagged.)
