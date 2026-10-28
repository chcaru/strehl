# Native-u16 bridge source review

2026-10-27. Root independently reviewed `export-originals.py` SHA256
45be9494838998ec54f8ff6f8e364b34117d7e4e3b6f8528ab742c7c67e3d7d2
and the generic native wrapper. No RAW export was executed.

**VERIFIED source:** the output directory is fresh under this worktree's
outputs; each decoder destination must be absent. Invocation requests the
complete7032x4688 native active sensor. The expected header, byte count,
camera/levels/active-buffer log fields, exact source order and original-file
before/after hashes are checked. One decoder runs at a time. Original codes
remain u16 and untouched, including codes beyond working white. No alignment,
MHC, WB or tone operation intervenes in the cache producer.

Three full7028-wide native overlaps are compared both elementwise and by
pixel hash against the previously independent RawPy caches. The four extra
columns are explicitly native-only. Physical green phases remain distinct;
the extra columns start at even x7028, preserving the local phase mapping.
Native metadata comes from the bound same-original full export receipt and
native logs, not a new inference from developed pixels. Profile coefficients
are reconstructed with the native f32 arithmetic and retained as bits.

**VERIFIED read-only preflight:** root loaded the wrapper under a non-main
module name, rehashed all six declared producer/evidence bindings, then called
`validate_metadata` against all299 manifest entries. It passed. This did not
call `main`, the decoder, or original-file hashing. Evidence is in
[the preflight receipt](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-export-preflight-1/receipt.json).

The wrapper's30s per-decoder timeout is secondary to a future root job-tree
limit; the generic executable can overwrite paths, making the fresh-target
checks essential. Root must bind sources, enforce resource/disk limits and
retain partial outputs on failure. The exact rebuilt-source provenance of the
old executable is not newly claimed; its frozen executable hash and previous
independent comparisons are the available evidence. This source review alone
does not authorize the19.7GB export or establish reconstruction quality.
