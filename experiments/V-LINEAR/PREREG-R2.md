# V-LINEAR round 2 — pre-registration

**Status: written and committed BEFORE any round-2 subject was swept.**
The point of this file is that the reading rules for the five new subjects were
fixed while their numbers were still unknown, so a verdict cannot have been
chosen to suit a result. Round 1 (`docs/research/V-LINEAR-BANDS.md`) is already
committed; this file only adds what is specific to round 2.

## Subjects, and why these five

Assigned by ORCH in priority order. They are not a random sample and the table
must not be read as one:

| # | subject | frames | stride | why it is on the list |
|---|---|---:|---:|---|
| 1 | `112MSDCF` | 79 | 1 | ORCH's band-0 gate-floor arm (32.1% → 80.9%) was measured on this subject and it is absent from round 1, so a **shipping default currently rests on an unqualified band**. |
| 2 | `flat-on-ruler-cpl` | 79 | 1 | fails the halo measurement, fact 1841 — overshoot **+4481.8 DN**, estimator-scale halo surviving the pyramid default |
| 3 | `tweezers-cpl` | 100 | 1 | fails the halo measurement — bump **1542.3** |
| 4 | `lavendar-cpl` | 299 | 4 | marginal on the halo measurement |
| 5 | `dry-erase-marker-head-cpl` | 299 | 4 | marginal on the halo measurement |

2–5 are the four subjects V-SPEED must score its halo fix on, and it needs a
qualified band to do that without repeating the error that produced correction
#4.

**All five will be reported.** If one produces an awkward or inconvenient
result it still appears in the table; the round-1 section already carries a
`flower-bud-alone-cpl` that qualifies nowhere, and that row is the most useful
one in it.

## The rule — unchanged from round 1, restated so it cannot drift

From `experiments/V-LINEAR2/PREREGISTRATION.md:51-52`, committed before
`bandsignal.py` first ran:

- **PASS** — `R >= 2.0` **and** CI low `>= 1.5`
- **MARGINAL** — `1.3 <= R < 2.0`
- **FAIL** — otherwise

`R` is the ratio of in-focus to defocused band power over the CONFIRMED tile
population. **Boundary** is the top edge of the highest-frequency PASSing band
of the `FINE` partition at or above 0.10 cyc/px, and is read off `FINE` only —
never off `BANDS`, whose wide `0.10-0.20` member can certify its own top edge
using content an octave below it (`bandsweep.boundary`, commissioned 5/5 in
`commission_boundary.py`).

## What is licensed out of this and what is not

Carried forward from round 1 unchanged, because nothing about adding subjects
weakens it:

- **Licensed:** per-band verdicts, and the per-subject boundary.
- **NOT licensed:** cross-subject comparison of R *magnitudes*. R depends on how
  defocused the `far` frames happen to be, which is a property of the stack, not
  of the subject's detail. `bee-1-cpl` moves 4.36x across the `far` ladder.
  Never write "subject A has 3x the fine structure of subject B" from this table.

## Controls that must run, and what each would show

1. **`far` ladder.** Every subject swept at `--far 20` and `--far 8`. Round 1
   found all five boundaries identical across `far` = 8 / 20 / auto. If a
   round-2 boundary MOVES with `far`, that subject's boundary is a property of
   the defocus offset rather than of the subject, and it must be reported as
   indeterminate rather than as a number.
2. **Decimation, for subjects 4 and 5 only.** Commissioned before use:
   `--simdecim 2` on `leaf-2-cpl` reproduced the full 182-develop run
   **digit-exactly on 12/12 bands** (R and CI low identical to 4 dp), with
   `n_real`=182, `step`=2, `kept`=30. Subjects 1–3 are undecimated.
3. **Develop-path invariance.** Round-1 develops were written by an older
   binary and the working tree is currently dirty, so comparability was
   measured, not assumed — see `r2_develop.ps1`'s header. Three binaries,
   bit-identical arrays.

## Pre-registered readings — fixed now, before the numbers

**Subject 1, `112MSDCF`, is the one with a decision attached.** ORCH's arm is
scored in band 0, which his corrected `contrast_ms.py` places at
**0.25-0.50 cyc/px**. So:

- If `0.25-0.30` **PASSes** on `112MSDCF` → band 0 carries signal on this
  subject, ORCH's gate-floor arm is qualified, and his result stands on this
  axis. This is the outcome that favours the orchestrator's existing claim.
- If `0.25-0.30` is **MARGINAL or FAIL** → the arm was scored in a band that is
  noise-dominated on its own subject, and the 32.1% → 80.9% number is
  **unqualified**: not refuted, but carrying no licence to move a shipping
  default. V-KILLB0 and V-BANDFLOOR have already been told to treat it as
  unqualified pending this measurement.

I have no stake in either. **The failure mode to guard against here is the
convenient one**: this lane has already had one result (the Zerene comparison)
where the outcome that flattered the project would have been wrong, and the
value of the answer is entirely in it being reported whichever way it falls.

**Subjects 2-5.** No pre-registered expectation, because nothing depends on a
particular answer — V-SPEED needs whichever band is qualified, not a specific
one. The one thing fixed in advance: if **no** band at or above 0.10 cyc/px
PASSes on a subject, that subject is flagged **NO QUALIFIED BAND**, and no
sharpness claim of any kind — halo, acuity, gate floor — may be scored on it by
any lane. Round 1 produced one such subject already
(`flower-bud-alone-cpl`, boundary 0.17 with nothing above it).

## What this round cannot settle

The round-1 caveat is carried forward verbatim, because five more subjects do
not repair it:

> Sufficient to refute "0.25 holds corpus-wide" — needs one counterexample, has
> four; insufficient to state the corpus range.

Ten subjects is still not the corpus, the five here were chosen for what depends
on them rather than at random, and the four causal candidates rejected in round
1 (stack depth, `far`, fine-structure content, and each term of `R` separately)
stay rejected — nothing in round 2 is designed to revive them. A lane still
cannot infer a band from a subject; it must run the test.
