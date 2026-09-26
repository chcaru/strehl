# Why the first full trace wrapper refused

VERIFIED by read-only comparisons after the root-run `on-1` Rust test completed.
No build-bound file was edited, no RAW was decoded and no output was rerendered.
The failed wrapper remains failed; this note does not rewrite its result.

`on-1/process.json` records a successful full488-source Rust process, exit0,
264.344 operational wall seconds, terminal Job accounting and no cleanup error.
The root wrapper subsequently refused its historical `candidate_sha256` check.
That check compared complete TIFF bytes across different builds. It was too
strong for image identity because the writer embeds the build in TIFF Software.

The new `on-1/output/candidate.tiff` and the retained
`garnet-spatial-trace/marigold4-fixed-1/output/candidate.tiff` were compared with
`tifffile`, NumPy and direct binary reads:

- Both are157,055,880-byte,6268×4176 single-page RGB16 TIFFs.
- Every decoded RGB16 sample is exactly equal; the actual pixel and concatenated
  strip-payload SHA256 is
  `6d26d2cc00f6eb76500d4574a7f0d3ba7eb35b364e100daac8eeb96422c13c11` in both.
- ICC bytes are identical, SHA256
  `238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b`.
- All four recorded merged-plane hashes, canonical plan, crop, thread count and
  source count match. The new Rust receipt reports held source evidence exact.
- Every TIFF tag value is identical except tag305, Software. Old:
  `strehl 0.0.0 (3386cd48430a-dirty)`. New:
  `strehl 0.0.0 (1693275a3411-dirty)`.
- The Software payload occupies the same34 bytes beginning at file offset3360
  in both files. Streaming raw-file comparison finds exactly12 changed bytes,
  at offsets3374 through3385 inclusive. **Zero changed bytes occur outside that
  Software payload.** Thus this is proved metadata-only, not inferred from
  matching receipt claims or a visual resemblance.

The actual read commands used Python3.12 `-I -B -X faulthandler`: one script
loaded both actual TIFF arrays, required `np.array_equal`, hashed decoded pixels
and all encoded strip payloads, compared all tag values and ICC bytes; a second
read tag305's actual `valueoffset/count`, then compared files in1MiB chunks and
asserted every differing byte lies inside that exact region. The receipt JSON
fields listed above were separately compared.

Proposed recovery is a separate saved-result verifier, not a weakened rerun.
It should preserve both original wrapper outcomes, validate successful Rust
processes and all held source evidence, prove the old/new decoded RGB16, ICC and
four complete merged planes identical, and require this exact tag305-only byte
exception for the historical cross-build comparison. Crucially, the **same
new binary's observer-on/off complete TIFF hashes and plane hashes must still
match exactly**. That comparison has no build-metadata excuse. A new receipt
must name the superseded cross-build file-hash gate and its bounded reason;
it must not create original-run completion files or claim the old gate passed.

This audit was written while `off-1` was still running. It makes no claim yet
about completed observer-on/off identity or the photographic interpretation.
