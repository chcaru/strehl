# Spatial reconstruction result

**REJECTED as a joint photographic repair.** Moving the fixed masks after full
AC reconstruction retains the earlier local facet gain and defines part of
the dark inclusion more clearly, but leaves its conspicuous coloured tail.
Independent review finds no decisive additional facet repair; Helicon B
remains visibly more compact at these glints. No default or automatic label
promotion follows. Close this exact frozen donor/support/order recipe.

The complete 70-frame output is 6920x4612 RGB16. Complete before/candidate/
late-control views and full masters remain under `spatial-full-1`. The
independent six-arm boards, including the previous recipe and Helicon B,
are in `spatial-review-1`; `spatial-results-review.md` states the decision.
The original RAW files and geometry remained unchanged. Baseline RGB16
pixels exactly reproduce the retained baseline.

Executed with Python312 (`-I -B`; `-X faulthandler` on the full run):

```
python experiments/donor-consistency/run.py build --out experiments/donor-consistency/build-4
python experiments/donor-consistency/run.py controls --build experiments/donor-consistency/build-4 --out experiments/donor-consistency/controls-4
python experiments/donor-consistency/run.py full --build experiments/donor-consistency/build-4 --screen experiments/donor-consistency/controls-4 --out experiments/donor-consistency/spatial-full-1 --spatial
python experiments/donor-consistency/photo-compare.py --run-dir experiments/donor-consistency/spatial-full-1
python -X faulthandler experiments/donor-consistency/spatial-photo-review.py
```

MEASURED operational costs: fresh core/CLI build151.094s, four controls0.406s,
complete triplet35.313s wall/122.75s CPU/4,045,553,664 bytes peak job commit.
These are single operations, not a speed comparison or full alignment workflow.
The spatial control exercises literal arithmetic, shared mean base, exact
zero/outside samples, overlap, both clamp directions, source order and a live
difference from coefficient masking. Passing these validates the operator,
not photographic quality. See controls-4's recorded output for the limits.

Full candidate TIFF SHA256:
`528e790139aa8db58916fe75df2a6b3523ddc867113a136eed3cfa8d578597d9`.
Independent review SHA256:
`d9e2ff72fe2de565e34604f0fbd9ba904f679038e508e825f3213dee82687b58`.
Six-arm image receipt SHA256:
`ef034630f941489fe5ad7ad5b92292ff94386df8dd1417af78f45e32c535beb1`.

Next discriminating check: inspect the actual gathered donor33 sample and
its full reconstructed AC/base at the residual tail, separate from taper,
retained baseline base and hull. A centre-mapped developed source crop is
not exact evidence of the source pixels the merge reads. Do not assume
correct donor content or placement, or sweep support to hide the failure.
The read-only concentration locator can be controlled separately; it is not
yet an admitted correction or proof of source ownership.
