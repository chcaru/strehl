# M193b prospective consumer and bounded constructor preregistration

Written before implementation, 2026-09-07. This is a prospective implementation
beside frozen M193 v1, not an amendment of its measurements or coverage status.

Falsifiers:

1. The original same-focus TIFF fixture must reproduce the v1 manifest exactly;
   its identity grid must retain 99918/99918 and its cropped grid must retain
   97188/99918 and FAIL. A changed fixture result rejects compatibility.
2. Stale or recomputed self-hashes must not admit a smaller, in-bounds denominator,
   incorrect area, foreign input/reference, changed transform or uncertainty,
   or a descriptor rebound to the altered digest under the original input binding.
   Any such admission rejects the repair. A self-hash is not external authority.
3. Duplicate JSON keys, nonfinite numbers, unknown fields/schema, booleans or
   floats in integer fields, malformed hashes, singular transforms, inconsistent
   counts/guards, and out-of-bounds rectangles must refuse before pixel counting.
4. Reordering inputs preserves exact v1 bundle/reference/manifest behavior.
   Duplicate paths and distinct paths with identical bytes preserve multiplicity;
   byte-distinct files with equal decoded pixels remain distinct inputs. Sorting
   retains the exact-byte tiebreak after equal digest and length. A one-pixel
   change must change the trusted input binding. Unsupported compressed TIFFs
   retain the v1 refusal; no new compressed-input schema is introduced.
5. Real path decoding must retain at most one decoded RGB array at once as N
   grows. Independent weakref instrumentation will contrast N=12 with v1;
   registration may be stubbed equally only for this lifetime experiment. This
   checks decoded-array retention, not peak RSS, native scalability, or feature
   accuracy. Real feature/registration behavior is checked separately.
6. Complementary-focus inputs that fail v1 registration must still refuse.
   Single-reference limitations are retained, never papered over by chaining.

The trusted registrar alone creates an immutable binding from input-derived
canonical manifest bytes. The candidate controls manifests/descriptors, not
registrar execution or the binding object. This Python API is not a sandbox
against arbitrary code execution, dishonest registrars, SHA-256 collisions, or
malicious concurrent writers. Streaming rehashes detect ordinary input changes
between passes; decoding reads one verified temporary byte snapshot at a time.

The consumer validates the trusted input denominator and output descriptor
structure. A well-formed false adapter/grid assertion is still an adapter
commissioning question. No adapter provenance, RAW coverage, native geometry,
holdout result, or scorecard closure is claimed by fixture retention.

Independent verification belongs to roadmap_audit, which re-chooses a non-square
scene, transform, malformed cases, and lifetime stimulus. The author will run
regression checks but will not label them independent verification.
