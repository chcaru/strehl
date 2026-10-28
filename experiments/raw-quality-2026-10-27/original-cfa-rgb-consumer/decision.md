# Composed MHC rows do not resolve the native reconstruction contract

2026-10-27. VERIFIED source review; no numerical or photographic result.

The [operator audit](operator-audit.md) and independent
[contract review](independent-contract-review.md) agree. Composing the existing
source MHC and geometric interpolation into rows evaluated against original
sensels is algebraically the already investigated once-RGB reconstruction.
It is not a new joint original-CFA estimator. Keeping signed f32 RGB through
band fusion could remove real remosaic, rounding and second-demosaic losses,
but still reconstructs each source before fusion. Existing once-RGB controls
also contain flat and neutral-detail regressions. That distinction matters
under the user's native-RAW-through-reconstruction requirement.

Close this source-only allocation as a proposed native-contract solution.
Do not launch a large once-RGB implementation on the basis of a renamed
composed kernel. Retain it as an explicitly non-native boundary diagnostic,
conditional on a later concrete photographic reason and separate release.
This decision does not reject joint CFA reconstruction generally, and no
photographic improvement or SOTA claim follows from the audit.

The separate complete StackMFF V3 weevil comparator remains in progress.
Its developed-RGB output can provide photographic evidence about fusion
behavior; it cannot establish native RAW compliance either. Choose any next
native implementation from that complete observation and the retained failure
evidence, without treating one external model or one kernel recipe as a whole
family verdict.

Root actually ran the unified and mechanical prior-art searches recorded in
[the brief](brief.md), read BUILD-DEMOSAIC and M95-demosaic, and reviewed both
reports. Their SHA-256 identities are
`018a16b62fb269f42c17d6af6474a97d7da3a630a12ea387fed4a316078b380e`
and `efd05c4ddab3731b0757a434cf6e5cb264e8b9ed4ebc39c7d930f8cf25fc0d6b`.
No code, runtime settings, capture files or frozen comparator inputs changed.
