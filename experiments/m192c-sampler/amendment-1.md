# M192c Amendment 1 — match the inherited launch arrangement

Frozen before the complete second commission. The original 64-arm result
`out-20260907-084426-145611` remains COMMISSIONING_FAILED. Only its three exact
Job-count gates failed (four processes, expected two); child identity and
allocation detection passed. All original sources are copied byte-for-byte in
`preserved-v1/`, matched by the first result's source-freeze hashes.

The independently frozen `launch-attribution.py` factorial observation names
the extra processes: CREATE_NO_WINDOW starts a conhost.exe for each Python
generation. Job counts are 2/3/3/4 as neither/child/parent/both generations use
the flag. These are measured helpers, not an inferred Job-counter bug.

The prospective launch had used CREATE_NO_WINDOW while the inherited original
shared its existing console. That is a confound in both the two-process premise
and the original-versus-prospective overhead comparison. Change the prospective
root to CREATE_SUSPENDED alone, matching inherited monitor_command; its spawned
child uses creationflags=0, inheriting the existing console. Neither creates a
new visible console. No acceptance threshold or process-count domain changes.
Retain actual discovered process names, in addition to PID/creation/parent.

Re-run ALL 64 arms and all alternating sweeps in a new directory. Do not replace
the old failed rows or join lineages. The expected-two-process count remains;
failure still invalidates commissioning. All other predicates remain frozen.
The new source freeze includes this amendment. The phase-tracing implementation
and telemetry queries are unchanged. Existing M192 evidence remains read-only.
