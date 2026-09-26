# Independent closure: stock chip reference

MEASURED by the retained bounded-job receipts: both complete-299-input attempts
stopped at the committed-memory limit. Neither produced a whole-stack TIFF or
successful output receipt. Close this fixed reference route; there is no
photographic quality verdict and no further resource or recipe retry.

| Attempt | Configured commitment | Observed peak job commitment | Wall seconds | Job CPU seconds |
| --- | ---: | ---: | ---: | ---: |
| run-2 | 24 GiB / 25,769,803,776 bytes | 25,829,523,456 bytes | 46.922 | 420.750 |
| run-3 | 40 GiB / 42,949,672,960 bytes | 43,231,391,744 bytes | 124.828 | 1,135.34375 |

Both process receipts name `child committed-memory bound`, record successful
owned termination, empty cleanup-error lists, terminal accounting and zero
remaining active processes. The observed peaks can exceed the configured ceiling
at the monitoring sample. These are job commitment and user-plus-kernel CPU,
not physical-memory usage or completed-render speed measurements. Both retained
900-second wall and 18,000-second CPU limits.

VERIFIED independently from actual saved receipts and current file hashes: each
attempt has byte-identical 299-entry input-before/input-after receipts; no output
TIFF exists. The runner performed the full input hashes, and the reviewer compared
those retained results without repeating the 118-GB scan. All 9 run-2 and 20
run-3 bound files still match, as do all 30 staged executable/DLL files. Executable
SHA256 remains `e256176d70bec54bb51a448b2adc452e7f49d21bc5042b40689a3257bbfdee9e`.
Both commands have 306 arguments; executable and every argument except the owned
output path are identical. All 299 ordered TIFFs, 8 threads, batch size 4,
CPU/no-OpenCL and image settings were preserved. No original RAW was read.

Run-3's immediate prelaunch snapshot passed: 53,620,277,248 bytes available versus
51,539,607,552 required (48 GiB), with no other watched scientific/vendor process.
That snapshot did not guarantee the vendor could finish within 40 GiB. The
single resource-only retry therefore exhausted the explicitly authorized route.

Actual render invocations, after the successful inventory-3:

```text
python -I -B -X faulthandler experiments/chip-upstream-reference/run.py full --inventory experiments/chip-upstream-reference/inventory-3 --out experiments/chip-upstream-reference/run-2
python -I -B -X faulthandler experiments/chip-upstream-reference/resource-retry.py --inventory experiments/chip-upstream-reference/inventory-3 --out experiments/chip-upstream-reference/run-3
```

Earlier missing-runtime, wrong-count and receipt-schema failures remain preserved;
they were not completed image trials. The two resource refusals do not establish
whether this stock upstream workflow would improve the chip, why our native stack
has artifacts, or whether another engine/setting can complete. Its independent
alignment, developed CA-off RGB and 8-bit workflow remain comparison limitations,
but no image was available to assess even within that limited scope. No algorithm
port, default change, partial-stack substitute or quality claim follows.
