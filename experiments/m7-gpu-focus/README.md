# m7-gpu-focus — pricing the GPU fusion prize

This experiment exists to answer one question, by measurement rather than argument:

> SYNTHESIS risk 10 — *"The GPU contribution format is being constrained by a CPU
> measurement."*

Fact 21 (196.8 ms/frame for ring-difference focus + fold) is **scalar Rust**. It is the
stated justification for fusing focus measurement into the merge kernel, which in turn is
the stated justification for forcing third-party focus measures to be WGSL that can be
spliced into that kernel. This crate ports the ring-difference measure to a `wgpu`
compute kernel, proves the port is numerically faithful, and then measures the *fused*
and *unfused* paths side by side. The difference between those two numbers **is** the
fusion prize. It is not argued here; it is measured.

The report is `docs/research/M7-gpu-focus-measured.md`.

## Files

| File | What it is |
| --- | --- |
| `src/cpu.rs` | A behavioural copy of the parts of `crates/strehl-core` this measurement needs — `PlaneGeometry`, `Noise`, `box_mean`, `FocusField`, `green_luma`, `Selection` — taken from commit `037d966`. Copied, not depended on, so that a concurrent edit to `crates/` cannot silently change the reference. Also holds `exact_focus_f64`, an independent f64 implementation that shares no code with either the CPU or the GPU path and acts as arithmetic truth. |
| `src/decode.rs` | `rawler` decode → a packed `u32` buffer containing **only** the 7032×4688 active area (project rule 7: the zero padding is not image data and is never measured). Both the CPU and the GPU path read this same buffer. |
| `src/gpu.rs` | Device setup, buffers, pipelines, the encoder-level timestamp harness, and `nvidia-smi` VRAM sampling. Builds four shader *modules* from one source by placeholder substitution: `m_a` (radii 1/3), `m_b` (radii 2/5), `m_f` (both, for the two-measure fused variant), `m_fast` (radii 1/3 with the raw fp32 divide, used only to price exactness). |
| `shaders/focus.wgsl` | The kernel. One workgroup of 32×8 threads produces a 32×8 plane tile from a 38×14 shared-memory tile, separable box sums, ring difference, `sigma` normalisation, then either an in-register merge (fused) or a store (unfused). |
| `src/main.rs` | The five subcommands below. |

## Run it in this order

Every command needs cargo on PATH:

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cd experiments\m7-gpu-focus
cargo build --release
```

```powershell
# 0. Self-tests. 18 assertions in 7 groups, no camera data needed.        (~25 s)
#    Group 1 is the load-bearing one: it verifies the claim that every partial
#    box sum in this kernel is exactly representable in f32, so accumulation
#    order cannot matter. Group 3 includes the diagnosis check that proves the
#    fp32 divide, not the summation, was the source of GPU/CPU disagreement.
.\target\release\m7-gpu-focus.exe selftest

# 1. Controls. Null, D2D, read, copy, and two H2D paths. Nothing below is
#    interpretable without these.                                         (~60 s)
.\target\release\m7-gpu-focus.exe controls "C:\dev\macro\test\109MSDCF" --limit 22

# 2. Verification against the CPU reference and against f64 truth, on real
#    frames, at the focus-field level and at the merge level.            (~150 s)
.\target\release\m7-gpu-focus.exe verify "C:\dev\macro\test\109MSDCF" --limit 22
.\target\release\m7-gpu-focus.exe verify "C:\dev\macro\test\119MSDCF" --limit 6

# 3. The headline. Five variants, the fusion prize, the CPU baseline, and a
#    bandwidth model built from the inline null and read controls.        (~4 min)
.\target\release\m7-gpu-focus.exe measure "C:\dev\macro\test\109MSDCF" --limit 22 --reps 30

# 4. Scale checks — the prize per frame must not depend on stack depth.
.\target\release\m7-gpu-focus.exe measure "C:\dev\macro\test\119MSDCF"    --limit 33  --reps 20
.\target\release\m7-gpu-focus.exe measure "C:\dev\macro\test\coffee-bean" --limit 105 --reps 20

# 5. CPU only, if you want the baseline without touching the GPU.
.\target\release\m7-gpu-focus.exe cpu "C:\dev\macro\test\109MSDCF" --limit 22
```

Captured output for each of these is in `results-*.txt` next to this file. Every number
in the report is traceable to one of them.

## The five variants, and why each exists

| | Variant | Dispatches / frame | What it isolates |
| --- | --- | --- | --- |
| A | fused | 1 | focus measured in registers, merged in the same kernel invocation. The proposed design. |
| B | unfused | 2 | focus written to memory, merge reads it back. **A plugin that emits a focus field.** |
| C | volume | 2 (N fields kept resident) | the whole focus volume materialised, merged afterwards. The most permissive plugin model. |
| D | fused2 | 1 | two different focus measures (radii 1/3 and 2/5) combined and merged in one kernel. |
| E | unfused2 | 3 | the same two measures as two independent plugin passes plus a merge. |

`B − A` is the fusion prize for one measure. `E − D` is the prize for two. `C − A` is the
prize against the most permissive plugin model there is.

## The controls, and what each one is for

- **Null** — one dispatch of the full 110×293 grid whose kernel returns immediately.
  Bounds dispatch overhead. A self-test asserts it writes nothing.
- **Read** — every word of all 22 frames read once, into 22 *distinct* buffers totalling
  1.351 GiB. Too large for the 5090's 96 MiB L2, so it is the honest DRAM bandwidth
  ceiling. **This is the reference the report uses.**
- **Copy** — read and write. Reported, then discarded as a reference: its single
  destination buffer fits in L2 and inflates the rate. Kept because saying so is the
  point.
- **D2D** — `copy_buffer_to_buffer`, the copy-engine path, for comparison with fact 10.
- **H2D (a) and (b)** — `queue.write_buffer` versus a mapped staging buffer. (b)
  discovers that the staging buffer is ReBAR device-local host-visible, so the host
  `memcpy` *is* the PCIe transfer.

## Things this code deliberately does not do

- It does not modify, or link against, anything under `crates/`. The CPU reference is a
  copy, so that a concurrent edit to `crates/strehl-core/src/focus.rs` cannot change this
  measurement's baseline without someone noticing the diff.
- It does not write anywhere except its own directory. The test stacks under
  `C:\dev\macro` are opened read-only.
- It does not measure the zero padding. `decode.rs` packs the active area only, so there
  is no padding in the buffer to accidentally measure.
- It does not claim a spill-free run on the strength of the `nvidia-smi` delta alone. The
  delta is reported, but the argument that nothing spilled is the achieved bandwidth:
  705–1429 GB/s is 11–23× PCIe 5.0 x16, and a spilled buffer cannot exceed PCIe.
