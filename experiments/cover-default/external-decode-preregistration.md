# COVER Q1 amendment — external-decoder identity

Frozen after the original COVER result, but before decoding the Q1 RAW with an
external implementation or comparing any external prediction with a render.
This is an amendment, not a rewrite of the original preregistration.

## Why the first Q1 is insufficient

The first Q1 compared `strehl stack` with alignment disabled against
`strehl stack` with an identity sidecar. Those arms proved that adding Crop's
identity warp and window did not change the bytes produced by the common
decode, pyramid, and output path. They did **not** prove that the common path
still represented the RAW samples correctly. A deterministic common error
could cancel.

The first Q1 is therefore retained as an internal differential control and
downgraded from an external identity proof. This amendment supplies the
missing external predicate with rawpy/LibRaw, whose decoder and RAW buffer do
not share code with strehl/rawler.

## Evidence already known

The candidate renders already exist and their hashes are frozen here so a
later result cannot select a more favourable rerender:

| artifact | dimensions | SHA-256 |
| --- | ---: | --- |
| copied `DSC00020.ARW` | raw | `77AAEC0B9958B97E8B712332E2A3C67013373623B8BCF52CC5C88B912F0070CA` |
| one-frame identity sidecar | — | `4C858562AF44E0646D9E45E445DEBAC17C6C9E4FEC28C325B9E653EB391E6C05` |
| direct TIFF | 3516x2344 | `447F1A6EF5212CECCE4890C0823C50E3D66DC65ED23733BC957F0217C31BFCF4` |
| no-fit TIFF | 3516x2344 | `5836AFBBE435760B366E042345D987F96C36CD31ACEE0C3C0AB18D5A2999E436` |
| Crop TIFF | 3506x2337 | `9033579443C98A769770F71A239104E3529F53FB152308080A7EE4AC1C72C972` |
| Scale TIFF | 3516x2344 | `23A385AC2E5C0C70B1F436C3D9E5F3C13E905FB8DE9A177AA1D988DAFDBE2FC2` |

Their internal results are also known: Crop is the exact `(5,4)` window of
direct and no-fit, and Scale differs. The external result is not known.

Prior independent-decoder work establishes the contracts to expect, without
establishing the answer:

* rawpy exposes an RGGB `4688x7028` visible mosaic at the same origin as
  rawler's `4688x7032` active representation;
* both report black 512;
* LibRaw exposes container white 16383, while this camera's independently
  established usable linear white is 15360;
* the four extra rawler columns are outside this comparison. Crop uses sensor
  columns 10 through 7021, wholly inside rawpy's 0 through 7027 overlap.

## Fixed external construction

Use the copied Q1 RAW under `D:\strehl-out\cover-default`, never the capture
tree. Inside a rawpy context manager, copy `raw_image_visible`,
`raw_pattern`, `color_desc`, `black_level_per_channel`, `white_level`, and
`camera_whitebalance`. Decode twice; the copied mosaic hashes and metadata must
agree.

The loader gate requires:

* shape `(4688,7028)`, dtype `uint16`;
* `raw_pattern == [[0,1],[3,2]]`, `color_desc == RGBG`;
* all four black levels equal 512;
* finite positive R/G/B camera white-balance values;
* the requested sensor rectangle is inside the external mosaic.

Failure is a failed instrument, not evidence for or against Crop.

For output pixel `(x,y)` in the Crop TIFF, define external sensor coordinates
from the already-fixed Crop origin `(ox,oy)=(5,4)`:

```text
R  = raw[2*(y+oy),   2*(x+ox)]
G1 = raw[2*(y+oy),   2*(x+ox)+1]
G2 = raw[2*(y+oy)+1, 2*(x+ox)]
B  = raw[2*(y+oy)+1, 2*(x+ox)+1]
```

Use float32 arithmetic explicitly. Subtract float32 512 from each site and
clamp each colour to non-negative; green is
`0.5f32 * (G1_black_subtracted + G2_black_subtracted)`. Normalise rawpy's
camera white balance by its green value and cast the three gains to float32.
For each R/G/B value `v` and gain `g`, independently serialize:

```text
u16(min(v * g / float32(15360 - 512), 1.0) * 65535.0 + 0.5)
```

with float32 at every arithmetic step and truncation to `uint16`. This is a
fixed camera-linear encoding rule over externally decoded sensor integers; no
value is fitted from a candidate TIFF.

Construct the corresponding external full-overlap prediction for rawpy's
`3514x2344` quad grid. Compare direct, no-fit, and Scale only over that overlap.
Compare Crop over its full `3506x2337` extent.

## Commissioning before reading the result

1. Verify two independent rawpy calls return identical copied-mosaic hashes.
2. Exercise the fixed float32 encoder on literal RGGB quads whose black
   subtraction, green mean, gain, clipping, and final integers are calculated
   separately as scalar closed forms. A channel-order or pre/post-black gain
   plant must make that fixture fail.
3. Take the real Crop TIFF as an immutable render artifact `C`. Compare `C`
   with a copy whose centre green sample is XOR `0x8000`. That comparator call
   must report exactly one differing sample and max absolute difference 32768.
4. Replace that plant with XOR `0x0001`. Against immutable `C`, it must improve
   max absolute difference to 1 and RMS toward zero.
5. Restore the copy. Against immutable `C`, all statistics must return exactly
   to zero.
6. Shift the external Crop origin by one quad in x. Its comparison with Crop
   must differ on more than 1% of samples, and returning to `(5,4)` must improve
   every reported statistic. The correct-origin result is not printed or
   interpreted until the loader, scalar fixture, candidate-mutation, and
   wrong-origin controls have passed.
7. The existing Scale TIFF is a whole-render positive arm: the external
   comparison must detect it as different rather than merely reproducing a
   synthetic mutation.

The render-path plant is applied to a copy of the actual serialized candidate,
not to the external generator. The expected array and candidate therefore
cannot share the planted assumption. The immutable-C comparison commissions
the integer comparator without presupposing whether C agrees with the external
decode.

The literal encoder fixtures are frozen as:

| raw `(R,G1,G2,B)` | gains `(R,G,B)` | externally calculated RGB16 |
| --- | --- | --- |
| `(4224,4224,11648,15360)` | `(2,1,0.5)` | `(32768,32768,32768)` |
| `(7936,512,512,15360)` | `(2,1,0.5)` | `(65535,0,32768)` |
| `(16383,15360,15360,16383)` | `(1,1,1)` | `(65535,65535,65535)` |

These follow from black-subtracted values 3712/7424/11136/14848, all exact
binary halves or quarters of the 14848 range where used. They are fixed here,
not generated by the implementation that will be checked.

## Predicates and reporting

Primary identity predicate:

* Crop versus the external prediction must be bit-exact over all
  `3506*2337*3` serialized samples: max absolute difference 0 DN, RMS 0 DN,
  differing fraction 0.

Required cross-checks:

* the direct TIFF over the external `3514x2344` overlap must be exact;
* the no-fit TIFF's `(5,4,3506,2337)` window must be exact;
* Scale over the external overlap must differ on more than 1% of samples.

Report max absolute difference, RMS, and differing fraction for all comparisons
and separately for R, G, and B. Report the external RAW mosaic SHA-256,
metadata, normalised white-balance gains, and expected-array SHA-256.

Any non-zero Crop result fails the requested end-to-end bit-identity claim.
Direct and Crop disagreeing with the external prediction in the same way may
diagnose a common downstream transformation, but it cannot be promoted back to
a pass. The existing negative default decision remains negative regardless:
external identity is necessary, while the already-measured 256 px border
hazard independently blocks Crop.

## Capture and host limits

No holdout is touched. `D:\personal\macro` remains read only. No new capture
render is needed. The external decoder reads only the private copy of the
already-authorised 109 reference frame. All numerical-library thread variables
remain capped at 8.

The host owner granted another lane an exclusive quiet window through
2026-09-03 09:59:55 local time. No decode, render, merge, build, or test may run
before that expiry.
