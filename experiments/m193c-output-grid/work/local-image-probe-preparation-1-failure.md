# Local-image preparation 1: bounded failure

MEASURED, 2026-09-08. Root ran the committed preparer once with all15 independently checked fresh source triples,211040 bytes. The actual complete command is retained in local-image-probe-preparation-1-outer.json; it is the command that ran, not a proposed invocation. Source commit855e51427f418ca4fe34bba09e69ba3f06d5e819, saved auditor commit571e52d7, continuation freeze f25a3b63.

Actual exit1; whole process wall9.546999999998661 seconds; stdout0 bytes; stderr1364 bytes. The traceback is the runtime-inventory read at prepare.py147, after same-read registration at63, rejected by check35. That guard combines process CPU+0.25<=5 and elapsed wall+0.5<=10. No separate CPU or wall sample was retained at failure. The external near-limit wall is consistent with its wall arm, but does not uniquely establish which term fired. This is a preparation-capacity failure, not an estimator or image-data result.

Root checked the complete closed set of possible release destinations: no plan, resource authorization, inventory receipt, preparation receipt or subject directory exists. No subject, numerical control or real image patch was executed. The helper reads module files in place but imports no numerical library and opens no native image payload. Empty stdout is retained with the canonical empty hash.

The entire original preparation reservation5CPU/10wall/1MiB stays charged. Actual terminal process CPU is unknown; the reservation is not a measurement. Unexecuted subject/audit reservations do not become evidence or authorize retry. A new attempt requires a separately reviewed prospective preparation amendment and fresh outer records. Original failed files and original committed sources remain preserved.

Root decision, prospective only: allocate a second preparation20CPU/60wall/1MiB. Aggregate preparation therefore25CPU/70wall/2MiB; retain fixed subject90CPU/140wall/60MiB and saved audit25CPU/30wall/3MiB. Full phase140CPU/240wall/65MiB retains baseline1418.443678CPU/1321.9278447999966wall/4068213529file/76952595metadata unchanged. Prospective cumulative caps1600CPU/1800wall/4GiBfiles/160MiBmetadata. This changes resource capacity only. All saved image pairs, stimuli, thresholds, calls and numerical methods remain fixed. Source review, committed freeze and fresh exact plan precede release.

Independent failure review and the narrow amendment are pending; this note does not verify its author.

Actual evidence bindings:

{
  "local-image-probe-preparation-1-stdout.bin": {
    "bytes": 0,
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "local-image-probe-preparation-1-stderr.bin": {
    "bytes": 1364,
    "sha256": "bda56ca8025fa39f77e305f7f6ed000b9eae335ad76da5a1c64456f68adcfe95"
  },
  "local-image-probe-preparation-1-exit.txt": {
    "bytes": 2,
    "sha256": "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865"
  },
  "local-image-probe-preparation-1-outer.json": {
    "bytes": 3150,
    "sha256": "23ff1213d9705eaf2785465a1044e7212b945a50341acc3ccb1ce81fa1c78ae6"
  }
}
