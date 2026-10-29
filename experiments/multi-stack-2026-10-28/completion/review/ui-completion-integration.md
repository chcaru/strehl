# Desktop completion integration

Status: source implemented; root-scheduled controls are recorded below. Actual GPU inspection of the new inspector is pending. This author implementation work follows the earlier independent review and does not replace independent review of its behavior.

## Saved options and mode scope

Old SessionDraft JSON defaults precision_weights, contribution_maps, focus_evidence and reproducibility to false. New drafts and immutable worker recipes retain the four choices; CLI forwarding uses those saved values. Precision requires at least two Repeat/HDR passes. Automatic reproducibility compares the first two declared passes in Combine/Interleave/Repeat/Layers. Focus evidence is optional outside Mosaic. Mosaic clears primary preference and the inapplicable ordinary diagnostic switches; its own coverage/join evidence is inherent. Invalid local-control requests fail before catalog mutation. Ordinary stack settings retain their existing route and restoration behavior.

VERIFIED by root: 26 session tests in outputs/multi-stack/completion/ui-session-controls-01. These include old-draft defaults, exact immutable command flags, incompatible-option no-op controls and ordinary transition regressions.

## Coverage, edits and export

The published Mosaic completion must bind final coverage.tiff with coverage_sha256. The UI verifies that checksum, exact photograph dimensions and binary Gray8 values. It does not re-erode physical support. An immutable Arc mask follows the loaded photograph and DevelopmentJob. Overview and native view samples touching unsupported coverage show a stable checkerboard; supported RGB remains unchanged. The checker is presentation data and never enters the linear image or export.

The additive shared export_image_with_coverage API uses the existing atomic color-managed writer. TIFF and PNG retain exact developed RGB, ICC metadata and straight alpha. Ordinary export_image delegates with no mask and retains byte-identical delivery. Current JPEG/AVIF coverage delivery refuses with an actionable TIFF/PNG choice before publication; unsupported pixels are never silently filled black. This is a current format limitation, not a claim that those container formats inherently lack alpha.

VERIFIED by root: two export controls plus nine matching UI controls in outputs/multi-stack/completion/ui-coverage-controls-01; the log shows fresh Compiling of edit, CLI and UI. Three new UI coverage controls exercise checksum/shape/type, no extra erosion, native/overview identity and checker exclusion from exported pixels. Two shared scalar reader controls passed in outputs/multi-stack/completion/scalar-reader-controls-01.

## Saved diagnostic inspection

The optional inspector reads saved focus, per-band contribution, first-two-pass reproducibility and Mosaic coverage/join/owner maps. It bounds JSON and scalar payloads, checks recorded geometry against photograph dimensions, accepts only basename TIFF receipts, verifies SHA256 and retains NaN as missing rather than zero. One selected full scalar field plus a bounded nearest-sampled display is retained; raw hover/probe values refer to original saved cells. A serial decoder lane prevents cancelled instances from multiplying large active decodes. Cancellation retains a pending lane until its worker retires.

Focus ordinals and local peak widths are descriptive shape, not metric depth or calibrated confidence. Contribution ESS/weights/variance refer to coefficients before collapse/demosaic/hull; conditional variance is not final-pixel uncertainty. Reproducibility exposes qualification and ring correlation/power curves. Unverified focus stays explicitly unverified even when correlation is high. Right/bottom incomplete spectral tiles have no result. Mosaic join status is categorical and does not pretend to be a probability.

Map state is separate from the photograph/edit recipe. inspect_session_diagnostic accepts only an exact current snapshot.saved_diagnostics.available label plus bounded opacity/sample coordinates; it accepts no path. The common worker pump supports headless discovery without claiming rendered UI evidence.

New adversarial controls cover invalid path labels, checksum tampering, canvas mismatch, partial spectral margins, tile ordering/qualification and normalized/no-op local-control requests. Their scheduled results and actual GPU evidence must be added after root execution.

## Actual UI commissioning preparation

[ui-completion-controls.py](ui-completion-controls.py) prepares four separately invoked phases. Options exercises automatic/explicit primary, Mosaic no-primary, incompatible requests and saved-draft restoration. Inspect discovers actual map labels from a fresh snapshot, probes the saved values and checks a refused unknown map. Render is disabled unless root explicitly supplies --permit-render. Capture uses only scripts/strehl-control.py screenshot and the actual offscreen egui/wgpu renderer.

The screenshot helper now supports a known --open-run in an isolated --catalog, exact diagnostic label/opacity/sample and bounded photo zoom/center. Capture waits for the actual map and two later painted frames. Unknown/malformed maps fail the screenshot instead of silently producing a plain photograph. Headless zoom command acceptance is recorded separately from actual GPU output. No OS automation is used.

Prepared, not executed here: isolated completion/desktop-06 controls against the real interleave and HDR precision outputs using the product Open completed CLI session path. The imported result preserves source receipts and labels renderer provenance; it does not imply the desktop worker authored the CLI render.

## Historical source-cache review

Independent read-only review of completion/sr/historical-cache.rs found no blocker in exact lock-minus-one-core-sha2/raw-source binding, header identity/geometry/envelope checks, full header+payload digest, read-only cache behavior or resident-budget handling. Original source freshness remains size/mtime-based, not a new full RAW hash on every memory hit. A malformed unrelated .cfa header causes conservative mixed-directory refusal. These are explicit research-reader limits; production cache acceptance was not relaxed. UI/edit additions use existing dependencies and leave Cargo.lock unchanged.


## Completed CLI import — implementation freeze

AUTHOR IMPLEMENTED, tests pending root scheduling: Open completed CLI session in Projects, `--open-run` for uncatalogued completed directories, and granted local command `import_completed_session` share one bounded worker. The worker verifies ordered pass/segment/source census, photograph/master geometry and scene-linear baseline, original renderer bindings plus aggregate completion when present, scalar map checksums/types/dimensions, and immutable current-file SHA identities. Legacy completed results explicitly report original output binding unavailable. Diagnostic schema warnings remain explicit and do not become independence certificates.

Imported catalogs and reopen paths do not scan RAW folders; capture thumbnails are withheld. Source folders from saved JSON do not create filesystem grants. Reopen rechecks retained artifact identities. Catalog insertion rolls back on failure; cancellation retains the worker lane until it exits. Four adversarial controls cover nonexistent source folders, legacy scope, changed output, incomplete/new binding publication, aggregate/payload tamper, ordered census, canvas, path escape, cancellation, transactional catalog failure and provenance immutability. Actual root tests and GPU results must be recorded before claiming verified behavior.

VERIFIED root-scheduled `ui-expanded-controls-02`: all34 session/import/diagnostic controls passed after a fresh UI compile, including all4 new importer controls. The first `session-expanded-08` compile failed at nested snapshot JSON macro recursion; imported provenance was moved outside the main macro, with no recursion-limit increase. Actual GPU commissioning remains pending.

## Actual binary08 commissioning checkpoint

Actual isolated mailbox workspace PID28228 exercised product completed-session imports for interleave-02 and hdr-precision-01, retaining explicit legacy current-file identity. Saved maps were selected by discovered labels, sampled and opacity changed; unknown path-like labels refused without changing selection. Saved result reopen succeeded. Staged pitch8 23+23 source folders were read for headers/previews only. Repeat automatic primary, explicit primary0, Mosaic no-primary refusal and saved draft immutability all passed. No RAW decode or engine render was requested. Orderly shutdown and launcher exit0 are retained under outputs/multi-stack/completion/desktop08.

**Not yet verified visually:** first actual GPU capture timed out after60s with the imported result reopened. Diagnostic-map, plain-with-view-preset, and plain-without-preset attempts all exited1 and produced no PNG. Owned PIDs41108,9564,20348 exited. This rules out selection/zoom-specific failure but does not establish the pending condition. Added actionable pending-state information to the offscreen timeout (readiness/deadline unchanged), awaiting root-scheduled rebuild. Logs/failures remain retained; no screenshot success is claimed.

The source blocker is now identified: `show_process` fell back from no scan to `expected_run.frames`, so imported results advertised182 available thumbnails and GPU readiness waited indefinitely. The fix restricts imported-result browser counts to actual scans, preserves summary provenance counts, and labels unloaded originals explicitly. App/component controls added; root schedules the new build. The diagnostic timeout remains useful for future failures.

**VERIFIED actual new binding positive:** binary08 product import of `interleave-pitch8-01` accepted strict renderer output plus aggregate completion bindings, selected catalog stack13, returned `renderer_bound:true`, and retained `source_count:null`. Scope: “Imported CLI result · renderer output bindings verified. Original capture previews are not loaded.” Evidence: `desktop08/import-bound-pitch8`. Owned PID23484 shut down cleanly. This is an import/provenance check, not a GPU verification or independence certificate.


## Actual GPU build09/build10 follow-up

VERIFIED: the imported-capture readiness fix passed the actual offscreen GPU path. Build09 produced six 1440 x 940 interleave screenshots, all exit0, and all were visually inspected. Totals, immutable saved passes, truthful unloaded-original scope, photo zoom and saved raw cells/curves were legible. They exposed an overlay projection bug: the second viewport rectangle was a screen aperture, not normalized UV. The diagnostic layer was consequently absent; that failed state is retained under `outputs/multi-stack/completion/desktop09/gpu-interleave`.

Build10 (strehl-ui.exe SHA256cc362ba91ee3d7771ff34d35d43f1d27ea91165f7aa3c4c6d0f2db3962f43398, verified before launch) produced six interleave and four HDR 1440 x 940 screenshots, all helper exits0. Every screenshot was inspected with original detail. Contribution, focus-flag and comparison overlays now physically follow the photograph at 1x and 8x. The incomplete comparison border remains uncolored. Raw cells, decoded flags, comparison qualification and ring correlation/power curves remain legible. All scopes state that imported camera previews are not loaded; the 182-source and126-source census is retained without fictitious thumbnail requests.

A smaller actual GPU defect was found at 8x: the main-photo map painted over the inset navigator with the main-photo coordinates. The frozen next source excludes the navigator's actual drawn rectangle from map paint and hover probing. The existing actual-egui mesh test now checks four clipped pieces, total painted area, and unchanged probe under navigator hover. This source fix awaits root-scheduled compilation and a new actual screenshot; build10 does not claim that defect fixed.

Commands actually run (build10, without RAW decode or renderer):

```powershell
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/ui-completion-controls.py capture --exe outputs/multi-stack/completion/binary-10/strehl-ui.exe --evidence outputs/multi-stack/completion/desktop10/gpu-interleave --run outputs/multi-stack/completion/interleave-02 --catalog outputs/multi-stack/completion/desktop08/projects.json --inspection outputs/multi-stack/completion/desktop08/inspect-interleave-02/result.json --sample 0.6 0.5 --opacity 0.6
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/ui-completion-controls.py capture --exe outputs/multi-stack/completion/binary-10/strehl-ui.exe --evidence outputs/multi-stack/completion/desktop10/gpu-hdr --run outputs/multi-stack/completion/hdr-precision-01 --catalog outputs/multi-stack/completion/desktop08/projects.json --inspection outputs/multi-stack/completion/desktop08/inspect-hdr/result.json --sample 0.6 0.5 --opacity 0.6
```

Each folder's result.json and numbered command receipts retain the exact helper invocations and process exits. These concurrent UI checks are not performance measurements.

## Optional original-CFA UI source checkpoint

Root-approved source now carries `original_cfa_reconstruction`, defaultfalse, through saved drafts, agent schema, immutable jobs and `--original-cfa-reconstruction`. It is limited to Combine/Interleave/Repeat/Hdr; Layers/Mosaic are refused before catalog mutation and mode changes clear incompatible next-run preferences. Existing ordinary settings remain unchanged; session jobs already reject binned output. The product label is “Original-CFA reconstruction (experimental)” and states that unsupported pixels retain the native result and output dimensions stay unchanged.

The new saved inspector reads outcome counts/limitations independently of optional-map loading. It verifies the geometry file against render-report.reconstruction.geometry_sha256, exact native canvas origin/dimensions/unit step/full bounds, two local map receipts and payload checksums. Support means coherent all-RGB replacement; fallback reasons use the renderer's explicit code labels. This is conditional support, not calibrated uncertainty or a resolution guarantee. Import retains geometry identity together with map identities. Wrong-count, wrong-origin, wrong-step/full-grid, wrong-schema/hash, tampered-payload and incompatible-mode controls were added. Root schedules tests/build; no unrun result is claimed at this checkpoint.

Root's GPU10 review identified a second visible legend issue: the power plot's first trace used the gold theme accent while its caption called it cyan. The source now uses explicit cyan/orange constants for both traces and colored labels; an actual egui shape control checks both stroke and text colors. A compact scalar color ramp uses the same mapping as the overlay and prints Low/High values. Reconstruction categorical maps show their exact code/label/color rows; other discrete maps explicitly warn that category colors repeat. These changes are source-frozen for root tests and require the next GPU capture before a visual pass is claimed.

## Original-CFA controls and inspector polish verified

VERIFIED reviewer-owned root-authorized commands: `ui-reconstruction-session-controls-03` freshly compiled UI and passed43 session controls; `ui-reconstruction-saved-controls-01` freshly compiled core/raw/plugin/CLI/UI and passed34 saved controls. Both exited0. Their complete logs/commands/resource receipts are retained under outputs/multi-stack/completion. Earlier failed compile attempts01(SHA formatting) and02(in-progress missing CLI module) remain recorded. The source now states that colors are sampled for display and hover/click reads the exact saved cell; actual next-build GPU evidence is still pending for the navigator exclusion, legends and original-CFA outcome panel.

## Actual UI12 commissioning complete

VERIFIED product12 UI SHA2562421be70e5df6585d0ca7b9ff1d988ce14268122b4e0b5ab375c58706d412a15:23 product commands passed reconstruction option immutability and unsupported-mode atomic refusals; owned mailbox process exited0. Six actual1440-by940 GPU screenshots all exited0 and were visually inspected. Low/High color ramps, cyan/orange power labels, sampling caveat and clean navigator exclusion now pass actual display review. Full scope, exact commands and PNG receipts are in [ui12-actual-gpu-review.md](ui12-actual-gpu-review.md) and outputs/multi-stack/completion/desktop12/review-receipt.json. No production reconstruction photograph or outcome panel is claimed.
