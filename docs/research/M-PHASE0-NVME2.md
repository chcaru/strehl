# M-PHASE0-NVME2 — cold-device ARW read rate (MEASURED)

**Verdict: PASS; storage is not a material bottleneck.** The Samsung 980 PRO
2 TB read the registered 60 real ARWs at **6.338 decimal GB/s of compressed
input** with Windows' page cache bypassed. An immediate ordinary warm reread
reached **20.615 compressed-input GB/s**, **3.25x** the cold-device rate. A
replication measured 6.342 and 19.671 compressed-input GB/s (3.10x).

## 1. Provenance and exact byte definition

| item | value |
|---|---|
| preregistration and harness | `experiments/M-PHASE0-IOPERF/`, commit `40e41a63d9e4197469363f201fe10668cbb82ea7` |
| binary | `nvme.exe`, SHA-256 `D38CFB6C74FD8C555BCF11E5FDB15201EBB672E8651964CF5CA340B21606BD19` |
| command | `$env:IOPERF_RUN_LABEL='accepted-1'; cargo run --release --manifest-path experiments\M-PHASE0-IOPERF\Cargo.toml --bin nvme` (then `accepted-2`) |
| input environment / flags | `IOPERF_ARW_DIR` unset, so fixed default `D:\personal\macro\112MSDCF`; no CLI flags; only run label differs |
| host | AMD Ryzen 9 9950X3D, 16C/32T; 61.56 GiB visible RAM; Windows 11 Home build 26200; Balanced power |
| device | D: = Samsung SSD 980 PRO 2 TB, NVMe, disk 1 |
| workload | first 60 name-sorted ARWs, `DSC00001.ARW`–`DSC00060.ARW` |
| numerator | exact metadata lengths: **2,252,959,744 compressed-input bytes** |
| denominator | `Instant`/QPC elapsed seconds around thread creation, opens, reads and joins |

Every device arm opens read-only handles with
`FILE_FLAG_NO_BUFFERING | FILE_FLAG_SEQUENTIAL_SCAN`, uses 4096-byte-aligned
8 MiB buffers, and consumes every returned block. All 60 file lengths are
4096-byte multiples. The primary uses eight workers to populate the device
queue; the one-worker arm exposes queue-depth dependence. Ordinary buffered
arms omit `SEQUENTIAL_SCAN` so Windows retains pages for the immediate reread.

## 2. Commissioning before the headline

### Timer — PASS

The independently planted 200 ms sleep measured 200.084 ms in accepted run 1
and 200.051 ms in run 2; empty closures measured at most 0.0001 ms. Both clear
the preregistered 150 ms RED threshold.

### Cache control — PASS

| proof | accepted 1 | accepted 2 |
|---|---:|---:|
| buffered warm / buffered first read | **3.265x** | **3.109x** |
| buffered warm / direct read after warming | **3.337x** | **3.189x** |
| direct QD8 after / before warming | 0.975x | 0.973x |

The same ordinary read becomes more than 3x faster on immediate reread, proving
that the first pass came from the device rather than RAM. More importantly,
after those pages are resident the no-buffering arm stays at device speed,
within 2.7% of its pre-warm rate instead of jumping to 19.7–20.6
compressed-input GB/s. That is the registered proof that the cold number
bypasses the Windows cache.

After amendment A1, every mode and worker count produced the identical
ordered consumption witness `87937d284e4f0b38` and exact byte total. The
program's before/after selected-file metadata witness was identical
(`3287963d2d8f23f5`). Independent `Get-ChildItem -Force` snapshots of the whole
79-file directory also matched before/after: 2,959,888,384 bytes and metadata
SHA-256 `4AD822BCF1568ABAD400198647CA653C3F2CDD25D8E3EF2F441951DE7AF6C5F1`.
The capture library remained read-only.

## 3. Rates

Every rate is decimal **compressed-input GB/s**; no decoded-output numerator is
relevant to a device read.

| arm | accepted 1 rate / busy | accepted 2 rate / busy |
|---|---:|---:|
| no-buffering, 1 worker, before | 4.970 / 9.7% | 5.063 / 7.9% |
| **no-buffering, 8 workers, cold primary** | **6.338 / 7.4%** | **6.342 / 6.4%** |
| buffered, first read | 6.313 / 9.6% | 6.327 / 11.6% |
| **buffered, immediate warm reread** | **20.615 / 24.7%** | **19.671 / 30.2%** |
| no-buffering, 8 workers, after warm | 6.178 / 15.1% | 6.169 / 15.6% |
| no-buffering, 1 worker, reverse endpoint | 5.136 / 8.3% | 5.111 / 7.6% |

The unrounded primary cold rates, 6.338117 and 6.341589 compressed-input GB/s,
differ by only **0.055%**. Although other agents were active on this shared
machine, `GetSystemTimes` measured only 6.4–7.4% busy during the accepted
primary arms, far below the preregistered 75% contention threshold. No
contention rerun was required; the second accepted run is a quiet replication,
not a selected replacement. Warm-arm busy fraction includes the cached
memory-copy work itself.

## 4. D15 decision and Rust consequence

The primary cold rate is 1.268x the proposal's assumed 5 compressed-input
GB/s, so the assumption was conservative. These 60 files take **0.3555 s**
from the device versus 0.4506 s at the assumption.

D11's measured 32-thread output rate projects the same 60 frames'
4,404,019,200 allocated bytes to **3.116 s of decoder time**. Cold storage is
therefore **11.41%** of decode time, below the preregistered 20% materiality
bar and overlapable.

**Rust change:** D15 does not justify an IOCP prefetch subsystem. Ordinary
read/decode can feed D11's bounded decode-to-fold seam. Re-open IOCP only if a
future workload or decoder makes measured cold storage at least 20% of decode,
not because of the now-replaced 5 compressed-input GB/s assumption.

## 5. Bias directions and limits

The page cache could only flatter a purported cold rate; no-buffering plus the
3.1–3.3x warm placebo catches that failure. Queue underfill, per-file opens,
thermal throttling, unrelated D: traffic and CPU contention can make the
device look slow. Eight workers flatter a one-file-at-a-time consumer, so the
~5.0 compressed-input GB/s one-worker control is reported beside the 60-file
prefetchable capability.

Administrator-only standby-list purge was unavailable (the account is not
elevated), but it was not needed. `fsutil fsinfo sectorinfo D:` was also denied,
so the physical-sector size was not independently queried; successful aligned
no-buffering reads prove the chosen 4096-byte contract is accepted. This does
not disable the SSD controller's internal firmware/DRAM behavior, and no
independent disk-traffic counter was recorded. The stable replication and
explicit Windows-cache placebo are the evidence available for the product's
cold-read question.

An independent verifier then ran a third read-only arm: 6.334 compressed-input
GB/s cold, cache-control ratio 3.194x, timer/read-only controls PASS, and the
same `87937d284e4f0b38` witness in all six modes. It independently recalculated
the 5 compressed-input GB/s and 11.41% decisions without discrepancy.
