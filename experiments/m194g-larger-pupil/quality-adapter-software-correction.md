# Build stamp and measurement writer correction

2026-09-07. Source/retained-metadata inspection only; no new control, image
decode or quality calculation. The first actual intended12 read remains failed
at independent-production-bridge-read-1, with original source snapshots and
adapter-controls.json SHA45ecf0c0b418033323d97b296c498e114f6527e3c76affa05838c2758feb7c98.
Its one completed population check precedes the first genuine entry refusal at
validate_plan's actual executable identity/software comparison. No TIFF decoded.

The expected string conflated two deliberately distinct product constants.
Cargo.toml supplies workspace package version0.0.0; strehl-cli inherits it.
main.rs SOFTWARE concatenates that version and STREHL_BUILD_ID, and the bridge
plan explicitly writes crate::SOFTWARE. The source-bound build2 compiler log
line253 has exactly the strehl-cli package's build-script-executed message,
package_id path+file:///C:/dev/blog/death-of-software/projects/strehl/crates/strehl-cli#0.0.0,
and environment STREHL_BUILD_ID=48f69d82b419. Thus this exact compiled executable's
plan string is `strehl 0.0.0 (48f69d82b419)`. Its copied executable SHA is
1a96f3a472288c1c057e16df4cd8a4d04ed6a4a5a1cc2c80adbd67d69df2ccd1.
The compiler log SHA is48d003eea110ce36563a9847eea1f42b51f3a18dd86caa8975ec04ca9f5131c7.
This uses the retained actual compiler message, never the current Git head.

image_out.rs separately defines MEASUREMENT_SOFTWARE as the package-only
`strehl 0.0.0` for CameraLinear measurement files. This avoids introducing a
source-stamp difference into measurement byte controls; the full compiled
identity is independently recorded by the executable and invocation bindings.
The adapter's TIFF receipt literal and the independent TIFF parser therefore
remain unchanged. Only validate_plan's build.software expected literal changes.
No prefix matching, arbitrary stamp acceptance or relaxed metadata types replace
the original exact comparison.

All twelve retained plans share the exact stamped build identity above; all
twelve saved output receipts report the package-only measurement string.
Source-only metadata scanning also checked the displayed sensor, normalization,
injected noise, represented WB, environment and floor-witness records, both
config modes, off/count/placebo counters, endpoint original/local indices,
common native300x226 crop at(10,8), and actual one/two-value floor banners.
No second literal discrepancy was identified. This is not an executed adapter
PASS or independent pixel read; the fixed59 controls and all12 independent
decodes still require the next separately committed command.
