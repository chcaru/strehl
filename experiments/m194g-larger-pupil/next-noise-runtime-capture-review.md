# Runtime capture: independent static review

**STATIC ONLY.** This reviews the small runtime/source snapshot helper, not
noise generation, an optical model, calibration, or CFA admission. No helper
was executed or imported during review.

The first reviewed `capture-noise-runtime.py` was
`c528d8f2a81e0e06205e803e1f3b8bdb83f67ca875be4f7f0aa814ad05315683`.
It verifies the externally supplied release digest and actual original argv,
hashes source bytes, and compiles the committed core from those exact bytes.
It calls `runtime_manifest`; it does not call `sample_frame`, the encoder, or
Generator construction. Reading the release's JSON string confirmed the
ordinary 65-character interpreter path with single separators; no argument
escaping defect was found.

Two source-level finalization issues were reported before execution: the
first version could leave a COMPLETE receipt after its final time check
failed, and it checked each current source before writing its snapshot rather
than rechecking the complete current/saved set after persistence. Exact
release-schema and empty-input checks were also requested.

The corrective version at
`85c12ac592b7f702a024117e174b29ad4043f97bd3291400525530b3b05edfb2`
was reread. It adds the exact schema/inputs checks and, after result
persistence, checks every current/saved source, runtime-manifest equality,
the actual persisted runtime file hash, and elapsed time. A failure changes
the receipt to `UNCOMMISSIONED_RUNTIME_SNAPSHOT` and retains its traceback.
These changes close the identified normal finalization path.

One further concrete error-handling recommendation was sent: a failure while
writing the downgraded receipt must be recorded as secondary and must not
replace the original finalization exception. The final inspected source,
`81715f227a6f235301812431bd5f1daa63857eaa4dd1a1cc0e069bdf6669f77e`,
implements that correction with a secondary note and re-raises the original.
It also imports the pinned authority and independent-reader modules after
the core, matching the actual generation runner's startup order before
capturing runtime hashes. Those module top levels import libraries and define
constants/classes/functions; they do not invoke sampling, encoding, optics,
or the reader's numerical checks. The core still precedes NumPy-dependent
reader import, so its pre-import thread guard is respected.

No remaining static blocker was found in this narrowly reviewed capture
path. None of the source inspections establishes actual runtime stability or
successful capture; a released terminal run remains necessary for that
evidence. Module imports are part of that later runtime operation and were
not performed by this review.

Read-only tools used were PowerShell `Get-Content`, `ConvertFrom-Json` on the
release argument string, and `Get-FileHash -Algorithm SHA256`. No numerical
imports, sampling, encoding or capture calls were made.
