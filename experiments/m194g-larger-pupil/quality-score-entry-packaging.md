# Separate entry receipts under the existing output limits

Prospective source-only packaging correction before any quality computation.
No mathematical rule, input, crop, output population, precision bar or resource
ceiling changes. Root found the initial scorer embedded all38 complete checked
entries in its one final JSON, although the held Store.json cap is4MiB/file.

Standard-library inspection of the actual successful intended12 reader result
69dc4b40673aec0b25fd4d900350bd2a4b4b905c81187559188e16bfa378f7f4
(1,799,058 bytes) gives canonical individual checked-entry sizes
136327,136346,136311,136330,136419,136438,136403,136422,136407,136411,
132152,132150 bytes. Their sum is1,628,116 bytes. Repeating even the smallest
retained descriptor38 times would be5,021,700 bytes, already above4,194,304,
before the other result metadata or numerical tables. The mean-size38
extrapolation is approximately5,155,701 bytes. This is a demonstrated
serialization scale from retained records, not a measured final38 artifact or
quality/runtime result. It shows why the previous layout was expected to refuse.

The revised controller persists each complete checked entry as its own
entries/entry-NN.json before proceeding to the next. The final result contains
38 ordered FileRefs. Each current-size child is comfortably below the unchanged
per-file limit, but actual writes still check that limit and may refuse. The
ordinal-to-pixel-hash map and common geometry alone support subsequent repeated
loads; full duplicate plan/receipt objects no longer accumulate in memory.
The original source/input chains and every admitted entry remain retained and
are rehashed by the same Store final checks. The score's cumulative32MiB output
and120CPU/240wall/32MiB named-array limits remain unchanged. No cap expansion or
skipped entry is permitted if the actual package still refuses.
