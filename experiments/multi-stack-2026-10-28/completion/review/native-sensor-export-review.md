# Native sensor master: source and binding review

This checkpoint distinguishes authorship. The root authored the consumer/export/CLI binding changes; the reviewer independently inspected them. The reviewer authored the UI optional-binding changes in session-import.rs and session-import-tests.rs; the root separately reviewed those changes and scheduled the tests. Neither author-run controls nor source review establish new photographic quality.

## Export contract

VERIFIED source inspection: simple-session contribution-map export borrows the exact final native merge planes before their reorder or demosaic. The shared streamed writer preserves signed f32 values, interleaving rows R,G1 thenG2,B from the native API order R,G1,B,G2. It checks finite values and uses bounded32-row strips, including a partial final strip; no aligned-frame volume or new image estimator is introduced. The checked reservation covers stripe storage and encoder overhead and is added only when this export is requested.

The typed report declares strehl.session-native-sensor-master.v1, file sensor-master.tiff, stage native-merge-before-demosaic, RGGB, signed-f32, full/crop geometry, sensor origin/dimensions, recorded per-pass photometric gains and development reference. Values are black-subtracted DN; no white balance, color matrix, display exposure or additional clamp is applied by this exporter. reconstruction_applied is false. photograph_reconstruction_requested separately records a later RGB reconstruction request, whose result may entirely fall back. This file must not be described as the final reconstructed RGB photograph or original camera RAW.

The CLI completion chain requires the file exactly when the typed report declares it: nonmosaic render bindings contain exactly the old three outputs or those three plus sensor-master.tiff. Mosaic retains its existing eight-file contract. Unsupported, missing, unbound and tampered declarations/files refuse. The stream test checks every site of a signed5x17quad fixture, including the34th sensor row, exact f32 bits and unchanged input planes.

## UI author implementation and independent review

The UI verifies and reads the bound render report before choosing its exact output census. It parses schema/file/stage/CFA/storage/reconstruction_applied with actual field types, then requires the declaration, physical file and fourth binding to agree. Unknown bound files cannot exploit the optional slot. Legacy unbound sensor sidecars refuse rather than acquiring a renderer-bound label. Imported provenance includes the sensor hash, so later saved reopen verification detects changes. Existing legacy three-file and mosaic eight-file contracts remain intact.

Source checkpoint: session-import.rs SHA256e08cc7d16e0f1d819c715d94c30801a05738879404dd068cbec8958012d71869; session-import-tests.rs SHA2561bace0779fdd210289952409d847f5f501a1647e29e8c73be0c2641960f9a80f. These files were formatted with rustfmt --edition 2024 --config skip_children=true crates/strehl-ui/src/session-import.rs crates/strehl-ui/src/session-import-tests.rs. The root independently reviewed the typed declaration and exact census before execution.

VERIFIED retained receipt and log: cargo test --locked -p strehl-cli -p strehl-ui session -- --test-threads=4, native-master-session-controls-01, exit0. Fresh Compiling is present for CLI and UI. CLI155 passed; UI64 passed, including positive optional import/reopen, hash mutation and17 malformed/missing/unbound/extra-file cases. Elapsed76.885 seconds is provenance only. No strict-lint or whole-workspace success is inferred from this filter.

## Remaining integration evidence

A full native run with export on versus off must retain identical photograph and RGB-master pixels; the writer's borrowed-plane/no-mutation test supports this expectation but does not replace end-to-end readback. New risk observers must read the native artifact in its exact stated gauge, gain and CFA order, preserve negative values and distinguish pre-demosaic merge from later RGB processing. The existing full32 outputs lack independent held reference acquisitions; a24-source held-acquisition comparison remains conditional on its frozen all32 geometry ancestry unless a separately controlled geometry fit is used.
