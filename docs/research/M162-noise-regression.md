# M162 — is DELIVER-V6's noise gap a regression or a trade?

**VERDICT: UNRESOLVED — neither REGRESSION nor TRADE is yet admissible.**

**Blocker:** M139 still holds the machine's exclusive compute lock. M162 has
performed no render and no real-image score.

M159's result stands: DELIVER-V6/fork fractional box9 residual is `1.515208x`
at the median on twelve frozen coffee-bean flat sites, with `0/12` below one.

The repository history narrows the live question to a small factorial.
Full-resolution gather is a deliberate **trade** candidate. A source-only
deployment audit confirms DELIVER-V6 ran at the pyramid default `2.0`, but
does **not** support the earlier claim that this was settled policy. The cited
ORCH decision was provisional; the later README calls `2.0` wrong and leaves
an explicit default-or-rerender obligation. SHIP-V2's original argv is not
recoverable to the primary-record standard, although the surviving records
fix the 26-subject survey at `4.5`. The required A/B remains blocked on compute.

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
| `b9b6921e` / SHIP-V2 | `CF33AE08...F0D6E6` | A same-day report and a surviving transcription of the vanished driver say the 26-subject run used explicit pyramid gate `4.5`; no original script, log, manifest, or argv record survives. Gather was the CFA phase-plane path. Historical output is gone. |
| `740e7056` / SHIP-V3 | `15EA7346...82A7B0` | Full-resolution gather became default. All 26 archived provenance records say `gate : (backend default)`; the pin's pyramid default is `2.0`. |
| `9b05d0b7` / SHIP-V4 | `44C2F2CD...59F490` | All 26 archived provenance records again say `gate : (backend default)`; the pin's pyramid default is `2.0`. |
| ORCH-FAITHFUL | `CBC09099...` | The archived run header names Git HEAD `5f367a94`; its binary banner reports `8a480af9-dirty`. Both sources have pyramid default `2.0`. The 26-render driver passes only `--srgb`. |
| `78fed9a1` | — | Gate floor became measured per warped frame; `STREHL_GATE_FLOOR=white` restores the old constant. |
| `f190a0ea` | `332FA6AE...8FD9C9` | Per-band gate-floor machinery landed. |
| `393d7ca3` | — | Red lateral-CA coefficient was refit; `STREHL_FIX_CA=0` remains a control. |
| `6af834da` / DELIVER-V6 | `2A7BCD7B...12B7` | All 33 banked masters used `stack <dir> -o <out> --srgb`, with no pyramid-gate override; source resolves that to `2.0`. |

### 3.1 Source-only deployment-gate audit

#### SHIP-V2: original deployed record missing; survey gate `4.5`

The strongest surviving statement is contemporaneous but secondary:
`b66f6157:docs/research/BUILD-RENDER.md:2030-2037` says one binary rendered
26/26 subjects with identical flags,
`--merge pyramid --pyramid-gate 4.5 --srgb --auto-exposure`. Commit
`580e04a2` later records byte-identical reproduction of two SHIP-V1 masters at
`4.5`, failure to reproduce them at the compiled `2.0`, and explicitly says
SHIP-V1 preserved no render script or argv. The surviving contemporaneous
transcription at `docs/research/ORCH-veiling.md:5836-5842` quotes the vanished
`C:\dev\strehl-out\ORCH-SHIP\render_ship.ps1` driver as:

```
stack <subject> --merge pyramid --pyramid-gate 4.5 --srgb --auto-exposure -o <out>
```

That is strong corroboration for `4.5`, but it is not the actual SHIP-V2
invocation, script, manifest, or run log demanded by this audit. The
`SHIP-V2`, `acceptance\SHIP-V2`, and `ORCH-SHIP\render_ship.ps1` paths are gone,
and no matching primary-record path exists in reachable Git objects.
Therefore the deployed SHIP-V2 value is **NOT RECOVERABLE** under the stated
evidence rule. This report will not promote the prose reconstruction into a
primary record.

The narrower question about the **26-subject survey's configuration** is
answerable. The records above place it at `4.5`; then commit `5dd9b649`
records a new 26-subject, 4,825-frame run at the explicit invocation
`--merge pyramid --pyramid-gate 4.5 --srgb`
(`docs/research/ORCH-veiling.md:7853-7859`), and commit `f2bcb349` closes the
survey at 26/26 opened (`:8459-8476`). Thus `4.5` is the survey configuration
even though the original SHIP-V2 primary invocation record is gone.

#### DELIVER-V6: default `2.0`, not overridden

The source pin is direct:

- `6af834da:crates/strehl-core/src/pyramid.rs:1152-1157` constructs
  `MergeConfig` with `gate: 2.0`;
- `6af834da:crates/strehl-cli/src/main.rs:1088-1094` starts from that default
  and changes it only when optional `pyramid_gate` is present;
- `experiments/DELIVER-V6/BANK-33.md:13-17` records the actual delivery
  invocation as `<exe> stack <dir> -o <out>\<subject>.tiff --srgb`, with all
  other `STREHL_*` unset;
- `experiments/DELIVER-V6/render.ps1:138` is the executed command and
  `:157-160` writes that command, environment, binary hash, and commit into
  each successful manifest record.

DELIVER-V6 therefore ran at pyramid gate **`2.0`**, with **no override**.

#### Intent: unresolved conflict, implemented by omission

There was no source edit from pyramid gate `4.5` to `2.0`; the compiled
pyramid default was already `2.0`. The earlier ORCH passages record a
provisional decision not to move it:

- commit `5ea8c058` is titled “gate 4.5 is not a safe universal default”;
  `docs/research/ORCH-veiling.md:4296-4315` records the second-subject reversal,
  where `4.5` bought little on `couch-fibers-cpl` and reduced the then-used
  detail proxies, and `:4346-4349` withdraws the recommendation to raise the
  **universal default** rather than rejecting the value `4.5`;
- commit `befded0c` states at
  `docs/research/ORCH-veiling.md:4763-4768` that the backend flip needs no gate
  change and “the default stays” at `2.0` **pending BUILD-BLEND**;
- the DELIVER pin's source comment,
  `6af834da:crates/strehl-core/src/pyramid.rs:992-1001`, explains the intended
  balance: high enough to reject noise, low enough not to throw away real
  low-contrast detail.

The relevant README evidence is later and points the other way:

- the cited ORCH passages were committed at 02:40 and 04:08 on 2026-08-26;
- commit `fd8f8b38` at 05:21 says users should keep
  `--pyramid-gate 4.5`, because `2.0` does not produce the measured picture
  (`README.md:666-677`);
- commit `580e04a2` at 11:38 states the open obligation: either move the
  default to `4.5` or rerender and resurvey the gallery at `2.0`
  (`README.md:354-361`);
- commit `244cad54` at 12:11 calls `2.0` “the wrong default”
  (`README.md:347-353`);
- the later ORCH corpus work at 12:55 and 15:03 rendered and surveyed the
  26 subjects at `4.5`, including the adversarial defocused-background case.

No later commit message, comment, or note records a decision that this newer
evidence was rejected and `2.0` was chosen as the correct default. The source
stayed at `2.0`, and later drivers stopped passing `--pyramid-gate`. That
settles the mechanism as **flag omission**, but leaves intent as an
**UNRESOLVED CONFLICT**. The earlier report's `DELIBERATE` verdict is retracted.

Those historical detail statistics remain proxies, not truth-referenced
detail measurements. They do not settle M162's artifact verdict in either
direction.

#### Blast radius

Direct stacked artifacts produced at the `2.0` backend default are:

- **SHIP-V3:** 26 masters, archived per-file provenance beginning at
  `experiments/ORCH-drift-check/acceptance-hash-index.txt:4810`; each record
  says `gate : (backend default)` and gives a verbatim argv without
  `--pyramid-gate`;
- **SHIP-V4:** 26 masters, corresponding archived records beginning at
  `acceptance-hash-index.txt:9068`;
- **ORCH-FAITHFUL:** 26 now-purged masters, whose inlined log begins at
  `experiments/ORCH-drift-check/purged/ORCH-FAITHFUL-index.txt:10`; the actual
  driver command is `experiments/ORCH-drift-check/render_head26.ps1:65`;
- **DELIVER-V6:** all 33 banked masters in
  `experiments/DELIVER-V6/BANK-33.md`.

DELIVER-V5's presentation PNGs are derivatives of SHIP-V4 masters
(`experiments/DELIVER-V5/geom.py:7-15`), so they inherit that `2.0` merge but
are not independent stack runs. SHIP-V3, SHIP-V4, and ORCH-FAITHFUL TIFFs have
since been purged after their text/hash records were banked; DELIVER-V6 is the
surviving current corpus.

#### README obligation and publication state

The compiled default never moved to `4.5`. The alternative branch was later
performed in artifacts: DELIVER-V6 used the no-override/default-`2.0`
invocation (`docs/research/DELIVER-V6.md:57-69`), rendered all original 26
subjects, and records that all 26 were inspected at 1:1 with subject-by-subject
findings (`:3-12`, `:245-381`). The run was then extended to 33 subjects.
Therefore the README's technical “rerender at `2.0` and re-survey” obligation
was discharged by DELIVER-V6.

The README was not updated to say so. It still calls the corpus-wide sweep
open, says dropping `4.5` produces an uncertified render, and bases every
reference-gallery quality claim on `4.5` (`README.md:666-677`). It explicitly
discloses that `4.5` is not the compiled default (`:198-206`, `:666-677`), so
it does not silently present those pixels as bare-command/default output.
Publication-facing quality evidence nevertheless remains scoped to the
non-default configuration, and the notice about default output is stale.

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

### Gate `2.0`: an unresolved configuration choice whose contribution remains unmeasured

Independent existing evidence shows why gate `4.5` remains an important
counterfactual:

- M126 measured `bee-3-cpl` flat-field high-pass RMS falling from `144.37` to
  `14.53 DN` at gate `4.5`, `9.9x` lower, while the compound eye was visually
  indistinguishable and the render was faster.
- BUILD-SHARP swept `4.5 -> 1.0 -> 0.0`. Added band power was largest in flat
  regions and smallest in detailed regions; the absolute delta was
  anti-correlated with scene detail. The lower gates added grain and mottle
  without a visible acuity gain in the inspected crops.

Commit `5ea8c058` records the opposite outcome on the deliberately adversarial
`couch-fibers-cpl`: raising the gate bought little and reduced the available
detail proxies. Those results are not truth-referenced, are not the M159
sites, and do not settle this lane. Later README measurements and the
26-subject `4.5` survey superseded that provisional default decision without
ever changing the compiled value. The record therefore shows conflicting
evidence, not a settled `2.0` trade policy.

The `4.5` arm is necessary both to attribute how much of M159's residual gap
comes from gate selection and to test the live configuration-regression
hypothesis. It is eligible under the same precommitted residual, proxy, gain,
clipping, and geometry guards as the other current-binary reversions. A proxy
loss still forbids calling it a fix.

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
6. a conditional, report-based SHIP-V2 reconstruction from retained binary
   `b9b6921e`, explicitly not a recovered deployment invocation;
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

**REGRESSION** requires an attributed change to lower paired residual by at
least 10%, with its 95% lower bound above one, while the reverted candidate
holds or improves the structure proxy and passes the gain, clipping, and
geometry guards. Gate `4.5`, measured-floor, and CA-off are eligible
current-binary reversions. Gate eligibility does not imply that this proxy is
a complete detail instrument; its blindness remains part of the scope of any
verdict.

**TRADE** requires no admissible quieter reversion and requires
either full-resolution gather, at a fixed gate, or gate `2.0`, at fixed
gather, to be materially noisier while materially increasing the proxy, with
both 95% intervals above one.

If the proxy cannot distinguish the arms, the answer remains unresolved. The
absence of an admissible truth-referenced detail instrument is not permission
to guess.

## 8. Current boundary

Answerable without compute:

- the comparator is an opaque archived output, not a rerunnable “best build”;
- no cross-project bisect exists;
- full-resolution gather was explicitly for preserving previously discarded
  detail;
- SHIP-V2's actual deployed argv is not recoverable from a primary record;
- the 26-subject survey was nevertheless rendered and assessed at gate `4.5`;
- DELIVER-V6 ran at the compiled pyramid default `2.0`, with no override;
- the relevant source record is an unresolved conflict, not a settled choice
  that `2.0` is correct;
- DELIVER-V6 technically discharged the README's default-`2.0` rerender and
  re-survey branch, but the README still says that work is open;
- SHIP-V3, SHIP-V4, ORCH-FAITHFUL, and DELIVER-V6 were all produced at that
  default, while DELIVER-V5 derivatives inherit SHIP-V4's merge.

Not answerable without compute:

- how much of M159's exact twelve-site gap each change contributes;
- whether gate `4.5` lowers those residuals while holding the commissioned
  proxy;
- whether gather's residual cost and proxy gain coexist on the same frozen
  coffee-bean experiment;
- the final REGRESSION-versus-TRADE ruling.

No M162 TIFF has been rendered and no real image has been scored while M139's
exclusive host lock remains in force.
