# M194e fourth complete float-run release

2026-09-07, root. Amendment4 and independent review were preregistered at
`d32bd33a`; source and author controls were committed at `89ce6313` before
this release. Release one fresh complete float-run-4, five primary images,
five angle refinements and five cell refinements. Reuse no earlier full-run
image. The three failed attempts and their exact sources remain retained.

The new family-wide cell-consumed pupil targets and relative weight-mass
check are explicit. All global cell/pupil, whole-image/edge and refinement
limits, model, scene, quadrature orders/depths and resource caps stay fixed.
No separate spatial half-budget test or analytic full-layer fast path is added.

Root parsed these complete current-source component results and their failures
and source-invariance fields. Textured API rows carry numerical error_e fields;
all336 were checked against the actual .004/.0008 max/RMS bars.

| Result | Passing population | SHA-256 |
| --- | --- | --- |
| author-controls-11/result.json | 264 | 7313221769eac8d09f133f08a69691245727c7440adc2826bad13ef4bddc8123 |
| independent-target-controls-1/result.json | 62 | c94c6c8a6222d68406eea8cd4c39fa4f70fe2771e0662a74b87a721e9910993b |
| independent-author-api-6/result.json | 31 analytic +336 textured | 466c380788d3ce726d3cc91f02da1c7addde71eb3afd02eecd477058d7832f9d |
| independent-map-controls-3/result.json | 400 | 44aa1c841eed2fff3057c4351c7bf054eb9c55a9cb67d420bb4f8be66ae74245 |
| independent-allocation-controls-4/result.json | 62 | 2b67e94226da7cf0a09d6378ea180c9fad4125c12b7aa54672503dcf4a68ff04 |
| independent-observer-4/result.json | 32 | 87ae62c0f302e39b2c2f4c70447cabba2596a5f2263300502b086b7c41f09640 |
| independent-reader-controls-6/result.json | 9 | 05042a5b6ab3cd96e447d9e2811999251fea909adc3c1e8694747c47e3f69b82 |
| independent-emission-api-7/result.json | original109 +82 allocation +15 target | 97a27dd56ddc0fccf18c7d5f53bb57556adfc025209b32553b446774f0a81a69 |
| independent-final-cfa-controls-5/result.json | original26 +10 allocation +3 target | e73ded3f0d3c0d8d76a590a77c3855ea7f2f119097616f64e9a1de0806677fc4 |

The source-bound genuine CFA reader again refuses fixture authority; no gate
was issued. The full-float reader passes its predecessor/source preflight and
refuses the deliberately absent bundle, with zero images read. Neither
refusal supplies scientific admission.

Frozen renderer SHA is
`487c1727ca3aab05dd66a7056fb368712ccaabbbe604818fdc8b47eda77b6e97`;
schema SHA is
`1efac4ff18b704047d3386e58379e6dd5c53fc7cd28854da044d20b35c179d13`.
Author controls bind all six producer Python sources. The full controller
binds the eight final design documents at entry and exit, including contract
SHA`c362b63626a820615b59584889492d94bc6520aa36c415a75443e2fcdde868cb`.
Its last wording repair clarifies partial-frame counts and changes no rule.

Run exactly, retaining stdout/stderr and a fresh bytecode prefix:

```text
python -X utf8 -X pycache_prefix=experiments/m194e-joint-pupil/work/cache-float-run-4 experiments/m194e-joint-pupil/commission.py --output experiments/m194e-joint-pupil/float-run-4 --controls experiments/m194e-joint-pupil/author-controls-11/result.json
```

Curie runs the producer. Only after its complete result does Zeno compare all
fifteen new arrays with the frozen independent reference, using the refreshed
reader and a fresh cache. Any full-run refusal remains a failure. Only a
genuine independent full-float PASS permits root's CFA emission, followed by
Socrates's independent actual-value conversion check. No physical calibration,
product quality, performance, default promotion or SOTA claim follows here.
