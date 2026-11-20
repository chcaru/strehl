# A7CR stacking performance, round 3: measurements

Evidence and scripts for
[the round-3 plan](../../docs/proposals/2026-11-a7cr-stacking-performance-plan-3.md),
taken on 2026-11-19. The plan holds the findings; this folder holds what they rest on.
Nothing here changes the engine.

Host: Ryzen 9 9950X3D, 64 GB, RTX 5090 and the integrated Radeon, D: Samsung 980 PRO,
C: WD SN8100, Windows 11 26200; WSL2 with Debian 13 (kernel 6.6.87.2). Engine
`strehl 0.1.0-alpha.6 (8571ac879b50-dirty)`. Stack: the scarab capture
(`D:/StrehlCaptures/stack-1794786793543-11226`, read-only), and for the smaller runs a
copy of its first 96 archives and journals. Host idle (0-5 % CPU) before every timed
run; one run at a time.

## Evidence

| File | What it is |
| --- | --- |
| `evidence/runs.txt` | One line per traced render: binary, environment, arguments, wall, user and kernel CPU, bytes read, peak private memory, page faults, host load before, exit code, output SHA-256 |
| `evidence/engine-traces.txt` | Per run: the fold trace (`STREHL_FOLD_TRACE=1`), read modes, stage lines and, for `gpu-profile-l24`, the device's per-kernel time (`STREHL_GPU_PROFILE=1`) |
| `evidence/osbench-windows.txt`, `evidence/osbench-wsl.txt` | `osbench.rs` on Windows (NTFS on C:) and in WSL2 (ext4 on its virtual disk, then a Windows drive through `/mnt/c`) |
| `evidence/wsl-engine.txt` | The engine built in WSL2 on the 24-plane copy: CPU route with an empty cache and cached, `STREHL_GPU_FOLD=on`, and `auto` |
| `evidence/codec-bench-windows-wsl.txt` | `strehl-raw-codec`'s `v2-bench` on the same eight archives on both systems |
| `evidence/capture-cadence.txt` | `capture-cadence.py` over every run under `D:/StrehlCaptures` |
| `evidence/pi-usb-check.txt` | The Pi's USB devices and its kernel log's enumerations, by port, speed and product |

Runs in `runs.txt`:

| Tag | Run |
| --- | --- |
| `full-a` | later render, 196 planes, stack on D:, default route |
| `l8-a` | `--limit 8` (three passes: the depth is unusable, so it renders again) |
| `win-cpu-first`, `win-cpu-later`, `win-cpu-later2`, `win-gpu-later` | 24-plane copy on C:, CPU route with an empty cache then cached, then the GPU route |
| `gpu-profile-l24` | `--limit 24` on D: with the device profiler and the fold trace |
| `igpu-on-l24` | the product build with the NVIDIA driver hidden: refuses the integrated device |
| `igpu-auto-l24` | a throwaway build with the discrete-device check behind a switch, on the integrated Radeon: the reference bytes, 99.8 s |
| `c-first`, `c-later-1..3` | the whole stack copied to C:, files purged from the cache before each run |

## Scripts

| File | What it does |
| --- | --- |
| `osbench.rs` | First-touch page faults, a blocked-thread round trip, direct and cached file reads, open cost; standard library only, the same source on both systems (`rustc -O osbench.rs`) |
| `wsl-build.sh`, `wsl-osbench.sh`, `wsl-engine.sh` | Build the engine in WSL with a user-level toolchain, run `osbench`, run the engine comparisons |
| `capture-cadence.py` | Per-run capture timing from the journals (read-only) |
| `pi-usb-check.py` | Reads the Pi's sysfs USB speeds and kernel log over the workspace's SSH runner; changes nothing |
| `purge.py` | Drops a folder's files from the Windows file cache without reading them |

The traces were taken with round 2's
[`trace.py`](../a7cr-stacking-performance-2026-11-18/trace.py), which now also records
the process's page faults, other I/O operations and bytes written.

## What was removed afterwards

The WSL toolchain and build, the 24-plane and whole-stack copies on C:, and the
experiment build were deleted after the runs. The source edit for the experiment build
(one condition in `crates/strehl-gpu/src/context.rs`) was reverted before anything else
was built; it was never committed.
