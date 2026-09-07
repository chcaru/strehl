# Independent review of the software-noise statistical reader

2026-09-07. **SOURCE-REVIEWED / DERIVED; no statistical execution.** Curie
reviewed Zeno's held `independent-noise-reader.py` at SHA
`aba1bc507a9236d55ad4799b786a56bc995d08eb33585f66280981e483d72138`
against `next-noise-contract.md` at SHA
`4e92e176d0cfae6dcdc9fedab3ff8f5d40f858c47eb0fcddbd14877d894d29f2`.
No held source was edited, imported or executed. This review finds no
statistical source-level blocker. It does not commission the reader, predict
that the fixed seeds will pass, or supply physical noise calibration.

## Quantities and consumed stages

`read_trace` (line309) reads the actual consumed photon/read addends, using the
mandatory exceptional arrays for post-Poisson colour scaling, cloned green,
omitted read and correlated read. It reconstructs and hash-checks their sum,
the selected-gain pre-encoder value and the actual encoder input. In
particular, the X moments consume the black-clamped `x_used`, not the earlier
unclamped hash. The nominal .25 gain remains a separate expectation. Every Q
sample is reconstructed with floor/fraction/parity logic (line230), distinct
from the producer's `rint` seam, with actual pre-clipping rail counts and the
per-sample half-DN bound.

`Temporal` (line478) updates five full spatial mean/M2 pairs by Welford at each
fixed site across exactly64 repeats. Only after temporal accumulation does
it average the3072 sites of each CFA parity; the variance denominator is
63*3072. It does not substitute spatial dispersion for temporal variance or
pool different parity means. The known P/R/E/X means and variances, 2% limits,
and bright/dark quantization checks match the contract. Zero-mean photon
populations additionally require zero actual nonzero photon counts. Their
ratio/correlation remains explicitly undefined, rather than an extra
independence pass.

## Pair populations and buffer reuse

`PairMoments` (line445) subtracts the specified known means and then computes
ordinary centered Pearson from all five sufficient sums. The reported
covariance uses pair_count-1. Subtracting the known mean does not replace
empirical centering. A non-photon zero denominator fails a healthy population.
The source slices implement these complete populations per level/parity:

| Instrument | Actual pairs | Count |
| --- | --- | --- |
| Photo/read | same photosite over64 repeats |196608 |
| Adjacent photo/read repeats |63 adjacent repeat pairs,3072 matching sites |193536 |
| G1/G2 photons | each complete native quad,64 repeats |196608 |
| Horizontal read |48 rows *63 same-parity horizontal neighbors *64 repeats |193536 |
| Vertical read |47 same-parity vertical neighbors *64 columns *64 repeats |192512 |

The horizontal and vertical slices exclude wraparound. The correlated-read
producer fault is periodic, but that does not make the reader pairs periodic.
Adjacent repeat pairs overlap and cannot be described as independent
replicates. All originating parity strata remain separate.

`cross_frame` (line722) uses all ten i<j pairs. For each, it concatenates only
the three registered read groups, giving36864 pairs of equal-variance,
zero-mean read observations. Individual group/parity values are descriptive;
the code explicitly removes their acceptance flag. The shared-frame fault
replaces only the dark group. No mean of correlations is used.

I followed scratch ownership through both accumulators. Welford's delta,
updated residual and product are overwritten for every quantity. Correlation
work buffers are distinct from the retained trace and previous-repeat arrays;
each subtraction/product overwrites its consumed region before reduction.
The previous repeat is copied, released before replacement, and never serves
as scratch. Cross-frame buffers are likewise distinct from both read traces.
The reviewed paths do not carry a previous residual into a new statistic or
modify an array that a later instrument assumes unchanged.

## Quantization and named failure instruments

`rounded_normal_oracle` (line582) uses the registered erfc-tail differences,
symmetry and k=1..12 second-moment sum. Its tail expression matches the bound
obtained by integrating (x+.5)^2 beyond L=12.5 and applying the normal-tail
upper bound. That is a truncation bound, not a total floating-point error
bound. The zero-bin probability is reported but correctly contributes no
second moment. No added-1/12 assertion enters the gate.

The bright variance comparison uses the declared a=64/63 correction and
sqrt(a*vX)+a/4 slack. This is appropriate to the actual average of per-site
sample variances: the per-site bounded rounding error and Cauchy/Jensen bounds
give that expression. The independently exact Q reconstruction supplies the
tighter per-sample check; this broad variance inequality alone cannot prove
independent quantization noise.

`fault_power` (line593) requires the named numerical failures rather than a
generic failed group: R/B consumed shot variances with green marginal
companions; all X mean/variance failures for doubled gain; read and encoded
dark variance for omitted read; zero temporal variance plus identical arrays
and failed adjacent-read null for repeated keys; cross-green failure with
preserved marginals; preserved read variance plus nonwrapping correlation>.2
for the correlated-read fault; and absent below-black codes plus dark encoded
mean/variance failure for black clamping. The last also retains altered X
moments, although its registered required instruments concern encoded dark
statistics. The covariance is retained alongside correlation.

`replay_checks` (line750) compares every restored temporal call with its
original baseline's full raw/consumed/encoded signatures. It separately
requires actual raw read-stream equality where the nominal read key is
unchanged, observer and reverse-order equality, and live keys/states/payloads.
The repeat/shared-key fault records remain structurally checked against their
declared actual overrides; their nominal mismatches are retained rather than
terminating before numerical instruments run. All healthy/restored temporal
groups and all ten healthy cross-frame correlations must pass. Shared-frame
fault power also requires identical dark read arrays and all ten pooled-null
rejections.

## Limits of this review

These gates test selected marginal and dependence paths, not universal
independence. Replayed restorations are intentionally identical and are not
new statistical replicates. The .02 bars are fixed engineering limits rather
than exact familywise probabilities. Strong finite-sample fluctuations must
remain failures; this review authorizes no changed seed, threshold or subset.
The same injected law supplies the software expectation and plant, so even a
future pass cannot establish camera calibration. The reader retains only the
current trace, previous repeat or two cross-frame traces plus online arrays;
it creates no repeat-volume or frame-volume and uses the caller's unchanged
Budget. Actual timing, memory witnesses and rejecting-control outcomes still
require the separately released execution.
