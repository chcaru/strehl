# Controller fixture amendment after retained first refusal

2026-09-07. The exact first controller command was frozen at `5a727a12` with
release SHA256 `8fb5686c322513f9a35a5eca6ef147d4b70b506d03ad2c9e4b8f1086458cd716`.
It exited1 and saved the14891-byte `controller-controls-1/result.json`
(SHA256 `e64683aaab93aca3590607e7d6f3d1d0d80a7ed710beb178ccb3a7bb01139889`) with
`UNCOMMISSIONED_CONTROLLER`. The valid, exit7, exact-log, overflow-log and
single-timeout controls passed their named predicates. The sixth,
nested-timeout, failed; later controls were not visited. Final source checks
and persistence completed with no finalization error. This is not a passed
controller population or evidence about an image.

The observed single Python invocations each accounted for two Job processes;
the nested invocation accounted for four, not the hard-coded two. The reason
for that multiplicity is unestablished. Its retained log contained only
`M193C_NESTED_PID=46736`, without the intended child's startup marker before
the1-second deadline. The original wall refusal was retained, cleanup errors
were empty, terminal Job accounting was observed and active processes were
zero. These observations prove termination/accounting within their recorded
scope; they do not prove the nested workload reached its intended sleep.

The prospective fixture amendment makes stdin null and stdout/stderr forwarding
explicit, records the actual parent and executing child PIDs, and compares
Job process count with the same run's valid single-invocation companion.
The nested case must show exactly one actual child startup PID distinct from
the parent, exactly one requested child PID, and more accounted processes
than that companion. It still requires the expected wall refusal, clean
cleanup and terminal zero-active accounting. A missing child, absent marker
or unchanged count fails. No cause is inferred from the previous count alone.

Only the nested fixture's prospective startup/timeout allowance changes from
1 to5 seconds. The single-timeout remains1 second. The ten-control population,
120-second outer allowance, source/metadata/persistence checks, memory/log/CPU
conditions and image-stage limits are unchanged. This is a repaired private
instrument, not a relaxed image or performance criterion. Preserve the whole
first attempt and run a newly committed release with a fresh cache/output;
never overwrite its log, result or source snapshots.
