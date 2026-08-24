# M78 — blur-equalised and phase-shifted short alignment edges

**Status:** measured; both arms ship nothing.

**ARGUED.** This directory forks `experiments/m23-metacal/` to test two separately attributable
repairs:

- **Arm A:** R5 cross-blur equalisation using fixed per-tile focus labels.
- **Arm B:** a known integer-plus-half-pixel moving-frame shift, removed analytically.

**ARGUED.** The binding contract is `PREREGISTRATION.md`. The real capture trees are read-only. No
M78 code or result belongs under `crates/`, `SYNTHESIS.md`, or `AGENTS.md`.

**MEASURED.** The inherited Rust estimator files were byte-identical to M23 when copied. The crate
rename and initial documentation were the only pre-registration-stage changes.

## Changes relative to M23

- **ARGUED.** `src/align.rs` adds a unit-normalised, radius-`ceil(3*sigma)`, separable Gaussian
  filter over only the fine-stage tile/search regions. `align_with_blur` retains M10's unfiltered
  coarse capture stage and changes only the final 128×128 correlations.
- **ARGUED.** `src/field.rs` adds the closed-form Gaussian attenuation of each sinusoid before
  point sampling; this is the interpolator-free Arm A control.
- **ARGUED.** `src/main.rs` adds `blur-eq`, `phase`, and `field-probe` modes, an exact integer
  point-copy, and exact similarity-algebra removal of the registered phase plant.
- **ARGUED.** `m78_analyze.py` computes the registered controls, conservation, windows, and local
  telescoping. `m78_heldout.py` reuses M10's train sets, strategies, and score for the fixed
  held-out gate.

## Reproduce

```powershell
Set-Location C:\dev\blog\death-of-software\projects\strehl\experiments\m78-blur-eq
.\run-m78.ps1
```

**ARGUED.** The run script validates all three fixed input hashes, forces a release build,
runs every registered arm and control, writes the analysis outputs, and compares read-only capture
inventories before and after.

**MEASURED.** The fixed source-table hashes are:

- M10 `coffee-bean`: `E242A64A6367FBE2C1A52D679D85CAA40BD091529E2FCE0D477EDB94FAC801A6`
- M12 `112MSDCF`: `045995EFA2CFF6804D0391274EB51E2919432BBC869F1983C853E9F036D943FF`
- M6 `coffee-bean` focus profile:
  `C5533D43654CC84E7CD4FA95ACFE87F72236B81D6C585484811017DC2D6FF8D4`

**MEASURED.** `out/analysis.txt` and `out/heldout.txt` hold the concise numeric record. The research
interpretation and ship decisions are in `docs/research/M78-blur-equalised-edges.md`.
