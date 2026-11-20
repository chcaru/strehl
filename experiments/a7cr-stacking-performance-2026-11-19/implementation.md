# A7CR stacking performance, round 3: implementation results

The stages of [the round-3 plan](../../docs/proposals/2026-11-a7cr-stacking-performance-plan-3.md)
built or measured on 2026-11-19 (evening and night), after the owner's direction: "take
forward the plan". One commit per stage on `main`, each checked against the reference
renders before it was committed. Every render is in
[`evidence/implementation-runs.txt`](evidence/implementation-runs.txt) (binary,
environment, wall and CPU seconds, peak private memory, host load before the run,
output SHA-256); timestamped engine logs are the `evidence/timeline-*.txt` files.

Input: the scarab capture (196 four-shot planes, 784 format-1 archives) on D: (Samsung
980 PRO). Host: Ryzen 9 9950X3D, 64 GB, RTX 5090; idle (0-5 % CPU) before each run, one
run at a time.

Labels: MEASURED, VERIFIED, DERIVED, ARGUED, UNVERIFIED.

## Results (MEASURED)

| Render | Before (HEAD `bbb954f58`) | Now | Commits |
| --- | ---: | ---: | --- |
| Later render, default route, stack on D: | 20.1-21.7 s (ten runs: HEAD, or a new build with its switch off) | 17.6-18.0 s | `30dec68ee`, `5f4c838ef` |
| `--limit 24`, GPU | 8.8 s | 7.1 s | the same |
| `--limit 8`, GPU | 8.1 s | 6.1 s | the same |
| `--limit 24`, CPU route | 36.9 s | 36.7 s | the same (the CPU route only gains the measurement) |

Every render wrote its reference bytes (full `02A6C8C2...`, `--limit 24` `E37E8E6F...`,
`--limit 8` `A9F840B4...`, both residual modes); the A7C II byte-freeze held 5/5 under
`auto` and `off` after R2 and under `auto` after the measurement change.

## Stage by stage

### R2: the GPU fold finished on the device (`30dec68ee`)

The host no longer reads 7.5 GB of totals back to resolve, collapse and clamp on the CPU.
It reads what it computes itself (`den`, the ensemble sums, the null windows: the blend
maps and the run log; with the desktop observing, the green planes' `num` and `usum` its
accumulator view reads), `BandMerge::finish_plan` computes the blend maps, and the device
resolves, collapses and clamps (`fold.wgsl`: `resolve`, `expand_add_v`, `clamp_hull`).
The half-stacks are finished there too and combined with `absorb`'s operations
(`combine`); a pass of several canonical chunks (the preview's two) folds every later
chunk into a second accumulator, combined after each chunk as the host absorbs chunks.

- Exactness: `strehl-gpu` `tests/fold.rs` `the_device_finish_is_finish_with_report` (two
  half-stacks and their absorb against `finish_with_report`, planes, report and averaged
  fractions bit for bit); three mutations caught (blend threshold, hull clamp, combine's
  min). `STREHL_FINISH_CHECK=1` on the scarab stack: the preview, both half-stacks and
  the stack bit-identical. The desktop's accumulator surfaces (`STREHL_UI_PROGRESS=1`,
  `--limit 24`) identical to the previous build's, 40 of 40.
- Time: half-stacks 1.6-2.4 s to 0.8-1.4 s; later render 20.1-21.0 s to 18.2-18.8 s
  (alternating `STREHL_DEVICE_FINISH=off` and on, two pairs).
- Not moved: the blend maps stay on the CPU (they use the platform `ln`): 0.18-0.22 s per
  finish, 0.49 s for the two halves side by side, about 0.9 s a render.

### The lateral-colour measurement (`5f4c838ef`)

The preview's measurement (every render) spent most of its 1.3 s in `cos` and `sin`: the
tile FFT evaluated each twiddle factor per butterfly (2.6 million pairs per 256 px tile)
and the Hann window per sample. Both now come from tables built once by the same
expressions; the column transforms run as whole-row butterflies; the upsampled-DFT
refinement advances its 30 sums side by side. Each element sees the same operations in
the same order.

- Exactness: the tabled FFT against the per-butterfly form (forward, inverse, windowed)
  and the refinement's whole grid against the one-sum-at-a-time form, bit for bit; a
  coarsened twiddle and a reversed sum order each fail them. The scarab residual line is
  unchanged (`red t (-0.092, -0.115) px, scale -12.6 ppm (688 of 694 tiles, rms 0.217 px)`).
- Time: the preview's collapse and measurement 1.8-2.0 s to 1.0 s, its pass 4.4 s to
  3.4-3.5 s. With the tables alone (before the layout changes) the preview's pass was
  4.1 s; at `--limit 96` its tile loop then still spent 8.3 core-seconds in forward
  transforms and 9.8 in correlations, which the layout changes addressed.

### C1: the camera's USB link reported (`847cb8c8b`)

The controller reads the camera's negotiated speed from sysfs at connect, keeps it in the
camera identity (every run's manifest records it) and in the state (`usb_speed_mbps`),
and below USB 3 appends a warning to the connect message; the desktop's Capture screen
shows it while the camera is connected. Installed on the studio Pi (backups
`/root/strehl-before-usb-link-1795160603` and `-1795160796`); checked live with the
camera at 480 Mbit/s ([`evidence/usb-link-2026-11-19.txt`](evidence/usb-link-2026-11-19.txt)).

## The camera link (C0): still USB 2.0, and not software

After the owner restarted the Pi and re-plugged the cable (2026-11-19 ~21:45 local) the
camera still enumerated as high-speed (480 Mbit/s, `version 2.10`) on the USB 2.0 half
of the blue port (`1-1`). VERIFIED in [`evidence/usb-link-2026-11-19.txt`](evidence/usb-link-2026-11-19.txt):

- The Pi's USB 3 receiver detects nothing at the far end: with the camera on, the paired
  SuperSpeed port's `PORTSC` reads `Not-connected Disabled Link:RxDetect`. A device
  whose SuperSpeed lanes are wired up and trying would show `Polling`, `Inactive` or
  compliance; `RxDetect` means no termination on the SuperSpeed pairs at all: the
  cable's SuperSpeed wires, a plug not fully seated (USB-A's SuperSpeed contacts sit
  deepest in the port), or the camera not offering SuperSpeed.
- No software changed on the Pi between the last SuperSpeed connection (14 Nov 18:56
  UTC) and the first high-speed one (15 Nov 22:44 UTC): the controller binaries in
  `/opt/strehl-capture` date from 12 and 14 Nov and 19 Nov, the only package change was
  `iperf3` on 12 Nov, and the Pi ran one boot from 12 to 19 Nov. The camera's 66
  journalled settings are identical in a fast run (14 Nov 12:18) and a slow one (19 Nov
  10:54). The kernel command line and udev rules carry no USB quirk.
- Next, by hand: push the USB-A plug fully into the blue port; flip the USB-C plug at
  the camera; try another cable known to be USB 3 (5 Gbit/s) data; try the Pi's other
  blue port (the Wi-Fi adapter's) for a minute. The Capture screen now says when the
  link is slow.

## Measured and not kept

- **R1, a stager filling upload memory ahead of the fold thread** (patch kept outside the
  repository). Bytes identical. On D:, three alternating pairs: wall 20.2 s against
  20.5 s, main fold 10.07 s against 10.23 s; on C: (stack copied, files purged before
  each run) no gain (main fold 9.87-10.12 s against 9.89-10.06 s); 1.8 GB more peak
  memory. Removing the copy from the fold thread exposes the next bounds: on D: the
  drive (50 GB at 5.7 GB/s is 8.8 s, the main fold is 10.1 s with its 1.1 s totals
  readback); on C: in-order decoding (sixteen decoders each spend about 600 ms on a
  plane in an 18-plane window, so the stager waits 4 s for the next plane). An upper
  bound taken first, with the copy simply skipped (wrong bytes), had shown 1.3 s, most of
  it from files the run found in the file cache.
- **A deeper read-ahead during the preview's tail** (44 planes, 11 GB hand-off): 22.8 s
  and 37.9 GB peak, worse.
- **The preview's files read through the file cache** so the main pass finds them: the
  main fold 10.65 s either way.

## Answers measured along the way

- **Publication** (round-3 R4): the desktop's decode of the 722 MB float master took
  0.166 s and of the 361 MB photograph 0.064 s (`strehl_edit::load_tiff` and the `tiff`
  crate, files just written). The plan's 1-3 s was wrong; a single decode would save
  about 0.2 s.
- **A resident engine** (decision D5): process start to the first log line is 0.27 s and
  exit 0.37-0.44 s (`evidence/timeline-*.txt`); the device and pipelines start inside the
  passes in tens of milliseconds with the pipeline cache. A resident engine would save
  about 0.7 s of an 18 s render, against a process-model change and round 2's Q1b.
  Cheaper: the desktop could stop waiting for the process to exit once the engine has
  written and closed its outputs (0.4 s).
- **The integrated Radeon as extra compute** (decision D4): on the same 24 planes it
  folds in 99.8 s against 36.5 s on the CPU and 8.8 s on the RTX 5090 (round-3
  measurement). It shares the CPU's memory bandwidth, and every stage it could take is
  done three times faster by the CPU or eleven times faster by the discrete device. On
  this machine it cannot help. For machines without a discrete device the plan's R8
  stands: a timing probe on real planes, not the self-test's small frames, deciding the
  route.

## Not built yet

- **Q13 (R5), group checks on the device**: about 16 s of a first render (41-45 s);
  matters for captures the desktop did not follow and for imported stacks.
- **R3, the preview journal**: without decision D1 (pocketed) it only hits identical
  re-renders, which the desktop rarely asks for.
- **R4, R7, R8, R9, C2-C4**, round 2's **Q11, Q14-Q16**: as the plan describes.
