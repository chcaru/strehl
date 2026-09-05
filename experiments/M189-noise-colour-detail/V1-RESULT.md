# M189 noise-colour detail v1 result

Status: **FAILED FROZEN P4; RETAINED**

Source freeze: commit `6533db2e`

No capture was opened.

## Frozen readings

| arm | score/base |
|---|---:|
| identity | `1.000000000x` |
| genuine optical improvement, sigma `1.00 -> 0.55` before noise | **`2.893930343x`** |
| genuine optical degradation, sigma `1.00 -> 1.65` before noise | `0.154653945x` |
| completed-image Gaussian blur, sigma `1.00` | `0.313909119x` |
| completed-image USM, amount `0.75`, sigma `1.00` | **`1.011364806x`** |
| adaptive denoise/sharpen/re-noise construction | `1.832091300x` |

USM raised uncorrected coherent power by `1.826803206x` and raised the measured
weighted temporal-noise power to `2.130897564x` of the external PTC reference.
The one-sided local correction removed almost all of that gain, but not enough:
the frozen P4 interval was `0.98 <= ratio <= 1.01`, so `1.011364806` is **RED**.
It is not rounded into the bar.

The positive-control arm is nevertheless decisive on its own question:
`Q_local` is not blind to genuine pre-noise improvement. Its exact measured
improvement/base ratio is **`2.893930343x`**.

## Post-result diagnosis — not a rescue of v1

An independent population calculation after the RED result found:

- exact per-frequency common-filter ratio: `1.000000000000x`;
- population ratio after the frozen 36-bin pooling:
  `0.999863556838x`; and
- the measured base score was `0.993698317129x` of its raw coherent power
  because sampling excursions with estimated `G > 1` are charged while
  excursions below one are not.

Thus v1's miss is an estimator/null-bias failure, not evidence that the
underlying per-frequency identity is false. Any repair is a new candidate and
must be frozen before rerun. This artifact remains the binding v1 verdict.

## Adjudication

`verify.py --self-test` reported:

```text
P0_identity: GREEN
P1_improvement: GREEN
P2_optical_degradation: GREEN
P3_post_blur: GREEN
P4_post_usm: RED
P5_usm_intervention: GREEN
P6_optical_noise_null: GREEN
P7_adaptive_attack: GREEN
P8_flat_specificity: GREEN
SOURCE_HASHES: GREEN
CHECKER_SELF_TEST: GREEN
VERDICT: RED
```
