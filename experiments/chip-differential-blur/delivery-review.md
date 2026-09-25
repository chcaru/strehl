# Independent native delivery review

VERIFIED by delivery-review.py on 2026-09-25, with no new renders or RAW decodes: all three saved deliveries have matching file bindings, executable pins, complete RGB16 dimensions/ICC and retained-map identities. The root-added Catmull–Rom checks close the earlier retained-map override ambiguity. Both retained and newly solved maps are checked before a successful completion receipt.

The manifest selects actual executable SHA256 bec4c357836ad1383800a6c933460ee7ef072c525b5957a6f5deb5194b203314, matching build-fixed-2/executables.json and the file itself. Its core-suite statement matches the actual 569-pass, 0-fail, 2-ignored log. The additional source-bindings and validation fields are provenance pointers; executable integrity is the field enforced by the wrapper. Documentation accurately distinguishes this corrected entry point from historical scripts that retain the old pin.

| Delivery | Sources | Native RGB size | Held map digest | Result |
| --- | ---: | --- | --- | --- |
| garnet-104 | 183 | 6524×4348 |5108e5fd3696d28b| Entire RGB16 array and ICC independently equal the corrected test adapter. |
| chip-before | 299 | 6500×4332 |bc92dcc743ae3d98| Bound to the historical executable. |
| chip-fixed | 299 | 6500×4332 |bc92dcc743ae3d98| Bound to the corrected executable; same full ordered input records, flags and environment as chip-before. |

The checker rehashed existing TIFF/JPEG/overview/map/executable/runner/helper files; independently derived ordered basename/size map identities; and verified that swapping the first two sources would fail that identity. All listed original paths still have their recorded sizes and modification times. It did not reread the many gigabytes of original RAW contents: endpoint content equality is established by the executed wrapper's before/after hashes and successful receipts. This scope distinction is retained in delivery-review.json.

Source safety follows the actual commands: output paths are fresh and outside the input directory; align output is explicitly outside the source; retained-map mode only loads/checks the map. Completed process receipts report exit0, no controller errors, terminal child-tree accounting and no cleanup failures. The old and corrected chip runs share every source record and the same unchanged map. Garnet's explicit zero exposure is consistent with its historical policy; the chip pair both omit an explicit exposure adjustment.

No rendering-quality admission follows from these mechanical checks. The wrapper completion status still requires independent full-image/native review; the manifest explicitly retains unresolved glare and occlusion defects.
