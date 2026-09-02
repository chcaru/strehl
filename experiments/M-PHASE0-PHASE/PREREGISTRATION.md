# M-PHASE0-PHASE — preregistration

**Lane:** C1's go/no-go. Sub-pixel phase coverage *and conditioning* census from existing
warpmaps, by field radius, including the May IBIS-ON stacks as the free dither pilot.

**Status:** written before any census number was computed. Section 12 records the
substrate recon that preceded it; that recon read metadata and existing outputs only and
computed no phase, no condition number, and no winnable fraction.

**House rules in force:** 9 (commission the instrument before trusting it), 18 (state bias
direction before measuring), 35 (a checker carrying its own answer tests nothing), 42
(path-scoped commits).

---

## 1. The question, in the proposal's words

`docs/proposals/2026-08-sota-path.md:1030-1034` states C1's kill line:

> Kill: if within-DOF relative registration cannot reach **[bar]** px on real stacks
> (measured first, cheaply, from existing warpmaps + one local refinement prototype — the
> phase/conditioning census is a corpus-only computation requiring zero new captures).

and at `:967-975` states the identifiability condition the census is supposed to gate:

> Alias unfolding is a small linear system per frequency neighbourhood: replicas at
> f ± k·f_s enter frame i with phase e^{j2π k f_s φ_i}, so recovery needs the matrix of
> those phases across contributing frames to be well-conditioned — which is precisely a
> statement about the *spread of sub-pixel phases φ_i* among within-DOF frames.
> M-PHASE0-PHASE therefore reports not just coverage but the condition-number
> distribution by field radius.

**`[bar]` is a literal unfilled placeholder.** The proposal asserts "~0.1–0.15 px" at
`:996-999` and repeats "~0.1 px bar" at `:1321-1324`, with no derivation and no citation.
The substrate recon (§12) searched both this repository and `C:\dev\macro` for a
derivation and found none; the nearest numbers price different quantities (a 0.125 px
*phase-diversity* target from the old Wronski probe, and BUILD-CHROMA's 0.1199 px
*chromatic displacement* for 9.36% energy loss). **A lane cannot be gated on a number
nobody has derived.** Deriving it is therefore the lane's first deliverable, and it comes
before the census, because it determines what the census has to report.

---

## 2. The lane has three parts, in this order

1. **Derive the bar.** A commissioned simulator of alias unfolding that answers: given
   `N` frames whose sub-pixel displacements are known to accuracy `σ_δ`, at what `σ_δ`
   does the reconstruction stop being better than not attempting it? This needs no data
   at all — it is a property of the linear algebra plus a noise model.
2. **The census.** For the seven May stacks, at a grid of sites, using the M66 focus
   cubes to choose the within-DOF frames and the warpmaps to compute their phases:
   the phase set, the system's conditioning, and — crossed with part 1 — the registration
   accuracy that site would require.
3. **The joint gate.** Winnable field fraction as a function of assumed registration
   accuracy, by radius and by stack. The verdict reads off that curve.

Part 3's shape is deliberate and is copied from M-PHASE0-ZFIELD, where reporting a
*ladder* over an uncertain operator parameter rather than a single number is what exposed
that the naive verdict was a substrate artefact. Here the uncertain parameter is the
registration accuracy a local refinement could achieve, which phase 0 cannot measure.

---

## 3. The algebra, stated so it can be checked

Write the per-frame sample lattice as `Λ` and the reconstruction target lattice as `Λ_t`,
with `Λ ⊂ Λ_t` of index `M = [Λ_t : Λ]`. Frame `i` samples the scene displaced by `d_i`
(a 2-vector, in **source full-resolution sensor pixels**). Sampling on `Λ` folds the
target band into `M` replicas indexed by coset representatives `g_k` of `Λ* / Λ_t*`.
Frame `i`'s measurement at target frequency `ν` is

    y_i = Σ_{k=0}^{M-1} X_k · exp(j2π ⟨ν + g_k, d_i⟩)

Factoring out the common unimodular `exp(j2π⟨ν, d_i⟩)` — which is known and invertible —
leaves the system matrix

    **A[i,k] = exp(j2π ⟨g_k, d_i⟩)**,   i = 1..N,  k = 0..M-1

This is a generalised Vandermonde matrix. Three exact consequences, all of which become
registered controls in §8:

- **(P1) Translation invariance.** Replacing every `d_i` by `d_i + c` right-multiplies `A`
  by the unitary `diag(exp(j2π⟨g_k, c⟩))`, so every singular value — and hence `κ(A)` —
  is *exactly* unchanged. **The conditioning is intrinsically a statement about relative
  placement.** This is precisely C1's claim at `:1006-1013` that SR consumes relative
  placement among the within-DOF frames, and it means the census is immune to absolute
  registration error by construction.
- **(P2) Lattice invariance.** Replacing any `d_i` by `d_i + λ` for `λ ∈ Λ` leaves `A`
  exactly unchanged, because `⟨g_k, λ⟩ ∈ ℤ` for coset representatives of the dual. Adding
  a vector *not* in `Λ` must change it.
- **(P3) Permutation invariance.** `κ` depends on the multiset `{d_i}` only, not on order.

### 3.1 The four replica counts this lane prices

| Name | Per-frame lattice `Λ` | Target `Λ_t` | `M` | Coset reps `g_k` (cycles/sensor px) |
|---|---|---|---:|---|
| **G-1x** | green quincunx | full pixel grid | 2 | (0,0), (½,½) |
| **RB-1x** | red or blue, spacing 2 | full pixel grid | 4 | (0,0), (½,0), (0,½), (½,½) |
| **G-2x** | green quincunx | half-pixel grid | 8 | the 8 cosets of the quincunx in ½ℤ² |
| **RB-2x** | red or blue, spacing 2 | half-pixel grid | 16 | the 16 cosets of 2ℤ² in ½ℤ² |

G-1x and RB-1x are C1's "1× before any SR claim" (`:1015-1021`): completing the CFA
without inventing values. G-2x and RB-2x are the 2× super-resolution claim (`:1023-1029`).

**A prediction that is arithmetic, not data, and is therefore registered now:** the system
is rank-deficient whenever `N < M`. C1's own feasibility paragraph (`:988-995`) estimates
**3–6 sharp frames per site**. Therefore **G-2x (M=8) and RB-2x (M=16) are infeasible at
the strict per-site read before any measurement is taken.** If the census reports
otherwise it is because the within-DOF sets are larger than C1 estimated, and that is a
finding about the corpus, not about C1. The pooled read (§6.3) is the only route by which
2× can be feasible at all, and that route buys its equations with a stationarity
assumption that must be stated, not hidden.

### 3.2 The closed form that commissions the simulator

For `M = 2, N = 2`, with `Δ = 2π⟨g_1, d_2 − d_1⟩`:

    κ = sqrt( (1 + |cos(Δ/2)|) / (1 − |cos(Δ/2)|) )

`κ = 1` exactly at `Δ = π` — for G-1x that is a relative displacement whose components sum
to one odd integer, i.e. **a half-cell offset along the quincunx diagonal is the optimum**,
and `κ → ∞` as `Δ → 0`. The simulator's numerical `κ` must reproduce this closed form to
`1e-10` over a sweep of `Δ`. This is registered as control C-E.

---

## 4. Deriving the bar: what "the bar" actually means

The reconstructor solves with *estimated* displacements `d̂_i = d_i + δ_i`, building `Â`
instead of `A`. It is not enough to say the answer degrades; the question is **when does
attempting the unfolding become worse than not attempting it**, because not attempting it
is the shipping behaviour and is always available.

Define, per trial:

- `x` — the true replica vector, `x_0` the baseband component, `x_{1..M-1}` the aliases.
- `x̂ = Â⁺ y` — the solution using estimated phases, from noisy `y = A x + n`.
- **`η = ‖x̂ − x‖ / ‖x_{1..M-1}‖`** — error relative to the alias energy at stake.

The no-attempt comparator is `x̂ = (x_0, 0, …, 0)` — keep the baseband, discard the
aliases — whose error is exactly `‖x_{1..M-1}‖`, i.e. **`η = 1` by construction.** So:

- **`η < 1` is the do-no-harm bar.** Registered as the primary bar.
- **`η < 0.5` is the worth-doing bar.** Registered as the secondary bar.
- `η < 0.1` is quoted for reference only and is not a gate.

**`bar(M, {d_i}, SNR) = the largest σ_δ whose median η stays below the bar.`** It is a
property of the site's own phase set, not of a global κ threshold, which is why the census
reports a required `σ_δ` per site rather than thresholding `κ`. `κ` is still reported,
because the proposal asks for it and because it is the interpretable summary.

### 4.1 First-order expectation, to be confirmed or refuted by the simulator

`Â[i,k] = A[i,k]·exp(j2π⟨g_k, δ_i⟩) ≈ A[i,k](1 + j2π⟨g_k, δ_i⟩)`, so the perturbation
enters as a relative row error of size `2π|g_k||δ_i|`, and the solution error is amplified
by the conditioning. The expected shape is therefore

    η ≈ C · κ · σ_δ        for small σ_δ

with `C` of order `2π·|g|`. **This is a prediction, not a result.** The simulator measures
`C` and the range of `σ_δ` over which linearity holds. If the measured `η(σ_δ)` is not
linear in `σ_δ` and not proportional to `κ` in the small-`σ_δ` regime, the derivation in
this section is wrong and §4's bar must be taken from the simulation alone, with the
discrepancy disclosed.

Taking the shape at face value, `η < 1` implies `σ_δ < 1/(C κ)`. At `κ = 2` and `C ≈ 2π·0.707`
this is `σ_δ ≲ 0.11` sensor px — which would place the proposal's asserted 0.1–0.15 px at
the **do-no-harm break-even**, not at a quality bar, and would make the worth-doing bar
roughly **0.06 px**. Registering that expectation here means the lane cannot later claim
the proposal was vindicated without the numbers actually landing there.

### 4.2 Noise

`κ` and the phase-error analysis both ignore measurement noise; the bar must not. The
simulator runs at:

- **noiseless** — the primary read. The bar it produces is an **upper bound** on
  achievable tolerance: no real system does better. Registering the primary read as an
  upper bound means the lane's bar is generous to C1, which is the safe direction for a
  go/no-go we do not want to fail spuriously.
- **finite SNR ladder** — alias-component SNR ∈ {30, 20, 10} dB, reported as a table.

---

## 5. Substrate, and its limits

From the recon (§12), all of which is corpus-only; **no new RAW decode, no Rust binary
run, no capture.**

| Input | What it gives | Where |
|---|---|---|
| Cached warpmaps | per-frame global 4-DOF similarity | `%LOCALAPPDATA%\strehl\warpmaps\*.warpmap.txt` |
| M66 D4 focus cubes | per-site through-focus response, float32 | `experiments/M66-gate-n-dependence/data/*-d4.npy` |
| M70 `w50` | empirical per-stack focus half-width | `experiments/M70-through-focus-spectrum/out/s21_shape_corpus.json` |

Seven May stacks: `109MSDCF` (22), `112MSDCF` (79), `113MSDCF` (63), `119MSDCF` (33),
`coffee-bean` (105), `coffee-bubbles` (19), `foam` (100). All seven have complete
zero-refusal maps and a D4 cube. All 421 May ARWs read `ImageStabilization: On`.

**Five limits, stated now:**

1. **The maps are a global 4-DOF similarity, not a dense field.** This census measures the
   phase carried by the *modelled* geometry. Local residual motion is invisible to it.
2. **There is no IBIS-OFF arm.** All 421 May frames are IBIS-On, so the "free dither pilot"
   is a single-arm observation: whatever dither is present is present in all of it, and
   this lane cannot attribute any of the measured phase spread to IBIS specifically. The
   proposal's framing at `:998-1003` treats the May stacks as a pilot; they are, but only
   in the sense of showing what an IBIS-On capture yields, not of isolating IBIS's
   contribution. The deliberate IBIS-ON/OFF bracket stays requested.
3. **Cached duplicate maps are not placement-identical.** §7 pre-registers the selection
   rule and §8 makes the spread a measured sensitivity arm rather than a silent choice.
4. **The cube plane is 3514×2344, the warp plane 3516×2344** — same origin and same
   lattice, the cube is two plane-columns short at the right edge (`M39` `:219-228`).
   Sites are taken from the cube, so the missing columns are simply absent from the census.
5. **The within-DOF frame set comes from a smoothed response.** M66 filters 27×27 then
   17×17 where the shipping fine field is 5×5 — the same substrate mismatch M-PHASE0-ZFIELD
   quantified at a factor of 6.83 in response noise. §6.2 chooses a frame-selection rule
   that does not depend on the peak's *width*, precisely to keep this out of the primary
   read.

---

## 6. What will be computed

### 6.1 Sites

A regular grid over each D4 cube with **stride 4** in both axes (= every 16th plane pixel,
every 32nd sensor pixel), giving ~147×220 ≈ 32k sites per stack. The warp is affine in
position, so the phase field is smooth and denser sampling adds nothing; the depth
structure that varies per site is what the grid samples. Cube site `[i,j]` maps to warp
plane coordinate `(x, y) = (4j, 4i)`, with no offset correction.

**Field radius** is pre-registered as **distance from the plane centre, normalised by the
plane half-diagonal** — convention 3 of the four found in the corpus (`M103/photo.py`
`:74-88`), chosen because it matches the alignment code's own `corner_radius = hypot(W,H)/2`
(`align.rs:379-395`) and so is the one the warp model is expressed in. The elliptical
convention is reported as a sensitivity arm only.

### 6.2 Within-DOF frame set

**Primary rule: the `n` frames whose cube index is nearest the per-site response argmax,
for `n ∈ {3, 4, 5, 6, 8}`, reported as a ladder.** This rule is chosen over a
`w50`-derived window on purpose: it does not depend on the peak's measured width, so the
M66 smoothing mismatch (§5 limit 5) cannot inflate the frame count. It is also what a real
implementation does — a fixed sample budget — so it is operationally the right definition.

**Sensitivity arm:** an actual half-width window from M70's per-stack `w50`, reported
alongside so the ladder can be located against a physical DOF.

**Site placeability.** A site whose through-focus response has no peak carries no depth
information and no detail to super-resolve. Sites are excluded when the response range
across frames fails to exceed `k·σ_r` for the per-site response noise `σ_r`, estimated as
in `M-PHASE0-ZFIELD/src/zflib.py`. The excluded fraction is **reported per stack**, and the
winnable fraction is reported **both** over placeable sites and over all sites.

### 6.3 The two reads, both reported

- **Strict (per-site).** Equations = the `N` frames only. This is the proposal's own
  formulation at `:967-975` and it is the honest identifiability statement.
- **Pooled (kernel).** Equations = frames × the distinct sub-pixel positions within a
  gather radius `R ∈ {1, 2}` target pixels. This is what a kernel-regression
  implementation (Wronski) actually solves, and it is the only route by which `M = 8`
  or `16` can be feasible at 3–6 frames.

Reporting only the strict read understates feasibility; reporting only the pooled read
overstates it, because the pooled equations are bought with an assumption of local
stationarity that the strict read does not need. **Both are primary.** Neither is allowed
to be quoted without the other in the note's headline.

### 6.4 Outputs

Per stack, per `M`, per `n`: the distribution of `κ`; the distribution of required `σ_δ` at
each bar; **the winnable field fraction as a function of assumed registration accuracy**;
and all of the above binned by field radius into 10 equal-area annuli.

---

## 7. Researcher degrees of freedom, closed now

1. **Map selection.** For each stack, among the complete zero-refusal cached maps, take the
   one whose placement-payload SHA256 is **lexicographically smallest**, and record that
   hash in the note. This rule is arbitrary but it is fixed before any number is seen,
   which is the only property that matters. §8 control C-G measures how much the choice
   could have mattered.
2. **Radius convention** — fixed in §6.1.
3. **Frame-selection rule** — fixed in §6.2, with the ladder over `n` reported in full so
   no single `n` can be selected after the fact.
4. **`M` ladder** — fixed in §3.1 at exactly the four values, all reported.
5. **Bars** — fixed in §4 at `η < 1` primary, `η < 0.5` secondary.
6. **Site grid and stride** — fixed in §6.1.
7. **Verdict thresholds** — fixed in §9.

---

## 8. Controls, registered before measuring

Each must be written and passing before the census is believed. Controls that can only
pass are worthless, so each pairs a required-invariance arm with a required-sensitivity
arm wherever the algebra permits one.

| # | Control | Must show |
|---|---|---|
| **C-A** | Exact recovery: `σ_δ = 0`, no noise, `N ≥ M`, distinct phases | `η < 1e-10`. If not, the solver is wrong. |
| **C-B** | All `d_i` in `Λ` (no phase diversity) | rank-deficient, **detected and reported infeasible**, not silently pseudo-inverted |
| **C-C** | `N < M` | same |
| **C-D** | Monotone response *and* monotone improvement | `η` rises with `σ_δ`; `η` falls when frames are added or phases are spread. A metric that only responds to degradation passes every planted-defect test trivially. |
| **C-E** | Closed form, §3.2 | numerical `κ` matches `sqrt((1+\|cos(Δ/2)\|)/(1−\|cos(Δ/2)\|))` to 1e-10 over a `Δ` sweep |
| **C-F** | **Lattice invariance with a sensitivity arm (P2)** | adding `(1,1)` sensor px to any `d_i` leaves G-1x `κ` **exactly** unchanged; adding `(1,0)` **must change it**. This tests the whole plane→sensor→lattice unit chain end to end: a factor-of-2 unit error fails it. |
| **C-G** | **Translation invariance (P1)** | adding a common `c` to every `d_i` leaves `κ` unchanged to 1e-12 |
| **C-H** | Permutation invariance (P3) | reordering frames leaves `κ` bit-identical |
| **C-I** | Synthetic null map: all displacements integer multiples of `Λ` | census reports **0% winnable** everywhere at every `σ_δ` |
| **C-J** | Synthetic ideal map: phases equispaced over the cosets | census reports **~100% winnable** at `σ_δ = 0`, degrading smoothly |
| **C-K** | Duplicate-map spread | for each stack, the max and RMS `κ` difference between distinct cached placement payloads, so limit 3 is quantified rather than assumed small |
| **C-L** | Cube/warp frame-axis agreement | cube frame `t` and map record `t` refer to the same ARW, verified against the filename-sorted listing |

**A control that has never fired may be a no-op.** C-F, C-I and C-J are additionally
*commissioned* by planting the defect each targets — a wrong unit scale for C-F, a
non-degenerate map for C-I, a degenerate one for C-J — and requiring each to fail.

---

## 9. Verdict rule, fixed before measuring

Evaluated on the **G-1x and RB-1x** strict read for the 1× claim, and on **G-2x** for the
2× claim, at the winnable-fraction curve's value at the most optimistic defensible `σ_δ`.

| Winnable field fraction | Verdict for that claim |
|---|---|
| ≥ 60% | **SURVIVE** |
| 25–60% | **NARROWED** — viable as an outer-field-only mode, per-pixel refusal elsewhere |
| < 25% | **KILL** for that claim |

60% is everything outside normalised radius 0.63; 25% is only the thin corner annulus
outside 0.87, which is not worth an architecture. The two claims are gated separately: it
is an expected and reportable outcome that 1× survives and 2× does not.

**The verdict is additionally labelled NOT ROBUST** if it flips anywhere across the `n`
ladder, the `M` ladder's neighbouring entries, the strict/pooled reads, or the duplicate-map
arm — the same robustness discipline that M-PHASE0-ZFIELD's F-ladder forced.

---

## 10. Bias directions, declared before measuring (house rule 18)

M-PHASE0-ZFIELD's most transferable lesson was that bias B1 there was registered with only
one of its two halves, and the omitted half drove the result. Each entry below therefore
states **both** halves where the bias has two.

| # | Bias | Direction |
|---|---|---|
| **B1** | Registration error inflates apparent phase spread: observed spread ≈ `sqrt(s² + σ_δ²)`. The census computes `κ` from *estimated* phases. | **FAVOURS C1.** Sharpest exactly where the spread is smallest — the predicted central dead zone — where the entire observed spread could be error. |
| **B2** | The map is a global 4-DOF similarity. Unmodelled local motion is (a) real diversity the census cannot see, and (b) diversity the reconstructor cannot know. | **BOTH.** (a) makes the census understate true diversity — **disfavours C1**. (b) means counting it would overstate *usable* diversity — **favours C1**. The census measures usable-under-the-global-model, which is a lower bound on what a local model could expose and an upper bound on nothing. |
| **B3** | M66's 27×27→17×17 smoothing widens the apparent focus peak. | **FAVOURS C1** — more frames pass a width-based window. Mitigated by §6.2's width-free primary rule; the `w50` arm carries the bias and is labelled. |
| **B4** | Excluding unplaceable sites removes featureless regions from the denominator. | **FAVOURS C1.** Reported both ways. |
| **B5** | The strict read counts only `N` equations; the pooled read buys more with a stationarity assumption. | Strict **disfavours**, pooled **favours**. Both reported (§6.3). |
| **B6** | Truncating to exactly `M` replicas assumes the signal is exactly `M`× oversampled. Real optics leak beyond. | **FAVOURS C1** — under-modelled replicas are unmodelled error the census does not charge for. |
| **B7** | The noiseless primary bar (§4.2). | **FAVOURS C1** — it is an upper bound on achievable tolerance. Deliberate: a go/no-go should not fail spuriously. |
| **B8** | Cube plane two columns short (§5 limit 4). | Negligible; stated for completeness. |

---

## 11. What would falsify this lane's own verdict

- **The units are wrong.** If plane px were confused with sensor px anywhere, every phase
  is off by 2×. C-F is designed to catch exactly this and has a sensitivity arm so it
  cannot pass vacuously.
- **The transform direction is wrong.** If the map is frame→reference where this lane
  assumes reference→frame, the displacements are inverted. Because `κ` is invariant under a
  common translation (P1) and the map is a similarity with `a ≈ 1`, an inverted convention
  is **not** guaranteed to show up as an obvious failure — it produces a plausible but
  wrong phase set. This is the lane's most dangerous single assumption; it is pinned from
  Rust source and validated numerically against M95's independently published statistics
  before any census runs.
- **`η` is the wrong figure of merit.** If the real reconstructor's error does not track
  `η`, the bar is mis-priced. `η` is defined against the no-attempt comparator, which is
  the honest baseline, but it is an `ℓ2` statistic on replica coefficients and not a
  rendered-image metric. D1's instruments are the eventual arbiter; this lane's bar is a
  *necessary* condition, not a sufficient one, and the note must say so.
- **The strict read is the wrong model.** If the shipping design pools spatially, the
  strict read's infeasibility verdict for `M = 8` does not bind. Hence §6.3.

---

## 12. Substrate recon that preceded this document

A read-only reconnaissance established, before this preregistration was written: the
warpmap format and transform family; that 381 cached maps exist covering 24 of 32 stacks,
all seven May stacks among them with complete zero-refusal placements; that duplicate full
maps are not always placement-identical; that all ten M66 cubes load as C-contiguous
little-endian float32 with the shapes their manifest claims; that all 421 May ARWs report
`ImageStabilization: On`; that no dense `WarpField` is implemented or persisted anywhere in
the product; that no prior corpus result computes a phase matrix, a condition number, or a
within-DOF phase census; and that `[bar]` has no derivation in either repository.

It also recomputed M110's headline jitter statistics from the primary `(299,4)` track file
and reproduced 0.48 px median and 13.8% ≥1 px, with a semantic correction: those are
centred **second differences over frame triples**, not adjacent first differences.

Prior partial results, none of which answers this lane's question: old PROBE3 measured
*post-alignment residual* shift SD on 119MSDCF (0.075 px at 3 frames rising to 0.273 px
over all 33) and on coffee-bean (0.097 px at 3 frames), in already-warped full-resolution
TIFFs whose arrays no longer exist; M95 measured all-frame modelled phase at two positions
on bee-3 and called it indistinguishable from uniform; M103 measured one-pair sparse-tile
fractional offsets on six stacks and diagnosed integer locking.

---

## 13. Reproduction

    cd projects/strehl
    python experiments/M-PHASE0-PHASE/src/p0_controls.py     # all controls, must be green
    python experiments/M-PHASE0-PHASE/src/p1_bar.py          # derives the bar
    python experiments/M-PHASE0-PHASE/src/p2_census.py       # the census
    python experiments/M-PHASE0-PHASE/src/p3_verdict.py      # the joint gate
    python experiments/M-PHASE0-PHASE/src/check_note.py      # independent verifier
    python experiments/M-PHASE0-PHASE/src/commission_note.py # plants, must all be caught

---

## Amendment 1 — three refinements forced by building the instrument

Written after `p0_controls.py` was green and **before** `p1_bar.py` was run. None of
these is a result; all three are design corrections that building the algebra exposed.

### A1.1 `κ` depends on the output frequency, so a target has several alias geometries

Section 3 wrote the system matrix as though a target fixed one set of representatives. It
does not. Which representative of each coset lands inside the target band depends on where
the output frequency `ν` sits, so `κ` is a function of `ν` as well as of `{d_i}`. The set
of distinct geometries is data-independent, small, and enumerated once: **G-1x has exactly
two** — the diagonal `(½,½)` and the anti-diagonal `(½,−½)` — and a quincunx unfolds along
one or the other depending on the quadrant of the band. RB-1x also has two; G-2x and RB-2x
have eight each. (Distinctness is taken up to column permutation and up to negating all
representatives, both of which leave every singular value alone.)

**Registered consequence:** every statistic is computed per geometry, and the **site-level
summary is the worst over geometries** — the largest `κ`, the smallest bar — because a
reconstruction has to serve the whole band, not its most convenient quadrant. The median
over geometries is reported alongside. Taking the best geometry would have been a
researcher degree of freedom worth roughly a factor of two, and it is closed here.

### A1.2 The registered `η < 1` bar is conservative, and the realistic comparator is also reported

Section 4 defined the no-attempt comparator as "keep the baseband, discard the aliases",
whose error is exactly `‖x_alias‖`, giving `η = 1`. That comparator assumes the baseband is
recovered *perfectly*. What actually ships does not: averaging the frames and zeroing the
aliases leaks alias energy into the baseband estimate, so its error is
`sqrt(1 + |leak|²/‖x_alias‖²) ≥ 1`.

So **`η < 1` demands the unfolder beat something better than the real alternative.** It is
kept as the primary registered bar precisely because it is the conservative one, and the
realistic per-trial comparator `η_naive` is computed in the same trial, with the same noise
and the same scene draw, and reported alongside. Both bars appear in the note. Bias B7's
declared direction is unchanged: the noiseless read still favours C1.

### A1.3 Infeasible is a reported category, not a dropped row

`N < M` and lattice-degenerate configurations return `κ = ∞`. These sites are **counted and
reported as infeasible**, never dropped from the denominator and never silently
pseudo-inverted. A site that cannot be solved at all and a site that is merely poorly
conditioned are different claims, and the winnable-fraction denominators in §9 include
both. This is what control C-B and plant 2 exist to protect: the instrument shipped with a
`smin > 0` rank test that reported `κ = 3.2e15` for a degenerate system instead of
infeasible, and the control caught it.

---

## Amendment 2 — the bar depends on the scene, and the first run assumed the most generous one

Written after `p1_bar.py` ran once and **before** its corrected re-run. The first run's
output is retained as `out/p1_bar_rho1_SUPERSEDED.json` so the correction can be audited
rather than taken on trust.

### A2.1 `plib.unfold_trial` drew a white scene, which is the best case, not a neutral one

Section 4 defined `eta = ||xhat - x|| / ||x_alias||` and left the scene implicit. The
implementation drew all `M` components independently at unit variance, so the aliases
carried `M-1` times the baseband energy. Real scenes do not: spectra fall off, and the
alias representatives sit at strictly higher spatial frequency than the baseband one, so
they carry **less** energy, not more.

The direction is not neutral and is declared here. `||x_alias||` is the denominator of
`eta`, so overstating it **understates** `eta` and **inflates** the bar. It also cripples
the naive comparator, because the energy the naive method throws away is exactly
`||x_alias||`. Both effects favour C1. The first run's headline — a tolerance near
**0.84 px at kappa = 1** — is therefore registered as an **upper bound on the bar**, not
the bar.

### A2.2 The scene ratio becomes an explicit swept parameter

Define

    rho = E|x_k|^2 / E|x_0|^2,  k >= 1

the per-alias-component energy relative to the baseband component at the same output
frequency. `rho = 1` is the white scene the first run assumed. The bar is registered from
here on as a function of **two** variables, `bar(kappa, rho)`, and `rho` is swept over
`{1, 0.3, 0.1, 0.03, 0.01}`.

Two consequences are predicted before the run, so that failing to see them falsifies the
model rather than being absorbed into it:

1. **The bar tightens monotonically as `rho` falls.** Less alias energy means less to win
   and a smaller denominator.
2. **`eta_naive -> 1` as `rho -> 0`.** With little alias energy there is little to leak,
   so the realistic comparator converges on the idealised one and the two registered bars
   must converge too. This is a self-consistency check on the whole construction, and it
   is registered as control C-Y.

### A2.3 The headline `rho` is modelled from measured spectral falloff, and the model is disclosed

The alias frequencies of the G-1x problem sit above the warp plane's Nyquist — the plane is
a 2x2 bin of the sensor, so it reaches `0.25 cyc/sensor-px` while the aliases sit near
`0.5` — and are therefore **not directly measurable** from any plane-resolution product in
this repository. Pretending otherwise would be the kind of unearned number this lane exists
to remove.

So the headline `rho` is obtained by fitting a power law `S(f) ~ f^-beta` to the measured
plane spectrum of real captures over the band where it *is* observable, and extrapolating
to the alias frequency. The fitted `beta`, the extrapolation factor, and the bar's
sensitivity to `beta` are all reported. If the bar's verdict flips within the measured
spread of `beta`, the lane reports NOT ROBUST rather than picking a `beta`.

### A2.4 Censoring in the `bar ~ 1/(C kappa)` fit is a defect and is repaired

The first run swept `sigma` only to 1.0 px and then **dropped** every configuration that
had not yet crossed its threshold. That keeps the configurations that crossed early and
discards the ones that never crossed, which biases the fitted `C` upward and is a silent
selection on the outcome variable. The re-run extends the grid until crossings are
interior, and any configuration still censored is **counted and reported** rather than
dropped — the same rule Amendment A1.3 already imposed on infeasible sites.

The first run also reported an IQR ratio of **11.21** for `G-1x/naive`, meaning
`bar * kappa` was not remotely constant. Section 4.1's `eta ~ C kappa sigma` is therefore
already known to be a poor single-parameter summary for at least one arm, and the re-run
reports the spread rather than the median alone.

### A2.5 Duplicate cached warpmaps disagree, so the census needs a canonical-map rule

Control C-X measured `kappa` across every cached sidecar for each stack and found the same
stack's duplicates disagreeing by up to a factor of **117** (`dry` 1.488 .. 50.460;
`113MSDCF` 1.554 .. 47.007; `coffee` 1.499 .. 29.221). These are not rounding differences;
they are different alignments produced under different strategies and spans.

Registered rule, fixed before the census runs: a stack's canonical map is the one whose
`strategy` and `note` match the product's current default path, with **zero refusals** and
the **largest placed count**; ties break on the lexicographically smallest digest. The
chosen digest is recorded per stack in the note, and the census is additionally repeated
across *all* maps of each stack as a robustness ladder. If the verdict flips across that
ladder, the lane reports NOT ROBUST.

---

## Amendment 3 — A2.2's predictions were falsified, and the diagnosis found a real defect

Written after the controls were re-run and **before** the corrected bar is derived. A2.2
registered two predictions precisely so that they could fail. They did. This amendment
records what failed, why, and what the failure exposed.

### A3.1 What was predicted, and what actually happened

A2.2 predicted (1) the bar tightens as `rho` falls, and (2) `eta_naive -> 1` as
`rho -> 0`. The instrument returned `eta` **bit-identical** across a 100x change in `rho`,
so both predictions were false and the bar did not move at all. Control C-Y failed, as it
was built to.

### A3.2 The cause: the model dropped the phase that the displacement actually carries

Section 3 wrote the system matrix as `A[i,k] = exp(j 2 pi <h_k, d_i>)`. That is wrong. A
displaced frame shifts the **whole** scene, not just its alias replicas, so replica `k`
arrives with the phase of its **own frequency**, `nu + h_k`:

    y_i = sum_k X_k exp(j 2 pi <nu + h_k, d_i>) = exp(j 2 pi <nu, d_i>) sum_k X_k exp(j 2 pi <h_k, d_i>)

so `A = D V` with `D = diag(exp(j 2 pi <nu, d_i>))`.

Because `h_0 = 0`, dropping `D` makes column 0 of `V` identically all-ones **for every
displacement**, so `Vhat e_0 = V e_0` exactly and `(pinv(Vhat) V - I) e_0 = 0` exactly. The
baseband was therefore recovered perfectly no matter how wrong the displacements were, all
error landed in the alias coefficients, and `eta`, a ratio of two quantities that both
scaled as `sqrt(rho)`, could not depend on `rho` at all. Measured first column of the error
operator under the old model: **3.42e-16**. Under the corrected model: **0.0551**.

**This is a defect that flattered C1**, and it had been through a full commissioning pass —
11 controls and 6 plants — without firing, because every one of those controls tested the
algebra of `V` and none tested whether `V` was the right matrix.

### A3.3 What survives untouched, and why

`D` is diagonal and unitary, so it leaves every singular value of `A` alone. **`kappa` is
exactly invariant to `nu`** — measured at `3.09e-14` relative across all four targets, every
geometry and four frequencies including one far outside the band (control C-AA). So every
conditioning result in this lane, and the entire census, which computes `kappa` with no
reference to any output frequency, stands unchanged. The defect was confined to the
reconstruction-error model, which is precisely where the bar comes from.

### A3.4 The comparator had the same defect, in the opposite direction

With `D` restored, averaging the raw measurements models a comparator that **never aligns**
— it sums frames with unremoved per-frame carrier phase and destroys its own baseband. That
is a strawman and it flatters the unfolder. The comparator now derotates by
`conj(Ahat[:, 0])`, which is exactly the estimated common phase, i.e. it aligns on the
**same estimated displacements the unfolder uses**, then averages, then zeroes the aliases.
Giving the comparator exact displacements would be equally unfair in the other direction.

Two structural consequences are now checked rather than assumed: at `sigma = 0` the
unfolder recovers exactly (`eta ~ 1e-15`) and `eta_naive` is **exactly** independent of
`rho` (measured spread `0.0e+00` across `rho` from 1 to 0.01), because with perfect
alignment every term in the comparator's error scales as `sqrt(rho)` along with the
denominator.

### A3.5 The corrected predictions, registered before the headline run

1. The bar tightens monotonically and **strictly** as `rho` falls. Displacement error now
   corrupts the baseband, and that corruption does not shrink with the alias energy, so it
   dominates as `rho -> 0`. Measured on one configuration at `kappa = 1.72`:
   `0.2818, 0.2290, 0.1719, 0.1081, 0.0650` px for `rho = 1, 0.3, 0.1, 0.03, 0.01`.
2. `rho = 1` gives the loosest bar of any `rho` (control C-Z). A2.1's claim was therefore
   right, but for the wrong reason and by luck: under the model as implemented it was not
   false but **vacuous**.
3. `nu` is swept over the fundamental band and the site summary is the **worst** over `nu`,
   which subsumes A1.1's worst-over-geometries rule rather than sitting beside it, since
   the geometry is a function of `nu`.

### A3.6 The consequence for the bar, stated before it is computed

The proposal's unsupported "~0.1-0.15 px" now sits **inside** the measured range rather than
outside it, but it corresponds to a particular `rho` near 0.1-0.03 rather than to a
geometric fact. So the lane's deliverable is not a single number: it is `bar(kappa, rho)`,
plus a defensible `rho` with its uncertainty. A2.3's problem — that the alias frequencies
sit above the warp plane's Nyquist and cannot be measured directly from anything in this
repository — is **not** dissolved by this correction and still has to be answered.

A3.7 records the standing methodological point: **a commissioned instrument is only
commissioned against the questions its controls ask.** Fifteen green controls did not
notice that the system matrix was the wrong matrix, because all of them tested that matrix's
algebra. The control that caught it was the one that tested a *physical* prediction about
the scene, and it caught it by failing.

---

## Amendment 4 — the bar, and a second gate the proposal does not mention

Registered **after** running `p1_bar.py` under the A3-corrected model. Section 4's
definition and A3.5's predictions were registered before the run; the bar values in A4.1
are the registered measurement. **A4.2 is not a registered prediction — it is an
exploratory finding**, discovered by inspecting rows the run produced for another purpose,
and it is labelled as such wherever it is used.

### A4.1 The bar, measured

`out/p1_bar.json`. 320 random `(N, nu, d)` draws per target, `M`-dependent `N` ladders,
1000 trials per point, sigma grid `{0} u geomspace(1e-3, 2, 31)`. Displacement clustering
scale drawn log-uniformly over `[0.02, 3.0]` px so the ill-conditioned tail is populated
rather than left to chance.

Median `bar_unit` (px), noiseless, pooled over `nu` and `N`:

| `rho` | G-1x | RB-1x |
| --- | --- | --- |
| 1.00 | 0.1401 | 0.0414 |
| 0.30 | 0.1235 | 0.0385 |
| 0.10 | **0.1006** | 0.0336 |
| 0.03 | 0.0678 | 0.0252 |
| 0.01 | 0.0433 | 0.0168 |

Two things follow.

**The proposal's number is vindicated, and my first attempt at it was the artifact.** The
superseded alias-only model gave 0.836 px — six to eight times more generous than the
proposal's asserted "~0.1-0.15 px", which is what made it suspicious enough to audit. The
corrected model puts G-1x at **0.1006 px** at `rho = 0.1` and **0.1401 px** at `rho = 1`.
The proposal's undefended assertion sits squarely inside the measured range. It was right;
the derivation it never showed would have agreed with it.

**The bar is a transfer function, not a number.** `kappa * bar` is far flatter than `bar`
itself — 0.20 to 0.38 across four decades of conditioning for G-1x — so the census's usable
form is approximately `bar ~ 0.36 / kappa` in the ill-conditioned tail where sites actually
live. `rho` scales it roughly as `rho^0.3`. The single scalar that replaces `[bar]` in the
proposal is **0.10 px**, and it is only correct at `kappa ~ 3` and `rho ~ 0.1`.

Censoring, per A2.4: **0 of 4480** rows failed to cross inside the sigma grid. The grid is
adequate and no row was dropped.

### A4.2 The noise gate (EXPLORATORY, not preregistered)

419 of 4480 rows have `bar_unit = 0` — unfolding is harmful at *every* displacement
accuracy including exact. Their distribution is the finding:

| SNR | G-1x | RB-1x |
| --- | --- | --- |
| inf | 0 / 1600 | 0 / 1600 |
| 30 dB | 31 / 320 | 123 / 320 |
| 20 dB | 93 / 320 | 172 / 320 |

Not one noiseless row is harmful, at any conditioning: all 1600 recover exactly
(`eta` at `sigma=0` has median 1.7e-15, max 1.55e-12 at `kappa = 10862`). Every zero-bar row
is a *noise* row. So C1 is gated twice, not once:

1. **the registration gate**, `sigma_delta < bar(kappa, rho)` — the gate the proposal asks
   about; and
2. **the noise gate**, `kappa < kappa_max(SNR)` — which the proposal does not mention.

The second gate is sharp, not gradual. Choosing the best single `kappa` threshold
misclassifies 2.2-4.1% of rows, and the fraction of (surviving, dead) pairs ordered the
wrong way is 0.003-0.007:

| SNR | target | best `kappa` threshold | misclassified |
| --- | --- | --- | --- |
| 30 dB | G-1x | 23.4 | 7 / 320 |
| 30 dB | RB-1x | 70.7 | 9 / 320 |
| 20 dB | G-1x | 9.6 | 13 / 320 |
| 20 dB | RB-1x | 24.5 | 7 / 320 |

`eta` at `sigma=0` fits `0.0544 * kappa^0.875` at 30 dB and `0.172 * kappa^0.875` at 20 dB;
the 3.16x noise ratio moves the threshold by 3.7x, consistent with the fitted exponent
(3.16^(1/0.875) = 3.75). The two fits differ only in the constant, which is the signature of
a noise-amplification gate rather than a modelling coincidence.

**The unit matters and is easy to overclaim.** `snr_db` in `plib` is defined per frame at
the working spatial frequency (`plib.py:337-339`: signal power `1 + (M-1)*rho`). That is
*not* global image SNR. Near Nyquist the OTF has attenuated the signal while the noise
stays white, so a frame that looks like 40 dB globally can be far worse at the frequency
being unfolded. The census must therefore estimate SNR **at the working frequency from the
data**, and must not import a global figure. Until it does, the numbers in this section fix
the *shape* of the gate and not its location on any real stack.

### A4.3 Consequence for the census and the verdict

`p2_census.py` must report the joint survival of both gates, not the registration gate
alone, and must report them separately so a site killed by noise is not miscounted as a
site killed by registration. `p3_verdict.py`'s ladders gain SNR as an axis. A site is
winnable only if `sigma_delta < bar(kappa, rho)` **and** `kappa < kappa_max(SNR)`.

Because A4.2 is exploratory, the verdict must state the fraction of the field it excludes
under both readings — with the noise gate applied and with it ignored — so a reader can see
exactly how much of the conclusion rests on an unregistered finding.

---

## Amendment 5 — C-X was wrong, the aligner is deterministic, and the census gets a better rule

A2.5 recorded duplicate cached warpmaps disagreeing "by up to a factor of 117" in `kappa`
and built a canonical-map rule around that. **A2.5's premise is withdrawn.** The factor of
117 was an artifact of my own grouping, and the underlying reproducibility worry was tested
directly and falsified.

### A5.1 Two defects in C-X, both mine

`clib.list_maps` groups sidecars by `name.split("-", 1)[0]`, the filename prefix. For
hyphenated stack names that is not the stack. The group C-X called `coffee` pooled
**`coffee-bean` and `coffee-bubbles`, which are different scenes**, and the group it called
`dry` pooled the `dry-erase-marker-head-cpl` variants. Comparing `kappa` across that group
compares different subjects, so the spread it reported was never a reproducibility figure.

The second defect survives the first: even grouped correctly by the authoritative
`stack-name` header, a stack's sidecars have **different frame counts** -- `109MSDCF` has
maps at N = 1, 3, 4, 6, 8, 12 and 22. Those are the N-ladder subsets other lanes generated,
not repeat alignments. Comparing them measures how conditioning varies with N, which is a
real thing this lane already measures on purpose, and not disagreement between alignments.

### A5.2 The reproducibility question, asked properly and answered

Restricting to sidecars at each stack's **full** frame count with zero refusals and every
frame placed leaves genuine candidates, and those still differed: all-but-the-reference
frame, median 0.11 / 0.18 / 0.024 plane px for `113MSDCF` / `119MSDCF` / `coffee-bubbles`.
Every pair shared reference frame, identity frame, strategy, note and cycle-floor
bit-for-bit, and the `coffee-bubbles` pair was written one minute apart. That is a strong
circumstantial case for non-determinism in `strehl align`, which -- given the bar of
0.10 sensor px derived in A4.1 -- would have been close to decisive for C1 on its own,
because a method cannot be more accurate than it is repeatable.

So it was tested rather than asserted. `strehl align` was run four times on
`D:\personal\macro\coffee-bubbles`: twice at the default thread count and twice at
`--threads 1`, the latter arm included because non-associative floating-point reduction
under thread scheduling is the obvious candidate mechanism.

**All four runs are bit-identical** (placement payload SHA256 `667f9de55069d163` in every
case), and identical across thread counts. `strehl align` is deterministic. The hypothesis
is falsified and the worry it raised for C1 is withdrawn.

The regenerated digest also equals the *majority* cached digest for that stack -- four of
the six `coffee-bubbles` sidecars carry `667f9de55069`. So the minority sidecars were
produced by a configuration or a build that differed in some field the header does not
print. Consistent with that, the sidecar **filename is a content-addressed cache key**: two
sidecars for one stack with different filenames are, by the aligner's own accounting,
different (input, configuration) tuples. They were never repeat runs.

### A5.3 The canonical-map rule, replaced

A2.5's rule picked among cached artifacts of unknown provenance and broke ties on an
admittedly arbitrary digest ordering. Since the aligner is deterministic, that is
unnecessary. **Replacement rule, fixed now:** the census runs on warpmaps
**regenerated for this lane** by the shipping binary at its default configuration, written
to `out/canon/<stack>.warpmap.txt`, with the placement-payload SHA256 recorded per stack in
the note. Anyone can reproduce them exactly with the command in section 13.

This is strictly better than A2.5: the substrate is reproducible on demand, its provenance
is known rather than inferred, and no arbitrary tie-break is needed.

The cached sidecars are retained as a **sensitivity arm**, since they represent real
configuration variation (resampler, span set, N), and the census is still repeated across
them. But they are no longer evidence of irreproducibility, and the note must not cite them
as such.

### A5.4 What this costs the lane, stated plainly

A5.2 removes an argument that would have favoured a KILL verdict. Recording it is not
optional: the case for non-determinism was assembled here, in this document, before it was
tested, and it looked strong. It was wrong. The registered verdict thresholds in section 9
are unchanged and the lane is no closer to a KILL than it was before C-X ran.

---

## Amendment 6 — an independent re-derivation of the model, and what it caught

A `rubber-duck` sub-agent was given the measurement model, the A3 diagnosis and the
`plib` implementation, and asked to re-derive the algebra from first principles by a
route of its own choosing. It used Poisson summation rather than a discrete-DFT
argument. Its report is the reason this amendment exists.

### A6.1 What it confirmed

Independently derived and agreeing with A3:

- `y_i = sum_k X_k exp(j 2 pi <nu + h_k, d_i>)` -- the phase carries the **full**
  frequency `nu + h_k`. A3's central correction is right.
- `A = D V` with `D` diagonal unitary, therefore `A^H A = V^H V` and **every singular
  value** of `A` equals that of `V`, so `kappa(A) = kappa(V)` exactly. This is stronger
  than control C-AA, which only measured the condition number; the whole spectrum is
  invariant. C-AA measured 3.09e-14 and is consistent.
- `(Vhat^+ V - I) e_0 = 0` exactly whenever `Vhat` has full column rank. Measured 3.42e-16.
- `eta = O(rho^(-1/2))` as `rho -> 0`, so a **weaker** alias signal makes the displacement
  tolerance **tighter**. A2.2's registered prediction had this backwards and A3.5 corrected
  it; the re-derivation confirms the corrected direction.

It also supplies the closed form A4.1 measured empirically: `bar ~ sqrt(rho) / |nu|`. The
measured exponent moves from `rho^0.26` over the full sweep to `rho^0.41` over the last
decade, approaching the predicted `rho^0.5` as `rho` falls. That is a non-trivial predicted
trend confirmed against data that was collected before the prediction was read.

### A6.2 Blocking issue 1: a global translation is not an unfolding error (REAL, CORRECTED)

The scene is determined only up to a global translation: displacing every frame by a common
`c` and rephasing the scene by `exp(-j 2 pi <nu + h_k, c>)` produces identical data.
`plib.unfold_trial` drew `delta` iid per frame, which puts a common component of standard
deviation `sigma / sqrt(N)` into every trial. Part of the error it charged the unfolder for
was therefore a re-choice of origin and not a failure to unfold.

**Direction, declared before measuring:** removing a gauge removes error, so the corrected
bar can only be **looser**, which makes C1 **easier**. This is the direction that favours
the conclusion already reached, so it gets the greater scrutiny, not the lesser.

Corrected by adding a `gauge` argument. `"zero_mean"` subtracts the mean of `delta` over
frames, which to first order is exactly the gauge direction and nothing else. **Both reads
are now reported and neither is allowed to stand alone**: `"raw"` also bounds the local
geometric error and is the conservative read; `"zero_mean"` isolates the unfolding question
C1 actually asks.

Measured effect on the bar (`out/p1_bar.json`, 7680 rows):

| `rho` | G-1x raw | G-1x zero-mean | ratio | RB-1x ratio |
| --- | --- | --- | --- | --- |
| 1.00 | 0.1401 | 0.1613 | 1.152 | 1.002 |
| 0.10 | **0.1006** | **0.1231** | 1.224 | 1.014 |
| 0.01 | 0.0433 | 0.0587 | 1.355 | 1.004 |

**The headline survives.** G-1x moves from 0.1006 to 0.1231 px at `rho = 0.1`; both sit
inside the proposal's asserted 0.1-0.15 px. RB-1x does not move at all, because at `M = 4`
and `N >= 4` the common component is smaller and the alias structure dominates.

### A6.3 Where the measurement refines the re-derivation

The report predicted that the gauge is what produces the `rho^(-1/2)` divergence, implying
that removing it would remove the divergence. **It does not, and the reason is instructive.**
Because `h_0 = 0`, the first column of `V` is the constant vector, so `V^+` maps the common
component of `q` exactly onto `e_0`: the gauge is precisely a pure baseband error. But the
*relative* part of the `nu` term acts on `X_0` as well, and it survives the projection. So
`eta` keeps its `rho^(-1/2)` behaviour after gauge fixing, and the measured ratio
`eta_zm / eta_raw` is flat at 0.67-0.76 across two decades of `rho` and across `N` in
`{3, 4, 6, 8}` rather than falling as the report's `(1 + rho) / (3 rho)` would require.
Both statements are consistent with its own algebra; the asymptotic was applied outside the
regime where it is the whole story.

### A6.4 Blocking issue 2: a wording defect in A3.2 (REAL, CORRECTED HERE)

A3.2 says the superseded model recovered "the baseband perfectly however wrong the
estimates were" and that "all error landed in the aliases". **That is wrong as written and
is corrected here.** `E_V e_0 = 0` is a statement about the first *column*, not the first
*row*: baseband **input** sources no error, but alias input can still leak **into** the
estimated baseband, since `Xhat_0 - X_0 = sum_{k>=1} (E_V)_{0k} X_k` is generically nonzero.

The conclusion A3.2 drew from it is unaffected -- `eta` is still exactly `rho`-invariant
under the superseded model, because `E_V x = E_{V,:,1:} x_{1:}` depends only on the alias
coefficients -- but the sentence claimed more than the algebra supports and would have
misled a reader. The corrected statement is: **baseband input causes no reconstruction
error.**

### A6.5 Qualifications accepted, and their standing

Three limits on the model, none of which invalidate a result already recorded:

1. **The `M`-term model assumes a target band limit.** Poisson summation has infinitely many
   aliases; frequencies outside the modelled band contribute a coherent residual, which is
   structured bias and not white noise. Bias B6 already covers truncation and
   `plib.unfold_mismatch` already measures it.
2. **`kappa` is `nu`-invariant only for a fixed alias-representative set.** Changing which
   representative `h_k` is used to wrap a frequency into the Nyquist square changes `V`
   itself. `plib.band_frequencies` returns the representative set alongside each `nu` for
   exactly this reason, and A1.1 already treats distinct representative sets as distinct
   geometries.
3. **Per-frame gain variation enters at the same order as phase error** when
   `|gamma_i| ~ 2 pi |f| |delta_i|`, and unlike the phase it is not protected by the
   `h_0 = 0` structure. **This is not currently modelled and is now an open item.** It can
   only make C1 harder, so it does not threaten a KILL verdict; it would threaten a SURVIVE
   one. Recorded as such rather than quietly absorbed.

### A6.6 Standing note

A6.2 and A6.4 were both found by an agent that had no stake in the answer, in an instrument
that had already passed 15 controls and 6 plants. This is the second time in this lane that
a defect survived a full commissioning pass, and the reason is the same one A3.7 recorded:
the controls tested the algebra the model already contained. Neither the gauge freedom nor
the column/row distinction was anything the existing controls asked about.

--------------------------------------------------------------------------------

## Amendment A7 -- the achievable floor, the averaging measurement, and rho

Registered after measuring. A7.1 through A7.3 execute section 4's plan and are
reported as preregistered. **A7.4 (rho) is EXPLORATORY**, as A4 was: the
preregistration named rho as a scale factor on the bar but did not specify how it
would be measured, so the instrument that measures it was designed with the
answer's direction already visible. It is recorded here so that the reader can
discount it accordingly, and its bias direction was declared in the script before
it was run.

### A7.1 What accuracy the aligner achieves (`src/p4_floor.py`)

Section 4 derived what registration accuracy the unfolding NEEDS. This measures
what the aligner DELIVERS, which is the other half of the verdict.

Two figures bracket the truth. The cycle-consistency floor is optimistic -- it is
the aligner's self-consistency and a systematic error shared by every edge is
invisible to it. Held-out reprojection is pessimistic -- it includes model error
the unfolding would not have to pay. The floor is the correct one to compare
against the bar, because the bar asks how well the pose is KNOWN.

The shipped `cycle-floor-px` pools spans 1 through 128. Almost all of that range
is out of scope: the unfolding registers frames that are within a depth of field
of one another. Recut to within-DOF spans only (span <= 8):

    median over 7 stacks     0.583 sensor px
    range                    0.267 -- 1.430
    best single stack        0.267  (113MSDCF)
    innermost annulus, best  0.139  (113MSDCF, radius decile 1 of 10)

Span 1 does not appear: the tightest triple (i, i+1, i+2) has outer span 2, so a
cycle-consistency floor at span 1 is unmeasurable by construction.

Against a bar of 0.1006 raw / 0.1231 gauge-fixed at kappa ~ 3 and rho = 0.1, the
median stack misses by 4.7x and the best whole stack by 2.2x. Only the innermost
annulus of the single best stack comes near, and it is still above the raw bar.

### A7.2 Averaging does not rescue it (`src/p5_gain.py`)

One escape was live and could not be settled by argument. A global solve uses many
edges. If per-edge errors were independent, the solved pose could beat the per-edge
floor by roughly sqrt(k) -- with k of 10 to 100 that is 3x to 10x, which is exactly
the size of the gap. C1 would survive on that alone.

Measured directly from the data with no solver in the loop: for each measured
short-span edge, compare one two-hop path's prediction error against the mean of
all available paths' predictions. That ratio IS the realised averaging gain.

    realised gain     1.00 -- 1.28x, median 1.07x
    iid prediction    2.24x

The positive control is the load-bearing one here, because a gain of 1.0 is also
what a broken instrument reports. On planted iid noise the instrument reads 1.45x;
on a planted systematic error shared across paths it reads exactly 1.000x. It can
see gain when gain exists.

Registration error at within-DOF spans is therefore SYSTEMATIC, not random, and
does not average down. The best achievable figure anywhere in the census, after
whatever averaging is really available, is **0.225 sensor px**.

### A7.3 The bar has a ceiling (`src/p6_ceiling.py`)

This is a recut of `p1_bar.json`, not fresh evidence, and is kept in a separate
script so it cannot be mistaken for one.

The bar is proportional to 1/kappa and kappa is a condition number, so kappa >= 1
and the bar cannot be loosened without limit. Verified rather than assumed: the
minimum kappa over all 7680 rows is 1.0278. At the best-conditioned decile
(kappa ~ 1.16), which is the most favourable geometry that exists anywhere in the
census:

    rho = 1      0.245 raw / 0.292 gauge-fixed sensor px
    rho = 0.1    0.157 / 0.211
    rho = 0.01   0.070 / 0.101

So C1 survives only if rho ~ 1 AND the site is in the best-conditioned decile AND
the stack is the best of the seven. That is a narrow escape but it is a real one,
and it made rho the last free parameter in the argument.

### A7.4 rho is zero, because the optics cannot reach the alias band (EXPLORATORY)

`src/p7_rho.py`. Bias direction declared in the script before running: three
approximations all INFLATE rho (unmeasurable aliases charged at the detection
ceiling, residual chroma sitting exactly at the alias frequencies, unremoved noise
landing in the alias band), and a larger rho LOOSENS the bar and FAVOURS C1.
Subtracting the shot floor is the one step that cuts against C1, so it is estimated
at the 10th percentile to deliberately under-subtract.

Substrate: Sony ILCE-7CM2, pitch 5.1227 um, Nyquist 97.6 cyc/mm, FE 100mm F2.8
Macro GM with a 2x teleconverter.

    stack            F     f_die (cyc/pitch)   cyc/mm   diffraction cutoff, m=2
    113MSDCF        11           0.181          35.4            0.28
    112MSDCF        11           0.181          35.4            0.28
    foam             8           0.248          48.4            0.39
    coffee-bean      8           0.190          37.0            0.39
    coffee-bubbles   8           0.256          50.0            0.39
    109MSDCF        11           0.144          28.1            0.28
    119MSDCF       5.6           0.210          41.1            0.55

Every stack's scene spectrum sinks into its own photon shot noise between 0.144 and
0.256 cycles/pitch, against a Nyquist of 0.500. The nearest G-1x alias frequency is
at 0.354 and most lie beyond 0.5. Of the 64 band frequencies, 52 to 60 have to be
skipped because their own power is already at the floor -- a ratio there would be a
zero over a zero, and the skipped count is reported separately so it cannot be read
as a measured one. Over the frequencies that can be scored, rho is ~1e-297: zero to
the limit of measurement.

The optics agree with the measurement independently. At m ~ 2 the effective aperture
is about 3x the marked one, and the resulting diffraction cutoff (last column) lands
at or just above the measured die-off in all seven cases. There is no content at the
alias frequencies because the lens cannot form any.

**m is the one soft spot.** It is not in EXIF (`FocusPosition2` and `SubjectDistance`
are both absent) and the cutoff scales as 1/(1+m). The script reports the ladder
m in {0, 1, 2}; m = 0 is physically impossible for macro but is listed because it is
the most favourable case C1 could claim. Even at m = 0 the cutoff is 0.83 and the
measured f_die is unchanged -- the measurement does not depend on m at all. Pinning
m from `30-calibration-grid` would tighten the physical corroboration, not the
measurement.

### A7.5 Verdict on C1

    needed, loosest possible (kappa ~ 1.16, rho = 1)    0.245 raw / 0.292 gauge-fixed
    needed at the measured rho (-> 0)                   below 0.070 / 0.101
    achievable, best anywhere after real averaging      0.225
    achievable, median stack                            0.583

At rho = 1 the best stack at the best-conditioned decile would just barely clear the
gauge-fixed bar. That is why rho decided the lane. At the measured rho the bar is
tighter than 0.101 and the best achievable figure misses it by 2.2x; the median
misses by 5.8x.

**C1 is KILLED**, and the kill is robust in the direction that matters: every
approximation in the rho instrument was biased to favour C1, the averaging escape
was measured rather than argued, and the aligner was proven deterministic in A5 so
the floor is not an artefact of run-to-run variation.

### A7.6 Instrument defects found, and the pattern

Five in `p7_rho.py` alone, and the two that matter most were both invisible to a
passing tally:

1. The white-scene control read 2.9x low for both targets. All 64 alias lookups fell
   past the last radial bin, and that bin was a degenerate FFT-corner bin reading
   0.048 against a true flat level of 0.139 -- ratio 2.89, matching exactly.
2. `plib.coset_reps` does not return the minimum-modulus coset member. It picks a
   canonical representative for the conditioning algebra. For a falling spectrum
   that names a member carrying far less power than its neighbour: every G-1x
   representative sat at |f| >= 0.795 while nearer members existed.
3. C-A went INERT. After the band was truncated to 0.5 the plant sat at |f| = 0.707,
   outside the measurable range, so it moved nothing -- and an inert plant is
   indistinguishable from a caught one in a tally that counts only greens. This is
   the second inert plant in this lane (the first was `p4_controls` plant 1, which
   patched `flib.then` while the generator BUILT with `then`, so generator and
   checker shared the defect and cancelled exactly).
4. Every stack reported rho of exactly 9.0000 -- the white-scene value. `mosaic()`
   gain-normalises by each channel's mean and a dark frame's mean is ~0 after black
   subtraction, so the noise spectrum exploded and swamped the signal. All six
   synthetic controls passed throughout this failure, which is why five data-side
   controls now exist.
5. rho still read 9.0000. The spectrum collapses 200x between f = 0.02 and 0.09 and
   then goes FLAT from 0.2 to 0.5. A diffraction-limited OTF is monotone decreasing
   to its cutoff, so a flat spectrum out to Nyquist is impossible: that plateau is
   photon shot noise, which a dark frame (read noise only, 3.8e-06 against a plateau
   of 3.3e-04, a factor of 87) never captures. Scene power was being charged for it.

The exposure control took two attempts and the first failure is worth recording.
Varying ISO at fixed exposure does not change shot noise relative to signal, because
ISO is gain applied after the photodiode and the electron count never moves. The
first C-I expected the plateau to track ISO and read 1.0x over a 13x span -- correct,
and completely uninformative. The lever is EXPOSURE. The same capture holds
matched-ISO 1/2 s against 1/8 s pairs, 4x the light: plateau 3.62x (predict 4),
scene 1.02x (predict 1), over 10 pairs. That is the control that means something.

--------------------------------------------------------------------------------

## Amendment A8 -- RETRACTION of A7's KILL verdict

**A7 reported C1 KILLED. That verdict is withdrawn. C1 is UNREFUTED.**

Withdrawn on independent verification by an agent that was given the argument, the
scripts and the data, and was asked to break it. It did, on three independent
load-bearing defects, any one of which voids the verdict. It confirmed it made no
change to this lane (`git diff --exit-code` clean) and reproduced every published
number before attacking it, so the defects are in the reasoning and the
instruments, not in the reproduction.

"Unrefuted" is not "verified". C1 has not been shown to work. It has not been shown
not to.

### A8.1 rho was never measured (CRITICAL)

`p7_rho.py`. Every alias frequency for the frequencies that could be scored lies
ABOVE the retained band. For 113MSDCF the four scored base frequencies sit at
|nu| = 0.0884 and their nearest alias is at 0.6187, while `radial_power` truncates
at 0.5. Across all seven stacks, **0 of 36 (or 0 of 108) alias lookups were inside
the measured spectrum.** Every one was extrapolated at the last retained bin, and
the `np.minimum.accumulate` envelope had already driven that bin to the 1e-300
floor. The reported rho ~ 1e-297 IS that floor. It is not a measurement of anything.

The lane's own conservative arm, `rho_g_floored`, reads **9**, and 9 does not kill
C1. A7 quoted the arm whose unknown tail had been set to zero and dismissed the
arm that retained the detection limit as "vacuous". That was backwards: the
floored arm is the honest one, and it is the one that had to be argued against.

There is a deeper problem than the truncation. Aliased power in a sampled signal
appears INSIDE the band -- that is what aliasing means. Reading power AT the alias
frequency of the continuous scene is not something one frame's periodogram can do
at all. Bounding rho needs either a genuine optical model or a measurement at a
finer sampling than the channel being tested. `rho_bound` as written cannot bound
rho, and no fix to the truncation repairs that.

### A8.2 "flat means noise" is false (CRITICAL)

A7 argued that a diffraction-limited OTF is monotone decreasing to its cutoff, so a
spectrum flat from 0.2 out to Nyquist cannot be scene content and must be shot
noise. The premise about the OTF is true. The inference does not follow, because
the captured spectrum is the object spectrum TIMES the OTF, and nothing constrains
the object.

Demonstrated, not argued: a planted **noiseless** scene with genuine flat
high-frequency content was classified by `shot_floor` as noise and driven from a
true rho of 8.99869 to 7.5e-300. And the object spectrum required is unremarkable
-- with a cutoff at 0.70 cyc/pitch, H(0.35) = 0.391 and H(0.50) = 0.175, so a PSD
proportional to 1/H^2 needs only **4.98x** more object power at 0.50 than at 0.35
to produce a flat captured plateau.

The exposure control (C-I) remains live and does establish exposure-dependent shot
noise on the paper capture at 3.62x against a predicted 4x. It establishes that
shot noise is present. It does not establish that any given plateau is ENTIRELY
shot noise, which is what the subtraction assumed.

Two further errors here. `f_die` is the FIRST threshold crossing, not the first
crossing that stays below: every stack rebounds afterwards, 2 to 19 times, by up to
6725x the floor for 109MSDCF, and the persistent crossing is 0.49792 for all seven.
And the 10th-percentile plateau was chosen to guarantee under-subtraction, but
measured against this repository's own sensor-noise model it runs as high as 10.84x
the predicted noise for coffee-bubbles, so it does not.

### A8.3 the averaging proxy is capped at sqrt(3) (CRITICAL)

`p5_gain.py:58-71`. The estimator scores the single path AND the averaged paths
against the same **noisy direct edge**, so that edge's own error appears in
numerator and denominator alike. For k independent two-hop paths the proxy reads
sqrt(3 / (1 + 2/k)), which is 1.464 at k = 5 and approaches sqrt(3) = 1.732 however
many paths are added.

Measured on scalar iid noise: true gain 2.2395x, proxy 1.4643x.

So A7's positive control, which "read 1.45x on planted iid noise", was reporting
**the proxy's own ceiling**. A7 compared that 1.45 against sqrt(k) = 2.24 and read
the difference as headroom, concluding the instrument could see gain when gain was
present. It could not. The control was CAPPED, not sensitive, and the real data's
1.07x has to be read against 1.46x rather than 2.24x.

The conclusion that within-DOF registration error is systematic is therefore
unproven. It may still be true; this instrument cannot say.

### A8.4 the "ceiling" is a median, and the headline is a corner (CRITICAL / HIGH)

`p6_ceiling.py:54-69` takes the **median** bar among rows below the 10th-percentile
kappa and calls it a ceiling. A ceiling is a maximum. From the same registered
`p1_bar.json`, at rho = 0.01, G-1x:

    reported "ceiling"      0.0703 raw / 0.1009 gauge-fixed
    actual maximum          0.2557 raw / 0.3093 gauge-fixed   (kappa 1.573, nu 0.088, N 8)
    99th percentile         0.1988 raw / 0.2337 gauge-fixed
    maximum at N <= 6       0.2079 raw / 0.2471 gauge-fixed

Both maxima exceed the 0.2250 A7 called best achievable. The bar depends on nu, N
and gauge as well as kappa, so kappa >= 1 does not deliver the asserted scalar
ceiling and A7.3's argument does not stand.

Separately, the 0.2250 headline is a **corner** statistic: `p5_gain` drops the
radius dimension that `p4_floor` had deliberately introduced. The same p5 transforms
on the same stack read **0.0801 sensor px at field centre** and 0.1168 at the first
annulus. Against a gauge-fixed bar of 0.1009, the aligner at field centre is at or
inside the bar. A7 compared a corner against a median and reported the ratio as a
margin.

### A8.5 the physical corroboration does not corroborate (MEDIUM)

`p7_rho.py:425-429` uses N_eff = N(1+m), which implicitly fixes pupil magnification
at one. This repository already records a **measured** bellows factor
B = N_eff/N in [2.41, 3.06]. Under that bound:

    f/5.6   cutoff 0.5435..0.6901 cyc/pitch    vs G alias start 0.3536   ABOVE
    f/8     cutoff 0.3805..0.4831              vs 0.3536                 ABOVE
    f/11    cutoff 0.2767..0.3513              vs 0.3536                 at/just below

So the optics CAN form green aliases in the f/5.6 and f/8 stacks. Even A7's own
m = 2 column puts four of seven stacks above the alias start. And the printed m = 2
cutoff is 1.51x to 2.64x the reported f_die, so it is a loose upper bound well away
from the measured die-off, not an independent confirmation of it.

Truncating at radial 0.5 also discards precisely the green-diagonal alias
neighbourhood, where five stacks carry median power between 1.43x and 23.4x the
selected floor. A7 declared residual chroma an upward bias favouring C1 and then
discarded its strongest location.

### A8.6 the controls, and the lesson

C-A is INERT for the third time in this lane. Its carrier is
`outer(cos(0.45x), cos(0.45y))`, whose spectral centre is at radius 0.6364, and
only 3.56e-13 of its windowed energy survives the 0.5 truncation. It passes through
endpoint leakage, not because the plant lands in the measured band. A7 recorded
fixing this defect and did not fix it. C-D is labelled "planted alias content" but
plants nothing and never calls `rho_bound`.

`p5_gain`'s four controls generate their base edge set with `flib.synth_consistent`,
which calls `flib.then`, and check with `flib.then`. Patching `then` to a reversed
composition left **all four passing** -- the identical generator/checker cancellation
this lane documented in A7.6 for `p4_controls` plant 1 and then reproduced.

Controls confirmed live: C-W, C-S, C-M, C-I, and the four data-side checks.

**The lesson A7 should have drawn and did not: a control can be CAPPED rather than
blind, and a capped control reads exactly like a sensitive one.** A positive control
must be calibrated against what the estimator reads when the effect is FULLY
PRESENT, not against the effect's true magnitude. A7 had 1.45 against an expected
2.24 and called the instrument sensitive; 1.45 was all it could ever read.

### A8.7 what is actually known

    C1 status                      UNREFUTED. Not verified. Not killed.
    rho                            UNMEASURED. Conservative reading 9. No valid bound exists.
    achievable accuracy            reproduces exactly: 0.267..1.430 sensor px pooled,
                                   but 0.0801 at field centre on the best stack
    averaging gain                 UNMEASURED; the estimator is capped at sqrt(3)
    the bar                        unchanged and still registered; A7.3's ceiling is void

The strongest surviving evidence against C1 is weak: a 63-crop probe over frames and
field positions found no radial excess near the alias boundary on the two stacks
examined (high-band/floor max 1.04). That suggests C1 may be UNPRODUCTIVE on these
scenes. It is not a refutation.

**No verdict may be filed for C1 until rho has a defensible bound.** The next step
is not another attempt at the same measurement -- `rho_bound`'s approach is
structurally unable to answer the question. It needs either a measurement at finer
sampling than the channel under test, or a forward optical model with the measured
bellows factor rather than N(1+m).

--------------------------------------------------------------------------------

## Amendment A9 -- a representative-sign defect in plib, and a real rho at last

Two findings from `experiments/M-PHASE0-RHO` (commit `4d7adf2d`), an independent lane
that ran to completion after I had wrongly recorded it as having produced nothing.
Both are confirmed here.

### A9.1 `full_reps` uses `nu + h` where `coset_reps` defines `nu - h` (CONFIRMED)

`plib.coset_reps` documents its own construction as "the element h with **nu - h**
in [-c/2, c/2)^2 is h = g + c * floor((nu - g)/c + 1/2)". `plib.full_reps` then
builds the phase-carrying frequencies as **`nu + h`**. The two disagree.

Reproduced directly:

    target   components   nu+h in band   nu-h in band
    G-1x        128            64            128
    RB-1x       256            64            256

Half of every G-1x system matrix and three quarters of every RB-1x one were built
from frequencies outside the target band. M-PHASE0-RHO's physical translation
control separates the two cleanly: absolute error **0.302143 under `nu+h`** and
**exactly 0 under `nu-h`**. An error of exactly zero on a physical control is the
discriminator; the band-membership count above only corroborates it.

Note that `nu+h` and `nu-h` differ by `2h`, which is a lattice vector whenever the
coset representative is half-integral, so both name the SAME replica. They do not
give the same phase, because a sub-pixel displacement is not on the sampling lattice.
The choice is therefore not cosmetic and is not absorbed by any gauge.

**This reaches the bar, not just rho.** With the corrected sign the pooled G-1x bar
moves from 0.095635 to **0.123212** at rho = 0.1, and from 0.039717 to **0.044721**
at rho = 0.01. Every bar figure in A7 and every figure in `p1_bar.json` is suspect
until `p1` is rerun with the corrected sign.

### A9.2 rho is approximately 0.0055, not 0 and not 1 (ADOPTED)

M-PHASE0-RHO measured it on undemosaiced data with a noise-aware estimator,
commissioned 12 PASS / 0 FAIL with 10 planted defects CAUGHT / 0 MISSED:

    G     0.00552   (95%  0.00185 -- 0.01078)
    RB    0.00530   (95%  0.00214 -- 0.00891)
    census range for design decisions   0.0001 -- 0.06

with raw 0.108817 and dark-only 0.108586 falling to 0.0055165 under full noise
subtraction -- so the noise correction is the whole measurement, which is exactly
where A7 went wrong in the other direction.

Its stated limits are adopted with it. Only **9 of 46** records directly detect
high-band power. Scenes vary by 5.84x and f/8-to-f/18 by 4.51x. A grid refinement
changes the median by **30.49x**, so no rho is meaningful without stating the
frequency grid and boundary convention. It explicitly refuses a universal scalar,
and that refusal is adopted: A2.2's common-scalar framing does not survive.

It also independently identifies A7.4's normalisation as wrong -- the nine-member
statistic returns 9 for green and 27 for red/blue on a white scene where A2.2's
normalisation requires 1. That is the same defect A8.1 retracted, found by a
different route.

### A9.3 consequence

rho ~ 0.0055 is far below the rho ~ 1 that A7.3 showed C1 needs at the loosest
geometry, so the direction of A7's conclusion may well survive. **It is not
re-asserted here.** The bar must first be rerun with the corrected representative
sign, and the verdict must then be resolved by field radius rather than pooled,
because A8.4 established that achievable accuracy is 0.0801 sensor px at field
centre against 0.2256 at the corner. A pooled comparison cannot decide a claim whose
two sides both vary by 3x across the field.
