# Multi-stack sessions

A session keeps several focus stacks of the same subject together. Each pass
retains its own capture order, calibration and identity. Ordinary single-folder
stacking continues to use the existing pipeline. These capabilities are opt-in
in development builds; the alpha.6 download predates them.

## Choose the result

| Mode | Result | Suitable inputs |
| --- | --- | --- |
| Combine detail | One photograph and scene-linear master, with captures admitted separately across focus. | Related passes with equal camera, lens, ISO, aperture and shutter time. |
| Interleaved focus | One photograph from complementary focus positions, retaining each pass's order. | Offset focus ladders that fill one another's missing focus coverage. |
| Repeated captures | One photograph and master; proposed matching observations are averaged only where their coefficients agree with the injected noise model. | Repeated focus sweeps of a static subject under stable lighting. |
| Exposure range | One photograph and master from compatible exposure passes, excluding clipped samples when an unclipped observation is available. | The same camera, lens, ISO and aperture, with different shutter times and stable lighting. |
| Aligned layers | One photograph and master per pass on a shared canvas. | Aperture, exposure, polarizer or lighting changes that should retain separate appearances. |
| Wider mosaic | An experimental wider canvas with measured overlap, focus-dependent geometry and explicit coverage. | Overlapping views with enough independently supported native correspondence; unsuitable overlap is refused. |
| Independent views | One photograph, master and focus/geometry bundle per viewpoint, each in its own coordinates. | Different subject angles that should remain separate, including inputs for external photogrammetry. |

Exposure range validates a bounded correction to the nominal shutter ratio.
It tests supported color/brightness consistency on separate spatial patches
and across several proposed focus pairs. A measured contradiction refuses the
pass; successful pairs cannot hide failing radiometry elsewhere in the sample.
The correction and refusal evidence are saved in `photometry.json`. If it
cannot validate a shared exposure scale, choose Aligned layers. These checks
do not establish a general camera response or prove physical focus equality.

A **pass** is one focus sweep. A **continuation folder** belongs to the same
sweep and extends its capture order. Add a separately acquired sweep as another
pass, even when its filenames restart at the same number. A copied RAW is not
another observation: the engine hashes original files and rejects duplicate
content anywhere in a session.

Repeated captures need not have equal lengths. Fitted scale and direct
cross-pass measurements propose possible partners; they do not establish
identical physical focus. Unmatched captures remain useful independent inputs.
Local disagreement prevents repeat averaging. Results depend on placement,
subject motion, illumination and focus coverage; a second stack does not
guarantee less noise or more detail.

## Optional primary stack

Leave **Automatic · no preferred pass** selected for symmetric fusion. The
engine still chooses a coordinate reference and its final white balance.

Selecting a primary stack anchors the output framing and prefers that stack
when supported, proposed matching observations disagree. Useful unmatched
focus captures can still contribute. This preference does not lock every pixel
to the primary photograph, and it cannot replace missing focus coverage.

For aligned layers, the choice sets the shared reference and initially viewed
layer; each layer keeps its own appearance. Wider mosaic and Independent views
have no primary preference. Switching to either mode clears it.

## In the desktop

1. Import the first stack, open Projects and choose **Create multi-stack
   session…**. Its ordinary catalog entry remains available.
2. Add independent passes or continuation folders. Reorder passes and folders
   explicitly, give them useful names and select the desired result mode.
3. Optionally choose a primary, then set the session RAM budget in Adjust.
4. Stack the session. Its saved recipe records the ordered sources, mode,
   primary and resources. Each new run has its own outputs and reports.
5. For aligned layers, choose the saved layer to inspect or develop. Source
   groups on the timeline retain pass boundaries and continuation order.
6. For independent views, select a view to inspect its own photograph and maps.
   **Export view bundle…** copies the complete bound result to a fresh folder;
   the copied bundle can be imported again after relocation.

A changed source list requires a reload. The worker verifies its completed
source census before publishing a saved result. Returning to an ordinary stack
restores the ordinary recipe, including exposure and worker settings.

Session renders currently use full resolution. Temporal smoothing, frame
limits, automatic exposure, source-repair recipes and ordinary coverage controls
are unavailable for sessions. Develop and export the retained photographs
after stacking. Session controls explain these restrictions rather than
silently ignoring settings.

## Optional evidence and reconstruction

**Weight repeats by predicted noise** uses separate guide acquisitions to predict
noise for compatible repeated observations. It is available for Repeated
captures and Exposure range. Disagreement still prevents averaging. The guides
and adaptive admission mean a saved conditional variance is not an unconditional
noise estimate for the final developed photograph.

**Save contribution maps** records source/group influence by detail scale.
It also retains `sensor-master.tiff`: the signed, black-subtracted native CFA
merge before demosaicing, white balance and display exposure. The report records
its coordinate origin and applied per-pass photometric gains. When original-CFA
reconstruction is enabled, this diagnostic remains the native merge baseline;
the later reconstructed RGB photograph and linear master are separate outputs.
**Save focus evidence** records per-pass focus ordinals, support and ambiguity.
An ordinal identifies a position in that pass's capture order; it is not a
distance or metric depth. **Compare the first two passes** adds reproducible
detail and disagreement maps and frequency curves. Shared processing or fixed
pattern noise can increase agreement, so these curves are not resolution tests.

**Original-CFA reconstruction (experimental)** estimates supported color directly
from the original sensor samples in Combine, Interleaved, Repeated and Exposure
range modes. It retains native output dimensions and keeps the ordinary stacked
RGB pixel wherever focus, phase diversity, geometry or appearance support fails.
Saved support and fallback-reason overlays show where it was used. It adds work
and does not guarantee more detail; the complete chart experiment so far showed
verified sparse replacement without a clearly visible detail improvement.

Wider mosaic computes its own focus and coverage evidence. Its implementation
and supplied-capture validation are still under active development; a connected
overlap graph alone is not sufficient to publish a qualified mosaic. Unsupported
canvas regions remain transparent. Independent views always retain separate
gauges, with unknown relative pose explicitly recorded; the bundle does not
perform 3-D reconstruction.

## Command line

Save a version-1 JSON manifest. Relative folders resolve beside the manifest;
absolute paths are also accepted.

```json
{
  "version": 1,
  "mode": "repeat",
  "passes": [
    { "name": "First sweep", "directories": ["captures/first"] },
    { "name": "Second sweep", "directories": ["captures/second-part-1", "captures/second-part-2"] }
  ],
  "primary_pass": null
}
```

The mode values are `combine`, `interleave`, `repeat`, `hdr`, `layers`, `mosaic`
and `independent_views`. `primary_pass` is null or a zero-based pass index;
it must be null for `mosaic` and `independent_views`.

```powershell
strehl session inspect session.json --hash-sources --out inspection.json
strehl session stack session.json --out-dir results/run-01 --cache cache/session --threads 16 --memory-limit-gib 16
```

The output directory must be fresh and outside every source folder. Inspection
reports also refuse to overwrite existing files. Captures are read-only; no
shared capture sidecar is written.

To save geometry separately:

```powershell
strehl session align session.json --out geometry.json --cache cache/session --threads 16 --memory-limit-gib 16
strehl session stack session.json --alignment geometry.json --out-dir results/run-02 --cache cache/session --threads 16 --memory-limit-gib 16
```

An explicit alignment must match the exact session, original identities,
resampler, settings and implementation binding. Otherwise the command refuses
it. Without `--alignment`, the persistent cache reuses only geometry that passes
the same checks.

Optional flags are `--precision-weights`, `--contribution-maps`,
`--focus-evidence`, `--reproducibility` and `--original-cfa-reconstruction`.
The CLI validates mode/option combinations before processing. For example:

```powershell
strehl session stack repeat-session.json --out-dir results/repeat-02 --cache cache/session --threads 16 --memory-limit-gib 32 --precision-weights --contribution-maps --focus-evidence
```

Ordinary one-pass, one-folder Combine/Repeat sessions delegate to the unchanged
single-stack pipeline. Their session memory limit does not change that
pipeline's existing memory planner.

## Outputs and resources

A fused run contains `photograph.tiff` and `master.tiff`. Layers contain these
files in `layer-01`, `layer-02`, and so on. The photograph is an SDR rendering;
the master retains scene-linear values for later development and HDR export.
Independent views use one child result per view and a parent manifest binding
their own source identities, calibration, coordinate systems and focus maps.
The view bundle export copies these completed results, without copying RAW files
or personal development edits. A preexisting destination is refused.

The run also retains the resolved session, full original-file hashes,
calibration, alignment, fusion diagnostics and a completion receipt. A failed
or cancelled run may retain diagnostic files, but is not a completed saved
result. Actual missing coverage is reported instead of being published as
black image data. Regions clipped in every available observation cannot be
recovered.

The separate session RAM budget defaults to 16 GiB. Increase it when the
checked reservation requires more; the engine refuses an insufficient budget.
Original decoded storage remains `u16` CFA. Sampling and fusion arithmetic use
`f32`, with bounded consuming workspaces and no aligned image volume.

The disk cache stores original CFA data, exact-bound geometry and small measured
noise-transfer reports. Repeat renders can reuse these calculations when the
operator, canvas and implementation match. It can grow substantially for deep
stacks; choose a destination with space for the originals' decoded CFA data.
Cache corruption is rejected. Removing an idle session cache causes later
renders to rebuild it.

CPU workers handle the engine's direct gathers and coefficient fusion; the
desktop viewer uses the GPU. Original-CFA reconstruction can retain more original
sources when the memory budget permits, which avoids repeated cache reads across
concurrent tiles. Its per-estimator source cap remains bounded. The implementation
does not currently use the GPU for engine fusion or provide calibrated depth.

## Evidence and limitations

The implementation and experiments are recorded in
[the multi-stack research directory](../experiments/multi-stack-2026-10-28/brief.md).
The proposal's scale pairing, resolution and mosaic claims are treated as
hypotheses. Large viewpoint changes, uncontrolled motion and changing
reflections may not fit the shared geometry. Aligned layers preserve useful
separate results when fusion is inappropriate; they are not a 3-D registration
or reconstruction system.

Current completion status and the limits of the measured outcomes are recorded
in the [requirements and evidence matrix](../experiments/multi-stack-2026-10-28/completion/review/requirements-completion.md).
