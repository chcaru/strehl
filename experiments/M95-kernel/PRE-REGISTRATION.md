# M95 arm 9 — pre-registration: landing the sharper kernels

Written before any number in `experiments/M95-kernel/` was computed.

## What is being built

`Resampler` gains two variants alongside `Nearest`/`Bilinear`/`CatmullRom`:
**Lanczos-3** and the **prefiltered cubic B-spline**. **The default does not
change in this commit.**

## The implementation problem, stated before it is solved

Arm 7 measured `bspline` at **−0.0951 dex** using the *exact* Unser IIR
prefilter — a recursive pass over the whole plane. `Resampler::sample(p, x, y)`
is a pure function of a `PlaneRef` and a coordinate, and `merge_cmd.rs` is
contended and forbidden to me, so there is nowhere to put a per-plane
coefficient buffer.

A variant that returns the *unprefiltered* B-spline basis when handed raw
samples would be strictly blurrier than Catmull-Rom while being named as an
upgrade. That is a trap, and I will not ship it.

The alternative is to fold the prefilter into the kernel. The prefilter's
impulse response is `h[k] = √3 · z^|k|` with `z = √3 − 2`, so the effective
interpolating kernel is `w(u) = √3 Σ_k z^|k| β³(u − k)`, evaluable as a finite
FIR of radius `R`. **`R` is an accuracy/edge-loss tradeoff and must be chosen by
measurement, not by taste**, because `support()` feeds `sample_checked` and a
larger radius rejects a wider border — the region the coverage crop already
makes fragile.

## Bars — registered now

- **B20 — the shipped kernel must be the measured kernel.** The truncated FIR
  must match the exact IIR-prefiltered B-spline to **max abs < 1e-4** on a real
  image tile. `R` is chosen as the **smallest radius** clearing this. If no
  R ≤ 12 clears it, the B-spline does not ship and I say so.
- **B21 — interpolating.** Both new kernels must reproduce sample values at
  integer phase to **< 1e-5**. A non-interpolating kernel makes an identity
  transform lossy; arm 7 caught Mitchell reading −0.2008 at identity this way.
- **B22 — the gain must survive the port.** Each shipped kernel must reproduce
  its arm-7 dex gain within **0.01 dex** when re-measured through the Rust
  implementation's own weights. If the port loses the gain, the port is wrong.
- **B23 — ringing, on real edges.** Measured on occluding and silhouette edges
  of `bee-3-cpl`, not on synthetic step patterns. **I predict, before looking:
  lanczos3 rings most, bspline intermediate, catmull-rom least.** If the
  ordering comes out differently that is a finding and I report it as one.
- **B24 — election neutrality.** The kernel must not change which frame wins a
  pixel. Required: a **separation control** showing the test could have detected
  a change, on the model of the demosaic branch's 21.6×. Without that control
  a null here means nothing.

## The default

**Not changed in this commit, under any result.** The orchestrator's reasoning
is accepted in full: a high-frequency sharpness metric and a ringing artifact
are the same signal, and this project has twice tonight had a metric confidently
prefer a visibly worse image. I will state which kernel I would default and what
I would give up, but the recommendation is evidence for a later decision, not
this commit's payload.

## Controls that must pass before any number is reported

- **K17.** Nearest-neighbour at integer phase must round-trip **exactly**
  (bit-identical), since it is a permutation. If it does not, the harness is
  wrong before any kernel is judged.
- **K18.** The identity transform through each kernel must return the input to
  **< 1e-5** — this is B21 measured through the real `gather_into`, not through
  the weight function in isolation.
- **K19.** A planted **σ = 1.0 px** blur must move the sharpness metric by
  **≥ 0.20 dex**, so a null on kernel differences is a claim about kernels
  rather than about a dead instrument.

## Falsifiers

- If B20 fails at every R ≤ 12, the B-spline does not ship.
- If B22 fails for a kernel, that kernel does not ship.
- If the eye disagrees with the metric on the 100% crops, **the eye wins** and
  the report says the metric was wrong.

---

# ADDENDUM 2 — the exact metrics for B23 and B24

Written **after** Lanczos-3 compiled and its unit tests passed, and **before**
`k3_ringing.py` / `m95-kernel.rs` existed or printed any number. B23 and B24
were registered abstractly above; this pins the statistics so they cannot be
chosen to suit a result.

## What reading `merge_cmd.rs` changed

`merge_cmd.rs:919-960` warps the frame **before** `green_luma_with_clip` and
`FocusField::compute` run. The resampler is therefore **upstream of the focus
statistic**, so the election consumes resampled pixels. B24 is a real question
about this code path, not a formality.

## B23 — the ringing statistic

**Overshoot against a kernel-independent reference interval.** For a
destination sample at source coordinate `(x, y)`, let `lo` and `hi` be the min
and max of the **2×2 bracketing source samples** `(⌊x⌋..⌊x⌋+1, ⌊y⌋..⌊y⌋+1)`.

```
overshoot = max(0, v − hi, lo − v) / max(hi − lo, eps)
```

The reference interval is the same 2×2 for every kernel **by construction**. A
per-kernel support window would silently reward the wider kernel with a wider
interval, which would be a measurement of the instrument.

**Populations, on a real `bee-3-cpl` frame — no synthetic steps.** Gradient
magnitude percentile is the operational definition of "edge":

| name | definition |
| --- | --- |
| `ALL` | every sampled pixel — the background rate |
| `EDGE` | top **1%** by gradient magnitude — silhouette and occluding edges |
| `TOP` | top **0.1%** — the hardest edges in the frame |

Reported per kernel per population: **mean**, **p99.9**, **max** overshoot, and
the **spatial extent** — the count of pixels per edge whose overshoot exceeds
1% of local contrast.

### Controls that make B23 admissible

- **K20 — nearest must read exactly 0.** It copies a bracketing sample, so it
  cannot leave the interval. Nonzero ⇒ the metric is broken.
- **K21 — bilinear must read exactly 0.** It is a convex combination of the
  four bracketing samples. A second, independent zero.
- **K22 — power.** Lanczos-3 on a synthetic step must read **> 0**. Two
  structural zeros plus one positive is the discipline-594 shape: the
  instrument demonstrably can say otherwise.

**Prediction, registered:** `lanczos3 > catmull-rom` on every population, and
`nearest = bilinear = 0`. A different ordering is a finding and I report it.

## B24 — the election statistic

For each kernel `K`: gather all four CFA phases of each frame with `K` through
the real `gather_checked` (exactly as `warp_frame_in_place` does), compute
`green_luma_with_clip`, then the **real** `FocusField::compute` at the **real**
`WINDOW_RADIUS`, with the **real** `profile::noise_model_for`. Elect by argmax
over frames. The statistic is the **fraction of covered pixels whose winning
frame index changes** between two kernels.

**The warp is per-frame, not common.** Frame `i` gets sub-pixel phase
`ax = frac(0.37 i)`, `ay = frac(0.61 i)` — deterministic, spread over all
phases, and shaped like the real aligner, which hands every frame its own
translation. A single common phase for all frames would make the kernel's
effect **common-mode** and would bias the answer toward neutrality by
construction.

### Controls

- **K23 — null.** Catmull-Rom against Catmull-Rom, recomputed, must be
  **exactly 0.000000**. Any drift means the harness is nondeterministic and no
  difference it reports is a kernel difference.
- **K24 — separation/power.** Catmull-Rom against Catmull-Rom with a **σ = 1.0
  px blur planted on one frame** must move a **large** fraction of winners.
  Bar: **≥ 5%**, and the separation over the null must be **≥ 10×**, on the
  model of the demosaic branch's 21.6×.

**Prediction, registered, and it is not the comfortable one:** because the warp
precedes the focus field, I expect the kernel **does** move the election —
non-zero, and I guess between **0.1% and 10%** of pixels. If it reads exactly
zero that is a surprise and I will say so. Either way the number is reported as
a finding, not absorbed.

**Scope note:** the default stays Catmull-Rom, so the shipped election is
byte-unchanged regardless of what B24 reads. B24 measures what selecting the
new kernel would do, which is what the later default decision needs.


---

# ADDENDUM 3 — the four-point kernel ladder (arm 11)

Written **after** `Resampler::Lanczos2` compiled and its unit tests passed
(`ac95e1b`), and **before** `lanczos2` was added to any measurement script or
printed a single number. The orchestrator asked for the two unpriced
intermediates, Mitchell-Netravali (B=C=1/3) and Lanczos-2, on the same
instrument as the existing two points, with a flat-region control.

Their stated hypothesis, which I am to kill or confirm by measurement:

> *"If Mitchell recovers most of the sharpness at a fraction of the ringing, it
> is the default and the trade dissolves."*

## What I already believe, stated now so a confirming result is not a surprise

I hold that **Mitchell B=C=1/3 cannot be the default**, on a structural ground
rather than a measured one: with `B != 0` the Keys/Mitchell kernel is **not
interpolating**, so `k(0) != 1` and a zero-phase resample is a blur. It pays a
cost on a stationary image. If that is right the hypothesis is dead before the
ringing axis is reached, and no amount of low ringing rescues it. Registering
this now so that the reader can discount it: **I expect Mitchell to fail, and
the bar below is written so it can prove me wrong.**

I hold **no prior** on Lanczos-2 beyond it sitting between the two points. Its
support is 2.0 px, equal to Catmull-Rom's, so on the border-cost axis it is free
where Lanczos-3 is not. Whether it is worth the default is exactly what this
measures.

## Bars

**B25 — the identity-phase control, and it is disqualifying.** Every kernel is
resampled at phase `(0, 0)` on the same tiles. An interpolating kernel must cost
`|dex| < 0.01` there. **A kernel failing B25 is not eligible to be the default
at any ringing figure**, because the cost is paid by every pixel of a
stationary image, and this project's whole complaint is softness. This is not a
tie-breaker; it is a gate.

**B26 — phase-averaged sharpness, same instrument as arms 4 and 8.**
`band_ratio` over the same tile selection, averaged over the seven non-zero
phases. Reported in dex relative to the unresampled tiles. Ranking claim:
`mitchell < catmullrom < lanczos2 < lanczos3` in recovered sharpness. **If
Lanczos-2 lands within 0.02 dex of Lanczos-3 it is the better candidate**, since
it buys nearly the same sharpness for Catmull-Rom's support and tap count.

**B27 — ringing on a clean step, same statistic for all kernels.** A 1000 DN
ideal step resampled at half-pixel phase; overshoot as a percentage of step
height. Catmull-Rom's value is **analytically 1/16 = 6.2500%** and that is the
arithmetic check on the harness — if the harness does not reproduce 6.2500% for
Catmull-Rom it is broken and every other cell is void.

**B28 — the flat-region control, per rule 9.** The same kernels on a
**featureless** region. A sharper kernel raises high-band energy on flat ground
too, which is amplified read and shot noise, not detail. Registered
requirement: report the flat-region high-band change beside the detail-region
change for every kernel. **If a kernel's flat-region gain is of the same order
as its detail-region gain, its sharpness number is noise amplification and I
must say so.**

**B29 — the negative control on the sharpness instrument.** Mitchell is
retained as the deliberate known-blurrier kernel from arm 4. The instrument must
rank it below Catmull-Rom. **If it does not, the instrument cannot rank kernels
and B26 is void** — this is the arm that makes B26 readable, and it must be
reported whichever way it falls.

## What would change my mind about Lanczos-2

- **Fails B25** — dead, same as Mitchell, no appeal.
- **Passes B25 but B26 gain over Catmull-Rom is below +0.02 dex** — not worth a
  default change; land it as an option and say so.
- **Passes B25, B26 gain is material, and B27 ringing is at or below
  Lanczos-3's** — then it is the candidate to take to the owner's eye, and the
  montage decides.
- **B28 shows the flat-region gain matching the detail-region gain** — the
  sharpness number is noise and the whole ladder needs re-reading.

## What I will not do

I will not add Mitchell to the shipped `Resampler` enum in order to measure it.
It is priced in the measurement harness only. Shipping a kernel I expect to fail
its own gate, so that it can be measured, would put a knowingly lossy option in
front of an operator.

---

# ADDENDUM 4 — arm 12: ringing on a real occluding edge

Registered before `x9_ringing.py` was written, and committed before it was run.

B27 measured ringing on a synthetic 1000 DN step and is harness-verified
(Catmull-Rom = 6.2500% = 1/16 exactly). The orchestrator asked for ringing
scored on real occluding edges, with a flat-region control, on the same
instrument across kernels. This is that instrument.

## The instrument

For each challenger arm A against the shipping default C (catmull-rom), on the
299-frame `bee-3-cpl` render where the kernel is the only variable:

`excess(p) = max(0, A(p) - localmax_C(p), localmin_C(p) - A(p))`

where localmax/localmin are taken over the 3x3 neighbourhood of C centred on p,
inclusive of the centre. `excess` is the amount by which the challenger leaves
the range the default render holds locally. That is overshoot, in DN, with no
model and no fitted parameter. It is exact: it compares bytes.

Pixels are binned by the local gradient magnitude of C into FLAT (lowest
decile), MID, and EDGE (top decile).

## Bars

**R1 — is it ringing at all?** Genuine ringing is an edge phenomenon.
Lanczos-3's mean excess in the EDGE bin must exceed its mean excess in the FLAT
bin by at least 3x. **If the excess is spread evenly across bins it is not
ringing, it is a gain or noise difference, and I must report it as such and not
call it ringing.** This is the rule 9 flat-region control and it is the arm most
likely to embarrass me.

**R2 — does the synthetic result hold on real data?** B27 says Lanczos-2 rings
identically to Catmull-Rom (6.2500%, 1.00x). On real edges Lanczos-2's EDGE
excess must therefore be below one third of Lanczos-3's. **If Lanczos-2 rings
comparably to Lanczos-3 on real edges, B27 does not transfer and I must say the
synthetic step misled me.**

**R3 — is the instrument alive?** A planted overshoot of known amplitude must be
recovered. I will take the catmull-rom arm, add a synthetic ring of +2000 DN to
the pixels immediately adjacent to strong edges, and require the instrument to
report a mean EDGE excess within 20% of the planted amount. **If it cannot
recover a ring it was handed, it cannot be trusted to find one it was not.**

## What I expect, so that being wrong is visible

I expect R1 to pass with a large margin, R2 to pass, and R3 to pass. I expect
Lanczos-3's mean EDGE excess to be a few hundred DN of 65535 — visible on a
gradient by eye at 1:1 but not obviously objectionable. If Lanczos-3's excess
turns out to be under 50 DN, its ringing is not a real objection to shipping it
as the default and I will say so.
