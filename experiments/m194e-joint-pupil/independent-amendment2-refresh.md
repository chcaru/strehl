# M194e amendment2 emission-reader refresh

2026-09-07. This applies the previously registered
[dependency refresh](independent-pin-refresh.md) to numerical amendment2,
released at `d839ce9b`. The [original API review](independent-emission-api-review.md)
and [final-reader commissioning](independent-final-cfa-reader.md) remain valid
records of their earlier source revisions. Their historical source-bound results
are not silently reassigned to this numerical method.

## Released change and retained scope

The new method is `polar-radial-ladder32-tangent-cell-v3`, with
`cell_map: predicate-square-distance-duffy-v1`. The schema adds amendment2 to
design bindings. Model, fixed scene, sensor, CFA conversion, error thresholds,
path rules and emission arithmetic are unchanged. The source hash/check-count
refresh does not grant scientific authority to private fixtures.

The scalar oracle remains unchanged at
`1b23d656481752fc3c34384c489fc6556e78a74925d8cd717f4faa350040d48a`.
No historical46-control oracle campaign, M194b/c/d image matrix, production build
or RAW campaign was repeated. Actual conversion and the live renderer observer
are covered again by the requested109 API controls. The unchanged independent
reference arrays retain their original externally bound digest; no replacement
reference was invented to accommodate the author's traversal change.

## Intermediate source-bound result

Curie first released renderer
`a59e9686823d6f4ab2749dd8ca0f1a0bbf6cd847ee32ed04eef44dc78a87aba5`
with the172-check `author-controls-7/result.json`, SHA-256
`ca18b6643b7290a276a659b5c7057da941162371abf13857a3612f7896831cee`.
The schema is
`b3aee835d7bec9206ebff2401e3af5beb63fc66bf2aca3a32b272b69398edc54`,
the emission contract is
`a8cbf1107004bdc61058e544f1efe88ebed83b7e6eac2381429ae4d150de1c40`,
and emitter remains
`fbcdfa2c716f638e9aa8f9cf13ba3024a575feca0ad15d1a67012f51176c82fd`.

```powershell
python -B -X faulthandler -X pycache_prefix=experiments/m194e-joint-pupil/work/independent-emission-cache-4 experiments/m194e-joint-pupil/independent-emission-api-controls.py --output experiments/m194e-joint-pupil/independent-emission-api-4 *> experiments/m194e-joint-pupil/independent-emission-api-4.log
```

Exit0, **109/109**, all source and original private input bytes unchanged.
Result SHA-256
`114a1a04b73a89ad3350fd5d9f48a5870975dad8736f13d6643d1e7f7d584b06`;
exact driver snapshot SHA-256
`5461975bda20ecb57b42ee809b49ef3de83ec48f73f5e0e0e0a5d9915207c922`.

The roughly seven-second invocation finished before root's request to hold
for one further provenance repair arrived. Root found that `commission.py`
had snapshotted designs initially but only computed their manifest bindings
at completion. The requested repair freezes and compares the design bindings
before/after. API4 therefore remains an intermediate valid result on driver
`90154a821fe0ea416fde8407953337b1cc42b75422fef36cd217d124ec26b35a`,
not final closure of the forthcoming controller revision. No final-reader
pin was advanced to this intermediate API result.

## Final source closure

The final controller is
`bca12a5c0f4d995d60133780687874b1bd6c21d7cf7746f6232e2063516aab18`.
It freezes design bindings, checks them before/after and emits that original
binding. The matching real172-check author record is
`author-controls-8/result.json`, SHA-256
`169e098024d80d23ca8f8166d12eb89c6dfb356f57caef6d7451cac67ab745c4`.
Its172 PASS values and all six before/after source hashes were checked before
being copied into the private API fixture.

The final API command was the command above with cache/output/log suffixes`5`.
Exit0, **109/109**, all source and original private input bytes unchanged.
The final reader was then pinned to that exact API driver/result and released
schema, and run as follows:

```powershell
python -B -X faulthandler -X pycache_prefix=experiments/m194e-joint-pupil/work/independent-final-cfa-cache-3 experiments/m194e-joint-pupil/independent-final-cfa-controls.py --output experiments/m194e-joint-pupil/independent-final-cfa-controls-3 *> experiments/m194e-joint-pupil/independent-final-cfa-controls-3.log
```

Exit0, **26/26**, all source and original private fixture bytes unchanged.
The genuine CLI was subsequently invoked with this complete private package's
actual manifest/gate hashes and the new final-reader control hash. It exited1
with `UNCOMMISSIONED_CFA` and
`independent predecessor nonterminal or fixture/genuine mode mismatch: author_api`.
No `cfa-commission.json` was written. The exact CLI/interpreter invocation is in
`independent-final-cfa-genuine-refusal-2/result.json`.

| Final artifact | SHA-256 |
| --- | --- |
| API driver `independent-emission-api-controls.py` | `80e2621527990b9657bb8ffb1e2f4f7d9c87a1d0e69239244ddc3b22f9c51600` |
| `independent-emission-api-5/result.json` | `7a55a2507dad991f780b45e9aa6509306a3408e621acbfc44b3570c830062595` |
| `independent-emission-api-5.log` | `17d2b961d41fee923e747794d2ca82f4cdd63b8243828894d59db1f477e32e16` |
| Final reader `independent-verify-cfa.py` | `9eb2f1528881186ce4ccf4ce4c19e9ef0123fdaab273b52cd3b2ecef0ce40dd8` |
| Reader controls `independent-final-cfa-controls.py` | `b14c0124bcbcfd1c487838b01157fe95763ba170fe52bc4cb926e82f47167776` |
| `independent-final-cfa-controls-3/result.json` | `9228ee913035769419d0cc1c86daac5566360ac70c5e8c4684fe3ca14bfa96ce` |
| `independent-final-cfa-controls-3.log` | `3c96ff98ae2e5326c669d1b103f10b64529db58e4a79b119691529c587327472` |
| `independent-final-cfa-genuine-refusal-2/result.json` | `054e685d8fec69a5be44ae7044f8ce0ecf7e9cf0c2c603b7608bf4d5f21671a3` |

The final-reader control code is byte-unchanged. API-driver edits are dependency
pins, the author-control path/hash and the explicit expanded172-check population.
Final-reader edits are dependency pins and the new API-result path/hash. The
existing exact-conversion, reference-error, tie-allowance, refusal and observer
expectations remain unchanged; no threshold was relaxed. Source differences
against the earlier snapshots are retained in
`independent-amendment2-reader-source-diff.txt`.

**Disposition: the refreshed API/reader boundary is VERIFIED on its private
controls.** There is no remaining blocker in this lane for the new full float
run. Genuine emission and CFA commissioning still require complete independent
mathematical admission and externally supplied real artifact digests. No
fixture-only gate was promoted, and the previous incomplete full population
remains uncommissioned.
