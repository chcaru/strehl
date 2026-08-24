# M90 round 2 — pre-registration: measuring `rho_warp`

**Written and committed before any result exists.** Nothing in this file was
edited after a measurement was seen. If a bar below is changed later, the change
and both values are reported in the milestone report.

Commissioned by the orchestrator after M90 round 1 recorded `rho_warp` as an
unmeasured constant with a **30.8x lever** on predicted sigma at `n_eff` = 44
(fact 1194). M86 landed `crates/strehl-core/src/align.rs` the same night, which
is what makes this reachable: the correlation is *induced by resampling*, and
until M86 there was no resampler in `crates/` to induce it.

---

## 1. What `rho_warp` is, stated precisely enough to be falsified

PRNU is a **fixed multiplicative pattern**: photosite `u` has response
`1 + p_u`, with `Var(p) = kappa^2` and `kappa` = 0.3096% MEASURED (fact 1062,
replicated independently in M90 round 1).

The merge does not materialise warped frames; it **gathers** (`align.rs` module
header, `gather_into` doc). So at output pixel `x`, frame `k` contributes a
resampled PRNU error

```text
e_k(x) = sum_j w_j( t_k(x) ) * p_{ u_j( t_k(x) ) }
```

where `w` is the resampling kernel and `t_k` maps reference coordinates to
source coordinates. Two quantities follow, and **both are needed** — reporting
either alone lets a reader compute the noise floor wrong:

- **`W`, the within-frame attenuation.** `W = Var(e_k) / kappa^2`. For a white
  pattern and a separable kernel, `W = (sum_i wx_i^2)(sum_j wy_j^2)`. Any kernel
  wider than nearest-neighbour is a lowpass and **attenuates the pattern inside
  a single frame**. `W = 1` for Nearest by construction.
- **`rho_warp`, the between-frame correlation.**
  `rho_kl = Cov(e_k, e_l) / sqrt(Var(e_k) Var(e_l))`.

The merged PRNU variance over `n` frames is then

```text
Var_merged / (kappa^2 S^2) = W * [ 1/n + (n-1)/n * rho ]   ==  F
```

**`F` is the primary measurand of this milestone**, not `rho` — because `F` is
what `predicted_sigma` gets wrong, and because `F` is measurable without
committing to the `W`/`rho` decomposition. `rho` is reported as a derived
quantity for continuity with fact 1194.

Two reference points bracket `F`:

| case | `F` | meaning |
| --- | --- | --- |
| `rho = 1`, `W = 1` | `1` | M90 round 1's bound: PRNU does not average down at all |
| `rho = 0`, `W = 1` | `1/n` | PRNU averages down exactly like temporal noise |

Define **`n_prnu = 1/F`**, the effective number of independent PRNU samples the
merge actually achieves. `n_prnu = 1` is the pessimistic bound; `n_prnu = n` is
the optimistic one. **`n_prnu` is the number I will hand back.**

---

## 2. A contradiction with the commissioning brief, registered in advance

The brief asks for:

> **a null** (an identity warp must induce `rho_warp` = 0 to a stated
> tolerance — if it does not, the instrument is measuring something else)

**Under the convention fact 1194 and M90 round 1 use, this is stated in the
wrong direction, and an instrument that passed it as written would be broken.**
`rho_warp = 1` means "does not average down"; `rho_warp = 0` means "averages
down like temporal noise". An identity warp makes every frame sample *the same
photosites*, which is perfect correlation: **`rho_warp` = 1, `F` = 1,
`n_prnu` = 1.**

I record this before running anything, and I resolve it by registering **both**
controls rather than picking one:

- **N2** is the identity null in the sense I believe was intended for the
  normalisation: identity warp must give `F` = 1.
- **N1** is the null in the sense that makes the brief's sentence true, and it
  is a genuinely good control: **an input with no fixed pattern at all must
  yield zero induced inter-frame correlation under any warp.** That is the
  placebo, and it is what actually tests "the instrument is measuring something
  else".

If the measurement shows I am wrong about the direction, the measurement wins
and the report says so.

---

## 3. The instrument

**The temporal-noise problem.** A PRNU map estimated from real flats is
`P = p + noise`. Correlating a map with itself would measure the noise as if it
were pattern. Solved by **estimating the pattern twice from disjoint flat
halves** — `P_A = p + n_A`, `P_B = p + n_B`, with `n_A` independent of `n_B` —
and only ever correlating an `A` against a `B`:

```text
Cov( gather(P_A, t_k), gather(P_B, t_l) )  =  Cov( e_k, e_l )  +  0
```

The temporal term vanishes in expectation from **numerator and denominator
alike**, so the instrument needs no knowledge of the noise level and no
subtraction of an estimated floor.

**The n^2 problem, and why there isn't one.** `F` needs `sum_{k,l} Cov(e_k,e_l)`
over all `n^2` pairs. But that sum is exactly

```text
sum_{k,l} Cov(e_k, e_l) = Cov( sum_k e_k , sum_l e_l )
```

so accumulating `merged_A = (1/n) sum_k gather(P_A, t_k)` and `merged_B`
likewise gives `F = Cov(merged_A, merged_B) / Cov(P_A, P_B)` in **O(n)**. This
is not an approximation of the merge; it *is* the merge, run on the pattern
instead of on the scene.

**Warps.** Real, measured, from M86's committed edge tables
(`experiments/M86-alignment/out/*-edges.csv`), solved to a placement with
`align.rs`'s own solver. Not planted, not assumed. `align.rs` is read-only to
this milestone and is called, never edited.

**Per-resampler.** Every number is reported for `Resampler::Nearest`,
`::Bilinear` and `::CatmullRom` separately. M86 flagged that its resampler
comparison on real frames is NOT MEASURED; this is the instrument that settles
it.

---

## 4. Registered bars

### N1 — placebo. **Must show no effect.**

Replace `P_A` and `P_B` with two independent synthetic noise fields sharing no
fixed pattern. Warp with the real placement.

> **PASS if** the induced inter-frame covariance is under **5%** of the value
> the same code path returns on real PRNU, for all three resamplers.

**If this fails, every other number in this milestone is void** — it would mean
the resampler is manufacturing inter-frame correlation out of independent noise.

### N2 — identity null. Normalisation check.

All `t_k` = identity.

> **PASS if** `F` = 1 within **±0.01** for all three resamplers, and
> `n_prnu` = 1 within ±0.01.

Catmull-Rom and bilinear are interpolating, so identity is exact at integer
positions; a failure here is a coordinate-convention bug, not physics.

### N3 — decorrelation bound. The other bracket.

Plant a distinct translation of **50 px** on each frame — far beyond every
kernel's support.

> **PASS if** `F` < **2/n** for all three resamplers.

### P1 — positive control, kernel ladder, **with values predicted from first
principles before running.**

Two frames, frame 0 identity, frame 1 planted at exactly `(+0.5, +0.5)` px, on a
**synthetic white** field so the kernel arithmetic is the only thing under test.
Measure `Cov(e_0, e_1) / Var(e_0)`.

Separable kernel overlap gives, in 1D, `Nearest` 0 (0.5 rounds away from zero to
the neighbouring site), `Bilinear` `[1,0]·[0.5,0.5]` = 0.5, `Catmull-Rom`
`[0,1,0,0]·[-0.0625,0.5625,0.5625,-0.0625]` = 0.5625. Squaring for 2D:

| resampler | support | **predicted** `Cov(e_0,e_1)/Var(e_0)` |
| --- | ---: | ---: |
| `Nearest` | 0.5 | **0.0000** |
| `Bilinear` | 1.0 | **0.2500** |
| `CatmullRom` | 2.0 | **0.3164** |

> **PASS if** all three land within **±0.02** of the predicted value **and** the
> ordering is strictly `Nearest` < `Bilinear` < `CatmullRom`.

This is stronger than the brief's "measurably higher correlation than a narrow
one, in the predicted direction": it predicts the *numbers*, so a hit is not
attributable to luck about a sign.

**Registered caveat on P1's real-PRNU counterpart.** Real PRNU is not perfectly
white — M71 measured a green nearest-neighbour ACF of about 0.45% — and the
high-pass used to isolate the pattern removes low frequencies. The real-field
arm of P1 is therefore expected to sit slightly **above** the synthetic
predictions. That arm carries no pass/fail; only the synthetic arm does.

### P2 — the real measurement, and what would make it not worth acting on.

> **The correction is NOT worth making if** `n_prnu` > `0.5 * n_eff` across the
> radial range on every real stack, i.e. PRNU averages down at least half as
> well as temporal noise everywhere the pipeline operates. In that case fact
> 1194's 30.8x lever collapses and M90 round 1's `rho = 1` quotation is simply
> wrong and should be retracted.

> **The `rho = 1` bound is CONFIRMED as operational, not merely bounding, if**
> `n_prnu` < 2 at the plane centre on stacks with `n_eff` > 20.

Both outcomes are reported. I expect a **radially varying** answer — breathing
is a scale term, so the induced shift is near zero at the warp centre and
largest at the corner — and if that is what I find, a single scalar `rho_warp`
is the wrong shape for the constant and I will say so.

### P3 — sign and magnitude of the sigma correction at real `n_eff`.

Report the change in `Estimator::predicted_sigma` at the `n_eff` values M90
round 1 measured on real stacks (1.35, 4.99, 7.26, 10.11, 22.89, 44.19), at
measured `F` against `F` = 1 and `F` = 1/n.

> **Registered prediction (may be wrong):** the correction is **positive**
> (the shipped model is over-confident) at every `n_eff`, and its magnitude
> **grows monotonically with `n_eff`**.

### N4 — planted defect (rule 12).

Plant a defect in the instrument, confirm the harness catches it, restore from a
**temp copy** — never `git checkout --`, which in this shared tree reverts to
HEAD and can destroy a sibling's uncommitted work.

---

## 5. Unidentifiability exit

If `F` cannot be separated from its nuisance terms with the captures on hand —
as M88's cutoff could not be, where the nuisance was 3x the signal — the
registered response is to **say so, name the capture that would fix it, and
stop**. That is a complete result. The specific hazard here is that the
high-pass radius that isolates the pattern also sets the spatial bandwidth over
which correlation is measured, so a `rho` that is really a statement about the
high-pass is the failure mode to watch for. **Registered diagnostic: repeat the
real measurement at two high-pass radii. If `F` moves by more than 20% between
them, `F` is a property of my filter and not of the sensor, and I stop.**

---

## 6. What this milestone will NOT do

- **Not** wire `rho_warp` into `PlaneNoise::variance`. Fact 1063's ruling
  stands. Measure the constant, price the blast radius, give the ruling.
- **Not** flip any default. Five siblings are mid-flight.
- **Not** edit `align.rs`, `merge.rs`, `stack.rs`, `main.rs`, or any module M89
  creates.
