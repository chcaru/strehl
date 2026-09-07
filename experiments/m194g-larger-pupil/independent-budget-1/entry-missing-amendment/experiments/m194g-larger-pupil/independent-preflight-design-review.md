# M194g independent preflight design review

2026-09-07. **Bounded design pass for geometry-only implementation and its
independent controls.** No geometry count, timing experiment, numerical
integration, scalar image, noise draw or product render was run. Intended
counting still requires the committed source/configuration release and actual
passing controls. Later float admission is not granted by this review.

Reviewed final draft `preregister.md` SHA256:
`d0c570ec892a2c3e40b90c0f7eef2a9ff0649dd53bc34adee6b6bc65280f14c8`.
The preceding design notes are M194f `next-larger-implementation.md`
(`987d7923577ffea261981b097190fa1886d03069d05b47ad10a17652b6e1bb61`)
and `next-larger-preregistration-notes.md`
(`800586f20914af01f67b262b44eba024a371923ca1cc88ed277e4ccef66d9704`).
Frozen M194e sources inspected are `model.py`
(`a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8`)
and `render.py`
(`487c1727ca3aab05dd66a7056fb368712ccaabbbe604818fdc8b47eda77b6e97`).

## Concrete issues corrected before this review passed

1. **Otherwise inert resource enforcement.** Frozen `cell_triangles`,
   `tangent_indices`, `triangle_rule` and `angular_cuts` neither check time
   nor report their arrays to `Meter`. The revised protocol explicitly makes
   the wrapper enforce a single non-resetting60CPU/120wall-second allowance
   across all fifteen arm/frame traversals, including analytic-only cells,
   with per-cell/rule checks and unique-backing-array accounting. Constructing
   the existing Meter alone would not enforce any limit on this path.
2. **An impossible broad diagnostic byte-null.** Counters, hook receipts,
   mode fields, timing and ordered traversal digests intentionally differ
   across observer modes or traversal orders. The revised equality requirement
   applies to numerical scalar/indicator/branch arrays. It no longer requires
   contradictory identity of changing execution evidence.
3. **The wrong height can count the wrong consumer.** The selector's exact
   rational height is not the rounded height used by `render_points`.
   The revised preflight now explicitly uses `Similarity.inverse(xy)` followed
   by the scene-normal dot product and offset for cut height, with `native_mask`
   radius and signed foreground-defocus alpha. A cancellation/negative-height
   companion must expose replacing that sequence with a rational or
   precombined height. Otherwise a plausible interval count could describe a
   different algorithm from the fallback it was intended to budget.

## Conditions to execute at source/control release

- **Exact coverage and work units:** every arm must visit the complete
  five-frame320×240 coordinate set once. Include arm, original index and
  coordinate in coverage, so duplicating one frame cannot replace another.
  A total count or opaque digest alone is insufficient. Retain low and high
  cell-rule calls separately: primary and angle-refined roots have16+64 points;
  cell-refined roots have64+256. Nominal angular nodes are each nonempty
  interval times48 for primary/cell-refined or96 for angle-refined. Repeated
  point coordinates remain separate evaluations, not deduplicated work.
- **Actual mass and cuts:** run `validate_cell_rule` on both rule weights and
  check complete cell root area as `render_cell` does. Preserve both signed
  heights, zero defocus and coincident cuts; do not replace actual floating
  partitions by the earlier ideal-geometry triangle bound. An omitted low
  rule, negative-height ladder, frame or cell, duplicate coordinate and wrong
  branch must fail with a valid companion. Geometry-only execution must not
  call Field/radiance, Bessel or pupil integration functions.
- **Real limits:** cover analytic-only traversal in injected time failures,
  enforce strict nominal thresholds (equality at8m points or1.2bn nodes is a
  refusal), and test both a permitted companion and a crossing. The whole-run
  clock must cover coefficient setup and traversal, not restart at each
  frame/arm. Account for retained rule arrays/caches and simultaneous views by
  backing allocation; keep the declared32MiB tracked-array scope distinct
  from RSS, Python-object overhead and uninstrumented library temporaries.
  Stream the ordered digest rather than retain the complete point/cut log.
- **Actual import/source closure:** freeze wrapper, selector, configuration,
  counter, independent controls and their imported local dependencies before
  intended traversal. Frozen `render.py` imports `model` by its bare module
  name. A new module alias therefore needs an explicit binding to the pinned
  model during import; hashing an unused model file is insufficient. Record
  actual module paths, source snapshots, versions and original arguments,
  then check the same source bytes after execution. Source mismatch, missing
  imports and changed settings must refuse; a fresh cache is not a substitute
  for this binding. This is a narrow local closure, not a new generic evidence
  framework.

These are unexecuted release conditions, not claims that the unwritten wrapper
already satisfies them. Refusals must retain partial evidence and remain
`UNCOMMISSIONED_COST`; no successful subset releases radiance work.

## Geometry, budgets and later scope

The squared-distance selector has the correct declared continuous-affine
meaning: native-square support uses M-transformed normal and foreground pupil
radius for either selected layer. Equality goes to coupled fallback. The4096-
bit guard bounds all exact-rational intermediates, not just their final reduced
fractions. An otherwise valid unsupported coefficient set must take unchanged
fallback, rather than silently approximate or alter its coefficients; invalid
nonfinite input is a separate refusal. No such guard proves pointwise identity
to rounded inverse mapping or clipping. The proposed external integral-error
bars correctly remain necessary at tangency and under cancellation.

**DERIVED only:** the point units above agree with the frozen helper API.
The previous ideal-partition worst-frame cell-refined point bound3,072,000 is
below the nominal8m ceiling, so that bound does not force a failure. Conversely
the loose68-interval envelope reaches10,027,008,000 angular nodes, far above
the1.2bn nominal ceiling. It cannot establish admission or impossibility: it
does not say that every point realizes the maximum. The actual geometry
preflight is needed. No runtime or memory measurement follows from these
arithmetic bounds, and the factor-two work margin does not bound adaptation.

A cost pass counts only initial geometry-dependent work. It does not validate
analytic transfer values, quadrature accuracy, adaptive resource sufficiency
or complete expected frames. The separately released radiance controls and
all fifteen complete arrays must still meet the registered external max/RMS,
boundary-band and refinement limits; analytic interiors must not dilute
unreported boundary errors. Independent reference code and its resource
allowance must be frozen before its launch. The old64×48 M194e gate is lineage,
not authority for320×240, and no noise/CFA/three-band quality claim is released
by this first phase. Zeno owns the separate spatial-math design review.

This review used document/source reads and SHA256 inspection only. Frozen
M194e sources and all prior artifacts remain unchanged.
