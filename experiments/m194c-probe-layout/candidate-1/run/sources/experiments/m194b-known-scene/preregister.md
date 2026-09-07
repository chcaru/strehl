# M194b — first production known-scene baseline

2026-09-07. Allocated in AGENTS and committed at
`19e230fbd44f58badd0959906ae1f1eb5519c60a` before dispatch. This brief is
written before generating the first benchmark bracket or production output.
It narrows the committed `review-production-truth/forward-model-plan.md` to its
first stop point. The producer, consumer, scorer and independent preregistrations
state their own finite falsifiers; none is replaced by a successful process exit.

## Fixed scope and baseline

Use the M194 shared production input path at the above revision, with only a
test-only manifest adapter added. The sole production baseline uses gate 2,
Catmull-Rom, three Laplacian bands plus base, two workers, full native MHC,
CameraLinear output, unity exposure and the actual nine-frame Crop domain.
No admission or arithmetic change is compared in this milestone.

The 320x240 sensor, explicit synthetic gain 0.25 DN/electron and read noise
4 electrons, black 512, white 15360, ISO label 160, scalar channel factors and
fixed WB are those in the design brief. Inject that model once. The frame-4
gauge and nine-rung M103 curved scale series are declared before images exist.
M103's published source values are reused software inputs; this is not an
independent measurement of the old capture. Freeze the actual output crop and
mapping before rendering, and score the fixed canonical 192x112 main window.

Baseline matrix, **40 actual TIFFs**:

| Scene | Input repeats | Render modes | Outputs |
|---|---|---|---|
| Flat | Noise-off plus seeds 701,709,719,727,733,739,743,751 | Full nine; original best-focus frame 4 | 18 |
| Single textured plane | Same | Same | 18 |
| Analytic spatial color | Noise-off | Same | 2 |
| Achromatic component null | Noise-off | Same | 2 |

Every single-frame output retains the original nine-frame domain, full-plane
centre and known placement. It is an available algorithm comparator, not an
oracle or mathematical lower error bound. Compare matching input bytes across
the two modes. Keep actual TIFFs in isolated ignored work storage and commit
their content/pixel hashes, complete settings and measurements.

## What may be concluded

Flat/DC, sensor arithmetic, CFA/crop mapping, analytic color and the declared
single-plane optical model have separate admission records. A failed numerical
optics check withholds the dependent observation-target conclusion. It cannot
erase a supported flat or coordinate result, nor can a successful flat test
commission optics. The specified S4/S8 and margin48/96 checks bound numerical
error; preserve refinements and failures rather than silently increasing a
tolerance. An effect below twice the relevant observed numerical difference
does not rank candidates.

Report per-channel reconstruction error, fixed-wave amplitude/phase and repeat
temporal variance. Disclose the eight-repeat uncertainty and all rails. No
pixel-independence confidence interval, output registration, brightness fit or
output-chosen ROI is allowed. This evaluates delivered pixels under specified
software stimuli. It does not commission a physical PSF, real occlusion-halo
quality, camera calibration, native performance or any SOTA axis.

Two-layer compositing/occlusion is explicitly deferred to the next small
extension with its own alpha/order controls. No new photography, commercial
comparator, sealed capture, holdout tuning, historical bar or scorecard edit
belongs to this first baseline.

## Prior art and independent work

Executed before dispatch:

```text
python -X utf8 experiments/ORCH-drift-check/prior_art.py known scene production truth benchmark
```

The query returned M194, M113-spectral, BUILD-DEMOSAIC, M135-detail-instrument,
M-PHASE0-RHO, M84b-ruler-metrology, M166-truth-reference-capture-audit,
M164-dominance-manifest, M136-m8-census-groundtruth and M192d. Also mentioned:
M87-occlusion, ORCH-veiling, M166-m10-definition-repair, M63-bimodality,
G-edof-deconvolution and M70-through-focus-spectrum. The committed design audit
also covers M25, BUILD-BLEND, M103, M48, M72 and M90. These delimit the claims;
an already answered or failed scope is not presented as a new discovery.

Producer: directional_detail. Consumer: implementation_audit. Scorer/program:
root. Independent verifier: roadmap_audit, with a different shape, phases,
coordinate algebra, noise draws and numerical optical reference. The verifier
must check actual CFA/TIFF bytes and re-choose controls, not only recompute a
summary. All agents preserve original M25 sources and M194 evidence.

The consumer adds vetted MIT/Apache test-only serde, serde_json and sha2
dependencies for strict typed JSON and cross-read content binding. This scoped
dependency extension was authorized before edits; exact versions/licenses and
lockfile delta are retained with its author evidence. No dependency
implementation source or forbidden repository is read.

After the commissioned baseline, choose one concrete quality mechanism using
its measured failure. Do not tune multiple parameters to make these fixtures
win, and do not claim this development baseline grants real-capture admission.
