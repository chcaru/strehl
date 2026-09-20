# Fixed RAW temporal-affinity support: rejected

MEASURED, 2026-09-19. The generated instrument completes, but the fixed rule
fails its image-quality screen. No photographic replay or default change is
admitted. See independent-results.md for the independently chosen comparisons
and the distinction between error, template amplitude and fan strength.

The rule groups fixed 8x8 output-quad blocks using the squared positive cosine
of all signed consecutive four-plane DN changes. Within a 32-quad centre
radius, it pools actual finest green energy and the injected floor separately,
then uses the existing SoftPower consumer. Other bands, base and hull remain
unchanged. This is conditional spatial support, not a newly identified donor.
Source noise is injected; the original generated images remain u16. No aligned
frame collection, full-photo adapter or production default was added.

## Commands and binding

Run from the repository with Python312:

```
python -I -B -X faulthandler experiments/raw-affinity-support/run.py build --out experiments/raw-affinity-support/build-1
python -I -B -X faulthandler experiments/raw-affinity-support/run.py controls --build experiments/raw-affinity-support/build-1 --out experiments/raw-affinity-support/controls-1
```

The fresh release build records `Compiling strehl-cli`, taking 181.421s. The
arithmetic controls and actual image screen take 0.266s and 2.719s. These are
operational receipts, not speed benchmarks. A passing test process means the
instrument completed; `photographic_replay_admitted` is false. The executable
SHA256 is `561adc89912d59966f60d9c77aba8633b456668dc1a71d338a1121309eabf3dc`.
The screen SHA256 is
`c36ea2504d1a93c221553ada1d7632b9d903d3e810f06c149ee37a1dd36b9d65`.
Source manifests and completed receipts bind the exact implementation, controls
and inputs; all bound sources remain unchanged.

## Image decision

Independent controls run flat regions first, followed by glint plus competing
thin structure, no-glint twins and true coloured radial detail. They include
common illumination brightening and a one-quad physical block-phase change.
Known truth, lost-amplitude, greyed, overcontrast and wrong-source destroyers
commission the scores. RGB truth error can penalize an otherwise sharp noisy
output; chroma error can improve through unwanted desaturation, and template
amplitude can remain correct while other structure is damaged. No one score
substitutes for the other mandatory guards.

Only three of thirteen cases pass: both flat cases and ISO100 radial. Eleven
are exercised; two ISO400 glint cases lack the required positive fan/noise
separation and remain recorded rather than being called replications.

| Case | Candidate / baseline RGB truth error | Decision |
|---|---:|---|
| Flat ISO100 / ISO400 | 0.87855 / 0.87764 | Noise-only gains, not detail gains |
| ISO100 glint, stable light, core / whole interior | 1.07016 / 1.09468 | Fails despite retained core amplitude |
| ISO100 glint, common brightening, ridge / whole interior | 3.13026 / 1.73873 | Genuine ridge amplitude also falls |
| ISO100 no-glint, stable light, boundary / interior | 1.05035 / 1.09560 | Fails independently of glint and brightening |
| ISO400 no-glint, stable light, boundary / interior | 1.09440 / 1.11616 | Same independent failure |
| True radial ISO100 / ISO400 | 0.91640 / 1.06304 | One passes, one fails |

All ratios compare spatial errors against the same camera-linear truth; they
are not temporal noise sigmas. In the common-brightening case, the ridge's
three baseline components [1.0264, 0.9944, 1.0454] become
[0.8314, 0.8029, 0.8382]. Conversely the stable-light core stays above unit
amplitude while RGB error worsens: that failure is not erasure.

The common ramp drives an independently commissioned unrelated two-block
affinity from zero to 0.999142. In the image case all 18,420 nonself affinities
become positive. The cue-free AllAffinity placebo is live and also fails;
its ridge error ratio is 3.43673. Moving the crop one quad retains the failure
(ridge ratio 3.34548), without proving a particular visible seam. The frozen
FAN window overlaps the near surface and ridge, so its 2.71554 error ratio is
a composite-region result, **not** a 2.7-fold increase in ray strength.

## Mechanical scope and closure

Off reproduces complete CFA and RGB exactly. All 65 case/source records retain
input and replay hashes, including gathered samples, guide, variance and beta;
all thirteen cases preserve nonfinest accumulators. The forced-source arm
changes 72,104 CFA samples and loses core amplitude, demonstrating a live
wrong-donor rejection. Arithmetic enumeration bounds affinity/pooling error
by 1.19e-7 / 5.81e-6. Fixed-descriptor reversal is algebra, not a second image
run. The actual rounded GPU gather reaches four AC levels plus base on these
small plants; this does not establish seven-band photographic behavior.

The plant shares the injected calibration and validates the operator, not the
camera calibration. There is no new photographic improvement, full-workflow
performance result or SOTA claim. Preserve the measured brightness association
as narrow evidence; it did not establish source ownership. Close this exact
rule without a block/radius/cosine sweep or brightness-normalization rescue:
the no-glint stable-light twin already rejects it.
