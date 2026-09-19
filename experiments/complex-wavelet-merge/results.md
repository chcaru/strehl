# Green-guided directional fusion: rejected

MEASURED, September 19. The fixed identity, one-level complex-wavelet candidate
fails its independent quality screen at both ISO100 and ISO400. No fractional
extension or photographic replay is admitted. Production defaults are unchanged.

| Scene | RGB truth RMSE / matched baseline, ISO100 | ISO400 | Decision |
| --- | ---: | ---: | --- |
| Flat | 0.93055 | 0.92882 | Pass |
| Horizontal wave vector | 1.33348 | 1.12524 | Fail error guard |
| Vertical wave vector | 1.33356 | 1.12333 | Fail error guard |
| Diagonal wave vector | 1.55811 | 1.44222 | Fail error and retention guards |
| Genuine colour, same focus | 1.00012 | 1.00045 | Pass |
| Genuine colour, varying focus | 1.19389 | 1.19028 | Fail error and retention guards |

The decisive colour failure is not removal of artificial contrast. At ISO100,
red truth-amplitude recovery falls from0.62951 to0.42942 and blue from0.62953
to0.27348. ISO400 has the same failure. Independent review identifies the
green-only directional information path: the fixture's green is horizontal,
while real R/B structures have other orientations. Their directional coefficients
mostly receive the all-frame fallback despite carrying actual coloured detail.
Uniform-focus colour remains almost unchanged. This supports a specific blind
spot; it does not prove a replacement rule succeeds.

Conversely, the axis cases are not large amplitude collapse: baseline recovery
is about1.04 and candidate about0.98–0.99. They pass the truth-capped retention
guard but fail RGB truth error. Do not describe those errors as lost amplitude.
Error can reward smoothing and amplitude can reward manufactured contrast;
the independently frozen screen couples both, with explicit destroyers.

Flat candidate error is still1.1433x the direct original-CFA mean at ISO100.
The unsafe hard-selection control is1.9771x that mean. That control also elects
its LL donor, whereas candidate LL is averaged: it does not isolate the effect
of the H/D/V vote. Neither control is a complete comparison-stacker workflow.

VERIFIED structural scope: both actual Rust tests pass; asymmetric complex and
impulse roundtrips, exact two-sample cyclic phase/origin shifts, constant-detail
null, independent impulse-response variance, source hashes, original known CFA
values and green addressing are checked. Maximum asymmetric roundtrip error
is2.403e-7 and heteroscedastic variance error3.824e-7. These are implementation
checks, not quality acceptance. The at-white refusal enforces the unclipped
linear-noise domain; it does not demonstrate clipping safety or calibration.

Commands run from the repository root with Python3.12, `-I -B`:

```
python -I -B experiments/complex-wavelet-merge/run.py build --out experiments/complex-wavelet-merge/build-3
python -I -B experiments/complex-wavelet-merge/run.py controls --build experiments/complex-wavelet-merge/build-3 --out experiments/complex-wavelet-merge/controls-1
```

Build3 freshly compiled both core and CLI in112.047s. The two tests completed
in1.250s. These are operational durations, not performance benchmarks. Complete
commands, environment, source/executable hashes and bounds are in the adjacent
build and control receipts. `controls-1/output/screen.json` is the numerical
result; `results-review.md` is the independent interpretation.

Build1 failed on a json! indexing expression; parentheses were added. Build2
failed on the implementation's bridge-module import; its name was corrected to
`correction_variance_diagnostic`. Neither fix changed a stimulus, threshold or
algorithm. Failed attempts are retained. No parameter sweep follows this failure.

The reusable result is a commissioned complex transform plus a measured failure
of this exact green-only, one-level fusion rule. A future all-CFA evidence path
or multilevel operator needs its own justified scope and independent controls.
The original screen remains failed.
