# Scratch scanner resolution correction

Status: SOURCE ONLY. No shim import, control, subprocess, compiler, fixture preparation or numerical operation has run. This is an operational correction proposal after the first common-TIFF dimensions build refused; it does not change the product or authorize another build.

## Saved failure and scope

The first build's eight negative-evidence files are preserved by root at commit `834a3c61`; the original 181-source archive is preserved at `8017d2f3`. Its `build-1/child-00.json` records a scanner `ValueError` for:

```
target/common-tiff-dimensions-1/debug/build/proc-macro2-0ff67e0f32290390/out/probe/libproc_macro2.rmeta
```

The retained error ends `canonical path`. The Cargo process had not reached the direct-exit-zero/EOF completion condition. Failure cleanup observed six active owned Job processes before termination and zero at the end. No strehl executable, fixture preparation or product invocation resulted. The full failed build reservation remains 600 CPU seconds and 300 wall seconds; later work must have a fresh explicit reservation.

DERIVED from the held source: `scan` invokes `owned` before its file stat. `owned` checks `path.resolve() == path` using non-strict resolution. A canonical mismatch is a `ValueError`, while scratch disappearance recovery accepts only `FileNotFoundError`. Therefore a temporary-file race *could* encounter the canonical predicate before the later stat can report absence. This is a possible mechanism, not a demonstrated cause.

Root's later metadata observation found the named file and its probe directory absent, with the existing parent resolving identically. That later state is not a reproduction of the earlier mismatch and does not establish when or why it happened. The proposal does not convert the saved failure into a success.

## Exact source seam

New source: `scratch-scan.py`, 2,264 bytes, SHA256 `be6da1fb1b69524565dc5bc7e074236c28777272ec1f938319dae3393e9c54fd`.

The inherited primitive source remains `experiments/m194h-pedestal-causality/build-and-run.py`, 40,626 bytes, SHA256 `b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410`. Its scanner, source readers, `owned`, `lexical`, and all original artifacts are unchanged.

The new factory `make_scanner(held, target)` captures the already authenticated module's original scan function. It creates one function object from the exact original scanner code and a shallow copy of its globals, replacing only the private copy's `owned` binding. Positional and keyword defaults are preserved. It rejects a scanner with closure free variables. It does not execute scanner code while constructing the function and does not mutate the supplied module.

The private scratch path check:

1. Uses the original lexical ancestry check, including ASCII/384-character width and reparse/symlink checks.
2. Requires repository and declared scratch-target containment.
3. Calls `path.resolve(strict=True)`.
4. Requires the result to equal the declared path. Its error includes both actual declared and resolved spellings.

An absent entry reported by strict resolution remains a `FileNotFoundError`; the unchanged scanner alone decides whether to count it as a tolerated scratch disappearance. A present canonical mismatch remains a failure. Permission, reparse/symlink, nonregular-file, non-directory, containment, capacity and other error paths remain refusals. No catch-all `ValueError` handling or post-failure `exists()` exemption is added.

The dispatcher checks the existing exact-bool policy. A false policy delegates directly to the captured original scanner with its existing strict behavior. A true policy requires the exact declared target root and invokes the private clone. This does not permit tolerant scans of retained output/source/evidence directories.

The clone returns the original result schema: file count, non-atomic observed extents, initial absence, disappearance count and at most eight bounded path/operation samples. Already counted extents remain counted. Initial absence means absence at this scan's first lstat, not proof that a target has never existed. Neither the old nor the new scanner is an atomic snapshot, a filesystem race-proof reader, or a peak scratch-space measurement.

## Prospective integration, still unexecuted

A separately reviewed new controller source will authenticate this shim through the release's positive source map and a fixed source digest before loading it. After configuring the private imported primitive module, it may assign only that private module's `scan` entry to `make_scanner(d, TARGET)`. Its other entry points remain unchanged. The factory captures the original scanner before that assignment; strict delegation cannot recurse through the replacement.

Only the build scratch call for the new fixed target may pass `tolerate_disappearance=True`. Retained artifact scans retain their false policy. The new build needs a fresh target and build output; original `build-1` and `target/common-tiff-dimensions-1` are not reusable success evidence. Root owns the subsequent release, path and cumulative-budget changes. This note does not change them.

The source/runtime/output overhead is one small source module and private function/global-table objects. It creates no new per-poll file, registry or unbounded history. Existing scanner cadence, scratch-byte ceiling, live work guards, owned-process cleanup and terminal publication rules remain operative. No speed, overhead or causal claim follows from this source review.

## Independent controls before release

The independent author owns `scratch-scan-controls.py` and `scratch-scan-spec.md`; no competing control implementation is supplied here. Their fixed population must call this actual factory against a private module containing the held scanner definitions. It must demonstrate a real owned fixture deletion between lexical ancestry inspection and native strict resolution, with reached-event assertions, one counted scratch disappearance, and restoration of bytes and observer seams.

The source contract also requires independent controls for retained strict delegation, present canonical mismatch including both spellings, reparse rejection, permission-error propagation, wrong target/policy, byte-cap refusal and a restored positive. Scoped adapters may inject metadata or resolution results, but must label those controls as injections, retain native delegation where claimed, and never patch the original imported module globally. Strict resolve's boolean argument must be observed. An absent-file result alone is insufficient power for the intended timing seam.

Root must review the actual independently authored population and its finite metadata allowance before running it once. Passing metadata controls would qualify the new branch and its boundaries; it would not reproduce the original failure, validate numerical output or justify a build retry by itself.
