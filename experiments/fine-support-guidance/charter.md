# Fine-scale support around defocused highlights

September 19: bounded diagnostic before another merge intervention. This is
not an accepted image-quality algorithm and changes no product default.

The complete vitamin-C native render retains long chromatic fans. Independent
source localization now finds compact glints near frames 28/33 and similar
long fans already in defocused frames 52/69. The twelve-colour/site-plane
intervention leaves the defect visible in a complete 70-frame replay. The
immediate question is therefore focus selection around the glint, not another
demosaicer, colour-neutralization rule, or clipping threshold.

First trace the existing actual per-band dominant-weight diagnostics through
the final MHC and pyramid expansion support. Root's held-native6 replay under
STREHL_PYRAMID_WEIGHT_DUMP already reproduces the complete original TIFF hash
exactly. The diagnostic reports weight preference and concentration, not signed
coefficient radiance or one winning frame per output pixel. InputRange clipping
can further limit the final reconstruction. Do not overclaim causal attribution.

The next fixed measurement asks whether the actual finest-scale green energy,
pooled over a neighbourhood containing both the glint and its fan, prefers the
compact focused observation at both locations. Use one extra box radius of
32 quad pixels (64 native pixels), chosen to cover the observed roughly
45–57-native-pixel centre-to-fan separations. It is not a measured optimum and
there will be no radius sweep to rescue a failure. Pool the existing fine
energy and its injected floor alike. No private noise estimator or new fitted
camera constant is allowed. Report all 70 observations, not merely the best.

Six locations are frozen in the cropped 6920x4612 output-native gauge:

| Role | x | y |
| --- | ---: | ---: |
| facet glint centre | 2624 | 2906 |
| facet fan | 2602 | 2945 |
| facet structural rim | 2760 | 2998 |
| inclusion glint centre | 3080 | 2150 |
| inclusion fan | 3102 | 2203 |
| nearby crystal structure | 3240 | 2070 |

Original active coordinates add (56,38); the merge's compact domain does not.
Phase-dependent MHC support matters. No nearest-coefficient index may be
reported as the frame choice for a complete native RGB pixel.

The candidate can fail in two obvious ways: the pool does not reach the real
compact source and still favours the fan, or it spans two depths and chooses
the neighbouring feature's focus instead. A future quality test must contain
that second case, true coloured detail, flat noise and an actual spatial depth
boundary. A single-plane plant cannot establish safety. Fine energy can rise
on noise and glints; it is a locator here, never a quality score.

Prior-art mechanical searches were run for `pyramid cross-scale consistency
depth coherence`, `pyramid sharpen overshoot`, and `specular highlight defocus
neighborhood focus`. Relevant records: BUILD-BLEND (coarse band energy can
prefer defocused features), BUILD-ELECT (high-pass election alone did not fix
the old manufactured seam; pyramid merging did), V-DILUTE (dilution refuted),
V-SELECT and V-SOFTCHECK-coherence (half-stack disagreement is not this quality
test), M13-window-depth (depth steps are load-bearing), M28/M89 (focus changes
are not generic burst outliers), BUILD-CHROMA (measured axial CA did not explain
its prior rainbow defect), M54 and M97c (pinning requires actual per-frame
evidence). None justifies attributing this photograph's fans to RAW saturation.

Author: full_context_placement, exact gathered fine-energy diagnostic only.
Independent review: placement_controls, support/choice interpretation and
failure cases. Root builds/runs and inspects photographs. Reuse current u16
RAW decode, source MHC/Catmull/CA, shared green guide/noise and existing kernels.
Gather supported patches on consumption; never retain an aligned frame volume.
Use the pinned existing alignment map under the workspace. Originals remain
read-only. Root records commands, source/executable hashes and process bounds.
No complete new candidate render until this cheap measurement supports it.

Implementation scope, amended before the run: root chose the existing full-domain
BandWorker consumer because its current GPU coordinate arithmetic and measured
probe already match the photographic baseline. Decode each original once, fold
it normally, then extract only the current luma/variance windows. Preserve even
quad origins and48-quad padding so the finest Laplacian reduction phase and
complete radius32 support match the full domain. The actual per-frame beta[0]
comes from that worker; no saved or newly fitted floor is substituted. Reuse
the existing native-correction-variance bridge to production Laplacian/smooth5
and the existing box filter. No aligned frame collection is retained. Report
the containing fine-grid cell and its3x3 neighbourhood for each native point;
these are guide coefficients, never one frame choice for a developed RGB pixel.
