# Independent complete-photo replay receipt review

2026-10-27. VERIFIED read-only metadata/hash/receipt audit. No RAW decode, pixel-array analysis, numerical restoration or Cargo job was run by this reviewer. Both complete photographic pairs are mechanically valid diagnostic outputs. The independent photographic review determines their utility; the seven generated quality failures in [the screen review](independent-screen-review.md) remain failed.

Root ran the frozen `native-restoration-build-1/cli-tests.exe`, SHA256`339efc0ac1652501b2a834ab9305cc7c6ede792316c42d20f7dfdbc32d32714d`, with exact commands:

```powershell
& 'C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\outputs\raw-quality-2026-10-27\native-restoration-build-1\cli-tests.exe' merge_cmd::native_restoration::replay_weevil --ignored --exact --nocapture --test-threads=1
& 'C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\outputs\raw-quality-2026-10-27\native-restoration-build-1\cli-tests.exe' merge_cmd::native_restoration::replay_flat --ignored --exact --nocapture --test-threads=1
```

Each completed exit0 with terminal job accounting and no cleanup error, under the180s/6GiB/4worker bound. Weevil records4.547s and766,038,016bytes peak committed job memory; flat4.640s and774,049,792bytes. These are saved-CFA reconstruction/writer observations, not complete299/60-source stacking times or a competitive workflow speed ranking. The original stacking costs remain necessary.

Independently streaming-rehashed119 unique master/input/report/dependency/display bindings, totaling4,348,597,509bytes, with no mismatch. TIFF metadata inspection confirms a single complete RGB16 and float32 image per arm: weevil6896x4596 at active origin[68,46], flat6932x4620 at[50,34]. The exact signed-CFA payload lengths match these dimensions. Both off sensor payload hashes equal their retained inputs. `noop-verified.json` baseline objects equal the main receipts.

The audited producing path reports exact complete no-op RGB16 and float pixel equality, material metadata equality and all retained input bytes/mtime unchanged. Independent header checks confirm literal ICC, ImageDescription, sample format, orientation/resolution and other material tags equal the held master in both arms. Both baseline float TIFFs are byte-identical to the held originals. RGB16 file bytes differ only in the expected provenance scope: held Software is `strehl 0.1.0-alpha.6 (4813e46bdc9a-dirty)`, replay says `strehl 0.1.0-alpha.6 (unknown)`; the complete pixel comparison is performed by the audited frozen binary. No second crop, CA correction, automatic retone or geometry change occurs. Weevil remains the retained CA-off input; flat keeps its own original preparation and development.

The actual correction changes all four planes and produces complete sensor, RGB16 and float masters, without substituting the baseline. Candidate RGB16 identities are:

| Dataset | Candidate master SHA256 |
| --- | --- |
| Weevil | `d31e93271d77a85bfb1ba1bae7ca8d672252d17590af844f528044c5aae218ea` |
| Flat | `9bf8939e26470500beb64d4d9c033557eafab94f7b0351037c20f5f8e967eb4a` |

Both receipts explicitly state `RAW_reads=0`, `original_RAW_read_or_written=false`, `admission=false` and `quality_claim=false`. Their299/60 source counts mean saved-master lineage, not a fresh original-file census. Display receipts bind the same three master types per arm and the complete overviews plus frozen ten/eight native witnesses. This audit verifies the objects being compared and their unchanged development; it does not establish preserved photographic detail, reduced halos, clean color or a useful complete-image improvement.
