# Fixed support diagnostic, September 19

MEASURED: the fixed radius32-quad diagnostic completes on all70 original
vitamin-C frames through the actual full-domain GPU gather and measured green
probe. All six original finest-band nominations reproduce the earlier actual
weight dump exactly. Pooling current finest energy and its injected floor
separately moves both fan positions toward the compact-source range:

| Output-native point | Original max-SNR frame | Pooled max-SNR frame |
| --- | ---: | ---: |
| facet core (2624,2906) |23|23|
| facet fan (2602,2945) |57|23|
| facet rim (2760,2998) |58|25|
| dark core (3080,2150) |32|27|
| dark fan (3102,2203) |69|27|
| nearby structure (3240,2070) |25|35|

These are guide-coefficient nominations, not final pixel ownership or quality.
Each pooled3x3 neighbourhood agrees on the displayed frame. No measured
energy/floor denominator is clamped in the54x70 observations. A larger energy
can reward noise and defocused rays; it is not a quality metric.

The nearby structural change is an explicit counterexample to unqualified
pooling. At that point frame35 has local excess-SNR0.619 versus frame25's2.819,
but pooled scores12.348 versus8.553. Root and a separate reviewer inspect the
native source25/35 views: the small angled boundary around crop(190,220) is
visibly softer in35. This is local photographic evidence of a risk, not a
measured loss in an enabled merge, which has not run yet. Even a fallback for
absent fine evidence would not protect it: pooled fine evidence is present.

One exploratory multiplication of the existing local and pooled scores is
also rejected before implementation: it leaves the dark fan at69 and the
facet fan at55. It preserves the nearby structure's25, demonstrating the
detail-versus-fan conflict rather than solving it. This was one arithmetic
check on the retained measurements, not an independent quality experiment.

Commands actually run (full Python executable in process receipts):

```
python -I -B experiments/fine-support-guidance/run.py build --out experiments/fine-support-guidance/build-1
python -I -B experiments/fine-support-guidance/run.py controls --build experiments/fine-support-guidance/build-1 --out experiments/fine-support-guidance/controls-1
python -I -B -X faulthandler experiments/fine-support-guidance/run.py measure --build experiments/fine-support-guidance/build-1 --out experiments/fine-support-guidance/measure-1
python -I -B experiments/fine-support-guidance/inspect-sources.py
```

VERIFIED by independently authored controls:18 literal box-sum comparisons,
58,075 even-origin crop field comparisons,11,497 live odd-origin phase
differences,322,535 scaling comparisons, exact zero flat energy, injected
floor28, invalid-input refusal and unchanged source buffers. This checks
operator arithmetic and crop phase, not camera calibration or photo quality.
Fresh release compilation is recorded. The diagnostic costs25.094wall seconds,
90.8125CPU seconds and peaks at2,928,451,584 committed bytes with8threads;
single operational observation, not a benchmark. Original file metadata and
saved map remain unchanged. Original contents were not rehashed.

DECISION: test one smaller intervention that replaces only band0 weights by
the fixed pooled energy/floor weights. Other Laplacian bands, mean base,
coefficients, camera calibration, alignment and tone stay as in the baseline.
No all-band propagation, neighbourhood sweep or default promotion follows.
Independent generated controls must exercise depth borrowing and genuine
coloured detail as well as flat noise. A complete fixed-tone off/on photograph
can qualify only after those controls; it may leave broader fan structure
because that belongs to unchanged bands. No new quality gain is claimed here.

## Fixed finest-only candidate: rejected

MEASURED, independently authored controls executed by root:

```
python -I -B experiments/fine-support-guidance/candidate-run.py build --out experiments/fine-support-guidance/candidate-build-1
python -I -B experiments/fine-support-guidance/candidate-run.py controls --build experiments/fine-support-guidance/candidate-build-1 --out experiments/fine-support-guidance/candidate-controls-1
```

Fresh release compilation takes106.437wall seconds. The two controls finish
successfully in0.797wall seconds, meaning the instrument ran; their saved
quality decision is **REJECTED**, not a passing candidate. Both noise levels
are retained in `candidate-controls-1/output/screen.json`.

At ISO100 the complete fixture is exercised. Fan-window truth RGB error
increases12.56%. Glint-core error becomes6.53x the baseline, while recovered
true component falls from above1.0 to0.410–0.423. Capping the baseline at1.0
still leaves58–59% loss of genuine signal. The simultaneously lower chroma
error is an explicit example of a cosmetic statistic rewarding destruction.
Boundary error is1.00194x, nearby texture is essentially unchanged and real
coloured-ray error falls to0.93368x, none of which rescues the lost glint.
Flat RGB/chroma errors fall to0.87855/0.88908x.

At ISO400 the glint fixture does not exceed the predeclared two-times-flat
separation: baseline fan error0.00340057 and noiseless defocused fan error
0.00370147 are below the0.00444157 bar. It cannot qualify that positive test.
The independently exercised real-coloured-ray case nevertheless fails with
1.16135x RGB error, despite improved chroma error and template recovery.
Do not quote the unexercised glint arm as independent confirmation.

VERIFIED: explicit disabled mode is bit-exact on both generated depth scenes;
all coarser-band/base weighted accumulators, fallback sums and hull buffers
remain identical after every frame. A separate literal-box oracle checks the
actual weight hook, including live admitted/refused cases. No full RAW off/on
render was admitted or run. The extra buffers remain behind the diagnostic
feature and disabled by default. This fixed radius32 mean-pooling intervention
is closed; no radius, exponent or threshold sweep follows.

The next measurement must separate a compact highlight from neighbouring
surfaces, rather than merely average their evidence. Existing M120e spatial
weight smoothing is only a proposal, and the old own-luma guided regularizer
has a recorded occlusion-rim failure. Neither is a validated switch to enable.
