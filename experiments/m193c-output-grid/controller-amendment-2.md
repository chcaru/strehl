# Memory-control amendment after the second retained refusal

2026-09-07. Release2 was frozen at `3cfefcbf` with SHA256
`e1aa6aa1a8de77d6b1da6ba7b4ee135fd0adf24451df6a8bf88af9a04a6cfbda`.
The actual command exited1 with `UNCOMMISSIONED_CONTROLLER`. The first six
controls passed, including the repaired nested-child test. It observed parent
PID44440, executing/requested child PID43384, four Job processes against the
single companion's two, the expected wall refusal, no cleanup error and final
zero-active accounting. This does not explain the prior multiplicity or
missing startup marker.

The seventh control, memory, did execute its128 MiB allocation attempt and
printed `M193C_MEMORY_REFUSED`. The parent also refused at its named
`child committed-memory bound`: the returned peak was143831040 bytes against
the configured67108864-byte request. It terminated its owned tree, yielding
exit3784556766 instead of the predicate's required clean exit7. Cleanup errors
were empty and terminal zero-active Job accounting was observed. The old
predicate rejected this combination of intended protective actions. Later
controls were unvisited; all first/second attempt artifacts remain unchanged.

No explanation of the above-limit peak is asserted. In particular, these
records do not prove that the OS-reported high-water value excludes a denied
commit or establish the physical resident-memory peak. The prospective helper
now reads back configured flags and the Job memory limit before resuming its
child; every control checks those values against its declared limits.

The revised memory instrument has a necessary positive companion: the same
128 MiB `bytearray` allocation must succeed under a256 MiB Job limit, return
the declared size and exit0. The following64 MiB negative companion admits
only either a clean child `MemoryError`/exit7 or the exact parent
committed-memory refusal with an observed peak above64 MiB. Both require
clean cleanup and terminal zero-active accounting. An unrelated exception,
ordinary exit9 after a permitted allocation, failure of the positive arm or
wrong configured limit fails. The parent never treats a memory-bound child
as successful product work.

There are now eleven fixed process controls. This addition repairs the
private instrument's missing positive arm and the interpretation of a
protective rejection; it does not change the64 MiB negative cap, image-stage
budgets, numerical accuracy bars or production-image population. The same
120-second outer controller allowance applies. A new committed source/command
release and fresh cache/output are required; no prior result is rewritten.
