# Independent pre-photograph execution review

MEASURED receipts, independently read without running a build, test or RAW job.
The full299 observation is still in progress at this review; no full-baseline
identity or photographic gain is claimed here.

The fresh build log contains both `Compiling strehl-core` and `Compiling
strehl-cli`, exits successfully in186.328s, and retains test executable
`f1953bc3bbc53c11bb502c326e3a95b25ef25d94786bde19b57ec955eb7566ef`.
The inspected build bindings match the reviewed adapter5ebb49dc, shared
implementation15eb9c44, driver1748eaa1 and observational plan9529c92e. The
review itself landed after build source collection and is **not** in that
binding set. Its separately retained SHA256 is
`429f34faef69d6a8f2e1092013ca9d90659075e4acd52a49db1769ae8f7f7bde`;
it names the same frozen numerical/driver sources. Do not describe it as a
build-bound file or silently amend the existing source receipt.

The same executable reran both instruments in2.641s. The entire twelve-case
screen is byte-identical to the rejected original, SHA256
`a63516111176f8b68a2f3d433ca596f672ea0a02823f71e298c92be546ee9144`.
The false quality qualification is preserved. Thus the general failure is
reproduced, not overcome by successful process exit or a new constructor.

Source149 cost completes successfully in4.078s with terminal job accounting
and no cleanup errors. It uses the full6468x4300 output/crop and original
source149/299 probe identity, while the prior has one source. The active-u16,
known4, guide, variance and beta agree with source149's retained full baseline
evidence. Canonical and candidate weight hashes are identical at every band,
with zero changed/zeroed weights. Both unsupported and supported prior regions
are present; coarse bypass counts include380614,16230 and7. This is therefore
an exercised full-size gather/probe/replay/finish/writer no-op, not merely a
count of source paths. It cannot test299-source competition or detail loss.

All four collapsed CFA hashes match between cost arms. Their RGB16 pixel hash
is identically `590c14fc7eaf5a6b3f8ddbbb853caf4dc8e6a7aaae4f49e20d819b666c3ee14a`,
and both TIFF files also hash identically. This one-source hash is intentionally
different from the required complete Current hash7df99f8f; the latter still
must pass on the full result before photographic interpretation.

The measured cost peak job commitment is5,035,110,400 bytes. Both source passes
sum to2.3172304s; recorded finishing takes1.3594176s. The fixed padded estimate
is1047.4242796s, below1500s, and peak is below12GiB, so the separate resource
gate permits the bounded full observation. Single-source working-set and time
do not certify complete-stack peak/time, and these operational readings are not
a speed benchmark. Full hard limits remain1800wall-s/7200CPU-s/16GiB.

Root commands reviewed are `chip-run.py build`, `controls`, and `cost`, using
the fresh `chip-build-1`, unchanged `chip-controls-1`, and `chip-cost-1` paths
from the frozen runner plan. No alternative recipe, parameter, frame subset
for the full pair, or quality threshold is introduced. The observational
question and known failure risks remain exactly those in observational-plan.md.

Receipt SHA256:

- build sources: cee784cec9fc7441c0ad45196822a81f9d774527c2ef3c2c19e8a45286736682
- build executables: 6bfc9b0e610d08936aa3abf0f8093a49649e8bb4fff2df7de80a16bf11626ce1
- controls completion: 87a09123cd1b9eed8e6d7d2725934e4fcf0b4b8ffccf8f4111ab187b6d17c570
- cost output receipt: 622830267a56f6476563ab616c80271c48db10db67314f5e9ccf3bdf0162d600
- cost resource decision: 4a0b04705cf7cc74b9e2691b9c1ba539207af0a5c7d34e4f11e0c1ca45286657
