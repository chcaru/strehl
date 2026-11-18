# A7CR stacking performance, round 2: evidence and prototypes

Measurements and prototypes behind
[the round-2 performance plan](../../docs/proposals/2026-11-a7cr-stacking-performance-plan-2.md),
taken on 2026-11-18 on the owner's desktop (Ryzen 9 9950X3D, 64 GB, RTX 5090; captures
on a Samsung 980 PRO, a WD SN8100 as the second drive). The plan's sections 3 and 4 state
the results; this folder is what they rest on. Nothing here is product code, and nothing
here changed the product tree.

Input for every run: the scarab capture, 784 `frame-NNNNNN.ARW.straw` archives, 196
four-shot planes, 48 GB (private corpus, read-only). Product binary: round 1's final
build of the working tree (`cbca976b7e96-dirty`, `--features gpu`), which is not on
`main` at the time of writing.

## Files

| Path | What it is |
| --- | --- |
| `evidence/runs.txt` | One line per traced render: command, environment, wall, CPU, bytes read, peak memory, exit code, output SHA-256 |
| `evidence/later-render-product-binary.txt` | Stage tables of three later renders with the product binary |
| `evidence/later-render-t3-tp.txt` | The instrumented build's stage table, every timer, per-decoder timers, CPU per thread role |
| `evidence/first-render-t6-first.txt` | Stage table of a first render (empty cache: alignment and group checks included) |
| `evidence/io-bench.txt` | Read throughput on the capture drive by method, threads and cache state |
| `evidence/dec-bench.txt`, `dec-bench2.txt` | Decode throughput: product loop against the row-buffered prototype (the second file has the final predictor) |
| `evidence/pipe-bench.txt`, `pipe-bench-c.txt` | Readers feeding decoders, on the capture drive and on the faster drive |
| `evidence/proto-bench.txt` | Predictor and alignment-search prototypes (bit-identity, then time); the group check on one thread |
| `evidence/fmt-bench.txt` | Bits per sample of candidate codes for a second archive format |
| `anchors.md` | Where each stage's code is (functions, approximate lines on 2026-11-18) |
| `trace.py`, `stages.py`, `threads.py` | Run a command under a 100 ms timeline (process CPU, bytes read, drive reads, memory, device use, per-thread CPU) and cut it at the render's banner lines |
| `tp.py`, `tp-threads.py` | Summarise an instrumented build's timers |
| `io-bench.py` | The storage measurement (Windows; the drive counter name `PhysicalDrive1` is this host's capture drive) |
| `bench2/` | Prototypes: `pred`, `predparts` (row-buffered predictor), `dec` (decode throughput), `pipe` (readers to decoders), `ncc` (alignment search as offset lanes), `fmt` (code statistics) |
| `timers/` | The instrumented build as exact-text patches for a scratch copy of the tree |

## Running them again

The tools write to the ignored folder `outputs/a7cr-perf-2/` (or `STREHL_PERF_OUT`),
never beside the scripts. Renders one at a time, on an idle host.

```powershell
# A traced render (needs psutil and pywin32; nvidia-smi for the device columns)
python experiments/a7cr-stacking-performance-2026-11-18/trace.py --threads --exe <strehl.exe> --tag t --env STREHL_PIXEL_SHIFT=remosaic --env STREHL_GPU_FOLD=on --out o.tif -- stack <capture> --demosaic --out o.tif
python experiments/a7cr-stacking-performance-2026-11-18/stages.py t

# Prototypes
cargo build --release --manifest-path experiments/a7cr-stacking-performance-2026-11-18/bench2/Cargo.toml
bench2 pred <capture>            # predictor: identical samples, then time
bench2 dec <capture> 64 16 rh cores
bench2 pipe <capture> 320 4 16 huc cores
bench2 ncc
bench2 fmt <capture>
```

The instrumented build: copy `crates/`, `third-party/`, `Cargo.toml`, `Cargo.lock` and
`rust-toolchain.toml` to a scratch folder outside the tree, link `experiments/`, `docs/`
and `scripts/` into it, put `timers/trace-points.rs` at its root, set `STREHL_SCRATCH` to
it and run the three `patch-tp-*.py` scripts; build with a separate target directory and
run with `STREHL_TP_OUT=<file>`. The patches assert every match, so they fail loudly once
the code has moved. If the links are directory junctions, remove them with `rmdir`, never
with a recursive delete.

## Limits

Single runs on one host and one stack. The instrumented build's output pixels were not
compared with the product's. Figures the plan marks DERIVED or ARGUED are not in this
folder; only what it marks MEASURED is.
