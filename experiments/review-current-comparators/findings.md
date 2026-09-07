# Current comparator scope refresh

2026-09-07, root. **VERIFIED paper content; ARGUED scheduling implications.**
Read-only research alongside M194e implementation. No external repository source,
model, dataset, executable or capture was read or downloaded. No external method
was run. This is a bounded refresh, not a comprehensive literature survey or a
new comparator admission.

## What changes the queue

The deterministic StackMFF V4 stage remains a useful later development comparator,
already identified in [M194d's literature check](../m194d-band-admission/literature-scope.md)
and [B's survey](../../docs/research/B-algorithms-sota.md). Do not treat it as a
new discovery. A source/weights licence check must precede implementation access;
an actual bounded run must establish supported input/output semantics and resource
requirements. The current literature check supplies none of that execution evidence.

The current paper refresh adds a specifically scoped reference: **ReDiffuse,
arXiv2603.21129v1, submitted 2026-03-22.** Its rotation-equivariant diffusion
architecture is evaluated on four image-pair datasets. For those evaluation
benchmarks, section4.1 explicitly says there is no ground truth and computes
MS-SSIM by averaging each source-to-fused comparison. Its other reported measures include gradient, edge and information
indices. The paper's gains therefore do not establish reconstruction error against
independent scene truth, native RAW noise behavior or long-stack scaling.
[Primary paper, sections3 and4](https://arxiv.org/html/2603.21129v1).

**ARGUED:** this does not refute ReDiffuse. It identifies a different tested
population and measurement question. A rotation property is useful to challenge
our own axis-sensitive processing, but it cannot replace truth and noise checks.
For CFA inputs, a geometric rotation also transforms the sampling lattice and
channel phase; blindly rotating a mosaic while keeping an RGGB declaration would
test a different color image. Any future rotation control must specify that map.

The GMFF paper distinguishes deterministic fusion from optional generative
restoration and recommends the former alone for scientific imaging. Deterministic
StackMFF V4 uses reference-based SSIM/PSNR; restoration uses BRISQUE/PIQE despite
available ground truth. Its registration sensitivity and synthesized training
stacks also matter to transfer. These are paper statements, not measured results
on strehl's population. [Primary paper, sectionsI, IV-A andV](https://arxiv.org/html/2512.21495v1).
M194d's earlier note records the fuller scope; no repeated novelty claim here.

## Consequence for this program

Continue the actual-output development route: commission the joint-pupil model,
then a separate production bridge and a fixed depth-boundary/noise comparison.
No paper found in this bounded refresh substitutes for those missing inputs.
Do not train or replace the stacker's architecture simply because a paper reports
better fusion indices. Equally, do not dismiss learned stack fusion by carrying
forward a blanket assertion that all learned methods only accept image pairs.

A later StackMFF V4 development arm must use independently interpreted delivered
pixels on the same declared scene/grid, disclose any RGB conversion and tiling,
and pair reconstruction error with flat-noise and wrong-output controls. Runtime
must be measured on the actual supported dimensions and stack length; a paper's
small-image GPU timing is not this product's CPU timing. This proposal does not
substitute any named arm in the scorecard: [M169](../../docs/research/M169-comparator-requirement-audit.md)
already distinguishes a useful foreign development arm from formal admission.

## Search and reading record

Local commands run before writing:

```text
python experiments/ORCH-drift-check/prior_art.py learned fusion comparator
rg -n 'StackMFF|ReDiffuse|Araujo|2311.17846|2512.21495|2603.21129' docs/proposals docs/research experiments/m194d-band-admission -g '*.md'
```

Prior-art results included M169, M146, M157 and M175. The targeted search found
B's existing GMFF/Araujo coverage and M194d's refresh; M169's verdict and comparator
contract were read before making the limited scheduling recommendation above.

Web searches run:

- `multi focus image fusion RAW focal stack 2025 2026 arxiv benchmark diffusion focus stacking`
- `site.arxiv.org focus stacking occlusion raw image 2025 2026`

Read the primary ReDiffuse abstract/full HTML (especially sections3 and4.1) and
GMFF HTML (especially sectionsI, IV-A andV). A journal-page request for
*One-shot multi-focus image stack fusion via focal depth regression* failed;
no full-text finding from that failed read is asserted. Search snippets and
secondary pages did not supply technical evidence. No benchmark number from an
external paper is promoted to a local performance or quality result.

An independent reader re-chose the primary-paper sections and checked this note.
Their two wording corrections distinguish ReDiffuse's evaluation benchmarks from
its training/validation data and make GMFF's reference-based stage explicit.
