# Sony capture workspace

Identifier: `sony-capture-ui-2026-11-07`. Owner: root. Allocated in the
[milestone ledger](../../docs/agents/milestone-ledger.md).

The owner requests a Rust desktop capture program styled like Strehl, with live
focus inspection, start/end focus marks, a smallest-step default, start/pause/stop,
optional automatic bounds, and metadata on the SD card if the protocol allows it.
They also request a research answer about A7CR pixel-shift/focus alternation
without asking them to acquire hardware. RAW captures remain on the camera card.

## Prior work and changed scope

`python scripts/research.py search 'focus control' --limit 10` and
`python experiments/ORCH-drift-check/prior_art.py 'focus control' 'pixel shift' 'auto bounds'`
were run before implementation. The owning evidence is the
[SDK audit](../sony-focus-control-2026-11-07/sdk-audit.md),
[two physical tests](../sony-focus-control-2026-11-07-capture-review/results.md), and
[optical upgrade analysis](../sony-upgrade-2026-11-07/results.md), committed in
`dd6c19d58cfce3f3ac9372891da0d63bd76f5411`.
The mechanical search also surfaces historical M86 alignment and V-LINEAR2
focus-band work; neither calibrates this live-view camera controller. M11/M69
show why unqualified gradient energy cannot establish sharpness or quality.

New work is capture orchestration and a preview aid, not a reconstruction
algorithm or a promotion of the rejected breathing-super-resolution branch.
One normalized focus unit is the smallest command, not the smallest guaranteed
physical displacement. Start/end marks have the same non-metric gauge.

## Implementation and controls

- Separate Rust/egui executable, using Strehl's palette. A narrow original C++
  process bridge retains the Sony SDK ABI; it does not download captured files.
- Exactly one owner of the camera. Transient JPEG preview buffers are bounded.
  Shutter completion requires events and idle card; timeouts never retry shutters.
  Pause/stop take effect at a completed camera operation. Persist intent before
  release and completion afterward. No crash recovery can assume an exposure
  did not occur merely because its acknowledgement was lost.
- Manual start/end marks and bounded directional approach. Include both endpoints
  even when the final interval is shorter. No physical-distance claim.
- An opt-in preview sweep only between user-selected rough limits, with a subject
  ROI and multiple local texture peaks; retain endpoints when support is missing
  or a peak is clipped. Flat/noise, gain-only, constant-texture, out-of-range peak
  and known blurred-texture controls precede use. Preview sharpening, noise,
  breathing and background texture can fool the score: suggestion only, reviewed
  and explicitly applied by the user. Never start capture from an auto suggestion.
- Metadata uploads must use documented APIs. If arbitrary SD writes are absent,
  journal locally and export new sidecars after the card is mounted; do not
  disguise a JSON file as a camera-settings upload.

Use at most two build workers. Run focused Rust state/protocol/journal tests,
the existing controller tests and native gate self-test, native offscreen UI
exercise at laptop sizes and relocated portable-package smoke. No camera is
automatically focused or exposed during verification. Capture corpora are read-only.
Document commands and build identity, distinguish synthetic/operator verification
from physical validation, and stop the auto-suggestion claim at unverified hardware.
