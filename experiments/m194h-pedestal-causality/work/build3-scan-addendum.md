# M194h build3: scratch disappearance repair

Status: SOURCE ONLY. No scanner control, compile, component, render, checker, numerical call, or external process has been executed by this author. Independent source review and root release remain required.

Build2 remains REFUSED. Its FileNotFoundError did not retain enough context to establish the exact path or cause. Concurrent Cargo scratch creation/removal is a candidate explanation, not an observed causal result. This correction neither reclassifies that attempt nor changes its charged work.

## Exact source delta

Previous driver: 38,240 B, SHA256 8276fc134d7db6dfcf2381bffb8796d4946ad1aa2a551ca3e275ddf3c78d8cf6.
Candidate build-and-run.py: 40,626 B, SHA256 b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410.

Only scan(), the scratch scan call in Budget.check(), and the build target/output constants change. Build3 uses target/m194h-pedestal-causality-3 and experiments/m194h-pedestal-causality/build-3; components-1 and subject-1 stay fixed. Retained-artifact scan calls keep the default strict policy. The compile-only owned-Job cleanup helper, child admission, all other driver function bodies, Rust sources, component/renderer population and numerical gates remain unchanged. AST comparison is source metadata only, not execution.

scan() takes keyword-only tolerate_disappearance=False. Only the live scratch call passes True. An actual FileNotFoundError during inspection/walk may be recorded and skipped under that policy. PermissionError, other OS errors, reparse/symlink rejection and file-family overflow still refuse. os.walk has an explicit onerror callback. Non-tolerated inspection errors carry the operation and path in the message itself, preserving context even when an outer receipt retains repr(error).

Every scan now returns files, bytes, initial_absent, observed_disappearances, disappearance_samples, tolerate_disappearance and scope. initial_absent means absent at this invocation's first lstat; it does not establish that the target never existed. Observed disappearances are events, not a unique-file count. Samples retain at most eight operation/path pairs, path strings limited to384 characters with a truncation flag. Bytes are the non-atomic sum of observed extents: already counted bytes are retained if a later disappearance is observed. This is not an atomic inventory, allocation peak, or proof that transient files never exceeded the scratch limit.

## Fixed source-selected control

work/scan-regression-control.py: 11,473 B, SHA256 c2e1a39bedd16fbe9b2dec9affed42c773ce5497b89bd254f6135779266dec11.
The future controller selects exactly the source AST definitions need, lexical, owned and scan from the hash-bound driver, supplying only their existing stdlib/path globals. It does not import the driver or execute its main, Job API, compiler, renderer, checker or any scientific code.

Exactly seven ordered rows are preregistered:

1. stable: two actual ordinary fixture files,16+32=48 bytes; strict scan must return two files,48 bytes and no disappearances.
2. scratch-deletion: the real os.walk enumerates both fixed names; a scoped wrapper deletes race.bin before yielding that same enumeration to the scanner. Require actual enumeration/removal, one surviving16-byte file and exactly one named file-inspection disappearance.
3. strict-deletion: restore the same32 bytes, repeat that actual enumeration/deletion under default strict policy, and require FileNotFoundError with the actual path and operation.
4. oversize: the restored actual48-byte population against47 bytes must raise the original file-family-capacity predicate, even with scratch tolerance enabled.
5. reparse-bit: a scoped lstat wrapper adds only the reparse attribute for one actual ordinary fixture file. Require that exact scanner predicate and path. This is a metadata injection, not a native junction.
6. permission-onerror: a scoped walk wrapper delivers PermissionError to the actual supplied onerror callback. Require propagation, callback reach and path. No ACL is changed.
7. restored: require original os.walk and Path.lstat identities, byte-identical fixture FileRefs, and complete strict scan-result equality to stable.

Rows are appended and progress is saved before each case, then updated in finally. Faults must exercise their declared branch. Scoped overrides restore in finally; only the two named tiny owned fixture files can be created/removed. The fixture content identities are compared after restoration; inode/mtime identity is not asserted across deliberate file recreation.

## Once-only command and terminal association

From the repository root, after exact source freeze and independent source review:

```text
C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe -I -S -B C:\dev\blog\death-of-software\projects\strehl\experiments\m194h-pedestal-causality\work\scan-regression-control.py --driver-sha256 b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410 --self-sha256 c2e1a39bedd16fbe9b2dec9affed42c773ce5497b89bd254f6135779266dec11
```

Fresh output is work/scan-regression-1, containing result.json, progress.json, the consumed/reusable publication-stage.json slot, and fixture/keep.bin plus fixture/race.bin. No retry or fallback output directory is authorized.

The result schema is m194h-scan-regression-v1; positive status PASS_METADATA_SCAN_REGRESSION_ONLY requires exactly all seven passed rows. Initial result status INITIAL_INCOMPLETE and detailed REFUSED are not admission. Progress schema is m194h-scan-control-progress-v1. Same-buffer source reads bind the parsed AST bytes; own source and driver hashes are rechecked before final publication. Fixed bounded staging, flush/fsync, readback and same-directory replacement preserve the previous canonical receipt until replacement bytes are complete. An OS/filesystem failure can still prevent detailed publication; root outer disposition then controls admission.

Stdout is a raw-byte JSON advertisement containing exact final result FileRef/status/passed, at most8KiB and checked for a full write. Root must retain actual command, raw stdout/stderr, actual exit and complete external wall interval, verify the advertisement against final bytes and progress, require actual exit0/no timeout, and verify whole wall <=20s and <=the saved prepublication wall+2s. A canonical positive without that actual outer association is insufficient.

## Finite metadata allowance

The separately authorized metadata phase charges10 CPU seconds,20 wall seconds and1MiB in full regardless of outcome. Live whole-process CPU and elapsed wall guards are9/18 before cases and final publication, leaving1 CPU/2 wall for bounded publication. Saved actual_prepublication is a sample, not complete process CPU; root's external wall covers the final write/flush/exit. No CPU is inferred from wall and no exact outer-wrapper CPU measurement is claimed.

Conservative file-family allocation in KiB: driver source128; controller16; addendum16; independent review16; root decision/command16; external outer64; raw stdout8; stderr8; exit1; final/progress/stage three times32. Total469KiB plus48 fixture bytes is480,304 B, leaving568,272 B under1MiB. These are reserved extents, not observed output sizes. New source intake is bounded before reading, fixed fixtures use at most32 bytes each, and each JSON receipt is capped at32KiB before publication. No unrelated evidence, data, runtime inventory or compiler scratch is read by this control.

The control establishes the new scanner seam only. It does not prove the proposed race caused Build2, commission the compiler process lifecycle again, relax a resource bar, or admit a later build. Root's separate build3 release retains all prior failures and costs.
