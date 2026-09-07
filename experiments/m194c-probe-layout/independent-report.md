# M194c independent probe-layout verification

**VERIFIED within the tested software scope:** canonical consumed-site traversal
removes dependence on unused storage in both gather modes. Rechosen Probe
measurements and actual delivered TIFFs are invariant to relocated active origins,
row/bottom padding, poisoned unused sites, and an odd trailing active row/column.
Real seed, warp, active-sample, noise-model and WB interventions remain live at
their appropriate consumers. This does not establish SOTA, a quality improvement,
camera calibration, or universal optical validity.

Final evidence is [independent-run-4/result.json](independent-run-4/result.json),
SHA256 `15365fdf9ec6de78a65db5e9886d15b201bdea9ed4068eb5c7dbc154d4a8ee11`.
Both isolated gather processes passed five Rust tests, including the deliberately
retained expected failure, and the Python reader independently decoded all48
delivered TIFFs. All102 compiled product/included-test source bindings remained
unchanged. The author's tests were not read or copied. The final preregistration
was written after accidental inspection of the candidate helper during context
restoration; the independent choices and semantic corrections were communicated
before implementation. This is not presented as a blind pre-edit verification.

## What was actually exercised

| Control | Result and admissible interpretation |
| --- | --- |
| Packed legacy RNG sequence | Six combinations of70x46/118x82 and indices0/17/43 matched the frozen old function at every sample. This is sequence lineage, not RNG or camera calibration. |
| Relocated/odd-tail RNG | Twelve distinct layout comparisons matched every consumed site and retained every outside address. Old traversal disagreed at3189–3205 of3220 sites and9576–9619 of9676 sites; the old failure had ample power. Each new seed also changed samples. |
| Actual Probe | Per gather,80 exact beta comparisons covered274x190 native, full/cropped analysis, all five nonlinear transforms and two requested band limits. Forty seed comparisons across both gathers were live; nonidentity warp was live. Actual normal beta contained two finite bands; tiny native28x18 returned empty. |
| WB/source semantics | Noninteger fullres Probe beta changed under WB[1.15,1,1.65]→[1.9,1,.7]; per-CFA-plane gather beta did not, matching its API. Replacing template samples left beta identical, because Probe intentionally replaces them. |
| Actual writer | Per gather,24 delivered CameraLinear TIFFs:12 full274x190 and12 cropped224x156. Four origin/padding/tail/poison variations per domain matched baseline pixels and complete bytes. Single active green photosite+500DN, all-active+200DN, injected noise model, WB and warp interventions each changed pixels and bytes. Across both gathers this is16 layout equalities and20 delivered power comparisons. |
| Stats flags | Eight byte/pixel equalities across the two flags and four gather/domain cases. **Inert option controls only:** `run_pyramid_prepared` does not consume these estimator stats flags. They are not active diagnostic commissioning or evidence for a new observer. |
| Direct pooling and lifecycle | Small16x24 pooling refused;32x30 finite field pooled exactly4; injected interior NaN propagated; Probe invalidation cleared its vector. These are software/helper controls. |
| Corrected component power | With the explicit `next_frame()` lifecycle, checkerboard None/empty length fallback outputs agree. Ordinary-floor interior sites are3110/2890; huge-floor mean sites are3052/2948, exactly the independent arithmetic mean. Changed variance is live. Raw NaN is a core fault injection yielding that mean, not the production caller's white-floor fallback. |

The two requested band limits3/6 are capped by these small dimensions to the
same available depth. They are not independent demonstrations at different
realized pyramid depths. The normal measured two-band case and the tiny empty
case are distinct. A normally measured band has two remaining descendants of
extent>=8, hence extent>=29 and at least23x23=529 pooled samples, exceeding256.
The plan for a small valid finite Probe to produce a sample-count NaN was
therefore rejected before execution. No impossible physical NaN plant was run.

Both production gather implementations read complete quads of
`2*full.width` by `2*full.height`; PlaneGeometry floors odd active dimensions.
The repair fills that same extent in active-relative row order. Analysis Crop
changes extraction, not the RNG origin. Odd trailing active sites are outside
the consumed extent, and both their values and padding remain untouched.
Absolute storage origin does not redefine the local RGGB parity. These source
observations support the scope of the exact numerical controls, not a claim
that arbitrary invalid Frame storage is accepted.

## Retained failures and corrections

1. Author-run-1 failed compilation on my test-only SHA2 0.11 hex formatting API.
   The correction formats digest bytes individually. Its build log is retained.
2. Independent-run-1 passed sampler/Probe/writer groups but failed the direct
   finite-floor power fixture in both gathers. The initial attenuation argument
   was unmeasured and is **withdrawn**. None/empty/NaN equalities in that fixture
   were unpowered and do not verify fallback correctness.
3. [Amendment1](independent-amendment-1.md) separately preregistered a checkerboard
   at the unchanged dimensions/amplitudes/noise/gate. Independent-run-2 also
   failed that component. Inspection identified the actual harness mistake:
   omitted `FrameWorkspace::next_frame()` preserved frame0's cached colour
   pyramid while later luma changed the weights. Production BandWorker does
   call this API. Curie independently confirmed the missing lifecycle call.
   The original omitted-reset harness stays as a named expected-failure test.
4. [Amendment2](independent-amendment-2.md) corrected only that lifecycle in the
   additive arm and corrected the NaN scope. `BandMerge::beta_for` returns a
   supplied beta without a finite check; production BandWorker truncates the
   finite prefix before calling it. The prior core-white-fallback expectation
   was wrong. No sample, dimension, threshold or model coefficient was tuned.
5. Independent-run-3 refused before any execution because a later full-suite
   rebuild overwrote the compiler-artifact target named by the earlier build
   record. The pinned copy was intact, but the strict live-artifact binding
   correctly failed. Final author-run-5 build/copy occurred after suite/lint;
   independent-run-4 then verified the exact artifact and ran successfully.

All failed outcomes remain in their original directories. The separate
[artifact audit](independent-artifacts-2.json) decodes the48 actual TIFFs from
failed run2 and passes its layout/power comparisons without treating the failed
component test as successful. The final suite is not retroactively a green
label for earlier attempts.

The ordinary `STREHL_GATE_FLOOR=debug` branch indexes beta[0] in its identity
report. A tiny empty Probe could reach that access; it was not executed here and
is outside this traversal repair. Floor was unset throughout this verification.
The existing stats flags do not supply active diagnostic proof; no new observer
was added by the product change. Parent owns the full fixed40 M194b readout and
its independent comparison, including any cross-version quality movement.

## Reproduction and bindings

Run from the repository root, preserving a fresh output directory:

```text
python experiments/m194c-probe-layout/independent-run.py --build-record experiments/m194c-probe-layout/author-run-5/build.json --build-sha256 8a4876025f515569b12baec9370513a2bcae779a199ce83cd790f4710faa68c0 --output experiments/m194c-probe-layout/independent-run-4
```

The saved command ran on Python3.12.10, NumPy2.4.4, tifffile2026.5.2. The runner
clears ambient STREHL settings and sets `STREHL_DEFECT=off`, `STREHL_FIX_CA=off`,
`STREHL_FULLRES_GATHER=0` then1, `STREHL_PYRAMID_WORKERS=2`, and
`RAYON_NUM_THREADS=2`. Each native process uses the exact independent module
filter with `--test-threads=1 --nocapture`. No capture was decoded. The sentinel
RAW paths were asserted absent.

| Artifact | SHA256 |
| --- | --- |
| Final independent-tests.rs | `72accd1598756d13e340947ded9c27f40c65420bd137c593b962131ddf8dc58d` |
| Final independent-run.py | `e1932ab3293ef73d8c179302c2e019787c68a7c0ec71f3d5f359bc87da44bde6` |
| Author-run-5 build.json | `8a4876025f515569b12baec9370513a2bcae779a199ce83cd790f4710faa68c0` |
| Exact copied native test executable,9617920bytes | `77aca47cfdd352eb5eefb936f5bf0126af174ac9f49fe698a1c713755dd8aa27` |
| Plane gather full baseline TIFF | `d1ce8596684100ef7bd7e022161b5cd49b80108a289cb3f70ed6946dc5ca4d86` |
| Plane gather cropped baseline TIFF | `f62a0a0c46333f2b5f81b6b244937cba153fba20b41fad47aff50b94ed7cbbef` |
| Fullres gather full baseline TIFF | `eea98d1d80c9805042a8ecbd4629d720c5f001e11a048448d683f80ed49f2070` |
| Fullres gather cropped baseline TIFF | `1eb75211f1f9ee5870c94b55e31e0631949e86dff5e77581e5a8b9d34ee55151` |

Each per-gather JSON contains actual TIFF paths, size, shape, independently read
pixel SHA256, Software/ImageDescription, and extrema. Raw logs retain sampler
failure counts, actual beta bits and component selection/mean evidence. The
root's final comparison must use its own candidate build binding; this report
does not substitute this independent test executable for that scored artifact.
