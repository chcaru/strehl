# M92b — the blast radius of the ISO defect

Follow-on to [`M92-null-averaging.md`](M92-null-averaging.md). Phase 1 found that
three M57 scripts set `ISO = 500` as a module constant and applied it to an
ISO-160 stack, inflating injected noise by 1.7587× and manufacturing the
0.34310 px bound that two milestones carried as the reason this project could
not measure sharpness. Fact 1242 left a liability in the corpus: *"any future
use of M57's S5/S6/S7 numbers on `109MSDCF` or `foam` inherits this."*

This milestone discharges that sentence. It asks three questions: who consumes
the contaminated numbers, where else the same *class* of defect lives, and
what can be built so that it cannot be written again.

**Placement note for the orchestrator:** this is a separate document rather
than a section of the phase-1 report, because it is a different question with
its own controls and its own verdict. Nothing in `M92-null-averaging.md` was
edited.

---

## §0 — Verdict

**SHIP** — on the mechanical fix. **The liability is bounded, and it is
smaller than fact 1242's wording implies.**

The evidence that decides it:

- MEASURED (S10, S12; `out/s10_const_scan.json`, `out/s12_use_sites.json`):
  the experiment tree contains **254 sensor-constant assignments across 165
  files**. Of these, **31** disagree with the EXIF of a stack the file opens.
  Of those 31, **exactly 3 reach a sensor model over real pixels** — and all
  three are the already-known M57 S5/S6/S7 instances. **20 of 31 reach the
  frozen detail operator**, where rule 15 makes disagreement with EXIF correct
  behaviour rather than a defect, and **4 define synthetic plants**, where
  there is no truth to disagree with.
- MEASURED (S10 + S12): **one previously unrecorded instance of the class**
  outside M57 — `m41-r3-kill/src/a11_metric_power.py:66` applies M25's
  refuted ISO-50 gain to real `119MSDCF` planes, understating injected noise
  by **1.4199×**.
- MEASURED (S14, `out/s14_guard_control.json`): a guard that makes the class
  impossible passes **10 of 10** control cases, including **two planted
  defects on the live tree that it caught** and **two planted non-defects it
  correctly ignored**.
- MEASURED (S15, `out/s15_pricing.json`): of the numbers that move, **none
  changes a conclusion** except the three already retracted in phase 1. Every
  other contaminated figure is a footnote, and §6 gives the arithmetic for
  each rather than asserting it.

**What is NOT established:** whether the absolute recovery ratios in fact 477
move under the m41 correction. I derived that fact 478's `(1 - rho)` law is
invariant and did not re-run m41 to test 477. That is stated as an open
question in §10, not smoothed over.

---

## §1 — What was scanned, and how

MEASURED (S9, `out/s9_iso_truth.json`): EXIF ISO for **34 stacks** — 23 under
`D:\personal\macro`, 11 under `D:\macro-dark-frames` — read from **every
frame**, not the first. No stack has mixed ISO. Both roots were opened
read-only.

MEASURED (S10): an AST walk over every `.py` under `experiments/`, extracting
assignments of `ISO`, `G`, `GAIN`, `GAIN_DN_PER_E`, `g_dn`, `RN_E`, `RN`,
`READ_NOISE_E`, `rn_e`, `BLACK`, `BLACK_LEVEL`, `WHITE`, `WHITE_LEVEL` to
literal-foldable expressions, then matching each file against the stack names
that appear in its **string literals excluding docstrings**.

MEASURED (S12): for each disagreement, an AST walk for the call sites the
constant flows into, classifying the *role* it plays:

| role | reaches | does EXIF apply? |
| --- | --- | --- |
| `SENSOR` | `gain_dn_per_e`, `read_noise_e`, `noise_var_dn`, or longhand `g*S + (rn*g)^2` over real pixels | **yes** — the constant claims to describe the sensor |
| `OPERATOR` | `focus_fields(cube, g, rn_e)` | **no** — rule 15 freezes the operator's constants so results compare across milestones |
| `PLANT` | `add_sensor_noise` over a synthetic image | **no** — the constant *defines* the plant |

**This distinction is the whole audit.** Without it the answer is "31
defects", which is wrong and would have sent someone to change 20 frozen
operator constants and silently break every cross-milestone comparison in the
corpus.

MEASURED: **193 further instances were excluded** because
`experiments/M62-sqrt-n/build-head/` vendors a whole copy of the repository;
its hits duplicate the originals verbatim.

---

## §2 — Two defects in my own scanner, found by making it fail

Reported here rather than quietly fixed, because both are instructive and
both would have produced a wrong audit.

MEASURED: **the first revision reported 0 instances across the whole tree.**
`m92lib.ROOT` is the *capture* root `D:\personal\macro`, not the repository
root, so `os.walk` traversed a path that does not exist. A scan that returns
zero findings on a tree known to contain three is indistinguishable from a
clean tree, and nothing in the output said so.

MEASURED: **the second revision missed tuple unpacking.** M57's
`s7_bias_or_variance.py:44` reads:

```python
PAD, G, RN_E, ISO = 32, 1.14469, 1.47, 500
```

An AST scan that only handles single-target `Name = value` reports **no hit**
here — it silently under-counts the very defect the audit exists to find.
Fixing this took the tree-wide count from 121 instances to 254.

MEASURED: **the second revision also over-reported**, counting stack names
that appear inside *docstrings*. `m61-ptc-high-iso/src/03-power-control.py` is
a pure synthetic plant whose module docstring names `foam` while describing
the regime it emulates; the scanner called it a MISMATCH.

Both shapes are now fixtures F3 and F4 in S11, which the pre-fix scanner
demonstrably fails and the post-fix scanner passes **6 of 6**
(`out/s11_scan_control.json`).

---

## §3 — Consumers of M57's contaminated numbers

MEASURED (grep over `docs/research/*.md` and `AGENTS.md`): the 0.343 px bound
and its derivatives are carried in **six corpus locations** and **one
milestone report**.

| location | what it says | status |
| --- | --- | --- |
| SYNTHESIS fact 811 | "PR13/14 noise null reads **0.343 px where the truth is exactly 0**" | contaminated, amendment in §9 |
| SYNTHESIS fact 1140 | M82's 0.1754 px effect is "**51.1% of the bound**" | contaminated, amendment in §9 |
| SYNTHESIS fact 1186 | "`dsig`, whose noise null had to be *measured* and then failed at 0.343 px" | contaminated, amendment in §9 |
| SYNTHESIS fact 1207 | "fails its own noise null at 0.343 px where truth is exactly zero" | contaminated, amendment in §9 |
| SYNTHESIS discipline 590 | "`dsig` — whose null had to be measured and then **failed at 0.343 px**" | contaminated, amendment in §9 |
| `AGENTS.md` M82 ledger row | quotes the frozen bound | contaminated, amendment in §9 |
| `docs/research/M82-normalised-gate.md` | **10 sites**; M82 froze 0.343 as its readability rule | **not edited** — another milestone's report |

MEASURED: **four numeric coincidences were checked and excluded** — they are
not the null. `M85-output-correctness.md` (0.3431, a saturation p99),
`M16-orientation-fpn-measured.md` (0.3438, a parameter table),
`M71-flat-fields.md` (0.3436%), and `M73-cylinder-invariant.md` (0.34325, an
`n_eff/N` ratio).

---

## §4 — The class scan: 31 disagreements, 3 live defects

MEASURED (S12, `out/s12_use_sites.log`):

| role | count | verdict |
| --- | --- | --- |
| `SENSOR` | 3 | **live defects** — all three are M57 S5/S6/S7 `ISO = 500` |
| `SENSOR?` (longhand sigma, hand-read) | 4 | 1 live, 2 inert, 1 false positive — §5 |
| `OPERATOR` | 20 | **not defects** — rule 15 |
| `PLANT` | 4 | **not defects** — they define the synthetic |

MEASURED: the three `SENSOR` instances price at **1.7305× / 1.7515× /
1.7595×** too much modelled noise on `109MSDCF` at 106 / 250 / 500 DN
(S15). This reproduces phase 1's independently measured 1.7587× merged ratio
from a completely different route — a static AST scan plus the canonical
model, against phase 1's direct measurement on loaded pixels.

MEASURED: **no other milestone in the tree applies an EXIF-refutable constant
to a sensor model through a named sensor call.** The search that establishes
this absence is S10 + S12 over all 165 files containing any such constant;
`out/s12_use_sites.json` lists every instance and its role.

---

## §5 — What is new

### 5.1 One further instance of the class — `m41-r3-kill`

MEASURED: `experiments/m41-r3-kill/src/a11_metric_power.py:66` reads

```python
G, RN_E = 0.11446886446886446, 4.2        # 119MSDCF, ISO 50
```

and lines 204–205 load **real** `119MSDCF` planes through `load_plane`. The
gain is `ISO/436.8`, which AGENTS's M25 row records as **wrong by 2× at ISO
50** — Sony ISO 50 is an extended pull that reads out at base-ISO gain,
measured on two independent routes and fixed in the Rust tree at `2a4f5c5`.
The corrected value is `max(ISO, 100)/436.8 = 0.22894`.

MEASURED (S15): injected noise is **0.7043× the correct amplitude at 250 DN**
and **0.7065× at 1200 DN** — i.e. **1.4199× too small**.

DERIVED: the direction matters and it is favourable. Too *little* noise makes
a detection task **easier**. So every "this metric failed to detect" claim in
a11 is **conservative** and survives the correction; only a positive detection
claim would be threatened. Fact 477's headline entries are `UNDEFINED`
crossings — failures — which is the surviving direction.

DERIVED: fact 478's `(1 - rho)` scaling law is **invariant** to this error.
`a11` scales the shared and the independent noise draws by the same
`sigma_map`, so a global amplitude scalar multiplies numerator and denominator
of the recovery ratio alike and cancels. This is the same algebra as facts
617/708, where a linear post-filter scales `C` and `U` by the same `|H|^2` and
ring FRC cannot move — and the same algebra as phase 1's fact 1240 global
per-draw scalar.

### 5.2 A structural defect: one constant, two contracts

MEASURED: `experiments/M55-sigpow-attack/src/e2_real_halfstacks.py:56` assigns
`G, RN_E = 1.14469, 1.47`, and that single pair feeds **both**

- line 160, `sig1 = sqrt(0.5 * (G * lvl + (RN_E * G) ** 2))` — a sensor model,
  where the correct ISO-500 read noise is M48's 1.2392; and
- line 165, `L1.focus_fields(sub, G, RN_E)` — the frozen operator, where 1.47
  is the deliberately frozen value (rule 15).

DERIVED: **this instance cannot be corrected in place.** Changing `RN_E` to
satisfy the sensor model silently unfreezes the operator and breaks
cross-milestone comparability; leaving it satisfies the operator and leaves
the sensor model on a superseded constant. The fix is to split the name, not
to change the number.

MEASURED (S15): the numeric cost is **1.0014×** — 0.14%. **Inert as a
number, live as a structure.** It is reported because the next milestone to
"correct" it in the obvious way will break something that no test covers.

### 5.3 A bare stack name is not an identifier

MEASURED (S9): **`119MSDCF` exists under both capture roots with different
ISO** — `D:\personal\macro\119MSDCF` is **ISO 50, 33 frames**;
`D:\macro-dark-frames\119MSDCF` is **ISO 400, 22 frames**. Resolving a bare
name to the wrong root gives a **4× gain error** (0.22894 vs 0.91575).

MEASURED: this bit my own S9 on its first run. Keying the ground-truth table
by name alone let the dark-root entry **overwrite** the capture-root entry,
losing one of the two silently and reporting 33 stacks where there are 34.
The table is now keyed by root **and** name, and `sensor_for()` **refuses** a
bare colliding name rather than picking one (§7, control H2).

### 5.4 A rig constant that contradicts the documented rig

MEASURED: `AGENTS.md` documents white level **15360**. Two files disagree:

- `experiments/M87-occlusion/src/m87lib.py:43` sets `WHITE = 16383.0`. This is
  **not a straight defect** — M54 measured 16383 as the real clip point on
  `coffee-bean`. It is a **named ambiguity** between a documented rig constant
  and a measured one, and the documentation is what should move.
- `experiments/m34-confidence-vector/src/01-channels.py:49` sets
  `WHITE = 15360 - 512`. This is white-*above-black*, a different quantity
  that happens to share a name. A false positive, recorded so the next scan
  does not re-raise it.

MEASURED: the remaining **64 rig-constant assignments** across the tree all
agree with the documented values — `BLACK = 512` in 55 files,
`BLACK_LEVEL = 512` in 2, `WHITE = 15360` in 6, `WHITE_LEVEL = 15360` in 1.

### 5.5 Harmless-but-latent constants, named as the orchestrator asked

MEASURED: **27 per-stack constants match the EXIF of every stack their file
opens.** They are correct today and latent tomorrow — each is a per-stack
quantity written as a module constant, and each becomes wrong the moment its
file is pointed at a second stack. The largest clusters are
`M87-occlusion/src/*` (**9 files**, `ISO = 100` against `bee-3-cpl`) and
`m31-verification/src/*` (**7 files**, `ISO = 160.0` against `109MSDCF`).
`experiments/ORCH-drift-check/decide.py:46` sets `GAIN = 0.229`, which matches
`bee-3-cpl`'s ISO 100 — but line 47 sets `RN_E = 3.0`, which matches
**neither** branch of the canonical model (1.2392 above ISO 400, 4.20 below).
Its role is `PLANT`, so it is not a defect; it is an undocumented constant.

---

## §6 — Retraction or footnote, one row at a time

The orchestrator's distinction: a number that moves but was never load-bearing
is a footnote; a number that moves and was used to cancel work is a
retraction.

| number | moves by | load-bearing? | verdict |
| --- | --- | --- | --- |
| M57's 0.34310 px null | → 0.089–0.094 px | **yes — it bounded what two milestones attempted** | **RETRACTION** (already folded, facts 1241–1243) |
| M82's "51.1% of the bound" | → effect exceeds the corrected null at `N = 1` | **yes — it produced 18 of 18 abstentions** | **RETRACTION** (already folded) |
| M55 `e1_dark_rho` read noise | 1.0033× and 1.0017× | no — the conclusion is a shortfall of hundreds-× in **variance** | **FOOTNOTE** |
| M55 `e2_real_halfstacks` read noise | 1.0014× | no numerically; **yes structurally** (§5.2) | **FOOTNOTE + structural flag** |
| m41 `a11` gain on `119MSDCF` | 0.7043× | direction is conservative for the claims actually made | **FOOTNOTE**, with fact 477 open (§10) |
| SYNTHESIS fact 130's 22.9 DN cap | → **32.41 DN** | **no** | **FOOTNOTE** — see below |

MEASURED (S15): fact 130 rules fact 88's measured 43.2–53.1 DN impossible
because the noise model caps temporal σ at 22.9 DN at ISO 50. That 22.9 was
computed with the superseded `g = 0.1145`; my reproduction of it lands at
**22.91 DN**, confirming the arithmetic being audited. With the corrected
`g = 0.22894` the cap becomes **32.41 DN**. Fact 88's range is still above the
corrected cap by **1.33×–1.64×**, so **the refutation stands and only the
digits move**. This is the clean example of the distinction the orchestrator
asked for: a number contaminated by exactly the same class of defect, in the
corpus, load-bearing for a refutation — and the refutation survives.

---

## §7 — The mechanical fix

`experiments/M92-null-averaging/src/s13_sensor_guard.py`. Two halves, because
policing a constant and removing it are different jobs and the class needs
both.

**(1) Remove the constant.** `sensor_for(stack)` returns
`(iso, gain_dn_per_e, read_noise_e)` from the capture's own EXIF, cached. A
script that asks the capture what its ISO is **cannot have this defect**.
`assert_sensor(stack, iso=..., g=..., rn_e=...)` is the registration-time
form: one call at the top of a script, which raises unless every declared
value matches EXIF, and returns the authoritative triple so the caller uses it
directly.

**(2) Police what remains.** `check_tree()` re-runs the S10 scan and fails on
any MISMATCH whose S12 role is `SENSOR`. It deliberately does **not** fail on
`OPERATOR` or `PLANT` roles — a guard that demands rule-15 frozen constants be
changed would be switched off within a week, and a guard that is switched off
is worth less than no guard.

MEASURED: run against the tree as it stands with the allowlist off, the guard
is **RED on exactly the three known m57 assignments and nothing else**, exit
code 1. With the three carried on an allowlist that requires each entry to
name the SYNTHESIS fact documenting it, the guard is **green**, exit code 0.
It is therefore adoptable today without a tree-wide edit, and the allowlist
cannot quietly absorb a new defect.

**Proposed promotion:** move `sensor_for` / `assert_sensor` into a shared
location and run `check_tree` from `scripts/corpus_lint.py` or alongside it. I
did not put it in `scripts/` myself — that directory is shared with six live
milestones tonight and the corpus gate is the orchestrator's.

---

## §8 — Controls, including the ones made to fail

MEASURED (S11, `out/s11_scan_control.json`) — **6 of 6**. Fixtures F3 (tuple
unpacking) and F4 (docstring-only stack name) are the two shapes earlier
revisions of the scanner **demonstrably failed**; §2 records what each got
wrong before the fix.

MEASURED (S14, `out/s14_guard_control.json`) — **10 of 10**, with defects
planted into the real tree in a directory the real guard really walks, then
removed:

| case | expected | got |
| --- | --- | --- |
| baseline, no plants | GREEN | GREEN |
| P1 — `ISO = 500` on `109MSDCF`, reaching `noise_var_dn` | **RED** | **RED** |
| P2 — the same defect hidden in a tuple unpacking | **RED** | **RED** |
| P3 — `ISO = 160` on `109MSDCF`, correct | GREEN | GREEN |
| P4 — `ISO = 500` reaching only `focus_fields` | GREEN | GREEN |
| P5 — no constant, uses `assert_sensor` | GREEN | GREEN |
| after cleanup | GREEN | GREEN |
| H1 — `assert_sensor("109MSDCF", iso=500)` | **RAISE** | **RAISE** |
| H2 — `sensor_for("119MSDCF")`, ambiguous | **RAISE** | **RAISE** |
| H3 — `assert_sensor("109MSDCF", iso=160)` | RETURN | RETURN |

P3 and P4 are the controls that matter as much as P1 and P2: **a guard that
fires on a correct constant, or on a frozen operator constant, is a guard that
gets disabled.** Both were planted specifically to try to make the guard
over-fire, and it did not.

MEASURED: the baseline and after-cleanup cases both read 0 findings, so the
control can distinguish its own plants from pre-existing state. Had the
baseline been dirty, S14 aborts and says so rather than reporting a pass.

**Where my instrument disagreed with itself:** S12's first revision classified
`M55/e2_real_halfstacks.py:56` as `OPERATOR` only, because its role
precedence suppressed a longhand-sigma use whenever a named operator call was
also present. That is exactly the dual-role case of §5.2 — the instrument was
hiding the single most interesting instance it had. Reported here rather than
silently corrected.

---

## §9 — Amendments for SYNTHESIS and AGENTS

These are the orchestrator's files. Below is verbatim before/after text. Each
amendment is a **minimal appended clause**, not a rewrite, so folding cannot
disturb the surrounding row.

### Fact 811

**BEFORE** (fragment): `PR13/14 noise null reads **0.343 px where the truth is exactly 0**.`

**AFTER**: `PR13/14 noise null reads **0.343 px where the truth is exactly 0** — **CONTAMINATED, see fact 1242: that figure is a single draw measured with 1.7587x too much injected noise; the corrected null is 0.089–0.094 px**.`

### Fact 1140

**BEFORE** (fragment): `**maximum absolute magnitude 0.1754 px against M82's frozen 0.343 px bound** taken from M57's measured independent-noise null -- **51.1% of the bound**`

**AFTER**: `**maximum absolute magnitude 0.1754 px against M82's frozen 0.343 px bound** taken from M57's measured independent-noise null -- **51.1% of the bound** (**the bound is contaminated: facts 1241–1243 correct it to 0.089–0.094 px, at which the 0.1754 px effect is readable at N = 1 and the 18 abstentions are not entitled**)`

### Fact 1186

**BEFORE** (fragment): `` `dsig`, whose noise null had to be *measured* and then failed at 0.343 px ``

**AFTER**: `` `dsig`, whose noise null had to be *measured* and then failed at 0.343 px (**contaminated; corrected to 0.089–0.094 px by fact 1242 — the contrast with an analytic null stands, the number does not**) ``

### Fact 1207

**BEFORE** (fragment): `fails its own noise null at 0.343 px where truth is exactly zero`

**AFTER**: `fails its own noise null at 0.343 px where truth is exactly zero (**contaminated figure; see fact 1242**)`

### Discipline 590

**BEFORE** (fragment): `` `dsig` -- whose null had to be measured and then **failed at 0.343 px**, abstaining 18 of 18 rows ``

**AFTER**: `` `dsig` -- whose null had to be measured and then **failed at 0.343 px**, abstaining 18 of 18 rows (**and the measured null was itself wrong by 1.7587x, fact 1242 — which strengthens this discipline rather than weakening it: a fitted null can be wrong in a way a theorem cannot**) ``

### Fact 130 — a *different* contamination, same class

**BEFORE** (fragment): `At ISO 50 (`g`=0.1145) with ROI means ≤4585 DN, temporal σ caps at **22.9 DN**; fact 88 reports 43.2–53.1 DN.`

**AFTER**: `At ISO 50 with ROI means ≤4585 DN, temporal σ caps at **32.41 DN** (**corrected by M92b: the original 22.9 DN used `g`=0.1145, the ISO-50 gain M25 later refuted; the corrected `g`=0.22894 raises the cap 1.41x**); fact 88 reports 43.2–53.1 DN, still above the corrected cap by 1.33x–1.64x, **so the refutation stands unchanged**.`

### `AGENTS.md` M82 ledger row

Append to the row's verdict text:

`**M92b: the 0.343 px bound this milestone froze is contaminated (facts 1241–1243). M82's own 0.1754 px effect clears the corrected null at N = 1; its 18 abstentions were caused by the bound, not by the instrument.**`

---

## §10 — What I did not do, and what is still open

- I did **not** re-run m41 to test whether fact 477's absolute recovery ratios
  move under the 1.4199× correction. I derived that fact 478's `(1 - rho)` law
  is invariant and that the direction of the error is conservative for
  failure-to-detect claims, which is what 477's headline entries are. A
  measurement would settle it; a derivation does not.
- I did **not** edit `docs/research/M82-normalised-gate.md`, which carries the
  bound at 10 sites. It is another milestone's report.
- I did **not** run any gate comparison and did not read or touch
  `experiments/M98-gate/` or `docs/research/M98-gate-adjudication.md`.
- I did **not** touch `crates/`.
- The guard lives in my own experiment tree. Promoting it into `scripts/` is
  the orchestrator's call and would collide with live milestones tonight.

---

## § Candidate facts

**P1.** The experiment tree contains 254 sensor-constant assignments across
165 Python files; 31 disagree with the EXIF of a stack their file opens, but
only **3 reach a sensor model over real pixels** — all three the known M57
S5/S6/S7 `ISO = 500` instances. **20 of 31 reach the frozen detail operator**,
where disagreement with EXIF is rule-15-correct behaviour, and 4 define
synthetic plants. *Significance:* fact 1242's liability is bounded and
one-milestone-wide, not corpus-wide; and an audit that skipped the use-site
classification would have demanded 20 changes that break every
cross-milestone comparison in the corpus. MEASURED — M92b S10/S12,
`experiments/M92-null-averaging/out/{s10_const_scan,s12_use_sites}.json`.

**P2.** `experiments/m41-r3-kill/src/a11_metric_power.py:66` applies
`G = 0.11446886` — M25's refuted `ISO/436.8` ISO-50 gain — to **real**
`119MSDCF` planes loaded at lines 204–205, understating injected noise by
**1.4199×** (0.7043× at 250 DN, 0.7065× at 1200 DN). *Significance:* the
second confirmed instance of the M92 class, and it shows the class predates
M57; the direction is conservative for a11's failure-to-detect claims, so
fact 477's `UNDEFINED` crossings survive, but the absolute recovery ratios
were not re-measured. MEASURED — M92b S10/S12/S15.

**P3.** Fact 478's `(1 - rho)` recovery-scaling law is **invariant** to a gain
error, because `a11` scales the shared and independent noise draws by the same
`sigma_map` and a global amplitude scalar cancels from the ratio.
*Significance:* the same algebra as facts 617/708 (a linear post-filter scales
`C` and `U` alike, so ring FRC cannot move) and as fact 1240's global per-draw
scalar — a third independent appearance of the cancelling-scalar structure,
which is now a reusable test for whether a published ratio is exposed to a
constant. DERIVED — M92b S15 §6.

**P4.** `M55-sigpow-attack/src/e2_real_halfstacks.py:56` assigns one
`G, RN_E` pair that feeds **both** a sensor model (line 160) and the frozen
detail operator (line 165). *Significance:* this instance **cannot be
corrected in place** — satisfying the sensor model unfreezes the operator and
breaks rule-15 comparability; the fix is to split the name. The numeric cost
is only 1.0014×, so it is inert as a number and live as a structure, and the
next milestone to "obviously" correct it will break something no test covers.
MEASURED (both use sites, and the 1.0014× price) — M92b S12/S15.

**P5.** `119MSDCF` exists under **both** capture roots with different sensors
— `D:\personal\macro` at ISO 50 / 33 frames, `D:\macro-dark-frames` at ISO
400 / 22 frames — so a bare stack name is not an identifier and resolving to
the wrong root is a **4× gain error**. *Significance:* this defeated my own
ground-truth table on its first run, where keying by name alone let one entry
silently overwrite the other; any helper that maps a bare name to a sensor
must refuse rather than choose. MEASURED — M92b S9,
`out/s9_iso_truth.json`.

**P6.** A registration-time guard for this defect class exists and is proven:
`sensor_for(stack)` / `assert_sensor(stack, ...)` read the constant from the
capture's own EXIF, and `check_tree()` fails any MISMATCH that reaches a
sensor model while deliberately ignoring `OPERATOR` and `PLANT` roles. It is
**RED on exactly the three known m57 assignments** with its allowlist off and
green with them carried, so it is adoptable today without a tree-wide edit.
*Significance:* converts fact 1242 from a standing liability into a check;
and the allowlist requires each entry to name the fact documenting it, so it
cannot quietly absorb a new defect. MEASURED — M92b S13,
`out/s13_sensor_guard.json`.

**P7.** The guard passes **10 of 10** falsifying-control cases with defects
planted into the live tree and removed, including **two planted non-defects it
correctly ignored** (a correct constant; a wrong constant reaching only
`focus_fields`) and two helper refusals (a declared ISO that EXIF contradicts;
an ambiguous bare stack name). *Significance:* a guard made to fire is half a
control — a guard that has been made to **stay quiet** on the two shapes that
would get it disabled is the other half, and the corpus's guard failures have
usually been over-firing rather than under-firing. MEASURED — M92b S14,
`out/s14_guard_control.json`.

**P8.** SYNTHESIS fact 130's 22.9 DN ISO-50 temporal-sigma cap was computed
with the superseded `g = 0.1145`; the corrected `g = 0.22894` raises it to
**32.41 DN**, a 1.41× move. Fact 88's measured 43.2–53.1 DN remains above the
corrected cap by **1.33×–1.64×**, so **the refutation stands and only the
digits move**. *Significance:* a second, independent instance of this defect
class already folded in the corpus and load-bearing for a refutation — and
the worked example of footnote-versus-retraction: the number moved, the
conclusion did not. MEASURED — M92b S15 §5; reproduction of the original
22.9 DN to 22.91 DN confirms the arithmetic audited.

**P9.** A tree-wide static scan for a defect class must handle **tuple
unpacking** and must exclude **docstrings** from stack-name matching. M57's
`s7_bias_or_variance.py:44` hides `ISO = 500` inside
`PAD, G, RN_E, ISO = 32, 1.14469, 1.47, 500`, invisible to a scan that only
walks single-target assignments; adding tuple support took this audit from
121 instances to 254. Conversely, `m61-ptc-high-iso/src/03-power-control.py`
is a pure synthetic plant whose *docstring* names `foam`, and counting that
produced a false MISMATCH. *Significance:* both shapes are now permanent
fixtures (S11 F3, F4) that the pre-fix scanner demonstrably fails — a scan
without them silently under-reports and over-reports at the same time.
MEASURED — M92b S11, `out/s11_scan_control.json`.

**P10.** `experiments/M87-occlusion/src/m87lib.py:43` sets `WHITE = 16383.0`
against `AGENTS.md`'s documented 15360, and **M54 measured 16383 as the real
clip point on `coffee-bean`**. *Significance:* this is a named ambiguity in
which the **documentation** is the thing that should move, not the code; the
remaining 64 rig-constant assignments in the tree all agree with the
documented values, so this is the only genuine rig disagreement.
MEASURED — M92b S10 rig section.

**P11.** 27 per-stack sensor constants in the tree currently **match** the
EXIF of every stack their file opens — largest clusters
`M87-occlusion/src/*` (9 files, `ISO = 100` / `bee-3-cpl`) and
`m31-verification/src/*` (7 files, `ISO = 160.0` / `109MSDCF`).
*Significance:* each is correct today and latent tomorrow, because a per-stack
quantity written as a module constant becomes wrong the moment its file is
pointed at a second stack — which is precisely how M57's defect was born, and
why the fix has to be `sensor_for(stack)` rather than a one-time correction
sweep. MEASURED — M92b S10 per-stack MATCH section.
