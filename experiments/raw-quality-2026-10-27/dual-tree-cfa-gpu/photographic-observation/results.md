# Complete weevil observation: reject the fixed candidate

2026-10-27. **VERIFIED photographic verdict: no substantial improvement.** Root
reviewed all three complete compositions, all thirty fixed native384px views,
the complete Helicon B8/B4/C comparisons and all ten B4 native witnesses.
Independent photographic review reaches the same rejection without receiving
root's verdict. The candidate adds broad teal/green veiling around the legs,
body boundaries and dark gaps. Rounded scales, soft fine structures, harsh
glints and occlusion contours remain. Local contrast changes do not establish
newly resolved structure. Do not promote, tune or optimize this fixed recipe.

## Commands and measured completion

Root ran from the worktree, with four CPU workers and the fixed RTX5090 worker:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/dual-tree-cfa-gpu/photographic-observation/run.py
python -B -X faulthandler experiments/raw-quality-2026-10-27/dual-tree-cfa-gpu/run-views.py --input outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-photograph-1/output --out outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-photograph-views-1
```

Both exited0. MEASURED research job:3554.016s (59.23minutes), peak host job
commitment15,233,900,544bytes. Torch peak allocated/reserved memory:
7,520,020,480/9,527,361,536bytes. Presentation:8.687s,991,690,752bytes peak job
commitment. Both the original1200s speed limit and14GiB host limit are exceeded;
the separately allocated4800s/16GiB observation bounds pass. The inherited
adapter receipt's14GiB label is stale; the actual parent job limits are
authoritative and independently checked. This job
includes canonical, candidate, uniform reference,16probes/source and multiple
masters; it is not an isolated candidate speed benchmark or a from-scratch
alignment workflow. Whole-host load is retained in the invocation directory.

VERIFIED: all299 sources and4784 probe draws completed; originals were reread
and preserved. The held CFA payload, RGB pixels, linear pixels and material
metadata reproduce exactly. RGB16 container bytes differ only through the
Software tag and resulting strip offsets; do not call that file byte-identical.
The actual pre-hull uniform null passes on all four phases (worst max0.001953125DN,
worst RMS0.000146002DN; fixed limits0.05/0.01). These are mechanical checks,
not photographic acceptance. Source phase3532.1405999s and finish10.708934s are
recorded separately.

The exact executable/runtime/source/worker/output identities and flags are in
[full invocation](../../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-photograph-1/invocation.json),
[completion](../../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-photograph-1/completion.json),
[complete receipt](../../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-photograph-1/output/receipt.json)
and [display receipt](../../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-photograph-views-1/display-receipt.json).
Independent audits: [photographic review](photographic-review.md) and
[full-results review](full-results-review.md).

## Whole outputs and full-resolution masters

All native outputs are6896x4596 with the same held tone and ICC. Overviews are
orientation only; native views provide detail judgments. No individual arm was
retuned for presentation. [Complete image/master index](../../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-photograph-views-1/index.md)
retains baseline, candidate and uniform RGB16, RGB32 and fused-CFA outputs.

| Arm | Complete-resolution image | Full-resolution master |
| --- | --- | --- |
| Previous pixels reproduced | [JPEG](../../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-photograph-views-1/baseline/complete-stack.jpg) | [RGB16 TIFF](../../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-photograph-1/output/baseline-master.tiff) |
| Rejected candidate | [JPEG](../../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-photograph-views-1/candidate/complete-stack.jpg) | [RGB16 TIFF](../../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-photograph-1/output/candidate-master.tiff) |
| Uniform causal reference | [JPEG](../../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-photograph-views-1/uniform/complete-stack.jpg) | [RGB16 TIFF](../../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-photograph-1/output/uniform-master.tiff) |
| Retained Helicon B4 workflow | [JPEG](../../../../outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2/stack-full.jpg) | [RGB16 TIFF](../../../../outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2/stack-master.tiff) |

Candidate RGB16 SHA256:
`6df7ce45b619c62994fde12cdf867c954175e611cb592f8caad460d09261302c`.
Candidate linear RGB32 SHA256:
`ff6d3f73c6dfb31e1f7563dc66616615c8d5a6401fd8e46e2ac2a4876aeb029d`.

## Root native-view observations

All coordinates are native output top-left,384x384. These are visual findings,
not gradient-energy rankings or claims about a unique physical cause.

| Witness | Origin | Candidate against exact previous pixels |
| --- | --- | --- |
| background-black |3800,500|Mostly dark; no useful detail claim. Broad surrounding veiling is better assessed at subject boundaries.|
| dark-elytron |2750,2120|Similar fine texture with changed broad blue/teal wash in the dark grooves; no resolved structure gain.|
| turquoise-scales |2120,1340|Rounded beads and bright glints remain; stronger broad color is not new scale topology.|
| elytron-seam |2950,1960|Soft diagonal seam and bright beads persist; no meaningful new separation.|
| bright-wing-rim |4050,1810|Bright green/white edge and glints remain; broad dark-side veiling increases.|
| thorax-texture |4520,2560|Dense round beads remain round; changed local contrast/glints do not reveal new fine anatomy.|
| upper-leg-hairs |1820,640|Existing strands remain soft; conspicuous additional teal haze surrounds the leg and dark background.|
| blue-joint |2680,850|Blue/green texture and glare remain; no newly distinct structure.|
| upper-occlusion |3850,1300|Teal spill broadens around the occlusion contour and a bright green glint extends; no halo repair.|
| eye-and-antenna |5350,2920|Dark gap becomes more veiled while the same sparse bright fragments remain. Historical label is not anatomical proof.|

Uniform is visibly defocused and is not focused truth. Its similarity to broad
spill does not by itself identify which candidate coefficient/base decision
causes the harm. Helicon B8/B4 preserve cleaner hair-background separation;
C retains harsh bloom. Their source development, CA, alignment and approximately
2% gauge difference prevent a pixelwise or merge-only causal ranking. No new
vendor run or claim of an exhaustively optimized commercial workflow is made.

## Architecture and next work

This is six-direction fusion on the **existing MHC/Catmull-remosaiced CFA
consumer**, not fulfillment of literal original-CFA reconstruction/demosaic-once.
The [contract audit](native-contract-review.md) identifies per-source color
reconstruction and requantization before the final merge/development. The
architecture documentation now states that limitation. Exact mechanics and
bounded CFA storage cannot substitute for the requested reconstruction contract.

Close this exact photographic recipe and its conditional acceleration proposal;
retain the generated color/glint failures and practical-speed failure. No
automatic other-insect/flat transfer, parameter sweep or production default
change follows. This does not reject every dual-tree representation or establish
an optical/capture ceiling.

The separately allocated [original-CFA band-residual prototype](../../joint-cfa-local-fit/band-residual/brief.md)
is source preparation only. Its scalar full-value predecessor was rejected by a
concrete depth-preservation counterexample. The new operator, independent controls
and actual-product bridge still need compilation/execution/review. No quality
improvement or full-photo release is claimed for that work. The overall user
goal, including other insects, marigolds and minerals, remains open.
