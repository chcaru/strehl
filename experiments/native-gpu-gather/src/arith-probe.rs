//! Exactness probe for the arithmetic a GPU-resident fold would need beyond
//! the gather's multiply/add: division and square root, in f32 directly and
//! through f64. Each result is compared bit for bit with the CPU.
//!
//! Why: the pyramid fold divides (pooled evidence, effective energy, the
//! selection ratio, the ensemble's z) and its variance model takes a square
//! root. Vulkan only requires 2.5 ULP for `OpFDiv` and leaves `Sqrt`
//! approximate, so whether this device reproduces the CPU is an empirical
//! question per device and driver, answered here rather than assumed.
//!
//! The shader goes through the same NoContraction decoration and passthrough
//! route as the gather, extended to admit f64.
use std::borrow::Cow;
use std::collections::BTreeSet;
use naga::{back::spv, valid::{Capabilities, ValidationFlags, Validator}};
use spirv::{Decoration, Op};
use wgpu::util::DeviceExt;

const SHADER: &str = r#"
@group(0) @binding(0) var<storage, read> a: array<f32>;
@group(0) @binding(1) var<storage, read> b: array<f32>;
@group(0) @binding(2) var<storage, read_write> out: array<u32>;
@group(0) @binding(3) var<storage, read_write> outd: array<f64>;
@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    let i = id.x + id.y * (65535u * 64u);
    if (i >= arrayLength(&a)) { return; }
    let x = a[i]; let y = b[i];
    let xd = f64(x); let yd = f64(y);
    out[8u*i+0u] = bitcast<u32>(x / y);
    out[8u*i+1u] = bitcast<u32>(sqrt(abs(x)));
    out[8u*i+2u] = bitcast<u32>(f32(xd / yd));
    out[8u*i+3u] = bitcast<u32>(f32(sqrt(abs(xd))));
    out[8u*i+4u] = bitcast<u32>(x * y + x);
    outd[i] = xd / yd;
    out[8u*i+7u] = bitcast<u32>(max(x, y) - min(x, y));
}
"#;

fn decorate(words: &[u32]) -> Result<Vec<u32>, String> {
    let mut i = 5; let mut insts = Vec::new();
    while i < words.len() {
        let n = (words[i] >> 16) as usize;
        if n == 0 || n > words.len() - i { return Err("bad SPIR-V".into()); }
        insts.push((i, Op::from_u32(words[i] & 65535).ok_or("opcode")?, &words[i..i + n]));
        i += n;
    }
    let insert = insts.iter().find(|(_, op, _)| op.is_type()).ok_or("no types")?.0;
    let mut floats = BTreeSet::new(); let mut results = BTreeSet::new();
    for &(_, op, w) in &insts {
        match op {
            Op::TypeFloat => { floats.insert(w[1]); }
            Op::TypeVector if floats.contains(&w[2]) => { floats.insert(w[1]); }
            Op::FNegate | Op::FAdd | Op::FSub | Op::FMul | Op::FDiv | Op::FRem | Op::FMod
                if floats.contains(&w[1]) => { results.insert(w[2]); }
            _ => {}
        }
    }
    let mut out = words[..insert].to_vec();
    for id in results { out.extend_from_slice(&[(3 << 16) | Op::Decorate as u32, id, Decoration::NoContraction as u32]); }
    out.extend_from_slice(&words[insert..]);
    Ok(out)
}

#[derive(Debug, Default, Clone)]
pub struct Report {
    pub samples: usize,
    /// Mismatches against the CPU's correctly rounded f32 `x / y`.
    pub f32_div: usize,
    pub f32_sqrt: usize,
    /// `f32(f64(x) / f64(y))`, against the CPU's f32 `x / y`.
    pub via_f64_div: usize,
    pub via_f64_sqrt: usize,
    /// `x * y + x` with NoContraction, against unfused CPU arithmetic.
    pub mul_add: usize,
    /// The f64 quotient itself against the CPU's f64 division.
    pub f64_div: usize,
    pub minmax: usize,
    pub first_f32_div: Option<(f32, f32, u32, u32)>,
}

/// Probe `samples` operand pairs: half drawn over the magnitudes the fold
/// handles (1e-3..1e9, positive), half over random finite normal bit patterns.
pub fn run(samples: usize, seed: u64) -> Result<Report, String> {
    let module = naga::front::wgsl::parse_str(SHADER).map_err(|e| format!("{e:?}"))?;
    let info = Validator::new(ValidationFlags::all(), Capabilities::FLOAT64).validate(&module)
        .map_err(|e| format!("{e:?}"))?;
    let options = spv::Options { lang_version: (1, 0),
        capabilities: Some([spv::Capability::Shader, spv::Capability::Float64].into_iter().collect()),
        ..Default::default() };
    let words = decorate(&spv::write_vec(&module, &info, &options, None).map_err(|e| format!("{e:?}"))?)?;

    let mut descriptor = wgpu::InstanceDescriptor::new_without_display_handle();
    descriptor.backends = wgpu::Backends::VULKAN;
    let instance = wgpu::Instance::new(descriptor);
    let adapter = pollster::block_on(instance.request_adapter(&wgpu::RequestAdapterOptions {
        power_preference: wgpu::PowerPreference::HighPerformance,
        force_fallback_adapter: false, compatible_surface: None, apply_limit_buckets: false,
    })).map_err(|e| e.to_string())?;
    let (device, queue) = pollster::block_on(adapter.request_device(&wgpu::DeviceDescriptor {
        label: Some("arith-probe"),
        required_features: wgpu::Features::PASSTHROUGH_SHADERS | wgpu::Features::SHADER_F64,
        required_limits: adapter.limits(), experimental_features: wgpu::ExperimentalFeatures::disabled(),
        memory_hints: wgpu::MemoryHints::Performance, trace: wgpu::Trace::Off,
    })).map_err(|e| e.to_string())?;
    let shader = unsafe { device.create_shader_module_passthrough(wgpu::ShaderModuleDescriptorPassthrough {
        label: Some("arith-probe"), spirv: Some(Cow::Borrowed(&words)),
        entry_points: Cow::Owned(vec![wgpu::PassthroughShaderEntryPoint { name: Cow::Borrowed("main"), workgroup_size: (64, 1, 1) }]),
        ..Default::default() }) };
    let entries: Vec<_> = (0..4).map(|binding| wgpu::BindGroupLayoutEntry {
        binding, visibility: wgpu::ShaderStages::COMPUTE,
        ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: binding < 2 },
            has_dynamic_offset: false, min_binding_size: None }, count: None }).collect();
    let layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor { label: None, entries: &entries });
    let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
        label: None, bind_group_layouts: &[Some(&layout)], immediate_size: 0 });
    let pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
        label: None, layout: Some(&pipeline_layout), module: &shader, entry_point: Some("main"),
        compilation_options: Default::default(), cache: None });

    let mut s = seed | 1;
    let mut next = move || { s ^= s << 13; s ^= s >> 7; s ^= s << 17; s };
    let mut operand = |k: usize| -> f32 {
        loop {
            let r = next();
            let v = if k % 2 == 0 {
                10f64.powf(-3.0 + 12.0 * ((r >> 11) as f64 / (1u64 << 53) as f64)) as f32
            } else {
                f32::from_bits((r >> 32) as u32)
            };
            if v.is_normal() && v.abs() < 1e30 && v.abs() > 1e-30 { return v; }
        }
    };
    let a: Vec<f32> = (0..samples).map(&mut operand).collect();
    let b: Vec<f32> = (0..samples).map(&mut operand).collect();
    let buf = |data: &[f32]| device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: None, contents: bytemuck::cast_slice(data), usage: wgpu::BufferUsages::STORAGE });
    let (ba, bb) = (buf(&a), buf(&b));
    let size = (samples * 8 * 4) as u64;
    let out = device.create_buffer(&wgpu::BufferDescriptor { label: None, size,
        usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC, mapped_at_creation: false });
    let dsize = (samples * 8) as u64;
    let outd = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: dsize,
        usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC, mapped_at_creation: false });
    let readd = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: dsize,
        usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
    let read = device.create_buffer(&wgpu::BufferDescriptor { label: None, size,
        usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
    let bind = device.create_bind_group(&wgpu::BindGroupDescriptor { label: None,
        layout: &layout,
        entries: &[wgpu::BindGroupEntry { binding: 0, resource: ba.as_entire_binding() },
                   wgpu::BindGroupEntry { binding: 1, resource: bb.as_entire_binding() },
                   wgpu::BindGroupEntry { binding: 2, resource: out.as_entire_binding() },
                   wgpu::BindGroupEntry { binding: 3, resource: outd.as_entire_binding() }] });
    let mut enc = device.create_command_encoder(&Default::default());
    {
        let mut pass = enc.begin_compute_pass(&Default::default());
        pass.set_pipeline(&pipeline);
        pass.set_bind_group(0, &bind, &[]);
        let groups = samples.div_ceil(64) as u32;
        pass.dispatch_workgroups(groups.min(65535), groups.div_ceil(65535), 1);
    }
    enc.copy_buffer_to_buffer(&out, 0, &read, 0, size);
    enc.copy_buffer_to_buffer(&outd, 0, &readd, 0, dsize);
    queue.submit([enc.finish()]);
    read.slice(..).map_async(wgpu::MapMode::Read, |_| {});
    readd.slice(..).map_async(wgpu::MapMode::Read, |_| {});
    device.poll(wgpu::PollType::wait_indefinitely()).map_err(|e| format!("{e:?}"))?;
    let view = read.slice(..).get_mapped_range().map_err(|e| format!("{e:?}"))?;
    let got: Vec<u32> = bytemuck::cast_slice::<u8, u32>(&view[..]).to_vec();
    drop(view);
    let viewd = readd.slice(..).get_mapped_range().map_err(|e| format!("{e:?}"))?;
    let gotd: Vec<u64> = bytemuck::cast_slice::<u8, u64>(&viewd[..]).to_vec();
    drop(viewd);

    let mut r = Report { samples, ..Default::default() };
    for i in 0..samples {
        let (x, y) = (a[i], b[i]);
        let g = &got[8 * i..8 * i + 8];
        let div = (x / y).to_bits();
        if g[0] != div { r.f32_div += 1; if r.first_f32_div.is_none() { r.first_f32_div = Some((x, y, g[0], div)); } }
        if g[1] != x.abs().sqrt().to_bits() { r.f32_sqrt += 1; }
        if g[2] != div { r.via_f64_div += 1; }
        if g[3] != x.abs().sqrt().to_bits() { r.via_f64_sqrt += 1; }
        if g[4] != (x * y + x).to_bits() { r.mul_add += 1; }
        let q = (x as f64 / y as f64).to_bits();
        if gotd[i] != q { r.f64_div += 1; }
        if g[7] != (x.max(y) - x.min(y)).to_bits() { r.minmax += 1; }
    }
    Ok(r)
}

/// Exhaustive census on the CPU: is the platform's f32 `ln` / `exp` correctly
/// rounded? Compares against the f64 function rounded to f32, over every f32 in
/// the range given. A mismatch is either a misrounded f32 result or (rarely) a
/// double-rounding artefact of the reference; both are counted and the first
/// few returned for inspection.
pub fn libm_census(exp: bool, lo: f32, hi: f32) -> (u64, u64, Vec<(f32, u32, u32)>) {
    use rayon::prelude::*;
    let (a, b) = (lo.to_bits(), hi.to_bits());
    let bits: Vec<u32> = if lo >= 0.0 { vec![a, b] } else { vec![0x8000_0000, a, 0, b] };
    let ranges: Vec<(u32, u32)> = if lo >= 0.0 { vec![(a, b)] } else { vec![(bits[0], bits[1]), (0, b)] };
    let mut tested = 0u64; let mut bad = 0u64; let mut first = Vec::new();
    for (s, e) in ranges {
        let (t, m, f) = (s as usize..e as usize + 1).into_par_iter().with_min_len(1 << 16).map(|u| u as u32).map(|u| {
            let x = f32::from_bits(u);
            let (got, want) = if exp { (x.exp(), (x as f64).exp() as f32) } else { (x.ln(), (x as f64).ln() as f32) };
            let miss = got.to_bits() != want.to_bits();
            (1u64, miss as u64, if miss { vec![(x, got.to_bits(), want.to_bits())] } else { Vec::new() })
        }).reduce(|| (0, 0, Vec::new()), |mut l, r| { l.0 += r.0; l.1 += r.1; if l.2.len() < 8 { l.2.extend(r.2.into_iter().take(8)); } l });
        tested += t; bad += m; if first.len() < 8 { first.extend(f.into_iter().take(8)); }
    }
    (tested, bad, first)
}