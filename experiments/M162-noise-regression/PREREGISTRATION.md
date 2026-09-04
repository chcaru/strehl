# M162 noise attribution preregistration

Status: **frozen before any M162 render or real-image score**.

M159 established that DELIVER-V6 carries `1.515208x` the fork's median
fractional box9 residual on twelve frozen coffee-bean flat sites. This
experiment asks whether an avoidable Strehl change caused a material part of
that gap, or whether the gap accompanies a deliberate preservation of image
structure.

The box9 statistic rewards blur. It is therefore never sufficient by itself.
M162 introduces one explicitly limited **detail-collapse proxy** and will not
call a quieter arm a win unless that proxy holds.

## 1. Fixed records and scope

### Comparator

The comparator is the archived `focus-stack` output, not a reproducible
executable:

| item | fixed value |
|---|---|
| TIFF | `C:\dev\macro\out\coffee-bean\stack.tif` |
| TIFF SHA-256 | `8636C20D73CA0CB1F57DB89BF8553ABC166E0FBC517E5C62A07C74DEE509066E` |
| source repository | `C:\dev\macro\focus-stack` |
| repository root commit | `4bc7f95e448cf20ee2bdd758403ec43e2612a1c6` |

The archived render predates the first retained commit and is not bound to an
executable or source revision. It is still a valid byte-pinned output
comparator. It is not a build that can be checked out and rerun.

### DELIVER-V6

| item | fixed value |
|---|---|
| TIFF | `C:\dev\strehl-out\DELIVER-V6\masters\coffee-bean.tiff` |
| TIFF SHA-256 | `F38CA50ED1A680FA4DBCDD8D0513BE538DD31634B4E89AC6A34885944790A2EC` |
| executable | `C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe` |
| executable SHA-256 | `2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7` |
| source | `6af834dac08d6605aee7ea3ad75809fdf6313770` |
| source capture | `D:\personal\macro\coffee-bean` |

`D:\personal\macro` is read-only. Every generated map, log, manifest, TIFF,
and result goes under `C:\dev\strehl-out\M162-noise-regression` or this
experiment directory.

### Attribution scope

The fork and Strehl have unrelated histories and different inputs:
Lightroom-developed linear Rec.2020 TIFFs versus RAW CFA files. There is no
valid fork-to-Strehl Git bisect. The fork TIFF stays fixed while M162
decomposes output-changing choices inside Strehl.

## 2. Primary factorial

All current-binary arms use one newly solved, byte-pinned private warpmap.
The exact DELIVER-V6 invocation omits `--pyramid-gate`; source inspection fixes
that compiled default at `2.0`. The gate-4.5 arms add only that flag. The plane
arms add only `STREHL_FULLRES_GATHER=0`.

| arm | gate | gather | other change |
|---|---:|---|---|
| `v6-g2-full` | compiled `2.0` | compiled full-resolution default | exact DELIVER-V6 flags |
| `v6-g4p5-full` | `4.5` | full resolution | none |
| `v6-g2-plane` | compiled `2.0` | CFA phase plane | none |
| `v6-g4p5-plane` | `4.5` | CFA phase plane | none |

Two current-binary controls isolate later changes:

| arm | change from `v6-g2-full` |
|---|---|
| `v6-g2-full-white-floor` | `STREHL_GATE_FLOOR=white` |
| `v6-g2-full-ca-off` | `STREHL_FIX_CA=0` |

Every inherited `STREHL_*` variable is removed before the recorded environment
is applied. The render harness records the executable, executable hash,
arguments, complete set environment, warpmap hash, output hash, source-file
hashes, exit code, and full banner.

The current baseline must reproduce the frozen DELIVER-V6 image pixels. A
container hash mismatch is disclosed because TIFF metadata can differ. A
pixel mismatch invalidates automatic classification until explained.

## 3. Conditional historical reconstruction

Only if the current-binary factorial leaves a material remainder does M162 run:

| arm | fixed value |
|---|---|
| name | `b9b-ship-v2-reconstruction` |
| executable | `C:\dev\strehl-out\acceptance-pins\b9b6921e\target\release\strehl.exe` |
| SHA-256 | `CF33AE080F438C6473034EC5078D0AB4C0AA9B53421747A3F765008DDDF0D6E6` |
| invocation | `stack <raw> -o <out> --merge pyramid --pyramid-gate 4.5 --srgb --auto-exposure` |

This is the nearest retained SHIP-V2 reconstruction. It is not the producer of
the archived fork TIFF, and it is not silently promoted to that status. It
gets its own warpmap solved by its own binary. Its sites are the same frozen
fork coordinates mapped through a newly measured similarity transform.

## 4. Inherited residual instrument

M162 dynamically imports
`experiments\M159-noise-clause\measure.py`; it does not retype the tone inverse
or statistic.

For each of M159's twelve frozen reference sites:

1. use M159's exact mapped Strehl box for every current-binary arm;
2. invert Strehl's recorded tone placement;
3. compute `sd(green / box9(green) - 1)`;
4. divide by M159's fixed fork denominator.

Sign conventions:

- `arm / fork > 1`: arm has more fractional box9 residual than the fork;
- `baseline / candidate > 1`: candidate is quieter than DELIVER-V6;
- `full / plane > 1`: full-resolution gather is noisier.

Paired site medians receive a deterministic 20,000-resample bootstrap interval.
Factorial effects are also reported in paired log space, including the
gate-by-gather interaction.

M159 already commissioned this inherited statistic with a movable null, added
noise as degradation, four-frame averaging as improvement, and a blur
challenge. M162 carries forward its limitation: it measures residual, not
physical noise, and rewards blur.

## 5. Detail-collapse proxy

This is a proxy, not a truth-referenced detail measurement.

For linear green `x` in one site:

1. `r = box5(x) - box13(x)`;
2. `floor = 1.4826 * median(abs(r - median(r)))`;
3. `tail = percentile(abs(r - median(r)), 99.5)`;
4. estimate the pure-noise tail multiplier `K` once from a deterministic
   `1024 x 1024` standard-normal field passed through the same filters;
5. report `sqrt(max(tail^2 - (K * floor)^2, 0))`.

This is an unnormalised, noise-corrected upper-tail amplitude in approximately
the `0.077-0.20 cycles/pixel` band. It is intended only to catch collapse of
resolved local structure.

It is blind to, and must never be described as measuring:

- phase fidelity or registration correctness;
- dense low-contrast texture whose energy does not reach the upper tail;
- structure outside its one spatial-frequency band;
- hallucinated detail or ringing, which it can reward;
- colour detail outside green;
- global image quality.

### Site selection

Before reading any new arm:

1. enumerate the same `384 x 384`, 192-pixel-stride fork grid as M159;
2. reject boxes outside a 200-pixel margin;
3. reject a box if any fork RGB sample is at or above `0.98`;
4. require fork green mean strictly inside `(0.08, 0.75)`;
5. reject overlap with any of M159's twelve flat sites;
6. rank by the fork-only proxy;
7. greedily freeze the highest twelve non-overlapping boxes.

No candidate output participates in selection. Candidate clipping is retained
as a failed guard, not used for post-hoc site removal.

### Commissioning

No real image is read unless all of these deterministic controls pass:

1. **Movable null:** two independent equal-noise captures of one latent
   structured field must put ratios on both sides of one, span at least `0.01`,
   and have median within `0.01` of one.
2. **Planted degradation:** Gaussian blur with sigma `0.8` must reduce the
   proxy on every one of 128 trials and by at least 10% at the median.
3. **Planted improvement:** restoring the unblurred latent field from that
   planted blur must increase the proxy on every trial and by at least 10% at
   the median.
4. **Added-noise challenge:** tripling capture-noise sigma must not increase
   the proxy at the median by more than 5%.
5. **Blur trap:** the same blur must improve the inherited box9 residual while
   worsening the proxy. This demonstrates why the two instruments are coupled.

## 6. Guards and decision rules

A candidate is a material residual improvement only if:

- median paired `baseline / candidate >= 1.10`; and
- the bootstrap 95% lower bound is above `1.0`.

The proxy **holds** only if:

- median paired `candidate / baseline >= 0.98`; and
- the bootstrap 95% lower bound is at least `0.95`; and
- no added clipping exceeds the baseline at any frozen detail site.

The analysis also reports linear-green mean and percentile-span ratios. A
median mean ratio outside `[0.99, 1.01]` blocks an automatic verdict because a
gain change can move a fractional residual without changing the merge's noise.

Classification:

- **REGRESSION:** at least one current-binary reversion materially lowers
  residual, the proxy holds or improves, and all guards pass. Gate `4.5` at
  full-resolution gather is the primary test.
- **TRADE:** no admissible quieter reversion exists, while full-resolution
  gather is materially noisier and materially raises the proxy at a fixed
  gate, with both 95% intervals above one.
- **UNRESOLVED:** baseline reproduction fails, commissioning fails, the proxy
  cannot discriminate, a guard fails, or neither rule is met.

If both an avoidable gate component and a detail-preserving gather component
exist, the report will say so. The overall remedy-bearing verdict is
**REGRESSION**, while separately naming the gather contribution as a trade.

No residual reduction accompanied by proxy loss will be reported as a win.

## 7. Execution order

1. `python analyze.py --commission-only`
2. after the host lock is released:
   `powershell -File render.ps1 -Stage current`
3. `python analyze.py`
4. only for a material unexplained remainder:
   `powershell -File render.ps1 -Stage historical`
5. `python analyze.py --include-historical`
