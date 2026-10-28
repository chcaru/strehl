# Multi-stack sessions

A session keeps several focus stacks of the same subject together. Each pass
retains its own capture order, calibration and identity. Ordinary single-folder
stacking continues to use the existing pipeline. These capabilities are opt-in
in development builds; the alpha.6 download predates them.

## Choose the result

| Mode | Result | Suitable inputs |
| --- | --- | --- |
| Combine detail | One photograph and scene-linear master, with captures admitted separately across focus. | Related passes with equal camera, lens, ISO, aperture and shutter time. |
| Repeated captures | One photograph and master; proposed matching observations are averaged only where their coefficients agree with the injected noise model. | Repeated focus sweeps of a static subject under stable lighting. |
| Exposure range | One photograph and master from compatible exposure passes, excluding clipped samples when an unclipped observation is available. | The same camera, lens, ISO and aperture, with different shutter times and stable lighting. |
| Aligned layers | One photograph and master per pass on a shared canvas. | Aperture, exposure, polarizer or lighting changes that should retain separate appearances. |

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
layer; each layer keeps its own appearance. Sessions do not currently provide
stitching, so a primary preference is never applied to a mosaic.

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

A changed source list requires a reload. The worker verifies its completed
source census before publishing a saved result. Returning to an ordinary stack
restores the ordinary recipe, including exposure and worker settings.

Session renders currently use full resolution. Temporal smoothing, frame
limits, automatic exposure, source-repair recipes and ordinary coverage controls
are unavailable for sessions. Develop and export the retained photographs
after stacking. Session controls explain these restrictions rather than
silently ignoring settings.

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

The mode values are `combine`, `repeat`, `hdr` and `layers`.
`primary_pass` is null or a zero-based pass index.

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

Ordinary one-pass, one-folder Combine/Repeat sessions delegate to the unchanged
single-stack pipeline. Their session memory limit does not change that
pipeline's existing memory planner.

## Outputs and resources

A fused run contains `photograph.tiff` and `master.tiff`. Layers contain these
files in `layer-01`, `layer-02`, and so on. The photograph is an SDR rendering;
the master retains scene-linear values for later development and HDR export.

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
desktop viewer uses the GPU. This implementation does not promise GPU fusion,
super-resolution, calibrated depth or depth-aware stitching.

## Evidence and limitations

The implementation and experiments are recorded in
[the multi-stack research directory](../experiments/multi-stack-2026-10-28/brief.md).
The proposal's scale pairing, resolution and mosaic claims are treated as
hypotheses. Large viewpoint changes, uncontrolled motion and changing
reflections may not fit the shared geometry. Aligned layers preserve useful
separate results when fusion is inappropriate; they are not a 3-D registration
or reconstruction system.
