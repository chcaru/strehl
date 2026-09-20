# Layered original-CFA reconstruction: first utility screen

MEASURED, 2026-09-19/20. The first prototype reconstructs the generated
overlapping detail but fails its complete admission screen. It is not a
photographic improvement. All existing product defaults remain unchanged.

```
python -I -B -X faulthandler experiments/layered-raw-inverse/run.py --out experiments/layered-raw-inverse/screen-1
```

This exact root-owned execution completes in55.218s, with peak committed job
memory2,719,694,848bytes. Those are operational receipts, not a speed benchmark.
The frozen model SHA256 is
`5710146ffcf463de85e317050bc81357922965d6006c7b4cf311f4d80d8ee512`;
the completed screen is
`cb26cc5a5358ebc054e867c2da974717f7084f7b5144d7bbb0bdbae4bfb8a460`.
All bound sources remain unchanged. Independent source and result reviews are
saved beside this report. Python/NumPy/SciPy/Torch versions are in runtime.json.

The new mechanism fits two nonnegative RGB radiance sheets and their coverage
directly to original u16 CFA readings. It composes visibility on each shared
aperture ray before integrating, includes supplied photon/read noise, and treats
digital16383 as a censored observation. It does not use development white15360
as a saturation ceiling. The first test supplies depths and a discrete64-ray
pupil; estimating these from real captures is still required. Each frame is
consumed separately; there is no aligned source-image volume.

## Result and limits

Seven of nine generated96x96 observations enter the fit. Two whole frames stay
withheld from initialization, fitting and comparator selection. The actual
input facade rejects their access, and replacing their values preserves the
initial state exactly. Full160-step optimization ends at its iteration limit;
that is not a convergence certificate.

| Case / measure | Two-layer | Comparator | Decision |
|---|---:|---:|---|
| Flat RGB RMS, DN | 8.675 | Training mean6.018; fixed-far5.606 | Noise guard fails |
| Layered whole RGB RMS, DN | 235.11 | Fixed-far496.88; mean753.72 | Registered image guard passes |
| Layered core RGB RMS, DN | 1064.73 | Fixed-far1786.24; mean3452.13 | Registered image guard passes |
| Layered crossing RGB RMS, DN | 848.92 | Fixed-far1532.73; mean2763.99 | Registered image guard passes |
| Layered held bright samples, supplied sigma units | 4.280 | Required <=1.75 | Prediction guard fails |
| Far-only scene held bright samples, supplied sigma units | 6.738 | Fixed-far9.466 | Both fail prediction |

Layered glint amplitude recovers0.837–0.855 and genuine glint-free filament
amplitude0.915–0.939, passing both fixed component guards. All layered image
bars pass; this is not simply highlight suppression. However, global held
prediction1.166 hides failure on41 bright samples. Flat prediction near1sigma
also hides noisier reconstructed radiance. Neither prediction alone nor a
component-amplitude score establishes image quality. RGB error, chroma error
and retained detail remain separate requirements. The far-only comparator is
restricted to the supplied far depth; the mean and truth-informed donor are
diagnostic baselines, not the canonical stacker or a SOTA comparison.

Angular illumination also fails held prediction. Since matched cases already
fail it, this does not commission a selective real-model mismatch detector.
Only one layered training-interior sample clips; censoring is live but this
does not validate broadly saturated photographic highlights.

Independent same64-ray forward paths agree within0.043DN. The separately
measured64-vs1024-ray difference fails the physical integration guard: crossing
RMS1.069–1.678 supplied sigma. That error is absent from the matched discrete
inference test and cannot excuse its failures. It independently blocks any
real-image application of this numerical optical configuration.

## Next numerical decision

The independently reviewed histories retain simultaneous decrease of both
data error and regularity penalty near the final step. Even the correct
far-only one-layer arm has not established stationarity. A separately scoped
continuation will therefore keep the exact saved objective and inputs, using
one bounded line-search solver on three fixed saved states. This distinguishes
unfinished optimization from the objective's bias; it does not revise the
failed first screen or authorize a parameter sweep. See convergence-plan.md
when frozen. Optical integration and actual RAW calibration remain separate.

For inspection, `display.py --screen experiments/layered-raw-inverse/screen-1
--out experiments/layered-raw-inverse/display-1` was run with Python312. The
four contact sheets show complete generated96x96 scenes under one fixed
asinh display, with the supported interior marked. They are diagnostic plants,
not crops or output improvements from the user's photographic stacks.

## First continuation attempt: execution refusal

```
python -I -B -X faulthandler experiments/layered-raw-inverse/run-convergence.py --out experiments/layered-raw-inverse/convergence-1
```

The process takes6.469s and independent scoring2.656s. All three arms refuse
before taking an optimization step: Torch L-BFGS requires a contiguous gradient
for its flattening operation, while this model's gradients have a different
memory layout. Saved parameter-state hashes are identical to the originals.
The scorer correctly records incomplete measurements, not image-quality
failures. Its SHA256 is
`866fb22f9477174af1c674b42b3aed15e96f3f48508f2b89852535d19e6286de`.
A layout-only repair will copy gradients to contiguous storage and assert exact
logical-value equality. No objective or optimizer setting change is warranted.
