# M194b post-render reader revision

The forty production TIFFs in `baseline-1` completed with unchanged sources.
The first scoring invocation refused at compiler-artifact path comparison:
Cargo's JSON uses forward slashes and the recorded Windows `Path` uses backslashes.
This is a reader representation error, not a different executable or a failed
product render. The first call produced no score file. Its exact command was:

```text
python -X utf8 experiments/m194b-known-scene/score-benchmark.py --index experiments/m194b-known-scene/baseline-1/run-index.json --expected-index-sha 37f99736bd32dfb4891bd8fa2b033cacc2c58e9265515fa53cb5921dd80d9c08 --out experiments/m194b-known-scene/baseline-score-initial.json
```

Before scoring those unchanged pixels, the root repaired platform-equivalent
path comparison and added the reviewer's final actual executable-length and
CameraLinear ImageDescription checks. Orientation and ICC mutations had
already been refused before rendering; the separately retained description
mutation exposed a further disposition gap in the reader.

The rendered input index and its original source snapshots stay immutable.
An external `reader-revision-v1.json` names that exact input-index SHA and both
old/new hashes for **only** `score.py` and `score-benchmark.py`. The caller must
supply that revision file's own expected digest. The reader requires the old
hashes to match the render snapshots and the new hashes to match its actual
analysis code. This explicitly separates an analysis-code repair from the
already frozen producer/consumer execution; it neither rebuilds the merger nor
rewrites a render's source identity. Independent validators receive this
binding and re-choose whole-package corruptions with it.

No target, mask, noise/optical constant, baseline setting, uncertainty formula
or acceptance tolerance changes. Metadata-only refusal checks do not require
rerendering the unchanged image inputs. Later reader corrections, if any, need
their own preserved revision file and reason; a revision must never silently
authorize a different producer, consumer or pixel bundle.

The first revised reader then reached the complete command history and refused
an actual same-file spelling: Rust canonicalization emits `\\?\C:\...`, while
the Python command uses `C:\...`. `Path.resolve()` preserves that difference
here. Version 2 uses the filesystem's same-file check for the already existing
TIFF, retaining content, byte-length and command bindings. The v1 revision and
both failed attempts remain; neither produced a score artifact.

Independent verification of v2 admitted the real bundle and rejected nine
coherently re-sealed geometry/config/readout corruptions, but accepted an extra
unknown plan field. Version 3 enforces the frozen plan's exact field set,
matching the declared strict reader scope. This is schema hardening: the actual
bundle, numerical results and nine material corruption refusals already passed.
Its v2 result remains recorded as nine of ten expected refusals.
