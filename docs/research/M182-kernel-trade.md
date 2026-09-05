# M182 — the range-safe kernel trade

**Status: MEASURED, SYNTHETIC, SHIPPING-CODE PROBED.** This lane prices the
resampler itself. It does not change a default, score an end-to-end M8-R render,
or claim that one axis clears the scorecard.

## 1. Answer

The kernel claim is true for the shipping `Nearest` and `Bilinear` gathers.
Nearest is a one-hot copy. Bilinear's one-dimensional weights are non-negative
and sum to one; the two-dimensional weights are their products, so they too are
non-negative and sum to one. Either output is therefore inside the scalar hull
of the source samples it consumed, for every phase and every finite input.
This is a construction property, not clipping.

`CatmullRom`, `Lanczos2`, and `Lanczos3` have negative lobes and all leave the
source hull on both adversarial plants. `ClampedCatmullRom` also returns a
range-safe value, but only because it applies the destructive, nonlinear clamp
that the scorecard has already preregistered as a defeat.

The detail trade is not free. Unrestored Bilinear loses modulation relative to
the default progressively across the band. The existing restoration can buy
most or more than all of that amplitude back in the upper band, but the strong
arm materially amplifies two-dimensional white-noise standard deviation. A
regularised arm with less noise cost ceases to match Catmull-Rom over most of
the band. Nearest's unit-amplitude MTF is a known blind spot: it preserves a
sinusoid's magnitude while applying phase-quantisation error, and its
truth-referenced RMS error exposes the loss.

**One-sentence answer:** **Conditional only — Bilinear obtains a range-safe
gather today, but the existing restoration gets close to eliminating its
detail deficit only by trading it for amplified noise; without accepting that
noise trade, no.**

## 2. Scope, units, and approach

The experiment is entirely synthetic and opened no RAW file. The Rust probe in
`experiments/M182-kernel-trade/src/main.rs` calls the production
`Resampler::sample`, `gather_mtf`, `design_fir`, and `restore_plane` functions.
The Python driver independently evaluates the exact formulas in
`restore.rs::tap`, checks unique source anchors before running, and writes the
curves and canonical JSON.

Two approaches were considered. A Python-only port was simpler, but it could
only prove agreement with itself. Adding a production example was unnecessary
and outside the lane's preferred boundary. The chosen standalone experiment
crate lives under the owned path and links `strehl-core` by path, so production
source remains untouched while all shipping behavior is measured directly.

**CANONICAL FREQUENCY CONVENTION:** `f` is cycles per gather-plane sample; plane Nyquist is `0.5`; for a demosaiced output `f_output cycles/pixel = f_plane / 2`.

Thus the three requested locations, 0.25, 0.5, and 0.75 of plane Nyquist, are
respectively 0.125, 0.25, and 0.375 cycles per plane sample, or 0.0625, 0.125,
and 0.1875 cycles per demosaiced output pixel. Restoration is evaluated with
`grid_factor=1`, matching the shipping `RestorePlan`, because restoration runs
on the CFA planes themselves (`restore.rs:1394-1403`). No transfer is evaluated
past the plane's Nyquist and no folded response is admitted.

**CANONICAL METHOD COUNTS:** raw-tap extrema use `1,000,001` phases; the complete tap-sum table uses `4,097`; shipping tap/overshoot probes use `131,072`; MTF uses `64` phases at `257` frequencies including DC and Nyquist.

The full per-phase sum table is `tap-phase-sums.csv`; the full MTF and
restoration curves are `mtf-curve.csv` and `restoration-curve.csv`.

## 3. Overshoot: proof and measurement

### 3.1 Convex-hull proof

For source values \(x_i\), let \(m=\min_i x_i\), \(M=\max_i x_i\), and let
\(w_i\geq0\) with \(\sum_i w_i=1\). Then

\[
m = \sum_i w_i m \leq \sum_i w_i x_i \leq \sum_i w_i M = M.
\]

Nearest has exactly one unit weight. Bilinear has weights `[1-f, f]` in each
axis for \(f\in[0,1]\); its 2-D weights are outer products and retain both
properties. This establishes hull containment without a data-dependent
operation. It remains true when the warp's phase changes from pixel to pixel,
even though that spatial variation means the whole warped image has no single
shift-invariant OTF.

### 3.2 Tap sweep

Table K1 distinguishes the raw f64 values returned by the private
`restore.rs:146-181` `tap()` model from the normalized f32 weights recovered by
delta-probing `align.rs`'s shipping sampler. “Negative mass” is
\(-\sum\min(w_i,0)\) at the worst phase. The last column is the largest error
when a constant plane is gathered; this is the operational DC check.

| kernel | most-negative raw `tap()` | max raw negative mass | raw tap-sum range | most-negative shipping response | max shipping negative mass | max constant-DC error |
|---|---:|---:|---:|---:|---:|---:|
| Nearest | `+0.000000000` | `0.000000000` | `[0.000000000000, 1.000000000000]` | `+0.000000000` | `0.000000000` | `0.000e+00` |
| Bilinear | `+0.000000000` | `0.000000000` | `[1.000000000000, 1.000000000000]` | `+0.000000000` | `0.000000000` | `0.000e+00` |
| CatmullRom | `-0.074074074` | `0.125000000` | `[1.000000000000, 1.000000000000]` | `-0.074074075` | `0.125000000` | `2.384e-07` |
| ClampedCatmullRom | N/A (pre-clamp: CatmullRom) | N/A (pre-clamp: CatmullRom) | N/A (nonlinear) | N/A (nonlinear) | N/A (nonlinear) | `0.000e+00` |
| Lanczos2 | `-0.086441525` | `0.127368704` | `[1.000000000000, 1.018949632446]` | `-0.085363202` | `0.125000004` | `1.192e-07` |
| Lanczos3 | `-0.147266663` | `0.270189823` | `[0.994298548810, 1.000000000000]` | `-0.147996381` | `0.271739140` | `1.788e-07` |

Three sum findings matter:

1. Bilinear is exactly a partition of unity throughout the sweep.
2. The raw Lanczos functions are not partitions of unity. This does not become
   a shipping brightness ripple because both `gather_mtf` and the align
   samplers normalize the phase's taps before use. The constant-plane probe
   confirms the effective gather preserves DC to f32 precision.
3. The symmetric `Nearest` model in `restore.rs::tap` gives both candidates
   zero weight at the exact half-sample tie. The shipping sampler instead uses
   `round()` and selects the upper sample. The fixed midpoint quadrature in
   `gather_mtf` never lands on the tie, so its existing self-test does not see
   the model discrepancy. It is measure-zero for the phase average but is a
   real exception to “raw taps sum to one at every phase.”

There is no `tap()` value for `ClampedCatmullRom`: `restore.rs` deliberately
panics before evaluating one because the gather is nonlinear. Its pre-clamp
polynomial is Catmull-Rom; reporting those as effective clamped weights would
falsely imply superposition.

### 3.3 Step and impulse

The numeric plants are horizontal 1-D signals replicated down a 2-D plane, so
the vertical pass is an exact identity while the shipping two-dimensional
sampler executes. Both span 0–1000 DN. Table K2 gives the maximum distance
outside that input range over all sampled positions and phases.

| kernel | analytic verdict | unit-step maximum | unit-impulse maximum |
|---|---|---:|---:|
| Nearest | cannot: one-hot copy | `0.000000 DN (0.000000%)` | `0.000000 DN (0.000000%)` |
| Bilinear | cannot: convex weights | `0.000000 DN (0.000000%)` | `0.000000 DN (0.000000%)` |
| CatmullRom | can: negative lobes | `74.074219 DN (7.407422%)` | `74.074074 DN (7.407407%)` |
| ClampedCatmullRom | cannot after destructive support clamp | `0.000000 DN (0.000000%)` | `0.000000 DN (0.000000%)` |
| Lanczos2 | can: negative lobes | `85.363281 DN (8.536328%)` | `85.363205 DN (8.536320%)` |
| Lanczos3 | can: negative lobes | `117.810791 DN (11.781079%)` | `147.996384 DN (14.799638%)` |

The Catmull-Rom step maximum here is larger than the familiar half-phase
example because this sweep asks for the worst phase rather than fixing the
phase at one half.

## 4. Detail cost

For the five supported linear kernels, the primary curve is the production
`restore::gather_mtf`: the magnitude of the normalized tap DTFT, averaged over
64 midpoint phases. A shipping-sampler cosine measurement cross-checks it.
`ClampedCatmullRom` has no OTF, so its row is instead the fundamental amplitude
of the same unit-cosine plant through the shipping nonlinear sampler. That row
is stimulus-conditioned and must not be used as a general transfer function.

Each MTF cell in Table M1 is `absolute / relative-to-CatmullRom`. “Not reached”
means the curve stays above the threshold through plane Nyquist, not that a
crossing was extrapolated.

| kernel | MTF @ 0.25 Nyq | MTF @ 0.50 Nyq | MTF @ 0.75 Nyq | MTF50 | MTF10 |
|---|---:|---:|---:|---:|---:|
| Nearest | `1.000000 / 1.004503x` | `1.000000 / 1.063556x` | `1.000000 / 1.277959x` | not reached | not reached |
| Bilinear | `0.949651 / 0.953928x` | `0.811592 / 0.863174x` | `0.627956 / 0.802501x` | `1.000000 Nyq (0.500000 c/plane; 0.799922x CR)` | not reached |
| CatmullRom | `0.995517 / 1.000000x` | `0.940242 / 1.000000x` | `0.782498 / 1.000000x` | not reached | not reached |
| ClampedCatmullRom | `0.995517 / 1.000000x` | `0.940242 / 1.000000x` | `0.779170 / 0.995747x` | not reached | not reached |
| Lanczos2 | `0.995714 / 1.000198x` | `0.941573 / 1.001417x` | `0.787116 / 1.005902x` | not reached | not reached |
| Lanczos3 | `1.003601 / 1.008121x` | `1.011455 / 1.075739x` | `0.886158 / 1.132474x` | not reached | not reached |

Nearest demonstrates why magnitude-only MTF is insufficient for a
phase-quantising sampler. Table M2 is RMS error against the analytically shifted
unit-amplitude cosine, on the same frequency grid. Lower is better.

| kernel | RMS error @ 0.25 Nyq | RMS error @ 0.50 Nyq | RMS error @ 0.75 Nyq |
|---|---:|---:|---:|
| Nearest | `0.159683` | `0.315691` | `0.464481` |
| Bilinear | `0.039284` | `0.150877` | `0.317004` |
| CatmullRom | `0.005559` | `0.061949` | `0.230735` |
| ClampedCatmullRom | `0.005559` | `0.061949` | `0.232094` |
| Lanczos2 | `0.007350` | `0.055847` | `0.227087` |
| Lanczos3 | `0.003431` | `0.011153` | `0.118798` |

## 5. Restoration and conditioning

### 5.1 Controlled restoration definition

The restoration trade uses a flat signal spectrum \(S(f)=1\) and reports
\(\lambda=\sigma^2/S\). Its exact autocorrelation input is
`r[0]=1+lambda, r[k>0]=0`; `design_fir` subtracts `sigma2` and therefore sees
the registered flat unit signal at every frequency. `gain_cap=4`, which does
not bind any one-dimensional inverse here, and the production four outer taps
are used.

For a symmetric 1-D FIR with full coefficient energy \(E=\sum_k g_k^2\), IID
noise standard deviation changes by \(\sqrt E\) after one pass. The shipping
restoration is separable, so after both image axes the standard-deviation ratio
is \(E\). These are post-restoration / pre-restoration noise SD ratios, not
spatial scene SD and not a temporal sensor-noise estimate.

Table R1 gives the minimum primary MTF on the closed in-band curve, its 2-D
diagonal product, the corresponding ideal inverse bounds, and the noise cost
of the production nine-tap FIR designed at zero regularisation. The gain range
is the realised FIR response. Values marked `*` for the clamped kernel are only
the cosine-fundamental minima, not conditioning numbers.

| kernel | minimum H, 1-D | minimum H, 2-D diagonal | max inverse, 1-D / 2-D | output-noise SD, 1-D / 2-D | realised FIR gain range | well-posed LSI inverse? |
|---|---:|---:|---:|---:|---:|---:|
| Nearest | `1.000000` | `1.000000` | `1.000000x / 1.000000x` | `1.000000x / 1.000000x` | `[1.000000, 1.000000]` | yes |
| Bilinear | `0.500000` | `0.250000` | `2.000000x / 4.000000x` | `1.379254x / 1.902341x` | `[1.000000, 1.969467]` | yes |
| CatmullRom | `0.625061` | `0.390701` | `1.599844x / 2.559500x` | `1.173710x / 1.377595x` | `[0.993870, 1.570395]` | yes |
| ClampedCatmullRom | `0.625061*` | `0.390701*` | N/A | N/A | N/A | N/A |
| Lanczos2 | `0.633494` | `0.401314` | `1.578548x / 2.491813x` | `1.168007x / 1.364241x` | `[0.994200, 1.550870]` | yes |
| Lanczos3 | `0.638272` | `0.407391` | `1.566730x / 2.454642x` | `1.107216x / 1.225927x` | `[0.987059, 1.505802]` | yes |

Bilinear never approaches zero inside the band: the inversion is bounded, not
singular. In 2-D its worst case is the Nyquist corner, where both separable
axes carry the minimum. The sub-unity realised minima for some inverse FIRs
are finite-tap least-squares ripple; `RestoreConfig::gain` constrains the
target to be at least one, but `design_fir` does not impose that inequality on
every realised frequency.

### 5.2 Bilinear restoration trade

Table R2 shows `restored Bilinear MTF / unrestored CatmullRom MTF`. The noise
column is the full two-axis output/input SD factor. “Band at/above CR” counts
the 257 registered frequency samples; the tiny nonzero floor in the weak arms
is the common DC point.

| lambda = sigma2/S | 2-D noise SD | @ 0.25 Nyq | @ 0.50 Nyq | @ 0.75 Nyq | @ 1.00 Nyq | band at/above CR | worst relative MTF |
|---:|---:|---:|---:|---:|---:|---:|---:|
| `0` | see R1 | `0.994709 / 0.999189x` | `1.002879 / 1.066619x` | `1.002100 / 1.280643x` | `0.984734 / 1.575420x` | `74.7082%` | `0.993649x` |
| `0.001` | `1.893610x` | `0.993571 / 0.998046x` | `1.001412 / 1.065058x` | `0.999472 / 1.277285x` | `0.981017 / 1.569474x` | `73.9300%` | `0.992975x` |
| `0.01` | `1.818374x` | `0.983687 / 0.988117x` | `0.988315 / 1.051129x` | `0.976475 / 1.247895x` | `0.948760 / 1.517868x` | `68.0934%` | `0.986118x` |
| `0.03` | `1.670908x` | `0.965371 / 0.969718x` | `0.959466 / 1.020446x` | `0.929565 / 1.187946x` | `0.883728 / 1.413826x` | `57.1984%` | `0.969708x` |
| `0.1` | `1.314015x` | `0.944241 / 0.948494x` | `0.865813 / 0.920841x` | `0.799995 / 1.022360x` | `0.709350 / 1.134850x` | `29.1829%` | `0.916615x` |
| `0.15` | `1.159179x` | `0.950260 / 0.954539x` | `0.822167 / 0.874421x` | `0.725094 / 0.926640x` | `0.622874 / 0.996501x` | `0.3891%` | `0.873047x` |
| `0.2` | `1.056308x` | `0.951674 / 0.955960x` | `0.808928 / 0.860340x` | `0.660364 / 0.843917x` | `0.557513 / 0.891934x` | `0.3891%` | `0.835339x` |
| `0.3` | `1.000000x` | `0.949651 / 0.953928x` | `0.811592 / 0.863174x` | `0.627956 / 0.802501x` | `0.500000 / 0.799922x` | `0.3891%` | `0.795852x` |

The answer is a curve, not “restoration fixes it.” The strongest arm nearly
flattens the Bilinear transfer, beats the default over the upper part of the
band, and still misses it slightly elsewhere because the realised FIR is
finite. That arm has the largest noise cost in R1. As the Wiener regulariser
reduces that cost, the portion of the band matching the default collapses.
No tested setting simultaneously matches Catmull-Rom over the whole sampled
band and leaves noise unchanged.

## 6. Controls and commissioning

The MTF instrument has a null, an inert arm, and both directions of response:
adding a constant does not move the fitted AC amplitude, a known three-tap
sharpener moves it up, and a known blur moves it down. The restoration
application control runs production `restore_plane` on deterministic white
input and compares measured SD gain with the exact energy of the returned
taps.

| control | observation | result |
|---|---|---:|
| MTF direction (`f=0.375`) | `0.627956` baseline; `0.627956` after inert `+137 DN`; `0.895952` sharpened; `0.091962` blurred | PASS |
| model vs shipping sampler | max `|delta MTF| = 2.294e-08` (bar `< 2.0e-06`) | PASS |
| restoration noise application | measured `1.313270x`, tap-energy prediction `1.313721x`, `|delta|=0.000451` (bar `< 0.005`) | PASS |
| structural/null arms | convex step+impulse zeros; high-noise restoration identity; production `restore::selftest` | PASS |

**INERT COMMISSION ANCHOR:** changing this sentence alone must not affect any measurement check.

`commission.py` mutates every canonical report line once and every semantic
predicate once, entirely in memory. Each mutation is first tied to an exact
unique full line; a zero-match or duplicate-match is a hard error. It also
changes the inert sentence and adds unrelated result metadata, both of which
must remain green.

**CANONICAL COMMISSION RESULT:** `74` checks passed; `74` planted defects caught; `0` missed; `2/2` inert arms survived; the sharpened positive control remained above baseline.

## 7. Provenance and reproducibility

Source identities at measurement:

| source | SHA-256 |
|---|---|
| `crates/strehl-core/src/restore.rs` | `3AB5C6660B7A45837AC4B5560078092E6AAFA9C85A041A935E95B0CD77533AFD` |
| `crates/strehl-core/src/align.rs` | `6D33F0E24F21D4370CCD8DF0BF618E54A5AD615B838BC265469B4F85051C2786` |
| `crates/strehl-cli/src/align_cmd.rs` | `B3DE7738151A6BC0500C66DD916F9FCB20CDB9BE0BF698AD00425D3EBB397C69` |

Artifact identities:

| artifact | size | SHA-256 |
|---|---:|---|
| `probe.tsv` | `13192` lines | `D4A6E392EEC5E79FC5A527BD001F8EEDC51A89BDB2F566D3068F196A33A877D9` |
| `mtf-curve.csv` | `1543` lines | `E62CB73BD0725E156D2A6BE197D2C1A694BFBA31570367E11C811B035262D663` |
| `restoration-curve.csv` | `11566` lines | `588F9BB207C914C93C53734CDF4DB509EAFB32ED8FC7D13BB169333D08BF43B3` |
| `tap-phase-sums.csv` | `24583` lines | `2309EF871F5A1EAAA7A206F2F9DB614DE4A152E52B74369DB955B997590FF171` |

Commands, from the `strehl` repository root:

```powershell
cargo test --release --manifest-path experiments/M182-kernel-trade/Cargo.toml
python -B experiments/M182-kernel-trade/analyze.py
python -B experiments/M182-kernel-trade/verify.py
python -B experiments/M182-kernel-trade/commission.py
```

The observed Rust test result was three passed, zero failed. The analysis
matched all 12 unique source anchors, emitted the complete Rust-probe trailer,
and passed every measurement control. Final verification passed all registered
checks; commissioning caught every planted defect, preserved both inert arms,
and preserved the sharpened positive control.

## 8. What differed from the supplied premise

The six variants, Catmull-Rom default, and restoration support map all match the
supplied context. Three qualifications did not:

- Raw tap sums are not universally one. Lanczos is explicitly normalized by
  the consumers, and the exact Nearest tie cannot be represented by the
  symmetric scalar `tap()` function.
- A warped gather whose phase varies by output location is linear for
  Bilinear, but is not globally shift-invariant. `gather_mtf` is explicitly a
  phase-average approximation. This does not weaken the convex-hull proof.
- Unit MTF magnitude does not make Nearest detail-free; its phase error is
  substantially worse than the interpolating kernels in the
  truth-referenced control.

No scorecard or orchestrator document was edited.
