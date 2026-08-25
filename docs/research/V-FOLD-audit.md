# V-FOLD — audit of the orchestrator's fold, facts 1560–1665

**Auditor:** V-FOLD (independent; no stake in any milestone in range)
**Scope offered:** facts 1560–1665 of `docs/research/SYNTHESIS.md` (106 rows).
**Scope actually audited to artefact level: 25 facts.** Method and selection below.
**Rule applied throughout:** a fact is confirmed only when I located the number in a
primary artefact — a JSON under `C:\dev\strehl-out\`, a re-run of the producing
script, or the crate source — and confirmed *what it is a number of*. A milestone
report repeating a number is **not** confirmation; it is the thing under audit.

---

## 1. Headline

**Of 25 facts audited, 8 are non-SAFE. All 8 err in the direction that STRENGTHENS
the claim. Zero weaken it.**

| | count |
| --- | --- |
| SAFE | 15 |
| UNSAFE-IN-A-CLAUSE | 7 |
| FACTUALLY-WRONG | 1 |
| UNVERIFIED (audited, could not settle) | 2 (1594, and one sub-clause of 1637) |
| **stronger : weaker** | **8 : 0** |

**Discipline 849 is CONFIRMED, not overstated.** Under a null of unbiased folding the
probability of 8/8 landing on the strengthening side is 0.5^8 = **0.0039**. Combined
with tonight's independently-found six (also 6:0), the fold has now produced
**14 directional errors and not one runs toward weakening a claim.**

I actively hunted for a weakening error, and I found exactly one candidate — fact
1579 undercounts the environment gates, which would have made ORCH's own point
*less* forceful. **It dissolved on dating** (§5). I report it anyway, because a null
would have been a real result and I want the record to show I looked.

The non-SAFE rate is **32 %** (8/25). That is a rate at which the corpus should not
be treated as self-certifying.

**Most serious finding: fact 1568 is FACTUALLY-WRONG in a matrix that six other
files repeat**, and it survived a validation that was structurally incapable of
detecting it. Second: **facts 1589 and 1593 are quoted verbatim in a crate comment**
(`crates/strehl-raw/src/identity.rs`) with the disqualifying qualifier missing.
Third: **fact 1658 is the one in-range fact `docs/captures-needed.md` relies on**,
and both of its defects push the owner toward a capture he is being told he needs.

---

## 2. How the 25 were chosen

The brief prioritised (a) facts carrying numbers, (b) facts cited in
`docs/captures-needed.md`, (c) facts cited under `crates/`. I scanned all three and
then chose for **auditability**, because an unauditable verdict is worthless:

- **All 6 in-range facts cited under `crates/`** — 1587, 1588, 1589, 1592, 1593, 1594,
  all cited from `crates/strehl-raw/src/identity.rs`. These are load-bearing on
  shipped code. Audited all six.
- **The 1 in-range fact cited in `docs/captures-needed.md`** — 1658. Audited.
- **The M113-ca cluster (1567–1573)** — 7 facts, dense with numbers, complete
  artefact set at `C:\dev\strehl-out\M113-ca\c*.json`.
- **The ORCH self-sourced clusters (1633–1646)** — 9 facts. These are the highest-risk
  rows in the range: **ORCH is its own source**, so no milestone author ever checked
  them, and they have *no saved artefact* — the numbers exist only in the fact text
  and in stdout nobody kept. I verified them the only way available: **by re-running
  ORCH's own scripts.** That is the strongest evidence in this report.
- **M115 (1650, 1651)** — 2 facts, complete artefacts.
- **1579** — the defaults audit, verifiable directly against `crates/` read-only.

Facts I deliberately did **not** audit: the six already corrected tonight
(1595/1598/1599/1601/1662/1663 — I confirmed ORCH has since amended them in place),
and the prose-only rows carrying no number, which cannot be checked against an
artefact and would have padded the count without adding a verdict you can act on.

I chose 25 thorough over 105 shallow, as instructed. The sample is **biased toward
number-dense and code-cited rows**, so the 32 % rate should be read as the rate
*among facts that carry checkable numbers*, not across the whole corpus.

---

## 3. Verdict table

| Fact | Verdict | Direction | Primary source (the artefact, not the report) | Correction needed |
| --- | --- | --- | --- | --- |
| 1567 | SAFE | – | `M113-ca\c9_binned.json`, `c4_globalfit.json` | none |
| **1568** | **FACTUALLY-WRONG** | **stronger** | `crates/strehl-core/src/color.rs:178-215` (+ my numpy re-derivation) | green→red is **27.4 %** not 10.4 %; red→green **7.7 %** not 20.3 % |
| 1569 | SAFE | – | `M113-ca\c8_linear.json`, `c4_globalfit.json` | none |
| 1570 | SAFE | – | `M113-ca\c9_binned.json` | none |
| **1571** | **UNSAFE-IN-A-CLAUSE** | **stronger** | `M113-ca\c10_rings.json` | the r=0.11 ring's bootstrap sd is **80.0 ppm**, outside the quoted "8-23 ppm" |
| 1572 | SAFE | – | `M113-ca\c9_binned.json` | none (see note) |
| 1573 | SAFE | – | `experiments/ORCH-drift-check/ca_gain.py:4,109-119` | none |
| 1579 | SAFE at fold time | – | `crates/**/*.rs` + `git log` | none — see §5, staleness not fold error |
| **1587** | **UNSAFE-IN-A-CLAUSE** | **stronger** | `M110-sheet\ca_overshoot_default_vs_ca.json` | headline "NO OVERSHOOT ANYWHERE" is not M110's claim; artefact holds `overshoot_pct` to **18.82 %** |
| 1588 | SAFE | – | `M110-sheet\ca_overshoot_default_vs_ca.json` | none |
| **1589** | **UNSAFE-IN-A-CLAUSE** | **stronger** | `M110-sheet\ca_overshoot_default_vs_ca.json` + `experiments/M110-sheet/sheet.py:262` | numbers exact; **measured in `--srgb`**, the space `--help` forbids for measuring |
| 1592 | SAFE at fold time | – | `crates/strehl-raw/src/identity.rs` + `git log` | none — see §5 |
| **1593** | **UNSAFE-IN-A-CLAUSE** | **stronger** | `experiments/M110-sheet/sheet.py:262` | same `--srgb` defect; **this row is quoted in a crate comment** |
| 1594 | UNVERIFIED | – | — | label is honestly `ARGUED`; `d142783` / `0.235 s` not located |
| 1633 | SAFE | – | re-ran `experiments/ORCH-drift-check/level_drift_budget.py` | none |
| **1634** | **UNSAFE-IN-A-CLAUSE** | **stronger** | re-ran `level_drift_budget.py` | 91.8 % / 0.449 % are **one window of six**, stated unqualified; the monotone `19624→18322` is **unlocated** |
| 1635 | SAFE | – | re-ran `level_drift_budget.py` | none |
| 1637 | SAFE, 1 sub-clause UNVERIFIED | – | re-ran `experiments/ORCH-drift-check/photometric_ab.py A1` | "six smoothest windows" endpoint set not reproducible |
| **1641** | **UNSAFE-IN-A-CLAUSE** | **stronger** | re-ran `photometric_ab.py`, `switch_gate.py`, + `experiments/V-FOLD/f1641.py` | every number confirmed; **"identical windows across arms" is REFUTED** |
| 1644 | SAFE | – | re-ran `experiments/ORCH-drift-check/switch_gate.py A1..A4` | none |
| 1645 | SAFE | – | re-ran `switch_gate.py` | none |
| 1646 | SAFE | – | re-ran `switch_gate.py` | none |
| 1650 | SAFE | – | `M115-deconv-headroom\out\s07_summary.json` | none |
| 1651 | SAFE | – | `M115-deconv-headroom\out\s05_ringing.json` | none |
| **1658** | **UNSAFE-IN-A-CLAUSE (x2)** | **stronger, stronger** | `M113-spectral\s3_analyse.json` + `docs/research/M113-spectral.md` | f/8 exception dropped; **±15 ppm spliced in from a different experiment** |

---

## 4. The eight defects, with the evidence

### 4.1 Fact 1568 — FACTUALLY-WRONG — the `camera_to_srgb` matrix is the wrong matrix

The most consequential finding, because six files repeat it.

`crates/strehl-core/src/color.rs:178-215` computes the matrix as
`inv(rownorm(A7C2_XYZ_TO_CAM @ SRGB_TO_XYZ_D65))` — **normalise, then invert.**
Fact 1568, `docs/research/M113-ca.md` §1, `experiments/M113-ca/src/c8_linear.py:11-12`,
`experiments/ORCH-drift-check/fold125.py:43-44` and the SUPERSEDED banner in
`ca_gain.py:8-9` all quote `rownorm(inv(A @ S))` — **invert, then normalise.** These
are different matrices.

I derived both in numpy (`experiments/V-FOLD/matrix.py`). The crate's algorithm gives

```
R  +1.6361  -0.4486  -0.1874
G  -0.1152  +1.4890  -0.3738
```

which matches `color.rs:221`'s own doc comment character for character
("its green row is `[-0.115, +1.489, -0.374]`"), and matches
`experiments/M110-sheet/ca_matrix_prereg.py`, which **already printed the
disagreement** ("ORCH relayed the green row as [-0.4530, +2.2300, -0.7770]" vs
"computed green row: [-0.1152, +1.4890, -0.3738]") and was not folded.

Consequence for the numbers in the row: **green-into-red is 27.4 %, not 10.4 %;
red-into-green is 7.7 %, not 20.3 %.**

**Why the validation could not catch it.** M113 offered "it reproduces the
neutral-response constant 1.07304438742" as proof. `neutral_response(A) = A @ D65_XYZ`
is **invariant to normalisation order**. So is the row-sum-equals-1 test the crate
itself runs. Both variants pass both checks. *The offered validation is structurally
incapable of separating the two candidates it was offered to choose between* — which
is the same failure as fact 1602's inert arm, in a different costume.

**Direction — stated honestly, because it is mixed.** Red-into-green is the
load-bearing coefficient for an R−G displacement measurement, and it is **overstated
2.6x** (20.3 % quoted vs 7.7 % true) — that is the strengthening error, and it is the
one that matters for how much of M113's CA signal you are willing to call an sRGB
artefact. Green-into-red is *understated* (10.4 % vs 27.4 %). So the row's
**conclusion** — that sRGB is cross-channel contaminated and unfit for measuring —
**survives and is if anything reinforced**; it is the specific quantities that are
wrong. I classify the row FACTUALLY-WRONG / stronger on the load-bearing coefficient
and say plainly that the qualitative finding is not disturbed.

`1.1975` (the wrong matrix's red row leading term) appears **exactly once** in the
whole corpus, so no later fact corrects it.

### 4.2 Fact 1587 — the headline is not the milestone's claim

Every radial number is exact: 9.73 / 9.78 / 9.47 and 14.22 / 13.68 / 11.66 all appear
in `width_profile` in `C:\dev\strehl-out\M110-sheet\ca_overshoot_default_vs_ca.json`.

But the row's headline is **"NO OVERSHOOT ANYWHERE"**, and that is not what M110 §16.2
says. M110's claim is narrower and defensible: *no discontinuity and no upward trend
past the support radius.* The artefact's `overshoot_pct` field reaches **18.82 %**.
The row also quotes a "0.00 %" null — that is the trivial **off-vs-off** control (M110
labels it "identical input"); the artefact's real null, `overshoot_inert_null`, runs
**4.68 %–25.73 %** and is not mentioned. And the real-minus-null excess on `bee-3-cpl`
**climbs across the support boundary**: +2.93 / +3.88 / +4.59.

Direction: **stronger.** A bounded, qualified, geometry-specific finding was folded
as an unbounded universal.

### 4.3 Facts 1589 and 1593 — right numbers, wrong measurement space — **and this one is in the crate**

I re-derived both figures from raw band DN in the artefact rather than trusting them:
61.0 % = (472.2 − 1209.6)/1209.6, 58.7 % = (995.5 − 2411.7)/2411.7, with the edge
contrasts moving 2.4511→1.9313 and 1.6309→1.2719. **The arithmetic is exact.**

What is missing is *what they are numbers of.* `experiments/M110-sheet/sheet.py:262`
shows **every M110-sheet render is produced with `--srgb`** — the space this project's
own `--help` describes as *"For looking at, NOT for measuring"*, and which M113
measured as cross-channel-contaminated at a chain transfer of 1.3073. A
*chroma-excess* statistic is precisely the statistic a cross-channel operator moves.
Neither row carries the qualifier.

**This has already propagated out of the corpus and into shipped code.**
`crates/strehl-raw/src/identity.rs` module doc, verbatim:

> the project's best-measured quality win (**61.0% and 58.7% less edge-localised chroma
> excess**, SYNTHESIS facts 1587-1589) had to ship switched **off**

Direction: **stronger.** "The project's best-measured quality win" is resting on a
measurement taken in the space the project forbids for measuring.

### 4.4 Fact 1571 — a spread quoted from the good rings only

±15 ppm is the exact half-range of `c10_rings.json`'s `eps_off` row, confirmed. The
residual and outside/inside figures are exact. But the parenthetical
"(bootstrap sd 8-23 ppm)" is grammatically bound to the range "r = 0.11 to 0.87" —
and the r=0.11 ring's bootstrap sd is **80.0 ppm**, over 3x the stated ceiling.
M113-ca prints the full row (`80 23 12 9 8 8 12`); the fold kept the tail and dropped
the head. Direction: **stronger** — the flatness looks ~3x better established.

### 4.5 Fact 1634 — a single-window result stated as a general one, plus an unlocated number

I re-ran `experiments/ORCH-drift-check/level_drift_budget.py`. It prints:

```
drift shape at window (2832, 400): linear trend removes 91.8% of the variance (residual sd 0.449% of level)
```

Both numbers exact — **at one window of the six the script measures.** Fact 1634
states them unqualified, as a property of "the drift". The script computes the fit for
no other window, so the generalisation has no support anywhere. Same failure as fact
1601 (ROI stated as frame). Direction: **stronger.**

Separately: the row's clause *"The sequence is monotone across the whole bracket
(19624 counts at f120 falling to 18322 at f208)"* **is not produced by the script and I
could not locate it in any artefact.** See §6.

### 4.6 Fact 1641 — every number right, the control claim wrong

I wrote `experiments/V-FOLD/f1641.py`, which loads `switch_gate.py`'s own `hf()` and
`pools()` so the geometry is identical to ORCH's instrument, and reads the TIFFs with
`tifffile.imread` under an `assert dtype == np.uint16`. Output:

```
bee-3-cpl A0 vs A2  (2832,1552)  hf(A0)=500.8  hf(A2)=348.0  ratio=0.6948  cut=30.5%
bee-3-cpl A0 vs A2  SMOOTH pool ratios: 0.851 0.673 0.813 0.657 0.803 0.969 0.692 0.615
bee-3-cpl A0 vs A1  (2832,1552)  ratio=1.0372
tweezers-cpl A0 vs A1  (784,784)  ratio=1.0272
```

**Every number in fact 1641 reproduces exactly** — `500.8 → 348.0`, the 30.5 % cut, the
`0.851 / 0.673 / 0.813` smooth-window ratios, and the `1.037` / `1.027` photometric
texture ratios. I had this flagged as a possible unattributed claim; **it is not one,
and I withdraw that suspicion.**

What is wrong is the methodological boast: *"identical windows across arms."* Both
scripts select windows from the **symmetric mean of A0 and the test arm**, so the pool
is arm-dependent by construction. Measured: brightness bars differ per arm
(bee 9586 / 9492 / 9498 / 9528; tweezers 7682 / 7766 / 7761 / 7691), and the
`photometric_ab` tweezers window sets genuinely differ — A1 contains (400,912), A2
contains (1680,400). Direction: **stronger** — it claims a control the instrument does
not implement, which is exactly the property fact 1624 makes a virtue of ("takes it as
an argument precisely so an A/B cannot silently become a comparison of two different
window sets"). Here it silently did.

### 4.7 Fact 1658 — two defects, and this is the row the owner's capture brief runs on

`docs/captures-needed.md` repeats it: *"fact 1658 established that every `-cpl` stack
you have shot is f/5.6 ... so both variables are currently held fixed everywhere."*

First: the source is **`docs/research/M113-spectral.md`**, not `M113-ca.md`
(both exist; the source column says only "M113"). I confirmed the crux at artefact
level in `C:\dev\strehl-out\M113-spectral\s3_analyse.json`:
`bee-1-cpl.eps_R_off = -0.000536168569518496` → **536.2 ppm**, at
`focus_m = 0.2841`, identical to `couch-fibers-cpl`. 654.9 − 536.2 = **118.7 ppm**.
The "3.5 ppm from the bee mean" is bee-1 against the mean of bee-2 and bee-3
(549.4 + 529.9)/2 = 539.65, difference 3.45. **Confirmed.**

**Defect 1 — the f/8 exception was dropped.** M113 wrote: *"Aperture is f/5.6 on every
`-cpl` stack — **only coffee-bean and foam differ at f/8 and both are non-CPL anyway.**"*
ORCH folded it as *"there is no aperture contrast anywhere in the library."* There is:
two stacks at f/8. It is confounded with subject and CPL, which is M113's actual and
correct point, but it is not absent. Direction: **stronger** — and it is the clause
`captures-needed.md` turns into "held fixed everywhere", which is what sends the owner
out with a camera.

**Defect 2 — `±15 ppm` is spliced in from a different experiment.** The clause
"Subject radial structure: refuted to **+/-15 ppm**" carries the n=8 authority of
M113-spectral's rival table. **The string does not occur in `M113-spectral.md` at
all** (whitespace-collapsed search: 0 hits for "15 ppm", 0 for "±15"). The only ±15 ppm
in the M113 corpus is the half-range of the ring table in **M113-ca**, on
**couch-fibers-cpl alone, n=1 stack, a different experiment**. This is the fact-1595
failure mode exactly: a number from one experiment presented as the result of another.
Direction: **stronger.**

---

## 5. The candidate weakening error, and why it is not one

I looked hard for an error running the other way. Two rows appeared to be wrong
against the current tree in ORCH's *disfavour*. **Both dissolved on dating, and I
report the dating rather than the accusation.**

- **Fact 1579** says "of the **seven** environment gates ... exactly ONE is on by
  default". I enumerated `crates/**/*.rs` and found an **eighth**:
  `STREHL_ROBUST_ELECTION` (`crates/strehl-core/src/merge.rs:508`), off by default,
  on the render path. That undercount would have made ORCH's own conclusion *weaker*.
  But: `git log -S` dates that gate to `e028113`, **2026-08-24 20:00:49**, and the fold
  to `63f1799`, **17:32:08** — the gate landed **2 h 28 m after** the fold. Not a fold
  error.
- **Fact 1592** says "STREHL PARSES NO CAMERA IDENTITY WHATSOEVER ... `git grep` for
  `0x010f`, `0x0110`, `"Make"`, `"Model"`, `LensSpec`, `maker_note` returns nothing."
  It now returns plenty — `crates/strehl-raw/src/identity.rs` does exactly this.
  But that file was created by `43cee3b` (M119), **2026-08-24 19:52:24**, and the fold
  is `a91be3e`, **17:59:11** — **1 h 53 m earlier**. The fact was true when folded and
  is now stale. Not a fold error.

Both rows are nonetheless **currently false as written** and a reader today will be
misled. That is a corpus-currency problem, not a directional one, and I flag it
separately so it is not scored against the fold.

The closest thing to a genuine weakening bias I found is **fact 1588**, which
describes overshoot as "only 9–19 %" where the artefact would have supported a
slightly larger figure. It is conservative, it is within the source, and I score it
SAFE.

---

## 6. Claims I could not source at all

One, and it is narrow:

- **Fact 1634**, clause: *"The sequence is monotone across the whole bracket (19624
  counts at f120 falling to 18322 at f208)."* `level_drift_budget.py` — the row's own
  cited instrument — does not compute or print it; I re-ran the script and grepped its
  full stdout for `19624`, `18322`, `f120`, `f208`, `monoton`: **zero hits.** A
  value-scan across `C:\dev\strehl-out\**\*.json` did not anchor it either. The
  arithmetic is self-consistent (a 6.6 % fall, inside the 3.2–8.4 % drift band), so
  this is more likely a number computed in a scratch session and not preserved than an
  invention. But **it has no locatable author**, which is the fact-1663 shape, and I
  cannot clear it.

I want to be explicit about a **suspicion I withdrew**: fact 1641's `500.8 → 348.0`,
`1.037` / `1.027` and `0.851 / 0.673 / 0.813` looked unattributed for most of this
audit — they appear in no artefact and no script output. They are real, and I
reproduced all of them (§4.6). The lesson is that "not in a JSON" is not the same as
"no author" when the instrument is re-runnable, and I did not report it until I had
re-run it.

Fact **1594**'s `d142783` and `0.235 s` I could not locate and did not pursue; the row
is honestly self-labelled `ARGUED`, so it makes no measurement claim. **UNVERIFIED.**

---

## 7. The label check

I compared column 2 against the source author's own words for all 25.

**No ARGUED→MEASURED upgrade was found in this sample.** The two known upgrades
(fact 1599) are outside it. Fact 1594 is the interesting case in the other direction:
ORCH marked its **own** claim `ARGUED` and wrote out the reason
("no mismatched render has been measured, and the size of the resulting error is
unknown"). Fact 1658's `REFUTED` matches M113-spectral's own verdict table.

**This matters for diagnosis.** The failure in this sample is **not** label inflation.
It is *scope inflation inside the prose of a correctly-labelled row*: the number is
right, the label is right, and the noun the number attaches to has quietly widened —
one window becomes "the drift" (1634), a bounded profile becomes "anywhere" (1587),
`--srgb` becomes unqualified (1589/1593), one stack becomes n=8 (1658), a rival
experiment's bound becomes this one's (1658). **A label audit would have caught none
of these eight.**

---

## 8. Exact replacement text

Single line each, no unescaped `|`, attributed to V-FOLD. Drop into the fourth column.

**1568** (also change column 2 to `MEASURED` → keep; the numbers change):

`**sRGB IS CROSS-CHANNEL CONTAMINATED, AND THE CORPUS QUOTED THE WRONG MATRIX FOR IT.** `camera_to_srgb` is `inv(rownorm(A @ S))` -- normalise **then** invert (`crates/strehl-core/src/color.rs:191-204`) -- not `rownorm(inv(A @ S))` as M113 §1, `c8_linear.py:11-12`, `fold125.py:43-44` and this row previously stated. Both variants have unit row sums, so the crate's own row-sum test and M113's offered `neutral_response` check (invariant to normalisation order) **cannot separate them**. Corrected rows: R `+1.6361 / -0.4486 / -0.1874`, G `-0.1152 / +1.4890 / -0.3738`, matching `color.rs:221`'s doc comment and `experiments/M110-sheet/ca_matrix_prereg.py`, which printed the disagreement and was not folded. **Green-into-red is 27.4 % (not 10.4 %) and red-into-green is 7.7 % (not 20.3 %)** -- the load-bearing coefficient for an R-G displacement was overstated **2.6x**. The conclusion that sRGB is unfit for measuring survives and is reinforced; the quantities were wrong. Corrected by V-FOLD against `color.rs` and an independent numpy derivation.`

**1571**:

`**THE RADIAL SHAPE IS FLAT, TO +/-15 ppm, ON THE BETTER-CONDITIONED STACK.** `eps(r)` on `couch-fibers-cpl` reads -677 / -660 / -647 / -649 / -655 / -662 / -670 ppm across r = 0.11 to 0.87 -- a half-range of exactly 15 ppm. Residuals after the shipped correction are 132.3 ppm (25 % of 529.9) on `bee-3-cpl` and 36.5 ppm (5.6 % of 654.9) on `couch`; the outside/inside ratio is 1.01278 over 111 windows. **Bootstrap sd is 8-23 ppm only for r >= 0.24; the innermost ring (r = 0.11) has sd 80.0 ppm**, over 3x that, so the flatness is established on the outer six rings and not on the seventh. Innermost-ring sd restored by V-FOLD from `C:\dev\strehl-out\M113-ca\c10_rings.json`.`

**1587**:

`**THE CA CORRECTION SHOWS NO DISCONTINUITY AND NO UPWARD TREND PAST ITS SUPPORT RADIUS -- WHICH IS NOT THE SAME AS NO OVERSHOOT.** Radial width rates run 9.73 / 9.78 / 9.47 inside and 14.22 / 13.68 / 11.66 outside, with no step at the boundary: M110 §16.2's actual claim, and it holds. **But `overshoot_pct` in `ca_overshoot_default_vs_ca.json` reaches 18.82 %**, and the "0.00 %" null quoted here is the trivial off-vs-off control M110 itself labels "identical input" -- the artefact's real `overshoot_inert_null` runs **4.68 % to 25.73 %**. Real-minus-null excess on `bee-3-cpl` **rises** across the support boundary: +2.93 / +3.88 / +4.59. The previous headline "NO OVERSHOOT ANYWHERE" was ORCH's generalisation, not M110's finding. Narrowed by V-FOLD against `C:\dev\strehl-out\M110-sheet\ca_overshoot_default_vs_ca.json`.`

**1589**:

`**61.0 % AND 58.7 % LESS EDGE-LOCALISED CHROMA EXCESS -- MEASURED IN `--srgb`, WHICH THIS PROJECT'S OWN `--help` FORBIDS FOR MEASURING.** The arithmetic is exact and V-FOLD re-derived it from raw band DN: 61.0 % = (472.2 - 1209.6)/1209.6 and 58.7 % = (995.5 - 2411.7)/2411.7, with edge contrasts moving 2.4511 -> 1.9313 and 1.6309 -> 1.2719. **`experiments/M110-sheet/sheet.py:262` shows every M110-sheet render is produced with `--srgb`** -- "For looking at, NOT for measuring" (`main.rs`), a space M113 measured at chain transfer 1.3073 and found cross-channel contaminated. A chroma-excess statistic is exactly the statistic a cross-channel operator moves, so the magnitude is not yet established in a measurement space. **`crates/strehl-raw/src/identity.rs` quotes these two numbers as "the project's best-measured quality win" and inherits the same missing qualifier.** Qualifier added by V-FOLD.`

**1593**:

`**THE CA PROFILE REMOVES EDGE-LOCALISED CHROMA EXCESS, BY AN AMOUNT NOT YET MEASURED IN A MEASUREMENT SPACE.** The wording "edge-localised chroma excess against a baseline five pixels away" is correct and is what the statistic measures -- it is not "chroma removed". **But every render behind it was produced with `--srgb` (`experiments/M110-sheet/sheet.py:262`)**, the space `--help` marks "For looking at, NOT for measuring" and M113 measured as cross-channel contaminated. The effect's existence is established; its size in linear camera-native space is not. **This row is cited from `crates/strehl-raw/src/identity.rs`, which repeats the unqualified figure.** Qualifier added by V-FOLD.`

**1634**:

`**THE DRIFT IS A SMOOTH TREND, NOT FRAME-TO-FRAME SCATTER -- ESTABLISHED AT ONE WINDOW OF SIX.** At window (2832, 400) a straight line in frame index removes **91.8 %** of the drift's variance, leaving a residual sd of **0.449 %** of level -- which is what a fitted per-frame gain removes, where scatter would not be. **`level_drift_budget.py` computes this fit for that window only**; the other five windows are not tested, so the shape claim is n=1 and does not yet generalise. **The clause "monotone across the whole bracket (19624 counts at f120 falling to 18322 at f208)" is not produced by that script and V-FOLD could not locate it in any artefact or script output; treat it as UNSOURCED until re-derived.** Scope corrected by V-FOLD by re-running `experiments/ORCH-drift-check/level_drift_budget.py`.`

**1641**:

`**THE SOFT GATE'S TEXTURED CONTROL IS NOT A CLEAN CONTROL, AND THE WINDOWS ARE NOT HELD FIXED ACROSS ARMS.** All medians reproduce exactly (tweezers 0.5533 / 0.5622 / 0.5444 for A2/A3/A4 against 0.7102 for A1; bee 0.8078 / 0.8188 / 0.8092 against 1.0638), as do the control figures: on `bee-3-cpl` the gaussian soft gate cuts window (2832,1552) by **30.5 % (500.8 -> 348.0)**, as large as its effect on that subject's smooth windows (0.851 / 0.673 / 0.813), while photometric's textured windows read 1.037 (bee) and 1.027 (tweezers). **The claim of "identical windows across arms" is REFUTED**: both `photometric_ab.py` and `switch_gate.py` select from the **symmetric mean of A0 and the test arm**, so the pool is arm-dependent by construction -- brightness bars differ per arm (bee 9586 / 9492 / 9498 / 9528) and the tweezers pools genuinely differ, A1 holding (400,912) where A2 holds (1680,400). Verified and corrected by V-FOLD by re-running both scripts.`

**1658**:

`**FOUR RIVAL EXPLANATIONS DIED ON EXISTING DATA, AND TWO OF THEM DIED ON EXIF ALONE.** Aperture and the teleconverter: **every `-cpl` stack in the corpus is f/5.6 on `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter` at 200 mm**, so no aperture *ladder* and no converter contrast exist -- **but two f/8 stacks do exist (`coffee-bean`, `foam`), both non-CPL and both confounded with subject, so aperture is not literally absent from the library, it is unusable.** Magnification and focus distance: `bee-1-cpl` reads **536.2 ppm** (`s3_analyse.json`, `eps_R_off = -0.000536168`), **3.5 ppm** from the mean of bee-2 and bee-3 but **118.7 ppm** from `couch-fibers-cpl` at an identical `focus_m = 0.2841`. A common scale error: refuted, CV of B/R **14.9 %** against 24.7 %. **The clause "subject radial structure: refuted to +/-15 ppm" is withdrawn from this row: +/-15 ppm occurs nowhere in `M113-spectral.md` -- it is the ring half-range from `M113-ca` on `couch-fibers-cpl` alone (n=1), a different experiment, and does not carry this row's n=8.** Corrected by V-FOLD against `C:\dev\strehl-out\M113-spectral\s3_analyse.json` and `docs/research/M113-spectral.md`.`

**Currency notes — not fold errors, but both rows are false as written today:**

**1579** append: ` **[V-FOLD, currency] An eighth gate now exists: `STREHL_ROBUST_ELECTION` (`crates/strehl-core/src/merge.rs:508`), also off by default. It landed at `e028113` 2 h 28 m after this fold, so the row was correct when written; the count is now 8, and the "exactly ONE on by default" conclusion is unchanged and slightly reinforced.]`

**1592** append: ` **[V-FOLD, currency] SUPERSEDED BY M119. `crates/strehl-raw/src/identity.rs` (`43cee3b`, 1 h 53 m after this fold) reads `T_MAKE = 0x010f`, `T_MODEL = 0x0110`, `T_MAKER_NOTE = 0x927c`, `LensInfo 0xa432`, `FocalLength 0x920a` and `MaxApertureValue 0x9205`, and exposes `lens_model`, `lens_type3`, `focal_len_mm`, `f_number` and `max_aperture_f`. The row was true when folded. **The dispatch gap it describes is still real** -- identity is parsed, profile selection is still only a hand-typed `STREHL_FIX_CA`.]`

---

## 9. What I would tell ORCH to change about the fold

Not a refactor — a defect pattern, stated once. Seven of the eight defects are the
**same defect**: a number was carried across correctly and the *noun it attaches to*
widened during summarising. One window → "the drift". A bounded radial profile →
"anywhere". `--srgb` → unqualified. n=1 in experiment A → n=8 in experiment B. Six
rings → seven. An arm-dependent pool → "identical windows". Tonight's six were the
same shape: a synthetic arm → "the real occluding scene", a 700x1100 ROI → "the
shipped frame", M86's warp → M87's.

**Every one of those widenings makes the claim larger. None makes it smaller.** That
is not a folding style, it is a gradient, and it does not require any intent to
explain — a summariser under length pressure drops qualifiers, and qualifiers are
almost always the thing that makes a claim narrower. The asymmetry is structural,
which is why it is 14:0 and not 8:6.

---

## 10. Scope statement

**25 of 106 facts audited** to artefact level. **81 not audited**, and I make no claim
about them. The sample is biased toward number-dense, code-cited and self-sourced
rows. Facts audited: 1567, 1568, 1569, 1570, 1571, 1572, 1573, 1579, 1587, 1588, 1589,
1592, 1593, 1594, 1633, 1634, 1635, 1637, 1641, 1644, 1645, 1646, 1650, 1651, 1658.

Scripts: `experiments/V-FOLD/`. Nothing under `crates/` was modified;
`docs/research/SYNTHESIS.md` was not edited.
