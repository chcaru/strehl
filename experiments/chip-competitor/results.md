# Complete chip workflow references

MEASURED: both Helicon methods complete all299 prepared full-resolution images
and produce7032x4688 RGB16 TIFFs with the expected sRGB ICC. Original metadata
and every prepared TIFF hash remain unchanged. No license, application setting,
image scale or input subset was changed. Development retains the product RAW
decoder/MHC/WB/matrix and fixed chip tone; its independent golden is exact.

Root and the separate photographic reviewer inspect complete-field overviews
through the common RGB16 conversion. **B has substantially cleaner broad
compartment boundaries and upper-left contact shapes than Current or C.** C
retains stronger multicolour spill and displaced-looking bands. These are
bounded whole-field photographic observations, not native-detail truth or a
noise score. No obvious trial lettering/logo is visible in the overviews;
exhaustive native-pixel absence has not been established.

B and C receive identical prepared inputs. Therefore their visible difference
cannot be attributed solely to development before fusion. It motivates a
source-choice/merge intervention. It does not identify a particular coefficient
rule: method-specific internal operations remain unknown. Current versus
either external workflow additionally differs in ordinary optical CA,
development order, alignment and output gauge. No pure merge superiority,
resolved-detail count or SOTA claim follows.

The coordinate tool passes its independent integer-translation commission
(all seven native cuts byte-identical), flat refusal and wrong-coordinate
destroyer. It then **refuses both actual global mappings**: B has42 training
inliers and15.58native-pixel held median, C25 and25.04. All seven external
local panels remain unavailable. Do not reuse the failed similarity as a
validated alignment, lower the thresholds or claim matched-native superiority.
Whole-field comparisons remain available. See `photographic-review.md` and
`comparison-1/coordinate-receipt.json` for the exact scope and evidence.

## Commands and retained artifacts

The following commands were executed from the repository using Python3.12:

```text
python -I -B -X faulthandler experiments/chip-competitor/run.py build --out experiments/chip-competitor/run-1
python -I -B -X faulthandler experiments/chip-competitor/run.py develop --out experiments/chip-competitor/run-1
python -I -B -X faulthandler experiments/chip-competitor/run.py b --out experiments/chip-competitor/run-1
python -I -B -X faulthandler experiments/chip-competitor/run.py c --out experiments/chip-competitor/run-1
python -I -B -X faulthandler experiments/chip-competitor/compare.py commission --out experiments/chip-competitor/comparison-commission-1
python -I -B -X faulthandler experiments/chip-competitor/compare.py compare --run experiments/chip-competitor/run-1 --commission experiments/chip-competitor/comparison-commission-1 --out experiments/chip-competitor/comparison-1
```

The two display commands run through the existing bounded Job wrapper; their
full invocations and process logs are in `comparison-commission-job-1` and
`comparison-job-1`. Source review precedes execution. Fresh compilation is
recorded in `run-1/build/process.log`. Both vendor jobs run sequentially after
the large native render exits.

| Stage | Single operational wall seconds | Peak Job commit bytes |
|---|---:|---:|
| Exporter build |29.344|456232960|
| All299 TIFF development |177.281|421216256|
| Helicon B, radius8/smoothing4 |45.625|35461603328|
| Helicon C, smoothing4 |38.250|34756362240|

These are not controlled speed benchmarks. Build/development overlap the
native phase-packed pair; vendor times exclude development and wrapper input
hashing. Job commit does not count the host's full footprint or GPU memory.

| Output | TIFF SHA256 | RGB16 little-endian SHA256 |
|---|---|---|
| B | d8b82dc7007cb11f7a17adcc2239124e6cb0f34b4a93d87aa64c675667a27349 | d7ad7a032d334918385d3705b9ecb1f5e7e83a393a20dfe67ce1310a32c7788f |
| C | 800ad948c4fa4a6eb839a096af009341f08dce9e89bc5d65a9e4ce617a708a48 | fd4a936f22993fb7a552d74d5f47ca61465938575297c14475c09b55406484d4 |

`comparison-1/images.md` leads with all three complete master/native/overview
links. Common displays use rounded `(u16+128)//257` with identical ICC; only
explicit overviews resize. Native Current6468x4300 has reference149 and crop
origin[282,194]; external7032x4688 outputs have their independent gauge.
Equal overview width is not equal physical magnification.

Decision: retain the cleaner B output as a concrete whole-chip target for the
next RAW-native source-coherence intervention. Preserve both C's failure and
automatic mapping refusal. The native pipeline has not reached SOTA on this
capture; this comparator is evidence of a gap, not an improvement to Strehl.
