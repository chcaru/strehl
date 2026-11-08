# Live-view fix and capture countdown

Continuation: `sony-capture-ui-2026-11-07-preview-fix`, root, 2026-11-07 Pacific.
The owner reports an invalid-JPEG preview and disabled start/end mark buttons,
and requests a countdown/time estimate. The original [results](results.md) cover
the initial package; this continuation changes its preview and UI behavior.

Prior lookup: `python scripts/research.py search 'capture preview' --limit 5`
and `python experiments/ORCH-drift-check/prior_art.py 'live-view JPEG' 'capture countdown'`.
The original capture report is the owning prior implementation. No reconstruction
algorithm, optical claim or camera capability is being added.

The supplied Sony SDK 2.02.00 reference, `html/class/live_view.html`, specifies
`GetImageData()` as the JPEG pointer and `GetImageSize()` as the JPEG byte count.
The original bridge instead required that pointer to equal the allocation base
and encoded from that base. Its assumption rejects an offset JPEG payload. The
correction must validate the returned subrange and encode the returned pointer.
Controls must reject null, out-of-range and truncated spans before dereferencing.
The Rust decoder must be checked with an actual encoded JPEG through the same
base64/JSON path used by the camera, rather than only a direct RGB simulator.

Manual marks should require a connected, editable camera with a reported focus
position, not a successfully decoded preview. A failed-preview UI exercise must
actually click both marks and jog between them, while leaving the error visible.
Automatic preview surveying continues to require functioning preview frames.

The timing consumer is the user waiting for a stack, in seconds of active time.
An initial rough estimate uses the SDK shutter-speed fraction, configured settle
time and an explicitly approximate operation allowance. Completed capture cycles
replace this with observed cadence. Pause duration must not enter the cadence or
reduce remaining time. Stop/error freezes elapsed time; incomplete operation
overruns must not display a false completed countdown. Deterministic monotonic
clock controls precede the UI exercise. No hardware timing accuracy is claimed.

Preserve SD-only RAW saving and memory-only camera previews. Build with two
workers, test the changed paths, inspect native UI renders, and verify the
relocated portable ZIP. No physical focus or exposure is required for this repair.
