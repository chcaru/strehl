# Stock chip reference: resource refusal

MEASURED on September 26 at project HEAD `856ddb64`: neither complete299-source
stock reference produced an output. The first actual render exceeded its24GiB
job commitment bound. One separately authorized resource-only retry exceeded
40GiB. Close this fixed reference attempt; there is no photographic quality
verdict, algorithm rejection, native improvement or SOTA result.

| Actual vendor attempt | Wall seconds | User+kernel CPU seconds | Peak job committed bytes | Outcome |
| --- | ---: | ---: | ---: | --- |
| run-2,24GiB cap | 46.922 | 420.75000 | 25,829,523,456 | Owned job terminated at memory bound |
| run-3,40GiB cap | 124.828 | 1,135.34375 | 43,231,391,744 | Owned job terminated at memory bound |

These are individual failed-job costs, not speed benchmarks. Each job's
terminal accounting has zero active processes, successful owned termination
and no cleanup errors. No master TIFF exists. Fresh full-file scans of all299
prepared TIFFs precede and follow each actual attempt; each pair of input
receipts is byte-identical. Those scans are outside the vendor timing.
The original RAW files were neither opened nor restatted. Source/runtime
bindings remained unchanged through each attempt.

The retry preserved every executable argument except its output path:
8threads,batch4,no-OpenCL,no-whitebalance,no-contrast, all299 ordered unaligned
7032x4688 RGB16 TIFFs, stock alignment/crop and other defaults. Immediately
before run-3, the saved guard recorded53,620,277,248bytes available out of
66,094,223,360physical bytes, with no other named scientific/vendor job.
This was an availability snapshot, not a memory reservation.

Earlier refusals are also retained. The old runtime lacked libprotobuf.dll;
an existing complete cached bundle supplied exactly matching common binaries
and two additional libraries, with no installation. The preparation helper
then checked the wrong output channel after actual successful version/help
calls. Inventory-1 caught an incorrect29-common-file assertion; the actual
manifest has28 common files and two additions. Inventory-2 passed, but run-1
stopped before image access because the order receipt lacked an assumed SHA
field. The developer receipt supplies those original hashes; the order receipt
supplies path/size/mtime only. Both source-review misses and corrections are
explicit in independent-review.md. Inventory-3 passed the corrected metadata
path before either actual stack attempt. These prefixes were not image runs.

Commands actually run from the repository root using the installed Python3.12
with `-I -B -X faulthandler`:

```text
experiments/chip-upstream-reference/run.py inventory --out experiments/chip-upstream-reference/inventory-1
experiments/chip-upstream-reference/run.py inventory --out experiments/chip-upstream-reference/inventory-2
experiments/chip-upstream-reference/run.py full --inventory experiments/chip-upstream-reference/inventory-2 --out experiments/chip-upstream-reference/run-1
experiments/chip-upstream-reference/run.py inventory --out experiments/chip-upstream-reference/inventory-3
experiments/chip-upstream-reference/run.py full --inventory experiments/chip-upstream-reference/inventory-3 --out experiments/chip-upstream-reference/run-2
experiments/chip-upstream-reference/resource-retry.py --inventory experiments/chip-upstream-reference/inventory-3 --out experiments/chip-upstream-reference/run-3
```

Executable/runtime identities and actual version/help calls are retained in
program-manifest.json. Each run folder records the entire299-file command,
environment, limits and actual process outcome. The independent result review
is independent-results.md. The prepared photographic viewer was not executed;
there is no complete candidate image to inspect or show. No further cap,
thread, batch-size or subset retry follows this fixed branch.
