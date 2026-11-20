# Capture pipeline and focus step, 2026-11-20: measurements

Evidence for [the round-4 plan](../../docs/proposals/2026-11-a7cr-capture-and-storage-plan-4.md).
Investigation only: no product code was changed and nothing was installed over the
controller. The storage half of the round is in
[`../stack-storage-2026-11-20/`](../stack-storage-2026-11-20/README.md).

Rig: ILCE-7CR, FE lens at f/5.6 (EXIF), ISO 100, 0.6 s, pixel shift four shots at the
shortest interval, uncompressed RAW to the host; Raspberry Pi 5 (4 GB, 4 cores) as USB host
and controller (`strehl-capture-headless` and `strehl-sony-ptp` of `847cb8c8b`); MT7921U
Wi-Fi adapter to the PC's receiver. Subject on the stage: a pencil (sharp lettering at lens
position 41000, wood grain at 39000); lens position units are the camera's (the property
allows 0 to 65535; this lens stopped at 63487).

Labels: MEASURED, VERIFIED (read in code or a log), DERIVED, ARGUED, UNVERIFIED.

## 1. The camera link is back at USB 3 (VERIFIED)

After the owner removed a USB 2.0 extender, the camera enumerates on the SuperSpeed port
(`2-1`, 5000 Mbit/s; controller state `usb_speed_mbps: 5000`). A RAW of 124.6 MB reaches the
Pi in 0.38-0.44 s (282-326 MB/s).

## 2. The installed controller today (MEASURED, `evidence/baseline-product-runs.txt`)

Three short stacks with the installed controller (6, 4 and 4 planes, 8 units apart, settle
500 ms, error correction off).

| Per four-shot plane | Seconds |
| --- | ---: |
| Plane period | 7.3 |
| `capture()` in the bridge | 5.96-5.97 |
| Focus command to `focus_complete` | 1.24-1.26 |
| `capture_intent` to the shutter (journal upload, capacity request, queue room) | 0.03-0.38 |

Inside `capture()`: 0.30 s from the command to the first exposure (the 200 ms pause between
half press and full press), the camera's four exposures, the wait for the fourth RAW
(ready 0.25 s after the camera reports the group over, 0.4-0.5 s to download), and a 250 ms
idle check.

Uplink: each RAW is on the PC 1.36 s (1.27-1.52) after the Pi has it: 0.93-0.96 s in the
request (51.7 MB on the wire at 54-55 MB/s; the receiver's store included) and 0.4 s before
it (the upload thread reads and hashes the file again, `transfer.rs:250` and `:405`). Four
RAWs take 5.4 s one after another. The Pi's CPU during a group's upload: 37-46 % of four
cores, the controller about one core, the bridge 5-14 % (`evidence/pi-cpu.txt`).

The journal: every plane adds 6.2 kB to `events.jsonl` (4.3 kB for a single shot), and the
whole file is sent again twice a plane (`transfer.rs`, `snapshot`). DERIVED: 0.24 GB over the
scarab's 196 planes, 14 GB over 1500 four-shot planes, 155 GB over 6000 single-shot planes.

Error correction was off. DERIVED from these figures and the checker's 0.34-0.70 s
(2026-11-19): with it on, a plane would take about 9 s, because the controller holds focus
until the fourth RAW has crossed the uplink and been checked.

## 3. The uplink's ceiling (MEASURED, `evidence/wifi-rate.txt`)

Raw TCP from the Pi to the PC: 57-58 MB/s on one stream, 69 MB/s on two or four. The link:
Wi-Fi 6, 5785 MHz, 80 MHz wide, -56 dBm, 960 Mbit/s. The Pi's Ethernet port is unused.

## 4. What the camera does, measured with an experimental bridge (`ptp-lab/`)

`ptp-lab/make-lab.py` writes a copy of the product's `ptp.rs` with timing primitives
(`lab-fragment.rs`); `build-lab.sh` cross-builds it in WSL from an overlay of the workspace;
`run-lab.py` runs a script of commands on the Pi beside the installed controller (which is
disconnected from the camera meanwhile) and saves a timestamped log. Scripts `l1` to `l10`,
logs in `evidence/`, `show-lab.py` prints a log. The lab binary was removed from the Pi.

### 4.1 Primitives (MEASURED, `l1-primitives`)

- Reading all properties takes 6.3 ms (5.8-13.8); an event read with nothing pending
  returns after its 10 ms timeout.
- The camera sends events for everything the controller polls for: `c206` when an image
  arrives in its buffer, `c201` when it can be fetched (0.34-0.38 s later), `c202` when it has
  been fetched, `c218` for a focus move's result.
- The 200 ms pause before the full press is not needed in manual focus. From the command to
  all four RAWs on the Pi: 5.58 s with it, 5.42 s without, 5.34 s with the full press alone.
- The pixel-shift interval is already the shortest of the camera's options; the drive mode
  offers no focus bracket in this mode, and the pixel-shift mode itself is not writable over
  PTP (`l10-drive-mode`).

### 4.2 The camera's own cadence (MEASURED, `l4-exposure-and-single`)

| Exposure | Image arrivals after the full press (s) | Group over, all four fetched (s) |
| --- | --- | ---: |
| 0.6 s | 1.11, 2.28, 3.39, 4.53 | 5.34-5.37 |
| 1/10 s | 0.57, 1.39, 2.00, 2.65 | 3.32 |
| 1/100 s | 0.51, 1.39, 1.87, 2.42 | 2.94 |

The camera spends about 0.5 s on each image beyond its exposure. A four-shot group cannot
finish sooner than about 2.5 s plus four exposures.

### 4.3 The lens (MEASURED, `l2-focus`, `l7-lens-motion`)

- A focus command takes 3-5 ms to send. The camera's focus-result event arrives 0.20-0.25 s
  later for steps of 1, 8, 32, 128, 512 and -177 units.
- The position the product waits for (`FocusPositionCurrentValue` equal to the target)
  reads back 0.28-0.67 s after the command, with no relation to the distance: it is the
  property's refresh, not the lens.
- Live view at 30 fps on the sharp lettering shows the image 77-84 % of the way at
  0.11-0.13 s and settled by 0.15-0.18 s for steps of 128, -128 and 512 (an upper bound: live
  view's own delay is included). Steps of 8 and 32 change the picture too little to time
  this way.

So the product's focus step is: lens there by about 0.18 s; readback at 0.45-0.67 s; then the
500 ms settle; then the 0.3 s pre-roll. The first exposure starts about 1.4 s after the lens
arrived.

### 4.4 Overlap (MEASURED, `l3-overlap`, `l4-exposure-and-single`)

- The camera accepts a focus move while the group's last RAW is still inside it, and while
  it still reports the group active (sent at the fourth `c206`): focus-result 1 both times.
- It accepts the next full press with that RAW still inside. The RAW was fetched during the
  next group's first exposure (0.04-0.46 s after the press); that group's first image
  arrived at 1.13 s, as in any group, and all its RAWs were complete.
- The same holds one RAW a plane.

### 4.5 The pipelined order, sustained (MEASURED, `l9-sustained`)

Full press; RAWs fetched whenever ready; lens sent on at the fourth image's arrival; next
full press 300 ms after the focus-result event (100 ms for single shots).

| | Installed controller | Pipelined order | |
| --- | ---: | ---: | --- |
| Four-shot plane, 0.6 s, 8 units | 7.3 s | 5.09 s (5.06-5.14, 8 planes) | 30 % less |
| One RAW a plane, 0.6 s, 8 units | 3.1 s (settle 100 ms, 14 Nov) | 1.54 s (1.48-1.58, 10 planes) | 50 % less |

Every RAW was fetched complete (32 and 10). The lab discards the RAWs, so the uplink is not
in these figures (section 2 and 3 bound it).

### 4.6 A short settle, screened at full resolution (MEASURED, `l8-settle`, `settle-analyse.py`)

Sixteen four-shot groups 8 units apart through best focus on the lettering, the full press
0, 100, 300 or 1500 ms after the focus-result event, interleaved; RAWs kept and analysed on
the PC. If the lens or rig were still moving, exposure 1 would be softer than exposures 2-4
of its group and displaced from where the 1500 ms groups put it.

| Settle after the focus-result event | Sharpness of exposure 1 over exposures 2-4 (median; range) | Shift scatter about the trend (rms; worst) |
| --- | --- | --- |
| 0 ms | 0.998; 0.980-1.007 | 0.075 px; 0.21 px |
| 100 ms | 1.010; 0.996-1.013 | 0.077 px; 0.17 px |
| 300 ms | 1.009; 0.982-1.010 | 0.081 px; 0.19 px |
| 1500 ms | 1.006; 0.999-1.014 | 0.082 px; 0.23 px |

Controls: the same ratio on a defocused flat window is 1 within 0.0034 (run first); a
planted Gaussian blur of 0.5 px sigma in exposure 1 moves the ratio from 1.014 to 0.976 and a
planted 0.2 px shift moves the residual from 0.09 to 0.37 px. No settle shows softness or
displacement beyond what the 1500 ms groups show.

Limits: four groups a settle; steps of 8 units; this lens and stand; the estimator is a
phase correlation on one window, not the engine's. The engine's own group check
(`strehl pixel-shift`) cannot score this scene: it demotes every group, the installed
controller's included, for too little structure. A stack of a structured subject is still
owed (plan, stage K4).

## 5. The focus step (MEASURED)

### 5.1 How many planes a point is sharp in (`focus-step-study.py`, `evidence/focus-step-study.txt`)

Scarab stack (196 planes, 8 units apart), planes 64-136, first exposure of each group, per
64 px tile.

| Measure | Width of a tile's peak at half height | Left one plane from the peak | Two planes | Four planes |
| --- | ---: | ---: | ---: | ---: |
| Fine detail (unblurred Laplacian of one green site plane) | 14.3 planes (12.2-16.4) | 0.93 | 0.88 | 0.75 |
| Mid detail (gradient after a 1.6 px blur) | 26.4 planes (22.9-31.8) | 0.99 | 0.98 | 0.93 |

The peak value is the largest of noisy values, so the "left" figures are biased low; a
Gaussian of the measured width would leave 0.986, 0.947 and 0.805.

### 5.2 Renders from fewer planes (`subset-run.py`, `render-subsets.ps1`, `compare-step-renders*.py`)

The stack rendered with the default four-shot route from all 196 planes (the reference
bytes `02A6C8C2...`), from every second plane and from every fourth (the middle plane the
same in all three).

| Against the full stack | Every 2nd plane (16 units) | Every 4th plane (32 units) |
| --- | --- | --- |
| Detail tiles, gradient energy at blurs of 0.5-2.5 px, floor removed | 0.998-1.000 (10th percentile 0.986-0.990) | 0.943-0.967 (amplitude 0.971-0.983) |
| Unblurred finest band, flat tiles | 0.889 | 0.540 |
| Unblurred finest band, detail tiles | 0.897 | 0.536 |
| Crops at the strongest edges, 200 % | not distinguishable | not distinguishable |
| First render, empty cache (other work running) | 26.3 s against 41.7 s | 17.3 s |

The unblurred finest band falls by the same factor where there is detail and where there is
none: that is selected noise (a selecting merge keeps the largest of N noisy coefficients),
not focus. Where signal dominates, half the planes lose nothing measurable and a quarter
lose 2-3 % of amplitude.

Limits: one subject, one magnification, one aperture. Depth of field changes with all
three, so the step has to be measured per setup (plan, stages F1-F3).

## 6. Files

- `rig.py`, `pi-survey.py`, `pi-cpu.py`, `wifi-rate.py`: rig control and probes (no keys printed).
- `group-timeline.py`, `receipts.py`: read a run's journal and receipts.
- `ptp-lab/`: the experimental bridge (fragment, patcher, build, runner), scripts `l0`-`l10`,
  `show-lab.py`, `lv-fetch.py`, `lv-analyse.py`, `raw-fetch.py`, `settle-analyse.py`,
  `synth-run.py`.
- `focus-step-study.py`, `subset-run.py`, `render-subsets.ps1`, `compare-step-renders.py`,
  `compare-step-renders-2.py`.
- `evidence/`: lab logs (`*.jsonl`), analyses (`*.txt`), the Pi survey.

Housekeeping: camera and light off, manage power on, lens within 50 units of where the
session found it, camera settings restored; the three test stacks on `D:` and all scratch on
`C:` deleted; nothing left on the Pi.
