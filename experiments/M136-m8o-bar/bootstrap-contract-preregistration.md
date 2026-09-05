# M136 verifier bootstrap same-bytes contract — pre-registration

Status: **PRE-REGISTERED BEFORE ANY BOOTSTRAP COMMISSIONING RUN.**

This document registers the execution-identity question only. It does not change
the frozen clamped-M8-O decision rule, the prospective interpretations, or any
M136 measurement result.

## 1. Trust boundary

The trust root is exactly:

1. the operator-invoked `recommission-verifier.ps1` bytes as interpreted by the
   current PowerShell process;
2. that current PowerShell process;
3. Windows file-share semantics for handles opened with
   `FileAccess.Read, FileShare.Read`, which deny write and delete sharing;
4. the approved Python runtime and its already-approved dependencies.

The wrapper must open and retain a read/share-read handle to
`launch-verifier.ps1`, hash that retained stream, and keep it open until the
child PowerShell process exits. The launcher must do the same for
`verifier_m136.py` until the Python child exits. Python must read the verifier
once into one byte array, hash that array, and compile that same array.

## 2. Exact pass license

A PASS licenses only this statement:

> Under the trust boundary above, the verifier source bytes executed by Python
> are the same bytes whose SHA-256 the launcher reports, and the launcher path
> could not be renamed, replaced, or modified after the wrapper accepted its
> retained-handle SHA-256 and before that launcher process exited.

PASS additionally licenses that direct unpinned `commission` and `verify`
execution is refused as `UNMEASURED` with a nonzero exit, and that the actual
launcher discriminates both registered source-substitution directions.

## 3. Non-claims

PASS does **not**:

- authenticate the operator-invoked wrapper, the current PowerShell process,
  the PowerShell executable, the Python executable, Python dependencies, the
  Windows kernel, or filesystem implementation;
- prove protection against a compromised trusted process or kernel;
- authenticate upstream candidate EXE bytes, candidate source, RAW inputs,
  warp maps, trace blocks, TIFFs, manifests, or other evidence;
- close any upstream same-bytes binding. Candidate EXE/source/RAW/warpmap
  execution and evidence bindings remain explicitly open;
- commission the M8-O statistic, change its bar, or license a research claim.

## 4. Registered source-substitution arms

Both directions are mandatory and use different accepted and substitute bytes.

### 4.1 ALLOW -> DENY

- Accepted source A emits `ALLOW`.
- Substitute source B emits `DENY`.
- Vulnerable arm: hash A and close it; land the real
  `TransientPathReplacement` first rename and replacement; invoke Python by
  pathname; require B to execute while the recorded digest remains A.
- Defended arm: restore A; invoke the actual `launch-verifier.ps1`; request its
  commissioning rename of A to the attack-backup pathname while its deny-write/
  deny-delete handle is live; require Windows sharing denial, A execution, and
  equality of the parent, child, launcher-receipt, and final-path SHA-256 values.

### 4.2 DENY -> ALLOW

Repeat the exact design with accepted source A emitting `DENY` and substitute
source B emitting `ALLOW`. A one-direction result is not a PASS.

For each direction, the vulnerable and defended verdicts must differ. The
accepted SHA-256 in one direction must equal the substitute SHA-256 in the
reverse direction, and vice versa.

## 5. Direct-launch arm

A separate minimal source must require `_M136_PINNED_SOURCE`.

- Direct `python -I -B <path>` execution must emit `UNMEASURED` and exit exactly
  `2`.
- Execution through the actual launcher must emit `PINNED`, exit `0`, and
  report one SHA-256 shared by the parent, child, launcher receipt, and final
  pathname.

The production verifier has no fallback to reopening `__file__`; direct
unpinned `commission` and `verify` therefore have the same fail-closed policy.

## 6. Expected rename/replacement denial

The commissioning attack performs the first real swap step:

`Move(accepted verifier path, attack-backup path)`.

While the launcher retains `FileShare.Read`, the accepted result is:

- attack did not land;
- HResult/Win32 low word is exactly `32`
  (`ERROR_SHARING_VIOLATION`);
- backup path is absent;
- accepted path remains/restores to accepted bytes;
- the child executes.

If the move lands, the launcher must close only as needed to restore the
accepted pathname, must not start Python, must write a refusal receipt, and must
exit nonzero.

## 7. Exact failure inputs

These inputs must fail:

1. accepted and substitute source bytes are equal;
2. supplied expected verifier SHA-256 differs from the retained-handle digest;
3. `_M136_PINNED_SOURCE` is absent, malformed, has extra/missing fields, names a
   different path, or contains non-byte source;
4. the injected source digest differs from SHA-256 of the injected raw bytes;
5. the bootstrap contract or bootstrap SHA-256 differs from the frozen verifier
   constants;
6. the commissioning rename lands;
7. the commissioning rename fails with any low word other than `32`;
8. launcher receipt, child output, parent digest, or final-path digest disagree;
9. either direction fails to discriminate vulnerable from defended execution;
10. direct unpinned execution returns zero or any status other than
    `UNMEASURED`.

## 8. Deterministic artifacts

`launch-verifier.ps1` receipts and the bootstrap fields added to
`verifier-commission.json` must contain only contract strings, fixed schema
values, SHA-256 values, exact exit/error codes, fixed sentinels, and booleans.
They must contain no temporary paths, timestamps, PIDs, handles, file IDs,
random identifiers, exception prose, or other run-varying data.

The existing `commission()` rerun inside `verify_manifest()` must reproduce the
frozen commissioning report byte-for-byte. Any nondeterminism is
`UNMEASURED`, not PASS.
