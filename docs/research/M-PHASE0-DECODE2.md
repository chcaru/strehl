# M-PHASE0-DECODE2 — real-ARW decoder scaling (MEASURED)

**Verdict: PASS.** The shipped black-box decoder delivers **381.0 decimal
MB/s of allocated u16 output at one Rayon thread** and **1,413.4 decimal MB/s
at 32 threads**. Those clear D11's preregistered 200 allocated-output MB/s/core
and 1.0 allocated-output GB/s aggregate bars. It has real intra-frame
parallelism, but it is effectively saturated by 16 threads.

This supersedes the interpretation of the bare `1245 MB/s` in
`M1-decode-measured.md` §4. That was compressed-input throughput from
concurrent files under an informal "not read earlier in this session" cache
condition. It remains useful prior art, but it is neither this numerator nor
this experiment.

## 1. Provenance and protocol

| item | value |
|---|---|
| preregistration and harness | `experiments/M-PHASE0-IOPERF/`, commit `40e41a63d9e4197469363f201fe10668cbb82ea7` |
| benchmark binary | `decode-42056de31aa0ddae.exe`, SHA-256 `6E38CCB515BF16F97A06A4F9AB105CF2DEC7C4704DC814905D8C7735019A5C45` |
| command | `& .\experiments\M-PHASE0-IOPERF\run-decode-sweep.ps1` |
| toolchain | `rustc 1.98.0`; `divan 0.1.21`; `strehl-raw` / `rawler 0.7.2`; bench profile opt-level 3, thin LTO, one codegen unit |
| host | AMD Ryzen 9 9950X3D, 16 cores / 32 logical processors; 61.56 GiB visible RAM |
| OS / power | Windows 11 Home build 26200; Balanced power scheme |
| input | `D:\personal\macro\112MSDCF`; name-sorted files 1, 30 and 60 |
| environment read by harness | `IOPERF_ARW_DIR=D:\personal\macro\112MSDCF`; `RAYON_NUM_THREADS` set to each table row; no benchmark CLI flags |
| sampling | 7 Divan samples x one serial three-file iteration, forward then reverse thread sweep |

The three compressed files total **112,066,560 bytes**. Each decode allocates
73,400,320 bytes (`7168 x 5120 x u16`), so an iteration produces
**220,200,960 allocated-output bytes**. The benchmark performs an untimed
decode first; these are explicitly **warm/page-cached CPU-decode rates**, not
cold-ingest rates.

All rates below are decimal. Divan's byte counter is allocated output. The
compressed-input rate is derived from the *same median duration* using the
fixed measured ratio `112,066,560 / 220,200,960 = 0.508928571`; no second
timer or ambiguous numerator is involved.

## 2. Controls ran first

### Timer RED — PASS

The second Divan arm performs the identical decodes and then requests an
independently planted 200 ms sleep. Median added time:

| Rayon threads | forward delta | reverse delta |
|---:|---:|---:|
| 1 | 203.5 ms | 211.7 ms |
| 2 | 288.9 ms | 287.8 ms |
| 4 | 246.6 ms | 237.2 ms |
| 8 | 193.8 ms | 203.1 ms |
| 16 | 191.7 ms | 189.6 ms |
| 32 | 188.4 ms | 189.3 ms |

Every arm exceeded the preregistered 150 ms detection floor. Overshoot at 2–4
threads is scheduler/benchmark variation and is not claimed as timer accuracy;
the control's job is to prove that the instrument detects a known slowdown.
Divan reported 100 ns timer precision.

### The decode is consumed — PASS

Before timing, all three frames matched the independently documented
`7168 x 5120` allocation and `7032 x 4688` active region and each contained
**33,003,520 nonzero samples**. Full-buffer FNV-64 witnesses were:

| file | full-buffer FNV-64 | timed sampled FNV-64 |
|---|---|---|
| `DSC00001.ARW` | `4d1cf309079b6b25` | `de32ae3c7f72a96a` |
| `DSC00030.ARW` | `1963b646206ff2b9` | `8e5deba388c4e6f0` |
| `DSC00060.ARW` | `083dd06c8504e652` | `074c341d68b93140` |

Every timed iteration re-derived and checked the sampled witness, then passed
both it and the decoded allocation through `divan::black_box`. All twelve
fresh processes also asserted that Rayon's actual pool size equalled the
requested curve point. Thus this is not an optimised-away call or an
environment variable that failed to resize an already-created pool.

## 3. Scaling curve

Per AGENTS rule 16, `chosen` is the smaller of the forward and reverse median
durations. Both timings and their whole-process machine-busy fractions remain
shown.

| Rayon threads | forward median / busy | reverse median / busy | chosen | compressed-input MB/s | allocated-output MB/s | speedup |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 594.1 ms / 11.0% | 577.9 ms / 7.1% | 577.9 ms | **193.9** | **381.0** | 1.00x |
| 2 | 311.9 ms / 10.0% | 315.0 ms / 10.1% | 311.9 ms | **359.3** | **706.0** | 1.85x |
| 4 | 219.8 ms / 13.2% | 229.9 ms / 15.8% | 219.8 ms | **509.9** | **1,001.8** | 2.63x |
| 8 | 189.5 ms / 18.9% | 194.1 ms / 16.6% | 189.5 ms | **591.4** | **1,162.0** | 3.05x |
| 16 | 156.0 ms / 20.6% | 155.5 ms / 18.1% | 155.5 ms | **720.7** | **1,416.1** | 3.72x |
| 32 | 155.8 ms / 17.0% | 158.2 ms / 20.9% | 155.8 ms | **719.3** | **1,413.4** | 3.71x |

This is the ambiguity the old bare number hid: at full machine the identical
work is **719.3 MB/s compressed input** or **1,413.4 MB/s allocated output**,
a 1.965x difference caused only by the numerator.

## 4. D11 decision and Rust consequence

At one thread, 381.0 MB/s of allocated output is 1.91x the proposal's
200 MB/s/core bar; it is not remotely "much less" than it. At full machine,
1.413 allocated-output GB/s is 1.41x the proposal's 1 allocated-output GB/s
acceleration bar. D11's owned-decoder branch is therefore **FALSE**. Its other
conjunct is also false in existing evidence: `BUILD-SPEED/REPORT.md` §2
measures the fold at 98.5% of the warm default run, so decoder dominance after
D12 has not been shown.

**Rust change:** retain `strehl_raw`/rawler; do not build an owned Sony LJPEG
decoder. The proposal's bounded decode-to-fold channel remains the useful seam
for overlap and future substitution. With the fold currently dominant, that
queue is architecture/isolation work, not evidence for replacing the decoder.

## 5. Bias directions and limits

Page-cache warming makes a first-run end-to-end claim look too fast, but here
it is explicit and intentionally removes storage from the CPU-decode
estimand. Shared CPU or memory contention can only make these rates look slow;
accepted process-wide busy fractions were 7.1–20.9%. Taking the faster
alternating median biases toward machine capability, not typical shared-box
latency. Compression ratio can move the compressed-input rate without changing
decoded work; the paired output rate prevents that failure.

Not verified here: CCD/core affinity, decoder scaling on another camera or
compression ratio, outer parallelism across files, and cold-storage cost.
M-PHASE0-NVME2 measures the last quantity separately.

An independent verifier reran the one-thread executable after the report was
written: baseline median 610.2 ms, planted-arm median 822.2 ms (212.0 ms RED
delta), with all geometry, checksum, byte-count and Rayon-pool assertions
passing. It also independently recalculated all 18 curve rates/speedups from
the raw medians and found no discrepancy.
