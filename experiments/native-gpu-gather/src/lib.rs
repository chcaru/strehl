//! Default-off one-frame port of the current fullres MHC/Catmull gather.
//! No RAW decoder, noise estimator, selector, merge or writer lives here.
//! CPU geometry is intentionally retained in f64; shader arithmetic is f32.
//! Source/operation ordering is preserved, but GPU compiler contraction and
//! final rounded equivalence require independent execution, not a source claim.
use std::time::Instant;
use rayon::prelude::*;
use strehl_core::{align::{Resampler, Similarity}, plane::PlaneGeometry};
use wgpu::util::DeviceExt;
#[path = "strict-spirv.rs"]
mod strict_spirv;
pub use strict_spirv::CompilationReport;

/// Two fixed schedules for the same descriptor arithmetic and strict shader.
#[derive(Clone, Copy, Debug, Eq, PartialEq, serde::Serialize)]
pub enum Schedule { Serial32, Parallel256 }
impl Schedule {
    fn strip_rows(self) -> usize { match self { Self::Serial32 => 32, Self::Parallel256 => 256 } }
}
pub const INVALID: u32 = u32::MAX;
pub const UNCONSUMED: u32 = u32::MAX - 1;

#[repr(C)]
#[derive(Clone, Copy, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct SamplePlan { pub x0: u32, pub y0: u32, pub fx: f32, pub fy: f32 }

/// Exact current sample_checked support and Catmull cell/phase decisions.
/// Coordinates are native fullres coordinates, not quad coordinates.
pub fn plan_at(width: usize, height: usize, x: f64, y: f64) -> SamplePlan {
    let invalid = SamplePlan { x0: INVALID, y0: 0, fx: 0.0, fy: 0.0 };
    if !x.is_finite() || !y.is_finite() || x < 1.5 || y < 1.5
        || x > width as f64 - 2.5 || y > height as f64 - 2.5 {
        return invalid;
    }
    // The support test above leaves no legal sample when either extent < 4.
    let x = x.clamp(1.0, (width - 2) as f64);
    let y = y.clamp(1.0, (height - 2) as f64);
    let x0 = (x.floor() as usize).min(width - 3);
    let y0 = (y.floor() as usize).min(height - 3);
    SamplePlan { x0: x0 as u32, y0: y0 as u32,
        fx: (x - x0 as f64) as f32, fy: (y - y0 as f64) as f32 }
}

pub struct Input<'a> {
    pub data: &'a [u16],
    pub stride: usize,
    /// Decoded active rectangle; an odd trailing row/column is not consumed.
    pub active: [usize; 4],
    pub geom: PlaneGeometry,
    pub black: f32,
    /// Already normalized by the current CLI wb_gains helper.
    pub gain: [f32; 3],
    /// Already computed on the CPU by the current 1.0 / gain expression.
    pub inverse_gain: [f32; 3],
    /// Current OpticalProfile::compose result per R/G/B, in pull convention.
    pub pulls: [Similarity; 3],
    pub green_only: bool,
    pub malvar: bool,
    pub resampler: Resampler,
}

#[derive(Debug, Default)]
pub struct Costs {
    pub pack_ms: f64,
    pub coordinate_ms: f64,
    /// Host wall time in submissions/waits/readback, NOT GPU timestamp time.
    pub submit_wait_readback_ms: f64,
    pub total_ms: f64,
    pub source_upload_bytes: u64,
    pub coordinate_upload_bytes: u64,
    pub parameter_upload_bytes: u64,
    /// Includes explicit coverage readback used by the experiment's controls.
    pub download_bytes: u64,
    pub device_buffer_bytes: u64,
}

pub struct Output {
    /// Two horizontally adjacent native sensels per word, first in low bits.
    pub packed: Vec<u32>,
    /// Two low bits per packed word; unconsumed green-probe R/B sites are zero.
    pub coverage: Vec<u32>,
    pub width: usize,
    pub height: usize,
    pub covered: usize,
    pub consumed_sites: usize,
    pub schedule: Schedule,
    pub costs: Costs,
}

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
struct Params { dims: [u32;4], photometry: [f32;4], inverse: [f32;4], flags: [u32;4] }

pub struct GpuGather {
    device: wgpu::Device,
    queue: wgpu::Queue,
    layout: wgpu::BindGroupLayout,
    mhc: wgpu::ComputePipeline,
    gather: wgpu::ComputePipeline,
    quantize: wgpu::ComputePipeline,
    schedule: Schedule,
    pub adapter: String,
    pub device_type: String,
    pub backend: String,
    pub initialization_ms: f64,
    pub compilation: CompilationReport,
}

impl GpuGather {
    /// M7's permissive wgpu30 device/buffer mechanism, with no timing feature,
    /// all-frame residency, ring kernel or merge reduction carried forward.
    pub fn new() -> Result<Self, String> { Self::new_with_arithmetic(true) }

    /// Single diagnostic: identical generated SPIR-V without NoContraction.
    /// This is not an alternative production/default path.
    pub fn new_undecorated_for_test() -> Result<Self, String> { Self::new_with_arithmetic(false) }

    fn new_with_arithmetic(strict: bool) -> Result<Self, String> {
        let start = Instant::now();
        let (words, mut compilation) = strict_spirv::compile(strict)?;
        let mut descriptor = wgpu::InstanceDescriptor::new_without_display_handle();
        descriptor.backends = wgpu::Backends::VULKAN;
        let instance = wgpu::Instance::new(descriptor);
        let adapter = pollster::block_on(instance.request_adapter(&wgpu::RequestAdapterOptions {
            power_preference: wgpu::PowerPreference::HighPerformance,
            force_fallback_adapter: false, compatible_surface: None, apply_limit_buckets: false,
        })).map_err(|e| e.to_string())?;
        let info = adapter.get_info();
        if info.device_type != wgpu::DeviceType::DiscreteGpu {
            return Err(format!("GPU gather requires a discrete hardware adapter, got {} ({:?})",info.name,info.device_type));
        }
        if info.backend != wgpu::Backend::Vulkan || !adapter.features().contains(wgpu::Features::PASSTHROUGH_SHADERS) {
            return Err("strict GPU gather requires Vulkan + PASSTHROUGH_SHADERS".into());
        }
        let (device, queue) = pollster::block_on(adapter.request_device(&wgpu::DeviceDescriptor {
            label: Some("native-gpu-gather"), required_features: wgpu::Features::PASSTHROUGH_SHADERS,
            required_limits: adapter.limits(), experimental_features: wgpu::ExperimentalFeatures::disabled(),
            memory_hints: wgpu::MemoryHints::Performance, trace: wgpu::Trace::Off,
        })).map_err(|e| e.to_string())?;
        compilation.max_storage_buffer_binding_size = device.limits().max_storage_buffer_binding_size;
        compilation.max_buffer_size = device.limits().max_buffer_size;
        device.on_uncaptured_error(std::sync::Arc::new(|e| panic!("GPU gather error: {e}")));
        let entries: Vec<_> = (0..6).map(|binding| wgpu::BindGroupLayoutEntry {
            binding, visibility: wgpu::ShaderStages::COMPUTE,
            ty: wgpu::BindingType::Buffer {
                ty: if binding == 0 { wgpu::BufferBindingType::Uniform }
                    else { wgpu::BufferBindingType::Storage { read_only: binding == 1 || binding == 3 } },
                has_dynamic_offset: false, min_binding_size: None,
            }, count: None,
        }).collect();
        let layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("native-gather-layout"), entries: &entries,
        });
        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: None, bind_group_layouts: &[Some(&layout)], immediate_size: 0,
        });
        let module = strict_spirv::module(&device, &words);
        let pipeline = |entry| device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some(entry), layout: Some(&pipeline_layout), module: &module,
            entry_point: Some(entry), compilation_options: Default::default(), cache: None,
        });
        let mhc = pipeline("mhc"); let gather = pipeline("gather");
        let quantize = pipeline("quantize_vector");
        Ok(Self { device, queue, layout, mhc, gather, quantize, schedule: Schedule::Parallel256,
            adapter: info.name.clone(), device_type: format!("{:?}",info.device_type),
            backend: format!("{:?}",info.backend), compilation, initialization_ms: start.elapsed().as_secs_f64()*1000.0 })
    }

    /// Change only descriptor scheduling and strip size; reuse this GPU context.
    pub fn set_schedule(&mut self, schedule: Schedule) { self.schedule = schedule; }
    pub fn schedule(&self) -> Schedule { self.schedule }

    /// One call owns one resident source frame. No aligned stack is retained.
    /// The caller must explicitly select this experiment; unsupported modes
    /// return Err before upload rather than silently changing the operator.
    pub fn run(&mut self, input: &Input<'_>) -> Result<Output, String> {
        self.run_inner(input, None)
    }

    /// Independent control seam; the ordinary experiment has no mutator.
    pub fn run_with_plan_mutator(&mut self, input: &Input<'_>,
        mutate: &mut dyn FnMut(usize, &mut [SamplePlan])) -> Result<Output, String> {
        self.run_inner(input, Some(mutate))
    }

    fn run_inner(&mut self, input: &Input<'_>,
        mut mutate: Option<&mut dyn FnMut(usize, &mut [SamplePlan])>) -> Result<Output, String> {
        let total = Instant::now();
        if !input.malvar || input.resampler != Resampler::CatmullRom {
            return Err("GPU prototype supports explicit Malvar + CatmullRom only".into());
        }
        let (gw,gh) = (input.geom.width,input.geom.height);
        let [ax,ay,aw,ah] = input.active;
        if gw == 0 || gh == 0 || aw/2 != gw || ah/2 != gh {
            return Err("GPU gather active/quad geometry mismatch".into());
        }
        let (w,h) = (gw.checked_mul(2).ok_or("width overflow")?,gh.checked_mul(2).ok_or("height overflow")?);
        let n = w.checked_mul(h).ok_or("pixel count overflow")?;
        if n > u32::MAX as usize / 3 || w > i32::MAX as usize || h > i32::MAX as usize {
            return Err("GPU gather indexing exceeds its u32/i32 domain".into());
        }
        let end_x = ax.checked_add(w).ok_or("active x overflow")?;
        let end_y = ay.checked_add(h).ok_or("active y overflow")?;
        if end_x > input.stride || end_y.checked_mul(input.stride).ok_or("storage overflow")? > input.data.len() {
            return Err("GPU gather active rectangle exceeds storage".into());
        }
        // Finite input bound makes shader intermediates representable. Unusual
        // metadata outside this bound is an explicit unsupported configuration.
        if !input.black.is_finite() || input.gain.iter().chain(&input.inverse_gain).any(|v| !v.is_finite() || *v <= 0.0) {
            return Err("GPU gather requires finite positive WB and finite black".into());
        }
        let gain_max = input.gain.iter().copied().fold(0.0f32,f32::max) as f64;
        let inv_max = input.inverse_gain.iter().copied().fold(0.0f32,f32::max) as f64;
        let bound = (65535.0 + (input.black as f64).abs()) * gain_max * 64.0;
        if bound > f32::MAX as f64 || bound*inv_max+(input.black as f64).abs() > f32::MAX as f64 {
            return Err("GPU gather finite intermediate bound exceeded".into());
        }
        let mut costs = Costs::default();
        let pack_start = Instant::now();
        let mut packed = Vec::with_capacity(n/2);
        for y in 0..h { let row = (ay+y)*input.stride+ax;
            for x in (0..w).step_by(2) { packed.push(u32::from(input.data[row+x]) | (u32::from(input.data[row+x+1])<<16)); }
        }
        costs.pack_ms = pack_start.elapsed().as_secs_f64()*1000.0;
        let schedule = self.schedule;
        let strip_rows = schedule.strip_rows();
        let strip_n = w*strip_rows.min(h);
        let source_bytes = (n*2) as u64;
        let rgb_bytes = (n*4*if input.green_only {1} else {3}) as u64;
        let plan_bytes = (strip_n*std::mem::size_of::<SamplePlan>()) as u64;
        let output_bytes = (strip_n*2) as u64;
        let limits = self.device.limits();
        for bytes in [source_bytes,rgb_bytes,plan_bytes,output_bytes] {
            if bytes > u64::from(limits.max_storage_buffer_binding_size) || bytes > limits.max_buffer_size {
                return Err(format!("GPU buffer {bytes} exceeds adapter binding/buffer limit"));
            }
        }
        if output_bytes*2 > limits.max_buffer_size
            || w.div_ceil(64) > limits.max_compute_workgroups_per_dimension as usize
            || h > limits.max_compute_workgroups_per_dimension as usize
            || (strip_n/2).div_ceil(64) > limits.max_compute_workgroups_per_dimension as usize {
            return Err("GPU dispatch/staging limit exceeded".into());
        }
        let execute_start = Instant::now();
        let source = self.device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("original-packed-cfa"), contents: bytemuck::cast_slice(&packed), usage: wgpu::BufferUsages::STORAGE,
        });
        let make_buffer = |label,size,usage| self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some(label), size, usage, mapped_at_creation: false,
        });
        let rgb = make_buffer("source-mhc",rgb_bytes,wgpu::BufferUsages::STORAGE);
        let plans = make_buffer("exact-cpu-coordinate-strip",plan_bytes,wgpu::BufferUsages::STORAGE|wgpu::BufferUsages::COPY_DST);
        let output = make_buffer("packed-gather-strip",output_bytes,wgpu::BufferUsages::STORAGE|wgpu::BufferUsages::COPY_SRC);
        let coverage = make_buffer("coverage-strip",output_bytes,wgpu::BufferUsages::STORAGE|wgpu::BufferUsages::COPY_SRC);
        let stage = make_buffer("packed-readback-strip",output_bytes*2,wgpu::BufferUsages::COPY_DST|wgpu::BufferUsages::MAP_READ);
        let mut params = Params { dims:[w as u32,h as u32,0,h as u32],
            photometry:[input.black,input.gain[0],input.gain[1],input.gain[2]],
            inverse:[input.inverse_gain[0],input.inverse_gain[1],input.inverse_gain[2],input.black.round().clamp(0.0,65535.0)],
            flags:[u32::from(input.green_only),0,0,0] };
        let uniform = self.device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("current-gather-parameters"), contents: bytemuck::bytes_of(&params),
            usage: wgpu::BufferUsages::UNIFORM|wgpu::BufferUsages::COPY_DST,
        });
        let buffers = [&uniform,&source,&rgb,&plans,&output,&coverage];
        let entries: Vec<_> = buffers.iter().enumerate().map(|(i,b)| wgpu::BindGroupEntry {
            binding:i as u32,resource:b.as_entire_binding(),
        }).collect();
        let bind = self.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label:None,layout:&self.layout,entries:&entries,
        });
        let mut encoder = self.device.create_command_encoder(&Default::default());
        { let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {label:Some("MHC"),timestamp_writes:None});
          pass.set_pipeline(&self.mhc);pass.set_bind_group(0,&bind,&[]);pass.dispatch_workgroups(w.div_ceil(64) as u32,h as u32,1); }
        self.queue.submit([encoder.finish()]);
        self.device.poll(wgpu::PollType::wait_indefinitely()).map_err(|e|e.to_string())?;
        costs.submit_wait_readback_ms += execute_start.elapsed().as_secs_f64()*1000.0;
        costs.source_upload_bytes = source_bytes;
        costs.parameter_upload_bytes = std::mem::size_of::<Params>() as u64;
        costs.device_buffer_bytes = source_bytes+rgb_bytes+plan_bytes+4*output_bytes+std::mem::size_of::<Params>() as u64;
        let mut all_coverage = Vec::with_capacity(n/2);
        let mut covered = 0usize;
        let mut plan = match schedule {
            Schedule::Serial32 => Vec::with_capacity(strip_n),
            // Initialize once, not once per strip. Only the last strip truncates.
            Schedule::Parallel256 => vec![SamplePlan{x0:INVALID,y0:0,fx:0.0,fy:0.0}; strip_n],
        };
        let point = |y: usize, x: usize| {
            let ci = if y%2 == 0 && x%2 == 0 {0} else if y%2 == 1 && x%2 == 1 {2} else {1};
            if input.green_only && ci != 1 {
                return SamplePlan{x0:UNCONSUMED,y0:0,fx:0.0,fy:0.0};
            }
            let (sx,sy) = input.pulls[ci].apply_at((x/2) as f64+(x%2) as f64*0.5,
                (y/2) as f64+(y%2) as f64*0.5,gw as f64*0.5,gh as f64*0.5);
            plan_at(w,h,2.0*sx,2.0*sy)
        };
        let invalid = |tap: &SamplePlan| tap.x0 < UNCONSUMED && (tap.x0 < 1 || tap.y0 < 1
            || tap.x0 as usize + 2 >= w || tap.y0 as usize + 2 >= h
            || !tap.fx.is_finite() || !tap.fy.is_finite()
            || !(0.0..=1.0).contains(&tap.fx) || !(0.0..=1.0).contains(&tap.fy));
        for y_start in (0..h).step_by(strip_rows) {
            let rows = strip_rows.min(h-y_start);
            let coordinate_start = Instant::now();
            match schedule {
                Schedule::Serial32 => {
                    plan.clear();
                    for y in y_start..y_start+rows { for x in 0..w { plan.push(point(y,x)); } }
                }
                Schedule::Parallel256 => {
                    plan.truncate(rows*w);
                    plan.par_chunks_mut(w).enumerate().for_each(|(row, taps)| {
                        let y = y_start+row;
                        for (x,tap) in taps.iter_mut().enumerate() { *tap = point(y,x); }
                    });
                }
            }
            // Parallel row completion precedes the independent mutation seam.
            if let Some(f) = mutate.as_mut() { f(y_start, &mut plan); }
            let invalid_plan = match schedule {
                Schedule::Serial32 => plan.iter().any(invalid),
                Schedule::Parallel256 => plan.par_chunks(w).any(|row|row.iter().any(invalid)),
            };
            if invalid_plan { return Err("coordinate control supplied an invalid Catmull stencil".into()); }
            costs.coordinate_ms += coordinate_start.elapsed().as_secs_f64()*1000.0;
            let execute_start = Instant::now();
            params.dims[2] = y_start as u32;params.dims[3] = rows as u32;
            self.queue.write_buffer(&uniform,0,bytemuck::bytes_of(&params));
            self.queue.write_buffer(&plans,0,bytemuck::cast_slice(&plan));
            let bytes = (w*rows*2) as u64;
            let mut encoder = self.device.create_command_encoder(&Default::default());
            { let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {label:Some("Catmull packed gather"),timestamp_writes:None});
              pass.set_pipeline(&self.gather);pass.set_bind_group(0,&bind,&[]);pass.dispatch_workgroups((w*rows/2).div_ceil(64) as u32,1,1); }
            encoder.copy_buffer_to_buffer(&output,0,&stage,0,bytes);
            encoder.copy_buffer_to_buffer(&coverage,0,&stage,bytes,bytes);
            self.queue.submit([encoder.finish()]);
            let (tx,rx) = std::sync::mpsc::channel();
            stage.map_async(wgpu::MapMode::Read,0..2*bytes,move |r| {let _=tx.send(r);});
            self.device.poll(wgpu::PollType::wait_indefinitely()).map_err(|e|e.to_string())?;
            rx.recv().map_err(|e|e.to_string())?.map_err(|e|e.to_string())?;
            { let view = stage.get_mapped_range(0..2*bytes).map_err(|e|e.to_string())?;
              let words: &[u32] = bytemuck::cast_slice(&view);let len=w*rows/2;
              packed[y_start*w/2..(y_start+rows)*w/2].copy_from_slice(&words[..len]);
              for &bits in &words[len..] {covered += (bits&3).count_ones() as usize;}
              all_coverage.extend_from_slice(&words[len..]); }
            stage.unmap();
            costs.submit_wait_readback_ms += execute_start.elapsed().as_secs_f64()*1000.0;
            costs.coordinate_upload_bytes += (plan.len()*std::mem::size_of::<SamplePlan>()) as u64;
            costs.parameter_upload_bytes += std::mem::size_of::<Params>() as u64;
            costs.download_bytes += 2*bytes;
        }
        costs.total_ms = total.elapsed().as_secs_f64()*1000.0;
        Ok(Output { packed,coverage:all_coverage,width:w,height:h,covered,
            consumed_sites:if input.green_only {n/2} else {n},schedule,costs })
    }

    /// Test-only-purpose entry point, using the actual shader quantizer.
    pub fn quantize_for_test(&mut self, values: &[f32]) -> Result<Vec<u32>, String> {
        if values.is_empty() { return Ok(Vec::new()); }
        let bytes = (values.len()*4) as u64;
        if values.len() > u32::MAX as usize || bytes*4 > u64::from(self.device.limits().max_storage_buffer_binding_size)
            || values.len().div_ceil(64) > self.device.limits().max_compute_workgroups_per_dimension as usize {
            return Err("quantization control exceeds device limits".into());
        }
        let params = Params { dims:[1,1,0,values.len() as u32], photometry:[0.0;4],inverse:[0.0;4],flags:[0;4] };
        let buffer = |label,contents:&[u8],usage| self.device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label:Some(label),contents,usage,
        });
        let uniform = buffer("quantizer-control",bytemuck::bytes_of(&params),wgpu::BufferUsages::UNIFORM);
        let dummy_raw = buffer("unused-control-raw",&[0u8;4],wgpu::BufferUsages::STORAGE);
        let dummy_rgb = buffer("unused-control-rgb",&[0u8;4],wgpu::BufferUsages::STORAGE);
        let dummy_coverage = buffer("unused-control-coverage",&[0u8;4],wgpu::BufferUsages::STORAGE);
        let values: Vec<_> = values.iter().map(|&v|SamplePlan{x0:0,y0:0,fx:v,fy:0.0}).collect();
        let plans = buffer("literal-quantizer-values",bytemuck::cast_slice(&values),wgpu::BufferUsages::STORAGE);
        let output = self.device.create_buffer(&wgpu::BufferDescriptor {
            label:Some("quantizer-results"),size:bytes,usage:wgpu::BufferUsages::STORAGE|wgpu::BufferUsages::COPY_SRC,mapped_at_creation:false,
        });
        let stage = self.device.create_buffer(&wgpu::BufferDescriptor {
            label:None,size:bytes,usage:wgpu::BufferUsages::MAP_READ|wgpu::BufferUsages::COPY_DST,mapped_at_creation:false,
        });
        let buffers = [&uniform,&dummy_raw,&dummy_rgb,&plans,&output,&dummy_coverage];
        let entries:Vec<_> = buffers.iter().enumerate().map(|(i,b)|wgpu::BindGroupEntry{binding:i as u32,resource:b.as_entire_binding()}).collect();
        let bind = self.device.create_bind_group(&wgpu::BindGroupDescriptor{label:None,layout:&self.layout,entries:&entries});
        let mut encoder = self.device.create_command_encoder(&Default::default());
        { let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor{label:Some("literal quantizer"),timestamp_writes:None});
          pass.set_pipeline(&self.quantize);pass.set_bind_group(0,&bind,&[]);pass.dispatch_workgroups(values.len().div_ceil(64) as u32,1,1); }
        encoder.copy_buffer_to_buffer(&output,0,&stage,0,bytes);self.queue.submit([encoder.finish()]);
        let (tx,rx) = std::sync::mpsc::channel();
        stage.map_async(wgpu::MapMode::Read,..,move |r|{let _=tx.send(r);});
        self.device.poll(wgpu::PollType::wait_indefinitely()).map_err(|e|e.to_string())?;
        rx.recv().map_err(|e|e.to_string())?.map_err(|e|e.to_string())?;
        let out = {let view=stage.get_mapped_range(..).map_err(|e|e.to_string())?;bytemuck::cast_slice::<u8,u32>(&view).to_vec()};
        stage.unmap();Ok(out)
    }
}
