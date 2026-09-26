# Fixture assertion arithmetic repair

`controls-1` is retained: identity/refusal tests passed, while estimator and
quality tests stopped at the fixture's full-RGB flux assertion before writing
their scientific reports. This is not an algorithm quality result.

Root-authorized standalone command executed, without RAW or stack runs:

```
python -I -B experiments/native-photometric-normalization/blur-sum-diagnostic.py
```

The exact finite sliding blur reproduced a naive left-fold relative sum
difference of **1.0284568409173429e-12** for blue/radius80, above the fixed
**1e-12** bar. Independent `math.fsum` gives **1.257981235418104e-15** on the
same array. Compensated summation equals `math.fsum` in all six channel/radius
cases; maximum relative conservation difference is **3.6164249146006924e-15**.

The only fixture repair replaces the two final assertion totals by compensated
`flux_sum`. Every blur output operation and the tolerance remain unchanged.
`blur-sum-diagnostic-2.json` records canonical f64 output hashes, unchanged
before/after the diagnostic reduction. The original diagnostic JSON is also
retained. These hashes commission the tiny diagnostic, not a native-render
identity claim. Root owns the fresh build and unchanged four-test rerun.
