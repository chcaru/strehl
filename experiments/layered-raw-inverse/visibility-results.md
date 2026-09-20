# Known visibility isolates a real failure, but is not sufficient

MEASURED,2026-09-20. Exact generated coverage is supplied to the same two
unknown radiance sheets, original sheet prior, original-CFA likelihood and
fixed solver. This is an oracle mechanism diagnostic, not an automatic stacker
or a photographic improvement. All previous failures remain recorded.

```
python -I -B -X faulthandler experiments/layered-raw-inverse/run-visibility-oracle.py --out experiments/layered-raw-inverse/visibility-1
```

With Python312, independent alpha-only preparation took2.031s, the two fits
35.625s, and independent scoring2.344s. Peak fit-job committed memory was
2,772,914,176bytes. Source, original observations, reference outputs and alpha
exports remain unchanged. Independent score SHA256:
`1b419e0c0eb0223522a23d4de0642b454bb1ec93b4b2a09e0e5f8ebf7a021088`.

| RGB truth RMS, DN | Known-alpha initial recomposition | Known-alpha fitted | Paired free-alpha fitted |
|---|---:|---:|---:|
| Flat whole | 7.51678 | 5.67202 | 43.30050 |
| Layered whole | 266.92966 | 150.97138 | 260.54748 |
| Layered core | 966.23442 | 731.45691 | 1117.53498 |
| Layered ridge | 454.47 | 312.40350 | 519.12885 |

Flat now passes every original and paired image/prediction check. Chroma RMS
is7.92557DN against mean8.36762; mean RGB is6.01845DN. Correct-alpha
recomposition alone still failed. The subsequent radiance fit supplies an
additional measured gain. Since the true flat sheets are identical, this
implicates removing spatial coverage freedom, not uniquely knowing alpha0.35.

Layered passes every original image bar and the paired core/ridge RGB and
filament protections. Correct-matte initial whole error was worse than the
old160-step result235.11192DN, so its final gain cannot all be credited to
recomposition. However, held bright41 samples still read2.14781 supplied sigma
against1.75 allowed. Glint recovery0.953–0.964 also misses the paired0.98
requirement against truth-capped free-alpha recovery. This is a remaining
attenuation, not a penalty for removing the reference's slight overshoot.

Both arms remain nonstationary. Flat returns after184 optimizer iterations/
196 actual evaluations with max normalized-parameter gradient7.24e-6, above
the fixed1e-6 criterion; layered reaches1000/1021 with0.002852. Neither is
a global-solution certificate. Known visibility helps materially on this
plant but is insufficient under this recipe. It supplies no real-photo
visibility estimator, optical calibration or SOTA comparison.

The independent interpretation is in independent-visibility-oracle-results.md.
Next measure the frozen objective's directional response to adding the known
far glint, with separate data/prior derivatives and a shifted-glint placebo.
Independent truth scoring must establish whether the proposed direction helps
the delivered image. This read-only diagnostic distinguishes a local prior
tradeoff from remaining descent without changing a coefficient or refitting.
The64-versus1024-ray integration failure still independently blocks real RAW.
