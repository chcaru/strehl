# M194e original numerical method — retained refusal

2026-09-07. **UNCOMMISSIONED_NUMERICS.** The released geometric model remains
the subject of commissioning. Its first polar-angle/clipped-cell implementation
cannot complete the registered independent cell controls within the declared
angular depth/error limits. No complete author float-model commission or final
CFA authority follows from this attempt. No quality comparison was run.

The original preregistration and independent design were committed at
`773f576299f58ea0b0a998a22243ee837f6f7d8d`. The failed numerical source is preserved
at `independent-author-api-1/render.py`, SHA-256
`2320d2a24a8678da7d50795662bb34b54a41c5200abdc8d111d9457c86d599a5`.
The corresponding model source is
`a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8`.

## Observations and limits

**MEASURED by the independent implementation:** the first actual-author API
run passed25 controls, including same-ray visibility, focused limits and same-cell
coupling. Its transformed affine point matched the separate Cartesian reference.
The following transformed affine cell refused at the angular depth ceiling.
[Original result and traceback](independent-author-api-1/result.json), SHA-256
`50db3812ca21ce518ea26fd68479d410247c07a385b67287598c2889edfb585e`.

A separately named diagnostic then attempted all340 fixed point/cell cases on
the frozen source. All170 point cases returned within their registered tolerance.
Of170 cell cases,56 refused at the angular depth/error ceiling: the transformed
affine cell and55 textured cells. All284 returned results met their applicable
tolerance; no returned discrepancy occurred. This is not a passing-subset
commission. The overall disposition remains **UNCOMMISSIONED_NUMERICS**.
[Complete refusal map](independent-refusal-map-1/result.json), SHA-256
`dba7db6989cb54abdc7e268e4644149d5e095550c74f47a9a52858c6e453d8de`.

**MEASURED diagnostic:** one failing cell quadrature point is approximately
`(37.2056406921,24.1294608479)` in native coordinates. Its half-plane residual is
`-0.00018694746` and its transformed pupil radius is `3.07989`. The relevant
unit-circle crossing is about `0.0000606994` radians from zero projection.
After10 midpoint subdivisions, the adjacent interval is still approximately
`0.003067843` radians wide. Its low/high quadrature difference is
`0.0000501648` electron against an allocated `0.000000122066` electron.
[Diagnostic](angle-diagnosis-1/result.json) binds the source and exact invocation.

**ARGUED diagnosis:** the registered cuts are present, but a narrow transition
in radial visibility remains beside the crossing. Cell quadrature creates points
close enough to the mask boundary to expose it. A numerical refusal is not proof
of inaccurate emitted pixels: this case returns no commissioned value.

## Next action and reproducibility

Root authorized a prospective proposal for geometry-scaled angular subdivisions,
with the same model, scenes, accuracy bars and computational ceilings. Independent
review and a committed amendment must precede its implementation. The original
refusal stays part of the record; successful replacement numerics cannot erase it.
The separate Cartesian reference need not be recomputed if its bound sources and
inputs do not change. Every required author control and full-scene arm still has
to pass before float authority, and actual CFA conversion has a separate check.

Commands are recorded verbatim in each linked JSON's `argv`. The refusal-map
driver explicitly consumes the original source snapshot and externally supplied
result hash. Both independent runs report unchanged source bytes. This is a
software/numerical result, not a physical-optics, noise-calibration, performance,
merge-quality or SOTA result. No capture or historical experiment was altered.
