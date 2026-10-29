# Native estimator experiment with geometric repeat proposals

This is separate from `noise-bee-repeat-matching-proposal.md` and its strict
compatibility producer. **GeometryProposal is not RepeatCompatible.** It cannot
enable focus, depth, PSF, optical bandwidth or original-CFA reconstruction.

The hidden `--uncertainty-repeat-proposals` research arm is restricted to exactly
two declared Repeat passes with at most64 originals each. Source counts are
checked before original decoding/alignment. It conflicts with original-CFA
reconstruction, no-group, only-pass and reproducibility controls. The ordinary
command and existing session behavior remain unchanged when it is absent.

## Frozen proposal mechanism

The proposal consumes only source identities and the saved direct native
geometry graph. For each source, use the nearest-rank75th percentile of incident
accepted native RMS/leverage plus the nearest-rank95th percentile of absolute
direct triangle log-scale closure. Require at least3 incident edges and1
triangle. There is no division by square root of sample count, no calibrated
uncertainty claim and no source-image residual from the downstream estimator.

A cross-pass pair is nominated only if a direct accepted native edge exists and
its saved placement log-scale gap is at most `max(old_radius, proxy_i+proxy_j)`.
Canonical original-content order defines assignment ties. The objective is
maximum pair count followed by minimum total integer cost
`round(1e6*(gap/radius)^2)`. This is a heuristic for proposing observations, not
optimal photographic quality. Normalized gap can reward uncertain/weak-leverage
fits; that failure direction must be exercised. Unknown proxies leave sources
single. No source is dropped, duplicated, split or silently truncated.

The output archives both the old assignment and every new proxy, nomination,
cost and resulting group. The actual per-coefficient agreement, original support,
clipping, primary fallback, injected noise and cross-group focus logic remain
unchanged. Regrouping still changes mean/variance and hence cross-group focus
weights; increased pair count alone is not a noise benefit.

## Required controls before full-photo inference

Run flat input first. Exercise the actual proposal-to-core path on stationary
texture, genuine fine focus steps, small blur, displacement, brightness changes,
clipping and unequal variance. Include an uncertainty/weak-leverage foil. Keep
clean-arm signal transfer per CFA component, both-own-state risk where the two
signals differ, and the ordinary ungrouped and old-proposal controls. A favorable
noise metric caused by loss of signal must fail interpretation. The fixed
proposal/cost policy must not be tuned from real candidate appearance.

For the32-original bee scene, preserve original identity, map, canvas, sampler,
noise, workers and display transform. Compare complete native outputs from old
4-pair grouping, broader geometric proposals and all-single grouping, with the
same nine fixed native witnesses and independent review. Save linear masters,
sensor outputs, full commands, executable/source bindings and resource receipts.
The existing all32 fit is conditional on those captures; do not describe it as
independent held-out placement. Real output quality and any noise claim remain
unverified until those comparisons are complete.

## Product17 execution binding, before new output inspection

`repeat-proposal-full.py` freezes the three commands and all source/map/build
identities before rendering. The simple session currently exports a linear RGB
master and contribution maps, but no separate final CFA sensor master; therefore
the three-arm result will retain these actual artifacts and will not claim a
sensor-master comparison. Original-site covariance remains a separate controlled
experiment. Full native PNGs and all nine unchanged384px witnesses use the
previously frozen black0.00033/white0.38858/sRGB transform. The complete legacy
linear master must remain bit-identical to product16.

New large artifacts are stored in `D:/codex-work/multi-stack-2026-10-28`, reached
through the workspace `outputs/multi-stack/overflow` junction. This is outside
all capture corpora. No existing capture, cache or result was moved or deleted.
The release build used4Cargo workers, took176.475s and sampled3.310GB peak private
memory. CLI SHA256 is
`036042897ce3bf4034f8c97db9859ebdb1b7b175aac7f246ba1602e54f86355f`.
Rendering uses8workers/16GiB and may overlap the separately scheduled4worker
cached mosaic/synthetic lanes; record host load and do not interpret these
elapsed times as isolated comparative performance benchmarks.
