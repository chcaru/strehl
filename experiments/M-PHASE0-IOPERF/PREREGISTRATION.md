# M-PHASE0-IOPERF — preregistration

**Registered:** 2026-09-02, before any payload byte in the nominated ARWs was
read by this lane, before any ARW was decoded by this lane, and before either
timing harness existed. Reconnaissance before registration was limited to
proposal/rule/prior-report reading, directory and file-metadata enumeration,
and hardware/OS queries.

**Owned paths:** `experiments/M-PHASE0-IOPERF/`,
`docs/research/M-PHASE0-DECODE2.md`, and
`docs/research/M-PHASE0-NVME2.md` only.

**Read-only input:** the first 60 name-sorted `*.ARW` files in
`D:\personal\macro\112MSDCF`, `DSC00001.ARW` through `DSC00060.ARW`.
Metadata reconnaissance found exactly **2,252,959,744 compressed bytes**. The
harness must open captures read-only and must never create a sidecar there.

### Amendment A1 — deterministic read checksum after commissioning

The first two NVMe commissioning runs passed the registered timer, byte-count,
cache-ratio, contention, and read-only controls, but exposed that the printed
eight-worker checksum changed with scheduler assignment: per-worker hashes
were XORed, so assigning the same file to another worker changed the aggregate.
This does not affect bytes or timing, but it makes the consumption witness
needlessly uninterpretable. Before accepting a measurement, checksum storage is
changed to one atomic slot per file and folded in filename order after all
workers join. The estimand, files, ordering, I/O flags, workers, buffer, timer
and every registered bar remain unchanged. Runs before this amendment are
commissioning only; the reported run must reproduce one deterministic checksum
across direct and buffered arms.

## 1. Questions and independent bars

The authoritative proposal's D11 question is whether the shipped decoder,
treated as a black box, has intra-frame parallelism that scales from one thread
to the full 16-core/32-thread machine. Its quantitative statements are:

* **at least 1.0 GB/s aggregate** makes the proposal's floor conservative; and
* an owned decoder is built only if the shipped decoder is both
  **much less than 200 MB/s/core of u16 output** and dominant after D12.

This lane operationalises "fast enough" conservatively as both
**at least 200,000,000 allocated-output bytes/s at one thread** and
**at least 1,000,000,000 allocated-output bytes/s at 32 threads**. Failure of
either registered threshold is reported; the proposal's owned-decoder trigger
still remains conjunctive with post-D12 dominance. The pre-existing
`BUILD-SPEED/REPORT.md` result that the fold is 98.5% of a warm run is external
to this instrument and will be identified as such, not re-measured here.

The authoritative D15 comparison is the proposal's assumed
**5,000,000,000 compressed input bytes/s**. A result below 4.5 GB/s calls that
assumption optimistic; above 5.5 GB/s calls it conservative; between those
values is consistent at this instrument's intended 10% resolution.

Separately, storage is a **material product bottleneck** if its measured
60-file cold-device time is at least 20% of the decoder's projected 60-file
full-machine time. This is deliberately stricter than asking merely whether
the device misses 5 GB/s. If material, the Rust consequence is queued IOCP
prefetch; otherwise storage does not independently justify IOCP.

All byte rates use exact byte counts and decimal SI seconds:

* **compressed-input rate** = sum of on-disk ARW lengths / elapsed time;
* **allocated-output rate** = sum of `Frame::allocated_bytes()` / elapsed time.

No bare "GB/s" is admissible. Binary GiB/s may be shown only as a secondary,
explicitly labelled conversion.

## 2. D11 / DECODE protocol

The committed benchmark is an isolated Cargo package under this experiment
and pins `divan = 0.1.21`; the repository currently has no `divan` dependency.
It calls only the public `strehl_raw::decode` seam and does not inspect rawler.

The decode workload is files 1, 30, and 60 from the registered 60-file set,
decoded serially inside each Divan iteration. Serial file dispatch is
intentional: changing only `RAYON_NUM_THREADS` then measures the shipped
decoder's intra-frame scaling rather than introducing an outer file pool.
Each process performs an untimed preflight decode first, making the D11 result
explicitly **warm/page-cached CPU decode**, not a claim about cold ingest.

Settings are `RAYON_NUM_THREADS = 1, 2, 4, 8, 16, 32`. Each setting runs in a
fresh process because Rayon's global pool cannot be resized after creation.
Divan uses 7 samples of one three-file iteration. A forward sweep and a reverse
sweep are both run; the minimum median duration per setting is the capability
curve required by rule 16, while both raw medians and machine-busy fractions
remain visible.

### Commissioning and failure inputs

1. **Timer RED:** a second Divan arm performs the identical three decodes and
   then sleeps for a planted 200 ms. The timer is commissioned only if its
   median is at least 150 ms slower than the baseline. The planted duration
   comes from the OS sleep request, not from either measured result, satisfying
   rule 35.
2. **Not a no-op:** preflight must reproduce the independently documented A7C
   II allocation of 7168 x 5120 x 2 = **73,400,320 bytes per frame**, print a
   nonzero full-data checksum for each file, and report the active geometry.
   Every timed iteration derives a checksum from decoded sample values and
   passes both that value and the frame data through `black_box`. A benchmark
   that returns an empty/zero frame therefore fails before timing, while the
   compiler cannot discard the decoded value.
3. **Numerator check:** compressed and allocated totals must be printed before
   Divan starts. The allocated-output counter is the counter Divan displays;
   compressed-input rate is derived from the same median duration, never from
   a second timing.

**Bias directions (rule 18):** deliberate page-cache warming flatters
end-to-end first-run speed but is required to isolate decoder CPU throughput;
background CPU/memory contention makes decode look slower. Taking the faster
of alternating sweeps biases toward capability and must not be presented as a
typical shared-machine time. Compression-ratio variation changes
compressed-input rate without changing allocated-output work, which is why
both numerators are mandatory.

## 3. D15 / NVME protocol

The same 60 files are read with Windows `FILE_FLAG_NO_BUFFERING` into
4096-byte-aligned buffers, in 8 MiB aligned reads. Metadata reconnaissance
showed all 60 file lengths are multiples of 4096. The primary is eight
concurrent read workers (device queue populated); one worker is a secondary
queue-depth control. Every handle is read-only.

One run is ordered:

1. no-buffering, one worker;
2. no-buffering, eight workers (**cold-device primary**);
3. ordinary buffered read, eight workers, first pass;
4. ordinary buffered read, eight workers, immediate warm re-read;
5. no-buffering, eight workers after the files are warm;
6. no-buffering, one worker (reverse endpoint).

This both alternates the queue-depth sweep and provides the cache placebo.
The primary cold rate is cache-independent by API contract. It is accepted
only if the ordinary warm rate is at least **1.5x** the after-warm
no-buffering rate and if no-buffering does not jump to the warm rate after the
cache is populated. Otherwise cache control is **FAILED** and D15 remains
open. Read byte counts must equal 2,252,959,744 in every arm.

The NVMe timer is commissioned before payload timing: an empty timed closure
and a closure containing an independently planted 200 ms sleep are measured.
The latter must report 150–400 ms and at least 150 ms more than the former.

System busy fraction from `GetSystemTimes` is recorded for every arm. Any run
whose primary arm is at least 75% busy is labelled **contended** and the entire
sequence is rerun in an attempt to obtain a quieter arm; both are reported.
If the shared machine never falls below that threshold, rates are reported as
contention-depressed lower bounds, not quiet-box values.

**Bias directions (rule 18):** the Windows page cache can only fool an alleged
cold read fast; `FILE_FLAG_NO_BUFFERING` and the warm-vs-direct placebo target
that failure. Concurrent unrelated D: traffic, CPU contention, thermal
throttling, per-file open overhead, and queue-depth underfill can make the
device look slow. Eight workers can flatter the single-consumer path but
measures the proposal's explicitly prefetchable 60-file workload; the
one-worker control exposes that choice.

## 4. Reporting and scope

Both reports must name the exact hardware, OS build, power scheme, commit,
commands, selected files and exact byte counts; show the controls before the
headline; state MEASURED versus DERIVED; and cite the old M1 number only as
prior art. Captures are snapshotted by `(path, length, last-write time)` before
and after measurement, with `Get-ChildItem -Force`; any change invalidates the
run. Commits are path-scoped to the owned paths under AGENTS rule 42.
