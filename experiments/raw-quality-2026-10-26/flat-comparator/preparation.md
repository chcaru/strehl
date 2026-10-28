# Flat60 native TIFF export preparation

**SOURCE-PREPARED / UNVERIFIED execution.** New example [flat-batch-develop.rs](../../../crates/strehl-cli/examples/flat-batch-develop.rs) is a capture-binding adaptation of the preserved weevil exporter. No build, RAW decode, TIFF export or numerical quality test was executed by this lane. Root owns the separate bounded wrapper and process scheduling.

[flat-export-config.json](flat-export-config.json) binds the exact60 entries of the completed flat baseline manifest: DSC00016.ARW through DSC00075.ARW. Its manifest SHA256 is `7a7f6474eca174c5dd9c9d4cabc6eb1ae15e8385c7395472a793175c59a107fe`. The exporter checks order, filename, containing directory, original size, manifest modification time and original content SHA before decoding. It rechecks every source's content and metadata after export. Capture files and sidecars are never written. Output must be a fresh workspace directory.

The first original's actual `wb_gains()` becomes the fixed output WB for all60 inputs, matching the native stack's first-source policy. Every frame's own WB bits and whether they differ are recorded; AWB variation does not alter development. Each source must retain camera ILCE-7CM2, ISO100, levels512/15360, the D65 matrix, exactly the first active rectangle, full7032x4688 dimensions and even Bayer phase. The product decoder supplies CFA identity. This is native product decoding/MHC/development, not a demosaiced fusion volume.

Tone comes from the exact `DisplayBaseline` header of the hash-bound flat linear master, not the rounded render log. The exporter checks RGB32 dimensions6932x4620 and the following f32 bits before the first original decode:

| Field | Expected f32 bits |
| --- | --- |
| Black | 1007739294 |
| White | 1052551964 |
| Contrast | 1057803469 |
| Exposure gain | 1065353216 |

The linear-master SHA256 is `51fd1f3e281c10def359af38a2064055de11b8788ff5ce7c0428d9e5a9e417ab`; the retained crop-export receipt is also hash-bound in config. The source reads TIFF metadata only for this check, then uses the same fixed tone for every complete source image. Source-specific automatic tone is absent.

`normalize_row` and the complete vitamin golden-fixture function were verified byte-identical to the preserved weevil source, including after formatting. The original-u16 normalization check and exact336-square RGB16 fixture run before original decoding. Their existing fixture paths/hashes are unchanged. Each full output must be RGB16 with the same nonempty ICC. Frames are processed sequentially with four Rayon workers; only the current original and current developer buffers are retained. `frames/` and ordered `inputs.txt` contain only the60 comparator TIFFs, with the golden TIFF outside them. Final status must be `60_UNALIGNED_NATIVE_RGB16_DEVELOPED`; partial outputs do not qualify.

Prepared root commands, **not run by this lane**:

```powershell
cargo build --locked --release -p strehl-cli --example flat-batch-develop
& '.\target\release\examples\flat-batch-develop.exe' 'C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\experiments\raw-quality-2026-10-26\flat-comparator\flat-export-config.json'
```

Root's wrapper owns fresh build/executable bindings, resource bounds and overlap/load records. Initial bounds from the brief are900 s wall,3600 CPU seconds,6GiB job commit and at least40GiB free disk. Runtime receipt retains `active_wh`, `frames`, `worker_count`, `golden`, executable/config/manifest identities and `input_content_and_metadata_unchanged`, plus per-frame AWB, fixed output WB and complete TIFF hashes. No speed claim follows from this preparation or a run overlapping the weevil experiment.

Source SHA256: `8c9a3b26d6b8416cb216b26670ba1537fe5fc2de6bfbf3b195645f866fe3a47e`. Config SHA256: `48d5a0acbf59557d4743ca197b9eb8d0c99671f325064ae20be1180c22489cd5`. Preserved weevil source SHA256 remains `36048da273521fe8ef9f1c3ee70ac9b2a443a8c36cdd2b1b1487b0f83485968d`. `rustfmt --edition 2024 --config skip_children=true crates/strehl-cli/examples/flat-batch-develop.rs` parsed successfully, exit0; this is not compilation. Manifest/name and metadata-to-f32 bit checks read existing JSON only; no new source pixels were read.

The eventual comparator remains a full-workflow comparison. These TIFFs apply MHC, color development and fixed tone before Helicon's alignment/merge and omit the native CA warp. Native RAW reconstruction uses its CA-on profile and held map, then develops once; crop and geometry can differ. Complete outputs and masters, followed by the eight frozen flat witnesses in explicit coordinates, are required. The exporter itself creates no focus stack and claims no quality improvement.
