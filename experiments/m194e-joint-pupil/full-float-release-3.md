# M194e third complete float-run release

2026-09-07, root. Amendment3 was preregistered at `2a75e519`; its numerical
implementation and author-control evidence were committed at `8596d413` before
this release. Release one fresh complete `float-run-3`: five primary images,
five angle refinements and five cell refinements. No frame from either failed
full run or a diagnostic substitutes into it.

The local area-proportional admission rule has explicitly changed to global
absolute-error allocation. Retain every registered model/population, whole-cell
and separate pupil limit, independent image and refinement limit, quadrature
map/order/depth and work/time/storage ceiling. Any refusal remains a failure.

Current source-bound component results, all under this experiment:

| Result | Passing population | SHA-256 |
| --- | --- | --- |
| author-controls-10/result.json | 196 | f04daa9b382c4f7800387dfab3a1829ad5d2c0c921fbffd830d5e7110bc9fbed |
| independent-allocation-controls-3/result.json | 62 | 358905a23abbe77453b2eb6c8ff04f8d9153a8aaa798d72546f71250300754f6 |
| independent-author-api-5/result.json | 31 analytic +336 textured | 72304b090ab0eb39c56583146c59e4fbcfefd272ef7adb951283121e5f1e244f |
| independent-map-controls-2/result.json | 400 | 3c4eae49bd5097d1f7ae2cca0d8e1981f2eb8985e87873bbad8a4b3b629b4d68 |
| independent-observer-3/result.json | 32 | 29e7312d20bd2a46033c1ce5fc982749a52f95ef6ad533f87f1960d902b507fd |
| independent-reader-controls-5/result.json | 9 | fe1d8474cd3e4aef9f6d6b66e33ebec3127fec4f1c9cf7497746e0d4052b8b27 |
| independent-emission-api-6/result.json | original109 +82 metadata | 1ca0bd3f9d7b3cea582372e8c88b5392b844c86ea28015179e7a51d38b54c9f3 |
| independent-final-cfa-controls-4/result.json | original26 +10 metadata | c7897cdae51520b035141086ef2c544d8cf95ad69d11ab2069776180bf3aa07f |

Root parsed each complete result, including all336 numerical texture errors;
those rows carry errors rather than individual pass flags. The initial generic
flag-count query was inapplicable and was corrected against the actual error
fields and the source's max/RMS conditions. Source-invariance checks pass.
The genuine final reader again refuses private fixture authority; no CFA gate
was produced by that control. Independent allocation run1's wrapper-lifetime
defect and author controls9's unpowered depth fixture remain preserved.

Frozen producer renderer SHA is
`a22d49fd43a1bc8d0f807fc1d4417104d5b9ffe1d771b418be58d276d7804460`;
schema SHA is
`578f403ed7167c6c0988d927691fa91e5deec7010407f90999e12a0328bbaf8b`.
The unchanged model, controller and emitter and updated author controls are
bound by controls10 and the before/after source snapshots of the intended run.
All seven current design files are frozen at entry and checked at exit.

Run exactly, with a fresh bytecode prefix and retained stdout/stderr:

```text
python -X utf8 -X pycache_prefix=experiments/m194e-joint-pupil/work/cache-float-run-3 experiments/m194e-joint-pupil/commission.py --output experiments/m194e-joint-pupil/float-run-3 --controls experiments/m194e-joint-pupil/author-controls-10/result.json
```

Curie runs the producer; Zeno independently reads every new array against the
unchanged frozen reference after a complete producer result. The producer cannot
commission itself. Only a genuine independent full-float PASS permits root's
CFA emission, followed by Socrates's actual-value final check. This release
establishes no physical calibration, production quality, default or SOTA claim.
