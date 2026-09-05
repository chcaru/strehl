# M189 noise-colour detail v2 result

Status: **SYNTHETIC COMMON-LSI COMMISSIONING GREEN**

Source freeze: commit `1dface58`

No capture was opened.

## Held-out readings

The v2 latent and all four temporal-noise streams were first executed after the
Amendment 1 source freeze.

| arm | `Q_sup` / base | failed-v1 `Q_local` / base |
|---|---:|---:|
| identity | `1.000000000x` | `1.000000000x` |
| genuine optical improvement, sigma `1.00 -> 0.55` before noise | **`2.920107520x`** | `2.922975033x` |
| genuine optical degradation, sigma `1.00 -> 1.65` before noise | `0.153249100x` | `0.152602762x` |
| completed-image Gaussian blur, sigma `1.00` | `0.322196098x` | `0.313079643x` |
| completed-image USM, amount `0.75`, sigma `1.00` | **`0.733681365x`** | `1.004839651x` |
| adaptive denoise/sharpen/re-noise construction | **`1.826782749x`** | `1.841745129x` |

The decisive positive control is therefore positive by a wide margin:

> `Q_sup(optical improvement) / Q_sup(base) = 2.920107520x`.

The ordinary three-direction result is:

- genuine improvement: rises `2.920107520x`;
- completed-image blur: falls to `0.322196098x`; and
- completed-image USM: falls to `0.733681365x`, despite raising uncorrected
  coherent power by `1.831827134x`.

USM raised weighted temporal-noise power to `2.144200309x` of the external PTC
reference, with a maximum radial-bin gain of `2.598358407x`. The conservative
envelope charges that transfer rather than crediting the coherent-power rise.

The optical base/improvement/degradation weighted noise gains were
`1.003806987 / 1.003721331 / 1.003847681`, inside the frozen `[0.97,1.03]`
null. The flat score was `-6.952412569`, below the base
`157941.745050`.

## Declared attack

The adaptive re-noise construction remained decisive:

- score/base: `1.826782749x`;
- weighted noise gain: `0.999574532x`; and
- maximum radial-bin gain: `1.043122738x`.

It sharpened the deterministic mean, discarded the coloured captured-noise
path, and added fresh signal-dependent PTC noise. The noise witness therefore
accepted its covariance while the coherent score rose.

## Independent adjudication

`verify_v2.py --self-test` reported:

```text
P0_identity: GREEN
P1_improvement: GREEN
P2_optical_degradation: GREEN
P3_post_blur: GREEN
P4_post_usm: GREEN
P5_usm_intervention: GREEN
P6_optical_noise_null: GREEN
P7_adaptive_attack: GREEN
P8_flat_specificity: GREEN
SOURCE_HASHES: GREEN
CHECKER_SELF_TEST: GREEN
VERDICT: GREEN
```

This is a synthetic commissioning of a common-LSI-safe candidate, not M1
admission. Adaptive signal/noise separation remains a measured limitation.

