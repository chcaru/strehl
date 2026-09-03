# M-PHASE0-IOPERF

Reproducible instruments for the proposal's two unmeasured phase-0 speed
gates:

* **D11 / DECODE:** real-ARW `divan` scaling of the public
  `strehl_raw::decode` black box from 1 through 32 Rayon threads.
* **D15 / NVME:** a 60-file Windows read test using
  `FILE_FLAG_NO_BUFFERING`, paired with an ordinary warm reread that proves the
  cache bypass is active.

Read `PREREGISTRATION.md` before the reports. Captures are opened read-only.
No harness writes under `D:\personal\macro`.

## Reproduce

From the repository root:

```powershell
# Forward and reverse 1,2,4,8,16,32 decode sweeps.
& .\experiments\M-PHASE0-IOPERF\run-decode-sweep.ps1

# Cold/direct, buffered-first, warm, and after-warm direct device arms.
$env:IOPERF_RUN_LABEL = 'repeat-1'
cargo run --release --manifest-path `
  .\experiments\M-PHASE0-IOPERF\Cargo.toml --bin nvme
Remove-Item Env:\IOPERF_RUN_LABEL
```

Divan's displayed byte counter is explicitly **allocated decoded-output
bytes/s**. Each run prints the exact compressed-input/allocated-output ratio so
the compressed-input rate is derived from the same elapsed time, rather than
from a second benchmark.

The NVMe program reports decimal
**compressed-input GB/s** (`exact file bytes / perf-counter seconds`) on every
arm. Its primary cold-device arm is the 8-worker
`FILE_FLAG_NO_BUFFERING` read before the buffered cache prime.

Results and gate decisions are in:

* `docs/research/M-PHASE0-DECODE2.md`
* `docs/research/M-PHASE0-NVME2.md`
