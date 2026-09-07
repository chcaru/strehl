# M194c pre-execution comparison review

These source/API corrections preceded the first candidate build and output.
They are review findings, not measured product failures.

- The first supplemental-source walker recognized `#[path]` modules but the
  actual test modules use `include!(concat!(env!("CARGO_MANIFEST_DIR"), ...))`.
  The walker now follows the actual form, including the nested frozen sampler.
  A real preflight confirmed the three Rust files are reached.
- Binding every top-level Python/Markdown file would make later independent
  report writing invalidate a run. The supplemental set now explicitly includes
  the root controller/comparison code, author/root preregistrations and legacy
  receipt, plus every top-level Rust file. Source-set refusal still covers new
  or missing Rust includes; reports and independent Python reads can continue.
- Root initially passed native offset18,14 to `canonical_grid`, which expects
  quad offset9,7, then treated the bound crop dictionary as a positional list.
  The independent reviewer caught both. The corrected code reads named x/y
  from the actual score's domain and verifies its relation to native offset.
  The existing mask hash check would have rejected the first mistake; neither
  incorrect form produced a reported candidate comparison.
- The initial controller reader checked success flags and log hashes without
  checking the exact three parent commands and their build/index bindings.
  It now checks those operations, original producer identity, the sole changed
  compiler input, and rereads the candidate with the unchanged M194b scorer.
  A score's self-consistent derived fields cannot replace the actual TIFF read.

Independent pure-function and actual-TIFF controls are recorded separately.
Their passing results do not conceal these review corrections or establish
camera fidelity, physical optics or SOTA performance.

## First completed run: serialized container mismatch

The first forty-output run completed normally. Root's subsequent comparison
preflight refused exact equality between the freshly reread score and its JSON
file: `domain` is returned as a tuple and serialized as a list. The diagnostic
in `comparison-first-failure.json` found zero scalar-value differences and exact
equality after JSON-container normalization. The comparison now performs that
normalization, retaining exact numeric equality. This changes no tolerance,
target, crop or formula. No version comparison was published from that failed
invocation. A new full matrix will bind the corrected reader and final
independent test API corrections; the first run is preserved unchanged.
