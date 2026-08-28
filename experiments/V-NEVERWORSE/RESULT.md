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

## 7. `coffee-bubbles` — adjudicated. CONVICTED.

ORCH asked for one subject to be settled properly: the only one of the four in
§6.5 whose reference is the complete stack, so the objection that sank the other
three — a `min` over a subsample standing in for a `min` over the stack — does not
apply. It is convicted. The excess is real, it is mid-scale, and no frame in the
stack contains it.

### 7.1 First, a correction I owe, because ORCH adopted the wrong version of it

Reporting §6.5 upward I wrote that `bee-2-cpl`'s +16% was the least trustworthy of
the four because *"a minimum over a small sample is biased high, which manufactures
excess."* ORCH quoted that reasoning back and acted on it. **The first clause is
true and the second is backwards.** A minimum biased *high* is a *larger*
denominator, and `master / min` therefore comes out *smaller*. Subsampling
**suppresses** measured excess; it cannot manufacture it.

§6.1 of this document already said so, which makes the error mine in the summary
rather than in the work — but a correct document does not repair a wrong briefing,
and the briefing is what was acted on.

Measured rather than argued, on the only stack that was taken entire
(`vn_subsample.py`, 4000 draws per row):

| frames drawn | median ratio | p10 | p90 | vs the full-19 answer |
|---|---|---|---|---|
| 3 | 1.4102x | 1.3698x | 1.4501x | 0.972 |
| 6 | 1.4167x | 1.3999x | 1.4501x | 0.977 |
| 12 | 1.4501x | 1.4154x | 1.4501x | 1.000 |
| 17 | 1.4501x | 1.4167x | 1.4501x | 1.000 |
| 19 | 1.4501x | 1.4501x | 1.4501x | 1.000 |

The p90 column is pinned at the full-stack value in **every** row and no percentile
of any row exceeds it, which is the whole point: a minimum over a subset can only
be greater than or equal to the minimum over the set, so the ratio can only come
out lower. **Every subsampled ratio in §3 and §6.5 is a lower bound.**
`bee-2-cpl`'s +16% is if anything understated.

The operational conclusion — do `coffee-bubbles` first — survives, but for the
opposite reason to the one I gave. It is not the least-inflated of the four. It is
the one whose number is **exact**, because all 19 frames were sampled and all 19
admitted, so there is no sampling argument to have.

### 7.2 Re-measured against all 19 sources

| quantity | value |
|---|---|
| frames in stack, sampled, admitted | 19, 19, 19 - all of them |
| window (master coords, 900x900) | y=38, x=14, cover 0.9887 |
| master blotch | 0.045810 |
| best (lowest) source frame | f0, 0.031591 |
| **master / best source** | **1.4501x** |
| per-frame blotch reproduced against the recorded values to | 3.873e-09 |

Writing that table I gave the frame-count row the same cell text as the one
in §6.5, and `vn_negctl65.py` refused to run: it reported that the frame-count cell
occurred twice where it needed to occur exactly once. It is the check ORCH asked for after the last round's
duplicate-satisfies-presence near-miss, it fired on the first document edit made
under it, and it stopped rather than mutating whichever copy it found first.
`vn_anchors.py` now reports every collision in one pass instead of one per run.

That last line is the gauge check for this section: the pipeline that renders and
registers the 19 frames here reproduces the recorded per-frame numbers to nine
decimal places, so the numerator and denominator are on the same gauge and the
`--linear-srgb --demosaic` correction of §1 is carried through.

### 7.3 The three hypotheses, distinguished — not weighed

ORCH asked for these to be separated rather than balanced. Each was given a test
that could have come out the other way.

**(c) An artifact of the blotch statistic on this subject's content — REFUTED.**
If `blotch` simply reads high on bubble imagery, the frames should read high too.
They do not. Every comparison below is candidate-count matched: the master's `min`
is over 19 frames, and each frame's null `min` is over the other 18, so neither
side gets a wider draw than the other.

| | master | frames, median | frames, max |
|---|---|---|---|
| whole window | **1.4501x** | 1.0586x | 1.1748x |
| worst tile (y=300, x=150) | **2.7202x** | 1.2816x | 1.4928x |

**0 of 19 frames score at or above the master, on either scale.** The statistic is
not reading the subject; it is reading the master.

**(b) The merge being charged for resolved fine structure no frame contains —
REFUTED.** This is the explanation that covered 20 of the 24 subjects in §5.2, so
it had to be tested rather than assumed absent. `vn_mech.py` removes structure
below a scale `k` from both sides and re-measures; a fine-detail mechanism dies as
`k` grows, a mid-scale one survives. Both signatures were planted and the
instrument was required to *separate* them, not merely to notice them:

| planted mechanism | survival at k=33 |
|---|---|
| fine (specular-highlight-like points) | 0.014 |
| mid-scale | 0.897 |
| **measured on `coffee-bubbles`** | **0.995** |

Separation between the two planted signatures is **62.1x**, and the real subject
sits at the mid-scale end of it, past the planted mid-scale arm. The excess over
the frames' own null is **37.0% at k=1 and 36.8% at k=33** — despeckling the image
does not touch it.

This also refuted a hypothesis of my own. The 1:1 contact sheet appeared to show
hard-edged rectangular blocks in the master's band field, and `boxblur(lum,
LO_R//2)` is a **square 51 px kernel**, so I suspected the blocks were the
statistic's own kernel ringing on resolved point highlights. `vn_diag_spec.py`
measured the band's step profile: it peaks at **49.8 px** with a harmonic at 99.7
px, which matched the kernel exactly and looked like a confirmation — but there is
**no lattice in the luminance at all**, and the mechanism sweep put survival at
0.995 where a kernel artifact on fine highlights would have been near 0.014. The
appearance was real and the explanation was wrong.

**(a) Genuine mid-scale structure the merge introduced — SUPPORTED**, as what is
left once (b) and (c) are excluded, and independently corroborated:

| evidence | value | reference |
|---|---|---|
| inter-frame motion / structure | **0.452** | static baseline 0.0287 — 15.7x |
| frame-to-frame band correlation at the worst tile | r = 0.178 | frames barely agree with each other there |
| master's correlation to the frame family | 0.4103 | matched null (each frame's best *other* frame) **0.5418** |

That last row is the sharpest of the three, and it reversed an earlier reading of
mine. I first compared the master's 0.4103 against the *median* pair correlation
0.1771 and concluded the master matched the family well. That was wrong:
`attr_best_corr` is a **max over 19**, and comparing a max to a median is not a
comparison. Against the correct matched null — each frame's *best other frame* —
the master matches the family **worse than the frames match each other**. The
master's band structure is not any frame's band structure.

**One robustness point in the merge's favour, worth stating because it removes an
obvious objection:** `blotch` is a standard deviation over a window, and a rigid
displacement does not change a standard deviation. **Misregistration cannot inflate
this ratio.** The conviction does not rest on registration quality.

### 7.4 The mechanism, stated only as far as it is measured

What is established: **the SHIP-V4 master carries band-scale (50-400 px) structure
that is present in no source frame, on a subject whose frames disagree with each
other 15.7x more than a static subject's do.** Mid-scale structure absent from
every frame, on a stack that moved.

The leading candidate is that inter-frame motion is being merged rather than
rejected — bubble content that moved between frames combining into structure that
no single frame contains. ORCH is right that this would be the more useful result:
it is a robustness defect, not a statistic disagreement. **I could not establish
it**, and it is not claimed. See §7.5.

Amplitude, for scale: at the worst tile the master's band std is 0.02669 against
0.010-0.019 for the frames, but `p99|band|` is comparable (0.064 against
0.046-0.065). **The master's band is elevated in bulk, not in its extremes** — this
is not a few hot pixels or a localised blow-out but a raised floor of mid-scale
modulation across the tile, which is consistent with merged motion and
inconsistent with an outlier spike.

Crops at native 1:1 are at `C:\dev\strehl-out\V-NEVERWORSE\bubbles\`
(`tile-master.png`, `tile-f00-lowest-blotch.png`, `tile-f16-best-match.png`, and
the three `band-*.png` at a shared scale). Nothing was written to `crops-1to1/`.

### 7.5 What I refused, and why each refusal is counted

Four instruments were built for this subject. Two certified and were used; two did
not certify and were **not** used. Both refusals ship in their own counted category
with the measurement that disqualified them, and both `vn_select.py` and
`vn_where.py` exit non-zero on their real-data path so neither can be run for a
number by accident.

| instrument | commissioning | status |
|---|---|---|
| `vn_bubbles.py` | 13 ok + 0 failed, 1 statistic refused | **used** |
| `vn_mech.py` | 6 ok + 0 failed | **used** |
| `vn_where.py` — is the excess where the motion is? | 3 ok + 3 failed | **REFUSED** |
| `vn_select.py` — did the merge select or blend? | 2 ok + 3 failed | **REFUSED** |

**`ghost_peak` (inside `vn_bubbles`) — refused.** Duplication detector. v1 was
*inverted*: the band's own autocorrelation is 0.91 at lag 12, so the max outside an
exclusion radius pins near the radius and the planted duplicate read **0.9468**
against a placebo of **0.9521** — the defect scored *better* than the control. v2
moved the right way but still failed, because a 50-400 px band in a 900 px window
holds only ~10-80 independent cells and chance anisotropy matches a planted
duplicate.

**The rigid-shift estimate — refused, and it must not be quoted.** My own
`shift_capped` flag fired: the estimate hit 167 px against a 140 px cap, so the
number is a boundary, not a measurement.

**`vn_where.py` — refused.** This is the one I most wanted, because it is ORCH's
robustness question. Five designs, each rejected on a measurement:

| design | why it failed |
|---|---|
| rank correlation across tiles | null spread 0.183; no plant clears it |
| the same, tiles overlapped | null spread 0.190 — **overlapping tiles are not independent, so 121 of them bought no power over 36** |
| averaging-master fixture | baseline pinned at -0.695; the LOW arm had nowhere to fall |
| two-group permutation z | 5 of 6 arms, but baseline +3.36: **motion inflates any `min`-based excess**, because a wider spread of frame band-std pushes the `min` denominator down |
| z referenced to the frames' own z | baseline -0.60 — the structural term does cancel — but asymmetric, below |

The final design's disqualifying table:

| plant | reading |
|---|---|
| injected where motion is LOW | **-4.26 sd** — detected |
| injected at random sites (placebo) | -2.68 sd — also moves |
| injected where motion is HIGH | **-0.44 sd — not detected** |

It reads de-localisation well and localisation barely, and localisation is the
direction the question needs. A green reading from it would have been unearned.
Root cause is the same wall that refused `ghost_peak`: **the band scale and the
window size jointly cap what any spatial analysis of `blotch` can resolve at 900
px.** Fixing it needs a larger window or a narrower band, and both change the
statistic under test.

**`vn_select.py` — refused**, with a negative result worth keeping. The two
endpoints of its scale — a master that *is* a frame, and a master that is an
outright average — sit **0.000 and 0.046** apart. Blur conserves flux, so at
50-400 px every frame of a focus stack is nearly the same image and choosing one is
nearly the same as averaging them. The recovered selection map's median run length
was 2 px against a planted 100 px patch, because wherever two frames agree the
per-pixel `argmin` is arbitrary. **Whether this merge selected or blended is not
recoverable from the master alone**, so the mechanism in §7.4 stops where it does.
One directional result survived and is recorded as suggestive only: with an
identical planted selection map, moving frames gave 1.1125x against static frames'
1.0571x, so selection over a moving subject does produce mid-scale excess. It did
not reach the 1.25x bar set before the run and is not counted as evidence.

### 7.6 Verdict, and what can be done about it

**CONVICTED.** On `coffee-bubbles` the merge is genuinely worse than every one of
the 19 frames it was built from, on `blotch`, at **1.4501x** over the best frame and
**37%** over the frames' own leave-one-out null. It is not a sampling artifact —
the whole stack was used. It is not the statistic reading the subject — no frame
reads high. It is not the merge being charged for resolved fine detail — the excess
survives despeckling at 0.995 against a 0.014 fine-detail signature.

**Fixability: cannot be stated, and the reason is specific.** Naming a fix requires
knowing whether the merge selected or blended at those pixels, and §7.5 shows that
is not recoverable from the master. What *can* be said is where to look: this is a
19-frame stack of a subject with heavy inter-frame motion, and the excess is
mid-scale structure matching no frame. **The instrumented test that would settle it
is inside the merge, not outside it** — log the per-pixel contribution weights for
this subject and check whether moving content was down-weighted. That is a lane
with source access, not this one.

**For the owner, in plain language, quotable as-is:**

> On one subject out of twenty-six — the coffee bubbles, where the bubbles visibly
> move between shots — the stacked result has more fine mottling than any of the
> nineteen individual frames it was made from, about 45% more than the cleanest one.
> This is not the stacker being blamed for picking up extra detail; we tested that
> and it is not the explanation. It is most likely the bubbles' movement being
> blended together instead of thrown away. On the other twenty-five subjects we
> found nothing of the kind. If you are printing the coffee bubbles, check the
> smooth areas at full size before you commit to paper.

---

## 8. The mechanism — ORCH's hypothesis is REFUTED, and the direction is backwards

Reporting the refutation first, as instructed.

### 8.1 The gauge finding: the module I was aimed at did not run

`softgate.rs` is not the shipping gate. Its Gaussian admission weight, its
`WEIGHT_FLOOR` and the `z = sqrt(32 ln 2) = 4.7096` truncation were all
unexecuted for every SHIP-V4 master. Three independent readings, at the build
commit `9b05d0b7` rather than at HEAD:

| check | result |
|---|---|
| `merge.rs` `SOFT_GATE_ENV` | `STREHL_SOFT_GATE`, and `None` — the top-hat `Gate` — "**must remain the default**" |
| the 26 masters' provenance | `STREHL_SOFT_GATE = (unset)` on **26 of 26** |
| the binary's own self-report | `selection : SOFT -- weight = (band power above the noise floor)^exponent` — the **pyramid** path, not the focus-response gate |

Two traps here, both of which would have produced a confident wrong answer.

**The source drifts from the binary.** `softgate.rs` differs by **29 lines**
between the build commit and HEAD, `merge.rs` by 142 and `focus.rs` by 630.
Reading the gate at HEAD and describing the shipping masters with it is the same
mismatched-gauge defect as measuring a master against a differently-rendered
frame. Every line quoted in this section is from `git show 9b05d0b7:`.

**The module's own status comment is stale and says the opposite of the truth.**
At `9b05d0b7` it reads *"Opt-in and not wired. Nothing in this module is
reachable from the default merge path"* — while `merge.rs` line 76 imports
`SoftGate` and line 1811 constructs it. It **is** reachable; it is merely not
*selected* by default. A structural claim taken from a doc comment would have
been wrong in both directions at once. The load-bearing evidence is the switch
default plus the 26 provenance files, not the prose.

### 8.2 What the shipping merge actually does

The default `stack` path is a Laplacian pyramid merge: 7 Laplacian levels plus a
base. Per coefficient the weight is `(band power above the noise floor)^exponent`
with a noise gate at **2.00x** the modelled band-noise power; below it no frame
may win and the merge averages. The base band is a plain mean. The selection is
made on green luma only.

The binary reports the admission decision per level, and the coarse levels land
inside the band `orch_blotch` measures — the master is 7032 px wide, so a
coefficient at the two coarsest Laplacian levels spans roughly **125 px and
63 px**, against the statistic's 50-400 px window.

### 8.3 The corpus test, commissioned in both directions — and it is NULL

If mottle came from a spatially varying mixture of *averaged* and *selected*
coefficients, the mixture should matter most where it is most mixed. The
mixedness `4p(1-p)` of the coarsest level's averaged fraction is 0 when every
coefficient goes the same way and 1 at `p = 0.5`.

`vn_mechtest.py`, commissioned **5 ok + 0 failed** on the real 24-subject
population with plants in both directions (excess replaced by a rising function
of mixedness must give rho > +0.8; by a falling function, rho < -0.8; labels
shuffled and mixedness shuffled must give ~0; and the placebo spread must be
resolvable). It also carries a **population guard**: the first run of this
harness certified three arms on **zero** subjects, because the loader read a key
that did not exist and "shuffled labels give rho ~ 0" is trivially true of
nothing at all. It now refuses to commission on fewer than 20 subjects.

| test | rho | permutation p |
|---|---|---|
| excess vs mixedness `4p(1-p)` | **+0.174** | 0.41 |
| excess vs raw averaged fraction | **+0.174** | 0.41 |
| excess vs frame count | **-0.028** | 0.90 |
| excess vs the master's own measured noise | **-0.031** | 0.89 |

All four null; the placebo spread is sd 0.203, so +0.174 is inside the noise of
the test. The corpus extremes are outright counterexamples:

| subject | mixedness | excess | |
|---|---|---|---|
| `109MSDCF` | **0.997** — the most mixed in the corpus | **0.996** | no excess at all |
| `bee-2-cpl` | 0.086 | **1.948** — the worst in the corpus | nearly unmixed |
| `flat-on-ruler-cpl` | **0.000** — nothing averaged | 1.065 | convicted by V-GATHER at 1.32x |

The frame-count null is the strongest of the four and it is worth stating alone.
A 299-frame stack averages residual noise down by `1/sqrt(299)`, a 19-frame
stack by `1/sqrt(19)` — a **4x** difference in noise amplitude. It buys **no**
reduction in excess (rho -0.028, p 0.90), and 299-frame stacks sit at both the
top and the bottom of the excess ranking. **The mottle is not unaveraged noise.**

That agrees with the independent evidence from §7.3: on `coffee-bubbles` the
excess survives despeckling at **0.995**, and the master's band is elevated in
bulk while its `p99|band|` is comparable to the frames'. Noise removed by a 33 px
opening-closing would not do that. **It is structure.**

### 8.4 Why the hypothesis is backwards, with the number that shows it

ORCH's premise was that in flat regions the gate has nothing but noise to
compare, so admission there is noise-driven. **The measurement says admission in
flat regions is not noise-driven; it is nearly complete.**

`docs/research/M111-waxy-blobs.md` §2 measured `n_eff` directly on a shipped
render, stratified by the winner's focus response — which is exactly the
conditional test ORCH asked for in point 3, already run:

| winner response | % of plane | mean `n_eff` | median `n_eff` |
|---|---|---|---|
| 0.60 – 0.65 | 18.55 | **275.5** | 285 |
| 1.00 – 1.50 | 6.96 | 22.5 | 17 |
| 3.00 – 5.00 | 9.17 | 3.0 | 2 |
| above 20 | 15.18 | **1.1** | 1 |

Admission falls **285 to 1** while the response rises about 8x. The flattest
regions are the *most* averaged, not the least. ORCH's step 2 — "its admission
decision in flat regions is driven by noise" — is the opposite of what the
shipped merge does, and steps 3 and 4 inherit the error: the predicted signature
was "excess worst where the response is flattest", and the flattest regions are
where `n_eff` approaches N.

**The mechanism that survives** is M111's, and it is not about noise at all:

> The merge stops averaging and starts electing wherever the winner's focus
> response rises out of the noise floor, because the gate's tolerance is an
> absolute constant in response units while the response itself is a
> contrast-scaled quantity spanning 0.43 to 84 on this stack.

The tolerance is fixed at `4.0 * sqrt(2) * FOCUS_NOISE_SD` = **0.086063**
response units. That is 14% of a response of 0.62 and 1.7% of a response of 5.
So the *effective* strictness of the gate varies by an order of magnitude with
local contrast, and regions carrying weak defocused structure fall into a
collapse band where `n_eff` drops toward 1 and each plateau is rendered from a
single frame. **The plateau seams are the mottle** — mid-scale structure present
in no single frame, which is precisely what §7.3 measured on `coffee-bubbles`
and what V-GATHER convicted on five more.

This explains all four nulls in §8.3 at once. A single-frame plateau is not
noise, so it does not scale with the noise level; averaging more frames does not
remove it, so it does not scale with frame count; and it lives in the
*transition* band, which the averaged-fraction proxy cannot see by construction —
that proxy fires only where **no** frame cleared the floor, which is the
`n_eff ≈ 285` case, the cleanest one. I flagged that blindness before running the
test and it is why the null is reported as a refutation of the *stated* mechanism
rather than of every possible admission mechanism.

### 8.5 The shape of the fix, and one caution about it

`softgate.rs` is a written, tested, unwired remedy pointing at this defect. It is
**not** the cause, and I would caution against reading it as the whole fix: a
Gaussian kernel softens the *edge* of the admission decision, but the defect
M111 measured is that the tolerance is on the **wrong scale**, not that it has a
hard edge. Softening a mis-scaled threshold moves the seam without removing the
collapse. **The fix indicated by the measurement is a tolerance that scales with
the local response** — a relative rather than absolute admission criterion — and
the soft kernel is complementary to that, not a substitute for it.

### 8.6 What I did not measure, counted

| item | status |
|---|---|
| corpus admission record, 26 subjects | **measured** — 24 correlated, 2 refused |
| `n_eff` stratified by response | **cited, not re-derived** — M111 §2, on a shipped render |
| my own per-pixel `n_eff` map | **NOT MEASURED** |
| counterfactual renders (plain mean; smoothed admission) | **NOT MEASURED** |
| sharpness alongside blotch for those counterfactuals | **NOT MEASURED** |

Partition: 26 examined = **24 measured + 2 refused + 0 failed**. The two refused
are `dry-erase-marker-head-cpl` and `highly-angled-ruler-mm-cpl`, which carry no
entry in `report/null.json` — they were never in the 24-subject null population,
so they have no excess to correlate.

The four counterfactual numbers ORCH asked for are not in this report. Producing
them means re-rendering the convicted subjects under three merge configurations
and carrying a sharpness statistic on the same pixels, and I did not get there.
I am not going to estimate them. What replaces them is the direction: the
conditional test ORCH wanted was already run by M111 and it points at a
tolerance-scaling defect, so the counterfactual worth spending the renders on is
**a response-relative tolerance**, not a plain mean.

### 8.7 The checker for this section failed its own commissioning first

Reporting this because it nearly cost the section its numbers, and because it is
the same defect class twice more.

`vn_verify8.py` ran **37 checks, 0 failed** on its first version and then caught
**5 of 13** planted defects. A green run and a blind run are the same glyph. Two
causes:

1. **Eight checks compared git and M111 against constants written in the
   checker.** Mutating the report could not fail them, because the report was
   never read; the checker was verifying its own copy of the answer. Fixed by
   parsing every value out of `RESULT.md` and treating the document as the
   claim and git / M111 as the oracle.
2. **The presence window was 220 characters,** wide enough that the adjacent
   table row's identical correlation value satisfied a mutated cell. This is the
   duplicate-satisfies-presence defect, and it is the second time this lane has
   hit it. Fixed by matching table claims per row on the exact cell, so nothing
   outside the cell counts.

Re-commissioned: **13 of 13 plants caught, placebo clean, restore verified
byte-identical.** The harness also carries a **crash arm** — the checker is
deliberately broken and required to return 2, not 0 and not 1 — because a
checker that dies and a checker that passes must never produce the same verdict.

## 9. Falsifying the fix before it ships

ORCH commissioned this lane to try to kill a **response-relative tolerance**
replacing an **absolute tolerance of 0.086063 response units**. The first thing
to report is that neither of those exists on the path that rendered the corpus.

### 9.1 The fix is aimed at the wrong module, again

`0.086063`, `FOCUS_NOISE_SD` and the whole focus-response tolerance occur
**zero times** in `pyramid.rs`, which is the shipping merge. The three hits for
the word `tolerance` in that file are assertion tolerances in unit tests. The
shipping selection, at `9b05d0b7:crates/strehl-core/src/pyramid.rs` lines
1351-1362 and 2092-2110, is:

```
floor  = gate * beta_k * var                       gate = 2.0
excess = max(smoothed L^2 - floor, 0)
w      = (excess / max(floor, 1) / SNR_REF)^p      SNR_REF = 64
```

**The shipping threshold is already relative** — it is a signal-to-noise ratio
against the locally modelled noise floor, raised to a per-band exponent. There
is no absolute constant to rescale. A response-relative tolerance would change
the `--merge` estimator path, which the provenance of all 26 masters lists
under `not applied`, and would leave every delivered image byte-identical.

This is the same class of error as the `softgate.rs` one in section 8, one
level down, and it is worth naming precisely: **the estimator path and the
pyramid path both contain something called a gate, and they are different
gates.** The disambiguating evidence is the binary's own self-report, which
names `--merge pyramid; THE DEFAULT PATH` and prints `noise gate : 2.00 x the
modelled band-noise power`.

**The knob that does exist** is the selection exponent, and `pyramid.rs` says
so itself, quantified, in the doc comment on `Hull`:

> The rate is driven by the selection exponent, not the gate: 0 violations at
> exponent ≤ 1, 72 at exponent 8, 511 at 16. The shipped per-band ramp is
> `2 3 4 5 8 8 8`, so **the three finest bands sit exactly where this turns
> severe**.

and it gives the structural reason a merge can be worse than its own inputs:

> **each band computes its own weight field**. Band 0 may be dominated by frame
> 12 while band 5 is dominated by frame 80, and a sum of convex combinations
> taken under *different* weightings is not a convex combination of the
> original pixels. Per-band convexity is true and does not imply reconstruction
> convexity.

So the counterfactual below is run on the exponent, not on a tolerance.

### 9.2 The instrument, and what it had to guess

`vn_pyr.py` reimplements the shipping merge offline in Python from the pinned
source: binomial `[1,4,6,4,1]/16` kernel, Laplacian pyramid of green luma,
`sq = smooth5(L^2)`, Gaussian pyramid of the variance, the weight above, base
band a plain mean, unweighted-mean fallback where nothing clears the floor, and
the `Hull::InputRange` clamp to the per-pixel range of the inputs.

`beta_k` is **not** guessed — it is taken from the binary's own self-report
(`0.8898 0.0529 0.0101 0.0024 0.0006 0.0001 0.0000 0.0000`, finest first).

**The one guess is the calibrated noise variance**, which is not in the crate.
It is fitted by photon transfer from the frames. Its sensitivity is measured
rather than assumed, and the ranking below survives a 4x sweep of it.

Fidelity, measured three ways: a constant survives smooth/reduce/expand exactly,
the pyramid reconstructs its input to `<1e-6 DN`, and a single-frame merge is
the identity. Then the strongest check available — **the reimplementation
reproduces the shipped result**: it scores `coffee-bubbles` at **1.354x** the
best source frame where the actual shipped master scores **1.444x**, a 6%
agreement between an independent Python reimplementation and the Rust binary.

### 9.3 Two defects I planted nothing to find, and found anyway

Both were caught by commissioning arms failing, and both would have produced
confident wrong numbers.

**The expand border bug.** `expand` was `4 * smooth5(zero_inserted)`, which is
exact in the interior and wrong at the border, because `mode="nearest"`
replicates the edge sample of the zero-inserted lattice and destroys the
even/odd tap balance. Expanding a constant `1200` gave interior std `0.0000`
but **min 300, max 2700, overall std 61.87**. That border ring then dominated
the finest Laplacian level, so the sharpness statistic moved **0.94x under a
sigma=5 blur** when it should have collapsed. My own self-test missed it
because it asserted only that `expand` preserved the **mean** of a constant —
and a spatially varying error with zero mean passes a mean test. Fixed by
normalising by the identically-smoothed lattice mask; sharpness now falls
**63x** under that blur, and every shape assertion checks spread as well as
level.

**The unphysical noise fit.** The first photon-transfer fit returned
`var = 10354.9 - 3.6972*S`, a **negative photon gain**. Shot noise cannot fall
with signal. The cause is that bright bins on this subject are bright because
they contain sharp detail, so a median `|L0|` there measures structure. A
negative slope drives `floor` to its clamp at bright pixels and makes every
weight there extreme. Fixed with a low quantile per bin and a non-negativity
constraint, and the harness now refuses outright rather than reporting.

### 9.4 The plateau structure is REAL, and it sits in the 20-60 px band

Winner field and `n_eff` per level, `coffee-bubbles`, all 19 frames, shipping
configuration. `level_px` is the native size of one cell at that level.

| level | cell px | exponent | mean `n_eff` | median | frac single-winner | median plateau | **frac area 20-60 px** |
|---|---:|---:|---:|---:|---:|---:|---:|
| L0 | 1 | 8.00 | 17.75 | 19.00 | 0.065 | 1.7 px | 0.000 |
| L1 | 2 | 8.00 | 1.36 | 1.16 | **0.680** | 3.5 px | 0.026 |
| L2 | 4 | 7.68 | 1.79 | 1.53 | 0.488 | 6.9 px | 0.276 |
| L3 | 8 | 5.49 | 2.42 | 2.02 | 0.371 | 13.9 px | **0.543** |
| L4 | 16 | 3.92 | 3.59 | 2.17 | 0.358 | 32.0 px | **0.365** |
| L5 | 32 | 2.80 | 5.34 | 2.86 | 0.195 | 64.0 px | 0.112 |
| L6 | 64 | 2.00 | 8.50 | 6.66 | 0.018 | 110.9 px | 0.000 |

**Answering ORCH's question directly: yes.** At L3, **54.3%** of the frame's
area sits in winner-plateaus of 20-60 px diameter, and 37.1% of coefficients
have effectively a single winner. At L4 it is 36.5%. The plateau structure is
concentrated exactly where the blotch convictions live.

Note the shape of `n_eff` across the ramp, because it corrects section 8.4's
borrowed account. `n_eff` is **not** monotone in response — it is **lowest at
L1-L4 and high at both ends**. L0 averages 17.75 of 19 frames because almost
nothing clears the noise floor at 1 px; L6 averages 8.50 because its exponent
is 2.0. The election happens in the middle, and it is the **exponent ramp**
that puts it there. This is a different mechanism from M111's absolute-tolerance
collapse, it is on the shipping path, and it is measured here rather than cited.

### 9.5 The counterfactual, with sharpness on the same pixels

Every row is the same 19 frames, the same tile, the same statistics.

| arm | blotch | **vs best source** | sharpness | **vs best source** |
|---|---:|---:|---:|---:|
| a. shipping (`2 3 4 5 8 8 8`) | 0.06716 | **1.354x** | 0.06905 | 0.755 |
| b. plain unweighted mean | 0.04874 | **0.983x** | 0.01986 | **0.217** |
| c. exponent 1, flat ramp | 0.05714 | **1.152x** | 0.06269 | 0.685 |
| d. exponent 2, no ramp | 0.06479 | 1.306x | 0.06561 | 0.717 |
| *the shipped master itself* | 0.07165 | *1.444x* | — | — |

**Arm (b) is the trap, and it is inadmissible.** A plain mean satisfies the
never-worse invariant outright — 0.983x, the only arm that does — and destroys
**78% of the sharpness**. That is the exact trade ORCH measured in
`focus-stack` at 0.077 fine grain and called "not a clean image, a smoothed
one". An independent reimplementation reproduces that failure mode here, which
is the strongest possible argument for carrying sharpness alongside every
blotch number: **on blotch alone, the worst arm wins.**

**Arm (c) is the real candidate.** Dropping the exponent to 1 removes
`(1.354 - 1.152) / (1.354 - 1.000)` = **57%** of the merge-attributable excess
for a **9.3%** relative sharpness cost (0.685 vs 0.755).

The guessed noise model does not carry this result:

| variance scale | shipping | exponent 1 | |
|---|---:|---:|---|
| x0.5 | 1.327x | 1.141x | exp-1 lower |
| x1.0 | 1.354x | 1.152x | exp-1 lower |
| x2.0 | 1.355x | 1.135x | exp-1 lower |

### 9.6 The ceiling, measured on three subjects, and it collapses as the stack deepens

The first report gave 57% from `coffee-bubbles` alone and refused to call it a
corpus number. Two more subjects from V-GATHER's convicted five now exist, and
the refusal was justified: **57% is the best case, it is the shallowest stack,
and the figure falls to 9% on the deepest one.**

| subject | OK frames | shipping | plain mean | exponent 1 flat | shipped master |
|---|---:|---:|---:|---:|---:|
| `coffee-bubbles` | 19 | 1.354x | **0.983x** | 1.152x | 1.444x |
| `112MSDCF` | 79 | 1.122x | **1.053x** | 1.099x | 1.260x |
| `flat-on-ruler-cpl` | 73 | 1.287x | **1.229x** | 1.261x | 1.297x |

Two derived quantities follow from those columns. The first is how much of the
excess is attributable to selection **at all** -- the gap from shipping to the
plain mean, which performs no selection whatsoever. The second is how much of
it the exponent knob can actually reach.

| subject | selection-attributable, at most | reachable by the exponent | sharpness cost of doing so |
|---|---:|---:|---:|
| `coffee-bubbles` | 104.9% | **57.1%** | 9.2% |
| `112MSDCF` | 56.3% | **19.1%** | 25.3% |
| `flat-on-ruler-cpl` | 20.3% | **9.1%** | 30.2% |

**The benefit falls and the cost rises, in the same direction, across all
three.** Flattening the exponent buys 57% of the excess for a 9% sharpness loss
on the 19-frame stack, and 9% of the excess for a 30% sharpness loss on the
73-frame one. That is the trade going the wrong way exactly where the tool is
supposed to earn its keep: deep stacks are what a focus stacker is for.

**Predicted ceiling for the corpus: about a fifth, not most of it.** The median
of the three is 19.1%. I will not give a frame-weighted corpus number from
three subjects, but the direction is consistent and it is the wrong direction
for the fix under test.

### 9.7 The plain mean still violates on 2 of 3, so a selection-independent floor exists

This is the finding that decides the question, and it does not depend on any
reimplementation detail of the gate.

**Arm (b) deletes the selection entirely** -- a plain unweighted mean over every
admitted frame, no weights, no exponent, no gate, nothing to mis-scale. On
`112MSDCF` it reads **1.053x** and on `flat-on-ruler-cpl` **1.229x**. Both are
violations of the invariant.

A merge with no selection in it cannot have a selection artifact. Therefore on
those two subjects **most of the blotch excess is not caused by the selection
rule, and no change to the selection rule -- exponent, tolerance, gate, or
weighting -- can remove it.** On `flat-on-ruler-cpl`, deleting selection
altogether removes 20.3% of the excess and **79.7% survives**.

What the floor is instead: both surviving subjects are deep sweeps whose
registration correlation against the master runs from 0.973 up to 0.9999 and
back down to 0.970 (`112MSDCF`) and 0.990 (`flat-on-ruler-cpl`). Averaging
frames across a focus sweep sums defocus halos, and a defocus halo is
mid-scale structure by construction. `blotch` is band-limited to 50-400 px and
divided by the mean, so it reads that halo as mottle. No single frame contains
it, because no single frame is an average. This is the same "charged for
structure no single frame contains" account that covered 20 of 24 subjects in
section 6, arriving through a different door -- and here it is demonstrated by
construction rather than argued, because the arm that isolates it is a plain
mean.

`coffee-bubbles` is the exception and it is the shallowest stack: its plain
mean reads 0.983x and **satisfies** the invariant. So the selection story is
true where the stack is shallow and false where it is deep.

### 9.8 Verdict on the prediction ORCH stated

ORCH set the test in falsifiable form: the fix should (a) break up the plateau
structure, (b) reduce the mid-scale excess on the convicted subjects, and (c)
leave fine grain and sharpness substantially unchanged -- and "if (a) happens
and (b) does not, the plateau story is wrong".

**(a) CONFIRMED.** The plateau structure is real, on all three subjects, and it
sits at the scales where the convictions live. Fraction of frame area in
connected winner-regions of 20-60 px diameter, by pyramid level:

| subject | L0 | L1 | L2 | L3 | L4 | L5 | L6 | L3+L4 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `coffee-bubbles` | 0.000 | 0.026 | 0.276 | 0.543 | 0.365 | 0.112 | 0.000 | **0.908** |
| `112MSDCF` | 0.002 | 0.017 | 0.125 | 0.460 | 0.669 | 0.354 | 0.000 | **1.129** |
| `flat-on-ruler-cpl` | 0.156 | 0.083 | 0.154 | 0.366 | 0.327 | 0.215 | 0.000 | **0.693** |

**(b) HAPPENS, BUT WEAKLY, AND IT SHRINKS WITH STACK DEPTH.** 57% / 19% / 9%.
On two of three subjects the excess that survives the change is larger than the
excess it removes, and on all three the result remains a violation: arm (c)
leaves 1.152x, 1.099x and 1.261x.

**(c) FAILS.** Sharpness on the same pixels falls 9.2%, 25.3% and 30.2%
relative to the shipping arm. On the two deep stacks that is a quarter to a
third of the resolved detail, paid for a single-digit-to-19% reduction in a
statistic that arm (b) shows is mostly not caused by selection at all.

By ORCH's own stated rule the plateau story is not refuted -- (b) does happen --
but it is **demoted from mechanism to contributing term**, and the fix under
test is not sufficient. The honest summary is: the plateaus are real, they are
mid-scale, they cost something, and they are the smaller half of the problem on
every subject except the shallowest.

**What this means for the build lane:** shipping the response-relative
tolerance will not deliver the invariant on `112MSDCF` or `flat-on-ruler-cpl`,
because the plain mean does not deliver it either. If the tolerance change also
sharpens the election it will cost resolved detail on exactly the deep stacks
where it buys least. This is the trade ORCH warned about with `focus-stack`,
and arm (b) is the extreme case of it in our own code: **the plain mean is the
only arm anywhere in this work that satisfies the invariant on `coffee-bubbles`,
and it destroys 78% / 87% / 92% of the sharpness relative to the best source
frame.**

| sharpness vs best source frame | shipping | plain mean | exponent 1 flat |
|---|---:|---:|---:|
| `coffee-bubbles` | 0.755 | **0.217** | 0.685 |
| `112MSDCF` | 1.814 | **0.131** | 1.355 |
| `flat-on-ruler-cpl` | 1.328 | **0.085** | 0.927 |

Note the shipping row: on `112MSDCF` and `flat-on-ruler-cpl` the merge is
**1.814x and 1.328x sharper** than the best single frame that went into it.
That is the positive half of the quality claim showing up in this lane's own
instrument, and it is what arm (b) throws away.

### 9.9 A third instrument defect, caught by the refusal path

`flat-on-ruler-cpl` is the first subject in this lane whose stack contains
frames that failed registration, and it broke the driver:

    79 in the stack = 73 OK + 5 UNREGISTERED + 1 POOR-REG

The bundle builder writes POOR-REG frames into the bundle; only UNREGISTERED
frames are omitted. The driver selected source frames by array-key prefix
rather than by state, so it read 74 frames, and the POOR-REG frame (`b0003`,
registration correlation `-4.7e-08`) scores `blotch` **exactly 0.0**. The
"best source frame" is a minimum, so the run divided by zero.

It exited **rc=2, REFUSED**, printing no ratio. That is the behaviour the crash
arm exists to guarantee: a checker that dies and a checker that passes must not
produce the same verdict. Had the degenerate frame scored `0.001` instead of
`0.0` there would have been no exception and the run would have reported a
plausible, badly wrong number -- so the fix is two parts, not one:

1. select source frames by `state == "OK"`, not by key prefix; and
2. **refuse explicitly** if any admitted frame scores zero on either statistic,
   rather than letting an infinite excess arrive as a float.

Part 2 is the one that matters, because part 1 alone would have gone green.

Regression evidence that the fix changed nothing else: re-running
`coffee-bubbles` after the change leaves `arms`, `plateaus`, `shipped_master`,
`exponents`, `noise_fit`, `varscale` and `frames` **identical**, and the only
delta is two new accounting keys in `source`. The memory refactor made in the
same session to let the merge run at 79 frames (aliasing the luma pyramid
instead of recomputing it, and a running min/max hull instead of an n-frame
stack) was verified the same way and is **bit-identical**, SHA256
`A126EB683147412ADD1DF8FD9B1335F08778F23529DFDDCD58D5057BC62613A8`.

### 9.10 What I did not measure

| item | status |
|---|---|
| plateau structure, 3 subjects, every OK frame | **measured** |
| counterfactual arms with paired sharpness, 3 subjects | **measured**, 4 arms each |
| sensitivity to the guessed noise model, 3 subjects | **measured**, 4x sweep |
| plateau structure on the other 3 of V-GATHER's five | **NOT MEASURED** |
| shared-weight-field counterfactual | **NOT MEASURED** |
| corpus-wide ceiling | **REFUSED** -- three subjects cannot support it |

Partition, subjects: **3 requested = 3 measured + 0 not attempted + 0 failed.**
Partition, frames on the subject that lost some: **79 in the stack = 73
admitted + 5 unregistered + 1 poor-registration.**

Two scope limits stand. **`flat-on-ruler-cpl`'s minimum is taken over 73 of 79
frames**, so by this lane's standing correction its 1.287x is a **lower bound**
on the true excess, and so is the 20.3% selection-attributable share derived
from it. And the noise model is still fitted rather than read from the code:
the two new subjects recovered a positive photon gain (`180.1 + 1.6498*S` and
`1.0 + 0.3699*S` DN^2), which `coffee-bubbles` did not, so the zero-gain fit
there remains this lane's weakest input -- covered, but not removed, by the
4x sweep.

### 9.11 ASK 1 -- `SNR_REF` does NOT cancel, and the source says it does

ORCH asked me to settle whether `SNR_REF = 64.0` cancels in the normalised
weight `w_i / sum_j w_j`, believing it does and that it is therefore an
overflow guard rather than a threshold. **It does not cancel. The belief is
correct about intent and wrong about effect, and the file states the wrong
one as fact.**

The algebra first, because it says exactly where the belief comes from.
Without the clamp, `w_i = (r_i / S)^p = r_i^p * S^-p`, and `S^-p` is common to
every frame at a level, so it divides out of the normalised weight exactly.
`pyramid.rs:2055-2059` says so in as many words: *"since every weight at a
level is divided by the same constant, the merge is mathematically unchanged
by it"*. That is true of the expression as written in the comment. It is not
true of the code beneath it, because `select_weight` clamps the log-domain
product to +/-80 before exponentiating, and **a clamp does not commute with a
scaling**. `pyramid.rs:2092` calls that clamp *"an overflow guard that never
binds in practice"*.

Measured on `coffee-bubbles`, 19 frames, shipping configuration:

| `SNR_REF` | fraction of coefficients where the clamp binds | max abs pixel change | max abs change in normalised weight |
|---|---:|---:|---:|
| 64.0 (shipping) | 0.002793 | 0 (reference) | 0 |
| 1.0 | 0.000041 | **606.3 DN** | **0.4666** |
| 4096.0 | 0.163599 | **1060 DN** | 0.8075 |

The clamp binds on **1 coefficient in 358** at the shipping value, not never.
A 606 DN pixel change on a 16-bit image is not a rounding artefact.

**Which end binds, and what it does.** `|p * ln r| > 80` at `p = 8` needs
`r < 4.5e-05`, i.e. `excess / floor < 0.0029`. The clamp therefore binds at
the **low** end, on coefficients barely above the noise floor. Every such
coefficient floors to `exp(-80) = 1.8e-35` and they all become **equal**, so
the merge averages them instead of ranking them. That is the opposite of the
overflow the comment describes, and its effect is benign in isolation --
averaging is the right thing to do down there. It is still an undocumented
behavioural switch sitting in a constant the file describes as inert.

**Commissioning, both directions.** The claim "changing `SNR_REF` changes
nothing" is a null result, and a null result from a blind instrument looks
identical to a null result from a sound one. So the run carries a **positive
control**: with the clamp bound forced from 80 to 1.0, so that it binds on
0.995 of coefficients, the same comparison reads **max abs pixel change
1236**. The instrument can see a difference when there is one. The **null
control**, rerunning the identical `SNR_REF`, reads **exactly 0**.

**Does this change the diagnosis? No.** `SNR_REF` is not a selectivity
threshold and is not the mottle mechanism. Reported because the file's own
description of it is contradicted on real data, and because a lane that reads
those two comments and reasons from them will reason wrongly, which is the
same trap that cost this project three re-aims tonight.

### 9.12 ASK 2 -- the weights are concentrated, but the field is COHERENT, not a patchwork

ORCH's stated mechanism was that at `p ~ 5.5` the per-pixel choice is
"chosen independently per pixel", producing "a spatially incoherent patchwork
at the scale of a pyramid band". Measured at level 3 on `coffee-bubbles`,
stratified by a through-focus flatness computed **from the source frames
without the gate**, so it cannot inherit the gate's own decisions:

| stratum | pixels | `n_eff` | mean top weight | fraction single-winner |
|---|---:|---:|---:|---:|
| 0 (most structured) | 2554 | 2.50 | 0.652 | 0.256 |
| 1 | 2554 | 2.54 | 0.646 | 0.244 |
| 2 | 2553 | 2.45 | 0.669 | 0.293 |
| 3 | 2554 | 2.32 | 0.690 | 0.309 |
| 4 (flattest) | 2554 | **2.28** | 0.695 | **0.316** |

The weights **are** concentrated: `n_eff` around 2.4 out of 19 frames, and a
top weight near 0.67. So the "already close to winner-take-all" half of
ORCH's reading is confirmed. The **flatness dependence is real but far too
small to be a mechanism**: `n_eff` moves 2.50 to 2.28 across the whole range,
a 9% change, and the single-winner fraction 25.6% to 31.6%.

The "incoherent" half is **refuted**:

| | 4-neighbour agreement | chance from marginals | excess | admitted pixels |
|---|---:|---:|---:|---:|
| shipping merge | 0.6385 | 0.0717 | **+0.5668** | 1.000 |
| null: same scene, no focus signal | 0.4928 | 0.0535 | +0.4392 | 0.992 |
| **attributable to real focus differences** | | | **+0.1275** | |

64% of neighbouring pixels choose the same frame where chance is 7%. The
winner field is not a patchwork, it is a **plateau field**, consistent with
the median plateau diameter of 13.9 px measured independently in section 9.4.

**The null is what makes that number mean anything, and it moved it a long
way.** `sq = smooth5(lap^2)` mixes neighbouring coefficients before the
selection ever sees them, so adjacent pixels share input and their winners
would agree even with nothing to agree about. The null keeps the scene, so
the gate admits at the same rate, and destroys only the between-frame focus
signal: every frame becomes the mean image plus independent noise at the
fitted level. **77.5% of the coherence excess survives that**, so it is
manufactured by the pipeline rather than found in the subject. The honest
figure attributable to real focus differences is **+0.1275, not +0.5668**.

### 9.13 ASK 3 -- the confidence-dependent exponent, measured before it ships

ORCH described the fix in words, not code, and the build lane's constants do
not exist yet, so I implemented the most defensible reading and then swept its
one free parameter, so that the conclusion does not rest on my choice of it:

    confidence c = 1 - exp(-kappa * spread / sd_est)
    p_eff        = p_lo + (p - p_lo) * c

with `spread` the range of smoothed band energies across frames and `sd_est`
their own estimation noise, `sqrt(2/keff)` times the measured local mean band
energy, `keff = 1/(sum K^2)^2` for the separable 5-tap kernel. `p_lo = 1` is
ORCH's rule as stated. **Everything in that paragraph is a guess except the
endpoints**, which are pinned by commissioning:

| commissioning arm | requirement | measured |
|---|---|---:|
| `kappa = 0` reproduces the flat-exponent arm | exact identity | max abs pixel delta **0** |
| `kappa = inf` reproduces the shipping merge | exact identity | max abs pixel delta **0** |
| the two limits are not the same image | must be large | **1720 DN** apart |

Both limits are **exact**, not approximate, which is why the sweep between
them can be read as the fix's whole reachable range rather than as one guess
about it.

**The result: the fix reaches no point that the existing scalar knobs do not.**

| arm | knob | blotch vs best source | sharpness vs best source | vs scalar frontier |
|---|---|---:|---:|---:|
| scalar | `exponent` 2.0 (shipping) | 1.354x | 0.755x | -- |
| scalar | `exponent` 1.8 | 1.332x | 0.757x | -- |
| scalar | `exponent` 1.6 | 1.305x | 0.756x | -- |
| scalar | `exponent` 1.4 | 1.265x | 0.749x | -- |
| scalar | `exponent` 1.2 | 1.214x | 0.725x | -- |
| scalar | `exponent` 1.0 | 1.152x | 0.685x | -- |
| confidence | `kappa` 0.005 | 1.196x | 0.709x | **-0.0067** |
| confidence | `kappa` 0.010 | 1.219x | 0.720x | **-0.0113** |
| confidence | `kappa` 0.050 | 1.286x | 0.746x | **-0.0282** |
| confidence | `kappa` 0.100 | 1.313x | 0.752x | +0.0008 |
| confidence | `kappa` 0.500 | 1.348x | 0.755x | +0.0033 |
| confidence | `kappa` 1.000 | 1.352x | 0.755x | +0.0007 |

The last column is the blotch of the scalar frontier interpolated to the same
sharpness, minus the confidence arm's blotch. Positive means the fix bought
something no scalar buys. **The largest gain anywhere is +0.0033 blotch, and
three of the six points are strictly worse than simply turning `exponent`
down.** On this subject the confidence rule is a more complicated way to
reach a curve that already exists.

**The oracle bound, which makes that implementation-independent.** My
implementation is one reading of ORCH's words; the build lane's will differ.
So I also measured an oracle that chooses, per pixel and **in image space
with both finished reconstructions in hand**, whether to take the shipping or
the flat-exponent result. It is strictly stronger than any confidence rule,
which must decide per band from noisy evidence:

| oracle, fraction of frame flattened | blotch | sharpness |
|---:|---:|---:|
| 0.10 | 1.288x | 0.723x |
| 0.25 | 1.253x | 0.734x |
| 0.50 | 1.210x | 0.741x |
| 0.75 | 1.177x | 0.729x |
| 0.90 | **1.160x** | 0.708x |

**Commissioned:** an oracle that did not dominate the scalar frontier would
not bound anything, and the run refuses if it does not. It dominates by
**+0.0478** blotch at matched sharpness.

| | blotch | share of the excess over 1.000x removed |
|---|---:|---:|
| shipping | 1.354x | -- |
| best confidence arm | 1.196x | **44.6%** |
| **oracle, any per-pixel exponent rule** | **1.160x** | **54.8%** |

**Even the oracle still violates the never-worse bound.** No per-pixel
exponent rule clears `coffee-bubbles`, whatever the build lane writes.

### 9.14 The decisive experiment -- a stack with nothing to resolve

Every blotch conviction in this document has one standing defence: that the
merge is being charged for resolved structure no single frame contains. On
real data that defence is untestable, because real frames really do differ in
focus. **This removes it by construction.**

Build a stack whose frames carry identical scene content and differ only by
independent noise at the fitted sensor level. No frame is better focused than
any other. There is nothing to resolve and nothing the merge can legitimately
add. Measure the **residual against the known base**, so the scene's own
mid-band content -- common to every arm -- cannot dominate the statistic.

**Commissioning, both directions.** A null that is not null would make any
excess legitimate and collapse the whole argument, so the construction is
checked in three ways:

| arm | requirement | measured |
|---|---|---:|
| the null is null | sharpness spread across synthetic frames ~ 0 | **0.0026** of the mean |
| planted focus advantage on one frame | must be detected | **0.5752** |
| planted blur on one frame | must be detected | **1.0672** |

and the statistic carries a **positive control on its own sensitivity**:
averaging 19 independent noise fields must cut the band energy to
`1/sqrt(19) = 0.229x`, and the run **refuses** if the plain mean does not
read that. It reads **0.249x**.

| arm | band (50-400 px) | fine | band vs best frame | fine vs best frame |
|---|---:|---:|---:|---:|
| shipping, as delivered | 2.08466 | 99.46558 | **1.840x** | 1.149x |
| exponent ladder alone, no admission gate | 1.79285 | 102.71260 | 1.582x | 1.186x |
| flat exponent, `p = 1` everywhere | 1.61676 | 98.68014 | 1.427x | 1.140x |
| confidence rule collapsing to `p = 1` | 1.66444 | 99.27505 | 1.469x | 1.147x |
| confidence rule collapsing to a true average | 1.49007 | 97.07336 | 1.315x | 1.121x |
| hard admission threshold alone, uniform weights | 1.43264 | 96.06861 | 1.264x | 1.110x |
| plain unweighted mean | 0.28218 | 19.86664 | **0.249x** | 0.229x |

**The shipping merge reads 1.840x the best frame it was built from, at mid
scale, on a stack where every frame is the same image.** That excess cannot
be resolved detail. It is manufactured. Against the plain mean the
manufacture factor is **7.39x**.

**Attribution, and this is the part that decides the fix.** Two noise-driven
decisions are stacked in this merge: **which** frames are admitted
(`excess = max(sq - floor, 0)` is a hard per-pixel threshold) and **how** they
are weighted once admitted (the exponent ladder). Turning each off separately:

| mechanism left running alone | band vs best frame | share of the excess over a plain mean |
|---|---:|---:|
| hard admission threshold only | 1.264x | **63.8%** |
| exponent ladder only | 1.582x | **83.8%** |

Those do not sum to 100%; they sum to 148%. **The two mechanisms are
redundant, not complementary.** Either one alone reproduces most of the
defect, so removing one alone leaves most of it standing. The exponent fix's
best case -- flat `p = 1` everywhere, which is more than the build lane
intends -- removes **26.0%**.

**The predicted ceiling ORCH asked for is therefore about a quarter, not
most, and there is a second mechanism.** It is the admission threshold, and
it is in the same file. A confidence rule applied only to the exponent will
land near 1.5x on this null. A confidence rule that also collapses to a
**true average** rather than to `p = 1` reads 1.315x, better but still six
times the mean's 0.249x, because the admission decision it leaves in place is
itself noise-driven.

**Sharpness on the same pixels, as required.** The fine column is the price
list. The plain mean reads **0.229x** of the best frame's fine grain -- it is
the cleanest arm at mid scale and by far the most destroyed at fine scale,
exactly the trade ORCH measured `focus-stack` taking at 0.077 and 0.260. Every
other arm sits between 1.110x and 1.186x, so on this null the mechanisms cost
essentially nothing in fine grain and buy nothing either: they are moving
noise from fine scales to mid scales, which is the worst direction available,
because mid-scale noise is what the eye reads as mottle.

### 9.14b The same on a second subject, and it gets worse with depth

`112MSDCF`, 79 frames, identical construction. Commissioned the same way:
the synthetic frames' sharpness spread is **0.0020** of the mean, a planted
focus advantage reads **2.0293** and a planted blur reads **1.0585**, so the
null is null and the check that says so can fail. The sensitivity control
passes: 79 averaged noise fields must read `1/sqrt(79) = 0.113x` and the
plain mean reads **0.115x**.

| arm | band (50-400 px) | fine | band vs best frame | fine vs best frame |
|---|---:|---:|---:|---:|
| shipping, as delivered | 1.06870 | 45.85142 | **3.160x** | 1.755x |
| exponent ladder alone, no admission gate | 0.94974 | 30.14141 | 2.808x | 1.153x |
| flat exponent, `p = 1` everywhere | 0.71432 | 40.34111 | 2.112x | 1.544x |
| confidence rule collapsing to `p = 1` | 0.76195 | 41.68305 | 2.253x | 1.595x |
| confidence rule collapsing to a true average | 0.61526 | 37.84826 | 1.819x | 1.448x |
| hard admission threshold alone, uniform weights | 0.54652 | 35.85899 | 1.616x | 1.372x |
| plain unweighted mean | 0.03892 | 2.93397 | **0.115x** | 0.112x |

| mechanism left running alone | band vs best frame | share of the excess over a plain mean |
|---|---:|---:|
| hard admission threshold only, 79 frames | 1.616x | **49.3%** |
| exponent ladder only, 79 frames | 2.808x | **88.4%** |

Every conclusion from section 9.14 reproduces. The shares again exceed 100%,
at 138%, so the two mechanisms are again redundant. The exponent fix's best
case removes **34.4%**.

**And one new thing, which is the worst number in this document.** The
manufacture factor -- shipping divided by the plain mean on a stack with
nothing to resolve -- is **7.39x on 19 frames and 27.46x on 79**. It rises
with stack depth. A plain mean improves as `1/sqrt(n)`; the shipping merge
does not follow it down, so the gap widens with every frame added. **Giving
this merge more frames buys more mottle relative to what those frames could
have given you.** That is the opposite of the property a stacker is for, and
it is consistent with section 9.6's independent finding on real data that the
selection-attributable share collapses as stacks deepen -- the same effect
seen from the other side.

---

### 9.15 Two more instrument defects, both caught by controls I nearly did not write

**The synthetic null measured the wrong quantity, and the `sqrt(n)` control
caught it.** The first version scored the merged image rather than the
residual. Every arm shares the same base, whose mid-band content is large, so
the statistic read **1.001x for shipping, 1.006x for the plain mean and
1.001x for the flat exponent** -- three arms indistinguishable, and a clean
acquittal of the merge. The `1/sqrt(19) = 0.229x` expectation is what showed
it was wrong: 19 averaged noise fields **cannot** read 1.006x. Scoring the
residual instead, the same arms read 1.840x, 0.249x and 1.427x. **A
responsiveness control is the only thing standing between "no effect" and "no
sensitivity", and those two produce the same three-digit number.**

**The coherence null was contaminated by abstention.** The first null used
pure noise with no scene. Nothing cleared the admission floor, so every weight
was zero, and `argmax` of an all-zero column returns frame 0 by convention --
not by selection. The null read **0.6023 agreement against a chance of
0.2784**, which would have destroyed the finding it was written to protect.
The marginal chance level was the tell: 19 symmetric frames must give
`1/19 = 0.053`, and 0.2784 means about 3.6 frames were winning everything.
Fixed by masking to pixels where some frame is actually admitted, and by
building the null from the real scene so that admission behaves the same way.
The corrected null reads 0.4928 agreement, chance 0.0535, on 0.992 of pixels.

**Both are the same defect as the one ORCH named earlier tonight: an absence
of signal being read as a pass.** A statistic that cannot respond and a
statistic that responded with zero are the same glyph.

### 9.16 What I did not measure, this round

| item | status |
|---|---|
| `SNR_REF` cancellation, with positive and null controls | **measured** |
| weight concentration by flatness, gate-free stratification | **measured** |
| winner-field coherence with a like-for-like null | **measured** |
| the confidence-dependent exponent, swept, against a scalar frontier | **measured** |
| oracle bound on any per-pixel exponent rule | **measured** |
| synthetic null with a passing `sqrt(n)` sensitivity control | **measured** |
| attribution between admission and exponent | **measured** |
| the same on a second subject | **measured**, `112MSDCF` |
| the same on the remaining convicted subjects | **NOT MEASURED** |
| the build lane's actual implementation | **NOT MEASURED** -- it does not exist yet |
| chroma under any of these arms | **NOT MEASURED** -- BUILD-OUTPUT holds that half |

Partition, ORCH's asks: **4 requested = 4 measured + 0 refused + 0 failed.**
Partition, subjects for the manufacture test: **2 attempted = 2 measured +
0 refused + 0 failed.**

The standing qualifier applies unchanged: where a subject's best-source
minimum is taken over fewer frames than the stack holds, the ratio is a
**lower** bound on the true excess. It does not apply to section 9.14 at all,
because the synthetic stack has no dropped frames and no registration step.

---

### 9.17 ASK: does the confidence rule restore N-invariance? No -- and on the deeper subject it makes it worse

ORCH's softness lane measured, against a literally identical denominator,
that merging **63 frames is 0.114 softer at 0.30-0.35 cyc/px than merging 32
frames of the same focus range**. It measured the effect. Nobody had
demonstrated the cause, and ORCH was explicit that his account of it was an
inference from the arithmetic rather than a measurement.

**The construction.** Frames are decimated with `linspace(0, n-1, k)`, which
pins the first and last frame in every arm, so the focus range is identical by
construction rather than by intention. Every arm is merged from the same
in-memory arrays, with the same config, the same fitted noise model and the
same band betas.

**The gauge, measured rather than asserted.** The arms' mean output levels
span **6.196%** of the mean on `coffee-bubbles`, from **702.9** to **747.6
DN**, and **2.344%** on `112MSDCF` -- so the merge's photometric level is
itself N-dependent, which is a finding in its own right and would have
contaminated any raw spectral comparison. The statistic normalises each image
by its own `0.02-0.05 cyc/px` band power; applying the observed drift to one
arm moves the reading by **1.4e-16** and **2.08e-16** respectively. The arms
differ in N and in nothing the statistic can see.

**The statistic is commissioned in both directions**, because an N-invariance
test won by blurring would read perfectly invariant:

| arm | requirement | measured |
|---|---|---:|
| planted blur | 0.30-0.35 power must fall | **0.010x** |
| planted sharpening | must rise, or it cannot detect softening at all | **2.573x** |
| null rescore | identical image, identical reading | **0** |
| exposure immunity | a 1.75x common gain must not move it | **0** |
| noise twin, up | adding an equal noise field must raise raw power | **2.002x** |
| noise twin, down | smoothing the residual must lower it | **0.008x** |

**`coffee-bubbles`, 19 frames.** `n_eff` and `share` are measured at the top
decile of through-focus response -- real detail -- and each arm supplies its
own weights.

| arm | N | 0.10-0.15 | 0.20-0.25 | 0.30-0.35 | 0.40-0.45 | blotch | n_eff | share | SNR at 0.30-0.35 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| shipping | 19 | 0.0783 | 0.0117 | 0.0062 | 0.0033 | 0.06716 | 1.78 | 0.755 | **0.30** |
| shipping | 9 | 0.0975 | 0.0146 | 0.0063 | 0.0028 | 0.06231 | 1.40 | 0.853 | 0.37 |
| shipping | 4 | 0.1363 | 0.0235 | 0.0090 | 0.0032 | 0.05626 | 1.18 | 0.928 | **0.49** |
| confidence | 19 | 0.0805 | 0.0152 | 0.0092 | 0.0050 | 0.06048 | 7.38 | 0.289 | 0.32 |
| confidence | 9 | 0.1017 | 0.0173 | 0.0081 | 0.0037 | 0.05781 | 3.99 | 0.437 | 0.36 |
| confidence | 4 | 0.1494 | 0.0265 | 0.0105 | 0.0037 | 0.05448 | 2.10 | 0.663 | 0.48 |
| argmax | 19 | 0.0780 | 0.0119 | 0.0061 | 0.0033 | 0.07481 | 1.00 | 1.000 | 0.29 |
| argmax | 9 | 0.0964 | 0.0148 | 0.0062 | 0.0028 | 0.06760 | 1.00 | 1.000 | 0.36 |
| argmax | 4 | 0.1359 | 0.0236 | 0.0090 | 0.0032 | 0.05890 | 1.00 | 1.000 | 0.48 |
| mean | 19 | 0.0411 | 0.0149 | 0.0068 | 0.0020 | 0.04874 | 19.00 | 0.053 | 0.69 |
| mean | 9 | 0.0720 | 0.0326 | 0.0152 | 0.0046 | 0.04898 | 9.00 | 0.111 | 0.68 |
| mean | 4 | 0.1500 | 0.0697 | 0.0316 | 0.0096 | 0.04875 | 4.00 | 0.250 | 0.68 |

**`112MSDCF`, 79 frames** -- the arms at 79 and 39 bracket the softness lane's
63-against-32 comparison.

| arm | N | 0.10-0.15 | 0.20-0.25 | 0.30-0.35 | 0.40-0.45 | blotch | n_eff | share | SNR at 0.30-0.35 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| shipping | 79 | 0.1088 | 0.0308 | 0.0167 | 0.0092 | 0.21187 | 3.60 | 0.470 | **1.28** |
| shipping | 39 | 0.0997 | 0.0265 | 0.0131 | 0.0067 | 0.21362 | 2.32 | 0.624 | 1.37 |
| shipping | 19 | 0.0905 | 0.0219 | 0.0100 | 0.0048 | 0.21445 | 1.65 | 0.787 | **1.53** |
| confidence | 79 | 0.1168 | 0.0386 | 0.0210 | 0.0107 | 0.20721 | 19.22 | 0.142 | 1.21 |
| confidence | 39 | 0.1089 | 0.0357 | 0.0183 | 0.0090 | 0.20867 | 10.59 | 0.245 | 1.33 |
| confidence | 19 | 0.0988 | 0.0298 | 0.0144 | 0.0067 | 0.20986 | 6.00 | 0.401 | 1.53 |
| argmax | 79 | 0.1043 | 0.0286 | 0.0157 | 0.0090 | 0.22411 | 1.00 | 1.000 | 1.24 |
| argmax | 39 | 0.0965 | 0.0252 | 0.0123 | 0.0065 | 0.22487 | 1.00 | 1.000 | 1.32 |
| argmax | 19 | 0.0891 | 0.0215 | 0.0097 | 0.0047 | 0.22454 | 1.00 | 1.000 | 1.47 |
| mean | 79 | 0.0166 | 0.0038 | 0.0011 | 0.0003 | 0.19887 | 79.00 | 0.013 | 0.97 |
| mean | 39 | 0.0239 | 0.0075 | 0.0023 | 0.0006 | 0.19870 | 39.00 | 0.026 | 1.00 |
| mean | 19 | 0.0394 | 0.0154 | 0.0049 | 0.0013 | 0.19826 | 19.00 | 0.053 | 0.99 |

**The softness lane's effect reproduces, on two subjects it never touched,
with a different instrument.** Shipping's noise-corrected sharpness at
0.30-0.35 falls monotonically as frames are added: **0.49 -> 0.37 -> 0.30**
on `coffee-bubbles` and **1.53 -> 1.37 -> 1.28** on `112MSDCF`. Adding frames
makes the output softer.

**The noise twin earned its place immediately, and it flips signs.** On raw
band power, going deeper reads *sharper* on six of eight selective arm-pairs
-- shipping on `112MSDCF` reads **+0.281 sharper** at 79 frames than at 39.
Corrected against a twin stack carrying no focus signal at all, the same
comparison reads **-0.062 softer**.

| subject | arm | raw 0.30-0.35 ratio, deep vs half | noise-corrected |
|---|---|--:|--:|
| `coffee-bubbles` | shipping | 0.9892 | **0.8157** |
| `coffee-bubbles` | confidence | 1.1422 *(reads sharper)* | **0.8658** *(is softer)* |
| `coffee-bubbles` | argmax | 0.9799 | 0.8062 |
| `coffee-bubbles` | mean | 0.4452 | **1.0176** |
| `112MSDCF` | shipping | 1.2805 *(reads sharper)* | **0.9378** *(is softer)* |
| `112MSDCF` | confidence | 1.1494 *(reads sharper)* | **0.9100** *(is softer)* |
| `112MSDCF` | argmax | 1.2678 *(reads sharper)* | **0.9391** *(is softer)* |
| `112MSDCF` | mean | 0.4776 | 0.9677 |

Every arm that reads sharper with depth on raw power is softer with depth once
the manufactured noise is removed. **Any N-invariance claim made on an
uncorrected magnitude would have come out with the wrong sign.**

**The answer to the ask: the confidence rule does not restore N-invariance,
and on the deeper subject it is actively harmful.**

| subject | shipping softening | confidence softening | fix removes |
|---|--:|--:|--:|
| `coffee-bubbles`, 9 -> 19 | -0.1843 | -0.1342 | **27.2%** |
| `112MSDCF`, 39 -> 79 | -0.0622 | -0.0900 | **-44.6%** |

On the 19-frame subject it removes about a quarter of the softening, the same
order as the quarter it accounts for on the mottle in section 9.14. **On the
79-frame subject it makes the softening 45% worse.** The commercially
important stacks are the deep ones -- the owner's deepest capture is a
**299-frame** bee and `flower-bud-alone-cpl` at **N=205** is already refused
by the print gate -- and the deep subject is where this fix goes the wrong
way.

**And my own prediction was wrong.** I predicted the fix would read
*identical* to shipping at real detail, on the argument that `p_eff <= p`
always and `conf -> 1` where differences are significant. The premise is
false: at the top decile of focus response the fix runs at `n_eff` **7.38**
against shipping's **1.78** on `coffee-bubbles`, and **19.22** against
**3.60** on `112MSDCF`. It is nowhere near shipping even where the signal is
strongest. My conclusion -- that the fix would not restore N-invariance --
survived, but for a reason I had not measured, which is not a success. It is
the same error I have been reporting in others all night: reasoning from the
shape of the code to a number instead of measuring it.

### 9.18 ORCH's cause, tested rather than assumed -- refuted by a control it cannot survive

ORCH's account: `SoftPower` normalises `w_i / sum_j w_j`, so the winner's
share depends on how many frames are near-tied with it, that count grows with
N, the effective frame count inflates and the reconstruction drifts toward an
average.

**The first half of that is true.** The winner's share at real detail does
fall as N rises, in every arm that selects at all -- `x0.885` and `x0.753` for
shipping on the two subjects.

**The second half is refuted.** `argmax` is winner-take-all: its share is
exactly **1.000** and its `n_eff` exactly **1.000** at every N, verified to
`1e-9` before it is used as a control, so it has **no dilution to have**. If
dilution caused the softening, this arm could not soften.

| subject | arm | share, half -> deep | dilution | noise-corrected softening |
|---|---|--:|--:|--:|
| `coffee-bubbles` | argmax | 1.000 -> 1.000 | **none, by construction** | **-0.194** |
| `coffee-bubbles` | shipping | 0.853 -> 0.755 | x0.885 | -0.184 |
| `coffee-bubbles` | confidence | 0.437 -> 0.289 | x0.662 | -0.134 |
| `coffee-bubbles` | mean | 0.111 -> 0.053 | **x0.474, maximal** | **+0.018** |
| `112MSDCF` | argmax | 1.000 -> 1.000 | **none, by construction** | **-0.061** |
| `112MSDCF` | shipping | 0.624 -> 0.470 | x0.753 | -0.062 |
| `112MSDCF` | confidence | 0.245 -> 0.142 | x0.579 | -0.090 |
| `112MSDCF` | mean | 0.026 -> 0.013 | **x0.494, maximal** | **-0.032** |

**An arm with zero dilution softens 105% and 98% as much as shipping.**
Dilution is not necessary for the softening on either subject, so it is not
the cause. On both subjects the maximally diluting arm -- the plain mean --
softens **least** of all four.

**One thing that does not replicate, and I am reporting it as such.** On
`coffee-bubbles` the correlation across the four arms between dilution and
softening is **-0.929**, which reads as the hypothesis being contradicted in
sign. On `112MSDCF` it is only **-0.155**. The strong anti-correlation is a
one-subject result and should not be quoted as a corpus finding. **The
control, however, replicates exactly**: the no-dilution arm softens as much as
shipping on both. The refutation rests on the control, not on the
correlation.

### 9.19 What it is instead -- a merge that selects is charged for every frame it is given

The noise twin carries **no focus signal whatsoever**: identical scene
content, independent noise at the fitted sensor level. Any mid-band power in
its output was manufactured. Comparing the selecting arm against the averaging
arm on that twin isolates the price of selection with the scene held at
literally zero.

| subject | N | manufactured 0.30-0.35 noise power, selecting vs averaging |
|---|--:|--:|
| `coffee-bubbles` | 4 | **2.16x** |
| `coffee-bubbles` | 9 | **6.79x** |
| `coffee-bubbles` | 19 | **24.82x** |
| `112MSDCF` | 19 | **23.24x** |
| `112MSDCF` | 39 | **80.78x** |
| `112MSDCF` | 79 | **240.70x** |

Scaling with N, per arm, on the real subjects:

| subject | arm | signal power | noise power |
|---|---|--:|--:|
| `coffee-bubbles`, 4 -> 19 | shipping | x1.476 | **x2.419** |
| `coffee-bubbles`, 4 -> 19 | confidence | x1.546 | **x2.344** |
| `coffee-bubbles`, 4 -> 19 | argmax | x1.482 | **x2.468** |
| `coffee-bubbles`, 4 -> 19 | mean | x0.218 | x0.215 |

**For every arm that selects, noise grows about 1.6 times faster than signal
as frames are added. For the plain mean, signal and noise fall at the same
rate and the SNR is flat** -- 0.68, 0.68, 0.69 across the three depths. That
is the whole of the N-dependent softening, and it is not about shares.

Averaging cancels noise. Selecting *keeps the largest* noise, and the largest
of N draws grows with N. A merge that picks a winner per pixel per band is
charged for every extra candidate it is handed, **whether or not that
candidate carries any signal**. In a flat region no candidate does, which is
exactly the manufactured mid-scale structure convicted in section 9.14. In a
detailed region one candidate does, but the other N-1 still bid, and the noise
they inject dilutes the SNR of the detail that is there.

**One mechanism does produce both defects, as ORCH argued -- but not the
mechanism he named.** It is not the winner's share being diluted. It is
selection on a quantity that contains noise, over a candidate set that grows
with N. The two are opposites: dilution is averaging creeping in, and this is
selection biting harder.

**A note on what depth actually trades.** On `112MSDCF` shipping's blotch
barely moves with depth -- 0.21445 at N=19 against 0.21187 at N=79, slightly
*better* -- while its sharpness falls from 1.53 to 1.28. Adding frames on that
subject buys a rounding error of mottle and pays 16% of the mid-band signal
for it.

### 9.20 The pre-registered out-of-sample test -- and it refutes my own model

For N independent draws the mean has band power `~ 1/N` while the maximum has
`~ 2 ln N`, so the price of selecting rather than averaging should scale as
`2 N ln N`. On `coffee-bubbles` that looked right: the premium grew **11.48x**
from N=4 to N=19 against a predicted **10.09x**.

Fitting a model to the subject that suggested it proves nothing, so the
prediction for the next subject was written to disk **before that subject was
run**, by a script that refuses to write a prediction for a subject already
measured and refuses to overwrite one already written. Both refusals were
exercised and both returned `rc=2`.

Calibrated on `coffee-bubbles` at N=19 (`C = 0.22185`), the registered
prediction for `112MSDCF` at **N=79** was a selection premium of **153.2**,
declared **refuted** outside **102.1 to 229.7**, with predicted growth
**6.17x** from N=19 to N=79.

**Measured: 240.70. Growth 10.36x against a predicted 6.17x. The model is
refuted.**

The miss is only 4.8% outside the interval and it is in the direction that
makes the defect *worse* than predicted, both of which would make it easy to
wave through. It is a refutation and it is recorded as one. The interval was
chosen before the measurement and is not being widened after it.

**What survives and what does not.** The qualitative mechanism survives
untouched and is strengthened -- the premium is real, it is large, and it
grows steeply with N. What is refuted is my model of *how fast*. Descriptively
the two subjects give an empirical exponent of **N^1.566** and **N^1.640**,
against the `2 N ln N` model's effective **N^1.3** over this range. I am
labelling that as description, not prediction: it is fitted to the same two
subjects it describes, and it has not been tested on a third. **Anyone
extrapolating a 299-frame stack from these numbers is extrapolating a curve
that has already failed once.**

### 9.21 What this means for the fix, stated for the build lane

1. **N-invariance is a legitimate acceptance criterion and it is measurable
   offline.** The construction in this section pins the focus range by
   construction, proves the arms share a gauge to `1e-16`, and corrects for
   manufactured noise. Shipping today reads **-0.184** on a 19-frame subject
   and **-0.062** on a 79-frame one.
2. **The confidence-dependent exponent does not deliver it.** It removes 27%
   of the softening on the shallow subject and makes it **45% worse** on the
   deep one. It is aimed at the exponent, and the exponent is not what grows
   with N.
3. **The quantity that grows with N is the candidate count**, and nothing in
   the proposed rule is a function of N. A fix for this defect has to be: the
   selectivity has to fall as the candidate set grows, or the selection has to
   be made on a quantity whose noise has already been suppressed, or the
   losers have to be averaged rather than discarded.
4. **The plain mean is N-invariant and is not the answer.** Its SNR is flat in
   N -- the only arm here that is -- but section 9.14 already priced it at
   **0.229x** of the best frame's fine grain. It wins invariance by not
   resolving anything, which is exactly the `focus-stack` trade at 0.077 and
   0.260 that ORCH warned about. **Invariance is necessary, not sufficient,
   and it must be quoted with a sharpness number beside it or it is
   inadmissible.**

**Partition.** 2 subjects examined = 2 measured + 0 refused + 0 failed.
4 arms x 3 depths x 2 subjects = **24 arm-measurements attempted = 24
measured + 0 refused + 0 failed.** 1 pre-registered prediction = 0 confirmed
+ **1 refuted** + 0 unscored.

### 9.22 Instrument defects caught this round

Five. Four were caught by controls rather than by inspection, and the fifth was caught by the negative control after the verifier had already reported itself green.

1. **A gauge check that could not fail.** The first `gauge()` asserted that
   `frames[i]` equalled `frames[i]` -- true for any input whatsoever. It was
   replaced by three properties a real mistake would break: endpoints pinned,
   no repeats, indices in range. **A check that cannot fail is not evidence
   that nothing is wrong; it is the absence of a check wearing its clothes.**
2. **The fix's `n_eff` column silently repeated shipping's.** `detail_neff`
   recomputed the weights itself with a hardcoded shipping merge, so both arms
   were described by identical numbers and would have read as perfect
   agreement between the fix and the code it replaces. Weights are now passed
   in from the arm that produced the image.
3. **The photometric gate refused a finding instead of testing the
   statistic.** The first version aborted the run because the arms' mean
   levels differed by more than 2%. But the level drift with N is a *result*,
   and the question is whether the statistic can see it. Rewritten to apply
   the observed drift to one arm and measure the movement -- **1.4e-16**.
   **A refusal triggered by the answer is not a safety check.**
4. **Abstention contamination, the same defect as section 9.15, caught in
   advance this time.** `argmax` over an all-zero weight column returns frame
   0, which would have manufactured a fake unanimous winner in every
   unadmitted pixel and quietly broken the one control the whole refutation
   rests on. Both the merge and `detail_neff` now guard on `sum > 0`
   explicitly.
5. **A verifier check satisfied by a word it was not looking at.** The
   pre-registered verdict in section 9.20 was checked by testing whether
   "refuted" appeared anywhere in the section. It appears twice there
   legitimately, so a planted edit flipping the conclusion to **confirmed** --
   while leaving all four numbers untouched -- passed a full green run of 712
   checks. The negative control caught it; review did not. The check now
   *parses* the verdict word out of the sentence and compares it against the
   record's `survives` flag. **A presence test is satisfied by any duplicate
   of the thing it looks for, so a conclusion needs an anchor of its own --
   the same defect ORCH named in my duplicate `+8%` and the same one recorded
   in section 9.15.**

## 10. Files

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
| `vn_bubbles.py` | the 19-frame re-measurement, motion and tile statistics (§7.2, §7.3) |
| `vn_mech.py` | separates fine from mid-scale mechanisms; the decisive instrument (§7.3) |
| `vn_subsample.py` | measures which way subsampling moves the ratio (§7.1) |
| `vn_where.py` | spatial localisation — **refused**, five designs, see §7.5 |
| `vn_select.py` | select-or-blend recovery — **refused**, see §7.5 |
| `vn_diag_spec.py` | band step-profile spectrum; refuted my own box-kernel hypothesis (§7.3) |
| `vn_admit.py` | extracts the shipping admission record from all 26 provenance files (§8.2) |
| `vn_mechtest.py` | admission vs measured excess, commissioned both ways (§8.3) |
| `pin9b05/` | gate source at the BUILD commit, not HEAD — the source drifts (§8.1) |
| `vn_pyr.py` | offline reimplementation of the SHIPPING pyramid merge (§9.2) |
| `vn_plateau.py` | winner-field plateaus, counterfactual arms, sensitivity (§9.4-9.6) |
| `vn_bungauge.py` | proves the reused source bundle is not the sRGB master (§9.2) |
| `vn_snrref.py` | ASK 1 and ASK 2: `SNR_REF` cancellation with a positive control, weight concentration by flatness, winner-field coherence with a like-for-like null (S9.11, S9.12) |
| `vn_confexp.py` | the confidence-dependent exponent implemented offline, swept against a scalar frontier, with an oracle bound (S9.13) |
| `vn_manuf.py` | the synthetic null: a stack with nothing to resolve, and the attribution between admission and exponent (S9.14) |
| `vn_ninv.py` | N-invariance at matched focus range: the spectral statistic, the noise twin that separates sharper from noisier, the four bracketing arms and the selection premium (S9.17-S9.19) |
| `vn_prereg.py` | writes a prediction to disk for a subject not yet measured, and refuses to write one for a subject already measured or to overwrite one already written (S9.20) |
| `vn_seals.py` | hashes every `strehl*.exe` and every `.tiff.ok` seal; reproduces §0. Plants decoys it must find, so reach is measured rather than assumed. |

Nothing outside `experiments/V-NEVERWORSE/` was modified. `D:\` was never written.
