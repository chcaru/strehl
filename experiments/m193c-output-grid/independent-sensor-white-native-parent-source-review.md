# Independent source review: camera-white native parent and association

Root reviewed Zeno's complete reader/parent deltas and specification before
execution. This is a source verdict; the separately held reader review is by
Curie and actual controls and nine-frame agreement remain unexecuted.

Held sources:

- `independent-sensor-white-derivative-read.py`,76606 bytes,
  `6a318b439d1b9c5cb460808fc1388c7723d66a5adaf63b3303a6c791568a4bb8`.
- `native-sensor-white-derivative-run.py`,54522 bytes,
  `da1afc635851eaa8b60e29c1a6e677493b782d9e5e9cad19bad509d543de3ea1`.
- `sensor-white-reader-preregister.md`,13341 bytes,
  `715c53c13002d3f4bb1cebaca0ca841459cda352599a202042d969d488fabb23`.

Actual read commands included these complete comparisons and a complete spec read:

```powershell
git diff --no-index -- experiments/m193c-output-grid/independent-sensor-derivative-read.py experiments/m193c-output-grid/independent-sensor-white-derivative-read.py
git diff --no-index -- experiments/m193c-output-grid/native-sensor-derivative-run.py experiments/m193c-output-grid/native-sensor-white-derivative-run.py
Get-Content -LiteralPath experiments/m193c-output-grid/sensor-white-reader-preregister.md
```

The diff commands returned1 for differing files; no subject/helper was imported
or executed. Root separately read the inherited metadata validator and the owned
primary's scalar-level consumption, and consulted the
[official public RawPy API](https://letmaik.github.io/rawpy/api/rawpy.RawPy.html#rawpy.RawPy.camera_white_level_per_channel).
The API distinguishes camera-channel metadata from generic saturation. It does
not prescribe fallback precedence. Thus camera-only comparison is an explicit
prospective policy for this population, not a claimed universal API rule or
physical calibration. Current documentation0.27.1 does not change the pinned
installed0.27.0 runtime.

Root re-chose the failure direction: selecting any field that matches the primary
would accept an incorrect camera list when the generic field happens to agree.
The new method requires a complete positive integer camera list, uniform at every
used CFA index, and exact agreement with the primary scalar. Generic white is
retained and typed but cannot rescue missing, mixed or wrong camera metadata.
No fallback, average, minimum, first-matching entry or tolerance is introduced.

The actual consumer controls include a correct case with unequal generic/camera
values, wrong camera values with generic equal to primary, mixed channels,
missing/malformed metadata and index cases, black and WB faults, and restoration.
The two valid calls use a different camera value and black/WB coefficients from
the observed real refusal. There are ten groups and23 scalar calls. Exact
exception matching is outside the tested call; an unexpected success raises
outside the catch. Original inputs are checked unchanged on both return paths.
These controls test selection semantics and regression behavior, not calibration.

`validate_native_metadata` preserves the old exact black comparison and G1 WB
normalization arithmetic, including the original2^-20 allowance. The original
private validator and runtime/domain/TIFF functions remain unchanged in the
source delta. Raw generic and camera properties are acquired without coercion
and retained in the original metadata witness. The new authority witness names
the selected camera value and carries false physical/provenance claims explicitly.

The parent requires the new reader basename and explicit white-method schemas,
the renamed sixth check `scalar-black-camera-white`, exact eleven native checks,
eight domain controls and ten white-control groups, with actual request, source,
runtime, file and process associations. The historical original0 reuse function,
complete plan checks and no-delete/no-new-primary path are unchanged. All prior
failed attempts and their resources must remain bound by the separate preparer.
Coverage is still conditional on nine actual fresh reader admissions.

VERIFIED by independent source inspection: no blocking defect found in this
reader/parent delta or its association with the declared method. This permits
preparation and independent review of a fresh exact release. It does not admit
the saved TIFF, any remaining frame, coverage, a default change or image quality.
The earlier white-field choice and review omission remain in the independently
audited failed run; this correction does not rewrite that observation.
