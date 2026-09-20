# Coupled pupil GPU operator passes its bounded numerical commission

MEASURED. The new fixed-table forward and adjoint pass discrete-pupil controls;
the preselected16384-point forward also passes its fixed density checks. This
resolves the measured quadrature discrepancy for the supplied scene/optics and
tested focus positions. No inverse fit or photographic improvement is claimed.

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/layered-raw-inverse/run-pupil-stencil.py --out experiments/layered-raw-inverse/pupil-stencil-1
```

The process completes in3.594s. Setup/mechanics/density sections take
0.265/0.282/1.047s, within their declared caps. These are commissioning costs,
not an alternating-sweep benchmark or a full-stack speed claim. Peak job
committed memory is3,246,379,008bytes; CUDA allocated/reserved peaks are
491,336,192/704,643,072bytes and are separate quantities.
Scored receipt SHA256:
`8ae48a156f1a4ccfb175b13c97549503da1ce02de05882fff222bfba91c8e1c3`.

The custom CUDA kernels aggregate same-ray near/far interpolation products,
retain their visibility coupling and gather the adjoint without atomic scatter.
They store latent/output planes and sparse tables, without an image-times-ray
or image-times-table tensor. CPU table setup is f64; stored coefficients and
image arithmetic are f32. The bundled NVRTC/driver compile and launch succeed.

For fixed64 rays, maximum pre-PSF discrepancy against independent CPU ray
enumeration is0.00091553DN; full-forward discrepancy against frozen Torch is
0.00041199DN. Worst adjoint relative L2 discrepancy is1.26787e-6. Independent
finite differences pass for both radiance sheets and coverage, and doubled
gradients fail. The incorrect independent-marginal visibility shortcut differs
by35.94852DN. Boundary transmission and its first-column-only adjoint pass
exactly on default and nondefault streams. Invalid inputs and double backward
are refused. Context-switch/graph-capture refusals are source-reviewed only.

| Fixed16384 forward comparison | Maximum whole normalized RMS | Maximum crossing normalized RMS |
| --- | ---: | ---: |
| Different-resolution4096 reference | 0.0121560 | 0.0219481 |
| Independently rotated16384 reference | 0.0036883 | 0.0052347 |
| Historical64 diagnostic | 0.8751165 | 1.6660706 |

All five declared focus positions meet both mandatory0.75-sigma convergence
comparisons. Same-pupil full-image discrepancy against independently chunked
Torch reaches0.02832031DN, below0.1DN. The original64 still fails crossing at
every tested focus, and whole support at focus8; those failures remain. Both
retained1024 diagnostics pass against the fixed candidate, but the candidate
count was selected before the run, not chosen from these scores.

Dense tables contain533-1625 joint entries at these positions, occupying
10,672-36,256bytes including the near marginal. More quadrature points change
setup accuracy without creating a ray-sized candidate image buffer. The
independent reference retains at most1024 rays per forward call.

These are finite-quadrature comparisons, not continuum truth or lens calibration.
The injected noise supplies the discrepancy scale; this plant cannot validate
that calibration. Adjoint execution was commissioned at64 rays; dense16384
testing was forward-only. No dense inverse, real geometry, full-resolution
render or speedup was tested. The prior free-visibility image failures remain
untouched. Before a dense inverse, its derivative and independently generated
resolved observations need their own checks; old64-generated observations
must not silently become ground truth for a different pupil model.

Independent review: independent-pupil-stencil-results.md. All bound source
and runtime-DLL hashes remain unchanged. No production default changed.
