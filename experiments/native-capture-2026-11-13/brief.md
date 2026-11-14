# Native Capture workspace

Integrate the current headless Pi capture experience into Strehl as a native left
rail tab. The Pi remains the camera owner. No webview or browser is used by the
PC Capture workspace; existing phone controls continue to share the same API.

Implement native live preview, zoom/subject ROI, manual focus bounds/jog/go,
minimum step default, settings, survey and suggested bounds, magnifier where
supported, start/pause/resume/stop, timers, transfer/storage status and explicit
uncertain-exposure recovery. Commands preserve the controller's captured revision
and are never automatically replayed after a timeout or stale-state refusal.

Move the receiver runtime into a reusable service entry point, exposed through
the main Strehl executable's background receiver mode. Native settings use the
existing receiver configuration/key/destination, compressed-storage option and
registered-run policy. A background receiver survives closing the editing window;
attach to an existing receiver instead of claiming or interrupting its port.

Provide a checked completed-stack handoff to Projects when every RAW is durable.
Do not implement incremental stacking in this stage, start processing implicitly,
or claim pixel-shift image-quality improvement. Preserve per-member receipts and
group journals as the future streaming-processing boundary.

Verification: isolated simulator/native UI controls through the app's own control
interface and screenshot helper, malformed/missing controller and stale/duplicate
commands, default receiver/settings compatibility, long-operation enabled states,
and optional short physical four-shot qualification only while the camera/queue
are idle. Preserve all captures, keys, unrelated work and existing startup.
Build a runnable source-inclusive native package; record exact build/source hashes,
tests, screenshots, real hardware scope and remaining limitations.
