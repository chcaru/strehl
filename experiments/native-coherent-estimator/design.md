# Fixed native coherent-source estimator

An optional diagnostic image mode, not a replacement/default or quality claim.
Use the current BandWorker's black-subtracted f32 planes [R,G1,G2,B] and its
actual green luma. Original source storage stays u16. No old mosaiced warp,
u16 rounding of gathered samples, old output writer, or aligned-frame volume.

The election is the explicit legacy recipe: FocusField::compute_at_radius at13
(27x27 Tenengrad magnitude normalized by the injected NoiseModel's green-luma
sigma), then merge::regularise at8 (17x17). FocusStats elects on that regularized
field, deterministic lower-index ties. Pass2 admits the elected source or any
source accepted by Gate::new(4.0), retaining the existing FOCUS_NOISE_SD=.015214.
Every admitted source contributes its entire four-plane tuple with weight1.
Divide each channel's f32 sum by the same u16 count. First contribution copies
the sample, preserving one-source signed-zero identity; later contributions
add in original source order. There is no per-band selection, terminal mean,
extra input hull, veil correction, censoring, or new regularizer/threshold.

The inherited field divisor is an unwarped-noise proxy. Its focus-response
constant is **not calibrated for the rounded MHC/CA gather**. Existing worker
variance and Laplacian beta are unchanged baseline inputs and replay evidence;
they do not become a Tenengrad correction. No private noise estimate is fitted.
Actual-path flat averaging and truth controls must qualify any useful scope.
BUILD-ELECT's wrong-depth bright collars and low-frequency seams remain direct
counterexamples; source coherence is not evidence of correct ownership.

Pass1 builds current baseline and FocusStats; pass2 recomputes and hash-checks
source/known4/luma/variance/beta/regularized focus before accumulation. Kept
state is O(pixels): stats, four sums/counts and one current observation/workspace,
plus small O(frames) hash receipts. MeanAll uses the identical accumulator with
every source admitted. Forced-source is a commissioning-only supplied donor;
it is never an automatic election. No environment override changes the recipe.

Generated adapter: <=70 sources, <=512 native pixels each dimension, supplied
similarities/no CA, actual rounded GPU and injected probe, same camera RGB
developer. Independent fixtures/acceptance belong to the reviewer; broad
contact structure, flat first, narrow coloured detail, depth boundaries and
wrong-source damage must be exercised. No test result is claimed here.

Separately callable chip adapter uses all299 originals, held map ce8534c9...,
normal optical CA (CA-before-MHC off), crop[141,97,3234,2150], fixed tone
[.004293,.946441,.55], WB/matrix and actual source-index299 probe gauge.
Current pyramid baseline retains canonical75/75/75/74 chunks and must match
RGB16-LE7df99f8f54339711c189380cca45cd63fd8106a2a196162bf562ecc60fbfd7db.
Coherent sums are sequential original-index sums, with no inherited candidate
chunk contract. Both outputs use existing four-plane full-context MHC and
development. Complete6468x4300 masters/whole views are mandatory.

Cost source149 uses original index/count299 and one admitted source. Require
candidate planes bit-identical to the actual gathered source and counts1;
compare its delivered pixels against the same writer on that gathered source.
Do **not** require identity to the one-source pyramid collapse, which may differ
by f32 reconstruction rounding. Resource admission and photographic admission
are separate root decisions. Root owns builds/runs/CLI hooks; author runs none.
