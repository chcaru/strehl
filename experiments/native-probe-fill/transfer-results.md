# Speed improvement transfers to the complete second stack

MEASURED and independently verified,2026-09-09. The unchanged row-parallel probe filler reduces complete native render time on the full22-frame109MSDCF stack from20.344 to15.625seconds at the per-arm minima:23.20% less wall time,1.3020x throughput. Both timing directions agree(23.49%/23.20%); median reduction23.34%. All four complete7032x4688 RGB16 TIFFs and decoded pixel payloads match exactly.

Actual original/parallel/parallel/original times:20.422/15.625/15.625/20.344seconds. Owned CPU work rises5.79% at per-arm minima; peak Job commitment remains about2.86GiB. Host busy includes each job's own use and is higher on parallel runs. This is a different complete macro stack from the earlier eight-frame112 prefix; it is not a mirror or a new physical calibration.

Command, exit0: Python312 -I -B experiments/native-probe-fill/run-native.py --transfer-109, runner/plan commit e416d675. Held original and candidate executables are reused without rebuilding. The map is the existing canonical direct109 sidecar,22placed/ref11/digest b70554b8cfd9b93e, matched independently to the exact ordered filename/size manifest. No new solve is run and no solve time from112 is assigned to109. Complete process cost includes current input decoding, map loading/coverage, image work, startup and final output completion.

The836,440,064bytes of original inputs were hashed read-only before execution; paths, sizes, timestamps and SHA256 are in transfer-plan-109.json. Full results, all actual arguments, profile counts, process outcomes and output hashes are in transfer-109. Large native TIFFs stay local; compact evidence is versioned. Independent interpretation is transfer-results-review.md.

No competitive scorecard bar, alignment-truth or photographic-quality claim moves. The exact default is retained. Source review now supports one next small candidate: omit unconsumed synthetic probe R/B outputs while preserving all source channels and exact green operations. See next-green-probe.md and experiments/native-green-probe/charter.md; it is unverified until compiled controls and native output/timing checks pass.
