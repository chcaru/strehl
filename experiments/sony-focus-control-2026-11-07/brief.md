# Sony focus control feasibility

Identifier: `sony-focus-control-2026-11-07`. Owner: root. Allocated in the
[milestone ledger](../../docs/agents/milestone-ledger.md) before implementation.

## Question and scope

Can an a7C II with the owner's FE 100mm F2.8 Macro GM, **Viltrox 2x**, and X4 CPL
produce smaller, repeatable optical focus displacements through Sony's absolute
focus interface than through native bracket width 1? Inspect the supplied SDK
and separate Camera Remote Command package for the later a7CR pixel-shift path.

Deliver a Windows USB capture helper, an executable built against the owner's
SDK, and a physical test with instructions. Do not claim a measured optical gain,
manufacture a pixel-shift API, modify the merge pipeline, install USB drivers,
or initiate a camera capture before the owner prepares the target. No campaign
on existing capture corpora; all existing RAWs remain read-only.

Owned paths: `tools/sony-control/`, this experiment directory, and ignored
`outputs/sony-control/`. Build workers: two. Sequence worker: one. No GPU work.
The protocol test produces 73 RAWs by default with a fixed, range-checked plan.
Per the owner's follow-up, photos are saved only to the camera's SD card. The
computer records logs, with no RAW/preview downloads or review copies. Storage
preflight checks the camera's remaining-image estimate against the whole plan.
Each exposure or group has a 90-second default timeout, configurable for long
exposures. SD-only saving remains selected after restoration of other settings.

## Prior work and changed input

Executed before implementation:

```powershell
python experiments/ORCH-drift-check/prior_art.py 'FocusPositionSetting' 'pixel shift' 'remote capture'
python scripts/research.py search 'focus' 'remote' --limit 4
```

The owning references are `docs/sony-focus-metadata.md`,
`docs/agents/capture-reference.md`, `docs/ARCHITECTURE.md`,
`docs/research/SYNTHESIS.md`, and `experiments/super-resolution-2026-11-01/`.
The earlier breathing-based reconstruction result does not establish an optical
benefit for this acquisition method. This experiment measures focus control,
not super-resolution. Future fixed-focus sensor shifts would introduce a different
sampling geometry and need their own allocation and evidence.

Sony SDK 2.02 describes normalized focus positions 0..65535 and reports operation
completion separately from the current value. The newly supplied PTP 3 reference
also documents a7CR pixel-shift properties. See [the audit](sdk-audit.md).

## Consumer, controls, and rejection conditions

The immediate consumer is a photographic analysis of the **position of a sharp
band on a fixed inclined texture**, in registered target coordinates. The native
width-1 bracket is the comparator, not a ground-truth motor calibration. The
normalized command coordinate is a separate gauge. Do not equate its units with
physical depth. Absolute micrometre claims require an independently calibrated
target scale, inclination and magnification.

Run flat-patch/no-motion controls first. Five captures precede any focus command;
three same-position commands form the placebo. A larger 512-unit displacement
is a candidate positive control and must visibly displace the sharp band before
the fine sweep is interpretable. It is not assumed to work merely because its
command is larger. Three repeated monotone sweeps and three returns from each
side expose quantization, direction dependence and positioning variance. Two
nine-shot width-1 bursts provide the comparator at the same starting position.

Each proposed metric must first reject a flat/noise-only patch and a deliberately
scrambled focus ordering. Edge energy alone is invalid: noise, sharpening and
breathing can increase it. Geometry must be registered independently enough that
framing drift is not mistaken for focus-band displacement. Report the null and
repeatability spread beside any claimed separation. Challenge conclusions with
different texture regions and an independent optical review before changing
product defaults. Author-run software tests are not that review.

Stop or mark inconclusive when:

- MF/absolute focus, required settings, or native brackets are unavailable.
- The command plan crosses a focus endpoint; do not clamp it.
- The larger-move control cannot be resolved with the target.
- Illumination, camera motion, clipping or return error masks the fine movement.
- A focus operation, shutter release, card write or restoration is uncertain.
- A native bracket ends early at infinity or reports fewer than nine captures.

No optical decision is implemented as a simplistic gradient threshold. The
delivered script records command and camera-event accounting, not photographic
quality or independent verification of the SD files.

## Software gates

The offline suite exercises the exact Python plan/execution code with a fake
bridge: a focus failure must prevent exposure; a capture failure must prevent
retry or later movement; wrong capture counts, a host destination, a busy card,
missing completion fields and any downloaded-file report must fail. A fake
bracket rejects changing count before changing the incompatible 0 -> - -> + order.
Positive paths account for 73 simulated card images in 57 shutter commands with
contiguous image-order ranges and no host image files. Intent is persisted before
the shutter and retained on failure. These events are not photographic evidence.

The native self-test exercises the same completion gate used by real captures:
an initially idle card without capture events must not pass, an unfinished native
bracket or card write must wait, and missing/extra events, card errors, unexpected
downloads and deadlines must fail. One second of idle state after all expected
events is required. No SDK connection is made during this self-test.

The native helper is compiled with warnings as errors and smoke-tested by real
SDK initialization/enumeration. Callback timing, SD-card completion, camera setting
restoration and physical focus behavior still require the camera test.

## Deliverables and completion boundary

See [the operator guide](../../tools/sony-control/README.md),
[SDK audit](sdk-audit.md), and [verification record](results.md).
The implementation handoff is complete when the native binary, tests, evidence
record and instructions are present. The optical experiment remains pending;
there is no SYNTHESIS fold or production quality claim at this boundary.
