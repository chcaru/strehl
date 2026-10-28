# Complete weevil alignment observation

2026-10-27. **MEASURED instrument completion; no photographic improvement.**
The optional read-only observer collected all existing alignment attempts for
the299-source glitter-weevil stack. The resulting map is byte-identical to the
held map. This establishes nonperturbation and retains previously missing
observations; it does not establish correct physical placement, a lens law,
recovered hair detail, or satisfaction of the quality goal.

## Actual observation

Input: `D:/personal/macro/insects/bug-3/107MSDCF`, exact ordered299 originals from
the existing manifest SHA`0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f`.
Reference149; guide3516x2344; ordinary deep configuration: coarse factor8,
coarse tile32/grid8x6/radius10; fine tile128/grid12x8/radius6/margin96;
minimum contrast4/peak0.5/tiles8; MAD multiplier3; one fine pass; unwarped tiles;
separable peak; spans1,2,4,8,16,32,64,96,128. Normal measured-component solve,
unit edge weighting, smooth1/huber1, Catmull-Rom map. Four workers.

| Retained quantity | Result |
| --- | ---: |
| Original sources decoded/preserved |299/299 |
| Requested pairs/fine passes |2340/2340 |
| Attempted fine tiles |224640 |
| Correlated tile observations |89131 |
| Accepted edges/refused pairs |2314/26 |
| Placed/refused frames |299/0 |
| Additional ordinary pair parity fits |4, all exact |
| Retained trace allocation |33323482bytes |
| Complete JSONL |172170684bytes |
| Owned-job wall time |139.25s |
| Peak job committed memory |10139885568bytes |

The four separately counted parity pairs were(0,1),(104,105),(148,149),(0,128),
using decoded guides without additional RAW decoding. Original SHA/size/mtime,
guide bytes, config, manifest, held map and executable remained unchanged.
All2340 requested pairs reached fine measurement; all26 refusals occurred at
spans96/128 through insufficient correlated/surviving tiles. There were no
omitted pairs. The native text map SHA remains
`4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225`.

The140-second observation includes input/guide hashing, serialization and four
extra fits. It is not a clean speed comparison with the old128.266-second
alignment job. Host load and terminal job accounting are retained. It stayed
within300s/1200CPU-second/16GiB bounds with no cleanup errors.

## Controls and descriptive findings

**VERIFIED:** the freshly rebuilt core and CLI controls passed. Ordinary and
observed results/edge order/maps are exact; actual coarse/flat refusals, one
outlier patch and a failed later pass retaining pass0 were exercised. Actual
green-guide construction passed the labelled-u16/individual-black-clamp test;
the actual R/B-substitution foil failed. All591 ordinary core tests passed;
four externally scheduled tests remained ignored in that ordinary run.

The fixed35-site continuous-scene discriminator retained every correlated
site, including later outliers. Symmetric defocus alone produced signed
anisotropy amplitude0.00213 and vector RMS0.03749guide pixels. The planted
non-similarity gave amplitude1.00340 sharp and1.00042 defocused, RMS0.05177 and
0.09625. Wrong-scale traces failed the same scorer. These are narrow generated
controls, not a camera calibration or a deep curved-track placement result.

**MEASURED descriptive census:** for spans1/8/32, correlated tile counts were
14008/13645/8400; search-border peak refusals31/58/4004. A Border refusal is a
correlation peak at the search boundary, not an out-of-image sample. The
all-correlated final-fit residual RMS(x,y) was respectively(.364,.259),
(.839,.905),(2.063,2.484)guide pixels. These compare different accepted/support
populations and remain confounded by focus, texture and clipping of the search.
Survivor residual means near zero are constrained by their fitted similarity.
None of these values is a measured displacement of an insect hair.

The signed-vector CSV explicitly recomputes diagnostic residuals from saved
f32 observations and saved f64 fits; it does not relabel them as originally
retained signed residuals. Original scalar residual arrays are retained too.
The initial summary does not transport source-i tiles to anchor149. Conditional
footprint transport and independent focus-support interpretation are separate
required steps before deciding whether the evidence supports any correction.

**MEASURED conditional support:** fixed spans1/8/32 cover856 pairs and82176
tile slots. Every footprint has positive overlap with its corresponding
anchor149 template under the held map. IoU minima are0.58028; mean IoU is
0.88604/0.88776/0.89332 respectively. Source-area overlap is at least0.74400.
This removes a blanket missing-image-footprint objection, while remaining
conditional on the existing map. It does not prove that the same hair/scale
dominates every correlation. The full [support receipt](../../../outputs/raw-quality-2026-10-27/insect-placement-support-1/output/support.json)
retains continuous overlap, all statuses, exact inverse/centre convention and
sample-cell corners distinct from fitting centres. No overlap threshold was
selected. Identity/translation/scale-rotation and wrong-inverse/centre controls
were exercised first. This saved-data job took3.765s/18984960bytes peak commitment;
it made no RAW read, fit or warp change.

**Independent decision after photographic review:** tiles15,41,56 retain every
span1/8 correlation and overlap the existing leg/hair, upper dorsal texture and
thorax witnesses. The existing whole-source/native views show different focus
neighborhoods there. This is enough for one predeclared held prediction test of
a measured field, with acquisition-disjoint training/held groups and span32
retained as an adverse population. It is not yet an identified physical
placement error: only reference-i footprints were transported, and the matched
moving patch/within-tile structure is not independently established. Do not
install a richer warp or claim restored insect detail from this observation.

## Reproduction and evidence

Commands actually run from the worktree:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-placement-observer/run.py build
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-placement-observer/run.py controls-core
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-placement-observer/run.py controls
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-placement-observer/run.py core-tests
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-placement-observer/run.py observe
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-placement-observer/run.py summary
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-placement-observer/run.py checks
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-placement-observer/run.py support
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-placement-observer/run.py build --iteration 2
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-placement-observer/run.py controls-core --iteration 2 --build-iteration 2
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-placement-observer/run.py controls --iteration 2 --build-iteration 2
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-placement-observer/run.py core-tests --iteration 2 --build-iteration 2
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-placement-observer/run.py checks --iteration 2
```

Build1 freshly compiled both affected crates. CLI executable SHA
`471767227c8e449fe3c4019a8127e72f905c7bd784567093ac01c3d77e2f5214`;
core executable SHA`f8010cbe923e41dfb764abea7558e3c35cc2e2bf77e069f84f3ea3249256eddf`.
See the [actual receipt](../../../outputs/raw-quality-2026-10-27/insect-placement-observe-1/output/receipt.json),
[invocation](../../../outputs/raw-quality-2026-10-27/insect-placement-observe-1/invocation.json),
[process accounting](../../../outputs/raw-quality-2026-10-27/insect-placement-observe-1/process.json),
[descriptive census](../../../outputs/raw-quality-2026-10-27/insect-placement-summary-1/output/summary.json),
and [independent review](independent-results.md).

Checks1 found existing Clippy/formatting failures plus one new fixed-chunk
hash-loop style warning and three new core formatting hunks. Exact compiled
source copies were preserved before those narrow cleanup changes in
`insect-placement-build-1/source-before-cleanup/`. Build2 freshly compiled both
crates after formatting and replacement of a fixed four-byte chunk iterator
by its array-slice equivalent. Both generated-control receipts are byte-exact
to build1, and all591 ordinary core tests pass again. Build2 CLI SHA
`12f01efbf85ef0fc8ab87f65e631f825de310d1cc71a95f50f66b98333f10726`;
core SHA`fe09397faa6b07a83ab858045c5eb7f021a88cc42c58ddc1832388fcea37a026`.
The actual299 observation remains bound to the preserved build1 source and
executable; it was not rerun for formatting/hash-iterator cleanup. Checks2
freshly checked the affected crates and no new observer diagnostic remains.
Full Clippy/format checks are still red on unrelated existing code, including
old align tests, image output and experimental adapters. No green aggregate
claim or unrelated cleanup sweep is made.

`python -B scripts/corpus_lint.py` was also run: exit1,16 existing violations
in historical research Markdown (table pipes and final newlines), with its Git
line-ending checks skipped because its `git ls-files --eol` call was unavailable.
No SYNTHESIS fold or historical-document repair was performed.

No merge or photograph was changed or rendered here. The previous complete
[weevil photograph](../../../outputs/raw-quality-2026-10-26/weevil-107-ca-off/stack-full.jpg)
and [full-resolution master](../../../outputs/raw-quality-2026-10-26/weevil-107-ca-off/stack-master.tiff)
remain the photographic baseline, with unresolved softness, glints and occlusion
contours. Existing complete Helicon comparisons remain applicable. This
instrument does not upgrade that result or the overall SOTA scorecard.
