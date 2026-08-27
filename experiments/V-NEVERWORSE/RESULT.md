# V-NEVERWORSE — is the merge ever worse than the frames it was built from?

**Lane question.** Measure the merge-attributable ratio (master against its own source
frames) on `blotch` and `chroma` for all 26 corpus subjects, so the project can state or
refuse:

> The strehl merge is never worse than the best single frame it was built from, on every
> subject in the corpus.

**Answer, in one line.** The invariant as stated is **VIOLATED**, and separately it was
**never measurable from the existing instrument**, because every master/source ratio this
project has published is computed on an unmatched, per-image, content-derived nonlinear
gauge. The gauge finding outranks the ratios and is reported first.

Everything below is reproducible from this directory. Scratch, logs, evidence TIFFs and
crops are under `C:\dev\strehl-out\V-NEVERWORSE\`.

---

## 0. Two corrections to the brief, found before any measurement

**The pin.** The brief named `740e7056`. SHIP-V4's own `RUN.txt` names **`9b05d0b7`**
(`strehl.exe` sha256 `44C2F2CD…F490`); `740e7056` rendered SHIP-V3. All 26 shipped masters
name the same build. Everything here uses `9b05d0b7`, copied to
`C:\dev\strehl-out\V-NEVERWORSE\bin\strehl.exe` and sha-verified on every render
(`vn_lib.check_pin`).

This lane found the discrepancy independently, before rendering anything, and the brief
later confirmed it. Note the scope carefully: `740e7056` is not a *wrong* build, it is the
**correct** build for a different corpus. It is wrong only as a pin for SHIP-V4. Verified
by hashing every sealed corpus on this machine against every pinned binary:

| corpus | seals | agree? | build sha256 | pin |
| --- | --- | --- | --- | --- |
| `acceptance\SHIP-V4` (**scored here**) | 26 | 26/26 | `44C2F2CD…F490` | `9b05d0b7` |
| `acceptance\SHIP-V3` | 26 | 26/26 | `15EA7346…A7B0` | `740e7056` |
| `SHIP-V2` | 26 | 26/26 | `CF33AE08…` | `b9b6921e` |

All three shipping corpora are internally consistent — one build each, every seal agreeing
— and each has its matching pin on disk. The check is one command and it is authoritative:

```powershell
(Get-FileHash <pinned exe> -Algorithm SHA256).Hash -eq (Get-Content <subject>.tiff.ok).Trim()
```

**Two builds here are the same size to the byte, and a third joins them.** Size and
timestamp identify nothing:

| build | bytes | provenance |
| --- | --- | --- |
| `44C2F2CD…F490` | 9,568,768 | seals SHIP-V4 |
| `15EA7346…A7B0` | 9,568,768 | seals SHIP-V3 |
| `B50EABC1…` | 9,568,768 | **seals neither**, and it sits at `strehl-out\PIN-V3\strehl.exe` |

That third one is the rule in the wild: a directory whose *name* claims to be the V3 pin,
holding a binary that is not the V3 pin, at a byte size identical to both real ones. On
this machine it is reached only by a commissioning fixture under `V-GATHER\pincommission`,
so it is not currently mis-scoring anything — but a lane reaching for "PIN-V3" by name, or
checking size, would be off-gauge and would see nothing wrong.

**RETRACTED — the absence claim in this section's first version was false.** It read:
"`066A87AB` is not present in any of the 160 copies of `strehl.exe` under `C:\dev`". ORCH
refuted it by holding the file. It is at
`C:\dev\strehl-out\V-REVIEW\bin\strehl-pinned.exe`, and it is there now.

The mechanism is in the retracted sentence itself. The scan filtered `fn.lower() ==
"strehl.exe"`; the file is named `strehl-pinned.exe`. **162 files match `strehl.exe` where
307 match `strehl*.exe`** — the query could reach barely half the population, and the build
I declared absent was in the half it could not see. I scoped the negative to the root,
honestly, and the root was not the binding scope: **the filename pattern was.** An absence
result is a statement about the query until the query's reach is measured.

So `vn_seals.py` no longer widens the pattern and calls it fixed — widening is unfalsifiable
on its own, because a wider query that still misses something looks exactly like a complete
one. It now **plants decoys it is required to find**, under names straddling each pattern
boundary, and hard-fails if a decoy inside the pattern is missed:

| planted build | `strehl.exe` | `strehl*.exe` | `*.exe` |
| --- | --- | --- | --- |
| `strehl.exe` | FOUND | FOUND | FOUND |
| `strehl-pinned-decoy.exe` — *the v1 miss* | **miss** | FOUND | FOUND |
| `strehl2.exe` | **miss** | FOUND | FOUND |
| `zz-renamed-build.exe` | **miss** | **miss** | FOUND |
| `renamed-build-no-ext` | **miss** | **miss** | **miss** |

v1's pattern misses **4 of the 5**. The last row is unreachable by design and is the
**measured residual blind spot** — a build renamed without an `.exe` extension would still
escape, and that is now a stated number rather than an assumed zero.

Corrected census, `C:\dev`, both scopes:

| scope | files walked | matched | hashed | distinct builds | `066A87AB` |
| --- | --- | --- | --- | --- | --- |
| `strehl*.exe` | 1,171,076 | 307 | 2.2 GB | 170 | **PRESENT, 1 copy** |
| `*.exe` (absence-grade) | 1,161,785 | 7,699 | 11.5 GB | 2,515 | **PRESENT, 1 copy** |

Both scopes find it. The `strehl*.exe` figures agree with ORCH's independent 301 paths / 165
builds to within the drift of six lanes rebuilding during the scan.

**One thing the corrected census surfaces that is worth acting on:** `066A87AB`'s single
copy is not a stray — it is `V-REVIEW\bin\strehl-pinned.exe`, i.e. a lane's *pinned working
binary*. That lane is pinned, deliberately and correctly by its own lights, to a build that
reproduces neither SHIP-V3 nor SHIP-V4. Its measurements are sound arm-versus-arm and may
not be quoted as shipping behaviour. Same class as the `PIN-V3` hazard below, but live.

`vn_seals.py` reproduces this whole section: it hashes every file matching a pattern under a
root, reads every `.tiff.ok` on disk, and fails on a corpus carrying more than one seal, a
seal with no binary within reach, or a path whose *name* claims a corpus its hash does not
seal. It classifies `V-GATHER\pincommission\*`, `V-REVIEW\pinguard\*` and `acceptance\PINTEST`
as other lanes' deliberate fixtures, so their intentionally mixed and synthetic seals are not
reported as incidents. Current state: **0 incidents**, three shipping corpora all 26/26
consistent, one name-vs-hash hazard (`PIN-V3` above). It refuses to imply an absence unless
the reach arm has run: `--skip-reach` prints "no absence claim may be drawn from this run",
and a decoy that should have been found is a fatal error, not a warning.

**The check that makes it a measurement, not an assumption.** Each master carries a
`<subject>--SHIP-V4.tiff.ok` file whose entire content is the sha256 of the binary that
rendered it. Reading all 26 and hashing my own copy:

- all 26 `.ok` files carry the **identical** hash `44C2F2CD…F490` — one build rendered the
  whole corpus, so there is no per-subject binary drift to control for;
- `C:\dev\strehl-out\V-NEVERWORSE\bin\strehl.exe` hashes to exactly that value.

Had the source arm been rendered by `740e7056`, every one of the 26 ratios would have
carried an uncontrolled binary difference between numerator and denominator — the same
mismatched-gauge defect §1 reports in the existing statistics, arriving by a different
door. Provenance is a gauge input, and a build is identified by its hash against the seal
of the corpus being compared to, never by its size, its path or its name.

**The label.** The `master/best-source` line at `orch_printready.py:223` is not computed by
the gate. It is read verbatim out of `experiments/V-REVIEW/vr_baseline.json`, which records

```json
"source_baseline": "max over registered source frames"
```

For a statistic where low is good, `max` is the **worst** frame. The nine existing
acquittals therefore establish *"the master is no worse than the worst frame it was built
from"* — not the best. The string printed to the operator says `best-source`.

### 0.1 Switch-state audit — what the source arm matched, and what it could not

The masters' verbatim argv is
`strehl.exe stack "D:\personal\macro\<subject>" --out <...>.tiff --srgb --auto-exposure`.
Reading a full provenance file rather than only its `binary :` line
(`bee-1-cpl--SHIP-V4.tiff.provenance.txt`) gives the resolved switch state:

```
RESOLVED SWITCH STATE (39 registry switches; 0 set)
```

Eleven switches are annotated `cleared by harness` — `STREHL_FIX_CA`, `STREHL_EDGE_AWARE`,
`STREHL_EDGE_TAU`, `STREHL_EDGE_CONF`, `STREHL_MERGE`, `STREHL_ALIGN`, `STREHL_CACHE_DIR`,
`STREHL_PYRAMID_WORKERS`, `STREHL_ONLY_FRAME`, `STREHL_WARPMAP`, `STREHL_FIX_HALO_DELTA` —
and the remaining twenty-eight `not set`. **Both annotations resolve to `(unset)`**, so
`vn_lib.render()`'s blanket clear of every `STREHL_*` variable reproduces the shipping
switch state exactly rather than merely approximately. Six of the thirty-nine are marked
`INAPPLICABLE`: estimator-only stages the pyramid backend never reaches.

**Matched:** all 39 switches, and the binary.
**Deliberately not matched:** two, both load-bearing and both stated.

- `STREHL_ONLY_FRAME` is set in the source arm and unset in the master. That switch *is*
  the source arm — it is the independent variable, not a confound.
- `--srgb --auto-exposure` is replaced by `--linear-srgb --demosaic`. This is the subject of
  §1: the shipping flags apply a per-image content-derived tone curve, and measuring a
  ratio across it measures exposure. §1.6 and G2 show the substitution is sound — the pin
  reproduces a shipped master **byte-identically** under the shipping flags, so the two
  paths are confirmed to differ only in the output transform.

---

## 1. THE GAUGE FINDING — the existing pair statistics are unsound

`vn_gauge.py`. Full transcript: `report\gauge.txt`.

### 1.1 What is wrong

`orch_blotchpair.py` and `orch_chromapair.py` compare a strehl master against source frames
**rendered with `--srgb`**. `--srgb` applies a per-image tone rendering computed from *the
image's own luminance percentiles* (`crates/strehl-cli/src/image_out.rs`,
`Tone::from_luminance`):

```
black = p0.1(luminance) * TONE_BLACK_FRACTION(0.85)
white = black + (p99.9(luminance) - black) / TONE_WHITE_TARGET(0.90)
        then placement, soft toe (0.004), sRGB encode, display S-curve (0.55)
```

Both percentiles come from the image being rendered. A 123-frame master and a single frame
get **different black points, different white points and a differently placed S-curve**.
`blotch = band/mean` survives a linear gain but not a black subtraction, a transfer curve or
an S-curve. `chroma`'s `(R−Y)/Y` likewise. The two arms of every existing ratio sit on two
different content-derived nonlinear curves.

Both statistics' own docstrings state the premise that fails: `orch_blotch.blotch_ratio`
says contrast is "invariant to the tone scaling the pipeline applies";
`orch_chroma.relative_chroma` says "dividing by luma is what makes this survive a tone
scale". Both are true of a *scale*. The pipeline does not apply a scale.

### 1.2 The documented defence does not reach the pixels

`vr_lib.py` names the defence: force `--exposure` to the master's own stops so gain and
curve are "COMMON MODE". Measured on `coffee-bubbles` frame 0, `--srgb --exposure=X`:

| commanded stops | commanded gain | delivered pixel gain (LSQ through origin, all pixels) |
|---|---|---|
| −0.26 | 1.0x | 1.00000x |
| −1.26 | 0.5x | 1.00000x |
| −2.26 | 0.3x | 1.00000x |
| +1.74 | 4.0x | 1.00000x |
| +5.00 | 38.3x | 1.00000x |

**153x of commanded range; worst departure from unity 0.000%.** The arms at −0.26, −1.26,
−2.26 and +1.74 are **pixel-identical**. A 2x commanded gain (−0.26 vs −1.26) changes
**11 bytes, all at offsets 339–359**, below the first strip at 3399 — i.e. inside
`ImageDescription` and nowhere else. The tone rendering is computed *after* exposure from
the resulting luminance, so it renormalises the commanded gain away.

The masters carry per-image gain **0.790x .. 13.548x = 17.1x across the corpus** (G1b). A
ratio statistic on a gain-sensitive quantity must be matched, and the only mechanism the
codebase offers for matching it is a no-op.

### 1.3 The tone difference is measured, not inferred

Same forced `--exposure` on both arms, master vs one of its own frames:

| subject | master black/white | frame black/white | span ratio |
|---|---|---|---|
| `coffee-bubbles` | 0.009860 / 0.990710 | 0.010340 / 0.830220 | **0.836x** |
| `wrapped-text-1` | 0.021410 / 0.995100 | 0.035560 / 0.833570 | **0.820x** |

### 1.4 Corroboration already in the tree

- Every master's provenance file: `sRGB, TONE CURVE APPLIED -- DO NOT MEASURE NUMERICALLY`.
- `strehl stack --help` on `--linear-srgb`: *"THIS IS THE MODE TO MEASURE IN … more than one
  result in this project has been retracted for exactly that."*
- `image_out.rs` carries a unit test named
  `tone_rides_with_the_viewing_render_and_never_with_a_measurement`.

The instruction was already written down. The pair statistics do not follow it.

### 1.5 How much it moved the published numbers

`vn_damage.py` — same subject, same windows, same 21 frames, admitted or refused by the same
decision, **only the gauge differs**. `report`/`damage.log`.

| subject | statistic | sRGB gauge (as published) min/med/max | linear gauge (measurable) min/med/max | gauge effect on max / on min |
|---|---|---|---|---|
| `lead-1-cpl` | blotch | 2.2141 / 1.2836 / **1.0618** | 1.8490 / 1.1288 / **0.9849** | **x0.928** / x0.835 |
| `lead-1-cpl` | band | 1.8645 / 1.1748 / 0.9843 | 1.8041 / 1.1177 / 0.9899 | x1.006 / x0.968 |
| `lead-1-cpl` | chroma | 1.1441 / 0.9470 / 0.9086 | 1.2776 / 0.9812 / 0.9292 | x1.023 / x1.117 |
| `leaf-2-cpl` | blotch | 2.6624 / 1.8032 / **1.1801** | 2.7661 / 1.6139 / **1.0749** | x0.911 / x1.039 |
| `leaf-2-cpl` | band | 2.2050 / 1.6041 / 1.0799 | 2.6117 / 1.5692 / 1.1111 | x1.029 / x1.184 |
| `foam` | blotch | 1.5043 / 1.0452 / 0.8932 | 1.9582 / 1.2165 / 0.9664 | x1.082 / x1.302 |
| `foam` | band | 0.9062 / 0.5729 / **0.5094** | 1.7360 / 1.1351 / **0.9520** | **x1.869** / x1.916 |
| `foam` | chroma | 1.2800 / 1.0539 / 0.9009 | 1.0627 / 0.9417 / 0.8805 | x0.977 / x0.830 |

My sRGB arm reproduces the published values closely enough to identify the quantity —
`foam` blotch 0.8932 vs published 0.88522 (0.9%), `foam` band 0.5094 vs 0.52709 (3.4%),
`leaf-2-cpl` blotch 1.1801 vs 1.13781 (3.7%), `lead-1-cpl` chroma 0.9086 vs 0.90316 (0.6%) —
across a different arm (SHIP-V3 vs V4), pin and frame sample. `lead-1-cpl` blotch/band agree
less well (16–18%), consistent with a different window choice on a different render.

**The single largest correction:** `foam`'s band ratio, the project's showcase evidence that
the merge *halved* an ugly subject's blotch band (`0.527`), reads **0.952** on a measurable
gauge. The merge did not halve it. It left it approximately unchanged. That claim should be
withdrawn or restated.

### 1.6 The gauge used here

`--linear-srgb --demosaic`: camera colour matrix to BT.709/D65, then stop. Verified per
subject (G5): **no tone clause on either arm**, camera levels identical on master and frame
(`black 512, white 15360`), `4688×7032×3` uint16. `--exposure` is *refused* on this path
(`"--exposure and --auto-exposure are viewing controls and need --srgb"`), so no per-image
gain flag exists to get wrong.

Licence to re-render: with the pin, a cleared environment and the master's own recorded
stops, `coffee-bubbles` re-renders **byte-identically** to the shipped master
(`aba490aa3f77`). Develop is downstream of the merge, so re-developing the same merge into
`--linear-srgb` changes only the develop. `vn_lib.render()` hard-errors if a tone clause ever
appears on the measurement path.

---

## 2. COMMISSIONING

`vn_commission.py`, subject `coffee-bubbles`, 19/19 frames. Full transcript:
`report\commission.txt`. Baseline: master blotch 0.04581, chroma 0.04572; vs BEST(min)
source blotch **1.4495x**, chroma **1.0871x**.

| arm | direction required | result | verdict |
|---|---|---|---|
| **N0** identity (α=0) | must not move | 1.449497x / 1.087109x, bitwise unchanged | PASS |
| **N1** placebo outside the window | must not move | 1.449497x (unmoved); the *same* plant inside the window reads **8.6139x**, so the placebo had power | PASS |
| **D1** degrade master blotch | must **rise** | amp 5→80 DN: 1.4519 · 1.4628 · 1.5092 · 1.6885 · **2.2785** (mean of 6 fields) | PASS |
| **I1** improve master blotch | must **fall**, and cross unity | α 0.20→0.95: 1.2074 · 0.9708 · 0.7453 · 0.5452 · **0.4338** — crosses unity downward | PASS |
| **D2** degrade master chroma | must **rise** | amp 10→160 DN: 1.0910 · 1.1097 · 1.1888 · 1.4721 · **2.2533** | PASS |
| **I2** improve master chroma | must **fall**, and cross unity | α 0.20→0.95: 0.9638 · 0.8455 · 0.7345 · 0.6344 · **0.5698** — crosses unity downward | PASS |
| **S1** degrade the DENOMINATOR | readings must move with the master untouched | blotch 1.4495→**1.1657**, chroma 1.0871→**1.0022** | PASS |
| **S2** thin the DENOMINATOR | readings must move | drop the argmin frame: 1.4495→1.4161 (2.31%). 60 random subsets/N: N=3 spans 1.109x, N=5 1.071x, N=9 1.041x, N=13 1.028x | PASS |
| **X1a** chromatic plant | blotch still, chroma up | blotch x0.993, chroma **x1.251** | PASS |
| **X1b** achromatic *multiplicative* plant | blotch up, chroma still | blotch **x1.254**, chroma x1.000 (cancels exactly in `(R−Y)/Y`) | PASS |
| **X1c** achromatic *additive* plant | **fooling direction** | blotch x1.472, chroma **x1.420** | PASS (documented) |
| **W1** resampling null | must not move | identity x1.0000; shift 0.37,0.61 px x1.0006/x0.9988; scale+shift x1.0094/x1.0049; rotate 0.05° x1.0005/x0.9997 — worst departure **0.94%** | PASS, but **under-scoped — see §2.3** |
| **W2** resampling null *at the magnification actually used* | must not move | round trip at each subject's own fitted scale, all 26 subjects: blotch **0.9991–1.0005**, chroma **0.9931–1.0000**; identity and round-trip-identity both exactly x1.0000 | PASS |
| **Q1** quantisation floor | must have headroom | master band 54.352 DN vs uint16 quantisation band 0.0149 DN = **3644x**; chroma-window luma p1 1134 DN vs the statistic's hard floor of 1.0 | PASS |

**Verdict: COMMISSIONED.** Both signs move, the denominator is load-bearing, the placebo has
demonstrated power and does not move, and the resampler the source arm goes through is
neutral to 0.94%.

Four of these arms failed first and each failure was a real defect in this instrument, fixed
and re-run: the amplitude ladders redrew the random field at every rung instead of scaling
one field; `blot_field` was not zero-mean so the plant moved `mean`, the *denominator* of
`blotch`; a single random field can partially cancel the window's own band structure, so
every ladder rung is now the mean of 6 independent fields with its range printed; and S2's
first version subsampled by `linspace`, which always retains both endpoints and therefore
the argmin, reporting a stability the estimator does not have.

**Declared fooling directions** (rule 18):

- **X1c.** Adding δ to R, G and B sends `(R−Y)/Y` to `(R−Y)/(Y+δ)`, so a purely *luminance*
  blotch modulates `orch_chroma`'s relative chroma — worth **x1.420** at δ_rms = 80 DN on a
  window with p1 luma 1134 DN. **A chroma ratio must never be read as chroma-only when the
  blotch ratio has also moved.** On this corpus blotch and chroma move together on most
  subjects, so the chroma column is *not* independent evidence.
- **W1's `relhf` column.** The 3 px term falls to **x0.710–x0.818** under a sub-pixel warp
  while `band/mean` holds to 0.94%. That is why this lane ratios `band/mean` and never
  `band/noise` — and it is also why the `relhf` focus proxy in §5 carries a stated bound
  rather than a claim. W2 reproduces this at the real magnification (`relhf` x0.66–x0.90)
  and it doubles as W2's own positive control: see §2.3.
- **Clipping reads as *perfect* chroma.** A window clipped to 65535 has R=G=B, so
  `relative_chroma` collapses toward zero and a destroyed frame scores as a flawless
  denominator. Caught on real data (§3) and now guarded.

### 2.1 A degenerate denominator caught on real data

The first 26-subject run reported `coffee-bean` chroma **vs_min = 638.4x**. Cause:
`orch_chroma.pick_window` chose a near-white background window (master mean 61211 DN); source
frames 31/36/26 clipped **99.97% / 99.95% / 79.2%** of that window, collapsing their chroma to
~5e-7 and manufacturing a 638x "violation". Two defects in this instrument, both mine:
`ncc_c` was computed but never enforced (only `ncc_b` gated admission), and there was no
clipping guard. Both fixed — per-statistic admission (`ok_b`, `ok_c`, with recorded reasons,
`SAT_DN=64000`, `SAT_MAX=0.02`), commissioning re-verified, all 26 subjects re-measured.

### 2.2 Source-set size: how many frames, and what it costs

**N = 21 uniformly spaced frames per subject**, both ends of the sweep always included.
Justification: a full source arm on the twelve 299-frame stacks is ~3.5 s per frame ×
299 × 26 ≈ 7.5 hours of render alone; N=21 is ~70–120 s per subject.

`vn_sens.py` deep-samples `lead-1-cpl` (123 frames) and `foam` (100) at **N=61** and then
recomputes on **200 random subsets per rung** (not `linspace` — see S2):

| subject / stat | N=3 | N=9 | N=21 | full | P(vs_min>1) at N=21 |
|---|---|---|---|---|---|
| `lead-1-cpl` blotch | 1.4866 | 1.6468 | 1.7703 | **1.8490** | 1.00 |
| `lead-1-cpl` chroma | 1.1223 | 1.2173 | 1.2776 | **1.2776** | 1.00 |
| `foam` blotch | 1.7504 | 1.9777 | 2.1990 | **2.1990** | 1.00 |
| `foam` chroma | 1.0166 | 1.0627 | 1.1133 | **1.1133** | 1.00 |

`vs_min` is **monotone increasing in N** — as it must be, since more frames can only lower
the min. Three of the four ladders cross unity at N=3–9 and none does at N≥13.

**The bound, stated:** subsampling can only *raise* the estimated minimum, so
`vs_min(sample) ≤ vs_min(full stack)`. **A violation found on the sample is real and is a
lower bound on its own size. A subject that passes on the sample has passed only against
the sampled reference, and may fail against the full stack.** The three subjects with the
smallest measured excess (`119MSDCF` 1.0108x, `109MSDCF` 1.0120x, `pencil-steep-angle-cpl`
1.0172x) are within that uncertainty and their *sign* is the only thing established.

---

### 2.3 W1 was under-scoped by 17.5x — found after the fact, chased, and closed

`vn_warpnull.py`. Full transcript: `report\warpnull.txt`.

**How it was found.** Re-reading a master's provenance file in full — prompted by the
switch-state audit in §0.1, not by anything in my own instrument — surfaced a line I had
not used:

```
coverage : field of view scaled to 0.9236 so that EVERY frame covers every pixel
           (7.6% of width dropped, then upsampled to keep the output dimensions)
```

A single-frame render covers 0.9974 uniformly. Measuring the fitted registration scale that
the source arm actually applies, over all **510** admitted frames across the 26 subjects:
**0.7745 … 0.9996, median 0.9566** — source windows are magnified by up to **1.29x**. W1
certified the resampler at `1 + 1.66e-2` = **1.7%**. That is a **17.5x under-coverage**, and
it is the same class of defect as an arm that never perturbs its reference: the null was
real, it just was not run where the instrument operates.

**The failure direction was specific and stated in advance.** If the warp *lowers* blotch,
every source frame reads artificially low, the min reads low, and every `vs_min` in §6 is
inflated. So the question was not "does the warp move things" but "does it move them in the
direction that would manufacture my result".

**Four defects in W2 itself before it could answer.** Each is recorded in the file.

1. The first affines scaled about the image **origin**, which translates a window at
   x = 5840 by ~900 px. That fetches different content; it does not resample the same
   content. Three of four subjects reported *window falls outside* — `warp_window` was
   doing its job and my transform was wrong.
2. With the centre fixed, the identity control still could not run on three subjects, whose
   windows sit 14–38 px from the image edge: a synthetic transform carries none of the
   inward translation a real registration matrix does, so there is no margin for the
   interpolation footprint. Fixed with an integer-only inward clamp applied identically to
   the baseline and every arm. **The script now hard-errors if any identity arm moves by
   more than 1e-6, or if a subject produces no identity control at all** — a null without
   its own control is not a null. Measured: both identity arms return 1.0 on all 26
   subjects and both statistics, worst departure **3.5e-7**.
3. **The arm I nearly reported was measuring the wrong thing.** Applying the fitted affine
   once to the master gave blotch factors from **0.2114x to 1.1095x** — a 373% "correction"
   that would have re-stated every number in this document. It is an artefact of the null.
   The pipeline's affine maps master → frame and `warp_window` pulls with
   `WARP_INVERSE_MAP`, so a real source frame's content arrives **in master space** and
   `orch_blotch`'s fixed 50–400 px band is applied at the scale it was designed for. My
   single application left the master's content at the *frame's* scale while the band still
   ran in master pixels — so it charged for a band shift the pipeline never incurs. A
   **round trip** (warp and unwarp) restores the geometry exactly and leaves only the
   interpolator behind, applying *two* interpolations where the pipeline applies one, which
   overstates the loss in the conservative direction.
4. **The arm labelled "worst scale" was the least warped frame, not the most.** It was
   `min(|s − 1|)` — the scale *closest* to unity. Caught by a checker that recomputed the
   quoted scale range from the measurement records and disagreed with the prose. Replaced
   by an *extreme scale* arm using the single most magnified frame each subject actually
   contributed, which is the true worst case; the table below reports it.

A 0.21x reading is not a resampler. Bilinear interpolation attenuates structure near
Nyquist, one to two pixels; the band under test is 50–400 px, three orders of magnitude
away. The extreme reading was implausible on its face and that is what prompted the check.

**The answer, all 26 subjects, round trip at each subject's own fitted scales.** Two arms
per subject — its median frame and its most magnified frame (down to 0.7745, a 1.29x
magnification) — and each row is scored at whichever of the two is worse:

| | min | median | max |
| --- | --- | --- | --- |
| blotch factor | 0.9870 (`leaf-2-cpl`) | 0.9996 | 1.0049 (`lavendar-cpl`) |
| chroma factor | 0.9847 (`wrapped-text-1`) | 0.9990 | 1.0000 |

Worst departure from unity on any subject, either statistic, either arm: **1.53%**. **The
failure direction is absent on all 26.** No subject's `vs_min` is inflated by more than
1.6%, so the resampler cannot account for any excursion in §6 — not the 3.8089x, and not
the 1.0108x either.

**The null is not inert, and it proves so itself.** In the same arms, `relhf` — a 3 px
proxy, i.e. one that lives exactly where bilinear interpolation does its damage — falls to
**x0.66–x0.90**. The round trip demonstrably moves the quantity that should move and leaves
alone the quantity that should not. Without that, "everything came back 1.0000x" would be
indistinguishable from a probe that never ran.

**Net effect on this document: none.** No ratio, partition, or verdict changes. W1's
conclusion was correct, but W1 had not established it — it was right at 1.7% and the
instrument runs at 29%. The distinction matters, because had the round trip come back at
0.81x, §6 would have needed re-stating and W1 would have certified it clean.

**The prose above is itself checked, and the checker is itself commissioned.**
`vn_verify23.py` re-derives all 26 numbers quoted in this section from the measurement
records — the W2 output, the per-subject ratio records, and a master's provenance file —
and pins each to its own contextual anchor rather than to bare presence. Its first run
found five wrong numbers I had typed, one of which was not a typo but the mislabelled arm
in defect 4 above. `vn_negctl23.py` then plants fourteen defects one at a time, plus a
placebo edit outside the checked span, and requires **RED on all fourteen and GREEN on the
placebo**; it copies the file to `$env:TEMP` first and restores from that copy, and it
hard-errors if any anchor does not land exactly once. Two rounds of that found two more
defects, both in the checking apparatus rather than the prose:

- **A presence test is satisfied by a duplicate.** Mutating the fitted scale range's upper
  bound still read GREEN, because the same four digits are the blotch median in the table
  below. Same for the magnification, repeated in the sentence under the table. Fixed by
  requiring each literal within 90 characters of its own anchor phrase.
- **The failure detector matched the word for "no failures".** The harness scanned for
  lines containing `MISMATCH`, which also matches the checker's own summary line
  *"N claims checked, 0 MISMATCH"* — so the placebo read as a false positive on every green
  run. Fixed by keying on the `FAILED:` block.

Final state: **15/15**, and the file restores byte-identically afterwards.

---

## 3. THE 26-ROW TABLE

`vn_run.py` → `vn_report.py`. Full transcript: `report\table.txt`.

- `absBlot` / `absChrm` are **the gate's own numbers**: `orch_blotch` and `orch_chroma`
  unmodified on the shipped SHIP-V4 master, at the shipped master's own windows. They match
  `orch_printready.py` (e.g. `lead-1-cpl` 0.00555, `foam` 0.46075).
- Every ratio column is on `--linear-srgb --demosaic`, master against that subject's own
  frames, each frame registered into the master's window (masters and single frames have
  different fit-to-cover crops).
- `b/mnSh` is min over the *sharper half* of the frames by `relhf`; `beat` is how many
  admissible frames strictly beat the master; `n` is frames registered, `N` the stack depth.

```
subject                               absBlot  absChrm |   b/min  b/mnSh   b/med   b/max | band/mn |   c/min   c/med   c/max |  beat    n    N | verdict
109MSDCF                              0.00169  0.00051 |  1.0120  1.0120  0.9955  0.8378 |  1.0099 |  1.1450  0.9942  0.9006 |  7/21   21   22 | BLOTCH>1 CHROMA>1
112MSDCF                              0.14667  0.03485 |  1.4015  1.2317  1.2219  1.1661 |  1.3029 |  1.3438  1.2653  1.2032 | 21/21   21   79 | BLOTCH>1 CHROMA>1
113MSDCF                              0.25168  0.02538 |  1.2900  1.1939  1.1395  1.0854 |  1.2575 |  1.1099  1.0868  1.0585 | 21/21   21   63 | BLOTCH>1 CHROMA>1
119MSDCF                              0.00157  0.00059 |  1.0108  1.0108  0.9594  0.8050 |  1.0015 |  1.0446  1.0127  0.9725 |  4/20   20   33 | BLOTCH>1 CHROMA>1
bee-1-cpl                             0.00105  0.00042 |  1.6266  1.6266  0.6253  0.5128 |  1.6857 |  1.1962  1.1340  1.0447 |  4/18   18  299 | BLOTCH>1 CHROMA>1
bee-2-cpl                             0.00133  0.00058 |  2.7897  2.6002  1.9483  0.8139 |  2.6685 |  1.3462  0.8716  0.7937 | 11/12   12  299 | BLOTCH>1 CHROMA>1
bee-3-cpl                             0.00113  0.00046 |  0.7848  0.7487  0.7451  0.7003 |  0.7713 |  1.3373  1.2804  1.2169 |  0/ 7    7  299 | CHROMA>1
coffee-bean                           0.00082  0.00010 |  1.6312  1.5232  1.5442  0.8708 |  1.6395 |  1.2135  0.9301  0.6380 | 16/18   18  105 | BLOTCH>1 CHROMA>1
coffee-bubbles                        0.09892  0.05460 |  1.4501  1.4154  1.3698  1.2343 |  1.4950 |  1.0877  0.9913  0.8711 | 19/19   19   19 | BLOTCH>1 CHROMA>1
couch-fibers-cpl                      0.04511  0.00418 |  3.8089  1.8150  1.4720  0.9635 |  3.6938 |  1.5936  1.1060  0.8531 | 11/13   13  299 | BLOTCH>1 CHROMA>1
dry-erase-marker-head-cpl             0.00446  0.00044 |       -       -       -       - |       - |  1.1195  1.0091  0.8888 |  -/ -   15  299 | CHROMA>1 b:REFUSED
flat-on-ruler-cpl                     0.18363  0.00277 |  1.4101  1.0675  1.0653  0.9854 |  1.4629 |  1.1795  1.0162  0.7761 | 15/19   19   79 | BLOTCH>1 CHROMA>1
flower-bud-alone-cpl                  0.00036  0.00033 |  2.0065  2.0065  1.6984  1.3866 |  1.8034 |  1.2954  1.1718  1.0549 |  8/ 8    8  205 | BLOTCH>1 CHROMA>1
flower-bud-with-background-fern-cpl   0.00092  0.00026 |  1.9354  1.9354  1.6364  1.1089 |  2.0088 |  1.0377  0.9471  0.8738 | 19/19   19  299 | BLOTCH>1 CHROMA>1
flower-inner-edge-cpl                 0.09921  0.01226 |  2.6420  2.3067  1.6666  0.9881 |  2.3292 |  3.3437  2.2205  0.8163 | 19/20   20  299 | BLOTCH>1 CHROMA>1
flowers-cpl                           0.01090  0.00992 |  2.5300  1.4564  1.4564  0.6710 |  2.0688 |  4.4774  1.7609  0.7109 | 13/17   17  176 | BLOTCH>1 CHROMA>1
foam                                  0.46075  0.03250 |  1.9582  1.2746  1.2165  0.9664 |  1.7360 |  1.0627  0.9417  0.8805 | 10/12   12  100 | BLOTCH>1 CHROMA>1
highly-angled-ruler-mm-cpl            0.00507  0.00093 | REFUSED: only 5/21 source frames admissible (UNREGISTERED x16)
lavendar-cpl                          0.00155  0.00057 |  0.9158  0.9158  0.7565  0.4553 |  0.8553 |  1.1321  1.0702  1.0041 |  0/ 7    7  299 | CHROMA>1
lead-1-cpl                            0.00555  0.02021 |  1.8490  1.4530  1.1288  0.9849 |  1.8041 |  1.2776  0.9812  0.9292 | 20/21   21  123 | BLOTCH>1 CHROMA>1
leaf-2-cpl                            0.00448  0.01973 |  2.7661  1.6178  1.6139  1.0749 |  2.6117 |  1.2064  0.9329  0.8957 | 20/20   20  182 | BLOTCH>1 CHROMA>1
pencil-flatter-angle-cpl              0.00164  0.00060 |  1.6208  0.5605  0.7459  0.3449 |  1.5162 |  1.1655  1.0756  0.9813 |  6/12   12  299 | BLOTCH>1 CHROMA>1
pencil-steep-angle-cpl                0.00501  0.00102 |  1.0172  0.7566  0.7819  0.6738 |  0.9541 |  1.3171  1.1709  0.7063 |  3/14   14  299 | BLOTCH>1 CHROMA>1
tweezers-cpl                          0.00345  0.00020 |  0.9544  0.9544  0.9293  0.7521 |  0.9322 |  1.1211  1.0227  0.9520 |  0/18   18  100 | CHROMA>1
wrapped-text-1                        0.00452  0.00097 |  1.0420  1.0420  0.7546  0.4316 |  1.0442 |  1.9607  1.2152  0.8175 |  4/14   14  130 | BLOTCH>1 CHROMA>1
wrapped-text-2                        0.00395  0.00088 |  1.0622  1.0475  0.6914  0.5139 |  1.0470 |  1.0339  0.8857  0.7690 |  5/21   21  120 | BLOTCH>1 CHROMA>1
```

### The partition, per statistic — it sums

```
BLOTCH   measured 24 + refused 2 + failed 0 = 26 of 26
  REFUSED  dry-erase-marker-head-cpl    the MASTER's own blotch window is 72.7% clipped -- no headroom on either arm
  REFUSED  highly-angled-ruler-mm-cpl   only 5/21 source frames admissible (UNREGISTERED x16)

CHROMA   measured 25 + refused 1 + failed 0 = 26 of 26
  REFUSED  highly-angled-ruler-mm-cpl   only 5/21 source frames admissible (UNREGISTERED x16)
```

Nothing failed; nothing is silently absent.

**A side finding worth someone's attention.** `dry-erase-marker-head-cpl` is refused here
because `orch_blotch.flattest` picks, as the master's flattest window, a region that is
**72.7% clipped at the sensor**. The gate nonetheless reports an absolute blotch of 0.00446
for that subject and passes it. A blotch measured on blown pixels is measuring nothing.
`orch_blotch` has no clipping guard; this lane's `SAT_MAX` guard is in `vn_lib`, and the gate
would benefit from the same. Owner of `orch_blotch` to judge.

---

## 4. THE NULL — `vs_min > 1` is the default, not the evidence

`vn_null.py`. Full transcript: `report\null.txt`. Rule 39: never report a ratio without its
null.

`vs_min` compares **one** number against the **minimum of N**. That is what the invariant
asks for, but it means any ordinary member of the source distribution also scores above 1.
So: leave-one-out. Each admissible source frame `f` is scored exactly as the master is —
`stat(f) / min(stat(g) for g ≠ f)` — giving N observations of the master's own question
asked of something that is definitionally *not* a merge.

```
excess = vs_min(master) / median(leave-one-out)
```

| | blotch | chroma |
|---|---|---|
| `vs_min > 1` | **21 / 24** | **25 / 25** |
| **excess over the null > 1** | **14 / 24** | **16 / 25** |
| median excess | **1.134** | **1.023** |
| excess range | 0.625 .. 1.948 | 0.872 .. 2.220 |

The null has real power: `loo_med` runs 1.02–2.60 on blotch. Roughly a third of the apparent
blotch violations and a third of the chroma violations are the shape of the denominator, not
the merge. `bee-1-cpl`'s headline 1.6266x has a null of **2.6013x** — a typical *frame* beats
the master's score at the same game, so that row is not evidence against the merge at all.

### 4.1 The rank test — extremum-free, and it does not go away

`beaten` = how many admissible frames strictly beat the master. If the master were an
ordinary draw from the same distribution its rank would be uniform, so
P(all n frames beat it) = 1/(n+1). This cannot be argued away as a bias of the minimum.

**Every admissible source frame beats the master on:**

| statistic | subjects | n | one-sided p |
|---|---|---|---|
| blotch | `112MSDCF`, `113MSDCF` | 21 | 0.0455 |
| blotch | `leaf-2-cpl` | 20 | 0.0476 |
| blotch | `coffee-bubbles`, `flower-bud-with-background-fern-cpl` | 19 | 0.0500 |
| blotch | `flower-bud-alone-cpl` | 8 | 0.1111 |
| chroma | `112MSDCF`, `113MSDCF` | 21 | 0.0455 |
| chroma | `bee-1-cpl` | 17 | 0.0556 |
| chroma | `bee-3-cpl`, `lavendar-cpl` | 7 | 0.1250 |
| chroma | `flower-bud-alone-cpl` | 8 | 0.1111 |

`lead-1-cpl` — the subject that created this lane — is beaten by **20 of 21** frames on
blotch (p = 0.0909).

**Note the window is chosen in the master's favour.** `orch_blotch.flattest` picks the
window that *minimises the master's own band energy*; the sources are then measured wherever
that lands. The comparison is biased toward the master and the master still loses. The
violations are conservative.

---

## 5. CHARACTERISING THE VIOLATION — what is the merge being charged for?

### 5.1 The `relhf` proxy failed, and the visual settled it

The pre-registered hypothesis was that the argmin frame wins by being *defocused* — a smooth
frame wins a smoothness contest for free (`V-bestframe.md` §2 hit exactly this). The `relhf`
table (`report\table.txt`) does **not** support it: `relhf@argmin / relhf@median` runs
0.80–1.11, i.e. the argmin looks like an ordinary frame.

**That table is uninformative and I am reporting it as uninformative, not as a negative
result.** `relhf` is 3 px energy over mean, and at 3 px on these exposures the term is
dominated by sensor noise rather than by resolved detail — a defocused frame keeps its noise.
W1 independently shows the same term is not warp-stable (x0.710–x0.818). The proxy cannot
answer the question.

The true-1:1 crops can. `vn_visual.py`, CROP = 380 px cut by slicing, no resize, no grade,
one display transform computed once from the master and applied identically to all three
images (rule 48). Crops in `visual\`.

| subject | crop std, master | crop std, argmin source | crop std, argmax source |
|---|---|---|---|
| `112MSDCF` (window 1558,14 → crop at 1818,274) | **79.45 DN** | 51.01 DN (f78) | 61.95 DN (f47) |
| `leaf-2-cpl` (14,14 → 274,274) | **161.36 DN** | 87.58 DN (f154) | 93.14 DN (f18) |
| `coffee-bubbles` (14,38 → 274,298) | **121.76 DN** | 78.61 DN (f0) | 79.46 DN (f17) |
| `lead-1-cpl` (22,14 → 282,274) | **65.58 DN** | 38.45 DN (f122) | 44.37 DN (f18) |

Note that argmin and argmax sit close together on every subject (51 vs 62, 88 vs 93, 79 vs
79, 38 vs 44) while the master sits well above **both**. The master is not losing to an
outlier; the whole source distribution is below it.

**And the crops say why.** On `112MSDCF` the master resolves a field of fine branching
filaments; the argmin source frame at the same 380 px is **completely defocused** — the
filaments are absent and only noise remains. On `coffee-bubbles` the master resolves sharp
specular highlights and fine speckle on the bubble film; the argmin frame is a smooth blur
with the highlights washed out. `lead-1-cpl` and `leaf-2-cpl` are near-flat paper at this
window in both arms and the difference is not visible at true 1:1.

So on the rank-decisive subjects the merge is being charged, by a 50–400 px band statistic,
for **structure it resolved that no sampled source frame resolved**. That is the innocent
explanation named in `orch_chromapair.py`'s own docstring, and here it is confirmed visually
rather than assumed.

### 5.2 Bounding the innocent explanation

`relhf` master / source-median, at the same window (`report\null.txt`). This is an unwarped
master against warped sources, so it is biased **up** by W1's suppression factor; the
conservative column applies the worst case, ×0.82.

Blotch excess over the null against that conservative detail gain:

| subject | excess over null | detail gain ×0.82 | excess / detail |
|---|---|---|---|
| `foam` | 1.216 | 8.652 | 0.14 |
| `flat-on-ruler-cpl` | 1.065 | 5.156 | 0.21 |
| `113MSDCF` | 1.139 | 1.905 | 0.60 |
| `112MSDCF` | 1.222 | 1.670 | 0.73 |
| `couch-fibers-cpl` | 1.472 | 1.946 | 0.76 |
| `lead-1-cpl` | 1.129 | 1.525 | 0.74 |
| `flower-inner-edge-cpl` | 1.667 | 1.707 | 0.98 |
| `leaf-2-cpl` | 1.614 | 1.639 | 0.99 |
| `flower-bud-alone-cpl` | 1.698 | 1.700 | 1.00 |
| `coffee-bean` | 1.544 | 1.504 | **1.03** |
| `coffee-bubbles` | 1.370 | 1.270 | **1.08** |
| `flowers-cpl` | 1.456 | 1.302 | **1.12** |
| `bee-2-cpl` | 1.948 | 1.675 | **1.16** |

On **20 of 24** measured subjects the merge-attributable band excess is at or below the
conservatively bounded detail gain at the same window. On **4** it exceeds it, by at most
**16%** (`bee-2-cpl`). Those four are the residual that a detail explanation does not cover,
and they are where a reviewer should look first. This is a bound, not a proof: `relhf` is a
weak proxy (§5.1) and the correction factor is borrowed from a different subject's warp.

---

## 6. VERDICT

Stated separately per statistic and per denominator, as required.

### 6.1 The invariant as literally stated — "no worse than the BEST single frame"

> **blotch — VIOLATED on 21 of 24 measured subjects** (2 refused, 0 failed), largest first:
> `couch-fibers-cpl` 3.8089x, `bee-2-cpl` 2.7897x, `leaf-2-cpl` 2.7661x,
> `flower-inner-edge-cpl` 2.6420x, `flowers-cpl` 2.5300x, `flower-bud-alone-cpl` 2.0065x,
> `foam` 1.9582x, `flower-bud-with-background-fern-cpl` 1.9354x, `lead-1-cpl` 1.8490x,
> `coffee-bean` 1.6312x, `bee-1-cpl` 1.6266x, `pencil-flatter-angle-cpl` 1.6208x,
> `coffee-bubbles` 1.4501x, `flat-on-ruler-cpl` 1.4101x, `112MSDCF` 1.4015x,
> `113MSDCF` 1.2900x, `wrapped-text-2` 1.0622x, `wrapped-text-1` 1.0420x,
> `pencil-steep-angle-cpl` 1.0172x, `109MSDCF` 1.0120x, `119MSDCF` 1.0108x.
> Holds on `bee-3-cpl` 0.7848x, `lavendar-cpl` 0.9158x, `tweezers-cpl` 0.9544x.
>
> **chroma — VIOLATED on 25 of 25 measured subjects** (1 refused, 0 failed), largest first:
> `flowers-cpl` 4.4774x, `flower-inner-edge-cpl` 3.3437x, `wrapped-text-1` 1.9607x,
> `couch-fibers-cpl` 1.5936x, `bee-2-cpl` 1.3462x, `112MSDCF` 1.3438x, `bee-3-cpl` 1.3373x,
> `pencil-steep-angle-cpl` 1.3171x, `flower-bud-alone-cpl` 1.2954x, `lead-1-cpl` 1.2776x,
> `coffee-bean` 1.2135x, `leaf-2-cpl` 1.2064x, `bee-1-cpl` 1.1962x, `flat-on-ruler-cpl`
> 1.1795x, `pencil-flatter-angle-cpl` 1.1655x, `109MSDCF` 1.1450x, `lavendar-cpl` 1.1321x,
> `tweezers-cpl` 1.1211x, `dry-erase-marker-head-cpl` 1.1195x, `113MSDCF` 1.1099x,
> `coffee-bubbles` 1.0877x, `foam` 1.0627x, `119MSDCF` 1.0446x,
> `flower-bud-with-background-fern-cpl` 1.0377x, `wrapped-text-2` 1.0339x.

Both are **lower bounds** on the full-stack figure (§2.2), and the chroma column is not
independent of the blotch column (X1c).

**The source arm's own resampling is not the cause.** That was the obvious innocent
explanation and it is measured and excluded in §2.3: pushing each master through a round
trip at its own fitted registration scale moves blotch by at most **1.3%** on any of the 26
subjects, and the direction that would manufacture these results is absent. It cannot
explain the 3.8089x and it cannot explain the 1.0108x either.

**This invariant should not be shipped as written.** It asks a per-region *selection*
stacker to beat the extremum of N draws on a smoothness statistic, at a window where most of
those draws are out of focus. §5.1 shows the merge is often losing because it resolved
something. The result is a real measurement of a badly posed question.

### 6.2 The defensible restatements

| statement | blotch | chroma |
|---|---|---|
| no worse than the **median** frame | holds on **10/24** | holds on **9/25** |
| no worse than the **worst** frame *(what the gate actually prints)* | holds on **18/24** | holds on **19/25** |
| no worse than a **typical frame playing the same game** (excess ≤ 1) | holds on **10/24** | holds on **9/25** |
| **rank**: not beaten by every frame | holds on **18/24** | holds on **19/25** |

None of the four reaches 26 or even 24. There is no denominator at which "the merge is never
worse than the frames it was built from" is currently true across this corpus.

### 6.3 What the print gate can and cannot say today

**REFUSED — the acceptance invariant is unestablished on all 26 subjects, not on 17.** The
nine ratios the gate prints are (a) computed on an unsound gauge whose error is measured here
at **0.83x–1.92x**, and (b) labelled `best-source` while computed against the **worst** frame.
The gap the brief identified is real and is larger than stated: the 17 PASS rows have no
ratio at all, *and* the 9 that do have one do not have a sound one.

`lead-1-cpl`, specifically: its published **1.258x** is `master/worst-source` on an sRGB
gauge. On a measurable gauge against the worst frame it is **0.985x**; against the *best*
frame it is **1.849x**; against the null it is **1.129x**; and 20 of 21 frames beat it.
Four different numbers, three different questions. The gate prints one of them under a label
that names another.

### 6.4 What I could not measure

- `highly-angled-ruler-mm-cpl` — **refused, both statistics.** 16 of 21 frames would not
  register into the master's window (`UNREGISTERED`), leaving 5, below this lane's `MIN_OK=7`.
  A steeply angled ruler changes appearance so fast through the sweep that a single master
  window has no counterpart in most frames. Measurable only with a per-frame window policy,
  which is a different instrument.
- `dry-erase-marker-head-cpl` — **refused, blotch only.** The master's own flattest window is
  72.7% clipped at the sensor. Measured on chroma (1.1195x) at an unclipped window.
- The four subjects in §5.2 where band excess exceeds the bounded detail gain
  (`bee-2-cpl`, `flowers-cpl`, `coffee-bubbles`, `coffee-bean`) are **characterised but not
  adjudicated**: the residual is 3–16% and my detail proxy is not good enough to resolve it.
  Settling those needs a sharpness statistic that is warp-stable, which is another lane's
  instrument.

---

## 6.5 The four unadjudicated subjects, named

These are the only genuine regression candidates in the corpus: the subjects where the
merge-attributable band excess is **not** covered by the conservatively bounded detail gain
at the same window (§5.2). Everything else is either within the bound or holds outright.

| subject | abs blotch | blotch vs min | band vs min | excess over null | detail bound ×0.82 | **excess over bound** | sampled / admitted / stack depth |
|---|---|---|---|---|---|---|---|
| `bee-2-cpl` | 0.00133 | 2.7897x | 2.6685x | 1.948 | 1.675 | **+16%** | 21 / 12 / 299 |
| `flowers-cpl` | 0.01090 | 2.5300x | 2.0688x | 1.456 | 1.302 | **+12%** | 21 / 17 / 176 |
| `coffee-bubbles` | 0.09892 | 1.4501x | 1.4950x | 1.370 | 1.270 | **+8%** | 19 / 19 / 19 |
| `coffee-bean` | 0.00082 | 1.6312x | 1.6395x | 1.544 | 1.504 | **+3%** | 21 / 18 / 105 |

Three things about this list that matter before anyone acts on it.

**The bound is weak in the merge's favour, and the residual is small against its own error
bars.** The `relhf` detail proxy failed its own commissioning as a sharpness statistic
(§5.1) and the ×0.82 warp correction is borrowed from a different subject's registration.
A 3% residual on `coffee-bean` is well inside that; a 16% residual on `bee-2-cpl` is the
only one I would call suggestive, and even it is not established.

**Three of the four are the same picture, and it is a picture about my instrument.** This
lane samples at most **21 frames per stack** (§2.2), so on `bee-2-cpl`, `flowers-cpl` and
`coffee-bean` — stacks of 299, 176 and 105 — the reference is a 21-frame subsample, of which
registration then admitted only **12, 17 and 18**. The `min` in "no worse than the best
single frame" is therefore a minimum over 12 to 18 draws standing in for a minimum over
105 to 299. That is a much weaker bound and it is biased in the merge's favour on the
absolute question, but it also means these three are the subjects **my measurement**
resolves worst, not demonstrably the subjects the merge handles worst.

**`coffee-bubbles` is the exception and is the one to look at first.** Its stack is 19 frames
deep, all **19 were sampled and all 19 admitted** — the only subject among the four whose
reference is the complete stack, with no subsampling and nothing dropped — and it still
shows +8%. It also carries a high absolute blotch (0.09892) at a window that is genuinely
flat. If there is a real merge regression anywhere in these four, `coffee-bubbles` is where
it is cleanest to prove and cheapest to re-measure. I did not adjudicate it because doing so
needs a warp-stable sharpness statistic, which is another lane's instrument.

**Every number in the table above is re-derived, not transcribed.** `vn_verify65.py` recomputes
each from `report\null.json` and the per-subject `ratio\*.json` records (`excess = vs_min /
loo_med`; `bound = relhf_ratio × 0.82`) and matches it against the document: 45 claims, all
green. Writing this section I misread the section 3 `beat` column as an admitted-frame count
and then misread `n_total` as a registered count; the checker caught both before this text
was committed, which is the whole reason it exists.

`vn_negctl65.py` commissions it with **17 planted defects and a placebo — 17/17 caught, placebo
clean, restore byte-identical.** Two of those plants failed on the first run, and both were
defects in the checking apparatus rather than in the prose:

- **A duplicate satisfied a presence test.** Mutating the `+8%` cell of `coffee-bubbles` read
  green, because the same `+8%` also appears in the prose a hundred characters away and the
  proximity window found that instead. Table-cell claims are now checked against the cell's
  own table row and nothing else. This is the second time this lane has been bitten by
  duplicate-satisfies-presence (§2.3); it is not a one-off.
- **A crash scored as a pass.** Substituting a subject in the table made the checker raise
  `IndexError` before printing anything, and the control — which keyed only on the `FAILED:`
  block — recorded that silence as green. The control now distinguishes three states, and any
  traceback is its own verdict. A checker that dies is not a checker that agreed.

---

## 6.6 For the owner's README — plain language, quotable as-is

> **What stacking gives you, and what it does not.** Strehl merges a run of frames into one
> image that is sharp front to back, and on every subject we tested it resolves detail that
> no single frame in the stack resolved — that is the win, and it is not in doubt. What it
> does **not** do is give you cleaner smooth areas than your best single frame. We checked
> this the hard way on all 26 test stacks, comparing each finished image against the actual
> frames it was built from: in flat, out-of-focus regions the merged file carries slightly
> more fine mottling than the cleanest frame that went into it, on 21 of the 24 subjects we
> could measure, and faint colour speckle behaves the same way. Most of that is not damage.
> The merge is largely being charged for texture it genuinely resolved — on 20 of those 24
> the extra mottling is fully accounted for by the extra real detail at the same spot, and
> at 100% on screen what you are looking at is hair, fibre and speckle that is really there.
> On four subjects it is not fully accounted for, by at most 16%. So: judge a stack on
> detail and depth of field, where it wins outright. If you are printing large and your
> subject has broad smooth backgrounds, look at those backgrounds at 100% before you commit
> — stacking is not a noise-reduction step, and we have never measured it to be one.

Written for someone judging prints. It concedes the finding in the first three sentences
rather than burying it, because the failure mode of a claim like this is a reviewer finding
the exception before the README admits it.

---

## 7. Files

| file | what it does |
|---|---|
| `vn_lib.py` | gauge, pin check, render, registration, per-statistic admission. Its docstring carries the gauge finding. |
| `vn_masters.py` | renders all 26 SHIP-V4 merges into `--linear-srgb --demosaic` |
| `vn_gauge.py` | gauge commissioning G1–G5 (§1) |
| `vn_commission.py` | instrument commissioning, 13 arms (§2) |
| `vn_run.py` | the 26-subject measurement (§3) |
| `vn_null.py` | leave-one-out null, rank test, detail bound (§4, §5.2) |
| `vn_sens.py` | N-sensitivity, random subsets (§2.2) |
| `vn_damage.py` | sRGB vs linear gauge at fixed windows and fixed frames (§1.5) |
| `vn_report.py` | the table and the partition (§3) |
| `vn_visual.py` | true-1:1 crops (§5.1) |
| `vn_warpnull.py` | the resampling null at the magnification actually used (§2.3) |
| `vn_verify23.py` | re-derives every number quoted in §2.3 from the records |
| `vn_negctl23.py` | negative control for that checker: 14 plants + 1 placebo, 15/15 |
| `vn_verify65.py` | re-derives every number in §6.5 from `null.json` and the ratio records |
| `vn_negctl65.py` | negative control for that checker: 17 plants + 1 placebo, 17/17 |
| `vn_seals.py` | hashes every `strehl*.exe` and every `.tiff.ok` seal; reproduces §0. Plants decoys it must find, so reach is measured rather than assumed. |

Nothing outside `experiments/V-NEVERWORSE/` was modified. `D:\` was never written.
