# Independent saved-build reconciliation review

VERIFIED by read-only receipt, hash, Cargo-artifact and emitted-dependency inspection on 2026-09-25. No build, test, RAW decode or render was run for this review.

The original `native-build-1` compiler succeeded in 182.375 s. Its process receipt records exit 0, no error/cleanup errors, terminal job accounting and no active processes. The log contains `Compiling strehl-cli`, a successful build-finished event, and a non-fresh CLI test artifact. The later original source guard failed; that failure and its source manifest must remain unchanged. There is no original `executables.json`.

The copied `native-build-1/cli-tests.exe` and the actual logged artifact `target/native-pyramid-profile/release/deps/strehl-d7e31143be64edff.exe` have the same SHA256:

`b07cfb916c4f208827b76079ac867c12ca1b1c0e68f9b86fb99b29d62055aae3`

All 342 original source-manifest entries were read and hashed. Exactly one differs: `experiments/source-gradient-target/lib.rs`, whose standalone module declaration gained `#[path = "independent-controls.rs"]` after its separate failed compile. Its old hash is `0fe16db18bce6374c41c185a78c0955611dbe5491a35f074212a9c5c7613f721`; current hash is `7c1b1cd493bf6d32fb6923ca1cc3bd88204ea3f6ad5d5ddd8e8755782059f1a7`. The other 341 entries still match their original hashes.

The actual emitted artifact stems identify these dependency files (all under `target/native-pyramid-profile/release/deps`):

| Depfile | SHA256 |
| --- | --- |
| `strehl-d7e31143be64edff.d` | `c1f5d2323418db1a1bf95c92eef314652671ef90ed135d18458d8f1411060060` |
| `strehl_core-60ead7b714ba5262.d` | `15290a143dcb422d40b7d3e370ea0e3ef5fa149b2c1c8ce87dbe74fe221e1a86` |
| `strehl_raw-fafc8dc126155040.d` | `8669dd4f3f0fc06d8eecfffb49536b30d8504552d453d3d50730a35c7c5f6811` |
| `strehl_plugin-edd6d273094bf97e.d` | `5966f9e77f60b480a26a0410e654a9692d4bdaeb6edf11fbf5a3ed44884acfa3` |
| `strehl_native_gpu_gather-84e7239effa49f53.d` | `24c4563e67e6d64971d4d2f8e5e51d73929616da63771aec26c826f2da6e1a25` |

None includes `source-gradient-target`. The CLI depfile includes the actual intercept operator, adapter and independent controls. Root workspace Cargo membership and crate source references also exclude the gradient harness. The own CLI build script only reads Git/build identity, not that harness. No third-party decoder source was opened.

Parsing and resolving the five first-line dependency lists gives 221 unique repository inputs. The 214 present in the original manifest are hash-identical. Seven consumed inputs were never covered by that inherited manifest:

- `crates/strehl-core/src/defect-map-ILCE-7CM2-dust.txt`
- `experiments/m193c-output-grid/derivative-controls-preregister.md`
- `experiments/m193c-output-grid/independent-derivative-design-review.md`
- `experiments/m193c-output-grid/private-protocol.md`
- `experiments/m193c-output-grid/registration-derivative-design.md`
- `experiments/native-gpu-gather/src/coordinates.glsl`
- `experiments/rb-own-guide/controls-1/output/screen.json`

This is a pre-existing inventory limitation, not evidence that those inputs changed. New bindings can freeze them for subsequent use; they cannot retrospectively establish their build-start hashes. The accurate claim is **all other originally bound sources retain their original hashes**, not that every compiler input had such a hash.

Source review of the separate `reconciled-run.py` found the requested narrow checks: exactly the named excluded change; clean compiler completion and fresh CLI compilation; identical copied/emitted executable; actual CLI/core depfile exclusion; retained original hashes; and a new immutable reconciliation receipt before delegating to the unchanged native controls/full functions. It preserves `original_build_guard_pass=false`. Root was notified to narrow its scope wording and retain the seven-input historical limit.

Conclusion: the one unrelated standalone module-path repair does not require recompiling this already emitted native CLI. This is an explicit source-inventory reconciliation, not an original guard pass, a claim of complete historical source coverage, or any scientific/photographic admission. The exact native controls and their unchanged scientific refusal still apply.
