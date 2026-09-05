# M135 slide commissioning amendment 4

Status: **DEPENDENCY-PATH REPAIR BEFORE THE FINAL FREEZE**

The first compilation attempt for the previously discovered
`experiments/m61-ptc-high-iso/decode-check` path exited `101`: its existing
`Cargo.lock` would need an update, while `--locked` correctly forbade one.
This lane may not modify that experiment.

The safe decoder route itself remains valid: `strehl-raw` is the project-owned
wrapper over the linked rawler API, and no rawler/LGPL source was opened.
This amendment adds a small lane-local Rust executable that calls only that
existing API and emits the already commissioned 16-byte-header plus active-
area-u16 payload contract.  It adds no dependency beyond `strehl-raw`, keeps
its lock and build output inside the owned lane, and leaves every Python
decoder comparison unchanged.

The failed build accessed no capture and no path under `D:\`.
