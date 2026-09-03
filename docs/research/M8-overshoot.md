# M8 source-hull census

**Verdict: FAIL; no blocker.** All work used the registered development-only
1/2.5/6-second stacks, never a holdout
(`docs/proposals/2026-09-sota-scorecard.md:283-285`). Input metadata fingerprints
were unchanged before/after (`experiments/M8-overshoot/results.json:329-353`).

## Registered measure

I measured scorecard v1.7's M8 text
(`docs/proposals/2026-09-sota-scorecard.md:1-2`): per-frame,
pre-merge/pre-clamp linear `f32`
M8-R against an independently reconstructed exact 4x4 Catmull-Rom support and
`tau_R = 8*ULP_f32(max(1,|lo|,|hi|))`
(`docs/proposals/2026-09-sota-scorecard.md:765-797`); final linear M8-O against
all geometrically valid frames with exactly `0.5/65535` serialization tolerance
(`docs/proposals/2026-09-sota-scorecard.md:798-805`). Both bars are exactly
`0.0000%`; the identity arm must also be zero
(`docs/proposals/2026-09-sota-scorecard.md:807-811`).

## Independent instrument and commissioning

The private-snapshot hook serializes placement coefficients, source planes, and
raw gathered values, but no hull or verdict
(`experiments/M8-overshoot/m8_trace.rs:107-126`). The Python checker imports no
Strehl code (`experiments/M8-overshoot/results.json:290-313`) and separately
implements centre mapping, support indexing, boundary validity, and ULP
tolerance (`experiments/M8-overshoot/checker.py:234-285`). Snapshot insertion
uses unique full-line anchors and hard-errors unless each occurs once
(`experiments/M8-overshoot/inject_trace.py:13-17`,
`experiments/M8-overshoot/inject_trace.py:42-50`).
For M8-O, each white-balanced support is independently mapped to the final
linear domain by `output_gain/frame_gain/sensor_range`
(`experiments/M8-overshoot/checker.py:332-361`,
`experiments/M8-overshoot/checker.py:409-417`).

Commissioning passed both directions: fractional Catmull hard step
`28/252` violations, 14 each sign, extrema `-0.0625/+0.0625`; copy null
`0/252`, exact-copy error `0`; convex bilinear null `0/300`. The additional
`lo/hi ±32*tau` plant found exactly `2/252`, one each sign
(`experiments/M8-overshoot/results.json:27-61`). The real crop/reference arm was
`0/32,919,152`, with zero exact-copy error
(`experiments/M8-overshoot/results.json:267-289`).

## Development reading

| Stack (`cover=scale`) | M8-R violations / denominator (%; signed excess, linear source units) | M8-O violations / denominator (%; signed excess linear) |
| --- | --- | --- |
| 1 s, `k=0.9862` | `23,101,596 / 1,977,960,960` (1.167950%; `-86.110535/+129.321899`) | `7,562 / 24,724,512` (0.030585%; `-0.000749496/+0.001127632`) |
| 2.5 s, `k=0.9870` | `20,808,895 / 2,010,926,976` (1.034791%; `-119.364258/+273.181641`) | `14,688 / 24,724,512` (0.059407%; `-0.001811185/+0.001910414`) |
| 6 s, `k=0.9859` | `19,280,685 / 2,142,791,040` (0.899793%; `-240.040039/+586.215820`) | `961,398 / 24,724,512` (3.888441%; `-1.049185276/+0.003703290`) |

Per-arm evidence and coordinate-manifest hashes are recorded at
`experiments/M8-overshoot/results.json:64-265`; coordinate-validity mismatches
were zero. Aggregate M8-R is `63,191,176 / 6,131,678,976` (1.030569%);
aggregate M8-O is `983,648 / 74,173,536` (1.326144%)
(`experiments/M8-overshoot/results.json:2-25`).

M8-O also fails, but final clamping can erase overshoot evidence; even a clean
M8-O could not establish a pass
(`docs/proposals/2026-09-sota-scorecard.md:823-825`). M8-R is decisively nonzero
on every arm, so the registered source-hull invariant fails.
