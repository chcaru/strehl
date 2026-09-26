# Shared chromatic source evidence: generated screen rejected

2026-09-25. MEASURED generated consumer screen only. No complete photograph or
production change is admitted by this result.

Commands executed with Python3.12 from the repository:

```
python -I -B -X faulthandler experiments/chromatic-source-evidence/run.py build --out experiments/chromatic-source-evidence/build-1
python -I -B -X faulthandler experiments/chromatic-source-evidence/run.py controls --build experiments/chromatic-source-evidence/build-1 --out experiments/chromatic-source-evidence/controls-1
```

The fresh CLI build succeeds in164.797seconds. Four independent tests execute
eight image cases, two identity placebos and one wrong-source destroyer in
16.750seconds. These are
operational costs, not speed benchmarks. Mechanical checks pass, all bound
sources remain exact, and the wrong-source destroyer is exercised. Overall
quality, positive exercise and candidate qualification are false. Screen SHA256:
`d6a19bb6230a13f2bab0aa1a4a8191d92634ae537a6111ae9f3e3765049d3e32`.

The operator changes coarse evidence to white-balanced, co-sited R-G/B-G
differences, propagates the injected RAW noise through paired projections, and
uses one shared source weight field for the original four CFA coefficients.
Finest coefficients and the mean base remain canonical. This tests source
evidence, not desaturation or subtraction of observed radiance.

The ISO100 unclipped positive is exercised, but outside RGB error increases
to1.03879x baseline instead of the required reduction. In the real-highlight
core, RGB error rises to1.50691x and green error to2.32121x; recovered template
amplitudes fall from0.889/1.012/0.956 to0.668/0.671/0.659. Its lower chroma error
is therefore not useful glare recovery: a genuine neutral highlight is damaged.
The core protection was added by independent root review before compilation or
measurement, with the same existing damage bars.

The clipped neutral control also fails: outside RGB error falls to0.73954x,
but real-texture retention falls below the98% bar. This is the falsifier for
reading lower error alone as quality. The ISO400 veil positive is unexercised
and quality fails independently. Both flats, neutral fine detail, crossed thin
depths and genuine coloured rays pass their bounded preservation checks.
Those successes do not qualify the failed rule or a deep-stack admission union.

RMSE can reward smoothing; template recovery can reward aligned false detail.
Both are commissioned against independent destroyers and used together here.
The injected model is shared with the plants, so these tests do not validate
camera noise calibration. The clipped fixture does not establish clipping in
the user's mineral originals. Preserve all eight cases; no threshold, source-
count or full-render campaign follows this fixed operator's rejection.

Independent interpretation is recorded separately in `independent-results.md`.
