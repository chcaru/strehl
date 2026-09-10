# Initial device-coordinate hardware refusal

MEASURED. The Rust release build completed successfully with fresh Compiling
lines for the CLI and GPU crate, taking170.063 wall seconds. The first
descriptor process then refused hardware admission in0.438 wall/0.171875 child
CPU seconds, before compiling/submitting the GLSL coordinate kernel or
executing any of the37 descriptor requests, four API refusals,18 image controls,
or native renders. Do not describe these unexecuted cases as failed comparisons.

Actual command:
~~~powershell
python -I -B experiments/native-pyramid-profile/build.py --gpu-gather --output-dir experiments/native-gpu-gather/build-native-3
python -I -B experiments/native-gpu-gather/run-device.py
~~~

Build source bfef41c11e17e892141a0342d918972e66c70ccd.
CLI SHA25689cf0f343070f60ed4d6818dd38112e93d9b056761b9188602446700ece481c2;
tests SHA256cd8668a30744ff94c8e32a1e581c07bb14182dacdbd75785e0b7638aff1cb780.
The descriptor report is retained at run-device-1/device-descriptor-results.json,
SHA256c376ff89636a11546d929d34b3238d3eea6706d872c75c7619d3ea437c3c4786.

The selected Vulkan adapter reports shader_f64=true, signed-zero/Inf/NaN
preservation for64=true, RTE32=true, RTE64=true, but denorm-preserve64=false.
Vulkan API numeric4211029; denorm and rounding independence both1.
The original all-input device implementation correctly refuses this absence.
Status remains CONTROL_FAILED/hardware refusal; numerical equivalence and
device-coordinate speed remain unmeasured. No later process was launched.

## Prospective guarded alternative

DERIVED proposal, independently reviewed before the next run: transforms whose
every finite nonzero coefficient has magnitude at least2^-900 have binary
coefficient quantum at least2^-952. Pixel positions and centres are exact
integer/half-integer values, so the multiply/add/subtract graph uses a lattice
no finer than2^-953. Rounding can coarsen it but cannot create a smaller nonzero
result. All finite nonzero intermediates then remain above the f64 subnormal
range. Signed zero, NaN and Inf still require their advertised preservation;
RTE32/64 and NoContraction remain mandatory.

The adaptation must preserve the complete existing image-input contract:
unsafe smaller coefficients use the unchanged CPU Parallel256 coordinate path,
with the returned actual schedule and a visible fallback marker. A direct
device-descriptor-only request must refuse unsafe coefficients. The native
timing harness requires device completion for every call, so fallback cannot
quietly qualify as a device timing win. New threshold/cancellation/subnormal/
fallback controls are prospective and separate from the fixed37+4 and18.
No criterion is relaxed, and no old failure is rewritten as a pass.
