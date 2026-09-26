# Same-band source agreement: complete chip observation

2026-09-25. Root owns execution. Independent interpretation is recorded separately.
This experimental rule is not a production default or a SOTA result.

Commands executed from the repository with Python3.12:

```
python -I -B -X faulthandler experiments/band-source-agreement/run.py build --out experiments/band-source-agreement/build-1
python -I -B -X faulthandler experiments/band-source-agreement/run.py build --out experiments/band-source-agreement/build-2
python -I -B -X faulthandler experiments/band-source-agreement/run.py controls --build experiments/band-source-agreement/build-2 --out experiments/band-source-agreement/controls-1
python -I -B -X faulthandler experiments/band-source-agreement/run.py full --build experiments/band-source-agreement/build-2 --controls experiments/band-source-agreement/controls-1 --out experiments/band-source-agreement/full-1
python -I -B -X faulthandler experiments/band-source-agreement/run.py views --run experiments/band-source-agreement/full-1 --out experiments/band-source-agreement/views-1
```

MEASURED: build1 fails at the large receipt's json macro recursion limit. Splitting
that same flat object into two objects and extending the first preserves all
keys/expressions, independently source-reviewed. No global recursion limit or
image arithmetic changed. The failed build remains intact. Build2 freshly
compiles both core and CLI and succeeds in196.656seconds.

MEASURED: all four independent controls pass in2.547seconds. These are single
operational costs, not speed benchmarks. The original general screen remains
false at both tested ISOs; its positive outside-spill fixture is unexercised.
The separately declared preservation screen passes. Contact-edge truth error
falls about2.3–2.5%, outside error rises1.4–1.7%, and glint-core error rises
2.7–3.24%. Flat controls are effectively unchanged, both true depth components
are retained, and the forced wrong-source destroyer is rejected. See
`independent-controls-result.md`. RMSE can reward smoothing; these checks are
only a damage screen, not photographic quality evidence.

Root therefore authorizes the one previously scoped complete-chip observation.
The runner keeps automatic photographic admission false and binds every source,
the current production master, geometry, injected noise and exact baseline tone.
MEASURED: the complete299-source job succeeds in376.797seconds, including its
two source passes and diagnostic/output work. This is not a production speed
benchmark. The complete baseline RGB16 and ICC match current production,
the baseline pinned rewrite is exact, both complete plane reconstructions
replay exactly, original metadata remain unchanged, and candidate tone is
literally the baseline's resolved tone. Candidate pixels change; that alone
is not a quality result.

Root viewed both complete-field overviews for orientation and one unresampled
native pair from each of the seven fixed regions. No convincing contact/grid,
rail, compartment or broad-spill repair is visible. Scratches and small marks
remain; the large existing defects also remain. Independent review then viewed
both complete images and all25 native pairs and also rejects the candidate:
no useful visible gain. See `independent-photographic-review.md`.
The full candidate JPEG was shown to the owner. No tuning sweep or production
promotion follows a negative complete-image result.

Both complete TIFFs are in `full-1/output/`; complete JPEGs and all50 native
tiles are in `views-1/`. Its completion receipt records their coordinates,
conversion, dimensions, ICC, hashes and source run. Every defect judgment
above uses native tiles; resized overviews supply orientation only.
