# Independent chromatic-evidence controls

Frozen before build/results. Four tests, eight image cases and three placebo
comparisons; no photographic run or new framework. Fixture/generator/scorer
reuse rb-own-guide with two independently chosen analytic additions.

Mechanical tests independently enumerate the twelve co-sited slots. Different
neutral intensities at all four native sites with dyadic WB[2,1,4] must project
to exact zero; wrong-site CFA subtraction does not. Two colour perturbations
give a known nonzero result, unchanged by an added neutral veil. Correlated
common-mode pairs project to zero despite positive marginal colour variation.
Eight direct projected coefficient pairs of+2/-2 in both components must yield
summed noise energy16: this commissions projection-before-square and factor2N.
Natural unsupported sites are exercised alongside live union sites, separately
from explicit Off/NoChroma. Source-local zero remains zero when another source
is admitted, while no source admitted means exact canonical fallback.

Image cases: flat and coloured-texture/neutral-veil at ISO100/400; neutral fine
detail, crossed thin depths, true coloured rays, and neutral clipped highlight
at ISO100. Every case uses the existing injected per-site noise, u16 storage,
runtime fractional similarities, rounded native gather and final MHC/RGB.
All signal/probe first-four identities and repeat hashes must hold. This does
not calibrate the shared injected noise model.

The new veil scene has one common coloured-texture focus at source4, with
amplitudes[0.065,0.025,-0.050] and frequency0.06; the neutral narrow glint has
peak0.65, focuses at source0 and spreads with defocus. The positive is bounded
below source clipping by construction, separately from the clipping falsifier.
Fixed outside/near regions are inherited
from the old glint fixture. A positive requires canonical outside error above
twice flat error, signed positive outside bias above flat error, active changed
weights,5% RGB/chroma error reduction, and preserved nearby texture. If the
canonical mixture removes the spill, record an unexercised positive and refuse
qualification; do not alter the plant or move the region.

Pre-execution amendment from root's independent choice review: the unclipped
Veil scene also protects the genuine focused highlight in the fixed core
window[112,110,133,132] (native bounds). Apply the same5% RGB/green/chroma and98%
template-retention bars there, and require baseline core recovery>=0.5 in all
channels. Selecting coloured source4 must not pass by erasing source0's real
highlight. This adds the missing protection before any build/results; it does
not change the stimulus, threshold or positive region. The clipped scene still
excludes its irrecoverable core.

The new clipped scene is neutral before sampling and WB, with peak2.4. Clamp
actual active u16 codes at Levels.white=15360 before WB. Assert that source
clipping occurred and differs across CFA phases. Score only retained outside
and adjacent regions; no recovery of clipped radiance is claimed. A nonzero
chromatic field on this or the neutral fine-detail scene is potentially false
evidence from clipping/MHC. Record it and require final RGB/green/chroma
non-regression; never count it as recovered real chromatic detail. This does
not establish original-source clipping in the user's mineral captures.

Fixed damage bars are at most5% increase in RGB, green or chroma truth error,
and98% bounded template retention where baseline recovery is at least0.5.
Protected true-detail fixtures must actually recover their templates. Lower
RMSE can reward smoothing; template correlation can reward wrong aligned
structure. Neither alone proves quality. The actual retention gate rejects a
half-detail destroyer. Forced coarse source0 must damage the positive scene's
far texture, and Off/NoChroma must reproduce complete CFA/RGB exactly.

All scientific failures are saved in screen.json. candidate_qualified requires
every quality bar, both positive fixtures exercised, and the live wrong-source
destroyer. photographic_replay_admitted remains false pending root's independent
interpretation. No parameter, phase, clipping, scene or support sweep follows
a failure of this fixed rule.

This five-source flat screen does not qualify the deep-stack ANY-source
admission union: false admissions can grow with source count. If the present
screen passes, a later complete-stack route requires a separately fixed
source-count noise/neutral-structure check before photographic execution.
