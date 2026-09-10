# Guarded device coordinates after hardware refusal

This is a prospective domain adaptation following the preserved
run-device-1 hardware refusal; no descriptor or image case ran there.
Source/derivation and failure scope: device-initial-refusal.md and
device-guard-review.md. The complete image-input contract remains exact:
all12 precomposed transform coefficients are checked, and unsafe finite
nonzero magnitudes below2^-900 use the existing CPU Parallel256 coordinate
path. Report the actual schedule and fallback reason. Direct device-only
descriptor requests refuse unsafe coefficients. GPU image arithmetic stays
in the original protected f32 module.

The guard proof is specific to the current half-integer coordinate graph:
coefficients have quantum at least2^-952, products at least2^-953, and RTE
add/sub/*2 cannot produce a nonzero f64 subnormal. The device therefore no
longer requests unsupported DenormPreserve64. RTE32/64, signed-zero/Inf/NaN
preservation64 and NoContraction remain required. No arithmetic tolerance or
image-equivalence criterion changes.

Fresh build-native-4 uses the existing600wall/1800CPU/8GiB/16MiB compile bounds.
Run-device-2 executes three separate processes in order:
1. New guard controls: threshold neighbors/signs, all12 coefficients,
   tiny/subnormal/cancellation cases, and exactly4 requested-Device vs
   Parallel256 whole-output comparison pairs. Actual fallback must be live.
2. Original37 device-descriptor requests plus4 API refusals, unchanged.
3. Original18 image controls, unchanged.

Each process retains120wall/120CPU/4GiB/4MiB limits; aggregate360CPU/256MiB
artifacts. Both original/submitted f32 image hashes must equal run-4, through
the actual compiled reports. Compilation/hardware/fallback evidence and
first failures must be retained. No later process follows a failure.

After all three pass, execute the existing device-native-112-1 three
off/on/placebo renders, then device-native-109-1 CPU/GPU/GPU/CPU, exactly as
execution-5.md defines. Bind this build/test executable and successful report
hashes; primary image schedule must be Device256. Every native GPU call must
actually complete Device256, including the green probe. A fallback aborts
timing admission, not a quiet substitution. The on-log must include both
held image and coordinate compiled-module hashes. Retained TIFF budget4GiB
and selected original-input metadata/map checks remain unchanged.

No new corpus, alignment solve, parameter sweep or image-quality claim follows.
If the guarded mechanism is exact but not reliably faster, close the transfer
hypothesis. This allocation does not authorize tuning until a speedup appears.
