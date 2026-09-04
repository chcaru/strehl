# M138 adapter amendment 4 — execute verified source bytes

**Frozen before rerun:** yes  
**Affected file:** `m138_adapter.py`

Amendment 3 moved local core loading behind bundle verification. A second
source review found one remaining ambiguity: Python's standard source loader
may execute a cached `.pyc` when its metadata appears current, while the bundle
binds `comparison_checker.py` rather than an interpreter-generated cache file.
The registered source was verified first, but the loader did not structurally
guarantee that those exact bytes were the code object executed.

This amendment removes the standard source loader. After the bundle and
environment pass, the adapter reads the verified `comparison_checker.py`
bytes, compiles those bytes directly with their registered filename, and
executes the resulting code in a fresh module. No bytecode cache is read or
written.

The request schema, output-state mapping, commissioning bars, core source, and
all valid-input arithmetic are unchanged. The amendment-3 25/25 result and its
5/5 bootstrap-order proof are preserved. The complete 25-check battery,
byte-stability replay, production description, and tampered-core bootstrap
proof must all be rerun under the amended bundle.
