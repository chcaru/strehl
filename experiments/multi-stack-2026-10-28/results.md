# Multi-stack implementation and validation

## Outcome and scope

VERIFIED: the additive session path supports Combine detail, Repeated captures,
Exposure range and Aligned layers in the CLI and desktop. An optional primary
sets the framing reference and prefers supported primary observations when
proposed matching observations disagree. It does not lock unmatched focus
regions to the primary. Unset is symmetric; a coordinate reference alone does
not acquire a fusion preference. Ordinary single-folder stacking keeps its
existing consumer. The base is remote main
`c149e52834fc1c86c2af0fe022713c39fa25f33c`, fetched again before final validation.

The attached proposal and derivations were hypotheses. The
[research challenge](challenge/report.md), [corpus census](corpus/report.md)
and [architecture audit](architecture/audit-and-pilot.md) informed the shipped
scope. No depth, super-resolution or stitching quality is asserted. The supplied
corpus does not supply independent phase or depth truth or a controlled mosaic
capture; implementing those claims from inferred scale alone was not justified.

## Engine contracts

VERIFIED by source review and controls: ordered explicit passes and continuation
folders retain distinct acquisition identity. Original content hashes reject
copied files as repeated observations. Runtime geometry solves direct pairwise
fits jointly, with separate within-pass tracks and connected-component evidence.
Original storage remains u16 CFA. Each consumer gathers same-color samples with
coverage and clipping masks; arithmetic is f32 and demosaic happens once.
There is no aligned-frame image volume.

Repeat groups propose at most one acquisition per pass. Local coefficient and
color agreement with the injected noise model governs averaging; unmatched
observations remain useful. Group variance reflects independent equal-weight
observations, not an optimal inverse-variance HDR estimator. Saturated samples
are excluded where supported unclipped observations exist. When all are clipped,
the engine preserves real clipped information and reports the fallback; it does
not invent recovered highlights or black unsupported pixels.

HDR requires matching camera/lens/ISO/aperture and validates a bounded correction
to the shutter ratio on spatial holdouts over several proposed focus pairs.
Contradictory supported radiometry cannot be hidden by selecting only successful
pairs. Failure retains diagnostic reports and withholds a completed photograph.
Layers preserve separate calibration and appearance on a common canvas.

## Complete real captures

Every table entry used all sources in the named passes. Capture folders remained
read-only. Exact commands, environment, executable SHA256, host load samples,
exit codes and timings are retained in the corresponding `outputs/multi-stack`
`*-run/receipt.json`, `command.log` and `resources.jsonl`. Source identities and
resolved recipes are beside each output. Times during concurrent validation are
observations, not isolated throughput comparisons.

| Run | Sources | Evidence |
| --- | --- | --- |
| Remote-main ordinary insect106 and107 | 299 each | Full photographs, RGB masters and sensor masters; isolated maps. |
| Candidate ordinary regression106 | 299 | All three complete output files byte-identical to baseline before build-stamp changes. |
| Single-session delegation6 | 299 | Fresh ordinary alignment and merge; all photograph and master pixel bits identical to main. Master file also identical. |
| Repeat4, pooled4, only106/107 controls | 598 joint geometry | All 598 placed;5,226 native edges,4,629 cycles;6880x4584 canvas. Repeat has 118 paired proposals and 480groups. |
| Explicit-primary6 | 598 | Primary0; exact same numeric geometry/canvas as no-primary. Complete photograph and master. |
| Slide HDR pair6 | 61+65 | 2.5s and6s;126 placed,863 edges,738 cycles;6928x4620 output; measured gain[2.5335414,1]. |
| Slide three-pass refusal5 | 60+61+65 | 1s pass has no eligible quarter-step focus nominees. It was never photometrically tested. No completed photo/master. |
| Aperture layers6 | 109+83 | Full f11/f14 fabric passes, distinct calibrations, two common-canvas photographs/masters. |

MEASURED: the complete598 repeat run took 1452.21 s with 13.397 GB sampled peak
private memory under a 16 GiB session budget. It overlapped other work; it is not
an isolated benchmark. The full 192-source layer export took 594.81 s with 8.482 GB
sampled peak private memory under the same budget, also concurrent.

## Photographic review and causal limits

The independent reviewer froze display and native witnesses before seeing the
candidate. The display implementation was commissioned against every baseline
encoded channel; crops were exact 384x384 slices with no resampling. Complete
masters and complete displayed images were retained. Overviews establish
framing only. See the [review protocol](challenge/photographic-review-protocol.md),
[initial and controlled insect review](review/first-repeat-photograph-review.md)
and [final five-arm review](review/insect-five-arm-photographic-review.md).

VERIFIED observations: the insect outputs have coherent complete framing with
no gross new missing anatomy or tiled seam in the inspected images. Fine hair
fringes, changed glints and pass-dependent occlusion content remain. The bright
underlying-leg region tracks pass107 and persists in pooled, repeat and primary0.
Primary preference is therefore not a general appearance lock. The only106
native control already changes some glints relative to the old consumer; those
changes cannot be attributed to adding another pass. The grouped path is active,
but no clear visible detail or deghosting gain over pooled fusion was established
in the nine frozen witnesses. This is not proof that every pixel is equal or
that no noise benefit exists elsewhere.

No temporal-noise, sqrt(K), resolution, depth or general highlight-recovery claim
is made from display brightness, gradient energy or spatial standard deviation.
The real pairs have no physical matched-focus ground truth. Flat-noise, motion,
blur, clipping, color disagreement, wrong-transfer and duplicate controls test
mechanics and gate failures; they do not establish photographic improvement.

The [aperture-layer review](challenge/aperture-layers-review.md) verified both
complete 6636x4424 RGB32F masters, identical canvas, finite values and exact
independent readback. Eighteen frozen native crops showed no holes or seams.
Soft fibers and glint fringes remain; different WB/aperture and no per-pass
ordinary baseline prevent attributing visible differences to aperture alone.
The selected optical profile itself labels f11 untested and f14 beyond its fit
evidence. This validates capability, not optical calibration or improvement.

The [final independent HDR review](review/hdr-photographic-review.md) uses the same geometry, color basis and two
predeclared display transforms for the fused result and both only-pass controls.
All six complete overviews and 72 native crops were inspected. The fused image
preserves short-only chart structures that the six-second result blurs or halos,
and avoids faint long-only regular texture in the two original-clipping core
witnesses. Against the short-only control, no clear added detail or shadow/noise
benefit was established; some high-contrast edges appear slightly softer.
All 61 short sources have full delivered-canvas coverage and zero clipped
footprints, so actual unclipped support exists. There is no per-band local
contribution receipt, and the proven clipped cores are mostly flat: this supports
highlight handling and preservation, not recovered fine detail or a general
increase in useful dynamic range. The initial HDR diagnostic controls used
pass-specific WB; review caught that confound and the final controls explicitly
use the fused session anchor WB. No claim relies on the mismatched controls.

## Regression, desktop and resource verification

VERIFIED: core suite 616 passed, 4 ignored plus sampler contract; desktop suite 987
passed, 15 ignored. Session-specific controls 52 passed after final prefetch
integration. Tests cover primary/no-primary, duplicates, wrong geometry/cache
bindings, masks, motion/blur/clipping disagreements, HDR holdouts, missing source
identity, UI source-census races and saved-run routing. Exact logs are retained.

The real desktop embedded engine rendered 10 original sources, saved its recipe,
validated the full ordered source census and hashes, restored saved runs, edited
and restored layer versions, and rendered native egui/wgpu screenshots. Reports
are in [desktop validation](geometry/desktop-validation.md) and independent
[completed UI review](review/final-saved-session-ui-review.md). Session summaries
show their actual pass/layer scope instead of pending ordinary diagnostics.
Returning to an ordinary stack restores its complete prior recipe.

Strict desktop Clippy and formatting pass. The engine inherits formatting and
Clippy findings from the exact main base; these are mapped in the independent
[lint audit](review/clippy-baseline-audit.md) and [format audit](review/engine-format-review.md).
New findings were corrected; inherited findings were not silently relabeled as
passing strict checks.

The first optimization parallelized independent gather and coefficient work
without changing reduction order. A 10-source full-resolution pilot preserved
every image bit while accumulation time fell from 11.141 s to 0.965 s. Total pilot
runtime changed 33.459 s to 22.440 s under the recorded conditions. Persistent exact
operator reports then reduced another pilot from 20.404 s cold-transfer to 10.123 s
warm-transfer, again with every image bit preserved. These are pilot/cache
measurements, not extrapolated full-corpus speedups.

MEASURED: alternating cold-transfer ABBA pilots took 21.201/20.206 s before and
15.376/15.180 s after prefetch, with zero cached transfer hits in every arm.
The smaller-time comparison is 24.9% faster; these are two runs per arm, not a
population confidence interval. All photograph/master bits, geometry, source
identities and non-resource/non-timing fusion reports match exactly. Sampled
peak private memory was 3.905–3.916 GB before and 3.499 GB after. Exact commands
and equality proof are retained in `outputs/multi-stack/prefetch-equality.json`;
reproduce with `sampling/benchmark-prefetch.py` and `verify-final-equality.py`.

Final bounded prefetch prepares at most four independent probes, constrained by
worker and checked memory limits, before fusion workspaces are allocated. Only
small transfer receipts survive that phase. Same-key repairs serialize, failures
join the active batch before returning, and fusion keeps its original source
order. A conservative reservation still includes one probe during fusion and
can refuse a near-limit job after prefetch; this is a resource UX limitation,
not an allocation overrun. GPU use remains in the desktop viewer; CPU fusion and
bounded caching were the validated performance path.

VERIFIED: the final candidate7 complete 598-source grouped render matches every
RGB16 photograph bit and RGB32F master bit from candidate4. Every numeric
geometry, transfer and fusion diagnostic matches; the comparison explicitly
checks the sole changed explanatory HDR limitation sentence. The final run
used 598 verified transfer-cache hits, took 481.404 s and peaked at 4.994 GB private
memory while other validation/build work ran. The faster cold-to-warm total is
not an isolated implementation speedup. Evidence: `final-full-equality.json`.

VERIFIED: the Windows portable package is `desktop-4f645cc797d86ea7`, built from
a copied source snapshot. Its source/binary manifests and every ZIP CRC pass;
all packaged Rust sources equal the validated worktree. The packaged desktop
embedded worker rendered the pilot successfully and matched the validated
photograph, master and numerical diagnostics exactly. The 25,674,028-byte ZIP
includes matching sources, rebuild instructions and decoder/license notices;
SHA256 is `289df6d3c875a743d9664618dfdece87a8e5cd30cb881d7406b988f5cc1e6ba1`.
This is a local Windows preview, not a signed or published release.

The [final independent style audit](sampling/final-style-audit.md) confirms zero
introduced Clippy warnings or formatting hunks. Final CLI Clippy retains
106 inherited warning sites; the engine format check retains 645 hunks. Corpus lint retains 16 diagnostics in seven
older files, whose Git content is unchanged (only checkout CRLF normalization).
The three newly introduced ledger-table gaps were fixed. Changed documentation
links and final newlines pass the recorded check.

## Reproduction and retained evidence

Compact retained commands, artifact hashes and equality receipts are in
[results/evidence.json](results/evidence.json). Start with [the product guide](../../docs/multi-stack.md). Full-source manifests
are under `outputs/multi-stack/manifests`; exact decoded caches and images are
local generated artifacts, not Git content. `run-command.py` records commands
and resources. `freeze-candidate.py` records owned source hashes and executable
hashes before each candidate campaign. Candidate source archives and complete
outputs remain under `outputs/multi-stack`.

This report does not fold new numbered claims into SYNTHESIS. The detailed
reports and receipts are the evidence record; established rejected native
spectral recipes and the earlier paused research program were not resumed.
