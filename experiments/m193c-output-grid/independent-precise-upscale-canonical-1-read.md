# Independent canonical precise-upscale outcome audit

2026-09-07. **VERIFIED complete private control experiment.** The canonical comparison repair passes its five metadata cases, and all seven scientific control groups pass. On this one known-rotation fixture, explicit precise upscaling removes the roughly four-native-pixel systematic displacement seen with explicit false. This is a finite effect of the detector option on the complete private extraction/matching pipeline. It is not evidence of real cross-focus accuracy or a universal detector offset.

## Independent literal-truth result

The auditor uses the known native-centre permutation `x_ref=3071-y_source`, `y_ref=x_source`, derives all four source-corner errors with integer Q32 arithmetic, and scores every captured landmark without fitting or selecting an inlier subset.

| Actual arm | Captured rows within 2 native pixels of truth | All-row RMS, native pixels | Median reference-minus-truth offset, native pixels | Largest source-corner error, native pixels |
|---|---:|---:|---|---:|
| explicit false | 0 / 256 | 4.003144935 | [4.0, 0.0] | 4.049269136 |
| precise true | 255 / 256 | 0.201947836 | [0.0, 0.0] | 0.001551253 |
| restored false | 0 / 256 | 4.003144935 | [4.0, 0.0] | 4.049269136 |

The true arm's four corner errors are **0.001465364, 0.001551253, 0.000768131, and 0.000921478 native pixels**, each inside the unchanged one-pixel bar. **One true-arm captured landmark remains outside two pixels of literal truth.** Its fitted holdout RMS is 0.059345100 native pixels on 128 held-out inliers; that selected fitted-residual statistic is distinct from the 0.201947836 all-row truth statistic. No metric here measures sharpness or noise.

False and restored-false feature records and entire canonical outcomes reproduce the original cache, including coordinates, descriptors/key hashes, split labels, inliers, maps, metrics, guard and site evidence. The true arm changes the feature/match population: exact joint sites are **239**, versus **237** in each false arm. Each arm has **10 joint groups crossing calibration/holdout**. Independent one-pixel adjacency gives the same counts, with no transitive over-radius components. The option affects the complete pipeline; these are not paired residuals on an identical correspondence set. Distinct sites do not establish statistical independence.

## The comparison repair has actual rejection power

Before the sole private decode, the subject commissioned the same whole-record comparator used by its reproduction checks. The auditor independently reconstructs the five cases from the actual cached outcome and compares every reported byte length, SHA256 and equality result with complete-record serialization:

- Converting 20 shared coordinate points from lists to tuples changes Python equality but preserves complete canonical bytes.
- Adding one Q8 unit to the first actual reference x-coordinate changes canonical bytes and is rejected.
- Restoring that coordinate restores equality.
- Adding one Q32 unit to actual map tx changes canonical bytes and is rejected.
- Restoring tx restores equality.

All five actual directions are **equal, unequal, equal, unequal, equal**. No scientific field is omitted and no tolerance is introduced. The fresh false reproduction saves and passes all **three** complete comparisons: features, frozen signature, and whole outcome against cache. Restored false saves and passes all **five** comparisons against the fresh false and original cache. The auditor recomputes every comparison independently from complete saved records, including the additional two whole-record authority comparisons to the failed preceding attempt.

The preceding `precise-upscale-1` remains a recorded failure. This new result does not reinterpret its false flag. The versioned repair explicitly moves equality to the serialization boundary and demonstrates both its null and its sensitivity to the smallest represented coordinate/map changes.

## Scientific controls and actual execution

Exactly **one private fixture decode, six feature extractions, six factory calls, and five matcher calls** occurred. All three arms record two constructor calls with the same five frozen SIFT arguments and only their explicit boolean option differing; every factory restoration witness is true. The true observation is followed by the fixed restored-false arm before true geometry admission.

The active map destroyer changes only true tx by **two native pixels**. Its four known-corner errors are about **1.999 to 2.001 native pixels**, so the same one-pixel oracle rejects it. Actual true off/count/placebo frozen signatures have identical SHA256 `8f664489734e91ea230f0692f060625c31d48bf503231a04eecf30c58feab028`; count reuses the existing true call, with no extra extraction. This is the exercised private observer path, not a universal observer guarantee.

Parent and worker both exit **0**, with `COMPLETE_PRIVATE_PRECISE_UPSCALE_CONTROL_ONLY`, no errors or finalization failures, and unchanged source checks. The Job reaches terminal accounting with two processes observed, zero active, no termination attempt, and no helper/cleanup error. Job CPU is **5.359375 seconds**, wall **5.468 seconds**, and peak committed Job memory **170,024,960 bytes**. All configured, local and global bounds pass; these are resource records, not comparative timing claims.

## Authority and accounting

The new closed plan, explicit implementation/comparison tags, source closure, failed-attempt audit chain, actual parent/worker arguments and request all check. Both preceding failures and every old source binding remain intact. The new inventory is **18 files / 1,164,283 bytes**, confirmed separately using `Get-ChildItem -Recurse -Force -File`. All output bytes are charged as files and metadata. No snapshot or image file was written.

Actual final totals are **510.46875 CPU seconds / 596.4671815000002 internal wall seconds / 3,955,495,913 file bytes / 30,295,267 metadata bytes**. The conservative outer-wall carry is **596.5200758 seconds**. The new 20-CPU-second/30-wall-second/1-MiB preparation allowance and all earlier charges remain carried without refund.

The auditor rechecks **228 metadata/source files** and performs only extent/identity checks on the private TIFF. Its pixel payload is not reopened; image/descriptor/key hashes remain opaque producer witnesses. The audit imports only its own pinned independent helper, with no subject or numerical-library import and no decode, extraction, matching or fit. No real-image phase exists in this source/request.

## Reproduction and limits

The audit source was completed after the actual completion notice. This is disclosed retrospective independent verification, with all-row truth scoring, integer corner arithmetic and one-pixel site grouping chosen separately from the subject. Ten inherited arithmetic/site commissioning cases ran before result checks. The actual complete branch is exercised; retained-failure branches in this auditor were not exercised by this outcome.

Actual command ran once, exit **0**, no stderr:

```text
C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe -B experiments\m193c-output-grid\work\independent-precise-upscale-canonical-1-audit.py --plan-sha256 a9f194a8cfd43c94a54ca7351aebf6a8c01658f1b96d9a987728adf1a44b0a90 --result-sha256 37d820048e59c04026d00f02a10282672585284aed8891592e45ddf3214ece03 --outer-sha256 c6f6f0c6731ad9e2e09e4302d72a1ac21420d62b23e36285cfd536c02973ace4 --console-sha256 6fd7b0d814bb32d037da09cec859999f35b341fc8eabe46adfb0eddcd5fbe37d --exit-sha256 13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354
```

- Source `work/independent-precise-upscale-canonical-1-audit.py`: **28,881 bytes**, SHA256 `52e52c011ff83c1c2f590cbd4da46b03b63619e22ac1d335a71a6b20c66fb09d`.
- Result `work/independent-precise-upscale-canonical-1-audit.json`: **25,983 bytes**, SHA256 `471c68d50e1cca2804eec32e38756d06b3e0d8db79716de1450fb038ff197b5e`.
- Schema `m193c-saved-precise-upscale-canonical-audit-v1`; status `PASS_SAVED_PRECISE_UPSCALE_CANONICAL_OUTCOME_AUDIT`; `subject_complete=true`.
- Audit-internal CPU **0.4375 seconds**, wall **0.4435027 seconds**; enclosing invocation **0.5038394 seconds**.

The guard remains **UNQUALIFIED_FOR_COARSE_LATTICE**. No consumer manifest, overlap/placement admission, real-scene quality result, default change or SOTA claim follows. A later real experiment must explicitly declare the altered detector setting and earn its own evidence.
