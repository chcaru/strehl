# Experimental temporal-energy guidance

Temporal-energy guidance is an optional mode for ordered focus brackets.
It is **Off by default**. It can erase weak detail that is sharp in only one
capture; this failure occurs in the generated controls. A large frame count does
not establish that a bracket is suitable, and there is no frame-count eligibility
rule. Inspect an Off comparison before retaining an On result.

The feature uses the previous, current and next captures in filename order to
guide the two finest detail bands. It applies fixed weights `[1,2,1]/4` separately
to detail energy and the complete modeled noise floor before computing merge
weights. It retains the original image coefficients, coarser bands, base and
fallback behavior. Endpoints and brackets shorter than three frames use their
original guidance. This does not use camera depth or autofocus metadata.

## Desktop toggle

Open **Adjust → Merge → Temporal detail smoothing**. The checkbox is Off for new
stacks and older saved recipes. Its value saves with the stack and each rendered
revision. Press **Stack** to render a comparison; this is a merge setting, not an
editing filter. Reset returns it to Off.

The visible note warns that faint detail present in only one capture may be
removed. Use full-resolution output, a positive Noise gate (or its engine default),
and no enabled source-range repair. The desktop explains incompatible settings
before starting; ordinary development edits remain available.

The desktop build includes the experimental engine capability. The checkbox
controls whether a run uses it; inherited shell settings cannot silently enable
it. The spatially shifted research control remains CLI-only.

## CLI build and run

Follow the [build prerequisites](desktop-build.md), then build the CLI from the
repository root:

```powershell
cargo build --locked --release -p strehl-cli --bin strehl --features temporal-energy
```

The runtime setting accepts these exact lowercase values:

| `STREHL_TEMPORAL_ENERGY` | Behavior |
| --- | --- |
| Unset or `off` | Ordinary pyramid path. |
| `on` | Experimental guidance from adjacent captures. |
| `shift` | Research placebo: spatially shifts the neighbor guidance. Do not use it as a photographic treatment. |

Example in PowerShell, using a new output folder outside the captures. Replace
both paths and keep the same ordered capture set for alignment and stacking.
The explicit alignment file must exist before stacking; `align --out` alone does
not make `stack` use that file.

```powershell
$captures = "D:\photos\ordered-bracket"
$trial = "C:\strehl-results\temporal-trial-01"
New-Item -ItemType Directory -Path $trial -ErrorAction Stop | Out-Null
$env:STREHL_WARPMAP = Join-Path $trial "alignment.txt"
$env:STREHL_TEMPORAL_ENERGY = "off"
$env:STREHL_SPATIAL_NOISE_FLOOR = "off"

.\target\release\strehl.exe align $captures --out $env:STREHL_WARPMAP
if ($LASTEXITCODE -ne 0) { throw "Alignment failed" }

$env:STREHL_TEMPORAL_ENERGY = "on"
try {
    .\target\release\strehl.exe stack $captures --merge pyramid --srgb --out "$trial\on.tiff" --linear-master "$trial\on-linear.tiff"
    if ($LASTEXITCODE -ne 0) { throw "Temporal stack failed" }
} finally {
    $env:STREHL_TEMPORAL_ENERGY = "off"
}
```

To make the comparison, run the same `stack` command with mode `off` and distinct
`off.tiff` / `off-linear.tiff` output names, retaining the same alignment map.
Use the same display settings for both linear masters; independently estimated
tone settings can hide or exaggerate differences. Inspect the whole photographs
and unresized crops, especially faint marks and narrow-focus detail. Choose new
output names for each trial. Active runs write an adjacent receipt such as
`on.tiff.temporal-energy.json` containing the mode, settings, source order,
alignment and completed output identities; source-content hashes require a
separate input manifest.

## Supported path and cost

Use the CPU `--merge pyramid` path with its normal soft weighting, hard noise-floor
gate, mean base and mean fallback. Every source in the alignment map must be
placed. Active mode refuses the estimator backend, source-region repair recipes,
sensor-master output, active GPU gathering and incompatible experimental spatial
floor or coefficient rewrites. Ordinary `--linear-master` output in the example
is supported; it is distinct from the experimental sensor master.

Guidance requires additional gathering/analysis, then gathering each original
capture again when it contributes to the merge. A small ring retains guidance
fields rather than an aligned image volume. Expect extra work and memory; the
CLI checks an estimated working-set budget. No comparative speed claim is made.

## Evidence and limits

**VERIFIED visual observations:** slide and chip fields looked smoother, with no
clear protected-detail loss or new color artifact in the fixed native witnesses.
This is limited to the inspected images and display. There is no demonstrated
sharpness gain or correction of the existing broad colored rims. Smoother
spatial grain alone is not a measurement of temporal noise. The real weak
single-frame detail failure in the generated tests still prevents a default
recommendation.

**MEASURED, independently verified:** on one near-black capture block, four
disjoint five-frame groups gave 5.40–12.43% lower aggregate temporal variance
(2.74–6.42% lower RMS sigma) across the fixed regions and RGB channels. Most of
this effect also occurred with spatially shifted neighbor guidance. This limited
result does not establish general photographic noise reduction, calibrated
radiometry or detail preservation. The
[public research status](research/metadata-continuation-2026-10-25.md#temporal-energy)
retains the generated failure, limited photograph observations and dark-repeat
qualification. Detailed campaign receipts and private capture data are retained
separately from the public source package.

When redistributing a build, retain the corresponding source/relink kit and
notices described in the [RAW decoder notice](raw-decoder-notice.md) and
[release workflow](development/release-workflow.md). Do not distribute a lone
statically linked executable.
