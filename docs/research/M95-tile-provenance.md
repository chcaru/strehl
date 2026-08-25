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

**BAR:** an array is NARROWED if a 4M-pixel sample of one channel holds fewer
than **4096 distinct values**. Native 16-bit RAW clears it widely; anything
through an 8-bit stage cannot.

| array | dtype | distinct levels | verdict |
| --- | --- | --- | --- |
| `M95-demosaic/scratch/truth_AHD.npy` | float32 | **175,477** | native |
| `truth_VNG.npy` | float32 | **174,060** | native |
| `truth_LINEAR.npy` | float32 | **171,771** | native |
| `M95-resample/rawpy-A.npy` | uint16 | **7,511** | native |
| `M95-ref/merge-g0-linear.tif` | uint16 | **21,649** | native |
| `M95-ref/merge-g0-noalign.tif` | uint16 | **21,776** | native |

**Arrays probed 6, NARROWED 0.**

`m95cov.load_luma` reads through **`tifffile.imread`**, not PIL
(`m95cov.py:24-25`), so the coverage tree was already structurally immune to the
16-bit-RGB narrowing hazard rather than accidentally so.

## 4. Load-bearing exposure: none

- **My published milestone does not use `pick_tiles` at all.** The election-
  quality work (`experiments/M95-oracle/`, `experiments/M95-merge-vs-frame/`)
  contains zero call sites; it selects ROIs by an explicit contrast criterion and
  scores every pixel in them.
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
