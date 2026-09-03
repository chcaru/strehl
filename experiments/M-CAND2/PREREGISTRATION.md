# M-CAND2 full-covariance Hotelling freeze

**Status: FROZEN before any scientific arm.** The scientific freeze is the
path-scoped Git commit containing this exact file and the paths listed by
`src/cand2.py:FROZEN_PATHS`. No comparison transform was evaluated while choosing
the settings below.

## Reused rig and sites

The experiment imports the frozen CAND1 RAW manifest, dual-decode loader, 5-by-96
geometry-only site grid, target/noise seed discipline, eight-thread cap, and
block-then-site bootstrap. It opens only the same five explicit development RAW
files and never scans or writes the capture root.

A site is one guarded macro-tile. The 480 sites occupy disjoint sensor support and
receive independent nuisance and noise streams. The four sealed templates are
common fixed detection tasks, not claimed as 480 independent patterns. All
observations belonging to one site stay in one cluster; acquisition block is
resampled before site.

## Dimension and estimator

Each complete observation is all four CFA planes over `8x8` plane pixels:
`p = 4*8*8 = 256`. Every leave-one-block-out fold has `n_K = 4*96 = 384`
independent covariance sites, so `n_K/p = 1.5`. The frozen refusal gates are
`n_K > p`, `n_K/p >= 1.40`, positive minimum eigenvalue, condition number
`<=1e8`, and successful Cholesky factorization. There is no shrinkage,
regularization, projection, channel selection, diagonal approximation, or
pseudoinverse.

Four sealed random nonperiodic templates occupy only
`0.12 <= f <= 0.25 cyc/native plane-px`. Alternatives are `+theta` and `-theta`,
so mean, RMS, support and position match. The template seed is derived from the
scientific freeze commit. The local additive task is exactly linear before the
registered nonlinear arms.

For each fold, symmetric `+/-` samples estimate each complete-vector derivative.
The covariance uses a separate zero-target realization from every training site;
no sample used for `d` is used for `K`. The unregularized Hotelling weight is
`w=K^-1 d`, solved by Cholesky. It is evaluated on separate held-out `+/-`
observations. The scalar is held-out `d'^2`, averaged over four templates, with a
band/task curve and accuracy diagnostic. Spatial stationarity is not established,
so this report will not call the result NEQ.

Baseline-only development tried amplitude `0.0015` first (`d'^2=0.428185`,
accuracy `0.627344`) and then froze `0.0045` (`d'^2=5.920683`, accuracy
`0.895573`). No challenge arm was viewed. At the final setting, the five
covariance condition numbers are `1.66179e5` through `2.17187e5`; the minimum
eigenvalue is `1.03410e-5`, all Cholesky residuals are below `1.0e-12`, and the
complete baseline range is `[0.123840,0.813940]`.

## Frozen transformations and order

All deterministic challenges start from the identical sealed baseline floats.

1. Unclipped float USM, Gaussian radius `1.0`, amount `0.5`: implementation check,
   not sharpening evidence. Require ratio residual `<=1e-8`, maximum held-score
   residual `<=1e-7`, congruence residual `<=1e-10`, and positive operator minimum
   eigenvalue.
2. The same USM followed by clipping to `[0,1]`: first kill arm. At least `0.1%`
   of scalar samples must change. Require one-sided `UCB95(R) <=1.01`; otherwise
   candidate 2 is dead.
3. Gamma-3, then logistic `expit(12*(Y-0.5))`: each complete two-sided 95% ratio
   interval must lie within `[0.99,1.01]`.
4. Saturation to `[0.10,0.90]`, then 8-bit quantization: a numeric result must have
   `R<=1` and `UCB95(R)<=1.01`; explicit `REFUSED_RANK` is allowed. An increase is
   death.
5. Only after all above pass: pre-noise Gaussian sigma `1.35` degradation must
   have `UCB95(R)<=0.70`; sigma `0.35` improvement must have `LCB95(R)>=1.30`;
   an exact-copy null must have ratio residual `<=1e-8`.

Any failure stops all later arms. No threshold, dimension, transform, covariance,
task, seed, or refusal rule changes after an arm output. The paired hierarchical
bootstrap is 10,000 draws at seed `0xC2B0057A`, acquisition block first and site
second. The `1.01` bar is inherited unchanged and does not move with sample size.

## Where the algebra stops

For the unclipped linear operator `A`, sample means and the full unregularized
sample covariance transform as `d'=Ad`, `K'=AKA^T`, so the finite quadratic form
and cross-fitted scalar scores are congruence-invariant. This is a correctness
identity, not evidence.

The identity stops at clipping, quantization, gamma/logistic tone, rank loss,
regularization, projection/channel selection, or a failed common-covariance model.
The experiment refuses nonstationary NEQ language, but full covariance itself does
not require stationarity. Optical direction additionally requires downstream noise
and a locally linear pre-noise task; both are explicit in the forward model.
