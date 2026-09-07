# Amendment4 independent API binding before execution

2026-09-07, after committed release d32bd33a, before the first candidate run.
The exact interfaces supplied by the author are `Integrator.cell_point_tolerance`,
`render_points(..., *, point_tolerance=None)`, and
`validate_cell_rule(triangle, weights)` called on both actual consumed rules.
The numerical renderer hash remains an external command argument; no execution
will use an unannounced mutable source.

The absent-mask smooth analytic fixture in the committed independent review
requires mask metadata despite having no visible foreground. Complete those
constructor fields as normal(1,0), offset0, mask_state absent, frame index0.
These are fixed before execution. The mask has no physical effect here, while
its orientation can set the numerical angular start convention. No parameter
was tried to choose this convention.

Constant/affine mass companions use the already registered normal triangle
[(2.25,-1.5),(4.25,-2.25),(3.25,0)] and tiny triangle
[(0,0),(1,0),(1,2^-50)]. Backgrounds are10000 and10000+3x-2y;
foreground8000, absent mask, and the registered defocus remain unchanged.
These affine fields are positive on their bounded evaluated cell/pupil domains;
no unrestricted photographic-scene claim is made.

Each run copies actual numerical source, the independent control source and
both independent design/binding documents into a new output directory, and
imports that copy under a fresh interpreter/cache prefix. Runtime receipts
record `sys.orig_argv`, executable, xoptions, versions and source hashes.
All faults and failed/unpowered results are retained before any correction.
