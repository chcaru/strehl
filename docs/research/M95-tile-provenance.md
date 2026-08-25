# M95 -- tile-selection provenance audit (ORCH fact 1764 / discipline 911)

**Question asked:** in the trees M95 owns, which scripts **re-select tiles per
arm** and which **select once and reuse**? For any that re-select, what was the
input provenance?

**Answer: none of the 33 call sites has the exposed pattern, and no input to any
of them is narrowed.** Both numbers were measured, not inferred.

Scripts: `experiments/M95-oracle/src/o11_tileaudit.py` (structure),
`o12_precision.py` and `o12b_tiffs.py` (provenance). Logs and JSON under
`experiments/M95-oracle/out/`.

---

## 1. The helper, quoted rather than described

`experiments/M95-coverage/src/m95cov.py`:

```python
s = float(np.diff(t, axis=0).var() + np.diff(t, axis=1).var())
```

ORCH's characterisation is exact: the ranking statistic is a differencing
dispersion, the class fact 1712 says under-reports noise 16x on narrowed input.

## 2. Structure -- answered by parsing, not by reading

35 files in the six trees M95 owns textually contain `pick_tiles`. The audit
classifies each call site by lexical loop depth **and** by the loop depth of the
calls reaching its enclosing function, because a call at depth 0 inside a helper
invoked per arm is a re-selection that depth alone would miss.

| class | count | meaning |
| --- | --- | --- |
| **ONCE** | **31** | one selection, loop depth 0, helper not reached from a loop |
| **RESELECT** | 1 | `M95-demosaic/d2_ladder.py` -- read by hand below |
| **REVIEW** | 1 | `M95-demosaic/d3_scale.py` -- read by hand below |
| TEXT-ONLY | 2 | `m95cov.py`, `m95dem.py` -- the definitions themselves |

Per tree: `M95-resample` 13 ONCE, `M95-coverage` 8 ONCE + 1 definition,
`M95-kernel` 4 ONCE, `M95-cdiff` 3 ONCE, `M95-dose` 2 ONCE, `M95-demosaic`
1 ONCE + 1 definition + the two below.

### 2.1 `d2_ladder.py` -- flagged, and clean for the reason that matters

`run_truth(alg)` is called three times, which is why the audit flagged it. But
inside each call the selection is made **once** and every demosaic arm is scored
against **that same pinned tile set**:

```python
def run_truth(alg, log):
    T = np.load(SCRATCH / f"truth_{alg}.npy")
    tiles = m95dem.pick_tiles(T, N, COUNT, LO, HI)
    M = m95dem.mosaic_rggb(T)
    arms = {}
    for name, fn in m95dem.DEMOSAICS.items():
        arms[name] = score(fn(M), T, tiles)
```

The tile set varies across **truth decoders**, not across **arms**. The published
ladder compares arms, and those comparisons are pinned. **The exposed pattern
does not occur.**

**One honest qualification.** Control **K5** (lines 190-215) compares `MHC`'s
signal across the three truths, and those three do use different tile sets, so
`mhc_max_dev` conflates a truth-decoder change with a tile-set change. K5 is a
specificity control, not a headline, and **the confound runs against the control
passing** -- extra tile-set variation can only inflate the deviation and break
the ranking, so `ranking preserved: True` is if anything understated. I am
flagging it rather than defending it.

### 2.2 `d3_scale.py` -- two calls, two different images

```python
tiles = m95dem.pick_tiles(L, N, COUNT, *ALIAS)     # L65, real sensor decode
ttiles = m95dem.pick_tiles(TL, N, COUNT, *ALIAS)   # L73, synthetic truth
```

Each image's published statistic is a **within-image band ratio computed on that
image's own pinned tiles**, and the headline is a ratio of those two ratios.
Different images necessarily get different tiles; there is no arm-vs-arm tile
mismatch. `L` comes straight from `rawpy.imread(ARW).postprocess(output_bps=16)`
-- camera RAW, native precision.

## 3. Provenance -- measured against a bar stated first

**The first bar was blunt and I replaced it.** `o12_precision.py` called an array
narrowed if it held fewer than 4096 distinct levels. `o14` showed that bar is
wrong in **both** directions: it convicts low-contrast native data, and it clears
narrowed data that spans a wide range. The oracle's `ROI-FLAT` is the proof --
genuinely native, and only **1110** distinct levels, because low contrast is the
property it was selected for.

**The correct discriminator is level SPACING, not level count.** Native RAW
arrives as consecutive integers, so the gap between neighbouring distinct values
is 1. Anything rescaled from an 8-bit stage lands on a lattice with a constant
stride greater than 1. Spacing separates narrowing from low contrast; a count
cannot.

**BAR (`o15_reprobe.py`):** integer arrays are NATIVE if the modal gap between
consecutive distinct levels is **1** and at least **90 %** of gaps are 1. Float
arrays have no lattice, but an 8-bit stage caps them at ~256 distinct values
regardless of range, so a count bar is decisive there: NATIVE if **> 4096**.

**POWER CONTROL, mandatory because the headline is an absence:** every array is
also measured after a planted 8-bit round trip. The planted arm must read
NARROWED, or the real-arm reading proves nothing.

| array | test | levels | modal gap | gaps == 1 | verdict |
| --- | --- | --- | --- | --- | --- |
| `truth_AHD.npy` | float-count | **175,477** | -- | -- | native |
| `truth_VNG.npy` | float-count | **174,060** | -- | -- | native |
| `truth_LINEAR.npy` | float-count | **171,771** | -- | -- | native |
| `M95-resample/rawpy-A.npy` | int-spacing | 7,511 | **1** | **98.6 %** | native |
| `M95-resample/merge-g0-linear.tif` | int-spacing | 21,649 | **1** | **95.7 %** | native |
| `M95-resample/merge-g0-noalign.tif` | int-spacing | 21,776 | **1** | **96.2 %** | native |

**REAL ARM: NATIVE 6/6. POWER CONTROL: planted arm NARROWED 6/6** (modal gap
54-158, **0.0 %** unit gaps; floats collapse to 201-223 levels). The instrument
could have said otherwise and did, on demand.

**o12's conclusion is confirmed under the correct test.** It was reached with a
blunt instrument and it survived a sharper one, which is the only reason it is
still in this report.

`m95cov.load_luma` reads through **`tifffile.imread`**, not PIL
(`m95cov.py:24-25`), so the coverage tree was already structurally immune to the
16-bit-RGB narrowing hazard rather than accidentally so.

## 3a. The hazard broadened to AVERAGING -- what that reopens, and what it does not

ORCH corrected the mechanism after this audit began: the vulnerable operation is
not **differencing** but **averaging**, because quantisation error is
value-deterministic and moves a whole sample population together instead of
averaging down (fact 1765; reproduced at 79x on a rank statistic with no
differencing in it). So `pick_tiles` is exposed for a more general reason than
first given, and **any pooled statistic is a candidate**.

**This does not reopen sections 2 or 3, and the reason is structural.** The audit
rests on two legs and both are mechanism-independent:

- **Pinned selection.** If every arm is scored on the same tiles, arms cannot
  differ by tile set -- whatever makes the ranking statistic vulnerable.
- **Native input.** If nothing is narrowed, no quantisation error enters at all,
  so no operation can be exposed to it, averaging or differencing.

The broadening changes **which operations are candidates**, not **whether
narrowed input is present** -- and the input side is the side I measured.

**It does reopen something else, and this is the part that needed new work.**
The election-quality milestone never calls `pick_tiles`, so `o11`/`o12` never
covered it. Under "any pooled statistic", its ROI means, box means and band
powers all become candidates for the first time -- and its headline (excess
deficit **+0.8119 / +2.3615 / +2.3793 pp**) is exactly the *small pooled number*
ORCH flags as most at risk, since a quantisation floor would sit under it.

**Measured, `o14_cubeprecision.py`,** on the cube those statistics pool
(`C:\dev\strehl-out\M95-oracle\ROI-*.g1.npy`, built by `o1_cube.py:74-80`
directly from `decode_raw(p).cfa` green planes -- no demosaic, no TIFF round
trip, no 8-bit stage anywhere in the path):

| ROI | arm | levels | modal gap | gaps == 1 | verdict |
| --- | --- | --- | --- | --- | --- |
| LOWDRIFT | real | 4,394 | **1** | **99.8 %** | native |
| LOWDRIFT | planted 8-bit | 256 | 17 | 0.0 % | NARROWED |
| MIDDRIFT | real | 4,377 | **1** | **99.3 %** | native |
| MIDDRIFT | planted 8-bit | 168 | 28 | 0.0 % | NARROWED |
| HIGHDRIFT | real | 4,439 | **1** | **99.5 %** | native |
| HIGHDRIFT | planted 8-bit | 247 | 18 | 0.0 % | NARROWED |
| FLAT | real | **1,110** | **1** | **97.3 %** | native |
| FLAT | planted 8-bit | 255 | 5 | 0.0 % | NARROWED |

**Real arm NATIVE 4/4; power control NARROWED 4/4.** No quantisation floor enters
any pooled statistic in the oracle tree, and the headline stands unchanged.

`ROI-FLAT`'s row is why section 3 changed instrument. At 1,110 levels the count
bar would have convicted the one ROI whose entire purpose is to be flat.

## 4. Load-bearing exposure: none


- **My published milestone does not use `pick_tiles` at all.** The election-
  quality work (`experiments/M95-oracle/`, `experiments/M95-merge-vs-frame/`)
  contains zero call sites; it selects ROIs by an explicit contrast criterion and
  scores every pixel in them. Not-calling-it is an argument, not a measurement,
  so section 3a measured its inputs anyway: **native 4/4, power control 4/4**.
- The `+0.1160 dex` resampler-kernel number ranked tiles through this helper, and
  it is **already withdrawn** on independent grounds (band is 12.8 % subject
  detail, 87.2 % noise; dark-frame placebo 1.0006). Nothing rests on it.
- Every remaining M95 number that ranked tiles did so **once**, on an input
  measured native above.

## 5. No change proposed to `pick_tiles`

Agreed on the reasoning: changing a shared ranking helper would silently move
every historical tile selection across seven trees. And with zero narrowed
inputs measured, no change is warranted here. **If ORCH wants the guard anyway,
the sanctioned shape as a verbatim patch** -- I have not applied it, because
`m95cov.py` is now shared with `M112-real-pixels` and a shared registration
point is not mine to move:

```python
def pick_tiles(img, n=NTILES, tile=TILE, pad=PAD):
    """The n sharpest non-overlapping tiles, kept clear of the border by `pad`."""
    # Fact 1712: this ranks on a differencing dispersion statistic, which
    # under-reports noise ~16x when the input has already been narrowed,
    # because quantisation error is correlated across frames. Fail loudly
    # rather than rank quietly on data that cannot support it.
    _s = img.reshape(-1)
    _s = _s[:: max(1, _s.size // 4_000_000)]
    _lv = np.unique(_s).size
    assert _lv >= 4096, (
        f"pick_tiles: input holds only {_lv} distinct levels in a "
        f"{_s.size}-sample; a differencing ranking statistic is not valid on "
        f"narrowed input (fact 1712). Pass native-precision data.")
    h, w = img.shape
```

## 6. A defect in this audit, caught and worth handing back

**The first run of `o11_tileaudit.py` printed `RESELECT: NONE` while auditing
zero files.** `ROOT` was resolved one directory short, so the tree paths did not
exist, the loop body never ran, and the summary reported a clean bill of health
from an empty set. It looked exactly like a pass.

The repair is a **coverage assertion**: count the files that textually contain
`pick_tiles` first, and hard-fail if the number audited does not match. The
second run prints `COVERAGE: expected 35 files, audited 35` before any verdict.

> **An audit whose headline is an absence must assert its own coverage, because
> "found no exposure" and "looked at nothing" print the same.** This is the
> discipline-595 power control applied to a static audit rather than to a
> measurement, and I did not have it until it caught me.
