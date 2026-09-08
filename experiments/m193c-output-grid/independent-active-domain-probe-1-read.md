# Independent read of actual active-domain probe1

**VERIFIED saved-record disposition: complete diagnostic, with decoder byte
agreement on the explicitly declared 7032x4688 rectangle for original0.**
All 4,688 saved candidate row hashes equal the actual primary receipt's row
hashes. The entire-domain hash and common-visible-subset hashes also agree.
Native1 remains **REFUSED**; this diagnostic does not independently establish
the physically correct sensor crop or admit a native derivative.

This is an independent audit of the root-authored probe's actual records and
their bytes, invocation, source and process associations. It did not import
the probe, NumPy, rawpy or any image helper; it did not decode RAW/TIFF, render,
register, or introduce another numerical method. The retained snapshot was
stream-hashed as bytes. No original corpus file was opened.

## Actual evidence and commands

The actual execution was released from commit `3b10e8ff`. The released source
is `active-domain-probe.py`, 13,219 bytes,
`db541d3f826da7d32617002a90ed48d8c3cf2bb401f09b18331be67b6807086b`,
with specification 5,627 bytes,
`783df10b5e2108f9466ca5a81924c02e50298bd5dff8c6d9738a2229bae69563`.
The prior [independent source review](independent-active-domain-probe-source-review.md)
records the pre-execution findings and their repairs.

| Actual artifact | Bytes | SHA-256 |
|---|---:|---|
| [Release](active-domain-probe-release-1.json) | 40,553 | `b540b3dd8d88587a87a98e5347c579221bc46dd40f014ddd7e0e70de17452538` |
| [Parent result](active-domain-probe-1/result.json) | 4,618 | `78330bd2c6f83ff9791fdd3406679ea1e7cd766d1968375e0a418f2185ef688e` |
| [Worker result](active-domain-probe-1/worker.json) | 350,731 | `1031e0bee6bec02473981911634857a700cc59f414d575cd18c7ff9a9b9cb03c` |
| [Worker log](active-domain-probe-1/worker.log) | 387 | `8482226fc988beb3d9c4fe951d5eb1b05e002b228ecf8372691643a7a84403c3` |
| [Actual root console](work/active-domain-probe-1-console.txt) | 390 | `e529731c77e828af28b004b365c0e147fbc0f665e2f981b8da8c10526a79d6a2` |
| [Actual root exit](work/active-domain-probe-1-exit.txt) | 3 | `13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354` |
| [Actual root outer observation](work/active-domain-probe-1-outer.json) | 944 | `97358d1936cf9229990c8ae4788f7b24a9ab6e398afd4150d8c01288cfc503bd` |

The original argument arrays in the parent and worker records exactly equal
the two committed release commands after substituting the release SHA for
`ACTUAL_RELEASE_SHA256`. They use the pinned Python312 executable, `-B`,
`-X faulthandler`, distinct fresh `cache-parent`/`cache-worker` prefixes,
the same probe source and release, and the literal worker flag only on the
worker. The observed subprocess command equals the worker record's command.
The outer root command equals the parent record's command and binds the
same release SHA. The root exit file contains actual `0` with CRLF.

The independent audit command actually run, from repository root, was:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B experiments/m193c-output-grid/work/independent-active-domain-probe-1-audit.py
```

The final [stdlib-only audit source](work/independent-active-domain-probe-1-audit.py)
is 9,572 bytes, SHA-256
`880f9cb397d7bebda70663276bb09b4b7fb79e522b6fdbcfbe358dbe137b22d9`.
It returned exit0 and `PASS_SAVED_PROBE_RECORD_AUDIT`. Its final pass rehashed
221 distinct files, verified 142 released sources and 73 input entries, and
compared all 4,688 rows. An initial metadata-audit pass counted220 files but
only cross-associated the separately declared snapshot reference; I caught
that scope omission before this verdict, added explicit hashing of the four
separate release dependency fields, and reran this byte/metadata audit only.
The corrected scope includes actual snapshot bytes. No probe was repeated.

## Source, dependency and actual-input association

Every released source currently matches its SHA/extent. All142 paths are
tracked in `3b10e8ff` and have no working-tree diff from that commit. The
committed release bytes themselves reproduce the external release SHA.
All73 released input entries and the separate runtime, adjacent-DLL, primary
and snapshot refs match actual bytes. Repeated references to the same resolved
path have no conflicting digest or extent.

The captured runtime remains Python3.12.10, NumPy2.4.4, rawpy0.27.0,
LibRaw0.22.1. I rehashed its actual executable, six recorded module files and
the two supplemental adjacent DLLs. The supplement still binds runtime SHA
`413975cbbbf5b1dc33407e6be1aa23e9195dc4471f1ee7e9de99f903dccd9442`.
The supplementary `raw_r.dll` and `vcomp140.dll` bytes retain the previously
reviewed pins. The source's pre-import version/file checks, post-import four
module-path checks, and final byte rechecks are required on its actual
successful path. The result does not serialize separate per-file before/after
tables; I do not invent those tables or claim exhaustive loaded-library
hermeticity from the completion status.

The primary is the actual original0 receipt at
`native-derivative-1/frame-00/native/result.json`, 350,873 bytes,
`e02482a38f3f15a2cc89ee83a809fdbdc590568db8a439754e956f20f8251427`.
Its absolute snapshot reference and the probe's repository-relative reference
resolve to the same retained `DSC00016.ARW`: 39,030,784 bytes,
`35ccc60a2cadbcdc999fb6765a326f5baaa298776fb951d12287e05c5892ed36`.
Both SHA and extent match the actual snapshot. Thus this comparison does not
silently use another frame, another decoder receipt or a cropped TIFF.

## What the actual diagnostic observed

Both records describe origin(0,0). The primary domain is 7032x4688. Rawpy
reported visible7028x4688 inside full7168x5120, margins0 and flip0.
The saved owned candidate has 65,932,032 bytes and the reviewed source copies
it inside the decoder context. The actual worker's successful path also
checks ownership and hashes the live visible view before closing its owner.

The candidate whole-domain hash, recorded comparison hash and actual primary
whole-domain hash all equal:

`e5b8c066623e6f64d4f945ae22dafb4ccb5238fd76fff36f39de8a16cd4739e1`.

All4,688 candidate row hashes equal the corresponding primary entries in
order, with exact `mismatch_rows=[]`. Both common-subset digests equal:

`53076376f2fbb40eb835874dedbed6b6854538f573eb86c6fe0a4cc248ef6c2c`.

The four disputed columns have the following **recorded probe observations**;
this audit did not reconstruct samples or recalculate these ranges:

| Column | Samples | Zero samples | Minimum u16 DN | Maximum u16 DN |
|---:|---:|---:|---:|---:|
| 7028 | 4,688 | 0 | 4,224 | 14,788 |
| 7029 | 4,688 | 0 | 7,442 | 14,827 |
| 7030 | 4,688 | 0 | 4,223 | 14,790 |
| 7031 | 4,688 | 0 | 7,432 | 14,721 |

Each column also has its actual full-column digest in the bound worker
result. Both fixed row-code witnesses are true: the one-code mutation changed
the digest and restoration recovered it. The frozen source makes these
assertions on the actual row-hash path; the baseline whole/row comparison was
not replaced with the mutated row. No sample was excluded to obtain agreement.

## Process completion and carried resources

Parent and worker are `COMPLETE_DIAGNOSTIC_ONLY`, with no error or
finalization errors. The actual child observation has exit0, direct exit and
pipe EOF true, no cleanup errors, terminal Job accounting true and active0.
Drain completed at its first recorded zero-active observation. Termination
was not attempted; its success flag is false rather than evidence of a kill.
The worker log's final summary binds the actual worker path and complete
status. The parent stdout similarly binds the actual parent result path.

Job CPU is1.5625 seconds: 10,312,500 user plus5,312,500 kernel100ns ticks.
Observed child wall is1.5939999999245629 seconds and peak Job committed memory
is238,780,416 bytes. These are below the actual30CPU/60wall/2GiB/1MiB-log
limits. They are operational observations, not speed or RSS claims.

The parent result's saved work is an earlier observation. The actual final
stdout reports cumulative37.71875CPU seconds,32.10093049996067wall seconds,
239,908,463 file bytes and3,079,412 metadata bytes. All are within the original
shared1200CPU/1800wall/4GiB/128MiB ceilings. The carried prior was34.984375CPU,
29.3349305wall,239,552,727file and2,723,676metadata bytes, including the explicit
preparation reservation. The three retained probe outputs total355,736 bytes;
adding these to the carried file/metadata figures reproduces final stdout
exactly. No additional outputs or first-publication failure files were present.

The reservation's ten enumerated metadata files total103,527 bytes; its
65,536-byte release allowance and actual40,553-byte release fit within the
fixed1MiB reservation. This remains conservative accounting, not measured
write I/O. Root's actual outer elapsed is2.8091498seconds. The next carry's
wall32.1440803 is derived from prior29.3349305 plus that outer observation;
it is larger than the internal final work sample and does not reset native1.
This later independent audit is not retrospectively included in the probe's
already-recorded work totals.

## Scoped conclusion

The evidence distinguishes a declared viewport difference from decoded-payload
disagreement on this one primary-declared rectangle: the independent full-buffer
ROI and primary payload agree throughout it, including the four extra columns.
This supports a prospectively explicit primary sensor-ROI reader contract.
It does **not** prove those columns are physically valid photosites, settle the
photographically correct crop, or establish any other frame's agreement.

The original native result remains `REFUSED`, SHA-256
`4299877897694e655ef04f88001e6406058c1b2d0efddded6d525510fbc9dfe0`,
with its first refusal retained. No other original was decoded, no native
pass was minted by this audit, and no coverage/registration/quality claim
follows from this single-snapshot diagnostic.
