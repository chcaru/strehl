# Differential-blur discriminator: stopped at independent control

**MEASURED: this fixed implementation did not pass its pure-translation
control. No photographic fit, RAW decode, alignment change or render followed.**
The independent plant contained a known translation and zero differential
Gaussian blur. The fitted translation-plus-Laplacian arm failed the preregistered
requirement that beta remain within 0.03 source-native pixel² of zero.

Actual command, from the repository root:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/chip-differential-blur/run.py --out experiments/chip-differential-blur/run-1
```

`run-1/result.json` records `STOP_SYNTHETIC_MODEL_SCREEN_FAILED`, zero saved
photographic arrays read, and zero RAW decodes. `process.log` identifies the
independent control's assertion, not an infrastructure or resource failure.
The fixed control reached that assertion after its convergence/admission and
known-displacement recovery checks. It did **not** complete the blur-only,
mixed, aperture, asymmetric or anisotropic controls. The failed control did not
serialize its fitted coefficient, so no exact beta value is claimed here.

MEASURED operational cost from terminal Windows-job accounting: 2.328 wall
seconds, 0.640625 CPU seconds, 143,962,112 bytes peak committed job memory. Exit 1
reflects the assertion. All child processes exited, cleanup errors are empty,
and no forced termination was needed. These are one-run resource observations,
not performance comparisons. Exact interpreter, command, environment, source
bindings and bounds are retained in `invocation.json`, `sources.json`, and
`process.json`. The runner's source-hash check after execution passed before
it surfaced the nonzero exit. No bound source was changed to pass the gate.

The model, controls and predeclared limits were independently reviewed before
execution. The primary plant re-chose G2/top-bottom support with a nonidentity
similarity and independent continuous Fourier/Gaussian truth. Its source SHA256
is `c2890db5008dd1e54fb508a8d15218346b33c99535b35864964e16bf92028e68`;
the model is `14f193c81bc02dd8e8dbf2cb5edf0389a8e5a37751311cbec91d59cfea3cc7db`.
Full source identities are in `run-1/sources.json`.

ARGUED consequence: this implementation has not separated an added blur term
from effects accompanying its translated/sampled input. Its beta must not be
interpreted as evidence of physical differential defocus on the chip. This
failure does not establish that differential blur is absent, and does not
identify the exact confound. No threshold, blur size, support, phase or model
was tuned after seeing the failure. The requested four-choice real-frame
stability comparison and changes from frozen successful displacements are
deliberately **unmeasured**, because their required discriminator failed first.

The September 19 modest local chip improvement and failed star-sand transfer
remain unchanged evidence. This result just closes the present simple blur
attribution route; it is not a new image-quality or SOTA claim. Independent
post-run review in `independent-result-review.md` agrees with stopping and
does not attribute the failed control to a particular physical cause.
