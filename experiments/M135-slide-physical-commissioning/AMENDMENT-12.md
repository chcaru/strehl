# M135 slide commissioning amendment 12

Status: **FINAL METADATA-BINDING REPAIR BEFORE COMMIT**

The terminal review found that frame hashes were bound but the ExifTool values
and chronological order stored beside them could still be edited.  The coarse
histogram and Stage C would then faithfully recompute the wrong question.

`summarize` now reruns Stage A with the frozen ExifTool binary and source root,
validates the regenerated inventory, and requires the complete metadata/order
projection to match before rerunning Stage C.  Inventory semantics also require
sequential `ordered_index` values and reproduce the timestamp/subsecond/
filename ordering directly.

A new mutation swaps two otherwise valid metadata rows and must be rejected.
No capture was opened while adding this control.
