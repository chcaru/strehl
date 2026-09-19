# Vitamin-C external whole-image comparator

Prepared 2026-09-19. **ARGUED recommendation:** run the retained MIT focus-stack fork on all 70 vitamin-C captures, with the product's RAW decoder, MHC demosaic and colour developer supplying unaligned RGB16 TIFFs. Compare the complete outputs at corresponding native photographic sites. This addresses the current quality-path request for a strong external whole-image reference after the focused star-placement result remained photographically null.

## Ready configuration

Input: `D:/personal/macro/requests/misc-diagnostic/crystalized-vitamin-c-cpl/DSC00094.ARW` through `DSC00163.ARW`, all 70 in filename order. Original paths are read-only inputs. The saved baseline input manifest is `vitamin-c-baseline-1/invocation.json`.

Baseline: `vitamin-c-baseline-1/vitamin-c.tiff`, 6920×4612 RGB16, global reference35, crop origin(56,38) in active native sensor coordinates. Its map is `vitamin-c.warpmap.txt`. Held executable `experiments/native-gpu-gather/build-native-6/strehl.exe`, SHA256 `2fd0a1615989e262fbba61e0a1587a9b8f20ff4913d3969510e967ce9d9219d7`.

Exporter: `crates/strehl-cli/examples/quality-batch-develop.rs`. It decodes one original at a time into u16, uses only the 7032×4688 active area, performs f32 black subtraction/WB normalization, and calls the actual `image_out::write_demosaiced` MHC/colour writer. It writes 70 **unaligned** native RGB16 TIFFs to the experiment directory. It never retains a collection of full RGB frames or materializes aligned source frames in strehl.

First-frame WB is held bit-for-bit across the export; every later frame must report identical normalized WB, camera ILCE-7CM2 and ISO100. Levels are512/15360. The decoder's D65 XYZ→camera matrix is held and checked against `[[.7460,-.2365,-.0588],[-.5687,1.3442,.2474],[-.0624,.1156,.6584]]`. Baseline TIFF tone is pinned to **.090420/.914606/.550**, the most precise values retained in its description; those are rounded values, not an assertion of identical original f32 tone bits. No per-frame tone measurement or exposure adjustment runs.

Before any original is decoded, an existing independently decoded star u16 patch passes through the **same new normalization function** and must equal actual-consumer normalized CFA bit-for-bit. Its MHC+developer RGB16 must then equal the saved actual-consumer TIFF. The wrapper checks native output dimensions/type and ICC bytes equal the baseline. This can reject a wrong phase, WB/order, MHC, or colour-development route; it is not a photographic quality metric.

Fork: `experiments/M175-fork-arm/bin/focus-stack.exe`, **VERIFIED present and hash-matched**, SHA256 `691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac`. MIT fork source pin `4bc7f95e448cf20ee2bdd758403ec43e2612a1c6`. M175 records two identical builds and an exact native RGB16 transfer witness; that establishes executable/transfer provenance, not competitive image quality.

**VERIFIED no second transfer curve:** the retained MIT build source `work/repro/source-a/src/colormgmt.cc:138` returns CV_16U inputs unchanged; `task_loadimg.cc:75` uses IMREAD_UNCHANGED; `task_saveimg.cc:127` skips finalisation for existing16-bit/requested16-bit/SRGB. M175's recorded actual run under `none/srgb/16` gave the exact input/output decoded-pixel SHA256 `2f8d3631e7e858e4e4fbb79d61ee031d07af7f5a809cc12050ab4d4501751087`. The flags name the already encoded samples; they do not apply another curve. Default reference is `count/2` at `focusstack.cc:290`, so70 inputs select ordinal35, `DSC00129.tiff`.

Frozen fork flags: `--threads=8 --batchsize=2 --no-opencl --no-whitebalance --no-contrast --consistency=2 --denoise=1.0 --input-colorspace=none --output-colorspace=srgb --output-bitdepth=16`, followed by all70 developed paths. Default neighbour alignment, middle reference35 and ≤2048 alignment resolution remain enabled. No original warp map is supplied. Photometric matching is disabled because development is shared. Output is `vitamin-c-comparator-1/fork.tiff`; natural coverage cropping may differ from strehl.

Root-controlled stages, from repository root (active attempt2):

```powershell
python experiments/quality-september19/vitamin-c-comparator.py build --out experiments/quality-september19/vitamin-c-comparator-2
python experiments/quality-september19/vitamin-c-comparator.py develop --out experiments/quality-september19/vitamin-c-comparator-2
python experiments/quality-september19/vitamin-c-comparator.py fork --out experiments/quality-september19/vitamin-c-comparator-2
```

Each stage is explicit. The exporter/fork have independent bounded Windows jobs; development caps360s wall/1800s CPU/3GiB committed memory, fork600s wall/2400s CPU/12GiB. These are caps, not speed predictions. Export needs about13.85GB; wrapper requires22GiB free before opening originals. **MEASURED inventory:** C: had722,542,628,864bytes free during preparation. Source, binary, original metadata and output hashes are recorded. No build, RAW decode or whole render was launched by this preparation task. Root's first build attempt failed because the repository's sha2 digest array lacks `LowerHex`; root replaced digest formatting with per-byte hexadecimal formatting, retained the failure under comparator-1 and started comparator-2. The active image path is therefore `vitamin-c-comparator-2/fork.tiff`. Build receipts, rather than this note, determine the final executable hash/status.

**Completion update:** root built comparator-2 and completed all70 developments. Its saved golden reports112,896/112,896 normalized f32 samples and338,688/338,688 RGB16 samples exactly equal their actual-consumer references. `development-complete.json` verifies7032×4688 RGB16 with the same2716-byte ICC profile as the baseline. The fork stage remains a separately dispatched root action; these development checks make no merged-image quality claim.

## Interpretation

This is a **complete-workflow photographic comparison**, not a pure merge experiment: fork receives colour-developed, tone-mapped RGB before merging; strehl applies colour and tone after its CFA merge. Native baseline corrects lateral CA during gather; this simple unaligned exporter applies no CA warp. Six-digit tone rounding and differing final coverage are also explicit. Judge corresponding structures at native scale; resized overviews orient only. If either output wins visibly, that identifies a useful product-level deficit, not its unique cause. Do not claim SOTA from this single scene or from the old transfer sentinel.

## Commercial and other retained references

**VERIFIED available historical Zerene PMax:** `D:/edited/macro/test2/2026-05-09-12.12.17 ZS PMax.tif`, SHA256 `b240fe4016e97ebb194497b2798a095c63c490c4fff54018d48d34c7523719a0`,196,453,660bytes. Matching63 original captures are `D:/personal/macro/113MSDCF/DSC00001.ARW` through `DSC00063.ARW`. Its63 Lightroom inputs remain at `D:/edited/macro/test2/20260507-DSC00001.tif` through `20260507-DSC00063.tif`. Both counts were checked with `Get-ChildItem -Force`; pairing and Lightroom Sharpness0/Contrast2012+100/noNR are documented in `docs/research/V-HEADTOHEAD.md` and `experiments/V-HEADTOHEAD/zer_geom.py`. This is the useful later **older-capture commercial reference**, with a substantial development confound. Do not reuse that report's retracted detail headline.

Historical owner-fork coffee image also remains at `C:/dev/macro/out/coffee-bean/stack.tif`, SHA256 `8636c20d73ca0cb1f57db89bf8553abc166e0fbc517e5c62a07c74dee509066e`. Its producing binary is unknown; M175's rebuild is a defensible retained source pin, not proof it reproduced that historical producer.

Zerene is installed, but current configuration SHA256 `22293ec5cebb3e111ac6c8bb7bda9ed7281fb329463d84612466bd61d5d57d75` is unchanged from the documented expired-trial save blocker. No fresh license validation or launch was attempted. No Helicon installation was found in the two ordinary Program Files roots; this is a scoped inventory, not a systemwide absence claim. No chip/star/vitamin external output was found in the current diagnostic originals tree or the inspected `D:/edited/macro` tree. No prohibited source was opened.
