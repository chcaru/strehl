# V-ANTI-verify -- independent verification of V-CA's anti-arm result

**VERDICT: CONFIRMED WITH QUALIFICATION.**

Every *factual* number V-CA reported reproduces bit-exactly, including all six SHA-256
hashes rebuilt from source. Every *inferential* claim built on the odd/even decomposition
(R4 a, b, c) is refuted or materially weakened. The headline -- **the shipped CA sign is
correct in the render domain** -- stands, and stands strongly.

| V-CA claim | status |
|---|---|
| R1 hashes, R2 headline, 16/16 tests, all 3 pre-registered predictions | **CONFIRMED, bit-exact and re-runnable** |
| R4(a) on-vs-off understates the correction 1.9x; interpolation opposes it | **REFUTED in sign and magnitude** |
| R4(b) the r 0.2-0.3 lobe is PROVEN to be interpolation | **REFUTED** -- 76 % of it survives with blur deleted |
| R4(c) a net-harmful *radius* exists; the missing guard is a lower one | **observation partly survives; mechanism and prescription REFUTED** |
| R3 the asymmetric transfer is caused by the `eps_b = None` blue floor | **unnecessary** -- convexity of `mean abs()` explains it with B bitwise constant |

---

## 1. Reproducibility -- RE-RUNNABLE, not merely recorded

This was ORCH's top question because the patch was reported absent from the tree. It is
absent, but the recorded patch is sufficient to regenerate the result exactly.

I recovered the verbatim patch from `42270f4` section 1, created my own detached worktree at
`42270f4` (not at current HEAD -- HEAD has since moved to `5a99350`, which changes merge
code), applied the patch by exact-anchor substitution, and rebuilt.

```
git worktree add --detach C:\dev\strehl-out\V-ANTI-wt 42270f4
cargo build --release -p strehl-cli      -> Finished `release` profile in 2m 09s
```

Six merges, same subject (`bee-3-cpl`, 299 frames), same shared sidecar
(`M110-sheet/bee-3-cpl/default.warp.json`), default binned-linear output, no `--srgb`:

| arm | my SHA-256 (16) | V-CA's | |
|---|---|---|---|
| `unset` | `C38FFBA98E211565` | `C38FFBA98E211565` | MATCH |
| `zero` | `C38FFBA98E211565` | `C38FFBA98E211565` | MATCH |
| `off` | `C38FFBA98E211565` | `C38FFBA98E211565` | MATCH |
| `false` | `C38FFBA98E211565` | `C38FFBA98E211565` | MATCH |
| `correct` | `64914FAF1D554B5C` | `64914FAF1D554B5C` | MATCH |
| `anti` | `22DBB9C7AA42D08D` | `22DBB9C7AA42D08D` | MATCH |

**6/6 bit-exact from source.** The metric on the freshly rendered arms:

```
unset    mean|R-Y| =   729.10 DN    +0.00000 %
correct  mean|R-Y| =   630.58 DN   -13.51251 %
anti     mean|R-Y| =  1006.08 DN   +37.98881 %
```

identical to V-CA's 729.10 / 630.58 / 1006.08 and to `metric.json` at five decimal places.
`cargo test --release -p strehl-core optics::` in the patched worktree: **16 passed, 0
failed**, including `the_two_profiles_differ_only_in_translation`, as reported.

The six output TIFFs from V-CA's original run also still exist under
`C:\dev\strehl-out\V-CA-anti\` and re-hash to the reported values.

**Cost to re-run: ~2 min build + ~11 min merges.** The worktree was destroyed
(`git worktree remove --force`, `git worktree prune`) and
`crates/strehl-core/src/optics.rs` verified clean against HEAD.

**Caveat, stated plainly:** what is reproducible is the *pipeline given the shared warp
sidecar*. Alignment was not re-run; a sidecar regression would not be caught by this.
That was V-CA's deliberate design choice and it is sound, but it is a boundary on the
reproduction.

---

## 2. The positive control -- valid, and inert for the RIGHT reason

The concern was that `zero`/`off`/`false` might be unrecognised tokens silently falling
through to a default. They are not.

`crates/strehl-core/src/optics.rs:452-454`:

```rust
if raw.is_empty() || raw == "0" || raw.eq_ignore_ascii_case("off") || raw.eq_ignore_ascii_case("false") {
    return Ok(None);
}
```

All three spellings are matched **explicitly**. Unrecognised tokens hit
`Err(CaConfigError::UnknownProfile)`. I proved the error is not swallowed, on the patched
binary:

```
typo-not-a-profile                 exit=1  Error: unknown lateral-CA profile "typo-not-a-profile"; known profiles: a7c2-fe100gm-2xtc-x4cpl
1                                  exit=1  Error: unknown lateral-CA profile "1"; ...
true                               exit=1  Error: unknown lateral-CA profile "true"; ...
on                                 exit=1  Error: unknown lateral-CA profile "on"; ...
a7c2-fe100gm-2xtc-x4cpl-anti-typo  exit=1  Error: unknown lateral-CA profile "..."; ...
```

Exit 1 and **no output file**. `arms.json` records `exit: 0` for all six arms, so no arm
could have been a silent fallthrough. **Control confirmed.**

Two qualifications, neither fatal:

- The four arms exercise **two** code paths, not four: `unset` returns at the `None` match,
  and `zero`/`off`/`false` share one `||` predicate and one `return`. What the control
  actually establishes is *end-to-end determinism of a 299-frame merge* plus *the env var
  is read and three off-spellings reach the off branch*. That is still exactly what the
  discriminator needed. It is not four independent parses.
- Stronger evidence than the hashes: **G and B are bitwise identical in all six arms**
  (0 differing pixels), and only R moves (7 983 978 px in `correct`, 7 983 833 in `anti`).
  That independently confirms `eps_b = None` and "green is never touched".

**Registered check V-CA never reported an outcome for:** the bonus prediction that
`default.warp.json` and `ca.warp.json` are byte-identical. I ran it. Both are
`4B56096D45128083DAF110176432C2F5202D366FD6B5FE8C749112AB65475721`. **It holds** -- CA is
merge-only. Reporting this belatedly is a gap in V-CA's write-up, not a defect in the result.

---

## 3. The odd/even decomposition -- the FIELD is a clean sign flip; the INFERENCE is not

### 3.1 The parity assumption itself is CORRECT

I attacked this first as instructed, and it holds:

- `optics.rs:319`: shipped `eps_r: -704.5e-6`. Registered patch: `eps_r: 704.5e-6`. Exact negation.
- The `translation` trap is **avoided**. The base const carries `translation: (0.6294, -0.4240)`,
  but the shipped key resolves to `A7C2_FE100GM_2XTC_X4CPL_RADIAL` which zeroes it
  (`optics.rs:457-459`), and the anti const explicitly re-states `translation: (0.0, 0.0)`.
  Both applied profiles therefore differ **only** in the sign of `eps_r`.
- The applied transform is a pure scale: `optics.rs:692`, sampled radius `= (1.0 + p.eps_r) * r`.
- G and B bitwise identical across arms, so `c = R - Y = 0.7874*R - K` with `K` arm-independent.
  The perturbation field is therefore exactly odd in `eps` to first order and exactly even at
  every even order.

**`anti` is the exact `eps -> -eps` of `correct`. Parity of the field is confirmed.**

### 3.2 But parity of the field does not transfer to parity of the metric

`mean abs(R-Y)` is a **rectifying, convex** functional. For a pixel with residual `c0` and
linear response `k`:

```
abs(c0+k e) + abs(c0-k e) - 2 abs(c0)  =  0                    if abs(k e) <= abs(c0)
                                       =  2(abs(k e) - abs(c0)) if abs(k e) >  abs(c0)
```

So the metric's EVEN component is **>= 0 by construction**, generated purely by pixels the
correction pushes *past* zero -- **with zero interpolation**. In particular, where `c0 ~ 0`,
`mean abs(k e)` is *exactly even in e*. V-CA's premise "an even function of eps, which a
correction cannot be" is algebraically false.

I built the controls V-CA did not. With `O = (c_anti - c_correct)/2` (odd field part) and
`E = ((c_anti - c_unset) + (c_correct - c_unset))/2` (even field part):

| arm | construction | metric vs `unset` |
|---|---|---|
| `correct` (observed) | `cu - O + E` | **-13.513 %** |
| `anti` (observed) | `cu + O + E` | **+37.989 %** |
| **correction, blur deleted** | `cu - O` | **-12.752 %** |
| **anti, blur deleted** | `cu + O` | **+41.374 %** |
| **blur alone, no correction** | `cu + E` | **-1.938 %** |

Field magnitudes on the edge ROI: `rms(O) = 610.18 DN`, `rms(E) = 262.78 DN`, `E/O = 0.4307`.

**Consequences:**

- V-CA's metric EVEN = `+12.238 pp`. A **perfectly odd field with zero blur** yields
  `(41.374 + -12.752)/2 = +14.311 pp`. **Rectification alone accounts for 117 % of the
  number V-CA attributes to interpolation.** The residual attributable to the genuine even
  field is `12.238 - 14.311 = -2.073 pp` -- *negative*.
- The **blur-only arm measures -1.938 %**. Resampling *improves* this metric; it does not
  "give back +12.24 %". Plainly: blurring R against an untouched G reduces the *amplitude*
  of chroma peaks, and `mean abs(R-Y)` on edge pixels is peak-amplitude dominated.
- 18.6 %-25.0 % of edge pixels have `sign(R-Y)` reversed by the correction -- direct
  confirmation that rectification is large.

### 3.3 Claim (a) -- REFUTED in sign and magnitude

> "The pure correction is -25.75 %; resampling gives back +12.24 %; interpolation **opposes**
> the correction. On-vs-off understates the true effect by 1.9x."

`-25.75 %` is `(anti - correct)/2` -- the **odd component of the metric**, which is not "the
metric of the odd component". The correction's actual effect with the even field deleted is
**-12.752 %**, against an observable of **-13.513 %**.

**On-vs-off is accurate to 0.76 pp. It does not understate by 1.9x, and interpolation does
not oppose the correction -- it helps it, by -0.76 pp in the `correct` arm and -3.39 pp in
the `anti` arm.** Both signs are opposite to V-CA's conclusion. This is the same shape as
the hazard already folded at `beffc84`: an excess-over-control disagreeing with the raw
statistic in sign.

### 3.4 Claim (b) -- REFUTED

> "At r 0.2-0.3 both arms are positive -- an even function of eps, which a correction cannot
> be. PROVEN to be interpolation."

With the even field component **deleted entirely**, at r 0.2-0.3:

| | `correct` | `anti` | zero-blur `cu-O` | zero-blur `cu+O` |
|---|---|---|---|---|
| r 0.2-0.3 | +8.53 % | +28.59 % | **+6.46 %** | **+28.69 %** |

**Both zero-blur arms are still positive**, and **76 % of the +8.53 % survives with blur
gone**. The lobe is the correction over-shooting a near-zero residual, not interpolation.
V-CA's own logic disproves itself: if "both arms positive" proved interpolation, it would
still prove it after interpolation was removed.

Blur's contribution to the inner band is annulus-dependent and small where V-CA argued it
was decisive: `+2.07 pp` of `+8.53` at r 0.2-0.3, `-0.08 pp` at r 0.1-0.2, and only at
r 0.3-0.4 does it dominate (`+0.66 %` observed vs `-2.67 %` zero-blur).

### 3.5 R3's "number that does not fit" is the same error

V-CA under-predicted `anti` by 11.3 pp and attributed the asymmetric transfer (0.180 helpful
vs 0.304 harmful) to an untouchable blue/yellow fringe under `eps_b = None`. **B is bitwise
identical in every arm**, and my dose ladder uses only the red-plane odd field, yet it
reproduces the asymmetry in full: `t = -1` gives `-12.75 %`, `t = +1` gives `+41.37 %`,
ratio **3.24**. The asymmetry is the convexity of `mean abs()` about a minimum near `t = -0.82`.
The blue floor is not needed. V-CA filed a symptom of its own decomposition error as an
unexplained residual.

---

## 4. Claim (c) -- observation partly survives; mechanism and prescription REFUTED

### 4.1 Dose-response ladder (planted, not a form-based rule)

`mean abs(cu + t*O)` over the registered edge ROI, `t = -1` being the shipped correction with
blur deleted:

```
   t     mean|R-Y| DN   vs off %
 -2.00       803.45    +10.197%
 -1.50       691.44     -5.165%
 -1.25       655.91    -10.039%
 -1.00       636.13    -12.752%   <- shipped
 -0.75       633.01    -13.180%
 -0.50       647.39    -11.207%
  0.00       729.10      0.000%
 +1.00      1030.76    +41.374%
 +2.00      1407.17    +93.001%
minimum at t = -0.82, 632.15 DN (-13.297%)
```

Clean, convex, single-minimum. **The shipped coefficient over-corrects by ~22 % on this
subject and metric.** That independently corroborates the section 6.4 finding V-CA already
cites, and it is a better-supported explanation of the inner harm than either interpolation
or a radius guard.

### 4.2 The observation survives rebinning; it does NOT survive dropping the stencil

Raw statistic printed beside every percentage, per project rule:

| r | n | raw off DN | `correct` | delta DN | zero-blur | sign-reversed | realised R levels |
|---|---|---|---|---|---|---|---|
| 0.0-0.1 | 29 149 | 839.2 | -0.57 % | -4.7 | -0.52 % | 2.7 % | 2 163 |
| 0.1-0.2 | 38 646 | 455.3 | +1.74 % | +7.9 | +1.82 % | 11.5 % | 2 117 |
| 0.2-0.3 | 46 829 | 418.9 | +8.53 % | +35.7 | +6.46 % | 18.6 % | 3 608 |
| 0.3-0.4 | 79 796 | 495.9 | +0.66 % | +3.3 | -2.67 % | 25.0 % | 4 140 |
| 0.4-0.5 | 141 909 | 663.5 | -15.75 % | -104.5 | -15.40 % | 21.9 % | 5 899 |
| 0.5-0.6 | 248 511 | 708.8 | -7.69 % | -54.5 | -8.63 % | 22.7 % | 7 662 |
| 0.6-0.7 | 132 701 | 872.8 | -17.30 % | -150.9 | -15.49 % | 22.4 % | 6 512 |
| 0.7-0.8 | 62 276 | 1 025.7 | -30.08 % | -308.6 | -25.05 % | 22.4 % | 4 338 |
| 0.8-0.9 | 37 432 | 1 100.1 | -31.25 % | -343.8 | -26.28 % | 21.5 % | 3 837 |

**Quantisation:** realised distinct R levels inside the measured window are **11 613** over
the whole edge ROI and 2 117-7 662 per annulus, against 65 536 nominal. Far above the regime
where the pooled-mean hazard bites. Not a live threat here.

Robustness of "inside r < 0.40 the correction is harmful":

| stencil | n (r<0.40) | raw DN | `correct` | zero-blur |
|---|---|---|---|---|
| green-grad top 20 % | 471 565 | 455.5 | **+0.36 %** | -0.43 % |
| green-grad top 10 % (registered) | 194 420 | 520.7 | **+2.08 %** | +0.40 % |
| green-grad top 5 % | 83 670 | 585.4 | **+6.60 %** | +3.44 % |
| green-grad top 1 % | 13 432 | 693.0 | **+31.08 %** | +21.84 % |
| RED-gradient top 10 % | 203 647 | 531.4 | **+1.60 %** | +0.03 % |
| **ALL pixels, no stencil** | 2 243 945 | 342.7 | **-0.24 %** | -0.45 % |

Equal-count quintiles of r: innermost quintile (r 0.000-0.370) `+3.90 %`, raw 517.4 DN.
Chroma redefined as `R-G`: r<0.40 `+2.19 %`, raw 606.3 DN. Fine 0.05 bins put the zero
crossing at r ~ 0.35.

**So: the sign survives rebinning, an alternative chroma definition, an alternative stencil
channel, and stencil percentiles from 1 % to 20 % -- but it inverts when the stencil is
removed, and in absolute DN the inner harm is +7.9 / +35.7 / +3.3 DN against -104 to -344 DN
outside. Net over the edge population the correction removes 7.84e7 DN of chroma.**

### 4.3 The prescription is wrong: the effect is not radial

This is the finding that kills (c)'s actionable half. A lateral-CA correction is a **pure
radial scale** and is rotationally symmetric by construction, so it cannot generate azimuthal
structure. Inside r < 0.45, binning the same pixels two ways:

```
binned by radius   : 9 bins spread  -17.21% ..  +12.63%   range 29.84 pp, sd  8.43
binned by azimuth  : 9 bins spread  -33.60% ..  +45.74%   range 79.34 pp, sd 26.32
```

**Azimuth organises the effect 2.7x more strongly than radius does.** Splitting V-CA's own
claim-(b) annulus (r 0.2-0.3, mean +8.53 %) into 12 sectors:

| sector | n | raw DN | `correct` | zero-blur |
|---|---|---|---|---|
| -180..-150 | 418 | 339.9 | -28.14 % | -26.65 % |
| -150..-120 | 1 409 | 323.0 | -33.36 % | -32.78 % |
| -120..-90 | 3 857 | 592.2 | -15.63 % | -14.10 % |
| -90..-60 | 4 937 | 505.3 | -20.07 % | -20.05 % |
| -60..-30 | 4 256 | 409.6 | +8.82 % | +8.09 % |
| -30..0 | 1 158 | 425.4 | +14.70 % | +13.53 % |
| 0..+30 | 1 424 | 562.6 | +9.03 % | +8.88 % |
| **+30..+60** | 3 195 | 222.3 | **+114.07 %** | +99.36 % |
| +60..+90 | 7 845 | 259.9 | +85.74 % | +73.61 % |
| +90..+120 | 8 397 | 479.5 | +19.32 % | +17.91 % |
| +120..+150 | 5 414 | 377.5 | -9.83 % | -12.19 % |
| +150..+180 | 4 516 | 527.5 | -29.82 % | -28.58 % |

**Six of twelve sectors are helpful, down to -33.4 %.** One sector carrying 6.8 % of the
annulus reads +114.07 %; dropping it alone takes the annulus from +8.53 % to +4.57 %.

The zero-blur column tracks the observed column within a few pp in **every** sector, so this
is not interpolation either -- it is the correction interacting with scene content.

**Therefore: "a net-harmful *radius* exists" is the wrong description, and "the missing guard
is a lower one" is the wrong remedy.** A lower radius guard would switch the correction off
across a full annulus in which half the sectors are gaining 20-33 %. What the data supports
is that the shipped scalar over-corrects (`t_opt = -0.82`) and that the residual harm is
localised in scene content, not in radius.

This does **not** reopen the default: the correction remains OFF, so nothing here is a live
user-facing defect. It changes what a future gate should be gated *on*.

---

## 5. A guard V-CA did not credit

Fact 1784's defect -- the sign-inverted correction that passed 9/9 unit tests -- would **not**
pass today. I flipped the shipped `eps_r` to `+704.5e-6` in the throwaway worktree and ran the
suite:

```
test optics::tests::correction_opposes_the_aberration ... FAILED
   panicked at crates\strehl-core\src\optics.rs:688: assertion failed: p.eps_r < 0.0
test optics::tests::the_shipped_coefficients_match_the_fit_they_claim ... FAILED
   panicked at crates\strehl-core\src\optics.rs:1001: red is under-magnified; eps_r must be negative
test result: FAILED. 14 passed; 2 failed
```

The render-domain anti arm is therefore **confirmatory redundancy**, not the sole guard. That
strengthens the project's position rather than weakening V-CA's -- but "no render-domain sign
check has run since" should not be read as "nothing has checked the sign since".

---

## 6. The number that does not fit

**The r 0.5-0.6 annulus.** It holds **248 511 of 824 446 edge pixels -- 30.1 %, the single
largest bin in the whole measurement** -- and reads only **-7.69 %** while its immediate
neighbours read **-15.75 %** and **-17.30 %**. Excluding it moves the headline from
**-13.513 %** to **-15.926 %** (which lands almost exactly on Addendum 5's independently
measured -16.00 %).

Nothing in either story explains it. Its median G (10 516) and its fraction of strongly
chromatic pixels (24.9 % above 1 000 DN) sit *between* its neighbours, so it is not brighter
or flatter. Its quadrant profile (-23.29 %, +7.26 %, +20.55 %, -33.84 %) is strongly
structured but does not match r 0.2-0.3's pattern, so "scene content" names it without
explaining it. And it sits at a shift of 0.82 px, between the half-pixel and whole-pixel
interpolation extremes, so no simple fractional-offset argument covers it either.

Because that one annulus carries 2.4 pp of a 13.5 pp headline, this is not a rounding detail.
If the headline is ever quoted as a single number, this bin is where it is being set.

---

## 7. What remains unverified

- **Everything in sections 3-6 is my own new measurement and has not been independently
  verified.** It should be treated as unverified until someone re-runs it.
- One subject (`bee-3-cpl`), one sidecar. Nothing here speaks to transfer.
- Alignment was not re-run; a sidecar regression is outside the reproduction boundary.
- `cu - O` is "first-order-shift-only", not literally "the correction with an ideal
  resampler": `E` absorbs *all* even-order terms, not only interpolation. The direction of
  every conclusion in section 3 is unaffected, but the exact split is a proxy.
- I did not verify V-CA's cited priors (`c10_rings.json`, Addendum 5's -16.00 %, the 0.950 /
  0.541 transfer split, section 6.4). Those come from `V-CA-audit.md` and are out of scope.

## 8. Scripts

Every number above is reproducible from the six TIFFs under `C:\dev\strehl-out\V-CA-anti\`
(or a fresh rebuild per section 1) using `experiments/V-ANTI/` alongside this file. All
readers use `tifffile.imread` with `assert a.dtype == np.uint16` and no fallback. No
`--srgb` render was measured.
