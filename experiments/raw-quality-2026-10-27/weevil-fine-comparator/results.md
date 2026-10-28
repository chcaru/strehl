# Complete weevil B4 comparison: no substantial gain

2026-10-27. VERIFIED by root and independent whole-image/native review: reducing Helicon B's radius8 to4 with smoothing4 does not substantially improve the complete weevil. No decisive new hair/scale separation appears; rounded scale/thorax contours, seam softness, glints and pale wing/occlusion rims remain. Some small features appear firmer, with no major new regression established in the frozen guards. This does not solve the native stacker's defects or establish a best vendor setting.

[Independent photographic review](photo-review/independent-results.md) links all three complete images and RGB16 masters, all ten native coordinate triplets and interpretation. Root independently viewed native CA-off, previous B8 and B4 whole overviews first, then all30 corresponding384-pixel PNGs. Native and vendor frames have different gauges and development order; B8/B4 have identical developed inputs/settings except radius, which makes their comparison more directly controlled. SIFT supplies location only, not placement truth or equal spatial resolution. No per-arm retone or crop resampling was introduced.

## Exact execution

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/weevil-fine-comparator/run.py
python -B -X faulthandler experiments/raw-quality-2026-10-27/weevil-fine-comparator/run-38g.py
python -B -X faulthandler experiments/raw-quality-2026-10-27/weevil-fine-comparator/photo-review/export-corresponding.py --whole-images-reviewed
```

MEASURED first command: exit1 before vendor launch, available physical memory47,255,482,368bytes below the49GiB preflight. It produced no processed photograph. Preserve `b-r4-desktop-1/`. The documented second wrapper changes only destination and memory bounds to38GiB Job/42GiB preflight; its source SHA256 is `5aeb574d175bbb8616557e21e0a6b720b54a1a5d175f428271ca6ee49f157e07`. Both were launched with authorized desktop access. No unrelated process was stopped.

MEASURED second command: exit0,45.344seconds vendor child and117.485seconds whole wrapper, peak Job commitment34,698,645,504bytes (32.32GiB). The process exited normally, terminal accounting has no active descendants/cleanup error, and no termination was attempted. Existing299-source TIFF export cost is separate (211.109seconds from its held receipt). Hashing/export overhead, caches, vendor worker behavior and historical host overlap prevent a clean competitive timing rank. GPU use is not established by these timings.

VERIFIED completeness: exact current command/timestamp in the fresh application log;598 rows account for all299 sources in both ordered passes. All299 TIFF content/metadata, application executable and held provenance pins are unchanged. Complete master is one RGB16 TIFF,7020x4676,196,984,074bytes, SHA256 `d24e944825fe5e8405dbf26a7339e7d69af4f70dea6607db1af81ea809a274ff`. Common ICC SHA256 `238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b` matches prior B/C. The vendor saved-output-list file remains absent; fresh application logging and complete TIFF readback establish the actual saved output explicitly. No trial reset, activation, installation or purchase occurred.

The exact [completion receipt](../../../outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2/completion.json), [process accounting](../../../outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2/process.json) and [input preservation](../../../outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2/preservation.json) retain execution identities. The new [full JPEG](../../../outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2/stack-full.jpg) and [full-resolution master](../../../outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2/stack-master.tiff) were shown to the user with native and previous comparator master links.

No native code/default or quality claim follows. The bounded source-support continuation is a diagnostic of captured contours, not a search for an unquestioned best-frame truth or a capture ceiling.
