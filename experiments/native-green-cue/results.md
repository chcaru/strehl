# Native green cue: full replacement rejected

**MEASURED: REJECT.** The one fixed original-green cue completed all78 synthetic
stack outputs. Its literal operator, nuisance, fallback, flat-noise and sharp
reconstruction controls passed. The actual consumer then failed79 acceptance
bars. Keep the existing default. No RAW photograph or further variant was run.

Source: `bd7d444e53a8ec399ffc8299e0431c98b20bb2bf`.
Charter: `33d87c0382e32ab4711f13bd9482287dffaaf0fe`.

## Decisive result

All48 individual noisy mixed-scene readouts (three directions, eight independent
noise seeds, two output readouts) had higher total known-truth RMSE:
**1.259116 to1.541109 times the existing selector**. The allowed maximum was1.05.
All six low-frequency-only readouts also lost fidelity. Noiseless horizontal
and vertical mixed fields worsened; the noiseless diagonal improved. These are
measured software-fixture results, not visible-defect claims about real photos.

The high-frequency coefficient improved in all48 individual noisy readouts
and in every direction/readout of the eight-seed mean images. This is a real
known-signal benefit in the controlled fixture. Total image error still worsened
in every individual noisy output: preserving that tone is not a complete
quality improvement. Mean images cannot be used to hide the increased error.

| Direction | Readout | Mean-image high coefficient error, off -> cue | Mean-image total RMSE DN, off -> cue |
|---|---|---|---|
| x | distinct green sites | .476004 -> .253650 |19.43897 ->19.86041 |
| x | reconstructed green | .528852 -> .360593 |17.39321 ->17.32564 |
| y | distinct green sites | .480209 -> .269115 |19.48910 ->20.61435 |
| y | reconstructed green | .531900 -> .371871 |17.43775 ->18.11239 |
| diagonal | distinct green sites | .459564 -> .075434 |19.10699 ->14.01321 |
| diagonal | reconstructed green | .419619 -> .076253 |15.38994 ->11.29869 |

Errors include phase against independently generated, unit-cell-integrated
sharp truth. The small x/reconstructed total-error change is not a robust
whole-image gain: independent review finds its jackknife SE exceeds the change.
Each individual noisy case remains a failure, including the diagonal ones.

Flat temporal variance decreased368.75484 ->300.70643DN^2 at distinct green
sites and278.82430 ->219.41906DN^2 after current green reconstruction
(18.45% and21.31% lower variance). Paired jackknife SEs of the variance
*differences* were9.58409 and7.10292DN^2. This flat control passed, but does not
license applying its result to textured regions. Temporal and spatial variation
are not interchangeable.

The independent sharp-source controls retained89.89% to109.08% high-tone
amplitude through the current demosaic kernel, within their complex-error bar.
Wrong phase coordinates and manufactured amplitude were rejected. Off versus
all-invalid cue reproduced3072 collapsed f32 bit patterns; a deliberately live
valid override changed all3072. These are scoped controls, not a whole native
TIFF or prior-binary equivalence certificate. The primary cue changed144504
scored collapsed samples; no per-frame weight/energy observer was added.

## Execution and bindings

Commands actually run, from the repository root (Python3.12 with installed
dependencies, two workers for the numerical child):

```
python -I -B experiments/native-pyramid-profile/build.py --green-cue --output-dir experiments/native-green-cue/build-1
python -I -B experiments/native-green-cue/run.py
```

Fresh release compile:99.140 wall seconds,191.953125 aggregate child CPU seconds.
Numerical test:2.890 wall seconds,4.890625 child CPU seconds,10,346,496 bytes
peak Job commit. Test exit101 is the final scientific rejection assertion;
terminal Job accounting is complete, with no time/memory intervention or cleanup
error. No numerical rerun. These times are not a native-stack speed benchmark.
A preceding Python launch with `-S` failed importing tifffile before creating the
build directory or starting Cargo; it was corrected to the normal runtime.

Test executable SHA256:
`b64a90f9e3dc0554c289404077574eeb5c0641fae8c487af0ff86e639f89882f`.
Measurement103554 bytes, SHA256:
`465c18ce35ae70bb58536c55f3b4d1d11ae678520c7dc8d8939eb21692289e48`.
The JSON retains all78 outputs as metric rows, paired delete-one values,
controls and the79 failures; it does not retain full reconstructed images.

Build invocation records the earlier charter HEAD because an abandoned empty
Git index lock postponed the source commit. The unchanged lock had no Git
process on two checks and allowed exclusive read-open; it was moved intact to
abandoned-index-lock-1.bin. No tree reset or unrelated edit was performed.
`build-1/committed-source.json` proves all14 declared compiled source bindings
match the eventual source commit byte for byte. Original build receipts remain.

## Program decision

Close this exact finest-band replacement. Do not retune its thresholds, blend
weight or stimulus after seeing these results, and do not send it to a real RAW
ladder. The C12 information channel is not refuted by this failed integration.
A future approach must explain how it protects individual textured outputs and
retains low-frequency selection before it earns another experiment. Current
C12 commissioning remains incomplete; SOTA quality and fair end-to-end speed
remain unestablished. Original corpus unchanged by this allocation: it read no
original images. This is not a whole-corpus hash audit.
