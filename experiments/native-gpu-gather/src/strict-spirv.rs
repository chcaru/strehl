//! Bounded compiler adapter for the embedded, owned gather shader only.
//! Naga has no NoContraction emission option. Keep its validated instructions
//! byte-for-byte and add only arithmetic-result decorations (SPIR-V section 3.20).
use std::{borrow::Cow, collections::{BTreeMap, BTreeSet}};
use naga::{back::spv, proc::{BoundsCheckPolicies, BoundsCheckPolicy}, valid::{Capabilities, ValidationFlags, Validator}};
use sha2::{Digest, Sha256};
use spirv::{Decoration, Op};

pub const ENTRY_POINTS: [&str; 3] = ["mhc", "gather", "quantize_vector"];
#[derive(Debug, serde::Serialize)]
pub struct CompilationReport {
    pub no_contraction: bool,
    pub max_storage_buffer_binding_size: u64,
    pub max_buffer_size: u64,
    pub original_sha256: String,
    pub decorated_sha256: String,
    pub submitted_sha256: String,
    pub arithmetic_results: usize,
    pub added_decorations: usize,
    pub float_operations: BTreeMap<String, usize>,
    pub entry_points: [&'static str; 3],
    pub group_zero_bindings: [u32; 6],
    pub bounds_policy: &'static str,
    pub validation: &'static str,
}

fn validate(module: &naga::Module) -> Result<naga::valid::ModuleInfo, String> {
    Validator::new(ValidationFlags::all(), Capabilities::empty()).validate(module)
        .map_err(|e| format!("owned shader validation: {e:?}"))
}
fn bytes(words: &[u32]) -> Vec<u8> { words.iter().flat_map(|w| w.to_le_bytes()).collect() }
fn hash(words: &[u32]) -> String { Sha256::digest(bytes(words)).iter().map(|b| format!("{b:02x}")).collect() }

// This scanner is an additional structural guard, not a replacement for SPIR-V
// Tools validation. Input is exclusively Naga output from the embedded WGSL.
fn instructions(words: &[u32]) -> Result<Vec<(usize, Op, &[u32])>, String> {
    if words.len() < 5 || words[0] != 0x07230203 || words[1] != 0x00010000
        || words[3] == 0 || words[4] != 0 {
        return Err("unexpected SPIR-V 1.0 header".into());
    }
    let mut out = Vec::new(); let mut i = 5;
    while i < words.len() {
        let n = (words[i] >> 16) as usize;
        if n == 0 || n > words.len() - i { return Err("bad SPIR-V instruction length".into()); }
        let op = Op::from_u32(words[i] & 65535).ok_or("unknown SPIR-V opcode")?;
        out.push((i, op, &words[i..i+n])); i += n;
    }
    Ok(out)
}

fn decorate(words: &[u32]) -> Result<(Vec<u32>, BTreeMap<String, usize>), String> {
    let insts = instructions(words)?;
    let insert = insts.iter().find(|(_, op, _)| op.is_type()).ok_or("no SPIR-V types")?.0;
    let mut float_types = BTreeSet::new(); let mut results = BTreeSet::new();
    let mut imports = BTreeSet::new(); let mut counts = BTreeMap::new();
    for &(at, op, w) in &insts {
        match op {
            Op::TypeFloat => {
                if w.len() != 3 || w[2] != 32 { return Err("only f32 image arithmetic admitted".into()); }
                float_types.insert(w[1]);
            }
            Op::TypeVector | Op::TypeMatrix if w.len() == 4 && float_types.contains(&w[2]) => { float_types.insert(w[1]); }
            Op::ExtInstImport => {
                if w.len() < 3 { return Err("bad extended instruction import".into()); }
                let name = bytes(&w[2..]);
                if name.split(|&c| c == 0).next() != Some(b"GLSL.std.450".as_slice()) {
                    return Err("unexpected extended instruction set".into());
                }
                imports.insert(w[1]);
            }
            Op::ExtInst => {
                if w.len() < 5 || !imports.contains(&w[3]) || w[4] == spirv::GlslStd450Op::Fma as u32 {
                    return Err("unrecognized or already fused extended arithmetic".into());
                }
            }
            Op::FmaKHR => return Err("already fused arithmetic".into()),
            Op::Decorate | Op::DecorateId => {
                if at >= insert || w.len() < 3 { return Err("misplaced decoration".into()); }
                if w[2] == Decoration::FPFastMathMode as u32 || w[2] == Decoration::NoContraction as u32 {
                    return Err("unexpected existing floating-point decoration".into());
                }
            }
            Op::MemberDecorate => {
                if at >= insert || w.len() < 4 || w[3] == Decoration::FPFastMathMode as u32
                    || w[3] == Decoration::NoContraction as u32 { return Err("unsupported member decoration".into()); }
            }
            Op::ExecutionMode | Op::ExecutionModeId if w.len() >= 3 && w[2] == spirv::ExecutionMode::FPFastMathDefault as u32 => {
                return Err("fast-math execution mode".into());
            }
            Op::FNegate | Op::FAdd | Op::FSub | Op::FMul | Op::FDiv | Op::FRem | Op::FMod
                | Op::VectorTimesScalar | Op::MatrixTimesScalar | Op::VectorTimesMatrix
                | Op::MatrixTimesVector | Op::MatrixTimesMatrix | Op::OuterProduct | Op::Dot => {
                if w.len() < 4 || !float_types.contains(&w[1]) || w[2] == 0 || w[2] >= words[3]
                    || !results.insert(w[2]) { return Err("bad or duplicate arithmetic result".into()); }
                *counts.entry(format!("{op:?}")).or_insert(0) += 1;
            }
            _ => {}
        }
    }
    if results.is_empty() || !counts.contains_key("FAdd") || !counts.contains_key("FMul") {
        return Err("no live multiply/add decoration targets".into());
    }
    let mut patched = Vec::with_capacity(words.len() + 3 * results.len());
    patched.extend_from_slice(&words[..insert]);
    for &id in &results { patched.extend_from_slice(&[(3 << 16) | Op::Decorate as u32, id, Decoration::NoContraction as u32]); }
    patched.extend_from_slice(&words[insert..]);
    // Check the emitted section, uniqueness and exact removal identity. No
    // instruction, operand, ID bound, layout, or kernel formula may be edited.
    let mut restored = patched[..5].to_vec(); let mut seen = BTreeSet::new();
    for (at, op, w) in instructions(&patched)? {
        if op == Op::Decorate && w.len() >= 3 && w[2] == Decoration::NoContraction as u32 {
            if w.len() != 3 || at < insert || at >= insert + 3 * results.len()
                || !results.contains(&w[1]) || !seen.insert(w[1]) { return Err("bad inserted NoContraction".into()); }
        } else { restored.extend_from_slice(w); }
    }
    if seen != results || restored != words { return Err("SPIR-V mutation exceeded decorations".into()); }
    Ok((patched, counts))
}

pub fn compile(strict: bool) -> Result<(Vec<u32>, CompilationReport), String> {
    let module = naga::front::wgsl::parse_str(include_str!("gather.wgsl"))
        .map_err(|e| format!("owned WGSL parse: {e:?}"))?;
    let info = validate(&module)?;
    if module.entry_points.len() != 3 || ENTRY_POINTS.iter().any(|name| !module.entry_points.iter().any(|ep|
        ep.name == *name && ep.stage == naga::ShaderStage::Compute && ep.workgroup_size == [64,1,1])) {
        return Err("owned shader entry points changed".into());
    }
    let mut options = spv::Options { lang_version: (1,0), flags: spv::WriterFlags::empty(),
        fake_missing_bindings: false,
        capabilities: Some([spv::Capability::Shader].into_iter().collect()),
        // Match wgpu Vulkan's checked-index policy, also checking buffers here
        // rather than depending on its private robustBufferAccess2 capability.
        bounds_check_policies: BoundsCheckPolicies { index: BoundsCheckPolicy::Restrict,
            buffer: BoundsCheckPolicy::Restrict, image_load: BoundsCheckPolicy::Restrict,
            binding_array: BoundsCheckPolicy::Restrict },
        ..Default::default() };
    let mut bindings = BTreeSet::new();
    for (_, global) in module.global_variables.iter() {
        let Some(binding) = global.binding else { continue; };
        if binding.group != 0 || binding.binding > 5 || !bindings.insert(binding.binding) {
            return Err("owned shader bindings changed".into());
        }
        let correct_space = match global.space {
            naga::AddressSpace::Uniform => binding.binding == 0,
            naga::AddressSpace::Storage { access } => binding.binding != 0
                && access.contains(naga::StorageAccess::STORE) == !matches!(binding.binding, 1 | 3),
            _ => false,
        };
        if !correct_space { return Err("owned shader binding access changed".into()); }
        options.binding_map.insert(binding, spv::BindingInfo { descriptor_set: 0,
            binding: binding.binding, binding_array_size: None });
    }
    if bindings != (0..6).collect() { return Err("owned shader requires exactly six bindings".into()); }
    let original = spv::write_vec(&module, &info, &options, None).map_err(|e| format!("SPIR-V emission: {e:?}"))?;
    let (patched, counts) = decorate(&original)?;
    // Independent frontend/IR validation, not spirv-val. Naga ignores the
    // NoContraction decoration on import, so never re-emit this parsed module.
    for words in [&original, &patched] {
        let parsed = naga::front::spv::parse_u8_slice(&bytes(words), &naga::front::spv::Options {
            adjust_coordinate_space: false, strict_capabilities: true, block_ctx_dump_prefix: None,
        }).map_err(|e| format!("generated SPIR-V parse: {e:?}"))?;
        validate(&parsed)?;
    }
    let total = counts.values().sum();
    let report = CompilationReport { no_contraction: strict,
        max_storage_buffer_binding_size: 0, max_buffer_size: 0, original_sha256: hash(&original),
        decorated_sha256: hash(&patched), submitted_sha256: hash(if strict { &patched } else { &original }),
        arithmetic_results: total, added_decorations: if strict { total } else { 0 }, float_operations: counts,
        entry_points: ENTRY_POINTS, group_zero_bindings: [0,1,2,3,4,5],
        bounds_policy: "Restrict indices/buffers/images/binding-arrays; integer division checks and loop bounds enabled",
        validation: "embedded WGSL+IR; Naga SPIR-V parse+IR; structural decoration/removal identity; NOT spirv-val" };
    Ok((if strict { patched } else { original }, report))
}

pub fn module(device: &wgpu::Device, words: &[u32]) -> wgpu::ShaderModule {
    let entry_points = ENTRY_POINTS.iter().map(|name| wgpu::PassthroughShaderEntryPoint {
        name: Cow::Borrowed(*name), workgroup_size: (64,1,1),
    }).collect::<Vec<_>>();
    // SAFETY: caller requires Vulkan and PASSTHROUGH_SHADERS. These words come
    // only from compile() above: the embedded validated module, explicit bounded
    // accesses, fixed binding layout and independently checked annotation-only
    // mutation. There is no external/unvalidated shader input. Passthrough is
    // necessary because the ordinary SPIR-V frontend discards NoContraction.
    unsafe { device.create_shader_module_passthrough(wgpu::ShaderModuleDescriptorPassthrough {
        label: Some("owned-mhc-catmull-spirv"), spirv: Some(Cow::Borrowed(words)),
        entry_points: Cow::Owned(entry_points), ..Default::default()
    }) }
}
