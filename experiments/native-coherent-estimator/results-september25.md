# Generated screen: do not advance this fixed estimator

MEASURED: the recovered generated screen completed all twelve cases. Neither
general qualification nor the separately planned optional chip observation
was admitted at ISO100 or ISO400. No RAW photograph was processed by this
candidate, and no full-image improvement is claimed.

Commands run from the repository, using Python312 with `-I -B -X faulthandler`:

```text
experiments/native-coherent-estimator/runner.py build --out experiments/native-coherent-estimator/build-1
experiments/native-coherent-estimator/runner.py build --out experiments/native-coherent-estimator/build-2
experiments/native-coherent-estimator/runner.py controls --build experiments/native-coherent-estimator/build-2 --out experiments/native-coherent-estimator/controls-1
```

Build1 failed on the previously uncompiled PlaneGeometry import. The mechanical
recovery and corrected module path are recorded in recovery-september25.md.
Build2 freshly compiled the relevant crates and completed; controls1 completed
in3.203s. A successful test-process exit means measurements completed, not that
image quality passed. Source bindings, commands, process records and complete
screen.json are retained in those directories.

Flat controls were run first. Candidate/current RGB RMSE ratios were0.89743
and0.89660, and chroma ratios0.88820 and0.88684, at ISO100/400 respectively.
Broad-contact interior RGB ratios were0.24213/0.32159 and edge ratios
0.60944/0.64838. These gains are accompanied by a decisive adverse scene:
near-fine/far-coarse RGB error rose2.46107/2.44977 times and chroma error
2.37902/2.37897 times. Neutral-glint extension chroma error rose
1.47720/1.49169 times. Thus cleaner contact regions do not establish general
improvement or justify suppressing the far surface.

The optional-quality booleans are true, but optional-fixture booleans are false
for near-fine/far-coarse, and the frozen combined admission is false. Independent
review by the mineral diagnosis agent identifies why: the candidate already
equals the forced wrong donor0 bit-for-bit. The destroyer therefore cannot
change an already wrong output. The genuine far component exists; its recovery
is about0.216 against current about0.77. This is not an excuse that the adverse
scene lacks truth. Separately, the inherited outside bright-spill positive is
unexercised for general qualification. Neither failed condition is removed.

These errors compare against generated scene truth and can be fooled by
unrepresentative scene/noise models; they do not calibrate the legacy guide
noise scale against the camera. Protected component recovery and meaningful
destroyers accompany the scalar errors in screen.json. The legacy gathered
guide noise constant remains uncalibrated. No claim about actual mineral or
marigold noise, glare, ghosting, or SOTA follows from these numbers.

Decision: close this fixed estimator without constructing the missing full
photograph adapter or retuning thresholds to the observed cases. Continue the
independent full-image merge/rendering investigations already in progress.
