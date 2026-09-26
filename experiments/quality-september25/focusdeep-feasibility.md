# FocusDeep: bounded readiness check

2026-09-25. Read-only triage while the independently reviewed harmonic
band-source-agreement experiment builds. This is not a new discovery or a
quality measurement.

**Decision: no ready scoped implementation/comparator route.** Do not launch a
training, dependency-installation or source-adaptation campaign from this check.

## Existing record and command

Ran the mechanical prior-art search before browsing:

```text
python -I -B experiments/ORCH-drift-check/prior_art.py FocusDeep learned RAW Araujo Ponce Mairal
```

Read `docs/research/B-algorithms-sota.md` section 3, which already discusses this
paper, its Helicon pseudo-ground truth and its domain limitations. Also read the
M65 conclusion: changed source labels alone do not establish a useful change to
the merge's accepted measurements. No existing closure is being reopened.

## Verified published method

The model accepts packed four-channel RGGB and outputs reconstructed RGB. The
dataset has 94 thirty-frame bursts; training uses 128×128 crops and Helicon
pseudo-ground truth. FocusDeep has fixed burst length and depends on input
order. It requires prealignment; its local feature alignment does not handle
large magnification errors. The authors mention sliding-window inference, but
do not specify a ready hundreds-of-frames integration here. They explicitly
acknowledge inherited pseudo-ground-truth errors. Training reportedly takes
about three days on sixteen V100 GPUs. That is not an inference timing or
memory benchmark. The inspected paper gives no inference peak-memory figure.
[Primary paper, sections 3.2–3.3, 5 and Appendix A](https://arxiv.org/html/2311.17846v1).

## Release readiness, checked 2026-09-25

| Requirement | Inspection result |
| --- | --- |
| Exact code licence | **UNVERIFIED.** No licence file or licence grant was visible in the author repository's root listing/README. No implementation source was opened. |
| Exact weights licence | **UNVERIFIED.** No verified weights release or grant was found on the inspected author surface. |
| Pretrained RAW checkpoint | **UNVERIFIED.** The README links the paper and dataset, but supplies no checkpoint link. This is not proof that no checkpoint exists elsewhere. |
| Inference API and dependencies | **UNVERIFIED.** No documented invocation or installation instructions appear in the inspected README. Filenames alone do not establish a usable API. |
| Runtime/peak memory on this machine | **UNVERIFIED.** No execution was attempted. |

Evidence: [author repository and README](https://github.com/araujoalexandre/FocusStackingDataset).
Direct web attempts to open `LICENSE`, `LICENSE.md` and releases failed; those
errors are not evidence of absence. The repository issue index also lists open
requests for training/inference code and custom-dataset testing; their contents
could not be retrieved, so they are not used to infer what is implemented.
[Issue index](https://github.com/araujoalexandre/FocusStackingDataset/issues).

## Consequence for Strehl

**ARGUED:** It is not presently a reproducible ready comparator for the complete
chip or marigold stacks. Missing licence/checkpoint/API evidence is sufficient
to stop before code inspection or integration, regardless of potential model
quality.

**ARGUED:** The published reconstruction architecture does not establish a
nonnegative source-weight API or a guarantee that output radiance is drawn
only from measured sources. Extracting such weights would be a new method,
not a conservative adapter. This check does not claim that the model actually
hallucinates in any particular photograph.

Reconsider only with an explicitly licensed RAW checkpoint and documented
inference contract. No downloads, source reads, dependencies, training, model
execution, RAW reads, renders or production changes were performed.
