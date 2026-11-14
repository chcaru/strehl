# Capture inside Strehl

Open **Capture** in the left rail. This is a native egui workspace, with the same
Pi camera owner and authenticated LAN protocol used by the phone controls.
There is no embedded browser. The Pi continues to own USB, focus sequencing,
pixel-shift groups and the bounded RAM upload queue.

## Connect and capture

1. Open **Connection settings** and enter the Pi's numeric LAN address and
   pairing key, or paste its full pairing link in the address field. Set your
   local subnet and choose **Save connection**. These settings remain local to
   this PC. The application does not create an internet relay.
2. Check **Receiver ready** and the destination under **Storage on this PC**.
   Choose a folder and save it. **Keep RAWs losslessly compressed** defaults to
   on in the receiver; Strehl reads `.ARW.straw` directly. Folder and format
   changes apply to new stacks; registered stacks retain their choices.
3. Connect the camera if needed. Use the live preview, zoom, focus slider or jog buttons
   and **Mark Start / Mark End**. Both marks work independently of JPEG preview
   health. Step **1** is the smallest normalized camera command unit; it is not
   a calibrated distance or a guarantee of lens encoder resolution.
4. Optionally select the subject region and survey a broad marked range.
   The survey suggests tighter bounds from live-view sharpness. A clipped survey
   cannot be applied; enlarge the initial range first. Camera magnification, when
   supported, centers on the selected region. Live view is a camera JPEG, not a
   full-resolution RAW quality assessment.
5. Choose **4-shot pixel shift** for four RAWs per focal plane, or turn it off for
   one RAW. This option requires the matched A7CR Pi controller/bridge; it is
   disabled for unsupported cameras. Apply changed sequence settings, then
   **Start stack**. Progress distinguishes
   focal planes from RAW members, shows elapsed/estimated remaining time, and
   reports uploads awaiting the PC. **Pause**, **Resume**, and **Stop** use the
   same sequence as the phone. Pixel-shift groups finish before pausing/stopping.
6. After every RAW and the final result receipt are durable, select the stack
   under **Completed captures** and choose **Open in Projects**. This rechecks
   completion receipts and file lengths. Archive decoding separately verifies
   the original RAW checksum. Processing remains an explicit Projects action.

If a camera operation fails, the recovery action stays available. An uncertain
exposure requires explicit acknowledgement before recovery. Mutations are never
automatically replayed after a lost reply. Another controller changing the focus
plan can reject an outdated request; inspect the refreshed state before retrying.

**Phone control · QR code** opens a pairing QR for the same LAN controller.
Scan it with the phone camera. It includes the private pairing key; keep it out
of shared screenshots. Android Chrome may require **Nearby devices** permission.
Pairing has no timer and survives an hours-long stack.

The focus slider offers **Fine** (128 command units either side), **Marked range**,
and **Full lens**. It sends one movement at a time and keeps only the latest drag
target while that movement completes. Capture locks the slider. Changing its
range alone does not move focus; lost acknowledgements clear pending movements.
Capture still approaches and settles each plane using the configured sequence
settings, independently of the quicker preview scrub.

**Focus peaking** overlays cyan high-frequency contrast from the live JPEG. Raise
**Threshold** for fewer highlights, or lower it for lower-contrast subjects. This
is a focusing aid: noise, texture and JPEG sharpening can also produce highlights.
It never alters a RAW. The subject rectangle appears only while selecting it;
the preview otherwise has no permanent yellow box. Phone controls also provide
focus scrubbing, peaking and the single/four-shot selector.

## Time and disk admission

Before capture, the estimate counts every exposure and a focus settle per plane.
Selecting four-shot capture updates time, total RAW count and disk requirements.
Once running, measured whole-plane cadence replaces the initial allowance.

Start is disabled when the current disk cannot fit the planned stack. The Pi also
checks fresh receiver capacity before any focus move or shutter, and rechecks the
registered destination before each following plane. This applies to phone/API
requests too. Unknown capacity fails closed. The budget uses the backend's RAW
size ceiling, codec/receipt overhead and 512 MiB headroom; it assumes no compression
savings. It can therefore reject a stack that would fit after compression. Other
programs can consume disk space later; the per-plane check stops further capture
if that happens. Already captured RAM files are preserved by the existing recovery
path. Receiver folder changes do not redirect an active stack.

An older receiver already running at upgrade can be used while its default folder
still matches the registered stack. Changing it mid-stack requires restarting the
receiver or restoring its original folder. Updated receivers report capacity for
the pinned run directly, independently of the new-stack default.

## Receiver lifetime and settings

Strehl reuses the existing receiver configuration and per-run destination index:
`%LOCALAPPDATA%/StrehlCaptureReceiver/receiver.json` and `receiver.runs.json`.
An already-running receiver is attached without interrupting it. **Start receiver**
starts the same Strehl executable with `--capture-receiver --config PATH` in a
background process. Closing the editing window does not stop that process or the
Pi. On Windows, the receiver holds an idle-sleep prevention request; display
sleep is allowed. Power loss, explicit sleep and a disconnected network can still
interrupt delivery. Keep the destination PC available until all uploads finish.

Native pairing preferences are in `%LOCALAPPDATA%/Strehl/capture.json`.
Treat that file and the receiver configuration as private: they contain keys.
`--capture-settings PATH` selects an isolated configuration for testing or another
installation. The receiver configuration path is a field in that JSON. The app
does not overwrite the Pi configuration or change existing autostart scripts.

The executable also supports `--capture` to open this tab immediately. For
example, launch `Strehl.exe --capture`. The receiver can run at sign-in with
`Strehl.exe --capture-receiver --config <existing-receiver.json>`; retain the
adjacent source/relink kit when installing a portable desktop package.

## Boundary for streaming processing

This integration retains the original focus plan, per-plane camera events,
pixel-shift member identities, durable transfer receipts and final result marker.
The completed-stack handoff admits only registered, complete receiver runs;
stopped or partially transferred groups remain available on disk for recovery.
The native UI lists the eight most recent complete runs among the last 32
registered runs. Older runs remain accessible through Projects' normal import.

Incremental alignment, fusion and development while capture continues are a
separate next stage. There is no provisional stacked photograph yet, and importing
a pixel-shift group does not claim that the ordinary stack renderer performs a
dedicated Sony pixel-shift reconstruction. That work must preserve group identity,
handle late/failed uploads and distinguish provisional results from a finalized
render. The receiver's durable receipts provide the natural admission boundary.
