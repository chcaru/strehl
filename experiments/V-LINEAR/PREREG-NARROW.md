# PRE-REGISTRATION — the 0.30–0.35 cyc/px qualification

**Written and committed BEFORE any 0.30–0.35 number exists.** Authorised by ORCH
correction #5. The purpose of committing this first is that there is a
convenient answer available in *both* directions here, and I have already
publicly taken one side.

## The question

ORCH's `-44.6%` (harmful at depth, `112MSDCF` 39→79) and `27.2%`
(`coffee-bubbles` 9→19) are measured at **0.30–0.35 cyc/px**. This lane's finest
committed slice is **0.30–0.40**, which FAILs qualification on `112MSDCF`
(R = 1.089) and has never been measured at all on `coffee-bubbles`. A FAIL on
the wider slice withdrew the licence; it did not prove the narrower slice is
noise. This measurement settles that.

## Instrument change, and why it cannot disturb the committed table

`bandsignal.py` is frozen and is not touched. Two bands are added **in
`bandsweep.py`** as a new `EXTRA` list:

```
EXTRA = [(0.30, 0.35), (0.35, 0.40)]
allb  = BANDS + FINE + EXTRA + [(SEL_LO, SEL_HI)]
```

`EXTRA` is deliberately **not** part of `FINE`, so `_fine_partition()` and
`boundary()` are unchanged and every one of the 241 committed checks in
`V-LINEAR-BANDS.md` stays valid.

`EXTRA` is appended **after** `FINE` and **before** the selection band for a
specific reason: `ratio_ci` draws from a module-level RNG
(`bandsignal.py:69`), so each call consumes randomness and shifts every
subsequent call. Inserting the new bands mid-list would change the CIs of every
band after them. Appending leaves all existing bands at their existing
positions in the RNG stream.

**COMMISSIONING REQUIREMENT, fixed in advance:** re-sweeping a subject whose
develops are already on disk must reproduce all 12 existing bands
**digit-exactly** (R, lo, hi to 4 dp). If any existing band moves, the
instrument change is contaminating the committed result and the measurement is
abandoned until it does not.

## Subjects, and why each

| subject | why | develops |
| --- | --- | --- |
| `112MSDCF` | carries the `-44.6%`. The reason this measurement exists. | must develop, 79 frames |
| `coffee-bubbles` | carries the `27.2%` and has **never** been band-qualified | must develop, 19 frames |
| `dry-erase-marker-head-cpl` | **positive control** — 0.30–0.40 PASSes at R = 4.877 | on disk |
| `paper-sweep` | second positive control — PASSes at R = 2.002, the weakest passer | on disk |
| `lavendar-cpl` | the discriminating middle — 0.30–0.40 is MARGINAL at 1.490 | on disk |

## Pre-registered readings

Rule unchanged and frozen: PASS = `R >= 2.0` **and** CI low `>= 1.5`;
MARGINAL = `1.3 <= R < 2.0`; FAIL = `R < 1.3`.

**Reading 1 — instrument valid, ORCH's band is noise.**
0.30–0.35 PASSes on `dry-erase-marker-head-cpl` **and** FAILs on `112MSDCF`.
Then the narrow band can qualify a subject, and it does not qualify ORCH's.
The licence stays withdrawn and the `-44.6%` is a measurement in a noise band.

**Reading 2 — ORCH's number is licensed and I was wrong to doubt it.**
0.30–0.35 PASSes on `112MSDCF`. Then the wider slice's FAIL was a dilution
effect of averaging 0.30–0.35 with an empty 0.35–0.40, the `-44.6%` is measured
in real signal, and my withdrawal was unnecessary.
**If this happens it is reported first, in the first sentence, without
softening, and the correction is mine.** This is the outcome that costs me
something and it is the one I am most likely to under-report.

**Reading 3 — the instrument is uninformative at this width. THE TRAP.**
0.30–0.35 FAILs on the positive controls as well. Then a narrow band cannot
qualify anything on any subject and a FAIL on `112MSDCF` carries no
information. The answer is **"cannot be determined"**, NOT confirmation.
This reading superficially resembles Reading 1 — both show `112MSDCF` failing —
and it is the one I must not mistake for a win. The positive control is what
separates them, which is why it is measured in the same run and not assumed.

**Reading 4 — `coffee-bubbles` is shallow and that is a confound.**
The stack is **19 frames**. `sweep()` sets `far_real = max(20, n/6) = 20`, which
19 frames cannot supply, so the guard `n - 2*far < 6` reduces `far` to about 6.
The defocused reference is then only ~6 frames from focus, which makes the
denominator of `R` *less* defocused and biases `R` **downward**. Therefore:
a FAIL on `coffee-bubbles` is **INDETERMINATE**, not noise, unless a subject
measured at a comparably small `far` still passes. The realised `far` is
reported for every subject.

## What is measured alongside, and why

**0.35–0.40 is measured as well.** Together with 0.30–0.35 it partitions the
committed 0.30–0.40 slice, so the three are checkable against each other. If
0.30–0.35 and 0.35–0.40 both FAIL while their union also FAILs, the picture is
coherent. If 0.30–0.35 PASSes while the union FAILs, the union's FAIL was
dilution and Reading 2 applies. Measuring only the band ORCH's number sits in
would leave no way to tell those apart.

## Declared limits, before the numbers

- A narrower band has fewer Fourier coefficients and therefore a noisier ratio
  and wider CI, so it is **intrinsically harder to PASS**. This biases the
  result toward FAIL, which is toward my own prior position. The positive
  control is the guard against reading that bias as a finding.
- `coffee-bubbles` at N=19 additionally cannot be swept at the `far` used for
  every other subject, so it is not strictly comparable to them.
- This measures the **source frames**, not any merge. It says whether the band
  carries signal on that subject; it says nothing about whether the confidence
  exponent helps or harms there.

---

## Addendum: `bee-1-cpl` at 0.30–0.35 (registered before the sweep finished)

ORCH's item 3. He has told the pyramid lane to score the confidence-dependent
exponent at depth on `bee-1-cpl`, on the strength of its **0.30–0.40 R=4.732
PASS**. That instruction is only sound if the subject qualifies at the slice
that lane will actually use. His words: *"If that one fails, I have misdirected
them and I need to know tonight."*

The develop for this subject was purged in the disk emergency and has been
re-made at the pin. It is **not assumed** equivalent to the purged one:

> **Acceptance condition for the re-develop.** All 12 pre-existing bands must
> reproduce the committed record **exactly**. If any moves, the re-develop is
> not the subject the committed table describes, and no narrow-band number from
> it may be compared with the other four subjects. Report that instead.

This single check tests the re-develop and the RNG-append property together.

### What each outcome means, decided now

- **PASS (R ≥ 2.0).** The direction is licensed at the exact slice. Report the
  value and say plainly that ORCH's item-3 instruction stands.
- **MARGINAL (1.5 ≤ R < 2.0).** The wide-band PASS does **not** narrow cleanly.
  The instruction is partially misdirected and must be reported as such, not
  rounded up to "qualified" because 4.732 was comfortable.
- **FAIL (R < 1.5).** ORCH has misdirected the pyramid lane and must be told
  tonight, unhedged.

### The discriminator, if it FAILs

A drop from 4.732 to below 1.5 would be far larger than anything seen so far,
so a FAIL would raise a second question: is it the subject, or does the narrow
band collapse on **deep** stacks generally? That is already answerable without
new work. `dry-erase-marker-head-cpl` is the same depth (N=300) and is already
measured at **0.30–0.35 R=4.530 PASS**, narrowing only −7.1% from its wide
band. So:

- both deep subjects narrow cleanly → a bee FAIL is **subject-specific**;
- only `dry-erase` narrows cleanly → still subject-specific, but the pyramid
  lane should be redirected to `dry-erase`, which is measured and qualified.

There is no outcome in which a bee FAIL licenses the exponent work to continue
on bee. Recording that now so it cannot be reasoned around afterwards.

### Expected value, stated so that agreement is not read as confirmation

`dry-erase` (N=300, wide 4.877) narrowed −7.1%. If `bee-1-cpl` behaves the
same, its narrow value lands near **4.4 and PASSes**. A PASS is therefore the
*expected* result and is weak evidence about anything; it confirms the
instruction and nothing more. The informative outcomes are the other two.
