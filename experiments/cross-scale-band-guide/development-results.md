# First development fit: learning is live, curved color still fails

MEASURED September 26. The richer source scorer learns useful weights on the
19 known development cases. This is not independent validation or an improvement
to a user's photograph. The original seven held cases are included in this fit.
No production setting has changed and no photographic render is admitted.

Root ran the following with installed Python 3.12, `-I -B -X faulthandler`,
through this directory's bounded run.py. Each directory preserves invocation,
input hashes, process log/accounting and completion receipt.

| Phase / output directory | Process seconds | Result |
| --- | ---: | --- |
| texture-train / textures-train-1 | 1.047 | 12 retained-source textures, unchanged originals |
| texture-held / textures-held-1 | 0.485 | 4 separate-subject textures, unchanged original |
| commission / commission-1 | 6.906 | all 19 complete uniform/prescribed CFA and RGB arrays exact |
| check-commission / commission-check-1 | 3.812 | independent gradient, loss-support and scorer controls pass |
| train / train-1 | 108.937 | 2048 updates; selected checkpoint 1536 |
| infer / infer-1 | 3.859 | frozen model, no truth read |
| check / check-1 | 3.953 | exact model/weights/CFA/RGB replay; quality failures retained |

These are single execution readings, not competitive production timings. The
texture staging jobs overlapped commissioning. No original RAW file was read.

Optimizer/evaluation/checkpoint time was 105.6315 seconds. The minimum declared
development objective is 0.0597806 of its initial uniform value. Both head and
body gradients were live. This objective was used to select the checkpoint;
its reduction is not independent evidence of quality or convergence. Independent
central finite differences on the full declared objective differed by 0.0713%,
with descent and wrong-direction ascent both exercised before training.

| Known development window | RGB RMSE / current | Prospective protection |
| --- | ---: | --- |
| Flat N5 interior | .87949 | pass |
| Flat N9 interior | .72115 | pass |
| Curved bright boundary | .72091 | FAIL: chroma 1.13113x current |
| Near-fine/far-coarse positive | .85095 | pass |
| Genuine unclipped glint core | .87276 | pass |
| Weak-color component window | .87105 | pass |

Curved whole-interior chroma also fails at 1.09541x current. Those are the only
prospective failing windows. No eligible component fails its retention guard;
this does not mean every component improved. Historical two-reference guards
also remain false. Clipped-core recovery is outside the score and excluded
from that case's training objective; its adjacent/spread windows remain tested.

New model source SHA256:
`03ddcab38c492557244638d93694b66473a749aaac6f7785fb129be98dfce96f`.
See independent-development-review.md for the separate scientific judgment.

Decision: preserve this complete fit. Do not repeat it on these 19 cases alone.
Proceed with 24 additional generated training cases, then a separately frozen
10-case challenge, retaining independent source/depth/color checks. Revision 2
will warm-start the selected model and increase both global and ROI chroma
coefficients from 0.5 to 2.0; architecture and other loss/optimizer choices stay
fixed. This prospectively targets the measured curved-color failure, with no
claim that it will succeed. The held challenge must not select that fit.

Native export preparation: build-1 reached a fresh `Compiling strehl-cli` and
failed on one missing closure type annotation. Root added `family:Family` only;
build-2 is the separate retry and completed with a fresh compile in 185.625s.
Buffered f32 writers avoid per-value OS calls; byte order and hash convention
are unchanged. All24 training cases exported in21.515s, all10 separate challenge
cases in20.407s. These are generated inputs, not new photographic outputs.

The streamed generic consumer passed independent nonzero-score/tile-boundary
controls in generic-controls-1. Native uniform and prescribed-weight replay
subsequently passed across all24 training and all10 challenge cases in
generic-train-1 and generic-held-1, including odd seven-band support. The
independent stage1 execution audit found no checkpoint, coverage, hash or replay
mismatch; see independent-execution-review.md.

MEASURED cost commissioning (`run.py expanded-cost --dataset
export-train-1/output/dataset.json --annotations training-annotations.json
--weights train-1/output/model.json --out expanded-cost-1`, paths relative to
this experiment): all43 forward/backward cases took5.961s, full evaluation
2.999s, preparation4.544s, peak CUDA allocation1,902,835,712bytes. Model
parameters were byte-identical before/after and head/body gradients were live.
The single-pass projection is95 complete updates within600s, not a benchmark.
Root therefore selects the unchanged full43 equal-case update schedule for
revision2; no minibatch substitution is needed. Independent loss qualification
must pass before fitting.

`run.py transfer-qualify --dataset export-held-1/output/dataset.json --out
transfer-qualify-1` completed before any candidate challenge inference. All11
required preservation protections and both nominated positives are qualified,
with the frozen destroyers exercised. This establishes that the screen can
reject damage; it says nothing about whether the model passes it.
