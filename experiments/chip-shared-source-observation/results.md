# Complete chip shared-source observation: rejected

2026-09-25. MEASURED execution; root and independent photographic rejection.
This rule remains experimental. No production default changes.

Commands executed with Python3.12 from the repository:

```
python -I -B -X faulthandler experiments/chip-shared-source-observation/run.py build --out experiments/chip-shared-source-observation/build-1
python -I -B -X faulthandler experiments/chip-shared-source-observation/run.py controls --build experiments/chip-shared-source-observation/build-1 --out experiments/chip-shared-source-observation/controls-1
python -I -B -X faulthandler experiments/chip-shared-source-observation/run.py full --build experiments/chip-shared-source-observation/build-1 --controls experiments/chip-shared-source-observation/controls-1 --execute-approved-observation --out experiments/chip-shared-source-observation/run-1
python -I -B -X faulthandler experiments/chip-shared-source-observation/run.py views --run experiments/chip-shared-source-observation/run-1 --out experiments/chip-shared-source-observation/views-1
```

The fresh build completes in198.453seconds. Three capacity controls and the two
unchanged old controls pass. The complete old generated screen is byte-identical:
SHA256 `460ed3045c650ac1a8bf3a9819ccc8999b2b1a2e9bcee1ad7fd4abb2ea053d0f`.
Its generated glint-core and near-detail harms remain. This separately authorized
299-source photograph tests a previously unrendered scene, not a revision of
that rejection. Only the two explicit70-to299 capacity limits change in copies
of the old costs/replay code; the runner checks those substitutions exactly.

The complete two-pass job finishes in293.110seconds, with peak committed job
memory17,901,383,680bytes. These are operational receipts, not speed benchmarks.
Reference149 and crop[133,89,3250,2166] produce6500x4332 output. Baseline RGB16
and ICC match current production exactly; the pinned baseline rewrite is exact.
Candidate development uses the same resolved tone. All299 source replay hashes
and colour-site support checks pass; original metadata and the map are unchanged.
The generated qualification and automatic photographic admission remain false.

Root inspected one unresampled pair in each of the seven fixed regions, plus
complete views for orientation. Some contacts become more abrupt, but large
new colour islands appear in yellow interiors and green shadows. Lower-array
rails acquire patchy transitions; broad bright plumes and duplicated edges
persist. Independent review inspects both complete views and all25 prescribed
native pairs and confirms material photographic regression. See
`independent-photographic-review.md`. No parameter sweep, marigold transfer or
default promotion follows. Sharper-looking edges do not compensate for damage
to the surrounding image.

Complete TIFFs remain in `run-1/output/`; full JPEGs and fixed native tiles are
in `views-1/`. Saved run completion deliberately retains its historical
awaiting-review status; this report and the independent review record the
subsequent decision. Later source additions do not retroactively alter its
bound build or completed execution receipts.
