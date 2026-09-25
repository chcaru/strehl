# Independent recipe provenance review

VERIFIED by `C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe -I -B -X faulthandler experiments/full-stack-source-prior/independent-recipes.py` on 2026-09-25. Result: `INDEPENDENT_RECIPE_CHECK_PASS`, retained in `independent-recipes.json`. No RAW was decoded and original contents were not rehashed; the root's cost/full adapter remains responsible for its mandatory input-content hashes.

All three recipes preserve every input row's index, length and recorded SHA256, match the retained alignment identity computed independently with FNV1a over ordered identity names and lengths, and bind maps with every frame placed. Swapping the first two rows fails every map identity; replacing marigold's staged identity names with original basenames also fails, demonstrating why the explicit name remapping is necessary.

| Recipe | Sources in original order | Map reference | CFA crop x,y,w,h | Exposure | Mode |
| --- | --- | --- | --- | --- | --- |
| marigold-4 | 279 from stack4.1 DSC00021–00299, then 209 from stack4.2 DSC00001–00209 | 244 | 191,128,3134,2088 | -0.5 EV | prior |
| ore-100 | 207, DSC00031–00237 | 103 | 83,55,3351,2234 | 0 EV | prior |
| garnet-104 | 183, DSC00027–00209 | 91 | 127,85,3262,2174 | 0 EV | current |

Actual TIFF file and RGB16 pixel hashes match all three recipes; dimensions are twice the CFA crop and ICC is present. The baseline file hashes also match the retained final delivery receipts. The crop/exposure pair agrees with each original render log. In particular, marigold binds the delivered highlight-preserving master and its retained `--exposure=-0.5` invocation, not the earlier unadjusted stack-4 output. The ore and garnet baselines are the delivered 0 EV versions. Tone remains automatic under the same writer policy, with resolved values to be checked at runtime.

Garnet's changed directory is accounted for by the existing folder-label receipt: old `minerals/104MSDCF` to `minerals/etched-spessartine-garnet/104MSDCF`, 183 verified unchanged SHA256 values. Recipe basenames, recorded hashes and sizes are unchanged; current file existence and size are independently checked. The other recipes retain their original paths.

No recipe blocker found. This verifies metadata/provenance and baseline binding, not current-source content identity, successful GPU replay, image quality, or alignment accuracy. The frozen recipe hashes and measured pixel hashes are in the JSON receipt.
