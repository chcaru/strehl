# Camera fault recovery UX

Allocation `sony-capture-ui-2026-11-08-fault-recovery`, root, November 8 Pacific.
The owner reports a focus-information failsafe left no apparent way to restart
without closing the app, and requests an audit of the whole capture UX. The
previous stack is finished. Existing Fault disables edits and polling, with only
a general Disconnect button and an error footer; there is no dedicated recovery.

Add an explicit, visible Reconnect action in native and browser interfaces.
Finish releasing the owned bridge before a replacement connection can open.
Reconnection must not start/repeat a shutter. Preserve previous RAWs/journal and
retain marks/settings for the same reported identity, instructing review of both
marks; changed identity invalidates marks. The bridge reports model/transport,
not a unique camera/lens serial; matching identity does not verify unchanged
physical focus. Distinguish uncertain exposure
outcomes from focus/status failures. Only an uncertain shutter requires the
operator to acknowledge camera/card inspection before reconnecting. Retain the
error and completed count until recovery succeeds or a new run begins.

Prior source: worker Fault paths, native bridge uncertainty latch and existing
`uncertain_shutter_never_retries_or_advances`; prior reports are
[browser remote](web-remote-results.md) and [preview fix](preview-fix-results.md).
The native SDK bridge source and RAW-saving protocol stay unchanged.
Use planted focus-information, capture-acknowledgement, disconnect and missing
focus-status failures with native UI/browser exercises and worker tests. Check
negative recovery admission first, then recovery and a separate successful run.
Do not use a physical camera or interpret simulator behavior as hardware proof.
