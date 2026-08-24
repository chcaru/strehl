# M62 addendum — qualifying the M64 certificate after M66

**Revised verdict: `CERTIFY-CONDITIONAL`.**

The thesis-level finding stands unconditionally. **The headline number does not,
and I am withdrawing its unconditional form.** My `DEFAULT` arm's ±2 % window
tolerates a **2.5 % reduction in `n_eff`** (derived below); the σ_F effect M66
found and M69 is settling is **19–21 %**, measured *on my own plant*. My criterion
is roughly eight times tighter than the quantity under investigation, so I cannot
honestly leave `5.431624` standing as though σ_F were settled.

No re-run. This ruling is derived from M66's committed report, my own committed
post-hoc gate sweep at `53c8d47`, and a read-only check of `merge.rs` and
`main.rs`. I implemented nothing.

| claim from my ruling | status now |
| --- | --- |
| the default path **estimates rather than selects** | **unconditional** — robust to σ_F error up to ≈8× |
| `SELECTOR-same-binary` = 0.976815, battery retains power | **unconditional** — exactly σ-invariant, see §4 |
| A0 ladder / B1a / B1b instrument arms | **unconditional** — no gate, no σ_F |
| determinism, byte-identical | **unconditional at gate 4**, unmeasured at gate 0 |
| Q2 monotone-and-saturating; Q4 no static burst can arbitrate the gate | **unconditional** — structural, N- and σ-free |
| **`DEFAULT` = 5.431624, PASS at ±2 %** | **CONDITIONAL on M69** |
| **efficiency = 1.000076, PASS at [0.98, 1.02]** | **CONDITIONAL on M69** |
| **guard G's margin** | **stands as run, but G carries an undeclared N domain — my defect** |

---

## 1. Two corrections to the framing I was given

I was asked to rule on a summary. I read M66 first, because I was wrong once
before by accepting an orchestrator's generalisation unchecked (discipline 409),
and the summary differs from the source in two places that matter.

**"The guard margin you relied on is a quarter of what was published" compares
two different configurations.** M66's own words: *"That is not a failure; it is a
guard whose stated safety factor is 2.8× smaller than published once N is allowed
to vary."* The 1.12× is `bee-1` **at an N=19 prefix** — a subset. M66's table has
a second column, *at own N*, and there the worst case is `coffee-bean` at
**0.30137, margin 3.15×**, against M64's published 0.30109 / 3.16×. **Guard G as
I specified it asserts the full frame count of a named stack, so it runs in the
*at own N* column, and M64's figure is correct for the configuration G actually
runs in.** The 1.12× is a real and important finding about G's behaviour under
subsetting; it is not a restatement of the same measurement. (MEASURED, M66
fact 20.)

**M66 says its M-GUARD failures are G behaving correctly, not G failing.** Its
words: *"three consecutive frames of a through-focus stack sit at nearly the same
depth, so they* are *a static burst, and M62's Requirement G correctly reports
them as focus-degenerate."* I accept that reading and note it is the **measured
instance of a foreclosure I had already declared**: my discipline-433 audit at
`53c8d47` §5 said G *"genuinely forecloses a legitimate case — a stack with so
little focus variation that admitting nearly everything is correct would be
rejected."* I predicted the failure mode abstractly; M66 found the cells. That
is the audit working, and it does not rescue me from §3.

## 2. Q1 — is gate 4's N-dependence inside or outside the certificate?

**Outside what the `DEFAULT` arm measured, inside what guard G claimed, and I
should have declared it in neither case.**

The `DEFAULT` arm ran at **N = 30 and only N = 30**. My certificate never
quantified over N, so nothing in it is falsified. But my ruling listed four
things `CERTIFY` does not mean — calibration, focus-correctness, the gate value,
detail — and **N was not among them.** A reader is entitled to have read
"the shipped default is a correct estimator" as portable across frame counts. It
is not established across frame counts, and M66's fact 18 prices the
non-portability at 1.0577 through the real operator. **That omission is mine, not
M66's discovery about the crate**, and this addendum is where I fix it.

**Guard G is the part that genuinely inherits the defect M66 proved.** G is a
fixed 0.95 line against `n_eff/N`, a statistic whose null value drifts with N,
and **nothing in G's statement mentions N** — which is, word for word, the defect
M66 proved in `Gate::tolerance()`. My guard has the same shape of error as the
thing it was built to police. I state that plainly because G is my instrument and
nobody else's.

## 3. Q2 — does the guard's margin change my verdict?

**No, and the reason is not the one that would flatter me.**

G ran on full stacks with asserted frame counts, where the worst measured margin
is 3.15×. My verdict was issued on that configuration and it stands there.

But two things must be said against it. First, **G's safety factor is a function
of N and its statement does not say so**; anyone running G on a subset, a short
stack, or a future capture under N ≈ 19 gets a margin near 1.12× and may not know
the line has moved under them. Second, **my own scoping correction and M66's
N-dependence cancel, in my favour, and I want that on the record rather than
quietly banked.** I noted at `53c8d47` that the five unmeasured stacks are the
*largest*. Larger N drives `n_eff/N` *down*, so the omitted stacks carry *more*
margin, not less — M66 measures `bee-1` at its own N = 299 at 0.23479, a 4.05×
margin, better than the measured worst case. **The gap I flagged is in the safe
direction.** That partially retires my own correction, and I would rather say so
than leave a caution standing that the evidence has since removed (discipline
409's lesson, applied to myself).

**G still does the work I designed it for**: it distinguishes a merge that
discriminates focus from one that has stopped. What it does *not* do, and never
did, is hold a constant meaning across N. G needs a declared domain — as
specified, `N ≥ 19` — and does not have one.

## 4. Q3 — conditional on M69, and exactly which half

**The transfer function, stated so it steers nothing.** `tolerance() = threshold
· √2 · FOCUS_NOISE_SD` (`merge.rs:310–311`, read directly). Tolerance is *linear*
in σ_F, so **rescaling σ_F by a factor `c` is exactly equivalent to rescaling the
gate by `c`.** My committed post-hoc sweep at `53c8d47` is therefore already the
σ-sensitivity curve, and I can price this without re-running anything:

| effective gate | 0 | 0.5 | 1 | 2 | **4** | 8 | 16 | 64 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ratio | 0.9773 | 1.3616 | 1.9710 | 3.7610 | **5.4354** | 5.4849 | 5.4849 | 5.4849 |
| `n_eff` | 1.0 | 2.966 | 6.804 | 18.434 | **29.539** | 30.0 | 30.0 | 30.0 |

**What is conditional.** My window is `√30 · (1 ± 0.02)` = [5.36768, 5.58677].
At efficiency 1.000076 the floor corresponds to `n_eff ≥ 28.81`. Measured
`n_eff` is 29.539, so **the criterion tolerates a loss of 0.73 admitted frames
out of 29.539 — 2.5 %.** (DERIVED from measured quantities.) A 19–21 % rescale is
about eight times that headroom. The arm moves toward √30 for `c > 1` and away
for `c < 1`; the curve is steeply asymmetric about gate 4, being nearly flat
above and steep below. **I am not saying which way M69 will land, and the
certificate is conditional in both directions**, because a criterion whose
headroom is 2.5 % cannot adjudicate a 20 % question either way.

Efficiency is conditional for a subtler and worse reason. It is ≈1 only in the
*saturated* regime and dips to **0.7556 at gate 1** in my own sweep — selection
bias, documented in M62 §. So a downward rescale could push `DEFAULT` out of the
[0.98, 1.02] band **for a selection-bias reason rather than an estimator defect**,
and my criterion would report a failure that is not one. That is a second
foreclosure in my own criteria, found by applying discipline 433 to this
question, and it is owed work — **I am not widening the band, which would be
exactly the post-hoc rescue my §6 forbids.**

**What is unconditional, and why.** For `DEFAULT` to score like a selector the
effective gate must fall to ≈0, since even at gate 1 — a **4× σ error** — it
scores 1.9710 against the selector's 0.9773, and at gate 2 it scores 3.7610.
**σ_F would have to be wrong by roughly eight-fold to convert this estimator into
a selector.** A 19–21 % error is nowhere near it. The thesis — the default
averages rather than selects — is robust by more than an order of magnitude in
the offending parameter. (DERIVED.)

**The power arm is exactly invariant, not approximately.** At `--gate 0`,
`tolerance = 0 · √2 · FOCUS_NOISE_SD = 0` **identically, for any value of the
constant**. So `SELECTOR-same-binary` cannot move under any rescaling of σ_F, and
**the battery keeps its ability to fail through any recalibration M69 produces.**
That is the single most reassuring fact in this addendum: a conditional
certificate is still a certificate from an instrument that can still refuse.

### The unifying observation

**Gate 8 is robust to both N and σ_F; gate 4 is sensitive to both; and it is the
same mechanism.** M66's M-HEADLINE is MET because at gate 8 the tolerance is
11.31 σ_F against a `c_N` drift of 1.03 σ_F — saturation swamps the drift. My
sweep shows the same at gate 8 for σ: `n_eff` is pinned at 30.0 and stays there
from gate 8 to gate 64, so a 20 % rescale moves nothing. **Gate 4 sits on the
shoulder of the admission curve, where both N and σ have leverage.** The
project's headline (5.4778 at gate 8) is safe from both for a structural reason;
the shipped default is exposed to both for the same structural reason, inverted.
(DERIVED, from M66 fact 17 and my sweep.)

## 5. K1's f32 ties — do they touch determinism or efficiency?

**They touch one claim of mine, immaterially, and I am correcting it rather than
waving it through.**

`admits` is `best - focus <= tolerance` (`merge.rs:320`), so exact `f32` ties are
admitted at any gate including 0. M66 measures `n_eff` = 1.0000058 worst case,
0–3 tied pixels in 515,094.

- **Efficiency: unaffected.** `n_eff` is *reported* correctly; the tie is in the
  merge and in the number alike, so `R/√n_eff` stays consistent.
- **Determinism: unaffected, and I have the measurement rather than the
  argument** — byte-identical SHA-256 across two runs of the decision arm. A `<=`
  over a deterministic iteration order cannot introduce nondeterminism. **But my
  determinism check ran at gate 4 only**; I never repeated it at gate 0, so for
  the tie path itself that statement is ARGUED, not MEASURED.
- **My input-side power condition was overstated.** In my last ruling I told you
  the power claim rests on `SELECTOR-same-binary` reporting *"`n_eff` = 1.0, the
  input-side condition for a pure selector."* **It is 1.0000058, and my "exactly
  1" was reading the CLI's 3-decimal display as an exact value.** The effect on
  the arm is ≈1.5 × 10⁻⁶ on a ratio of 0.9768 against a 1.05 ceiling — immaterial
  by six orders of magnitude — but the condition should be stated as a tolerance,
  not an identity. Correcting my own §6, not M66's finding.

## 6. Candidate (ii) — would adopting it invalidate the battery?

**No. Say yes to it on my account.** Two reasons, and I checked the second rather
than assuming it.

The battery is spec-driven: arms are `argv` templates in
`acceptance-spec.json`, so a merge that replaces `--gate` with `--alpha` is
tested by editing data. Nothing in my Python names a gate.

The real risk was losing my last power arm, since `SELECTOR-shipped` is already
`NO-POWER` and `--gate 0` might not survive a reparameterisation — the
`CANNOT-CERTIFY` contingency my §3.3 pre-registered. **That risk is already
retired: `strehl argmax-baseline` exists as a standalone subcommand**
(`main.rs:217–218`), described by the crate itself as *"naive per-pixel argmax
(NOT THE DEFAULT; a negative control)"* (`stack.rs:222`). It takes no gate, so it
is invariant to any gate reparameterisation **and** to any σ_F rescale. M64
created a durable negative control when it moved the selector there, which I do
not think was the reason it did so.

**My spec does not currently use it.** That is owed work for whoever holds the
instrument next, alongside the input-side power assignment I conceded to M55 —
and I am not making either change now, because amending the spec while ruling
with it is precisely what my §6 bars.

## 7. What I am asking for

Route the σ_F question to M69 as planned. **When it lands, this certificate needs
one re-run, not a re-argument** — `python src/10-acceptance.py --exe <binary>
--tag m69`, ~9 minutes, unmodified — and the arms that move will be `DEFAULT` and
`ESTIMATOR-explicit`. If M69 rescales σ_F, `DEFAULT`'s ±2 % window will decide
the matter on its own terms and I will report what it says, in either direction.

I do not believe the change should be reverted or rerouted. **M64 built the right
thing**; what M66 has shown is that the *gate*, not the estimator, is denominated
in a unit that drifts with N and is mis-sized on real texture. Nothing in that
touches whether the default path averages, which is what I certified and what
remains true by an eight-fold margin.

## 8. Labels

**MEASURED**: the sweep table, `n_eff` values, 0.976815, the byte-identical
determinism hash, M66's facts as cited, the source lines in `merge.rs` /
`main.rs` / `stack.rs`.
**DERIVED**: the 2.5 % `n_eff` headroom; σ-rescale ≡ gate-rescale by linearity of
`tolerance()`; the ≈8× robustness of the estimator/selector verdict; exact
σ-invariance of gate 0; that saturation is the common mechanism for gate 8's
robustness to both N and σ.
**ARGUED**: that determinism holds on the tie path at gate 0; that adopting
candidate (ii) is safe for the battery given `argmax-baseline` exists; that the
omitted large stacks' extra guard margin retires my earlier scoping caution.
