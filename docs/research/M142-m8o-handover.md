# M142 M8-O harness handover

**Status:** CLOSED without a scored census.

M142 built a development harness for the preregistered M8-R and M8-O v1.5
measurement. It must not be rebuilt merely to pursue an M8 pass. N6 in
`ORCH-clamp-default-decision.md` couples any kernel-change route to M8 with the
still-open detail blocker `(a)`. The current harness is also bound to a private
development configuration rather than the shipping default.

## What the harness measures

The runner is
`experiments/M142-m8o-execute/run-clamped-m8o.ps1`. It orchestrates:

1. an exact source snapshot and private instrumented build;
2. directional commissioning of the checker and independent verifier;
3. a pre-target instrument freeze;
4. per-capture rendering and trace collection;
5. primary adjudication and independent recomputation; and
6. exact per-capture and aggregate summaries.

M8-R checks every eligible per-frame gathered value against the independently
reconstructed exact `4x4` source-support hull. M8-O v1.5 maps each per-frame
source interval through the registered intermediate arithmetic, projects it to
the representable `[0,1]` output domain, and compares the final serialized
`u16` output with fixed `q = 1/131070`. Both gates are exact zero: one violation
fails. The combined experiment also requires the separately registered
crop/reference identity arm to be zero.

Trace v3 uses `<8s15I6d4f32s32sI` (200 bytes). The first `32s` is
`instrument_freeze_sha256`; the second is `frame_source_sha256`.

### Recorded command sequence

These are the exact mechanics of the closed CE83 development campaign. They
are documented for reproduction, not authorized for a new score:

```powershell
Set-Location C:\dev\blog\death-of-software\projects\strehl
$Commit = "248178b921f98ec1f13ea4c07d30fa68ace787a0"

powershell -NoProfile -ExecutionPolicy Bypass -File .\experiments\M142-m8o-execute\run-clamped-m8o.ps1 -Mode Prepare -SourceCommit $Commit
powershell -NoProfile -ExecutionPolicy Bypass -File .\experiments\M142-m8o-execute\run-clamped-m8o.ps1 -Mode Commission -SourceCommit $Commit
powershell -NoProfile -ExecutionPolicy Bypass -File .\experiments\M142-m8o-execute\run-clamped-m8o.ps1 -Mode Freeze -SourceCommit $Commit
powershell -NoProfile -ExecutionPolicy Bypass -File .\experiments\M142-m8o-execute\run-clamped-m8o.ps1 -Mode Census -Capture All -SourceCommit $Commit
powershell -NoProfile -ExecutionPolicy Bypass -File .\experiments\M142-m8o-execute\run-clamped-m8o.ps1 -Mode Verify -SourceCommit $Commit
powershell -NoProfile -ExecutionPolicy Bypass -File .\experiments\M142-m8o-execute\run-clamped-m8o.ps1 -Mode Summarize -SourceCommit $Commit
```

### Current pin block

Commit `6fa6002cfea2c677d232b0952d0c2ae44b1ab1a0` left the live runner with:

```powershell
$RequiredCommit = "248178b921f98ec1f13ea4c07d30fa68ace787a0"
$RequiredVerifierCommit = "f77a8bd2"
$RequiredVerifierCommissionCommit = "f77a8bd2"
$RequiredVerifierSha256 = "EBC780597CCC72E48DC73A6FA72CD14329BAA806CDF066484595FD1A03F520FB"
$RequiredVerifierCommissionSha256 = "E60B699113D5896E735F85EA791C28747CFA6CCC57EF50BA17F9A3749CDF11E4"
```

`$RequiredCommit` selects the only source commit the current runner accepts.
The two `*Commit` verifier values identify the M136 revision in diagnostics;
the runner's actual byte checks are the two raw Windows working-byte SHA-256
values:

- `EBC780...` covers `experiments/M136-m8o-bar/verifier_m136.py`.
- `E60B69...` covers
  `experiments/M136-m8o-bar/verifier-commission.json`, the independently
  recommissioned PASS report for those verifier bytes.

Those pins identify the intended verifier artifacts. They do not prove which
verifier bytes Python compiled at process startup; see the integrity section.

## Reusable versus CE83-specific

### Reusable components

The following are reusable as implementation material, not as already-frozen
evidence:

- the value-only trace-v3 wire format and freeze/source hash fields;
- exact `f32` representation arithmetic, representable-domain projection, and
  integer-zero decision logic;
- M8-R support reconstruction and the copy, clamped-copy, bilinear, raw
  Catmull-Rom, widened-clamp, and explicit high/low controls;
- M8-O green/red numeric cases, the integer-quantizer discriminator, malformed
  trace controls, and directional degradation/improvement commissioning;
- fail-closed phase ordering, atomic checker staging, exact capture inventory,
  at-least-64-bit aggregation, rail disclosures, and independent recomputation;
- source/build receipts and the general Prepare -> Commission -> Freeze ->
  Census -> Verify -> Summarize orchestration.

Reuse requires a new prospective contract, commissioning, and freeze. Existing
files below `experiments/M142-m8o-execute/out` are incomplete development
evidence. They are not a target result.

### CE83-specific components

The following are welded to CE83 and must not be inherited accidentally:

- source commit `248178b921f98ec1f13ea4c07d30fa68ace787a0`;
- `patch_snapshot_m142.py` and its exact private-tree hashes, replacements, and
  product-changing clamped-kernel patch;
- the forced command configuration `--merge pyramid --cover crop --resampler
  clamped-catmull --fix-ca off`;
- the three `flat-et1s`, `flat-et2.5s`, and `flat-et6s` development captures;
- their M134 clamped warp maps and registered hashes;
- checker requirements for the clamped-kernel trace identifier and
  `clamped-catmull` warpmap spelling;
- Crop origin reconstruction, compact-TIFF coordinates, Crop eligibility and
  denominator mapping, and Crop-specific fixtures; and
- the preregistered clamped/Crop/CA-off population and provenance schema.

The current runner cannot score a shipping-default Scale campaign by changing
one command-line word. Scale needs a prospectively defined output lattice,
scale factor, coordinate mapping, eligibility and denominator; corresponding
trace/checker/fixture/verifier changes; full directional recommissioning; and a
separate mandatory crop/reference identity arm.

## Intentional source-commit rejection

The runner refuses every source commit except CE83 by design:

```powershell
$RequiredCommit = "248178b921f98ec1f13ea4c07d30fa68ace787a0"
```

```powershell
if ($SourceCommit -ne $RequiredCommit) {
    throw "Source commit $SourceCommit differs from preregistered candidate $RequiredCommit"
}
```

This is a prospective evidence guard, not a broken general-purpose interface.
A successor must replace the pin and all dependent source/patch identities
together after a scored commit is named.

## Observed render floor

The completed `flat-et1s` render took approximately **234 seconds for 60 RAW
frames**. This is a single observed floor, not a benchmark. It covers the
instrumented `strehl.exe stack` invocation that emitted the TIFF and trace
blocks. It excludes source snapshotting, patching, compilation, tests,
commissioning, freezing, input fingerprinting, the primary checker,
independent verification, summarization, and the other captures.

Neither checker attempt completed, so there is no measured checker or
independent-verifier runtime and no defensible end-to-end runtime estimate.

## Same-bytes and TOCTOU handover

M142 found a repeated vulnerable shape:

```text
hash(path) -> close -> parse or execute by reopening path
```

That sequence proves the bytes present during hashing, not the bytes later
consumed. In this harness the class reached artifacts that can affect or
attribute the number: the candidate executable, checker and verifier scripts,
compiled source files, RAW inputs, warpmap, target traces, TIFF, and verdict
metadata. Primary-checker examples included hashing a trace and reopening it
for its header and memory maps, and decoding a TIFF separately from hashing
its path.

M136 commit `f77a8bd2` materially improves this inside the verifier:
`PinnedFile` hashes a retained file object, and parsing or mapping remains
attached to that accepted object. Its powered substitution controls exercise
JSON and trace header/body replacements in both directions.

The correction is important: `f77a8bd2` closes post-startup same-object reads,
but **does not prove verifier execution-byte identity**. Python has already
opened and compiled `verifier_m136.py` before the verifier captures and hashes
`Path(__file__)`. Likewise, a PowerShell wrapper that reads or hashes the
script and then launches the pathname does not prove that Python consumed the
same bytes. The `f77a8bd2` pin is therefore an intended-artifact identity, not
a complete M149 bootstrap seal.

The same limitation remains upstream for Cargo reopening source files after a
manifest pass and for `strehl.exe` reopening RAWs and a warpmap after runner
fingerprinting. A future lane must not infer that a hardened result reader
retroactively proves producer input or process-image identity.

## Adopted prospective integrity standard

Every artifact whose bytes can affect or attribute a future census must be
**bracket-hashed**:

1. hash it immediately before the relevant build, render, check, or verify
   run;
2. hash it immediately after;
3. record both digests in emitted evidence; and
4. fail closed if they differ.

This applies at minimum to the candidate executable, checker and verifier
scripts, warpmap, RAW inputs, and compiled source tree. Scripts and JSON
consumed by M142's own process must additionally be read once into memory, then
hashed and parsed or compiled from that same byte buffer rather than reopened
by path.

This standard is deliberately limited. It does **not** cryptographically seal
the run against a live adversary: a swap-and-restore operation can present the
same bytes at both brackets. It closes accidental drift and swap-and-leave
cases and requires a deliberate attack to survive two recorded digests.

The in-memory clause cannot be met for a Rust executable launched by path.
For that executable, the before/after bracket and an explicit disclosure of
this limitation are the contract; do not silently claim process-image
attestation.

