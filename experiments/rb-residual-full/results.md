# Guarded R/B residual: complete photographic rejection

Root execution, independently reviewed. The complete70-source vitamin-C
observation finishes but fails photographic review. Do not promote the
operator, tune its threshold, optimize this exact recipe, or spend a second
stack render on it. Generated colour-focus improvements remain measured;
their transfer to this real photograph is rejected.

## Executed evidence

```text
python -I -B -X faulthandler experiments/rb-residual-full/build-run.py build --build experiments/rb-residual-full/build-1
python -I -B -X faulthandler experiments/rb-residual-full/build-run.py controls --build experiments/rb-residual-full/build-1
python -I -B -X faulthandler experiments/rb-residual-full/full-run.py cost --build experiments/rb-residual-full/build-1 --screen experiments/rb-residual-guard/controls-1 --out experiments/rb-residual-full/cost-1
python -I -B experiments/rb-residual-full/cost-decision.py --cost experiments/rb-residual-full/cost-1
python -I -B -X faulthandler experiments/rb-residual-full/full-run.py full --build experiments/rb-residual-full/build-1 --screen experiments/rb-residual-guard/controls-1 --cost experiments/rb-residual-full/cost-1 --out experiments/rb-residual-full/full-1
python -I -B -X faulthandler experiments/rb-residual-full/photo-compare.py --run-dir experiments/rb-residual-full/full-1
```

MEASURED: fresh build177.437s. Independent writer test0.297s: the fixture
changes1423 reconstructed camera-green pixels while CFA greens stay fixed;
omitting the copy changes4227 delivered samples. The intended R/B update
changes8541/8556 samples. Independent old camera-RGB reconstruction, legacy
writer identity and ICC are exact. These are mechanical controls, not quality.

MEASURED: source35 full-domain checkpoint10.000s wall,7.5262s source phase,
1.8897s finish,5,066,752,000 peak job bytes. All16 probe members, actual CA,
N70 threshold and reached seven bands are retained. Source-known4, canonical
and candidate are exactly equal in this one-source hull placebo. The frozen
feasibility estimate648.724s passes; it is not a benchmark or a speed claim.

MEASURED: complete pair464.125s wall,6,059,954,176 peak job bytes,70 sources,
6920x4612 RGB16. Original metadata, map and123 bound sources remain unchanged.
Canonical RGB16 pixels match the historical complete baseline exactly. TIFF
file bytes differ because Software metadata records the current build. R/B
candidate source grouping is18/18/18/16, both CFA greens remain exact, and the
writer preserves canonical camera G before the unchanged matrix/tone. Final
sRGB green is allowed to change under that matrix.

Baseline TIFF SHA256:
47ac86c8ddc8103fbac358f56c9a5371628ef3fb8f0122e54be69422c439bb3b.
Candidate TIFF SHA256:
db9aaa2683fa2dfb4e98880e053bbaf982a84575f98aafbd3e1b6020db76ecf8.
Receipt SHA256:
959542800c7937b94f67b21b56daeffe4e5668382bdb38ba5ea2458a69672aef.

## Photographic decision

OBSERVED independently from complete overviews and the eight frozen native
views, with the held Helicon B comparator. The full candidate makes central
magenta highlights more conspicuous without a convincing structural gain.
Facet core acquires stronger pink/green fringes; the dark inclusion acquires
a saturated magenta loop and stronger cyan/pink tails. The extended branches
remain. The pale background is essentially unchanged. No compensating fine
crystal or nearby competing-depth detail recovery earns acceptance. Helicon
remains a comparator, not ground truth; no photographic quality percentage
is inferred from these observations.

The two complete images are retained in full-1/photo-comparison-1 as
baseline-overview.jpg and candidate-overview.jpg, with complete-resolution
PNGs. RGB16 masters are full-1/output/baseline.tiff and candidate.tiff. Show
these complete before/after views to the owner; native crops are supplemental.
The user must not be shown only a favorable section.

Frozen generated admission stays false and the new photographic decision is
also NO-GO. Keep the reusable writer and actual noise propagation controls;
do not describe them as a delivered image improvement. The next intervention
must first distinguish physically useful source content from the real fan
sources; independent channel selection has now made this defect worse.
