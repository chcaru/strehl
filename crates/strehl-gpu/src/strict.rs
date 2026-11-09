//! WGSL -> SPIR-V with every floating-point arithmetic result decorated
//! `NoContraction`, so the driver may not fuse a multiply and an add. Naga has
//! no option to emit it and its SPIR-V frontend discards it, so the words are
//! patched after emission and submitted through passthrough.
//!
//! Adapted from `experiments/native-gpu-gather/src/strict-spirv.rs`, extended
//! to admit f64 (the fold divides and takes logarithms through f64).
use std::collections::BTreeSet;

use naga::back::spv;
use naga::valid::{Capabilities, ValidationFlags, Validator};
use spirv::{Decoration, Op};

/// One instruction: word offset, opcode and its words.
type Inst<'a> = (usize, Op, &'a [u32]);

fn instructions(words: &[u32]) -> Result<Vec<Inst<'_>>, String> {
    if words.len() < 5 || words[0] != 0x0723_0203 {
        return Err("unexpected SPIR-V header".into());
    }
    let mut out = Vec::new();
    let mut i = 5;
    while i < words.len() {
        let n = (words[i] >> 16) as usize;
        if n == 0 || n > words.len() - i {
            return Err("bad SPIR-V instruction length".into());
        }
        let op = Op::from_u32(words[i] & 0xffff).ok_or("unknown SPIR-V opcode")?;
        out.push((i, op, &words[i..i + n]));
        i += n;
    }
    Ok(out)
}

/// Decorate every float arithmetic result `NoContraction`. Refuses a module
/// that already carries fused or fast-math arithmetic.
fn decorate(words: &[u32]) -> Result<(Vec<u32>, usize), String> {
    let insts = instructions(words)?;
    let insert = insts
        .iter()
        .find(|(_, op, _)| op.is_type())
        .ok_or("no SPIR-V types")?
        .0;
    let mut floats = BTreeSet::new();
    let mut results = BTreeSet::new();
    for &(_, op, w) in &insts {
        match op {
            Op::TypeFloat => {
                floats.insert(w[1]);
            }
            Op::TypeVector | Op::TypeMatrix if w.len() == 4 && floats.contains(&w[2]) => {
                floats.insert(w[1]);
            }
            Op::FmaKHR => return Err("already fused arithmetic".into()),
            Op::ExtInst if w.len() >= 5 && w[4] == spirv::GlslStd450Op::Fma as u32 => {
                return Err("already fused arithmetic".into());
            }
            Op::Decorate if w.len() >= 3 && w[2] == Decoration::FPFastMathMode as u32 => {
                return Err("fast-math decoration".into());
            }
            Op::FNegate
            | Op::FAdd
            | Op::FSub
            | Op::FMul
            | Op::FDiv
            | Op::FRem
            | Op::FMod
            | Op::VectorTimesScalar
            | Op::Dot
                if w.len() >= 4 && floats.contains(&w[1]) =>
            {
                if results.contains(&w[2]) {
                    return Err("duplicate arithmetic result".into());
                }
                results.insert(w[2]);
            }
            _ => {}
        }
    }
    if results.is_empty() {
        return Err("no float arithmetic to decorate".into());
    }
    // Subnormals must survive: the CPU keeps them, and the fold's soft-power
    // numerator is routinely subnormal where every frame's weight sits at the
    // exp(-80) clamp. A device that flushes them turns such a coefficient into
    // zero (MEASURED on bug-7 before this: 3.5% of samples, up to 6213 DN).
    // So every entry point gets DenormPreserve for f32 and f64
    // (SPV_KHR_float_controls). wgpu cannot query whether a device honours
    // it, so the equivalence test, which fails on a flushing device, is the
    // check (`tests/fold.rs`).
    let entries: Vec<u32> = insts
        .iter()
        .filter(|(_, op, _)| *op == Op::EntryPoint)
        .map(|(_, _, w)| w[2])
        .collect();
    let last_capability = insts
        .iter()
        .filter(|(_, op, _)| *op == Op::Capability)
        .map(|(at, _, w)| at + w.len())
        .max()
        .ok_or("no capabilities")?;
    let last_mode = insts
        .iter()
        .filter(|(_, op, _)| matches!(op, Op::ExecutionMode | Op::ExecutionModeId | Op::EntryPoint))
        .map(|(at, _, w)| at + w.len())
        .max()
        .ok_or("no entry points")?;
    let mut extension = vec![0u32];
    let name = b"SPV_KHR_float_controls\0";
    for chunk in name.chunks(4) {
        let mut word = [0u8; 4];
        word[..chunk.len()].copy_from_slice(chunk);
        extension.push(u32::from_le_bytes(word));
    }
    extension[0] = ((extension.len() as u32) << 16) | Op::Extension as u32;

    let mut out = Vec::with_capacity(words.len() + 3 * results.len() + 64);
    out.extend_from_slice(&words[..last_capability]);
    out.extend_from_slice(&[
        (2 << 16) | Op::Capability as u32,
        spirv::Capability::DenormPreserve as u32,
    ]);
    out.extend_from_slice(&extension);
    out.extend_from_slice(&words[last_capability..last_mode]);
    for &entry in &entries {
        for width in [32u32, 64] {
            out.extend_from_slice(&[
                (4 << 16) | Op::ExecutionMode as u32,
                entry,
                spirv::ExecutionMode::DenormPreserve as u32,
                width,
            ]);
        }
    }
    out.extend_from_slice(&words[last_mode..insert]);
    for &id in &results {
        out.extend_from_slice(&[
            (3 << 16) | Op::Decorate as u32,
            id,
            Decoration::NoContraction as u32,
        ]);
    }
    out.extend_from_slice(&words[insert..]);
    Ok((out, results.len()))
}

/// Compile `source` to decorated SPIR-V; returns the words and the number of
/// decorated arithmetic results.
pub fn compile(source: &str) -> Result<(Vec<u32>, usize), String> {
    let module = naga::front::wgsl::parse_str(source).map_err(|e| e.emit_to_string(source))?;
    let info = Validator::new(ValidationFlags::all(), Capabilities::FLOAT64)
        .validate(&module)
        .map_err(|e| format!("shader validation: {e:?}"))?;
    let options = spv::Options {
        lang_version: (1, 0),
        capabilities: Some(
            [spv::Capability::Shader, spv::Capability::Float64]
                .into_iter()
                .collect(),
        ),
        ..Default::default()
    };
    let words = spv::write_vec(&module, &info, &options, None)
        .map_err(|e| format!("SPIR-V emission: {e:?}"))?;
    decorate(&words)
}

/// Entry points of `fold.wgsl`, all `@workgroup_size(256)`.
pub const ENTRY_POINTS: &[&str] = &[
    "fill",
    "luma",
    "hull",
    "reduce_h",
    "reduce_v",
    "expand_h",
    "expand_sub_v",
    "smooth_h",
    "smooth_v",
    "level",
    "accum",
    "mhc",
    "gather",
    "extract",
    "variance",
    "sum64",
    "sum64_finish",
    "demean",
    "noise",
    "rowsq",
    "pack",
];
