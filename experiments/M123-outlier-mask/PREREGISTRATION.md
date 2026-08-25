# M123 — pre-registration

Written **before** any result was looked at. Nothing below was chosen after
seeing a number. Where a value comes from an earlier milestone it is cited so a
reader can tell what is inherited and what is new.

---

## 0. The brief's question is already answered, and this section says so first

The brief asks:

> Does `LowFreq` fire on genuine subject motion while staying quiet on focus
> difference alone?

**That question is closed, in the tree, with a derivation of why the answer must
be no.** AGENTS rule 40 requires searching `docs/research/` for the question
before commissioning, and naming every report found. Four exist:

| report | data | verdict |
| --- | --- | --- |
| `M28-robustness-mask-measured.md` | real | detector separable if the reference is the *adjacent* frame; no merge effect measured; "NOT INDEPENDENTLY VERIFIED" |
| `M60-robustness-mask-at-merge-time.md` | real | "**I did not build the mask**"; "a mask keyed on chi2 would be a sharpness detector wearing a robustness label" (§246) |
| `M89-robustness-mask.md` | real, 23 stacks | "The metric works and should be adopted. **The mask, as specified, should not ship**" |
| `M97r-outlier-mask.md` | **synthetic only** | `LowFreq` fires on **100.0%** of a defocus trap at mean chi2 **972.98**, *above* `Raw`'s 85.31 |

`outlier.rs` itself marks the arm the brief asks about as a **MEASURED
FAILURE** (`Discriminator::LowFreq` doc comment, lines 91–115) and carries a
named regression test for it,
`low_pass_filtering_does_not_discriminate_defocus_it_amplifies_it`.

The reason is derived, not empirical (M97r W3): box-averaging `m = (2r+1)^2`
samples divides the noise variance by `m` while a spatially extended defocus
residual survives almost intact. For a step edge the filtered residual is of
order `C*r_d/R` and the filtered noise of order `sigma/R`; the statistic is
their ratio, `C*r_d/sigma`, **independent of `R`**. Filtering cannot buy
defocus-blindness because it rescales signal and noise together. Motion behaves
identically, so the arm separates nothing at any radius.

Re-running `LowFreq` on real captures to rediscover this would be exactly the
failure rule 40 exists to prevent: re-deriving a settled answer, which then
arrives with the authority of a fresh measurement. **I will still run it, as an
inertness control only** — it costs nothing on top of the runs below and it
keeps the negative reproducible on real data — but it is not the question.

**The brief's premise is stale in one further respect.** It describes the module
as providing "two discriminators". It provides **four**: `Raw`, `LowFreq`,
`Shift`, `ShiftFree`. The module-level doc header (lines 20–33) still says "two"
and still describes `LowFreq` as the arm where "defocus largely cancels"; the
enum docs 40 lines below say the opposite and cite the measurement. The header
is stale against its own enum. Recorded as a finding, not fixed here.

## 1. The question this milestone actually asks

> **Does `ShiftFree` — the only arm that survives M97r's synthetic controls —
> separate real subject motion from real defocus on real captures, and does its
> in-sample `DEFAULT_MIN_SHIFT_PX = 0.35` bar hold out of sample?**

This is open, and the module says so itself. `DEFAULT_MIN_SHIFT_PX`'s doc
comment ends: "**It has not yet been measured on real frames; see the
`NOT VERIFIED` note in the milestone record.**" M97r §6 names the same gap:
"**No real frames were used. Every number here is synthetic.** … the 0.35 px bar
must be re-measured against them before it means anything about the corpus."

M97r's entire gate configuration — `0.35`, `RESOLUTION_MARGIN = 3.0`, the choice
of `ShiftFree` over `Shift` — was chosen against the four synthetic cases used to
report it. M97r §6 says so in as many words ("The gate configuration is
in-sample"). So every number defending it is in-sample, and the corpus is the
held-out set.

**AGENTS rule 34 makes this the highest-value measurement available.** "A plant
that supplies its own noise constant cannot detect that constant being wrong."
M97r drew its noise from the model and normalised by the same model, so it is
scale-invariant in the gain and **could not have detected a miscalibration of any
size**. Only real sensor noise can falsify the calibration.

## 2. Arms — and what real data buys that a plant cannot

| case | material | focus | motion | role |
| --- | --- | --- | --- | --- |
| `flat-null` | `flat-fields/flat-fields` adjacent pair | fixed | none | **CALIBRATION NULL, high signal** — tests the `g*S` shot term |
| `dark-null` | `D:\macro-dark-frames` adjacent pair | n/a | none | **CALIBRATION NULL, low signal** — tests the `(RN*g)^2` term |
| `defocus` | `109MSDCF` adjacent pairs | **changes** | none | **TRAP** — must stay quiet. Quietest stack in the corpus |
| `motion` | `coffee-bubbles` adjacent pairs | **constant** (0.2841 m throughout) | real bubble drift | **PLANT** — must fire |
| `foam` | `foam` adjacent pairs | changes | real | realistic hard case, both effects at once |
| `plant-shift` | `109MSDCF` pair, one plane shifted by a known amount | changes | synthetic | **POSITIVE CONTROL**, proportionality |

`coffee-bubbles` is the reason this is worth doing at all. `captures-needed.md`
line 1264 records it as **"none (0.2841 m throughout)"** for focus, "Contaminated
by real bubble motion (0.947 first-to-last)". That is *real subject motion at
constant focus* — the exact positive control no synthetic plant can supply, and
the exact case `109MSDCF` (focus change, no motion) is the complement of. The
two together are the discriminating pair, on real sensor data.

`flat-null` and `dark-null` are the rule-34 tests. Two flats are the same scene
at the same focus with independent real noise at high signal; two darks the same
at low signal. Between them they exercise both terms of
`sigma^2(S) = g*S + (RN*g)^2` against real photons.

## 3. Parameters, fixed now

| parameter | value | provenance |
| --- | --- | --- |
| `tile` | 32 | module `Params::default()` |
| `blur_radius` | 6 | module `Params::default()` |
| `threshold_k` | **6.0** | module `Params::default()`, and M97r's reported value |
| `min_shift_px` | **0.35** | `DEFAULT_MIN_SHIFT_PX`, inherited unchanged |
| `RESOLUTION_MARGIN` | 3.0 | module constant |
| crop | centred 1024 px quad crop, green phase | rule 7 — active area only, never the full decoded buffer |

**`threshold_k = 6.0` is inherited, not chosen.** Taking the module default is
the only setting that is not fitted to my own results. I am explicitly *not*
sweeping `k` to find a value that makes the mask look good; if 6.0 fails, that is
the finding.

At `tile = 32`, `N = 1024`, the disagreement arms' null spread is
`sqrt(2/1024) = 0.0442`, so the bar is `1 + 6*0.0442 = 1.265`. Under a correct
noise model a 6-sigma one-sided bar gives a per-tile false-positive probability
of order `1e-9`. Over the ~20k tile-tests in this run the expected count of
chance false positives is `~2e-5`. **Therefore any measured trap FPR above about
0.1% is evidence of model error, not of statistical fluctuation.** That is the
prediction this design is built to falsify.

For the displacement arms the bar is `1 + k = 7.0` on 2 dof (`thresholds()`
lines 521–525), whatever the tile pools.

## 4. Success criteria — pre-registered, and the run is a FAIL if any is missed

1. **Null (rule 34).** `flat-null` and `dark-null` mean `chi2` for `Raw` in
   **[0.90, 1.10]**.
   Expected ~0.99: M89 measured **0.9897** on a locked-down static stack and
   attributed the 1% deficit to common-mode correlation between frames
   (`rho ~ 0.0103`). Per rule 30 I assert *at the known-disagreeing value*
   rather than narrowing the domain: I expect slightly below 1.0, not exactly 1.
   A reading outside [0.8, 1.2] indicts the noise model and, per the brief, is
   the most important finding available and gets said loudly.
2. **Trap.** `ShiftFree` gated fire rate on `109MSDCF` adjacent pairs
   **<= 1.0%**.
   `<= 5%` is marginal-but-tolerable and will be reported as such; `> 5%` is a
   fail. Rationale: the mask drops tiles from the average, so an FPR of `f`
   costs `f` of `n_eff`; at 5% that is 2.5% added noise, which is the most a
   defence against a rare event may cost. The brief's own bar ("30% … will
   destroy renders") is far looser than anything I would accept.
3. **Plant.** `ShiftFree` gated fire rate on `coffee-bubbles` **>= 20%** of
   informative tiles.
   Not 100%: bubble motion is spatially localised, so most tiles legitimately
   contain no motion. The number that matters is that it is far above the trap.
4. **Separation.** Plant fire rate **>= 10x** trap fire rate. This is the whole
   value proposition; below 10x the mask is not buying discrimination.
5. **Inertness control (rule 20 / rule 11).** `Raw` must fire on the trap where
   `ShiftFree` is quiet. **A `ShiftFree` null on `109MSDCF` means nothing unless
   `Raw` fires on the same input** — otherwise the harness is inert rather than
   correct. If `Raw` does not fire on the defocus trap, every null in this run is
   void and I report exactly that.
6. **Positive control proportionality.** A planted shift of `d` px on a real
   `109MSDCF` pair must be recovered with `|s|` monotone in `d`, and the gate
   must fire for `d >= 0.5` and not for `d = 0`.

## 5. What would make each measurement fail — rule 20, written before the run

| check | the input that makes it FAIL | does such an input exist? |
| --- | --- | --- |
| null in [0.9, 1.1] | a gain wrong by any factor; `chi2` scales as `1/g` | yes — M25 shipped a 2x gain error (facts 550, 552) |
| trap quiet | defocus curvature displacing a curved edge (M97r W5) | yes — it fired on 60.9% of the synthetic trap for `Shift` |
| plant fires | motion below the 0.35 px bar | yes — bubble drift is not guaranteed to exceed it |
| `Raw` fires on trap | a decode that returned identical buffers | yes — and check 5 is precisely the guard |
| separation >= 10x | either of the two above | yes |

**The inertness control is the load-bearing one.** Every null in §4 is
uninterpretable without it, which is why it is criterion 5 and not a footnote.

## 6. Declared in advance

- **Gate.** No merge is run in phase 1, so no gate applies. If phase 2 happens,
  every render is at `DEFAULT_GATE = 4.0` (`merge.rs:298`), stated per number.
  `merge.rs:3027` labels gate 0 a `negative control`; I will not quote a gate-0
  number as a result.
- **Reads only.** Nothing is written to `D:\`. Outputs go to
  `C:\dev\strehl-out\M123\`.
- **Phase 2 is conditional and I expect not to reach it.** Given M60 and M89
  both declined to ship a mask at the merge seam on real data, the prior is
  against wiring. Phase 2 proceeds only if §4.1–§4.5 all pass. If
  `crates/strehl-core/src/merge.rs` has uncommitted modifications or recent
  commits from another agent, I do not edit it and hand the diff over instead.
- **In-sample honesty.** `0.35` and `k = 6.0` are inherited from M97r unchanged.
  If I change either after seeing a result, the result becomes in-sample and I
  will label it so rather than quoting it as held out.
