# M110 — track jitter: can a roughness prior fix it, and does anyone see it?

**Question.** M103 measured (fact 1435) that the alignment solve's per-frame
placement track carries a median second-difference jitter of **0.4829 px** on
`bee-3-cpl`, ~110x what real track curvature can explain, with **13.8%** of
adjacent frame pairs disagreeing by **>= 1 px**. Fact 1393 says the merge elects
a single frame per pixel in detailed regions (`n_eff = 1`), so two adjacent
output pixels electing frames `j` and `j+1` inherit inconsistent placements.
The proposed mechanism for the owner's "waxy blob" complaint is therefore *local
geometric incoherence*, not softness.

**Answer, in one line.** The prior works exactly as derived, removes exactly
what it was aimed at, passes every accuracy and robustness bar — and **changes
nothing a viewer can see**. Shipped behind `STREHL_SMOOTH`, **off by default**.

---

## 0. The finding that reframes the brief

The orchestrator's brief asked me to *add* a second-difference roughness penalty
to `solve_global`. **It is already there.** `GlobalOptions::smooth`
(`align.rs:1767`) has emitted `[1,-2,1]` penalty rows since M86
(`align.rs:2088-2110`). It defaults to `0.0` and **no product path sets it**.

So the real work was never "add an operator". It was:

1. find out why an operator that already exists was never turned on, and
2. supply the one thing it lacked — **robustness** — and the one thing nobody
   had measured: **whether the win is visible**.

Two corrections to the brief, both MEASURED:

- **The 6.758-6.76 px held-out figure is a `coffee-bean` number** (M86 §G0), not
  `bee-3-cpl`. Quoting it against a `bee-3-cpl` solve would be a gauge error.
  The correct `bee-3-cpl` baseline, measured here and confirmed by the product
  binary itself, is **13.578 px**.
- **Fact 1181's +65% does not reproduce.** M86 P20 reports `smooth = 0.02`
  costing +65% held-out on `bee-3-cpl`. On the shipped edge set I measure
  `lambda = 0.02` at **13.5773 px** against **13.5776 px** free — a change of
  **-0.002%**. See §7; this needs adjudication by the orchestrator.

---

## 1. Pre-registered bars

Registered in `experiments/M110-track-jitter/PREREG.md`, commit `0889b95`,
**before any measurement**. Amendment A1 (grid width only, no bar changed) was
committed in `9aefcc6` after B0 and before any `lambda > 0`.

| bar | registered threshold | result |
|---|---|---|
| B0 | reproduce fact 1435 median `0.4829 +/- 0.0001` px | **PASS** |
| B1a | `1196/1196` f64 words equal, `0` differing | **PASS** |
| B1b | one penalty row at weight `1e-12` must turn B1a RED | **FAIL as registered** (see §3) |
| B2 | `heldout(lambda*) <= 1.02 * heldout(0)` | **PASS** (0.983x) |
| B3 | median jitter `<= 0.2415` px (>= 2.00x reduction) | **PASS** (0.2112 px, 2.29x) |
| B4a | recovered `<= 0.50x` planted, and within `+/- 20%` of derived `H(pi)` | **PASS** (0.200x, -0.27%) |
| B4b | step recovery `>= 90%`, `<= 5` frames off by > 0.5 px | **PASS** (96.14%, 0 frames) |
| B5 | `rho_1 <= 0` **and** power above `pi/2` `>= 0.5` | **PASS** (-0.599, 0.838) |
| B5 power control | step plant + non-robust must read `rho_1 > 0` | **FAIL as registered** (see §6) |
| B6 | visibility, run only if B1-B4 pass | **INVISIBLE** |

Two registered items failed. Neither is relaxed below; both are reported as
findings, which is what discipline 710 asks for.

---

## 2. The design, and why it beats the parametric alternative

MEASURED-then-DERIVED. In the log domain the solve is
`min ||D x - y||^2 + lambda^2 ||L x||^2`, `D` the edge rows, `L` the `[1,-2,1]`
stencil. For a mode of wavenumber `w`:

```
H(w) = |D v|^2 / ( |D v|^2 + lambda^2 |L v|^2 )
```

At `w = pi` **every even span is blind** — `sin(pi s / 2) = 0` for even `s` — so
the data term is carried by the 298 span-1 edges alone:

```
H(pi) = 1192 / (1192 + 4752 lambda^2) = 1 / (1 + 3.987 lambda^2)
```

**P1 (DERIVED, then MEASURED to <= 0.54%).** This is a *frequency-selective*
operator. At `lambda = 3` it retains **0.027** of the Nyquist mode and **0.93**
of a 10-frame-period mode — a **34x** separation. A degree-6 polynomial is a
hard rank constraint: it cannot express that separation at all, which is exactly
why fact 1 caught it deleting real structure and why fact 47 priced its win at
"~6%, inside the noise". **The two error budgets are separable, and a spectral
prior separates them; a parametric solve cannot.**

I therefore did **not** wire `solve_poly`, and §7 shows the stiff limit of my own
operator reproducing fact 1's failure quantitatively.

### The change I made

`GlobalOptions::smooth_huber_px: Option<f64>` (`align.rs`), defaulting to `None`.
When set, the penalty rows carry IRLS weights recomputed each pass from the
second difference measured **in the solver's own metric**,
`sqrt(rho^2 |d2 a|^2 + |d2 b|^2)` — which is `corner_err_rms` of the stencil, so
the threshold is in plane px and directly comparable to `huber_px`. Threshold
**1.0 px**, chosen from fact 1435's published p90 of 1.0772 px (so ~90% of
observed second differences stay quadratic and only the tail is capped) — a
principled choice, not a tuned one.

**Approximation, ARGUED with a bound.** The code penalises `d2 A`, not
`d2 ln A`. For `|A| ~ 1 +/- 0.05` these agree to <= 5%. Keeping `d2 A` preserves
linearity, which is what makes B1's bit-exactness argument possible at all.

---

## 3. B1 — the null control, and the control that had to be broken twice

**B1a: PASS.** Three independent limbs, each a hard gate that exits non-zero:

| limb | words | differing |
|---|---|---|
| after my change vs before it, `lambda = 0` | 1196 | **0** |
| after my change vs M103's committed baseline | 1196 | **0** |
| `lambda = 0` **with** `smooth_huber_px = 1.0` set | 1196 | **0** |

**B1b: FAILED AT ITS REGISTERED VALUE — and that is the finding.** I registered
a `1e-12` penalty row. It produced a **bit-identical** result. So did `1e-10`
and `1e-9`. The control only fires at **`1e-8`**:

| sabotage amplitude | differing words | control |
|---|---|---|
| `1e-12`, `1e-10`, `1e-9` | 0 | **blind** |
| `1e-8` | 823 | fires |
| `1e-6` | 973 | fires |
| `1e-4`, `1e-2` | 1195 | fires |

**P2 (MEASURED).** The B1 bit-equality gate has a detection floor near
`1e-8` in relative penalty weight. Below it a perturbation is genuinely below
the f64 resolution of the normal equations, not merely "small".

This is not a defective control; it is a control whose sensitivity I asserted
instead of measuring. Registering `1e-12` was a pre-registration defect. The
control **is** valid and **was** shown to fail: the smallest `lambda` I use
anywhere (0.02) sits **2 x 10^6** above the floor, and `lambda* = 1` sits
**1 x 10^8** above it.

Sabotage was applied and removed via a `$env:TEMP` copy with an explicit
`LastWriteTime` touch; the rebuild after restore recompiled `strehl-core` and
re-verified 1196/1196 equal with the sabotage env var still set (inert).

### 3.1 Exit-code integrity of the B1 gate (audit against fact 1443)

Fact 1443 refutes the prior belief that "a PASS taken from an observed nonzero
exit code is safe": under Windows PowerShell 5.1 the `-First` corruption value
is `-1`, so a red control shaped as `if ($code -ne 0) { pass }` passes on the
artifact it exists to detect. I audited every arm above against it.

**No arm needs re-measuring, for three independent reasons (MEASURED):**

1. **No `$LASTEXITCODE` read in this milestone follows a filtered pipeline.**
   Every arm assigns command output to a variable, reads the code on the very
   next statement, and filters the variable afterwards — the pattern rule 47
   prescribes.
2. **Every arm records a literal value** (`exit=$c`), never a predicate. No
   `if ($code -ne 0)` was written anywhere in this milestone.
3. **The gate carries a discriminator that does not depend on the exit code
   at all.** `cmp` prints `differing N`; B1a was scored on `differing 0` and
   B1b on `differing 823`. Content, not status.

Point 3 is the load-bearing one, and it also settles the direction of any
residual risk. In the agent shell the corruption value is `0`, so corruption
can only turn a genuine `1` into `0` — it can only make a **red** arm look
green, never a green arm look red. My red arms were observed at **`1`**, a
value this host's corruption cannot manufacture.

I nonetheless re-exercised both paths of the gate under the assertion form
fact 1443 prescribes — an assertion on the **exact** expected code, not on
non-zero-ness — on tracks known to differ and known to match. No rebuild and
no sabotage were required, because the failure path is the same code path:

| path | assertion | result | corroborating content |
|---|---|---|---|
| RED (`track-l0` vs `track-l1-robust`) | `if ($code -ne 1) { throw }` | **held** | `differing 1196 -> FAIL` |
| GREEN (`track-l0-BEFORE` vs `-FINAL`) | `if ($code -ne 0) { throw }` | **held** | `differing 0 -> PASS` |

Both pre-cleared with `cmd /c exit 0` first, per rule 47's note that stale
values produce false negatives.

---

## 4. B2 and B3 — accuracy and the target quantity

`lambda* = 1`, robust, Huber 1.0 px. Baseline is `lambda = 0`.

| quantity | `lambda = 0` | `lambda* = 1` | change |
|---|---|---|---|
| held-out median corner error | 13.5776 px | **13.3529 px** | **0.983x** |
| jitter median | 0.4829 px | **0.2112 px** | **2.29x down** |
| jitter p90 | 1.0772 px | 0.5261 px | 2.05x down |
| jitter max | 9.7069 px | 6.9057 px | 1.41x down |
| adjacent pairs `>= 1 px` | **13.80%** | **0.67%** | **20.5x down** |
| near-reference median / max | 0.4464 / 1.7045 | 0.2049 / 0.9150 | 2.18x / 1.86x |
| far-from-reference median / max | 0.6259 / 9.7069 | 0.2516 / 6.9057 | 2.49x / 1.41x |
| corner `d2` median (A+B) | 0.9981 px | 0.4831 px | 2.07x down |
| corner `d2` max (A+B) | 12.9560 px | 8.9303 px | 1.45x down |

**B2 PASS** at 0.983x against a 1.02x bar. Held-out does not worsen at *any*
`lambda` up to 300. A paired bootstrap on the same test edges gives
`delta = -0.208 px, SE 0.0945, z = -2.20`.

> **Honest limit.** The test set is **23 edges**. `z = -2.20` on 23 edges is weak
> evidence. I claim **"does not worsen"**, which the bar asks for. I do **not**
> claim the prior improves accuracy, though every point estimate says so.

> **Second honest limit.** Held-out tests on spans `>= 40`, which probe
> *low-frequency* structure. B2 is a strong guard against the fact-1 failure
> (deleting real smooth geometry) and a **weak** guard against high-frequency
> over-smoothing. B4b, not B2, is the bar with power there.

**B3 PASS** at 0.2112 px against a 0.2415 px bar.

**P3 (MEASURED).** The fraction of adjacent frame pairs whose placements
disagree by `>= 1 px` falls from **13.80% to 0.67%** — a **20.5x** reduction.
This is the quantity the election-boundary mechanism actually depends on, and it
moves far more than the median does.

> **The tension I must report.** The robust prior *deliberately* leaves the far
> tail alone: max jitter 6.91 px robust vs **2.91 px** with a purely quadratic
> prior at the same `lambda`. Robustness means declining to flatten a 9.7 px
> excursion, because the solver **cannot distinguish a 9.7 px estimation error
> from a 9.7 px real tripod bump**. B3's tail win and B4b's step survival are in
> direct conflict, and I chose B4b. A regulariser that erases real motion must
> not ship (the brief's words, and I agree).

---

## 5. B4 — the two-sided positive control

**B4a PASS, and it confirms a prediction stored before the run.** Planted
`+/- 0.5 px` alternation on a truth track carrying `bee-3-cpl`'s real degree-4
curvature (fact 1410 forbids a linear plant):

| lambda | recovered | ratio | derived `H(pi)` | rel. error |
|---|---|---|---|---|
| 0 | 0.50005 px | **1.00010** | 1.00000 | +0.01% |
| 0.5 | 0.25003 px | 0.50005 | 0.50084 | -0.16% |
| **1** | 0.10000 px | **0.20000** | 0.20054 | **-0.27%** |
| 3 | 0.01355 px | 0.02710 | 0.02712 | -0.05% |
| 5 | 0.00499 px | 0.00999 | 0.00993 | +0.54% |

Bar was `+/- 20%`; worst observed is **0.54%**, a **37x** margin, across a 100x
attenuation range. `lambda = 0` recovers the plant at **100.01%**.

> **A bug I found by disbelieving my own first number.** My first B4a run read
> 0.484x at `lambda = 0`, where it must read 1.0 on noiseless edges. The solve
> was exact (max deviation **0** px); the *estimator* was wrong. Projecting onto
> `(-1)^j` is not trend-immune: over an odd frame count `sum_j (-1)^j j = 149`,
> not 0, so a linear carrier leaks in at ~0.498 of its per-frame slope and
> swamped the plant. Replaced with a second-difference projection, which
> annihilates constant and linear exactly.

**B4b PASS, and the negative control does its job.** Planted **10.0 px** genuine
step at frame 150, `lambda = 1`:

| penalty | step recovered | frames off by > 0.5 px | max deviation | verdict |
|---|---|---|---|---|
| purely quadratic | **77.16%** | 2 | 1.2567 px | **FAILS the 90% bar** |
| **robust, Huber 1.0 px** | **96.14%** | **0** | 0.2128 px | **PASS** |

**P4 (MEASURED).** The robustness change is **load-bearing, not decoration**: at
the operating point it moves step survival from 77.16% to 96.14%. The quadratic
arm fails the registered bar, so B4b has genuine power — it is not a bar that
passes by construction. At `lambda = 2` and `3` the robust prior also degrades
(83.50%, 61.75%), which independently argues for `lambda* = 1`.

---

## 6. B5 — the fact-1 falsifier

Removed signal `r(j) = ln|A_0(j)| - ln|A_1(j)|`, mean and linear trend removed.

| arm | rms | lag-1 autocorr | power above `pi/2` | reading |
|---|---|---|---|---|
| `lambda* = 1`, robust | 0.1411 px | **-0.5994** | **0.8375** | **NOISE** |
| power control, `lambda = 3000` | 4.5746 px | **+0.9678** | 0.0038 | SMOOTH |
| **registered** control: step plant, non-robust | 0.0972 px | **-0.6197** | 0.8995 | NOISE |

**B5 PASS on its registered reading**: `rho_1 = -0.599 <= 0` and
`0.8375 >= 0.5`. What the prior removed at `lambda* = 1` is **estimation error,
not geometry** — the outcome fact 1 demands.

**The registered power control FAILED, and this is a real finding.** I
registered that the step plant solved with a non-robust penalty must read
`rho_1 > 0`. It reads **-0.6197**. My registered assumption was wrong: a
second-difference prior's response to a step is a **localised oscillatory
kernel**, not a smooth blob, so genuine localised damage reads as "noisy".

**P5 (MEASURED).** B5's smooth-vs-noisy statistic detects **broadband**
over-smoothing and is **blind to localised damage**. It is a weaker falsifier
than I registered it as. B4b is the bar that catches localised damage, and it
did — 77.16% on exactly the arm B5 could not see.

I substituted a `lambda = 3000` power control **post hoc**; it reads
`rho_1 = +0.9678` and establishes that the statistic *can* say "smooth". That
substitution is flagged, not hidden. Per my own pre-registration, B5's power
against localised damage is reported as **not established**.

---

## 7. The stiff limit measures facts 1 and 47 directly

Pushing `lambda` to infinity drives the solve to the best straight line in frame
index (the null space of `[1,-2,1]`):

| lambda | held-out | jitter median |
|---|---|---|
| 0 | 13.5776 px | 0.4829 px |
| **0.02** (M86's value) | **13.5773 px** | 0.4826 px |
| 1 | 13.3292 px | 0.2050 px |
| 300 | 12.6589 px | 0.0015 px |
| 1000 | 14.7435 px | 0.0010 px |
| 3000 | 21.1209 px | 0.0002 px |
| 100000 | 21.8764 px | 0.0001 px |

**P6 (MEASURED).** The fully-stiff (straight-line) limit costs **21.99 px vs
13.58 px free — +61.9%** held-out on `bee-3-cpl`. This confirms fact 1's "no
low-order polynomial in frame index matches a direct per-frame fit"
quantitatively, and prices fact 47's observation that a straight line captures
93.9% of corner motion: that missing 6.1% is worth **+62% of held-out error**.

**P7 (MEASURED, needs adjudication).** `smooth = 0.02` — the setting fact 1181
prices at **+65%** held-out on `bee-3-cpl` — measures **13.5773 px vs 13.5776 px
free, a change of -0.002%**, on the shipped span ladder using M103's committed
edge dump. The derivation explains why it *must* be a no-op: `H(pi) = 0.9984` at
`lambda = 0.02`. Either M86's S6 row used a different training set than its
label implies, or fact 1181 needs re-measurement. **I could not resolve this** —
see §10.

---

## 8. B6 — is it visible? No.

Two full 299-frame `bee-3-cpl` renders, identical in every respect except the
sidecar. Both arms align and resample identically, so fact 1436's -33.0%
resample confound cancels exactly. No auto-levels, no exposure change, default
gate 4.0. Sidecars written to my own scratch; **the capture library was verified
clean afterwards.**

- Arm A: `STREHL_SMOOTH` unset. Product reports held-out **13.578 px**.
- Arm B: `STREHL_SMOOTH=1 STREHL_SMOOTH_HUBER=1.0`. Product reports **13.353 px**.

Both match my probe (13.5776 / 13.3529) to the printed precision — an
independent cross-check of the harness against the shipping binary.

**The naive difference is large and entirely misleading.** 40.1% of pixels
differ by `>= 1` display level, max 119.6 levels. But phase correlation shows the
arms differ by a **global translation of 0.5712 px** — turning the prior on
moves the whole output. Integer-only registration (the brief's requirement, and
correct: sub-pixel resampling would blur the quantity under test) leaves ~0.43 px
of global offset, which dominates every local difference. **A difference image
between these two panels measures the gauge shift, not the jitter.**

The only trustworthy comparison is shift-invariant scalars:

| metric | A (baseline) | B (prior) | B/A |
|---|---|---|---|
| centre high-band fraction (> 0.25 Nyquist) | 0.006123 | 0.006139 | **1.00256** |
| centre Laplacian variance | 583120 | 583668 | **1.00094** |
| whole-frame Laplacian variance | 422904 | 421265 | **0.99613** |
| `\|grad\|` p99 | 19920.6 | 19926.3 | 1.00029 |
| `\|grad\|` p99.9 | 31756.6 | 31842.2 | 1.00269 |

**P8 (MEASURED). The jitter is not visible.** Every shift-invariant metric
agrees between arms to within **0.6%**, and **the sign is not even consistent**:
centre metrics say the prior is 0.1-0.26% *sharper*, the whole-frame metric says
0.39% *softer*. An effect whose sign flips between metrics is below the noise of
those metrics.

For scale: fact 1436 measured the aligned path costing **-33.0%** of centre
high-band energy. The prior's effect is **+0.26%** — **127x smaller** than a
confound the project already knows about and tolerates.

**P9 (ARGUED, from P8 + fact 1393).** A 2.29x reduction in solve-side jitter and
a 20.5x reduction in `>= 1 px` adjacent-pair disagreement produce **no measurable
change in rendered sharpness or edge structure**. Either the "waxy blob"
mechanism is not driven by track jitter, or the merge is far less sensitive to
inter-frame placement disagreement than fact 1393 suggests. **M110 does not
distinguish these**, and the blob hypothesis is neither confirmed nor refuted —
only shown not to be fixed by this.

### 8.1 Cache-contamination control (fact 1446)

Fact 1446 reports that `StackIdentity` omits `reference` and `resampler`, so a
cached sidecar can hand an arm bytes produced under inputs it did not ask for.
B6 is exactly the class of comparison this corrupts, so I ran the control ORCH
prescribed. Harness: `experiments/M110-track-jitter/cache_control.ps1`.

**Scope first (MEASURED).** Only B6 is exposed. B0–B5 run in
`experiments/M110-track-jitter/probe`, which reads its inputs solely through
`std::fs::read_to_string` on committed text — M103's edge CSV and my own track
dumps. It never calls `WarpMap::load` or `StackIdentity::from_paths`, never
decodes a RAW, and consults no cache. **Those bars cannot be contaminated by
this defect.**

**The control, run on the full 299-frame stack:**

| step | command | exit | output sha256 (first 16) |
|---|---|---|---|
| 1 | `merge` arm B, `STREHL_WARPMAP=wm-B.json` | 0 | `834FB50773BEA993` |
| 2 | `align --reference 40` (**same frame set**) | 0 | — |
| 3 | `merge` arm B, byte-identical to step 1 | 0 | `834FB50773BEA993` |

**PASS — step 1 == step 3, byte-for-byte.** The intervening command changed
`reference` on an *identical* frame set, which is precisely the collision fact
1446 describes. Both arms logged `alignment : ON (sidecar-override), reference
frame 0, 299 placed / 0 refused`. The capture library held at **0** non-ARW
files before and after.

**Why the arm is immune, confirmed in code.** `alignment_for`
(`merge_cmd.rs:1046`) returns `load_or_solve` **only** when `STREHL_WARPMAP` is
unset; when set it loads the named path and uses `check_stack` as a *guard*, not
a *selector*. B6 named its sidecar explicitly, so no cache lookup occurs.

**And the two arms never differed in the unkeyed fields anyway.** Both sidecars
self-report `reference 0` and `resampler catmull-rom`; their `heldout-px` fields
decode to **13.5776** and **13.3529**, matching the probe exactly. Their
`stack-digest` is **identical** (`8d023c0fe355d109`) — a direct demonstration of
fact 1446's defect in my own data: the digest cannot tell these two sidecars
apart. It did not matter here only because selection was explicit.

**P10 (MEASURED) — a separate reproducibility hazard, not a cache one.** Step 1
did **not** reproduce the archived `B-prior.tif` (`89C2025A…` vs `834FB507…`).
The cause is not the cache: `strehl.exe` was rebuilt at **13:06:35**, eight
minutes *after* the B6 renders at **12:57:32** and **12:58:35**, and the merge
path has since changed under me — `merge_cmd.rs` is currently uncommitted-modified
by another agent, `merge_cmd/dump.rs` is new, and the re-run prints an M97 caveat
line absent from the original. **In a shared working tree, an archived render
stops being reproducible because other milestones mutate the render path.** This
is distinct from fact 1446 and is reported to ORCH as such.

**B6 re-tested on a contemporaneous pair.** B6's claim is *relative*, and the
original arms were rendered back-to-back on one binary with nothing in between
— the clean protocol. I nonetheless re-rendered **both** arms on the current
binary and recomputed shift-invariant scalars
(`experiments/M110-track-jitter/recheck_b6.py`):

| quantity | original (12:57/12:58) | re-run (current binary) |
|---|---|---|
| arms byte-distinct | yes | yes |
| centre high-band, B vs A | +0.26% | **+0.031%** |
| whole-frame high-band, B vs A | -0.39% | **+0.172%** |

**The conclusion is reproduced and slightly strengthened**: the difference is
*smaller* than originally measured, and remains ~190x and ~590x below fact
1436's known -33.0% resample cost. B6's verdict — **invisible** — stands. (The
two rows use different high-band operators, so compare verdicts, not digits.)

---

## 9. Recommendation: **ship behind a flag, off by default**

Implemented as `STREHL_SMOOTH` (with `STREHL_SMOOTH_HUBER`, default 1.0 px),
read at both product solve sites in `align_cmd.rs`. Unset, the code path is
**bit-exact** with today's (B1a, 1196/1196).

**Why not on by default.** B6 is the whole argument. The solve-side wins are
real, pre-registered and reproducible, but nobody can see them, and the project's
own rules say a default must earn its place with evidence. Turning this on by
default would change every rendered pixel (via a 0.571 px gauge shift), invalidate
byte-frozen comparisons across the corpus, and buy **+0.26%** on a metric whose
sign is not stable — while the pipeline already gives up **33%** elsewhere.

**Why ship it at all.** Three reasons, all measured: (1) it costs nothing when
off; (2) the mechanism is now understood analytically and confirmed to 0.54%, so
a future milestone that *does* find a visible artefact has a calibrated tool
ready; (3) M86 §13.5 found `smooth` **wins** on `foam`, the stack with the weakest
edge set — and the span-starved regime is exactly where the prior should dominate.
**`foam` was not tested here** and is the obvious next experiment.

---

## 10. What I could not verify, and loose ends

1. **Fact 1181 (+65% at `smooth = 0.02`) does not reproduce** — I measure
   -0.002% (P7). I did **not** re-run M86's S6 configuration to find the
   discrepancy; my run used M103's committed edge dump filtered to the shipped
   ladder, which may differ from M86's training set. **Needs adjudication.**
2. **Only one stack.** Everything here is `bee-3-cpl`. `foam` — where M86 says
   `smooth` wins, and where the mechanism predicts the largest effect — was not
   tested at all.
3. **B2's test set is 23 edges.** The "no regression" conclusion is sound at the
   registered bar; the apparent *improvement* is not established.
4. **B5 has no established power against localised damage** (P5), by my own
   pre-registration's rule. Its `lambda = 3000` power control is post-hoc.
5. **B1b failed at its registered `1e-12`**; the control is demonstrated at
   `1e-8`. The registered value was a pre-registration defect, not a code defect.
6. **The 0.571 px global gauge shift between arms was not itself explained.** It
   is consistent with the prior re-seating the whole track, but I did not verify
   that, and it is the reason a difference image is uninterpretable.
7. **No perceptual test.** B6 is instrument metrics on a full-frame render plus
   one high-detail crop. Nobody looked at the two panels side by side and gave a
   verdict; the crops are at `C:\dev\strehl-out\M110\img\AB-crop-sbs.tif`
   (uncommitted, outside the repo).
8. **`d2 A` vs `d2 ln A`** (<= 5% for `|A| ~ 1 +/- 0.05`) is DERIVED, not
   measured on this stack.
9. **The Huber threshold of 1.0 px was not swept.** It is justified from fact
   1435's p90, not optimised. `lambda` was swept; the threshold was not.
10. **Another agent's uncommitted `optics.rs` broke the shared tree mid-run.** I
    waited rather than touching it. If that file changes `strehl-core`'s
    behaviour, my product-path numbers (§8) may need re-running.
11. **The archived B6 TIFFs are no longer reproducible** (P10) — the binary was
    rebuilt 8 minutes after them and the merge path has since changed. The
    *conclusion* was re-tested on a contemporaneous pair and holds (§8.1), but
    the specific archived bytes cannot be regenerated. A byte-frozen render in a
    shared tree has a shelf life measured in minutes.
12. **ORCH's note that `cargo clippy -D warnings` fails at `align.rs:2108`
    (`pen_w`) is a misattribution — it is not M110's.** Measured:
    `cargo clippy --release -p strehl-core --all-targets -- -D warnings` exits
    **101** with exactly four errors, none in `align.rs`:

    | location | lint |
    |---|---|
    | `strehl-core/src/optics.rs:416:27` | hex literal not grouped evenly |
    | `strehl-core/src/robust.rs:409:17` | useless use of `vec!` |
    | `strehl-core/src/robust.rs:451:17` | useless use of `vec!` |
    | `strehl-core/src/robust.rs:464:17` | useless use of `vec!` |

    `robust.rs` was last committed by **M93** and is currently
    uncommitted-modified by a live agent; `optics.rs` is not M110's either.
    M110's `align.rs` work is **committed** (`79264b6`), not uncommitted, and
    draws **no clippy diagnostic at all**. I did not fix these — not my lane.

---

*Every claim above is labelled MEASURED (from a run whose command is in the
experiment directory), DERIVED (from algebra stated in full), or ARGUED. The
harness is `experiments/M110-track-jitter/probe`, the pre-registration is
`experiments/M110-track-jitter/PREREG.md`, and the raw sweeps are in
`experiments/M110-track-jitter/data`.*
