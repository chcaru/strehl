# M6 — what the alignment residual is, and how big the halo is

Two measurements, answering SYNTHESIS §10 open questions 6 and 10.

* **Q6.** M3 measured a 0.6–1.3 px alignment residual that is neither estimator
  noise (0.19 px) nor global-model error (12 parameters beat 4 by ≤6%). Is it
  **(a)** depth-dependent magnification, or **(b)** blur-induced correlation
  bias? §3.4.2 says the answer gates whether a lens plugin is real computation
  or a data file.
* **Q10.** §3.4.1 item B1 estimates the required halo at "~39 plane px at the
  frame corner" and argues a scalar `halo() -> usize` cannot express it. Replace
  the estimate with a measurement and rule on the interface.

The report is `docs/research/M6-residual-halo-measured.md`. Read that first;
this file is only how to re-run it.

---

## Layout

| Path | What it is |
| --- | --- |
| `m6_lib.py` | The estimator. Loaders, two-way fixed effects, S1/S2/S4/S5/S6/S7, halo arithmetic. No I/O beyond CSV reads. |
| `m6_selftest.py` | 12 groups of self-tests. Every statistic is planted and recovered, and every statistic has a case where it must stay silent. |
| `m6_peakiness.py` | Depth-label quality: does a case even have a focus peak to find? |
| `m6_controls.py` | Planted-cause controls on synthetic stacks built from real frames. |
| `m6_measure.py` | The primary measurement on the three real stacks. |
| `data/` | Generated CSVs. Not committed. |
| `out/` | Saved run output and the winner-index maps. Not committed. |
| `bin/` | A copy of `strehl.exe` pinned to a known commit. Not committed. |

The Rust half lives in `../m3-drift`, which is a standalone crate (its own
`Cargo.toml` and `Cargo.lock`, deliberately not a workspace member).

---

## Running it

Every shell needs cargo on PATH first:

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
```

### 0. Pin the CLI

`crates/` is under concurrent edit, so the CLI is built once and the binary is
copied out. Everything afterwards runs the copy, and the commit it came from is
recorded next to it.

```powershell
cd C:\dev\blog\death-of-software\projects\strehl
git rev-parse HEAD | Out-File -Encoding ascii experiments\m6-residual-halo\bin\BUILT-FROM-COMMIT.txt
cargo build --release -p strehl-cli
Copy-Item target\release\strehl.exe experiments\m6-residual-halo\bin\strehl-m6.exe -Force
Get-FileHash experiments\m6-residual-halo\bin\strehl-m6.exe -Algorithm SHA256
```

### 1. Winner-index maps

The proxy depth map. These come from the *unaligned* stack, so they are
radially smeared by the drift; they are used as a cross-check on the registered
focus profiles, never as the primary label. See the report, "Two depth labels".

```powershell
cd C:\dev\blog\death-of-software\projects\strehl\experiments\m6-residual-halo
.\bin\strehl-m6.exe stack C:\dev\macro\test\109MSDCF    --out out\109MSDCF-stack.tiff    --index-map out\109MSDCF-index.tiff
.\bin\strehl-m6.exe stack C:\dev\macro\test\119MSDCF    --out out\119MSDCF-stack.tiff    --index-map out\119MSDCF-index.tiff
.\bin\strehl-m6.exe stack C:\dev\macro\test\coffee-bean --out out\coffee-bean-stack.tiff --index-map out\coffee-bean-index.tiff
```

### 2. Build the measurement harness and check it did not regress

`--synthetic` is M3's own known-warp control. It must still reproduce M3 §0:
worst scale error 2.23e-5, residuals 0.194 / 0.196 / 0.190 / 0.165 px.

```powershell
cd ..\m3-drift
cargo build --release
.\target\release\m3-drift.exe --synthetic C:\dev\macro\test\109MSDCF
```

### 3. Per-tile residuals for the three real stacks

Roughly 10 min for 109MSDCF, 20 min for 119MSDCF, 2 h for coffee-bean.

```powershell
.\target\release\m3-drift.exe --m6 C:\dev\macro\test\109MSDCF    ..\m6-residual-halo\data\109MSDCF    --iso 160 --deltas 1,2,4,8
.\target\release\m3-drift.exe --m6 C:\dev\macro\test\119MSDCF    ..\m6-residual-halo\data\119MSDCF    --iso 50  --deltas 1,2,4,8,16
.\target\release\m3-drift.exe --m6 C:\dev\macro\test\coffee-bean ..\m6-residual-halo\data\coffee-bean --iso 50  --deltas 1,2,4,8,16,32
```

### 4. Planted-cause controls

Six synthetic stacks built by warping **one real frame**, so the texture and the
sensor noise are real and only the cause is planted.

```powershell
.\target\release\m3-drift.exe --m6-control C:\dev\macro\test\109MSDCF ..\m6-residual-halo\data\control --iso 160 --n 14 --deltas 1,2,4
```

### 5. Analysis

```powershell
cd ..\m6-residual-halo
python m6_selftest.py
python m6_peakiness.py
python m6_controls.py | Out-File -Encoding utf8 out\controls.txt
python m6_measure.py  | Out-File -Encoding utf8 out\measure.txt
```

`m6_selftest.py` and `m6_controls.py` both exit non-zero on failure. Nothing in
the report should be quoted if either does.

`m6_measure.py --cause` and `m6_measure.py --halo` run one deliverable each.
`--halo` needs only the `-fits.csv` files and takes a few seconds.

---

## The design, in one page

**The degeneracy that had to be broken.** Within a single frame pair `(0, k)` a
tile's depth `w` and its defocus `|k/2 − w|` are a deterministic linear function
of each other: `|w − k| − |w − 0| = k − 2w`. No regression can separate them.
The fix is to slide the reference at a fixed baseline — align `(j, j+Δ)` for
every `j` — so the same tile is seen at many defocus levels while its depth
stays fixed, and the same defocus level is seen at many depths.

**Tiles are registered, not chained.** The canonical tile grid is defined in
frame-0 coordinates and warped into frame `j` to place the anchor. Only the
*anchor position* uses a fitted model; every displacement is measured directly
between the two frames of the pair. AGENTS.md rule 6 (never chain alignments) is
not violated, because no measurement is composed from another measurement.

**Two grids, deliberately.** `grid=m3` is exactly M3's published grid (10 px
margin) and exists so the halo arithmetic and the regression check run on the
same fits M3 published. `grid=m6` is inset by 56 px so a warped tile stays
inside the plane. They give different numbers at k=1 — g = −6.04e-4 vs −7.36e-4,
rms 0.703 vs 0.519 px — and both are in the CSVs.

**The torus null.** A plain permutation of the depth field destroys spatial
autocorrelation as well as causal coupling, so it is too easy to beat. Every
null here cyclically shifts the depth field over the 12×8 tile grid instead,
which preserves both the marginal distribution and the spatial autocorrelation
and destroys only the coupling. That is the placebo §5 item 6 asks for.

**Identification is checked, not assumed.** `ident` is the fraction of the
regressor's variance that survives two-way demeaning. If every tile has the same
winner index, `|c − w|` is a pure function of the pair and the pair dummies
absorb it entirely; the coefficient is then a ratio of two small numbers. Any
result with `ident < 0.02` is reported as *unidentified* and not quoted.

---

## Things this code deliberately does not do

* **It does not use a synthetic-only null.** SYNTHESIS §5 item 9 exists because
  M5's estimator false-alarmed on 0.4% of white-noise tiles and 34.2% of real
  dark frames. Every null here runs on real sensor data with real texture. The
  synthetic cases exist to plant *causes*, not to establish floors.
* **It does not compare a spatial spread to a temporal spread.** S7 decomposes
  the per-tile residual into a repeatable part and a scatter part, and both are
  averages over the *same* set of pairs. The project has committed that
  confusion twice; this measurement contains no such comparison.
* **It does not build its synthetic frames by resampling, where that matters.**
  `N0-integer` shifts by whole pixels. Bilinear resampling attenuates high
  spatial frequencies by a sub-pixel-phase-dependent amount, which plants a
  sharpness modulation nobody asked for; that is what broke the original
  `N1-null`. See the report, "The null that was not a null".
* **It does not treat the CLI's `--index-map` as truth.** That map is computed
  on an unaligned stack, so it is smeared by the very drift being measured. It
  is a cross-check.
* **It does not model the residual's dependence on defocus as anything but
  linear.** `|c − w|` measures the pair's mean defocus, not the *asymmetry*
  between the two frames, and asymmetry saturates once `|c − w| > Δ/2`. On the
  105-frame stack that misspecification is visible and is reported rather than
  fixed, because fixing it would mean choosing a functional form after seeing
  the data.
* **It does not write anything outside this directory and `../m3-drift`.** The
  test stacks are read-only.
