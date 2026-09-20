# Full-size cost witness: refused, no full photograph

**MEASURED, 2026-09-19.** The separately scoped observational route stops at
its one-source checkpoint. No70-frame candidate photograph was produced.
The prior small-screen photographic admission remains false.

Root ran:

```
python -I -B experiments/boundary-cfa-wavelet/run.py build --out experiments/boundary-cfa-wavelet/build-3
python -I -B -X faulthandler experiments/boundary-cfa-wavelet/run.py controls --build experiments/boundary-cfa-wavelet/build-3 --out experiments/boundary-cfa-wavelet/controls-2
python -I -B -X faulthandler experiments/boundary-cfa-wavelet/full-run.py controls --build experiments/boundary-cfa-wavelet/build-3 --screen experiments/boundary-cfa-wavelet/controls-2 --out experiments/boundary-cfa-wavelet/full-controls-1
python -I -B -X faulthandler experiments/boundary-cfa-wavelet/full-run.py cost --build experiments/boundary-cfa-wavelet/build-3 --screen experiments/boundary-cfa-wavelet/controls-2 --mechanical experiments/boundary-cfa-wavelet/full-controls-1 --out experiments/boundary-cfa-wavelet/cost-1
```

Fresh core/CLI compilation completed in127.156s. The unchanged generated
controls completed in4.797s, retaining the old failed decision. The new
independent full-domain mechanical test completed in1.047s: twelve-level
one-axis transforms, full binding refusals, explicit CA GPU/CPU consumed-code
and coverage equality, unchanged generated source/output hashes, headroom
refusals and pinned TIFF writer all passed.

The real source35 cost job exited101 after33.141s. It completed the actual
full-resolution signal/gather and all eight noise pairs, wrote its source
receipt and one-source baseline TIFF, then refused candidate reconstruction
with `nonfinite inverse input`. There is no candidate TIFF or completed cost
receipt. The one-source baseline is a cost artifact, not a stack output or
an improvement to show the user.

| Completed source phase | Seconds |
| --- | --- |
| Original decode |0.1054125|
| Actual baseline fold |0.644651|
| Full signal transform |1.5650308|
| Eight original-source noise pairs |28.7347466|
| Coefficient weights/fusion |0.3926346|
| Whole source processing, including receipts |31.708082|

These nested phase times are not additive without accounting for their scope.
Peak job committed memory was7101923328bytes, below the12GiB cost bar. Full
mode would additionally retain a canonical baseline partial accumulator.

**DERIVED incomplete extrapolation:**70 times the recorded source processing
plus the already frozen120s allowance is2339.56574s, before final finishing.
This exceeds the1500s feasibility estimate bar. It is not a measured full
runtime or a physical lower bound on a future warmer run. The failed cost job
alone already refuses full admission; the timing gives an independent reason
not to repair this implementation merely to launch the same expensive trial.

The finite individual weights are not sufficient to prove finite weighted
numerators. A product/accumulation overflow is a source-level hypothesis for
the inverse refusal; independent review determines how specifically the
available evidence supports it. Do not silently cap values, alter probe
count, lower resolution or rerun to evade this result.

Retain the useful small-domain operator/variance controls and the separately
scoped full adapter as experimental evidence, with its failed cost witness.
The next quality intervention is the distinct shared categorical source field
described in fresh-priority-review.md, aimed at the real source-consistency
failure. No default change, SOTA claim or photographic gain was earned here.
