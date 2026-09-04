# M162 — is DELIVER-V6's noise gap a regression or a trade?

**VERDICT: UNRESOLVED — neither REGRESSION nor TRADE is yet admissible.**

**Blocker:** M139 still holds the machine's exclusive compute lock. M162 has
performed no render and no real-image score.

M159's result stands: DELIVER-V6/fork fractional box9 residual is `1.515208x`
at the median on twelve frozen coffee-bean flat sites, with `0/12` below one.

The repository history narrows the live question to a small factorial:
full-resolution gather is the leading deliberate **trade** candidate; the
later omission of the shipped `--pyramid-gate 4.5` is the leading avoidable
**regression** candidate. The required A/B remains blocked on compute.

## 1. Correction to the premise: there is no fork-to-Strehl change set

The “fork” is Chris Caruso's modified MIT-licensed fork of Petteri Aimonen's
`focus-stack`, at `C:\dev\macro\focus-stack`. The archived comparator is:

```
C:\dev\macro\out\coffee-bean\stack.tif
sha256 8636C20D73CA0CB1F57DB89BF8553ABC166E0FBC517E5C62A07C74DEE509066E
```

Its log records neighbour alignment, complex-wavelet coefficient selection,
spatial/subband majority filtering, wavelet denoising, inverse transform, and
colour reassignment. The denoiser explicitly thresholds or scales small
coefficients while retaining large sharp contrasts. That is a direct
mechanism by which the fork can produce less flat-field residual.

The archived run used 105 Lightroom-developed TIFFs. Its log was created on
May 10 before the fork's first retained commit,
`4bc7f95e448cf20ee2bdd758403ec43e2612a1c6` at 19:56 local time. No executable
or source revision is cryptographically bound to the render. The retained
May 17 executable postdates it by six days and is not its producer.

So the fork's “best-known build” is an opaque, byte-pinned output and archived
run, not a reproducible build. DELIVER-V6 instead starts from RAW CFA files and
owns demosaic, colour, tone, merge, and output. The repositories have unrelated
Git histories. A Git bisect from one program to the other is impossible and
would confound both algorithm and input development.

The admissible attribution is therefore: hold the fork TIFF fixed, reproduce
DELIVER-V6, and decompose output-changing choices inside Strehl.

## 2. DELIVER-V6 ground truth

```
TIFF   C:\dev\strehl-out\DELIVER-V6\masters\coffee-bean.tiff
sha256 F38CA50ED1A680FA4DBCDD8D0513BE538DD31634B4E89AC6A34885944790A2EC

EXE    C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe
sha256 2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7

SOURCE 6af834dac08d6605aee7ea3ad75809fdf6313770
ARGV   strehl.exe stack <raw-directory> -o <master>.tiff --srgb
ENV    all STREHL_* unset except a private cache
```

Commit `6af834da` changed V-NEVERWORSE experiment material rather than the
output pipeline. It is nevertheless the exact source and binary that produced
the frozen DELIVER-V6 master.

## 3. The relevant Strehl changes

| point | retained binary SHA-256 | output-affecting fact |
|---|---|---|
| `b9b6921e` / SHIP-V2 | `CF33AE08...F0D6E6` | Gallery command used `--merge pyramid --pyramid-gate 4.5 --srgb --auto-exposure`; gather was the CFA phase-plane path. Historical output is gone. |
| `740e7056` | `15EA7346...82A7B0` | Full-resolution gather became default; a direct environment switch remains. |
| SHIP-V3/V4 deployment | — | Gate flag was omitted, so compiled default `2.0` replaced shipped `4.5`; this was configuration drift, not a `DEFAULT_GATE` code edit. |
| `9b05d0b7` / SHIP-V4 | `44C2F2CD...59F490` | Retained post-gather, pre-measured-floor checkpoint. |
| `78fed9a1` | — | Gate floor became measured per warped frame; `STREHL_GATE_FLOOR=white` restores the old constant. |
| `f190a0ea` | `332FA6AE...8FD9C9` | Per-band gate-floor machinery landed. |
| `393d7ca3` | — | Red lateral-CA coefficient was refit; `STREHL_FIX_CA=0` remains a control. |
| `6af834da` / DELIVER-V6 | `2A7BCD7B...12B7` | Frozen binary and TIFF exist. |

The important correction is the gate. The compiled default is `2.0` at
SHIP-V2, `740e7056`, and DELIVER-V6. SHIP-V2 was quieter under an explicit
deployment flag, `4.5`; later deliveries omitted it. Treating this as a
gradual algorithm drift would miss the leading one-line explanation.

## 4. What existing evidence says, and does not say

### Full-resolution gather: a deliberate trade candidate

Commit `740e7056` says the old half-resolution phase-plane path was “throwing
away detail before the election.” A one-binary A/B at gate `4.5` found on
coffee-bean:

- `1.953x` coherent change at `0.20-0.25 cycles/output-pixel`;
- `2.696x` at `0.25-0.30`;
- no corresponding coherent gain in flat controls.

Only the first band survived later commissioning as a resolution claim. The
higher band is merely a coherent change and the upper band was withdrawn.
For M162 this is prior mechanism evidence and a detail proxy, not a
truth-referenced general detail measurement. It does establish that turning
full-resolution gather off is not an innocent “denoise” operation: that path
was introduced to retain information the plane path discarded.

### Gate `2.0`: an avoidable regression candidate

Independent existing evidence points the other way for the deployment change:

- M126 measured `bee-3-cpl` flat-field high-pass RMS falling from `144.37` to
  `14.53 DN` at gate `4.5`, `9.9x` lower, while the compound eye was visually
  indistinguishable and the render was faster.
- BUILD-SHARP swept `4.5 -> 1.0 -> 0.0`. Added band power was largest in flat
  regions and smallest in detailed regions; the absolute delta was
  anti-correlated with scene detail. The lower gates added grain and mottle
  without a visible acuity gain in the inspected crops.

Those results are not the M159 sites and do not settle this lane. They make
gate omission the leading regression hypothesis and justify testing it first.

### Measured gate floor: probably the wrong sign to explain the gap

The earlier warp-only synthetic probe found a floor below the white constant.
Real demosaiced-frame measurement later found the opposite on the production
path: demosaic correlation dominates, and measured/white reaches about `1.55x`
at band 0. The measured floor is therefore stricter, which should average more
and generally lower residual. It is unlikely to cause DELIVER-V6's excess, but
`STREHL_GATE_FLOOR=white` remains a direct control because interaction with
the gate cannot be dismissed from source alone.

## 5. Frozen experiment

`experiments\M162-noise-regression\PREREGISTRATION.md` fixes:

1. a current-binary `2 x 2` factorial:
   gate `2.0/4.5` by full-resolution/plane gather;
2. measured-floor and CA-off controls;
3. exact M159 flat sites and unchanged M159 tone inversion/statistic;
4. one private shared warpmap for all current arms;
5. baseline pixel reproduction against frozen DELIVER-V6;
6. a conditional SHIP-V2 reconstruction from retained binary `b9b6921e`;
7. deterministic paired bootstrap intervals and explicit verdict thresholds.

The historical reconstruction is labelled exactly that. It cannot repair the
fork provenance gap and will not be presented as the archived producer.

## 6. The detail guard

M162's new statistic is a **detail-collapse proxy**:

```
band = box5(green) - box13(green)
floor = 1.4826 * MAD(band)
tail = p99.5(abs(band - median(band)))
proxy = sqrt(max(tail^2 - (K * floor)^2, 0))
```

`K` comes from deterministic pure noise through the same filters. Sites are
chosen only from the fixed fork raster, before any new arm is read: top twelve
non-overlapping proxy sites after headroom, mean, and flat-site-overlap gates.

The proxy is not truth referenced. It can reward ringing or hallucinated
structure, does not test phase fidelity, sees only one frequency band and
green channel, and can miss dense low-contrast texture. It exists to catch the
specific failure “the residual improved because structure collapsed.”

Before any real image is read, it must demonstrate:

- a movable independent-noise null;
- a planted Gaussian-blur degradation;
- recovery from that blur as a planted improvement;
- no reward for tripled added noise;
- the expected trap: blur improves box9 residual while worsening the proxy.

The CPU-light synthetic commission has now run (`commissioning.json`), 128
trials, seed 162, and all five gates pass:

| control | median ratio | required direction |
|---|---:|---|
| independent equal-noise null | `1.000233x` | movable around one |
| blur / original proxy | `0.854357x` | degradation below one |
| original / blur proxy | `1.170471x` | improvement above one |
| 3x-noise / original proxy | `0.955880x` | added noise not rewarded |
| blur / original box9 residual | `0.735309x` | residual rewards blur |

The null spans `0.990152-1.013197`, with 59 trials below and 69 above one.
This commissions the proxy's direction on its planted controls; it does not
promote it into a truth-referenced detail instrument.

A candidate residual reduction with proxy loss is not a win.

## 7. Precommitted ruling

**REGRESSION** requires a current-binary reversion to lower paired residual by
at least 10%, with its 95% lower bound above one, while the structure proxy,
gain, clipping, and geometry guards hold.

**TRADE** requires no admissible quieter reversion and requires
full-resolution gather, at a fixed gate, to be materially noisier while
materially increasing the proxy, with both 95% intervals above one.

If gate `4.5` passes while full-resolution gather also proves a paid structure
benefit, the result is mixed: the gather portion is a trade, but the overall
remedy-bearing verdict is **REGRESSION** because an avoidable component exists.

If the proxy cannot distinguish the arms, the answer remains unresolved. The
absence of an admissible truth-referenced detail instrument is not permission
to guess.

## 8. Current boundary

Answerable without compute:

- the comparator is an opaque archived output, not a rerunnable “best build”;
- no cross-project bisect exists;
- full-resolution gather was explicitly for preserving previously discarded
  detail;
- the gate moved from deployed `4.5` to compiled `2.0` by flag omission;
- existing evidence makes those the leading trade and regression hypotheses.

Not answerable without compute:

- how much of M159's exact twelve-site gap each change contributes;
- whether gate `4.5` lowers those residuals while holding the commissioned
  proxy;
- whether gather's residual cost and proxy gain coexist on the same frozen
  coffee-bean experiment;
- the final REGRESSION-versus-TRADE ruling.

No M162 TIFF has been rendered and no real image has been scored while M139's
exclusive host lock remains in force.
