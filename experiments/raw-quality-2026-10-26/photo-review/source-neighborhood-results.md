# Weevil source neighborhoods and actual-gather observation

**VERIFIED — source-supported diagnostic evidence, no photographic improvement.**

The complete source-TIFF locator ran successfully once. All 299 source TIFF
hashes matched the completed exporter receipt. Generated blur/noisy-flat controls
ran before photographic statistics; they demonstrate that these energies can
reward noise and therefore cannot serve as quality metrics. The actual dark
background was measured before each subject region. The bounded process exited
0 in 101.891 seconds with peak job commitment 448,356,352 bytes and no termination
or cleanup errors. These are operational costs during concurrent host work,
not a speed benchmark. Invocation and accounting are in
`source-locator-process-1/`.

| Frozen site | Broad locator interval, inclusive | Native neighbor views inspected |
| --- | --- | --- |
| upper-leg-hairs | 130–156 | 142,143,144; earlier original149 |
| thorax-texture | 95–115 | 104,105,106 |
| turquoise-scales | 81–106 | 92,93,94 |

Indices are zero-based in the pinned 299-source order. Complete contact sheets
were inspected first for orientation. Each listed 384-square native view was
then inspected separately without resizing. The actual map locates source crop
centers, rounded to even native coordinates; native scale/rotation differences
are retained. `source-locator-1/locator.json` records every rectangle and scalar
sequence. The source TIFFs have fixed premerge tone; inverse sRGB in the locator
is display-linear after tone, not scene-linear radiance.

Real bright scale marks and separating dark gaps persist across the three
neighboring source views at each scale site. However, sharp focus still changes
across a single 384-square crop because of subject depth. At these inspected
sites, no specific source-supported structure erased by the baseline has been
established. This is **not** evidence that no erasure exists elsewhere, that the
capture reached its optical limit, or that source and stack have equal feature
width. Those would require additional matched photographic measurements. Hard
white/cyan glints are already present in the focused sources, so their appearance
in the stack is not by itself a color-focus failure.

## Actual consumer split: an earlier color-fringe change

Root captured original149 through the actual production full-resolution CPU
gather, using the complete retained map, original tiny reference-gauge roundoff,
runtime gear profile and native delivered crop. This lane did not reimplement
that gather. The original captured u16 crop exactly matches the independently
decoded RawPy array on the entire delivered rectangle. Capture and array hashes
are in `outputs/raw-quality-2026-10-26/weevil-anchor149-gather/capture.json`.

The captured original and gathered CFA were developed with the same repository
MHC port, same 512/15360 levels, as-shot WB and camera matrix. They and the actual
stack's retained linear master use one fixed gain3.434/sRGB display. No local
fit, sharpening, resizing or denoising was added. `source149-gather-1/receipt.json`
binds the PNGs and float patches. The port's float operation order can differ
slightly from the native writer; both original/gathered arms share it.

At the hair site, the actual gathered arm has visibly stronger orange/blue edge
separation than the original, particularly along portions of the upper outline
and lower protruding hairs. A similar colored surround is present in the
completed stack. The stack also resolves more of the appendage's depth than
anchor149; that is not a reason to treat its whole crop as a worse image.

Exact u16 phase differences in this frozen 384-square site:

| CFA phase | Changed sites / 36,864 | Mean absolute change, DN |
| --- | --- | --- |
| R | 31,228 | 21.4966 |
| G1 | 0 | 0 |
| G2 | 0 | 0 |
| B | 17,971 | 5.4622 |

Thus the colored-edge change enters during the red/blue gather before temporal
stack merging. The visible dark-background control remains nearly black in both
single-source arms; the stack has more visible faint colored specks under this
fixed display. This is a control observation, not a calibrated noise estimate.

**ARGUED next causal check:** repeat the actual consumer with the same149 map and
CA forced off. The present split combines source MHC, channel-specific CA
coordinates, resampling and u16 rounding, so it does not yet isolate a faulty CA
coefficient. A source-dependent CA calibration or applicability check is a
promising generally applicable direction if the off-control supports it.
Globally disabling a measured profile, or declaring fine-detail recovery from
this crop, is not justified. Any proposed fix still needs a complete weevil
output, full-resolution master, all frozen guards and independent review.

Executed from the current worktree:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-26/photo-review/run-locator.py
python -B -X faulthandler experiments/raw-quality-2026-10-26/photo-review/develop-gather.py
python -B -X faulthandler experiments/raw-quality-2026-10-26/photo-review/measure-gather-phases.py
```

No original RAW was read by these commands. The previously completed full stack
and master remain the baseline linked in [baseline-review.md](baseline-review.md).
The full Helicon comparison is being reviewed independently by the integration
lane; neither these local source views nor locator energies substitute for it.
