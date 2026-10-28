# Native local spectral fusion: source-only decision

2026-10-27. Root allocates a short concrete design audit after the failed global
inverse and incomplete blur-phase graph. No numerical job, implementation,
RAW decoding or build is authorized by this allocation.

Question: can a windowed Fourier, noise-gated source aggregation on correctly
located original CFA samples offer an implementable native reconstruction,
without the low-frequency imbalance of the rejected global inverse or the
full-value mixture defect? Study Delbracio/Sapiro Fourier Burst Accumulation
from the primary CVPR2015 paper, not third-party code. Root searched research.py
and prior_art.py for 'Fourier burst accumulation' and retained experiment
Markdown for Fourier fusion/Delbracio; no direct implementation was located.
That is search evidence, not proof of absence.

The published method concerns registered motion-blurred RGB bursts; do not
attribute native CFA, focus-bracket, noise or occlusion guarantees to it. The
specific adaptation must say how original sensels at their continuous physical
locations yield phase-correct native coefficients; same-phase interpolation is
an operator with its own response, not free registration. Sensor integration,
aliasing/repeated versus diverse phases, color, windows, defocus OTF sign,
spatially varying depth, clipping and covariance must have explicit semantics.
Storage remains u16 CFA, reconstruction f32, streamed gather/no aligned volume,
demosaic once. No strict variance ceiling that forces genuine detail to zero.

Mandatory predecessors: direct-cfa-level-balanced/results.md,
joint-cfa-local-fit/identifiability/{next-estimator,operator-proposal}.md,
continuous-cfa-kernel/method-audit.md, native-pixel-fusion/photographic-review.md,
dual-tree-cfa-gpu photographic rejection, positive native-cfa-kernel and joint
Lanczos failures, and current phase correlation source/control results.

Cfa-residual owns design.md: a concrete fixed minimal operator plus cost and
critical falsifiers, or a precise reason this candidate is not ready. Root owns
prior-art/selection; integration-review later owns challenge.md. Read source
and papers only. Avoid a long survey, mode census or another unbounded inverse.
Flats must precede sharpness; independent color and simultaneous near-fine/
far-coarse must challenge weights. A future release must lead promptly from
bounded controls to complete real photographs, not synthetic-only closure.
