# M77 addendum B — pre-registration: the M70 cross-check, and a null that can void it

**Written and committed before any number in this addendum existed.** The
original pre-registration (`PREREGISTRATION.md`, committed `00a1900`) is not
edited; this is a second, separately-scoped registration for work that did not
exist when it was written.

---

## B.1 Why there is an addendum

M70 (`docs/research/M70-through-focus-spectrum.md` §21, folded at `6779857`)
measured a **gate-free** count of how many frames carry mid-band signal on two
real stacks, and reported it against M73's measured admission at the shipped
gate. Its §21.3 table gives spectral `n_eff` = **4.148** (`wrapped-text-1`,
K=130) and **4.050** (`wrapped-text-2`, K=120) against admitted **1.238** and
**1.766**.

That is an **independent, gate-free reference point for the same question M77
was chartered on**, obtained by an instrument that shares no constant with mine.
M77 §6 ruled INDETERMINATE on a control failure and §10 said the milestone could
not choose an operating gate. **M70 supplies a candidate operating point from
outside.** This addendum asks one question:

> **Does the spatial variance/bias tradeoff, measured on the shipped CLI, place
> M70's spectrally-implied operating point inside or outside the region where
> opening the gate is free?**

I am not predicting which. **A disagreement between the two instruments is a
finding, not a failure**, and so is an agreement.

## B.2 What is blind and what is not — declared before running

**`wrapped-text-1` is NOT blind.** Its full ladder is published in
`M77-gate-sweep.md` §6 and committed at `93b785c`, and I had read it before M70's
number reached me. Any agreement on that stack is worth less than it looks.

**`wrapped-text-2` IS blind.** M77 has never run it; it is not in
`m77.STACKS`; no ROI has been chosen on it and no gate ladder computed. It is a
sibling subject of the same class, measured by both M70 and M73 for their own
reasons. **It is the arm that can actually surprise me, and it is registered
here before its ROIs exist.**

## B.3 Arms

| arm | what it is | stacks |
| --- | --- | --- |
| **B0** | ROI selection by the §4 rule, unchanged, on the new stack | `wrapped-text-2` |
| **B1** | gate ladder, detail ROI = the detail ROI (the real measurement) | both |
| **B2** | **null:** gate ladder, detail ROI = **the flat ROI** | both |

**B2 is the null run M70's discipline demands** — *"register a null run alongside
each criterion so you can tell an absent effect from a blind instrument."* Its
mechanism: INVARIANT 2's headline is
`corrected_rms = sqrt(max(0, raw_rms² − noise_rms²))` (`merge_cmd.rs:280–305`),
where `noise_rms` is the **calibrated model's** prediction and the merged image's
σ *"already carries the 1/sqrt(n) from averaging"* (`merge_cmd.rs:302`). **Any
noise the model does not predict is not subtracted, and what is not subtracted
is averaged away as the gate opens.** On a structureless patch there is no
detail to lose, so a fall in the retention ratio there is instrument, not
subject. B2 measures the size of that term on the same stacks, at the same
rungs, through the same binary.

**B2 is conservative by construction and I say so in advance:** M77 §4 recorded
that no genuinely flat ROI exists on 3 of 5 stacks, so the flat patch carries
some real structure and B2 will attribute some genuine detail loss to the
instrument. That biases B2 toward declaring criterion X1 unreadable, i.e.
**against my being able to report a cross-check verdict at all.**

## B.4 Ladder

`--gate 0 2 4 8 16 24 32 40 48 64 96 128` — twelve rungs in one pass, denser
than §5's eight in the decade where `n_eff` passes through M70's value on the
published `wrapped-text-1` ladder. `merge_cmd.rs:609–618` places no cap on the
count. Everything else — binary, ROI rule, statistics — is §3–§5 unchanged.

## B.5 The observables

Per stack, per rung `T`, read from the shipped CLI's own stderr tables:

* `n_eff(T)` — `merge_cmd.rs:966`
* `HP_RATIO(T)` — INVARIANT 1, `merge_cmd.rs:1007`
* `RET(T)` — INVARIANT 2 retention, `merge_cmd.rs:1189`, detail ROI = detail (B1)
* `RET_null(T)` — the same, detail ROI = flat (B2)

Derived, §7's definitions unchanged:

* `dN_ben(T) = HP_RATIO(4.0) / HP_RATIO(T)`  (>1 = quieter than shipped)
* `dD(T) = RET(T) / RET(4.0)`  and  `dD_null(T) = RET_null(T) / RET_null(4.0)`

New:

* `T*` — the gate at which `n_eff(T)` equals M70's spectral `n_eff` for that
  stack, by log–log interpolation between the two bracketing rungs.
* `[T_lo, T_hi]` — the gates at `0.5×` and `2.0×` that value. **M70 §21.5 states
  its count and M73's are not the same quantity and must be read as
  order-of-magnitude**; a factor-2 band is my declared reading of that caveat,
  fixed here, before I know where it lands.

## B.6 Criteria, bars, and consequences

**X1 — the cross-check.** `dD(T*) > 0.98`.
*MET* → the spectrally-implied operating point is inside the region where
opening the gate costs no material detail; the two instruments agree that the
signal M70 counts is affordable to take.
*NOT MET* → they disagree, and the disagreement is the reported result: the
frequency side counts signal the spatial side says costs resolved detail to
harvest.
**Consequence either way: reported as a two-instrument comparison, not as a
ruling on the gate.** M77 §6's INDETERMINATE stands; this addendum does not
reopen it, because the control that produced it (K3) is not re-run here.

**X2 — blind replication.** On `wrapped-text-2`, unseen: does any rung with
`T > 4` satisfy `dN_ben ≥ 1.10` **and** `dD > 0.98`?
*MET* → the "free rung above the shipped gate" result replicates on a stack
chosen by other milestones, on ROIs I had not seen.
*NOT MET* → it does not replicate, and §6's `wrapped-text-1` free rung is a
single-stack result within its subject class.

**X3 — the null, which gates X1.** `contam_D(T*) = |1 − dD_null(T*)| / |1 − dD(T*)|`.
* `contam_D(T*) ≥ 0.5` → **X1 is UNREADABLE** on that stack. I report the number
  and **decline to rule X1 MET or NOT MET there.** The instrument cannot
  separate detail loss from residual-noise averaging at that rung.
* `dD_null(T*)` degenerate (`RET_null(4.0) ≤ 0`, i.e. the corrected residual
  clamps to zero) → **X3 itself is unreadable**, X1 is reported UNGATED and
  labelled as such rather than silently trusted.

**X4 — the σ limb (M71), priced not assumed.** M71 §8.3 measures the shipped
noise model as **over-confident above S ≈ 504 DN per photosite**, reaching
**−12.75%** at S = 8000. `noise_rms` in X1's statistic is built from that model.
Recompute `corrected_rms` at every rung with `noise_rms` scaled by
`1/(1 + e(S̄))` where `e` is M71's measured error at the detail ROI's own mean
signal level, and ask: **does `dD(T*)` cross the 0.98 bar under the correction?**
*Crosses* → X1's verdict is σ-model-dependent and must be reported as
conditional on a constant another milestone has shown to be wrong.
*Does not cross* → X1 is robust to the known σ error, and I say by what margin.
This is arithmetic on numbers the CLI already prints; if it turns out to need a
new capture or a `crates/` change, **I will report it as not-free and stop**,
per the orchestrator's instruction.

## B.7 What would make me conclude the comparison is mine, not real

Registered in advance, in the form M70's §19.3 hazard demands:

1. **X3 fires on both stacks** → the disagreement (or agreement) is my
   instrument's residual-noise term, not the subject's. I report UNREADABLE and
   nothing else.
2. **`dD_null` and `dD` track each other rung-for-rung** (Pearson `r > 0.95`
   over the twelve rungs, on both stacks) → the detail statistic is not
   responding to detail at all. Reported whatever X1 says.
3. **X2 NOT MET while X1 MET on `wrapped-text-2`** → the two bars contradict on
   one stack; I report the contradiction rather than choosing.

## B.8 Hazards taken from M70, and how this design answers them

* **No half-wave rectification anywhere.** Nothing in B1/B2 clips a per-frame
  value before summing across frames. The only clamp in the chain is
  `max(0, raw² − noise²)` **inside** a single already-merged image, which is not
  a sum across frames. M70 P5's `0.4K/√(2 ln K)` inflation is unavailable here,
  and X3's degeneracy branch is exactly the case where that clamp bites.
* **A moving null.** X3 is the registered defence: it is measured at every rung,
  not assumed flat.
* **`n_eff` granularity mismatch.** Declared in B.5 via `[T_lo, T_hi]`, from
  M70's own §21.5 caveat, not discovered afterwards.

## B.9 The circularity, restated for this addendum

M77 §10 stands unchanged: the gate is denominated in `FOCUS_NOISE_SD` and every
rung on my ladder is a multiple of it, so **`T*` is a number in units M69 showed
to be texture-dependent by 4.06×.** What this addendum adds is that **M70's
spectral `n_eff` is not** — it is a count of frames carrying band-limited signal
and touches no gate constant. **The cross-check is therefore between one
circular instrument and one that is not**, which is the only reason it is worth
running; and it means a disagreement is attributable to my side at least as
readily as to M70's. Said here, before the result.

## B.10 Scope

`wrapped-text-1` and `wrapped-text-2` only. No spectra, no transform — M70 owns
the frequency domain and this addendum reads its published numbers rather than
recomputing them. **No change to anything under `crates/`.** No edit to
`SYNTHESIS.md`, `AGENTS.md`, `OWNER-QUESTIONS.md`, `docs/captures-needed.md`, or
another milestone's report.
