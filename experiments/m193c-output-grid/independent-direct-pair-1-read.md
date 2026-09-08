# Independent saved direct-pair outcome audit

VERIFIED saved outcome: the parent and worker both exited 0 with
`COMPLETE_DIRECT_PAIR_SUPPORT_ONLY`. All seven controls passed, all nine feature
extractions returned, and all 23 planned pair calls completed with scientific
registration refusals. Completion describes the observations, not successful
registration. No direct support edge, placement solve, overlap denominator or
accuracy claim was produced.

The held independent checker ran once and exited 0. It consumed saved metadata,
source/runtime/command bindings, opaque TIFF hashes and retained landmark
records. It did not decode images, re-extract features or rerun matching/fitting.
The previous coverage refusal remains unchanged.

## Actual population and refusal interpretation

The exact 23-pair span-1/2/4 plus local-5-star population and its call directions
match the parent plan, worker plan, request, individual pair files and worker
result. Local indices 0..8 map to originals 0,13,26,39,52,65,78,91,104. Star reference
5/original 65 differs from reporting anchor 4/original 52.

All nine feature records returned: original 0 has 503 retained features; each
other original has 1,024. Every real pair's saved landmark coordinates belong
to its associated feature records, and its digest ordering and alternating
calibration/holdout split agree. Descriptor/key hashes remain producer
witnesses: their preimages were not retained for independent reconstruction.

| Actual scientific refusal | Pairs |
| --- | ---: |
| `too few total mutual landmarks` | 15 |
| `no majority landmark consensus` | 8 |

Every refusal is the recorded `ContractError` with code
`UNMEASURED_INPUT_REGISTRATION_INADEQUATE`, not an unrelated exception. No
`FEATURE_UNAVAILABLE` outcome or unvisited suffix occurred. The historical
ordered call reference 5/source 8 (original 65/original 104) retained **22**
mutual landmarks and reproduced the exact earlier too-few-total message.
The old failure record did not retain this count.

Independent union-find components and edge-deletion checks agree with the saved
graph: **zero edges, nine singleton components, no bridges and cycle rank 0**.
The anchor connects only to itself. Historical reproduction permits this narrow
topology interpretation; it does not qualify geometry. With no returned real
transform, accepted-holdout/returned-transform branches of the checker are not
commissioned by this population. Other methods/pairs are untested.

## Controls, execution and accounting

The audit joined all seven separate control files and their aggregate record:
`geometry-0`, `geometry-2`, `observer-null`, `identity`,
`complementary-refusal`, `association-destroyer-restored`, and
`blob-sha-refusal-restored`. The two distinct fixture maps/metrics/guards agree
with frozen oracles; their swapped/restored associations are distinct. Actual
off/count/placebo signatures and canonical hashes match. The private observer's
256-entry collection is producer-asserted liveness; the audit directly inspected
the retained landmarks of the real pair calls. The authenticated decoder control
records zero refused decoder calls and one restored call. No control was rerun.

The run was frozen at `e4d4b894`; its plan binds 170 source paths. Actual source
bytes, interpreter, parent/worker argv, request, runtime and terminal records
match their pins. Runtime remains Python 3.12.10, NumPy 2.4.4, OpenCV 4.13.0,
tifffile 2026.5.2 and the recorded OpenCV build digest. Historical closure is
reused through the pinned completed coverage audit, including its explicit
contract metadata exception, not reimplemented or relabelled as Git-byte identity.

The worker Job has terminal active processes 0, total processes 2, terminated
processes 0, direct exit/EOF and completed drain, no attempted termination,
null error and no cleanup errors. Worker CPU is 52.859375 seconds and wall
53.25 seconds; peak committed memory is 8,263,897,088 bytes below 8 GiB. Parent
and worker finalization errors are empty; there are no missing retained records.

| Cumulative final accounting | Value |
| --- | ---: |
| CPU | 422.453125 seconds |
| Internal wall receipt | 457.0005757000763 seconds |
| Conservative next wall: prior 402.6725757 + root outer 54.3849439 | 457.0575196 seconds |
| Charged file extent | 3,948,978,385 bytes |
| Charged metadata extent | 23,777,739 bytes |

The new CPU is 54.25 seconds, including the complete worker Job. A separate
`Get-ChildItem -Force -Recurse -File` inventory found **46 files totaling
1,417,587 bytes**, exactly both file/metadata carry deltas. No TIFF or RAW was
written. Old snapshot reservations and the nonrefundable preparation allowance
remain charged. All caps pass; no performance comparison is claimed.

## Reproducible audit and retained evidence

The [audit source](work/independent-direct-pair-1-audit.py) remains unchanged:
20,396 bytes, SHA256
`df7d49229ca1d7dd50b88ba83665e32932571b2a2d6ab175dfa31c6bef2404ad`.
Actual command (Python exit captured explicitly):

```powershell
& 'C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe' -B 'experiments/m193c-output-grid/work/independent-direct-pair-1-audit.py' --plan-sha256 fb7a6b8e00503f07b4c6403b25403357f53fb967ba9466e6829e3fc1fe187179 --result-sha256 af1e60284bcb2888441113faf9835be3e7ab1091f08eeb38f2123f590c09a919 --outer-sha256 aa6e424f5af640ca2f5b3ad1c178fef5470fd5f0c9ce89d027f1302c594757a4 --console-sha256 75138d199eefc0a63444912c20e7f24a80c592b841201248a3035deba230a48d --exit-sha256 13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354
```

[Audit JSON](work/independent-direct-pair-1-audit.json): 13,711 bytes,
SHA256 `2b8b4a6ce4e2f245c95249555bdc3911f0802385fcc781b1427f2dc83bb9bef1`.
[Inventory](work/independent-direct-pair-1-inventory.json): 12,380 bytes,
SHA256 `3a242820af33b3dd9639382764d24df7e425c27b4dbda283f5180d4c4458a60a`.
The four audit artifacts fit the existing 128 KiB subset of the charged
1 MiB allowance. No failed audit attempt or subject retry occurred.
