//! Fixed owned GLSL coordinate kernel. This does not alter the f32 image shader.
//! Naga cannot import float-control execution modes. Original IR and original
//! SPIR-V are validated; the final additive patch has structural checks only.
use std::{borrow::Cow, collections::{BTreeMap, BTreeSet}};
use ash::vk;
use naga::{back::spv, proc::{BoundsCheckPolicies, BoundsCheckPolicy}, valid::{Capabilities, ValidationFlags, Validator}};
use sha2::{Digest, Sha256};
use spirv::{Capability, Decoration, ExecutionMode, Op};
use wgpu::util::DeviceExt;
use crate::{Params, SamplePlan};
use strehl_core::align::Similarity;

#[derive(Debug, serde::Serialize)]
pub struct CoordinateReport {
    pub hardware: Hardware,
    pub original_sha256: String,
    pub submitted_sha256: String,
    pub arithmetic_results: usize,
    pub added_capabilities: [&'static str; 2],
    pub execution_modes: [&'static str; 3],
    pub coefficient_guard: &'static str,
    pub entry_point: &'static str,
    pub bindings: [u32; 3],
    pub validation: &'static str,
}
#[derive(Debug, serde::Serialize)]
pub struct Hardware {
    pub vulkan_api: u32,
    pub shader_f64: bool,
    pub signed_zero_inf_nan_preserve_f64: bool,
    pub denorm_preserve_f64: bool,
    pub rounding_rte_f32: bool,
    pub rounding_rte_f64: bool,
    pub denorm_independence: i32,
    pub rounding_independence: i32,
}
/// Exact 2^-900 threshold; all twelve precomposed pull components are checked.
pub const MIN_DEVICE_COEFFICIENT: f64 = f64::from_bits((1023u64 - 900) << 52);
pub const COEFFICIENT_GUARD: &str = "every finite nonzero pull coefficient abs>=2^-900; unsafe actual frames use Parallel256; direct descriptor helper refuses";
pub fn coefficients_safe(pulls: [Similarity;3]) -> bool {
    pulls.iter().all(|t| [t.a.re,t.a.im,t.b.re,t.b.im].into_iter()
        .all(|c| c == 0.0 || !c.is_finite() || c.abs() >= MIN_DEVICE_COEFFICIENT))
}
// The accepted finite coefficients are integer multiples of 2^-952. Centred
// coordinates are exact half-integers, so products and every finite subsequent
// sum/difference are multiples of 2^-953. RTE preserves this lattice; no finite
// nonzero intermediate is subnormal. Overflow/nonfinite paths retain SINF64.
// This guard must precede every device coordinate upload, including test paths.
pub fn hardware(adapter: &wgpu::Adapter) -> Result<Hardware, String> {
    if adapter.get_info().backend != wgpu::Backend::Vulkan ||
        !adapter.features().contains(wgpu::Features::SHADER_F64 | wgpu::Features::PASSTHROUGH_SHADERS) {
        return Err("device coordinates require Vulkan + SHADER_F64 + PASSTHROUGH_SHADERS".into());
    }
    // SAFETY: the guard retains wgpu's adapter. Only immutable Vulkan physical
    // device properties are queried; no HAL resource is changed or destroyed.
    let hal = unsafe { adapter.as_hal::<wgpu::hal::api::Vulkan>() }.ok_or("missing Vulkan adapter")?;
    if hal.shared_instance().instance_api_version() < vk::API_VERSION_1_2 {
        return Err("device coordinates require Vulkan 1.2 float controls".into());
    }
    let mut floats = vk::PhysicalDeviceFloatControlsProperties::default();
    let api = {
        let mut props = vk::PhysicalDeviceProperties2::default().push_next(&mut floats);
        unsafe { hal.shared_instance().raw_instance().get_physical_device_properties2(hal.raw_physical_device(), &mut props); }
        props.properties.api_version
    };
    let result = Hardware { vulkan_api: api, shader_f64: true,
        signed_zero_inf_nan_preserve_f64: floats.shader_signed_zero_inf_nan_preserve_float64 != 0,
        denorm_preserve_f64: floats.shader_denorm_preserve_float64 != 0,
        rounding_rte_f32: floats.shader_rounding_mode_rte_float32 != 0,
        rounding_rte_f64: floats.shader_rounding_mode_rte_float64 != 0,
        denorm_independence: floats.denorm_behavior_independence.as_raw(),
        rounding_independence: floats.rounding_mode_independence.as_raw() };
    if api < vk::API_VERSION_1_2 || !result.signed_zero_inf_nan_preserve_f64
        || !result.rounding_rte_f32 || !result.rounding_rte_f64 {
        return Err(format!("required device coordinate float controls unsupported: {result:?}"));
    }
    // No denorm mode is requested at either width: the per-frame coefficient
    // guard excludes subnormal f64 inputs/intermediates. The accepted fraction
    // cast is zero or >=2^-52, normal f32. Preserve SINF64; RTE32/64 agree.
    // Hardware denorm support remains reported even when it is absent.
    Ok(result)
}
fn bytes(words: &[u32]) -> Vec<u8> { words.iter().flat_map(|w|w.to_le_bytes()).collect() }
fn hash(words: &[u32]) -> String { Sha256::digest(bytes(words)).iter().map(|b|format!("{b:02x}")).collect() }
fn validate(module: &naga::Module) -> Result<naga::valid::ModuleInfo,String> {
    Validator::new(ValidationFlags::all(),Capabilities::FLOAT64).validate(module).map_err(|e|format!("coordinate IR: {e:?}"))
}
fn instructions(words: &[u32]) -> Result<Vec<(usize,Op,&[u32])>,String> {
    if words.len()<5 || words[0]!=0x07230203 || words[1]!=0x00010000 || words[3]==0 || words[4]!=0 {
        return Err("unexpected coordinate SPIR-V 1.0 header".into());
    }
    let mut out=Vec::new(); let mut at=5;
    while at<words.len() {
        let len=(words[at]>>16) as usize;
        if len==0 || len>words.len()-at {return Err("invalid coordinate instruction length".into());}
        let op=Op::from_u32(words[at]&65535).ok_or("unknown coordinate opcode")?;
        out.push((at,op,&words[at..at+len]));at+=len;
    }
    Ok(out)
}
fn patch(words: &[u32]) -> Result<(Vec<u32>,usize),String> {
    let insts=instructions(words)?;
    let type_at=insts.iter().find(|(_,op,_)|op.is_type()).ok_or("coordinate types absent")?.0;
    let cap_at=insts.iter().find(|(_,op,_)|*op!=Op::Capability).ok_or("coordinate capability section absent")?.0;
    let modes_end=insts.iter().filter(|(_,op,_)|*op==Op::ExecutionMode).map(|(at,_,w)|at+w.len()).max().ok_or("coordinate execution modes absent")?;
    let mut entry=None; let mut types=BTreeSet::new(); let mut results=BTreeSet::new(); let mut imports=BTreeSet::new();
    let mut saw64=false;
    for &(at,op,w) in &insts {
        match op {
            Op::Capability if w.len()!=2 || ![Capability::Shader as u32,Capability::Float64 as u32].contains(&w[1]) => return Err("unexpected coordinate capability".into()),
            Op::Extension => return Err("unexpected existing coordinate extension".into()),
            Op::EntryPoint => {
                if w.len()<4 || w[1]!=spirv::ExecutionModel::GLCompute as u32 || entry.replace(w[2]).is_some() {return Err("coordinate entry changed".into());}
            }
            Op::ExecutionMode => if w.len()!=6 || w[2]!=ExecutionMode::LocalSize as u32 || w[3..]!=[64,1,1] {return Err("coordinate local size changed".into());},
            Op::ExecutionModeId => return Err("unexpected coordinate mode ID".into()),
            Op::TypeFloat => {
                if w.len()!=3 || ![32,64].contains(&w[2]) {return Err("coordinate float width changed".into());}
                saw64 |= w[2]==64; types.insert(w[1]);
            }
            Op::TypeVector | Op::TypeMatrix if w.len()==4 && types.contains(&w[2]) => {types.insert(w[1]);}
            Op::ExtInstImport => {
                if w.len()<3 || bytes(&w[2..]).split(|&c|c==0).next()!=Some(b"GLSL.std.450".as_slice()) {return Err("unexpected coordinate extended set".into());}
                imports.insert(w[1]);
            }
            Op::ExtInst => if w.len()<5 || !imports.contains(&w[3]) || w[4]==spirv::GlslStd450Op::Fma as u32 {return Err("fused or unknown coordinate extinst".into());},
            Op::FmaKHR => return Err("coordinate already fused".into()),
            Op::Decorate | Op::DecorateId => if at>=type_at || w.len()<3 || [Decoration::NoContraction as u32,Decoration::FPFastMathMode as u32].contains(&w[2]) {return Err("unexpected coordinate decoration".into());},
            Op::MemberDecorate => if at>=type_at || w.len()<4 || [Decoration::NoContraction as u32,Decoration::FPFastMathMode as u32].contains(&w[3]) {return Err("unexpected coordinate member decoration".into());},
            Op::FNegate | Op::FAdd | Op::FSub | Op::FMul | Op::FDiv | Op::FRem | Op::FMod |
            Op::VectorTimesScalar | Op::MatrixTimesScalar | Op::VectorTimesMatrix | Op::MatrixTimesVector |
            Op::MatrixTimesMatrix | Op::OuterProduct | Op::Dot => {
                if w.len()<4 || !types.contains(&w[1]) || w[2]==0 || w[2]>=words[3] || !results.insert(w[2]) {return Err("invalid coordinate arithmetic result".into());}
            }
            _ => {}
        }
    }
    if !saw64 || results.is_empty() {return Err("no live f64 coordinate arithmetic".into());}
    let entry=entry.ok_or("no coordinate entry")?;
    let mut additions:BTreeMap<usize,Vec<u32>>=BTreeMap::new();
    let caps=additions.entry(cap_at).or_default();
    for cap in [Capability::SignedZeroInfNanPreserve,Capability::RoundingModeRTE] {
        caps.extend_from_slice(&[(2<<16)|Op::Capability as u32,cap as u32]);
    }
    let mut name=b"SPV_KHR_float_controls\0".to_vec(); while name.len()%4!=0 {name.push(0);}
    caps.push((((name.len()/4+1) as u32)<<16)|Op::Extension as u32);
    caps.extend(name.chunks_exact(4).map(|w|u32::from_le_bytes(w.try_into().unwrap())));
    let modes=additions.entry(modes_end).or_default();
    for (mode,width) in [(ExecutionMode::SignedZeroInfNanPreserve,64),
        (ExecutionMode::RoundingModeRTE,32),(ExecutionMode::RoundingModeRTE,64)] {
        modes.extend_from_slice(&[(4<<16)|Op::ExecutionMode as u32,entry,mode as u32,width]);
    }
    let annotations=additions.entry(type_at).or_default();
    for &id in &results {annotations.extend_from_slice(&[(3<<16)|Op::Decorate as u32,id,Decoration::NoContraction as u32]);}
    let mut patched=words[..5].to_vec();let mut inserted=Vec::new();
    for &(at,_,w) in &insts {
        if let Some(extra)=additions.get(&at) {inserted.push((patched.len(),extra.clone()));patched.extend_from_slice(extra);}
        patched.extend_from_slice(w);
    }
    // Re-scan the emitted module and remove exactly the fixed inserted chunks.
    // No IDs, original instructions, bounds checks or operands may be changed.
    let checked=instructions(&patched)?;let starts:BTreeSet<_>=checked.iter().map(|(at,_,_)|*at).collect();
    let mut restored=patched.clone();
    for (at,extra) in inserted.iter().rev() {
        if !starts.contains(at) || &restored[*at..*at+extra.len()]!=extra.as_slice() {return Err("bad coordinate annotation insertion".into());}
        restored.drain(*at..*at+extra.len());
    }
    if restored!=words || inserted.len()!=additions.len() {return Err("coordinate SPIR-V patch exceeded fixed additions".into());}
    Ok((patched,results.len()))
}
pub struct DeviceCoordinates { layout:wgpu::BindGroupLayout, pipeline:wgpu::ComputePipeline }
impl DeviceCoordinates {
    pub fn new(device:&wgpu::Device, hardware:Hardware) -> Result<(Self,CoordinateReport),String> {
        let module=naga::front::glsl::Frontend::default().parse(&naga::front::glsl::Options::from(naga::ShaderStage::Compute),include_str!("coordinates.glsl"))
            .map_err(|e|format!("owned coordinate GLSL: {e:?}"))?;
        let info=validate(&module)?;
        if module.entry_points.len()!=1 || module.entry_points[0].name!="main" || module.entry_points[0].workgroup_size!=[64,1,1] {
            return Err("coordinate entry interface changed".into());
        }
        let mut options=spv::Options {lang_version:(1,0),flags:spv::WriterFlags::empty(),fake_missing_bindings:false,
            capabilities:Some([Capability::Shader,Capability::Float64].into_iter().collect()),
            bounds_check_policies:BoundsCheckPolicies{index:BoundsCheckPolicy::Restrict,buffer:BoundsCheckPolicy::Restrict,
                image_load:BoundsCheckPolicy::Restrict,binding_array:BoundsCheckPolicy::Restrict},
            force_loop_bounding:true,emit_int_div_checks:true,..Default::default()};
        let mut bindings=BTreeSet::new();
        for (_,global) in module.global_variables.iter() {
            let Some(binding)=global.binding else {continue;};
            let correct=match global.space {
                naga::AddressSpace::Uniform=>binding.binding==1,
                naga::AddressSpace::Storage{access}=>binding.binding!=1 && access.contains(naga::StorageAccess::STORE)==(binding.binding==2),
                _=>false };
            if binding.group!=0 || binding.binding>2 || !correct || !bindings.insert(binding.binding) {return Err("coordinate bindings changed".into());}
            options.binding_map.insert(binding,spv::BindingInfo{descriptor_set:0,binding:binding.binding,binding_array_size:None});
        }
        if bindings!=(0..3).collect() {return Err("coordinate needs exactly three bindings".into());}
        let original=spv::write_vec(&module,&info,&options,None).map_err(|e|format!("coordinate SPIR-V emission: {e:?}"))?;
        let parsed=naga::front::spv::parse_u8_slice(&bytes(&original),&naga::front::spv::Options {
            adjust_coordinate_space:false,strict_capabilities:true,block_ctx_dump_prefix:None}).map_err(|e|format!("original coordinate SPIR-V parse: {e:?}"))?;
        validate(&parsed)?;
        let (words,arithmetic_results)=patch(&original)?;
        let report=CoordinateReport{hardware,original_sha256:hash(&original),submitted_sha256:hash(&words),arithmetic_results,
            added_capabilities:["SignedZeroInfNanPreserve","RoundingModeRTE"],
            execution_modes:["SignedZeroInfNanPreserve 64","RoundingModeRTE 32","RoundingModeRTE 64"],
            coefficient_guard:COEFFICIENT_GUARD,
            entry_point:"main",bindings:[0,1,2],validation:"owned GLSL+Naga IR and original SPIR-V parse+IR; final fixed additions structurally checked with exact removal identity; final patched SPIR-V NOT fully Naga-validated and NOT spirv-val"};
        let entries:Vec<_>=(0..3).map(|binding|wgpu::BindGroupLayoutEntry{binding,visibility:wgpu::ShaderStages::COMPUTE,
            ty:wgpu::BindingType::Buffer{ty:if binding==1 {wgpu::BufferBindingType::Uniform}else{wgpu::BufferBindingType::Storage{read_only:binding==0}},has_dynamic_offset:false,min_binding_size:None},count:None}).collect();
        let layout=device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor{label:Some("device-f64-coordinate-layout"),entries:&entries});
        let pipeline_layout=device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor{label:None,bind_group_layouts:&[Some(&layout)],immediate_size:0});
        // SAFETY: caller checked Vulkan1.2, F64 and every requested float control
        // and enabled passthrough. Only the owned, bounded module above enters;
        // its final additive patch is structurally checked, not spirv-val-certified.
        let shader=unsafe {device.create_shader_module_passthrough(wgpu::ShaderModuleDescriptorPassthrough{
            label:Some("owned-f64-coordinate-spirv"),spirv:Some(Cow::Borrowed(&words)),
            entry_points:Cow::Owned(vec![wgpu::PassthroughShaderEntryPoint{name:Cow::Borrowed("main"),workgroup_size:(64,1,1)}]),..Default::default()})};
        let pipeline=device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor{label:Some("device-f64-coordinates"),layout:Some(&pipeline_layout),module:&shader,
            entry_point:Some("main"),compilation_options:Default::default(),cache:None});
        Ok((Self{layout,pipeline},report))
    }
    pub fn transforms(device:&wgpu::Device,pulls:[Similarity;3])->wgpu::Buffer {
        let values=pulls.map(|t|[t.a.re,t.a.im,t.b.re,t.b.im]);
        device.create_buffer_init(&wgpu::util::BufferInitDescriptor{label:Some("three-f64-pulls"),contents:bytemuck::cast_slice(&values),usage:wgpu::BufferUsages::STORAGE})
    }
    pub fn bind(&self,device:&wgpu::Device,transforms:&wgpu::Buffer,params:&wgpu::Buffer,plans:&wgpu::Buffer)->wgpu::BindGroup {
        let buffers=[transforms,params,plans];let entries:Vec<_>=buffers.iter().enumerate().map(|(i,b)|wgpu::BindGroupEntry{binding:i as u32,resource:b.as_entire_binding()}).collect();
        device.create_bind_group(&wgpu::BindGroupDescriptor{label:Some("device-coordinate-bindings"),layout:&self.layout,entries:&entries})
    }
    pub fn encode(&self,encoder:&mut wgpu::CommandEncoder,bind:&wgpu::BindGroup,count:usize) {
        let mut pass=encoder.begin_compute_pass(&wgpu::ComputePassDescriptor{label:Some("f64 coordinate strip"),timestamp_writes:None});
        pass.set_pipeline(&self.pipeline);pass.set_bind_group(0,bind,&[]);pass.dispatch_workgroups(count.div_ceil(64) as u32,1,1);
    }
    pub fn readback(&self,device:&wgpu::Device,queue:&wgpu::Queue,w:usize,h:usize,pulls:[Similarity;3],green:bool,y:usize,rows:usize)->Result<Vec<SamplePlan>,String> {
        if !coefficients_safe(pulls) {return Err(format!("unsafe device coordinate coefficients: {COEFFICIENT_GUARD}"));}
        let n=w.checked_mul(h).ok_or("coordinate extent overflow")?;
        if w==0 || h==0 || w%2!=0 || h%2!=0 || n>u32::MAX as usize/3 || w>i32::MAX as usize || h>i32::MAX as usize || rows==0 || rows>256 || y.checked_add(rows).is_none_or(|end|end>h) {
            return Err("invalid device coordinate dimensions/strip".into());
        }
        let count=w*rows;let bytes=(count*16) as u64;let limits=device.limits();
        if bytes>limits.max_storage_buffer_binding_size || bytes>limits.max_buffer_size || count.div_ceil(64)>limits.max_compute_workgroups_per_dimension as usize {return Err("device coordinate test exceeds device limits".into());}
        let params=Params{dims:[w as u32,h as u32,y as u32,rows as u32],photometry:[0.0;4],inverse:[0.0;4],flags:[u32::from(green),0,0,0]};
        let uniform=device.create_buffer_init(&wgpu::util::BufferInitDescriptor{label:Some("coordinate-test-parameters"),contents:bytemuck::bytes_of(&params),usage:wgpu::BufferUsages::UNIFORM});
        let transforms=Self::transforms(device,pulls);
        let plans=device.create_buffer(&wgpu::BufferDescriptor{label:Some("coordinate-test-output"),size:bytes,usage:wgpu::BufferUsages::STORAGE|wgpu::BufferUsages::COPY_SRC,mapped_at_creation:false});
        let stage=device.create_buffer(&wgpu::BufferDescriptor{label:None,size:bytes,usage:wgpu::BufferUsages::COPY_DST|wgpu::BufferUsages::MAP_READ,mapped_at_creation:false});
        let bind=self.bind(device,&transforms,&uniform,&plans);let mut encoder=device.create_command_encoder(&Default::default());
        self.encode(&mut encoder,&bind,count);encoder.copy_buffer_to_buffer(&plans,0,&stage,0,bytes);queue.submit([encoder.finish()]);
        let (tx,rx)=std::sync::mpsc::channel();stage.map_async(wgpu::MapMode::Read,..,move|r|{let _=tx.send(r);});
        device.poll(wgpu::PollType::wait_indefinitely()).map_err(|e|e.to_string())?;
        rx.recv().map_err(|e|e.to_string())?.map_err(|e|e.to_string())?;
        let out={let view=stage.get_mapped_range(..).map_err(|e|e.to_string())?;bytemuck::cast_slice::<u8,SamplePlan>(&view).to_vec()};
        stage.unmap();Ok(out)
    }
}
