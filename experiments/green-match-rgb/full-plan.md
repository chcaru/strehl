# Complete RAW replay after the fixed generated screen

The generated-only two-test screen admits one photographic replay, subject to
independent review. It does not establish a photographic gain. Retain the same
2-sigma source-green acceptance, uniform whole-tuple average, and exact baseline
fallback. Do not tune parameters from the photograph.

Use all 70 original vitamin-C ARWs, the existing held warp map and exact native
crop 6920x4612, unchanged CA profile, white balance, seven-band merge, canonical
four-chunk baseline reduction, and fixed tone. First write the current baseline;
its RGB16 output must be identical to the retained phase-packed experiment's
baseline. Then replay the RAW sources once into streaming source-colour sums and
counts. No aligned image volume or original-file output is allowed. This is a
prototype with an additional RAW pass, not a speed improvement claim.

The generated helper's maximum accepted geometry may expand to this sensor's
active quad extent for the full replay; its arithmetic must remain unchanged.
Rerun both generated tests after the adapter build and bind that result to the
same executable before the full run. Freeze source, config, map, executable,
input sizes/times, invocation, and bounded-process completion. Limit the full
pair to 600 seconds wall time, 3600 CPU seconds, 16 GiB committed memory and
eight execution threads. Inputs remain read-only.

Root and an independent reviewer inspect the complete outputs for overall
changes, and the same five previously frozen 384x384 native regions for fine
detail. The two photographed colour-fan regions are the intended targets;
clean backgrounds and real crystal edges are regression controls. Reduced
colourfulness alone is not success: desaturation, blurring, lost texture,
block boundaries and an increased occlusion halo all defeat a gain claim.
Brightness/colour differences have no neutral-reference truth here, so do not
call a global colour shift more accurate. These ROIs are photographic controls,
not calibrated flat noise patches.

Provide complete native PNGs and RGB16 masters whenever presenting an
improvement to the user. Native crops are diagnostic additions only. Preserve
the complete files even if the candidate is rejected. Any retained benefit
still requires transfer to a different actual stack before default promotion;
no local gain or synthetic error reduction licenses a SOTA claim.

Pre-colour-replay correction after the first baseline: comparing whole TIFF
hashes across builds also compares the Software tag. The first run stopped
because tag305 recorded the newer committed revision, although independent
TIFF decoding found every one of 95,745,120 RGB16 samples identical. Keep the
original file and its hash as provenance. Replace only that file-container
guard with decoded RGB16 type/dimensions and a fixed little-endian pixel hash
from the original reference. The outer runner additionally compares both
decoded arrays exactly. No image arithmetic, threshold, acceptance criterion
or photographic region changes. Preserve the refused run and original adapter
under `full-first-freeze`.
