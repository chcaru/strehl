# Complete opal rendering comparison

Root independently executed and inspected this comparison on September25/26.
The implementation author did not execute or judge the new render. **No useful
photographic improvement is identified; none of these four arms is promoted.**

MEASURED: the fresh production render uses all155 ordered originals, retained
reference77 geometry, native6792x4528 output and exposure−0.3EV. The actual
full-stack adapter reproduces every production RGB16 sample and ICC. Its
canonical chunk count and execution-thread count also match production.
All source identities and unchanged-file checks pass. The existing four
independent rendering controls pass under the same retained test executable.

MEASURED: the full four-arm replay holds resolved tone, exposure, camera matrix
and sensor ceilings exactly. The observer-on/off full TIFF is byte-identical.
Sensor-rolloff-off is byte-identical to current, and both is byte-identical to
shoulder. These identities are whole-image results, not just target agreement.
The cache invocation takes89.985s and3,517,853,696 bytes peak job commitment;
the cached factorial takes3.031s. These are individual bounded job observations,
not comparative performance benchmarks.

VERIFIED by visual inspection: current and shoulder complete-image views retain
the same broad pale reflection and blue/green/pink colour pattern. At the
frozen unresampled384px reflection target, shoulder slightly changes the
brightest marks but does not establish additional separated bands or useful
gradation. The broad washed-out appearance remains. The colour-control target
is unchanged. Reduced brightness by itself was explicitly excluded as evidence
of improved quality. No noise or sharpness-quality claim is made.

The commands run, using the system Python312 executable with
`-I -B -X faulthandler`, were:

```text
scripts/render-native.py --input D:/personal/macro/minerals/rainbow-opal-cabochon/103MSDCF --out outputs/quality-september25/opal-103 --warp-map outputs/minerals-september24/103msdcf/alignment.txt --exposure=-0.3
experiments/opal-headroom/run.py cache --build experiments/optical-support-veto/build-1 --production outputs/quality-september25/opal-103 --out experiments/opal-headroom/cache-1
experiments/opal-headroom/run.py controls --build experiments/optical-support-veto/build-1 --out experiments/opal-headroom/controls-1
experiments/opal-headroom/run.py replay --build experiments/optical-support-veto/build-1 --controls experiments/opal-headroom/controls-1 --cache-run experiments/opal-headroom/cache-1 --out experiments/opal-headroom/replay-1
experiments/opal-headroom/run.py views --run experiments/opal-headroom/replay-1 --out experiments/opal-headroom/views-1
```

Exact bindings and receipts are retained in those run directories; full native
images and both frozen native targets are in `views-1`. The production master
and full JPEG are in `outputs/quality-september25/opal-103`.

This closes the omitted fixed factorial. It does not establish where the broad
reflection originated: every arm retains the actual writer's pin protection.
A separate read-only stage observation is scoped to distinguish pre-existing
merged radiance, interpolation, pin clipping and final display mapping. No
shoulder, exposure or desaturation sweep follows this null result.
