# M193c first build refusal — independent repair review

2026-09-07. **RETAINED-RECORD AND SOURCE REVIEW ONLY.** No build, helper,
image or RAW command was run by this reviewer. Original build1 artifacts
remain unchanged; this note does not convert that failure into a pass.

The parent launched the source committed at `1e5e100a` using release
`acd61560cf5fb61f098792ed274369ba9268f24d1ef844544292b8b06fab6414`
and reports collecting controller exit 1. I independently read:

- `bridge-build-1/result.json`, 26349 bytes, SHA256
  `dd4ef7dd8a710bbc0b59de4d781dfb4a85b5975311d03befb0e3ba95e8770d87`.
- The actual compiler log, 184496 bytes, SHA256
  `d9d28c2f84cf6950c42366aca3671bb7fffa9fefe1cb984ea8aab6a2a5bd0da2`.

The record is `UNCOMMISSIONED_BUILD`, with compiler exit 101 and
`rebuilt_cli=true`. The log visibly contains `Compiling strehl-cli` and
E0432 at the private adapter's import of the nonexistent
`strehl_core::noise::NoiseProvenance`. No copied test executable or listing
was admitted. Compiler cleanup errors are empty; terminal Job accounting
is true with zero active processes. The actual terminal Job CPU is
1486093750 100-ns ticks, and helper wall time is 21.375 seconds, under its
separate build limits. These are build observations, not image performance.
The result's `sources_after` is null because the normal success path was
not reached; do not report a populated before/after success map for this
attempt merely because its finalization errors are empty.

The reviewed Rust change is exactly one import:
`use strehl_core::noise::{PlaneNoise, Provenance as NoiseProvenance};`.
I checked the owned `crates/strehl-core/src/noise.rs` declaration: its enum
is `Provenance` and it has the existing `Fallback` variant consumed here.
The alias keeps all existing use sites, coefficients and injection calls
unchanged. The build driver changes only the target suffix from
`m193c-output-grid-build-1` to `m193c-output-grid-build-2` in the exact command
and matching fresh-target guard. It does not reuse the failed target or
change caps, populations, software-stamp logic or numerical acceptance.

| Repaired source | Bytes | SHA256 |
| --- | ---: | --- |
| private-adapter.rs | 23746 | e9fe4be0fe6354e00294900c8f5bad1aade76fbbfb2be1367bb7cafa13ed85a8 |
| bridge-build.py | 14682 | f7690d009893698b6d9756d971ff0f3989e44a996b13fe5bd0d535add1cc29c7 |

**Disposition:** the minimal import repair matches the actual owned API and
is ready for a separately frozen fresh build2 command. This source review
does not establish that the next compile or listing will pass. No product
image or native derivative stage is released by it.
