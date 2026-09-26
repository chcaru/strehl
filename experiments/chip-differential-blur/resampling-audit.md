# Read-only audit of the first differential-blur refusal

**VERIFIED by source inspection:** the pure-translation control and its fitted
model have an asymmetric sampling transfer. **ARGUED:** stopping was correct,
because this implementation has not earned a physical interpretation of beta.
The stop does not establish that differential defocus cannot be separated by a
different observation model. No RAW, photographic arrays, model fits, generated
plants, builds, maps, or renders were run during this audit. No bound source was
changed and no threshold is relaxed.

The retained result says only that the joint coefficient differed from zero by
at least the registered 0.03 source-native pixel-squared tolerance after the
displacement and convergence checks passed. Its actual value was not saved.
This audit therefore cannot identify its measured sign, magnitude, or dominant
cause. This is consistent with `independent-result-review.md`, which already
named sampling blur as an unisolated candidate.

## Concrete mismatch in the tested source

`independent-controls.py:9` synthesizes the continuous sum of four sinusoids
directly, with analytic Gaussian Fourier attenuation when sigma is nonzero.
It is not a Fourier shift of a raster. At lines 54 and 63, each source raster
site is evaluated at the inverse similarity and planted translation. No image
resampler generated the source. The first plant has zero differential Gaussian
blur, known translation (0.43, -0.57) source-native pixels, and nonidentity
similarity `A=1.0008+0.0003i`, `B=0.13-0.09i` in the code's stated convention.

Both source and target then receive the fixed normalized phase-only Gaussian
guide. At line 65, target values are sampled at integer reference CFA sites.
Its bilinear sampler is consequently an identity at those sites. The source
is sampled at similarity-mapped coordinates plus the fitted translation;
these coordinates are fractional. `implementation.py:14` imports the sampler
from `quality-september14/local-green-translation.py:42`, whose implementation
uses `map_coordinates(..., order=1, prefilter=False)`. Both the source guide
and its five-point Laplacian are sampled this way at `implementation.py:69`.

Thus the source design column carries a numerical interpolation transfer that
the target column does not. The added Laplacian is expressly capable of
absorbing part of that transfer. Yet the control at line 83 predicts beta from
the planted Gaussian sigma alone. That prediction omits this source-side
transfer. The independent continuous plant is appropriate for detecting the
problem; changing it to share the fitting resampler would hide the very
sampling effect it exposes.

## Falsifiable implication, with its limits

**DERIVED, not a rerun:** for a sufficiently smooth field, bilinear sampling at
fractional coordinates `(u,v)` has leading error

```
I[f] = f + 0.5*u*(1-u)*f_xx + 0.5*v*(1-v)*f_yy + higher-order terms.
```

At identity geometry with half-pixel displacement in both axes, this is
`I[f] = f + 0.125*Laplacian(f) + ...`. A model predicting an unresampled target
from this source can therefore prefer a **negative** beta near -0.125 native
pixel squared at low spatial frequency even though physical differential blur
is zero. At an integer displacement this interpolation term is absent. These
are idealized asymptotic predictions, not the missing coefficient of run-1.
The coefficient is also not a general correction constant: unequal fractional
coordinates introduce directional second derivatives, nonidentity similarity
varies the phase spatially, and frequency changes the approximation error.

The phase-only guide adds a separate limitation. It is a discrete,
phase-dependent normalized filter; applying nominally equal native sigma to
two differently transformed sampling lattices does not guarantee identical
continuous transfer after alignment. A five-point discrete Laplacian also
only approximates the generator's continuous Gaussian relation. Consequently,
the bilinear mismatch is concrete, but source reading alone does not prove it
dominates the failed gate. Neither an offset subtraction nor a wider beta bar
is justified.

A bounded **generated-only** discriminator would first save all readings
before any assertion. It could hold the motion at its independently known
value and compare the existing bilinear design columns with exact continuous
evaluation of the same analytic source and its five-point Laplacian, at fixed
integer and half/half displacements under identity geometry. This first layer
would deliberately omit the phase guide to isolate interpolation, and would
be labelled an instrument unit control, not acceptance of the full model.
The test has power: the exact-evaluation arm predicts zero beta for zero
physical blur; the bilinear half/half arm predicts negative beta of the above
order, while the integer arm predicts zero interpolation contribution. The
hypothesis loses if that contrast is absent. Unequal-axis phase is an explicit
out-of-isotropic-model control, not a scalar correction to fit away.

Only if useful would a second fixed comparison retain the actual phase guide
to find how much of the original failure remains. Its outcome could still be
null. No saved-photo retry follows either result automatically. The current
branch stays closed for physical blur attribution; resolving this numerical
instrument issue is not itself an alignment or image-quality improvement.

## Prior decisions checked

Mechanical search executed from the repository root:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B experiments/ORCH-drift-check/prior_art.py translation defocus phase alignment
```

The returned closures include:

- `docs/research/M23-metacalibrated-edges-measured.md`, especially the opening
  result and section 6: a zero-defocus self-pair through a bilinear plant and
  a point-sampled field gave sharply different responses. Attribution to
  defocus was retracted; per-edge response calibration shipped nothing. That
  report retains a NOT INDEPENDENTLY VERIFIED banner, so its historical
  measurements are not newly verified here. It names exactly the class of
  instrument confound found above and forbids treating response calibration
  as an established repair.
- `docs/research/M78-blur-equalised-edges.md`, sections 1, 5 and 6: Gaussian
  cross-blur and bilinear half-shifts improved conservation statistics but
  failed paired predictive held-out gates. Neither shipped. Its exact-render
  control distinguishes an interpolation lowpass from a useful phase repair.
  This audit does not reopen cross-blur, phase dither, or scalar shrinkage
  correction, and it does not use a fit residual as photographic evidence.
- `docs/research/M-PHASE0-XSPEC.md`: the complex through-focus phase channel was
  NOT ROBUST at its registered gate, explicitly not a blanket KILL of phase.
  The present observation supplies no new admission evidence for that route.
- `docs/research/M6-residual-halo-measured.md`: the older defocus-related
  residual diagnosis is context, not proof of the cause of this chip control.

The September 19 modest local full-chip improvement and failed star-sand
photographic transfer remain unchanged. A numerical explanation of a control
failure cannot upgrade either photographic verdict.

Current SHA256 identities were read with `Get-FileHash` and agree with the
retained run's named implementation/control identities:

| File | SHA256 |
| --- | --- |
| implementation.py | 14f193c81bc02dd8e8dbf2cb5edf0389a8e5a37751311cbec91d59cfea3cc7db |
| independent-controls.py | c2890db5008dd1e54fb508a8d15218346b33c99535b35864964e16bf92028e68 |
| ../quality-september14/local-green-translation.py | 5b64f7e612fd94cd8a22515bffb67addcee71021f6338f10a249c63864420196 |

This document is a new read-only decision audit, not a milestone fold, a
replacement for the original result, or independent verification of a new
measurement. The only new finding is the identified source-level mismatch and
its explicitly unmeasured, falsifiable consequence.
