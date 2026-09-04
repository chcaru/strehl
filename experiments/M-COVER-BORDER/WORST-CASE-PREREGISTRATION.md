# M-COVER-BORDER worst-case generality — preregistration

Frozen: 2026-09-03, before rendering or profiling
`very-tilted-all-axis-sw10-cpl`.

## Question and prior knowledge

The common-linear instrument reports:

- 109: Scale 8 plane px, Crop 256 plane px; both central artificial-window
  controls return 8.
- 113: nominal Scale 640, Crop 320; both centered artificial-window controls
  return 320, so neither physical tail is admitted as a safe inset.

The new question is whether 8/256 generalizes on the hardest available
coverage geometry.

The source is:

```text
D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\
  very-tilted-all-axis-sw10-cpl
```

The scorecard designates it `DEVELOPMENT — NOT HOLDOUT`: 197 ARWs, ISO 100,
1 s, f/5.6, 200 mm, all-axis tilt. It is commissioning/development evidence
only and will not be reported as a scored result. The capture tree is strictly
read-only.

No output from this source has been inspected for this lane before this
registration.

## Frozen executable and render arms

Use the same executable as the matched 109/113 rerun:

```text
D:\strehl-out\cover-default\target\release\strehl.exe
sha256 1AC423529D5AAD88B7141801E47DCD612FCA8061558578A88592DB715CE81A0F
```

Render four arms into `D:\strehl-out\M-COVER-BORDER\worst-case`:

```text
Scale b2, Scale b7, Crop b2, Crop b7
```

Command shape:

```text
strehl.exe stack <source>
  --merge pyramid --pyramid-bands <2|7>
  --resampler catmull-rom --cover <scale|crop> --out <scratch TIFF>
```

No `--srgb`, auto exposure, exposure, or output-scale option is permitted.

All inherited `STREHL_*` variables are removed, then:

```text
STREHL_CACHE_DIR=D:\strehl-out\M-COVER-BORDER\worst-case-cache
STREHL_FULLRES_GATHER=1
STREHL_DEFECT=off
STREHL_FIX_CA=off
STREHL_PYRAMID_WORKERS=2
RAYON_NUM_THREADS=6
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
```

The first arm may solve alignment. Every subsequent arm must use the same
serialized map; its bytes are hashed before and after each scored profile.
All four logs must report 197 placed, zero refused, identical `k`, and the
same Crop rectangle where applicable.

## Host-load gate

No arm may launch until five one-second total-CPU samples average at most 15%.

During an arm, sample total CPU and the render process tree every second.
Normalize render CPU by logical-core count and define:

```text
external busy = max(total system busy - render-tree busy, 0)
```

Use a trailing five-sample mean. If it exceeds 10%, suspend the render process
tree by PID, wait until a fresh five-second external mean is at most 10%, then
resume. Record every sample, pause and resume. The monitor itself does not
count as render CPU and therefore remains conservatively inside external busy.

The load log must record the pre-load samples, logical-core count, maximum
five-second external mean while running, and every gated pause. No process is
killed or addressed by name.

## Primary profile

Use `contradiction.py` without changing the 109/113 definition:

```text
E(lo,hi) =
  (mean G_b7(lo,hi) / mean G_b2(lo,hi)) / R_deep - 1
```

- output: default linear camera-native RGB16;
- distance: binned plane pixels from the emitted boundary;
- threshold: `abs(E) <= 0.001`;
- deep start: 768 plane px;
- edges:
  `0,2,4,8,16,32,64,96,128,160,192,256,320,384,448,512,640,768`;
- nominal safe: smallest registered `lo >= 8` whose complete deeper tail
  passes.

Because the 768+ row is normalized to zero by construction, a nominal result
of exactly 768 is a censored `NEVER_SAFE_BEFORE_DEEP`, not a measured safe
inset.

One plane pixel is two sensor/full-resolution-output pixels per axis.

## Centered artificial-boundary control

Apply the same centered `1024x1024` control used on 109/113:

- threshold 0.1%;
- deep start 384 window px;
- edges
  `0,2,4,8,16,32,64,96,128,160,192,256,320,384`.

The control is geometrically admissible only when its minimum distance from
the real emitted boundary is greater than the physical profile's nominal safe
inset. If not, report specificity `UNRESOLVED_CONTROL_INSIDE_NOMINAL_REACH`
rather than treating the control as independent.

Per mode:

- physical safe 8: `SPECIFIC_AT_FLOOR`;
- physical safe >8, admissible central control at 8 and peak <=0.1%:
  `BOUNDARY_LOCAL_SUPPORTED`;
- physical safe >8, admissible central control itself fires:
  `NONSPECIFIC_SCENE_TAIL`;
- censored physical tail or inadmissible control: `UNRESOLVED` with the exact
  reason.

## Conserved-error descriptor

Repeat the registered positive residual-mass calculation through 256 plane px
and over the full plane.

- Scale/Crop below 20% in both scopes rejects conserved-error smearing.
- At least 50% in either scope plus a lower Scale peak supports it.
- Anything else is unresolved.

This descriptor cannot rescue a failed boundary-specificity gate.

## Three-subject disposition

Report 109, 113 and very-tilted in one table with:

- nominal safe inset in plane pixels;
- censored/admitted status;
- centered-control result and physical clearance;
- per-mode specificity verdict.

Interpretation is frozen:

1. If very-tilted is specific and reproduces Scale 8 / Crop 256, the exact
   32x relation replicates on the worst geometry.
2. If specific but the ratio differs, the defect generalizes but one fixed
   inset does not.
3. If the artificial control fires, the nominal tail is scene-driven and no
   safe inset is admitted for that cell.
4. If admitted safe insets vary by at least 10x across specific sources, state
   that a single fixed inset is the wrong abstraction.
5. Negative or censored results remain valid commissioning evidence, never a
   score.

## Commissioning

Before real profiling:

- retain every existing contradiction commission;
- plant a synthetic `safe=deep_start` case and require it to be labeled
  `NEVER_SAFE_BEFORE_DEEP`;
- commission the centered-control geometric-admissibility branches;
- commission the load monitor's pre-load refusal, external-busy subtraction,
  PID-specific pause/resume decision, and zero-external null.
