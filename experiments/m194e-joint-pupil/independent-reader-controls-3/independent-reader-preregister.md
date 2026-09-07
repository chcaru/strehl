# Independent final-array reader controls

These are file-reader commissioning checks before the actual final author bundle
is available, not another scene, numerical method or source of float authority.
They exercise `independent-compare.py::array/read_json` using a byte copy of the
already bound independent refined frame2. The unchanged array and an identical
relocated copy must pass with exact array equality. Independently changed file
hash, trailing payload, float32 header, wrong dimensions, NaN value and duplicate
JSON keys must refuse. A finite `.005`-electron change at pixel(32,24) with its
file digest correctly updated must pass the file reader and fail the existing
whole-frame maximum discrepancy bar. This separates structural validity from
numerical accuracy. No scene parameter, threshold or tolerance changes.

Every case runs once, cheaply, with one process and at most two numerical-library
threads. Preserve failures and source snapshots; a failed control prevents using
this reader for a genuine float commission until its cause is recorded and fixed.
