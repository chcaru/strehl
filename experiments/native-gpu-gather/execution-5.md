# Device coordinates: one bounded transfer-cost test

The measured Parallel256 pipeline is near-flat against CPU on native109. The
next candidate removes the roughly528MB/frame descriptor upload and host plan
generation. It changes only coordinate placement; MHC/Catmull image arithmetic
and the merge/noise/writer stay fixed. GPU remains opt-in/default-off.

A failing input exists: a source coordinate just outside support that becomes
inside after f32 rounding, an exact fractional midpoint with wrong tie parity,
a red/blue pull replaced by green, or a batch using local rather than full-grid
row origin. The independent descriptor design fixes these before execution.
A hardware/compiler refusal is CONTROL_FAILED, never numerical equivalence.

Build-native-3 uses the existing fresh release builder, max600wall/1800childCPU/
8GiB Job/16MiB log. Source and executable hashes bind every child.
Run-device-1 runs exactly the separate descriptor controls first (37 requests
plus4 API refusals), then the original18 image controls only if those pass.
Each child:120wall/120CPU/4GiB/4MiB log; aggregate240CPU/256MiB retained artifacts.
Current descriptor report must record actual hardware controls and shader
hashes. Original18 acceptance/schema/population remain unchanged.

Only after both pass: device-native-112-1 runs three GPU/Device256 rounded
renders of the existing eight-RAW112 plan, log off/on/placebo. All three must
match the held whole-TIFF and decoded RGB16 hashes; completed RGB and green
calls must equal input count, with no CPU fallback. This proves observer
nonperturbation on the new route, including placebo. The existing full native
height exercises multiple256-row batches and the80-row final strip.

Only after those pass: device-native-109-1 executes same-binary
CPU/GPU/GPU/CPU on the existing22-RAW109 plan, rounded consumer, device schedule,
eight workers and numeric logs off. Report both directions and per-setting
minima, decode separately, complete process CPU/wall/memory, exact hashes and
route evidence. No speed claim from the112 pilot or forward direction alone.
Near-flat timing is an observed bound; no repeated sweep is allocated merely
to produce a favorable order.

Each native child keeps existing180wall/900CPU/8GiB/2MiB log limits.
Seven additional TIFFs plus the13 retained predecessor outputs fit4GiB total;
retain all20 locally with hashes. Never write source RAWs. Check selected
input size/mtime and saved-map hash before/after; this is not a corpus audit.
Timing includes initialization/preparation/transfers/synchronization/write and
excludes the saved alignment solve. Exact image identity preserves current
quality; it does not establish SOTA quality or a fair competitor ranking.

If any control or native comparison fails, preserve evidence and stop later
arms. Repair only a demonstrated bounded implementation defect against fixed
criteria; do not change stimulus, tolerance, precision contract or controls to
make the run pass. If the transfer hypothesis yields no reliable speed gain,
record that result and close it rather than expanding the GPU framework.
