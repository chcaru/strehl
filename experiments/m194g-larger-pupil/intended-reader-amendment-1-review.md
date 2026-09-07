# Intended bridge reader: first-run refusal and scoped repair

The exact release1 command frozen at6dc536bf returned exit1. The complete
failed result and source snapshots remain in independent-production-bridge-read-1.
The first population check passed; the first actual plan failed the verifier's
software-string check. No TIFF was decoded and no quality metric was computed.

The verifier expected the TIFF's package-only `strehl 0.0.0` string for the
plan's executable identity. Those are distinct product fields. The compiled
bridge uses crate::SOFTWARE in its plan; CameraLinear image output uses
MEASUREMENT_SOFTWARE. The retained actual compiler.log line253 identifies
strehl-cli#0.0.0 and STREHL_BUILD_ID=48f69d82b419, independently predicting
`strehl 0.0.0 (48f69d82b419)` for this exact executable. Actual saved plans
carry that value. Exported TIFF metadata still requires `strehl 0.0.0`.

Root independently inspected the actual failed child, the compiler line and
both source call sites. The proposed repair changes only the plan's exact
build-specific expected string. It does not relax executable/file hashes,
output software checks, geometry, population, controls, numerical criteria,
noise seeds or product settings. A new committed release and fresh directory
are required before rerunning all59 controls and all12 independent reads.
The failed first attempt is evidence about the verifier interface, not product
image quality. No gate is issued by the first attempt.
