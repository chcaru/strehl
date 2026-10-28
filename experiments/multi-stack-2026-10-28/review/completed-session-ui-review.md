# Independent completed-session UI review

Date: 2026-10-28. Screenshot supplied by scheduled architecture lane:
outputs/multi-stack/desktop-validation/candidate3/layers-workspace-verified.png.
Inspected directly with view_image, without Computer Use or another desktop
process. This is product/UI evidence only; a resized workspace photograph does
not establish photographic quality.

VERIFIED screenshot observations:

- Selected output and explicit primary both identify Pass 106 primary. The two
  declared passes contain five captures each, and the pass strip preserves the
  reordered pass identity. This part of the selection model reads clearly.
- The finished image header states 10 frames, while the selected layer contains
  five. The top pipeline says 5/10 frames processed and 5 accepted while the
  final phase says Saved. These mix session and selected-layer counts and make
  the completed job look half finished.
- Register, Separate and Reconstruct say awaiting observation; the direct-fit
  panel shows zero observed; the scale matrix says scale plan pending/awaiting
  work. These are unavailable ordinary-pipeline diagnostics in this completed
  session, not pending work. They occupy roughly two-fifths of the main area.
- CAPTURE / ADMITTED SAMPLES is empty. Both passes remain in the source ribbon
  while one layer is selected; without scope text, the labels suggest all ten
  sources contributed to that layer and admission telemetry is forthcoming.

Recommended correction sent to root and architecture: present an explicit
selected-layer summary, for example Layer 2 of 2 / Pass 106 / 5 captures, separate
from Session / 2 passes / 10 captures / 2 outputs complete. Replace unavailable
ordinary diagnostics with a truthful session summary and photograph space.
Retain full-session source browsing while identifying its scope and which pass
feeds the selected layer; do not label absent session diagnostics as waiting.

No implementation edits, build, control request or render were run by reviewer.
A revised actual screenshot is needed to verify the correction.
