# A7CR capture and storage, round 4: the pipeline, the focus step and the bytes

**Status:** Proposal (2026-11-20). Nothing here is built. Investigation and experiments
only; no product code changed.
**Date:** 2026-11-20.
**Owner's questions:** what else speeds up capture end to end, first-time stacking and
follow mode included? Is the camera driver slower than the camera's own focus bracketing,
and would a lower-level control API help? How can stacks take less disk, with up to 6000
images a stack and every gigabyte counting, losslessly or otherwise?
**Scope:** the capture rig (camera, Pi controller, uplink, receiver), the archive format,
the engine only where it reports or reads. Stage labels (K, F, A, E) are plan-local;
allocate milestone rows before dispatch.
**Audience:** the owner, then an implementing agent.
**Follows:** [round 3](2026-11-a7cr-stacking-performance-plan-3.md) and
[its results](../../experiments/a7cr-stacking-performance-2026-11-19/implementation.md).
**Evidence:** [`experiments/capture-pipeline-2026-11-20/`](../../experiments/capture-pipeline-2026-11-20/results.md)
(rig, focus step) and [`experiments/stack-storage-2026-11-20/`](../../experiments/stack-storage-2026-11-20/README.md)
(storage).

Labels: MEASURED, VERIFIED (read in the code or a log), DERIVED, ARGUED, UNVERIFIED.

---

## 1. Answers

**The camera link is fixed.** With the USB 2.0 extender gone the camera is on the
SuperSpeed port at 5000 Mbit/s and a RAW reaches the Pi in 0.4 s (VERIFIED on the rig).
A four-shot plane takes 7.3 s again (MEASURED).

**The driver is already at the lowest level.** It speaks Sony's PTP commands straight to
the camera over USB; there is no SDK or higher layer left to drop. What costs time is the
order the controller does things in. It polls where the camera sends events, waits for a
lens position readback that lags the lens by up to half a second, starts its settle time
only then, and will not move the lens or press the shutter until the last RAW of the
previous plane has been fetched. The camera needs none of that: it accepts a focus move
and the next shutter press with a RAW still inside it (MEASURED).

| One plane, 0.6 s exposures, 8 units a step (MEASURED) | Installed controller | Pipelined order, on the camera |
| --- | ---: | ---: |
| Four-shot | 7.3 s | 5.09 s (8 planes, 5.06-5.14) |
| One RAW a plane | 3.1 s | 1.54 s (10 planes) |
| Four-shot with error correction on | about 9 s (DERIVED) | 5.1 s if retakes are deferred (stage K3) |

The camera's own focus bracketing cannot be driven or timed over this link: the drive mode
offers none while pixel shift is on, and the two are separate drive modes, so it would not
give four-shot planes anyway (ARGUED). The comparison the owner had in mind is therefore
UNVERIFIED. What is measured: the camera itself spends 0.5 s on every
image beyond its exposure, which sets a floor of about 2.5 s plus four exposures for a
four-shot plane.

**The largest lever is the number of planes.** In the scarab stack a point's finest detail
stays within half of its peak for 14 planes. Rendering that stack from every second plane
loses nothing measurable where signal dominates (0.998-1.000 of the full stack's detail
energy), and from every fourth plane 2-3 % of amplitude, with crops at 200 % that cannot be
told apart (MEASURED, one subject). Half the planes is half the capture, half the disk and
a first render in 26 s instead of 42 s. The right step depends on magnification and
aperture, so the product should measure it from the stack and say so (stages F1-F3).

**Disk: lossless is nearly spent; the real saving is a calibrated tier.** Of a format-2
archive's sensor data, 81-92 % is the entropy of the sensor's own noise, which no lossless
method removes (MEASURED). A better predictor is worth 4-12 %, using neighbouring frames
3-4 % more at the price of archives that depend on each other, and recompressing the
embedded JPEGs exactly 1.8 %. Storing each sample to within half a noise sigma instead
(step of one sigma, k = 1) makes an archive 2.5-3 times smaller. A render from such frames
is indistinguishable from a render from frames with that much extra random noise added
(MEASURED with a placebo): detail contrast 1.0003, noise amplitude +0.2 to +0.5 %. It is
irreversible, so it is the owner's decision (section 8, D3).

**First-time stacking and follow mode** are small beside the capture: the photograph is
ready about 25 s after a 17-24 minute capture ends (27.7 s MEASURED on 19 November, before
round 3 took 2.8 s off the render). The capture itself is what follow mode
spends its time on, so everything above is the follow-mode answer. Two cheap items remain
for stacks the desktop did not watch (stages E1, E2).

What it adds up to for a scarab-sized stack (196 planes at 8 units, four-shot, 0.6 s):

| | Capture | On disk |
| --- | ---: | ---: |
| Today | 23.9 min (29 min with error correction) | 49.0 GB |
| Pipelined controller (K1-K3) | 16.7 min | 49.0 GB |
| and a step of 16 units (F) | 8.3 min | 24.5 GB |
| and the calibrated tier at k = 1 (A4) | 8.3 min | about 9.5 GB |

For 6000 images (1500 four-shot planes at this brightness): 3.0 h and 375 GB today; 2.1 h
with the pipelined controller; about 1.1 h and 190 GB at twice the step; about 72 GB of
that in the calibrated tier (DERIVED from the per-plane and per-file figures).

Ranked by what the owner gets back:

| # | Lever | Today (MEASURED) | After | Stage |
| --- | --- | --- | --- | --- |
| 1 | Focus step finer than the depth of field needs | 14 planes inside a point's fine-detail peak | half the planes: half the time, disk and render (MEASURED on scarab) | F1-F3 |
| 2 | The controller waits where the camera does not | 7.3 s a plane; 3.1 s single | 5.1 s; 1.5 s (MEASURED on the camera) | K1 |
| 3 | Noise stored exactly | 59.8 MB of sensor data a file | 19.8-22.4 MB at k = 1 (MEASURED) | A4 |
| 4 | Focus held for the PC's verdict | about 9 s a plane with error correction (DERIVED) | 5.1 s | K3 |
| 5 | One upload at a time, each file hashed twice, the journal resent whole | 5.4 s of uplink a plane; 14-155 GB of journal on a 6000-image stack (DERIVED) | 3.0-3.8 s a plane; kilobytes | K2 |
| 6 | Exposure time | 2.4 s of every 5.1 s plane | 1.2 s less a plane for each halving | K5 |
| 7 | Lossless coding short of the noise floor | 7.4-7.8 bits a sample | 4-12 % less, exact | A1, A3 |

---

## 2. Rules for the implementer

Rounds 2 and 3 hold for the engine: reference hashes on both routes, the A7C II
byte-freeze, switches declared, timings with host load. Additions for this round:

- **The controller's safety rules are not negotiable.** A shutter transition is marked
  uncertain before it is sent and never retried; a RAW is bound to its plane and journalled
  before another shutter; an unexpected file stops the run; focus is checked against its
  target for every group. The pipelined order changes when things happen, not which checks
  run. Each rule keeps a test that fails when the rule is removed.
- **The lab bridge is not product code.** `experiments/capture-pipeline-2026-11-20/ptp-lab/`
  has no validation and discards RAWs. Read it for the order of operations and the event
  codes; do not install it.
- **Qualify on the rig, on a structured subject.** A capture change is done when a real
  stack shows the period, every RAW on the PC with its SHA-256, and the engine's group
  checks (`strehl pixel-shift`: witness shift and z) no worse than a stack taken the old
  way on the same subject. The pencil on the stage today is too plain for that check.
- **Nothing irreversible happens to a stack without the owner asking for it, per stack.**
  Thinning and the calibrated tier write new files, verify them, and delete originals only
  on an explicit confirmation that names what is lost.
- **A report is not a change.** F1 must not alter a render's bytes.

---

## 3. Measurements

All in the evidence folders; the tables there carry ranges and controls. In brief.

### 3.1 The installed controller (MEASURED)

A plane is 7.3 s: 5.97 s in the bridge's `capture()`, 1.25 s for the focus step, up to
0.4 s of journal upload, capacity request and queue wait before the shutter. Inside
`capture()`: a 200 ms pause between half and full press, the four exposures, the last RAW
(ready 0.25 s after the group ends, 0.4-0.5 s to fetch) and a 250 ms idle check.

Each RAW is on the PC 1.36 s after the Pi has it: 0.4 s before the request (the upload
thread reads and hashes it a second time) and 0.95 s in it, at 54 MB/s on the wire. Raw TCP
over the same Wi-Fi link carries 58 MB/s on one stream and 69 MB/s on two. The Pi's four
cores are 37-46 % busy while a group uploads.

### 3.2 The camera (MEASURED with the lab bridge)

- Events exist for everything polled: image arrived (`c206`), image fetchable (`c201`,
  0.35 s later), focus result (`c218`). Reading all properties takes 6 ms.
- Image arrivals after a full press at 0.6 s: 1.11, 2.28, 3.39, 4.53 s; at 1/10 s: 0.57,
  1.39, 2.00, 2.65 s. About 0.5 s an image is the camera's own.
- The full press alone works in manual focus; the 200 ms pause buys nothing.
- A focus command's result event comes 0.20-0.25 s later whatever the distance. Live view
  shows the image settled 0.15-0.18 s after the command. The position readback the product
  waits for arrives at 0.28-0.67 s, unrelated to distance: it is the property refreshing.
  The product's 500 ms settle starts only then, so the first exposure begins 1.4 s or more
  after the lens arrived.
- A focus move sent at the fourth image's arrival, with the camera still reporting the
  group active and that RAW inside it, is accepted. So is the next full press. The RAW is
  fetched during the next group's first exposure and that group runs as any other.
- Sixteen groups with the shutter 0, 100, 300 and 1500 ms after the focus-result event:
  exposure 1 is as sharp as exposures 2-4 at every settle (0.998-1.010; a planted 0.5 px
  blur reads 0.976) and no more displaced (0.075-0.082 px rms at every settle, the
  1500 ms groups included).

### 3.3 The focus step (MEASURED on the scarab stack)

| | Fine detail | Mid detail |
| --- | ---: | ---: |
| Width of a 64 px tile's peak at half height, in planes of 8 units | 14.3 (12.2-16.4) | 26.4 |

| Render against all 196 planes | Every 2nd plane | Every 4th plane |
| --- | --- | --- |
| Detail energy where signal dominates (blurs 0.5-2.5 px) | 0.998-1.000 | 0.943-0.967 |
| Finest band, unblurred, in flat and in detail tiles alike | 0.89 | 0.54 |
| Edge crops at 200 % | same | same |

The second row is selected noise, not focus: a selecting merge keeps the largest of N
noisy coefficients, so the full stack's finest band carries more of it.

### 3.4 Storage (MEASURED; bits per sample of the 9600 x 6376 strip)

| | Scarab frames | Dark-background frames |
| --- | ---: | ---: |
| Format 2 today | 7.41-7.81 | 5.90-6.27 |
| Noise floor (no lossless method goes below) | 6.79-6.80 | 4.93-5.07 |
| Best predictor tried, archives independent (22 cross-colour taps, weights per tile) | 7.10-7.27 | 5.17-5.60 |
| The same with the group's earlier shots and the previous plane | 6.99 (one plane) | not tried |
| JPEG-LS, JPEG XL lossless | 7.45-7.79, 10-15 times slower to decode | 5.59-6.08 |
| Calibrated, k = 0.5 | 3.62-3.95 | 4.02 |
| Calibrated, k = 1 | 2.58-2.93 | 2.77 |
| Calibrated, k = 2 | 1.67-2.05 | 1.78 |

A file also carries 3.0-4.4 MB of camera JPEGs (a full-size one, a preview, a thumbnail),
5-9 % of a format-2 archive. JPEG XL's JPEG transcoding restores them byte for byte and
saves 1.07-1.14 MB a file. The raw values have no gaps, combing or masked pixels to
exploit. A per-pixel gain map, the one thing only a stack can know, is worth 0.4 %.

The calibrated quantiser is a table on the sample's own value: bins of odd width no wider
than k sigma under the product's noise model, restored at their middle; clipped samples
exact; no prediction, so an error cannot spread. On six repeated frames its added variance
is 0.82 of k^2 sigma^2 / 12 at k = 1 and the mean of the quantised frames carries no
signal-locked pattern (correlation 0.003 at most between halves).

Rendered (24 planes, default route), against the lossless render:

| | Calibrated k = 1 | Placebo: random noise of the same size |
| --- | ---: | ---: |
| Rms difference, flat tiles | 8.77 | 8.73 |
| Rms difference, detail tiles | 33.7 | 34.1 |
| Gradient energy, flat tiles (noise) | 1.0042 | 1.0040 |
| Gradient energy, detail tiles | 1.0003 | 1.0002 |

---

## 4. Findings

1. **Sequencing, not protocol, is the driver's cost.** 2.2 s of a 7.3 s plane is waiting
   that the camera does not ask for: 0.2 s pre-roll, 0.6 s of readback lag and settle
   beyond what was screened as needed, 1.2 s for the last RAW, 0.25 s idle check.
2. **The settle the product applies is three times what it says.** 500 ms after a readback
   that is itself 0.3-0.5 s late, then 0.3 s of pre-roll. Counted from the camera's
   focus-result event, 0 to 300 ms showed no effect on the first exposure in the screen.
3. **Error correction's hold is an uplink wait.** The verdict needs the fourth RAW on the
   PC; the hold is that RAW's 1.4 s lag plus the check. The engine already takes each
   plane's last complete group by plane number (`pixel-shift-cmd.rs`, `plane_groups`,
   VERIFIED), so a retake does not have to be the next group recorded.
4. **The uplink is enough if it is kept busy.** A pipelined plane puts 207-263 MB on the
   wire every 5.1 s (41-52 MB/s); the link carries 58-69 MB/s. One upload at a time with
   0.4 s of rehashing a file needs 5.4-6.5 s a plane and would fall behind.
5. **The journal upload is quadratic.** Harmless at 196 planes, 14 GB at 1500 four-shot
   planes, 155 GB at 6000 single shots.
6. **The stack was taken about twice as finely as its optics need,** and a selecting merge
   gets noisier in its finest band the more planes it selects from.
7. **A stack's bytes are mostly noise.** Lossless methods compete for the last 8-19 %;
   frames next to each other in time share almost nothing a coder can use, because what
   differs between them is the noise.
8. **Quantising below the noise is noise.** At one sigma the merge responds to it exactly
   as to random noise of that variance.

---

## 5. Budget (four-shot plane, 0.6 s; MEASURED unless marked)

| Part | Installed | Pipelined |
| --- | ---: | ---: |
| Press to first exposure | 0.30 | 0.12 |
| Four exposures and the camera's 0.5 s an image, to the fourth arrival | 4.4 | 4.4 |
| Last RAW ready, fetched, idle check | 1.2 | overlapped with the lens |
| Journal, status, capacity, queue room | 0.1-0.4 | off the capture thread |
| Lens: command to result event (readback today) | 0.45-0.67 | 0.28 |
| Settle | 0.5, then 0.2-0.3 more | 0.3 |
| **Plane** | **7.3** | **5.09** |

Plane time is about 2.5 s + 4 x exposure + settle (DERIVED from 3.2; 5.2 s at 0.6 s against
5.09 s measured). At 0.3 s exposures 3.9-4.0 s; at 1/10 s 3.2 s.

---

## 6. Stages

### K1. The pipelined plane (bridge and worker)

What: the order of section 3.2, with the product's checks.

- Full press without the 200 ms pause.
- Fetch each RAW when its ready event arrives; a fetch never gates the lens or the shutter.
- At the group's last image arrival (count the `c206` events against the shots asked for,
  and cross-check the buffer count property), send the next plane's focus target.
- Press the next shutter one settle after the focus-result event (`c218` with result 1).
  Check the position readback against the target on every property read during the group
  and require it equal by the group's end; a mismatch fails the group (retake), as
  "Focus changed within pixel-shift group" does today.
- Drop the 250 ms idle tail between planes; keep it at the end of the run.
- Bind files by the camera's own sequence (object info) so the previous plane's last RAW,
  fetched during this plane, cannot be mistaken for this plane's first.
- Take the per-plane status read, journal snapshot and capacity request off the capture
  thread (the journal is written locally before the shutter as now; its upload is K2's).

Shape: the bridge's `capture-host` returns when the group is over and its RAWs are on the
Pi. Either let it return at the last arrival with one RAW owed and let `focus` run with a
RAW pending, or give the bridge one command for "move, settle, shoot" that streams
`raw-ready` lines for whichever plane a RAW belongs to. The second keeps the timing in one
place.

Gates: the mock-link tests extended with a camera that holds a RAW across a shutter (must
bind it to the earlier plane), sends a fifth file (must stop), and never reports the target
position (must fail the group). On the rig: 5.1-5.3 s a plane at 0.6 s; 1.5-1.6 s single.

Saves 2.2 s of 7.3 s a plane (30 %); half of a single-shot plane.

### K2. Uplink that keeps up

- Two upload workers (the link carries 69 MB/s on two streams against 58 on one; the Pi
  has two idle cores).
- Hash once: the controller's capture-time SHA-256 is the one the upload sends
  (`transfer.rs:250`, `:405`).
- Send the journal's new lines, not the file (an append request on the receiver; whole
  file only at the start and the end).
- Admit a group by bytes in RAM, not by an empty queue: 8 to 12 frames, the tmpfs raised
  from 1 GB to 2 GB (the Pi has 3.8 GB free). The capture still stops and waits when the
  PC falls behind that far.

Gate: a 30-plane four-shot run of a bright scene with K1 holds its period with the queue
bounded; a throttled receiver makes the capture wait, not fail. Without K2, K1 is
uplink-bound at about 5.4-6.5 s a plane.

### K3. Error correction without holding focus

The controller goes on to the next plane. When a verdict asks for a retake, it finishes
the group in flight, returns to the failed plane through the approach move (as the first
plane is reached), retakes it, and continues from where it was. The journal records the
plane number with each group as now; the engine needs no change (finding 3). Two retakes
a plane and the 15 s fail-open stay.

Gates: the controller's error-correction tests with a verdict that arrives one group late;
a forced retake on the rig (`STREHL_FOLLOW_RETAKE_PLANES`) renders with the retaken group.
Open question for the rig: the lens's repeatability returning to a plane, measured as the
retaken group's fit against its neighbours.

Saves the hold: about 9 s to 5.1 s a plane for runs with error correction on.

### K4. Settle, qualified

After K1 the settle counts from the focus-result event. Default 300 ms until a stack of a
structured subject, taken once with 300 ms and once with 1500 ms, shows the engine's
witness shift and z statistics unchanged; then try 100 ms the same way. 200 ms of settle is
0.2 s a plane.

### K5. Light (owner, hardware)

Each halving of the exposure is 1.2 s off a four-shot plane. At 0.3 s a plane is about
4.0 s. Below about 0.3 s a bright scene's 260 MB a plane outruns the Wi-Fi link, and the
Pi's unused Ethernet port (110 MB/s) is the fix.

### K6. One RAW a plane outside pixel-shift mode (owner and implementer, a short test)

The 0.5 s the camera spends on each image was only measured in pixel-shift drive mode,
which single-shot planes use too (one shot of a group). The mode is a menu setting, not
writable over PTP, and `configure` requires it. UNVERIFIED whether ordinary single
shooting is faster; a ten-minute test with the menu switched and the check relaxed tells.

### F1. The stack reports its own focus step

The fold already measures a focus energy for every 8 px cell and plane for its depth map.
Keep those per-plane values for the finest band that is signal-dominated, and report for
the stack: the median width W of a cell's peak at half height, in planes, over cells whose
peak stands six times above their floor (the measure of `focus-step-study.py`); and the
factor W / 7, how many times finer than needed the planes are. W / 7.2 lost nothing
measurable on the scarab and W / 3.6 lost 2-3 %, so 7 is the conservative end; it is one
subject's evidence and the report should say so.

Report only: printed by `stack` and `follow`, shown by the desktop beside the finished
photograph and on the Capture screen as a suggestion for the next stack with the same
setup ("this stack's planes were 2.0 times closer than its depth of field needed; a step
of 16 would have taken half the time and half the disk"). Gate: bytes unchanged; the
scarab reports about 14 planes; a synthetic stack of known blur width reports it.

### F2. A survey before a long stack

Twelve to sixteen single RAWs at the finest step around the middle of the marked range
(25 s at 1.5 s each), checked on the PC with F1's measure, before the owner commits to
1500 planes. Uses the existing `capture_positions` command.

### F3. Render from, and keep, every Nth plane

`stack --every N` (a view: nothing deleted), so the owner can compare a half-density render
with the full one on any existing stack; and `strehl thin`, which after that comparison and
an explicit confirmation deletes the unused planes' archives and rewrites the journal and
receipts as `subset-run.py` does. Halves an oversampled stack that is already on disk.

### A1. Embedded JPEGs recompressed exactly

1.07-1.14 MB a file (1.8 %), byte-exact restoration kept. Measured with libjxl's JPEG
transcoding (BSD-3-Clause). Check the licence of whatever binds it before linking (some
Rust wrappers are GPL), or evaluate a permissively licensed Lepton implementation, which
was not measured here. Fits format 2 as a new chunk method.

### A2. Superseded groups

A retaken plane's earlier group stays on disk and is never read (`follow` reports the
count). Delete them when the run finishes with every plane complete: 250 MB a retake.

### A3. A better lossless predictor (format 3, lossless)

Least-squares weights over about 22 causal taps across the colours, per 512 px tile, with
the weights stored; format 2's block coder kept. Estimated 4-7 % off bright frames and
10-12 % off dark ones with archives still independent (the estimator's ideal code length,
side information charged). UNVERIFIED: speed. Gate before adopting: a later render's wall
time within 5 % of format 2's, and the gain realised by a real coder within 1 % of the
estimate. If the decode cost fails the gate, per-frame weights (3-5 %) are the fallback.

### A4. The calibrated tier (format 3, calibrated; owner's decision D3)

- The archive stores, per sample, the code of `quant.py`'s table and the table itself
  (code to value), so decoding depends on nothing outside the file. It records k, the
  noise parameters the table was built from and the SHA-256 of the restored ARW (the
  original with only its strip changed), which `verify` and `restore` check.
- Coding: first the existing predictor and block coder over the restored values; measure
  against JPEG XL's 2.93 bits a sample and the estimator's 2.58. A file is then 22-26 MB
  with its JPEGs kept, 20-22 MB without (decision D4).
- The engine's noise model gains the tier's variance, (w^2 - 1) / 12 at each level, read
  from the archive: one injected model, as the invariant requires. Gate: on a calibrated
  stack the green witness's fitted read noise and gain move by the predicted amounts.
- Per channel: blue's measured noise is 0.80-0.89 of the model, so its k is effectively
  8 % higher; either accept that or build the table per colour.
- Offered as an explicit action on a finished stack ("compact"), never during capture and
  never by default. It writes the new archives, decodes each against its recorded hash,
  re-renders nothing by itself, and deletes the originals only on confirmation.
- Qualification beyond this round: a whole stack, a second subject, the owner's eye on the
  finished photograph, and the placebo repeated on both.

2.5 to 3 times smaller. Renders also read that much less from the drive, which is the
bound of a later render's main pass on D: (DERIVED: several seconds of an 18 s render).

### E1. The receiver checks groups for every run

Run `follow` from the receiver for any run nobody is following, so a stack captured
without the desktop open still finds its group checks done. Turns most first renders
(41-45 s) into later renders (18 s).

### E2. Group checks on the device

Round 2's Q13, unchanged: about 16 s of a first render, for imported stacks.

---

## 7. Measured or read, and not worth building

- **Coding a frame against its neighbours** (the group's other shots, the previous
  plane): 3-4 % beyond the best single-frame predictor, for archives that no longer stand
  alone and a chain that one damaged file breaks. **A sensor gain map:** 0.4 %, and it
  needs 90-130 frames to pay for itself.
- **JPEG-LS or JPEG XL for the sensor data:** no smaller than format 2 on bright frames and
  10-15 times slower to decode.
- **Folding each plane as it arrives.** It would need placements that never change once
  made, the lateral-colour residual from the first planes only, and the first plane as the
  reference; three quality decisions to save about 20 s after a capture of many minutes.
- **The camera on the PC instead of the Pi.** Removes the uplink, which K2 already makes
  sufficient at this exposure, and needs a USB backend on Windows.
- **Calibrated compression on the Pi before upload.** It would cut the uplink 2.6 times,
  but it makes the loss happen at capture, before anything has been checked. Not without
  the owner asking for exactly that.
- **Dither in the quantiser.** Not needed up to k = 2 (worst bias of a mean 0.005 sigma).

---

## 8. Decisions for the owner

- **D1. Focus step.** Take the next stack at twice the usual step and compare? The
  evidence is one subject; F1 would make it a measurement on every stack.
- **D2. Thinning stacks already on disk.** Allowed after F1 and a side-by-side render,
  one stack at a time? It deletes planes.
- **D3. The calibrated tier.** Allowed at all, given the rule that the original ARW stays
  restorable? If so: k = 1 (2.5-3 times smaller, each sample within half a sigma, render
  noise +0.2 to +0.5 %) or k = 0.5 (half the size, within a quarter sigma)? Recommended:
  k = 1, as an explicit action on stacks that are finished.
- **D4. The camera's JPEGs inside compacted files.** Keep all three recompressed (2-3 MB of
  a 22-26 MB file), keep only the 1616 x 1080 preview and the thumbnail (0.2-0.4 MB), or
  drop them? The stack never reads them; the desktop's source-frame previews do
  (`source-preview.rs`, VERIFIED), and would show the small preview where they show the
  full-size JPEG now. Recommended: the small preview and thumbnail only.
- **D5. Error correction.** Is a retake that returns to the plane a few seconds later
  acceptable in place of holding focus? It is what makes error correction free.
- **D6. Light and network.** Can the exposure come down from 0.6 s? Can a network cable
  reach the Pi if it does?

---

## 9. Risks and what was not verified

- **Events and overlap were observed on one body, one firmware, one lens.** The product
  should fall back to today's order when an expected event does not arrive, and say so.
- **The settle screen is small** (four groups a setting, one target, an estimator that is
  not the engine's). K4 is the qualification.
- **The lab discards RAWs.** The pipelined period with the uplink in the loop is DERIVED
  from the link's measured rate, not run.
- **Error-correction timing is DERIVED** (it was off on the rig today); lens repeatability
  on a return move is unmeasured.
- **The focus step evidence is one stack.** A different magnification or aperture changes
  the depth of field; F1 exists so that nobody has to trust this stack's number.
- **Calibrated tier:** 24 planes of one stack rendered; ISO 100 only; the table is only as
  right as the noise model; irreversible. A3's and A4's coders are estimates until built.
- **The camera's built-in bracketing was not timed.**
- **Journal sizes for 6000-image stacks are extrapolated** from 196 planes.

---

## 10. Evidence

- `experiments/capture-pipeline-2026-11-20/results.md`: rig measurements, the lab bridge
  and its logs, the settle screen, the focus-step study and the subset renders.
- `experiments/stack-storage-2026-11-20/README.md`: byte budget, raw statistics, the
  floor, single-frame and cross-frame coders, the calibrated quantiser, the render from
  calibrated frames and its placebo.
- Engine build for every render: `13fed04c0`; the full-stack and 24-plane renders
  reproduced their reference bytes (`02A6C8C2...`, `E37E8E6F...`).
