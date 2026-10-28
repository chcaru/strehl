# Final-CFA color pilot execution state

2026-10-27. Source prepared and independently reviewed; no build, operator
execution, numerical control or photographic result exists for this pilot yet.
The separate native-spectral full299 process finished cleanly in root
session15141, and complete photographic review rejected that fixed fusion
recipe. The user-requested stopping point has been reached. Do not run this
prepared pilot without a later user resumption.

The user subsequently requested a good stopping point and status report around
18:49 local. Root finished and reviewed the already-running full299 output.
This prepared final-color pilot remains unexecuted at that boundary; the
prospective commands below require a later user resumption.

The source-ready implementation has one independent-color spectral completion,
one normalized-camera writer with no second normalization/completion, twenty
retained generated controls and separate independent source review. Both root
wrappers were syntax-parsed without importing or executing their modules.
All numerical thresholds remain prospective. See brief.md, controls-protocol.md
and independent-source-review.md for exact scope and known adverse cases.

After the full299 job is terminal, first verify and present its complete ordinary
MHC candidate/uniform photographs using the existing native-spectral delivery
wrapper. Do not infer a gain from its generated controls. The new writer can
then be registered as a standalone Cargo example pointing to this directory;
no product default changes are planned. Root alone releases jobs in this order:

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/final-cfa-color/pilot/run.py build --iteration 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/final-cfa-color/pilot/run.py null --iteration 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/final-cfa-color/pilot/run.py controls --iteration 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/final-cfa-color/pilot/run.py cost --iteration 1
```

These are prospective commands, not an execution record. Observe each result
and independently review controls before releasing dependent work. The cost
uses the exact complete held native baseline CFA and real large FFT shape,
including workspace, final native development and preservation/readback. It
is also the direct baseline-only final-color intervention, not a synthetic
timing surrogate. Failed mechanical controls or resource bounds stop dependent
execution without substituting another recipe. Preserve all failures.

If valid and practical, run the unchanged operator on candidate and uniform
full299 CFA fields with the corresponding run.py stages, then run-delivery.py.
Its required held-receipt is the cost result; the six retained photo arms are
held-mhc, held-color, candidate-mhc, candidate-color, uniform-mhc, uniform-color.
All six complete photographs, RGB16/float masters and sixty fixed native384
witnesses are mandatory, with the held native and Helicon B4/B8 workflows and
their gauge/development caveats. Any actual gain requires independent review
and broader flat/second-insect transfer; a null does not complete the goal.
