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

## Revision2 and independent challenge: preservation failure

MEASURED via `run.py develop-qualify` to develop-qualify-1, then
`expanded-train` to expanded-train-1 with the explicitly chosen full43 schedule,
the cost receipt, independent qualification, training annotations and stage1
model. The independent objective derivative differs by0.39494%; all43 masks,
valid gradient stencils, flat KL and clipping controls pass. Training completed
102 updates in584.057s (584.719s process). It selected step102 from checkpoints
0/32/64/96/102. Its objective moved4.7663021e-5 to3.7399788e-5. Cumulative
fit time is689.688s of the1200s program allowance; at most one revision remains.

The selected model SHA is
`882532f9d735e1955d75f28679715b4ba4b0dc4829e2d8dba7ed36bb4767a705`.
`expanded-infer` to transfer-infer-1 took7.407s; `transfer-check` to
transfer-check-1 took10.578s. The check binds transfer-qualify-2 and
generic-held-1. The second qualification repeats the same frozen science after
adding exact selected-model-to-weights and whole-CFA/RGB replay; all10 model
replays and separate saved-weight reconstructions pass. It is not a new or
easier quality screen. No challenge result selected the model checkpoint.

Both nominated RGB positives pass (fork.90479 and thin.76065 times current),
all flats pass, weak-color near RGB is.65054 and genuine glint core.71693.
These generated error reductions do not establish photographic quality.
The full prospective conjunction FAILS: genuine-glint adjacent RGB1.08133,
clipped-glint adjacent1.08358, and material component-retention failures.
Fine4px carrier amplitudes fall roughly25%; glint-adjacent R/G/B fall22–28%.
Some16/32px carriers also fail preservation; the8px blue-only threshold miss
is borderline but cannot explain the other failures. Lower RGB error rewards
some smoothing here, exactly why preservation is checked separately.

The old19 regression also ran (`infer` to developer-infer-2, `check` to
developer-check-2). Curved positive chroma remains1.13932 times current,
slightly worse than stage1's1.13113. Six other old cases pass prospective
guards; the curved failure is not resolved by the larger chroma coefficient.
See independent-transfer-review.md for every failed component and the
independent decision: diagnose preservation on existing training cases before
spending a complete70-source photographic run. No production default changes.

A reusable native/Torch bridge is prepared separately for the complete vitamin-C
70 stack. It is not a marigold stack. Its smaller workload makes it a reasonable
first future observation, but would not qualify minerals or the complete488
marigold. No RAW cost/full job has run for this model and no photographic
improvement is claimed.

## Final bounded revision and complete-photograph decision

The intervening user-requested goal-wording turn made no implementation
progress. On resume, the original live handles were polled: preserve-train-1
finished successfully and build-3 failed on one nonexistent module import.
No job was restarted from a timeout or an empty log.

MEASURED: preserve-qualify-1 independently exercises masked contrast moments,
flat controls, gain/noise blind directions and the complete objective derivative
(1.07396% relative difference). The final fit selected step82 in481.276s;
all three fits together cost1170.964s, below the1200s allowance. There is no
fourth fit in this recipe. Model SHA is
`02f5d9fbfa16efa18207b82884a83f232cd8ab2355995dba04c11a91dd1fa02a`.
The chosen objective is3.795479668e-5, including9.087879060e-7 contrast penalty.
Training loss is not photographic evidence or a convergence claim.

Root ran preserve-infer/transfer-check to reused-regression-infer-1 and
reused-regression-check-1, and infer/check to developer-infer-3 and
developer-check-3. Exact model/weights/complete CFA/RGB replay passes. The
scientific conjunction still FAILS. Finest red/blue carrier retention is88.73%;
unclipped-glint-adjacent green retention83.37%; curved positive chroma1.13969
times current. The ten-case challenge has informed this revision and is now
reused regression evidence, despite historical FRESH field names in its
unchanged checker. Independent-preserve-review.md records the complete
decision: one complete70 vitamin-C diagnostic observation is informative after
bridge/cost checks, while this recipe remains rejected for release. No default
or threshold changes, and no claim that the remaining losses are negligible.

MEASURED: build-4 freshly compiled in195.657s after correcting only the bridge
module import. Full-run controls to bridge-controls-1 passed in24.079s. Actual
nonzero model weights and reconstructed CFA/RGB match the commissioned generic
consumer exactly on the retained3/7AC fixtures. Canonical observer-off, stats,
and score routes are bit-identical; compact zero-head uniform and terminal
wrong-order refusal pass. Phase/source comparisons exercise unequal inputs;
they are not separate injected phase-mutant runs. Odd7 support is earlier generic evidence, not a new odd IPC
case. These checks do not establish photographic quality. Exact commands,
source hashes, limits and terminal process accounting are retained per run.

## Complete70 photographic execution

MEASURED: full-cost-1 refused after60.688s because its historical baseline
predated production commit3fe71e35's weighted-numerator correction. The new
fixed-tone RGB16 differs at exactly four channel samples, each+1; independently
checked over all95,745,120 samples. Rounded RGB8 and ICC are identical. Preserve
that refusal and baseline-reference-review.md: the corrected same-build TIFF
and native CFA cache became new exact references, with no epsilon relaxation.
The source version change is known; attribution of each changed sample is not.

MEASURED: full-cost-2 passed in63.468s with all70 context frames and one scored
source. Root then ran full-run.py full to full-1. All70 original RAW files were
consumed in each pass and the complete6920x4612 RGB16 pair was delivered in
157.750s process time (445.063s summed CPU). Peak owned-job committed memory
was13,894,406,144 bytes; Torch peak allocation3,883,719,680 bytes and reserved
4,414,504,960 bytes. This instrumented run uses retained alignment and is not
a competitive full-workflow timing benchmark. Both instrumented canonical
passes match exactly in native CFA and complete TIFF; terminal Mean and input
bounds are unchanged. Current baseline CFA repeats the new anchor exactly.

Candidate master SHA256:
`331eb89a86e8bcf77c0f81f64cbacec07e2ef7871ae15365541292bfbc7aa879`;
decoded RGB16 SHA256:
`881ceb812b444a0ff2d3febb0578a5f8f4eaed80ba39b8914f137be2bb756e87`.
photo-compare.py created views-1 from saved masters only: whole PNG/JPEG views,
five384px and three120/160px native comparison regions, matched ICC/development,
and retained Helicon B coordinates without new registration or resampling.

Root inspection rejects this final recipe: a dark inclusion is filled by a
bright white patch, and nearby structure is softened. A smoother background is
not a photographic quality win. Independent photographic review is recorded
separately; no default change, fourth fit or claim that glare/ghosting/occlusion
halos are solved follows. The reusable bridge remains available, but this
specific three-fit learned-weight recipe stops. A distinct common edge-aware
analysis/synthesis hypothesis is the next bounded implementation, with the
existing source decisions held and wrong-guide controls required.
