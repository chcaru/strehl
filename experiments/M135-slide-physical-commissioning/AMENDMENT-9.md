# M135 slide commissioning amendment 9

Status: **CROSSCHECK TRANSPORT HARDENED BEFORE COMMIT**

The final reviewer correctly noted that pathname rechecks cannot close a
time-of-check/time-of-use race around `File::create`, even with reparse
component validation.  The stronger repair is to remove the writable path.

`m135-slide-raw-crosscheck` now streams its binary active-area payload to
stdout and its geometry record to stderr.  Python validates and hashes the
captured bytes directly.  Stage B has no scratch argument, creates no decoder
file, and has no filesystem path that can be redirected into the capture
tree.  The earlier scratch-path guard in amendment 7 is therefore superseded,
not relied upon.

The payload header, pixel order, all-frame bit comparison, and decoder
independence are unchanged.
