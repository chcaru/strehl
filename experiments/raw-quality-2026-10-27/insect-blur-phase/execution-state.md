# Execution state

2026-10-27: fixed recipe CLOSED after complete real-source observations.
Candidate p1 places232/299 frames and p2 places226/299, leaving67/73 unplaced.
Neither is render eligible. No partial-stack render, threshold rescue or seed
edge insertion follows. No photographic gain is claimed. See results.md and
full/independent-actual-review.md. The SOTA goal remains active and unmet.

Commands actually completed:

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-blur-phase/run-controls.py --iteration 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-blur-phase/full/run-actual-controls.py
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-blur-phase/full/run.py cost --iteration 1
```

Mechanism controls: clean9.844s, all40pairs,214references independently
verified. Positive p2 errors stay below0.057native pixels; all six flat/noise/
rank cases refuse. Two mixed-depth adversities refuse. This is not physical
accuracy or photographic evidence. Peak Job commitment2,935,906,304bytes;
Torch allocated41,026,560/reserved62,914,560bytes. Pixel-free geometry/combiner
controls also pass, clean0.141s and14,135,296bytes peak Job commitment.

Cost1: clean33.266s, six pairs,576tile slots,1152physical-green slots, all299
cache bytes and original metadata preserved. Actual reader/census/JSON campaign
took0.91733s; one-time prebinding15.207s and post-verification account for most
wall time. Peak Job3,031,764,992bytes; GPU allocated141,712,896/reserved178,257,920.
The fixed pairs have p1/p2 paired-observation counts7/3,0/0,20/18,29/25,0/5,0/0
in their retained order. This is poor support on the sampled long edges and
first short pair; it does not establish complete graph coverage or a useful map.
No refusal threshold is changed. See full/cost-concurrency.md for the concurrent
native build; these timings are operational observations, not benchmarks.

Build1 failed on adapter digest formatting before tests; its sources/process
remain archived. Build2 fixes only that hash-text conversion. Cargo compiled
successfully, but one unidentified owned descendant remained to the900s bound.
The harness terminated its own job and recorded failure; build2 is not clean.
Build3 separately confirmed the unchanged cached artifact with a natural clean
exit. No unowned process was killed, and no numerical job crossed a kill boundary.

Full source implementation is in full/: actual.py, graph.rs, render.rs,
views.py and bounded wrappers. Source reviews independently checked geometry,
refusals, global solve reuse and exact CPU/direct-off rendering.
All2340pair observations completed cleanly in233.969s. Native controls and exact
2314-edge held-map replay pass. Candidate graph solve confirms the incomplete
coverage above. The prepared renderer and views source remain unexecuted.
Root moved to separately allocated weevil-fusion-order and native-spectral-fusion
questions; neither is a demonstrated improvement or extension of this recipe.
