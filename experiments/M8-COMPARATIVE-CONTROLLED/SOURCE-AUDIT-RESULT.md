# `focus-stack` source audit and control result

**Status: `UNMEASURED`.** Synthetic diagnostics and admission controls only.
No subject frame was decoded, no holdout was opened, and M8-O was not run.

## Registration and provenance

* Source/diagnostic preregistration: `43c6a760`
* Depthmap-off full-control preregistration: `b5a45137`
* Normal-crop retry preregistration: `ed064117`
* Executable:
  `C:\dev\macro\focus-stack\dist\focus-stack.exe`
* Executable SHA-256:
  `0ABA0CF0936AF8B1CACE2681CA43D49729D253E8ED1F786F2A8960B7974CA45D`
* Local source candidate:
  `chcaru/macro@864ff08862414682e75d58245a1e7f1d25cf3315`
* Public upstream comparison:
  `PetteriAimonen/focus-stack@0cd289e224fe24aead5b146faeaa46950775f346`

The executable has no embedded Git revision or reproducible-build record.
Source conclusions are corroborated by the executable controls below but are
not claimed as a cryptographic source/binary identity.

## Audit answers

### 1. Does `--no-align` skip the warp?

Yes. The local option parser sets `ALIGN_NONE`
(`focus-stack/src/main.cc:1300-1308`). One `Task_Align` wrapper is scheduled
per input (`focus-stack/src/focusstack.cc:864,894-939`), but its task branch
directly aliases the source image when `ALIGN_NONE` is set
(`focus-stack/src/task_align.cc:133-138`). Upstream has the equivalent branch
at `src/task_align.cc:59-63`.

No fit, transform, `warpAffine`, or interpolation is executed. This is stronger
than `--no-transform` alone, whose non-bypass path still calls
`cv::warpAffine(..., INTER_LANCZOS4, ...)`
(`focus-stack/src/task_align.cc:828-834`).

### 2. What were the 93 `Align` labels?

The retained full-control stdout contains 93 progress lines matching
`] Align `:

* unique input names: `92`;
* missing input names: `0`;
* duplicate: `048-identity-witness.tif`, exactly twice.

The worker prints a task when it starts (`worker.cc:267-272`) and redraws one
still-running task when another finishes (`worker.cc:351-356`). The duplicate
is a progress redraw, not a 93rd task or input. Each of the 92 actual wrappers
takes the source-alias bypass above.

### 3. Does an identity transform still resample?

The selected `--no-align` route constructs no resampling call at all. The
zero-phase-kernel question is therefore defined away. If only
`--no-transform` were used, the implementation would still call OpenCV
Lanczos warping and would require a separate pixel proof even for an identity
matrix.

### 4. Can final depthmap construction be skipped?

Yes, with `--depthmap-chain=off`, and an `N=8` identical diagnostic writes an
output. However, this is a different merge arm. The default `auto` path feeds
the confidence pipeline (`focusstack.cc:1091-1114,1251-1265`);
`main.cc:1858-1879` documents `off` as restoring pre-Phase-12.5 behavior.

## Crash diagnosis

All comparator processes passed their preregistered host-load gate.

| arm | N | relation | extra option | exit | output |
| --- | ---: | --- | --- | ---: | --- |
| `I02-S` | 2 | identical | none | `1` | no |
| `I08-S` | 8 | identical | none | `1` | no |
| `I92-S` | 92 | identical | none | `1` | no |
| `V92-S` | 92 | ordinal-offset varied | none | `0` | yes |
| `I08-S-extra-BD2B50DF7EC0` | 8 | identical | `--depthmap-chain=off` | `0` | yes |

The identical arms fail in final depthmap construction with OpenCV
`ranges[i][0] < ranges[i][1]`. Failed Gaussian fits write amplitude zero
(`task_depthmap.cc:1274-1305`); final confidence creates a histogram of that
plane (`:1589-1594`); and `histogrampercentile.cc:6-19` passes an all-zero
range `[0,0]` to `cv::calcHist`. `V92-S` succeeding proves this is not a
92-input capacity limit. The registered stop condition was met, so `I02-F`
was not run.

## Full admission controls

Every full arm used 92 byte-identical hard links to the same registered
`3392x2262x3` uint16 aperiodic witness.

| arm | outcome | reason |
| --- | --- | --- |
| default, `--nocrop` | `FAIL` | final zero-range depthmap crash; no output |
| depthmap-off, `--nocrop` | `FAIL` | output `3584x2560`, expected `3392x2262` |
| depthmap-off, normal crop | `FAIL` | dimensions exact; declared linear-domain equality failed |

The padded extent is source-explained:
`task_loadimg.cc:224-236` stores the original rectangle as `valid_area`, and
`task_saveimg.cc:203-213` preserves the padded matrix under `--nocrop` but
otherwise returns that rectangle.

For the normal-crop retry:

* output schema: `3392x2262x3`, uint16, Orientation 1;
* samples: `23,018,112`;
* samples within `4 DN` of the declared linear input: `0`;
* maximum registered direct error: `18,817 DN`;
* after one source-declared sRGB EOTF: all samples within `1 DN`;
* EOTF-predicted mean/max absolute error: `0.001539 / 1 DN`.

`colormgmt.cc:282-288` treats uint16 inputs as already encoded.
`colormgmt.cc:290-404` applies the OETF only to float inputs, and
`colormgmt.cc:548-607` applies the EOTF for linear-Rec.2020 output. The
registered linear uint16 input was therefore decoded a second time. Exact
per-coordinate EOTF agreement strongly corroborates identity geometry but
fails the common-linear-domain contract.

## Licensed conclusion

The default and both separately preregistered nondefault arms are
`UNMEASURED`. No M8-O numerator, denominator, signed extrema, excess
distribution, comparator/strehl common stack, or sharpening pair exists.

This is a **controlled merge audit, not a default-settings product benchmark**.
Disabling a comparator's normal alignment deliberately removes one part of its
product.

The no-run free-comparator survey and scientific-versus-market Zerene
distinction are recorded in
`docs/research/M8-COMPARATIVE-PROTOCOL.md` §§15.3 and 17.
