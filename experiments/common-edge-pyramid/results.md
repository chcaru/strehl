# Common-edge pyramid: fixed recipe rejected

2026-09-26. Root executed the independently authored controls. **MEASURED:**
the implementation passes its arithmetic checks but fails the photographic
nomination screen. No full RAW candidate was run and no default changed.
The independent interpretation is in `independent-results.md`.

Commands run from the repository, using installed Python 3.12 with
`-I -B -X faulthandler`:

```
experiments/common-edge-pyramid/run.py build --out experiments/common-edge-pyramid/build-1
experiments/common-edge-pyramid/run.py build --out experiments/common-edge-pyramid/build-2
experiments/common-edge-pyramid/run.py controls --build experiments/common-edge-pyramid/build-2 --out experiments/common-edge-pyramid/controls-1
```

Build 1 failed on a missing `QuadSource` trait import in independent controls.
The author added that import only. Build 2 freshly compiled the CLI and
completed in 196.344 seconds. The two controls completed in 3.625 seconds,
with terminal active-process count zero and peak Job committed memory
647,745,536 bytes. These are operational observations, not speed benchmarks.
All bound sources and inputs remained unchanged during the successful runs.

The actual guide increases final RGB RMSE at the curved boundary from
0.01136408 to 0.02488815, and at the two-depth detail site from 0.00518630 to
0.01426402. The latter loses near green detail: signed component recovery
falls from 1.00855 to 0.54029, while the far component remains near its old
value. RMSE alone could reward smoothing; these separate components expose
the loss. Truth guidance also fails the fixed protections, so a corrupted
canonical guide alone does not explain the failure.

All three flat controls fail the uniform-average comparison, but are nearly
unchanged from canonical. **Correction to the brief live update:** the result
does not demonstrate a substantial new flat-noise regression; it fails to
repair the inherited selection cost relative to uniform averaging. Genuine
glint core retention passes its coefficient guard, while glint error and
adjacent-detail retention fail. No claim that the glint itself vanished follows.

The constant-guide null, ordinary canonical observer identity, independent
support enumeration, matching roundtrips, direct averaging, and live
destroyers pass. These establish implementation and scorer behavior on the
tested fixtures, not photographic quality, calibration, or seven-band
occlusion performance. No bandwidth, guide or threshold rescue follows.

The previous user-facing goal-text reply made no implementation progress.
This continuation completed the pending experiment and changed the next
action: stop this recipe and obtain focused original-frame witnesses for the
existing complete slide2 diagnostic. Its prior source149 was too defocused
to test the printed bar defects. A new source locator is an attribution aid,
not an image-quality score or evidence that geometry caused those defects.
The complete RAW SOTA goal and the glare/ghosting defects remain unresolved.
