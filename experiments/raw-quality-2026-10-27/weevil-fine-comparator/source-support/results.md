# Five-source weevil support observation

2026-10-27. **VERIFIED limited source support; no missing-detail or optical-ceiling finding.** This small pass does not justify a new reconstruction mechanism. No original RAW was opened or modified.

The fixed complete source views were inspected independently and by root before nominations: [0](overviews/source-000.png), [74](overviews/source-074.png), [149](overviews/source-149.png), [224](overviews/source-224.png), [298](overviews/source-298.png). The full-resolution RGB16 source masters are the already exported [DSC00001](../../../../outputs/raw-quality-2026-10-26/weevil-107-tiff-export/frames/DSC00001.tiff), [DSC00075](../../../../outputs/raw-quality-2026-10-26/weevil-107-tiff-export/frames/DSC00075.tiff), [DSC00150](../../../../outputs/raw-quality-2026-10-26/weevil-107-tiff-export/frames/DSC00150.tiff), [DSC00225](../../../../outputs/raw-quality-2026-10-26/weevil-107-tiff-export/frames/DSC00225.tiff), and [DSC00299](../../../../outputs/raw-quality-2026-10-26/weevil-107-tiff-export/frames/DSC00299.tiff). These are individual source photographs, not stack outputs.

Source74 brings dorsal texture into focus;149 favors legs and hairs. Endpoints0/298 are broadly defocused;224 favors antenna/tarsi outside the three retained witnesses. We froze74/149 in [nominees.json](nominees.json) and retained all three regions on both, including poor-focus negatives. Neither complete view establishes a focused thorax reference.

| Existing 384px witness | Source74 origin | Source149 origin | Independent observation |
| --- | --- | --- | --- |
| turquoise-scales | 2181,1381 | 2188,1386 | Source74 is mixed-focus: large upper-left blur discs coexist with more focused lower/right scales and dark-band texture. Source149 is heavily defocused. The native complete stack shows substantially more scales across this rectangle. This pair does not expose a sharper omitted scale boundary. |
| thorax-texture | 4596,2608 | 4588,2606 | Both sources show defocused discs/rings. Their appearance cannot define missing thorax detail or a capture limit. |
| upper-leg-hairs | 1879,677 | 1888,686 | Source149 preserves recognizable lower-edge hair trajectories also visible in the stack. Focused left-side hairs are broadly comparable; source right-side scales/glints remain defocused while the stack contains more detail. Source74 is strongly defocused. No erased hair is established. |

All six native PNGs and exact RGB16 crops are in [the crop receipt](crops/receipt.json). I inspected each at384x384 without resizing, then revisited all three corresponding [native CA-off witnesses](../photo-review/native-ca-off/). The current complete stack remains [full JPEG](../../../../outputs/raw-quality-2026-10-26/weevil-107-ca-off/stack-full.jpg) and [RGB16 master](../../../../outputs/raw-quality-2026-10-26/weevil-107-ca-off/stack-master.tiff). The previous [B8/B4 full-workflow review](../photo-review/independent-results.md) remains unchanged; this source pass does not rehabilitate either its unresolved softness or its halos/glints.

Source tone and ICC were preserved exactly; PNGs use `(RGB16+128)//257`. Only whole-source overviews were resized to1617x1078. The runtime map locates crop centers, without warping source pixels: reference149 active center uses native crop offset(68,46), then `q=C+a*(p-C)+2b`, `C=(3516,2344)`. Source74 scale is1.0060357;149 is1.0. Integer-rounded rectangles are context correspondences, not equal physical footprints or placement measurements. Source TIFF development precedes merging and uses its frozen tone; native automatic development occurs after merging. The existing tone difference remains a comparison limitation.

**MEASURED commands**, from the worktree:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/weevil-fine-comparator/source-support/run-bounded.py overviews
python -B -X faulthandler experiments/raw-quality-2026-10-27/weevil-fine-comparator/source-support/run-bounded.py crops
```

Both exit0 with terminal job accounting and no cleanup errors:3.609s/315,736,064B peak for five whole views;0.906s/46,895,104B for six crops. These are export costs, not stack performance. Reused the flat cached-TIFF helper with scoped bindings; receipts verify every read TIFF/hash before and after, exact lossless crop pixels and original ICC. No sharpness search, numerical fit, source-selection oracle, new crop search or original decode was performed. Five spaced sources cannot rule out a more informative focus interval elsewhere in the299-frame stack.
