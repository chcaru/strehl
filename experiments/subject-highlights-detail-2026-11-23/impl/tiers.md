# Exposure tiers: the capture format (plan X3)

**Status:** contract for stages X3 (Pi), X4 (engine), X5 and R (desktop), 2026-11-24.
Everything here is additive: a capture without highlight groups is written and read
exactly as before.

## The plan

`Plan.highlight` (omitted when off):

```json
{"shutter": 65586, "every": 2, "first_plane": 1, "last_plane": 199, "shots": 4}
```

- `shutter`: the camera's ShutterSpeed property value for the highlight groups.
- `every`: a highlight group at every plane (1) or every second plane (2) within the range,
  counted from `first_plane` (plane numbers as files carry them, 1-based).
- `shots`: 4 (the owner's decision: highlight groups are four-shot).

## The journal

- `capture_intent` and `capture_buffered` events carry `"tier": "base"` or
  `"tier": "highlight"` and `"exposure": {"iso": <code>, "shutter": <code>}` (the
  commanded values). Absent `tier` means `base`.
- Each file entry in `capture_buffered.data.response.camera_reply.files[]` carries
  `"tier"` too.
- At a plane: base group, then set shutter, highlight group, then set shutter back,
  then the move. The lens does not move between the two groups.
- New events `exposure_intent` / `exposure_complete` record each shutter change.

## Follow-up passes

`queue_pass {planes: [..], tier: "highlight"|"shadow"|"base", shutter: <code>}` appends
groups of that tier to a finished capture (R3). Their `capture_buffered` events carry the
tier and exposure as above; plane numbers are the existing planes'. Infill planes (R2)
use `queue_infill {positions: [..]}` and get new plane numbers after the last.

## Positions runs

`capture_positions` accepts `shutters: [<code>, ..]`, one per position (or omitted):
the Calibrate survey (X1) takes each position at two shutters by listing it twice.
Each group's events carry its exposure; `tier` is `"base"`.

## Capability

`capabilities.exposure_tiers: true`. A desktop sends `highlight`, `shutters`, and
`queue_pass` only to a host that announces it.

## The engine's identity

- `all_groups` reads `tier` per group; `plane_groups` keeps the last complete group per
  plane **and tier**. The base tier is what the stack is made of; a highlight group is a
  companion of its plane's base group, or, with `every` above 1, of the nearest plane's.
- The exposure ratio is measured per pair (never taken from the shutter codes alone):
  start from the commanded ratio, correct it from sites well exposed in both groups.
