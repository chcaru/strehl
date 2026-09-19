# Preserve colour through the focus merge: first screen

The fixed independent screen admits one photographic replay. This is a measured
generated-scene result, not an improvement claim about an actual photograph.
The implementation remains test-only and no default changes.

Commands run from the repository root:

```
python -I -B experiments/phase-packed-rgb/run.py build --out experiments/phase-packed-rgb/build-1
python -I -B experiments/phase-packed-rgb/run.py screen --build experiments/phase-packed-rgb/build-1 --out experiments/phase-packed-rgb/screen-1
```

The fresh release build compiles strehl-cli and completes in 147.516 seconds.
The two independent tests pass in a 2.765-second bounded job. These are single
operational costs, with other program work running concurrently, not timing
benchmarks. Exact invocations, source/executable bindings and process accounting
are retained beside the runs.

MEASURED: all six fractionally shifted true-colour cases (three scene types at
ISO100 and ISO400) reduce both RGB and true-chroma error by more than five
percent. Their RGB RMSE ratios are 0.643–0.847. The independently measured
in-phase colour amplitudes increase; the truth-capped amplitude guard is not
hiding a lost component. Fractionally shifted neutral cases also improve in
this screen. Coincident textured frames are essentially unchanged. This is
consistent with an interpolation-order intervention, not universal enhancement.

MEASURED: the worst flat RGB RMS ratio is 1.004643 and the worst flat chroma
RMS ratio is 1.078951. The modest chroma penalty is real and is retained in the
decision. These quantities compare errors against the same known flat truth;
they are not spatial scene variation called temporal sensor noise. The shared
injected noise constants commission the operator, not the camera calibration.

VERIFIED BY EXECUTION: all four known-site planes are identical before and
after the actual merge; guide, variance and measured probe are shared. The
actual product writer matches all 217,500 RGB16 values of the baseline helper.
The independent explicit-CA oracle checks all twelve site/colour combinations,
with wrong-phase/channel and unsupported-source refusals. Flat tests run first;
colour-removal, half-amplitude and excess-contrast controls establish failure
directions for the metrics. The varying-focus fixture actually selects content.

The tiny domain reaches four Laplacian bands plus base, and each ISO uses one
fixed noise realization. It is not the full seven-band consumer. The next
step is one complete 70-frame vitamin-C pair using the current map, canonical
four-plane chunk boundaries, fixed development and real full-source support.
All twelve pulls must cover the common output. Whole-image memory, runtime,
actual photographic benefit and broader competitive quality remain unmeasured.

## Complete-source adapter commissioning

The full adapter keeps the original four-plane memory plan when choosing frame
reduction groups. At the real dimensions this gives four chunks of at most
18 frames; using the candidate's twelve-plane plan would give one chunk and
silently change floating-point reduction order. It reconstructs one complete
unaligned original at a time and releases its temporary RGB before the next
frame. The measured photograph still uses one shared guide, variance and
probe, and both outputs receive exactly the same pinned development.

Commands run:

```
python -I -B experiments/phase-packed-rgb/run.py build --out experiments/phase-packed-rgb/build-2
python -I -B experiments/phase-packed-rgb/run.py build --out experiments/phase-packed-rgb/build-3
python -I -B experiments/phase-packed-rgb/run.py screen --build experiments/phase-packed-rgb/build-3 --out experiments/phase-packed-rgb/screen-2
```

Build-2 exposes one missing Rust closure type annotation in the independent
control. The retained failure is corrected by adding `n:usize`; no arithmetic
or decision changes. The full-run wrapper's exact test name is also corrected
to include its enclosing `merge_cmd` module before the next build. Build-3
freshly compiles strehl-cli and completes in 136.406 wall seconds. Screen-2
passes all four tests in a 2.954-second bounded job; these are operational
costs, not benchmarks.

VERIFIED BY EXECUTION: 217,500 full-source interior colour values equal the
strict saved-patch route; 269,232 near-sensor-edge values equal the existing
explicit colour/phase oracle. A known-four-supported crop has nine unsupported
missing-blue samples and is correctly refused by the twelve-pull route. The
inclusive sampler boundary passes and its just-outside counterpart fails.
The generated active origin is odd on both axes and has nontrivial stride.

VERIFIED BY EXECUTION: three unequal chunks (2,2,1) match independent direct
accumulator absorption and preserve all 72,500 known-plane values exactly.
The fixture actually selects detail. Both paired output writers match all
435,000 independently developed RGB16 samples, with a live tone witness.
All 28 earlier quality cases run again and retain the same admission decision.
These checks validate the adapter; only a complete photograph can establish
whether the additional colour data help the observed highlight artifacts.

## Complete photographic result: no promotion

Commands actually run:

```
python -I -B experiments/phase-packed-rgb/run.py full --build experiments/phase-packed-rgb/build-3 --out experiments/phase-packed-rgb/full-1
python -I -B experiments/phase-packed-rgb/photo-compare.py
```

MEASURED: all 70 originals are consumed; both complete RGB16 outputs are
6920x4612, with no additional inset. All twelve pulls are supported. Known
four-plane values and admission fractions remain bit-identical after the
actual seven-band merge and canonical four-chunk reduction. The paired job
takes 57.906 wall / 331.203125 CPU seconds, peaking at 8,207,220,736 committed
bytes. It executes both arms, so it is not a standalone candidate benchmark.
Original sizes/mtimes and the pinned map are unchanged. All source and
executable bindings survive the run.

Paired baseline TIFF SHA256:
`c0d8faca8a23f31a73b843fbc9aa9f55fda96b5fcce9d3540ebf6a2b4319bb21`.
Candidate TIFF SHA256:
`7e1801d7009bf014e49be84e2f8084d729317cd1c0bf5390ed666536c372e62c`.
Both whole images, native frozen windows and coordinate receipts are under
`full-1/photo-comparison-1`. The original earlier baseline used automatically
resolved tone; this pair pins the same six-decimal tone in both arms, so only
the paired baseline is the precise control for this intervention.

ARGUED FROM INDEPENDENT NATIVE INSPECTION: this is a photographic null for the
intended highlight-colour improvement. Root and the independent reviewer
inspect all five frozen native windows and identify no newly resolved facet
or inclusion. The conspicuous multicolour fans remain in `facet-edges` and
`dark-inclusion`; one candidate cluster appears slightly more comb-like,
not cleaner. Smooth fields and the principal facet boundaries are retained.
The candidate avoids the external comparator's obvious grain penalty but
does not gain its reduced long-spoke appearance. Whole overviews locate the
subjects only; these fine-defect findings come from native 384x384 samples.

Do not promote this fixed candidate, optimize it, or sweep its settings on
the strength of the generated-scene gain. Preserve the bounded implementation
and independent controls as a negative result for this photograph. The next
diagnosis traces these exact highlights through the already-developed source
frames before selecting another intervention. This does not refute all joint
RAW colour reconstruction; it refutes this proposed remedy on its target.
