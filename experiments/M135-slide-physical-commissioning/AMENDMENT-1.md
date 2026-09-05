# M135 slide commissioning amendment 1

Status: **FROZEN AFTER THE FIRST COMMISSIONING RUN WENT RED AND BEFORE ITS
REPLACEMENT RUN**

The frozen physical preregistration is unchanged.  The failed author-
commissioning artifact is preserved as `commission-run1-failed.json`, SHA-256
`1e0e5f034d0153fa582f251b761731bd08ce32355bc976d8c8dd6675858ac26c`.

Seven controls were red.  None exposed an authorized-slide outcome and no path
under `D:\` was opened:

1. The timestamp-sort mutation used filenames whose lexical order accidentally
   matched timestamp order.  Replace only the fixture names so the wrong
   selector is potent.
2. The rawpy lifetime audit demanded five `np.array(copy=True)` calls although
   the fifth copied object is `bytes(raw.color_desc)`.  Require the four array
   copies that actually exist and separately require the mosaic copy to occur
   inside the context.
3. Reordering the same four quadrilateral vertices is not a geometric
   mutation because the detector intentionally canonicalizes unordered points.
   Move one vertex inside the opposite triangle so convexity, not caller order,
   is challenged.
4. The stop-band control compared two float32 inverse FFTs at `1e-5` relative
   RMS and observed `1.4901452e-5`, while the load-bearing exact-zero mask check
   passed.  Keep that exact-zero check and use a `2e-5` numerical round-trip
   bound.  No physical frequency limit changes.
5. The registration-motion plant called the ECC routine on unfiltered images,
   unlike the production path, and fell below the unchanged `0.7` correlation
   floor.  Route the plant through the same frozen low-pass/downsample path.
6. The above-band plant let its in-band carrier underflow to exact zero at
   remote focus positions.  Add a small fixed in-band floor so the curve
   remains a valid positive focus curve; keep the peak and distractor
   locations unchanged.
7. The dynamic import of the existing M135 core did not insert the module into
   `sys.modules` before executing its dataclass declarations.  Repair the
   loader only.

No equivalence bar, frequency cap, role rule, flat rule, expected frame count,
or schema is relaxed.
