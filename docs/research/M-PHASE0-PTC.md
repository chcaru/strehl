# M-PHASE0-PTC — B1's go/no-go, answered from evidence the corpus already held

**Lane:** `experiments/M-PHASE0-PTC/`
**Scope:** the proposal's Phase 0 item *"M-PHASE0-PTC — B1 prototype on two stacks,
scored against M90's independent g."*
**Captures consumed:** none. **New decodes:** none. **Frames read:** none.

Every claim below is labelled **MEASURED**, **DERIVED** or **ARGUED**.

---

## 0. Headline

**B1 is not a build. It is a port, with a bar that cannot be met as written and one
output that must be struck.**

Three findings, each from the project's own prior measurements:

1. **B1's acceptance bar is unreachable** — it names a ±0.0642% precision figure as an
   accuracy target for a quantity whose two best independent measurements disagree by
   **1.33%**, and whose reference lane explicitly declines to narrow it beyond a
   **1.2 percentage-point** band. **(MEASURED)**
2. **B1's estimator already exists and has already been run in-stack** — M61-E1, on 12
   subject stacks and 1554 frames, ISO 50–1000, with a *passing* pre-registered control.
   The proposal cites M90 six times and **M61 zero times**. **(MEASURED)**
3. **B1's "read floor" output rests on a mechanism measured to fail, twice** — M90's
   PR-4d failed on flats; re-tested here on independent subject-frame data, **68.8% of
   the fitted intercepts are negative**, i.e. physically impossible. **(MEASURED)**

And one constructive result: with M61's own consistency gate applied, the per-stack
accuracy spread **collapses 5.9×**, giving a bar that *is* achievable. **(MEASURED)**

---

## 1. What was actually asked, and why it cannot be answered as asked

The proposal, §5 B1:

> **Acceptance:** recovers M90's independent `g` within its CI on the reference body,
> per-stack, from subject frames alone

M90's quoted value is `g = 0.221113 ± 0.000142 DN/e⁻` (§2.2). Taken as the bar, that
is **±0.0642%**.

**Fact 1 (MEASURED).** The same quantity, same body, measured by two careful methods:
M90 gives 0.221113, M71 gives 0.224103. They differ by **1.3342%** — **20.8× the bar**.

**Fact 2 (MEASURED).** M90 §8.2 records this as a *failed* pre-registered bar and
declines to resolve it:

> "The honest statement is: the true shipped-gain error is somewhere in −2.2% to −3.4%,
> and this milestone cannot narrow it further."

That stated band is **1.2 pp wide — 19× the CI the proposal cites as its bar.**

**Fact 3 (DERIVED).** The `± 0.000142` is a **precision** statement about one
regression's slope. B1 uses it as an **accuracy** statement about `g`. On this body
those differ by a factor of 19, and the reference lane says so in its own words. **No
estimator can pass B1's acceptance as written**, not because estimators are bad but
because the bar is narrower than the reference's own knowledge of the answer.

---

## 2. The estimator already exists

**Fact 4 (MEASURED).** B1 describes: *"take adjacent-frame pairs, remove the fitted gain
ratio, high-pass, and in low-gradient tiles regress the robust variance of the difference
against mean signal — a temporal PTC at the working exposure."*

That is **M61-E1**, specified in `docs/research/M61-ptc-high-iso-measured.md` §1 and run
in `experiments/m61-ptc-high-iso/`: temporal adjacent-frame difference, per CFA plane,
raw DN, never demosaiced, low-texture tile selection on an independence argument, on
**subject stacks** — 12 stacks, 1554 frames, ISO 50–1000. Its pre-registered ISO-160
control **passed** (`r = 0.9887` greens, band 0.80–1.20).

**Fact 5 (MEASURED).** The proposal contains **6** occurrences of "M90" and **0** of
"M61". B1 cites as precedent a *single-frame spatial* PTC ("F §2.3 … within 2%") and
misses the *temporal in-stack* lane that is its own design, already executed.

**Consequence (DERIVED).** B1's cost drops from "build and validate a runtime noise
estimator" to "port a validated estimator into the binary and generalise it to unknown
bodies". Its risk profile changes accordingly. **This does not diminish B1** — the
portability payoff (`Provenance::Measured`) is untouched. It changes what Phase 1 must
budget for it.

---

## 3. The per-stack reality

M61's ladder is on disk per stack and per plane
(`experiments/m61-ptc-high-iso/data/ptc-ladder.csv`, 48 rows), with split-half internal
replicates. That is precisely the evidence B1's acceptance asks for.

**Fact 6 (MEASURED).** Low-mode stacks, greens, against M90 scaled by the model's own
`g_model` column:

| stack | ISO | g greens | Δ vs M90 | CONSIST |
|---|---|---|---|---|
| `119MSDCF` | 50 | 0.226133 | +2.270% | pass |
| `coffee-bean` | 50 | 0.224188 | +1.391% | pass |
| `bee-1` | 100 | 0.222641 | **+0.691%** | pass |
| `bee-3` | 100 | 0.222805 | **+0.765%** | pass |
| `wrapped-text-1` | 100 | 0.204460 | −7.532% | **DROP** |
| `109MSDCF` | 160 | 0.362146 | +2.365% | pass |

**Inside B1's named CI: 0 of 6. Inside M90's own stated band: 5 of 6.**

**Fact 7 (MEASURED). The binding limit is systematic, not statistical.** Split-half
internal replicates of the *same* stack agree to a **median 0.224%**. Stack-to-stack
scatter is **9.896 pp**. External/internal = **44.3×**.

> **This is the operationally important number in the lane.** More frames of one subject
> cannot buy accuracy — the noise floor is already 44× below the scatter. B1 must average
> over **subjects**, or report a per-stack value with an honest systematic band. It cannot
> claim a tight CI from one stack. **(DERIVED)**

---

## 4. The read floor must be struck

**Fact 8 (MEASURED).** M90's PR-4d **FAILED**: the PTC intercept recovered a *known*
planted read floor **11.0% low** on synthetic data, and returned **−2.795 DN²** —
negative, physically impossible — on real flats. M90 concluded: *"no read-noise number
in this report is trustworthy, and I do not publish one."*

**Fact 9 (MEASURED). Re-tested here on independent data** (subject frames, different
lane, different scenes): `icptA < 0` in **33 of 48 rows = 68.8%**, range **−548.41 to
+42.44 DN²**. By plane: R 10/12, G1 8/12, G2 8/12, B 7/12.

**Fact 10 (MEASURED).** M61 already knew. It reports **only the slope**, and prints a
forced-zero-intercept variant `gA_zero_icpt` specifically as proof the answer does not
lean on the intercept.

**Consequence (DERIVED).** B1 lists "read floor" among its outputs and B5 leans on the
same intercept for black-level drift. **Both must be struck or re-sourced.** B1's own
text already notes the optically-black route does not exist on this sensor, so the
remaining candidate is B5's deep-shadow quantile route — which is *not* the intercept and
must be validated separately.

---

## 5. The bar that is achievable

M61 measured which fit-quality metric predicts slope error (`12-gate-metric.py`,
falsifying two of its own predictions on the way). The survivor is **CONSIST** =
`half_pct < 5%` AND `ac_pct < 10%` — a *consistency* gate, which asks whether a stack
reproduces itself and **never looks at the answer**. That is what makes it legal here.

> **A correction to my own instinct, recorded because it nearly cost the result.** I was
> going to gate on fit residual. M61 measured that this is *wrong*: the known-accurate
> control (18.2% residual) and `119MSDCF` (44.7%) score badly on residual while being
> clean on every other metric. Reading the prior lane's **errors** section, not just its
> results, is what caught it.

**Fact 11 (MEASURED).** CONSIST as implemented here drops **exactly**
`{coffee-bubbles, wrapped-text-1}` and retains the other ten — reproducing M61 fact 33 —
under **both** candidate aggregations independently.

**Fact 12 (MEASURED).** Applying it:

| | n | spread | width |
|---|---|---|---|
| ungated | 6 | −7.532% … +2.365% | 9.896 pp |
| **CONSIST** | 5 | **+0.691% … +2.365%** | **1.674 pp** |

**Collapse factor 5.9×.** The external scatter was dominated by badly-conditioned fits,
not by a real per-scene gain difference.

### Proposed replacement acceptance for B1

> On CONSIST-passing stacks (`half_pct < 5%` AND `ac_pct < 10%`), the in-stack `g` agrees
> with M90's independent value to within **±3%**, per stack, from subject frames alone.
> Stacks failing CONSIST are reported as **UNMEASURED** rather than given a value.

±3% sits inside M90's own 2.2–3.4% band of ignorance, so the bar does not demand more
accuracy than the reference possesses — which is exactly the defect in the stated bar.
The **UNMEASURED** clause matters as much as the number: `wrapped-text-1` is −7.5% off,
and a runtime estimator that silently returns that value would widen gates on a lie.

---

## 6. An observation I did not predict, labelled as such

After gating, all five surviving stacks sit on the **same side** of M90. Scatter
straddles; a one-sided result is an offset. Nothing registered in this lane predicted it,
and I saw it only after §5 printed. **It carries no pass/fail.**

Because comparing an ISO 50 or 160 stack to M90's ISO-100 value requires the model's ISO
scaling to be right, the observation is split and **both arms are reported**:

| arm | what it assumes | mean g | vs M90 | vs M71 |
|---|---|---|---|---|
| **A — ISO 100 only** | **nothing** | 0.222723 | **+0.728%** | −0.616% |
| B — all low-mode | the model's ISO scaling | 0.224422 | +1.496% | +0.142% |

**The arms differ by 0.768 pp, and ARM A is the one that means anything.** ARM B's extra
offset is carried by the ISO 50 and ISO 160 stacks — that is, by the *scaling*, not by the
gain measurement. Had only ARM B been run, this lane would have reported a +1.5% offset
that is half an artefact.

**Fact 13 (MEASURED).** ARM A: `bee-1` and `bee-3` agree with each other to **0.074 pp**
and land **54% of the way** from M90 to M71. The in-stack method therefore has the
*precision* to resolve the 1.33% tie — but **two stacks is not a measurement of a
systematic, and the tie is not broken.**

**The test that would settle it, registered now so it stays falsifiable:** run the
in-stack temporal PTC on every ISO-100 subject stack passing CONSIST, n ≥ 6, and ask
whether the mean offset from M90 exceeds its own stack-to-stack standard error.
**Direction registered in advance: positive — in-stack reads above M90, toward M71.**
Nothing in this lane rests on it.

---

## 7. My own errors, disclosed

**Error 1 — the baseline, not the measurement.** Step 2's first run scaled M90 linearly
in ISO and reported the ISO-50 stacks at **+104.5%** and **+102.8%**. M61's own rule is
`g_model = max(ISO,100)/436.8` — the `max` clamps below ISO 100, and the CSV confirms it:
the ISO 50 rows carry `g_model = 0.2289377`, *identical* to ISO 100. ISO 50 on this body
is a pull ISO, not a lower sensor gain.

The signature was unmissable: the measured ISO-50 values (0.2261, 0.2242) sit right beside
the ISO-100 values (0.2226, 0.2228), exactly as a clamp predicts. **The measured column
was fine; the baseline was mine and it was wrong.** This is the third time this session
that magnitudes were sound and a *baseline or sign* was not. The fix is structural, not
arithmetic: the scaling is now **read from the same file the data came from** (control
C6), so it cannot disagree with the model that produced the data.

**Error 2 — my pre-registration is author-attested, not commit-attested.** Each script's
predictions were written into its docstring before that script was run, but the scripts
were **not committed before running**, unlike M61's practice. The reader should weight
them accordingly.

**Scope limit — what this lane did *not* verify.** I verified my *transcription* of M90
and M61 (controls C1–C7, all passing, several reproducing published aggregates to four
decimals). I did **not** re-derive M90's or M61's underlying measurements from frames.
The findings here are about the *relationships between published numbers* and are only as
good as those numbers.

---

## 8. What this changes in the proposal

| item | change | basis |
|---|---|---|
| **B1 acceptance** | replace the CI bar with the ±3% CONSIST-gated bar of §5 | facts 1–3, 11–12 |
| **B1 outputs** | **strike "read floor"** | facts 8–10 |
| **B1 cost** | reclassify from *build* to *port + generalise* | facts 4–5 |
| **B1 method** | require averaging over **subjects**, not frames | fact 7 |
| **B5** | its black-level-drift intercept inherits fact 9; re-source or validate separately | facts 8–10 |
| Phase 0 | **this lane is complete.** No captures were needed and none were used. | — |

**Not changed:** B1's portability payoff, its two-piece ship rule, or its place in the
sequencing. The physics is sound; the bar and one output were not.

---

## 9. Reproducing this

```
python experiments/M-PHASE0-PTC/src/b1_audit.py       # §1-2   -> out/b1-audit.{txt,json}
python experiments/M-PHASE0-PTC/src/b1_perstack.py    # §3-4   -> out/b1-perstack.{txt,json}
python experiments/M-PHASE0-PTC/src/b1_bar.py         # §5     -> out/b1-bar.{txt,json}
python experiments/M-PHASE0-PTC/src/b1_tie.py         # §6     -> out/b1-tie.{txt,json}
```

Each script carries its registered questions, directions and controls in its docstring,
and refuses to make its claims if its controls fail. Inputs are quotations with citations
attached to the value; every derived figure is computed, never retyped.
