# M193 — independent geometry takeover review

**Disposition: DO NOT CLOSE blocker `(b)` or apply the routed readiness removals.**
M193 supplies a prospective geometry definition and a synthetic reference
implementation. It does not yet supply a validated product/comparator geometry
apparatus. Its overlap consumer also accepts a corrupted denominator under the
original hash and changes a field-of-view failure into a pass.

This is a takeover review of M193, not a new milestone. The root commissioned the
review. No frozen M193 algorithm, scorecard, product code, RAW file, candidate
output, or holdout was changed or consumed. The only new artifacts are this report
and `experiments/review-m193-geometry/`. Findings below concern the checked-out
artifacts at HEAD `cba20daef1b92e1c5b41d95df06a96c65c003051`; the existing M193
contract has an uncommitted status/precommit amendment, identified explicitly in
the provenance section.

## 1. The consumer can certify a changed denominator

**MEASURED on the frozen consumer path.**
`reference.py::validate_output_grid` compares the descriptor's saved overlap hash
to the manifest's saved `manifest_sha256`, but does not recompute the latter.
`output_retention` then obtains its denominator from the unvalidated
`common_overlap.width * common_overlap.height`.

Before execution, the challenge registered that changing the rectangle without
updating its hash must be rejected. The original cropped fixture supplies a live
failure; the original identity fixture supplies a live pass. The challenge then
changes only the manifest rectangle to an interior 20-by-20 region, retaining
the original overlap hash and the original cropped descriptor.

| Arm | Numerator / denominator | Result |
|---|---:|---|
| Original identity control | 99,918 / 99,918 | PASS, 100% |
| Original cropped control | 97,188 / 99,918 | FAIL, 97.267759563% |
| Cropped descriptor plus stale-hash 20-by-20 denominator | 400 / 400 | **PASS, 100%** |

The challenge independently recomputes the tampered manifest digest and confirms
that it differs from the stored digest. The failure therefore is not a legitimate
newly frozen overlap. The exact arm M193's denominator rule exists to prevent is
accepted by its consumer.

Two additional mutations also return PASS: changing the overlap schema to
`UNRECOGNIZED-OVERLAP-SCHEMA`, and changing `area_pixels` to 1 while leaving the
width and height unchanged. These violate the contract's stated unknown-schema,
hash, and count-partition failure conditions. `verify_freeze.py` checks the saved
fixture's self-hash, but that does not guard each manifest passed to
`output_retention`.

**Failure direction:** corrupting the population can manufacture a favourable
field-of-view result. The crop/identity controls establish both directions of
the score on the same consumer; this is not a mere string-presence check.

## 2. The output descriptor is not a product adapter

**VERIFIED by source inspection.** `make_output_grid` creates fixture hashes
from the literal strings `M193 fixture adapter` and `M193 fixture settings`, and
defaults the map and its residual to identity and zero. `validate_output_grid`
checks that adapter/settings hashes are lowercase hexadecimal, not that a real
artifact exists or establishes the asserted map. Substituting two all-zero
hashes passes the same consumer in the challenge.

That behavior can be acceptable for a low-level schema helper. It is not evidence
that a real stacker's output follows that map. No production adapter or renderer
was exercised by this review or by M193's fixture verification. The reference
module has no post-render consumer that compares actual dimensions to the frozen
descriptor, despite `FAIL_OUTPUT_GRID_CONTRACT` being listed in the contract.

The routed `mark-b-closed` replacement changes the meaning of `(b)` from
“unresolved native-scale/cover=scale geometry” to a closed *definition*, then
removes it from eight readiness rows. That is an overclaim. Definition closure
and product geometry closure are different results. In particular, the routed
M10 replacement itself still says a compatible native-grid product and
commissioned integrated checker are missing.

## 3. A fixed reference still faces the focus-sweep failure

**VERIFIED by source inspection:** `construct_overlap` chooses the minimum TIFF
byte-hash key and calls `register_to_reference` independently for every other
input. It does not build a multiscale graph or choose references for content
overlap. This repeats the single-reference assumption prohibited for deep stacks
by AGENTS rule 6; a deterministic reference choice does not establish common
sharp content.

**MEASURED synthetic challenge:** two 384-by-288 RGB16 images share exact identity
geometry and the same texture. One preserves left-hand texture and defocuses the
right; the other preserves the right and defocuses the left. Each has 1,024 SIFT
features. They yield only 3 mutual matches, and `construct_overlap` refuses with
`UNMEASURED_INPUT_REGISTRATION_INADEQUATE`. The matched-focus identity control
on the same feature path yields 256 matches and exactly 0 px RMS.

This refusal is correct and safe; it is not a false geometry score. It establishes
that even perfect planted placement can be unmeasurable under the registered
constructor. The experiment does **not** establish a real-corpus failure rate or
require this two-frame plant to be accepted. It rules out treating the synthetic
warped-texture pass as evidence that the native deep-stack geometry problem is
closed. The next coverage experiment must include changing in-focus content and
the measured curved placement track, not just one image under a similarity.

## 4. Memory is a derived feasibility concern, not a measured peak

**DERIVED from the implementation and native dimensions.**
`construct_overlap` retains the caller's exact TIFF byte strings, keys them in a
dictionary, and creates `decoded = [decode_input_tiff(blob) ...]` for every unique
frame before registration. At 7,032 by 4,688 RGB16 pixels:

```
one frame payload = 7032 * 4688 * 3 * 2 = 197,796,096 bytes
299 TIFF payloads plus 299 decoded arrays
                  = 2 * 299 * 197,796,096
                  = 118,282,065,408 bytes = 110.158758 GiB
```

This excludes TIFF headers, feature extraction, and allocation overhead. It is a
payload lower bound for a native 299-frame unique-input call, **not** a measured
RSS value, a product M12 result, or evidence that a process crashed. A streaming
constructor is needed before treating this implementation as practical on the
reference host; the deterministic byte key can be computed while streaming.

## 5. Required remedy and admissible next claim

1. Preserve the M193 v1 baseline. Add a prospective consumer revision that
   validates the complete overlap schema, recomputed hash, bounds, input binding,
   and rectangle/count consistency before using any denominator. Unknown or stale
   inputs must refuse. Run this exact tamper through the revised consumer and
   require a refusal while the original crop and identity controls retain their
   verdicts. An independent verifier must test the revised path.
2. Supply actual per-program adapters and input-derived mapping evidence, hash
   their implementations/settings, and implement the post-render descriptor
   confirmation. Hash syntax and asserted zero residual are insufficient.
3. Bound constructor memory and demonstrate real development-capture coverage,
   including deep changing-focus content. Retain named refusals for unsupported
   populations. A different registration design requires prospective registration,
   not silent mutation of the frozen v1 algorithm.
4. Record the current achievement as **geometry definition proposed/frozen;
   consumer integrity and product applicability not yet established**. Do not
   remove `(b)` merely because its normative words are now exact.

No scorecard threshold needs changing to discharge the consumer defect. No result
here licenses a cover-mode change, a scored-geometry pass, or an M10 pass.

## 6. Reproduction and provenance

Command run from the repository root, exit **0**, approximately 2.2 seconds:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B experiments/review-m193-geometry/challenge.py --focus
```

The exit means **the defect was reproduced**, as the terminal line states:
`REPRODUCED: stale-denominator defect changes FAIL to PASS`. It does not mean the
M193 checker passed. The script writes its full results to
`experiments/review-m193-geometry/challenge-results.json`. It uses no RAW loader,
network, scored seed, or actual stacker output.

| Artifact | SHA-256 of checked-out bytes |
|---|---|
| M193 `reference.py` | `C08340F6F0658FAE048DDA92629A543B5A539462A93DB196AAAE29E1862BA790` |
| M193 `contract-v1.json` | `19421729AC39273A5F61CDA5068026F3458BA08C98F0AA954DE7C219CBFABF47` |
| M193 `fixtures.json` | `8F5EBCBA9688F0D08E71D74F1E8C881702C932BA7D3386E1F9131FFA882AC693` |
| Review `challenge.py` | `A01BDE285AB32893D893E3437C475B13EA02F92865DE2CB8EBA6732CE7D9DF91` |
| Review `challenge-results.json` | `B6FB5EBC67D5611B72A436C7BD7ACA4139EE1C607A7ECFF4A1EC2DA83D1439A7` |

The post-run source hash agrees with the source hash captured by the challenge.
`git diff -- experiments/M193-cover-overlap` identifies the pre-existing contract
changes as `status = FROZEN_PRE_COMPARATOR_OUTPUT` and
`algorithm_precommit_commit = dfaa2f639b85af0b568e7f8af1e8722548831c91`.
This review made neither change and did not adopt the routed replacements.
