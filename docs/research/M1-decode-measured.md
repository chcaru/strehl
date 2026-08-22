# M1 — Decode throughput and sensor constants (MEASURED)

Date: this session. Machine: Ryzen 9 9950X3D / 64 GB / RTX 5090, Windows 11.
Tool: `files/scratch/decode-bench` (Rust 1.98.0 MSVC, `--release`), `rawler` 0.7.2.
Corpora: `C:\dev\macro\test\109MSDCF` (22 ARW) and `D:\personal` (first 40 ARW,
never previously read by this session).

This file records only what was measured. Every number below came out of a run
whose output I read.

---

## 1. `rawler` decodes A7C II ARW correctly — hard dependency cleared

- **122 / 122 files decoded, 0 failures**, across two unrelated corpora and
  three disjoint file ranges.
- 100 of those were arbitrary real-world shots, not the curated test bracket.

**Status: VERIFIED.** The plan's single largest external dependency works. The
2–4 month "write our own ARW decoder" branch stays closed.

## 2. Sensor constants — independently confirmed

Reported directly by `rawler`, agreeing with the prior corpus:

| Constant | Value | Prior corpus | Verdict |
| --- | --- | --- | --- |
| Model | `ILCE-7CM2` | A7C II | confirmed |
| CFA | RGGB, 2x2 | RGGB | confirmed |
| White level | **15360** | "usable 15360, not 16383" | **confirmed** |
| Black level | **512** (all 4 channels) | 512 | confirmed |
| Active area | 7032 x 4688 = **32.97 MP** | 33 MP | confirmed |
| WB coeffs | [2.861, 1.0, 1.482, NaN] | — | new |

Note the 4th WB coefficient is `NaN` (no emerald channel). Any code consuming
`wb_coeffs` must not blindly iterate all four.

## 3. Decoded buffer is zero-padded — 11% of the allocation is not data

`rawler` returns a **7168 x 5120 = 36.70 MP** buffer but only fills the
7032 x 4688 active area. The right 136 columns and bottom 432 rows are
**exactly 0** (n = 3,544,448 probed, mean 0.000, sd 0.0000, min 0, max 0).

- Allocation: 73.4 MB/frame. Real data: 66.0 MB/frame.
- 60 frames: **4.40 GB allocated vs 3.96 GB useful.**

Consequences:
- The synthesis figure of 66 MB/frame was correct **for data**, but the
  allocation we must actually budget for is 73.4 MB unless we repack.
- Repacking to the active area costs a copy but saves 440 MB at N=60.
- **Never compute statistics over the full buffer.** Zeros are not black level;
  they are outside the sensor and will drag any mean/sd toward zero.

## 4. Decode throughput

Sequential means one file at a time; `rawler` is internally multithreaded, so
even "sequential" already uses many cores. "Cold" means the files had never been
read in this session.

| Mode | Cache | ms/frame | 60-frame | MB/s |
| --- | --- | --- | --- | --- |
| Sequential | cold | 78.2 | 4.69 s | 503 |
| Sequential | warm | 40.4–49.8 | 2.4–3.0 s | 764–914 |
| **Rayon across files** | **cold** | **29.7** | **1.78 s** | **1245** |
| Rayon across files | warm | 15.2 | 0.91 s | 2424 |

The cold-parallel row is the one that matters: it is a **true 60-frame stack of
never-before-read files**, which is exactly the real first-run workload.

**Decode for a 60-frame stack costs 1.78 s cold, 0.91 s warm.**

Two things this shows:

1. **Cold sequential decode is an I/O-serialisation artifact, not a cost.**
   Reading one file at a time yielded 503 MB/s; issuing reads concurrently
   yielded 1245 MB/s from the same cold storage — **2.5x** more. Any design that
   decodes frames one-at-a-time leaves half the disk on the table.
2. **Cross-file parallelism is where the win is, not intra-file.** `rawler`
   already saturates cores inside one file, yet parallel-across-files still gave
   2.4–4.6x. The gain is from overlapping each file's serial head and its I/O
   stall, so it survives even when the CPU is already busy.

## 5. Bearing on the C-vs-D budget dispute

Report D put decode at the top of the budget; report C put alignment at 5.0 s
and called it dominant.

**Decode is now pinned at 0.9–1.8 s for 60 frames.** Against a ~15 s whole-stack
target that is **6–12%** of budget. Decode is *not* the dominant stage, and the
earlier reading of these results (which used the 4.69 s cold-sequential number)
overstated it by 2.6x.

Alignment remains the open question and is now, by elimination, the most likely
place for the budget to actually go. **C's concern deserves the next
measurement; D's 0.10 s estimate is the one that needs defending.**

---

## What this does NOT show

- **The FPN / averaging-pillar question is still open, and cannot be answered
  from these files.** The plan was to use optically-masked sensor pixels as a
  free dark frame. `rawler` reports `blackareas` as **empty** for Sony and crops
  the masked border away, so no zero-light pixels survive decode. The padding is
  synthetic zeros, not masked pixels.
  **Unblocking action: 20 lens-cap frames at ISO 100 and at ISO 400.** That is a
  two-minute capture and it settles whether frame averaging reaches sigma/sqrt(N)
  or plateaus on a fixed-pattern floor — the one live threat to the central
  design pillar.
- Nothing here measures alignment, focus measure, or merge quality.
