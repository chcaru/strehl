# Final native CFA color completion: source audit

2026-10-27. Source-only work while the unchanged native spectral full299 job
runs. No numerical, RAW, GPU, image-generation or build jobs; no changes to
existing Rust/Cargo or any native-spectral-fusion/pilot bound file. Root alone
can release implementation or measurements in a later written scope.

## Changed evidence and question

The fixed spectral controls5 and saved-array stage audit1 retain substantial
channel-specific signal in the final CFA, then lose amplitude or add cross-color
components when completing missing RGB samples. For example the independent
color scene's physical CFA recovers about0.959/0.914/0.978 of R/G/B components,
while its actual dense camera output recovers about0.650/0.766/0.650. Known
camera sites agree with CFA to about1e-4DN. These are generated observations,
not proof of the weevil's defect or a defect unique to MHC; the shared-bin and
flat penalties already exist before completion. The current full native weevil
photograph is pending and cannot be inferred from these scores.

Question: is there a concrete, generally applicable final RAW-color completion
method that preserves identifiable chromatic detail and neutral detail without
buying them with noise, aliasing or ringing? Prefer a bounded alteration of the
one final CFA-to-RGB stage. A genuinely native joint reconstruction alternative
may be described if single-CFA identifiability prevents it, but must explicitly
respect originalu16 storage, f32 arithmetic, consumer gathers, no aligned-frame
volume and no per-source demosaic/remosaic disguised as RAW reconstruction.

## Prior work to retain

Root ran `python -B scripts/research.py search demosaic --limit 10` and
`python -B experiments/ORCH-drift-check/prior_art.py demosaic`; mechanical output
is retained under outputs/raw-quality-2026-10-27/final-cfa-color-source-lookup/.
Read relevant full reports/amendments, not search snippets:

- M95-demosaic: a loudness ranking is not fidelity; even linear MHC can create
  aliases. Its pseudo-truth also carries decoder assumptions.
- M95-cdiff and BUILD-SHARP: earlier directional/color-difference variants failed
  their actual-capture/noise bars. Do not rebrand them as a new free win.
- M104b-demosaic-lever: preregistration and controls, with its historical optical
  cutoff and broad linear-interpolator statements scoped to their evidence.
  Do not transplant the old optical ceiling to the current teleconverter/code86
  capture. Current core comments already correct the linearity guarantee.
- BUILD-DEMOSAIC and V-GATHER: double demosaic can hide color error by correlating
  channels; R-B high-pass power alone can reward the wrong direction.
- The complete phase-packed vitamin/chip and weevil-fusion-order nulls: removing
  the final MHC after per-source MHC is not a demonstrated photographic solution.
- Current native spectral design/challenge, controls5, source149 and stage-audit1:
  distinguish physical source information, fused CFA and inferred final sites.

Never read forbidden GPL/LGPL implementation sources. Published primary papers
and permitted MIT/Apache sources are available, but no implementation is needed
for an initial mathematical proposal. Cite exact primary sources for borrowed
algorithms; do not claim novelty merely because the local index lacks a result.

## Owned work and decision

Cfa-residual owns design.md: one concrete proposal, consumer quantities, physical
sampling/alias assumptions, means of preserving known CFA sites, boundaries,
noise dependence, controls and estimated work/memory. No broad survey or sweep.
Photo-review owns prior-photo-constraints.md: the relevant earlier photographic
negatives and a concise actual-photograph acceptance plan with full masters and
the already fixed witnesses. Integration-review owns challenge.md after reading
the proposal: re-choose assumptions/references/nulls and identify an adversarial
neutral/color/depth case. Root chooses whether to implement, without treating
one rejected recipe as a prohibition on every adaptive or joint method.

Any later test starts with flats, constant/affine color, neutral fine diagonal
detail, independent colored modes inside their actual physical Nyquist regions,
out-of-band aliases, weak chroma beside bright structure and crossing/depth
edges. Noise amplification, invented component power and erased real structure
must be reported separately. A score cannot finish this lane. Any claimed gain
requires complete weevil outputs with full-resolution masters, independent
review and transfer to flat/second-insect controls before a general claim.

Stop this source audit with a short implementable design and challenge, or a
specific reason that a different architecture is needed. Do not extend it into
an unbounded investigation or change the running spectral recipe.
