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
