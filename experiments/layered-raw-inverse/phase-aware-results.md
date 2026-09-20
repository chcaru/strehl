# Supplied sampling phases: fixed reconstruction rejected

**MEASURED; independently reviewed.** `phase-aware-3` completed the numerical
commission and both flat fits, then stopped at the predeclared image gate.
No layered or wrong-phase fit ran and no photograph or product default changed.

The phase-aware flat output has RGB/chroma RMSE **19.1481/18.6372 DN**, versus
**17.1631/16.8017** for the paired identity inverse and **5.95102/8.34724** for
its same-data mean. It fails both paired 5% guards and the same-data guards.
The historical known-alpha comparison is nonmatched; rejection does not rely
on it. These are errors against generated flat truth, not temporal-noise
estimates. Demeaning barely changes the errors, so a global colour offset does
not explain the failure. Good withheld original-CFA prediction does not protect
the delivered image. Bright and censored strata were absent.

Dense translated forward/adjoint and independent data-adequacy checks pass.
Both returned fits remain nonstationary after the fixed 160 Adam plus 1000
LBFGS iterations. Reject this recipe, without an iteration, prior or phase
schedule rescue; do not generalize this result to all motion-aware RAW methods.
The detailed choice review, controls, costs and limits are in
[independent-phase-aware-results.md](independent-phase-aware-results.md).

The two earlier commissioning refusals are retained at `3f24b149` and
`e5df5216`. The sole numerical repair changes the physical-alpha finite-
difference step from .001 to .25 and asserts admissible alpha bounds. The
fixed-radiance operator is affine in physical alpha, so this introduces no
real-arithmetic truncation. No tolerance or image criterion changed.

Root execution, repository working directory:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/layered-raw-inverse/run-phase-aware.py --out experiments/layered-raw-inverse/phase-aware-3
```

Five completed stage receipts sum to **87.500 s**; the largest process-job
committed peak is **3,147,837,440 bytes**. These are 96-square operational
costs, not full-stack performance. Bound sources and generated data stayed
unchanged. Originals were not decoded or modified in this experiment.

Score SHA256: `6987e009c12072a16efbeaa61242131a0b3872d4ed54e231286f54bef97e88a6`.
Independent review SHA256 at acceptance:
`e1a395213feaf10f3e0cb26daf9ec1b64ce13cc5ad76813badb1d3e384315bf5`.

The next program decision must target an identified defect in a real complete
stack. Numerical correctness and generated headroom alone have repeatedly
failed to predict a photographic improvement. SOTA remains unestablished.
