# Workstream D — Rust Ecosystem Survey and Hardware Envelope

Research date: **2026-08-22**. All crates.io figures fetched that day via `https://crates.io/api/v1/crates/<name>`.

## §0 Method and labelling key

| Label | Meaning |
|---|---|
| **MEASURED-LOCALLY** | Number produced by a command I ran on this machine (read-only). |
| **MEASURED** | Number from a benchmark someone else actually ran, source named. |
| **VERIFIED** | Read directly in the primary document / source file cited. |
| **UNVERIFIED** | Inference, derivation, or recollection not backed by a fetched source. |
| **COULD NOT CONFIRM** | Search executed, exact query recorded, nothing found. |

Toolchain state on this box (MEASURED-LOCALLY): `rustc`/`cargo` **not installed**; `nvcc` **not installed**; NVIDIA driver **610.62**, CUDA user-mode driver **13.3**; Python 3.12.10; PowerShell 7.6.5; Windows 11 Home 10.0.26200. All CUDA capability probing was therefore done through `nvcuda.dll` via Python `ctypes` (driver API only, no toolkit).

---

## §1 Rust crate survey

### 1.1 RAW decoding

| Crate | Ver | License | Last release | Downloads (total / 90d) | Pure Rust? | Status |
|---|---|---|---|---|---|---|
| **rawler** | 0.7.2 | LGPL-2.1 | 2026-02-26 | 107,720 / 37,419 | Pure Rust | Active (dnglab/dnglab) |
| rawloader | 0.37.2 | LGPL-2.1 | 2026-08-15 | 312,423 / 14,073 | Pure Rust | Active (pedrocr) |
| imagepipe | 0.5.1 | LGPL-3.0-only | 2026-08-15 | 116,948 / 4,261 | Pure Rust | Active (pedrocr) |
| quickraw | 0.2.1-alpha.1 | LGPL-2.1 | 2023-06-19 | 22,310 / 1,364 | Pure Rust | Stale (3 yr) |
| libopenraw | 0.4.0-alpha.12 | LGPL-3.0-or-later | 2025-08-22 | 46,205 / 4,654 | Rust rewrite | Alpha |
| libraw (dcuddeback) | 0.1.1 | MIT | 2015-11-05 | 6,056 / 131 | C binding | Abandoned |
| libraw-rs | 0.0.4 | MIT/Apache-2.0 | 2021-02-02 | — | C binding | Abandoned |
| libraw-sys | 0.1.1 | MIT | 2015-11-05 | — | C binding | Abandoned |
| `dnglab`, `rawspeed-sys`, `dcraw` | — | — | — | **404 on crates.io** | — | Not published as libs |

Source: crates.io API for each name. `dnglab` is a binary target inside the `dnglab/dnglab` repo, not a published library crate — COULD NOT CONFIRM any published `dnglab` lib crate (query: `https://crates.io/api/v1/crates/dnglab` → 404).

**Sony A7C II (ILCE-7CM2) support — VERIFIED**

| Question | Answer | Evidence |
|---|---|---|
| A7C II supported by rawler? | **Yes, "all" modes** | `dnglab/dnglab:SUPPORTED_CAMERAS.md` row `SONY \| ILCE-7CM2 \| ✅ Yes \| all` |
| Camera definition present? | Yes | `dnglab/dnglab:rawler/data/cameras/sony/a7cm2.toml` — `model="ILCE-7CM2"`, `color_pattern="RGGB"`, `bps=8`, color matrices `A` and `D65` |
| Lossless-compressed ARW? | **Yes** | `rawler/src/decoders/arw.rs:135-184` — compression `7` → `decode_ljpeg`; comment lines 145-147: "Starting with A-1, image is compressed in tiles with LJPEG92. Data is RGGB for bayer readout…" |
| Other ARW compressions | `1` uncompressed, `32766` ARW6 wavelet, `32767` ARW1/ARW2 | same file, same range |
| Pre-demosaic CFA exposed? | **Yes** — `PixU16` + CFA pattern + black/white levels + color matrices | rawler is a *decoder*; `imagepipe` is the separate develop-to-RGB layer |
| Can write DNG? | **Yes** | `rawler/src/dng/writer.rs`, `dng/convert.rs`, `dng/original.rs` |
| Sony `FocusPosition` / `FocusPosition2`? | **No** | GitHub code search `repo:dnglab/dnglab FocusPosition` → 2 hits total, both in `rawler/src/decoders/nef/lensdata.rs` and `rawler/src/decoders/pef.rs` (Nikon/Pentax only) |

`rawler` declares `rust-version = "1.89"`, `edition = "2024"` (VERIFIED, `rawler/Cargo.toml`).

**Sony maker-note focus data — where it actually lives (VERIFIED from ExifTool source)**

Reference: `exiftool/exiftool:lib/Image/ExifTool/Sony.pm` (11,969 lines). Note `exiftool.org/TagNames/Sony.html` 404s; use the GitHub raw Perl.

| Fact | Line(s) | Detail |
|---|---|---|
| Tag 0x9050 dispatch | 1789 | `0x9050 => [...]` variant list |
| A7C II uses **Tag9050d** | 1816-1821 | Condition matches `^(ILCE-(6700\|7CM2\|7CR)\|ILME-FX2\|ZV-(E1\|E10M2))\b`, LittleEndian |
| Tag9050d table | 8309-8789 | NOTES: "Valid for ILCE-6700/7CM2/7CR/ZV-E1…"; `PROCESS_PROC => \&ProcessEnciphered` |
| **FocusPosition2** | 8782-8786 | `0x002d => { Name => 'FocusPosition2' }`, FORMAT `int8u` (**one byte**), "seen values from 80 - 255 (= infinity)" |
| Encryption | 1776, `sub Decipher` 11517 | "simple substitution cipher… The formula is: `$c = ($b*$b*$b) % 249`"; values 249-255 untranslated. **~20 lines of Rust to reimplement.** |
| FocusDistance composite | 10895-10902 | `metres = FocusPosition * FocalLength / 1000`; `>=128` → inf |
| FocusDistance2 composite | 10904-10925 | `(2**($val/16-5) + 1) * FocalLengthIn35mmFormat / 1000`; `>=255` → inf |
| **Accuracy caveat** | 10917-10921 | Verbatim: *"This calculation may be wrong… The actual embedded data seems to be proportional to magnification not a focus distance."* |
| A7C II model ID | 2257 | `397` |

**Implication for focus stacking:** `FocusPosition2` is an 8-bit, non-linear, magnification-proportional value. **Good enough** for frame ordering, monotonicity/direction checks, gap detection, and a coarse scale prior. **Not good enough** as a metric focus-distance input to a depth model.

**Recommendation:** `rawler` 0.7.2 for decode + DNG write. **Deal-breaker risks:** (a) LGPL-2.1 — static linking in Rust triggers the relinking obligation, a first-order architecture decision; (b) no Sony FocusPosition — we must write our own Tag9050d parser + decipher (small, well-documented).

**EXIF/maker-note helper crates**

| Crate | Ver | License | Last release | Note |
|---|---|---|---|---|
| kamadak-exif | 0.6.1 | BSD-2-Clause | 2024-11-06 | No maker-note deciphering |
| nom-exif | 3.6.2 | "non-standard" (crates.io) | 2026-07-29 | License string is non-SPDX — audit before use |
| little_exif | 0.6.23 | MIT OR Apache-2.0 | 2026-01-13 | Read/write EXIF |
| rexiv2 | 0.10.0 | GPL-3.0-or-later | 2023-01-21 | exiv2 binding; GPL |

### 1.2 Demosaic

| Crate | Ver | License | Last release | Downloads | Algorithms |
|---|---|---|---|---|---|
| **demosaic** | 0.3.0 | MIT OR Apache-2.0 | 2026-02-18 | **866 total** | Bilinear, MHC, PPG, VNG, AHD; Quad-PPG + binning/remosaic; Markesteijn 1/3-pass, DHT (X-Trans) |
| bayer | 0.1.5 | MIT | 2017-07-22 | — | Dead |
| librtprocess (not on crates.io) | 0.12.0 | **GPL-3.0** | repo last pushed 2024-01-26 | — | ahd, **amaze, dcb, hphd, igv, lmmse, rcd**, vng4, bayerfast, markesteijn, xtransfast, CA_correct, HLRecovery_inpaint |

`demosaic` is pure Rust, `no_std`, f32 in / planar CHW f32 out; its own README says it is "*Not* blazingly fast" (VERIFIED, `naorunaoru/demosaic:README.md`).

**COULD NOT CONFIRM** any permissively-licensed Rust implementation of AMaZE, RCD, LMMSE, DCB, IGV, or Menon. Queries run on crates.io: `?q=demosaic&sort=downloads`, `?q=bayer&sort=downloads`, `?q=amaze`, `?q=rcd`. Nothing.

**Recommendation:** implement demosaic ourselves as GPU kernels (RCD and AMaZE are the quality targets; RCD is the more tractable port and is the modern RawTherapee default for most content). **Deal-breaker risk:** librtprocess is GPL-3.0, so we cannot copy its code — we must work from the published algorithm descriptions. This is a real engineering cost (weeks, not days) and should be scheduled as a first-class workstream, not assumed away.

### 1.3 Color management

| Crate | Ver | License | Last release | Total dl / 90d | Pure Rust? |
|---|---|---|---|---|---|
| **moxcms** | 0.9.0 | BSD-3-Clause OR Apache-2.0 | 2026-07-22 | 64.8 M / **33.1 M** | Pure Rust |
| lcms2 | 6.1.1 | MIT | 2025-07-13 | 6.02 M / 983 K | Binding |
| lcms2-sys | 4.0.7 | MIT | 2026-06-25 | 6.08 M / 994 K | C (Little-CMS) |
| qcms | 0.3.0 | MIT | 2024-01-09 | 2.73 M / 1.33 M | Pure Rust (Firefox) |
| colorutils-rs | 0.8.0 | BSD-3-Clause OR Apache-2.0 | 2026-04-12 | 196,290 / 34,212 | Pure Rust |
| palette | 0.7.7 | MIT OR Apache-2.0 | 2026-08-02 | 16.1 M / 8.07 M | Pure Rust |
| color (linebender) | 0.3.3 | Apache-2.0 OR MIT | 2026-05-05 | 4.30 M / 2.60 M | Pure Rust |
| kolor | 0.1.9 | MIT OR Apache-2.0 | 2023-04-25 | 19,705 | Stale |

`moxcms` scope (VERIFIED, README): pure-Rust ICC, CMYK⇄RGBX, RGBX⇄RGBX, LAB, GRAY, "any to any Display Class ICC up to 16 inks". 33.1 M downloads/90d — it is now a dependency of the mainstream `image` ecosystem.

**UNVERIFIED gap:** grepping the moxcms README for `f32`, `16-bit`, `HDR`, `PQ` returned nothing — its internal numeric precision and HDR transfer-function support were **not confirmed**.

**Recommendation:** `moxcms` 0.9.0 as primary (permissive, pure Rust, huge adoption), `lcms2` as the escape hatch for anything exotic. **Deal-breaker risk:** unconfirmed f32/HDR precision — validate with a round-trip test against lcms2 before committing.

### 1.4 Image IO

| Crate | Ver | License | Last release | Total dl | Role |
|---|---|---|---|---|---|
| tiff (image-tiff) | 0.11.3 | MIT | 2026-02-10 | 107.7 M | TIFF/BigTIFF |
| exr (exrs) | 1.74.2 | BSD-3-Clause | 2026-07-10 | 66.0 M | Pure-Rust OpenEXR |
| png | 0.18.1 | MIT OR Apache-2.0 | 2026-02-14 | 201.7 M | PNG |
| image | 0.25.10 | MIT OR Apache-2.0 | 2026-03-10 | 172.8 M | Umbrella |
| zune-image | 0.5.0 | MIT/Apache-2.0/Zlib | 2026-01-24 | 85,451 | Fast decoders |
| jxl-oxide | 0.12.6 | MIT OR Apache-2.0 | 2026-05-29 | 2.06 M | JXL **decoder only** |
| jpegxl-rs | 0.15.0+libjxl-0.12.0 | **GPL-3.0-or-later** | 2026-07-03 | 147,407 | libjxl binding (enc+dec) |
| ravif | 0.13.0 | BSD-3-Clause | 2026-01-19 | 41.4 M | AVIF encode |
| avif-serialize | 0.8.9 | BSD-3-Clause | 2026-05-07 | 41.8 M | AVIF container |
| libavif | 0.14.0 | BSD-2-Clause | 2024-07-05 | 81,083 | C binding |
| openexr (vfx-rs) | 0.11.0 | BSD-3-Clause | 2021-10-21 | 23,645 | Stale |
| dng (apertus) | 1.6.0 | **AGPL-3.0** | 2026-07-28 | 21,851 | DNG — AGPL, avoid |

**image-tiff capability audit (the critical one) — VERIFIED**

| Capability | Read | Write | Evidence |
|---|---|---|---|
| BigTIFF | ✔ | ✔ | README:8-41; `src/encoder/mod.rs:1114-1122` `TiffEncoder::new_big`, `write_bigtiff_header` |
| 32-bit float (IEEEFP Gray/RGB/RGBA/CMYK 32\|64) | ✔ | ✔ | README:8-41 |
| **Tiled** | **✔** | **✘** | Decode: `src/decoder/image.rs` has `ChunkType::Tile`, `tiles_across()`, `tiles_down()`, TileWidth/TileLength. Encode: `src/encoder/mod.rs` writes only `Tag::RowsPerStrip` (712, 892) and `Tag::StripOffsets` (936); grep `tile` in `src/encoder/*` → **no matches** |
| Compression decode | None, LZW, Deflate, PackBits, Fax4, JPEG, ZSTD | — | README |
| Compression encode | — | None, LZW, Deflate, PackBits | README |

**Deal-breaker:** we need to *write* tiled 32-bit-float BigTIFF (that is the natural intermediate/output format for a 33 MP HDR stack). `image-tiff` cannot. Options: (a) write our own tiled-BigTIFF encoder — the format is simple and this is ~500 lines; (b) bind libtiff. Recommend (a), because it also lets us control ZSTD/deflate predictor choice and tile sizes to match the GPU tile scheduler.

**Recommendation:** `tiff` 0.11.3 for reading, **our own tiled-float-BigTIFF writer** for output, `exr` 1.74.2 for OpenEXR interchange, `png` 0.18.1 for previews. Avoid `jpegxl-rs` (GPL) — use `jxl-oxide` if decode-only suffices; JXL *encoding* has no permissive Rust option (COULD NOT CONFIRM one; queries `?q=jpegxl`, `?q=jxl`).

### 1.5 GPU compute

| Crate | Ver | License | Last release | Total dl | Note |
|---|---|---|---|---|---|
| **wgpu** | 30.0.1 | MIT OR Apache-2.0 | **2026-08-22** | 32.2 M | Released the day of this survey |
| naga | 30.0.1 | MIT OR Apache-2.0 | 2026-08-22 | 35.1 M | Shader translation |
| ash | 0.38.0+1.3.281 | MIT OR Apache-2.0 | 2024-04-01 | 33.3 M | Raw Vulkan |
| vulkano | 0.35.2 | MIT OR Apache-2.0 | 2025-08-16 | 2.10 M | Safe Vulkan |
| **cudarc** | 0.19.9 | MIT OR Apache-2.0 | 2026-08-11 | 7.33 M | Repo now `chelsea0x3b/cudarc` |
| cust | 0.3.2 | MIT OR Apache-2.0 | **2022-02-16** | 463,250 | crates.io release 4 yrs stale |
| rustc_codegen_nvvm | 0.3.0 | MIT OR Apache-2.0 | 2022-02-07 | 16,755 | Rust-CUDA codegen |
| spirv-builder / spirv-std | 0.10.0-alpha.1 | MIT OR Apache-2.0 | 2026-04-17 | 232 K / 435 K | rust-gpu |
| cubecl / cubecl-cuda | 0.11.0-pre.2 | MIT OR Apache-2.0 | 2026-08-10 | 1.05 M / 1.03 M | Pre-release |
| burn | 0.22.0-pre.2 | MIT OR Apache-2.0 | 2026-08-10 | 1.26 M | ML framework |
| candle-core | 0.11.0 | MIT OR Apache-2.0 | 2026-06-26 | 7.23 M | ML framework |
| krnl | 0.1.1 | MIT OR Apache-2.0 | **2024-05-28** | 10,421 | Dormant |
| gpu-allocator | 0.28.0 | MIT OR Apache-2.0 | 2025-09-26 | 17.0 M | Vulkan/DX12 suballocator |
| vk-mem | 0.5.0 | MIT/Apache-2.0 | 2025-08-12 | 161,630 | VMA binding |
| direct-storage | 0.7.1 | Apache-2.0 OR MIT | 2025-09-09 | **11,213 (252/90d)** | Only real DirectStorage binding |
| microsoft-directstorage | 0.0.0 | — | — | 1,209 | Placeholder, empty |
| cudaforge | 0.1.6 | MIT OR Apache-2.0 | 2026-06-16 | 404,348 | "CUDA kernel builder for Rust with incremental builds" |
| nvrtc / nvptx | 0.1.3 / 0.2.3 | MIT | 2023 / 2018 | tiny | Dead |
| windows | 0.62.2 | MIT OR Apache-2.0 | 2025-10-06 | 301.6 M | Win32 bindings |

**wgpu 30.0.1 capability facts — VERIFIED** (`gfx-rs/wgpu:wgpu-types/src/features.rs`, `limits.rs`, `CHANGELOG.md`)

| Feature | State | Evidence |
|---|---|---|
| Subgroup ops | **✔ Available** — `SUBGROUP` (bit 38), `SUBGROUP_VERTEX` (39), `SUBGROUP_BARRIER` (40). WGSL: ballot/All/Any/Add/Mul/Min/Max/And/Or/Xor, prefix ops, shuffles, quad ops | `features.rs:1071-1082`; `CHANGELOG.md:3103-3115` |
| Subgroup size query | Moved from `Limits` to `AdapterInfo` (`subgroup_min_size`/`subgroup_max_size`) | CHANGELOG |
| f16 | **✔** `SHADER_F16` on Vulkan/Metal/DX12/WebGPU; WGSL `enable f16;`. Vulkan backend has an **f16 IO polyfill** so `storageInputOutput16` is not required (PR #7884) | `features.rs`; CHANGELOG |
| i16 / 16-bit storage | **✔** `SHADER_I16` (bit 34), `enable wgpu_int16;`. Vulkan needs `shaderInt16` + `VK_KHR_16bit_storage`; DX12 needs SM 6.2 `Native16BitShaderOpsSupported` | `features.rs:1125-1161` |
| **Cooperative matrix / tensor cores** | **✘ effectively unusable on NVIDIA.** `EXPERIMENTAL_COOPERATIVE_MATRIX` (bit 57), verbatim: *"The implementation currently only supports 8x8 f32 matrices… Most Vulkan implementations (NVIDIA, AMD) primarily support f16 inputs at larger sizes (e.g., 16x16), so Vulkan support may be limited."* | `features.rs:1406-1424` |
| Bindless | ✔ `wgpu_binding_array` enable directive, `PARTIALLY_BOUND_BINDING_ARRAY` (DX12 Tier 3 + Vulkan), `max_binding_array_elements_per_shader_stage` | `features.rs:1690-1699` |
| Default limits | `max_storage_buffers_per_shader_stage: 8`, `max_storage_buffer_binding_size: 128 MiB`, `max_buffer_size: 256 MiB`, **`max_compute_workgroup_storage_size: 16384` (16 KiB)**, `max_compute_invocations_per_workgroup: 256`, `max_compute_workgroups_per_dimension: 65535` | `limits.rs:436-458` |

Limits are requestable up to adapter limits, but **the Vulkan-side ceiling for compute workgroup shared memory on NVIDIA is far below the 99 KiB opt-in available through CUDA**. The exact NVIDIA Vulkan `maxComputeSharedMemorySize` was **not measured** (`vulkaninfo` not installed) → **UNVERIFIED**; commonly 48 KiB.

**Rust-CUDA / sm_120 — VERIFIED**

| Fact | Evidence |
|---|---|
| Repo `Rust-GPU/rust-cuda`, 5,326 stars, not archived, `pushed_at` 2026-08-17 (latest `main` commits 2026-05-03) | GitHub API |
| **Last GitHub release is "0.3", 2022-02-07** | GitHub releases |
| `Compute120`, `Compute120f`, `Compute120a` present in the NVVM arch enum (alongside 90/90a, 100/100f/100a, 101, 103, 110, 121) | `crates/nvvm/src/lib.rs:326-441` |
| CUDA 12.9+ base/`f`/`a` suffix semantics documented; `#[cfg(target_feature = "compute_120")]` gating | `crates/cuda_builder/src/lib.rs:96-137` |
| Naming: they use `compute_120`, not `sm_120` — code search `repo:Rust-GPU/rust-cuda sm_120` → `total_count: 0` | GitHub code search |

**Verdict:** sm_120 *is* targeted on `main`, but only via a git dependency. The published `cust` 0.3.2 / `rustc_codegen_nvvm` 0.3.0 are from **February 2022** and predate Blackwell entirely. Depending on Rust-CUDA means depending on an unreleased git ref — a supply-chain and reproducibility risk.

**cudarc 0.19.9 — VERIFIED**

| Fact | Evidence |
|---|---|
| Supports CUDA **11.4–11.8, 12.0–12.9, 13.0–13.3** (local UMD is 13.3 ✔) | README |
| Wraps driver API, NVRTC, cuRAND, cuBLAS, cuBLASLt, NCCL, cuDNN, cuSPARSE, cuSOLVER, **cuFILE (GPUDirect Storage)**, CUPTI, nvtx, cuFFT | README |
| Default feature `dynamic-loading` → **no CUDA libs needed at build time** | README |
| `CudaContext::load_module(Ptx)` accepts `PtxKind::Image` (**cubin bytes**), `::Src`, `::File`, `::Binary`; then `load_function(name)`, `stream.launch_builder(&f).arg(..).launch(cfg)` | `src/driver/safe/core.rs:2198-2240` |

**Verdict:** compiling CUDA C++ with an external `nvcc` to cubin/fatbin and loading it from Rust via `cudarc` is **fully supported and is the low-risk fast path**.

**Recommendation:** `wgpu` 30.0.1 as the portable baseline (**risk:** no tensor cores, 16 KiB default / ~48 KiB max workgroup shared memory, no TMA, no clusters); `cudarc` 0.19.9 + externally-`nvcc`-built cubins as the fast path (**risk:** requires a CUDA toolkit in the build environment for the fast path; ship it as an optional feature with prebuilt fatbins). Avoid `cust`/Rust-CUDA for production. `CubeCL` is interesting (single kernel source → CUDA + wgpu) but is at `0.11.0-pre.2` — evaluate, do not commit.

### 1.6 SIMD on CPU

| Crate | Ver | License | Last release | Total dl / 90d |
|---|---|---|---|---|
| wide | 1.6.1 | Zlib/Apache-2.0/MIT | 2026-08-07 | 67.4 M / 15.8 M |
| safe_arch | 1.2.0 | Zlib/Apache-2.0/MIT | 2026-08-14 | 66.5 M / 15.5 M |
| **pulp** | 0.22.3 | MIT | 2026-06-20 | 20.2 M / 8.36 M |
| multiversion | 0.8.0 | MIT OR Apache-2.0 | 2024-12-08 | 13.9 M / 1.99 M |
| fearless_simd | 0.7.0 | Apache-2.0 OR MIT | 2026-08-11 | 3.71 M / **2.67 M** (fast-rising, linebender) |
| raw-cpuid | 11.6.0 | MIT | 2025-09-05 | 158.3 M |
| cpufeatures | 0.3.0 | MIT OR Apache-2.0 | 2026-02-05 | 854.8 M |
| packed_simd_2 | 0.3.8 | — | 2022-06-01 | Dead |
| simd (hsivonen) | 0.2.5 | — | 2025-08-05 | Self-described "OBSOLETE: see core::simd" |

**`std::simd` status — VERIFIED**

| Fact | Evidence |
|---|---|
| Portable SIMD tracking issue **still open** (updated 2026-08-12) → `std::simd` remains **nightly-only** | `rust-lang/rust#86656` |
| **Open soundness/miscompile risk:** `rust-lang/rust#154152` "portable_simd: STATUS_HEAP_CORRUPTION on Windows MSVC with `Simd<u32, 16>` in tight loops" (updated 2026-03-21) | `rust-lang/rust#154152` |
| AVX-512 target features + intrinsics **stabilized in Rust 1.89.0 (2025-08-07)** (PR 138940, issue 111137) | `rust-lang/rust:RELEASES.md:1130, 1181` |
| `avx512fp16` intrinsics stabilized in **1.94.0 (2026-03-05)** | `RELEASES.md:500` |
| Current stable | **1.98.0 (2026-08-20)** — `RELEASES.md` head |

`#154152` is squarely on our platform (Windows MSVC) and our vector width (512-bit). That alone disqualifies `std::simd` for this project.

**Recommendation:** stable `core::arch` AVX-512 intrinsics (available since 1.89) wrapped by **`pulp`** (or `wide` for simple cases), with **`multiversion`** for runtime dispatch and `raw-cpuid`/`cpufeatures` for detection. **Deal-breaker risk for the alternative:** `std::simd` is nightly-only *and* has an open Windows-MSVC heap-corruption bug at 512-bit widths.

### 1.7 Parallelism and scheduling

| Crate | Ver | License | Last release | Total dl |
|---|---|---|---|---|
| rayon | 1.12.0 | MIT OR Apache-2.0 | 2026-04-14 | 506.6 M |
| chili | 0.2.1 | MIT OR Apache-2.0 | 2025-03-26 | 1.27 M |
| crossbeam | 0.8.4 | MIT OR Apache-2.0 | 2024-01-08 | 130.7 M |
| tokio | 1.53.1 | MIT | 2026-07-20 | 899.9 M |
| core_affinity | 0.8.3 | MIT/Apache-2.0 | 2025-03-01 | 33.4 M |
| hwlocality | 1.0.0-alpha.12 | MIT | 2026-04-05 | 462,630 |
| hwlocality-sys | 0.7.1 | MIT | — | 496,354 |
| thread_priority | 3.1.1 | MIT | 2026-06-20 | 10.5 M |
| num_cpus | 1.17.0 | MIT OR Apache-2.0 | 2025-05-30 | 565.2 M |
| hwloc2 | 2.2.0 | MIT | 2020-05-22 | 73,411 (dead) |
| affinity | 0.1.2 | MIT OR Apache-2.0 | 2021-10-16 | 1.4 M (dead) |

**CCD asymmetry — COULD NOT CONFIRM any CCD/V-Cache-aware Rust crate.** crates.io queries run: `?q=numa`, `?q=affinity`, `?q=topology`, `?q=cache+aware`, `?q=thread+pinning`. Nothing addresses AMD dual-CCD asymmetry. `hwlocality` (hwloc bindings, alpha) is the closest — it exposes full cache topology and binding but has no AMD-specific policy.

Practical answer, and what I did to prove it works: call `GetLogicalProcessorInformationEx` directly (Win32, via the `windows` crate) to read L3 instances and their affinity masks, then pin `rayon` worker threads with `core_affinity`. See §2.2 for the measured topology.

**Recommendation:** `rayon` 1.12.0 + **manual CCD-aware pinning** via `core_affinity` 0.8.3 driven by `GetLogicalProcessorInformationEx`. Build two rayon pools: a "cache pool" bound to the V-Cache CCD for large-tile/stencil work, and a "clock pool" bound to the frequency CCD for latency-sensitive or branchy work (entropy decode, LJPEG bitstream). **Deal-breaker risk:** none technically, but Windows' scheduler will fight explicit affinity if the process also uses the OS "preferred core" hints; verify with a pinned-vs-unpinned A/B before shipping. `chili` is an interesting low-overhead fork-join alternative but is small (1.27 M dl) and last released 2025-03-26.

### 1.8 IO

| Crate | Ver | License | Last release | Total dl / 90d | Platform |
|---|---|---|---|---|---|
| memmap2 | 0.9.11 | MIT OR Apache-2.0 | 2026-06-22 | 317.1 M | All |
| **compio** | 0.19.2 | MIT | **2026-08-18** | 758,872 / 382 K | **IOCP on Windows**, io_uring on Linux |
| io-uring | 0.7.14 | MIT OR Apache-2.0 | 2026-08-11 | 52.7 M | Linux only |
| tokio-uring | 0.5.0 | MIT | 2024-05-27 | 1.92 M | Linux only, stale |
| glommio | 0.9.0 | Apache-2.0 OR MIT | 2024-03-25 | 156,696 | Linux only, stale |
| monoio | 0.2.4 | MIT OR Apache-2.0 | 2024-08-20 | 1.36 M | Linux-first |
| direct-storage | 0.7.1 | Apache-2.0 OR MIT | 2025-09-09 | **11,213 / 252** | Windows |

**DirectStorage:** `direct-storage` 0.7.1 (Tsukisoft/direct-storage-rs) is the **only** real Rust binding. 252 downloads in 90 days is essentially zero adoption. `microsoft-directstorage` is a 0.0.0 name placeholder. The GPU-decompression path (GDeflate) is not useful to us anyway — ARW is not GDeflate-compressed, so DirectStorage would only give us the "bypass the CPU on the read path" half, which plain IOCP already approximates.

**Is overlapping the reads worth it?** 60 × ~60 MB ARW ≈ 3.6 GB. On a PCIe 4/5 NVMe (5–12 GB/s) that is **0.3–0.7 s of pure read**, versus tens of seconds of decode+align+merge. Overlapping is worth doing (it is free with a completion-based runtime) but is **not** a bottleneck. LJPEG entropy decode on CPU will dominate the ingest stage.

**Recommendation:** `memmap2` 0.9.11 for the simple path + `compio` 0.19.2 (IOCP) for overlapped prefetch of the next N files while decoding the current ones. **Deal-breaker risk:** DirectStorage via `direct-storage` 0.7.1 is high-risk (252 dl/90d, single maintainer) and low-reward here — do not put it on the critical path. Note `cudarc` exposes **cuFILE/GPUDirect Storage**, which is the more interesting long-term direct-to-VRAM path, though on Windows/WDDM GDS support is limited (UNVERIFIED — not tested).

### 1.9 Numerics

| Crate | Ver | License | Last release | Total dl |
|---|---|---|---|---|
| faer | 0.24.4 | MIT | 2026-06-24 | 4.15 M (repo moved to codeberg.org/sarah-quinones/faer) |
| nalgebra | 0.35.0 | Apache-2.0 | 2026-05-24 | 85.1 M |
| ndarray | 0.17.2 | MIT/Apache-2.0 | 2026-01-10 | 112.8 M |
| num-traits | 0.2.19 | MIT/Apache-2.0 | 2024-05-03 | 943.1 M |
| half | 2.7.1 | MIT/Apache-2.0 | 2025-10-14 | 424.2 M |
| rustfft | 6.4.1 | — | 2025-09-18 | 25.8 M |
| realfft | 3.5.0 | — | 2025-06-12 | — |
| bytemuck | 1.25.2 | — | 2026-07-19 | 340.0 M |
| zerocopy | 0.8.56 | — | 2026-08-06 | 829.6 M |

**Recommendation:** `nalgebra` 0.35.0 for small fixed-size geometry (homographies, 3×3 colour matrices, lens models), `faer` 0.24.4 for anything that becomes a real dense solve (global alignment bundle, least-squares fits), `half` 2.7.1 for f16/bf16 host-side, `bytemuck` for zero-copy GPU upload. **Deal-breaker risk:** `faer`'s repo moved to Codeberg — check the release cadence before depending on it for a core path; `nalgebra` alone covers most needs.

### 1.10 Testing, benchmarking, profiling, image-quality metrics

| Crate | Ver | License | Last release | Total dl |
|---|---|---|---|---|
| criterion | 0.8.2 | Apache-2.0 OR MIT | 2026-02-04 | 263.3 M |
| divan | 0.1.21 | MIT OR Apache-2.0 | 2025-04-10 | 6.77 M |
| insta | 1.48.0 | Apache-2.0 | 2026-06-11 | 91.1 M |
| proptest | 1.11.0 | MIT OR Apache-2.0 | 2026-03-24 | 172.7 M |
| tracy-client | 0.18.4 | MIT/Apache-2.0 | 2026-01-05 | 11.4 M |
| puffin | 0.20.0 | MIT OR Apache-2.0 | 2026-03-18 | 5.45 M |
| pprof | 0.14.1 | Apache-2.0 | 2025-07-23 | 46.8 M |
| **ssimulacra2** | 0.5.1 | BSD-2-Clause | 2024-12-29 | 37,532 |
| **butteraugli** | 0.9.3 | BSD-3-Clause | 2026-05-28 | 37,132 (18.8 K/90d), pure Rust, imazen |
| dssim / dssim-core | 3.4.0 | **AGPL-3.0** | 2025-09-21 | 233 K / 501 K |
| image-compare | 0.5.0 | MIT | 2025-08-18 | 1.72 M |

**Recommendation:** `divan` for microbenchmarks (lower ceremony, better for kernel sweeps), `criterion` for the regression-tracked headline benchmarks, `tracy-client` 0.18.4 for frame/stage timeline profiling (it correlates CPU and GPU zones, which is exactly what a hybrid pipeline needs), `insta` + `proptest` for correctness, `ssimulacra2` 0.5.1 + `butteraugli` 0.9.3 for quality regression gates. **Deal-breaker risk:** `dssim` is **AGPL-3.0** — do not link it, even in dev-dependencies, if the binary is ever distributed. `ssimulacra2` last released 2024-12-29 (stale but the metric is frozen anyway).

### 1.11 CLI / UI

| Crate | Ver | License | Last release | Total dl |
|---|---|---|---|---|
| egui / eframe | 0.36.1 | MIT OR Apache-2.0 | 2026-08-07 | 22.0 M / 17.0 M |
| iced | 0.14.0 | MIT | 2025-12-07 | 2.57 M |
| tauri | 2.11.5 | — | 2026-07-01 | 26.9 M |
| dioxus | 0.8.0-alpha.1 | — | 2026-07-31 | 2.39 M |
| slint | 1.17.1 | **GPL-3.0-only OR commercial** | 2026-07-07 | 1.52 M |

**Recommendation:** `egui`/`eframe` 0.36.1. It is the only option that runs *on top of `wgpu`*, which means the 33 MP HDR image never leaves the GPU — we render our own `wgpu` texture into the egui frame and do tone-mapping in a shader. `iced` also uses wgpu but is smaller. Tauri/Dioxus push pixels through a webview, which is wrong for a 33 MP HDR viewer. **Deal-breaker risk:** egui is immediate-mode and its colour management is sRGB-centric; HDR/wide-gamut display output would need custom surface configuration (UNVERIFIED whether egui 0.36 exposes HDR swapchain formats). Avoid `slint` (GPL-or-commercial).

### 1b Licensing risk register (first-order architecture decision)

| Crate | License | Consequence |
|---|---|---|
| rawler, rawloader, quickraw | LGPL-2.1 | Static linking in Rust triggers the relinking obligation. Either dynamically load, or ship object files, or accept LGPL-adjacent distribution terms. |
| imagepipe | LGPL-3.0-only | Same, and GPLv3-family. |
| libopenraw | LGPL-3.0-or-later | Same. |
| librtprocess | GPL-3.0 | **Cannot copy code.** Reimplement AMaZE/RCD from published descriptions. |
| dssim, dssim-core | AGPL-3.0 | Do not link if distributing. |
| dng (apertus) | AGPL-3.0 | Do not link. |
| jpegxl-rs | GPL-3.0-or-later | Do not link; use `jxl-oxide` (decode-only, MIT/Apache). |
| slint | GPL-3.0-only OR commercial | Avoid unless buying a licence. |
| rexiv2 | GPL-3.0-or-later | Avoid. |
| nom-exif | "non-standard" per crates.io | Audit the actual LICENSE file before use. |

**The single biggest licensing decision:** `rawler` is LGPL-2.1 and is also *the only crate that decodes A7C II lossless-compressed ARW and writes DNG*. There is no permissive alternative. Options: (1) accept LGPL and structure `rawler` as a dynamically-loaded plugin behind our plugin ABI — which the pluggable design already calls for; (2) license the whole app under a GPL-family licence; (3) write our own ARW decoder. **(1) is the strongest fit for the stated pluggable architecture** and should be an explicit design constraint on the plugin boundary from day one.

---

## §2 Hardware envelope

### 2.1 RTX 5090 / Blackwell sm_120

All rows MEASURED-LOCALLY via `nvcuda.dll` driver API (`cuDeviceGetAttribute`) unless noted.

| Property | Value | Attr ID |
|---|---|---|
| Name / compute capability | NVIDIA GeForce RTX 5090 / **12.0 (sm_120)** | — |
| **SM count** | **170** | 16 |
| **L2 cache** | 100,663,296 B = **96 MiB** | 38 |
| **Max persisting L2** | 62,914,560 B = **60 MiB** | 108 |
| Max access-policy window | 134,217,728 B = 128 MiB | 109 |
| Memory bus width | **512 bits** | 37 |
| Memory clock | 14,001,000 kHz (28 Gbps GDDR7 effective) | 36 |
| **VRAM bandwidth (derived)** | **~1792 GB/s** — 512 bit × 28 Gbps ÷ 8. **UNVERIFIED** as a spec figure (TechPowerUp behind bot-check, amd/nvidia pages unreachable) | — |
| Total VRAM | 34,190,458,880 B = **31.84 GiB** | — |
| Shared mem / SM (max) | 102,400 B = **100 KiB** | 81 |
| **Shared mem / block (opt-in)** | 101,376 B = **99 KiB** | 97 |
| Max threads / SM | **1536** (= 48 warps) | 39 |
| Max blocks / SM | **24** (driver) — **Tuning Guide text says 32; discrepancy unexplained** | 106 |
| Warp size | 32 | — |
| **CLUSTER_LAUNCH** | **1 → thread block clusters / DSMEM ARE available on sm_120** | 120 |
| **TENSOR_MAP_ACCESS_SUPPORTED** | **1 → TMA tensor maps ARE available on sm_120** | 127 |
| Timeline semaphore interop | 1 | 114 |
| Memory pools | 1 | 115 |
| Mem-sync domain count | 4 | 126 |
| **Async engine count** | **1** | 40 |
| GPU overlap | 1 | 15 |
| Pageable mem access / concurrent managed | 0 / 0 | 88 / 89 |
| DMA-buf supported | 0 | 124 |
| **BAR1 size** | **32768 MiB — full ReBAR, entire VRAM host-visible** (`nvidia-smi -q`) | — |
| Max SM clock / mem clock | 3090 MHz / 14001 MHz (`nvidia-smi --query-gpu`) | — |
| PCIe | **gen 5 × 16** (max and current, `nvidia-smi --query-gpu`) | — |

> **Caution for anyone reproducing this:** `CUdevice_attribute` IDs 122–132 are easy to mis-map and I got them wrong on the first pass. Correct: 122 `CAN_USE_64_BIT_STREAM_MEM_OPS`, 123 `CAN_USE_STREAM_WAIT_VALUE_NOR`, 124 `DMA_BUF_SUPPORTED`, 125 `IPC_EVENT_SUPPORTED`, 126 `MEM_SYNC_DOMAIN_COUNT`, **127 `TENSOR_MAP_ACCESS_SUPPORTED`**, 128 `HANDLE_TYPE_FABRIC_SUPPORTED`, 129 `UNIFIED_FUNCTION_POINTERS`.

**sm_120 feature verdicts from NVIDIA primary docs — VERIFIED**

Source A: Blackwell Tuning Guide, `https://docs.nvidia.com/cuda/blackwell-tuning-guide/index.html` (static HTML, parses fine).
Source B: PTX ISA guide, `https://docs.nvidia.com/cuda/parallel-thread-execution/index.html` (3.5 MB static HTML).

| Question | Verdict | Evidence |
|---|---|---|
| Max concurrent warps/SM | **48** for cc 12.0 (64 for cc 10.0) | Source A, verbatim |
| Shared memory capacity/SM | **128 KB** for cc 12.0 (228 KB for cc 10.0). Driver reports 100 KiB *usable* — 128 KB is the unified L1/shmem block | Source A + attr 81 |
| Max shared memory per thread block | **99 KB** for cc 12.0 | Source A, verbatim; matches attr 97 |
| Static shared allocation limit | still 48 KB without `cudaFuncAttributeMaxDynamicSharedMemorySize` opt-in | Source A |
| **Thread block clusters** | **✔ SUPPORTED.** "Thread block clusters are supported by Blackwell GPUs as well. A thread block can read from, write to, and perform atomics in shared memory of other thread blocks within its cluster. This is known as Distributed Shared Memory." Max portable cluster size 8 | Source A, verbatim |
| DSMEM bandwidth | "Distributed Shared Memory can be used by an SM simultaneously with L2 cache accesses… combined bandwidth of both distributed shared memory and L2" | Source A, verbatim |
| Cluster ISA availability | "Cluster level is applicable only on target architecture **sm_90 or higher**" — sm_120 qualifies | Source B, line 861; `.cluster` / `::cluster` qualifiers at 12539-12542, 12840-12842, 13408, 13467 |
| **TMA (`cp.async.bulk.tensor`)** | **✔ SUPPORTED with restrictions.** §9.7.9.26.5.1 "Restriction on Tensor Copy instructions": "*Following are the restrictions for sm_120a: `cp.async.bulk.tensor` with the direction `.shared::cluster.global` doesn't support: the sub-byte types; the qualifier `.swizzle_atomicity`*" | Source B, lines 14926-14927, 14958-14961; corroborated by driver attr 127 = 1 |
| PTX max shared memory table | sm_90a 228 KB, sm_100a/103a 228 KB, sm_110a 228 KB, **sm_120a/121a 100 KB** | Source B, ~lines 2245-2261 |
| `sm_120` mentions in PTX ISA | 109 total; `sm_120a` = arch-specific (MMA, sub-byte), `sm_120f` = family-specific | Source B |

**Headline correction to a common assumption:** TMA and thread-block clusters are *often* described as Hopper-sm_90-and-datacenter-only. On this consumer sm_120 part they are **both present and confirmed two independent ways** (driver attribute + PTX ISA restriction text that only makes sense if the instruction exists). The real sm_120 limitation versus sm_100 is **shared memory: 100 KB vs 228 KB**, and **48 warps/SM vs 64**.

**Tensor cores:** sm_120a arch-specific MMA including sub-byte types is referenced throughout the PTX ISA. Exact supported type matrix (fp8 e4m3/e5m2, fp4, bf16) was **not** exhaustively enumerated — the CUDA C Programming Guide is JS-rendered and could not be parsed (see §6). **UNVERIFIED** at the level of a definitive per-type table. For a focus-stacking pipeline this matters little: our hot kernels are stencil/reduction/convolution, not GEMM. Tensor cores would only pay off if we add a learned focus-measure or a learned denoiser.

### 2.2 Ryzen 9 9950X3D

MEASURED-LOCALLY via `GetLogicalProcessorInformationEx` and `Get-CimInstance Win32_Processor`.

| Property | Value |
|---|---|
| Cores / threads | **16 C / 32 T**, single processor group |
| **L3 instance 1** | **98,304 KB (96 MB), LPs 0–15** → **3D V-Cache CCD** (cores 0–7) |
| **L3 instance 2** | **32,768 KB (32 MB), LPs 16–31** → **frequency CCD** (cores 8–15) |
| L2 | 16 × 1024 KB unified, 16-way, per core |
| L1D / L1I | 48 KB 12-way / 32 KB 8-way; line 64 B |
| Max clock (CIM) | 4300 MHz base-ish reported value |
| RAM | 2 × 32 GB DDR5-6000 (G.Skill F5-6000J3040G32G) → **~96 GB/s theoretical dual-channel (derived, UNVERIFIED as achievable)** |
| OS | Windows 11 Home 10.0.26200 |

**Actionable:** affinity mask `LPs 0–15` = cache-resident work (large-tile stencils, pyramid levels that fit in 96 MB, LJPEG Huffman tables + working set); `LPs 16–31` = clock-sensitive/branchy work. The asymmetry is *measurable at the OS level* — no guessing required, and no crate needed.

### 2.3 AVX-512 on Zen 5

**Measured CPUID feature bits (MEASURED-LOCALLY, raw CPUID leaf 7 via `ctypes` + `VirtualAlloc`):**

| Present | Absent |
|---|---|
| AVX512 **F, DQ, IFMA, CD, BW, VL** | **AVX512_FP16** ✘ |
| **VBMI, VBMI2, VNNI, BITALG, VPOPCNTDQ, VP2INTERSECT, BF16** | AVX_IFMA ✘ |
| **AVX_VNNI** | SHA512 ✘, AVX10 ✘ |

**Full-width (not double-pumped) evidence — VERIFIED at compiler-model level:**

| Evidence | Source |
|---|---|
| `X86_TUNE_AVX512_SPLIT_REGS` ("AVX512 ops are split into two AVX256 ops") is enabled for `m_ZNVER4 \| m_C86_4G_M7 \| m_C86_4G_M8` — **and NOT for `m_ZNVER5`** | `gcc-mirror/gcc:gcc/config/i386/x86-tune.def:646-648` |
| `X86_TUNE_AVOID_512FMA_CHAINS` **is** set for `m_ZNVER5 \| m_ZNVER6` — GCC still avoids tight 512-bit FMA dependency chains on Zen 5 | `x86-tune.def:590-593` |
| `AVOID_FALSE_DEP_FOR_TZCNT` / `..._FOR_BLS` are Zen5-only | `x86-tune.def:372-380` |
| `ZN5AdditionalFeatures = [MOVDIRI, MOVDIR64B, VP2INTERSECT, PREFETCHI, AVXVNNI]` on top of ZN4 (F/CDI/DQI/BWI/VLX/VBMI/VBMI2/IFMA/VNNI/BITALG/GFNI/BF16/VPOPCNTDQ) — **exactly matches my CPUID dump** | `llvm/llvm-project:llvm/lib/Target/X86/X86.td:1753-1760` |
| `znver5` reuses `Znver4Model`; there is no separate `X86ScheduleZnver5.td` | `X86.td:2207-2211` (the file 404s) |
| AVX512_FP16 is a **Zen 6** feature per `ZN6AdditionalFeatures` | `X86.td` |

**Conclusion:** Zen 5 **is full-width 512-bit** (GCC drops the split-register tuning that it applies to Zen 4). This is **VERIFIED at compiler-model level, UNVERIFIED at measured-throughput level** — I **COULD NOT CONFIRM** with an independent measurement: chipsandcheese.com URLs tried all returned 404, amd.com product pages timed out, TechPowerUp is behind a bot check.

**Best current way to write portable-but-AVX-512-capable Rust:** stable `core::arch` AVX-512 intrinsics (stabilized 1.89.0, 2025-08-07) inside `#[target_feature(enable = "avx512f,avx512bw,avx512vl,avx512dq")]` functions, dispatched at runtime by `multiversion` 0.8.0 or hand-rolled `is_x86_feature_detected!`, with `pulp` 0.22.3 providing the generic-over-ISA abstraction so the same algorithm body compiles for SSE4/AVX2/AVX-512. **Do not** use `std::simd`. Note `avx512fp16` intrinsics exist since 1.94.0 but **this CPU does not have the feature** — do not build an f16 CPU path around it; use `half` + AVX-512BW/BF16 conversions instead (BF16 *is* present).

### 2.4 PCIe and host↔device bandwidth

| Metric | Value | Label |
|---|---|---|
| Link | PCIe **gen 5 × 16** (max and current) | MEASURED-LOCALLY (`nvidia-smi --query-gpu`) |
| **Pinned H2D** | **56.9 GB/s** (256 MiB transfer, best of 5) | MEASURED-LOCALLY |
| **Pinned D2H** | **55.7 GB/s** | MEASURED-LOCALLY |
| Caveat | The GPU was ~90 % busy with another process during the measurement → **these are lower bounds** | — |
| BAR1 | 32768 MiB = full VRAM host-visible (ReBAR on) | MEASURED-LOCALLY |
| Async engines | 1 | MEASURED-LOCALLY (attr 40) |

**Does pinned/write-combined memory + `cudaMemcpyAsync` overlap matter at our sizes?** **Yes, decisively.** A 400 MB f32 RGB frame at 56.9 GB/s is **~7 ms**; a 66 MB u16 Bayer frame is **~1.2 ms**. Both are far shorter than any realistic per-frame compute (align + focus measure + merge on 33 MP). With pinned buffers and 3 streams, PCIe transfer disappears entirely behind compute. Without pinning, pageable copies go through a staging buffer and typically halve throughput — so pinning is mandatory, not optional. `ASYNC_ENGINE_COUNT = 1` means **one copy direction at a time** overlaps with compute, so structure as: stream A = H2D of frame *n+1*, stream B = compute on frame *n*, stream C = D2H of result *n−1*, with events serialising the copy engine.

---

## §3 wgpu vs CUDA — the capability gap

| Capability | wgpu 30.0.1 | CUDA on sm_120 | Consequence for us |
|---|---|---|---|
| Subgroup ops (ballot/reduce/scan/shuffle/quad) | **✔** `SUBGROUP`/`SUBGROUP_BARRIER` | ✔ warp intrinsics | **No gap.** Focus-measure reductions and prefix sums port cleanly. |
| f16 arithmetic + storage | **✔** `SHADER_F16`, WGSL `enable f16;`, Vulkan f16-IO polyfill | ✔ `__half`/`__half2` | **No gap.** f16 residency strategy works on both. |
| i16 / 16-bit storage buffers | **✔** `SHADER_I16` (`enable wgpu_int16;`) | ✔ | **No gap.** u16 Bayer stays packed on both paths. |
| **Tensor cores / cooperative matrix** | **✘ practically.** `EXPERIMENTAL_COOPERATIVE_MATRIX`, **8×8 f32 only**; NVIDIA Vulkan exposes 16×16 f16 → no match | ✔ full `mma`/`wgmma`, sub-byte types on sm_120a | Only matters if we add learned components. Portable path simply omits them. |
| **Workgroup shared memory** | **16 KiB default**, adapter-capped (NVIDIA Vulkan commonly 48 KiB — **UNVERIFIED locally**) | **99 KiB opt-in** | **Real gap.** CUDA can hold a 2× larger stencil tile in shared memory → fewer passes, less L2 traffic. |
| **TMA (`cp.async.bulk.tensor`)** | **✘ no exposure** | **✔ confirmed** (driver attr 127, PTX §9.7.9.26.5.1) | CUDA path gets hardware-descriptor-driven async tile loads with automatic bounds/swizzle. |
| **Thread block clusters / DSMEM** | **✘ no exposure** | **✔ confirmed** (driver attr 120, Tuning Guide) | CUDA path can share tile halos across up to 8 blocks without a round trip to L2. |
| Async copy / multi-stream overlap | ✔ via queue submission, but no explicit copy-engine control | ✔ explicit streams + events + `cudaMemcpyAsync` on pinned memory | CUDA path has finer control of the single async engine. |
| Timeline semaphores | ✔ internally | ✔ (`TIMELINE_SEMAPHORE_INTEROP_SUPPORTED = 1`) | No gap. |
| Bindless | ✔ `wgpu_binding_array`, DX12 Tier 3 / Vulkan | ✔ | No gap. |
| Persisting L2 carve-out | ✘ | **✔ 60 MiB** via `cudaAccessPolicyWindow` | CUDA can pin the reference-frame pyramid in L2. |
| GPUDirect Storage | ✘ | ✔ via `cudarc` cuFILE (Windows/WDDM support UNVERIFIED) | Long-term only. |
| Max buffer size default | 256 MiB (`max_buffer_size`), 128 MiB per storage binding | Limited by VRAM | **Real gap.** Must request raised limits; still forces chunking of 400 MB frames into multiple bindings. |

**Verdict:** wgpu is a *fully viable* portable baseline for this workload — subgroups and f16/i16 are the features that actually matter for stencil/reduction image processing, and they are all present. The CUDA fast path buys **shared-memory capacity (99 KiB vs ~48 KiB), TMA, clusters/DSMEM, explicit stream control, and the 60 MiB persisting-L2 carve-out**. Expect a meaningful but not order-of-magnitude gap — the design should not be *architected around* CUDA, but the hot kernels should be written so a CUDA variant can be dropped in per-kernel.

---

## §4 Memory and streaming strategy for a 24 GB working set on a 32 GB GPU

### 4.1 Published precedents

| System | Pattern | Evidence |
|---|---|---|
| **OpenImageIO ImageCache** | Tile-granular LRU cache over many files; automatically closes least-recently-used file handles; filename-keyed, thread-safe, no explicit open/close. Verbatim: *"It is reasonable to access thousands of image files totalling hundreds of GB of pixels, efficiently and using a memory footprint on the order of 50 MB."* | `AcademySoftwareFoundation/OpenImageIO:src/doc/imagecache.rst:16-46` (CC-BY-4.0) |
| **libvips** | Verbatim: *"demand-driven, horizontally threaded"* — operations are lazy; a sink pulls regions and each worker evaluates a horizontal strip of the whole pipeline. Peak memory is O(threads × strip), not O(image). | `libvips/libvips:README.md:9-13` |
| **Google HDR+ (Halide)** | Verbatim: *"align — Aligns multiple raw RGGB frames of a scene in `T_SIZE x T_SIZE` tiles which overlap by `T_SIZE_2` in each dimension"*. Coarse-to-fine Gaussian pyramid with `DOWNSAMPLE_RATE` per layer; L1-distance scoring reduced over a 16×16 `RDom`; `num_tx = width/T_SIZE_2 - 1`. **Alignment runs on the Bayer mosaic, not on demosaiced RGB.** | `timothybrooks/hdr-plus:src/align.cpp:22, 30, 50-55, 71-74, 101-106, 118-123` (MIT) |
| Blender Cycles tile scheduler; Halide scheduling primitives | **COULD NOT CONFIRM** — not fetched. Listed as a follow-up. | — |

### 4.2 The recommendation

**The 24 GB figure is a self-inflicted wound.** It comes from choosing f32 RGB as the resident representation. Do not do that.

| Step | Action | Working-set effect |
|---|---|---|
| **1. Never materialise f32 RGB** | Keep frames resident as **u16 Bayer** (33 MP × 2 B ≈ **66 MB/frame**) or, where a demosaiced form is genuinely needed, **f16 planar RGB** (~200 MB/frame). Demosaic on the fly, per tile, in-kernel. | **60 frames of u16 Bayer ≈ 4 GB** — fits in VRAM with 28 GB to spare. Both `SHADER_F16`/`SHADER_I16` (wgpu) and `__half`/u16 (CUDA) support this. |
| **2. Align in the Bayer domain** | Follow HDR+: coarse-to-fine pyramid alignment on the mosaic. Avoids demosaicing 60 frames just to align them, and is the quality-correct choice for a RAW-native pipeline. | Removes the largest single source of intermediate memory. |
| **3. Overlapping-tile scheduler** | Partition the *output* into tiles with a `T_SIZE/2`-style overlap (HDR+ pattern) so alignment and blend seams are handled. For each tile, gather the corresponding motion-compensated source region from every frame. | Per-tile working set = tile_area × frames × 2 B — **megabytes, not gigabytes**. This is the core of the design. |
| **4. Persist pyramids, not pixels** | Keep the 1/4 and 1/16 alignment pyramids resident (≈6 % of full size) and re-stream full-res data only per tile. Pin the reference frame's pyramid in the **60 MiB persisting L2 carve-out** on the CUDA path. | ~250 MB for 60 frames of pyramid. |
| **5. Out-of-core LRU over host RAM** | Model the frame store on **OIIO's ImageCache**: tile-granular, LRU, with host RAM (64 GB) as the L4 tier and NVMe as L5. A pull-based/demand-driven evaluation (libvips model) means we never plan a full-image allocation. | Bounded, tunable peak memory; degrades gracefully at 100+ frames. |
| **6. Triple-buffered async PCIe** | Pinned host buffers + 3 CUDA streams (H2D / compute / D2H), events serialising the **single** async copy engine. Measured 56.9 GB/s → a 66 MB u16 frame moves in **1.2 ms**, a 400 MB f32 frame in **7 ms**. Full 32 GB ReBAR means the host can also write directly into VRAM where that is simpler. | Transfer fully hidden behind compute. |
| **7. Exploit sm_120 shared memory on the CUDA path** | 99 KiB opt-in shared memory + **TMA** + **clusters/DSMEM** for the stencil-heavy kernels (focus measure, guided filter, Laplacian-pyramid blend). DSMEM lets neighbouring tile blocks exchange halos without an L2 round trip. | Fewer passes over VRAM; the pipeline is memory-bound, so pass count is the metric that matters. |
| **8. wgpu fallback shape** | Because wgpu caps workgroup shared memory near 48 KiB and exposes neither TMA nor clusters, the portable path uses **smaller tiles and more passes**. Same algorithm, different tile constants — parameterise tile size per backend. | Measurable but not catastrophic gap. |
| **9. Disk** | Overlap ARW reads with decode via `compio` (IOCP). 60 × 60 MB = 3.6 GB ≈ 0.3–0.7 s on NVMe — never the bottleneck. LJPEG entropy decode on CPU will dominate ingest; parallelise it across both CCDs with `rayon`. | Ingest hidden behind GPU work after the first 2–3 frames. |

**Summary answer:** not "tiled streaming *or* out-of-core *or* half precision" — **all three, in that priority order, with 16-bit Bayer residency doing most of the work.** Get the representation right first (24 GB → 4 GB) and the out-of-core machinery becomes an insurance policy for 100+-frame stacks rather than a hard requirement for 60.

---

## §5 Recommended stack, one line per area

| Area | Recommendation | Deal-breaker risk |
|---|---|---|
| RAW decode | `rawler` 0.7.2 | **LGPL-2.1** (isolate behind the plugin boundary) + no Sony FocusPosition (write our own Tag9050d decipher) |
| Maker notes | Our own Tag9050d parser, modelled on ExifTool `Sony.pm` | FocusPosition2 is 8-bit and magnification-proportional — ordering prior only, not metric |
| Demosaic | **Write our own GPU RCD/AMaZE** | No permissive Rust implementation exists; `librtprocess` is GPL so we cannot copy. Real multi-week cost. |
| Colour | `moxcms` 0.9.0, `lcms2` 6.1.1 as escape hatch | moxcms f32/HDR precision UNVERIFIED — round-trip test first |
| TIFF | `tiff` 0.11.3 read + **our own tiled-float-BigTIFF writer** | image-tiff encoder cannot write tiles at all |
| EXR / PNG | `exr` 1.74.2 / `png` 0.18.1 | None |
| GPU portable | `wgpu` 30.0.1 | No tensor cores, ~48 KiB shmem, no TMA/clusters, 256 MiB default max buffer |
| GPU fast path | `cudarc` 0.19.9 + nvcc-built cubins | Needs CUDA toolkit at build time; ship prebuilt fatbins. **Avoid `cust`/Rust-CUDA** (crates.io release 2022-02) |
| SIMD | `pulp` 0.22.3 + `multiversion` 0.8.0 on stable AVX-512 intrinsics | `std::simd` is nightly-only (#86656) **and** has an open Windows-MSVC heap-corruption bug (#154152) |
| Parallelism | `rayon` 1.12.0 + `core_affinity` 0.8.3 + `GetLogicalProcessorInformationEx` | No CCD/V-Cache-aware crate exists; Windows scheduler may fight explicit affinity |
| IO | `memmap2` 0.9.11 + `compio` 0.19.2 (IOCP) | DirectStorage only via `direct-storage` 0.7.1 at **252 dl/90d** — high risk, low reward |
| Numerics | `nalgebra` 0.35.0 + `faer` 0.24.4 + `half` 2.7.1 | faer moved to Codeberg — check cadence |
| Bench / profile | `divan` 0.1.21 + `criterion` 0.8.2 + `tracy-client` 0.18.4 | None |
| Quality metrics | `ssimulacra2` 0.5.1 + `butteraugli` 0.9.3 | **`dssim` is AGPL-3.0 — do not link** |
| UI (later) | `egui`/`eframe` 0.36.1 | HDR swapchain exposure UNVERIFIED; sRGB-centric colour handling |

---

## §6 Gaps, could-not-confirms, and follow-ups

| Item | Status | Exact query / attempt |
|---|---|---|
| NVIDIA Vulkan `maxComputeSharedMemorySize` on the 5090 | **UNVERIFIED** | `vulkaninfo` not installed; not permitted to install. Assumed 48 KiB. |
| Tuning Guide "32 blocks/SM" vs driver `MAX_BLOCKS_PER_MULTIPROCESSOR = 24` | **Unexplained discrepancy** | Both read directly; no reconciling text found. |
| RTX 5090 VRAM bandwidth as a *published spec* | **UNVERIFIED** (1792 GB/s is derived from measured bus width × measured clock × 2) | TechPowerUp GPU database → bot check; nvidia.com product pages not reachable. |
| Zen 5 measured AVX-512 throughput | **COULD NOT CONFIRM** | chipsandcheese.com — three URLs tried, all 404. amd.com — timeout. Compiler-model evidence only (GCC/LLVM). |
| DDR5-6000 *achievable* bandwidth | **UNVERIFIED** (~96 GB/s theoretical, derived) | Not measured — would require running a benchmark, out of scope. |
| sm_120 tensor-core supported type matrix (fp8 e4m3/e5m2, fp4, bf16) | **UNVERIFIED** in full | CUDA C Programming Guide is JS-rendered (~27 KB shell HTML only). Subpages `03-advanced/feature-survey.html` and `05-appendices/compute-capabilities.html` → 404. Archive URLs `docs.nvidia.com/cuda/archive/{13.0,12.9,12.8}/cuda-c-programming-guide/index.html` → all 404. |
| `libopenraw` 0.4.0-alpha A7C II support / CFA exposure | **Not investigated** | Only crates.io metadata fetched. Follow-up if rawler's LGPL becomes a blocker (though libopenraw is LGPL-3.0 too). |
| `moxcms` numeric precision / HDR transfer functions | **UNVERIFIED** | README grep for `f32`, `16-bit`, `HDR`, `PQ` → no matches. |
| Blender Cycles tile scheduler; Halide scheduling docs | **COULD NOT CONFIRM** | Not fetched. Suggested follow-up: `blender/blender` `intern/cycles/integrator/tile.cpp`; `halide/Halide` tutorials on `tile`/`compute_at`/`store_at`. |
| cuFILE / GPUDirect Storage on Windows WDDM | **UNVERIFIED** | `cudarc` exposes it; Windows support not tested. |
| `nom-exif` actual license | **UNVERIFIED** | crates.io reports the non-SPDX string "non-standard". Read the repo LICENSE before use. |
| Permissive Rust JPEG XL *encoder* | **COULD NOT CONFIRM** | crates.io `?q=jpegxl`, `?q=jxl` — only `jxl-oxide` (decode-only) and `jpegxl-rs` (GPL). |
| Any CCD/V-Cache-aware Rust scheduling crate | **COULD NOT CONFIRM** | crates.io `?q=numa`, `?q=affinity`, `?q=topology`, `?q=cache+aware`, `?q=thread+pinning`. |
| Permissive Rust AMaZE/RCD/LMMSE/DCB/IGV/Menon | **COULD NOT CONFIRM** | crates.io `?q=demosaic`, `?q=bayer`, `?q=amaze`, `?q=rcd`. |
| Published `dnglab` library crate | **COULD NOT CONFIRM** | `https://crates.io/api/v1/crates/dnglab` → 404. Also `rawspeed-sys`, `dcraw` → 404. |

### Reproduction notes for this environment

- PowerShell has no heredoc: use `@'` … `'@ | python -` for inline Python. Guard `print` against non-ASCII (a 🔥 in a crates.io description caused a `charmap` codec crash).
- `Invoke-WebRequest -UseBasicParsing` on `raw.githubusercontent.com`, split on newlines, manual index loop = reliable remote grep with line numbers. `gh api .../contents/... --jq .content` + base64 mangles long lines — prefer raw.githubusercontent.
- `gh api repos/OWNER/REPO/git/trees/HEAD?recursive=1 --jq '.tree[].path'` for whole-repo listings; `gh api "search/code?q=repo:OWNER/REPO+TERM"` for content search.
- The Blackwell Tuning Guide and the PTX ISA guide are **static HTML and parse fine**; the CUDA C Programming Guide is not.

---

# Follow-up 1

New measurement taken for this section (MEASURED-LOCALLY, `nvcuda.dll` driver API, 512 MiB buffers, best of 7):

| Metric | Value |
|---|---|
| **Device-to-device effective bandwidth (read+write counted)** | **1503 GB/s** |
| **`cuMemsetD32` write-only bandwidth** | **1540 GB/s** |
| Implied fraction of the derived 1792 GB/s peak | **~84-86%** |

All timing arithmetic below uses **1500 GB/s achievable VRAM bandwidth** and the previously measured **56.9 GB/s pinned H2D**.

---

## FU1.1 Is the CUDA fast path worth it for THIS workload?

### Kernel inventory, classified by arithmetic intensity

| Kernel | Class | Arithmetic intensity | Tensor cores relevant? |
|---|---|---|---|
| Bayer-domain affine resampling (gather) | Gather, bandwidth-bound | ~1-4 FLOP/byte | No |
| Separable Gaussian / Laplacian pyramid | Separable stencil, bandwidth-bound | ~1-2 FLOP/byte | No |
| Local variance / modified-Laplacian focus measure | Small stencil + reduction | ~2-5 FLOP/byte | No |
| Guided / bilateral filter | Stencil, box-filter reducible | ~2-6 FLOP/byte | No |
| **N-frame weighted merge** | **Reduction over frame axis** | **<0.5 FLOP/byte** | No |
| Demosaic RCD/AMaZE | Large branchy stencil | ~10-20 FLOP/byte | No |
| Graph-cut / MRF on index map | Irregular, poorly GPU-suited | n/a | No |

**Tensor cores: CONFIRMED IRRELEVANT.** Tensor cores are a fix for compute-bound dense GEMM at arithmetic intensity above roughly 50 FLOP/byte. Every kernel above is under 20, and the dominant one (merge) is under 0.5. There is no matrix-multiply structure anywhere in this pipeline. The only way tensor cores become relevant is if a learned focus measure or learned denoiser is added later — and that path is better served by ONNX Runtime / DirectML as a separate optional module than by making the whole core pipeline CUDA-dependent. **This removes the single loudest argument for CUDA.**

### 99 KiB vs ~48 KiB shared memory — what it actually buys

Model: a separable stencil holding a T x T output tile plus a halo of `r` on each side, f32 in shared memory. Shared bytes = (T + 2r)^2 x 4. Global read traffic per output pixel = ((T + 2r) / T)^2.

| Halo r | Max T at 48 KiB | Read overhead | Max T at 99 KiB | Read overhead | **Traffic saved** |
|---|---|---|---|---|---|
| 3 (7-tap Gaussian) | 104 | 1.119x | 153 | 1.080x | **3.5%** |
| 8 (guided filter) | 94 | 1.395x | 143 | 1.243x | **11%** |
| 16 (coarse pyramid level) | 78 | 1.884x | 127 | 1.560x | **17%** |

VERIFIED inputs: `max_compute_workgroup_storage_size: 16384` default (`wgpu-types/src/limits.rs:436-458`, raisable to adapter limit); sm_120 `MAX_SHARED_MEMORY_PER_BLOCK_OPTIN = 101,376 B` (driver attr 97) and Blackwell Tuning Guide "maximum shared memory per thread block is 99 KB". The ~48 KiB NVIDIA-Vulkan figure remains **UNVERIFIED** (`vulkaninfo` unavailable).

Reading: the benefit is **3.5% on the common small-halo case** and **11-17% only on large-halo kernels**. Large-halo kernels are a minority of pipeline time, and the standard mitigation — a two-pass separable decomposition, or a summed-area/box-filter formulation of the guided filter — removes most of the halo overhead in *both* backends. **Net effect on end-to-end time: 2-5%.**

### TMA — does it matter for dense coalesced access?

**No, essentially.** TMA (`cp.async.bulk.tensor`, VERIFIED present on sm_120 via driver attr 127 and PTX ISA §9.7.9.26.5.1) delivers three things: (i) hardware address generation for multi-dimensional tiles, (ii) automatic out-of-bounds handling at tile edges, (iii) swizzled layouts matched to MMA fragment layouts. Our access pattern is already dense, coalesced, and row-major; (i) saves a handful of integer ALU ops per tile, which is free at bandwidth-bound occupancy; (ii) is convenience, not throughput; (iii) is worthless without MMA. The genuine benefit — asynchronous global-to-shared overlapping with compute — is already largely obtained through warp-level latency hiding at **48 warps/SM** occupancy (Blackwell Tuning Guide, cc 12.0). **Estimated benefit: low single-digit percent.**

### Persisting L2 carve-out on the N-frame merge — does the reuse pattern exist?

**No, not in the merge.** Per output tile the merge working set is N x tile: for a 128 x 128 tile and 60 frames of u16 CFA that is **1.97 MB**, which already fits in the 96 MiB L2 with no carve-out at all. More importantly, **each frame's tile is read exactly once** in the merge — there is no reuse for a carve-out to protect. A persisting carve-out only helps a buffer that is re-read while other traffic streams past it.

The one place that pattern *does* exist is **alignment**: 60 frames each compared against one reference pyramid. Reference pyramid at u16 with 1/4 + 1/16 + 1/64 levels is approximately 22 MB, read 60 times. Pinning it in the 60 MiB carve-out saves at most 59 x 22 MB = **1.3 GB of VRAM traffic = 0.9 ms** at 1500 GB/s. Against a total GPU budget of 500-800 ms (§FU1.3) that is **~0.2%**. And a 22 MB buffer re-read in a tight loop will largely stay resident in a 96 MiB L2 anyway, carve-out or not.

### Are subgroups + f16 + i16 sufficient for the reductions?

**Yes.** VERIFIED against `wgpu-types/src/features.rs:1071-1082`: `subgroupAdd/Mul/Min/Max/And/Or/Xor`, ballot, prefix (inclusive/exclusive) scans, shuffles and quad ops are all exposed, plus `SUBGROUP_BARRIER`. That is the complete primitive set for a two-level reduction (subgroup reduce -> workgroup shared-memory tree -> global). `SHADER_I16` keeps CFA data packed at 16 bits in storage buffers; `SHADER_F16` covers focus maps and blend weights. **Nothing required by these kernels is missing from wgpu.**

> **Precision caveat that overrides the naive "use f16 everywhere" advice from the main report:** f16 has a 10-bit explicit mantissa, i.e. ~2^-11 relative precision. For **linear 14-bit sensor data at full scale**, that is a quantisation step of roughly 8 LSB — strictly *worse* than u16, which stores 14-bit linear values exactly with 2 bits of headroom. **Keep CFA/linear-scene-referred data in u16 (storage) and f32 (arithmetic). Use f16 only for bounded, low-dynamic-range quantities: focus maps, blend weights, index maps, alignment displacement fields.** This does not change the 4 GB working-set figure, because u16 and f16 are the same size.

### Verdict

| Source of CUDA advantage | Est. end-to-end gain |
|---|---|
| Tensor cores | **0%** (no GEMM in the pipeline) |
| 99 KiB vs ~48 KiB shared memory | 2-5% |
| TMA | 1-3% |
| Clusters / DSMEM halo exchange | 1-3% |
| Persisting L2 carve-out | ~0.2% |
| Better compiler on the one branchy kernel (RCD/AMaZE) | 1-2% end-to-end |
| Explicit stream/copy-engine control | ~0% (PCIe is 0.07 s of a multi-second budget) |
| **Total** | **~1.05x - 1.15x, credibly bounded below 1.2x** |

**Estimated end-to-end speedup of a CUDA fast path over a well-written wgpu implementation: ~1.1x.**

And that figure is *itself* an overstatement of the value, because §FU1.3 shows **the GPU is not the bottleneck** — all GPU work is 0.5-0.8 s inside a 2.5-5.5 s pipeline dominated by CPU RAW decode. A 1.1x GPU speedup therefore moves end-to-end time by roughly **1-3%**.

**Recommendation: cut CUDA from v1 entirely.** Keep only the architectural seam — a `ComputeBackend` trait with per-kernel dispatch, so a CUDA variant can be added kernel-by-kernel later if profiling ever justifies it. Ship one excellent portable backend. Revisit only if (a) a learned component is added, or (b) profiling shows a specific kernel is shared-memory-capacity-bound after the algorithmic mitigations above have been applied.

---

## FU1.2 Memory and precision consequences of each alignment strategy

**Premise (accepted, not re-derived):** the transform is a *scale* (-1.012% over 33 frames on the reference rig, i.e. ~-0.031% per adjacent frame pair). At 7008 px wide, edge displacement is **~35 px between the extreme frame pair** and **~1.1 px between adjacent frames**, and displacement varies continuously across the frame. An arbitrary affine resample of a Bayer mosaic does not produce a valid Bayer mosaic — correct.

Reference frame budget: 33 MP. u16 CFA = **66 MB/frame**. Full-res RGB: u16/f16 = 198 MB, f32 = 396 MB.

### (a) Split CFA into 4 half-resolution planes (R, G1, G2, B), resample each on its own regular grid

| Quantity | Value |
|---|---|
| Per frame, u16 | 4 planes x 8.25 MP x 2 B = **66 MB** (no growth — same pixel count) |
| **60 frames, u16** | **3.96 GB VRAM** |
| Per frame if f32 required | 132 MB -> 60 frames = **7.9 GB** |
| Host RAM (staging, u16) | 3.96 GB |
| PCIe traffic | 3.96 GB up = 0.07 s at 56.9 GB/s |

**Precision:** a single bicubic/Catmull-Rom resample of 14-bit-in-u16 data has 2 bits of headroom; round-trip error stays below ~0.25 LSB at 14-bit scale, so **u16 survives ONE resample**. It does *not* survive a cascade (align -> refine -> re-align), where errors accumulate and negative lobes of a windowed-sinc kernel can clip at 0. **Do not use f16 here** (see the caveat above — f16 is worse than u16 for linear data at full scale). If more than one resample is unavoidable, go to f32 (132 MB/frame, 7.9 GB for 60) or keep the *composition* of transforms and resample once.

**Caveat specific to this option:** G1 and G2 sit on different sub-lattices offset by (1,0) and (0,1) from each other. Resampling them independently on their own grids is correct only if the sub-lattice offset is carried in the sample coordinates. Getting this wrong produces a subtle maze/labyrinth artefact that survives demosaic. Also, half-resolution planes halve the Nyquist limit per plane, so a naive per-plane resample is slightly softer than a joint one — relevant because sharpness *is* the product.

### (b) Demosaic first, then align in RGB

| Quantity | Value |
|---|---|
| Per frame, u16 RGB | **198 MB** |
| **60 frames, u16 RGB** | **11.9 GB VRAM** |
| Per frame, f32 RGB | 396 MB |
| **60 frames, f32 RGB** | **23.8 GB** <- *this is exactly the original 24 GB problem* |
| Host RAM | 11.9 GB (u16) to 23.8 GB (f32) |
| PCIe traffic | 11.9-23.8 GB = 0.21-0.42 s at 56.9 GB/s |

**Precision:** resampling demosaiced RGB is precision-benign (already interpolated). But this is the worst option on every other axis: it triples storage, triples merge-stage bandwidth (the merge is the pipeline's bandwidth monster), and it **demosaics 60 frames instead of 1**, which for RCD/AMaZE is the most expensive per-pixel kernel in the inventory. It also breaks the RAW-native premise: demosaic-then-align means alignment and merge operate on interpolated, spatially-correlated data, and demosaic artefacts get baked in before the merge can reject them. **Reject.**

### (c) Keep source frames unwarped as u16 CFA; apply the transform as a gather at consumption time <- RECOMMENDED

| Quantity | Value |
|---|---|
| **60 frames, u16 CFA, VRAM** | **3.96 GB** (the 4 GB figure is fully preserved) |
| Host RAM | 3.96 GB |
| PCIe traffic | 3.96 GB = **0.07 s** |
| Extra VRAM for aligned intermediates | **zero** |

**Recompute cost, computed against measured bandwidth:**

| Item | Cost per frame |
|---|---|
| Streaming read of one u16 CFA frame at 1500 GB/s | 66 MB / 1500 GB/s = **44 us** |
| Catmull-Rom gather: 33e6 output samples x 16 taps x 2 FLOP = 1.06 GFLOP; 5090 FP32 peak ~104 TFLOP/s | 10 us at peak, **~40 us at 25% efficiency** |
| Bilinear gather (4 taps) instead | ~10 us |
| **Materialise-once alternative** (read + gather + write) | 44 + 40 + 44 = **128 us**, plus 66 MB VRAM/frame |

So: a gather-at-consumption stage costs roughly **2x a plain streaming read**. Three consuming stages cost 3 x 84 = **252 us/frame**. Materialising once and then reading three times costs 128 + 3 x 44 = **260 us/frame** *and* 66 MB extra VRAM per frame (**+3.96 GB across 60 frames**).

**Conclusion: option (c) is a wash on time and saves 4 GB.** The recompute is affordable — decisively so. Three supporting factors:

1. **The gather is ALU, not bandwidth.** At scale 1.012 the mapping is near-identity, so consecutive output pixels read consecutive input pixels. Locality is excellent; the gather is effectively a coalesced read with a fractional offset.
2. **L2 absorbs it.** A 128x128 output tile touches a ~130x130 source region = ~34 KB per plane. With 96 MiB of L2 (MEASURED-LOCALLY, attr 38), the source footprint for an entire tile-column across all 60 frames stays resident.
3. **It composes with tiling.** Because nothing is materialised, the tile scheduler is free to choose any tile size and any traversal order without a corresponding allocation. This is precisely the libvips demand-driven model (`libvips/libvips:README.md:9-13`) applied to the frame axis.

**Cost to be honest about:** the transform must be threaded through every consuming kernel as a parameter (a 6-float affine plus the CFA sub-lattice offsets), and every kernel needs a halo margin sized to the local displacement. That is an API discipline cost, not a performance cost — and it is exactly the discipline the plugin architecture needs anyway.

### (d) Per-tile integer alignment, sub-pixel handled in the merge (HDR+ pattern) — does it work for a *scale*?

**Partially, and not sufficiently for this product.**

Tile-constant integer shift is valid only while the *differential* displacement across one tile is below ~0.5 px:

| Alignment tile size | Differential displacement across tile, extreme frame pair (1.012% scale) | Valid? |
|---|---|---|
| 512 px (scheduling tile) | 5.2 px | **No** |
| 128 px | 1.30 px | **No** |
| 64 px | 0.65 px | Marginal |
| **32 px (HDR+ `T_SIZE`)** | **0.32 px** | **Yes** |
| 16 px | 0.16 px | Yes |

So the geometry does work **at HDR+ alignment-tile granularity (16-32 px)** — but note this is the *alignment* tile size, which is an order of magnitude smaller than the *scheduling* tile size, and the two must not be conflated.

The real objection is quality, not geometry. HDR+ tolerates residual sub-pixel misalignment because its goal is **noise reduction**, and a slight blur from imperfect sub-pixel registration is an acceptable trade for variance reduction (`timothybrooks/hdr-plus:src/align.cpp:71-74` — tiles overlap by `T_SIZE_2` precisely so the merge can blend across residual error). **Focus stacking has the opposite objective: residual sub-pixel misalignment directly destroys the acutance that is the entire point of the output.** A half-pixel registration error at the merge is a half-pixel blur in the sharpest region of the final image.

**Verdict on (d): use it as a residual-refinement layer on top of (c), not as an alternative to it.** Apply the global affine as a gather (c), then run HDR+-style 32 px tile search on the already-globally-corrected data to pick up local residuals (focus breathing non-linearity, subject motion, thermal drift). The residual field after global correction will be small and slowly varying, which is exactly the regime where tile-integer + sub-pixel-in-merge is legitimate.

### Summary table

| Option | VRAM, 60 frames | Host RAM | PCIe | Precision needed | Verdict |
|---|---|---|---|---|---|
| (a) 4 CFA planes, resampled | **3.96 GB** (u16) / 7.9 GB (f32) | 3.96 GB | 0.07 s | u16 for one resample; f32 if cascaded | Viable; watch G1/G2 sub-lattice offsets |
| (b) Demosaic then align | 11.9 GB (u16) / **23.8 GB (f32)** | up to 23.8 GB | 0.21-0.42 s | benign | **Reject** — recreates the 24 GB problem, 60x demosaic cost |
| **(c) Gather at consumption** | **3.96 GB** | 3.96 GB | **0.07 s** | u16 storage, f32 in-kernel | **RECOMMENDED** — wash on time, saves 4 GB, composes with tiling |
| (d) Tile-integer + merge sub-pixel | 3.96 GB | 3.96 GB | 0.07 s | u16 | Geometry OK only at 16-32 px tiles; **insufficient alone** for a sharpness-critical product. Use as residual layer on (c) |

---

## FU1.3 Is a 15 s end-to-end budget realistic for 60 x 33 MP?

### Key finding: ARW decode has intra-frame parallelism (VERIFIED)

The suspicion that RAW decode "parallelises across frames but not within one" is **wrong for Sony ARW**.

| Fact | Evidence |
|---|---|
| ARW LJPEG is stored as **512 x 512 tiles**, each an independently addressable stream via `TileOffsets` | `dnglab/dnglab:rawler/src/decoders/arw.rs:483-499` — "The image is split into 512x512 tiles with cpp = 1, but the LJPEG stream is compressed as 256x256 with cpp = 4"; `coltiles`/`rowtiles` computed from `TileWidth`/`TileLength`; each tile gets its own `LjpegDecompressor::new(src)` at line 524-525 |
| rawler **already** decodes these in parallel | `rawler/src/decompressors/mod.rs:210-218` — `decompress_strips_fn` uses `.par_chunks_mut(width * stripsize)` with `use rayon::prelude::*` (line 41) |
| rawler depends on rayon and multiversion | `rawler/Cargo.toml` — `rayon = "1"`, `multiversion = "0.8"` |

For a ~7008 x 4672 sensor at `TileLength = 512`, that is **~10 strip-rows of intra-frame parallelism** (and 140 tiles of theoretical parallelism if the strip granularity is refined). Combined with 60-way frame-level parallelism, **saturating 32 threads is trivial**. The Amdahl risk the budget feared does not exist.

### Budget allocation (60 frames x 33 MP)

Bandwidth basis: **1500 GB/s VRAM (MEASURED-LOCALLY)**, **56.9 GB/s pinned H2D (MEASURED-LOCALLY)**, NVMe assumed 5 GB/s (**UNVERIFIED** — not measured).

| Stage | Where | Traffic / work | Time | Label |
|---|---|---|---|---|
| Disk read, 60 x ~60 MB ARW | NVMe | 3.6 GB | **0.7 s** | UNVERIFIED (NVMe rate assumed) |
| **RAW LJPEG decode -> u16 CFA** | **CPU, 16C/32T** | **3.96 GB of u16 output** | **1.2 - 4.1 s** | **UNVERIFIED** (see below) |
| PCIe upload, u16 CFA | H2D | 3.96 GB at 56.9 GB/s | **0.07 s** | derived from MEASURED-LOCALLY |
| Bayer align (pyramid build + coarse-to-fine search) | GPU | ~15 GB | 0.01 s ideal -> **0.10 s** realistic | derived |
| Focus measure (local variance / mod-Laplacian) | GPU | ~8 GB | 0.005 s ideal -> **0.15 s** realistic | derived |
| N-frame weighted merge (+ gather-at-consumption) | GPU | ~6 GB, x2 for gather | **0.10 s** | derived |
| Demosaic RCD/AMaZE on the **single merged frame** | GPU | branchy, ~10 passes | **0.10 - 0.30 s** | derived |
| Pyramid blend / seam handling | GPU | ~2 GB | **0.10 s** | derived |
| Colour transform + output encode (16-bit or f32 tiled BigTIFF, ZSTD, rayon) | CPU | ~200 MB | **0.2 - 0.4 s** | derived |
| **GPU subtotal** | | | **0.5 - 0.8 s** | |
| **TOTAL, fully serial (no overlap)** | | | **~2.7 - 6.1 s** | |
| **TOTAL, decode overlapped with GPU** | | | **~2.2 - 5.3 s** | |

The decode figure is the only large uncertainty. **COULD NOT CONFIRM** a published LJPEG-decode throughput number for rawler (searched: GitHub `repo:dnglab/dnglab` for benchmark files; no criterion benchmark or published figure found). The range above assumes **60-200 MB/s of u16 output per core**, which is the plausible band for Huffman-coded lossless JPEG. **This is the single number worth measuring first** — a 20-line `divan` benchmark against one A7C II ARW would collapse the entire budget uncertainty.

### Which stage dominates?

**RAW decode, by a factor of 2-8x over all GPU work combined.** Every GPU stage is bandwidth-bound and the 5090 has 1500 GB/s measured; the entire GPU pipeline moves roughly 30-35 GB, which at measured bandwidth is under 25 ms of pure traffic. Even inflating that by 20x for kernel inefficiency, launch overhead, and the branchy demosaic, the GPU lands at 0.5-0.8 s. The CPU entropy decode moves less data but is serial-dependency-bound per Huffman stream and cannot use SIMD effectively.

### Is 15 s achievable? **Yes, with a 2.5-5.5x margin.**

### Design consequences

| # | Consequence |
|---|---|
| 1 | **Reinforces cutting CUDA (FU1.1).** The GPU accounts for ~15-25% of end-to-end time. A 1.1x GPU speedup buys 1-3% overall. A second backend cannot be justified against a stage that is not the bottleneck. |
| 2 | **Do NOT build decode/compute overlap in v1.** Overlapping decode of frame N+1 with GPU work on frame N can save at most the GPU time (0.5-0.8 s of a 2.7-6.1 s budget) = **15-25%**. There is no *memory* forcing function either: all 60 decoded frames are only 3.96 GB, which fits in both 64 GB host RAM and 32 GB VRAM. Build the **seam** (a bounded frame-producer channel between decode and the GPU scheduler) so overlap is a v1.1 change of the consumer loop, not a rewrite. **This is a real v1 scope reduction.** |
| 3 | **Optimise decode, not the GPU.** The highest-leverage work in the whole project is CPU LJPEG throughput. Measure it first. If rawler's strip-level rayon parallelism under-fills 32 threads, decode 2-4 frames concurrently in an outer `rayon` scope and let the nested parallelism fill in — do not hand-roll a tile scheduler until measurement says the strip granularity is the limit. |
| 4 | **CCD affinity: decode belongs on the frequency CCD.** LJPEG Huffman decode is branch-heavy, serially dependent, with a tiny working set (one 512x512 tile = 512 KB, comfortably inside the 1 MB per-core L2 measured in §2.2). It gains nothing from 96 MB of V-Cache and loses from the V-Cache CCD's lower clocks. Prefer LPs 16-31 (32 MB L3 CCD) for decode; reserve LPs 0-15 (96 MB V-Cache CCD) for the large-tile CPU fallback path and output compression. **Practical note: rayon's work-stealing self-balances across the asymmetry**, so this is a tuning refinement, not a correctness requirement — measure per-CCD decode throughput before adding explicit pinning. |
| 5 | **Output encoding is a real 0.2-0.4 s line item.** Our own tiled-BigTIFF writer (required anyway, since `image-tiff`'s encoder cannot write tiles — §1.4) should compress tiles in parallel with rayon from day one. This is free parallelism that a strip-based writer cannot exploit. |
| 6 | **Disk IO never justifies DirectStorage.** 0.7 s of NVMe read against a 2.7-6.1 s budget, fully hideable behind decode with `compio`/IOCP prefetch. This closes out the `direct-storage` 0.7.1 risk item (252 downloads/90d) — **do not adopt it.** |

### New gaps opened by this section

| Item | Status | Next action |
|---|---|---|
| rawler ARW LJPEG decode throughput (MB/s of u16 output per Zen 5 core) | **COULD NOT CONFIRM** — no published benchmark found in `dnglab/dnglab` | Highest-value measurement in the project. Run `divan` on one A7C II ARW, single-thread and 32-thread. |
| Actual `TileWidth`/`TileLength` in an A7C II ARW (assumed 512) | **UNVERIFIED** | Read the TIFF tags from a real file. Determines available intra-frame parallelism. |
| NVMe sequential read rate on this machine | **UNVERIFIED** (5 GB/s assumed) | Quick read of a 3.6 GB file, cache-cold. |
| NVIDIA Vulkan `maxComputeSharedMemorySize` (48 KiB assumed) | **UNVERIFIED** | Still gates the FU1.1 shared-memory estimate; a 64 KiB or 96 KiB answer would shrink the CUDA case further. |
| Whether rayon strip granularity fully saturates 32 threads on one frame | **UNVERIFIED** | Falls out of the decode benchmark above. |
