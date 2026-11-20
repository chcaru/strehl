# A7CR four-shot stacking performance, round 3: the stones that are left

**Status:** Plan, partly built (2026-11-19, night): R2, the lateral-colour measurement
(section 3.1's preview line) and C1 are on `main`; R1 was built, measured and not kept;
C0 is still the owner's (the Pi sees no SuperSpeed device at all). Results:
[implementation.md](../../experiments/a7cr-stacking-performance-2026-11-19/implementation.md).
Owner's decisions: D1, D2 and D3 pocketed; D4 yes where it helps (measured: not on this
machine); D5 answered by measurement (about 0.7 s a render).
**Date:** 2026-11-19.
**Owner's question:** what big performance stones are left unturned? Does running the
engine from WSL give any lift? Better I/O? Anything else, including new algorithms?
**Scope:** the capture rig (camera, Pi controller, uplink), `strehl-cli`, `strehl-gpu`,
`strehl-core`, the desktop's render and publication path. No code was changed except one
measurement script (`trace.py` now records page faults).
**Audience:** the owner, then an implementing agent. Each stage says what to change, why
the output cannot change (or that it does, as a decision), how to prove it, and what it
should save.
**Follows:** [round 2](2026-11-a7cr-stacking-performance-plan-2.md) and
[its results](../../experiments/a7cr-stacking-performance-2026-11-18/implementation.md).
Round 2's rules (its section 2) apply in full. Stage labels here (R, C) are plan-local;
allocate milestone rows before dispatch.
**Evidence:** [`experiments/a7cr-stacking-performance-2026-11-19/`](../../experiments/a7cr-stacking-performance-2026-11-19/results.md).

Labels: MEASURED, VERIFIED (read in the code or a log), DERIVED, ARGUED, UNVERIFIED.

---

## 1. Answers

**The largest stone is not in the stacker.** Since 15 November the camera has been
talking to the Pi at USB 2.0 speed. A four-shot plane takes 16.4 s where it took 7.1 s on
14 November, so the scarab capture took 53.6 minutes where the same rig would have taken
about 23 (MEASURED from the capture journals; VERIFIED in the Pi's kernel log). Every
render time in this document is small beside that.

**WSL: no.** The same engine, same source, same 24 planes, files on the distribution's
own disk:

| 24 planes of the scarab stack (MEASURED) | Windows | WSL2 (Debian 13) |
| --- | ---: | ---: |
| CPU route, cached | 36.3-36.6 s | 52.2-54.1 s |
| Default route (`auto`) | 8.8 s (GPU) | 55.6 s (no device: falls back to the CPU) |
| Kernel CPU time, CPU route | 33-35 s | 105-128 s |
| Output | `E37E8E6F...` | the same bytes |

WSL2 is a virtual machine. Its memory faults cost 2.4-3.3 times Windows' own, a blocked
thread takes 47 µs to wake against 0.8 µs, and the distribution has no Vulkan driver for
the RTX 5090 (NVIDIA ships CUDA and Direct3D 12 libraries there, not Vulkan). Captures on
a Windows drive would also be read through the `/mnt` bridge at 0.24-0.48 GiB/s against
10.8-13.7 GiB/s natively. A native Linux boot was not measured; the bound on it is that
the kernel is 7 % of a render's CPU time on Windows and none of the render's wall time
waits on it (section 3.3).

**Better I/O: not yet.** With the whole stack copied to the drive that reads 2.5 times
faster (C:, 14.6 GB/s against D:'s 5.7 GB/s), a later render took 19.4-19.8 s against
20.1-20.5 s (MEASURED). The fold is bound by one thread, not by the drive. After stage R1
removes that bound, the faster drive is worth about 2 s (DERIVED).

**The stacker itself: 40 to 50 % of a later render is still removable with identical
bytes,** in four stages that are plumbing, not arithmetic (section 6). Beyond that the
fold meets three floors that are close together on this machine: the device's own
kernels (5.4 s for 196 planes), the decoders (about 6.7 s) and the drive (3.5 s on C:,
8.9 s on D:).

**What exact arithmetic rules out.** Two ideas that would have been large do not survive
a reading of the merge (section 3.9): folding only the planes that are in focus at each
tile, and folding each plane as it arrives during the capture. Both would change the
bytes, for reasons that are part of the merge's quality, not accidents of the code.

**What is left outside exact arithmetic** is a draft tier: a small stored proxy of every
plane, stacked in about a second for display while the exact render runs. It is a product
decision (section 8, D3), not a speed-up of the photograph.

Ranked by time the owner would get back:

| # | Stone | Today (MEASURED) | After (DERIVED unless marked) | Stage |
| --- | --- | --- | --- | --- |
| 1 | Camera link at USB 2.0 | 16.4 s a plane; 53.6 min for 196 planes | 7.1 s a plane (MEASURED 14 Nov); about 23 min | C0, C1 |
| 2 | One thread copies every plane into upload memory | main fold 10.2 s | about 9 s on D:, about 7 s on C: | R1 |
| 3 | The device idles while the CPU finishes the fold, in both passes | 4.7 s tail, 2.0 s of the preview | about 3 s less | R2 |
| 4 | The preview pass is repeated on every render | 4.3 s of 20.5 s; about 40 % of a small stack's render | 0 when its inputs are unchanged | R3 |
| 5 | A first render's group checks run on the decoder threads | about 16 s of 41-45 s | about 2 s | R5 (round 2's Q13) |
| 6 | Each render is a new process; the desktop decodes the result again | about 1.1 s in the engine, 1-3 s in the desktop (ARGUED) | about 0.2 s and under 1 s | R4 |
| 7 | Fast route only on discrete Vulkan devices; 21.6 GB of host memory for 8 planes | every other machine runs the CPU route, 4-9 times slower | measured choice of route; memory by budget | R8 |
| 8 | After C0, the uplink and the queue pace the capture | 0.3-0.6 s a plane waiting, 1.5 s hold with error correction | under 0.5 s | C2-C4 |

---

## 2. Rules for the implementer

Round 2's section 2 holds: the five reference hashes on both routes after every stage, the
A7C II byte-freeze 5/5, no reassociation, switches declared in
`scripts/check-defaults.py`, scheduling never arithmetic, cold and cached numbers quoted
separately. Additions:

- **Time the stage you are replacing first.** Every "today" figure below came from
  `STREHL_FOLD_TRACE=1`, `STREHL_GPU_PROFILE=1` or `trace.py`; quote the same line after.
- **A purged file cache is the cold case.** `purge.py` in the evidence folder drops a
  folder's files from the Windows cache without reading them.
- **A decision is not a stage.** Anything in section 8 changes bytes or the product and
  waits for the owner.

---

## 3. Measurements

Host: Ryzen 9 9950X3D (16 cores, 32 threads), 64 GB, RTX 5090 (32 GB), integrated
Radeon; D: Samsung 980 PRO 2 TB (captures), C: WD SN8100 2 TB; Windows 11 26200, power
plan Balanced. Engine: `strehl 0.1.0-alpha.6 (8571ac879b50-dirty)`, built from the
working tree that was committed as `8372ad1a8`. Stack: the scarab capture,
196 four-shot planes, 784 format-1 archives, 47.7 GiB. Host idle (0-5 % CPU) before each
run; one run at a time. Every render below wrote its reference bytes.

### 3.1 A later render today (MEASURED, `full-a`, 20.5 s, stack on D:)

| Phase | Seconds | CPU cores busy | Device busy | What happens |
| --- | ---: | ---: | ---: | --- |
| Start to device ready | 0.9 | 4 | - | first log line at 0.26 s; Vulkan device and pipelines 0.54 s |
| Preview fold, 25 planes | 2.2 | 8 | 26 % | 0.93 s of it waiting for decodes (cold files, 246 ms for a first member) |
| Preview collapse and CA measurement | 2.0 | 22 | 4 % | CPU collapse, then `measure_mosaic` |
| Main fold, 196 planes | 10.2 | 17 | 59 % | below |
| Reference tiles beside half-stacks | 2.1 | 17 | 6 % | half-stacks finished on the CPU (2.0 s) |
| Collapse, restoration, write | 2.6 | 13 | 6 % | collapse 0.6 s, restoration 1.5 s, write 0.15 s |
| Exit | 0.3 | | | |

Process: 283 s user, 21 s kernel, 54.4 GB read, 14.2 million page faults, 30.2 GB peak
private memory.

The main fold's 10.2 s on the in-order fold thread (`STREHL_FOLD_TRACE`):

| Fold thread | Seconds | Per plane |
| --- | ---: | ---: |
| Copying each plane into upload memory (`stage`) | 4.86 | 24.8 ms |
| Waiting for decodes | 2.33 | 11.9 ms |
| Submitting the fold | 1.27 | 6.5 ms |
| Totals read back at the end | 1.17 | once |
| Probe round trip | 0.50 | 2.5 ms |

Meanwhile sixteen decoder threads decode for 112.7 s and sit idle for 25.4 s; a file
costs 144 ms there against 83-88 ms alone (section 3.3's codec bench).

### 3.2 The faster drive (MEASURED, `c-later-1..3`, files purged from the cache before each)

| Later render | D: (980 PRO, 5.7 GB/s) | C: (SN8100, 14.6 GB/s direct) |
| --- | ---: | ---: |
| Wall | 20.1-20.5 s | 19.4-19.8 s |
| Main fold | 10.2 s | 9.9-10.2 s |
| Fold thread waiting for decodes | 2.33 s | 2.20-2.35 s |
| Reader-seconds for 50.5 GB | 26.5 | 10.4-10.8 |

The readers finish in 40 % of the time and the fold does not move.

### 3.3 Windows against WSL2 (MEASURED)

`osbench.rs`, one source file, standard library only, built with the same compiler on
both sides:

| Primitive | Windows | WSL2, ext4 on its virtual disk | WSL2, Windows drive (`/mnt/c`) |
| --- | ---: | ---: | ---: |
| First touch of a page, 1 / 4 / 16 threads | 207 / 306 / 608 ns | 537 / 724 / 2,015 ns | |
| Blocked-thread round trip | 0.77 µs | 47.8 µs | |
| Direct read, 4 threads | 13.6 GiB/s | 13.1 GiB/s | 0.48 GiB/s |
| Cached read, 1 / 4 threads | 13.4 / 21.2 GiB/s | 34.7 / 39.4 GiB/s | 0.24 / 0.45 GiB/s |
| Open, read 64 KiB, close | 13 µs | 1.6 µs | 1,485 µs |
| One-thread decode, format 1 / format 2 (same 8 files) | 82.8 / 94.5 ms | 73.2 / 89.3 ms | |

Linux's file cache and cheap opens are real, and a single decode is 5-12 % faster there
(DERIVED: about 3 ms of it is the cached read of a 63 MB file; ARGUED: most of the rest
for format 1 is Zstd's assembly decoder, round 2's Q17). The engine does not live on
those: it bypasses the cache for cold files, opens about a thousand files a render, and
pays for memory faults and thread hand-offs, where the virtual machine is worse. The whole engine, section 1's table: 44-50 % slower on the CPU
route, and `STREHL_GPU_FOLD=on` fails with "vulkan drivers/libraries could not be
loaded" (VERIFIED: `/usr/lib/wsl/lib` holds CUDA, Direct3D 12 and encoder libraries, no
Vulkan driver; the engine requests `wgpu::Backends::VULKAN` only, `context.rs:102`).
Mesa has a Vulkan-on-Direct3D-12 layer; it was not installed or tested, and it would sit
on top of the same Windows driver the native route already uses. The virtual machine
also gets half the host's memory by default (30 GB here), just under a full render's
peak on Windows (30.2 GB).

What a native Linux boot could gain is bounded from the Windows side: 21 s of kernel
time in 304 s of CPU (7 %), 14.2 million page faults at 0.2-0.6 µs (3-9 s of that CPU),
and no phase of section 3.1 waiting on either. ARGUED: a few per cent, not measured.

### 3.4 Small stacks and fixed costs (MEASURED)

| Render | Wall | Peak private memory | Passes |
| --- | ---: | ---: | --- |
| 196 planes | 20.5 s | 30.2 GB | preview (25 planes) 4.9 s, final 15.0 s |
| `--limit 24` | 8.8 s (11.0 s with the device profiler on) | 24.7 GB | with the profiler: preview (all 24) 4.6 s, final 5.8 s |
| `--limit 8` | 8.1 s | 21.6 GB | preview 3.0 s, final 2.0 s, final again 2.6 s |

- The preview's stride is `(RAW files / 32).clamp(1, 8)` (`merge_cmd.rs`,
  `stride_for`): a stack under 32 RAWs is folded twice in full. `--limit 24` counts RAWs,
  so it shows that case; a real 24-plane four-shot capture has 96 RAWs and previews 8
  planes.
- When the depth measured during the fold is unusable ("only 1789 of 235224 cells show a
  focus peak"), the engine renders a third time without the restoration. The rig's
  6-plane test stacks were this case.
- Memory does not follow the stack: 21.6 GB of private memory for eight planes, and
  14.0 GB of device memory at 24 (`v2-on-f1-gpu-l24`, round 2's run log).

### 3.5 Other devices (MEASURED, experiment build)

With the NVIDIA driver hidden from the Vulkan loader (`VK_LOADER_DRIVERS_DISABLE=*nv*`)
the product refuses the integrated Radeon: "GPU fold requires a discrete GPU"
(`context.rs`, one comparison). A throwaway build that skips the comparison folded the
24 planes on the integrated device and wrote **the reference bytes** (`E37E8E6F...`), so
another vendor's driver passes. It took 99.8 s against 36.5 s for this machine's CPU
route and 8.8 s on the RTX 5090: this integrated device is the desktop processor's
display adapter, and a 16-core CPU beats it. Which route is faster is a property of the machine, not of the
device's type.

### 3.6 The device's time (MEASURED, `STREHL_GPU_PROFILE=1`, main pass, 24 planes)

27.7 ms of kernels per plane, 5.4 s for 196 planes: gather 9.2 ms (33 %), accumulate
4.0, assemble 2.9, hull 2.6, expand 2.0, the gate-floor probe's noise 1.8, the rest under
1 ms each. Round 2's Q16 lists the candidates; the probe is new information (section
3.9).

### 3.7 The capture (MEASURED from `events.jsonl` of every run; `capture-cadence.py`)

| When | Four-shot `capture()` at 0.6 s shutter | Fourth RAW after the third | Plane period |
| --- | ---: | ---: | ---: |
| 13-14 Nov, 14 runs | 5.82-6.00 s | 1.09-1.17 s (the camera's own cadence) | 7.0-7.3 s (four runs on 14 Nov) |
| 15-19 Nov, 6 runs incl. scarab | 14.5-15.0 s | 3.06-3.22 s (39-41 MB/s) | 15.9-17.5 s |

In a fast run the first RAW is complete 0.40 s after the camera offers it (314 MB/s);
in the slow runs every RAW takes 3.1 s and the camera has all four buffered by 5 s. The
Pi's kernel log (`dmesg`, read-only, `pi-usb-check.py`) says why:

| Port | Speed | Device | Enumerations | First to last (UTC) |
| --- | --- | --- | ---: | --- |
| 2-1 | SuperSpeed | ILCE-7CR | 3 | 13 Nov 22:45 to 14 Nov 18:56 |
| 1-1 | high-speed (USB 2.0) | ILCE-7CR | 14 | 15 Nov 22:44 to 19 Nov 18:53 |
| 1-1 | full-speed (12 Mbit/s) | ILCE-7CR | 6 | 19 Nov |

ARGUED: port 1-1 is the USB 2.0 half of the same connector as 2-1 (on 12 November the
camera's powered-off identity enumerated on 1-1 and, ten seconds later, the powered-on
camera on 2-1). So the cable is still in a USB 3 port and the SuperSpeed pairs no longer
link; six enumerations at 12 Mbit/s say the
link is marginal even at USB 2.0. ARGUED: cable, connector seating or orientation, or
something added in line on 15 November. Not software: the rate is the same in single-shot
and four-shot runs and across controller restarts.

With the link restored the camera sets the pace: about 1.75 s to the first RAW, then
shutter + 0.55 s for each further one, 0.7 s of fixed waits, and 1.26 s of focus move and
settle. Then the next bounds appear (read in the controller and measured from the
journals and receipts by a code dive, not by me): the upload queue admits a four-shot
group only when empty (`transfer.rs`, `MAX_PENDING_FRAMES = 4`), which cost 0.3-0.6 s a
plane on 14 November; the uplink carries 245-270 MB a plane over Wi-Fi that measured
29-41 MB/s, about what a 7 s plane needs; and with error correction on, the hold for the
PC's verdict was 1.46-1.64 s a plane on 19 November.

### 3.8 The desktop around the engine (VERIFIED by a code dive unless marked)

- One engine process per stack, two passes inside it. Nothing from the `follow` checker
  survives except its journals; the closing stack decodes everything again.
- Publication after the engine exits (`jobs.rs:1194-1245`; the two decodes checked by
  me): the 722 MB float master is decoded whole (`load_tiff`, which per the dive tests
  every sample for finiteness on one thread); the 361 MB result is decoded whole and
  dropped (`validate_tiff`); then the result is decoded again for
  the 1,600 px overview, and Edit loads the master again. Not timed anywhere. MEASURED
  bound: engine totals leave 1.7-1.8 s of a desktop render for start, scan, publication
  and exit together.
- Every Adjust control is an engine argument: noise gate, scales, coarse power, fine
  ramp, exposure, fringing, coverage crop, resampler, first-N. Each change restacks in
  full, both passes. Edit's adjustments apply live from the master.
- Polls on the capture-end path: 250 ms (`follow`), 200 ms (desktop follower), 70 ms
  (scan pick-up), 50 ms (engine exit). `four_shot_planes` parses the journal three times
  in the desktop and again in the engine. The connection thread re-verifies up to 32
  registered runs every 5 s, stat-ing every RAW.
- The Execution panel still says "CPU stacking · GPU display" (`controls.rs:138`).

### 3.9 What the merge's arithmetic allows (VERIFIED by a code dive; formulas at `fold.wgsl:461-511`, `pyramid.rs:3429-3457`, `:3994-4005`)

- A plane's contribution is a pure function of that plane, its placement and global
  parameters. Nothing compares a plane with the running total.
- The selecting weight is exactly zero where a plane's evidence is under the noise
  floor. But four other sums take every plane at every pixel regardless of weight: the
  plain sum of coefficients (`usum`), the ensemble sums, and the level-0 minimum and
  maximum. The output is the all-plane mean wherever no plane clears the gate (86 % of
  the finest band's coefficients in the 8-plane run's log) and is clamped to the
  all-plane range everywhere.
- The sums are f32, in plane order, in one canonical chunk; two ranges folded
  separately do not combine to the same bits. A prefix can be resumed exactly.
- Every gather needs the final alignment solve: its reference is the middle plane and
  its cover scale is fitted over the whole map (`align_cmd.rs:1757`, `:2245`), and red
  and blue need the preview's CA refinement.
- The gate-floor probe (the "noise" kernel, 1.8 ms a plane) reads no image samples: its
  inputs are noise seeded by the plane's index, the plane's placement and template
  metadata (`gatefloor.rs`, `fold.wgsl:1004-1032`). Its result per plane can be kept
  with the map.
- The preview hands the final pass two things, both held in process statics and never
  kept on disk: the CA residual (two channels' translation and scale, about 100 bytes)
  and 643 predicted tiles (a hint only; a miss is gathered as before).

---

## 4. Findings

**F1. The capture is 2.3 times longer than it was, for a physical reason.** Section 3.7.
Nothing in the software noticed: the controller already walks the device's sysfs entry
(`ptp.rs:850-868`) and could have read its speed.

**F2. The fold thread, not the drive or the device, bounds the main fold.** It copies
482 MB per plane (4.86 s), and that copy also competes with sixteen decoders for memory
bandwidth: files decode 1.6 times slower inside the fold than alone. This is round 2's
Q5d, not built; today's measurements make it the first engine stage.

**F3. The device is idle for 6.7 s of a 20.5 s render** (preview collapse, tail), while
16-22 cores do work whose device form is already specified (round 2's Q7).

**F4. The preview pass is 21 % of a large render and about 40 % of a small one, and its
whole product is 100 bytes.** Round 2 declined to keep it on disk because a hand-listed
key could miss an input. Section 6's R3 keys it on everything the process can see
instead.

**F5. Exactness forbids the two large shortcuts.** A depth-sparse fold would drop planes
from the all-plane mean that sets the noise of every flat region, and from the range
clamp. Folding at arrival would gather with placements that the final solve then moves.
Neither is a plumbing limitation.

**F6. WSL and a faster drive are not levers today** (sections 3.2, 3.3). The drive
becomes one after R1.

**F7. The fast route is narrower than "all machines".** It needs a discrete device by
policy, Vulkan by construction (pass-through SPIR-V and f64, so no Metal), about 14 GB of
device memory and over 20 GB of host memory at any stack size. The bit-identity itself
is portable (section 3.5).

**F8. Around the engine, a render pays for a new process, a second and third decode of
its own output, and a full restack per Adjust change.** Individually 0.3-2 s; together
they are most of what is left once the fold is near its floors.

**F9. After the USB link is restored, the capture is paced by the camera, then by the
uplink and the single-group queue.** The exposures are 2.4 s of a 7.1 s plane.

---

## 5. Budget

Later render of the scarab stack, seconds. "Today" MEASURED; the rest DERIVED from
section 3 and round 2's stage estimates.

| Line | Today, D: | After R1 | After R2 | R3 hit | R4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Start, device, pass set-up | 1.1 | 1.1 | 1.1 | 1.1 | 0.3 |
| Preview pass | 4.3 | 4.3 | 3.3 | 0 | 0 |
| Main fold | 10.2 | 9.0 | 9.0 | 9.0 | 9.0 |
| Tail | 4.7 | 4.7 | 2.7 | 2.7 | 2.7 |
| Exit | 0.3 | 0.3 | 0.3 | 0.3 | 0 |
| **Later render, stack on D:** | **20.5** (the lines sum to 20.6) | **19.4** | **16.4** | **13.1** | **12.0** |
| **The same, stack on C:** (main fold 7.0 after R1) | **19.6** (MEASURED) | **17.4** | **14.4** | **11.1** | **10.0** |

What bounds each line afterwards:

- Main fold: on D: the drive (50.5 GB at 5.7 GB/s is 8.9 s). On C: the decoders (107-113
  core-seconds on 16 threads, 6.7-7.0 s, less if R1's saved copies give them back the
  memory bandwidth), then the device at 5.4 s. Round 2's Q16 is what moves the device.
- Tail: the restoration (1.5 s), reference tiles, the 722 MB read-back and the write.
- A first render adds group checks: 16 s today, about 2 s after R5.
- Capture end to photograph in the desktop is a later render with a preview miss, plus
  publication: 27.7 s MEASURED on 19 November with an empty engine cache, about 22 s
  with a warm one; about 16 s after R1, R2 and R4, about 14 s with the capture on C:.

---

## 6. Stages

In build order. C stages are the capture; R stages the PC.

### C0. Restore the camera's USB 3 link (owner, hardware)

Re-seat and flip the USB-C plug at the camera, try the cable that was in use on 14
November, and remove anything added in line on 15 November. Check with
`python experiments/a7cr-stacking-performance-2026-11-19/pi-usb-check.py` after switching
the camera on: the newest ILCE-7CR line must say SuperSpeed on port 2-1. Saves 9.2 s a
plane, 30 minutes on a 196-plane stack.

### C1. The controller reports the link

At connect, read the device's `speed` (the sysfs walk exists, `ptp.rs:850-868`); put it
in the controller's state and each run's journal with the measured MB/s per RAW; the
desktop's Capture screen warns below 5,000 Mbit/s before a stack starts. Test: a scripted
camera at a forced low speed shows the warning. This is the gate that would have caught
F1 on the first frame.

### R1. The fold thread only submits (round 2's Q5d and Q6's remainder)

Decoders write each member's samples straight into persistently mapped upload buffers
(a ring sized to the decode window), using the row-buffered predictor that already keeps
its working rows in ordinary memory, so nothing reads the mapped memory back. `stage`
becomes a hand-off. Bytes: the same samples reach the same kernels in the same order.
Proof: the reference set; `STREHL_FOLD_TRACE` shows `upload (stage)` near zero and the
device above 85 % busy. Expected: main fold 10.2 s to about 9 s on D: and about 7 s on
C:. Risk: device memory for the ring (18 planes are 8.7 GB; the window may need to
shrink on smaller devices, which is R8's budget).

### R2. The device finishes what it folded (round 2's Q7), in both passes

Round 2's Q7 text stands: resolve, collapse, `absorb` and the hull clamp as kernels
mirroring `finish_with_report` operand for operand; read back twelve planes and the
halves' tile crops instead of 7.5 GB of accumulators. Additions from today's trace:

- The preview's collapse is the same kernels.
- `separate_bilinear` (`ca-refine.rs:225`) builds a 60 MP RGB image with a nine-tap loop
  that branches on site colour and bounds for every tap. Four specialised interior loops
  (one per site parity), each adding the same terms in the same order, with the generic
  loop kept for the border, are bit-identical by construction. Profile `measure` itself
  before touching it (round 2's Q10 note).

Check mode: `STREHL_COLLAPSE_CHECK=1` compares the device's planes with the CPU's bit
for bit, and fails on a shifted kernel (mutation). Expected: about 2 s of the tail and
about 1 s of the preview.

### R3. Keep what the preview measured

Journal the CA residual and the tile plan beside the warp map. The key answers round 2's
objection by not listing inputs: it is a SHA-256 over everything the preview pass can
see, with a short list of exclusions, so a forgotten input makes a miss, never a wrong
photograph.

- In the key: the build identity; every resolved merge option; every declared `STREHL_*`
  variable's value (the set is closed by `scripts/check-defaults.py`); the stride; the
  SHA-256 of each preview member's archive (from receipts or the verified record); the
  map file's bytes; the group-journal lines of the preview's planes.
- Excluded, each with a test that it cannot change a sample: output paths, progress
  flags, worker counts, the trace switches.
- On a hit the final pass starts at once. Also journal the last render's actual 400
  tiles, so the fold captures all their crops and the 10-frame regather goes.
- `STREHL_PREVIEW_CHECK=1` runs the preview anyway and exits 1 unless the residual is
  bit-identical to the journalled one. Mutation: perturb one journalled value. The
  desktop sets the check on a schedule (say every 20th hit) so drift cannot hide.

Expected: 4.3 s of a large render, about 3 s of a 24-plane one, whenever the stack, map
and merge settings are unchanged. An Adjust change still misses; decision D1 is what
turns those into hits.

### R4. A resident engine and one decode of the result

- The desktop keeps one engine worker alive between renders, with its device, pipelines
  and parsed journals. This needs round 2's Q1b first: the preview's products and the
  stride are process statics today (`merge_cmd.rs:9291-9296`) and must belong to a
  render. Saves start, device and exit (about 1.1 s a render).
- The checker hands the closing stack to that worker instead of a new process, and the
  capture-end path wakes on the journal's change instead of four polls.
- Publication: instrument it first (it has no timings). Then have the engine write, with
  each output, its length, SHA-256 and a finite flag computed from memory it already
  holds; the desktop checks length and hash in one streamed, multi-threaded pass and
  decodes each file once, sharing the master with Edit. Expected 1-2 s (ARGUED).
- `four_shot_planes` parsed once per scan; `verify_completed` on a change, not a timer.

### R5. Group checks on the device (round 2's Q13, unchanged)

Still the largest item of a first render without journals: about 16 s of 41-45 s. It
matters for captures taken without the desktop following them and for imported stacks.

### R6. Hot captures on the fastest drive (after R1; decision D2)

The receiver stores new runs on the fastest local drive and moves a run to the archive
drive when it has not been opened for some days (or on request). Worth about 2 s per
render once R1 is in, nothing before. Bytes untouched; the move must keep receipts and
journals valid (they are relative to the run folder).

### R7. Device kernels (round 2's Q16), with two cheap additions

- Keep each plane's gate-floor result with the map (key: map bytes, refinement, the
  probe's configuration, build). Saves the "noise" kernel and its round trip, about
  0.35 s per fold, and lets two planes be in flight.
- The hull's minimum and maximum inside the gather that writes the sample.

Measure each with `STREHL_GPU_PROFILE` before and after; round 2 expected about a fifth
of the device's time in total.

### R8. Other machines

- **Choose the route by measurement.** Let any Vulkan device with the required features
  take the self-test; add a timing probe to it (a few planes' kernels against the same
  planes on the CPU) and record the faster route with the self-test's result. Today's
  rule would refuse a laptop's capable integrated device and would accept a discrete
  device slower than the CPU.
- **Memory by budget.** The decode window, upload ring, reference-crop capture and
  retained planes sized from free host and device memory (round 2's supervisor, Q11);
  the accumulators' layout by round 2's Q14. Target: an 8-plane stack in under 8 GB.
  Scheduling only; the canonical chunks stay derived from geometry.
- **The CPU route** stays round 2's Q15. It is what a Mac runs (no f64 and no
  pass-through SPIR-V on Metal), so it deserves its profile before more device work is
  done for machines that already have a fast route.

### R9. Small stacks

When the preview folded every plane and its depth tap is unusable, render without the
restoration at once; the decision reads the same energies the final pass would have
measured, so it is the same decision. Saves the doomed pass (2.0 s of 8.1 s on eight
planes). For larger stacks the retry stays.

### C2-C4. The capture after C0

- **C2. Uplink.** Wire the Pi if a cable can reach it, or run two uploads at once; drop
  the upload thread's second read and SHA-256 of a file the controller already hashed
  (`transfer.rs:250`, `:405`). This also shortens the error-correction hold, which waits
  for the PC to hold each RAW.
- **C3. Queue of two groups.** Let the next group's shutter go while one group is still
  uploading (8 pending frames; the Pi has the memory). Saves the 0.3-0.6 s wait.
- **C4. Light.** Each 0.1 s off the shutter is 0.4 s a plane. More light at the same
  aperture is the only large capture lever left after C0; a strobe would remove 2.4 s of
  a 7.1 s plane. UNVERIFIED on this rig.

The settle time (500 ms; 100 ms measured 0.5 s faster) is a vibration parameter and
needs its own image test before anyone shortens it.

---

## 7. Measured or read, and not worth building

- **Running the engine in WSL2**: slower in every route (section 3.3).
- **Moving captures to a faster drive now**: under 1 s (section 3.2). See R6.
- **A depth-sparse fold and folding at arrival as exact changes**: ruled out by the
  merge (section 3.9, F5).
- **Decoding format 2 on the device, on this machine**: the CPU supplies decoded planes
  in about 6.7 s and the device needs 5.4 s for its own kernels; moving the decode onto
  the device adds serial work per lane to the bound side (ARGUED; not measured). It is
  an option for machines with few cores and a strong device.
- **A fold checkpoint for tail-only changes**: only exposure, automatic exposure,
  coverage crop and the confidence map would hit it (section 3.8), and Edit already
  applies exposure live from the master. Not worth 2-7 GB per stack.
- **Memory-mapped reads, deeper read-ahead, more decoder threads**: round 2 measured
  each; nothing here changes those results.

---

## 8. Decisions for the owner

- **D0. The USB link** (C0). What changed at the rig between 14 November 10:56 and 15
  November 14:44 local time?
- **D1. Measure the lateral-CA residual under the default merge settings whatever Adjust
  says.** The residual is a property of the lens and the stack's geometry; measuring it
  from a preview merged with the default configuration makes it independent of the
  Adjust controls, so with R3 every Adjust restack skips the preview (about 4.3 s of
  20 s, about 40 % of a small stack). Default renders keep their bytes; renders with
  non-default merge settings change slightly (the residual they apply would come from
  the default-settings preview). ARGUED that this is at least as correct; UNVERIFIED on
  images.
- **D2. Hot captures on C:** (R6). C: has about 500 GB free, room for ten stacks of this
  size.
- **D3. A draft tier.** `follow` already decodes every plane during the capture. It
  could store a proxy of each assembled plane at a quarter of the output's width and
  height (2376 x 1584 RGB, about 23 MB a plane, 4.4 GB for this stack; at an eighth,
  1.1 GB). A proxy stack is a sixteenth of the samples and folds on the device in about a
  second with its read. That would give a picture that builds during the capture, a picture
  about a second after the capture ends, and Adjust previews in a second or two, each
  replaced by the exact render when it lands. A draft is a true stack of a smaller
  capture, not a downscale of the final photograph: its finest band is the full render's
  second band, so it shows framing, coverage and coarse behaviour and cannot show the
  finest band's gating. UNVERIFIED how well it predicts the final; build a
  prototype and compare before committing the desktop to it.
- **D4. Let non-discrete devices try** (R8's first item).
- **D5. A resident engine process** in the desktop (R4): a process-model change, with
  round 2's Q1b as its precondition.

---

## 9. Risks and what was not verified

- The USB cause is inferred from the kernel log and the rates; nobody has looked at the
  cable. If re-seating does not restore SuperSpeed, test the camera on the Pi's other
  USB 3 port and with a second cable before suspecting the camera.
- R1's "about 7 s on C:" assumes the decoders speed up when the copies stop competing
  with them; if they do not, the fold is 7.0 s there instead of about 6.7 s. On D: the
  drive hides the difference.
- R3 is only as safe as its exclusions; each needs its test, and the check mode must run
  in the reference harness.
- Section 3.8 and the controller details in 3.7 come from code dives by subagents; I
  re-read the publication path and the preview driver only. Re-read the cited lines
  before building on them.
- Publication's cost is bounded (under 1.8 s with start and exit) but not timed; the 1-3
  s after "saved" is ARGUED from file sizes.
- The integrated-device result is one device and one stack size. How a current laptop
  device compares with its own CPU is UNVERIFIED; R8's timing probe exists so that
  nobody has to guess.
- Native Linux, large pages, and the Balanced power plan against High performance were
  not measured. The first two are bounded by section 3.3; the third is a one-run
  experiment for the owner's machine.
- D3's proxy sizes and times are DERIVED from plane geometry and the device's measured
  per-plane time scaled by area; nothing was prototyped.

---

## 10. Evidence

In [`experiments/a7cr-stacking-performance-2026-11-19/`](../../experiments/a7cr-stacking-performance-2026-11-19/results.md):
`evidence/runs.txt` (every traced render: command, environment, wall, CPU, reads, page
faults, hash), `evidence/engine-traces.txt` (fold and device traces per run),
`evidence/osbench-windows.txt`, `evidence/osbench-wsl.txt`, `evidence/wsl-engine.txt`,
`evidence/codec-bench-windows-wsl.txt`, `evidence/capture-cadence.txt`,
`evidence/pi-usb-check.txt`, and the scripts that produced them.
