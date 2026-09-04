# M164 real-pair audit — amendment 1

Status: **FROZEN AFTER RUN 1 FAILED, BEFORE RUN 2**

Run 1 used the prepared command and stopped on the first pair because
`coffee-bean` retained only `4/12` eligible fixed sites, below the frozen
minimum of `8`. The persistent failure artifact is
`out/realpair-run1-failed.json`, SHA-256
`6BF42C86151B4E0909689F6BCB9AFDD7DA2564A2BA9ADCD0193CB380CA07C065`.

This amendment changes orchestration only:

1. evaluate all three authorized burned pairs even if one pair raises;
2. record each failed pair as `PAIR_INVALID`, including its error;
3. retain every scientific threshold, fixed site, adapter, transfer family,
   input hash and pair whitelist unchanged;
4. return process exit `2` if any pair is invalid; and
5. report the aggregate historical verdict as `PARTIAL` whenever any pair is
   invalid.

The amendment does not lower the eight-site minimum, replace sites, weaken
registration or rail gates, or convert a missing precondition into
`NOT_VETOED`.

