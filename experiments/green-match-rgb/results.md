# Source-colour projection: generated screen and complete-photo decision

**VERIFIED generated screen:** both fixed ISO cases admit one photographic
replay. This is not a photographic improvement claim or a production change.
The test-only rule accepts a source when its green value is within the fixed
injected-variance threshold of the current merge's collapsed green, then
averages accepted complete colour tuples. Unsupported quads retain the exact
baseline RGB. The threshold is a heuristic with a correlated target, not a
calibrated residual probability or RGB covariance estimate.

Commands executed with Python 3.12 from the repository root:

```
python -I -B experiments/green-match-rgb/run.py build --out experiments/green-match-rgb/build-1
python -I -B experiments/green-match-rgb/run.py controls --build experiments/green-match-rgb/build-1 --out experiments/green-match-rgb/controls-1
```

The build freshly compiled `strehl-cli` and completed in 132.172 seconds job
wall time. The two independent controls passed in 1.765 seconds. Full source
and executable bindings, commands and bounded process accounting are beside
each run. The controls author inspected the outcome separately from the
implementation author; `results-review.md` records that assessment.

**MEASURED, candidate/baseline RGB truth-RMSE ratio:**

| Fixed generated scene | ISO100 | ISO400 |
| --- | ---: | ---: |
| Flat | 0.93517 | 0.93415 |
| Neutral detail | 0.57920 | 0.59278 |
| Genuine coloured detail | 0.86042 | 0.81032 |
| Genuine coloured detail with varying focus | 0.88759 | 0.91034 |

Absolute error can reward smoothing, so it was paired with independently
commissioned true-component recovery. All fixed component guards passed;
the largest genuine-colour loss was 1.56% in the ISO400 varying-focus red
component. The fixed green-zero-crossing subset also improved R/B truth error
(ratios 0.90073 / 0.92584). Flat RGB error improved while flat chroma error
increased slightly (ratios 1.00456 / 1.00252). These are operator tests under
the injected sensor model, not a new camera calibration.

Exact tuple, threshold-boundary and no-source fallback controls passed.
Reversing colour-replay source order produced identical outputs in these
fixtures. All actual source gathers matched the baseline's four known sites,
and the source arrays remained unchanged. Varying-focus scenes admitted
exactly one source at 75.47% / 66.85% of full-crop quads, and fell back at
5.18% / 0.50%; the method is projection with selective averaging, not broad
multi-frame denoising of detailed regions.

The controls deliberately expose two limitations: identical green with
different chroma is averaged into an intermediate colour, and a source with
matching green and clipped red remains admitted. This rule is not clipping
aware or generally colour safe. The photographic test must check actual
colour artifacts, texture loss and background regressions rather than rely
on these generated error ratios.

Complete-photo protocol is frozen in `full-plan.md`. Adapter implementation,
fresh post-adapter controls and independent review precede that one run.

## Complete photograph outcome

**Decision: retain as experimental; target artifact unresolved.** The complete
70-frame image has less visible fine grain in the two low-detail background
windows. Long coloured fans remain in both targeted highlight windows, and
some fine crystal texture looks smoother. Neither reviewer identifies a newly
resolved feature. This is a background-smoothing tradeoff, not the intended
source-selection repair or a SOTA result. No default promotion, parameter
sweep, speed optimization or transfer claim is justified by it.

Root inspected both whole-field overviews for orientation and all five frozen
384x384 pairs at native sampling. In the facet and dark-inclusion views, the
candidate retains the broad fans and some highlights appear more granular or
block-like. Pale background and the mostly low-detail bright-facet window have
less visible fine grain. Fine-crystal large edges remain recognizable, but
smaller texture is smoother and gives no convincing resolution gain. The
independent review reached the same main conclusion without reading root's
verdict first; see `full-2/photo-comparison-1/photographic-review.md`.

Commands run:

```
python -I -B experiments/green-match-rgb/full-run.py build --out experiments/green-match-rgb/full-build-1
python -I -B experiments/green-match-rgb/full-run.py controls --build experiments/green-match-rgb/full-build-1 --out experiments/green-match-rgb/full-controls-1
python -I -B -X faulthandler experiments/green-match-rgb/full-run.py full --build experiments/green-match-rgb/full-build-1 --screen experiments/green-match-rgb/full-controls-1 --out experiments/green-match-rgb/full-1
python -I -B experiments/green-match-rgb/full-run.py build --out experiments/green-match-rgb/full-build-2
python -I -B experiments/green-match-rgb/full-run.py controls --build experiments/green-match-rgb/full-build-2 --out experiments/green-match-rgb/full-controls-2
python -I -B -X faulthandler experiments/green-match-rgb/full-run.py full --build experiments/green-match-rgb/full-build-2 --screen experiments/green-match-rgb/full-controls-2 --out experiments/green-match-rgb/full-2
python -I -B experiments/green-match-rgb/photo-compare.py --run-dir experiments/green-match-rgb/full-2 --out experiments/green-match-rgb/full-2/photo-comparison-1
```

The first full run stopped before colour replay after 30.859 seconds because
the TIFF Software tag recorded the newer build revision. Independent decoding
found **all 95,745,120 RGB16 samples identical**, with no other tag difference.
The failure and original guard are preserved in `full-1` and
`full-first-freeze`. The corrected guard checks decoded RGB16 dimensions/type,
sample/page count and the independently fixed little-endian pixel hash from
the original reference. It retains the truthful Software tag and both file
hashes. The outer runner also compares actual decoded arrays exactly. No
rendering arithmetic or acceptance criterion was changed.

Both full-adapter builds freshly compiled the CLI (130.703 / 134.234 seconds).
Both subsequent two-test screens passed (1.704 / 1.812 seconds) and their
complete screen JSON is byte-identical to the initial generated result.
Independent source review covers the full adapter and the guard correction.

**MEASURED complete paired prototype:** 94.969 seconds wall time, 398.53125
CPU seconds, peak job committed memory 3,567,026,176 bytes. This includes two
RAW passes, baseline plus candidate writing and diagnostic hashes; it is not
a benchmark against another product or a candidate-only speed claim.
All70 active-u16 second decodes and actual guide/variance fields match the
first pass by hash; original file sizes/times and held map remain unchanged.
There are no unsupported colour pulls. Source images were not written.

Whole-image source participation is descriptive only: average16.8604 accepted
sources per quad; 0.9452% fall back and 1.8714% accept exactly one source.
These counts cannot prove quality and are not used as an acceptance score.

Complete6920x4612 outputs, shown to the user with the tradeoff stated:

- `full-2/photo-comparison-1/baseline.png` and `candidate.png`, entire extent,
  rounded RGB16-to-RGB8 conversion with ICC retained and no resampling.
- `full-2/output/baseline.tiff`, file SHA256
  `bc6a921000bf942e678a31d6d4374bf2d347f61e61162d1d0dc98f80212cfd9e`.
- `full-2/output/candidate.tiff`, file SHA256
  `c27d8b10fc0b702792d46b7bacbbcc57939c3255ee85b5db411d0fbcf75d8b8d`.

Baseline decoded-pixel SHA256 is
`2a19cd9b7236a13bf90e81b87e85b1058e071aa19f4a5af82b97f453687d0dda`,
identical to the historical reference. Full-resolution image files remain
local; compact native review images and receipts are retained with the source.
